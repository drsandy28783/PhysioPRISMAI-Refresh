"""
Quota Enforcement Middleware for PhysiologicPRISM
==================================================

This module provides decorators to enforce subscription quotas on:
- Patient creation
- AI feature usage

Usage:
    @require_patient_quota
    def add_patient():
        ...

    @require_ai_quota
    def ai_diagnosis():
        ...
"""

import logging
from functools import wraps
from flask import jsonify, g, request
from subscription_manager import (
    check_patient_limit,
    check_voice_limit,
    deduct_patient_usage,
    reserve_ai_usage_atomic,
    release_ai_usage_atomic,
    log_ai_usage,
    deduct_voice_usage,
    get_user_subscription,
    increment_patient_usage_atomic,
    decrement_patient_usage_atomic
)

logger = logging.getLogger("app.quota_middleware")


def _peek_ai_quota(user_id):
    """
    Non-mutating, advisory AI quota check for GET requests that never
    deduct quota (e.g. treatment_plan_summary). No reservation needed since
    there's no write to race on.
    """
    subscription = get_user_subscription(user_id)
    if subscription.get('status') != 'active':
        return False, "Your subscription has expired. Please upgrade to continue using AI features."

    ai_calls_limit = subscription.get('ai_calls_limit', 0)
    ai_calls_used = subscription.get('ai_calls_this_month', 0)
    ai_tokens = subscription.get('ai_tokens_balance', 0)

    if ai_calls_limit == -1 or ai_calls_used < ai_calls_limit or ai_tokens > 0:
        return True, ""

    return False, f"AI quota exhausted ({ai_calls_limit} calls). Purchase tokens or upgrade your plan."


def require_patient_quota(f):
    """
    Decorator to check patient creation quota before executing function.
    Uses atomic increment to prevent race conditions.

    Usage:
        @app.route('/add_patient')
        @require_auth
        @require_patient_quota
        def add_patient():
            # Patient creation logic
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get user ID from g.firebase_user (Firebase auth) or g.user (session auth)
            user_data = getattr(g, 'firebase_user', None) or getattr(g, 'user', None)
            if not user_data:
                return jsonify({'error': 'User not authenticated'}), 401

            user_id = user_data.get('email') or user_data.get('uid')
            if not user_id:
                return jsonify({'error': 'User not authenticated'}), 401

            # Only enforce quota for POST requests (actual creation, not viewing form)
            from flask import request
            if request.method != 'POST':
                # GET request - just render form, no quota check
                return f(*args, **kwargs)

            # ATOMIC INCREMENT: Increment counter FIRST (pessimistic locking)
            # This prevents race conditions where multiple requests check at same time
            success, new_count, error_message = increment_patient_usage_atomic(user_id)

            if not success:
                logger.warning(f"Patient quota check failed for {user_id}: {error_message}")
                return jsonify({
                    'error': 'Quota exceeded',
                    'message': error_message,
                    'quota_type': 'patients',
                    'action_required': 'upgrade'
                }), 403

            # Quota incremented successfully - proceed with patient creation
            try:
                result = f(*args, **kwargs)

                # Check if the response indicates success
                if isinstance(result, tuple):
                    response, status_code = result[0], result[1] if len(result) > 1 else 200
                else:
                    response, status_code = result, 200

                # If creation failed (4xx or 5xx status), rollback the quota
                if status_code >= 400:
                    logger.warning(f"Patient creation failed (status {status_code}), rolling back quota for {user_id}")
                    decrement_patient_usage_atomic(user_id)

                return result

            except Exception as e:
                # Patient creation failed - rollback the quota increment
                logger.error(f"Patient creation exception for {user_id}, rolling back quota: {e}")
                decrement_patient_usage_atomic(user_id)
                raise

        except Exception as e:
            logger.error(f"Error in patient quota middleware: {e}")
            return jsonify({'error': 'Quota check failed'}), 500

    return decorated_function


def require_ai_quota(f):
    """
    Decorator to check AI usage quota before executing function.

    Usage:
        @app.route('/ai_suggestion/diagnosis')
        @require_auth
        @require_ai_quota
        def ai_diagnosis():
            # AI logic
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get user ID from g.firebase_user (Firebase auth) or g.user (session auth)
            user_data = getattr(g, 'firebase_user', None) or getattr(g, 'user', None)
            if not user_data:
                return jsonify({'error': 'User not authenticated'}), 401

            user_id = user_data.get('email') or user_data.get('uid')
            if not user_id:
                return jsonify({'error': 'User not authenticated'}), 401

            # GET requests (e.g. treatment_plan_summary) never deduct quota,
            # same as before -- just an advisory, non-mutating check.
            if request.method != 'POST':
                can_use_ai, message = _peek_ai_quota(user_id)
                if not can_use_ai:
                    logger.warning(f"AI quota exceeded for {user_id}: {message}")
                    return jsonify({
                        'error': 'Quota exceeded',
                        'message': message,
                        'quota_type': 'ai_calls',
                        'action_required': 'upgrade_or_buy_tokens'
                    }), 403
                return f(*args, **kwargs)

            # ATOMIC RESERVATION: reserve quota/token FIRST (pessimistic
            # locking) so two concurrent requests can't both read the same
            # pre-increment count and both pass. Released below if the
            # request turns out to be a cache hit or fails.
            reserved, will_use_token, message = reserve_ai_usage_atomic(user_id)

            if not reserved:
                logger.warning(f"AI quota exceeded for {user_id}: {message}")
                return jsonify({
                    'error': 'Quota exceeded',
                    'message': message,
                    'quota_type': 'ai_calls',
                    'action_required': 'upgrade_or_buy_tokens'
                }), 403

            # Store whether we used a token
            g.use_ai_token = will_use_token

            try:
                result = f(*args, **kwargs)
            except Exception:
                release_ai_usage_atomic(user_id, will_use_token)
                raise

            # Check if the response indicates success
            if isinstance(result, tuple):
                response, status_code = result[0], result[1] if len(result) > 1 else 200
            else:
                response, status_code = result, 200

            cache_hit = getattr(g, 'cache_hit', False)

            if not (200 <= status_code < 300):
                # Request failed -- release the reservation
                release_ai_usage_atomic(user_id, will_use_token)
            elif cache_hit:
                # Cache hits are free -- release the reservation
                release_ai_usage_atomic(user_id, will_use_token)
                logger.info(f"AI cache hit for {user_id} - quota reservation released")
            else:
                log_ai_usage(user_id, used_token=will_use_token, cache_hit=False)
                if will_use_token:
                    logger.info(f"Used 1 AI token for {user_id}")
                else:
                    logger.info(f"Deducted AI quota for {user_id}")

            return result

        except Exception as e:
            logger.error(f"Error in AI quota middleware: {e}")
            return jsonify({'error': 'Quota check failed'}), 500

    return decorated_function


def require_voice_quota(f):
    """
    Decorator to check voice typing quota before executing function.

    Usage:
        @app.route('/api/transcribe')
        @require_auth
        @require_voice_quota
        def api_transcribe_audio():
            # Voice transcription logic
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get user ID from g.firebase_user (Firebase auth) or g.user (session auth)
            user_data = getattr(g, 'firebase_user', None) or getattr(g, 'user', None)
            if not user_data:
                return jsonify({'error': 'User not authenticated'}), 401

            user_id = user_data.get('email') or user_data.get('uid')
            if not user_id:
                return jsonify({'error': 'User not authenticated'}), 401

            # Check voice quota
            can_use_voice, message = check_voice_limit(user_id)

            if not can_use_voice:
                logger.warning(f"Voice typing quota exceeded for {user_id}: {message}")
                return jsonify({
                    'error': 'Quota exceeded',
                    'message': message,
                    'quota_type': 'voice_minutes',
                    'action_required': 'upgrade'
                }), 403

            # Execute the function
            result = f(*args, **kwargs)

            # Check if the response indicates success
            if isinstance(result, tuple):
                response, status_code = result[0], result[1] if len(result) > 1 else 200
            else:
                response, status_code = result, 200

            # Only deduct if request was successful (2xx status)
            if 200 <= status_code < 300:
                # Get duration from response if available
                duration_seconds = 0
                if hasattr(response, 'get_json'):
                    data = response.get_json()
                    if isinstance(data, dict):
                        duration_seconds = data.get('duration', 0)

                # Store duration in g for deduction
                if hasattr(g, 'voice_duration_seconds'):
                    duration_seconds = g.voice_duration_seconds

                # Deduct voice usage
                if duration_seconds > 0:
                    deduct_voice_usage(user_id, duration_seconds)
                    logger.info(f"Deducted voice typing usage for {user_id}: {duration_seconds:.1f}s")

            return result

        except Exception as e:
            import traceback
            logger.error(f"Error in voice quota middleware: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'error': 'Quota check failed',
                'message': str(e),
                'details': 'Voice transcription quota check failed. Please contact support if this persists.'
            }), 500

    return decorated_function


def check_subscription_status(f):
    """
    Decorator to check subscription status (active/expired) before executing function.
    Less strict than quota checks - just verifies user has an active subscription.

    Usage:
        @app.route('/premium_feature')
        @require_auth
        @check_subscription_status
        def premium_feature():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get user ID from g.firebase_user (Firebase auth) or g.user (session auth)
            user_data = getattr(g, 'firebase_user', None) or getattr(g, 'user', None)
            if not user_data:
                return jsonify({'error': 'User not authenticated'}), 401

            user_id = user_data.get('email') or user_data.get('uid')
            if not user_id:
                return jsonify({'error': 'User not authenticated'}), 401

            # Get subscription
            subscription = get_user_subscription(user_id)

            # Check if active
            if subscription.get('status') != 'active':
                return jsonify({
                    'error': 'Subscription required',
                    'message': 'This feature requires an active subscription',
                    'action_required': 'subscribe'
                }), 403

            return f(*args, **kwargs)

        except Exception as e:
            logger.error(f"Error in subscription status check: {e}")
            return jsonify({'error': 'Subscription check failed'}), 500

    return decorated_function


def add_usage_info_to_response(f):
    """
    Decorator to add usage/quota information to API responses.
    Useful for mobile apps to display quota status.

    Usage:
        @app.route('/api/patients')
        @require_auth
        @add_usage_info_to_response
        def get_patients():
            return jsonify({'patients': [...]})

        # Response will include:
        # {
        #     'patients': [...],
        #     'quota_info': {
        #         'patients_used': 3,
        #         'patients_limit': 10,
        #         'ai_calls_used': 15,
        #         'ai_calls_limit': 100,
        #         'tokens_balance': 50
        #     }
        # }
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Execute the function outside the try -- if f() itself raises, let
        # it propagate normally instead of falling into the except below,
        # which previously referenced `result` before it was ever assigned
        # (UnboundLocalError), masking the real error.
        result = f(*args, **kwargs)

        try:
            # Get user ID
            user_id = g.user.get('email') or g.user.get('uid')

            if not user_id:
                return result

            # Get subscription
            from subscription_manager import get_usage_stats
            usage_stats = get_usage_stats(user_id)

            # Modify response to include quota info
            if isinstance(result, tuple):
                response, status_code = result[0], result[1] if len(result) > 1 else 200

                # If response is JSON, add quota_info
                if hasattr(response, 'get_json'):
                    data = response.get_json()
                    if isinstance(data, dict):
                        data['quota_info'] = usage_stats
                        return jsonify(data), status_code

            return result

        except Exception as e:
            logger.error(f"Error adding usage info to response: {e}")
            # Return original response if error
            return result

    return decorated_function
