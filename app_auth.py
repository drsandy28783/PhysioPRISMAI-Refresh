"""
Firebase Authentication Module for Bearer Token Verification

This module provides Firebase Admin SDK initialization and a decorator
for protecting Flask routes with Firebase ID token authentication.

Usage:
    from app_auth import require_firebase_auth

    @app.route('/api/protected', methods=['POST'])
    @csrf.exempt
    @require_firebase_auth
    def protected_route():
        user_id = g.firebase_user['uid']
        user_email = g.firebase_user['email']
        # Your route logic here
"""

import os
import logging
import json
from functools import wraps
from flask import request, jsonify, g
import firebase_admin
from firebase_admin import auth, credentials
from firebase_admin.exceptions import FirebaseError
from azure_cosmos_db import get_cosmos_db

logger = logging.getLogger("app.auth")

# ─── FIREBASE ADMIN INITIALIZATION ──────────────────────────────────────
# Initialize Firebase Admin SDK using explicit credentials or Application Default Credentials
# Supports Azure deployments via GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable
# Get Firebase project ID from environment
FIREBASE_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('FIREBASE_PROJECT_ID') or 'physiologicprism-474610'

try:
    # Check if already initialized (avoid re-initialization)
    firebase_admin.get_app()
    logger.info("Firebase Admin SDK already initialized")
except ValueError:
    # Not initialized yet, so initialize now
    # Try to use explicit credentials from environment variable (required for Azure)
    sa_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON', '').strip()

    if sa_json:
        # Parse JSON credentials from environment variable
        try:
            cred_dict = json.loads(sa_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'projectId': cred_dict.get('project_id')})
            logger.info(f"Firebase Admin SDK initialized with explicit credentials for project {FIREBASE_PROJECT_ID}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
            raise ValueError("Invalid Firebase credentials JSON")
    else:
        # Fallback to Application Default Credentials (for local/GCP)
        logger.warning("No explicit Firebase credentials found. Using Application Default Credentials (may fail on Azure).")
        firebase_admin.initialize_app(options={
            'projectId': FIREBASE_PROJECT_ID
        })
        logger.info(f"Firebase Admin SDK initialized with ADC for project {FIREBASE_PROJECT_ID}")


# ─── FIREBASE ID TOKEN VERIFICATION ────────────────────────────────────
def verify_firebase_token(id_token):
    """
    Verify Firebase ID token and return decoded claims.

    Args:
        id_token: The Firebase ID token from the Authorization header

    Returns:
        dict: Decoded token claims containing uid, email, etc.

    Raises:
        FirebaseError: If token verification fails
    """
    # Verify the token with revocation check enabled
    decoded_token = auth.verify_id_token(id_token, check_revoked=True)

    # Validate issuer and audience for additional security
    expected_issuer = f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}"
    if decoded_token.get('iss') != expected_issuer:
        raise ValueError(f"Invalid token issuer. Expected {expected_issuer}")

    if decoded_token.get('aud') != FIREBASE_PROJECT_ID:
        raise ValueError(f"Invalid token audience. Expected {FIREBASE_PROJECT_ID}")

    return decoded_token


# ─── AUTHENTICATION DECORATOR ──────────────────────────────────────────
def require_firebase_auth(f):
    """
    Decorator to protect routes with Firebase ID token authentication.

    Expects Authorization header with format: "Bearer <id_token>"

    On success:
        - Attaches decoded token claims to flask.g.firebase_user
        - Contains: uid, email, email_verified, etc.

    On failure:
        - Returns 401 Unauthorized with generic error message
        - NEVER logs the token value

    Usage:
        @app.route('/api/protected', methods=['POST'])
        @csrf.exempt  # Apply csrf.exempt BEFORE this decorator
        @require_firebase_auth
        def protected_route():
            user_id = g.firebase_user['uid']
            return jsonify({'success': True})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract Authorization header
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            logger.warning("Missing Authorization header")
            return jsonify({'error': 'Authentication required'}), 401

        # Check for Bearer token format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            logger.warning("Invalid Authorization header format")
            return jsonify({'error': 'Invalid authentication format'}), 401

        id_token = parts[1]

        # IMPORTANT: Never log the token value
        # logger.debug(f"Token: {id_token}")  # NEVER DO THIS

        try:
            # Verify the token
            decoded_token = verify_firebase_token(id_token)

            # Attach user info to Flask's g object
            g.firebase_user = {
                'uid': decoded_token.get('uid'),
                'email': decoded_token.get('email'),
                'email_verified': decoded_token.get('email_verified', False),
                'name': decoded_token.get('name'),
                'picture': decoded_token.get('picture'),
                # Add any other claims you need
            }

            # Log successful authentication (without token details)
            logger.info(f"Authenticated user: {g.firebase_user['uid']}")

            # Call the original route function
            return f(*args, **kwargs)

        except auth.ExpiredIdTokenError:
            logger.warning("Expired token")
            return jsonify({'error': 'Token expired'}), 401

        except auth.RevokedIdTokenError:
            logger.warning("Revoked token")
            return jsonify({'error': 'Token revoked'}), 401

        except auth.InvalidIdTokenError:
            logger.warning("Invalid token")
            return jsonify({'error': 'Invalid token'}), 401

        except FirebaseError as e:
            logger.error(f"Firebase authentication error: {type(e).__name__}")
            return jsonify({'error': 'Authentication failed'}), 401

        except Exception as e:
            logger.error(f"Unexpected authentication error: {type(e).__name__}")
            return jsonify({'error': 'Authentication failed'}), 401

    return decorated_function


# ─── HYBRID AUTHENTICATION (Session + Bearer Token) ───────────────────────
def require_auth(f):
    """
    Hybrid authentication decorator supporting both:
    1. Firebase Bearer tokens (preferred, modern approach)
    2. Flask sessions (legacy, for backwards compatibility)

    Priority: Tries bearer token first, falls back to session.

    Attaches user info to flask.g.user with consistent structure:
    {
        'uid': str,           # Firebase UID or email for session-based
        'email': str,
        'name': str,
        'institute': str,
        'is_admin': int,
        'is_super_admin': int,
        'approved': int,
        'auth_method': 'bearer' | 'session'
    }

    Usage:
        @app.route('/api/endpoint')
        @require_auth
        def my_route():
            user_email = g.user['email']
            return jsonify({'success': True})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session, redirect

        # Try bearer token authentication first (modern approach)
        auth_header = request.headers.get('Authorization')

        if auth_header and auth_header.startswith('Bearer '):
            try:
                # Extract token
                parts = auth_header.split()
                if len(parts) == 2:
                    id_token = parts[1]

                    # Verify Firebase token
                    decoded_token = verify_firebase_token(id_token)

                    # Get user info from Firestore using Firebase UID
                    firebase_uid = decoded_token.get('uid')
                    firebase_email = decoded_token.get('email')

                    # Try to find user by Firebase UID first, then by email
                    db = get_cosmos_db()

                    user_doc = None
                    # Check if user document exists with firebase_uid field
                    users_with_uid = db.collection('users').where('firebase_uid', '==', firebase_uid).limit(1).stream()
                    for doc in users_with_uid:
                        user_doc = doc
                        break

                    # Fall back to email lookup
                    if not user_doc:
                        user_doc = db.collection('users').document(firebase_email).get()
                        if not user_doc.exists:
                            logger.warning(f"User not found in Cosmos DB for Firebase UID {firebase_uid}")
                            return jsonify({'error': 'User not found'}), 404

                    user_data = user_doc.to_dict()

                    # Check approval status
                    if user_data.get('is_super_admin', 0) != 1:
                        if user_data.get('approved', 0) != 1:
                            return jsonify({'error': 'Account pending approval'}), 403
                        if user_data.get('active', 1) != 1:
                            return jsonify({'error': 'Account deactivated'}), 403

                    # Attach user info to g object
                    g.user = {
                        'uid': firebase_uid,
                        'email': user_data.get('email') or firebase_email,
                        'name': user_data.get('name', decoded_token.get('name', '')),
                        'institute': user_data.get('institute', ''),
                        'is_admin': user_data.get('is_admin', 0),
                        'is_super_admin': user_data.get('is_super_admin', 0),
                        'approved': user_data.get('approved', 0),
                        'auth_method': 'bearer'
                    }

                    logger.info(f"Authenticated via bearer token: {g.user['email']}")
                    return f(*args, **kwargs)

            except auth.ExpiredIdTokenError:
                logger.warning("Expired bearer token, falling back to session")
            except auth.RevokedIdTokenError:
                logger.warning("Revoked bearer token")
                return jsonify({'error': 'Token revoked'}), 401
            except auth.InvalidIdTokenError:
                logger.warning("Invalid bearer token, falling back to session")
            except FirebaseError as e:
                logger.warning(f"Firebase error: {type(e).__name__}, falling back to session")
            except Exception as e:
                logger.warning(f"Bearer token auth failed: {type(e).__name__}, falling back to session")

        # Fall back to session-based authentication
        user_id = session.get('user_id')
        if not user_id:
            # API paths must always return 401 JSON — never redirect to login page.
            # HTML redirect is only appropriate for browser-facing web routes.
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect('/login') if request.accept_mimetypes.accept_html else (jsonify({'error': 'Authentication required'}), 401)

        # Validate session
        db = get_cosmos_db()
        user_doc = db.collection('users').document(user_id).get()

        if not user_doc.exists:
            session.clear()
            return redirect('/login') if request.accept_mimetypes.accept_html else (jsonify({'error': 'User not found'}), 404)

        user_data = user_doc.to_dict()

        # Check approval status (super admins bypass this)
        if user_data.get('is_super_admin', 0) != 1:
            if user_data.get('approved', 0) != 1:
                return "Account pending approval" if request.accept_mimetypes.accept_html else (jsonify({'error': 'Account pending approval'}), 403)
            if user_data.get('active', 1) != 1:
                return "Account deactivated" if request.accept_mimetypes.accept_html else (jsonify({'error': 'Account deactivated'}), 403)

        # Attach user info to g object (same structure as bearer token auth)
        g.user = {
            'uid': user_id,
            'email': user_id,  # For session auth, user_id is the email
            'name': session.get('user_name', user_data.get('name', '')),
            'institute': session.get('institute', user_data.get('institute', '')),
            'is_admin': session.get('is_admin', user_data.get('is_admin', 0)),
            'is_super_admin': session.get('is_super_admin', user_data.get('is_super_admin', 0)),
            'approved': user_data.get('approved', 0),
            'auth_method': 'session'
        }

        logger.debug(f"Authenticated via session: {g.user['email']}")
        return f(*args, **kwargs)

    return decorated_function
