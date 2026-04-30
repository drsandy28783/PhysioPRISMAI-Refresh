# Flask Dual Auth — Session Cookies (Web) + Bearer Tokens (Mobile)

The web app uses Flask session cookies set at login.
The mobile app must use Firebase ID tokens sent as Bearer headers.
Both must work on the same Flask routes without breaking each other.

---

## The Problem

Flask's `@login_required` (or equivalent decorator) typically only checks `session['user_id']`.
Mobile apps can't use cookies the same way — they send a Firebase Bearer token instead.
Without dual-auth support, **every mobile API call returns 401**.

---

## Solution: Dual Auth Decorator

Replace or augment your existing `@login_required` with this:

```python
# auth_utils.py
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from functools import wraps
from flask import request, session, jsonify, g
import os

# Initialize Firebase Admin SDK (do this once at app startup)
def init_firebase_admin():
    if not firebase_admin._apps:
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
            "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
            "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
            "token_uri": "https://oauth2.googleapis.com/token",
        })
        firebase_admin.initialize_app(cred)


def login_required_dual(f):
    """
    Decorator that accepts EITHER:
    - Flask session cookie (web app)
    - Firebase Bearer token (mobile app)
    Sets g.user_id and g.user_email for use in route.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # --- Method 1: Flask session (web) ---
        if 'user_id' in session:
            g.user_id = session['user_id']
            g.user_email = session.get('user_email', '')
            g.auth_method = 'session'
            return f(*args, **kwargs)

        # --- Method 2: Firebase Bearer token (mobile) ---
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
            try:
                decoded = firebase_auth.verify_id_token(token)
                g.user_id = decoded['uid']
                g.user_email = decoded.get('email', '')
                g.auth_method = 'bearer'
                return f(*args, **kwargs)
            except firebase_auth.ExpiredIdTokenError:
                return jsonify({"error": "Token expired", "code": "TOKEN_EXPIRED"}), 401
            except firebase_auth.InvalidIdTokenError:
                return jsonify({"error": "Invalid token", "code": "INVALID_TOKEN"}), 401
            except Exception as e:
                return jsonify({"error": f"Auth error: {str(e)}"}), 401

        # --- No valid auth found ---
        # Return JSON for mobile (not a redirect)
        if request.headers.get('Accept', '').startswith('application/json') or \
           request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "Authentication required", "code": "UNAUTHENTICATED"}), 401
        
        # Redirect for web browser
        from flask import redirect, url_for
        return redirect(url_for('login'))

    return decorated_function
```

---

## Apply to Existing Routes

```python
# app.py — replace @login_required with @login_required_dual on all API routes
from auth_utils import login_required_dual, init_firebase_admin

# Initialize at startup
init_firebase_admin()

# Before (web only):
@app.route('/api/ai/subjective-suggestions', methods=['POST'])
@login_required
def ai_subjective():
    user_id = session['user_id']
    ...

# After (web + mobile):
@app.route('/api/ai/subjective-suggestions', methods=['POST'])
@login_required_dual
def ai_subjective():
    user_id = g.user_id  # Works for both session and Bearer auth
    ...
```

---

## Mobile App Side — Attach Token to Every Request

```js
// src/services/api.js
import { getAuth } from 'firebase/auth';

const getAuthHeaders = async () => {
  const auth = getAuth();
  const user = auth.currentUser;
  if (!user) throw new Error('Not authenticated');
  
  const token = await user.getIdToken(/* forceRefresh= */ false);
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };
};

export const apiPost = async (path, body) => {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
  
  if (response.status === 401) {
    // Token may be expired — force refresh and retry once
    const auth = getAuth();
    const newToken = await auth.currentUser.getIdToken(true);
    headers['Authorization'] = `Bearer ${newToken}`;
    return fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
  }
  
  return response;
};

export const apiGet = async (path) => {
  const headers = await getAuthHeaders();
  return fetch(`${API_BASE_URL}${path}`, { method: 'GET', headers });
};
```

---

## CORS — Add Mobile Origins

```python
# app.py
from flask_cors import CORS

CORS(app, supports_credentials=True, origins=[
    # Web app
    "https://physiologicprism.com",
    "https://physiologicprism.web.app",
    "https://physiologicprism.firebaseapp.com",
    
    # Mobile app (React Native / Expo production)
    "capacitor://localhost",
    "ionic://localhost",
    "http://localhost",          # Android emulator
    "http://localhost:8081",     # Metro bundler
    "http://localhost:19000",    # Expo dev tools
    
    # Development
    "http://127.0.0.1:5000",
])
```

Also add to all API responses:
```python
@app.after_request
def add_cors_headers(response):
    # Mobile apps need explicit headers on every response including errors
    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    return response
```

---

## Firebase Admin SDK Setup in Azure

Store these in Azure Container Apps environment variables (never commit):

```
FIREBASE_PROJECT_ID=physiologicprism
FIREBASE_PRIVATE_KEY_ID=abc123...
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxx@physiologicprism.iam.gserviceaccount.com
```

Get from: Firebase Console → Project Settings → Service Accounts → Generate new private key.

---

## Debugging Auth Issues

```python
# Add this temporarily to any failing route to diagnose:
@app.route('/api/debug/auth', methods=['GET'])
def debug_auth():
    return jsonify({
        "has_session": 'user_id' in session,
        "session_user": session.get('user_id'),
        "has_auth_header": 'Authorization' in request.headers,
        "auth_header_prefix": request.headers.get('Authorization', '')[:20],
        "origin": request.headers.get('Origin'),
        "accept": request.headers.get('Accept'),
    })
```

Call `/api/debug/auth` from the mobile app to verify headers are reaching Flask correctly.
