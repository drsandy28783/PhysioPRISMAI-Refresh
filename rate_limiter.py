"""
Rate Limiting for PhysiologicPRISM

Route-level rate limiting via Flask-Limiter, backed by Redis when
REDIS_HOST is configured (shared limits across all Gunicorn workers),
falling back to in-memory storage otherwise (per-worker limits only --
up to 3x looser than configured under 3 gthread workers).
Login attempt tracking is persisted in Cosmos DB so lockouts survive
restarts and are shared across all Gunicorn workers regardless of the
rate limiter's storage backend.

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
import redis

logger = logging.getLogger("app.rate_limiter")

# Login attempt tracking — state lives in Cosmos DB user documents
MAX_LOGIN_ATTEMPTS = 3

# Connect to Redis when configured, so rate limits are shared across all
# Gunicorn workers instead of each worker enforcing its own independent
# in-memory counter. Falls back to in-memory storage if REDIS_HOST is
# unset or unreachable.
redis_client = None
redis_available = False
_storage_uri = "memory://"

_REDIS_HOST = os.environ.get('REDIS_HOST')
if _REDIS_HOST:
    _redis_port = os.environ.get('REDIS_PORT', '6379')
    _redis_password = os.environ.get('REDIS_PASSWORD', '')
    _redis_db = os.environ.get('REDIS_DB', '0')
    _redis_ssl = os.environ.get('REDIS_SSL', 'false').lower() == 'true'
    _scheme = 'rediss' if _redis_ssl else 'redis'
    _auth = f':{_redis_password}@' if _redis_password else ''
    _redis_uri = f'{_scheme}://{_auth}{_REDIS_HOST}:{_redis_port}/{_redis_db}'

    try:
        _test_client = redis.from_url(_redis_uri, socket_connect_timeout=2)
        _test_client.ping()
        redis_client = _test_client
        redis_available = True
        _storage_uri = _redis_uri
        logger.info(f"Rate limiter using Redis storage at {_REDIS_HOST}:{_redis_port}")
    except Exception as e:
        logger.warning(f"Redis configured but unreachable ({e}) -- falling back to in-memory rate limiting")


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


# Initialize Flask-Limiter with Redis storage when available, else in-memory
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["1000 per hour", "100 per minute"],
    storage_uri=_storage_uri,
    storage_options={},
    strategy="fixed-window",
    headers_enabled=True,
    swallow_errors=True,
)

_backend = "Redis" if redis_available else "in-memory"
logger.info(f"Rate limiter initialized with {_backend} storage (login lockouts use Cosmos DB)")


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

        # Atomic increment closes the race where concurrent failed attempts
        # all read the same pre-increment count and undercount the total,
        # letting brute force exceed MAX_LOGIN_ATTEMPTS.
        applied, new_count = ref.increment_if('failed_login_attempts', 1)
        if not applied:
            return False

        just_locked = new_count == MAX_LOGIN_ATTEMPTS
        if new_count >= MAX_LOGIN_ATTEMPTS:
            ref.update({'account_locked': True})

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
        'redis_available': redis_available,
        'storage_type': 'redis' if redis_available else 'memory',
        'login_lockout_backend': 'cosmos_db',
    }


def health_check():
    backend = "Redis" if redis_available else "in-memory"
    return True, f"Rate limiter healthy ({backend} routes, Cosmos DB login lockouts)"
