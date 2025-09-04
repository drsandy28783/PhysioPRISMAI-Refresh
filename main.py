import os
import re
import io
import json
import csv
import profile
import requests
import secrets
from flask import (Flask, render_template, request, redirect,session, url_for, flash,jsonify, make_response, g)
from datetime import datetime, timezone
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from xhtml2pdf import pisa
from functools import wraps
import logging
from google.api_core.exceptions import GoogleAPIError
from firebase_admin_init import db
from firebase_admin import auth as fb_auth,  firestore as _fa_fs
SERVER_TIMESTAMP = _fa_fs.SERVER_TIMESTAMP
from firestore_helpers import (upsert_user_profile, create_patient, list_patients_for_owner, update_patient, delete_patient, create_follow_up, list_followups_for_patient
)
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore
from werkzeug.utils import secure_filename
from flask_cors import CORS

ALLOWED_ORIGINS = [
    "https://physiologicprism.com",
    "https://www.physiologicprism.com",
    "https://physioprismai-refresh-1.onrender.com",  # keep during transition
    "http://localhost:3000", "http://127.0.0.1:3000"  # local dev
]


import openai
# some versions of the OpenAI pip package don’t expose openai.error
try:
    from openai import OpenAIError
except ImportError:
    # fall back so our except‐clauses below still work
    OpenAIError = Exception


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# initialize OpenAI
openai.api_key = os.environ['OPENAI_API_KEY']
AI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4-turbo")
AI_TEMPERATURE = float(os.environ.get("OPENAI_TEMPERATURE", "0.2"))
AI_MAXTOKENS_DEFAULT = int(os.environ.get("OPENAI_MAXTOKENS_DEFAULT", "140"))

_PHI_PATTERNS = [
    (re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.I), "[REDACTED_EMAIL]"),
    (re.compile(r'\b(?:\+?\d[\d\s\-]{7,}\d)\b'), "[REDACTED_PHONE]"),
    (re.compile(r'\b\d{1,2}\s+[A-Za-z]{3,}\s+\d{2,4}\b'), "[REDACTED_DATE]"),
    (re.compile(r'\b\d{4}-\d{2}-\d{2}\b'), "[REDACTED_DATE]"),
    (re.compile(r'\b\d{2}/\d{2}/\d{2,4}\b'), "[REDACTED_DATE]"),
    (re.compile(r'\b(?:MRN|UHID|ID)[:\s]*[A-Za-z0-9-]{4,}\b', re.I), "[REDACTED_ID]"),
    (re.compile(r'\b\d{12,16}\b'), "[REDACTED_NUMBER]"),
]

def _redact_phi(text: str, max_chars: int = 1500) -> str:
    text = (text or "")[:max_chars]
    for pat, repl in _PHI_PATTERNS:
        text = pat.sub(repl, text)
    return text.strip()

def _clip_output(text: str, max_lines: int = 8) -> str:
    if not text:
        return ""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines[:max_lines]).strip()



def _truthy(v):
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "y", "on")
    return bool(v)

def _get_user_profile():
    """
    Tries UID first (if session['user_id'] looks like a UID), then falls back to email-keyed doc.
    Returns dict with at least {'id': <doc_id>, ...} or None.
    """
    uid = session.get('user_id')
    email = (session.get('email') or session.get('user_email') or "").lower()

    # Try UID doc if uid doesn't look like an email
    if uid and "@" not in uid:
        snap = db.collection("users").document(uid).get()
        if snap.exists:
            d = snap.to_dict() or {}
            d["id"] = snap.id
            return d

    # Fallback to email-keyed doc (your current schema)
    key = email or (uid if uid and "@" in uid else None)
    if key:
        snap = db.collection("users").document(key).get()
        if snap.exists:
            d = snap.to_dict() or {}
            d["id"] = snap.id
            return d
    return None

def get_uid_from_request() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    id_token = auth_header.split(" ", 1)[1].strip()
    try:
        decoded = fb_auth.verify_id_token(id_token)
        return decoded.get("uid")
    except Exception:
        return None

def get_user_data_scope(profile):
    """Determine what data user can access based on role"""
    role = profile.get('role', 'individual')
    
    return {
        'role': role,
        'institute_id': profile.get('institute_id') if role in ['institute_admin', 'institute_physio'] else None,
        'can_see_institute_data': role == 'institute_admin'
    }

AUTH_BASE = "https://identitytoolkit.googleapis.com/v1"
FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY')  # already present, keep

def _firebase_signup(email: str, password: str):
    url = f"{AUTH_BASE}/accounts:signUp?key={FIREBASE_WEB_API_KEY}"
    r = requests.post(url, json={
        "email": email, "password": password, "returnSecureToken": True
    }, timeout=20)
    return r.json()

def _firebase_signin(email: str, password: str):
    url = f"{AUTH_BASE}/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    r = requests.post(url, json={
        "email": email, "password": password, "returnSecureToken": True
    }, timeout=20)
    return r.json()

def _ensure_individual_profile(email: str, uid: str, name: str = ""):
    """Keep your current email-keyed schema; create if missing."""
    ref = db.collection('users').document(email)
    snap = ref.get()
    if not snap.exists:
        ref.set({
            'uid': uid,
            'email': email,
            'name': name or email.split('@')[0],
            'role': 'individual',
            'approved': 1,         # individuals are self‑serve
            'active': 1,
            'is_admin': 0,
            'created_at': SERVER_TIMESTAMP,
            'updated_at': SERVER_TIMESTAMP,
            # slots for future monetization/compliance
            'tokens_remaining': 0,
            'gdpr_consent': False,
            'hipaa_ack': False,
        })
    else:
        ref.set({'uid': uid, 'updated_at': SERVER_TIMESTAMP}, merge=True)

def _age_sex_from(data: dict, patient: dict | None = None) -> str:
    """Return a safe 'age sex' string from request data / previous / patient, or 'Unknown'."""
    data = data or {}
    prev = data.get("previous", {}) or {}

    # Try the ready-made field first
    age_sex = (data.get("age_sex")
               or prev.get("age_sex")
               or (patient.get("age_sex") if patient else "")
               or "").strip()

    # If not present, synthesize from age + sex wherever available
    if not age_sex:
        age = (data.get("age") or prev.get("age") or (patient.get("age") if patient else None))
        sex = (data.get("sex") or prev.get("sex") or (patient.get("sex") if patient else "")).strip()
        parts = []
        if age is not None and str(age).strip():
            parts.append(str(age).strip())
        if sex:
            parts.append(sex)
        age_sex = " ".join(parts).strip()

    return age_sex or "Unknown"

def _age_sex_from(data: dict, patient: dict | None = None) -> str:
    """Safely return 'age sex' string from data / previous / patient, or 'Unknown'."""
    data = data or {}
    prev = (data.get("previous") or {}) if isinstance(data.get("previous"), dict) else {}
    age_sex = (data.get("age_sex") or prev.get("age_sex") or (patient or {}).get("age_sex") or "").strip()
    if not age_sex:
        age = data.get("age") or prev.get("age") or (patient or {}).get("age")
        sex = (data.get("sex") or prev.get("sex") or (patient or {}).get("sex") or "").strip()
        parts = []
        if age is not None and str(age).strip():
            parts.append(str(age).strip())
        if sex:
            parts.append(sex)
        age_sex = " ".join(parts).strip()
    return age_sex or "Unknown"

def _present_history_from(data: dict) -> str:
    if not data: return ""
    prev = data.get("previous") or {}
    return (data.get("present_history") or prev.get("present_history") or "").strip()

def _past_history_from(data: dict) -> str:
    if not data: return ""
    prev = data.get("previous") or {}
    return (data.get("past_history") or prev.get("past_history") or "").strip()

def _subjective_from(data: dict) -> dict:
    if not data:
        return {}
    prev = data.get("previous") or {}
    val = data.get("subjective") or prev.get("subjective") or {}
    return val if isinstance(val, dict) else {}


def _perspectives_from(data: dict) -> dict:
    if not data: return {}
    prev = data.get("previous") or {}
    val = data.get("perspectives") or prev.get("perspectives") or {}
    return val if isinstance(val, dict) else {}

def _assessments_from(data: dict) -> dict:
        if not data:
            return {}
        prev = data.get("previous") or {}
        val = data.get("assessments") or prev.get("assessments") or {}
        return val if isinstance(val, dict) else {}

def _collect_prev(data: dict, patient: dict | None = None) -> dict:
    """One object you can insert into any prompt."""
    return {
        "age_sex":         _age_sex_from(data, patient),
        "present_history": _present_history_from(data),
        "past_history":    _past_history_from(data),
        "subjective":      _subjective_from(data),
        "perspectives":    _perspectives_from(data),
        "assessments":     _assessments_from(data),
    }

def _nz(x, default="None"):
    s = (x or "").strip() if isinstance(x, str) else x
    return str(s) if s not in (None, "", []) else default

def _has_role(profile, role):
    if role == "super_admin":
        return _truthy(profile.get("is_super_admin")) or profile.get("role") == "super_admin"
    if role == "admin":
        # treat legacy flags as admin
        return _truthy(profile.get("is_admin")) or profile.get("role") in ("admin", "institute_admin")
    return profile.get("role") == role

def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        def _w(*a, **k):
            prof = _get_user_profile()
            if not prof:
                return redirect(url_for("login"))
            if any(_has_role(prof, r) for r in roles):
                return fn(*a, **k)
            return ("Forbidden", 403)
        return _w
    return deco
def now_ts():
    return datetime.now(timezone.utc)



AI_REQUEST_TIMEOUT = int(os.getenv("AI_REQUEST_TIMEOUT", "18"))

def get_ai_suggestion(prompt: str) -> str:
    """PHI-safe, token-efficient single entry point used by all endpoints."""
    safe_prompt = _redact_phi(prompt, max_chars=1500).strip()
    if not safe_prompt:
        return ""  # fast-fail on empty input

    start = datetime.now(timezone.utc)
    try:
        resp = openai.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content":
                 "You are a physiotherapy assistant. PHI guardrails: never output or request names, "
                 "addresses, phone numbers, emails, dates of birth, IDs, or exact locations. "
                 "Be concise and return only the requested items."},
                {"role": "user", "content": safe_prompt},
            ],
            temperature=AI_TEMPERATURE,
            max_tokens=AI_MAXTOKENS_DEFAULT,
            stop=[],
            # For SDKs <1.0: use request_timeout=AI_REQUEST_TIMEOUT
            timeout=AI_REQUEST_TIMEOUT,
        )
        out = (resp.choices[0].message.content or "").strip()
        return _clip_output(out, max_lines=8)
    except Exception as e:
        logger.error("OpenAI call failed: %r", e, exc_info=True)
        # bubble up; your route's except turns this into JSON error already
        raise
    finally:
        try:
            ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
            logger.info("AI call took %sms", ms)
        except Exception:
            pass



def log_action(user_id, action, details=None):
    """Append an entry into Firestore `audit_logs` collection."""
    entry = {
        'user_id': user_id,
        'action': action,
        'details': details,
        'timestamp': SERVER_TIMESTAMP
    }
    db.collection('audit_logs').add(entry)

def fetch_patient(patient_id):
    """Return a patient dict or None if not found or on error."""
    try:
        doc = db.collection('patients').document(patient_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data['patient_id'] = doc.id
        return data
    except GoogleAPIError as e:
        logger.error(f"Firestore error fetching patient {patient_id}: {e}", exc_info=True)
        return None

# REPLACE the _json_or_form function (around line 396) with this:
def _json_or_form(req):
    """Robust request data parsing for both web forms and mobile JSON"""
    
    # First try: Standard JSON parsing
    try:
        data = req.get_json(force=False, silent=True)
        if data:
            return data
    except Exception:
        pass
    
    # Second try: Form data (for web)
    if req.form:
        return req.form.to_dict()
    
    # Third try: Raw data as JSON (for mobile)
    try:
        raw_data = req.get_data(as_text=True)
        if raw_data:
            import json
            return json.loads(raw_data)
    except Exception:
        pass
    
    # Fourth try: Empty request
    return {}



app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
app.secret_key =os.environ.get('SECRET_KEY', 'dev_default_key')
app.config['WTF_CSRF_ENABLED'] = True
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d-%m-%Y'):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime(format)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# make sure you set a secret key for sessions + CSRF 
# initialize CSRF protection on *all* POST routes by default
csrf = CSRFProtect(app)
CORS(
    app,
    resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
    supports_credentials=False,  # we're using Authorization header, not cookies
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Authorization", "Content-Disposition"],
    methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
)

# ─── CSRF ERROR HANDLING ────────────────────────────
@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    flash("The form you submitted is invalid or has expired. Please try again.", "error")
    return redirect(request.referrer or url_for('index')), 400

# ─── EXPOSE CSRF TOKEN TO TEMPLATES & AJAX ───────────
@app.after_request
def set_csrf_cookie(response):
    response.set_cookie('csrf_token', generate_csrf())
    return response

@app.after_request
def add_cors(resp):
    resp.headers.setdefault("Access-Control-Allow-Origin", "*")
    resp.headers.setdefault("Access-Control-Allow-Headers", "Content-Type, Authorization")
    resp.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
    return resp


@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)

@app.get("/_firestore_ping")
def firestore_ping():
    # Write a heartbeat doc so we know credentials & Firestore work
    db.collection("_health").document("last_ping").set(
        {"ts": _fa_fs.SERVER_TIMESTAMP}, merge=True
    )
    return jsonify({"ok": True})

@app.before_request
def _cors_preflight():
    if request.method == "OPTIONS":
        resp = make_response("", 204)
        resp.headers.setdefault("Access-Control-Allow-Origin", "*")
        resp.headers.setdefault("Access-Control-Allow-Headers", "Content-Type, Authorization")
        resp.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        return resp


@app.before_request
def enforce_custom_domain():
    host = request.headers.get("Host", "")
    # If someone visits the Render subdomain or apex, redirect to www
    if host.endswith("onrender.com") or host == "physiologicprism.com":
        return redirect(
            request.url.replace(host, "www.physiologicprism.com", 1),
            code=301
        )





# ─────────────────────────────────────────────────────────────────────────────
# API HELPERS: token-auth admin check + profile lookup by UID
# ─────────────────────────────────────────────────────────────────────────────




def _profile_by_uid(uid: str) -> dict | None:
    """Return the email-keyed user profile for a given Firebase UID."""
    q = db.collection("users").where("uid", "==", uid).limit(1).get()
    if not q:
        return None
    doc = q[0]
    d = doc.to_dict() or {}
    d.setdefault("id", doc.id)  # email doc id
    return d

def _is_admin(profile: dict) -> bool:
    role = (profile.get("role") or "").lower()
    return int(profile.get("is_admin", 0)) == 1 or role in ("admin", "institute_admin")

def _require_admin_from_token():
    """
    Returns (profile_dict, error_response_or_None).
    Validates Authorization Bearer token, loads profile by UID, ensures admin.
    """
    uid = get_uid_from_request()
    if not uid:
        return None, (jsonify({"ok": False, "error": "UNAUTHORIZED"}), 401)
    me = _profile_by_uid(uid)
    if not me:
        return None, (jsonify({"ok": False, "error": "PROFILE_NOT_FOUND"}), 403)
    if not _is_admin(me):
        return None, (jsonify({"ok": False, "error": "FORBIDDEN"}), 403)
    return me, None

# ─────────────────────────────────────────────────────────────────────────────
# 1) JSON: AUDIT LOGS (admin: institute-wide; non-admin: self)
#    GET /api/audit_logs   -> { ok: true, items: [...], admin?: {...} }
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# 2) JSON: USER APPROVAL / REJECTION (admin only; same institute)
#    POST /api/users/approve  { email }
#    POST /api/users/reject   { email }
# ─────────────────────────────────────────────────────────────────────────────



@app.get("/api/patients/<patient_id>")
@csrf.exempt  # GET doesn’t need CSRF, but exempt is harmless for mobile
def api_get_patient(patient_id):
    uid = get_uid_from_request()
    if not uid:
        return jsonify({"ok": False, "error": "UNAUTHORIZED"}), 401

    try:
        data = fetch_patient(patient_id)  # must exist in your codebase
    except Exception as e:
        return jsonify({"ok": False, "error": "FETCH_FAILED"}), 500

    if not data:
        return jsonify({"ok": False, "error": "NOT_FOUND"}), 404

    # Optional owner check (uncomment if you store owner_uid on patient)
    # if data.get("owner_uid") != uid and not _is_admin(_profile_by_uid(uid) or {}):
    #     return jsonify({"ok": False, "error": "FORBIDDEN"}), 403

    return jsonify({"ok": True, "patient": data})


# ─────────────────────────────────────────────────────────────────────────────
# SECURE GENERIC QUERY  — POST /api/firestore/query
#  - Whitelisted collections & fields
#  - Limited ops, filters, order, and page size
#  - Row-level security for patients/users/audit_logs
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED_QUERY = {
    "patients": {
        "fields": {"patient_id", "name", "age_sex", "owner_uid", "institute", "created_at"},
        "orderable": {"name", "created_at"},
        "ops": {"==", "in", ">=", "<=", "array_contains"},
        "types": {}
    },
    "users": {
        "fields": {"email", "uid", "name", "role", "approved", "active", "institute", "is_admin", "created_at"},
        "orderable": {"name", "created_at"},
        "ops": {"==", "in"},
        "types": {"approved": int, "active": int, "is_admin": int}
    },
    "audit_logs": {
        "fields": {"user_id", "action", "details", "timestamp"},
        "orderable": {"timestamp"},
        "ops": {"==", ">=", "<="},
        "types": {}
    },
}
SAFE_MAX_LIMIT = 50

@app.post("/api/firestore/query")
@csrf.exempt
def api_firestore_query():
    uid = get_uid_from_request()
    if not uid:
        return jsonify({"ok": False, "error": "UNAUTHORIZED"}), 401

    me = _profile_by_uid(uid)
    if not me:
        return jsonify({"ok": False, "error": "PROFILE_NOT_FOUND"}), 403

    data = request.get_json(silent=True) or {}
    collection = (data.get("collection") or "").strip()
    if collection not in ALLOWED_QUERY:
        return jsonify({"ok": False, "error": "COLLECTION_NOT_ALLOWED"}), 403

    spec = ALLOWED_QUERY[collection]
    allowed_fields = spec["fields"]
    allowed_ops = spec["ops"]
    orderable = spec["orderable"]
    casters = spec.get("types", {})

    filters = data.get("filters") or []
    if not isinstance(filters, list):
        return jsonify({"ok": False, "error": "BAD_FILTERS"}), 400

    order_by = data.get("order_by")
    order_dir = (data.get("order_dir") or "asc").lower()
    limit = int(data.get("limit") or 20)
    if limit > SAFE_MAX_LIMIT:
        limit = SAFE_MAX_LIMIT
    if order_by and order_by not in orderable:
        return jsonify({"ok": False, "error": "ORDER_BY_NOT_ALLOWED"}), 400
    if order_dir not in ("asc", "desc"):
        order_dir = "asc"

    # base query
    q = db.collection(collection)

    # Row-level security
    if collection == "patients":
        if _is_admin(me):
            # To restrict admins to their institute’s patients, ensure patients store "institute"
            # q = q.where("institute", "==", me.get("institute", ""))
            pass
        else:
            q = q.where("owner_uid", "==", uid)

    elif collection == "users":
        if not _is_admin(me):
            return jsonify({"ok": False, "error": "FORBIDDEN"}), 403
        q = q.where("institute", "==", me.get("institute", ""))

    elif collection == "audit_logs":
        if _is_admin(me):
            # If you store institute on logs, constrain here; else default to self to avoid full scans.
            # q = q.where("institute", "==", me.get("institute", ""))
            pass
        else:
            q = q.where("user_id", "==", uid)

    # Client filters (whitelisted)
    if len(filters) > 3:
        return jsonify({"ok": False, "error": "TOO_MANY_FILTERS"}), 400

    for f in filters:
        if not isinstance(f, dict):
            return jsonify({"ok": False, "error": "BAD_FILTER_ITEM"}), 400
        field = f.get("field")
        op = f.get("op")
        value = f.get("value")
        if field not in allowed_fields:
            return jsonify({"ok": False, "error": f"FIELD_NOT_ALLOWED:{field}"}), 400
        if op not in allowed_ops:
            return jsonify({"ok": False, "error": f"OP_NOT_ALLOWED:{op}"}), 400
        caster = casters.get(field)
        if caster is int:
            try:
                value = int(value)
            except Exception:
                return jsonify({"ok": False, "error": f"BAD_TYPE_FOR:{field}"}), 400
        q = q.where(field, op, value)

    # Sorting + limit
    if order_by:
        try:
            direction = firestore.Query.ASCENDING if order_dir == "asc" else firestore.Query.DESCENDING
            q = q.order_by(order_by, direction=direction)
        except Exception:
            # order_by not supported without index; fail safe
            return jsonify({"ok": False, "error": "ORDER_BY_UNAVAILABLE"}), 400

    q = q.limit(limit)

    try:
        docs = q.stream()
        items = []
        for d in docs:
            row = d.to_dict() or {}
            row["id"] = d.id
            items.append(row)
        return jsonify({"ok": True, "items": items})
    except Exception:
        return jsonify({"ok": False, "error": "QUERY_FAILED"}), 500
    

@app.post("/api/transcribe")
@csrf.exempt
def api_transcribe_audio():
    if "audio" not in request.files:
        return jsonify({"ok": False, "error": "NO_FILE"}), 400
    if openai is None or not getattr(openai, "api_key", ""):
        return jsonify({"ok": False, "error": "OPENAI_NOT_CONFIGURED"}), 500

    f = request.files["audio"]
    filename = secure_filename(f.filename or "audio.webm")
    tmp_path = os.path.join("/tmp", filename)
    f.save(tmp_path)

    try:
        with open(tmp_path, "rb") as audio_file:
            # Whisper v1
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        text = getattr(transcript, "text", None) or getattr(transcript, "get", lambda k: None)("text")
        return jsonify({"ok": True, "text": text or ""})
    except Exception as e:
        return jsonify({"ok": False, "error": "TRANSCRIBE_FAILED"}), 500
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/audit_logs — admin: institute-wide; non-admin: self
# ─────────────────────────────────────────────────────────────────────────────
# === SINGLE SOURCE OF TRUTH ===
@app.get("/api/audit_logs")
@csrf.exempt
def api_audit_logs():
    """
    Admins (role admin/institute_admin/super_admin): all logs for users in their institute.
    Non-admins: only their own logs.
    Response: { ok: true, items: [ {user_id, name?, action, details, timestamp} ], admin?: {...} }
    """
    uid = get_uid_from_request()
    if not uid:
        return jsonify({"ok": False, "error": "UNAUTHORIZED"}), 401

    me = _profile_by_uid(uid)  # uses your existing helper
    if not me:
        return jsonify({"ok": False, "error": "PROFILE_NOT_FOUND"}), 403

    def _is_admin(p):
        role = (p.get("role") or "").lower()
        return bool(p.get("is_super_admin")) or role in ("admin", "institute_admin", "super_admin") or bool(p.get("is_admin"))

    items = []

    if _is_admin(me):
        inst = me.get("institute") or me.get("institute_name") or ""
        # Map institute users -> (uid, name)
        profiles = []
        for u in db.collection("users").where("institute", "==", inst).stream():
            d = u.to_dict() or {}
            u_uid = d.get("uid") or u.id
            profiles.append((u_uid, d.get("name", "Unknown")))
        # Pull each user's logs, attach name
        for puid, pname in profiles:
            for e in db.collection("audit_logs").where("user_id", "==", puid).stream():
                row = e.to_dict() or {}
                row["name"] = pname
                items.append(row)
        return jsonify({"ok": True, "items": items, "admin": {"institute": inst, "count": len(items)}}), 200

    # Non-admin: only own logs
    for e in db.collection("audit_logs").where("user_id", "==", uid).stream():
        items.append(e.to_dict() or {})
    return jsonify({"ok": True, "items": items}), 200




# ─────────────────────────────────────────────────────────────────────────────
# USER MGMT — admin only, same-institute guard
# POST /api/users/approve {email}
# POST /api/users/reject {email}
# POST /api/users/deactivate {email}
# POST /api/users/reactivate {email}
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/users/approve")
@csrf.exempt
def api_users_approve():
    admin, err = _require_admin_from_token()
    if err: return err

    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    if not email:
        return jsonify({"ok": False, "error": "EMAIL_REQUIRED"}), 400

    doc = db.collection("users").document(email).get()
    if not doc.exists:
        return jsonify({"ok": False, "error": "USER_NOT_FOUND"}), 404

    target = doc.to_dict() or {}
    if (target.get("institute") or "") != (admin.get("institute") or ""):
        return jsonify({"ok": False, "error": "DIFFERENT_INSTITUTE"}), 403

    db.collection("users").document(email).update({
        "approved": 1,
        "updated_at": SERVER_TIMESTAMP
    })
    try:
        log_action(admin.get("uid"), "Approve User", email)
    except Exception:
        pass

    return jsonify({"ok": True})


@app.post("/api/users/reject")
@csrf.exempt
def api_users_reject():
    admin, err = _require_admin_from_token()
    if err: return err

    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    if not email:
        return jsonify({"ok": False, "error": "EMAIL_REQUIRED"}), 400

    doc = db.collection("users").document(email).get()
    if not doc.exists:
        return jsonify({"ok": False, "error": "USER_NOT_FOUND"}), 404

    target = doc.to_dict() or {}
    if (target.get("institute") or "") != (admin.get("institute") or ""):
        return jsonify({"ok": False, "error": "DIFFERENT_INSTITUTE"}), 403

    db.collection("users").document(email).delete()
    try:
        log_action(admin.get("uid"), "Reject User", email)
    except Exception:
        pass

    return jsonify({"ok": True})


@app.post("/api/users/deactivate")
@csrf.exempt
def api_users_deactivate():
    admin, err = _require_admin_from_token()
    if err: return err

    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    if not email:
        return jsonify({"ok": False, "error": "EMAIL_REQUIRED"}), 400

    doc = db.collection("users").document(email).get()
    if not doc.exists:
        return jsonify({"ok": False, "error": "USER_NOT_FOUND"}), 404

    target = doc.to_dict() or {}
    if (target.get("institute") or "") != (admin.get("institute") or ""):
        return jsonify({"ok": False, "error": "DIFFERENT_INSTITUTE"}), 403

    db.collection("users").document(email).update({
        "active": 0,
        "updated_at": SERVER_TIMESTAMP
    })
    try:
        log_action(admin.get("uid"), "Deactivate User", email)
    except Exception:
        pass

    return jsonify({"ok": True})


@app.post("/api/users/reactivate")
@csrf.exempt
def api_users_reactivate():
    admin, err = _require_admin_from_token()
    if err: return err

    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    if not email:
        return jsonify({"ok": False, "error": "EMAIL_REQUIRED"}), 400

    doc = db.collection("users").document(email).get()
    if not doc.exists:
        return jsonify({"ok": False, "error": "USER_NOT_FOUND"}), 404

    target = doc.to_dict() or {}
    if (target.get("institute") or "") != (admin.get("institute") or ""):
        return jsonify({"ok": False, "error": "DIFFERENT_INSTITUTE"}), 403

    db.collection("users").document(email).update({
        "active": 1,
        "updated_at": SERVER_TIMESTAMP
    })
    try:
        log_action(admin.get("uid"), "Reactivate User", email)
    except Exception:
        pass

    return jsonify({"ok": True})


def login_required(approved_only=True):
    def real_decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect('/login')
            if approved_only and session.get('is_admin') != 1 and session.get('approved') == 0:
                return "Access denied. Awaiting approval by admin."
            return f(*args, **kwargs)
        return decorated_function
    return real_decorator


def patient_access_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        patient_id = kwargs.get('patient_id')
        if not patient_id:
            return "Patient ID is required.", 400

        doc = db.collection('patients').document(patient_id).get()
        if not doc.exists:
            return "Patient not found.", 404

        patient = doc.to_dict()
        if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
            return "Access denied.", 403

        g.patient = patient
        return f(*args, **kwargs)
    return decorated_function

def _ensure_institute_admin_profile(*, email: str, uid: str, name: str, institute: str) -> dict:
    """
    Ensure the email-keyed user doc exists as an *approved, active* institute admin.
    Returns the profile dict.
    """
    doc_ref = db.collection("users").document(email)
    snap = doc_ref.get()
    base = snap.to_dict() or {}

    profile = {
        "email": email,
        "uid": uid,
        "name": name or base.get("name"),
        "role": "institute_admin",
        "is_admin": 1,
        "approved": 1,
        "active": 1,
        "institute": institute or base.get("institute", ""),
        "updated_at": firestore.SERVER_TIMESTAMP,
    }
    # keep created_at if present
    if not snap.exists:
        profile["created_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set({**base, **profile}, merge=True)
    return doc_ref.get().to_dict() or profile


def _ensure_institute_physio_profile_pending(
    *, email: str, uid: str, name: str, institute: str, institute_id: str | None = None
) -> dict:
    """
    Ensure the email-keyed user doc exists as a *pending* institute physio.
    Returns the profile dict.
    """
    doc_ref = db.collection("users").document(email)
    snap = doc_ref.get()
    base = snap.to_dict() or {}

    profile = {
        "email": email,
        "uid": uid,
        "name": name or base.get("name"),
        "role": "physio",
        "is_admin": 0,
        "approved": 0,    # PENDING
        "active": 1,
        "institute": institute or base.get("institute", ""),
        "institute_id": institute_id or base.get("institute_id", ""),
        "updated_at": firestore.SERVER_TIMESTAMP,
    }
    if not snap.exists:
        profile["created_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set({**base, **profile}, merge=True)
    return doc_ref.get().to_dict() or profile



@app.route('/')
def index():
    return render_template('index.html')

@app.post("/api/users/upsert")
@csrf.exempt
def api_upsert_profile():
    uid = get_uid_from_request()
    if not uid:
        return jsonify({"error": "unauthorized"}), 401
    email = request.json.get("email", "")
    partial = request.json.get("profile", {}) or {}
    upsert_user_profile(uid, email, partial)
    return jsonify({"status": "ok"})

@app.post("/api/patients")
@csrf.exempt
def api_create_patient():
    uid = get_uid_from_request()
    if not uid:
        return jsonify({"error": "unauthorized"}), 401

    profile = _profile_by_uid(uid)
    if not profile:
        return jsonify({"error": "profile_not_found"}), 401
        
    data = request.get_json() or {}
    
    # IMPORTANT: Use created_by instead of owner_uid to match Firebase rules
    patient_data = {
        'created_by': uid,  # Changed from owner_uid to created_by
        'owner_uid': uid,   # Keep this for backward compatibility
        'institute_id': profile.get('institute_id'),
        **data,
        'created_at': SERVER_TIMESTAMP,
        'updatedAt': SERVER_TIMESTAMP
    }
    
    doc_ref = db.collection('patients').document()
    doc_ref.set(patient_data)
    
    return jsonify({"id": doc_ref.id}), 201

@app.get("/api/patients/mine")  
@csrf.exempt
def api_list_my_patients():
    uid = get_uid_from_request()
    if not uid:
        return jsonify({"error": "unauthorized"}), 401

    # Get user profile and determine data scope
    profile = _profile_by_uid(uid)
    if not profile:
        return jsonify({"error": "profile_not_found"}), 401
        
    scope = get_user_data_scope(profile)
    
    try:
        query = db.collection('patients')
        
        if scope['role'] == 'institute_admin':
            # Admin sees all patients in their institute
            if scope['institute_id']:
                query = query.where('institute_id', '==', scope['institute_id'])
        else:
            # Both institute_physio and individual see only their own patients
            query = query.where('owner_uid', '==', uid)
        
        patients = []
        for doc in query.stream():
            patient_data = doc.to_dict() or {}
            patient_data['id'] = doc.id
            patients.append(patient_data)
        
        return jsonify(patients)
        
    except Exception as e:
        return jsonify({"error": "failed to list patients"}), 500
    

@app.patch("/api/patients/<patient_id>")
@csrf.exempt
def api_update_patient(patient_id):
    uid = get_uid_from_request()
    if not uid:
        return jsonify({"error": "unauthorized"}), 401
    update_patient(patient_id, request.json or {})
    return jsonify({"status": "ok"})

@app.delete("/api/patients/<patient_id>")
@csrf.exempt
def api_delete_patient(patient_id):
    uid = get_uid_from_request()
    if not uid:
        return jsonify({"error": "unauthorized"}), 401
    delete_patient(patient_id)
    return jsonify({"status": "ok"})

@app.post("/api/patients/<patient_id>/follow-ups")
@csrf.exempt
def api_create_followup(patient_id):
    uid = get_uid_from_request()
    if not uid:
        return jsonify({"error": "unauthorized"}), 401
    fid = create_follow_up(uid, patient_id, request.json or {})
    return jsonify({"id": fid}), 201

@app.get("/api/patients/<patient_id>/follow-ups")
@csrf.exempt
def api_list_followups(patient_id):
    uid = get_uid_from_request()
    if not uid:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify(list_followups_for_patient(patient_id))


@app.post("/api/institute/physio/login")
@csrf.exempt
def api_institute_physio_login():
    """
    JSON: { "email": "...", "password": "..." }
    Signs in with Firebase Auth; checks your Firestore email-keyed profile.
    Ensures user has 'physio' or 'institute_physio' role and is approved/active.
    """
    data = _json_or_form(request)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"ok": False, "error": "EMAIL_PASSWORD_REQUIRED"}), 400

    res = _firebase_signin(email, password)
    if "error" in res:
        return jsonify({"ok": False, "error": res["error"].get("message", "LOGIN_FAILED")}), 401

    uid = res.get("localId")
    id_token = res.get("idToken")
    if not uid or not id_token:
        return jsonify({"ok": False, "error": "NO_UID_OR_TOKEN"}), 500

    snap = db.collection("users").document(email).get()
    if not snap.exists:
        return jsonify({"ok": False, "error": "PROFILE_NOT_FOUND"}), 403
    profile = snap.to_dict() or {}

    def as_bool(v):
        if isinstance(v, str):
            return v.strip().lower() in ('1','true','yes','y','on')
        return bool(v)

    # Role check: ensure it's a physio role
    if profile.get("role") not in ("physio", "institute_physio"):
        return jsonify({"ok": False, "error": "ROLE_MISMATCH"}), 403
    
    # Approval and active status checks
    if not as_bool(profile.get("approved", 0)): # Physios need explicit approval
        return jsonify({"ok": False, "error": "NOT_APPROVED"}), 403
    if not as_bool(profile.get("active", 1)):
        return jsonify({"ok": False, "error": "DEACTIVATED"}), 403

    # Optional: set server session for web views (if applicable)
    session['user_email'] = email
    session['user_name']  = profile.get('name') or email.split('@')[0]
    session['user_id']    = uid
    session['role']       = profile.get('role') # 'physio' or 'institute_physio'
    session['is_super_admin'] = 0
    session['is_admin']   = 0 # Physios are not admins
    session['institute']  = profile.get('institute', '')
    session['institute_id'] = profile.get('institute_id', '')

    try:
        log_action(uid, 'login', f"institute_physio={email}")
    except Exception:
        pass

    return jsonify({"ok": True, "uid": uid, "profile": profile, "idToken": id_token}), 200


# --- UNIFIED LOGIN -----------------------------------------------------------
@app.post("/api/login")
@csrf.exempt
def api_login_unified():
    print(f"=== LOGIN DEBUG ===")
    print(f"Content-Type: {request.headers.get('Content-Type')}")
    print(f"Raw data: {request.get_data(as_text=True)}")
    print(f"Form data: {dict(request.form)}")
    print(f"JSON data: {request.get_json(silent=True)}")
    
    data = _json_or_form(request)
    print(f"Parsed data: {data}")
    print(f"=== END DEBUG ===")
    # --- robust body parsing: try JSON first, then form, then raw JSON ---
    data = request.get_json(silent=True)
    if not data:
        if request.form:
            data = request.form.to_dict(flat=True)
        else:
            raw = request.get_data(as_text=True)  # safe now (cache=True by default)
            try:
                data = json.loads(raw) if raw else {}
            except Exception:
                data = {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        raw_len = len(request.get_data(as_text=True) or "")
        return jsonify({
            "ok": False,
            "error": "EMAIL_PASSWORD_REQUIRED",
            "debug": {
                "content_type": request.headers.get("Content-Type"),
                "raw_len": raw_len,
                "parsed": bool(data),
            },
        }), 400

    # 1) Firebase sign-in
    res = _firebase_signin(email, password)
    if "error" in res:
        return jsonify({"ok": False, "error": res["error"].get("message", "LOGIN_FAILED")}), 401

    uid = res.get("localId")
    id_token = res.get("idToken")
    if not uid or not id_token:
        return jsonify({"ok": False, "error": "NO_UID_OR_TOKEN"}), 500

    # 2) Load the user's profile (email-keyed doc)
    doc = db.collection("users").document(email).get()
    if not doc.exists:
        return jsonify({"ok": False, "error": "PROFILE_NOT_FOUND"}), 403

    profile = doc.to_dict() or {}

    def normalize_role(input_role):
        s = str(input_role or '').strip().lower()

        if s in ('institute_admin', 'admin'):
            return 'institute_admin'
        elif s in ('institute_physio', 'physio'):
            return 'institute_physio'
        else:
            return 'individual'

    raw_role = profile.get("role", "")
    print(f"[DEBUG] Raw role from Firestore: '{raw_role}'")
    role = normalize_role(raw_role)
    print(f"[DEBUG] Normalized role: '{role}'")

    # Convert boolean fields safely
    def as_int_bool(value):
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, str):
            return 1 if value.lower() in ('1', 'true', 'yes', 'active') else 0
        return int(value) if value is not None else 0

    approved = as_int_bool(profile.get("approved", 1))
    active = as_int_bool(profile.get("active", 1))
    
    print(f"[DEBUG] Final check values: role={role}, approved={approved}, active={active}")

    # 3) Role-based gates - FIXED INDENTATION
    if role == "individual":
        if active != 1:
            return jsonify({"ok": False, "error": "DEACTIVATED"}), 403
    elif role == "institute_admin":
        if active != 1:
            return jsonify({"ok": False, "error": "DEACTIVATED"}), 403
    elif role == "institute_physio":
        if approved != 1:
            print(f"[DEBUG] institute_physio not approved: {approved}")
            return jsonify({"ok": False, "error": "NOT_APPROVED"}), 403
        if active != 1:
            print(f"[DEBUG] institute_physio not active: {active}")
            return jsonify({"ok": False, "error": "DEACTIVATED"}), 403
    elif role in ("admin", "super_admin"):
        if active != 1:
            return jsonify({"ok": False, "error": "DEACTIVATED"}), 403
    else:
        print(f"[DEBUG] Unknown role encountered: '{role}'")
        return jsonify({"ok": False, "error": "UNKNOWN_ROLE"}), 403

    print(f"[DEBUG] All role checks passed for: {role}")

# 4) Light server session (useful for web views)
    session['user_email'] = email
    session['user_name']  = profile.get('name') or email.split('@')[0]
    session['user_id']    = uid
    session['role']       = role
    session['is_super_admin'] = 1 if role == 'super_admin' else 0
    # ✅ treat all admin variants as admin for server-side checks
    session['is_admin']       = 1 if role in ('institute_admin', 'admin', 'super_admin') else 0
    session['institute']      = profile.get('institute', '')
    session['institute_id']   = profile.get('institute_id', '')

    try:
        log_action(uid, 'login', f"{role}={email}")
    except Exception:
        pass

    return jsonify({"ok": True, "uid": uid, "idToken": id_token, "profile": profile}), 200



@app.post("/api/individual/login")
@csrf.exempt
def api_individual_login():
    """
    JSON: { "email": "...", "password": "..." }
    Signs in with Firebase Auth; checks your Firestore email‑keyed profile.
    """
    data = _json_or_form(request)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"ok": False, "error": "EMAIL_PASSWORD_REQUIRED"}), 400

    res = _firebase_signin(email, password)
    if "error" in res:
        return jsonify({"ok": False, "error": res["error"].get("message", "LOGIN_FAILED")}), 401

    uid = res.get("localId")
    id_token = res.get("idToken")
    if not uid or not id_token:
        return jsonify({"ok": False, "error": "NO_UID_OR_TOKEN"}), 500

    # Ensure profile (in case user was created outside your app)
    _ensure_individual_profile(email=email, uid=uid)
    snap = db.collection('users').document(email).get()
    if not snap.exists:
        return jsonify({"ok": False, "error": "PROFILE_NOT_FOUND"}), 403
    profile = snap.to_dict() or {}

    def as_bool(v):
        if isinstance(v, str):
            return v.strip().lower() in ('1','true','yes','y','on')
        return bool(v)

    if not as_bool(profile.get('approved', 1)):
        return jsonify({"ok": False, "error": "NOT_APPROVED"}), 403
    if not as_bool(profile.get('active', 1)):
        return jsonify({"ok": False, "error": "DEACTIVATED"}), 403
    if (profile.get('role') or 'individual') != 'individual':
        return jsonify({"ok": False, "error": "ROLE_MISMATCH"}), 403

    # Optional server session (used by your web templates)
    session['user_email'] = email
    session['user_name']  = profile.get('name') or email.split('@')[0]
    session['user_id']    = uid
    session['role']       = 'individual'
    session['is_super_admin'] = 0
    session['is_admin']       = 0
    session['institute']      = profile.get('institute','')
    session['institute_id']   = profile.get('institute_id','')

    try:
        log_action(uid, 'login', f"user={email}")
    except Exception:
        pass

    return jsonify({"ok": True, "uid": uid, "profile": profile, "idToken": id_token}), 200


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        # Show approved institutes for institute_physio option
        institutes = [
            {**d.to_dict(), 'id': d.id}
            for d in db.collection('institutes').where('status', '==', 'approved').stream()
        ]
        return render_template('register.html', institutes=institutes)

    # POST: process registration
    form = request.form
    role = (form.get('role') or '').strip()
    
    # Use the exact role values from your HTML form
    if role not in ['individual', 'institute_admin', 'institute_physio']:
        flash('Invalid role selection.', 'danger')
        return redirect(url_for('register'))

    payload = {
        'name': (form.get('name') or '').strip(),
        'age': (form.get('age') or '').strip(),
        'sex': (form.get('sex') or '').strip(),
        'area_of_practice': (form.get('area_of_practice') or '').strip(),
        'credentials': (form.get('credentials') or '').strip(),
        'email': (form.get('email') or '').strip().lower(),
        'phone': (form.get('phone') or '').strip(),
        'role': role,  # Store exact role from form
        'status': 'pending',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }

    # Role-specific validation
    if role == 'institute_admin':
        payload['institute_name'] = (form.get('institute_name') or '').strip()
        if not payload['institute_name']:
            flash('Institute name is required for Institute Admin.', 'danger')
            return redirect(url_for('register'))

    if role == 'institute_physio':
        payload['institute_id'] = (form.get('institute_id') or '').strip()
        if not payload['institute_id']:
            flash('Please select an institute to join.', 'danger')
            return redirect(url_for('register'))

    # Save registration request
    db.collection('registration_requests').add(payload)
    flash('Registration request submitted. You will be contacted after approval.', 'success')
    return redirect(url_for('login'))



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    # --- POST: authenticate with Firebase Auth (REST) ---
    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password') or ''

    if not email or not password:
        flash('Please enter email and password.', 'danger')
        return redirect(url_for('login'))

    try:
        # 1) Firebase Auth sign-in
        payload = {'email': email, 'password': password, 'returnSecureToken': True}
        r = requests.post(
            f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}',
            json=payload, timeout=15
        )
        result = r.json()
        if 'error' in result:
            msg = result['error'].get('message', 'Authentication failed')
            flash(f'Login failed: {msg}', 'danger')
            return redirect(url_for('login'))

        uid = result.get('localId')  # Firebase UID

        # 2) Load Firestore profile (email-keyed in your DB)
        snap = db.collection('users').document(email).get()
        if not snap.exists:
            flash('User not found in Firestore profile. Contact support.', 'danger')
            return redirect(url_for('login'))
        profile = snap.to_dict() or {}

        # helper: 1/0, true/false, etc.
        def as_bool(v):
            if isinstance(v, str):
                return v.strip().lower() in ('1','true','yes','y','on')
            return bool(v)

        # 3) Approval and active gates
        if not as_bool(profile.get('approved', 0)):
            flash('Your account is not approved yet. Please wait for approval.', 'danger')
            return redirect(url_for('login'))
        if not as_bool(profile.get('active', 1)):
            flash('Your account is deactivated. Contact support.', 'danger')
            return redirect(url_for('login'))

        # 4) Success → set session
        role = (profile.get('role') or 'individual').strip().lower()
        session['user_email'] = email
        session['user_name']  = profile.get('name') or result.get('displayName') or email.split('@')[0]
        session['user_id']    = uid
        session['role']       = role

        # Admin status STRICTLY by role (ignore stored is_admin)
        session['is_super_admin'] = 1 if (role == 'super_admin' or as_bool(profile.get('is_super_admin', 0))) else 0
        session['is_admin']       = 1 if role in ('admin', 'institute_admin') else 0

        # Optional institute info for your admin template
        session['institute']    = profile.get('institute_name') or profile.get('institute') or ''
        session['institute_id'] = profile.get('institute_id') or ''

        # Optional audit
        try:
            log_action(session['user_id'], 'login', f"user={email}")
        except Exception:
            pass

        # Early redirects by role
        if session['is_super_admin'] == 1:
            return redirect(url_for('superadmin_home'))
        if session['is_admin'] == 1:
            return redirect(url_for('admin_dashboard'))

        # Fallback
        return redirect(url_for('dashboard'))

    except Exception as e:
        app.logger.error("Login exception: %s", e, exc_info=True)
        flash('Something went wrong while logging in. Please try again.', 'danger')
        return redirect(url_for('login'))




@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/superadmin')
@role_required('super_admin')
def superadmin_home():
    pending = [{**d.to_dict(), 'id': d.id} for d in db.collection('registration_requests').where('status', '==', 'pending').stream()]
    users = [{**d.to_dict(), 'id': d.id} for d in db.collection('users').stream()]
    # Optional: recent activity logs if you already have audit_logs collection
    logs = [{**d.to_dict(), 'id': d.id} for d in db.collection('audit_logs').order_by('timestamp', direction=_fa_fs.Query.DESCENDING).limit(50).stream()]
    return render_template('superadmin.html', pending=pending, users=users, logs=logs)

@app.post('/superadmin/approve/<req_id>')
@role_required('super_admin')
def superadmin_approve(req_id):
    req_ref = db.collection('registration_requests').document(req_id)
    snap = req_ref.get()
    if not snap.exists:
        flash('Request not found', 'error')
        return redirect(url_for('superadmin_home'))
    
    r = snap.to_dict()
    email = (r.get('email') or '').lower()
    if not email:
        flash('Request missing email', 'error')
        return redirect(url_for('superadmin_home'))

    # Create Firebase Auth user
    try:
        user_rec = fb_auth.get_user_by_email(email)
    except Exception:
        tmp_pwd = secrets.token_urlsafe(12)
        user_rec = fb_auth.create_user(
            email=email,
            display_name=r.get('name', ''),
            password=tmp_pwd,
            disabled=False
        )
    uid = user_rec.uid

    # Handle institute creation/assignment
    institute_id = None
    if r.get('role') == 'institute_admin':
        # Create new institute
        inst = {
            'name': r.get('institute_name'),
            'admin_uid': uid,
            'admin_email': email,
            'status': 'approved',
            'created_at': now_ts().isoformat(),
            'updated_at': now_ts().isoformat(),
        }
        _, institute_ref = db.collection('institutes').add(inst)
        institute_id = institute_ref.id
    elif r.get('role') == 'institute_physio':
        institute_id = r.get('institute_id')

    # Create standardized user profile
    user_doc = {
        'uid': uid,
        'email': email,
        'name': r.get('name'),
        'phone': r.get('phone'),
        'role': r.get('role'),  # Already standardized from registration
        'approved': 1,
        'active': 1,
        'is_admin': 1 if r.get('role') == 'institute_admin' else 0,
        'area_of_practice': r.get('area_of_practice'),
        'credentials': r.get('credentials'),
        'sex': r.get('sex'),
        'age': r.get('age'),
        'institute_id': institute_id,
        'institute': r.get('institute_name') if r.get('role') == 'institute_admin' else None,
        'updated_at': now_ts().isoformat(),
        'created_at': now_ts().isoformat(),
    }
    
    db.collection('users').document(email).set(user_doc)

    # Close the request
    req_ref.update({'status': 'approved', 'approved_at': now_ts().isoformat()})

    flash('User approved. They can log in now (use Forgot Password to set password).', 'success')
    return redirect(url_for('superadmin_home'))

@app.post('/superadmin/reject/<req_id>')
@role_required('super_admin')
def superadmin_reject(req_id):
    req_ref = db.collection('registration_requests').document(req_id)
    if not req_ref.get().exists:
        flash('Request not found', 'error'); return redirect(url_for('superadmin_home'))
    req_ref.update({'status': 'rejected', 'rejected_at': now_ts().isoformat()})
    flash('Request rejected.', 'info')
    return redirect(url_for('superadmin_home'))

@app.post('/superadmin/delete_user/<uid>')
@role_required('super_admin')
def superadmin_delete_user(uid):
    # uid is Firebase UID; try to delete from Auth and profile (email-keyed)
    try:
        fb_auth.delete_user(uid)
    except Exception:
        pass

    # delete by email-key if present
    q = db.collection('users').where('uid', '==', uid).limit(1).get()
    if q:
        db.collection('users').document(q[0].id).delete()

    flash('User deleted.', 'info')
    return redirect(url_for('superadmin_home'))


@app.route('/dashboard')
@login_required()
def dashboard():
    if session.get('is_super_admin') == 1:
        return redirect(url_for('superadmin_home'))
    return render_template('dashboard.html', name=session.get('user_name'))


@app.route('/admin_dashboard')
@login_required()
def admin_dashboard():
    # only institute‑admins allowed
    if session.get('is_admin') != 1:
        return redirect(url_for('login_institute'))

    # build a query for non‑admin physios in this institute, pending approval
    users_ref = db.collection('users')
    docs = (
        users_ref
        .where(filter=FieldFilter('is_admin',   '==', 0))
        .where(filter=FieldFilter('approved',   '==', 0))
        .where(filter=FieldFilter('institute',  '==', session.get('institute')))
        .stream()
    )

    # pull the documents into a list of dicts
    pending_physios = [doc.to_dict() for doc in docs]

    # render
    return render_template(
        'admin_dashboard.html',
        pending_physios=pending_physios,
        name=session.get('user_name'),
        institute=session.get('institute')
    )


 
@app.route('/view_patients')
@login_required()
def view_patients():
    # optional filters
    name_f = (request.args.get('name') or '').strip().lower()
    id_f   = (request.args.get('patient_id') or '').strip()

    try:
        uid = session.get('user_id')  # Firebase UID saved at login
        if not uid:
            flash("Session expired. Please log in again.", "error")
            return redirect(url_for('login'))

        # 1) Fetch only this physio's patients from Firestore
        docs = (
            db.collection('patients')
              .where('physio_id', '==', uid)
              .stream()
        )

        patients = []
        for d in docs:
            p = d.to_dict() or {}
            p.setdefault('patient_id', d.id)  # template expects this
            patients.append(p)

        # 2) Apply optional filters in Python (safer/portable)
        if name_f:
            def name_matches(p):
                candidates = [
                    str(p.get('name', '')),
                    str(p.get('subjectiveExamination', {}).get('contextualFactorsPersonal', '')),
                    str(p.get('contextualFactorsPersonal', '')),
                ]
                return any(c.lower().startswith(name_f) for c in candidates if c)
            patients = [p for p in patients if name_matches(p)]

        if id_f:
            patients = [p for p in patients if p.get('patient_id') == id_f or str(p.get('id', '')) == id_f]

        # 3) Normalize created_at for templates (no hasattr in Jinja)
        #    - adds p['created_at_str'] as 'DD-MM-YYYY'
        #    - also adds a temp timestamp for sorting (then removes it)
        from datetime import datetime

        for p in patients:
            ts = p.get('created_at')
            dt = None
            if ts is not None:
                if hasattr(ts, 'strftime'):  # Firestore/Python datetime
                    dt = ts
                elif isinstance(ts, str):
                    try:
                        dt = datetime.fromisoformat(ts)
                    except Exception:
                        dt = None
            p['created_at_str'] = dt.strftime('%d-%m-%Y') if dt else ''
            p['_sort_ts'] = (dt.timestamp() if dt else 0.0)

        # Optional: show most recent first
        patients.sort(key=lambda x: x.get('_sort_ts', 0.0), reverse=True)
        for p in patients:
            p.pop('_sort_ts', None)

    except Exception as e:
        logger.error("Firestore error in view_patients: %s", e, exc_info=True)
        flash("Could not load your patients list. Please try again later.", "error")
        return redirect(url_for('dashboard'))

    return render_template('view_patients.html', patients=patients)



# ------------------------------
#   INSTITUTE: ADMIN AUTH (API)
# ------------------------------




@app.post("/api/institute/admin/login")
@csrf.exempt
def api_institute_admin_login():
    """
    JSON: { "email": "...", "password": "..." }
    """
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    password = d.get("password") or ""

    if not (email and password):
        return jsonify({"ok": False, "error": "EMAIL_PASSWORD_REQUIRED"}), 400

    res = _firebase_signin(email, password)
    if "error" in res:
        return jsonify({"ok": False, "error": res["error"].get("message", "LOGIN_FAILED")}), 401

    uid = res.get("localId")
    id_token = res.get("idToken")
    if not uid or not id_token:
        return jsonify({"ok": False, "error": "NO_UID_OR_TOKEN"}), 500

    snap = db.collection("users").document(email).get()
    if not snap.exists:
        return jsonify({"ok": False, "error": "PROFILE_NOT_FOUND"}), 403
    profile = snap.to_dict() or {}

    # gates
    if profile.get("role") not in ("admin", "institute_admin"):
        return jsonify({"ok": False, "error": "ROLE_MISMATCH"}), 403
    if int(profile.get("approved", 0)) != 1:
        return jsonify({"ok": False, "error": "NOT_APPROVED"}), 403
    if int(profile.get("is_admin", 0)) != 1:
        return jsonify({"ok": False, "error": "NOT_ADMIN"}), 403

    # set your existing session layout (so your templates keep working)
    session['user_email'] = email
    session['user_name']  = profile.get('name') or email.split('@')[0]
    session['user_id']    = uid
    session['role']       = 'institute_admin'
    session['is_super_admin'] = 0
    session['is_admin']   = 1
    session['institute']  = profile.get('institute', '')
    session['institute_id'] = profile.get('institute_id', '')

    try: log_action(uid, 'login', f"institute_admin={email}")
    except Exception: pass

    return jsonify({"ok": True, "uid": uid, "profile": profile, "idToken": id_token}), 200


# -------------------------------------
#   INSTITUTE: PHYSIO REG + APPROVAL
# -------------------------------------




@app.get("/api/institute/physios/pending")
@csrf.exempt
@login_required()
def api_institute_pending_physios():
    """Admin-only: list unapproved physios in admin's institute."""
    if session.get('is_admin') != 1:
        return jsonify({"ok": False, "error": "FORBIDDEN"}), 403
    inst = session.get('institute') or ''
    docs = (db.collection('users')
              .where('role', '==', 'institute_physio')
              .where('approved', '==', 0)
              .where('institute', '==', inst)
              .stream())
    items = [d.to_dict() for d in docs]
    return jsonify({"ok": True, "items": items})


@app.post("/api/institute/physio/approve")
@csrf.exempt
@login_required()
def api_institute_approve_physio():
    """Admin-only: body { email: '...' } → set approved=1."""
    if session.get('is_admin') != 1:
        return jsonify({"ok": False, "error": "FORBIDDEN"}), 403
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    if not email:
        return jsonify({"ok": False, "error": "EMAIL_REQUIRED"}), 400

    # ensure in same institute
    target = db.collection('users').document(email).get()
    if not target.exists:
        return jsonify({"ok": False, "error": "USER_NOT_FOUND"}), 404
    t = target.to_dict() or {}
    if t.get('institute') != session.get('institute'):
        return jsonify({"ok": False, "error": "DIFFERENT_INSTITUTE"}), 403

    db.collection('users').document(email).update({
        'approved': 1,
        'updated_at': SERVER_TIMESTAMP
    })
    try: log_action(session['user_id'], 'Approve Physio', f"{email}")
    except Exception: pass

    return jsonify({"ok": True})




@app.route('/login_institute', methods=['GET', 'POST'])
def login_institute():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        try:
            # Firebase Auth login
            payload = {
                'email': email,
                'password': password,
                'returnSecureToken': True
            }
            r = requests.post(
                f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}',
                json=payload
            )
            result = r.json()

            if 'error' in result:
                flash('Invalid credentials', 'danger')
                return redirect('/login_institute')

            # Firestore check
            user_doc = db.collection('users').document(email).get()
            if not user_doc.exists:
                flash('User not found in Firestore.', 'danger')
                return redirect('/login_institute')

            user_data = user_doc.to_dict()

            if user_data.get('approved') == 1 and user_data.get('active') == 1:
                session['user_email'] = email
                session['user_name'] = user_data.get('name')
                session['user_id'] = result['localId'] # Use Firebase UID
                session['role'] = user_data.get('role')
                session['is_admin'] = user_data.get('is_admin', 0)
                session['institute'] = user_data.get('institute')

                if user_data.get('is_admin') == 1:
                    return redirect('/admin_dashboard')
                else:
                    return redirect('/dashboard')
            else:
                flash('Your account is not approved or is inactive.', 'danger')
                return redirect('/login_institute')

        except Exception as e:
            print("Login institute error:", e)
            flash("Login failed due to a system error.", "danger")
            return redirect('/login_institute')

    return render_template('login_institute.html')




    

@app.route('/approve_physios', methods=['GET', 'POST'])
@login_required()
def approve_physios():
    current_user_email = session.get('user_email')
    current_user_doc = db.collection('users').document(current_user_email).get()

    if not current_user_doc.exists:
        flash('Current user not found.', 'danger')
        return redirect('/admin_dashboard')

    current_user_data = current_user_doc.to_dict()
    institute_name = current_user_data.get('institute')

    # Fetch all physios from the same institute who are not approved
    pending = db.collection('users') \
        .where('role', '==', 'institute_physio') \
        .where('approved', '==', 0) \
        .where('institute', '==', institute_name) \
        .stream()

    pending_physios = [doc.to_dict() for doc in pending]

    return render_template('approve_physios.html', physios=pending_physios)



@app.route('/approve_user/<user_email>', methods=['POST'])
@login_required()
def approve_user(user_email):
    user_email = user_email.lower()
    try:
        db.collection('users').document(user_email).update({
            'approved': 1
        })
        flash('User approved successfully.', 'success')
    except Exception as e:
        print("Approval error:", e)
        flash('Error approving user.', 'danger')
    return redirect('/approve_physios')


@app.route('/reject_user/<user_email>', methods=['POST'])
@login_required()
def reject_user(user_email):
    user_email = user_email.lower()
    try:
        db.collection('users').document(user_email).delete()
        flash('User rejected and deleted successfully.', 'info')
    except Exception as e:
        print("Rejection error:", e)
        flash('Error rejecting user.', 'danger')
    return redirect('/approve_physios')




@app.route('/audit_logs')
@login_required()
def audit_logs():
    logs = []
    if session.get('is_admin') == 1:
        users = db.collection('users').where('institute', '==', session['institute']).stream()
        profiles = []
    for u in users:
        d = u.to_dict() or {}
        uid = d.get('uid') or u.id  # fallback to doc id if older docs
        profiles.append({'uid': uid, 'name': d.get('name', 'Unknown')})

    for p in profiles:
        entries = db.collection('audit_logs').where('user_id', '==', p['uid']).stream()
        for e in entries:
            data = e.to_dict()
            data['name'] = p['name']
            logs.append(data)


    # Sort by timestamp descending
    logs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

    return render_template('audit_logs.html', logs=logs)

@app.route('/export_audit_logs')
@login_required()
def export_audit_logs():
    if session.get('is_admin') != 1:
        return redirect('/login_institute')

    users = db.collection('users').where('institute', '==', session['institute']).stream()
    profiles = []
    for u in users:
        d = u.to_dict() or {}
        uid = d.get('uid') or u.id
        profiles.append({'uid': uid, 'name': d.get('name', 'Unknown')})

    logs = []
    for p in profiles:
        entries = db.collection('audit_logs').where('user_id', '==', p['uid']).stream()
        for e in entries:
            log = e.to_dict()
            logs.append([
                p['name'],
                log.get('action', ''),
                log.get('details', ''),
                log.get('timestamp', '')
            ])

    # Prepare CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['User', 'Action', 'Details', 'Timestamp'])
    writer.writerows(logs)

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=audit_logs.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


@app.route('/add_patient', methods=['GET', 'POST'])
@login_required()
def add_patient():
    if request.method == 'POST':
        # 1) collect form values
        data = {
            'physio_id':       session.get('user_id'),
            'name':            request.form['name'],
            'age_sex':         request.form['age_sex'],
            'contact':         request.form['contact'],
            'present_history': request.form['present_history'],
            'past_history':    request.form.get('past_history', '').strip(),
            'institute':       session.get('institute'),
            'created_at':      SERVER_TIMESTAMP
        }

        # 2) Create a new patient document with an auto-generated ID
        new_patient_ref = db.collection('patients').document()
        pid = new_patient_ref.id
        data['patient_id'] = pid

        # 3) Set the data for the new patient
        new_patient_ref.set(data)

        log_action(session.get('user_id'),
                   'Add Patient',
                   f"Added {data['name']} (ID: {pid})")

        # 4) redirect to the next screen
        return redirect(url_for('subjective', patient_id=pid))

    # GET → render the blank form
    return render_template('add_patient.html')





@app.route('/subjective/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def subjective(patient_id):
    patient = g.patient
    if request.method == 'POST':
        fields = [
            'body_structure', 'body_function', 'activity_performance',
            'activity_capacity', 'contextual_environmental',
            'contextual_personal'
        ]
        entry = {f: request.form[f] for f in fields}
        entry['patient_id'] = patient_id
        entry['timestamp'] = SERVER_TIMESTAMP
        db.collection('subjective_examination').add(entry)
        return redirect(f'/perspectives/{patient_id}')
    return render_template('subjective.html', patient_id=patient_id, patient=patient)



@app.route('/perspectives/<path:patient_id>', methods=['GET','POST'])
@login_required()
@patient_access_required
def perspectives(patient_id):
    if request.method == 'POST':
        # ← UPDATED TO MATCH YOUR HTML FIELD NAMES
        keys = [
            'knowledge',
            'attribution',
            'expectation',               # was 'illness_duration'
            'consequences_awareness',
            'locus_of_control',
            'affective_aspect'
        ]

        # collect form values safely
        entry = {
            k: request.form.get(k, '')  # use .get() to avoid KeyError
            for k in keys
        }
        entry.update({
            'patient_id': patient_id,
            'timestamp': SERVER_TIMESTAMP
        })

        # save to your collection
        db.collection('patient_perspectives').add(entry)

        # redirect to the next screen
        return redirect(url_for('initial_plan', patient_id=patient_id))

    # GET: render the form
    return render_template('perspectives.html', patient_id=patient_id)


@app.route('/initial_plan/<path:patient_id>', methods=['GET','POST'])
@login_required()
@patient_access_required
def initial_plan(patient_id):
    if request.method == 'POST':
        sections = ['active_movements','passive_movements','passive_over_pressure',
                    'resisted_movements','combined_movements','special_tests','neuro_dynamic_examination']
        entry = {'patient_id': patient_id, 'timestamp': SERVER_TIMESTAMP}
        for s in sections:
            entry[s] = request.form.get(s)
            entry[f"{s}_details"] = request.form.get(f"{s}_details", '')
        db.collection('initial_plan').add(entry)
        return redirect(f'/patho_mechanism/{patient_id}')
    return render_template('initial_plan.html', patient_id=patient_id)



@app.route('/patho_mechanism/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def patho_mechanism(patient_id):
    if request.method == 'POST':
        keys = [
            'area_involved', 'presenting_symptom', 'pain_type', 'pain_nature',
            'pain_severity', 'pain_irritability', 'possible_source',
            'stage_healing'
        ]
        entry = {k: request.form[k] for k in keys}
        entry['patient_id'] = patient_id
        entry['timestamp'] = SERVER_TIMESTAMP
        db.collection('patho_mechanism').add(entry)
        return redirect(f'/chronic_disease/{patient_id}')
    return render_template('patho_mechanism.html', patient_id=patient_id)


@app.route('/chronic_disease/<path:patient_id>', methods=['GET','POST'])
@login_required()
@patient_access_required
def chronic_disease(patient_id):
    if request.method == 'POST':
        # Pull back *all* selected options as a Python list:
        causes = request.form.getlist('maintenance_causes')
        entry = {
            'patient_id': patient_id,
            'causes': causes,                            # <- store the list
            'specific_factors': request.form.get('specific_factors', ''),
            'timestamp': SERVER_TIMESTAMP
        }
        db.collection('chronic_diseases').add(entry)
        return redirect(f'/clinical_flags/{patient_id}')
    return render_template('chronic_disease.html', patient_id=patient_id)


@app.route('/clinical_flags/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def clinical_flags(patient_id):
    if request.method == 'POST':
        entry = {
            'patient_id': patient_id,
            'red_flags':     request.form.get('red_flags', ''),
            'yellow_flags':  request.form.get('yellow_flags', ''),
            'black_flags':   request.form.get('black_flags', ''),
            'blue_flags':    request.form.get('blue_flags', ''),
            'timestamp':     SERVER_TIMESTAMP
        }
        db.collection('clinical_flags').add(entry) 
        return redirect(url_for('objective_assessment', patient_id=patient_id))


    return render_template('clinical_flags.html', patient_id=patient_id)


@app.route('/objective_assessment/<path:patient_id>', methods=['GET','POST'])
@csrf.exempt
@login_required()
@patient_access_required
def objective_assessment(patient_id):
    if request.method == 'POST':
        entry = {
            'patient_id': patient_id,
            'plan':          request.form['plan'],
            'plan_details':  request.form.get('plan_details',''),
            'timestamp':     SERVER_TIMESTAMP
        }
        db.collection('objective_assessments').add(entry)
        return redirect(f'/provisional_diagnosis/{patient_id}')

    return render_template('objective_assessment.html', patient_id=patient_id)



@app.route('/provisional_diagnosis/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def provisional_diagnosis(patient_id):
    if request.method == 'POST':
        keys = [
            'likelihood', 'structure_fault', 'symptom', 'findings_support',
            'findings_reject', 'hypothesis_supported'
        ]
        entry = {k: request.form[k] for k in keys}
        entry['patient_id'] = patient_id
        entry['timestamp'] = SERVER_TIMESTAMP
        db.collection('provisional_diagnosis').add(entry)
        return redirect(f'/smart_goals/{patient_id}')
    return render_template('provisional_diagnosis.html', patient_id=patient_id)


@app.route('/smart_goals/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def smart_goals(patient_id):
    if request.method == 'POST':
        keys = [
            'patient_goal', 'baseline_status', 'measurable_outcome',
            'time_duration'
        ]
        entry = {k: request.form[k] for k in keys}
        entry['patient_id'] = patient_id
        entry['timestamp'] = SERVER_TIMESTAMP
        db.collection('smart_goals').add(entry)
        return redirect(f'/treatment_plan/{patient_id}')
    return render_template('smart_goals.html', patient_id=patient_id)


@app.route('/treatment_plan/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def treatment_plan(patient_id):
    if request.method == 'POST':
        keys = ['treatment_plan', 'goal_targeted', 'reasoning', 'reference']
        entry = {k: request.form[k] for k in keys}
        entry['patient_id'] = patient_id
        entry['timestamp'] = SERVER_TIMESTAMP
        db.collection('treatment_plan').add(entry)
        return redirect('/dashboard')
    return render_template('treatment_plan.html', patient_id=patient_id)

from datetime import datetime, timezone
from google.cloud import firestore  # for Query.ASCENDING

@app.route('/follow_ups/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def follow_ups(patient_id):
    patient = g.patient  # set by @patient_access_required

    try:
        if request.method == 'POST':
            # --- 1) Normalize and validate form fields ---
            # session_number: must be int and >= 1
            try:
                session_number = int(request.form.get('session_number', '').strip())
                if session_number < 1:
                    raise ValueError
            except Exception:
                flash('Invalid session number.', 'error')
                return redirect(f'/follow_ups/{patient_id}')

            # session_date: parse ISO yyyy-mm-dd to timezone-aware datetime
            date_str = (request.form.get('session_date') or '').strip()
            try:
                # html <input type="date"> gives 'YYYY-MM-DD'
                session_date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            except Exception:
                flash('Invalid session date.', 'error')
                return redirect(f'/follow_ups/{patient_id}')

            grade            = (request.form.get('grade') or '').strip()
            belief_treatment = (request.form.get('belief_treatment') or '').strip()
            belief_feedback  = (request.form.get('belief_feedback') or '').strip()
            treatment_plan   = (request.form.get('treatment_plan') or '').strip()

            # --- 2) Build the document to write (consistent types) ---
            entry = {
                'patient_id'    : patient_id,            # Firestore doc ID of patient
                'owner_uid'     : session.get('user_id'),# helpful for scoping later
                'session_number': session_number,        # INT (not string!)
                'session_date'  : session_date,          # DATETIME (not string!)
                'grade'         : grade,
                'perception'    : belief_treatment,      # keep both keys if you use them elsewhere
                'feedback'      : belief_feedback,
                'belief_treatment': belief_treatment,    # preserve original field names used in JS
                'belief_feedback' : belief_feedback,
                'treatment_plan': treatment_plan,
                'timestamp'     : SERVER_TIMESTAMP,      # server write time
            }

            db.collection('follow_ups').add(entry)
            log_action(
                session['user_id'],
                'Add Follow-Up',
                f"Follow-up #{session_number} for {patient_id}"
            )
            return redirect(f'/follow_ups/{patient_id}')

        # --- 3) On GET, read all existing follow-ups (uniform types so order_by works) ---
        docs = (
            db.collection('follow_ups')
              .where('patient_id', '==', patient_id)
              .order_by('session_number', direction=firestore.Query.ASCENDING)
              .stream()
        )
        followups = [d.to_dict() for d in docs]

        return render_template(
            'follow_ups.html',
            patient=patient,
            patient_id=patient_id,
            followups=followups
        )

    except Exception as e:
        app.logger.exception('Error in follow_ups route')
        # Avoid leaking details to users, but make it obvious in logs
        return make_response('Internal Server Error in follow_ups', 500)


# ─── VIEW FOLLOW-UPS ROUTE ─────────────────────────────────────────────
@app.route('/view_follow_ups/<path:patient_id>')
@login_required()
@patient_access_required
def view_follow_ups(patient_id):
    patient = g.patient
    docs = (db.collection('follow_ups')
              .where('patient_id', '==', patient_id)
              .order_by('session_date', direction=_fa_fs.Query.DESCENDING)
              .stream())
    followups = [d.to_dict() for d in docs]

    return render_template('view_follow_ups.html', patient=patient, followups=followups)


@app.route('/edit_patient/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def edit_patient(patient_id):
    patient = g.patient
    doc_ref = db.collection('patients').document(patient_id)

    if request.method == 'POST':
        updated_data = {
            'name': request.form['name'],
            'age_sex': request.form['age_sex'],
            'contact': request.form['contact']
        }
        doc_ref.update(updated_data)
        log_action(session['user_id'], 'Edit Patient', f"Edited patient {patient_id}")
        return redirect(url_for('view_patients'))

    return render_template('edit_patient.html', patient=patient, patient_id=patient_id)


@app.route('/patient_report/<path:patient_id>')
@login_required()
@patient_access_required
def patient_report(patient_id):
    patient = g.patient
    # fetch each section
    def fetch_one(coll):
        d = db.collection(coll).where('patient_id', '==',
                                      patient_id).limit(1).get()
        return d[0].to_dict() if d else {}

    subjective = fetch_one('subjective_examination')
    perspectives = fetch_one('patient_perspectives')
    diagnosis = fetch_one('provisional_diagnosis')
    treatment = fetch_one('treatment_plan')
    goals = fetch_one('smart_goals')
    return render_template('patient_report.html',
                           patient=patient,
                           subjective=subjective,
                           perspectives=perspectives,
                           diagnosis=diagnosis,
                           goals=goals,
                           treatment=treatment)


@app.route('/download_report/<path:patient_id>')
@login_required()
@patient_access_required
def download_report(patient_id):
    patient = g.patient
    # 2) Fetch each section for the report
    def fetch_one(coll):
        result = db.collection(coll) \
                     .where('patient_id', '==', patient_id) \
                     .limit(1).get()
        return result[0].to_dict() if result else {}

    subjective   = fetch_one('subjective_examination')
    perspectives = fetch_one('patient_perspectives')
    diagnosis    = fetch_one('provisional_diagnosis')
    goals        = fetch_one('smart_goals')
    treatment    = fetch_one('treatment_plan')

    # 3) Render the HTML template
    rendered = render_template(
        'patient_report.html',
        patient=patient,
        subjective=subjective,
        perspectives=perspectives,
        diagnosis=diagnosis,
        goals=goals,
        treatment=treatment
    )

    # 4) Generate PDF
    pdf = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(rendered), dest=pdf)
    if pisa_status.err:
        return "Error generating PDF", 500

    # 5) Return the PDF
    response = make_response(pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = (
        f'attachment; filename={patient_id}_report.pdf'
    )
    log_action(
        session.get('user_id'),
        'Download Report',
        f"Downloaded PDF report for patient {patient_id}"
    )
    return response



@app.route('/manage_users')
@login_required()
def manage_users():
    if session.get('is_admin') != 1:
        return "Access Denied: Admins only."
    docs = db.collection('users')\
             .where('is_admin','==',0)\
             .where('approved','==',1)\
             .where('institute','==',session.get('institute'))\
             .stream()
    users = [d.to_dict() for d in docs]
    return render_template('manage_users.html', users=users)


@app.route('/deactivate_user/<user_email>')
@login_required()
def deactivate_user(user_email):
    if session.get('is_admin') != 1:
        return "Access Denied"
    db.collection('users').document(user_email).update({'active': 0})
    log_action(session.get('user_id'), 'Deactivate User',
               f"User {user_email} was deactivated")
    return redirect('/manage_users')


@app.route('/reactivate_user/<user_email>')
@login_required()
def reactivate_user(user_email):
    if session.get('is_admin') != 1:
        return "Access Denied"
    db.collection('users').document(user_email).update({'active': 1})
    log_action(session.get('user_id'), 'Reactivate User',
               f"User {user_email} was reactivated")
    return redirect('/manage_users')



@app.route('/ai_suggestion/past_questions', methods=['POST'])
@csrf.exempt
@login_required()
def ai_past_questions():
    data = request.get_json() or {}
    age_sex = _age_sex_from(data)
    present_hist = data.get('present_history', '').strip()

    prompt = (
    "Generate 5 short, clear follow-up questions suitable for a physiotherapy intake form. "
    "Focus only on comorbidities, risk factors, and symptom timeline. "
    "Do not include or request any patient names, identifiers, or location data.\n"
    f"Age/Sex: {age_sex}\n"
    f"Present history: {present_hist}\n"
    "Return the questions as a numbered list."
     "Return only a numbered list of up to 5 questions. Do not include explanations or extra text."
)
    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500



@app.route('/ai_suggestion/provisional_diagnosis', methods=['POST'])
@csrf.exempt
@login_required()
def ai_provisional_diagnosis():
    data = request.get_json() or {}
    age_sex = _age_sex_from(data)
    present_hist = data.get('present_history', '').strip()
    past_hist    = data.get('past_history', '').strip()

    prompt = (
        "Given the following patient case (no names or identifying details):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present_hist}\n"
        f"Past history: {past_hist}\n"
        "List up to two likely provisional diagnoses for physiotherapy with a brief rationale for each. "
         "Format as a numbered list."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500



@app.route('/ai_suggestion/subjective/<field>', methods=['POST'])
@csrf.exempt
@login_required()
def ai_subjective_field(field):
    data = request.get_json() or {}
    age_sex = _age_sex_from(data)
    present_hist = data.get('present_history', '').strip()
    past_hist = data.get('past_history', '').strip()
    inputs = data.get('inputs', {})

    # Compose a brief summary of relevant prior subjective findings (excluding current field)
    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}"
        for k, v in inputs.items() if k != field and v
    )

    prompt = (
        "You are a physiotherapy clinical assistant. Do not use or request any patient names or identifiers.\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present_hist}\n"
        f"Past history: {past_hist}\n"
        f"Other subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"\nFor **{field.replace('_', ' ').title()}**, suggest 2–3 open-ended questions a physiotherapist should ask to clarify this aspect. "
        "Format as a numbered list."
         "Return only a numbered list of up to 2-3 suggestions. No explanations."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/ai_suggestion/subjective_diagnosis', methods=['POST'])
@csrf.exempt
@login_required()
def ai_subjective_diagnosis():
    data = request.get_json() or {}
    age_sex = _age_sex_from(data)
    present_hist = data.get('present_history', '').strip()
    past_hist = data.get('past_history', '').strip()
    inputs = data.get('inputs', {})

    findings = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}"
        for k, v in inputs.items() if v
    )

    prompt = (
        "Given the following (no names or patient identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present_hist}\n"
        f"Past history: {past_hist}\n"
        f"Subjective findings:\n{findings if findings else 'None'}\n"
        "List up to 2 likely provisional diagnoses for physiotherapy, each with a one-sentence rationale. Format as a numbered list."
         "Answer in up to 5 numbered points. Do not include patient names or identifiers."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/ai_suggestion/perspectives/<field>', methods=['POST'])
@csrf.exempt
@login_required()
def ai_perspectives_field(field):
    data = request.get_json() or {}
    prev   = data.get('previous', {})

    age_sex = _age_sex_from(data)
    present = _present_history_from(data)
    past = _past_history_from(data)
    subj = _subjective_from(data)
    perspectives = _perspectives_from(data)

    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in perspectives.items() if k != field and v
    )

    prompt = (
        "Given this case (do not use any names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives recorded:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        f"\nFor **{field.replace('_', ' ').title()}**, suggest 2–3 open-ended questions a physiotherapist should ask to clarify this perspective. Format as a numbered list."
         "Provide only a short list (2-3 items). No preamble or explanations."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/ai_suggestion/perspectives_diagnosis', methods=['POST'])
@csrf.exempt
@login_required()
def ai_perspectives_diagnosis():
    data = request.get_json() or {}
    prev   = data.get('previous', {})

    age_sex = _age_sex_from(data)
    present = _present_history_from(data)
    past    = _past_history_from(data)
    subj    = _subjective_from(data)
    persps  = _perspectives_from(data)

    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in persps.items() if v
    )

    prompt = (
        "Given this case (do not use any names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        "Based on this information, provide up to 2 provisional clinical impressions for physiotherapy, each 1–2 sentences and integrating the patient perspectives. Format as a numbered list."
         "Provide only a short list (2 items). No preamble or explanations."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500



@app.route('/ai_suggestion/initial_plan/<field>', methods=['POST'])
@csrf.exempt
@login_required()
def ai_initial_plan_field(field):
    data = request.get_json() or {}
    prev      = data.get('previous', {})
    selection = data.get('selection', '').strip()

    age_sex = _age_sex_from(data)
    present = _present_history_from(data)
    past    = _past_history_from(data)
    subj    = _subjective_from(data)
    persp   = _perspectives_from(data)

    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in persp.items() if v
    )

    prompt = (
        "Given this case (no patient names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        f"\nThe therapist marked **{field.replace('_', ' ').title()}** as **{selection}**. "
        "Interpret this category as:\n"
        "- 'Mandatory assessment': essential tests\n"
        "- 'Assessment with precaution': tests needing caution\n"
        "- 'Absolutely contraindicated': tests to avoid\n"
        "List 2–4 specific assessment tests or maneuvers that fit this category as a numbered list."
         "Return only a concise list of relevant points. Maximum 5."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500



@app.route('/ai_suggestion/initial_plan_summary', methods=['POST'])
@csrf.exempt
@login_required()
def ai_initial_plan_summary():
    data = request.get_json() or {}
    prev        = data.get('previous', {})
    assessments = data.get('assessments', {})

    age_sex = _age_sex_from(data)
    present = _present_history_from(data)
    past    = _past_history_from(data)
    subj    = _subjective_from(data)
    persp   = _perspectives_from(data)

    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in persp.items() if v
    )
    assessments_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {assessments[k]['choice']} ({assessments[k]['details']})"
        for k in assessments if assessments[k].get('choice') or assessments[k].get('details')
    )

    prompt = (
        "Given this case (no patient names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        f"Assessment plan:\n{assessments_summary if assessments_summary else 'None'}\n"
        "In 2–3 sentences, summarize the assessment findings and include up to two likely provisional diagnoses within those sentences."
         "Summarize in 2–3 sentences only."

    )

    try:
        summary = get_ai_suggestion(prompt)
        return jsonify({'summary': summary})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/ai_suggestion/patho/possible_source', methods=['POST'])
@csrf.exempt
@login_required()
def ai_patho_source():
    data = request.get_json() or {}
    prev      = data.get('previous', {})
    selection = data.get('selection', '').strip()

    age_sex = _age_sex_from(data)
    present = _present_history_from(data)
    past    = _past_history_from(data)
    subj    = _subjective_from(data)
    persp   = _perspectives_from(data)
    # Define _assessments_from to safely extract assessments from data
    assess  = _assessments_from(data)

    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in persp.items() if v
    )
    assessments_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v['choice']}" for k, v in assess.items() if v.get('choice')
    )

    prompt = (
        "Given this case (do not use patient names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        f"Assessment plan:\n{assessments_summary if assessments_summary else 'None'}\n"
        f"\nThe therapist marked Possible Source of Symptoms as: {selection}.\n"
        "Describe 2–3 concise, plausible anatomical or physiological mechanisms explaining how this source could cause the patient's symptoms. Format as a numbered list."
         "Provide only 3–5 possible sources in numbered form. Do not include personal data."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500



@app.route('/ai_suggestion/chronic/specific_factors', methods=['POST'])
@csrf.exempt
@login_required()
def ai_chronic_factors():
    data = request.get_json() or {}
    prev           = data.get('previous', {})
    text_input     = data.get('input', '').strip()
    causes_selected= data.get('causes', [])

    age_sex = _age_sex_from(data)
    present = _present_history_from(data)
    past    = _past_history_from(data)
    subj    = _subjective_from(data)
    persp   = _perspectives_from(data)
    assess  = _assessments_from(data)

    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in persp.items() if v
    )
    assessments_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v.get('choice')}" for k, v in assess.items() if v.get('choice')
    )

    causes_str = ", ".join(causes_selected) if causes_selected else "None"

    prompt = (
        "Given this case (no patient names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        f"Assessment plan:\n{assessments_summary if assessments_summary else 'None'}\n"
        f"Maintenance causes indicated: {causes_str}\n"
        f"Specific chronic factors described: {text_input if text_input else 'None'}\n"
        "List 3–5 focused, open-ended questions a physiotherapist should ask to clarify these chronic contributing factors."
         "Return 3–5 numbered points. Do not include any names, dates, or identifiers."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500



@app.route('/ai_suggestion/clinical_flags/<patient_id>/suggest', methods=['POST'])
@csrf.exempt
@login_required()
@patient_access_required
def clinical_flags_suggest(patient_id):
    data = request.get_json() or {}
    prev  = data.get('previous', {})
    field = data.get('field', '')
    text  = data.get('text', '').strip()

    # Determine relevancy hints (optional, use your existing logic)
    relevancy_hints = []
    if prev.get('subjective', {}).get('pain_irritability') == 'Present':
        relevancy_hints.append('Psychosocial risk factors (Yellow Flags)')
    if prev.get('assessments', {}).get('special_tests', {}).get('choice') == 'Absolutely Contraindicated':
        relevancy_hints.append('System/Environment barriers (Black Flags)')

    age_sex = _age_sex_from(data)
    present = _present_history_from(data)
    past    = _past_history_from(data)
    subj    = _subjective_from(data)
    persp   = _perspectives_from(data)
    assess  = _assessments_from(data)

    subjective_summary = "\n".join(
        f"- {k.title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.title()}: {v}" for k, v in persp.items() if v
    )
    assessments_summary = "\n".join(
        f"- {k.title()}: {v.get('choice')}" for k, v in assess.items() if v.get('choice')
    )
    flags_summary = ", ".join(relevancy_hints) if relevancy_hints else "General flags"

    prompt = (
        "Given this case (no patient names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        f"Assessment plan:\n{assessments_summary if assessments_summary else 'None'}\n"
        f"Relevant clinical flags: {flags_summary}\n"
        f"You are focusing on: {field.replace('_', ' ').title()} - {text}\n"
        "List 3–5 open-ended follow-up questions a physiotherapist should ask to further explore this flag."
         "Provide only 3–5 concise numbered points. Avoid identifiers."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestions': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500



    # 10) Objective Assessment Suggestions
@app.route('/objective_assessment/<patient_id>/suggest', methods=['POST'])
@csrf.exempt
@login_required(approved_only=False)
@patient_access_required
def objective_assessment_suggest(patient_id):
    data = request.get_json() or {}
    field  = (data.get('field') or '').strip()
    choice = (data.get('value') or '').strip()

    # enrich with patient + previous context
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return jsonify({'error': 'Patient not found'}), 404
    patient = doc.to_dict()

    prev = _collect_prev(data, patient)

    subj_summary = "\n".join(
        f"- {k.replace('_',' ').title()}: {v}" for k, v in prev["subjective"].items() if v
    )
    assess_summary = "\n".join(
        f"- {k.replace('_',' ').title()}: {(v.get('choice','') if isinstance(v, dict) else v)}"
        for k, v in prev["assessments"].items()
        if (v if not isinstance(v, dict) else (v.get('choice') or v.get('details')))
    )

    prompt = (
        "A physiotherapist is selecting options during an objective assessment (do not use patient names or identifiers).\n"
        f"Age/Sex: {_nz(prev['age_sex'], 'Unknown')}\n"
        f"Present history: {_nz(prev['present_history'])}\n"
        f"Past history: {_nz(prev['past_history'])}\n"
        f"Subjective summary:\n{_nz(subj_summary)}\n"
        f"Assessments so far:\n{_nz(assess_summary)}\n\n"
        f"For the **{field.replace('_',' ').title()}** section, they have chosen: {_nz(choice)}.\n"
        "List 3–5 specific next assessment actions/tests and what positive/negative findings would suggest.\n"
        "Return only a numbered list (3–5 items), no extra commentary."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500


@app.route('/ai_suggestion/objective_assessment/<field>', methods=['POST'])
@csrf.exempt
@login_required(approved_only=False)
def objective_assessment_field_suggest(field):
    """Suggest 3–5 specific objective assessments based on the selected field."""
    data = request.get_json() or {}
    choice = (data.get('value') or '').strip()

    prev = _collect_prev(data)

    subj_summary = "\n".join(
        f"- {k.replace('_',' ').title()}: {v}" for k, v in prev["subjective"].items() if v
    )
    assess_summary = "\n".join(
        f"- {k.replace('_',' ').title()}: {(v.get('choice','') if isinstance(v, dict) else v)}"
        for k, v in prev["assessments"].items()
        if (v if not isinstance(v, dict) else (v.get('choice') or v.get('details')))
    )

    prompt = (
        "A physiotherapist is selecting options during an objective assessment (no names/identifiers).\n"
        f"Age/Sex: {_nz(prev['age_sex'], 'Unknown')}\n"
        f"Present history: {_nz(prev['present_history'])}\n"
        f"Past history: {_nz(prev['past_history'])}\n"
        f"Subjective summary:\n{_nz(subj_summary)}\n"
        f"Prior assessments:\n{_nz(assess_summary)}\n\n"
        f"For the **{field.replace('_',' ').title()}** section, they selected: {_nz(choice)}.\n"
        "List 3–5 next assessment actions/tests (numbered list only)."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500



@app.route('/provisional_diagnosis_suggest/<patient_id>')
@csrf.exempt
@login_required()
@patient_access_required
def provisional_diagnosis_suggest(patient_id):
    field = (request.args.get('field', '') or '').strip()

    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return jsonify({'suggestion': ''}), 404
    patient = doc.to_dict()

    # Build a richer prior summary from patient record
    prev = {
        'age_sex':          _age_sex_from({}, patient),
        'present_history': (patient.get('present_history') or patient.get('present_complaint') or '').strip(),
        'past_history':    (patient.get('past_history') or '').strip(),
        'subjective':       patient.get('subjective_inputs') or {},
        'perspectives':     patient.get('perspectives_inputs') or {},
        'assessments':      patient.get('initial_plan_assessments') or {},
    }

    subj_summary = "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in prev['subjective'].items() if v)
    persp_summary = "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in prev['perspectives'].items() if v)
    assess_summary = "\n".join(
        f"- {k.replace('_',' ').title()}: {(v.get('choice','') if isinstance(v, dict) else v)}"
        for k, v in prev['assessments'].items()
        if (v if not isinstance(v, dict) else (v.get('choice') or v.get('details')))
    )

    templates = {
        'likelihood':
            "Given the following clinical context (no identifiers):\n"
            f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
            f"Present history: {_nz(prev['present_history'])}\n"
            f"Past history: {_nz(prev['past_history'])}\n"
            f"Subjective:\n{_nz(subj_summary)}\n"
            f"Patient perspectives:\n{_nz(persp_summary)}\n"
            f"Assessments:\n{_nz(assess_summary)}\n\n"
            "List 3 likely provisional diagnoses with a one-line rationale each (numbered).",

        'structure_fault':
            "Based on the case (no identifiers):\n"
            f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
            f"Present history: {_nz(prev['present_history'])}\n"
            f"Assessments:\n{_nz(assess_summary)}\n\n"
            "List key anatomical structures likely at fault (3–5 bullets).",

        'symptom':
            "Using this case (no identifiers):\n"
            f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
            f"Present history: {_nz(prev['present_history'])}\n"
            f"Subjective:\n{_nz(subj_summary)}\n\n"
            "Suggest 3–5 clarifying questions focused on the main symptom (numbered).",

        'findings_support':
            "From this case (no identifiers):\n"
            f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
            f"Present history: {_nz(prev['present_history'])}\n"
            f"Assessments:\n{_nz(assess_summary)}\n\n"
            "List 3–5 clinical findings that would support the leading provisional diagnosis.",

        'findings_reject':
            "From this case (no identifiers):\n"
            f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
            f"Present history: {_nz(prev['present_history'])}\n"
            f"Assessments:\n{_nz(assess_summary)}\n\n"
            "List 3–5 findings that would rule out the leading provisional diagnosis."
    }

    prompt = templates.get(field,
        "You are a physiotherapy assistant (no identifiers). Provide 3 concise points on: " + (field or "provisional diagnosis")
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        logger.info(f"[server] provisional_diagnosis_suggest {field}: {suggestion}")
        return jsonify({'suggestion': suggestion})
    except OpenAIError as e:
        logger.error(f"OpenAI API error in provisional_diagnosis_suggest: {e}", exc_info=True)
        return jsonify({'suggestion': '', 'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception as e:
        logger.error(f"Unexpected error in provisional_diagnosis_suggest: {e}", exc_info=True)
        return jsonify({'suggestion': '', 'error': 'An unexpected error occurred.'}), 500






@app.route('/ai_suggestion/smart_goals/<field>', methods=['POST'])
@csrf.exempt
@login_required()
def ai_smart_goals(field):
    data = request.get_json() or {}

    # main.js sends these blobs; normalize them
    prev = {
        "age_sex":         _age_sex_from({"previous": data.get("previous") or {}}),
        "present_history": (data.get("previous", {}).get("present_history") or "").strip(),
        "past_history":    (data.get("previous", {}).get("past_history") or "").strip(),
        "subjective":       data.get("previous_subjective") or {},
        "perspectives":     data.get("previous_perspectives") or {},
        "assessments":      data.get("previous_assessments") or {},
    }
    text = (data.get('input') or '').strip()

    assess_summary = "\n".join(
        f"- {k.replace('_',' ').title()}: {(v.get('choice','') if isinstance(v, dict) else v)}"
        for k, v in prev["assessments"].items()
        if (v if not isinstance(v, dict) else (v.get('choice') or v.get('details')))
    )

    prompts = {
        'patient_goal':
            "Draft one concise patient-centric SMART goal (numbered list with 1 item).",
        'baseline_status':
            "State a clear baseline status for tracking the SMART goal (1 bullet).",
        'measurable_outcome':
            "List 2–3 measurable outcomes for the goal (numbered).",
        'time_duration':
            "Suggest a realistic timeframe (weeks/months) aligned to the goal (1–2 bullets)."
    }

    base = (
        "You are a physiotherapy assistant. Do not include or request identifiers.\n"
        f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
        f"Present history: {_nz(prev['present_history'])}\n"
        f"Assessments:\n{_nz(assess_summary)}\n"
    )
    if text:
        base += f"\nFocus area: {_nz(text)}\n"

    prompt = base + "\n" + prompts.get(
        field,
        f"Provide a concise SMART-goal suggestion for **{field.replace('_',' ').title()}** (1–3 bullets)."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error'}), 500





# 13) Treatment Plan Suggestions
# 13) Treatment Plan Suggestions
@app.route('/ai_suggestion/treatment_plan/<field>', methods=['POST'])
@csrf.exempt
@login_required()
def treatment_plan_suggest(field):
    data = request.get_json() or {}
    text_input = (data.get('input') or '').strip()
    patient_id = (data.get('patient_id') or '').strip()

    # If a patient_id is provided, pull richer context
    patient = None
    if patient_id:
        pdoc = db.collection('patients').document(patient_id).get()
        if pdoc.exists:
            patient = pdoc.to_dict()

    prev = _collect_prev({}, patient)

    prompt = (
        "You are a physiotherapy assistant. Do not use names or identifiers.\n"
        f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
        f"Present history: {_nz(prev['present_history'])}\n"
        f"Past history: {_nz(prev['past_history'])}\n"
        f"Subjective present: {_nz(', '.join([k for k,v in prev['subjective'].items() if v]))}\n"
        f"Assessments: {_nz(', '.join([k for k,v in prev['assessments'].items() if v]))}\n\n"
        f"Focus area (**{field.replace('_',' ').title()}**): {_nz(text_input)}\n\n"
        "Propose 3 concise, evidence-aligned treatment actions (bulleted)."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'field': field, 'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500



@app.route('/ai_suggestion/treatment_plan_summary/<patient_id>')
@csrf.exempt
@login_required()
@patient_access_required
def treatment_plan_summary(patient_id):
    """Gather saved screens and produce a concise, PHI-safe treatment plan summary."""
    pat_doc = db.collection('patients').document(patient_id).get()
    patient_info = pat_doc.to_dict() if pat_doc.exists else {}

    def fetch_latest(collection_name):
        coll = (
            db.collection(collection_name)
              .where('patient_id', '==', patient_id)
              .order_by('timestamp', direction=_fa_fs.Query.DESCENDING)
              .limit(1)
              .get()
        )
        return coll[0].to_dict() if coll else {}

    subj      = fetch_latest('subjective_examination')
    persp     = fetch_latest('patient_perspectives')
    assess    = fetch_latest('objective_assessments')
    patho     = fetch_latest('patho_mechanism')
    chronic   = fetch_latest('chronic_diseases')
    flags     = fetch_latest('clinical_flags')
    objective = fetch_latest('objective_assessments')
    prov_dx   = fetch_latest('provisional_diagnosis')
    goals     = fetch_latest('smart_goals')
    tx_plan   = fetch_latest('treatment_plan')

    prompt = (
        "You are a PHI-safe clinical summarization assistant. Do not use any patient names or IDs.\n\n"
        f"Patient demographics: {patient_info.get('age_sex', 'N/A')}; "
        f"Sex: {patient_info.get('sex', 'N/A')}; "
        f"Past medical history: {patient_info.get('past_history', 'N/A')}.\n\n"
        "Subjective examination:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in subj.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Patient perspectives (ICF):\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in persp.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Initial plan of assessment:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v.get('choice','') if isinstance(v, dict) else v}" for k, v in assess.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Pathophysiological mechanism:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in patho.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Chronic disease factors:\n"
        f"- Maintenance causes: {chronic.get('maintenance_causes','')}\n"
        f"- Specific factors: {chronic.get('specific_factors','')}\n\n"
        "Clinical flags:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in flags.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Objective assessment:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in objective.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Provisional diagnosis:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in prov_dx.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "SMART goals:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in goals.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Treatment plan:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in tx_plan.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Create a concise treatment plan summary that links history, exam findings, goals, and interventions.\n"
        "Return 3–5 numbered points. No preamble."
    )

    try:
        summary = get_ai_suggestion(prompt).strip()
        return jsonify({'summary': summary})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500



@app.route('/ai_followup_suggestion/<patient_id>', methods=['POST'])
@csrf.exempt
@login_required()
@patient_access_required
def ai_followup_suggestion(patient_id):
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return jsonify({'error': 'Patient not found'}), 404
    patient = doc.to_dict()

    data = request.get_json() or {}
    prev = _collect_prev({}, patient)

    session_no    = data.get('session_number')
    session_date  = data.get('session_date')
    grade         = data.get('grade')
    perception    = data.get('perception')
    feedback      = data.get('feedback')

    case_summary = "\n".join(filter(None, [
        f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}",
        f"Present history: {_nz(prev['present_history'])}",
        f"Past history: {_nz(prev['past_history'])}",
        f"Subjective: {_nz(', '.join([k for k,v in prev['subjective'].items() if v]))}",
        f"Assessments: {_nz(', '.join([k for k,v in prev['assessments'].items() if v]))}",
    ]))

    prompt = (
        "You are a PHI-safe clinical reasoning assistant for physiotherapy. Never include patient names or IDs.\n\n"
        "Case summary so far:\n"
        f"{case_summary}\n\n"
        "New follow-up session details:\n"
        f"- Session number: {_nz(session_no)} on {_nz(session_date)}\n"
        f"- Grade: {_nz(grade)}\n"
        f"- Perception: {_nz(perception)}\n"
        f"- Feedback: {_nz(feedback)}\n\n"
        "Suggest the next treatment session focus (2–3 bullets) aligned with prior findings and any SMART goals."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error occurred.'}), 500




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))



