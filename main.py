import os
import io
import json
from flask import (Flask, render_template, request, redirect,session, url_for, flash,jsonify)
from datetime import datetime
from flask_login import login_required
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from xhtml2pdf import pisa
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from google.api_core.exceptions import GoogleAPIError
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin.firestore import SERVER_TIMESTAMP
from google.cloud.firestore_v1.base_query import FieldFilter
import openai
# some versions of the OpenAI pip package don’t expose openai.error
try:
    from openai.error import OpenAIError
except ImportError:
    # fall back so our except‐clauses below still work
    OpenAIError = Exception


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# initialize OpenAI
openai.api_key = os.environ['OPENAI_API_KEY']


cred = credentials.Certificate(os.environ['GOOGLE_APPLICATION_CREDENTIALS'])
firebase_admin.initialize_app(cred)
db = firestore.client()
def get_ai_suggestion(prompt: str) -> str:
    """
        Sends a prompt to OpenAI and returns the assistant's reply.
        """
    # Using the v1+ client syntax
    resp = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{
            "role": "system",
            "content": "You are a helpful clinical reasoning assistant."
        }, {
            "role": "user",
            "content": prompt
        }],
        temperature=0.7,
        max_tokens=200)
    # The path to the text is the same
    return resp.choices[0].message.content


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




app = Flask(__name__)
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

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)


def login_required(approved_only=True):

    def wrapper(f):

        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect('/login')
            if approved_only and session.get('is_admin') != 1 and session.get(
                    'approved') == 0:
                return "Access denied. Awaiting approval by admin."
            return f(*args, **kwargs)

        return decorated_function

    return wrapper

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        pwd = request.form['password']
        pw_hash = generate_password_hash(pwd)
        db.collection('users').document(email).set({
            'name': name,
            'email': email,
            'password_hash': pw_hash,
            'created_at': SERVER_TIMESTAMP,
            'approved': 1,
            'active': 1,
            'is_admin': 0
        })
        session['user_id'] = email
        session['user_name'] = name  
        return redirect('/dashboard')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        pwd = request.form['password']
        doc = db.collection('users').document(
            email).get()  # type: ignore[attr-defined]
        if not doc.exists:
            return "Invalid login credentials."
        user = doc.to_dict()
        if check_password_hash(user.get('password_hash', ''), pwd):
            if user.get('approved', 0) == 1 and user.get('active', 1) == 1:
                session.update({
                    'user_id': email,
                    'user_name': user.get('name'),
                    'institute': user.get('institute'),
                    'is_admin': user.get('is_admin', 0),
                    'approved': user.get('approved', 0)
                })
                log_action(email, 'Login', f"{user.get('name')} logged in.")
                return redirect('/dashboard')
            elif user.get('active', 1) == 0:
                return "Your account has been deactivated. Contact your admin."
            else:
                return "Your registration is pending admin approval."
        return "Invalid login credentials."
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/dashboard')
@login_required()
def dashboard():
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
        name_f = request.args.get('name')
        id_f   = request.args.get('patient_id')

        try:
            # 1) Base collection
            coll = db.collection('patients')
            q = coll

            # 2) Apply filters
            if name_f:
                # Note: Firestore requires an order_by on the same field when using >=
                q = q.where('name', '>=', name_f).order_by('name')
            if id_f:
                q = q.where('patient_id', '==', id_f)

            # 3) Restrict by institute or physio
            if session.get('is_admin') == 1:
                q = q.where('institute', '==', session.get('institute'))
            else:
                q = q.where('physio_id', '==', session.get('user_id'))

            # 4) Execute and materialize
            docs = q.stream()
            patients = [doc.to_dict() for doc in docs]

        except GoogleAPIError as e:
            logger.error(f"Firestore error in view_patients: {e}", exc_info=True)
            flash("Could not load your patients list. Please try again later.", "error")
            return redirect(url_for('dashboard'))

        # 5) Render on success
        return render_template('view_patients.html', patients=patients)



@app.route('/register_institute', methods=['GET', 'POST'])
def register_institute():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        pwd = generate_password_hash(request.form['password'])
        inst = request.form['institute']
        db.collection('users').document(email).set({
            'name':
            name,
            'email':
            email,
            'phone':
            phone,
            'password_hash':
            pwd,
            'institute':
            inst,
            'is_admin':
            1,
            'approved':
            1,
            'active':
            1,
            'created_at':
            SERVER_TIMESTAMP
        })
        log_action(None, 'Register', f"{name} registered as Institute Admin")
        return redirect('/login_institute')
    return render_template('register_institute.html')


@app.route('/login_institute', methods=['GET', 'POST'])
def login_institute():
    if request.method == 'POST':
        email = request.form['email']
        pwd = request.form['password']
        doc = db.collection('users').document(
            email).get()  # type: ignore[attr-defined]
        if not doc.exists:
            return "Invalid credentials or account doesn't exist."
        user = doc.to_dict()
        if check_password_hash(user.get('password_hash', ''), pwd):
            if user.get('approved', 0) == 0:
                return "Your account is pending approval by the institute admin."
            if user.get('active', 1) == 0:
                return "Your account has been deactivated. Please contact your admin."
            session.update({
                'user_id': email,
                'user_name': user.get('name'),
                'institute': user.get('institute'),
                'is_admin': user.get('is_admin', 0),
                'approved': user.get('approved', 0)
            })
            log_action(email, 'Login',
                       f"{user.get('name')} (Admin) logged in.")
            if user.get('is_admin', 0) == 1:
                return redirect('/admin_dashboard')
            return redirect('/dashboard')
        return "Invalid credentials or account doesn't exist."
    return render_template('login_institute.html')

@app.route('/register_with_institute', methods=['GET', 'POST'])
def register_with_institute():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = generate_password_hash(request.form['password'])
        institute = request.form['institute']
        is_admin = 0
        approved = 0
        active = 1

        # Check if user already exists
        existing_email = db.collection('users').where('email', '==', email).stream()
        existing_phone = db.collection('users').where('phone', '==', phone).stream()

        if any(existing_email) or any(existing_phone):
            return "Email or phone number already registered."

        # Register new user under selected institute
        db.collection('users').add({
            'name': name,
            'email': email,
            'phone': phone,
            'password': password,
            'institute': institute,
            'is_admin': is_admin,
            'approved': approved,
            'active': active
        })

        log_action(user_id=None, action="Register", details=f"{name} registered as Institute Physio (pending approval)")

        return "Registration successful! Awaiting admin approval."

    # GET method: show list of institutes (unique from admin users)
    admins = db.collection('users').where('is_admin', '==', 1).stream()
    institutes = list({admin.to_dict().get('institute') for admin in admins})

    return render_template('register_with_institute.html', institutes=institutes)
    

@app.route('/approve_physios')
@login_required()
def approve_physios():
    if session.get('is_admin') != 1:
        return redirect('/login_institute')

    docs = (db.collection('users')
              .where('is_admin','==',0)
              .where('approved','==',0)
              .where('institute','==', session.get('institute'))
              .stream())

    pending = []
    for d in docs:
        data = d.to_dict()
        # Firestore doc ID is the physio’s email
        data['email'] = d.id
        pending.append(data)

    return render_template('approve_physios.html', physios=pending)


@app.route('/approve_user/<user_email>', methods=['POST'])
@login_required()
def approve_user(user_email):
        if session.get('is_admin') != 1:
            return redirect('/login_institute')
        db.collection('users').document(user_email).update({'approved': 1})
        log_action(session.get('user_id'), 'Approve User',
                   f"Approved user {user_email}")
        return redirect('/approve_physios')



@app.route('/audit_logs')
@login_required()
def audit_logs():
    logs = []

    if session.get('is_admin') == 1:
        # Admin: fetch logs for all users in their institute
        users = db.collection('users') \
                  .where('institute', '==', session['institute']) \
                  .stream()
        user_map = {u.id: u.to_dict() for u in users}
        user_ids = list(user_map.keys())

        for uid in user_ids:
            entries = db.collection('audit_logs').where('user_id', '==', uid).stream()
            for e in entries:
                data = e.to_dict()
                data['name'] = user_map[uid]['name']
                logs.append(data)

    elif session.get('is_admin') == 0:
        # Individual physio: only their logs
        entries = db.collection('audit_logs').where('user_id', '==', session['user_id']).stream()
        for e in entries:
            data = e.to_dict()
            data['name'] = session['user_name']
            logs.append(data)

    # Sort by timestamp descending
    logs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

    return render_template('audit_logs.html', logs=logs)

@app.route('/export_audit_logs')
@login_required()
def export_audit_logs():
    if session.get('is_admin') != 1:
        return redirect('/login_institute')

    users = db.collection('users') \
              .where('institute', '==', session['institute']) \
              .stream()
    user_map = {u.id: u.to_dict() for u in users}
    user_ids = list(user_map.keys())

    logs = []
    for uid in user_ids:
        entries = db.collection('audit_logs').where('user_id', '==', uid).stream()
        for e in entries:
            log = e.to_dict()
            logs.append([
                user_map[uid]['name'],
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

        # 2) build a per‑month counter key, e.g. "2025/07"
        now       = datetime.utcnow()
        month_key = now.strftime('%Y%m')

        counter_ref = db.collection('patient_counters').document(month_key)

        # 3) bump the counter transactionally
        @firestore.transactional
        def bump(txn):
            snap = counter_ref.get(transaction=txn)
            data_snap = snap.to_dict() or {}
            if not snap.exists:
                txn.set(counter_ref, {'count': 1})
                return 1
            else:
                new_count = data_snap.get('count', 0) + 1
                txn.update(counter_ref, {'count': new_count})
                return new_count

        seq = bump(db.transaction())

        # 4) assemble your pretty patient ID "YYYY/MM/NN"
        pid = f"{now.year:04d}/{now.month:02d}/{seq:02d}"

        # 5) write the patient doc under that ID
        db.collection('patients').document(pid).set({
            **data,
            'patient_id': pid
        })

        log_action(session.get('user_id'),
                   'Add Patient',
                   f"Added {data['name']} (ID: {pid})")

        # 6) redirect to the next screen
        return redirect(url_for('subjective', patient_id=pid))

    # GET → render the blank form
    return render_template('add_patient.html')





@app.route('/subjective/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
def subjective(patient_id):
    doc = db.collection('patients').document(
        patient_id).get()  # type: ignore[attr-defined]
    if not doc.exists:
        return "Patient not found."
    patient = doc.to_dict()
    if session.get('is_admin') == 0 and patient.get(
            'physio_id') != session.get('user_id'):
        return "Access denied."
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
def perspectives(patient_id):
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return "Patient not found."
    patient = doc.to_dict()
    if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
        return "Access denied."

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
def initial_plan(patient_id):
    doc = db.collection('patients').document(patient_id).get()  # type: ignore[attr-defined]
    if not doc.exists:
        return "Patient not found."
    patient = doc.to_dict()
    if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
        return "Access denied."
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
def patho_mechanism(patient_id):
    doc = db.collection('patients').document(
        patient_id).get()  # type: ignore[attr-defined]
    if not doc.exists:
        return "Patient not found."
    patient = doc.to_dict()
    if session.get('is_admin') == 0 and patient.get(
            'physio_id') != session.get('user_id'):
        return "Access denied."
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
def clinical_flags(patient_id):
    # fetch patient record just like your other screens
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return "Patient not found."
    patient = doc.to_dict()
    if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
        return "Access denied."

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
def objective_assessment(patient_id):
    # (fetch patient, check access—same as your other screens)
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return "Patient not found."
    patient = doc.to_dict()
    if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
        return "Access denied."

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
def provisional_diagnosis(patient_id):
    doc = db.collection('patients').document(
        patient_id).get()  # type: ignore[attr-defined]
    if not doc.exists:
        return "Patient not found."
    patient = doc.to_dict()
    if session.get('is_admin') == 0 and patient.get(
            'physio_id') != session.get('user_id'):
        return "Access denied."
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
def smart_goals(patient_id):
    doc = db.collection('patients').document(
        patient_id).get()  # type: ignore[attr-defined]
    if not doc.exists:
        return "Patient not found."
    patient = doc.to_dict()
    if session.get('is_admin') == 0 and patient.get(
            'physio_id') != session.get('user_id'):
        return "Access denied."
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
def treatment_plan(patient_id):
    doc = db.collection('patients').document(
        patient_id).get()  # type: ignore[attr-defined]
    if not doc.exists:
        return "Patient not found."
    patient = doc.to_dict()
    if session.get('is_admin') == 0 and patient.get(
            'physio_id') != session.get('user_id'):
        return "Access denied."
    if request.method == 'POST':
        keys = ['treatment_plan', 'goal_targeted', 'reasoning', 'reference']
        entry = {k: request.form[k] for k in keys}
        entry['patient_id'] = patient_id
        entry['timestamp'] = SERVER_TIMESTAMP
        db.collection('treatment_plan').add(entry)
        return redirect('/dashboard')
    return render_template('treatment_plan.html', patient_id=patient_id)

@app.route('/follow_ups/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
def follow_ups(patient_id):
    # 1) fetch patient and permission check
    patient_doc = db.collection('patients').document(patient_id).get()
    if not patient_doc.exists:
        return "Patient not found", 404
    patient = patient_doc.to_dict()
    if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
        return "Access denied", 403

    # 2) handle new entry
    if request.method == 'POST':
        entry = {
            'patient_id':      patient_id,
            'session_number':  int(request.form['session_number']),
            'session_date':    request.form['session_date'],
            'grade':           request.form['grade'],
            'perception':      request.form['belief_treatment'],
            'feedback':        request.form['belief_feedback'],
            'treatment_plan':  request.form['treatment_plan'],
            'timestamp':       SERVER_TIMESTAMP
        }
        db.collection('follow_ups').add(entry)
        log_action(session['user_id'], 'Add Follow-Up',
                   f"Follow-up #{entry['session_number']} for {patient_id}")
        return redirect(f'/follow_ups/{patient_id}')

    # 3) on GET, pull all existing
    docs = (db.collection('follow_ups')
              .where('patient_id', '==', patient_id)
              .order_by('session_number')
              .stream())
    followups = [d.to_dict() for d in docs]

    return render_template('follow_ups.html',                       patient=patient, patient_id=patient_id,
                           followups=followups)

# ─── VIEW FOLLOW-UPS ROUTE ─────────────────────────────────────────────
@app.route('/view_follow_ups/<path:patient_id>')
@login_required()
def view_follow_ups(patient_id):
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return "Patient not found."
    patient = doc.to_dict()

    # Access control
    if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
        return "Access denied."

    docs = (db.collection('follow_ups')
              .where('patient_id', '==', patient_id)
              .order_by('session_date', direction=firestore.Query.DESCENDING)
              .stream())
    followups = [d.to_dict() for d in docs]

    return render_template('view_follow_ups.html', patient=patient, followups=followups)


@app.route('/edit_patient/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
def edit_patient(patient_id):
    doc_ref = db.collection('patients').document(patient_id)
    doc = doc_ref.get()
    if not doc.exists:
        return "Patient not found", 404

    patient = doc.to_dict()

    if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
        return "Access denied", 403

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
def patient_report(patient_id):
    doc = db.collection('patients').document(
        patient_id).get()  # type: ignore[attr-defined]
    if not doc.exists:
        return "Patient not found."
    patient = doc.to_dict()
    if session.get('is_admin') == 0 and patient.get(
            'physio_id') != session.get('user_id'):
        return "Access denied."
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
def download_report(patient_id):
    # 1) Fetch patient record and check permissions
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return "Patient not found.", 404
    patient = doc.to_dict()
    if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
        return "Access denied.", 403

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
    age_sex        = data.get('age_sex', '').strip()
    present_hist   = data.get('present_history', '').strip()

    prompt = (
        "You are a physiotherapy clinical decision-support assistant. "
        "Exclude any patient identifiers.\n"
        "History provided:\n"
        f"- Age/Sex: {age_sex}\n"
        f"- Present history: {present_hist}\n\n"
        "Provide five concise follow-up questions to clarify the patient's past medical history, "
        "focusing on relevant comorbidities, risk factors, and symptom timeline. "
        "Format as a numbered list."
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
    age_sex        = data.get('age_sex', '').strip()
    present_hist   = data.get('present_history', '').strip()
    past_hist      = data.get('past_history', '').strip()

    prompt = (
        "You are a physiotherapy clinical decision-support assistant. "
        "Exclude any patient identifiers.\n"
        "History provided:\n"
        f"- Age/Sex: {age_sex}\n"
        f"- Present history: {present_hist}\n"
        f"- Past history: {past_hist}\n\n"
        "List up to two possible provisional diagnoses with a one-sentence rationale each. "
        "Format each as a numbered item."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})

    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503

    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500


@app.route('/ai_suggestion/subjective/<field>', methods=['POST'])

@login_required()
def ai_subjective_field(field):
       data = request.get_json() or {}
       age_sex      = data.get('age_sex', '').strip()
       present_hist = data.get('present_history', '').strip()
       past_hist    = data.get('past_history', '').strip()
       inputs       = data.get('inputs', {})

       prompt = (
           "You’re a physiotherapy clinical decision-support assistant. Exclude all identifiers.\n"
           "Patient info:\n"
           f"- Age/Sex: {age_sex}\n"
           f"- Present history: {present_hist}\n"
           f"- Past history: {past_hist}\n\n"
           "Subjective findings so far:\n" +
           "\n".join(f"- {k.replace('_',' ').title()}: {v}"
                     for k, v in inputs.items() if k != field and v) +
           f"\n\nFor **{field.replace('_',' ').title()}**, provide **2 – 3 concise, open-ended questions** to explore this area further (align with WHO ICF)."
       )

       try:
           suggestion = get_ai_suggestion(prompt)
           return jsonify({'suggestion': suggestion})
       except OpenAIError:
           return jsonify({'error': 'AI service unavailable.'}), 503
       except Exception:
           return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/ai_suggestion/subjective_diagnosis', methods=['POST'])

@login_required()
def ai_subjective_diagnosis():
       data = request.get_json() or {}
       age_sex      = data.get('age_sex', '').strip()
       present_hist = data.get('present_history', '').strip()
       past_hist    = data.get('past_history', '').strip()
       inputs       = data.get('inputs', {})

       prompt = (
           "You’re a physiotherapy clinical decision-support assistant. Exclude all identifiers.\n"
           "Patient info:\n"
           f"- Age/Sex: {age_sex}\n"
           f"- Present history: {present_hist}\n"
           f"- Past history: {past_hist}\n\n"
           "Subjective exam findings:\n" +
           "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in inputs.items() if v) +
           "\n\nList up to **2 provisional diagnoses** with a **one-sentence rationale** each. Format as a numbered list."
       )

       try:
           suggestion = get_ai_suggestion(prompt)
           return jsonify({'suggestion': suggestion})
       except OpenAIError:
           return jsonify({'error': 'AI service unavailable.'}), 503
       except Exception:
           return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/ai_suggestion/perspectives/<field>', methods=['POST'])
@login_required()
def ai_perspectives_field(field):
        data     = request.get_json() or {}
        prev     = data.get('previous', {})      # from AddPatient + Subjective
        inputs   = data.get('inputs', {})        # current field value

        # Build prompt pieces
        age_sex  = prev.get('age_sex', '')
        present  = prev.get('present_history', '')
        past     = prev.get('past_history', '')
        subj     = prev.get('subjective', {})    # you may have stored as nested dict

        prompt = (
            "You are a physiotherapy clinical decision-support assistant. Exclude any identifiers.\n"
            "Patient summary:\n"
            f"- Age/Sex: {age_sex}\n"
            f"- Present history: {present}\n"
            f"- Past history: {past}\n\n"
            "Subjective findings:\n" +
            "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k,v in subj.items() if v) +
            "\n\n"
            "Patient perspectives recorded so far:\n" +
            "\n".join(f"- {k.replace('_',' ').title()}: {v}" 
                      for k,v in prev.get('perspectives', {}).items() if k != field and v) +
            f"\n\nFor **{field.replace('_',' ').title()}**, suggest **2–3 concise, open-ended questions** a physiotherapist can ask to explore this area deeper. "
            "Format as a numbered list."
        )

        try:
            suggestion = get_ai_suggestion(prompt)
            return jsonify({'suggestion': suggestion})
        except OpenAIError:
            return jsonify({'error': 'AI service unavailable.'}), 503
        except Exception:
            return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/ai_suggestion/perspectives_diagnosis', methods=['POST'])
@login_required()
def ai_perspectives_diagnosis():
        data   = request.get_json() or {}
        prev   = data.get('previous', {})
        inputs = data.get('inputs', {})

        age_sex  = prev.get('age_sex', '')
        present  = prev.get('present_history', '')
        past     = prev.get('past_history', '')
        subj     = prev.get('subjective', {})
        persps   = inputs  # latest perspective values

        prompt = (
            "You are a physiotherapy clinical decision-support assistant. Exclude any identifiers.\n"
            "Patient summary:\n"
            f"- Age/Sex: {age_sex}\n"
            f"- Present history: {present}\n"
            f"- Past history: {past}\n\n"
            "Subjective findings:\n" +
            "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k,v in subj.items() if v) +
            "\n\n"
            "Patient perspectives:\n" +
            "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k,v in persps.items() if v) +
            "\n\nProvide up to **2 provisional clinical impressions** (1–2 sentences each), integrating these perspectives. "
            "Number each item."
        )

        try:
            suggestion = get_ai_suggestion(prompt)
            return jsonify({'suggestion': suggestion})
        except OpenAIError:
            return jsonify({'error': 'AI service unavailable.'}), 503
        except Exception:
            return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/ai_suggestion/initial_plan/<field>', methods=['POST'])
@login_required()
def ai_initial_plan_field(field):
    data      = request.get_json() or {}
    prev      = data.get('previous', {})
    selection = data.get('selection', '').strip()

    # Build prompt
    prompt = (
        "You are a PHI-safe clinical assessment assistant. Use WHO-ICF and physiotherapy best practices.\n\n"
        "Patient context:\n"
        f"- Age/Sex: {prev.get('age_sex','')}\n"
        f"- Present history: {prev.get('present_history','')}\n"
        f"- Past history: {prev.get('past_history','')}\n\n"
        "Subjective findings:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}"
                  for k,v in (prev.get('subjective',{})).items() if v) +
        "\n\nPerspectives:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}"
                  for k,v in (prev.get('perspectives',{})).items() if v) +
        f"\n\nThe therapist marked **{field.replace('_',' ').title()}** as “{selection}”. "
        "Interpret “Mandatory assessment” as essential tests, “Assessment with precaution” as tests requiring caution, "
        "and “Absolutely Contraindicated” as tests to avoid. "
        "List 2–4 specific tests or maneuvers matching this category as a bullet list."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error':'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error':'Unexpected error.'}), 500


@app.route('/ai_suggestion/initial_plan_summary', methods=['POST'])
@login_required()
def ai_initial_plan_summary():
    data        = request.get_json() or {}
    prev        = data.get('previous', {})
    assessments = data.get('assessments', {})

    # Build prompt
    prompt = (
        "You are a PHI-safe clinical summarizer.\n\n"
        "Patient context:\n"
        f"- Age/Sex: {prev.get('age_sex','')}\n"
        f"- Present history: {prev.get('present_history','')}\n"
        f"- Past history: {prev.get('past_history','')}\n\n"
        "Subjective findings:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}"
                  for k,v in (prev.get('subjective',{})).items() if v) +
        "\n\nPerspectives:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}"
                  for k,v in (prev.get('perspectives',{})).items() if v) +
        "\n\nAssessment plan:\n" +
        "\n".join(
          f"- {k.replace('_',' ').title()}: {assessments[k]['choice']} ({assessments[k]['details']})"
          for k in assessments
        ) +
        "\n\nProvide a concise 2-3 sentence summary of the assessment findings and up to two provisional diagnoses."
    )

    try:
        summary = get_ai_suggestion(prompt)
        return jsonify({'summary': summary})
    except OpenAIError:
        return jsonify({'error':'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error':'Unexpected error.'}), 500

@app.route('/ai_suggestion/patho/possible_source', methods=['POST'])
@csrf.exempt
@login_required()
def ai_patho_source():
    data      = request.get_json() or {}
    prev      = data.get('previous', {})
    selection = data.get('selection', '').strip()

    # Build prompt
    prompt = (
        "You are a PHI-safe clinical reasoning assistant. Integrate all collected patient data—"
        "demographics, presenting complaint, medical history, subjective findings, "
        "patient perspectives, and planned assessments.\n\n"
        "Patient summary:\n"
        f"- Age/Sex: {prev.get('age_sex','')}\n"
        f"- Present history: {prev.get('present_history','')}\n"
        f"- Past history: {prev.get('past_history','')}\n\n"
        "Subjective findings:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}"
                  for k,v in prev.get('subjective',{}).items() if v) +
        "\n\nPerspectives:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}"
                  for k,v in prev.get('perspectives',{}).items() if v) +
        "\n\nAssessment plan:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}"
                  for k,v in prev.get('assessments',{}).items() if v.get('choice')) +
        f"\n\nThe clinician marked **Possible Source of Symptoms** as “{selection}”. "
        "Describe 2–3 concise, plausible anatomical or physiological mechanisms explaining how this source produces the patient’s symptoms. "
        "Format as a numbered list."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error':'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error':'Unexpected error.'}), 500



@app.route('/ai_suggestion/chronic/specific_factors', methods=['POST'])
@csrf.exempt
@login_required()
def ai_chronic_factors():
    data            = request.get_json() or {}
    prev            = data.get('previous', {})
    text_input      = data.get('input', '').strip()
    causes_selected = data.get('causes', [])  # if you want checkboxes

    # Build prompt
    prompt = (
        "You are a PHI-safe clinical questioning assistant. Integrate all prior patient data:\n"
        f"- Age/Sex: {prev.get('age_sex','')}\n"
        f"- Present history: {prev.get('present_history','')}\n"
        f"- Past history: {prev.get('past_history','')}\n\n"
        "Subjective findings:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}"
                  for k,v in prev.get('subjective',{}).items() if v) +
        "\n\nPerspectives:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}"
                  for k,v in prev.get('perspectives',{}).items() if v) +
        "\n\nAssessment plan:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v.get('choice')}"
                  for k,v in prev.get('assessments',{}).items() if v.get('choice')) +
        "\n\nThe clinician indicated these maintenance causes:\n" +
        ("\n".join(f"- {c}" for c in causes_selected) if causes_selected else "- None") +
        f"\n\nSpecific factors described: {text_input}\n\n"
        "What 3–5 directed, open-ended questions should the physiotherapist ask to clarify these chronic contributing factors?"
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error':'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error':'Unexpected error.'}), 500



@app.route('/ai_suggestion/clinical_flags/<patient_id>/suggest', methods=['POST'])
@csrf.exempt
@login_required()
def clinical_flags_suggest(patient_id):
    data   = request.get_json() or {}
    prev   = data.get('previous', {})
    field  = data.get('field', '')
    text   = data.get('text', '').strip()

    # Determine which flags are “relevant” based on prior inputs
    # (e.g. if pain_irritability == Present → highlight Yellow Flags)
    relevancy_hints = []
    if prev.get('subjective', {}).get('pain_irritability') == 'Present':
        relevancy_hints.append("Psychosocial risk factors (Yellow Flags)")
    if prev.get('assessments', {}).get('special_tests', {}).choice =='Absolutely Contraindicated':
        relevancy_hints.append("System/Environment barriers (Black Flags)")
    # … add any other heuristics you like …

    prompt = (
        "You are a PHI-safe clinical prompting assistant.\n"
        "Integrate patient data:\n"
        f"- Age/Sex: {prev.get('age_sex','')}\n"
        f"- Present history: {prev.get('present_history','')}\n"
        f"- Past history: {prev.get('past_history','')}\n\n"
        "Subjective findings:\n" +
        "\n".join(f"- {k.title()}: {v}" for k,v in prev.get('subjective',{}).items() if v) +
        "\n\nPerspectives:\n" +
        "\n".join(f"- {k.title()}: {v}" for k,v in prev.get('perspectives',{}).items() if v) +
        "\n\nAssessments:\n" +
        "\n".join(f"- {k.title()}: {v.get('choice')}" for k,v in prev.get('assessments',{}).items() if v.get('choice')) +
        "\n\nRelevant flags to consider (based on above):\n" +
        ("\n".join(f"- {h}" for h in relevancy_hints) or "- General flags") +
        f"\n\nYou are focusing on **{field.replace('_',' ').title()}** where the clinician noted:\n“{text}”\n\n"
        "List 3–5 open-ended follow-up questions a physiotherapist should ask to probe this flag."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestions': suggestion})
    except OpenAIError:
        return jsonify({'error':'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error':'Unexpected error.'}), 500


    # 10) Objective Assessment Suggestions
@app.route('/objective_assessment/<patient_id>/suggest', methods=['POST'])
@login_required(approved_only=False)
def objective_assessment_suggest(patient_id):
        data = request.get_json() or {}
        logger.info(f"🔎 [server] ObjectiveAssessment payload for patient {patient_id}: {data}")
        field  = data.get('field')
        choice = data.get('value')

        prompt = (
            f"A physio is filling out an objective assessment for patient {patient_id}. "
            f"They have chosen '{choice}' for the '{field}' field. "
            "List 3–5 specific assessments they should perform next."
        )

        try:
            suggestion = get_ai_suggestion(prompt).strip()
            logger.info(f"💬 [server] ObjectiveAssessment suggestion: {suggestion}")
            return jsonify({'suggestion': suggestion})

        except OpenAIError as e:
            logger.error(f"OpenAI API error in objective_assessment_suggest: {e}", exc_info=True)
            return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503

        except Exception as e:
            logger.error(f"Unexpected error in objective_assessment_suggest: {e}", exc_info=True)
            return jsonify({'error': 'An unexpected error occurred.'}), 500

@app.route('/ai_suggestion/objective_assessment/<field>', methods=['POST'])
@login_required(approved_only=False)
def objective_assessment_field_suggest(field):
    """
    Suggest 3–5 specific objective assessments based on the selected field.
    """
    data = request.get_json() or {}
    logger.info(f"🧠 [server] ObjectiveAssessment payload for patient {data.get('patient_id')}: {data}")
    choice = data.get('value', '')

    prompt = (
        f"A physiotherapist is filling out an objective assessment for patient {data.get('patient_id')}. "
        f"They have chosen '{choice}' for the '{field}' field. "
        "List 3–5 specific assessments they should perform next."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        logger.info(f"🧠 [server] ObjectiveAssessment suggestion for “{field}”: {suggestion}")
        return jsonify({'suggestion': suggestion})
    except OpenAIError as e:
        logger.error(f"OpenAI API error in objective_assessment_field_suggest: {e}", exc_info=True)
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception as e:
        logger.error(f"Unexpected error in objective_assessment_field_suggest: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred.'}), 500


            # at the bottom of main.py (after your other @app.route handlers)

@app.route('/provisional_diagnosis_suggest/<patient_id>')
@login_required()
def provisional_diagnosis_suggest(patient_id):
                # which field was clicked?
                field = request.args.get('field', '')
                logger.info(f"🧠 [server] provisional_diagnosis_suggest for patient {patient_id}, field {field}")

                # pull together any prior inputs you’ve stored — you can load them from Firestore
                # or however you’ve been persisting each screen. Here’s a stub:
                doc = db.collection('patients').document(patient_id).get()
                if not doc.exists:
                    return jsonify({'suggestion': ''}), 404
                patient = doc.to_dict()

                # Example: you might also fetch each collection (subjective, perspectives, etc.)
                # and merge them into a single `prev` dict. For now, we’ll just work off patient demographics:
                prev = {
                    'age_sex': patient.get('age_sex',''),
                    'present_complaint': patient.get('present_complaint',''),
                    # …and so on
                }

                # define a prompt for each box
                prompts = {
                    'likelihood':       f"Given all prior data for patient {patient_id}, suggest how likely diagnoses should be phrased.",
                    'structure_fault':  f"For patient {patient_id}, suggest which anatomical structures to consider faulty based on history.",
                    'symptom':          f"For patient {patient_id}, suggest clarifying questions about their main symptom.",
                    'findings_support': f"List clinical findings that would support the provisional diagnosis in patient {patient_id}.",
                    'findings_reject':  f"List common findings that might rule out this provisional diagnosis for patient {patient_id}."
                }

                # pick the right one (or default)
                prompt = prompts.get(field, f"Help with {field} for patient {patient_id}.")

                try:
                    suggestion = get_ai_suggestion(prompt).strip()
                    logger.info(f"🤖 [server] provisional_diagnosis_suggest → {suggestion}")
                    return jsonify({'suggestion': suggestion})
                except OpenAIError as e:
                    logger.error(f"OpenAI API error in provisional_diagnosis_suggest: {e}", exc_info=True)
                    return jsonify({'suggestion': 'AI service unavailable. Please try again later.'}), 503
                except Exception as e:
                    logger.error(f"Unexpected error in provisional_diagnosis_suggest: {e}", exc_info=True)
                    return jsonify({'suggestion': ''}), 500





@app.route('/ai_suggestion/smart_goals/<field>', methods=['POST'])
@login_required()
def ai_smart_goals(field):
    data = request.get_json() or {}
    # combine all your saved inputs from localStorage
    prev = {
        **data.get('previous', {}),                 # add_patient_data
        **data.get('previous_subjective', {}),      # subjective_inputs
        **data.get('previous_perspectives', {}),    # perspectives_inputs
        **data.get('previous_assessments', {})      # initial_plan_inputs
    }
    text = data.get('input', '').strip()

    # field‑specific top‑level instructions
    prompts = {
        'patient_goal':      "Based on the patient’s entire record, suggest 2–3 patient‑centric SMART goals they could aim for.",
        'baseline_status':   "Given those goals and the patient context, what baseline status should I record? Describe the starting point.",
        'measurable_outcome':"What measurable outcomes would you expect for these goals? List 2–3 concrete metrics.",
        'time_duration':     "What realistic time duration (e.g. weeks or months) fits those outcomes given the patient's condition?"
    }
    # fallback if something else slips in
    base_prompt = prompts.get(field,
        f"You are a PHI‑safe physiotherapy assistant. Help with field '{field}'."
    )

    # *optional*—stitch in all prior screen data:
    context_lines = []
    for k, v in prev.items():
        if v:
            context_lines.append(f"- {k}: {v}")
    if context_lines:
        base_prompt += "\n\nPatient context:\n" + "\n".join(context_lines)

    # finally, tack on whatever free text the physio just entered:
    if text:
        base_prompt += f"\n\nCurrent input: {text}"

    try:
        suggestion = get_ai_suggestion(base_prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error'}), 500



# 13) Treatment Plan Suggestions
@app.route('/ai_suggestion/treatment_plan/<field>', methods=['POST'])
@login_required()
def treatment_plan_suggest(field):
    data       = request.get_json() or {}
    logger.info(f"🧠 [server] TreatmentPlan payload for patient {data.get('patient_id')}: {data}")
    text_input = data.get('input', '').strip()

    # field‑specific prompts
    prompts = {
        'treatment_plan': "Based on this patient’s case, outline 3‑4 evidence‑based interventions you would include in the treatment plan.",
        'goal_targeted':  "Given the treatment goals and patient context, what specific goal would you target first?",
        'reasoning':      "Explain the clinical reasoning that links the chosen interventions to the patient’s impairments.",
        'reference':      "Suggest 1‑2 key references (articles or guidelines) that support this plan."
    }

    prompt = prompts.get(field,
        f"For the field “{field}”, provide a brief suggestion based on the patient’s data."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        logger.info(f"🧠 [server] TreatmentPlan suggestion for “{field}”: {suggestion}")
        return jsonify({ 'field': field, 'suggestion': suggestion })
    except OpenAIError:
        return jsonify({ 'error': 'AI service unavailable. Please try again later.' }), 503
    except Exception:
        return jsonify({ 'error': 'An unexpected error occurred.' }), 500

@app.route('/ai_suggestion/treatment_plan_summary/<patient_id>')
@login_required()
def treatment_plan_summary(patient_id):
    """
    Gathers every saved screen for this patient and asks the AI to
    produce a concise treatment‑plan summary.
    """
    # 1) Load patient demographics
    pat_doc = db.collection('patients').document(patient_id).get()
    patient_info = pat_doc.to_dict() if pat_doc.exists else {}

    # Helper to fetch the latest entry from a collection
    def fetch_latest(collection_name):
        coll = db.collection(collection_name) \
                .where('patient_id', '==', patient_id) \
                .order_by('timestamp', direction=firestore.Query.DESCENDING) \
                .limit(1) \
                .get()
        return coll[0].to_dict() if coll else {}

    # 2) Pull in each screen’s data
    subj      = fetch_latest('subjective_examination')       # e.g. pain, history
    persp     = fetch_latest('subjective_perspectives')      # ICF beliefs
    assess    = fetch_latest('subjective_assessments')       # initial plan choices
    patho     = fetch_latest('pathophysiological_mechanism')
    chronic   = fetch_latest('chronic_disease_factors')
    flags     = fetch_latest('clinical_flags')
    objective = fetch_latest('objective_assessment')
    prov_dx   = fetch_latest('provisional_diagnosis')
    goals     = fetch_latest('smart_goals')
    tx_plan   = fetch_latest('treatment_plan')

    # 3) Build a single prompt that walks the AI through each section
    prompt = (
        "You are a PHI‑safe clinical summarization assistant.\n\n"
        f"Patient demographics: {patient_info.get('age_sex', 'N/A')}; "
        f"Sex: {patient_info.get('sex', 'N/A')}; "
        f"Past medical history: {patient_info.get('past_history', 'N/A')}.\n\n"

        "Subjective examination:\n"
        + "\n".join(f"- {k}: {v}" for k,v in subj.items() if k not in ('patient_id','timestamp')) 
        + "\n\n"

        "Patient perspectives (ICF model):\n"
        + "\n".join(f"- {k}: {v}" for k,v in persp.items() if k not in ('patient_id','timestamp'))
        + "\n\n"

        "Initial plan of assessment:\n"
        + "\n".join(f"- {k}: {v.get('choice')} (details: {v.get('details','')})"
                    for k,v in assess.items() if k not in ('patient_id','timestamp'))
        + "\n\n"

        "Pathophysiological mechanism:\n"
        + "\n".join(f"- {k}: {v}" for k,v in patho.items() if k not in ('patient_id','timestamp'))
        + "\n\n"

        "Chronic disease factors:\n"
        + f"- Maintenance causes: {chronic.get('maintenance_causes','')}\n"
        + f"- Specific factors: {chronic.get('specific_factors','')}\n\n"

        "Clinical flags:\n"
        + "\n".join(f"- {k}: {v}" for k,v in flags.items() if k not in ('patient_id','timestamp'))
        + "\n\n"

        "Objective assessment:\n"
        + "\n".join(f"- {k}: {v}" for k,v in objective.items() if k not in ('patient_id','timestamp'))
        + "\n\n"

        "Provisional diagnosis:\n"
        + "\n".join(f"- {k}: {v}" for k,v in prov_dx.items() if k not in ('patient_id','timestamp'))
        + "\n\n"

        "SMART goals:\n"
        + "\n".join(f"- {k}: {v}" for k,v in goals.items() if k not in ('patient_id','timestamp'))
        + "\n\n"

        "Finally, the treatment plan:\n"
        + "\n".join(f"- {k}: {v}" for k,v in tx_plan.items() if k not in ('patient_id','timestamp'))
        + "\n\n"

        "Using all of the above, create a **concise treatment‑plan summary** "
        "that links the patient’s history, exam findings, goals, and interventions into a coherent paragraph."
    )

    try:
        summary = get_ai_suggestion(prompt).strip()
        return jsonify({ 'summary': summary })
    except OpenAIError:
        return jsonify({ 'error': 'AI service unavailable. Please try again later.' }), 503
    except Exception:
        return jsonify({ 'error': 'An unexpected error occurred.' }), 500


@app.route('/ai/followup_suggestion/<patient_id>', methods=['POST'])
@login_required()
def ai_followup_suggestion(patient_id):
    # 1. Load patient record
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return jsonify({'error': 'Patient not found'}), 404
    patient = doc.to_dict()

    # 2. Parse the current form data
    data = request.get_json() or {}
    session_no    = data.get('session_number')
    session_date  = data.get('session_date')
    grade         = data.get('grade')
    perception    = data.get('perception')
    feedback      = data.get('feedback')

    # 3. Build a PHI‑safe summary including SMART Goals
    case_summary_lines = [
        f"Age/Sex: {patient.get('age_sex', 'N/A')}",
        f"History: {patient.get('chief_complaint', '')}",
        f"Subjective: {patient.get('subjective_notes', '')}",
        f"Perspectives: {patient.get('perspectives_summary', '')}",
        f"Initial Plan: {patient.get('initial_plan_summary', '')}",
        f"SMART Goals: {patient.get('smart_goals_summary', '')}"
    ]
    case_summary = "\n".join(line for line in case_summary_lines if line.split(": ",1)[1])

    # 4. Stitch into a single prompt
    prompt = (
        "You are a PHI‑safe clinical reasoning assistant for physiotherapy.\n\n"
        f"Patient ID: {patient_id}\n\n"
        "Case summary so far:\n"
        f"{case_summary}\n\n"
        "New follow‑up session details:\n"
        f" • Session #: {session_no} on {session_date}\n"
        f" • Grade: {grade}\n"
        f" • Perception: {perception}\n"
        f" • Feedback: {feedback}\n\n"
        "Based on ICF guidelines, the SMART Goals above, and the new session data, "
        "suggest a focussed plan for the next treatment."
    )

    # 5. Call the AI
    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error occurred.'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
