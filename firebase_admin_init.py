# firebase_admin_init.py
import os, json, base64
import firebase_admin
from firebase_admin import credentials, firestore

def _load_cred():
    # Your common JSON-in-env names (checks in this order)
    for key in [
        "GOOGLE_APPLICATION_CREDENTIALS_JSON",  # recommended
        "FIREBASE_SERVICE_ACCOUNT_JSON",        # also OK
        "FIREBASE_CREDENTIALS",                 # if you used this name earlier
    ]:
        raw = os.getenv(key)
        if raw:
            return credentials.Certificate(json.loads(raw))

    # Base64-encoded JSON variant (optional)
    b64 = os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64")
    if b64:
        return credentials.Certificate(json.loads(base64.b64decode(b64).decode("utf-8")))

    # File path variants (only if you actually mount a file)
    path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    if path and os.path.exists(path):
        return credentials.Certificate(path)

    # ADC (uses GOOGLE_APPLICATION_CREDENTIALS file path)
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return credentials.ApplicationDefault()

    raise RuntimeError(
        "No Firebase credentials found. Set one of: "
        "GOOGLE_APPLICATION_CREDENTIALS_JSON, FIREBASE_SERVICE_ACCOUNT_JSON, "
        "FIREBASE_CREDENTIALS, FIREBASE_SERVICE_ACCOUNT_BASE64, "
        "FIREBASE_SERVICE_ACCOUNT_PATH, or GOOGLE_APPLICATION_CREDENTIALS."
    )

if not firebase_admin._apps:
    cred = _load_cred()
    firebase_admin.initialize_app(cred)

db = firestore.client()
