# firebase_admin_init.py
import os, json, base64
import firebase_admin
from firebase_admin import credentials, firestore

def _load_cred():
    # 1) JSON string in env (good for Render/Cloud Run secrets)
    raw_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if raw_json:
        try:
            data = json.loads(raw_json)
            return credentials.Certificate(data)
        except Exception:
            pass

    # 2) Base64-encoded JSON in env (avoids multiline issues)
    b64 = os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64")
    if b64:
        data = json.loads(base64.b64decode(b64).decode("utf-8"))
        return credentials.Certificate(data)

    # 3) Path to JSON file
    path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    if path and os.path.exists(path):
        return credentials.Certificate(path)

    # 4) Application Default Credentials (Cloud Run / gcloud auth)
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return credentials.ApplicationDefault()

    raise RuntimeError(
        "No Firebase credentials found. "
        "Set one of: FIREBASE_SERVICE_ACCOUNT_JSON, FIREBASE_SERVICE_ACCOUNT_BASE64, "
        "FIREBASE_SERVICE_ACCOUNT_PATH, or GOOGLE_APPLICATION_CREDENTIALS."
    )

if not firebase_admin._apps:
    cred = _load_cred()
    firebase_admin.initialize_app(cred)

db = firestore.client()
def get_firestore_client():
    """Returns the Firestore client."""
    return db