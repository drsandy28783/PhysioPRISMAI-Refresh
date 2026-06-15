"""
Rate Limiting for PhysiologicPRISM

Route-level rate limiting via Flask-Limiter (in-memory).
Login attempt tracking is persisted in Cosmos DB so lockouts survive
restarts and are shared across all Gunicorn workers.

Usage:
    from rate_limiter import limiter, check_login_attempts, record_failed_login

    # Apply to routes
    @app.route('/api/endpoint')
    @limiter.limit("100 per minute")
    def endpoint():
        pass
"""

import os
import logging
from flask import g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger("app.rate_limiter")

# Login attempt tracking — state lives in Cosmos DB user documents
MAX_LOGIN_ATTEMPTS = 3

# Redis stubs kept for import compatibility (health check in main.py references these)
redis_client = None
redis_available = False


def get_user_identifier():
    """
    Get unique identifier for rate limiting.

    Returns:
        str: User identifier (Firebase UID, email, or IP address)
    """
    # Priority 1: Firebase UID
    if hasattr(g, 'firebase_user') and g.firebase_user:
        return f"user:{g.firebase_user.get('uid', 'unknown')}"

    # Priority 2: Session email
    if hasattr(g, 'user') and g.user:
        return f"user:{g.user.get('email', 'unknown')}"

    # Priority 3: IP address
    return f"ip:{get_remote_address()}"


# Initialize Flask-Limiter with in-memory storage (route-level throttling only)
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["1000 per hour", "100 per minute"],
    storage_uri="memory://",
    storage_options={},
    strategy="fixed-window",
    headers_enabled=True,
    swallow_errors=True,
)

logger.info("Rate limiter initialized with in-memory storage (login lockouts use Cosmos DB)")


# ─── LOGIN ATTEMPT TRACKING (Cosmos DB) ─────────────────────────────
#
# Lockout state is stored on the user document so it survives restarts
# and is visible to all Gunicorn workers.
#
# Fields written: failed_login_attempts (int), account_locked (bool)


def check_login_attempts(email, db=None):
    """
    Return (is_allowed, 0).  is_allowed is False when the account is locked.
    db is the Cosmos DB client (db.collection('users').document(...)).
    """
    if not email:
        return True, 0
    if db is None:
        return True, 0

    try:
        doc = db.collection('users').document(email.lower()).get()
        if doc.exists and doc.get('account_locked'):
            logger.warning(f"Login blocked — account locked: {email}")
            return False, 0
    except Exception as e:
        logger.error(f"check_login_attempts error for {email}: {e}")
        # Fail open so a Cosmos DB hiccup doesn't lock everyone out
    return True, 0


def record_failed_login(email, db=None) -> bool:
    """
    Increment failed_login_attempts on the user document.
    Sets account_locked=True when the count reaches MAX_LOGIN_ATTEMPTS.
    Returns True only on the attempt that just crossed the threshold
    (so callers send the reset email exactly once).
    """
    if not email:
        return False
    if db is None:
        return False

    try:
        ref = db.collection('users').document(email.lower())
        doc = ref.get()
        if not doc.exists:
            return False

        current = doc.get('failed_login_attempts') or 0
        new_count = current + 1
        just_locked = new_count == MAX_LOGIN_ATTEMPTS

        update = {'failed_login_attempts': new_count}
        if just_locked:
            update['account_locked'] = True

        ref.update(update)
        logger.info(f"Failed login attempt {new_count}/{MAX_LOGIN_ATTEMPTS} for {email}")
        return just_locked

    except Exception as e:
        logger.error(f"record_failed_login error for {email}: {e}")
        return False


def clear_login_attempts(email, db=None):
    """
    Clear the lockout state after a successful login or password reset.
    """
    if not email:
        return
    if db is None:
        return

    try:
        db.collection('users').document(email.lower()).update({
            'failed_login_attempts': 0,
            'account_locked': False,
        })
        logger.info(f"Cleared login lockout for {email}")
    except Exception as e:
        logger.error(f"clear_login_attempts error for {email}: {e}")


def get_rate_limit_stats():
    return {
        'redis_available': False,
        'storage_type': 'cosmos_db',
        'login_lockout_backend': 'cosmos_db',
    }


def health_check():
    return True, "Rate limiter healthy (in-memory routes, Cosmos DB login lockouts)"
