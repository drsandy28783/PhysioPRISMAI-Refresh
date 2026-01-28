"""
Mobile API Endpoints for PhysiologicPRISM
==========================================

This module provides REST API endpoints for the mobile app.
All endpoints use Firebase Bearer token authentication and return JSON responses.

These endpoints wrap the existing web app functionality to provide mobile compatibility
without breaking the existing web interface.
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from azure_cosmos_db import get_cosmos_db, SERVER_TIMESTAMP
from app_auth import require_firebase_auth, require_auth
from firebase_admin import auth
from functools import wraps
from rate_limiter import redis_client, redis_available
from email_service import (
    send_registration_notification,
    send_approval_notification,
    send_institute_admin_registration_notification,
    send_institute_staff_registration_notification,
    send_institute_staff_approval_notification
)

logger = logging.getLogger("app.mobile_api")

# Terms of Service Version - Keep in sync with main.py
TOS_VERSION = '1.0'

def compare_tos_versions(user_version, current_version):
    """
    Compare ToS versions and determine if re-acceptance is required.
    Only major version changes require re-acceptance.
    """
    try:
        user_parts = user_version.split('.')
        current_parts = current_version.split('.')

        user_major = int(user_parts[0]) if user_parts else 0
        current_major = int(current_parts[0]) if current_parts else 1

        user_minor = int(user_parts[1]) if len(user_parts) > 1 else 0
        current_minor = int(current_parts[1]) if len(current_parts) > 1 else 0

        return {
            'requires_acceptance': user_major < current_major,
            'has_updates': (user_major != current_major) or (user_minor != current_minor),
            'user_major': user_major,
            'current_major': current_major
        }
    except (ValueError, AttributeError):
        return {
            'requires_acceptance': True,
            'has_updates': True,
            'user_major': 0,
            'current_major': 1
        }

# Create Blueprint for mobile API routes
mobile_api = Blueprint('mobile_api', __name__, url_prefix='/api')


# Get Cosmos DB client
db = get_cosmos_db()


# Firebase Auth REST API helper
# DEPRECATED: No longer using Firebase REST API for password verification
# Now using Cosmos DB password_hash verification only (consistent with web app)
# import requests

# def verify_firebase_password(email, password):
#     """
#     [DEPRECATED] Verify user credentials using Firebase Auth REST API.
#     This function is no longer used. Password verification now uses Cosmos DB only.
#     """
#     pass



# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def log_audit(action, details=None, user_id=None):
    """Log an audit entry for compliance tracking"""
    try:
        # Get user_id from parameter, g.user, or details
        if user_id is None:
            if hasattr(g, 'user') and g.user:
                user_id = g.user.get('email') or g.user.get('uid')
            elif details and 'email' in details:
                user_id = details['email']
            else:
                user_id = 'unknown'

        entry = {
            'user_id': user_id,
            'action': action,
            'timestamp': SERVER_TIMESTAMP,
            'ip_address': request.environ.get('REMOTE_ADDR', 'unknown'),
            'user_agent': request.headers.get('User-Agent', 'unknown'),
        }
        if details:
            entry['details'] = details

        db.collection('audit_logs').add(entry)
        logger.info(f"Audit log: {action} by {entry['user_id']}")
    except Exception as e:
        logger.error(f"Failed to log audit entry: {e}")


def get_user_profile(user_email_or_uid):
    """Get user profile from Cosmos DB by email or Firebase UID"""
    # Try by email first (document ID)
    user_doc = db.collection('users').document(user_email_or_uid).get()
    if user_doc.exists:
        return user_doc.to_dict()

    # Try by Firebase UID
    users = db.collection('users').where('firebase_uid', '==', user_email_or_uid).limit(1).stream()
    for user_doc in users:
        return user_doc.to_dict()

    return None


def require_role(*allowed_roles):
    """Decorator to check if user has one of the allowed roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = g.user.get('role', 'individual')

            # Normalize role
            if user_role == 'admin':
                user_role = 'institute_admin'
            elif user_role == 'physio':
                user_role = 'institute_physio'

            # Check if user is admin (admins can do everything)
            if g.user.get('is_admin') == 1 or g.user.get('is_super_admin') == 1:
                return f(*args, **kwargs)

            # Check role
            if user_role not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route('/login', methods=['POST'])
def api_login():
    """
    Mobile login endpoint

    Request body:
    {
        "email": "user@example.com",
        "password": "password123"
    }

    Response:
    {
        "ok": true,
        "uid": "firebase_uid",
        "idToken": "firebase_id_token",
        "profile": {
            "uid": "firebase_uid",
            "email": "user@example.com",
            "name": "User Name",
            "role": "institute_physio",
            "institute": "Institute Name",
            "institute_id": "institute_123",
            "approved": 1,
            "active": 1
        }
    }
    """
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'ok': False, 'error': 'Email and password required'}), 400

        # Get user from Cosmos DB
        user_doc = db.collection('users').document(email).get()
        if not user_doc.exists:
            logger.warning(f"Login attempt for non-existent user: {email}")
            return jsonify({'ok': False, 'error': 'Invalid credentials'}), 401

        user_data = user_doc.to_dict()

        # Check if user is approved and active
        if user_data.get('is_super_admin', 0) != 1:
            if user_data.get('approved', 0) != 1:
                return jsonify({'ok': False, 'error': 'Account pending approval'}), 403
            if user_data.get('active', 1) != 1:
                return jsonify({'ok': False, 'error': 'Account deactivated'}), 403

            # Check email verification (super admins bypass this check)
            if not user_data.get('email_verified', False):
                logger.warning(f"Login attempt with unverified email: {email}")
                return jsonify({
                    'ok': False,
                    'error': 'EMAIL_NOT_VERIFIED',
                    'message': 'Please verify your email address before logging in. Check your inbox for the verification link.'
                }), 403

            # Check ToS version (super admins bypass this check)
            user_tos_version = user_data.get('tos_version', '0.0')
            tos_comparison = compare_tos_versions(user_tos_version, TOS_VERSION)

            # Only block login for major version changes
            if tos_comparison['requires_acceptance']:
                logger.info(f"User {email} needs to accept updated ToS - major version change (user: {user_tos_version}, required: {TOS_VERSION})")
                return jsonify({
                    'ok': False,
                    'error': 'TOS_UPDATE_REQUIRED',
                    'message': 'Our Terms of Service have been updated with significant changes. Please review and accept the new terms to continue.',
                    'current_version': user_tos_version,
                    'required_version': TOS_VERSION
                }), 403

        # Check for minor ToS updates (will be included in success response)
        user_tos_version = user_data.get('tos_version', '0.0')
        tos_comparison = compare_tos_versions(user_tos_version, TOS_VERSION)
        tos_update_available = tos_comparison['has_updates'] and not tos_comparison['requires_acceptance']

        # Verify password - handle both Cosmos DB hash and Firebase Auth
        from werkzeug.security import check_password_hash
        password_hash = user_data.get('password_hash', '')
        firebase_uid = user_data.get('firebase_uid')
        
        logger.info(f"Login attempt for {email}: password_length={len(password)}, has_password_hash={bool(password_hash)}, has_firebase_uid={bool(firebase_uid)}")

        # Case 1: User has Cosmos DB password hash - verify it (like web app)
        if password_hash:
            if not check_password_hash(password_hash, password):
                logger.warning(f"Password verification failed for {email}")
                log_audit('failed_login', {'email': email})
                return jsonify({'ok': False, 'error': 'Invalid credentials'}), 401

            logger.info(f"Cosmos DB password verification successful for {email}")
            
            # Password verified. Get or create Firebase UID
            if not firebase_uid:
                try:
                    # Try to find existing Firebase Auth user
                    firebase_user = auth.get_user_by_email(email)
                    firebase_uid = firebase_user.uid
                    logger.info(f"Found existing Firebase Auth user for {email}")
                except:
                    # Create new Firebase Auth user
                    try:
                        firebase_user = auth.create_user(
                            email=email,
                            password=password,
                            display_name=user_data.get('name', '')
                        )
                        firebase_uid = firebase_user.uid
                        logger.info(f"Created Firebase Auth user for {email}")
                    except Exception as e:
                        logger.error(f"Failed to create Firebase user: {e}")
                        return jsonify({'ok': False, 'error': 'Authentication service error'}), 500
                
                # Update Cosmos DB with Firebase UID
                db.collection('users').document(email).update({'firebase_uid': firebase_uid})
        
        # Case 2: User has no Cosmos DB password hash - must be Firebase Auth only user
        else:
            logger.info(f"User {email} has no password_hash, checking Firebase Auth")
            try:
                # Get Firebase Auth user
                firebase_user = auth.get_user_by_email(email)
                firebase_uid = firebase_user.uid
                logger.info(f"Found Firebase Auth user for {email}: {firebase_uid}")
                
                # Update Cosmos DB with Firebase UID if not present
                if not user_data.get('firebase_uid'):
                    from werkzeug.security import generate_password_hash
                    db.collection("users").document(email).update({
                        "firebase_uid": firebase_uid,
                        "password_hash": generate_password_hash(password)
                    })
                    logger.info(f"Updated Cosmos DB with firebase_uid and password_hash for {email}")
                    
            except Exception as e:
                logger.error(f"Firebase Auth user not found for {email}: {e}")
                log_audit('failed_login', {'email': email})
                return jsonify({'ok': False, 'error': 'Invalid credentials'}), 401

        # Generate custom token for the user
        try:
            custom_token = auth.create_custom_token(firebase_uid)
            id_token = custom_token.decode('utf-8') if isinstance(custom_token, bytes) else custom_token
        except Exception as e:
            logger.error(f"Failed to create custom token: {e}")
            return jsonify({'ok': False, 'error': 'Token generation failed'}), 500

        # Determine user role
        if user_data.get('is_super_admin', 0) == 1:
            role = 'institute_admin'
        elif user_data.get('is_admin', 0) == 1:
            role = 'institute_admin'
        else:
            role = user_data.get('role', 'individual')

        # Log successful login
        log_audit('mobile_login', {'email': email})

        # Return profile data
        profile = {
            'uid': firebase_uid,
            'email': email,
            'name': user_data.get('name', ''),
            'role': role,
            'institute': user_data.get('institute', ''),
            'institute_id': user_data.get('institute_id', ''),
            'approved': user_data.get('approved', 0),
            'active': user_data.get('active', 1),
            'is_admin': user_data.get('is_admin', 0),
            'is_super_admin': user_data.get('is_super_admin', 0)
        }

        response_data = {
            'ok': True,
            'uid': firebase_uid,
            'idToken': id_token,
            'profile': profile
        }

        # Include ToS update notification for minor version changes
        if tos_update_available:
            response_data['tos_update_available'] = True
            response_data['tos_message'] = f'Our Terms of Service have been updated (v{TOS_VERSION}). Review the changes in Settings.'
            response_data['current_tos_version'] = TOS_VERSION

            # Create notification for minor ToS update
            try:
                from notification_service import notify_tos_update
                notify_tos_update(email, TOS_VERSION, is_major=False)
            except Exception as e:
                logger.warning(f"Failed to create ToS update notification: {e}")

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        # Return more detailed error for debugging (remove in production)
        import traceback
        error_details = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"Login stack trace: {stack_trace}")
        return jsonify({
            'ok': False,
            'error': 'Login failed',
            'debug': error_details  # Include error details for debugging
        }), 500


@mobile_api.route('/register', methods=['POST'])
def api_register():
    """
    Mobile registration endpoint for individual physiotherapists

    Request body:
    {
        "name": "Full Name",
        "email": "user@example.com",
        "phone": "+91XXXXXXXXXX",
        "institute": "Institute Name",
        "password": "password123",
        "gdpr_data_processing": true,
        "gdpr_terms_of_service": true,
        "gdpr_ai_data_consent": false
    }

    Response:
    {
        "success": true,
        "message": "Registration successful",
        "email": "user@example.com"
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'institute', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400

        name = data['name'].strip()
        email = data['email'].strip().lower()
        phone = data['phone'].strip()
        institute = data['institute'].strip()
        password = data['password']

        # Validate GDPR consent
        gdpr_data_processing = data.get('gdpr_data_processing', False)
        gdpr_terms_of_service = data.get('gdpr_terms_of_service', False)
        gdpr_ai_data_consent = data.get('gdpr_ai_data_consent', False)

        if not gdpr_data_processing or not gdpr_terms_of_service:
            return jsonify({
                'success': False,
                'error': 'You must consent to data processing and terms of service to register'
            }), 400

        # Validate password length
        if len(password) < 8:
            return jsonify({'success': False, 'error': 'Password must be at least 8 characters'}), 400

        # Check if user already exists in Cosmos DB
        existing_user = db.collection('users').document(email).get()
        if existing_user.exists:
            return jsonify({'success': False, 'error': 'An account with this email already exists'}), 409

        # Create Firebase Auth user first
        try:
            firebase_user = auth.create_user(
                email=email,
                password=password,
                display_name=name
            )
            firebase_uid = firebase_user.uid
            logger.info(f"Created Firebase Auth user for {email}: {firebase_uid}")
        except Exception as e:
            logger.error(f"Failed to create Firebase Auth user for {email}: {e}")
            return jsonify({'success': False, 'error': 'Failed to create authentication account'}), 500

        # Hash password for Cosmos DB backup
        from werkzeug.security import generate_password_hash
        password_hash = generate_password_hash(password)

        # Create user document in Cosmos DB
        db.collection('users').document(email).set({
            'name': name,
            'email': email,
            'phone': phone,
            'institute': institute,
            'password_hash': password_hash,
            'firebase_uid': firebase_uid,
            'created_at': SERVER_TIMESTAMP,
            'approved': 0,  # Require admin approval
            'active': 1,
            'is_admin': 0,
            'email_verified': False,
            # GDPR Consent fields
            'consent_data_processing': 1,
            'consent_terms': 1,
            'consent_ai': 1 if gdpr_ai_data_consent else 0,
            'consent_date': SERVER_TIMESTAMP,
            # ToS Acceptance Logging (Legal requirement)
            'tos_accepted_at': SERVER_TIMESTAMP,
            'tos_version': TOS_VERSION,
        })

        # Log registration action
        log_audit('mobile_register', {
            'email': email,
            'name': name,
            'institute': institute,
            'ai_consent': gdpr_ai_data_consent
        })

        # Send email notification to super admin about new registration
        try:
            send_registration_notification({
                'name': name,
                'email': email,
                'phone': phone,
                'institute': institute,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            logger.info(f"Sent registration notification to super admin for {email}")
        except Exception as e:
            logger.error(f"Failed to send registration notification for {email}: {e}")

        logger.info(f"Successfully registered mobile user: {email}")

        return jsonify({
            'success': True,
            'message': 'Registration successful! Your account is pending admin approval.',
            'email': email
        }), 201

    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Registration failed. Please try again.'
        }), 500


@mobile_api.route('/accept-tos', methods=['POST'])
@require_auth
def api_accept_tos():
    """
    Accept updated Terms of Service from mobile app

    Request body:
    {
        "accept_tos": true
    }

    Response:
    {
        "success": true,
        "message": "Terms of Service accepted successfully"
    }
    """
    try:
        user_email = g.user.get('email') or g.user.get('uid')

        data = request.get_json() or {}

        if not data.get('accept_tos'):
            return jsonify({
                'success': False,
                'error': 'You must accept the Terms of Service to continue'
            }), 400

        # Update user's ToS acceptance
        db.collection('users').document(user_email).update({
            'tos_version': TOS_VERSION,
            'tos_accepted_at': SERVER_TIMESTAMP,
            'consent_terms': 1
        })

        # Log the action
        log_audit('tos_acceptance', {
            'email': user_email,
            'version': TOS_VERSION
        })

        logger.info(f"User {user_email} accepted ToS version {TOS_VERSION}")

        return jsonify({
            'success': True,
            'message': 'Terms of Service accepted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error accepting ToS: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to accept Terms of Service'
        }), 500


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route('/notifications', methods=['GET'])
@require_auth
def api_get_notifications():
    """
    Get notifications for current user

    Query Parameters:
    - unread_only: 'true' to get only unread notifications
    - category: Filter by category (subscription, quota, system, payment, security)
    - limit: Maximum number to return (default 50)

    Response:
    {
        "success": true,
        "notifications": [
            {
                "id": "notification_id",
                "title": "Notification Title",
                "message": "Notification message",
                "type": "info|success|warning|error",
                "category": "system",
                "read": false,
                "created_at": "2025-01-01T00:00:00Z",
                "action_url": "/some-url"
            }
        ]
    }
    """
    try:
        from notification_service import NotificationService

        user_email = g.user.get('email') or g.user.get('uid')
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        category = request.args.get('category')
        limit = int(request.args.get('limit', 50))

        notifications = NotificationService.get_user_notifications(
            user_id=user_email,
            limit=limit,
            unread_only=unread_only,
            category=category
        )

        # Convert timestamps to strings for JSON serialization
        for notification in notifications:
            if 'created_at' in notification and notification['created_at']:
                try:
                    notification['created_at'] = notification['created_at'].isoformat()
                except:
                    pass

        return jsonify({'success': True, 'notifications': notifications}), 200

    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch notifications'}), 500


@mobile_api.route('/notifications/unread-count', methods=['GET'])
@require_auth
def api_get_unread_count():
    """
    Get count of unread notifications

    Response:
    {
        "success": true,
        "count": 5
    }
    """
    try:
        from notification_service import NotificationService

        user_email = g.user.get('email') or g.user.get('uid')
        count = NotificationService.get_unread_count(user_email)

        return jsonify({'success': True, 'count': count}), 200

    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        return jsonify({'success': False, 'error': 'Failed to get unread count'}), 500


@mobile_api.route('/notifications/<notification_id>/read', methods=['POST'])
@require_auth
def api_mark_notification_read(notification_id):
    """
    Mark a notification as read

    Response:
    {
        "success": true
    }
    """
    try:
        from notification_service import NotificationService

        user_email = g.user.get('email') or g.user.get('uid')
        success = NotificationService.mark_as_read(notification_id, user_email)

        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'success': False, 'error': 'Notification not found or access denied'}), 404

    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return jsonify({'success': False, 'error': 'Failed to mark notification as read'}), 500


@mobile_api.route('/notifications/read-all', methods=['POST'])
@require_auth
def api_mark_all_notifications_read():
    """
    Mark all notifications as read

    Response:
    {
        "success": true,
        "count": 10
    }
    """
    try:
        from notification_service import NotificationService

        user_email = g.user.get('email') or g.user.get('uid')
        count = NotificationService.mark_all_as_read(user_email)

        return jsonify({'success': True, 'count': count}), 200

    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        return jsonify({'success': False, 'error': 'Failed to mark notifications as read'}), 500


@mobile_api.route('/notifications/<notification_id>', methods=['DELETE'])
@require_auth
def api_delete_notification(notification_id):
    """
    Delete a notification

    Response:
    {
        "success": true
    }
    """
    try:
        from notification_service import NotificationService

        user_email = g.user.get('email') or g.user.get('uid')
        success = NotificationService.delete_notification(notification_id, user_email)

        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'success': False, 'error': 'Notification not found or access denied'}), 404

    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete notification'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# PATIENT MANAGEMENT ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route('/patients/mine', methods=['GET'])
@require_auth
def api_list_my_patients():
    """
    Get list of patients for the current user with optional filtering

    Query Parameters:
    - name: Filter by patient name (case-insensitive substring match)
    - patient_id: Filter by patient ID (substring match)
    - contact: Filter by contact number (substring match)
    - complaint: Filter by chief complaint (case-insensitive substring match)
    - date_from: Filter by created date from (YYYY-MM-DD)
    - date_to: Filter by created date to (YYYY-MM-DD)
    - sort: Sort order (newest, oldest, name_asc, name_desc)

    Response:
    {
        "patients": [...],
        "total_count": 100,
        "filtered_count": 10
    }
    """
    try:
        user_email = g.user.get('email') or g.user.get('uid')

        # Get filter parameters from query string
        name_filter = request.args.get('name', '').strip()
        id_filter = request.args.get('patient_id', '').strip()
        contact_filter = request.args.get('contact', '').strip()
        complaint_filter = request.args.get('complaint', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        sort_by = request.args.get('sort', 'newest')
        status_filter = request.args.get('status', '').strip()  # active, completed, archived
        tags_filter = request.args.getlist('tags')  # Multiple tags

        # Debug logging
        logger.info(f"Fetching patients for user: {user_email} with filters: name={name_filter}, id={id_filter}, contact={contact_filter}")

        # Query patients for this physiotherapist
        patients_ref = db.collection('patients').where('physio_id', '==', user_email).stream()

        patients = []
        for patient_doc in patients_ref:
            patient_data = patient_doc.to_dict()
            patient_data['id'] = patient_doc.id

            # Convert timestamp to ISO format if present
            if 'created_at' in patient_data and patient_data['created_at']:
                try:
                    patient_data['created_at'] = patient_data['created_at'].isoformat()
                except:
                    pass

            patients.append(patient_data)

        # Enrich patient data with assessment completion status for progress tracking
        for patient in patients:
            patient_id = patient.get('patient_id')
            if patient_id:
                # Check if subjective examination exists
                subj_docs = db.collection('subjective_examination') \
                    .where('patient_id', '==', patient_id).limit(1).get()
                if subj_docs:
                    patient['subjectiveExamination'] = True

                # Check if patient perspectives exists
                persp_docs = db.collection('subjective_perspectives') \
                    .where('patient_id', '==', patient_id).limit(1).get()
                if persp_docs:
                    patient['patientPerspectives'] = True

                # Check if objective assessment exists
                obj_docs = db.collection('objective_assessment') \
                    .where('patient_id', '==', patient_id).limit(1).get()
                if obj_docs:
                    patient['objectiveAssessment'] = True

                # Check if provisional diagnosis exists
                diag_docs = db.collection('provisional_diagnosis') \
                    .where('patient_id', '==', patient_id).limit(1).get()
                if diag_docs:
                    patient['provisionalDiagnosis'] = True

                # Check if initial plan exists
                plan_docs = db.collection('initial_assessment') \
                    .where('patient_id', '==', patient_id).limit(1).get()
                if plan_docs:
                    patient['initialPlan'] = True

                # Check if SMART goals exists
                goals_docs = db.collection('smart_goals') \
                    .where('patient_id', '==', patient_id).limit(1).get()
                if goals_docs:
                    patient['smartGoals'] = True

                # Check if treatment plan exists
                treatment_docs = db.collection('treatment_plans') \
                    .where('patient_id', '==', patient_id).limit(1).get()
                if treatment_docs:
                    patient['treatmentPlan'] = True

        # Store original count
        total_count = len(patients)

        # Apply client-side filtering
        filtered_patients = patients

        if name_filter:
            filtered_patients = [p for p in filtered_patients
                                if name_filter.lower() in (p.get('name') or '').lower()]

        if id_filter:
            filtered_patients = [p for p in filtered_patients
                                if id_filter.lower() in (p.get('patient_id') or '').lower()]

        if contact_filter:
            filtered_patients = [p for p in filtered_patients
                                if contact_filter in (p.get('contact') or '')]

        if complaint_filter:
            filtered_patients = [p for p in filtered_patients
                                if complaint_filter.lower() in (p.get('present_history') or '').lower()]

        # Filter by treatment status
        if status_filter:
            filtered_patients = [p for p in filtered_patients
                                if p.get('status', 'active') == status_filter]

        # Filter by tags (patient must have at least one of the selected tags)
        if tags_filter:
            filtered_patients = [p for p in filtered_patients
                                if any(tag in (p.get('tags') or []) for tag in tags_filter)]

        # Date range filtering
        if date_from:
            try:
                from datetime import datetime, timedelta
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                filtered_patients = [p for p in filtered_patients
                                    if p.get('created_at') and datetime.fromisoformat(p['created_at'].replace('Z', '+00:00')) >= from_date]
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid date_from format: {date_from}, {e}")

        if date_to:
            try:
                from datetime import datetime, timedelta
                to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                filtered_patients = [p for p in filtered_patients
                                    if p.get('created_at') and datetime.fromisoformat(p['created_at'].replace('Z', '+00:00')) < to_date]
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid date_to format: {date_to}, {e}")

        # Apply sorting
        if sort_by == 'newest':
            filtered_patients.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        elif sort_by == 'oldest':
            filtered_patients.sort(key=lambda x: x.get('created_at', ''))
        elif sort_by == 'name_asc':
            filtered_patients.sort(key=lambda x: (x.get('name') or '').lower())
        elif sort_by == 'name_desc':
            filtered_patients.sort(key=lambda x: (x.get('name') or '').lower(), reverse=True)

        logger.info(f"Found {total_count} patients, {len(filtered_patients)} after filtering")

        return jsonify({
            'patients': filtered_patients,
            'total_count': total_count,
            'filtered_count': len(filtered_patients)
        }), 200

    except Exception as e:
        logger.error(f"Error fetching patients: {e}")
        return jsonify({'error': 'Failed to fetch patients'}), 500


@mobile_api.route('/patients/<patient_id>/status', methods=['POST'])
@require_auth
def api_update_patient_status(patient_id):
    """Update patient treatment status"""
    try:
        user_email = g.user.get('email') or g.user.get('uid')

        # Verify patient exists
        patient_ref = db.collection('patients').document(patient_id)
        patient_doc = patient_ref.get()

        if not patient_doc.exists:
            return jsonify({'success': False, 'error': 'Patient not found'}), 404

        patient = patient_doc.to_dict()

        # Check access
        if patient.get('physio_id') != user_email:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Get new status
        data = request.get_json()
        new_status = data.get('status')

        if new_status not in ['active', 'completed', 'archived']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400

        # Update status
        patient_ref.update({
            'status': new_status,
            'status_updated_at': SERVER_TIMESTAMP
        })

        log_audit('update_patient_status', {
            'email': user_email,
            'patient_id': patient_id,
            'new_status': new_status
        })

        return jsonify({'success': True, 'status': new_status}), 200

    except Exception as e:
        logger.error(f"Error updating patient status: {e}")
        return jsonify({'success': False, 'error': 'Failed to update status'}), 500


@mobile_api.route('/patients/<patient_id>/tags', methods=['POST'])
@require_auth
def api_update_patient_tags(patient_id):
    """Update patient tags"""
    try:
        user_email = g.user.get('email') or g.user.get('uid')

        # Verify patient exists
        patient_ref = db.collection('patients').document(patient_id)
        patient_doc = patient_ref.get()

        if not patient_doc.exists:
            return jsonify({'success': False, 'error': 'Patient not found'}), 404

        patient = patient_doc.to_dict()

        # Check access
        if patient.get('physio_id') != user_email:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Get tags
        data = request.get_json()
        tags = data.get('tags', [])

        # Clean and deduplicate tags
        cleaned_tags = list(set([tag.strip() for tag in tags if tag.strip()]))

        # Update tags
        patient_ref.update({
            'tags': cleaned_tags
        })

        log_audit('update_patient_tags', {
            'email': user_email,
            'patient_id': patient_id,
            'tags': cleaned_tags
        })

        return jsonify({'success': True, 'tags': cleaned_tags}), 200

    except Exception as e:
        logger.error(f"Error updating patient tags: {e}")
        return jsonify({'success': False, 'error': 'Failed to update tags'}), 500


@mobile_api.route('/tags/suggestions', methods=['GET'])
@require_auth
def api_get_tag_suggestions():
    """Get tag suggestions for autocomplete"""
    try:
        user_email = g.user.get('email') or g.user.get('uid')

        # Get all patients for this user
        patients = db.collection('patients').where('physio_id', '==', user_email).stream()

        # Collect unique tags
        all_tags = set()
        for doc in patients:
            patient = doc.to_dict()
            all_tags.update(patient.get('tags') or [])

        # Add default/suggested tags
        default_tags = [
            'Sports Injury', 'Post-Surgery', 'Chronic Pain', 'Acute Pain',
            'Neurological', 'Orthopedic', 'Pediatric', 'Geriatric',
            'Work-Related', 'Motor Vehicle Accident', 'Falls',
            'Upper Extremity', 'Lower Extremity', 'Spine',
            'High Priority', 'Follow-Up Required', 'Discharged'
        ]
        all_tags.update(default_tags)

        return jsonify({'success': True, 'tags': sorted(list(all_tags))}), 200

    except Exception as e:
        logger.error(f"Error getting tag suggestions: {e}")
        return jsonify({'success': False, 'error': 'Failed to get tags'}), 500


@mobile_api.route('/patients/<patient_id>', methods=['GET'])
@require_auth
def api_get_patient(patient_id):
    """Get a specific patient by ID"""
    try:
        patient_doc = db.collection('patients').document(patient_id).get()

        if not patient_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404

        patient_data = patient_doc.to_dict()
        patient_data['id'] = patient_doc.id

        # Check if this patient belongs to the current user
        user_email = g.user.get('email') or g.user.get('uid')
        if patient_data.get('physio_id') != user_email and g.user.get('is_admin', 0) != 1:
            return jsonify({'error': 'Unauthorized'}), 403

        # Convert timestamps
        for field in ['created_at', 'updated_at']:
            if field in patient_data and patient_data[field]:
                try:
                    patient_data[field] = patient_data[field].isoformat()
                except:
                    pass

        log_audit('view_patient', {'patient_id': patient_id})

        return jsonify(patient_data), 200

    except Exception as e:
        logger.error(f"Error fetching patient: {e}")
        return jsonify({'error': 'Failed to fetch patient'}), 500


@mobile_api.route('/patients', methods=['POST'])
@require_auth
def api_create_patient():
    """
    Create a new patient

    Request body:
    {
        "name": "Patient Name",
        "age_sex": "45/M",
        "contact": "1234567890",
        "chief_complaint": "Back pain",
        "medical_history": "...",
        ...
    }
    """
    try:
        data = request.get_json()

        # Generate UUID for patient
        patient_id = str(uuid.uuid4())
        user_email = g.user.get('email') or g.user.get('uid')

        # Prepare patient data
        patient_data = {
            'physio_id': user_email,
            'name': data.get('name', ''),
            'age_sex': data.get('age_sex', ''),
            'contact': data.get('contact', ''),
            'chief_complaint': data.get('chief_complaint', ''),
            'medical_history': data.get('medical_history', ''),
            'surgical_history': data.get('surgical_history', ''),
            'occupation': data.get('occupation', ''),
            'created_at': SERVER_TIMESTAMP,
            'updated_at': SERVER_TIMESTAMP
        }

        # Add optional fields if provided
        optional_fields = [
            'subjective', 'patient_perspectives', 'initial_plan',
            'pathophysiological_mechanism', 'chronic_disease_factors',
            'clinical_flags', 'objective_assessment', 'provisional_diagnosis',
            'smart_goals', 'treatment_plan'
        ]

        for field in optional_fields:
            if field in data:
                patient_data[field] = data[field]

        # Save to Cosmos DB
        db.collection('patients').document(patient_id).set(patient_data)

        log_audit('create_patient', {'patient_id': patient_id, 'patient_name': patient_data['name']})

        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'message': 'Patient created successfully'
        }), 201

    except Exception as e:
        logger.error(f"Error creating patient: {e}")
        return jsonify({'error': 'Failed to create patient'}), 500


@mobile_api.route('/patients/<patient_id>', methods=['PATCH'])
@require_auth
def api_update_patient(patient_id):
    """Update an existing patient"""
    try:
        # Check if patient exists
        patient_doc = db.collection('patients').document(patient_id).get()
        if not patient_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404

        patient_data = patient_doc.to_dict()
        user_email = g.user.get('email') or g.user.get('uid')

        # Check ownership
        if patient_data.get('physio_id') != user_email and g.user.get('is_admin', 0) != 1:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get update data
        update_data = request.get_json()
        update_data['updated_at'] = SERVER_TIMESTAMP

        # Update patient
        db.collection('patients').document(patient_id).update(update_data)

        log_audit('update_patient', {'patient_id': patient_id})

        return jsonify({
            'success': True,
            'message': 'Patient updated successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error updating patient: {e}")
        return jsonify({'error': 'Failed to update patient'}), 500


@mobile_api.route('/patients/<patient_id>', methods=['DELETE'])
@require_auth
def api_delete_patient(patient_id):
    """Delete a patient"""
    try:
        # Check if patient exists
        patient_doc = db.collection('patients').document(patient_id).get()
        if not patient_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404

        patient_data = patient_doc.to_dict()
        user_email = g.user.get('email') or g.user.get('uid')

        # Check ownership
        if patient_data.get('physio_id') != user_email and g.user.get('is_admin', 0) != 1:
            return jsonify({'error': 'Unauthorized'}), 403

        # Delete patient
        db.collection('patients').document(patient_id).delete()

        log_audit('delete_patient', {'patient_id': patient_id, 'patient_name': patient_data.get('name')})

        return jsonify({
            'success': True,
            'message': 'Patient deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error deleting patient: {e}")
        return jsonify({'error': 'Failed to delete patient'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# FOLLOW-UP MANAGEMENT ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route('/patients/<patient_id>/follow-ups', methods=['POST'])
@require_auth
def api_create_follow_up(patient_id):
    """
    Create a follow-up for a patient

    Request body:
    {
        "date": "2025-01-20",
        "notes": "Patient progress...",
        "objective_findings": "...",
        "treatment_given": "...",
        "next_plan": "..."
    }
    """
    try:
        # Verify patient exists and user has access
        patient_doc = db.collection('patients').document(patient_id).get()
        if not patient_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404

        patient_data = patient_doc.to_dict()
        user_email = g.user.get('email') or g.user.get('uid')

        if patient_data.get('physio_id') != user_email and g.user.get('is_admin', 0) != 1:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get follow-up data
        data = request.get_json()
        follow_up_id = str(uuid.uuid4())

        follow_up_data = {
            'patient_id': patient_id,
            'physio_id': user_email,
            'date': data.get('date', ''),
            'notes': data.get('notes', ''),
            'subjective': data.get('subjective', ''),
            'objective_findings': data.get('objective_findings', ''),
            'assessment': data.get('assessment', ''),
            'treatment_given': data.get('treatment_given', ''),
            'next_plan': data.get('next_plan', ''),
            'created_at': SERVER_TIMESTAMP,
            'updated_at': SERVER_TIMESTAMP
        }

        # Save follow-up
        db.collection('follow_ups').document(follow_up_id).set(follow_up_data)

        # Update patient's last_follow_up
        db.collection('patients').document(patient_id).update({
            'last_follow_up': follow_up_data['date'],
            'updated_at': SERVER_TIMESTAMP
        })

        log_audit('create_follow_up', {'patient_id': patient_id, 'follow_up_id': follow_up_id})

        return jsonify({
            'success': True,
            'follow_up_id': follow_up_id,
            'message': 'Follow-up created successfully'
        }), 201

    except Exception as e:
        logger.error(f"Error creating follow-up: {e}")
        return jsonify({'error': 'Failed to create follow-up'}), 500


@mobile_api.route('/patients/<patient_id>/follow-ups', methods=['GET'])
@require_auth
def api_list_follow_ups(patient_id):
    """Get all follow-ups for a patient"""
    try:
        # Verify patient exists and user has access
        patient_doc = db.collection('patients').document(patient_id).get()
        if not patient_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404

        patient_data = patient_doc.to_dict()
        user_email = g.user.get('email') or g.user.get('uid')

        if patient_data.get('physio_id') != user_email and g.user.get('is_admin', 0) != 1:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get follow-ups
        follow_ups_ref = db.collection('follow_ups').where('patient_id', '==', patient_id).stream()

        follow_ups = []
        for follow_up_doc in follow_ups_ref:
            follow_up_data = follow_up_doc.to_dict()
            follow_up_data['id'] = follow_up_doc.id

            # Convert timestamps
            for field in ['created_at', 'updated_at']:
                if field in follow_up_data and follow_up_data[field]:
                    try:
                        follow_up_data[field] = follow_up_data[field].isoformat()
                    except:
                        pass

            follow_ups.append(follow_up_data)

        # Sort by date descending
        follow_ups.sort(key=lambda x: x.get('date', ''), reverse=True)

        return jsonify({'follow_ups': follow_ups}), 200

    except Exception as e:
        logger.error(f"Error fetching follow-ups: {e}")
        return jsonify({'error': 'Failed to fetch follow-ups'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# INSTITUTE ADMIN ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route('/institute/physios/pending', methods=['GET'])
@require_auth
def api_list_pending_physios():
    """Get list of pending physiotherapist approvals (admin only)"""
    try:
        # Check if user is admin
        if g.user.get('is_admin', 0) != 1 and g.user.get('is_super_admin', 0) != 1:
            return jsonify({'error': 'Admin access required'}), 403

        institute = g.user.get('institute', '')
        is_super_admin = g.user.get('is_super_admin', 0) == 1

        # Super admins see ALL pending users, regular admins see only their institute
        if is_super_admin:
            pending_users = db.collection('users').where('approved', '==', 0).stream()
        else:
            pending_users = db.collection('users') \
                .where('institute', '==', institute) \
                .where('approved', '==', 0) \
                .stream()

        users = []
        for user_doc in pending_users:
            user_data = user_doc.to_dict()
            user_data['email'] = user_doc.id

            # Convert timestamp
            if 'created_at' in user_data and user_data['created_at']:
                try:
                    user_data['created_at'] = user_data['created_at'].isoformat()
                except:
                    pass

            # Add type label for display (like web app)
            if user_data.get('is_admin') == 1:
                type_label = 'INSTITUTE ADMIN'
                type_class = 'admin'
            elif user_data.get('user_type') == 'institute_staff':
                type_label = 'Institute Staff'
                type_class = 'staff'
            else:
                type_label = 'Individual'
                type_class = 'individual'

            users.append({
                'email': user_doc.id,
                'name': user_data.get('name', ''),
                'phone': user_data.get('phone', ''),
                'institute': user_data.get('institute', ''),
                'role': user_data.get('role', 'individual'),
                'type_label': type_label,
                'type_class': type_class,
                'created_at': user_data.get('created_at', '')
            })

        return jsonify({'pending_users': users}), 200

    except Exception as e:
        logger.error(f"Error fetching pending users: {e}")
        return jsonify({'error': 'Failed to fetch pending users'}), 500


@mobile_api.route('/admin/dashboard/stats', methods=['GET'])
@require_auth
def api_admin_dashboard_stats():
    """Get dashboard statistics for admins and super admins"""
    try:
        # Check if user is admin
        if g.user.get('is_admin', 0) != 1 and g.user.get('is_super_admin', 0) != 1:
            return jsonify({'error': 'Admin access required'}), 403

        is_super_admin = g.user.get('is_super_admin', 0) == 1
        institute = g.user.get('institute', '')

        if is_super_admin:
            # Super admin: global statistics
            total_users = len(list(db.collection('users').stream()))
            total_institutes = len(set(u.to_dict().get('institute') for u in db.collection('users').where('is_admin', '==', 1).stream()))
            total_patients = len(list(db.collection('patients').stream()))
            pending_count = len(list(db.collection('users').where('approved', '==', 0).stream()))

            # Get institutes summary
            institutes_ref = db.collection('users').where('is_admin', '==', 1).stream()
            institutes = {}
            for inst in institutes_ref:
                inst_data = inst.to_dict()
                inst_name = inst_data.get('institute')
                if inst_name and inst_name not in institutes:
                    institutes[inst_name] = {
                        'name': inst_name,
                        'admin_count': 0,
                        'user_count': 0,
                        'patient_count': 0
                    }
                if inst_name:
                    institutes[inst_name]['admin_count'] += 1

            # Count users and patients per institute
            for inst_name in list(institutes.keys()):
                users = db.collection('users').where('institute', '==', inst_name).stream()
                institutes[inst_name]['user_count'] = len(list(users))

                patients = db.collection('patients').where('institute', '==', inst_name).stream()
                institutes[inst_name]['patient_count'] = len(list(patients))

            return jsonify({
                'total_users': total_users,
                'total_institutes': total_institutes,
                'total_patients': total_patients,
                'pending_count': pending_count,
                'institutes': list(institutes.values()),
                'is_super_admin': True
            }), 200
        else:
            # Regular admin: institute statistics
            institute_users = len(list(db.collection('users').where('institute', '==', institute).stream()))
            institute_patients = len(list(db.collection('patients').where('institute', '==', institute).stream()))
            pending_count = len(list(db.collection('users').where('institute', '==', institute).where('approved', '==', 0).stream()))

            return jsonify({
                'institute_users': institute_users,
                'institute_patients': institute_patients,
                'pending_count': pending_count,
                'institute': institute,
                'is_super_admin': False
            }), 200

    except Exception as e:
        logger.error(f"Error fetching admin dashboard stats: {e}")
        return jsonify({'error': 'Failed to fetch dashboard statistics'}), 500


@mobile_api.route('/institute/physios/<uid>/approve', methods=['POST'])
@require_auth
def api_approve_physio_by_uid(uid):
    """Approve a physiotherapist by Firebase UID"""
    try:
        # Check if user is admin
        if g.user.get('is_admin', 0) != 1 and g.user.get('is_super_admin', 0) != 1:
            return jsonify({'error': 'Admin access required'}), 403

        # Find user by Firebase UID
        users = db.collection('users').where('firebase_uid', '==', uid).limit(1).stream()
        user_doc = None
        for doc in users:
            user_doc = doc
            break

        if not user_doc:
            return jsonify({'error': 'User not found'}), 404

        user_email = user_doc.id

        # Get user data before updating
        user_data = user_doc.to_dict()

        # Update user approval status
        db.collection('users').document(user_email).update({
            'approved': 1,
            'approved_at': SERVER_TIMESTAMP,
            'approved_by': g.user.get('email'),
            'email_verified': True  # Auto-verify email when admin approves
        })

        log_audit('approve_physio', {'email': user_email, 'uid': uid})

        # Send approval notification email to the user
        try:
            send_approval_notification({
                'name': user_data.get('name', 'User'),
                'email': user_email,
                'institute': user_data.get('institute', 'N/A')
            })
            logger.info(f"Sent approval notification to {user_email}")
        except Exception as e:
            logger.error(f"Failed to send approval notification to {user_email}: {e}")

        return jsonify({
            'success': True,
            'message': 'User approved successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error approving user: {e}")
        return jsonify({'error': 'Failed to approve user'}), 500


@mobile_api.route('/institute/physios/<uid>/reject', methods=['POST'])
@require_auth
def api_reject_physio_by_uid(uid):
    """Reject a physiotherapist by Firebase UID"""
    try:
        # Check if user is admin
        if g.user.get('is_admin', 0) != 1 and g.user.get('is_super_admin', 0) != 1:
            return jsonify({'error': 'Admin access required'}), 403

        # Find user by Firebase UID
        users = db.collection('users').where('firebase_uid', '==', uid).limit(1).stream()
        user_doc = None
        for doc in users:
            user_doc = doc
            break

        if not user_doc:
            return jsonify({'error': 'User not found'}), 404

        user_email = user_doc.id

        # Delete user
        db.collection('users').document(user_email).delete()

        log_audit('reject_physio', {'email': user_email, 'uid': uid})

        return jsonify({
            'success': True,
            'message': 'User rejected and deleted'
        }), 200

    except Exception as e:
        logger.error(f"Error rejecting user: {e}")
        return jsonify({'error': 'Failed to reject user'}), 500


@mobile_api.route('/users/approve', methods=['POST'])
@require_auth
def api_approve_user_by_email():
    """Approve a user by email"""
    try:
        # Check if user is admin
        if g.user.get('is_admin', 0) != 1 and g.user.get('is_super_admin', 0) != 1:
            return jsonify({'error': 'Admin access required'}), 403

        data = request.get_json()
        user_email = data.get('email', '').strip().lower()

        if not user_email:
            return jsonify({'error': 'Email required'}), 400

        # Get user data before updating
        user_doc = db.collection('users').document(user_email).get()
        if not user_doc.exists:
            return jsonify({'error': 'User not found'}), 404

        user_data = user_doc.to_dict()

        # Update user approval status
        db.collection('users').document(user_email).update({
            'approved': 1,
            'approved_at': SERVER_TIMESTAMP,
            'approved_by': g.user.get('email'),
            'email_verified': True  # Auto-verify email when admin approves
        })

        log_audit('approve_user', {'email': user_email})

        # Send approval notification email to the user
        try:
            send_approval_notification({
                'name': user_data.get('name', 'User'),
                'email': user_email,
                'institute': user_data.get('institute', 'N/A')
            })
            logger.info(f"Sent approval notification to {user_email}")
        except Exception as e:
            logger.error(f"Failed to send approval notification to {user_email}: {e}")

        return jsonify({
            'success': True,
            'message': 'User approved successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error approving user: {e}")
        return jsonify({'error': 'Failed to approve user'}), 500


@mobile_api.route('/users/reject', methods=['POST'])
@require_auth
def api_reject_user_by_email():
    """Reject a user by email"""
    try:
        # Check if user is admin
        if g.user.get('is_admin', 0) != 1 and g.user.get('is_super_admin', 0) != 1:
            return jsonify({'error': 'Admin access required'}), 403

        data = request.get_json()
        user_email = data.get('email', '').strip().lower()

        if not user_email:
            return jsonify({'error': 'Email required'}), 400

        # Delete user
        db.collection('users').document(user_email).delete()

        log_audit('reject_user', {'email': user_email})

        return jsonify({
            'success': True,
            'message': 'User rejected and deleted'
        }), 200

    except Exception as e:
        logger.error(f"Error rejecting user: {e}")
        return jsonify({'error': 'Failed to reject user'}), 500


@mobile_api.route('/users/upsert', methods=['POST'])
@require_auth
def api_upsert_user():
    """Create or update user profile"""
    try:
        data = request.get_json()
        user_uid = data.get('uid')

        if not user_uid:
            return jsonify({'error': 'UID required'}), 400

        # Only allow users to update their own profile unless admin
        if g.user.get('uid') != user_uid and g.user.get('is_admin', 0) != 1:
            return jsonify({'error': 'Unauthorized'}), 403

        # Prepare user data
        user_data = {
            'firebase_uid': user_uid,
            'name': data.get('name', ''),
            'updated_at': SERVER_TIMESTAMP
        }

        # Add optional fields
        if 'institute' in data:
            user_data['institute'] = data['institute']
        if 'phone' in data:
            user_data['phone'] = data['phone']

        # Find user by Firebase UID
        users = db.collection('users').where('firebase_uid', '==', user_uid).limit(1).stream()
        user_doc = None
        for doc in users:
            user_doc = doc
            break

        if user_doc:
            # Update existing user
            db.collection('users').document(user_doc.id).update(user_data)
            user_email = user_doc.id
        else:
            # Create new user (use email from data or Firebase)
            user_email = data.get('email', '')
            if not user_email:
                return jsonify({'error': 'Email required for new user'}), 400

            user_data['email'] = user_email
            user_data['created_at'] = SERVER_TIMESTAMP
            user_data['approved'] = 0  # Require approval
            user_data['active'] = 1

            db.collection('users').document(user_email).set(user_data)

        log_audit('upsert_user', {'email': user_email, 'uid': user_uid})

        return jsonify({
            'success': True,
            'message': 'User profile updated successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error upserting user: {e}")
        return jsonify({'error': 'Failed to update user profile'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# Cosmos DB QUERY ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route('/cosmosdb/query', methods=['POST'])
@require_auth
def api_secure_query():
    """
    Execute a secure Cosmos DB query

    Request body:
    {
        "collection": "patients",
        "filters": [
            {"field": "physio_id", "operator": "==", "value": "user@example.com"}
        ],
        "limit": 100
    }
    """
    try:
        data = request.get_json()
        collection_name = data.get('collection', '')
        filters = data.get('filters', [])
        limit = data.get('limit', 100)

        # Security: Only allow querying certain collections
        # Added 'users' and 'audit_logs' for mobile app functionality
        allowed_collections = ['patients', 'follow_ups', 'users', 'audit_logs']
        if collection_name not in allowed_collections:
            return jsonify({'error': 'Collection not allowed'}), 403

        # Start query
        query = db.collection(collection_name)

        # Apply filters
        for filter_spec in filters:
            field = filter_spec.get('field')
            operator = filter_spec.get('operator')
            value = filter_spec.get('value')

            if field and operator and value is not None:
                query = query.where(field, operator, value)

        # Apply limit
        if limit:
            query = query.limit(limit)

        # Execute query
        results = []
        for doc in query.stream():
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            results.append(doc_data)

        return jsonify({'results': results}), 200

    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return jsonify({'error': 'Query failed'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOGS ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route('/audit_logs', methods=['GET'])
@require_auth
def api_get_audit_logs():
    """Get audit logs (admin: all logs, user: own logs)"""
    try:
        limit = request.args.get('limit', 100, type=int)
        user_email = g.user.get('email') or g.user.get('uid')

        if g.user.get('is_admin', 0) == 1 or g.user.get('is_super_admin', 0) == 1:
            # Admin: get all logs for their institute
            institute = g.user.get('institute', '')

            # Get all users in institute
            users = db.collection('users').where('institute', '==', institute).stream()
            user_emails = [u.id for u in users]

            # Get logs for all users (Cosmos DB has 'in' query limit of 10)
            logs = []
            for user_chunk in [user_emails[i:i+10] for i in range(0, len(user_emails), 10)]:
                chunk_logs = db.collection('audit_logs') \
                    .where('user_id', 'in', user_chunk) \
                    .order_by('timestamp', direction='DESCENDING') \
                    .limit(limit) \
                    .stream()
                for log_doc in chunk_logs:
                    log_data = log_doc.to_dict()
                    log_data['id'] = log_doc.id
                    logs.append(log_data)
        else:
            # Regular user: only their own logs
            logs_ref = db.collection('audit_logs') \
                .where('user_id', '==', user_email) \
                .order_by('timestamp', direction='DESCENDING') \
                .limit(limit) \
                .stream()

            logs = []
            for log_doc in logs_ref:
                log_data = log_doc.to_dict()
                log_data['id'] = log_doc.id
                logs.append(log_data)

        # Convert timestamps
        for log in logs:
            if 'timestamp' in log and log['timestamp']:
                try:
                    log['timestamp'] = log['timestamp'].isoformat()
                except:
                    pass

        # Sort by timestamp
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return jsonify({'logs': logs[:limit]}), 200

    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        return jsonify({'error': 'Failed to fetch audit logs'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# SUBSCRIPTION & PAYMENT ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route('/subscription', methods=['GET'])
@require_auth
def api_get_subscription():
    """
    Get user's subscription details and usage stats

    Response:
    {
        "subscription": {
            "plan_type": "solo",
            "status": "active",
            "price_amount": 899,
            "currency": "INR",
            "current_period_end": "2025-02-20T00:00:00"
        },
        "usage": {
            "patients_used": 5,
            "patients_limit": -1,
            "patients_percent": 0,
            "ai_calls_used": 45,
            "ai_calls_limit": 100,
            "ai_percent": 45.0,
            "tokens_balance": 50
        }
    }
    """
    try:
        from subscription_manager import get_user_subscription, get_usage_stats

        user_id = g.user.get('email') or g.user.get('uid')

        subscription = get_user_subscription(user_id)
        usage_stats = get_usage_stats(user_id)

        # Convert datetime objects to ISO format
        if 'current_period_end' in subscription and subscription['current_period_end']:
            try:
                subscription['current_period_end'] = subscription['current_period_end'].isoformat()
            except:
                pass

        if 'trial_end_date' in subscription and subscription['trial_end_date']:
            try:
                subscription['trial_end_date'] = subscription['trial_end_date'].isoformat()
            except:
                pass

        return jsonify({
            'subscription': subscription,
            'usage': usage_stats
        }), 200

    except Exception as e:
        logger.error(f"Error fetching subscription: {e}")
        return jsonify({'error': 'Failed to fetch subscription'}), 500


@mobile_api.route('/subscription/plans', methods=['GET'])
def api_get_plans():
    """
    Get all available subscription plans

    Response:
    {
        "plans": {
            "solo": {
                "name": "Solo Professional",
                "price": 899,
                "currency": "INR",
                "patients_limit": -1,
                "ai_calls_limit": 100,
                "features": [...]
            },
            ...
        }
    }
    """
    try:
        from subscription_manager import get_all_plans

        plans = get_all_plans()

        return jsonify({'plans': plans}), 200

    except Exception as e:
        logger.error(f"Error fetching plans: {e}")
        return jsonify({'error': 'Failed to fetch plans'}), 500


@mobile_api.route('/subscription/checkout', methods=['POST'])
@require_auth
def api_create_subscription_checkout():
    """
    Create a Razorpay subscription checkout

    Request body:
    {
        "plan_type": "solo"
    }

    Response:
    {
        "checkout_data": {
            "subscription_id": "sub_...",
            "razorpay_key": "rzp_...",
            "amount": 89900,
            "currency": "INR",
            "name": "User Name",
            "email": "user@example.com",
            "phone": "1234567890",
            "description": "Solo Professional Subscription"
        }
    }
    """
    try:
        from razorpay_integration import create_subscription_checkout

        data = request.get_json()
        plan_type = data.get('plan_type')

        if not plan_type:
            return jsonify({'error': 'plan_type required'}), 400

        user_id = g.user.get('email') or g.user.get('uid')
        user_name = g.user.get('name', '')
        user_email = g.user.get('email', '')
        user_phone = g.user.get('phone', '')

        checkout_data = create_subscription_checkout(
            user_id=user_id,
            plan_type=plan_type,
            user_name=user_name,
            user_email=user_email,
            user_phone=user_phone
        )

        if not checkout_data:
            return jsonify({'error': 'Failed to create checkout'}), 500

        log_audit('subscription_checkout_created', {'plan_type': plan_type})

        return jsonify({'checkout_data': checkout_data}), 200

    except Exception as e:
        logger.error(f"Error creating subscription checkout: {e}")
        return jsonify({'error': 'Failed to create checkout'}), 500


@mobile_api.route('/subscription/verify', methods=['POST'])
@require_auth
def api_verify_subscription_payment():
    """
    Verify subscription payment and activate subscription

    Request body:
    {
        "razorpay_payment_id": "pay_...",
        "razorpay_subscription_id": "sub_...",
        "razorpay_signature": "...",
        "plan_type": "solo"
    }

    Response:
    {
        "success": true,
        "message": "Subscription activated successfully"
    }
    """
    try:
        from razorpay_integration import verify_subscription_payment
        from subscription_manager import upgrade_subscription

        data = request.get_json()
        payment_id = data.get('razorpay_payment_id')
        subscription_id = data.get('razorpay_subscription_id')
        signature = data.get('razorpay_signature')
        plan_type = data.get('plan_type')

        if not all([payment_id, subscription_id, signature, plan_type]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Verify payment signature
        is_valid = verify_subscription_payment(payment_id, subscription_id, signature)

        if not is_valid:
            return jsonify({'error': 'Payment verification failed'}), 400

        # Activate subscription
        user_id = g.user.get('email') or g.user.get('uid')

        success = upgrade_subscription(
            user_id=user_id,
            plan_type=plan_type,
            subscription_id=subscription_id,
            payment_id=payment_id
        )

        if not success:
            return jsonify({'error': 'Failed to activate subscription'}), 500

        log_audit('subscription_activated', {'plan_type': plan_type, 'subscription_id': subscription_id})

        return jsonify({
            'success': True,
            'message': 'Subscription activated successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error verifying subscription payment: {e}")
        return jsonify({'error': 'Payment verification failed'}), 500


@mobile_api.route('/subscription/cancel', methods=['POST'])
@require_auth
def api_cancel_subscription():
    """
    Cancel user's subscription

    Response:
    {
        "success": true,
        "message": "Subscription cancelled. Access continues until 2025-02-20"
    }
    """
    try:
        from subscription_manager import cancel_subscription, get_user_subscription

        user_id = g.user.get('email') or g.user.get('uid')

        # Get current subscription
        subscription = get_user_subscription(user_id)
        period_end = subscription.get('current_period_end')

        # Cancel subscription
        success = cancel_subscription(user_id)

        if not success:
            return jsonify({'error': 'Failed to cancel subscription'}), 500

        log_audit('subscription_cancelled', {'user_id': user_id})

        message = "Subscription cancelled successfully"
        if period_end:
            try:
                # Handle both datetime objects and ISO strings from Cosmos DB
                if isinstance(period_end, str):
                    period_end = datetime.fromisoformat(period_end.replace('Z', '+00:00'))
                period_end_str = period_end.strftime('%Y-%m-%d')
                message = f"Subscription cancelled. Access continues until {period_end_str}"
            except:
                pass

        return jsonify({
            'success': True,
            'message': message
        }), 200

    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        return jsonify({'error': 'Failed to cancel subscription'}), 500


@mobile_api.route('/subscription/check-user-limit', methods=['GET'])
@require_auth
def api_check_user_limit():
    """
    Check if institute can add more users (for team/institute plans)

    Response:
    {
        "can_add_user": true,
        "current_users": 3,
        "max_users": 5,
        "message": "",
        "upgrade_available": true,
        "next_tier": "team_10",
        "next_tier_info": {
            "name": "Team (10 Users)",
            "price": 7499,
            "max_users": 10
        }
    }
    """
    try:
        from subscription_manager import check_user_limit, get_user_subscription, PLANS

        user_id = g.user.get('email') or g.user.get('uid')

        # Get institute_id (for admins) or user's own ID
        institute_id = g.user.get('institute_id', user_id)

        # Check user limit
        can_add, message, current_users, max_users = check_user_limit(institute_id)

        # Get current subscription to suggest upgrades
        subscription = get_user_subscription(institute_id)
        plan_type = subscription.get('plan_type')

        # Determine next tier
        upgrade_available = False
        next_tier = None
        next_tier_info = None

        tier_progression = {
            'solo': 'team_5',
            'team_5': 'team_10',
            'team_10': 'institute_15',
            'institute_15': 'institute_20',
            # Legacy plan mappings for backward compatibility
            'starter': 'team_5',
            'professional': 'team_5',
            'clinic': 'team_10',
            'institute_5': 'team_10',
            'institute_10': 'institute_15'
        }

        if plan_type in tier_progression:
            next_tier = tier_progression[plan_type]
            upgrade_available = True
            next_tier_plan = PLANS.get(next_tier, {})
            next_tier_info = {
                'plan_type': next_tier,
                'name': next_tier_plan.get('name'),
                'price': next_tier_plan.get('price'),
                'max_users': next_tier_plan.get('max_users'),
                'patients_limit': next_tier_plan.get('patients_limit'),
                'ai_calls_limit': next_tier_plan.get('ai_calls_limit')
            }

        log_audit('check_user_limit', {
            'institute_id': institute_id,
            'current_users': current_users,
            'max_users': max_users
        })

        return jsonify({
            'can_add_user': can_add,
            'current_users': current_users,
            'max_users': max_users,
            'message': message,
            'upgrade_available': upgrade_available,
            'next_tier': next_tier,
            'next_tier_info': next_tier_info
        }), 200

    except Exception as e:
        logger.error(f"Error checking user limit: {e}")
        return jsonify({'error': 'Failed to check user limit'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN PURCHASE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route('/tokens/packages', methods=['GET'])
def api_get_token_packages():
    """
    Get available AI call packages

    Response:
    {
        "packages": {
            "starter": {"calls": 25, "price": 325, "per_call": 13.00, "name": "Starter Pack"},
            "regular": {"calls": 50, "price": 599, "per_call": 11.98, "name": "Regular Pack"},
            ...
        }
    }
    """
    try:
        from subscription_manager import get_token_packages

        packages = get_token_packages()

        return jsonify({'packages': packages}), 200

    except Exception as e:
        logger.error(f"Error fetching token packages: {e}")
        return jsonify({'error': 'Failed to fetch token packages'}), 500


@mobile_api.route('/tokens/checkout', methods=['POST'])
@require_auth
def api_create_token_checkout():
    """
    Create a Razorpay order for token purchase

    Request body:
    {
        "package": "regular"
    }

    Response:
    {
        "checkout_data": {
            "order_id": "order_...",
            "razorpay_key": "rzp_...",
            "amount": 17900,
            "currency": "INR",
            "name": "User Name",
            "email": "user@example.com",
            "phone": "1234567890",
            "description": "100 AI Tokens"
        }
    }
    """
    try:
        from razorpay_integration import create_token_purchase_order

        data = request.get_json()
        package = data.get('package')

        if not package:
            return jsonify({'error': 'package required'}), 400

        user_id = g.user.get('email') or g.user.get('uid')
        user_name = g.user.get('name', '')
        user_email = g.user.get('email', '')
        user_phone = g.user.get('phone', '')

        checkout_data = create_token_purchase_order(
            user_id=user_id,
            package=package,
            user_name=user_name,
            user_email=user_email,
            user_phone=user_phone
        )

        if not checkout_data:
            return jsonify({'error': 'Failed to create checkout'}), 500

        log_audit('token_checkout_created', {'package': package})

        return jsonify({'checkout_data': checkout_data}), 200

    except Exception as e:
        logger.error(f"Error creating token checkout: {e}")
        return jsonify({'error': 'Failed to create checkout'}), 500


@mobile_api.route('/tokens/verify', methods=['POST'])
@require_auth
def api_verify_token_payment():
    """
    Verify token payment and add tokens to account

    Request body:
    {
        "razorpay_order_id": "order_...",
        "razorpay_payment_id": "pay_...",
        "razorpay_signature": "...",
        "package": "regular"
    }

    Response:
    {
        "success": true,
        "message": "100 tokens added to your account",
        "new_balance": 150
    }
    """
    try:
        from razorpay_integration import verify_token_payment
        from subscription_manager import purchase_tokens, get_user_subscription

        data = request.get_json()
        order_id = data.get('razorpay_order_id')
        payment_id = data.get('razorpay_payment_id')
        signature = data.get('razorpay_signature')
        package = data.get('package')

        if not all([order_id, payment_id, signature, package]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Verify payment signature
        is_valid = verify_token_payment(order_id, payment_id, signature)

        if not is_valid:
            return jsonify({'error': 'Payment verification failed'}), 400

        # Add tokens
        user_id = g.user.get('email') or g.user.get('uid')

        success = purchase_tokens(
            user_id=user_id,
            package=package,
            payment_id=payment_id,
            transaction_data={'order_id': order_id}
        )

        if not success:
            return jsonify({'error': 'Failed to add tokens'}), 500

        # Get new balance
        subscription = get_user_subscription(user_id)
        new_balance = subscription.get('ai_tokens_balance', 0)

        from subscription_manager import TOKEN_PACKAGES
        tokens_added = TOKEN_PACKAGES.get(package, {}).get('tokens', 0)

        log_audit('tokens_purchased', {'package': package, 'tokens': tokens_added})

        return jsonify({
            'success': True,
            'message': f'{tokens_added} tokens added to your account',
            'new_balance': new_balance
        }), 200

    except Exception as e:
        logger.error(f"Error verifying token payment: {e}")
        return jsonify({'error': 'Payment verification failed'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# PROFILE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route('/users/profile', methods=['GET'])
@require_firebase_auth
def get_user_profile():
    """
    Get current user's profile information
    """
    try:
        user_email = g.user.get('email')

        # Get user document from Cosmos DB
        user_ref = db.collection('users').document(user_email)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({'error': 'User not found'}), 404

        user_data = user_doc.to_dict()

        # Remove sensitive fields
        user_data.pop('password_hash', None)
        user_data['email'] = user_email

        log_audit('Get Profile', {'email': user_email})

        return jsonify({
            'success': True,
            'profile': user_data
        }), 200

    except Exception as e:
        logger.error(f'Error getting profile: {e}', exc_info=True)
        return jsonify({'error': 'Failed to get profile'}), 500


@mobile_api.route('/users/update-profile', methods=['POST'])
@require_firebase_auth
def update_user_profile():
    """
    Update user profile (name, phone, consents)
    Does NOT include password change
    """
    try:
        user_email = g.user.get('email')
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate required fields
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()

        if not name:
            return jsonify({'error': 'Name is required'}), 400

        # Prepare updates
        updates = {
            'name': name,
            'phone': phone,
            'consent_ai': 1 if data.get('consent_ai') else 0
        }

        # Update user document
        user_ref = db.collection('users').document(user_email)
        user_ref.update(updates)

        log_audit('Profile Update', {
            'email': user_email,
            'fields_updated': ', '.join(updates.keys())
        })

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        }), 200

    except Exception as e:
        logger.error(f'Error updating profile: {e}', exc_info=True)
        return jsonify({'error': 'Failed to update profile'}), 500


@mobile_api.route('/users/change-password', methods=['POST'])
@require_firebase_auth
def change_user_password():
    """
    Change user password
    Returns success=True to indicate logout is needed on client side
    """
    try:
        user_email = g.user.get('email')
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        current_password = data.get('current_password', '').strip()
        new_password = data.get('new_password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()

        # Validate inputs
        if not current_password or not new_password or not confirm_password:
            return jsonify({'error': 'All password fields are required'}), 400

        if new_password != confirm_password:
            return jsonify({'error': 'New passwords do not match'}), 400

        if len(new_password) < 8:
            return jsonify({'error': 'New password must be at least 8 characters'}), 400

        # Verify current password using Cosmos DB (like web app)
        from werkzeug.security import check_password_hash, generate_password_hash
        user_doc = db.collection('users').document(user_email).get()

        if not user_doc.exists:
            return jsonify({'error': 'User not found'}), 404

        user_data = user_doc.to_dict()
        password_hash = user_data.get('password_hash', '')

        if not password_hash or not check_password_hash(password_hash, current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Get Firebase UID for updating Firebase Auth
        firebase_uid = user_data.get('firebase_uid')

        # Update password in Firebase Auth if user has Firebase UID
        if firebase_uid:
            try:
                auth.update_user(
                    firebase_uid,
                    password=new_password
                )
            except Exception as auth_error:
                logger.error(f'Firebase Auth password update failed: {auth_error}')
                # Continue anyway to update Cosmos DB

        # Update password_hash and timestamp in Cosmos DB
        user_ref = db.collection('users').document(user_email)
        user_ref.update({
            'password_hash': generate_password_hash(new_password),
            'password_changed_at': SERVER_TIMESTAMP
        })

        log_audit('Password Change', {
            'email': user_email,
            'source': 'mobile_app'
        })

        # Return success=True and logout_required=True
        # Client should clear tokens and redirect to login
        return jsonify({
            'success': True,
            'logout_required': True,
            'message': 'Password changed successfully. Please log in with your new password.'
        }), 200

    except Exception as e:
        logger.error(f'Error changing password: {e}', exc_info=True)
        return jsonify({'error': 'Failed to change password'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE MANAGEMENT ENDPOINTS (GST COMPLIANCE)
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route('/invoices', methods=['GET'])
@require_firebase_auth
def api_get_invoices():
    """
    Get all invoices for the current user

    Response:
    {
        "success": true,
        "invoices": [
            {
                "invoice_id": "abc123",
                "invoice_number": "INV-2025-0001",
                "invoice_date": "2025-01-18",
                "description": "Professional Plan Subscription",
                "base_amount": 847.46,
                "cgst": 76.27,
                "sgst": 76.27,
                "total_amount": 1000.00,
                "currency": "INR",
                "status": "paid"
            }
        ]
    }
    """
    try:
        user = g.user
        user_email = user.get('email')

        if not user_email:
            return jsonify({'success': False, 'error': 'User email not found'}), 400

        # Get all invoices for this user
        invoices_ref = db.collection('invoices')
        query = invoices_ref.where('user_id', '==', user_email).order_by('invoice_date', direction='DESCENDING')
        invoices = query.stream()

        invoices_list = []
        for invoice_doc in invoices:
            invoice_data = invoice_doc.to_dict()

            # Convert timestamp to string for JSON serialization
            if invoice_data.get('invoice_date'):
                try:
                    invoice_data['invoice_date'] = invoice_data['invoice_date'].strftime('%Y-%m-%d')
                except:
                    invoice_data['invoice_date'] = None

            # Add invoice_id
            invoice_data['invoice_id'] = invoice_doc.id

            # Remove sensitive business details (keep only necessary fields)
            simplified_invoice = {
                'invoice_id': invoice_data.get('invoice_id'),
                'invoice_number': invoice_data.get('invoice_number'),
                'invoice_date': invoice_data.get('invoice_date'),
                'description': invoice_data.get('description'),
                'base_amount': invoice_data.get('base_amount'),
                'cgst': invoice_data.get('cgst'),
                'sgst': invoice_data.get('sgst'),
                'igst': invoice_data.get('igst'),
                'gst_rate': invoice_data.get('gst_rate'),
                'total_amount': invoice_data.get('total_amount'),
                'currency': invoice_data.get('currency'),
                'status': invoice_data.get('status'),
                'payment_id': invoice_data.get('payment_id'),
                'payment_method': invoice_data.get('payment_method')
            }

            invoices_list.append(simplified_invoice)

        log_audit('mobile_view_invoices', {'email': user_email, 'count': len(invoices_list)})

        return jsonify({
            'success': True,
            'invoices': invoices_list
        }), 200

    except Exception as e:
        logger.error(f'Error fetching invoices: {e}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to fetch invoices'}), 500


@mobile_api.route('/invoices/<invoice_id>', methods=['GET'])
@require_firebase_auth
def api_get_invoice_details(invoice_id):
    """
    Get single invoice details

    Response:
    {
        "success": true,
        "invoice": {
            // Full invoice details
        }
    }
    """
    try:
        user = g.user
        user_email = user.get('email')

        if not user_email:
            return jsonify({'success': False, 'error': 'User email not found'}), 400

        # Get invoice
        invoice_ref = db.collection('invoices').document(invoice_id)
        invoice_doc = invoice_ref.get()

        if not invoice_doc.exists:
            return jsonify({'success': False, 'error': 'Invoice not found'}), 404

        invoice_data = invoice_doc.to_dict()

        # Security: Verify invoice belongs to current user
        if invoice_data.get('user_id') != user_email:
            logger.warning(f'Unauthorized invoice access attempt: {user_email} tried to access invoice {invoice_id}')
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        # Convert timestamp to string
        if invoice_data.get('invoice_date'):
            try:
                invoice_data['invoice_date'] = invoice_data['invoice_date'].strftime('%Y-%m-%d')
            except:
                invoice_data['invoice_date'] = None

        invoice_data['invoice_id'] = invoice_id

        log_audit('mobile_view_invoice', {'email': user_email, 'invoice_number': invoice_data.get('invoice_number')})

        return jsonify({
            'success': True,
            'invoice': invoice_data
        }), 200

    except Exception as e:
        logger.error(f'Error fetching invoice details: {e}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to fetch invoice'}), 500


@mobile_api.route('/invoices/<invoice_id>/download', methods=['GET'])
@require_firebase_auth
def api_download_invoice(invoice_id):
    """
    Download invoice as PDF (returns base64 encoded PDF)

    Response:
    {
        "success": true,
        "pdf_base64": "JVBERi0xLjQKJeLjz9MK...",
        "filename": "INV-2025-0001.pdf"
    }
    """
    try:
        user = g.user
        user_email = user.get('email')

        if not user_email:
            return jsonify({'success': False, 'error': 'User email not found'}), 400

        # Get invoice
        invoice_ref = db.collection('invoices').document(invoice_id)
        invoice_doc = invoice_ref.get()

        if not invoice_doc.exists:
            return jsonify({'success': False, 'error': 'Invoice not found'}), 404

        invoice_data = invoice_doc.to_dict()

        # Security: Verify invoice belongs to current user
        if invoice_data.get('user_id') != user_email:
            logger.warning(f'Unauthorized invoice download attempt: {user_email} tried to download invoice {invoice_id}')
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        # Generate PDF
        from invoice_generator import generate_invoice_pdf
        import base64

        pdf_content = generate_invoice_pdf(invoice_data)

        if not pdf_content:
            return jsonify({'success': False, 'error': 'Failed to generate PDF'}), 500

        # Convert PDF to base64 for mobile transmission
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

        invoice_number = invoice_data.get('invoice_number', 'invoice')
        filename = f"{invoice_number}.pdf"

        log_audit('mobile_download_invoice', {'email': user_email, 'invoice_number': invoice_number})

        return jsonify({
            'success': True,
            'pdf_base64': pdf_base64,
            'filename': filename,
            'invoice_number': invoice_number
        }), 200

    except Exception as e:
        logger.error(f'Error downloading invoice: {e}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to download invoice'}), 500


#────────────────────────────────────────────────────────────────────────────
# DASHBOARD ANALYTICS ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route('/dashboard/analytics', methods=['GET'])
@require_auth
def api_get_dashboard_analytics():
    """
    Get dashboard analytics and usage statistics

    Response:
    {
        "success": true,
        "analytics": {
            "plan_type": "solo",
            "plan_name": "Solo Professional",
            "status": "active",
            "patients_used": 15,
            "patients_limit": -1,
            "patients_percent": 0,
            "ai_calls_used": 45,
            "ai_calls_limit": 100,
            "ai_percent": 45,
            "tokens_balance": 50,
            "total_patients": 45,
            "recent_patients": 15,
            "days_until_renewal": 25,
            "renewal_date": "2025-02-15",
            "cache_hit_rate": 35.5,
            "cache_savings_usd": 12.50
        }
    }
    """
    try:
        user = g.user
        user_email = user.get('email')

        if not user_email:
            return jsonify({'success': False, 'error': 'User email not found'}), 400

        # Get subscription and usage data
        from subscription_manager import get_usage_stats, PLANS
        from datetime import datetime, timedelta

        usage_stats = get_usage_stats(user_email)

        # Get plan details
        plan_type = usage_stats.get('plan_type', 'free_trial')
        plan_info = PLANS.get(plan_type, {})

        # Get total patient count (all time)
        patients_ref = db.collection('patients').where('created_by', '==', user_email)
        total_patients = len(list(patients_ref.stream()))

        # Get recent patients (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        # Convert to ISO format string for Cosmos DB query
        thirty_days_ago_iso = thirty_days_ago.isoformat()
        recent_patients_ref = patients_ref.where('created_at', '>=', thirty_days_ago_iso)
        recent_patients_count = len(list(recent_patients_ref.stream()))

        # Get cache statistics
        from ai_cache import AICache
        ai_cache = AICache(db)
        cache_stats = ai_cache.get_cache_statistics(days=30) or {}

        # Calculate days until renewal/expiry
        days_until_renewal = None
        renewal_date = None
        show_renewal_warning = False

        if usage_stats.get('period_end'):
            try:
                period_end = usage_stats['period_end']
                # Handle Cosmos DB ISO strings and Firestore timestamps
                if isinstance(period_end, str):
                    period_end = datetime.fromisoformat(period_end.replace('Z', '+00:00'))
                elif hasattr(period_end, 'timestamp'):
                    # Firestore timestamp - already a datetime-like object
                    pass

                if period_end:
                    renewal_date = period_end.strftime('%Y-%m-%d')
                    # Make timezone-naive for comparison
                    period_end_naive = period_end.replace(tzinfo=None) if period_end.tzinfo else period_end
                    days_until_renewal = (period_end_naive - datetime.utcnow()).days
                    show_renewal_warning = days_until_renewal <= 5
            except:
                pass
        elif usage_stats.get('trial_end'):
            try:
                trial_end = usage_stats['trial_end']
                # Handle Cosmos DB ISO strings and Firestore timestamps
                if isinstance(trial_end, str):
                    trial_end = datetime.fromisoformat(trial_end.replace('Z', '+00:00'))
                elif hasattr(trial_end, 'timestamp'):
                    # Firestore timestamp - already a datetime-like object
                    pass

                if trial_end:
                    renewal_date = trial_end.strftime('%Y-%m-%d')
                    # Make timezone-naive for comparison
                    trial_end_naive = trial_end.replace(tzinfo=None) if trial_end.tzinfo else trial_end
                    days_until_renewal = (trial_end_naive - datetime.utcnow()).days
                    show_renewal_warning = days_until_renewal <= 3
            except:
                pass

        # Determine quota status
        patients_status = 'success' if usage_stats.get('patients_percent', 0) < 70 else ('warning' if usage_stats.get('patients_percent', 0) < 90 else 'danger')
        ai_status = 'success' if usage_stats.get('ai_percent', 0) < 70 else ('warning' if usage_stats.get('ai_percent', 0) < 90 else 'danger')

        analytics = {
            # Plan information
            'plan_type': plan_type,
            'plan_name': plan_info.get('name', 'Unknown'),
            'plan_price': plan_info.get('price', 0),
            'status': usage_stats.get('status', 'unknown'),

            # Usage statistics
            'patients_used': usage_stats.get('patients_used', 0),
            'patients_limit': usage_stats.get('patients_limit', 0),
            'patients_percent': usage_stats.get('patients_percent', 0),
            'ai_calls_used': usage_stats.get('ai_calls_used', 0),
            'ai_calls_limit': usage_stats.get('ai_calls_limit', 0),
            'ai_percent': usage_stats.get('ai_percent', 0),
            'tokens_balance': usage_stats.get('tokens_balance', 0),

            # Patient statistics
            'total_patients': total_patients,
            'recent_patients': recent_patients_count,

            # Renewal information
            'days_until_renewal': days_until_renewal,
            'renewal_date': renewal_date,
            'show_renewal_warning': show_renewal_warning,

            # Cache statistics
            'cache_hit_rate': cache_stats.get('hit_rate_percent', 0),
            'cache_savings_usd': cache_stats.get('total_savings_usd', 0),
            'cache_hits': cache_stats.get('cache_hits', 0),
            'cache_misses': cache_stats.get('cache_misses', 0),

            # Status indicators
            'patients_status': patients_status,
            'ai_status': ai_status,
        }

        log_audit('mobile_view_analytics', {'email': user_email})

        return jsonify({
            'success': True,
            'analytics': analytics
        }), 200

    except Exception as e:
        logger.error(f'Error fetching dashboard analytics: {e}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to fetch analytics'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# DRAFT AUTO-SAVE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route('/draft/save', methods=['POST'])
@require_auth
def api_save_draft():
    """
    Auto-save form draft data for mobile app
    Stores partial form data so users can resume later
    """
    try:
        data = request.get_json() or {}

        form_type = data.get('form_type')
        patient_id = data.get('patient_id')
        form_data = data.get('form_data', {})

        if not form_type or not patient_id:
            return jsonify({'ok': False, 'error': 'Missing form_type or patient_id'}), 400

        user_email = g.user.get('email')

        # For new patient forms, skip patient verification since patient doesn't exist yet
        if patient_id != 'new_patient' and form_type != 'add_patient':
            # Verify user has access to this patient
            patient_doc = db.collection('patients').document(patient_id).get()

            if not patient_doc.exists:
                return jsonify({'ok': False, 'error': 'Patient not found'}), 404

            patient = patient_doc.to_dict()

            # Access control
            if g.user.get('is_admin') != 1 and patient.get('physio_id') != user_email:
                return jsonify({'ok': False, 'error': 'Access denied'}), 403

        # Create unique draft ID: user_email + patient_id + form_type
        draft_id = f"{user_email}_{patient_id}_{form_type}"

        # Save or update draft
        draft_ref = db.collection('form_drafts').document(draft_id)
        existing_draft = draft_ref.get()

        draft_ref.set({
            'user_id': user_email,
            'patient_id': patient_id,
            'form_type': form_type,
            'form_data': form_data,
            'updated_at': SERVER_TIMESTAMP,
            'created_at': existing_draft.to_dict().get('created_at') if existing_draft.exists else SERVER_TIMESTAMP
        }, merge=True)

        logger.info(f"Draft saved: {draft_id}")

        return jsonify({
            'ok': True,
            'message': 'Draft saved',
            'draft_id': draft_id
        }), 200

    except Exception as e:
        logger.error(f"Error saving draft: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@mobile_api.route('/draft/get/<patient_id>/<form_type>', methods=['GET'])
@require_auth
def api_get_draft(patient_id, form_type):
    """
    Retrieve saved draft for a form
    """
    try:
        user_email = g.user.get('email')

        # For new patient forms, skip patient verification since patient doesn't exist yet
        if patient_id != 'new_patient' and form_type != 'add_patient':
            # Verify user has access to this patient
            patient_doc = db.collection('patients').document(patient_id).get()

            if not patient_doc.exists:
                return jsonify({'ok': False, 'error': 'Patient not found'}), 404

            patient = patient_doc.to_dict()

            # Access control
            if g.user.get('is_admin') != 1 and patient.get('physio_id') != user_email:
                return jsonify({'ok': False, 'error': 'Access denied'}), 403

        # Get draft
        draft_id = f"{user_email}_{patient_id}_{form_type}"
        draft_doc = db.collection('form_drafts').document(draft_id).get()

        if not draft_doc.exists:
            return jsonify({
                'ok': True,
                'has_draft': False,
                'draft_data': None
            }), 200

        draft = draft_doc.to_dict()

        return jsonify({
            'ok': True,
            'has_draft': True,
            'draft_data': draft.get('form_data', {}),
            'updated_at': draft.get('updated_at'),
            'created_at': draft.get('created_at')
        }), 200

    except Exception as e:
        logger.error(f"Error getting draft: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@mobile_api.route('/draft/delete/<patient_id>/<form_type>', methods=['DELETE'])
@require_auth
def api_delete_draft(patient_id, form_type):
    """
    Delete a saved draft (after successful form submission)
    """
    try:
        user_email = g.user.get('email')

        # Delete draft
        draft_id = f"{user_email}_{patient_id}_{form_type}"
        db.collection('form_drafts').document(draft_id).delete()

        logger.info(f"Draft deleted: {draft_id}")

        return jsonify({
            'ok': True,
            'message': 'Draft deleted'
        }), 200

    except Exception as e:
        logger.error(f"Error deleting draft: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@mobile_api.route('/health', methods=['GET'])
def api_health():
    """
    Comprehensive health check endpoint for monitoring.

    Checks the health of all critical systems:
    - Cosmos DB database connection
    - Redis cache connection
    - OpenAI API availability (if enabled)

    Returns:
        200 OK if all systems healthy
        503 Service Unavailable if any critical system is down

    Response format:
        {
            "status": "healthy" | "unhealthy",
            "timestamp": "2025-12-19T10:30:00Z",
            "checks": {
                "Cosmos DB": "ok" | "error",
                "redis": "ok" | "degraded" | "error"
            }
        }
    """
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'checks': {}
    }

    # Check Cosmos DB connection
    try:
        # Perform a simple read operation to verify Cosmos DB is accessible
        # Using limit(1) to minimize data transfer
        test_query = db.collection('users').limit(1).get()
        health_status['checks']['Cosmos DB'] = 'ok'
        logger.debug("Health check: Cosmos DB OK")
    except Exception as e:
        health_status['checks']['Cosmos DB'] = 'error'
        health_status['status'] = 'unhealthy'
        logger.error(f"Health check: Cosmos DB failed - {str(e)}")

    # Check Redis connection
    try:
        if redis_available and redis_client:
            # Test Redis connection with ping
            redis_client.ping()
            health_status['checks']['redis'] = 'ok'
            logger.debug("Health check: Redis OK")
        else:
            # Redis not available, using in-memory fallback
            health_status['checks']['redis'] = 'degraded'
            logger.debug("Health check: Redis degraded (using in-memory fallback)")
    except Exception as e:
        health_status['checks']['redis'] = 'error'
        health_status['status'] = 'unhealthy'
        logger.error(f"Health check: Redis failed - {str(e)}")

    # Determine HTTP status code
    status_code = 200 if health_status['status'] == 'healthy' else 503

    return jsonify(health_status), status_code
