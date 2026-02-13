"""
Redis-based Rate Limiting for PhysiologicPRISM

This module provides persistent, distributed rate limiting using Redis.
Falls back to in-memory rate limiting if Redis is unavailable.

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

# Redis Configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
REDIS_DB = int(os.environ.get('REDIS_DB', 0))

# Rate Limiting Configuration
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes in seconds

# Try to connect to Redis
redis_client = None
redis_available = False

try:
    import redis

    # Create Redis client
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD if REDIS_PASSWORD else None,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True
    )

    # Test connection
    redis_client.ping()
    redis_available = True
    logger.info(f"✅ Redis connected successfully at {REDIS_HOST}:{REDIS_PORT}")

except ImportError:
    logger.warning("⚠️ Redis package not installed. Using in-memory rate limiting.")
    redis_available = False

except Exception as e:
    logger.warning(f"⚠️ Redis connection failed: {str(e)}. Using in-memory rate limiting.")
    redis_available = False
    redis_client = None


# In-memory fallback (only used if Redis unavailable)
_in_memory_storage = {}


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


def get_storage_uri():
    """
    Get storage URI for Flask-Limiter.

    Returns:
        str: Redis URI if available, otherwise in-memory URI
    """
    if redis_available and redis_client:
        # Build Redis URI
        if REDIS_PASSWORD:
            return f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
        else:
            return f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    else:
        return "memory://"


# Initialize Flask-Limiter
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["1000 per hour", "100 per minute"],
    storage_uri=get_storage_uri(),
    storage_options={},
    strategy="fixed-window",
    headers_enabled=True,
    swallow_errors=True  # Don't crash app if rate limiting fails
)

logger.info(f"Rate limiter initialized with storage: {'Redis' if redis_available else 'Memory'}")


# ─── LOGIN ATTEMPT TRACKING ─────────────────────────────────────────


def check_login_attempts(email):
    """
    Check if user is locked out due to failed login attempts.

    Args:
        email (str): User email address

    Returns:
        tuple: (is_allowed, remaining_lockout_seconds)
            - is_allowed: True if user can attempt login, False if locked out
            - remaining_lockout_seconds: Seconds remaining in lockout (0 if not locked)
    """
    if not email:
        return True, 0

    key = f"login_attempts:{email.lower()}"

    if redis_available and redis_client:
        try:
            # Get attempt count from Redis
            attempts = redis_client.get(key)

            if attempts and int(attempts) >= MAX_LOGIN_ATTEMPTS:
                # Check TTL (time remaining)
                ttl = redis_client.ttl(key)
                if ttl > 0:
                    logger.warning(f"User {email} is locked out. {ttl}s remaining.")
                    return False, ttl

            return True, 0

        except Exception as e:
            logger.error(f"Redis error checking login attempts: {str(e)}")
            # Fail open - allow login if Redis fails
            return True, 0

    else:
        # In-memory fallback
        import time
        if key in _in_memory_storage:
            attempts, timestamp = _in_memory_storage[key]

            # Check if lockout expired
            elapsed = time.time() - timestamp
            if elapsed < LOCKOUT_DURATION:
                if attempts >= MAX_LOGIN_ATTEMPTS:
                    remaining = int(LOCKOUT_DURATION - elapsed)
                    logger.warning(f"User {email} is locked out. {remaining}s remaining.")
                    return False, remaining
            else:
                # Lockout expired, clear it
                del _in_memory_storage[key]

        return True, 0


def record_failed_login(email):
    """
    Record a failed login attempt.

    Args:
        email (str): User email address
    """
    if not email:
        return

    key = f"login_attempts:{email.lower()}"

    if redis_available and redis_client:
        try:
            # Increment attempt count
            attempts = redis_client.incr(key)

            # Set expiry on first attempt
            if attempts == 1:
                redis_client.expire(key, LOCKOUT_DURATION)

            logger.info(f"Failed login attempt {attempts}/{MAX_LOGIN_ATTEMPTS} for {email}")

        except Exception as e:
            logger.error(f"Redis error recording failed login: {str(e)}")

    else:
        # In-memory fallback
        import time
        if key in _in_memory_storage:
            attempts, timestamp = _in_memory_storage[key]

            # Check if lockout expired
            elapsed = time.time() - timestamp
            if elapsed >= LOCKOUT_DURATION:
                # Reset counter
                _in_memory_storage[key] = (1, time.time())
            else:
                # Increment counter
                _in_memory_storage[key] = (attempts + 1, timestamp)
        else:
            # First attempt
            _in_memory_storage[key] = (1, time.time())

        attempts = _in_memory_storage[key][0]
        logger.info(f"Failed login attempt {attempts}/{MAX_LOGIN_ATTEMPTS} for {email}")


def clear_login_attempts(email):
    """
    Clear failed login attempts (called after successful login).

    Args:
        email (str): User email address
    """
    if not email:
        return

    key = f"login_attempts:{email.lower()}"

    if redis_available and redis_client:
        try:
            redis_client.delete(key)
            logger.info(f"Cleared login attempts for {email}")
        except Exception as e:
            logger.error(f"Redis error clearing login attempts: {str(e)}")

    else:
        # In-memory fallback
        if key in _in_memory_storage:
            del _in_memory_storage[key]
            logger.info(f"Cleared login attempts for {email}")


def get_rate_limit_stats():
    """
    Get rate limiting statistics (for debugging/monitoring).

    Returns:
        dict: Rate limiting statistics
    """
    stats = {
        'redis_available': redis_available,
        'storage_type': 'redis' if redis_available else 'memory',
        'redis_host': REDIS_HOST if redis_available else None,
        'redis_port': REDIS_PORT if redis_available else None,
    }

    if redis_available and redis_client:
        try:
            info = redis_client.info('stats')
            stats['redis_total_connections'] = info.get('total_connections_received', 0)
            stats['redis_connected_clients'] = info.get('connected_clients', 0)
        except Exception as e:
            stats['redis_error'] = str(e)

    return stats


# Health check function
def health_check():
    """
    Check if rate limiter is healthy.

    Returns:
        tuple: (is_healthy, status_message)
    """
    if redis_available and redis_client:
        try:
            redis_client.ping()
            return True, "Redis connection healthy"
        except Exception as e:
            return False, f"Redis connection unhealthy: {str(e)}"
    else:
        return True, "Using in-memory rate limiting (Redis not available)"
