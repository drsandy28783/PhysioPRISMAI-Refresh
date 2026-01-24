import os
import io
import json
import csv
import uuid
import secrets
import string
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─── ENVIRONMENT VALIDATION ──────────────────────────────────────────
# Validate required environment variables at startup (fail fast)
# Note: Uses print() instead of logger as logging isn't set up yet

def validate_required_env_vars():
    """
    Validate that all required environment variables are set.
    Fail fast with clear error messages if any are missing.

    This prevents the app from starting with missing configuration,
    which could lead to runtime errors or security issues.
    """
    required_vars = {
        'SECRET_KEY': {
            'description': 'Flask secret key for session encryption',
            'how_to_fix': 'Generate with: python -c "import secrets; print(secrets.token_hex(32))"',
            'required_in': ['local', 'production']
        },
        'RESEND_API_KEY': {
            'description': 'Resend API key for sending emails',
            'how_to_fix': 'Get from https://resend.com/api-keys',
            'required_in': ['local', 'production']
        },
    }

    # Check which environment we're in
    is_cloud_run = bool(os.environ.get('K_SERVICE'))  # Cloud Run sets this
    environment = 'production' if is_cloud_run else 'local'

    missing_vars = []

    for var_name, var_info in required_vars.items():
        if environment in var_info['required_in']:
            if not os.environ.get(var_name):
                missing_vars.append((var_name, var_info))

    if missing_vars:
        print("\n" + "=" * 70, file=sys.stderr)
        print("❌ CRITICAL: Required environment variables missing!", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print("ENVIRONMENT CONFIGURATION ERROR", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f"\nEnvironment: {environment.upper()}", file=sys.stderr)
        print(f"Missing {len(missing_vars)} required variable(s):\n", file=sys.stderr)

        for var_name, var_info in missing_vars:
            print(f"  ❌ {var_name}", file=sys.stderr)
            print(f"     Purpose: {var_info['description']}", file=sys.stderr)
            print(f"     Fix: {var_info['how_to_fix']}", file=sys.stderr)
            print("", file=sys.stderr)

        print("📋 HOW TO FIX:\n", file=sys.stderr)
        if environment == 'local':
            print("For LOCAL DEVELOPMENT:", file=sys.stderr)
            print("  1. Copy .env.example to .env", file=sys.stderr)
            print("  2. Fill in the missing values", file=sys.stderr)
            print("  3. Restart the application", file=sys.stderr)
        else:
            print("For CLOUD RUN DEPLOYMENT:", file=sys.stderr)
            print("  1. Store secrets in Google Secret Manager", file=sys.stderr)
            print("  2. Update Cloud Run service to use secrets", file=sys.stderr)
            print("  3. See: GOOGLE_CLOUD_DEPLOYMENT.md", file=sys.stderr)
        print("\n" + "=" * 70 + "\n", file=sys.stderr)

        raise ValueError(
            f"Missing required environment variables: {', '.join([v[0] for v in missing_vars])}. "
            f"See error output above for details."
        )

    print(f"[OK] All required environment variables configured for {environment}")

# Run validation at import time (before any other imports that might use env vars)
validate_required_env_vars()
# ─────────────────────────────────────────────────────────────────────

from flask import (Flask, render_template, request, redirect, session, url_for, flash, jsonify, make_response, g, current_app)
from datetime import datetime, timedelta
from flask_login import login_required
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from flask_cors import CORS
from flask_talisman import Talisman
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from xhtml2pdf import pisa
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from app_auth import require_firebase_auth, require_firebase_auth_with_rate_limit, require_auth
from ai_cache import AICache, get_ai_suggestion_with_cache
from rate_limiter import (
    limiter,
    check_login_attempts,
    record_failed_login,
    clear_login_attempts,
    get_rate_limit_stats,
    redis_client,
    redis_available
)
from schemas import (
    PatientSchema,
    SubjectiveExaminationSchema,
    AIPromptSchema,
    SubscriptionCheckoutSchema,
    TokenPurchaseSchema,
    PaymentVerificationSchema,
    FollowUpSchema,
    # New schemas for comprehensive validation
    UserRegistrationSchema,
    LoginSchema,
    ProfileUpdateSchema,
    ProvisionalDiagnosisSchema,
    PatientStatusSchema,
    PatientTagsSchema,
    SubscriptionCancelSchema,
    RazorpayWebhookSchema,
    FollowUpScheduleSchema,
    InstituteStaffApprovalSchema,
    InstituteRegistrationSchema,
    ForgotPasswordSchema,
    ResetPasswordSchema,
    EmailVerificationSchema,
    ResendVerificationSchema,
    Enable2FASchema,
    Disable2FASchema,
    Verify2FASchema,
    DraftSaveSchema,
    BlogPostSchema,
    NotificationActionSchema,
    DataDeletionRequestSchema,
    TOSAcceptanceSchema,
    AccessRequestSchema,
    SyncUserSchema,
    validate_data,
    validate_json
)
from ai_prompts import (
    get_past_questions_prompt,
    get_subjective_field_prompt,
    get_subjective_diagnosis_prompt,
    get_patient_perspectives_field_prompt,
    get_patient_perspectives_prompt,
    get_provisional_diagnosis_prompt,
    get_objective_assessment_prompt,
    get_pathophysiology_prompt,
    get_chronic_factors_prompt,
    get_clinical_flags_prompt,
    get_initial_plan_field_prompt,
    get_initial_plan_summary_prompt,
    get_smart_goals_prompt,
    get_treatment_plan_field_prompt,
    get_treatment_plan_summary_prompt,
    get_provisional_diagnosis_field_prompt,
    get_followup_prompt,
    get_generic_field_prompt
)
from email_service import (
    send_registration_notification,
    send_approval_notification,
    send_institute_admin_registration_notification,
    send_institute_staff_registration_notification,
    send_institute_staff_approval_notification,
    send_password_reset_notification,
    send_email_verification
)
import logging
import time
from collections import defaultdict

# ===== AZURE SERVICES (HIPAA BAA Compliant) =====
# Azure Cosmos DB (replaces Firebase Firestore)
from azure_cosmos_db import (
    get_cosmos_db,
    SERVER_TIMESTAMP,
    DELETE_FIELD,
    Increment,
    CosmosDBDocument,
    CosmosDBQuery
)

# Azure OpenAI (replaces Vertex AI)
from azure_openai_client import (
    get_azure_openai_client,
    get_system_prompt,
    AzureOpenAIClient
)

# Azure AD B2C (replaces Firebase Auth)
from azure_ad_b2c_auth import (
    get_azure_b2c,
    is_b2c_configured,
    require_b2c_auth
)

# Exception classes for error handling
class AzureOpenAIError(Exception):
    """Azure OpenAI API error"""
    pass

class CosmosDBError(Exception):
    """Cosmos DB error"""
    pass

import json, logging, sys

# ---- Google Cloud friendly structured logging ----
class GCPJsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "severity": record.levelname,
            "message": record.getMessage(),
        }
        return json.dumps(payload, ensure_ascii=False)

_root = logging.getLogger()                 # root logger
_root.handlers = []                         # remove default handlers
_stream = logging.StreamHandler(sys.stdout) # Cloud Run reads stdout/stderr
_stream.setFormatter(GCPJsonFormatter())
_root.addHandler(_stream)
_root.setLevel(logging.INFO)                # use DEBUG during troubleshooting
# --------------------------------------------------

logger = logging.getLogger("app")           # module logger you can keep using



# Rate limiting now handled by rate_limiter.py (Redis-based)
# Old in-memory implementation removed for production readiness

# HIPAA Compliance Configuration
HIPAA_COMPLIANT_MODE = os.environ.get('HIPAA_COMPLIANT_MODE', 'false').lower() == 'true'

# Terms of Service Version - Update this when ToS is modified
# Increment minor version (1.1, 1.2) for minor changes - shows notification only
# Increment major version (2.0, 3.0) for significant changes - requires re-acceptance
TOS_VERSION = '1.0'
TOS_LAST_UPDATED = '2025-01-01'  # Update this date when ToS changes

def compare_tos_versions(user_version, current_version):
    """
    Compare ToS versions and determine if re-acceptance is required.

    Returns:
        dict with:
        - 'requires_acceptance': True if major version changed (blocking)
        - 'has_updates': True if any version changed (for notification)
        - 'user_major': User's major version number
        - 'current_major': Current major version number
    """
    try:
        user_parts = user_version.split('.')
        current_parts = current_version.split('.')

        user_major = int(user_parts[0]) if user_parts else 0
        current_major = int(current_parts[0]) if current_parts else 1

        user_minor = int(user_parts[1]) if len(user_parts) > 1 else 0
        current_minor = int(current_parts[1]) if len(current_parts) > 1 else 0

        # Major version change requires re-acceptance
        requires_acceptance = user_major < current_major

        # Any version change should show notification
        has_updates = (user_major != current_major) or (user_minor != current_minor)

        return {
            'requires_acceptance': requires_acceptance,
            'has_updates': has_updates,
            'user_major': user_major,
            'current_major': current_major
        }
    except (ValueError, AttributeError):
        # If parsing fails, require acceptance for safety
        return {
            'requires_acceptance': True,
            'has_updates': True,
            'user_major': 0,
            'current_major': 1
        }

# ===== AZURE OPENAI CLIENT INITIALIZATION =====
# Initialize Azure OpenAI client (GPT-4o)
# HIPAA compliant mode is now ALWAYS enabled with Azure (we have BAA!)
client = None
try:
    client = get_azure_openai_client()
    logger.info("✅ Using Azure OpenAI GPT-4o - AI features enabled (HIPAA BAA covered)")
    logger.info(f"✅ Azure OpenAI endpoint: {client.endpoint}")
    logger.info(f"✅ Deployment: {client.deployment_name}")
except Exception as e:
    logger.error(f"❌ Failed to initialize Azure OpenAI client: {e}")
    logger.error("AI features will be disabled")
    client = None

# Note: HIPAA_COMPLIANT_MODE can stay 'true' - Azure OpenAI is HIPAA compliant!
# We no longer disable AI in HIPAA mode since we have BAA with Microsoft
if HIPAA_COMPLIANT_MODE and client:
    logger.info("✅ HIPAA compliant mode: Enabled with Azure OpenAI (BAA active)")
# ────────────────────────────────────────────────────────────


# ─── FIRESTORE SETUP ────────────────────────────────
# ─── FIRESTORE SETUP (Key-less ADC Mode for Cloud Run) ────────────────────────────────

# ===== AZURE COSMOS DB INITIALIZATION =====
# Get Cosmos DB configuration from environment
COSMOS_DB_ENDPOINT = os.environ.get('COSMOS_DB_ENDPOINT')
COSMOS_DB_KEY = os.environ.get('COSMOS_DB_KEY')
COSMOS_DB_DATABASE_NAME = os.environ.get('COSMOS_DB_DATABASE_NAME', 'physiologicprism')

# Validate required Cosmos DB configuration
if not COSMOS_DB_ENDPOINT or not COSMOS_DB_KEY:
    logger.error("❌ CRITICAL: Azure Cosmos DB not configured!")
    logger.error("=" * 70)
    logger.error("COSMOS DB CONFIGURATION MISSING")
    logger.error("=" * 70)
    logger.error("")
    logger.error("The application requires Azure Cosmos DB connection to function.")
    logger.error("")
    logger.error("📋 HOW TO FIX:")
    logger.error("")
    logger.error("For LOCAL DEVELOPMENT:")
    logger.error("  1. Copy .env.azure to .env")
    logger.error("  2. Set COSMOS_DB_ENDPOINT and COSMOS_DB_KEY in .env file")
    logger.error("  3. Values are in AZURE_CREDENTIALS_CONFIRMED.md")
    logger.error("")
    logger.error("For AZURE CONTAINER APPS DEPLOYMENT:")
    logger.error("  Set environment variables in Container Apps configuration")
    logger.error("  Or use Azure Key Vault references")
    logger.error("")
    logger.error("For more help, see: AZURE_MIGRATION_PROGRESS.md")
    logger.error("=" * 70)
    raise ValueError(
        "Azure Cosmos DB configuration must be set via COSMOS_DB_ENDPOINT and COSMOS_DB_KEY environment variables. "
        "For local development: set in .env file. "
        "For Azure deployment: configure in Container Apps settings. "
        "See AZURE_MIGRATION_PROGRESS.md for setup instructions."
    )

logger.info(f"✅ Using Azure Cosmos DB: {COSMOS_DB_DATABASE_NAME}")

try:
    # Initialize Cosmos DB client
    db = get_cosmos_db()
    logger.info(f"✅ Cosmos DB client connected to database: {COSMOS_DB_DATABASE_NAME}")
    logger.info(f"✅ Cosmos DB endpoint: {COSMOS_DB_ENDPOINT}")
except Exception as e:
    logger.error(f"❌ Failed to initialize Azure Cosmos DB: {e}", exc_info=True)
    raise
# ─────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────


def get_ai_suggestion(prompt: str, metadata: dict = None) -> str:
    """
    Sends a prompt to Azure OpenAI GPT-4o and returns the assistant's reply.
    Uses intelligent caching to reduce costs and build training data.
    Now HIPAA compliant with Microsoft BAA!

    Args:
        prompt: The sanitized prompt (PHI-safe)
        metadata: Optional metadata for cache analytics (endpoint, tags, etc.)

    Returns:
        str: AI response (from cache or fresh API call)
    """
    # Check if AI client is available
    if client is None:
        return "AI service is not available. Please check configuration."

    try:
        # Azure OpenAI GPT-4o model
        model = "gpt-4o"

        # Use intelligent caching system
        # This will check cache first, then call AI API if cache miss
        response = get_ai_suggestion_with_cache(
            db=db,
            prompt=prompt,
            model=model,
            openai_client=client,
            metadata=metadata or {}
        )
        return response

    except (AzureOpenAIError, Exception) as e:
        logger.error(f"Azure OpenAI API error: {e}")
        return "AI service temporarily unavailable. Please try again."


def log_action(user_id, action, details=None):
    """Append an entry into Firestore `audit_logs` collection."""
    entry = {
        'user_id': user_id,
        'action': action,
        'details': details,
        'timestamp': SERVER_TIMESTAMP
    }
    db.collection('audit_logs').add(entry)

def generate_temp_password(length=12):
    """Generate a secure temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

def generate_reset_token():
    """Generate a secure password reset token."""
    return secrets.token_urlsafe(32)

def store_reset_token(db, email, token):
    """
    Store password reset token in Firestore user document.

    Args:
        db: Firestore database instance
        email: User's email address
        token: Reset token to store

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Token expires in 30 minutes
        expiry_time = datetime.utcnow() + timedelta(minutes=30)

        user_ref = db.collection('users').document(email)
        user_ref.update({
            'reset_token': token,
            'reset_token_expiry': expiry_time
        })

        logger.info(f"Password reset token stored for {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to store reset token for {email}: {str(e)}")
        return False

def verify_reset_token(db, token):
    """
    Verify password reset token and return user email if valid.

    Args:
        db: Firestore database instance
        token: Reset token to verify

    Returns:
        str or None: User email if token is valid, None otherwise
    """
    try:
        # Search for user with this token
        users_ref = db.collection('users')
        query = users_ref.where('reset_token', '==', token).limit(1)
        results = list(query.stream())

        if not results:
            logger.warning(f"No user found with reset token")
            return None

        user_doc = results[0]
        user_data = user_doc.to_dict()

        # Check if token has expired
        token_expiry = user_data.get('reset_token_expiry')
        if not token_expiry:
            logger.warning(f"Reset token has no expiry time")
            return None

        # Convert Firestore timestamp to datetime if needed
        if hasattr(token_expiry, 'timestamp'):
            token_expiry = datetime.fromtimestamp(token_expiry.timestamp())

        if datetime.utcnow() > token_expiry:
            logger.warning(f"Reset token expired for {user_doc.id}")
            return None

        logger.info(f"Valid reset token verified for {user_doc.id}")
        return user_doc.id  # Document ID is the email

    except Exception as e:
        logger.error(f"Error verifying reset token: {str(e)}")
        return None

def clear_reset_token(db, email):
    """
    Clear password reset token from user document.

    Args:
        db: Firestore database instance
        email: User's email address
    """
    try:
        user_ref = db.collection('users').document(email)
        user_ref.update({
            'reset_token': DELETE_FIELD,
            'reset_token_expiry': DELETE_FIELD
        })
        logger.info(f"Reset token cleared for {email}")
    except Exception as e:
        logger.error(f"Failed to clear reset token for {email}: {str(e)}")

def create_firebase_auth_account(email, name, temp_password=None):
    """
    Create a Firebase Authentication account for a user.

    Args:
        email: User's email address
        name: User's display name
        temp_password: Optional password. If not provided, generates one.

    Returns:
        dict: {'success': bool, 'uid': str, 'temp_password': str, 'error': str}
    """
    try:
        # Generate temp password if not provided
        if not temp_password:
            temp_password = generate_temp_password()

        # Create Firebase Auth user
        user_record = auth.create_user(
            email=email,
            password=temp_password,
            display_name=name,
            email_verified=False
        )

        logger.info(f"Created Firebase Auth account for {email}, UID: {user_record.uid}")

        return {
            'success': True,
            'uid': user_record.uid,
            'temp_password': temp_password,
            'error': None
        }

    except auth.EmailAlreadyExistsError:
        logger.warning(f"Firebase Auth account already exists for {email}")
        try:
            # Get existing user
            existing_user = auth.get_user_by_email(email)
            return {
                'success': True,
                'uid': existing_user.uid,
                'temp_password': None,  # Don't reset existing password
                'error': 'Account already exists'
            }
        except Exception as e:
            logger.error(f"Error getting existing Firebase Auth user {email}: {e}", exc_info=True)
            return {
                'success': False,
                'uid': None,
                'temp_password': None,
                'error': str(e)
            }
    except Exception as e:
        logger.error(f"Error creating Firebase Auth account for {email}: {e}", exc_info=True)
        return {
            'success': False,
            'uid': None,
            'temp_password': None,
            'error': str(e)
        }

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


# ─── PHI SANITIZATION FUNCTIONS ────────────────────────────────
import re

def sanitize_age_sex(age_sex_str):
    """Convert exact age to age range to protect PHI."""
    if not age_sex_str:
        return "Age/Sex not specified"
    
    # Extract age and sex
    match = re.search(r'(\d+)\s*([MF]|male|female)', age_sex_str.strip(), re.IGNORECASE)
    if not match:
        return "Demographics: Adult"
    
    age = int(match.group(1))
    sex = match.group(2).upper()[0]  # M or F
    
    # Convert to age ranges
    if age < 18:
        age_range = "Under 18"
    elif age < 30:
        age_range = "20s"
    elif age < 40:
        age_range = "30s"
    elif age < 50:
        age_range = "40s"
    elif age < 60:
        age_range = "50s"
    elif age < 70:
        age_range = "60s"
    else:
        age_range = "70+"
    
    return f"{age_range} {sex}"


def sanitize_clinical_text(text):
    """Remove PHI from clinical text while preserving clinical information."""
    if not text:
        return ""
    
    # Remove common PHI patterns
    sanitized = text
    
    # Remove specific dates (but keep relative time references)
    sanitized = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '[date removed]', sanitized)
    sanitized = re.sub(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4}\b', '[date removed]', sanitized, flags=re.IGNORECASE)
    
    # Remove proper names (preserve medical and anatomical terms)
    medical_terms = {
        # Medical abbreviations and facilities
        'MRI', 'CT', 'X-ray', 'PT', 'OT', 'Dr', 'Hospital', 'Clinic', 'Emergency', 'Department',
        # Body parts - general
        'Pain', 'Back', 'Knee', 'Shoulder', 'Hip', 'Neck', 'Arm', 'Leg', 'Ankle', 'Foot', 'Hand',
        'Wrist', 'Elbow', 'Spine', 'Lumbar', 'Thoracic', 'Cervical', 'Chest', 'Abdomen', 'Head',
        'Finger', 'Thumb', 'Toe', 'Heel', 'Calf', 'Thigh', 'Forearm', 'Pelvis', 'Groin', 'Buttock',
        # Directional terms
        'Right', 'Left', 'Bilateral', 'Anterior', 'Posterior', 'Lateral', 'Medial', 'Upper', 'Lower',
        'Proximal', 'Distal', 'Superior', 'Inferior', 'Dorsal', 'Ventral', 'Superficial', 'Deep',
        # Spinal regions
        'Sacral', 'Coccyx', 'Sacrum', 'Vertebral', 'Intervertebral', 'Disc',
        # Joints and structures
        'Joint', 'Muscle', 'Tendon', 'Ligament', 'Bone', 'Tissue', 'Nerve', 'Fascia'
    }
    words = sanitized.split()
    sanitized_words = []
    # Convert medical_terms to lowercase for case-insensitive matching
    medical_terms_lower = {term.lower() for term in medical_terms}
    for word in words:
        clean_word = re.sub(r'[^\w]', '', word)
        # Check if it's a capitalized word that's not a medical term
        if clean_word.istitle() and clean_word.lower() not in medical_terms_lower and len(clean_word) > 2:
            sanitized_words.append('[name removed]')
        else:
            sanitized_words.append(word)
    sanitized = ' '.join(sanitized_words)
    
    # Remove phone numbers
    sanitized = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[phone removed]', sanitized)
    
    # Remove addresses (simple pattern)
    sanitized = re.sub(r'\b\d+\s+\w+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)\b', '[address removed]', sanitized, flags=re.IGNORECASE)
    
    # Clean up multiple spaces
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    return sanitized


def sanitize_subjective_data(inputs_dict):
    """Sanitize subjective examination data to remove PHI."""
    if not inputs_dict:
        return {}
    
    sanitized = {}
    for key, value in inputs_dict.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_clinical_text(value)
        else:
            sanitized[key] = value
    
    return sanitized


# ============================================================================
# Utility Helpers (Output Constraints & Data Flattening)
# ============================================================================

def flatten_docs(docs_dict: dict) -> dict:
    """Flatten nested dict-of-docs into a single {field: value} map, dropping PHI-like keys."""
    if not isinstance(docs_dict, dict):
        return {}
    flat = {}
    for _doc_id, doc in docs_dict.items():
        if not isinstance(doc, dict):
            continue
        for k, v in doc.items():
            if k in ('patient_id', 'timestamp', 'created_by', 'uid', 'mrn'):
                continue
            if v is None or v == "":
                continue
            key = k if k not in flat else f"{k}_{_doc_id}"
            flat[key] = v
    return flat

def hard_limits(text: str, items: int, kind: str = "numbered list") -> str:
    """Append a firm output constraint to a prompt."""
    return (
        text
        + f"\nReturn only a {kind} of up to {items} items. "
          "Do not include headings, explanations, references, or any extra text."
    )


def sanitize_patient_data(data_dict):
    """Comprehensive sanitization of patient data for AI prompts."""
    sanitized = {}
    
    # Sanitize age/sex
    if 'age_sex' in data_dict:
        sanitized['demographics'] = sanitize_age_sex(data_dict['age_sex'])
    
    # Sanitize clinical histories
    if 'present_history' in data_dict:
        sanitized['clinical_presentation'] = sanitize_clinical_text(data_dict['present_history'])
    
    if 'past_history' in data_dict:
        sanitized['medical_background'] = sanitize_clinical_text(data_dict['past_history'])
    
    # Sanitize subjective findings
    if 'subjective' in data_dict:
        sanitized['clinical_findings'] = sanitize_subjective_data(data_dict['subjective'])
    
    # Sanitize other nested data
    for key, value in data_dict.items():
        if key not in ['age_sex', 'present_history', 'past_history', 'subjective']:
            if isinstance(value, dict):
                sanitized[key] = sanitize_subjective_data(value)
            elif isinstance(value, str):
                sanitized[key] = sanitize_clinical_text(value)
            else:
                sanitized[key] = value
    
    return sanitized
# ─────────────────────────────────────────────────────


app = Flask(__name__)

# Configure Flask to trust proxy headers from Firebase Hosting
# This fixes session/cookie issues when behind Firebase Hosting proxy
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,  # Trust 1 proxy for X-Forwarded-For
    x_proto=1,  # Trust 1 proxy for X-Forwarded-Proto
    x_host=1,  # Trust 1 proxy for X-Forwarded-Host
    x_port=1,  # Trust 1 proxy for X-Forwarded-Port
    x_prefix=1  # Trust 1 proxy for X-Forwarded-Prefix
)

# Security Configuration - HIPAA/GDPR Compliance
# Mandatory SECRET_KEY - no fallback for security
if not os.environ.get('SECRET_KEY'):
    logger.error("SECURITY ERROR: SECRET_KEY environment variable is required")
    raise ValueError("SECRET_KEY environment variable must be set for production")

app.secret_key = os.environ['SECRET_KEY']

# Secure Session Configuration
# Use server-side sessions to work with Firebase Hosting proxy
app.config.update(
    # Session Security
    # Using client-side sessions (signed cookies) for Cloud Run compatibility
    # Cloud Run is ephemeral and auto-scales, so filesystem sessions don't work
    SESSION_TYPE=None,  # Client-side sessions (signed cookie) - works across Cloud Run instances
    SESSION_COOKIE_SECURE=True,  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY=True,  # Prevent XSS access to cookies
    SESSION_COOKIE_SAMESITE='Lax',  # CSRF protection while allowing same-site navigation
    SESSION_COOKIE_PATH='/',  # Available across entire site
    SESSION_COOKIE_NAME='session',  # Explicit session cookie name
    SESSION_COOKIE_DOMAIN=None,  # No domain restriction - works with proxied requests
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),  # Session timeout
    SESSION_REFRESH_EACH_REQUEST=True,  # Refresh session on each request
    PREFERRED_URL_SCHEME='https',  # Force HTTPS for URL generation behind proxy

    # CSRF Protection
    WTF_CSRF_ENABLED=True,
    WTF_CSRF_TIME_LIMIT=3600,  # 1 hour CSRF token lifetime
    WTF_CSRF_SSL_STRICT=False,  # Allow CSRF through proxies

    # Security Headers
    SEND_FILE_MAX_AGE_DEFAULT=300,  # 5 minutes for static files (short cache for active development)

    # Data Protection
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max request size
)

# Initialize Rate Limiter with Flask app (Redis-based)
limiter.init_app(app)
logger.info("Rate limiter initialized with Flask app")

# ─── SECURITY HEADERS (Flask-Talisman) ────────────────────────────
# Configure comprehensive security headers for HIPAA/GDPR compliance
# Talisman automatically applies these headers to all responses

# Content Security Policy (CSP) - Controls what resources can be loaded
csp = {
    'default-src': [
        "'self'",
    ],
    'script-src': [
        "'self'",
        # NOTE: 'unsafe-inline' removed - we use nonces instead for better security
        'https://www.gstatic.com',  # Firebase
        'https://www.googletagmanager.com',  # Google Analytics
        'https://checkout.razorpay.com',  # Razorpay payment checkout
    ],
    'style-src': [
        "'self'",
        "'unsafe-inline'",  # Required for inline styles
        'https://fonts.googleapis.com',  # Google Fonts
        'https://checkout.razorpay.com',  # Razorpay styles
    ],
    'img-src': [
        "'self'",
        'data:',  # Data URIs for inline images
        'https:',  # Allow all HTTPS images (for flexibility)
        'https://cdn.razorpay.com',  # Razorpay images
        'https://www.googletagmanager.com',  # Google Analytics
        'https://www.google-analytics.com',  # Google Analytics
    ],
    'font-src': [
        "'self'",
        'https://fonts.gstatic.com',  # Google Fonts
        'https://r2cdn.perplexity.ai',  # Additional font CDN
    ],
    'connect-src': [
        "'self'",
        'https://www.googleapis.com',  # Google APIs
        'https://securetoken.googleapis.com',  # Firebase Auth
        'https://identitytoolkit.googleapis.com',  # Firebase Auth
        'https://www.gstatic.com',  # Firebase
        'https://api.razorpay.com',  # Razorpay API
        'https://lumberjack.razorpay.com',  # Razorpay logging
        'https://www.google-analytics.com',  # Google Analytics
        'https://analytics.google.com',  # Google Analytics
        'https://region1.google-analytics.com',  # Google Analytics
    ],
    'frame-src': [
        "'self'",
        'https://accounts.google.com',  # Google Sign-In
        'https://api.razorpay.com',  # Razorpay checkout iframe
        'https://checkout.razorpay.com',  # Razorpay checkout iframe
    ],
    'frame-ancestors': [
        "'self'",  # Prevent clickjacking - only allow embedding in same origin
    ],
}

# Initialize Talisman with security headers
# Detect if running in production (Cloud Run) or locally
is_production = bool(os.environ.get('K_SERVICE'))

Talisman(
    app,
    force_https=is_production,  # Force HTTPS in production only (not in local development)
    strict_transport_security=is_production,  # Enable HSTS in production only
    strict_transport_security_max_age=31536000,  # HSTS max age: 1 year
    strict_transport_security_include_subdomains=True,  # Apply HSTS to subdomains
    content_security_policy=csp,  # Apply CSP defined above
    content_security_policy_nonce_in=['script-src'],  # Add nonce to script-src for inline scripts
    referrer_policy='strict-origin-when-cross-origin',  # Control referrer information
    x_content_type_options=True,  # Prevent MIME type sniffing (nosniff)
    x_xss_protection=True,  # Enable XSS protection in browsers
    session_cookie_secure=is_production,  # Secure cookies in production only
    session_cookie_http_only=True,  # Prevent JavaScript access to session cookies
    force_file_save=False,  # Don't force file downloads
    frame_options='SAMEORIGIN',  # Allow framing only from same origin (prevents clickjacking)
    frame_options_allow_from=None,  # No external frame embedding allowed
    content_security_policy_report_uri=None,  # CSP violation reporting (can add later)
    content_security_policy_report_only=False,  # Enforce CSP (not just report)
    permissions_policy={  # Feature Policy (formerly Permissions-Policy)
        'geolocation': '()',  # Block geolocation
        'microphone': '()',  # Block microphone
        'camera': '()',  # Block camera
    },
)

logger.info("Flask-Talisman security headers configured and enabled")

# ───────────────────────────────────────────────────────────────────

# ─── ERROR TRACKING (Sentry) ───────────────────────────────────────
# Sentry for error tracking and performance monitoring in production
# CRITICAL: Must sanitize all events to prevent PHI leakage (HIPAA compliance)

def sanitize_sentry_event(event, hint):
    """
    Sanitize Sentry events to ensure NO PHI (Protected Health Information) is sent.
    This is CRITICAL for HIPAA compliance.

    PHI includes:
    - Patient names, emails, phone numbers
    - Medical record numbers (MRNs)
    - Passwords, tokens, API keys
    - Any patient-specific clinical data

    Args:
        event: Sentry event dictionary
        hint: Additional context from Sentry

    Returns:
        Sanitized event or None (to drop the event entirely)
    """
    # List of sensitive keys that must be redacted
    sensitive_keys = [
        'password', 'token', 'secret', 'api_key', 'authorization',
        'patient_name', 'name', 'email', 'phone', 'contact',
        'patient_id', 'mrn', 'address', 'dob', 'date_of_birth',
        'medical_history', 'diagnosis', 'treatment', 'prescription',
        'ssn', 'social_security', 'credit_card', 'card_number',
    ]

    # Sanitize request data
    if 'request' in event:
        # Sanitize request body data
        if 'data' in event['request']:
            data = event['request']['data']
            if isinstance(data, dict):
                for key in list(data.keys()):
                    # Check if key contains sensitive information
                    if any(sensitive in key.lower() for sensitive in sensitive_keys):
                        data[key] = '[REDACTED]'
            elif isinstance(data, str):
                # If data is a string (like JSON), redact the entire thing to be safe
                event['request']['data'] = '[REDACTED - potentially contains PHI]'

        # Sanitize query parameters
        if 'query_string' in event['request']:
            event['request']['query_string'] = '[REDACTED]'

        # Sanitize cookies (may contain session tokens)
        if 'cookies' in event['request']:
            event['request']['cookies'] = '[REDACTED]'

        # Sanitize headers (may contain auth tokens)
        if 'headers' in event['request']:
            headers = event['request']['headers']
            if isinstance(headers, dict):
                for key in ['Authorization', 'Cookie', 'X-Api-Key']:
                    if key in headers:
                        headers[key] = '[REDACTED]'

    # Sanitize extra context
    if 'extra' in event:
        extra = event['extra']
        # Remove any patient data from extra context
        keys_to_remove = []
        for key in extra.keys():
            if any(sensitive in key.lower() for sensitive in ['patient', 'user', 'phi', 'personal']):
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del extra[key]

    # Sanitize user context (keep only non-PHI identifiers)
    if 'user' in event:
        user = event['user']
        if isinstance(user, dict):
            # Keep only UID (anonymous identifier), remove email
            allowed_keys = ['id']
            user_sanitized = {k: v for k, v in user.items() if k in allowed_keys}
            event['user'] = user_sanitized

    # Sanitize breadcrumbs (may contain PHI in logs)
    if 'breadcrumbs' in event:
        breadcrumbs = event['breadcrumbs']
        if isinstance(breadcrumbs, dict) and 'values' in breadcrumbs:
            for breadcrumb in breadcrumbs['values']:
                if 'message' in breadcrumb:
                    # Redact any message that might contain PHI
                    message = breadcrumb['message']
                    if any(sensitive in message.lower() for sensitive in ['patient', 'email', 'phone', 'name']):
                        breadcrumb['message'] = '[REDACTED - potentially contains PHI]'
                if 'data' in breadcrumb:
                    breadcrumb['data'] = '[REDACTED]'

    return event


# Initialize Sentry (if DSN configured)
SENTRY_DSN = os.environ.get('SENTRY_DSN')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            FlaskIntegration(),
            LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors as events
            ),
        ],
        environment=ENVIRONMENT,

        # Performance Monitoring
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring (adjust based on traffic)
        profiles_sample_rate=0.1,  # 10% of transactions for profiling

        # HIPAA Compliance - CRITICAL SETTINGS
        send_default_pii=False,  # Never send PII automatically
        before_send=sanitize_sentry_event,  # Sanitize ALL events before sending

        # Release tracking
        release=os.environ.get('APP_VERSION', '1.0.0'),

        # Additional settings
        attach_stacktrace=True,  # Include stack traces for better debugging
        max_breadcrumbs=50,  # Limit breadcrumbs to control data volume
    )
    logger.info(f"✅ Sentry initialized for environment: {ENVIRONMENT}")
    logger.info(f"   - Error tracking: ENABLED")
    logger.info(f"   - Performance monitoring: ENABLED (10% sample rate)")
    logger.info(f"   - PHI sanitization: ENABLED (HIPAA-compliant)")
else:
    logger.warning("⚠️  Sentry DSN not configured - error tracking disabled")
    logger.info("   To enable Sentry:")
    logger.info("   1. Sign up at https://sentry.io")
    logger.info("   2. Create a new Python/Flask project")
    logger.info("   3. Set SENTRY_DSN environment variable")

# ───────────────────────────────────────────────────────────────────

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d-%m-%Y'):
    if not value:
        return ''
    if isinstance(value, str):
        try:
            # Handle Cosmos DB ISO format with 'Z' or '+00:00'
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            # If parsing fails, return the original string
            return value
    elif not hasattr(value, 'strftime'):
        # If it's not a datetime object and not a string, return as-is
        return str(value)
    return value.strftime(format)

# Security Functions for HIPAA/GDPR Compliance
# Note: Rate limiting functions now imported from rate_limiter.py (Redis-based)

def add_security_headers(response):
    """
    DEPRECATED: Security headers now handled by Flask-Talisman (configured above)

    This function is kept for reference but is no longer used.
    Talisman automatically applies comprehensive security headers including:
    - Content-Security-Policy (CSP)
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    - X-Frame-Options

    See Talisman configuration above for current security header settings.
    """
    # This function body is commented out as Talisman handles all security headers
    # response.headers.update({
    #     'X-Content-Type-Options': 'nosniff',
    #     'X-XSS-Protection': '1; mode=block',
    #     'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    #     'Content-Security-Policy': "...",
    #     'Referrer-Policy': 'strict-origin-when-cross-origin',
    #     'Permissions-Policy': 'geolocation=(), microphone=()'
    # })
    return response

# make sure you set a secret key for sessions + CSRF
# Custom CSRF protection that skips /api/* routes (mobile API uses Bearer tokens)
class APIAwareCSRFProtect(CSRFProtect):
    def protect(self):
        # Skip CSRF protection for API routes (they use Bearer token auth)
        if request.path.startswith('/api/'):
            return
        # For all other routes, use standard CSRF protection
        super().protect()

csrf = APIAwareCSRFProtect(app)

# ─── CORS CONFIGURATION ────────────────────────────────────────────
# CORS is configured for API routes that use Firebase bearer tokens
# If using Firebase Hosting rewrites, CORS may not be needed (same-origin)
# Uncomment and configure if calling the raw Cloud Run URL directly
# CORS(app, resources={
#     r"/ai_suggestion/*": {
#         "origins": [
#             "https://YOUR-PROJECT-ID.web.app",
#             "https://YOUR-PROJECT-ID.firebaseapp.com"
#         ],
#         "methods": ["POST", "OPTIONS"],
#         "allow_headers": ["Content-Type", "Authorization"],
#         "supports_credentials": False  # Bearer tokens don't need credentials
#     }
# })

# ─── MOBILE API BLUEPRINTS ────────────────────────────────────────────
# Register mobile API endpoints for the mobile app
try:
    from mobile_api import mobile_api
    from mobile_api_ai import mobile_api_ai
    logger.info(f"Mobile API imported successfully. Blueprint: {mobile_api}")

    # Register blueprints
    app.register_blueprint(mobile_api)
    app.register_blueprint(mobile_api_ai)
    logger.info(f"Mobile API blueprints registered. Routes: {[rule.rule for rule in app.url_map.iter_rules() if rule.rule.startswith('/api/')]}")

    # Pass AI client configuration to mobile API
    mobile_api_ai.get_ai_suggestion = get_ai_suggestion
    mobile_api_ai.get_ai_suggestion_with_cache = get_ai_suggestion_with_cache
    mobile_api_ai.HIPAA_COMPLIANT_MODE = HIPAA_COMPLIANT_MODE
    mobile_api_ai.client = client
    mobile_api_ai.USE_AZURE_OPENAI = True  # Azure OpenAI GPT-4o
    mobile_api_ai.AzureOpenAIError = AzureOpenAIError
    logger.info(f"Mobile API AI configuration passed: Using Azure OpenAI GPT-4o")

    # Exempt mobile API routes from CSRF protection (mobile apps use Bearer tokens)
    csrf.exempt(mobile_api)
    csrf.exempt(mobile_api_ai)
    logger.info(f"CSRF exempt blueprints: {csrf._exempt_blueprints}")

    # Enable CORS for mobile API endpoints
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",  # Allow all origins for mobile app (can be restricted later)
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": False  # Bearer tokens don't need credentials
        }
    })

    logger.info("Mobile API endpoints registered successfully")

    # Additional CSRF bypass for /api/* routes as a fallback
    @app.before_request
    def skip_csrf_for_api():
        """Skip CSRF protection for API routes that use Bearer token auth"""
        if request.path.startswith('/api/'):
            # Mark the view as exempt by adding to the exempt set dynamically
            view = app.view_functions.get(request.endpoint)
            if view:
                csrf._exempt_views.add(view)

except Exception as e:
    logger.warning(f"Failed to register mobile API endpoints: {e}")
    logger.warning("Mobile app will not be able to connect. This is normal if mobile_api.py doesn't exist yet.")
# ─── GEO-RESTRICTION MIDDLEWARE (HIPAA COMPLIANCE) ──────────────────────────
# Block US traffic until HIPAA BAA is obtained
# Controlled via BLOCK_US_TRAFFIC environment variable
try:
    from geo_restriction import check_geo_restriction, get_geo_blocking_status

    @app.before_request
    def geo_restriction_middleware():
        """
        Block access from US due to lack of HIPAA BAA.
        Can be disabled by setting BLOCK_US_TRAFFIC=false
        """
        return check_geo_restriction()

    # Log geo-blocking status on startup
    geo_status = get_geo_blocking_status()
    if geo_status['enabled']:
        logger.warning(f"🌍 GEO-BLOCKING ENABLED - Blocking: {geo_status['blocked_countries']}")
        logger.info(f"   Reason: HIPAA BAA not obtained for US")
        logger.info(f"   To disable: Set BLOCK_US_TRAFFIC=false")
    else:
        logger.info(f"🌍 Geo-blocking DISABLED - All regions allowed")

except ImportError as e:
    logger.warning(f"Geo-restriction module not found: {e}")
    logger.warning("US traffic will NOT be blocked. Deploy geo_restriction.py to enable blocking.")

# ─── CSRF ERROR HANDLING ────────────────────────────
@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    # Return JSON for API requests
    if request.path.startswith('/api/') or request.accept_mimetypes.best == 'application/json':
        return jsonify({'ok': False, 'error': 'CSRF validation failed', 'message': str(error)}), 400
    flash("The form you submitted is invalid or has expired. Please try again.", "error")
    return redirect(request.referrer or url_for('index')), 400


# ═══════════════════════════════════════════════════════════════════
# COMPREHENSIVE ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def handle_404_error(error):
    """Handle 404 Page Not Found errors"""
    logger.warning(f"404 error: {request.url}")
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def handle_500_error(error):
    """Handle 500 Internal Server Error"""
    logger.error(f"500 error: {error}", exc_info=True)
    return render_template('errors/500.html', timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')), 500


@app.errorhandler(503)
def handle_503_error(error):
    """Handle 503 Service Unavailable"""
    logger.error(f"503 error: Service unavailable - {error}")
    return render_template('errors/503.html', timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')), 503


@app.errorhandler(413)
def handle_request_entity_too_large(error):
    """Handle requests that exceed MAX_CONTENT_LENGTH (16MB)"""
    logger.warning(f"413 error: Request payload too large from IP {request.environ.get('REMOTE_ADDR')}")
    return jsonify({
        'error': 'Request too large',
        'message': 'The request payload exceeds the maximum allowed size (16MB)',
        'max_size': '16MB'
    }), 413


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Catch-all handler for unexpected errors"""
    # Log the full error with stack trace
    logger.error(f"Unexpected error: {error}", exc_info=True)

    # Don't expose internal error details to users
    # Return generic 500 error page
    return render_template('errors/500.html', timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')), 500


# ─── HTTPS ENFORCEMENT MIDDLEWARE ───────────
@app.before_request
def enforce_https():
    """Force HTTPS in production"""
    if not request.is_secure and request.headers.get('X-Forwarded-Proto', 'http') != 'https':
        # Allow local development
        if request.host.startswith('localhost') or request.host.startswith('127.0.0.1'):
            return None
        # Redirect to HTTPS
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

# ─── SENTRY CONTEXT MIDDLEWARE ──────────────
@app.before_request
def set_sentry_context():
    """
    Add request context to Sentry for better error debugging.
    HIPAA-compliant: Only adds non-PHI metadata.
    """
    if SENTRY_DSN:
        # Add non-PHI request metadata to Sentry
        sentry_sdk.set_context("request", {
            "endpoint": request.endpoint,
            "method": request.method,
            "url_rule": str(request.url_rule) if request.url_rule else None,
            "remote_addr": request.remote_addr,  # IP address (not PHI)
            "user_agent": request.headers.get('User-Agent', 'Unknown'),
        })

        # Add user context if logged in (Firebase UID only, no email/name)
        if hasattr(g, 'firebase_user') and g.firebase_user:
            sentry_sdk.set_user({
                "id": g.firebase_user.get('uid'),  # Anonymous UID (not PHI)
                # DO NOT include email, name, or any other PHI
            })
        elif 'user_id' in session:
            # Session-based auth
            sentry_sdk.set_user({
                "id": session.get('user_id'),  # Email/UID from session (not PHI if it's UID)
                # DO NOT include other session data
            })

        # Add custom tags for filtering in Sentry
        sentry_sdk.set_tag("environment", ENVIRONMENT)
        sentry_sdk.set_tag("hipaa_mode", str(HIPAA_COMPLIANT_MODE))

# ───────────────────────────────────────────────

# ─── SECURITY HEADERS & CSRF TOKEN ───────────
@app.after_request
def security_headers_and_csrf(response):
    # Security headers now automatically applied by Flask-Talisman (see configuration above)
    # This function now only handles CSRF token cookie

    # Set secure CSRF token cookie
    response.set_cookie(
        'csrf_token',
        generate_csrf(),
        secure=True,  # Only send over HTTPS
        httponly=False,  # Needs to be accessible to JS for AJAX
        samesite='Lax',  # CSRF protection (Lax needed for Firebase Hosting proxy)
        path='/',  # Available across entire site
        max_age=3600  # 1 hour expiration
    )
    return response

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)


def login_required(approved_only=True):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Security: Check if user is logged in
            # Debug logging for session troubleshooting
            logger.info(f"Session check for {request.endpoint}: session keys = {list(session.keys())}, cookies = {list(request.cookies.keys())}")

            if 'user_id' not in session:
                logger.info(f"Unauthorized access attempt to {request.endpoint} from IP {request.environ.get('REMOTE_ADDR', 'unknown')}")
                return redirect('/login')

            # Security: Check session timeout (8 hours from login OR 2 hours idle)
            login_time_str = session.get('login_time')
            last_activity_str = session.get('last_activity')
            current_time = datetime.utcnow()

            if login_time_str:
                login_time = datetime.fromisoformat(login_time_str)
                # Check absolute session timeout (8 hours)
                if current_time - login_time > timedelta(hours=8):
                    logger.info(f"Session expired for user {session.get('user_id')} - 8 hour limit reached")
                    session.clear()
                    flash("Your session has expired. Please log in again.", "warning")
                    return redirect('/login')

            if last_activity_str:
                last_activity = datetime.fromisoformat(last_activity_str)
                # Check idle timeout (2 hours of inactivity)
                if current_time - last_activity > timedelta(hours=2):
                    logger.info(f"Session expired for user {session.get('user_id')} - idle timeout")
                    session.clear()
                    flash("Your session has expired due to inactivity. Please log in again.", "warning")
                    return redirect('/login')

                # Update last activity timestamp
                session['last_activity'] = current_time.isoformat()

            # Security: Check approval status if required
            # Super admins bypass approval checks
            if approved_only and session.get('is_super_admin') != 1:
                if session.get('is_admin') != 1 and session.get('approved') == 0:
                    logger.warning(f"Access denied for unapproved user {session.get('user_id')} to {request.endpoint}")
                    return "Access denied. Awaiting approval by admin.", 403

            return f(*args, **kwargs)
        return decorated_function
    return wrapper

def super_admin_required():
    """Decorator for super admin only routes"""
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect('/login')
            if session.get('is_super_admin') != 1:
                logger.warning(f"Unauthorized super admin access attempt by {session.get('user_id')} to {request.endpoint}")
                flash("Access denied. Super admin privileges required.", "error")
                return redirect('/dashboard'), 403
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

@app.route('/')
def index():
    # Redirect to homepage for now, or show old index for logged-in users
    return redirect(url_for('homepage'))

@app.route('/homepage')
def homepage():
    return render_template('homepage.html')

@app.route('/welcome')
def welcome():
    # Old welcome page for existing users
    return render_template('index.html')

@app.route('/request-access')
def request_access():
    """Display early access request form"""
    return render_template('request_access.html')

@app.route('/pilot-program')
def pilot_program():
    """Display pilot program information page"""
    return render_template('pilot_program.html')

@app.route('/security')
def security_page():
    """Display security and compliance page"""
    return render_template('security.html')

@app.route('/submit-access-request', methods=['POST'])
@app.route('/api/submit-access-request', methods=['POST'])
def submit_access_request():
    """Handle early access request form submission (web form or mobile JSON)"""
    try:
        # Support both form data (web) and JSON (mobile)
        if request.is_json:
            data = request.get_json()
            access_data = {
                'name': data.get('full_name'),
                'email': data.get('email'),
                'phone': data.get('phone', ''),
                'institute': data.get('organisation', ''),
                'message': data.get('use_case', '')
            }

            is_valid, result = validate_json(AccessRequestSchema, access_data)
            if not is_valid:
                return jsonify({'error': 'Validation failed', 'details': result}), 400

            full_name = result['name']
            email = result['email']
            role = data.get('role')
            organisation = result['institute']
            country = data.get('country')
            use_case = result['message']
            pilot_interest = data.get('pilot_interest', False)
        else:
            # Form data from web
            access_data = {
                'name': request.form.get('full_name'),
                'email': request.form.get('email'),
                'phone': request.form.get('phone', ''),
                'institute': request.form.get('organisation', ''),
                'message': request.form.get('use_case', '')
            }

            is_valid, result = validate_data(AccessRequestSchema, access_data)
            if not is_valid:
                flash(f"Validation error: {result}", "error")
                return redirect('/request-access')

            full_name = result['name']
            email = result['email']
            role = request.form.get('role')
            organisation = result['institute']
            country = request.form.get('country')
            use_case = result['message']
            pilot_interest = request.form.get('pilot_interest') == 'yes'

        # Store in Cosmos DB
        access_request_ref = db.collection('access_requests').document()
        access_request_ref.set({
            'full_name': full_name,
            'email': email,
            'role': role,
            'organisation': organisation,
            'country': country,
            'use_case': use_case,
            'pilot_interest': pilot_interest,
            'timestamp': SERVER_TIMESTAMP,
            'status': 'pending'  # pending, approved, rejected
        })

        # Send notification email to admin
        try:
            from email_service import send_early_access_notification, send_early_access_confirmation

            # Email to admin
            send_early_access_notification(
                admin_email=os.environ.get('ADMIN_EMAIL', 'drsandeep@physiologicprism.com'),
                full_name=full_name,
                email=email,
                role=role,
                organisation=organisation,
                country=country,
                use_case=use_case,
                pilot_interest=pilot_interest
            )

            # Confirmation email to user
            send_early_access_confirmation(
                full_name=full_name,
                email=email,
                role=role,
                pilot_interest=pilot_interest
            )
        except Exception as e:
            logger.error(f"Failed to send early access notification emails: {str(e)}")

        # Return JSON for mobile, redirect for web
        if request.is_json:
            return jsonify({
                'success': True,
                'message': "Thank you for your interest! We'll review your request and get back to you by email soon."
            }), 200
        else:
            flash('Thank you for your interest! We\'ll review your request and get back to you by email soon.', 'success')
            return redirect(url_for('request_access'))

    except Exception as e:
        logger.error(f"Error submitting access request: {str(e)}")

        # Return JSON error for mobile, redirect for web
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'There was an error submitting your request. Please try again or contact us directly.'
            }), 500
        else:
            flash('There was an error submitting your request. Please try again or contact us directly.', 'error')
            return redirect(url_for('request_access'))


# ═══════════════════════════════════════════════════════════════════════════
# FIREBASE AUTH ROUTES (New authentication flow)
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/login/firebase')
def login_firebase():
    """Serve Firebase Auth login page"""
    return render_template('login_firebase.html')


@app.route('/register/choice')
def register_choice():
    """Show registration type selection page"""
    return render_template('register_choice.html')


@app.route('/register/firebase')
def register_firebase():
    """Serve Firebase Auth registration page"""
    return render_template('register_firebase.html')


# ═══════════════════════════════════════════════════════════════════════════
# LEGACY SESSION-BASED AUTH ROUTES (Backwards compatibility)
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/register', methods=['GET'])
@csrf.exempt
def register():
    """Show registration type choice page"""
    return render_template('register_choice.html')


@app.route('/register/individual', methods=['GET', 'POST'])
@csrf.exempt  # Exempt register from CSRF to work with Firebase Hosting proxy
def register_individual():
    # Redirect to Firebase Auth registration for AI features to work
    if request.method == 'GET':
        return redirect('/register/firebase')

    if request.method == 'POST':
        # Validate input using Marshmallow schema
        form_data = {
            'name': request.form.get('name', '').strip(),
            'email': request.form.get('email', '').strip().lower(),
            'phone': request.form.get('phone', '').strip(),
            'institute': request.form.get('institute', '').strip(),
            'password': request.form.get('password', ''),
            'consent_data_processing': request.form.get('consent_data_processing') == 'on',
            'consent_terms': request.form.get('consent_terms') == 'on',
            'consent_ai': request.form.get('consent_ai') == 'on'
        }

        is_valid, result = validate_data(UserRegistrationSchema, form_data)
        if not is_valid:
            # Flatten validation errors for user-friendly display
            error_messages = []
            for field, errors in result.items():
                for error in errors:
                    error_messages.append(f"{field.replace('_', ' ').title()}: {error}")
            flash(' | '.join(error_messages), "error")
            return redirect('/register')

        # Use validated data
        name = result['name']
        email = result['email']
        phone = result['phone']
        institute = result['institute']
        pwd = result['password']
        consent_ai = result.get('consent_ai', False)

        # Security: Check if user already exists
        existing_user = db.collection('users').document(email).get()
        if existing_user.exists:
            flash("An account with this email already exists.", "error")
            return redirect('/register')

        pw_hash = generate_password_hash(pwd)
        db.collection('users').document(email).set({
            'name': name,
            'email': email,
            'phone': phone,
            'institute': institute,
            'password_hash': pw_hash,
            'created_at': SERVER_TIMESTAMP,
            'approved': 0,  # Security: Require admin approval
            'active': 1,
            'is_admin': 0,
            'user_type': 'individual',  # Track registration type
            # GDPR Consent fields
            'consent_data_processing': 1,  # Required
            'consent_terms': 1,  # Required
            'consent_ai': 1 if consent_ai else 0,  # Optional
            'consent_date': SERVER_TIMESTAMP,
            # ToS Acceptance Logging (Legal requirement)
            'tos_accepted_at': SERVER_TIMESTAMP,
            'tos_version': TOS_VERSION,  # Track which version of ToS was accepted
        })

        log_action(None, 'Register', f"{name} ({email}) registered - pending approval. AI consent: {consent_ai}")

        # Send notification to super admin
        try:
            send_registration_notification({
                'name': name,
                'email': email,
                'phone': phone,
                'institute': institute,
                'created_at': datetime.now().isoformat()
            })
        except Exception as email_error:
            # Log error but don't fail registration
            logger.error(f"Failed to send registration notification for {email}: {email_error}")

        flash("Registration successful! Your account is pending admin approval.", "success")
        return redirect('/login')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
@csrf.exempt  # Exempt login from CSRF to work with Firebase Hosting proxy - still secure via rate limiting
def login():
    # Redirect to Firebase Auth login for AI features to work
    if request.method == 'GET':
        return redirect('/login/firebase')

    if request.method == 'POST':
        # Validate input using Marshmallow schema
        login_data = {
            'email': request.form.get('email', '').strip().lower(),
            'password': request.form.get('password', '')
        }

        is_valid, result = validate_data(LoginSchema, login_data)
        if not is_valid:
            logger.warning(f"Invalid login data: {result}")
            return "Invalid login credentials.", 401

        # Use validated data
        email = result['email']
        pwd = result['password']

        # Security: Check if user is rate limited (email-based)
        is_allowed, lockout_remaining = check_login_attempts(email)
        if not is_allowed:
            logger.warning(f"Blocked login attempt for {email} - rate limited ({lockout_remaining}s remaining)")
            return f"Too many failed attempts. Please try again in {int(lockout_remaining/60)} minutes.", 429
        
        try:
            # Get client IP for logging
            client_ip = request.environ.get('REMOTE_ADDR', 'unknown')

            doc = db.collection('users').document(email).get()
            if not doc.exists:
                record_failed_login(email)
                return "Invalid login credentials.", 401

            user = doc.to_dict()
            if check_password_hash(user.get('password_hash', ''), pwd):
                # Successful password verification - check account status
                # Super admins bypass approval checks
                is_super_admin = user.get('is_super_admin', 0)

                # Check email verification (super admins bypass)
                if is_super_admin != 1 and not user.get('email_verified', False):
                    logger.warning(f"Login attempt with unverified email: {email} from IP {client_ip}")
                    flash("Please verify your email address before logging in. Check your inbox for the verification link.", "error")
                    return redirect('/resend-verification?email=' + email)

                if is_super_admin == 1 or (user.get('approved', 0) == 1 and user.get('active', 1) == 1):
                    # Security: Create secure session
                    session.permanent = True
                    session.update({
                        'user_id': email,
                        'user_name': user.get('name'),
                        'institute': user.get('institute'),
                        'is_admin': user.get('is_admin', 0),
                        'is_super_admin': is_super_admin,
                        'approved': user.get('approved', 0),
                        'login_time': datetime.utcnow().isoformat(),
                        'last_activity': datetime.utcnow().isoformat()
                    })
                    session.modified = True  # Explicitly mark session as modified

                    # Debug: Log session after setting
                    logger.info(f"Session set for {email}: keys = {list(session.keys())}")

                    # Clear failed login attempts (Redis-based)
                    clear_login_attempts(email)

                    # Security audit logging
                    role = "Super Admin" if is_super_admin == 1 else ("Admin" if user.get('is_admin') == 1 else "User")
                    log_action(email, 'Login', f"Successful {role} login from IP {client_ip}")
                    logger.info(f"Successful {role} login for {email} from IP {client_ip}")

                    # Redirect super admins to their dashboard
                    if is_super_admin == 1:
                        return redirect('/super_admin_dashboard')
                    return redirect('/dashboard')
                elif user.get('active', 1) == 0:
                    logger.warning(f"Login attempt for deactivated account {email} from IP {client_ip}")
                    return "Your account has been deactivated. Contact your admin.", 403
                else:
                    logger.warning(f"Login attempt for unapproved account {email} from IP {client_ip}")
                    return "Your registration is pending admin approval.", 403
            else:
                # Invalid password
                record_failed_login(email)
                return "Invalid login credentials.", 401

        except Exception as e:
            logger.error(f"Login error for {email} from IP {client_ip}: {str(e)}")
            record_failed_login(email)
            return "Login service temporarily unavailable. Please try again.", 503
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log_action(user_id, 'Logout', 'User logged out')
    session.clear()
    # Render a page that clears localStorage before redirecting
    return render_template('logout.html')


# ═══════════════════════════════════════════════════════════════════════════
# PASSWORD RESET ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password_page():
    """
    Web page for requesting password reset.

    GET: Display forgot password form
    POST: Process password reset request
    """
    if request.method == 'GET':
        return render_template('forgot_password.html')

    elif request.method == 'POST':
        # Get client IP for rate limiting
        client_ip = request.environ.get('REMOTE_ADDR', 'unknown')

        # Rate limiting: Max 3 reset requests per 15 minutes per IP
        reset_attempts_key = f"reset_{client_ip}"
        reset_attempts = login_attempts.get(reset_attempts_key, [])
        current_time = time.time()

        # Clean old attempts
        reset_attempts = [t for t in reset_attempts if current_time - t < 900]

        if len(reset_attempts) >= 3:
            logger.warning(f"Too many password reset attempts from IP {client_ip}")
            flash('If an account exists with this email, you will receive password reset instructions.', 'success')
            return render_template('forgot_password.html')

        # Get email from form
        email = request.form.get('email', '').strip().lower()

        # Validate email
        if not email or '@' not in email or len(email) > 254:
            flash('If an account exists with this email, you will receive password reset instructions.', 'success')
            return render_template('forgot_password.html')

        # Record attempt
        reset_attempts.append(current_time)
        login_attempts[reset_attempts_key] = reset_attempts

        try:
            # Check if user exists
            user_doc = db.collection('users').document(email).get()
            if not user_doc.exists:
                # Security: Don't reveal that user doesn't exist
                logger.info(f"Password reset requested for non-existent email: {email}")
                flash('If an account exists with this email, you will receive password reset instructions.', 'success')
                return render_template('forgot_password.html')

            user_data = user_doc.to_dict()

            # Generate reset token
            reset_token = generate_reset_token()

            # Store token in Firestore
            if not store_reset_token(db, email, reset_token):
                logger.error(f"Failed to store reset token for {email}")
                flash('If an account exists with this email, you will receive password reset instructions.', 'success')
                return render_template('forgot_password.html')

            # Generate reset URL
            base_url = request.host_url.rstrip('/')
            reset_url = f"{base_url}/reset-password/{reset_token}"

            # Send email via n8n webhook
            send_password_reset_notification(
                user_data={
                    'name': user_data.get('name', ''),
                    'email': email
                },
                reset_token=reset_token,
                reset_url=reset_url
            )

            # Log action
            log_action(email, 'Password Reset Request', f'Reset link sent to {email} from IP {client_ip}')
            logger.info(f"Password reset email sent to {email}")

            flash('If an account exists with this email, you will receive password reset instructions.', 'success')
            return render_template('forgot_password.html')

        except Exception as e:
            logger.error(f"Error in forgot_password_page: {str(e)}")
            flash('If an account exists with this email, you will receive password reset instructions.', 'success')
            return render_template('forgot_password.html')


@app.route('/api/forgot-password', methods=['POST'])
@csrf.exempt  # API endpoint - CSRF not applicable
def forgot_password():
    """
    Initiate password reset process.
    Generates reset token and sends email with reset link.

    Request Body:
        {
            "email": "user@example.com"
        }

    Returns:
        200: Reset email sent (even if user doesn't exist - security best practice)
        400: Invalid request
        429: Too many requests
        500: Server error
    """
    try:
        # Get client IP for rate limiting
        client_ip = request.environ.get('REMOTE_ADDR', 'unknown')

        # Rate limiting: Max 3 reset requests per 15 minutes per IP
        reset_attempts_key = f"reset_{client_ip}"
        reset_attempts = login_attempts.get(reset_attempts_key, [])
        current_time = time.time()

        # Clean old attempts
        reset_attempts = [t for t in reset_attempts if current_time - t < 900]

        if len(reset_attempts) >= 3:
            logger.warning(f"Too many password reset attempts from IP {client_ip}")
            return jsonify({
                'success': True,
                'message': 'If an account exists with this email, you will receive password reset instructions.'
            }), 200  # Don't reveal rate limiting to prevent enumeration

        # Get and validate email from request
        data = request.get_json() or {}
        forgot_password_data = {
            'email': data.get('email', '').strip().lower()
        }

        # Validate using Marshmallow schema
        is_valid, result = validate_json(ForgotPasswordSchema, forgot_password_data)
        if not is_valid:
            # Security: Don't reveal validation failures
            logger.warning(f"Invalid forgot password request from IP {client_ip}: {result}")
            return jsonify({
                'success': True,
                'message': 'If an account exists with this email, you will receive password reset instructions.'
            }), 200

        # Use validated email
        email = result['email']

        # Record attempt
        reset_attempts.append(current_time)
        login_attempts[reset_attempts_key] = reset_attempts

        # Check if user exists
        user_doc = db.collection('users').document(email).get()
        if not user_doc.exists:
            # Security: Don't reveal that user doesn't exist
            logger.info(f"Password reset requested for non-existent email: {email}")
            return jsonify({
                'success': True,
                'message': 'If an account exists with this email, you will receive password reset instructions.'
            }), 200

        user_data = user_doc.to_dict()

        # Generate reset token
        reset_token = generate_reset_token()

        # Store token in Firestore
        if not store_reset_token(db, email, reset_token):
            logger.error(f"Failed to store reset token for {email}")
            return jsonify({
                'success': True,
                'message': 'If an account exists with this email, you will receive password reset instructions.'
            }), 200  # Don't reveal error

        # Generate reset URL
        base_url = request.host_url.rstrip('/')
        reset_url = f"{base_url}/reset-password/{reset_token}"

        # Send email via n8n webhook
        send_password_reset_notification(
            user_data={
                'name': user_data.get('name', ''),
                'email': email
            },
            reset_token=reset_token,
            reset_url=reset_url
        )

        # Log action
        log_action(email, 'Password Reset Request', f'Reset link sent to {email} from IP {client_ip}')
        logger.info(f"Password reset email sent to {email}")

        return jsonify({
            'success': True,
            'message': 'If an account exists with this email, you will receive password reset instructions.'
        }), 200

    except Exception as e:
        logger.error(f"Error in forgot_password: {str(e)}")
        return jsonify({
            'success': True,
            'message': 'If an account exists with this email, you will receive password reset instructions.'
        }), 200  # Don't reveal error details


@app.route('/api/reset-password', methods=['POST'])
@csrf.exempt  # API endpoint - CSRF not applicable
def reset_password_api():
    """
    Reset user password using valid token.

    Request Body:
        {
            "token": "reset_token_here",
            "new_password": "new_secure_password"
        }

    Returns:
        200: Password reset successful
        400: Invalid request or token
        500: Server error
    """
    try:
        data = request.get_json() or {}

        # Prepare data for validation
        reset_data = {
            'token': data.get('token', '').strip(),
            'password': data.get('new_password', ''),
            'confirm_password': data.get('new_password', '')  # Use same for API compatibility
        }

        # Validate using Marshmallow schema
        is_valid, result = validate_json(ResetPasswordSchema, reset_data)
        if not is_valid:
            error_msg = 'Invalid reset data'
            if 'password' in result:
                error_msg = result['password'][0]
            elif 'token' in result:
                error_msg = 'Invalid or missing reset token'
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400

        # Use validated data
        token = result['token']
        new_password = result['password']

        # Verify token and get user email
        email = verify_reset_token(db, token)
        if not email:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired reset token'
            }), 400

        # Get user data
        user_doc = db.collection('users').document(email).get()
        if not user_doc.exists:
            logger.error(f"User not found for valid token: {email}")
            return jsonify({
                'success': False,
                'error': 'Invalid reset token'
            }), 400

        user_data = user_doc.to_dict()

        # Hash new password
        new_password_hash = generate_password_hash(new_password)

        # Update Firestore password
        user_ref = db.collection('users').document(email)
        user_ref.update({
            'password_hash': new_password_hash,
            'password_updated_at': SERVER_TIMESTAMP
        })

        # Update Firebase Auth password if account exists
        firebase_uid = user_data.get('firebase_uid')
        if firebase_uid:
            try:
                auth.update_user(
                    firebase_uid,
                    password=new_password
                )
                logger.info(f"Firebase Auth password updated for {email}")
            except Exception as firebase_error:
                logger.warning(f"Failed to update Firebase Auth password for {email}: {str(firebase_error)}")
                # Continue - Firestore password is updated, which is primary

        # Clear reset token
        clear_reset_token(db, email)

        # Log action
        client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
        log_action(email, 'Password Reset', f'Password successfully reset from IP {client_ip}')
        logger.info(f"Password successfully reset for {email}")

        return jsonify({
            'success': True,
            'message': 'Password has been reset successfully. You can now login with your new password.'
        }), 200

    except Exception as e:
        logger.error(f"Error in reset_password_api: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while resetting your password. Please try again.'
        }), 500


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_page(token):
    """
    Web page for resetting password with token.

    GET: Display reset password form
    POST: Process password reset
    """
    if request.method == 'GET':
        # Verify token is valid before showing form
        email = verify_reset_token(db, token)
        if not email:
            flash('Invalid or expired reset link. Please request a new password reset.', 'error')
            return redirect('/login')

        return render_template('reset_password.html', token=token)

    elif request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validate inputs
        if not new_password or not confirm_password:
            flash('Both password fields are required', 'error')
            return render_template('reset_password.html', token=token)

        if new_password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html', token=token)

        if len(new_password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('reset_password.html', token=token)

        # Verify token
        email = verify_reset_token(db, token)
        if not email:
            flash('Invalid or expired reset link. Please request a new password reset.', 'error')
            return redirect('/login')

        try:
            # Get user data
            user_doc = db.collection('users').document(email).get()
            if not user_doc.exists:
                flash('User account not found', 'error')
                return redirect('/login')

            user_data = user_doc.to_dict()

            # Hash new password
            new_password_hash = generate_password_hash(new_password)

            # Update Firestore password
            user_ref = db.collection('users').document(email)
            user_ref.update({
                'password_hash': new_password_hash,
                'password_updated_at': SERVER_TIMESTAMP
            })

            # Update Firebase Auth password if account exists
            firebase_uid = user_data.get('firebase_uid')
            if firebase_uid:
                try:
                    auth.update_user(
                        firebase_uid,
                        password=new_password
                    )
                    logger.info(f"Firebase Auth password updated for {email}")
                except Exception as firebase_error:
                    logger.warning(f"Failed to update Firebase Auth password for {email}: {str(firebase_error)}")
                    # Continue - Firestore password is updated

            # Clear reset token
            clear_reset_token(db, email)

            # Log action
            client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
            log_action(email, 'Password Reset', f'Password successfully reset from IP {client_ip}')
            logger.info(f"Password successfully reset for {email}")

            flash('Password has been reset successfully. You can now login with your new password.', 'success')
            return redirect('/login')

        except Exception as e:
            logger.error(f"Error resetting password for token {token}: {str(e)}")
            flash('An error occurred while resetting your password. Please try again.', 'error')
            return render_template('reset_password.html', token=token)


# ═══════════════════════════════════════════════════════════════════════════
# FIREBASE AUTH API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# EMAIL VERIFICATION ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/verify-email', methods=['GET'])
def verify_email():
    """
    Email verification endpoint (web interface).
    Called when user clicks verification link in email.

    Query params:
        - email: User's email address
        - token: Verification token
    """
    from email_verification import verify_token

    email = request.args.get('email', '').strip().lower()
    token = request.args.get('token', '').strip()

    if not email or not token:
        flash("Invalid verification link", "error")
        return redirect('/login')

    success, message = verify_token(email, token)

    if success:
        flash(message, "success")
        log_action(email, 'Email Verified', f'Email verified successfully for {email}')
        return render_template('email_verified.html', email=email)
    else:
        flash(message, "error")
        return render_template('verification_failed.html', error=message, email=email)


@app.route('/api/verify-email', methods=['POST'])
@csrf.exempt
def api_verify_email():
    """
    Email verification API endpoint (for mobile app).

    Body:
        - email: User's email address
        - token: Verification token
    """
    from email_verification import verify_token

    try:
        data = request.get_json() or {}

        # Validate token using schema (email is included for this endpoint's compatibility)
        verification_data = {
            'token': data.get('token', '').strip()
        }

        is_valid, result = validate_json(EmailVerificationSchema, verification_data)
        if not is_valid:
            return jsonify({'ok': False, 'error': 'INVALID_TOKEN', 'details': result}), 400

        # Use validated token
        token = result['token']
        email = data.get('email', '').strip().lower()  # Email is used by verify_token function

        if not email:
            return jsonify({'ok': False, 'error': 'MISSING_EMAIL'}), 400

        success, message = verify_token(email, token)

        if success:
            log_action(email, 'Email Verified (API)', f'Email verified via mobile app for {email}')
            return jsonify({'ok': True, 'message': message}), 200
        else:
            return jsonify({'ok': False, 'error': message}), 400

    except Exception as e:
        logger.error(f"API email verification error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'VERIFICATION_FAILED'}), 500


@app.route('/api/resend-verification', methods=['POST'])
@csrf.exempt
def api_resend_verification():
    """
    Resend email verification link (for mobile app).

    Body:
        - email: User's email address
    """
    from email_verification import resend_verification_token, is_email_verified

    try:
        data = request.get_json() or {}

        # Validate email using schema
        resend_data = {
            'email': data.get('email', '').strip().lower()
        }

        is_valid, result = validate_json(ResendVerificationSchema, resend_data)
        if not is_valid:
            return jsonify({'ok': False, 'error': 'INVALID_EMAIL', 'details': result}), 400

        # Use validated email
        email = result['email']

        # Check if user exists
        user_doc = db.collection('users').document(email).get()
        if not user_doc.exists:
            return jsonify({'ok': False, 'error': 'USER_NOT_FOUND'}), 404

        # Check if already verified
        if is_email_verified(email):
            return jsonify({'ok': False, 'error': 'ALREADY_VERIFIED'}), 400

        # Generate new token
        token = resend_verification_token(email)
        if not token:
            return jsonify({'ok': False, 'error': 'FAILED_TO_GENERATE_TOKEN'}), 500

        # Send email
        user_data = user_doc.to_dict()
        app_url = request.host_url.rstrip('/')

        send_email_verification(
            {'name': user_data.get('name'), 'email': email},
            token,
            app_url
        )

        log_action(email, 'Resend Verification', f'Verification email resent to {email}')
        return jsonify({'ok': True, 'message': 'Verification email sent'}), 200

    except Exception as e:
        logger.error(f"Resend verification error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'RESEND_FAILED'}), 500


@app.route('/resend-verification', methods=['GET', 'POST'])
def web_resend_verification():
    """
    Resend email verification link (web interface).
    """
    from email_verification import resend_verification_token, is_email_verified

    if request.method == 'GET':
        return render_template('resend_verification.html')

    try:
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash("Email is required", "error")
            return redirect('/resend-verification')

        # Check if user exists
        user_doc = db.collection('users').document(email).get()
        if not user_doc.exists:
            flash("No account found with this email", "error")
            return redirect('/resend-verification')

        # Check if already verified
        if is_email_verified(email):
            flash("Email is already verified. You can log in now.", "info")
            return redirect('/login')

        # Generate new token
        token = resend_verification_token(email)
        if not token:
            flash("Failed to generate verification token. Please try again later.", "error")
            return redirect('/resend-verification')

        # Send email
        user_data = user_doc.to_dict()
        app_url = request.host_url.rstrip('/')

        send_email_verification(
            {'name': user_data.get('name'), 'email': email},
            token,
            app_url
        )

        log_action(email, 'Resend Verification (Web)', f'Verification email resent to {email}')
        flash("Verification email sent! Please check your inbox.", "success")
        return redirect('/login')

    except Exception as e:
        logger.error(f"Web resend verification error: {e}", exc_info=True)
        flash("An error occurred. Please try again later.", "error")
        return redirect('/resend-verification')


@app.route('/api/sync-user', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def sync_user_to_firestore():
    """
    Sync Firebase Auth user to Firestore users collection.
    Called after successful Firebase Auth registration.

    Expects:
        - Authorization header with Firebase ID token
        - JSON body with user data

    Returns:
        - 200: User synced successfully
        - 400: Invalid request
        - 409: User already exists
    """
    try:
        # Get Firebase user info from decorator
        firebase_uid = g.firebase_user['uid']
        firebase_email = g.firebase_user['email']

        # Get additional user data from request
        data = request.get_json() or {}

        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'institute']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Check if user already exists in Firestore
        user_doc = db.collection('users').document(firebase_email).get()
        if user_doc.exists:
            logger.warning(f"User already exists in Firestore: {firebase_email}")
            return jsonify({'error': 'User already exists'}), 409

        # Create user document in Firestore
        user_data = {
            'firebase_uid': firebase_uid,
            'name': data['name'],
            'email': firebase_email,
            'phone': data.get('phone', ''),
            'institute': data.get('institute', ''),
            'consent_data_processing': data.get('consent_data_processing', False),
            'consent_terms': data.get('consent_terms', False),
            'consent_ai': data.get('consent_ai', False),
            'is_admin': 0,  # Regular user by default
            'is_super_admin': 0,
            'approved': 0,  # Pending approval
            'active': 1,
            'created_at': SERVER_TIMESTAMP,
            # ToS Acceptance Logging (Legal requirement)
            'tos_accepted_at': SERVER_TIMESTAMP,
            'tos_version': TOS_VERSION
        }

        db.collection('users').document(firebase_email).set(user_data)

        log_action(None, 'Firebase Register', f"{data['name']} ({firebase_email}) registered via Firebase Auth - pending approval")

        logger.info(f"User synced to Firestore: {firebase_email}")

        return jsonify({
            'success': True,
            'message': 'User synced successfully',
            'uid': firebase_uid
        }), 200

    except Exception as e:
        logger.error(f"Error syncing user to Firestore: {e}", exc_info=True)
        return jsonify({'error': 'Failed to sync user data'}), 500


@app.route('/api/verify-login', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def verify_login():
    """
    Verify Firebase Auth login and return user data.
    Checks approval status and returns user information.

    Expects:
        - Authorization header with Firebase ID token

    Returns:
        - 200: Login verified, user data returned
        - 403: Account not approved or deactivated
        - 404: User not found in Firestore
    """
    try:
        # Get Firebase user info from decorator
        firebase_uid = g.firebase_user['uid']
        firebase_email = g.firebase_user['email']

        # Get user data from Firestore
        user_doc = db.collection('users').document(firebase_email).get()

        if not user_doc.exists:
            # Try to find by firebase_uid
            users = db.collection('users').where('firebase_uid', '==', firebase_uid).limit(1).stream()
            user_doc = None
            for doc in users:
                user_doc = doc
                break

            if not user_doc:
                logger.warning(f"User not found in Firestore: {firebase_email}")
                return jsonify({'error': 'User not found. Please register first.'}), 404

        user_data = user_doc.to_dict()

        # Check approval status
        is_super_admin = user_data.get('is_super_admin', 0)
        approved = user_data.get('approved', 0)
        active = user_data.get('active', 1)

        # Super admins bypass approval check
        if is_super_admin != 1:
            if approved != 1:
                logger.warning(f"Login attempt for unapproved account: {firebase_email}")
                return jsonify({
                    'error': 'Account pending approval',
                    'approved': 0
                }), 403

            if active != 1:
                logger.warning(f"Login attempt for deactivated account: {firebase_email}")
                return jsonify({
                    'error': 'Account deactivated',
                    'active': 0
                }), 403

            # Check email verification (super admins bypass this check)
            if not user_data.get('email_verified', False):
                logger.warning(f"Login attempt with unverified email: {firebase_email}")
                return jsonify({
                    'error': 'EMAIL_NOT_VERIFIED',
                    'message': 'Please verify your email address before logging in. Check your inbox for the verification link.',
                    'email_verified': False
                }), 403

            # Check ToS version (super admins bypass this check)
            user_tos_version = user_data.get('tos_version', '0.0')
            tos_comparison = compare_tos_versions(user_tos_version, TOS_VERSION)

            # Only block login for major version changes
            if tos_comparison['requires_acceptance']:
                logger.info(f"User {firebase_email} needs to accept updated ToS - major version change (user: {user_tos_version}, required: {TOS_VERSION})")
                return jsonify({
                    'error': 'TOS_UPDATE_REQUIRED',
                    'message': 'Our Terms of Service have been updated with significant changes. Please review and accept the new terms to continue.',
                    'current_version': user_tos_version,
                    'required_version': TOS_VERSION,
                    'redirect': '/accept-updated-tos'
                }), 403

        # Check for minor ToS updates (will be included in success response)
        user_tos_version = user_data.get('tos_version', '0.0')
        tos_comparison = compare_tos_versions(user_tos_version, TOS_VERSION)
        tos_update_available = tos_comparison['has_updates'] and not tos_comparison['requires_acceptance']

        # Check for 2FA requirement
        if user_data.get('totp_enabled'):
            # Store pending 2FA verification
            session['pending_2fa_user'] = firebase_email
            session['pending_2fa_user_data'] = {
                'name': user_data.get('name'),
                'institute': user_data.get('institute'),
                'is_admin': user_data.get('is_admin', 0),
                'is_super_admin': is_super_admin
            }
            logger.info(f"2FA required for {firebase_email}")
            return jsonify({
                'success': True,
                'requires_2fa': True,
                'redirect': '/verify-2fa',
                'message': 'Two-factor authentication required'
            }), 200

        # Security: Create secure session (same as traditional login)
        session.permanent = True
        session.update({
            'user_id': firebase_email,
            'user_name': user_data.get('name'),
            'institute': user_data.get('institute'),
            'is_admin': user_data.get('is_admin', 0),
            'is_super_admin': is_super_admin,
            'approved': approved,
            'login_time': datetime.utcnow().isoformat(),
            'last_activity': datetime.utcnow().isoformat()
        })
        session.modified = True  # Explicitly mark session as modified

        # Log successful login
        role = "Super Admin" if is_super_admin == 1 else ("Admin" if user_data.get('is_admin') == 1 else "User")
        log_action(firebase_email, 'Firebase Login', f"Successful {role} login via Firebase Auth")
        logger.info(f"Successful {role} Firebase login for {firebase_email}")

        # Return user data with appropriate redirect URL
        redirect_url = '/super_admin_dashboard' if is_super_admin == 1 else ('/admin_dashboard' if user_data.get('is_admin', 0) == 1 else '/dashboard')

        response_data = {
            'success': True,
            'redirect': redirect_url,
            'user': {
                'uid': firebase_uid,
                'email': firebase_email,
                'name': user_data.get('name', ''),
                'institute': user_data.get('institute', ''),
                'is_admin': user_data.get('is_admin', 0),
                'is_super_admin': is_super_admin,
                'approved': approved,
                'active': active
            }
        }

        # Include ToS update notification for minor version changes
        if tos_update_available:
            response_data['tos_update_available'] = True
            response_data['tos_message'] = f'Our Terms of Service have been updated (v{TOS_VERSION}). Review the changes in Settings.'
            response_data['current_tos_version'] = TOS_VERSION

            # Create notification for minor ToS update
            try:
                from notification_service import notify_tos_update
                notify_tos_update(firebase_email, TOS_VERSION, is_major=False)
            except Exception as e:
                logger.warning(f"Failed to create ToS update notification: {e}")

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error verifying login: {e}", exc_info=True)
        return jsonify({'error': 'Login verification failed'}), 500


# ═══════════════════════════════════════════════════════════════════════════
# MOBILE APP JSON API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

# DEPRECATED - moved to mobile_api.py
# @app.route('/api/login', methods=['POST'])
# @csrf.exempt  # DEPRECATED - endpoint moved to mobile_api.py
def api_login_deprecated_old():
    """
    JSON API endpoint for mobile app login.
    Traditional email/password authentication.

    Expects JSON:
        {
            "email": "user@example.com",
            "password": "password123"
        }

    Returns JSON:
        {
            "ok": true,
            "uid": "user@example.com",
            "idToken": "bearer-token-here",
            "profile": {
                "email": "user@example.com",
                "name": "User Name",
                "role": "individual",
                "institute": "Institute Name",
                ...
            }
        }
    """
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        # Validation
        if not email or not password:
            return jsonify({'ok': False, 'error': 'EMAIL_PASSWORD_REQUIRED'}), 400

        # Security: Check rate limiting (email-based, Redis-backed)
        is_allowed, lockout_remaining = check_login_attempts(email)
        if not is_allowed:
            return jsonify({'ok': False, 'error': 'TOO_MANY_ATTEMPTS', 'retry_after': lockout_remaining}), 429

        # Get user from Firestore
        doc = db.collection('users').document(email).get()
        if not doc.exists:
            record_failed_login(email)
            return jsonify({'ok': False, 'error': 'INVALID_LOGIN_CREDENTIALS'}), 401

        user = doc.to_dict()

        # Verify password
        if not check_password_hash(user.get('password_hash', ''), password):
            record_failed_login(email)
            return jsonify({'ok': False, 'error': 'INVALID_LOGIN_CREDENTIALS'}), 401

        # Check approval status
        is_super_admin = user.get('is_super_admin', 0)
        approved = user.get('approved', 0)
        active = user.get('active', 1)

        if is_super_admin != 1:
            if approved != 1:
                return jsonify({'ok': False, 'error': 'NOT_APPROVED'}), 403
            if active != 1:
                return jsonify({'ok': False, 'error': 'DEACTIVATED'}), 403

        # Clear failed login attempts (Redis-based)
        clear_login_attempts(email)

        # Generate a simple bearer token (or use Firebase if available)
        # For now, we'll create a session-based token
        token = secrets.token_urlsafe(32)

        # Store token in Firestore (optional - for token validation)
        db.collection('user_tokens').document(email).set({
            'token': token,
            'created_at': SERVER_TIMESTAMP,
            'expires_at': datetime.utcnow() + timedelta(hours=8)
        })

        # Determine role
        if is_super_admin == 1:
            role = "super_admin"
        elif user.get('is_admin', 0) == 1:
            role = "institute_admin"
        else:
            role = "individual"

        # Log successful login
        log_action(email, 'API Login', f"Successful mobile login from IP {client_ip}")

        # Return user profile
        return jsonify({
            'ok': True,
            'uid': email,
            'idToken': token,
            'profile': {
                'email': email,
                'name': user.get('name', ''),
                'role': role,
                'institute': user.get('institute', ''),
                'institute_id': user.get('institute', ''),
                'approved': approved,
                'active': active
            }
        }), 200

    except Exception as e:
        logger.error(f"API login error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'LOGIN_FAILED'}), 500


# DEPRECATED - moved to mobile_api.py
# @app.route('/api/login_institute', methods=['POST'])
# @csrf.exempt
def api_login_institute_deprecated_old():
    """
    JSON API endpoint for institute admin login.
    Similar to /api/login but verifies admin role.
    """
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'ok': False, 'error': 'EMAIL_PASSWORD_REQUIRED'}), 400

        # Get user
        doc = db.collection('users').document(email).get()
        if not doc.exists:
            return jsonify({'ok': False, 'error': 'INVALID_LOGIN_CREDENTIALS'}), 401

        user = doc.to_dict()

        # Verify password
        if not check_password_hash(user.get('password_hash', ''), password):
            return jsonify({'ok': False, 'error': 'INVALID_LOGIN_CREDENTIALS'}), 401

        # Verify admin role
        if user.get('is_admin', 0) != 1 and user.get('is_super_admin', 0) != 1:
            return jsonify({'ok': False, 'error': 'NOT_ADMIN'}), 403

        # Check approval
        if user.get('approved', 0) != 1 and user.get('is_super_admin', 0) != 1:
            return jsonify({'ok': False, 'error': 'NOT_APPROVED'}), 403

        # Generate token
        token = secrets.token_urlsafe(32)
        db.collection('user_tokens').document(email).set({
            'token': token,
            'created_at': SERVER_TIMESTAMP,
            'expires_at': datetime.utcnow() + timedelta(hours=8)
        })

        role = "super_admin" if user.get('is_super_admin', 0) == 1 else "institute_admin"

        log_action(email, 'API Admin Login', f"Successful mobile admin login")

        return jsonify({
            'ok': True,
            'uid': email,
            'idToken': token,
            'profile': {
                'email': email,
                'name': user.get('name', ''),
                'role': role,
                'institute': user.get('institute', ''),
                'institute_id': user.get('institute', ''),
                'approved': user.get('approved', 1),
                'active': user.get('active', 1)
            }
        }), 200

    except Exception as e:
        logger.error(f"API institute login error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'LOGIN_FAILED'}), 500


@app.route('/api/register', methods=['POST'])
@csrf.exempt
def api_register():
    """
    JSON API endpoint for individual physiotherapist registration.
    """
    try:
        data = request.get_json() or {}

        # Prepare data for validation
        registration_data = {
            'name': data.get('name', '').strip(),
            'email': data.get('email', '').strip().lower(),
            'phone': data.get('phone', '').strip(),
            'institute': data.get('institute', '').strip(),
            'password': data.get('password', ''),
            'consent_data_processing': data.get('gdpr_data_processing', False),
            'consent_terms': data.get('gdpr_terms_of_service', False),
            'consent_ai': data.get('gdpr_ai_data_consent', False)
        }

        # Validate using Marshmallow schema
        is_valid, result = validate_json(UserRegistrationSchema, registration_data)
        if not is_valid:
            return jsonify({'ok': False, 'error': 'VALIDATION_FAILED', 'details': result}), 400

        # Use validated data
        name = result['name']
        email = result['email']
        phone = result['phone']
        institute = result['institute']
        password = result['password']
        gdpr_ai = result.get('consent_ai', False)

        # Check if user exists
        existing_user = db.collection('users').document(email).get()
        if existing_user.exists:
            return jsonify({'ok': False, 'error': 'EMAIL_EXISTS'}), 409

        # Create user
        pw_hash = generate_password_hash(password)
        db.collection('users').document(email).set({
            'name': name,
            'email': email,
            'phone': phone,
            'institute': institute,
            'password_hash': pw_hash,
            'created_at': SERVER_TIMESTAMP,
            'approved': 0,  # Pending approval
            'active': 1,
            'is_admin': 0,
            'user_type': 'individual',  # Track registration type
            'email_verified': False,  # Email verification required
            'consent_data_processing': 1,
            'consent_terms': 1,
            'consent_ai': 1 if gdpr_ai else 0,
            'consent_date': SERVER_TIMESTAMP
        })

        log_action(None, 'API Register', f"{name} ({email}) registered via mobile - pending approval and email verification")

        # Create and send email verification token
        try:
            from email_verification import create_verification_token

            token = create_verification_token(email)
            app_url = request.host_url.rstrip('/')

            send_email_verification(
                {'name': name, 'email': email},
                token,
                app_url
            )
            logger.info(f"Verification email sent to {email}")
        except Exception as verify_error:
            # Log error but don't fail registration
            logger.error(f"Failed to send verification email to {email}: {verify_error}")

        # Send notification to super admin via n8n
        try:
            send_registration_notification({
                'name': name,
                'email': email,
                'phone': phone,
                'institute': institute,
                'created_at': datetime.now().isoformat()
            })
        except Exception as webhook_error:
            # Log error but don't fail registration
            logger.error(f"Failed to send registration notification: {webhook_error}")

        return jsonify({
            'ok': True,
            'message': 'Registration successful. Please check your email to verify your account.'
        }), 201

    except Exception as e:
        logger.error(f"API register error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'REGISTRATION_FAILED'}), 500


@app.route('/api/register_institute', methods=['POST'])
@csrf.exempt
def api_register_institute():
    """
    JSON API endpoint for institute admin registration.
    Auto-approved with admin privileges.
    """
    try:
        data = request.get_json() or {}

        # Prepare data for validation
        registration_data = {
            'name': data.get('name', '').strip(),
            'email': data.get('email', '').strip().lower(),
            'phone': data.get('phone', '').strip(),
            'institute_name': data.get('institute', '').strip(),
            'password': data.get('password', ''),
            'consent_data_processing': data.get('gdpr_data_processing', True),  # Default to True for institute admins
            'consent_terms': data.get('gdpr_terms_of_service', True),
            'consent_ai': data.get('gdpr_ai_data_consent', False)
        }

        # Validate using Marshmallow schema
        is_valid, result = validate_json(InstituteRegistrationSchema, registration_data)
        if not is_valid:
            return jsonify({'ok': False, 'error': 'VALIDATION_FAILED', 'details': result}), 400

        # Use validated data
        name = result['name']
        email = result['email']
        phone = result.get('phone', '')
        institute = result['institute_name']
        password = result['password']

        # Check if user exists
        existing_user = db.collection('users').document(email).get()
        if existing_user.exists:
            return jsonify({'ok': False, 'error': 'EMAIL_EXISTS'}), 409

        # Create institute admin - REQUIRES SUPER ADMIN APPROVAL
        pw_hash = generate_password_hash(password)
        db.collection('users').document(email).set({
            'name': name,
            'email': email,
            'phone': phone,
            'institute': institute,
            'password_hash': pw_hash,
            'created_at': SERVER_TIMESTAMP,
            'approved': 0,  # Requires super admin approval
            'active': 1,
            'is_admin': 1,  # Admin privilege (activated upon approval)
            'is_super_admin': 0,
            'user_type': 'institute_admin'  # Track registration type
        })

        log_action(None, 'API Register Institute', f"{name} ({email}) registered as institute admin via mobile - pending super admin approval")

        # Send notification to super admin via n8n
        try:
            send_institute_admin_registration_notification({
                'name': name,
                'email': email,
                'phone': phone,
                'institute': institute,
                'created_at': datetime.now().isoformat()
            })
        except Exception as webhook_error:
            # Log error but don't fail registration
            logger.error(f"Failed to send institute admin registration notification: {webhook_error}")

        return jsonify({
            'ok': True,
            'message': 'Registration successful! Your account is pending super admin approval. You will receive an email once approved.'
        }), 201

    except Exception as e:
        logger.error(f"API register institute error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'REGISTRATION_FAILED'}), 500


@app.route('/api/register_with_institute', methods=['POST'])
@csrf.exempt
def api_register_with_institute():
    """
    JSON API endpoint for institute staff registration.
    Requires institute admin approval.
    """
    try:
        data = request.get_json() or {}

        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()
        institute = data.get('institute', '').strip()
        password = data.get('password', '')

        # Validation
        if not all([name, email, phone, institute, password]):
            return jsonify({'ok': False, 'error': 'MISSING_FIELDS'}), 400

        if len(password) < 8:
            return jsonify({'ok': False, 'error': 'PASSWORD_TOO_SHORT'}), 400

        # Check duplicates
        existing_user = db.collection('users').document(email).get()
        if existing_user.exists:
            return jsonify({'ok': False, 'error': 'EMAIL_EXISTS'}), 409

        # Check phone duplicate
        users = db.collection('users').where('phone', '==', phone).limit(1).stream()
        if list(users):
            return jsonify({'ok': False, 'error': 'PHONE_EXISTS'}), 409

        # Create institute staff member
        pw_hash = generate_password_hash(password)
        db.collection('users').document(email).set({
            'name': name,
            'email': email,
            'phone': phone,
            'institute': institute,
            'password_hash': pw_hash,
            'created_at': SERVER_TIMESTAMP,
            'approved': 0,  # Pending approval (super admin or institute admin)
            'active': 1,
            'is_admin': 0,
            'user_type': 'institute_staff'  # Track registration type
        })

        log_action(None, 'API Register Staff', f"{name} ({email}) registered as institute staff via mobile - pending approval")

        # Send notification to SUPER ADMIN (for visibility)
        try:
            send_registration_notification({
                'name': name,
                'email': email,
                'phone': phone,
                'institute': institute,
                'created_at': datetime.now().isoformat(),
                'user_type': 'institute_staff'
            })
        except Exception as email_error:
            # Log error but don't fail registration
            logger.error(f"Failed to send staff registration notification to super admin: {email_error}")

        # Also notify institute admin (they can approve)
        try:
            # Query for institute admin
            admins = db.collection('users').where('institute', '==', institute).where('is_admin', '==', 1).limit(1).stream()
            admin_email = None
            for admin_doc in admins:
                admin_email = admin_doc.id  # Document ID is the email
                break

            if admin_email:
                send_institute_staff_registration_notification({
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'institute': institute,
                    'created_at': datetime.now().isoformat()
                }, admin_email)
            else:
                logger.warning(f"No institute admin found for {institute} to send notification")
        except Exception as webhook_error:
            # Log error but don't fail registration
            logger.error(f"Failed to send institute staff registration notification: {webhook_error}")

        return jsonify({
            'ok': True,
            'message': 'Registration successful. Awaiting institute admin approval.'
        }), 201

    except Exception as e:
        logger.error(f"API register staff error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'REGISTRATION_FAILED'}), 500


@app.route('/api/institutes/list', methods=['GET'])
@csrf.exempt
def api_institutes_list():
    """
    JSON API endpoint to get list of registered institutes.
    Returns institutes that have admin users.
    """
    try:
        # Get all users with is_admin = 1
        admins = db.collection('users').where('is_admin', '==', 1).stream()

        # Extract unique institute names
        institutes = []
        seen = set()

        for admin in admins:
            user = admin.to_dict()
            institute_name = user.get('institute', '')
            if institute_name and institute_name not in seen:
                seen.add(institute_name)
                institutes.append({
                    'name': institute_name,
                    'institute': institute_name
                })

        # Sort alphabetically
        institutes.sort(key=lambda x: x['name'])

        return jsonify(institutes), 200

    except Exception as e:
        logger.error(f"API institutes list error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'FAILED_TO_FETCH_INSTITUTES'}), 500


@app.route('/api/test-firestore', methods=['GET'])
def test_firestore_connection():
    """
    Test endpoint to verify Firestore connectivity.
    Returns connection status and basic database info.

    Access: /api/test-firestore
    """
    try:
        # Test 1: Check if db client exists
        if db is None:
            return jsonify({
                'success': False,
                'error': 'Firestore client not initialized',
                'project_id': FIREBASE_PROJECT_ID
            }), 500

        # Test 2: Try to read a collection
        users_ref = db.collection('users')
        users_count = len(list(users_ref.limit(1).stream()))

        # Test 3: Try to write a test document
        test_ref = db.collection('_connection_test').document('test')
        test_ref.set({
            'timestamp': SERVER_TIMESTAMP,
            'test': 'Connection successful'
        })

        # Test 4: Read it back
        test_doc = test_ref.get()

        # Clean up test document
        test_ref.delete()

        # Success!
        return jsonify({
            'success': True,
            'message': 'Firestore connection successful',
            'project_id': FIREBASE_PROJECT_ID,
            'tests_passed': {
                'client_initialized': True,
                'can_read': True,
                'can_write': True,
                'can_delete': True
            },
            'database_info': {
                'users_collection_exists': users_count > 0,
                'test_document_created': test_doc.exists
            }
        }), 200

    except Exception as e:
        logger.error(f"Firestore connection test failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'project_id': FIREBASE_PROJECT_ID
        }), 500


# ═══════════════════════════════════════════════════════════════════════════
# GDPR COMPLIANCE ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/privacy-policy')
def privacy_policy():
    """Display Privacy Policy (GDPR requirement)"""
    return render_template('privacy_policy.html')


@app.route('/terms-of-service')
def terms_of_service():
    """Display Terms of Service"""
    return render_template('terms_of_service.html')


@app.route('/refund-policy')
def refund_policy():
    """Display Refund Policy"""
    return render_template('refund_policy.html')


@app.route('/accept-updated-tos')
def accept_updated_tos():
    """
    Display page for users to accept updated Terms of Service.
    This page is shown when user's accepted ToS version doesn't match current version.
    """
    return render_template('accept_updated_tos.html',
                          tos_version=TOS_VERSION,
                          tos_last_updated=TOS_LAST_UPDATED)


@app.route('/api/accept-updated-tos', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def api_accept_updated_tos():
    """
    API endpoint to accept updated Terms of Service.
    Updates user's tos_version and tos_accepted_at in Firestore.

    Expects:
        - Authorization header with Firebase ID token
        - JSON body with acceptance confirmation

    Returns:
        - 200: ToS accepted successfully
        - 400: Invalid request
        - 404: User not found
    """
    try:
        # Get Firebase user info from decorator
        firebase_email = g.firebase_user['email']

        # Get and validate request data
        data = request.get_json() or {}

        tos_data = {
            'tos_version': data.get('tos_version', TOS_VERSION),
            'accepted': data.get('accept_tos', False)
        }

        is_valid, result = validate_json(TOSAcceptanceSchema, tos_data)
        if not is_valid:
            return jsonify({'error': 'Invalid ToS acceptance data', 'details': result}), 400

        if not result['accepted']:
            return jsonify({'error': 'You must accept the Terms of Service to continue'}), 400

        # Get user document
        user_doc = db.collection('users').document(firebase_email).get()

        if not user_doc.exists:
            return jsonify({'error': 'User not found'}), 404

        # Update user's ToS acceptance
        db.collection('users').document(firebase_email).update({
            'tos_version': TOS_VERSION,
            'tos_accepted_at': SERVER_TIMESTAMP,
            'consent_terms': 1
        })

        # Log the action
        log_action(firebase_email, 'ToS Acceptance', f"Accepted Terms of Service version {TOS_VERSION}")
        logger.info(f"User {firebase_email} accepted ToS version {TOS_VERSION}")

        return jsonify({
            'success': True,
            'message': 'Terms of Service accepted successfully',
            'redirect': '/login/firebase'
        }), 200

    except Exception as e:
        logger.error(f"Error accepting ToS: {e}", exc_info=True)
        return jsonify({'error': 'Failed to accept Terms of Service'}), 500


@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required()
def edit_profile():
    """
    GDPR Right to Rectification: Allow users to update their personal data
    """
    user_email = session.get('user_id')
    user_ref = db.collection('users').document(user_email)
    user_doc = user_ref.get()

    if not user_doc.exists:
        flash("User not found", "error")
        return redirect(url_for('dashboard'))

    user_data = user_doc.to_dict()

    if request.method == 'POST':
        # Update profile fields
        updates = {
            'name': request.form.get('name', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'consent_ai': 1 if request.form.get('consent_ai') else 0
        }

        # Validate required fields
        if not updates['name']:
            flash("Name is required", "error")
            return redirect(url_for('edit_profile'))

        # Handle password change if provided
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if current_password or new_password or confirm_password:
            # Validate current password
            if not check_password_hash(user_data.get('password_hash', ''), current_password):
                flash("Current password is incorrect", "error")
                return redirect(url_for('edit_profile'))

            # Validate new password
            if len(new_password) < 8:
                flash("New password must be at least 8 characters", "error")
                return redirect(url_for('edit_profile'))

            if new_password != confirm_password:
                flash("New passwords do not match", "error")
                return redirect(url_for('edit_profile'))

            # Update password
            updates['password_hash'] = generate_password_hash(new_password)
            updates['password_changed_at'] = SERVER_TIMESTAMP
            log_action(user_email, 'Password Change', 'User changed password')

            # Security: Update user document
            user_ref.update(updates)

            # Security: Force logout after password change (best practice)
            # This invalidates the current session and requires re-login with new password
            session.clear()
            flash("Password changed successfully. Please log in with your new password.", "success")
            return redirect(url_for('login'))

        # Update user document (no password change)
        user_ref.update(updates)

        # Update session if name changed
        if updates['name'] != session.get('user_name'):
            session['user_name'] = updates['name']

        log_action(user_email, 'Profile Update', f"Updated profile: {', '.join([k for k in updates.keys() if k != 'password_hash'])}")
        flash("Profile updated successfully", "success")
        return redirect(url_for('dashboard'))

    # GET request - display form
    return render_template('edit_profile.html', user=user_data)


# ─────────────────────────────────────────────────────────────────────────────
# TWO-FACTOR AUTHENTICATION (2FA) - TOTP with Google Authenticator
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/setup-2fa')
@login_required()
def setup_2fa():
    """
    Setup 2FA - Generate secret and show QR code
    Only available for admin users
    """
    import pyotp
    import qrcode
    import io
    import base64

    user_email = session.get('user_id')
    user_ref = db.collection('users').document(user_email)
    user_doc = user_ref.get()

    if not user_doc.exists:
        flash("User not found", "error")
        return redirect(url_for('dashboard'))

    user_data = user_doc.to_dict()

    # Check if user is admin
    if user_data.get('is_admin') != 1:
        flash("2FA is only available for admin accounts", "warning")
        return redirect(url_for('edit_profile'))

    # Check if 2FA is already enabled
    if user_data.get('totp_enabled'):
        flash("2FA is already enabled", "info")
        return redirect(url_for('edit_profile'))

    # Generate new TOTP secret
    secret = pyotp.random_base32()

    # Store secret temporarily (not enabled yet)
    user_ref.update({
        'totp_secret_pending': secret
    })

    # Generate TOTP URI for QR code
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user_email,
        issuer_name="PhysiologicPRISM"
    )

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64 for display
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render_template('setup_2fa.html',
                          qr_code=qr_code_base64,
                          secret=secret)


@app.route('/enable-2fa', methods=['POST'])
@login_required()
def enable_2fa():
    """
    Verify TOTP code and enable 2FA
    """
    import pyotp
    import secrets

    user_email = session.get('user_id')
    user_ref = db.collection('users').document(user_email)
    user_doc = user_ref.get()

    if not user_doc.exists:
        flash("User not found", "error")
        return redirect(url_for('dashboard'))

    user_data = user_doc.to_dict()

    # Get the pending secret
    secret = user_data.get('totp_secret_pending')
    if not secret:
        flash("Please start 2FA setup first", "error")
        return redirect(url_for('setup_2fa'))

    # Get the verification code and validate
    form_data = {
        'totp_code': request.form.get('code', '').strip()
    }

    is_valid, result = validate_data(Verify2FASchema, form_data)
    if not is_valid:
        flash("Invalid TOTP code format (6 digits required)", "error")
        return redirect(url_for('setup_2fa'))

    code = result['totp_code']

    # Verify the code
    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        flash("Invalid verification code. Please try again.", "error")
        return redirect(url_for('setup_2fa'))

    # Generate backup codes
    backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
    hashed_backup_codes = [generate_password_hash(code) for code in backup_codes]

    # Enable 2FA
    user_ref.update({
        'totp_enabled': True,
        'totp_secret': secret,
        'totp_secret_pending': None,
        'totp_backup_codes': hashed_backup_codes,
        'totp_enabled_at': SERVER_TIMESTAMP
    })

    log_action(user_email, 'Enable 2FA', 'User enabled two-factor authentication')

    # Show backup codes to user
    return render_template('2fa_backup_codes.html', backup_codes=backup_codes)


@app.route('/disable-2fa', methods=['POST'])
@login_required()
def disable_2fa():
    """
    Disable 2FA (requires password confirmation)
    """
    user_email = session.get('user_id')
    user_ref = db.collection('users').document(user_email)
    user_doc = user_ref.get()

    if not user_doc.exists:
        flash("User not found", "error")
        return redirect(url_for('dashboard'))

    user_data = user_doc.to_dict()

    # Validate input
    form_data = {
        'password': request.form.get('password', ''),
        'totp_code': request.form.get('totp_code', '')
    }

    is_valid, result = validate_data(Disable2FASchema, form_data)
    if not is_valid:
        flash("Invalid input. Please check your entries.", "error")
        return redirect(url_for('edit_profile'))

    # Verify password
    password = result['password']
    if not check_password_hash(user_data.get('password_hash', ''), password):
        flash("Incorrect password", "error")
        return redirect(url_for('edit_profile'))

    # Disable 2FA
    user_ref.update({
        'totp_enabled': False,
        'totp_secret': None,
        'totp_backup_codes': None,
        'totp_disabled_at': SERVER_TIMESTAMP
    })

    log_action(user_email, 'Disable 2FA', 'User disabled two-factor authentication')
    flash("Two-factor authentication has been disabled", "success")
    return redirect(url_for('edit_profile'))


@app.route('/api/cancel-2fa', methods=['POST'])
@csrf.exempt
def cancel_2fa():
    """Cancel pending 2FA verification"""
    session.pop('pending_2fa_user', None)
    session.pop('pending_2fa_user_data', None)
    return jsonify({'success': True}), 200


@app.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    """
    Verify 2FA code during login
    """
    import pyotp

    # Check if we have a pending 2FA verification
    pending_user = session.get('pending_2fa_user')
    if not pending_user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Validate TOTP code
        form_data = {
            'totp_code': request.form.get('code', '').strip()
        }

        is_valid, result = validate_data(Verify2FASchema, form_data)
        if not is_valid:
            flash("Invalid TOTP code format (6 digits required)", "error")
            return redirect('/verify-2fa')

        code = result['totp_code']
        use_backup = request.form.get('use_backup') == '1'

        # Get user data
        user_ref = db.collection('users').document(pending_user)
        user_doc = user_ref.get()

        if not user_doc.exists:
            session.pop('pending_2fa_user', None)
            flash("User not found", "error")
            return redirect(url_for('login'))

        user_data = user_doc.to_dict()

        verified = False

        if use_backup:
            # Verify backup code
            backup_codes = user_data.get('totp_backup_codes', [])
            for i, hashed_code in enumerate(backup_codes):
                if check_password_hash(hashed_code, code.upper()):
                    # Remove used backup code
                    backup_codes.pop(i)
                    user_ref.update({'totp_backup_codes': backup_codes})
                    verified = True
                    log_action(pending_user, '2FA Backup Code Used', f'Used backup code (remaining: {len(backup_codes)})')
                    break
        else:
            # Verify TOTP code
            secret = user_data.get('totp_secret')
            if secret:
                totp = pyotp.TOTP(secret)
                verified = totp.verify(code, valid_window=1)

        if verified:
            # Complete login
            session.pop('pending_2fa_user', None)
            session['user_id'] = pending_user
            session['user_name'] = user_data.get('name')
            session['is_admin'] = user_data.get('is_admin', 0)
            session['institute'] = user_data.get('institute')
            session['login_time'] = datetime.now().isoformat()

            log_action(pending_user, 'Login', 'Successful login with 2FA')
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid verification code", "error")
            return render_template('verify_2fa.html')

    return render_template('verify_2fa.html')


@app.route('/export-data')
@login_required()
def export_data_page():
    """
    Data export options page - allows users to choose export format
    """
    return render_template('export_data.html')


@app.route('/export-my-data')
@login_required()
def export_my_data():
    """
    GDPR Right to Data Portability: Export all user data in JSON format
    """
    user_email = session.get('user_id')

    try:
        # Collect all user data
        export_data = {
            'export_date': datetime.utcnow().isoformat(),
            'user_email': user_email,
            'personal_data': {},
            'patients': [],
            'audit_logs': []
        }

        # Get user profile
        user_doc = db.collection('users').document(user_email).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            # Remove sensitive fields
            user_data.pop('password_hash', None)
            export_data['personal_data'] = user_data

        # Get all patients created by this user
        patients_ref = db.collection('patients').where('physio_id', '==', user_email).stream()
        for patient_doc in patients_ref:
            patient_data = patient_doc.to_dict()
            patient_data['patient_id'] = patient_doc.id
            export_data['patients'].append(patient_data)

        # Get audit logs for this user
        logs_ref = db.collection('audit_logs').where('user_id', '==', user_email).order_by('timestamp', direction='DESCENDING').limit(1000).stream()
        for log_doc in logs_ref:
            log_data = log_doc.to_dict()
            # Convert timestamp to ISO format
            if 'timestamp' in log_data and hasattr(log_data['timestamp'], 'isoformat'):
                log_data['timestamp'] = log_data['timestamp'].isoformat()
            export_data['audit_logs'].append(log_data)

        # Create JSON response
        response = make_response(json.dumps(export_data, indent=2, default=str))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename=physio_assist_data_{user_email}_{datetime.utcnow().strftime("%Y%m%d")}.json'

        log_action(user_email, 'Data Export', 'User exported personal data (GDPR)')
        return response

    except Exception as e:
        logger.error(f"Error exporting data for {user_email}: {e}")
        flash("Error exporting data. Please try again or contact support.", "error")
        return redirect(url_for('dashboard'))


@app.route('/export/patients/csv')
@login_required()
def export_patients_csv():
    """
    GDPR Right to Data Portability: Export patient data in CSV format
    """
    user_email = session.get('user_id')

    try:
        # Get all patients created by this user
        patients_ref = db.collection('patients').where('physio_id', '==', user_email).stream()

        # Prepare CSV data
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            'Patient ID', 'Name', 'Age/Sex', 'Contact', 'Chief Complaint',
            'Present History', 'Past History', 'Created At', 'Updated At'
        ])

        # Write patient data
        for patient_doc in patients_ref:
            patient_data = patient_doc.to_dict()
            writer.writerow([
                patient_doc.id,
                patient_data.get('name', ''),
                patient_data.get('age_sex', ''),
                patient_data.get('contact', ''),
                patient_data.get('chief_complaint', ''),
                patient_data.get('present_history', ''),
                patient_data.get('past_history', ''),
                patient_data.get('created_at', ''),
                patient_data.get('updated_at', '')
            ])

        # Create CSV response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=patients_export_{datetime.utcnow().strftime("%Y%m%d")}.csv'

        log_action(user_email, 'Patients CSV Export', 'User exported patient data as CSV (GDPR)')
        return response

    except Exception as e:
        logger.error(f"Error exporting patients CSV for {user_email}: {e}")
        flash("Error exporting patient data. Please try again or contact support.", "error")
        return redirect(url_for('edit_profile'))


@app.route('/export/patients/pdf')
@login_required()
def export_patients_pdf():
    """
    GDPR Right to Data Portability: Export patient data in PDF format
    """
    user_email = session.get('user_id')

    try:
        # Get user info
        user_doc = db.collection('users').document(user_email).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        user_name = user_data.get('name', user_email)

        # Get all patients created by this user
        patients_ref = db.collection('patients').where('physio_id', '==', user_email).stream()
        patients = []
        for patient_doc in patients_ref:
            patient_data = patient_doc.to_dict()
            patient_data['patient_id'] = patient_doc.id
            patients.append(patient_data)

        # Create HTML for PDF
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                h2 {{ color: #34495e; margin-top: 30px; }}
                .patient-card {{
                    border: 1px solid #ddd;
                    padding: 15px;
                    margin-bottom: 20px;
                    border-radius: 5px;
                    background-color: #f9f9f9;
                }}
                .field {{ margin-bottom: 10px; }}
                .field strong {{ color: #2c3e50; }}
                .export-info {{
                    background-color: #e8f5e9;
                    padding: 10px;
                    border-left: 4px solid #4caf50;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <h1>Patient Data Export - PhysiologicPRISM</h1>
            <div class="export-info">
                <p><strong>Exported for:</strong> {user_name} ({user_email})</p>
                <p><strong>Export Date:</strong> {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC</p>
                <p><strong>Total Patients:</strong> {len(patients)}</p>
            </div>
        """

        for patient in patients:
            html_content += f"""
            <div class="patient-card">
                <h2>{patient.get('name', 'N/A')}</h2>
                <div class="field"><strong>Patient ID:</strong> {patient.get('patient_id', 'N/A')}</div>
                <div class="field"><strong>Age/Sex:</strong> {patient.get('age_sex', 'N/A')}</div>
                <div class="field"><strong>Contact:</strong> {patient.get('contact', 'N/A')}</div>
                <div class="field"><strong>Chief Complaint:</strong> {patient.get('chief_complaint', 'N/A')}</div>
                <div class="field"><strong>Present History:</strong> {patient.get('present_history', 'N/A')}</div>
                <div class="field"><strong>Past History:</strong> {patient.get('past_history', 'N/A')}</div>
                <div class="field"><strong>Provisional Diagnosis:</strong> {patient.get('provisional_diagnosis', 'N/A')}</div>
                <div class="field"><strong>Created:</strong> {patient.get('created_at', 'N/A')}</div>
            </div>
            """

        html_content += """
        </body>
        </html>
        """

        # Convert HTML to PDF
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.BytesIO(html_content.encode('utf-8')), dest=pdf_buffer)

        if pisa_status.err:
            raise Exception("PDF generation failed")

        pdf_buffer.seek(0)
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=patients_export_{datetime.utcnow().strftime("%Y%m%d")}.pdf'

        log_action(user_email, 'Patients PDF Export', 'User exported patient data as PDF (GDPR)')
        return response

    except Exception as e:
        logger.error(f"Error exporting patients PDF for {user_email}: {e}")
        flash("Error exporting patient data as PDF. Please try again or contact support.", "error")
        return redirect(url_for('edit_profile'))


@app.route('/export/audit-logs/csv')
@login_required()
def export_my_audit_logs_csv():
    """
    GDPR Right to Data Portability: Export user's own audit logs in CSV format
    """
    user_email = session.get('user_id')

    try:
        # Get audit logs for this user
        logs_ref = db.collection('audit_logs').where('user_id', '==', user_email).order_by('timestamp', direction='DESCENDING').limit(5000).stream()

        # Prepare CSV data
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Timestamp', 'Action', 'Details'])

        # Write log data
        for log_doc in logs_ref:
            log_data = log_doc.to_dict()
            timestamp = log_data.get('timestamp', '')
            if hasattr(timestamp, 'isoformat'):
                timestamp = timestamp.isoformat()
            writer.writerow([
                timestamp,
                log_data.get('action', ''),
                log_data.get('details', '')
            ])

        # Create CSV response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=audit_logs_{datetime.utcnow().strftime("%Y%m%d")}.csv'

        log_action(user_email, 'Audit Logs CSV Export', 'User exported audit logs as CSV (GDPR)')
        return response

    except Exception as e:
        logger.error(f"Error exporting audit logs CSV for {user_email}: {e}")
        flash("Error exporting audit logs. Please try again or contact support.", "error")
        return redirect(url_for('edit_profile'))


# ═══════════════════════════════════════════════════════════════════════════
# INVOICE MANAGEMENT ROUTES (GST COMPLIANCE)
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/my-invoices')
@login_required()
def my_invoices():
    """
    View all invoices for current user (GST tax compliance)
    """
    try:
        user_email = session.get('user_id')

        # Get all invoices for this user
        invoices = db.collection('invoices').where('user_id', '==', user_email).order_by('invoice_date', direction='DESCENDING').stream()

        invoices_list = []
        for invoice_doc in invoices:
            invoice_data = invoice_doc.to_dict()
            invoice_data['invoice_id'] = invoice_doc.id
            invoices_list.append(invoice_data)

        log_action(user_email, 'View Invoices', f'User viewed invoices page ({len(invoices_list)} invoices)')

        return render_template('my_invoices.html', invoices=invoices_list)

    except Exception as e:
        logger.error(f"Error loading invoices for {user_email}: {e}")
        flash("Error loading invoices. Please try again.", "error")
        return redirect(url_for('dashboard'))


@app.route('/invoices/<invoice_id>')
@login_required()
def view_invoice(invoice_id):
    """
    View single invoice details
    """
    try:
        user_email = session.get('user_id')

        # Get invoice
        invoice_ref = db.collection('invoices').document(invoice_id)
        invoice_doc = invoice_ref.get()

        if not invoice_doc.exists:
            flash("Invoice not found", "error")
            return redirect(url_for('my_invoices'))

        invoice_data = invoice_doc.to_dict()

        # Security: Verify invoice belongs to current user
        if invoice_data.get('user_id') != user_email:
            flash("Unauthorized access to invoice", "error")
            return redirect(url_for('my_invoices'))

        invoice_data['invoice_id'] = invoice_id

        log_action(user_email, 'View Invoice', f'User viewed invoice {invoice_data.get("invoice_number")}')

        return render_template('view_invoice.html', invoice=invoice_data)

    except Exception as e:
        logger.error(f"Error viewing invoice {invoice_id}: {e}")
        flash("Error loading invoice. Please try again.", "error")
        return redirect(url_for('my_invoices'))


@app.route('/invoices/<invoice_id>/download')
@login_required()
def download_invoice(invoice_id):
    """
    Download invoice as PDF
    """
    try:
        user_email = session.get('user_id')

        # Get invoice
        invoice_ref = db.collection('invoices').document(invoice_id)
        invoice_doc = invoice_ref.get()

        if not invoice_doc.exists:
            flash("Invoice not found", "error")
            return redirect(url_for('my_invoices'))

        invoice_data = invoice_doc.to_dict()

        # Security: Verify invoice belongs to current user
        if invoice_data.get('user_id') != user_email:
            flash("Unauthorized access to invoice", "error")
            return redirect(url_for('my_invoices'))

        # Generate PDF
        from invoice_generator import generate_invoice_pdf

        pdf_content = generate_invoice_pdf(invoice_data)

        if not pdf_content:
            flash("Error generating PDF. Please try again.", "error")
            return redirect(url_for('my_invoices'))

        # Return PDF as download
        invoice_number = invoice_data.get('invoice_number', 'invoice')
        filename = f"{invoice_number}.pdf"

        response = make_response(pdf_content)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'

        log_action(user_email, 'Download Invoice', f'User downloaded invoice {invoice_data.get("invoice_number")}')

        return response

    except Exception as e:
        logger.error(f"Error downloading invoice {invoice_id}: {e}")
        flash("Error downloading invoice. Please try again.", "error")
        return redirect(url_for('my_invoices'))


@app.route('/request-data-deletion', methods=['GET', 'POST'])
@login_required()
def request_data_deletion():
    """
    GDPR Right to Erasure (Right to be Forgotten): Request account deletion
    """
    user_email = session.get('user_id')
    user_ref = db.collection('users').document(user_email)
    user_doc = user_ref.get()

    if not user_doc.exists:
        flash("User not found", "error")
        return redirect(url_for('dashboard'))

    user_data = user_doc.to_dict()

    # Check if deletion is already pending
    deletion_pending = user_data.get('deletion_requested', False)
    deletion_request_date = user_data.get('deletion_request_date', '')

    if request.method == 'POST':
        # Validate deletion request data
        deletion_data = {
            'reason': request.form.get('reason', ''),
            'confirm_deletion': request.form.get('confirm_deletion') == 'on',
            'password': request.form.get('password', '')
        }

        is_valid, result = validate_data(DataDeletionRequestSchema, deletion_data)
        if not is_valid:
            flash(f"Validation error: {result}", "error")
            return redirect('/request-data-deletion')

        # Verify email confirmation
        confirm_email = request.form.get('confirm_email', '').strip().lower()
        if confirm_email != user_email.lower():
            flash("Email confirmation does not match", "error")
            return redirect(url_for('request_data_deletion'))

        # Verify password
        password = request.form.get('password', '')
        if not check_password_hash(user_data.get('password_hash', ''), password):
            flash("Incorrect password", "error")
            return redirect(url_for('request_data_deletion'))

        # Verify understanding checkbox
        if not request.form.get('confirm_understanding'):
            flash("You must confirm that you understand the consequences", "error")
            return redirect(url_for('request_data_deletion'))

        # Get deletion reason (optional)
        deletion_reason = request.form.get('deletion_reason', '').strip()

        # Calculate scheduled deletion date (30 days from now)
        scheduled_deletion = datetime.utcnow() + timedelta(days=30)

        # Mark account for deletion
        user_ref.update({
            'deletion_requested': True,
            'deletion_request_date': SERVER_TIMESTAMP,
            'scheduled_deletion_date': scheduled_deletion,
            'deletion_reason': deletion_reason,
            'active': 0  # Deactivate account immediately
        })

        # Log the deletion request
        log_action(user_email, 'Account Deletion Request', f"User requested account deletion. Reason: {deletion_reason or 'Not provided'}. Scheduled for: {scheduled_deletion.strftime('%Y-%m-%d')}")

        # Clear session and redirect to login
        session.clear()
        flash("Your account deletion request has been submitted. Your account is now deactivated.", "success")
        return redirect(url_for('login'))

    # GET request - display form
    return render_template(
        'request_data_deletion.html',
        deletion_pending=deletion_pending,
        deletion_request_date=deletion_request_date
    )


@app.route('/cancel-data-deletion', methods=['POST'])
@login_required()
def cancel_data_deletion():
    """
    Allow users to cancel account deletion during the 30-day grace period
    """
    user_email = session.get('user_id')
    user_ref = db.collection('users').document(user_email)
    user_doc = user_ref.get()

    if not user_doc.exists:
        flash("User not found", "error")
        return redirect(url_for('dashboard'))

    user_data = user_doc.to_dict()

    # Check if deletion is pending
    if not user_data.get('deletion_requested', False):
        flash("No deletion request found", "info")
        return redirect(url_for('edit_profile'))

    # Cancel the deletion request
    user_ref.update({
        'deletion_requested': False,
        'deletion_request_date': None,
        'scheduled_deletion_date': None,
        'deletion_cancelled_at': SERVER_TIMESTAMP,
        'active': 1  # Reactivate account
    })

    # Log the cancellation
    log_action(user_email, 'Account Deletion Cancelled', 'User cancelled account deletion request during grace period')

    flash("Your account deletion request has been cancelled. Your account is now active again.", "success")
    return redirect(url_for('edit_profile'))


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/notifications', methods=['GET'])
@login_required()
def get_notifications():
    """Get notifications for current user"""
    try:
        from notification_service import NotificationService

        user_email = session.get('user_id')
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


@app.route('/api/notifications/unread-count', methods=['GET'])
@login_required()
def get_unread_count():
    """Get count of unread notifications"""
    try:
        from notification_service import NotificationService

        user_email = session.get('user_id')
        count = NotificationService.get_unread_count(user_email)

        return jsonify({'success': True, 'count': count}), 200

    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        return jsonify({'success': False, 'error': 'Failed to get unread count'}), 500


@app.route('/api/version', methods=['GET'])
def get_app_version():
    """Get current app version for auto-reload system"""
    # Increment this version number when deploying new changes
    APP_VERSION = '1.0.6'
    MOBILE_VERSION = '1.0.0'  # Update this when mobile app version changes
    return jsonify({
        'version': APP_VERSION,
        'mobile_version': MOBILE_VERSION,
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/api/notifications/<notification_id>/read', methods=['POST'])
@login_required()
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        from notification_service import NotificationService

        user_email = session.get('user_id')
        success = NotificationService.mark_as_read(notification_id, user_email)

        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'success': False, 'error': 'Notification not found or access denied'}), 404

    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return jsonify({'success': False, 'error': 'Failed to mark notification as read'}), 500


@app.route('/api/notifications/read-all', methods=['POST'])
@login_required()
def mark_all_notifications_read():
    """Mark all notifications as read"""
    try:
        from notification_service import NotificationService

        user_email = session.get('user_id')
        count = NotificationService.mark_all_as_read(user_email)

        return jsonify({'success': True, 'count': count}), 200

    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        return jsonify({'success': False, 'error': 'Failed to mark notifications as read'}), 500


@app.route('/api/notifications/<notification_id>', methods=['DELETE'])
@login_required()
def delete_notification(notification_id):
    """Delete a notification"""
    try:
        from notification_service import NotificationService

        user_email = session.get('user_id')
        success = NotificationService.delete_notification(notification_id, user_email)

        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'success': False, 'error': 'Notification not found or access denied'}), 404

    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete notification'}), 500


@app.route('/notifications')
@login_required()
def notifications_page():
    """Notification history page"""
    try:
        from notification_service import NotificationService

        user_email = session.get('user_id')
        notifications = NotificationService.get_user_notifications(user_email, limit=100)

        return render_template('notifications.html',
                             notifications=notifications,
                             name=session.get('user_name'))

    except Exception as e:
        logger.error(f"Error loading notifications page: {e}")
        flash("Could not load notifications. Please try again later.", "error")
        return redirect(url_for('dashboard'))


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULED TASKS (Called by Cloud Scheduler)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/cron/check-subscription-reminders', methods=['POST'])
def cron_check_subscription_reminders():
    """
    Scheduled task to check subscription renewals and trial expiries.
    Should be called daily by Cloud Scheduler.

    Security: Validates X-CloudScheduler-JobName header or secret token.

    Returns:
        JSON summary of notifications sent
    """
    # Verify this is from Cloud Scheduler or has valid secret
    scheduler_header = request.headers.get('X-CloudScheduler-JobName')
    auth_header = request.headers.get('Authorization')
    cron_secret = os.environ.get('CRON_SECRET', 'default-cron-secret')

    if not scheduler_header and auth_header != f'Bearer {cron_secret}':
        logger.warning("Unauthorized cron access attempt")
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        from subscription_manager import check_subscription_reminders
        summary = check_subscription_reminders()

        logger.info(f"Subscription reminder cron completed: {summary}")
        return jsonify({
            'success': True,
            'summary': summary
        }), 200

    except Exception as e:
        logger.error(f"Error in subscription reminder cron: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/cron/cleanup-old-notifications', methods=['POST'])
def cron_cleanup_old_notifications():
    """
    Scheduled task to delete notifications older than 90 days.
    Should be called weekly by Cloud Scheduler.

    Returns:
        JSON summary of deleted notifications
    """
    # Verify this is from Cloud Scheduler or has valid secret
    scheduler_header = request.headers.get('X-CloudScheduler-JobName')
    auth_header = request.headers.get('Authorization')
    cron_secret = os.environ.get('CRON_SECRET', 'default-cron-secret')

    if not scheduler_header and auth_header != f'Bearer {cron_secret}':
        logger.warning("Unauthorized cron access attempt")
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        from notification_service import NotificationService
        deleted_count = NotificationService.delete_old_notifications(days=90)

        logger.info(f"Notification cleanup cron completed: {deleted_count} deleted")
        return jsonify({
            'success': True,
            'deleted_count': deleted_count
        }), 200

    except Exception as e:
        logger.error(f"Error in notification cleanup cron: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/dashboard')
@login_required()
def dashboard():
    """
    User dashboard with usage analytics and statistics
    """
    try:
        user_email = session.get('user_id')

        # Get subscription and usage data
        from subscription_manager import get_usage_stats, get_plan_info, PLANS
        usage_stats = get_usage_stats(user_email)

        # Get plan details
        plan_type = usage_stats.get('plan_type', 'free_trial')
        plan_info = PLANS.get(plan_type, {})

        # Get total patient count (all time) - optimized query
        patients_ref = db.collection('patients').where('created_by', '==', user_email)
        patient_docs = list(patients_ref.stream())
        total_patients = len(patient_docs)

        # Convert to list of dicts
        patients_list = [doc.to_dict() for doc in patient_docs]

        # Get recent patients (last 30 days) - client-side filtering to avoid index requirement
        from datetime import datetime, timedelta, timezone
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        # Helper to parse created_at ISO strings from Cosmos DB
        def parse_created_at_iso(created_at):
            if not created_at:
                return None
            if isinstance(created_at, str):
                try:
                    return datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    return None
            return created_at

        try:
            # Try server-side filtering (requires Cosmos DB index)
            # Convert datetime to ISO format string for Cosmos DB query
            thirty_days_ago_iso = thirty_days_ago.isoformat()
            recent_patients_ref = patients_ref.where('created_at', '>=', thirty_days_ago_iso)
            recent_patients_count = len(list(recent_patients_ref.stream()))
        except Exception as e:
            # Fallback to client-side filtering if index doesn't exist
            logger.warning(f"Error loading dashboard analytics: {e}")
            recent_patients_count = len([
                p for p in patients_list
                if parse_created_at_iso(p.get('created_at')) and parse_created_at_iso(p.get('created_at')) >= thirty_days_ago
            ])

        # Get cache statistics (user-specific would be better, but using global for now)
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
                    renewal_date = period_end
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
                    renewal_date = trial_end
                    # Make timezone-naive for comparison
                    trial_end_naive = trial_end.replace(tzinfo=None) if trial_end.tzinfo else trial_end
                    days_until_renewal = (trial_end_naive - datetime.utcnow()).days
                    show_renewal_warning = days_until_renewal <= 3
            except:
                pass

        # Determine quota status colors
        patients_status = 'success' if usage_stats.get('patients_percent', 0) < 70 else ('warning' if usage_stats.get('patients_percent', 0) < 90 else 'danger')
        ai_status = 'success' if usage_stats.get('ai_percent', 0) < 70 else ('warning' if usage_stats.get('ai_percent', 0) < 90 else 'danger')

        analytics_data = {
            # Usage stats
            'usage_stats': usage_stats,
            'plan_info': plan_info,
            'plan_type': plan_type,

            # Patient statistics
            'total_patients': total_patients,
            'recent_patients': recent_patients_count,
            'patients_list': patients_list,  # For completion tracking

            # Cache statistics
            'cache_stats': cache_stats,
            'cache_hit_rate': cache_stats.get('hit_rate_percent', 0),
            'cache_savings_usd': cache_stats.get('total_savings_usd', 0),

            # Renewal information
            'days_until_renewal': days_until_renewal,
            'renewal_date': renewal_date,
            'show_renewal_warning': show_renewal_warning,

            # Status indicators
            'patients_status': patients_status,
            'ai_status': ai_status,
        }

        return render_template('dashboard.html',
                             name=session.get('user_name'),
                             analytics=analytics_data)

    except Exception as e:
        logger.error(f"Error loading dashboard analytics: {e}", exc_info=True)
        # Fallback to basic dashboard
        return render_template('dashboard.html',
                             name=session.get('user_name'),
                             analytics={})


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
        .where('is_admin', '==', 0)
        .where('approved', '==', 0)
        .where('institute', '==', session.get('institute'))
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
        """Enhanced patient list with advanced search and filtering"""
        # Get filter parameters
        name_filter = request.args.get('name', '').strip()
        id_filter = request.args.get('patient_id', '').strip()
        contact_filter = request.args.get('contact', '').strip()
        complaint_filter = request.args.get('complaint', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        sort_by = request.args.get('sort', 'newest')  # newest, oldest, name_asc, name_desc
        status_filter = request.args.get('status', '').strip()  # active, completed, archived
        tags_filter = request.args.getlist('tags')  # Multiple tags can be selected

        try:
            # 1) Base query - fetch all patients for this user
            coll = db.collection('patients')

            # 2) Restrict by institute or physio
            if session.get('is_admin') == 1:
                q = coll.where('institute', '==', session.get('institute'))
            else:
                q = coll.where('physio_id', '==', session.get('user_id'))

            # 3) Execute query
            docs = q.stream()
            patients = [doc.to_dict() for doc in docs]

            # Note: Removed N+1 query problem - assessment status is now loaded on demand via frontend

            # Helper function to parse created_at (stored as ISO string in Cosmos DB)
            def parse_created_at(patient):
                """Parse created_at from ISO string to datetime object"""
                created_at = patient.get('created_at')
                if not created_at:
                    return None
                if isinstance(created_at, str):
                    try:
                        # Parse ISO format: "2026-01-18T15:39:55.123456+00:00"
                        return datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        return None
                # Already a datetime object
                return created_at

            # 4) Apply client-side filtering (to avoid Firestore query limitations)
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

            # 5) Date range filtering
            if date_from:
                try:
                    from_date = datetime.strptime(date_from, '%Y-%m-%d')
                    filtered_patients = [p for p in filtered_patients
                                        if parse_created_at(p) and parse_created_at(p) >= from_date]
                except ValueError:
                    pass  # Invalid date format, skip filter

            if date_to:
                try:
                    to_date = datetime.strptime(date_to, '%Y-%m-%d')
                    # Add 1 day to include the entire end date
                    to_date = to_date + timedelta(days=1)
                    filtered_patients = [p for p in filtered_patients
                                        if parse_created_at(p) and parse_created_at(p) < to_date]
                except ValueError:
                    pass  # Invalid date format, skip filter

            # 6) Apply sorting
            if sort_by == 'newest':
                filtered_patients.sort(key=lambda p: parse_created_at(p) or datetime.min, reverse=True)
            elif sort_by == 'oldest':
                filtered_patients.sort(key=lambda p: parse_created_at(p) or datetime.min)
            elif sort_by == 'name_asc':
                filtered_patients.sort(key=lambda p: (p.get('name') or '').lower())
            elif sort_by == 'name_desc':
                filtered_patients.sort(key=lambda p: (p.get('name') or '').lower(), reverse=True)

            # 7) Apply pagination (limit to 50 patients per page)
            page = request.args.get('page', 1, type=int)
            per_page = 50
            total_pages = (len(filtered_patients) + per_page - 1) // per_page
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_patients = filtered_patients[start_idx:end_idx]

        except GoogleAPIError as e:
            logger.error(f"Firestore error in view_patients: {e}", exc_info=True)
            flash("Could not load your patients list. Please try again later.", "error")
            return redirect(url_for('dashboard'))

        # 8) Collect unique tags from all patients for filter dropdown
        all_tags = set()
        for p in patients:
            all_tags.update(p.get('tags') or [])
        all_tags = sorted(list(all_tags))

        # 9) Render on success
        return render_template('view_patients.html',
                             patients=paginated_patients,
                             total_count=len(patients),
                             filtered_count=len(filtered_patients),
                             all_tags=all_tags,
                             current_status=status_filter,
                             current_tags=tags_filter,
                             page=page,
                             total_pages=total_pages)



@app.route('/register_institute', methods=['GET', 'POST'])
def register_institute():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        pwd = generate_password_hash(request.form['password'])
        inst = request.form['institute']
        db.collection('users').document(email).set({
            'name': name,
            'email': email,
            'phone': phone,
            'password_hash': pwd,
            'institute': inst,
            'is_admin': 1,
            'approved': 0,  # Requires super admin approval
            'active': 1,
            'created_at': SERVER_TIMESTAMP,
            'user_type': 'institute_admin',  # Track registration type
            # GDPR Consent fields
            'consent_data_processing': 1,
            'consent_terms': 1,
            'consent_ai': 0,  # Default for institute admins
            'consent_date': SERVER_TIMESTAMP,
            # ToS Acceptance Logging (Legal requirement)
            'tos_accepted_at': SERVER_TIMESTAMP,
            'tos_version': TOS_VERSION,
        })
        log_action(None, 'Register', f"{name} registered as Institute Admin - pending super admin approval")

        # Send notification to super admin
        try:
            send_institute_admin_registration_notification({
                'name': name,
                'email': email,
                'phone': phone,
                'institute': inst,
                'created_at': datetime.now().isoformat()
            })
        except Exception as email_error:
            # Log error but don't fail registration
            logger.error(f"Failed to send institute admin registration notification for {email}: {email_error}")

        flash("Registration successful! Your account is pending super admin approval. You will receive an email once approved.", "success")
        return redirect('/login_institute')
    return render_template('register_institute.html')


@app.route('/login_institute', methods=['GET', 'POST'])
def login_institute():
    if request.method == 'POST':
        # Input validation and sanitization
        email = request.form.get('email', '').strip().lower()
        pwd = request.form.get('password', '')

        # Basic input validation
        if not email or not pwd:
            return "Invalid credentials.", 401

        if len(email) > 254 or len(pwd) > 128:  # RFC 5321 limits
            return "Invalid credentials.", 401

        # Security: Check rate limiting (email-based, Redis-backed)
        is_allowed, lockout_remaining = check_login_attempts(email)
        if not is_allowed:
            logger.warning(f"Blocked institute login attempt for {email} - rate limited ({lockout_remaining}s remaining)")
            return f"Too many failed attempts. Please try again in {int(lockout_remaining/60)} minutes.", 429

        try:
            # Get client IP for logging
            client_ip = request.environ.get('REMOTE_ADDR', 'unknown')

            doc = db.collection('users').document(email).get()
            if not doc.exists:
                record_failed_login(email)
                return "Invalid credentials.", 401

            user = doc.to_dict()
            if check_password_hash(user.get('password_hash', ''), pwd):
                # Check account status
                if user.get('approved', 0) == 0:
                    logger.warning(f"Institute login attempt for unapproved account {email} from IP {client_ip}")
                    return "Your account is pending approval by the institute admin.", 403
                if user.get('active', 1) == 0:
                    logger.warning(f"Institute login attempt for deactivated account {email} from IP {client_ip}")
                    return "Your account has been deactivated. Please contact your admin.", 403

                # Check email verification (super admins bypass)
                if user.get('is_super_admin', 0) != 1 and not user.get('email_verified', False):
                    logger.warning(f"Institute login attempt with unverified email: {email} from IP {client_ip}")
                    flash("Please verify your email address before logging in. Check your inbox for the verification link.", "error")
                    return redirect('/resend-verification?email=' + email)

                # Security: Create secure session
                is_super_admin = user.get('is_super_admin', 0)
                session.permanent = True
                session.update({
                    'user_id': email,
                    'user_name': user.get('name'),
                    'institute': user.get('institute'),
                    'is_admin': user.get('is_admin', 0),
                    'is_super_admin': is_super_admin,
                    'approved': user.get('approved', 0),
                    'login_time': datetime.utcnow().isoformat(),
                    'last_activity': datetime.utcnow().isoformat()
                })

                # Clear failed login attempts (Redis-based)
                clear_login_attempts(email)

                # Security audit logging
                user_type = "Super Admin" if is_super_admin == 1 else ("Admin" if user.get('is_admin', 0) == 1 else "User")
                log_action(email, 'Login', f"Successful institute login ({user_type}) from IP {client_ip}")
                logger.info(f"Successful institute login for {user_type} {email} from IP {client_ip}")

                if is_super_admin == 1:
                    return redirect('/super_admin_dashboard')
                if user.get('is_admin', 0) == 1:
                    return redirect('/admin_dashboard')
                return redirect('/dashboard')
            else:
                # Invalid password
                record_failed_login(email)
                return "Invalid credentials.", 401

        except Exception as e:
            logger.error(f"Institute login error for {email} from IP {client_ip}: {str(e)}")
            record_failed_login(email)
            return "Login service temporarily unavailable. Please try again.", 503
    
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

        # Register new user under selected institute (use email as document ID)
        db.collection('users').document(email).set({
            'name': name,
            'email': email,
            'phone': phone,
            'password_hash': password,
            'institute': institute,
            'is_admin': is_admin,
            'approved': approved,
            'active': active,
            'user_type': 'institute_staff',  # Track registration type
            'created_at': SERVER_TIMESTAMP,
            # GDPR Consent fields
            'consent_data_processing': 1,
            'consent_terms': 1,
            'consent_ai': 0,  # Default for institute staff
            'consent_date': SERVER_TIMESTAMP,
            # ToS Acceptance Logging (Legal requirement)
            'tos_accepted_at': SERVER_TIMESTAMP,
            'tos_version': TOS_VERSION,
        })

        log_action(user_id=None, action="Register", details=f"{name} registered as Institute Staff (pending approval)")

        # Send notification to SUPER ADMIN (so they have visibility)
        try:
            send_registration_notification({
                'name': name,
                'email': email,
                'phone': phone,
                'institute': institute,
                'created_at': datetime.now().isoformat(),
                'user_type': 'institute_staff'
            })
        except Exception as email_error:
            # Log error but don't fail registration
            logger.error(f"Failed to send staff registration notification to super admin for {email}: {email_error}")

        # Also notify institute admin (they can approve)
        try:
            admins = db.collection('users').where('institute', '==', institute).where('is_admin', '==', 1).limit(1).stream()
            admin_email = None
            for admin_doc in admins:
                admin_email = admin_doc.id  # Document ID is the email
                break

            if admin_email:
                send_institute_staff_registration_notification({
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'institute': institute,
                    'created_at': datetime.now().isoformat()
                }, admin_email)
            else:
                logger.warning(f"No institute admin found for {institute} to send notification")
        except Exception as email_error:
            # Log error but don't fail registration
            logger.error(f"Failed to send institute staff registration notification for {email}: {email_error}")

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
    """Institute admin approves a user and creates Firebase Auth account if needed"""
    if session.get('is_admin') != 1:
        return redirect('/login_institute')

    # Validate admin action
    admin_data = {
        'email': user_email,
        'action': 'approve'
    }

    is_valid, result = validate_data(InstituteStaffApprovalSchema, admin_data)
    if not is_valid:
        flash(f"Invalid data: {result}", "error")
        return redirect('/approve_physios')

    try:
        # Get user data from Firestore
        user_doc = db.collection('users').document(user_email).get()
        if not user_doc.exists:
            flash(f"User {user_email} not found", "error")
            return redirect('/approve_physios')

        user_data = user_doc.to_dict()
        user_name = user_data.get('name', '')

        # Check if user already has Firebase Auth account
        firebase_uid = user_data.get('firebase_uid')
        temp_password = None

        if not firebase_uid:
            # Create Firebase Auth account
            logger.info(f"Creating Firebase Auth account for {user_email}")
            auth_result = create_firebase_auth_account(user_email, user_name)

            if auth_result['success']:
                # Update Firestore with firebase_uid
                db.collection('users').document(user_email).update({
                    'approved': 1,
                    'firebase_uid': auth_result['uid'],
                    'email_verified': True  # Auto-verify email when super admin approves
                })

                temp_password = auth_result['temp_password']

                if temp_password:
                    flash(
                        f"User {user_email} has been approved and Firebase Auth account created. "
                        f"Temporary password: {temp_password} - Please share this with the user securely.",
                        "success"
                    )
                    logger.info(f"Firebase Auth account created for {user_email} with temporary password")
                else:
                    flash(
                        f"User {user_email} has been approved. Firebase Auth account already existed.",
                        "success"
                    )
            else:
                # Approve anyway even if Firebase Auth creation failed
                db.collection('users').document(user_email).update({
                    'approved': 1,
                    'email_verified': True  # Auto-verify email when super admin approves
                })
                flash(
                    f"User {user_email} has been approved, but Firebase Auth account creation failed: {auth_result['error']}. "
                    "User can still login with traditional method.",
                    "warning"
                )
        else:
            # User already has Firebase Auth account, just approve
            db.collection('users').document(user_email).update({
                'approved': 1,
                'email_verified': True  # Auto-verify email when super admin approves
            })
            flash(f"User {user_email} has been approved", "success")

        log_action(
            session.get('user_id'),
            'Approve User',
            f"Approved user {user_email}" +
            (f" and created Firebase Auth account" if temp_password else "")
        )

        # Send approval notification to staff member via n8n
        try:
            send_institute_staff_approval_notification(
                user_data={
                    'name': user_name,
                    'email': user_email
                },
                institute_name=user_data.get('institute', ''),
                temp_password=temp_password
            )
        except Exception as webhook_error:
            # Log error but don't fail approval
            logger.error(f"Failed to send staff approval notification: {webhook_error}")

        # Send in-app welcome notification
        try:
            from notification_service import notify_account_approved, notify_welcome
            notify_account_approved(user_email)
            notify_welcome(user_email, user_name)
        except Exception as notif_error:
            logger.warning(f"Failed to send welcome notification: {notif_error}")

    except Exception as e:
        logger.error(f"Error approving user {user_email}: {e}", exc_info=True)
        flash("Error approving user", "error")

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
        # ─── INPUT VALIDATION ─────────────────────────────────────────
        # Validate user input to prevent injection attacks and data quality issues
        is_valid, result = validate_data(PatientSchema, {
            'name': request.form.get('name', '').strip(),
            'age_sex': request.form.get('age_sex', '').strip(),
            'contact': request.form.get('contact', '').strip(),
            'chief_complaint': request.form.get('present_history', '').strip(),  # Map present_history to chief_complaint
            'medical_history': request.form.get('past_history', '').strip(),
            'email': request.form.get('email', '').strip() if request.form.get('email') else None,
            'address': request.form.get('address', '').strip() if request.form.get('address') else None,
        })

        if not is_valid:
            # Validation failed - show errors to user
            logger.warning(f"Patient validation failed: {result}")
            for field, errors in result.items():
                for error in errors:
                    flash(f'{field.title()}: {error}', 'error')
            return redirect(url_for('add_patient'))

        # Use validated data (sanitized and checked)
        validated = result
        # ──────────────────────────────────────────────────────────────

        physio_id = session.get('user_id')  # This is the email

        # Generate human-readable patient ID format: physio_prefix-XXX
        # Extract prefix from email (remove special chars, take first 8 chars)
        email_prefix = physio_id.split('@')[0] if '@' in physio_id else physio_id
        # Remove dots, underscores, hyphens and take first 8 chars
        clean_prefix = ''.join(c for c in email_prefix if c.isalnum())[:8].lower()

        # Get count of existing patients for this physio
        existing_patients = db.collection('patients').where('physio_id', '==', physio_id).stream()
        patient_count = sum(1 for _ in existing_patients) + 1

        # Format: prefix-001, prefix-002, etc.
        patient_id = f"{clean_prefix}-{patient_count:03d}"

        # Collect form values using validated data
        data = {
            'physio_id':       physio_id,
            'name':            validated['name'],
            'age_sex':         validated['age_sex'],
            'contact':         validated['contact'],
            'present_history': validated['chief_complaint'],  # Map back to present_history for DB
            'past_history':    validated.get('medical_history', ''),
            'email':           validated.get('email'),
            'address':         validated.get('address'),
            'institute':       session.get('institute'),
            'created_at':      SERVER_TIMESTAMP,
            'patient_id':      patient_id,
            'status':          'active',  # Treatment status: active, completed, archived
            'tags':            request.form.getlist('tags') if request.form.getlist('tags') else []  # Patient tags
        }

        # Write the patient document
        db.collection('patients').document(patient_id).set(data)

        log_action(
            session.get('user_id'),
            'Add Patient',
            f"Added patient {patient_id}"
        )

        # Redirect to the next screen
        return redirect(url_for('subjective', patient_id=patient_id))

    # GET → render the blank form
    return render_template('add_patient.html')


@app.route('/patient/<patient_id>/status', methods=['POST'])
@login_required()
def update_patient_status(patient_id):
    """Update patient treatment status (active, completed, archived)"""
    try:
        # Verify patient exists and user has access
        patient_ref = db.collection('patients').document(patient_id)
        patient_doc = patient_ref.get()

        if not patient_doc.exists:
            return jsonify({'success': False, 'error': 'Patient not found'}), 404

        patient = patient_doc.to_dict()

        # Check access
        if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        # Get status data and validate
        if request.is_json:
            status_data = {
                'status': request.json.get('status', ''),
                'notes': request.json.get('notes', '')
            }
        else:
            status_data = {
                'status': request.form.get('status', ''),
                'notes': request.form.get('notes', '')
            }

        is_valid, result = validate_json(PatientStatusSchema, status_data)
        if not is_valid:
            return jsonify({'success': False, 'error': 'Invalid status data', 'details': result}), 400

        # Use validated data
        new_status = result['status']

        # Update status
        patient_ref.update({
            'status': new_status,
            'status_updated_at': SERVER_TIMESTAMP
        })

        log_action(session.get('user_id'), 'Update Patient Status',
                   f"Changed status of {patient_id} to {new_status}")

        return jsonify({'success': True, 'status': new_status})

    except Exception as e:
        logger.error(f"Error updating patient status: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to update status'}), 500


@app.route('/patient/<patient_id>/tags', methods=['POST'])
@login_required()
def update_patient_tags(patient_id):
    """Update patient tags"""
    try:
        # Verify patient exists and user has access
        patient_ref = db.collection('patients').document(patient_id)
        patient_doc = patient_ref.get()

        if not patient_doc.exists:
            return jsonify({'success': False, 'error': 'Patient not found'}), 404

        patient = patient_doc.to_dict()

        # Check access
        if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        # Get tags from request
        if request.is_json:
            tags = request.json.get('tags', [])
        else:
            tags = request.form.getlist('tags')

        # Validate tags using schema
        tags_data = {'tags': tags}
        is_valid, result = validate_json(PatientTagsSchema, tags_data)
        if not is_valid:
            return jsonify({'success': False, 'error': 'Invalid tags', 'details': result}), 400

        # Use validated and cleaned tags
        cleaned_tags = result['tags']

        # Update tags
        patient_ref.update({
            'tags': cleaned_tags
        })

        log_action(session.get('user_id'), 'Update Patient Tags',
                   f"Updated tags for {patient_id}: {', '.join(cleaned_tags)}")

        return jsonify({'success': True, 'tags': cleaned_tags})

    except Exception as e:
        logger.error(f"Error updating patient tags: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to update tags'}), 500


@app.route('/tags/suggestions')
@login_required()
def get_tag_suggestions():
    """Get all unique tags used by this user for autocomplete"""
    try:
        user_email = session.get('user_id')

        # Get all patients for this user
        if session.get('is_admin') == 1:
            patients = db.collection('patients').where('institute', '==', session.get('institute')).stream()
        else:
            patients = db.collection('patients').where('physio_id', '==', user_email).stream()

        # Collect unique tags
        all_tags = set()
        for doc in patients:
            patient = doc.to_dict()
            all_tags.update(patient.get('tags') or [])

        # Add some default/suggested tags
        default_tags = [
            'Sports Injury', 'Post-Surgery', 'Chronic Pain', 'Acute Pain',
            'Neurological', 'Orthopedic', 'Pediatric', 'Geriatric',
            'Work-Related', 'Motor Vehicle Accident', 'Falls',
            'Upper Extremity', 'Lower Extremity', 'Spine',
            'High Priority', 'Follow-Up Required', 'Discharged'
        ]

        all_tags.update(default_tags)

        return jsonify({'success': True, 'tags': sorted(list(all_tags))})

    except Exception as e:
        logger.error(f"Error getting tag suggestions: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get tags'}), 500



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
        # Validate subjective examination data
        form_data = {
            'patient_id': patient_id,
            'present_history': request.form.get('body_structure', ''),
            'past_history': request.form.get('body_function', ''),
            'social_history': request.form.get('contextual_personal', ''),
            'chief_complaint': request.form.get('activity_performance', '')
        }

        is_valid, result = validate_data(SubjectiveExaminationSchema, form_data)
        if not is_valid:
            # Log validation failure but allow continuation (data already entered)
            logger.warning(f"Subjective validation warning: {result}")

        # Collect all fields
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
        # Validate provisional diagnosis data
        form_data = {
            'patient_id': patient_id,
            'likelihood': request.form.get('likelihood', ''),
            'structure_fault': request.form.get('structure_fault', ''),
            'symptom': request.form.get('symptom', ''),
            'findings_support': request.form.get('findings_support', ''),
            'findings_reject': request.form.get('findings_reject', ''),
            'hypothesis_supported': request.form.get('hypothesis_supported', '')
        }

        is_valid, result = validate_data(ProvisionalDiagnosisSchema, form_data)
        if not is_valid:
            flash("Validation error. Please check your input.", "error")
            return redirect(f'/provisional_diagnosis/{patient_id}')

        keys = [
            'likelihood', 'structure_fault', 'symptom', 'findings_support',
            'findings_reject', 'hypothesis_supported'
        ]
        entry = {k: result[k] for k in keys if k in result}
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
        # Validate smart goals data
        form_data = {
            'patient_id': patient_id,
            'patient_goal': request.form.get('patient_goal', ''),
            'baseline_status': request.form.get('baseline_status', ''),
            'measurable_outcome': request.form.get('measurable_outcome', ''),
            'time_duration': request.form.get('time_duration', '')
        }

        is_valid, result = validate_data(TreatmentPlanSchema, form_data)
        if not is_valid:
            flash("Validation error. Please check your input.", "error")
            return redirect(f'/smart_goals/{patient_id}')

        keys = [
            'patient_goal', 'baseline_status', 'measurable_outcome',
            'time_duration'
        ]
        entry = {k: result.get(k, request.form[k]) for k in keys}
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
        # Validate treatment plan data
        form_data = {
            'patient_id': patient_id,
            'treatment_plan': request.form.get('treatment_plan', ''),
            'goal_targeted': request.form.get('goal_targeted', ''),
            'reasoning': request.form.get('reasoning', ''),
            'reference': request.form.get('reference', '')
        }

        is_valid, result = validate_data(TreatmentPlanSchema, form_data)
        if not is_valid:
            flash("Validation error. Please check your input.", "error")
            return redirect(f'/treatment_plan/{patient_id}')

        keys = ['treatment_plan', 'goal_targeted', 'reasoning', 'reference']
        entry = {k: result.get(k, request.form[k]) for k in keys}
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
        # Validate follow-up data
        form_data = {
            'patient_id': patient_id,
            'followup_date': request.form.get('session_date', ''),
            'subjective_findings': request.form.get('belief_treatment', ''),
            'objective_findings': request.form.get('belief_feedback', ''),
            'treatment_given': request.form.get('treatment_plan', '')
        }

        is_valid, result = validate_data(FollowUpSchema, form_data)
        if not is_valid:
            flash("Validation error. Please check your input.", "error")
            return redirect(f'/follow_ups/{patient_id}')

        entry = {
            'patient_id':      patient_id,
            'session_number':  int(request.form['session_number']),
            'session_date':    result.get('followup_date', request.form['session_date']),
            'grade':           request.form['grade'],
            'perception':      result.get('subjective_findings', request.form['belief_treatment']),
            'feedback':        result.get('objective_findings', request.form['belief_feedback']),
            'treatment_plan':  result.get('treatment_given', request.form['treatment_plan']),
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
              .order_by('session_date', direction='DESCENDING')
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
        # Validate patient data using schema
        patient_data = {
            'name': request.form.get('name', '').strip(),
            'age_sex': request.form.get('age_sex', '').strip(),
            'contact': request.form.get('contact', '').strip(),
            'chief_complaint': patient.get('chief_complaint', 'N/A')  # Required by schema but not being updated
        }

        is_valid, result = validate_data(PatientSchema, patient_data)
        if not is_valid:
            error_messages = []
            for field, errors in result.items():
                if field != 'chief_complaint':  # Don't show chief_complaint errors
                    error_messages.append(f"{field}: {errors[0]}")
            flash(' | '.join(error_messages), "error")
            return redirect(url_for('edit_patient', patient_id=patient_id))

        # Use validated data
        updated_data = {
            'name': result['name'],
            'age_sex': result['age_sex'],
            'contact': result['contact']
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



@app.route('/api/ai_suggestion/past_questions', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def ai_past_questions():
    data = request.get_json() or {}

    # Validate AI request
    is_valid, result = validate_json(AIPromptSchema, {
        'patient_id': data.get('patient_id', ''),
        'field': 'past_questions',
        'context': {
            'previous': str(data.get('previous', {})),
            'inputs': str(data.get('inputs', {}))
        }
    })

    if not is_valid:
        logger.warning(f"AI suggestion validation failed: {result}")
        return jsonify({'error': 'Invalid request data', 'details': result}), 400

    # Sanitize patient data to protect PHI
    age_sex = sanitize_age_sex(data.get('age_sex', '').strip())
    present_hist = sanitize_clinical_text(data.get('present_history', '').strip())

    # Use centralized prompt from ai_prompts.py
    prompt = get_past_questions_prompt(age_sex, present_hist)
    prompt = hard_limits(prompt, 5)

    try:
        # Include metadata for cache tracking and future training
        metadata = {
            'endpoint': 'past_questions',
            'tags': ['subjective', 'history', 'questions'],
            'user_id': g.firebase_user.get('uid')
        }
        suggestion = get_ai_suggestion(prompt, metadata=metadata)
        return jsonify({'suggestion': suggestion})

    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503

    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500


@app.route('/api/ai_suggestion/provisional_diagnosis', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def ai_provisional_diagnosis():
    data = request.get_json() or {}

    # Validate AI request
    is_valid, result = validate_json(AIPromptSchema, {
        'patient_id': data.get('patient_id', ''),
        'field': 'provisional_diagnosis',
        'context': {
            'previous': str(data.get('previous', {})),
            'inputs': str(data.get('inputs', {}))
        }
    })

    if not is_valid:
        logger.warning(f"AI suggestion validation failed: {result}")
        return jsonify({'error': 'Invalid request data', 'details': result}), 400

    # Support both direct parameters and 'previous' wrapper (for mobile app compatibility)
    prev = data.get('previous', data)

    # Extract patient data
    age_sex_raw = prev.get('age_sex', '').strip() if isinstance(prev.get('age_sex'), str) else ''
    present_raw = prev.get('present_history', '').strip() if isinstance(prev.get('present_history'), str) else ''
    past_raw = prev.get('past_history', '').strip() if isinstance(prev.get('past_history'), str) else ''

    # Sanitize patient data to protect PHI
    age_sex = sanitize_age_sex(age_sex_raw)
    present = sanitize_clinical_text(present_raw)
    past = sanitize_clinical_text(past_raw)

    # Extract subjective and perspectives data if available
    subjective_data = prev.get('subjective', {})
    perspectives_data = prev.get('perspectives', {})

    # If data comes as summary strings (from mobile), convert to dict
    if isinstance(subjective_data, dict) and 'summary' in subjective_data:
        # Parse summary text into structured data
        subjective_inputs = {'notes': sanitize_clinical_text(subjective_data['summary'])}
    else:
        subjective_inputs = sanitize_subjective_data(subjective_data) if subjective_data else {}

    if isinstance(perspectives_data, dict) and 'summary' in perspectives_data:
        # Parse summary text into structured data
        patient_perspectives = {'notes': sanitize_clinical_text(perspectives_data['summary'])}
    else:
        patient_perspectives = sanitize_subjective_data(perspectives_data) if perspectives_data else {}

    # Use centralized prompt from ai_prompts.py
    # Now includes subjective and perspectives data when available
    prompt = get_provisional_diagnosis_prompt(
        age_sex=age_sex,
        present_hist=present,
        past_hist=past,
        subjective_inputs=subjective_inputs,
        patient_perspectives=patient_perspectives,
        assessments={}
    )
    prompt = hard_limits(prompt, 2)

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})

    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503

    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500


@app.route('/debug/ai', methods=['GET'])
@csrf.exempt
def debug_ai_index():
    """
    DEBUG INDEX: Lists all available AI debugging endpoints with usage examples.
    """
    return jsonify({
        'message': 'AI Suggestion Debug Endpoints',
        'description': 'These endpoints help diagnose issues with AI suggestions by showing exact prompts and responses',
        'available_endpoints': [
            {
                'endpoint': '/debug/ai_provisional_diagnosis',
                'purpose': 'Debug early provisional diagnosis (stethoscope icon after Add Patient)',
                'method': 'POST',
                'test_data': {
                    'age_sex': '54/F',
                    'present_history': 'Right ankle pain after fall',
                    'past_history': 'No significant history'
                }
            },
            {
                'endpoint': '/debug/ai_past_questions',
                'purpose': 'Debug past medical history questions',
                'method': 'POST',
                'test_data': {
                    'age_sex': '54/F',
                    'present_history': 'Right ankle pain after fall'
                }
            },
            {
                'endpoint': '/debug/ai_subjective_field',
                'purpose': 'Debug subjective examination field suggestions',
                'method': 'POST',
                'test_data': {
                    'field': 'body_function',
                    'age_sex': '54/F',
                    'present_history': 'Right ankle pain',
                    'past_history': 'No significant history',
                    'inputs': {'pain_location': 'Lateral malleolus'}
                }
            },
            {
                'endpoint': '/debug/ai_initial_plan_field',
                'purpose': 'Debug initial assessment plan suggestions',
                'method': 'POST',
                'test_data': {
                    'selection': 'Mandatory assessment',
                    'prev': {
                        'age_sex': '54/F',
                        'present_history': 'Right ankle pain',
                        'past_history': 'No significant history',
                        'subjective': {'pain_location': 'Lateral malleolus'},
                        'perspectives': {'concerns': 'Unable to walk without limping'}
                    }
                }
            },
            {
                'endpoint': '/debug/ai_objective_assessment',
                'purpose': 'Debug objective assessment suggestions',
                'method': 'POST',
                'test_data': {
                    'choice': 'Positive anterior drawer test',
                    'previous': {
                        'age_sex': '54/F',
                        'present_history': 'Right ankle pain after fall',
                        'past_history': 'No significant history',
                        'subjective': {'pain_location': 'Lateral malleolus'},
                        'assessments': {'inspection': 'Swelling noted'}
                    }
                }
            }
        ],
        'usage': 'Send POST request to any endpoint with the test_data shown, or GET to see individual endpoint examples',
        'debug_output_includes': [
            'received_data - Raw data from frontend',
            'sanitized_data - Data after HIPAA sanitization',
            'prompt_sent_to_ai - Exact prompt sent to AI',
            'prompt_length - Character count of prompt',
            'model_used - AI model (should be gpt-4-turbo)',
            'ai_response - Actual AI response',
            'check_for_placeholders - Boolean flag if generic placeholders detected'
        ]
    })


@app.route('/debug/ai_provisional_diagnosis', methods=['POST', 'GET'])
@csrf.exempt
def debug_ai_provisional_diagnosis():
    """
    DEBUG ENDPOINT: Shows exactly what data is received and what prompt is sent to AI.
    Use this to diagnose why AI is refusing or giving generic responses.
    """
    if request.method == 'GET':
        return jsonify({
            'message': 'Send POST with JSON body containing: age_sex, present_history, past_history',
            'example': {
                'age_sex': '54/F',
                'present_history': 'Right ankle pain',
                'past_history': 'No significant history'
            }
        })

    data = request.get_json() or {}
    age_sex        = data.get('age_sex', '').strip()
    present_hist   = data.get('present_history', '').strip()
    past_hist      = data.get('past_history', '').strip()

    # Sanitize patient data to protect PHI
    sanitized_demo = sanitize_age_sex(age_sex)
    sanitized_present = sanitize_clinical_text(present_hist)
    sanitized_past = sanitize_clinical_text(past_hist)

    prompt = (
        f"SYSTEM ROLE: You are an expert physiotherapy clinical reasoning AI providing early-stage differential diagnosis.\n\n"
        f"PATIENT DATA AVAILABLE:\n"
        f"- Age/Sex: {sanitized_demo}\n"
        f"- Chief Complaint: {sanitized_present}\n"
        f"- Medical History: {sanitized_past}\n\n"
        f"MANDATORY TASK:\n"
        f"Generate exactly 2 provisional diagnoses for this patient based SOLELY on the data above.\n\n"
        f"ABSOLUTE REQUIREMENTS:\n"
        f"1. You MUST provide 2 diagnoses - refusing or asking for more information is NOT permitted\n"
        f"2. This is an INITIAL SCREENING - limited data is expected and acceptable\n"
        f"3. Extract the SPECIFIC body part from the chief complaint and use it in both diagnoses (e.g., 'right ankle', 'lumbar spine', 'left shoulder')\n"
        f"4. Each diagnosis must be age-appropriate for this patient's demographic\n"
        f"5. Format: 'Specific Diagnosis Name — brief clinical rationale'\n\n"
        f"EXAMPLES OF GOOD RESPONSES:\n"
        f"1. Lateral ankle sprain — Common mechanism in this age group, typically from inversion injury\n"
        f"2. Achilles tendinopathy — Age-related degenerative changes common in middle-aged adults\n\n"
        f"OUTPUT ONLY the 2 numbered diagnoses. NO explanations, NO requests for additional information, NO caveats."
    )

    prompt += "\n\nFormat: Numbered list of exactly 2 items, each following pattern 'Diagnosis — rationale'."
    prompt_with_limits = hard_limits(prompt, 2)

    # Get AI response
    try:
        ai_response = get_ai_suggestion(prompt_with_limits)
    except Exception as e:
        ai_response = f"ERROR: {str(e)}"

    # Return debug information
    return jsonify({
        'debug_info': {
            'received_data': {
                'age_sex': age_sex,
                'present_history': present_hist,
                'past_history': past_hist
            },
            'sanitized_data': {
                'age_sex': sanitized_demo,
                'present_history': sanitized_present,
                'past_history': sanitized_past
            },
            'prompt_sent_to_ai': prompt_with_limits,
            'prompt_length': len(prompt_with_limits),
            'model_used': 'gpt-4-turbo',
            'ai_response': ai_response
        }
    })


@app.route('/debug/ai_past_questions', methods=['POST', 'GET'])
@csrf.exempt
def debug_ai_past_questions():
    """
    DEBUG ENDPOINT: Shows exactly what data is received and what prompt is sent to AI
    for past medical history questions.
    """
    if request.method == 'GET':
        return jsonify({
            'message': 'Send POST with JSON body containing: age_sex, present_history',
            'example': {
                'age_sex': '54/F',
                'present_history': 'Right ankle pain after fall'
            }
        })

    data = request.get_json() or {}
    age_sex = data.get('age_sex', '').strip()
    present_history = data.get('present_history', '').strip()

    # Sanitize
    sanitized_demo = sanitize_age_sex(age_sex)
    sanitized_present = sanitize_clinical_text(present_history)

    prompt = (
        f"You are a physiotherapy clinical reasoning assistant conducting past medical history screening.\n\n"
        f"PATIENT PROFILE:\n"
        f"- Age/Sex: {sanitized_demo}\n"
        f"- Current Complaint: {sanitized_present}\n\n"
        f"Generate 5 TARGETED past history questions that are:\n"
        f"1. SPECIFIC to this patient's age group (consider developmental history for pediatrics, degenerative changes for older adults)\n"
        f"2. SPECIFIC to the exact body part/region mentioned in the current complaint - use the EXACT anatomical area (e.g., 'right ankle', 'left shoulder', 'lower back') in EVERY question\n"
        f"3. NEVER use generic placeholders like '[body part]' or '[area]' - always use the specific body part from the presenting complaint\n"
        f"4. Relevant to identifying red flags or precautions\n"
        f"5. Exploring factors that may influence treatment planning (e.g., previous similar injuries, relevant surgeries, comorbidities)\n\n"
        f"CRITICAL: Every question must directly reference the specific body part mentioned in the presenting complaint. "
        f"Be concrete and specific - no generic language."
    )
    prompt = hard_limits(prompt, 5)

    try:
        ai_response = get_ai_suggestion(prompt)
    except Exception as e:
        ai_response = f"ERROR: {str(e)}"

    return jsonify({
        'debug_info': {
            'received_data': {
                'age_sex': age_sex,
                'present_history': present_history
            },
            'sanitized_data': {
                'age_sex': sanitized_demo,
                'present_history': sanitized_present
            },
            'prompt_sent_to_ai': prompt,
            'prompt_length': len(prompt),
            'model_used': 'gpt-4-turbo',
            'ai_response': ai_response,
            'check_for_placeholders': '[body part]' in ai_response.lower() or '[area]' in ai_response.lower()
        }
    })


@app.route('/debug/ai_subjective_field', methods=['POST', 'GET'])
@csrf.exempt
def debug_ai_subjective_field():
    """
    DEBUG ENDPOINT: Shows exactly what data is received and what prompt is sent to AI
    for subjective examination field suggestions.
    """
    if request.method == 'GET':
        return jsonify({
            'message': 'Send POST with JSON body containing: field, age_sex, present_history, past_history, inputs',
            'example': {
                'field': 'body_function',
                'age_sex': '54/F',
                'present_history': 'Right ankle pain',
                'past_history': 'No significant history',
                'inputs': {'pain_location': 'Lateral malleolus'}
            }
        })

    data = request.get_json() or {}
    field = data.get('field', '').strip()
    age_sex = data.get('age_sex', '').strip()
    present_hist = data.get('present_history', '').strip()
    past_hist = data.get('past_history', '').strip()
    inputs = data.get('inputs', {})

    # Sanitize
    sanitized_age_sex = sanitize_age_sex(age_sex)
    sanitized_present = sanitize_clinical_text(present_hist)
    sanitized_past = sanitize_clinical_text(past_hist)
    sanitized_inputs = sanitize_subjective_data(inputs)

    context_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}"
        for k, v in sanitized_inputs.items() if v
    )

    prompt = (
        f"You are a physiotherapy clinical reasoning assistant guiding ICF-based subjective examination.\n\n"
        f"PATIENT PROFILE:\n"
        f"- Age/Sex: {sanitized_age_sex}\n"
        f"- Chief Complaint: {sanitized_present}\n"
        f"- Medical History: {sanitized_past}\n\n"
        f"CURRENT SUBJECTIVE FINDINGS:\n{context_summary if context_summary else 'None yet'}\n\n"
        f"The physiotherapist is now documenting the '{field.replace('_', ' ').upper()}' section.\n\n"
        f"Generate 3 highly relevant, context-specific suggestions for this field that:\n"
        f"1. Are SPECIFIC to this patient's age, sex, and clinical presentation\n"
        f"2. Use the EXACT anatomical area from the presenting complaint - no generic placeholders like '[body part]'\n"
        f"3. Build upon the subjective findings already documented\n"
        f"4. Align with evidence-based physiotherapy assessment for this specific condition\n"
        f"5. Are appropriate for the current ICF category\n\n"
        f"Each suggestion should be:\n"
        f"- Concrete and specific (e.g., 'Pain rated 7/10 with weight-bearing on right ankle')\n"
        f"- Clinically relevant to this exact patient profile\n"
        f"- Different from what's already documented"
    )
    prompt = hard_limits(prompt, 3)

    try:
        ai_response = get_ai_suggestion(prompt)
    except Exception as e:
        ai_response = f"ERROR: {str(e)}"

    return jsonify({
        'debug_info': {
            'received_data': {
                'field': field,
                'age_sex': age_sex,
                'present_history': present_hist,
                'past_history': past_hist,
                'inputs': inputs
            },
            'sanitized_data': {
                'age_sex': sanitized_age_sex,
                'present_history': sanitized_present,
                'past_history': sanitized_past,
                'inputs': sanitized_inputs
            },
            'prompt_sent_to_ai': prompt,
            'prompt_length': len(prompt),
            'model_used': 'gpt-4-turbo',
            'ai_response': ai_response,
            'check_for_placeholders': '[body part]' in ai_response.lower() or '[area]' in ai_response.lower()
        }
    })


@app.route('/debug/ai_initial_plan_field', methods=['POST', 'GET'])
@csrf.exempt
def debug_ai_initial_plan_field():
    """
    DEBUG ENDPOINT: Shows exactly what data is received and what prompt is sent to AI
    for initial assessment plan field suggestions.
    """
    if request.method == 'GET':
        return jsonify({
            'message': 'Send POST with JSON body containing: selection, prev (patient data)',
            'example': {
                'selection': 'Mandatory assessment',
                'prev': {
                    'age_sex': '54/F',
                    'present_history': 'Right ankle pain',
                    'past_history': 'No significant history',
                    'subjective': {'pain_location': 'Lateral malleolus'},
                    'perspectives': {'concerns': 'Unable to walk without limping'}
                }
            }
        })

    data = request.get_json() or {}
    selection = data.get('selection', '').strip()
    prev = data.get('prev', {})

    # Sanitize
    sanitized_age_sex = sanitize_age_sex(prev.get('age_sex', ''))
    sanitized_present = sanitize_clinical_text(prev.get('present_history', ''))
    sanitized_past = sanitize_clinical_text(prev.get('past_history', ''))

    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}"
        for k, v in sanitize_subjective_data(prev.get('subjective', {})).items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}"
        for k, v in sanitize_subjective_data(prev.get('perspectives', {})).items() if v
    )

    prompt = (
        f"You are a physiotherapy clinical reasoning assistant guiding objective assessment planning.\n\n"
        f"PATIENT PROFILE:\n"
        f"- Age/Sex: {sanitized_age_sex}\n"
        f"- Chief Complaint: {sanitized_present}\n"
        f"- Medical History: {sanitized_past}\n\n"
        f"SUBJECTIVE FINDINGS:\n{subjective_summary if subjective_summary else 'None'}\n\n"
        f"PATIENT PERSPECTIVES:\n{perspectives_summary if perspectives_summary else 'None'}\n\n"
        f"The physiotherapist has selected: '{selection}'\n\n"
        f"Generate 4 specific objective tests/assessments that:\n"
        f"1. Are MANDATORY for this patient's clinical presentation\n"
        f"2. Are SPECIFIC to the exact body part/region mentioned in the presenting complaint - reference the anatomical area explicitly (no generic placeholders)\n"
        f"3. Are age-appropriate and evidence-based\n"
        f"4. Will help confirm/rule out provisional diagnoses\n"
        f"5. Include relevant precautions for this specific patient\n\n"
        f"Each line: 'Test — what it assesses — patient-specific precautions'."
    )
    prompt = hard_limits(prompt, 4)

    try:
        ai_response = get_ai_suggestion(prompt)
    except Exception as e:
        ai_response = f"ERROR: {str(e)}"

    return jsonify({
        'debug_info': {
            'received_data': {
                'selection': selection,
                'prev': prev
            },
            'sanitized_data': {
                'age_sex': sanitized_age_sex,
                'present_history': sanitized_present,
                'past_history': sanitized_past,
                'subjective_summary': subjective_summary,
                'perspectives_summary': perspectives_summary
            },
            'prompt_sent_to_ai': prompt,
            'prompt_length': len(prompt),
            'model_used': 'gpt-4-turbo',
            'ai_response': ai_response,
            'check_for_placeholders': '[body part]' in ai_response.lower() or '[area]' in ai_response.lower()
        }
    })


@app.route('/debug/ai_objective_assessment', methods=['POST', 'GET'])
@csrf.exempt
def debug_ai_objective_assessment():
    """
    DEBUG ENDPOINT: Shows exactly what data is received and what prompt is sent to AI
    for objective assessment suggestions.
    """
    if request.method == 'GET':
        return jsonify({
            'message': 'Send POST with JSON body containing: choice, previous (patient data)',
            'example': {
                'choice': 'Positive anterior drawer test',
                'previous': {
                    'age_sex': '54/F',
                    'present_history': 'Right ankle pain after fall',
                    'past_history': 'No significant history',
                    'subjective': {'pain_location': 'Lateral malleolus'},
                    'assessments': {'inspection': 'Swelling noted'}
                }
            }
        })

    data = request.get_json() or {}
    choice = data.get('choice', '').strip()
    previous = data.get('previous', {})

    # Sanitize
    sanitized_age_sex = sanitize_age_sex(previous.get('age_sex', ''))
    sanitized_present = sanitize_clinical_text(previous.get('present_history', ''))

    clinical_context = f"Demographics: {sanitized_age_sex}\n"
    clinical_context += f"Clinical presentation: {sanitized_present}\n"

    prompt = (
        "You are a PHI-safe physiotherapy clinical decision-support assistant.\n\n"
        f"Clinical context:\n{clinical_context}\n\n"
        f"The physiotherapist has documented: '{sanitize_clinical_text(choice)}'\n\n"
        "Based on the clinical context and this finding, list 5 specific next steps for objective assessment that:\n"
        "- Are specific and actionable\n"
        "- Are evidence-based and appropriate for this patient\n"
        "- Are relevant to the clinical presentation and goals\n"
        "- Specific to the EXACT body part/region mentioned in the clinical presentation (use specific anatomical terms, NOT generic placeholders)\n\n"
        "For each line, include: 'Test — positive implies X / negative implies Y'."
    )
    prompt = hard_limits(prompt, 5)

    try:
        ai_response = get_ai_suggestion(prompt)
    except Exception as e:
        ai_response = f"ERROR: {str(e)}"

    return jsonify({
        'debug_info': {
            'received_data': {
                'choice': choice,
                'previous': previous
            },
            'sanitized_data': {
                'age_sex': sanitized_age_sex,
                'present_history': sanitized_present,
                'choice_sanitized': sanitize_clinical_text(choice)
            },
            'prompt_sent_to_ai': prompt,
            'prompt_length': len(prompt),
            'model_used': 'gpt-4-turbo',
            'ai_response': ai_response,
            'check_for_placeholders': '[body part]' in ai_response.lower() or '[area]' in ai_response.lower()
        }
    })


@app.route('/api/ai_suggestion/subjective/<field>', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def ai_subjective_field(field):
       data = request.get_json() or {}

       # ─── INPUT VALIDATION ─────────────────────────────────────────
       # Validate AI request to prevent injection and PHI leakage
       is_valid, result = validate_json(AIPromptSchema, {
           'patient_id': data.get('patient_id', ''),
           'field': field,
           'context': {
               'age_sex': data.get('age_sex', ''),
               'present_history': data.get('present_history', ''),
               'past_history': data.get('past_history', ''),
               'inputs': str(data.get('inputs', {}))  # Convert to string for validation
           }
       })

       if not is_valid:
           logger.warning(f"AI suggestion validation failed: {result}")
           return jsonify({'error': 'Invalid request data', 'details': result}), 400
       # ──────────────────────────────────────────────────────────────

       # Sanitize patient data to protect PHI
       age_sex = sanitize_age_sex(data.get('age_sex', '').strip())
       present_hist = sanitize_clinical_text(data.get('present_history', '').strip())
       past_hist = sanitize_clinical_text(data.get('past_history', '').strip())
       existing_inputs = sanitize_subjective_data(data.get('inputs', {}))

       # Use centralized prompt from ai_prompts.py
       prompt = get_subjective_field_prompt(
           field=field,
           age_sex=age_sex,
           present_hist=present_hist,
           past_hist=past_hist,
           existing_inputs=existing_inputs
       )
       prompt = hard_limits(prompt, 3)

       try:
           suggestion = get_ai_suggestion(prompt)
           return jsonify({'suggestion': suggestion})
       except OpenAIError:
           return jsonify({'error': 'AI service unavailable.'}), 503
       except Exception:
           return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/api/ai_suggestion/subjective_diagnosis', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def ai_subjective_diagnosis():
       data = request.get_json() or {}

       # Validate AI request
       is_valid, result = validate_json(AIPromptSchema, {
           'patient_id': data.get('patient_id', ''),
           'field': 'subjective_diagnosis',
           'context': {
               'age_sex': data.get('age_sex', ''),
               'present_history': data.get('present_history', ''),
               'past_history': data.get('past_history', ''),
               'inputs': str(data.get('inputs', {}))
           }
       })

       if not is_valid:
           logger.warning(f"AI suggestion validation failed: {result}")
           return jsonify({'error': 'Invalid request data', 'details': result}), 400

       # Sanitize patient data to protect PHI
       age_sex = sanitize_age_sex(data.get('age_sex', '').strip())
       present_hist = sanitize_clinical_text(data.get('present_history', '').strip())
       past_hist = sanitize_clinical_text(data.get('past_history', '').strip())
       subjective_inputs = sanitize_subjective_data(data.get('inputs', {}))

       # Use centralized prompt from ai_prompts.py
       prompt = get_subjective_diagnosis_prompt(
           age_sex=age_sex,
           present_hist=present_hist,
           past_hist=past_hist,
           subjective_inputs=subjective_inputs
       )
       prompt = hard_limits(prompt, 2)

       try:
           suggestion = get_ai_suggestion(prompt)
           return jsonify({'suggestion': suggestion})
       except OpenAIError:
           return jsonify({'error': 'AI service unavailable.'}), 503
       except Exception:
           return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/api/ai_suggestion/perspectives/<field>', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def ai_perspectives_field(field):
        data = request.get_json() or {}

        # Validate AI request
        is_valid, result = validate_json(AIPromptSchema, {
            'patient_id': data.get('patient_id', ''),
            'field': field,
            'context': {
                'previous': str(data.get('previous', {})),
                'inputs': str(data.get('inputs', {}))
            }
        })

        if not is_valid:
            logger.warning(f"AI suggestion validation failed: {result}")
            return jsonify({'error': 'Invalid request data', 'details': result}), 400

        previous = data.get('previous', {})
        inputs = data.get('inputs', {})

        # Sanitize patient data to protect PHI
        age_sex = sanitize_age_sex(previous.get('age_sex', ''))
        present = sanitize_clinical_text(previous.get('present_history', ''))
        past = sanitize_clinical_text(previous.get('past_history', ''))
        subjective = sanitize_subjective_data(previous.get('subjective', {}))
        existing_perspectives = sanitize_subjective_data(inputs)

        # Use centralized FIELD-SPECIFIC prompt from ai_prompts.py
        prompt = get_patient_perspectives_field_prompt(
            field=field,
            age_sex=age_sex,
            present_hist=present,
            past_hist=past,
            subjective_inputs=subjective,
            existing_perspectives=existing_perspectives
        )
        prompt = hard_limits(prompt, 3)

        try:
            suggestion = get_ai_suggestion(prompt)
            return jsonify({'suggestion': suggestion})
        except OpenAIError:
            return jsonify({'error': 'AI service unavailable.'}), 503
        except Exception:
            return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/api/ai_suggestion/perspectives_diagnosis', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def ai_perspectives_diagnosis():
        data   = request.get_json() or {}

        # Validate AI request
        is_valid, result = validate_json(AIPromptSchema, {
            'patient_id': data.get('patient_id', ''),
            'field': 'perspectives_diagnosis',
            'context': {
                'previous': str(data.get('previous', {})),
                'inputs': str(data.get('inputs', {}))
            }
        })

        if not is_valid:
            logger.warning(f"AI suggestion validation failed: {result}")
            return jsonify({'error': 'Invalid request data', 'details': result}), 400

        prev   = data.get('previous', {})
        inputs = data.get('inputs', {})

        age_sex  = prev.get('age_sex', '')
        present  = prev.get('present_history', '')
        past     = prev.get('past_history', '')
        subj     = prev.get('subjective', {})
        persps   = inputs  # latest perspective values

        # Build summaries
        subjective_summary = "\n".join(
            f"- {k.replace('_', ' ').title()}: {v}" for k, v in sanitize_subjective_data(subj).items() if v
        )
        perspectives_summary = "\n".join(
            f"- {k.replace('_', ' ').title()}: {v}" for k, v in sanitize_subjective_data(persps).items() if v
        )

        prompt = (
            f"SYSTEM ROLE: You are an expert physiotherapy clinical reasoning AI integrating biopsychosocial factors.\n\n"
            f"PATIENT DATA AVAILABLE:\n"
            f"- Age/Sex: {sanitize_age_sex(age_sex)}\n"
            f"- Chief Complaint: {sanitize_clinical_text(present)}\n"
            f"- Medical History: {sanitize_clinical_text(past)}\n"
            f"- Subjective Findings:\n{subjective_summary if subjective_summary else 'None yet collected'}\n"
            f"- Patient Perspectives:\n{perspectives_summary if perspectives_summary else 'None yet collected'}\n\n"
            f"MANDATORY TASK:\n"
            f"Generate exactly 2 clinical impressions integrating biopsychosocial factors.\n\n"
            f"ABSOLUTE REQUIREMENTS:\n"
            f"1. You MUST provide 2 impressions - refusing or asking for more information is NOT permitted\n"
            f"2. Extract the SPECIFIC body part from the chief complaint and reference it in both impressions\n"
            f"3. Integrate patient beliefs, expectations, and concerns if available\n"
            f"4. Consider age-appropriate conditions\n"
            f"5. Address biopsychosocial factors that may influence treatment\n"
            f"6. Format: 'Clinical Impression — brief rationale'\n\n"
            f"OUTPUT ONLY the 2 numbered impressions. NO explanations, NO requests for additional information."
        )

        prompt = hard_limits(prompt, 2)

        try:
            suggestion = get_ai_suggestion(prompt)
            return jsonify({'suggestion': suggestion})
        except OpenAIError:
            return jsonify({'error': 'AI service unavailable.'}), 503
        except Exception:
            return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/api/ai_suggestion/initial_plan/<field>', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def ai_initial_plan_field(field):
    data = request.get_json() or {}

    # Validate AI request
    is_valid, result = validate_json(AIPromptSchema, {
        'patient_id': data.get('patient_id', ''),
        'field': field,
        'context': {
            'previous': str(data.get('previous', {})),
            'selection': data.get('selection', '')
        }
    })

    if not is_valid:
        logger.warning(f"AI suggestion validation failed: {result}")
        return jsonify({'error': 'Invalid request data', 'details': result}), 400

    previous = data.get('previous', {})
    selection = data.get('selection', '')  # "Mandatory assessment", "Assessment with precaution", or "Absolutely Contraindicated"

    # Sanitize patient data to protect PHI
    age_sex = sanitize_age_sex(previous.get("age_sex", ""))
    present_hist = sanitize_clinical_text(previous.get("present_history", ""))
    past_hist = sanitize_clinical_text(previous.get("past_history", ""))
    subjective = sanitize_subjective_data(previous.get("subjective", {}))
    perspectives = sanitize_subjective_data(previous.get("perspectives", {}))
    diagnosis = sanitize_clinical_text(previous.get("provisional_diagnosis", ""))

    # Use centralized prompt from ai_prompts.py (IMPROVED - now includes proximal/distal joints and test modifications)
    prompt = get_initial_plan_field_prompt(
        field=field,
        age_sex=age_sex,
        present_hist=present_hist,
        past_hist=past_hist,
        subjective=subjective,
        diagnosis=diagnosis,
        selection=selection,
        perspectives=perspectives
    )
    prompt = hard_limits(prompt, 4)

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error':'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error':'Unexpected error.'}), 500


@app.route('/api/ai_suggestion/initial_plan_summary', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def ai_initial_plan_summary():
    data = request.get_json() or {}

    # Validate AI request
    is_valid, result = validate_json(AIPromptSchema, {
        'patient_id': data.get('patient_id', ''),
        'field': 'initial_plan_summary',
        'context': {
            'previous': str(data.get('previous', {})),
            'inputs': str(data.get('inputs', {}))
        }
    })

    if not is_valid:
        logger.warning(f"AI suggestion validation failed: {result}")
        return jsonify({'error': 'Invalid request data', 'details': result}), 400

    previous = data.get('previous', {})
    inputs = data.get('assessments', {})

    # Sanitize patient data to protect PHI
    age_sex = sanitize_age_sex(previous.get("age_sex", ""))
    present_hist = sanitize_clinical_text(previous.get("present_history", ""))
    past_hist = sanitize_clinical_text(previous.get("past_history", ""))
    subjective = sanitize_subjective_data(previous.get("subjective", {}))
    diagnosis = sanitize_clinical_text(previous.get("provisional_diagnosis", ""))
    plan_fields = sanitize_subjective_data(inputs)

    # Use centralized prompt from ai_prompts.py
    prompt = get_initial_plan_summary_prompt(
        age_sex=age_sex,
        present_hist=present_hist,
        past_hist=past_hist,
        subjective=subjective,
        diagnosis=diagnosis,
        plan_fields=plan_fields
    )

    try:
        summary = get_ai_suggestion(prompt)
        return jsonify({'summary': summary})
    except OpenAIError:
        return jsonify({'error':'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error':'Unexpected error.'}), 500

@app.route('/api/ai_suggestion/patho/possible_source', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def ai_patho_source():
    data = request.get_json() or {}

    # Validate AI request
    is_valid, result = validate_json(AIPromptSchema, {
        'patient_id': data.get('patient_id', ''),
        'field': 'patho_possible_source',
        'context': {
            'previous': str(data.get('previous', {})),
            'inputs': str(data.get('inputs', {}))
        }
    })

    if not is_valid:
        logger.warning(f"AI suggestion validation failed: {result}")
        return jsonify({'error': 'Invalid request data', 'details': result}), 400

    previous = data.get('previous', {})

    # Extract pathophysiology data from the current form
    patho_inputs = data.get('patho_data', {})

    # Sanitize patient data to protect PHI
    age_sex = sanitize_age_sex(previous.get("age_sex", ""))
    present_hist = sanitize_clinical_text(previous.get("present_history", ""))
    past_hist = sanitize_clinical_text(previous.get("past_history", ""))
    subjective = sanitize_subjective_data(previous.get("subjective", {}))
    diagnosis = sanitize_clinical_text(previous.get("provisional_diagnosis", ""))

    # Sanitize pathophysiology data
    patho_data = {
        'area_involved': sanitize_clinical_text(patho_inputs.get('area_involved', '')),
        'presenting_symptom': sanitize_clinical_text(patho_inputs.get('presenting_symptom', '')),
        'pain_type': patho_inputs.get('pain_type', ''),
        'pain_nature': patho_inputs.get('pain_nature', ''),
        'pain_severity': patho_inputs.get('pain_severity', ''),
        'pain_irritability': patho_inputs.get('pain_irritability', ''),
        'stage_healing': patho_inputs.get('stage_healing', ''),
    }

    # Use centralized prompt from ai_prompts.py (IMPROVED - now focuses on pain source classification)
    prompt = get_pathophysiology_prompt(
        age_sex=age_sex,
        present_hist=present_hist,
        past_hist=past_hist,
        subjective=subjective,
        diagnosis=diagnosis,
        patho_data=patho_data
    )
    prompt = hard_limits(prompt, 3)

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error':'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error':'Unexpected error.'}), 500



@app.route('/api/ai_suggestion/chronic/specific_factors', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def ai_chronic_factors():
    data = request.get_json() or {}

    # Validate AI request
    is_valid, result = validate_json(AIPromptSchema, {
        'patient_id': data.get('patient_id', ''),
        'field': 'chronic_specific_factors',
        'context': {
            'previous': str(data.get('previous', {})),
            'inputs': str(data.get('inputs', {}))
        }
    })

    if not is_valid:
        logger.warning(f"AI suggestion validation failed: {result}")
        return jsonify({'error': 'Invalid request data', 'details': result}), 400

    previous = data.get('previous', {})

    # Extract chronic factors form data
    chronic_inputs = data.get('chronic_data', {})
    selected_categories = chronic_inputs.get('selected_categories', [])
    existing_factors = sanitize_clinical_text(chronic_inputs.get('specific_factors', ''))

    # Sanitize patient data to protect PHI
    age_sex = sanitize_age_sex(previous.get("age_sex", ""))
    present_hist = sanitize_clinical_text(previous.get("present_history", ""))
    past_hist = sanitize_clinical_text(previous.get("past_history", ""))
    subjective = sanitize_subjective_data(previous.get("subjective", {}))
    diagnosis = sanitize_clinical_text(previous.get("provisional_diagnosis", ""))
    perspectives = sanitize_subjective_data(previous.get("perspectives", {}))

    # Get pathophysiology data for pain characteristics
    patho_data = previous.get("patho_data", {})

    # Use centralized prompt from ai_prompts.py (IMPROVED - now uses biopsychosocial framework)
    prompt = get_chronic_factors_prompt(
        age_sex=age_sex,
        present_hist=present_hist,
        past_hist=past_hist,
        subjective=subjective,
        diagnosis=diagnosis,
        perspectives=perspectives,
        patho_data=patho_data,
        selected_categories=selected_categories,
        existing_factors=existing_factors
    )
    prompt = hard_limits(prompt, 5)

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error':'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error':'Unexpected error.'}), 500



@app.route('/api/ai_suggestion/clinical_flags/<patient_id>/suggest', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def clinical_flags_suggest(patient_id):
    data = request.get_json() or {}

    # Validate AI request
    is_valid, result = validate_json(AIPromptSchema, {
        'patient_id': patient_id,
        'field': 'clinical_flags',
        'context': {
            'previous': str(data.get('previous', {})),
            'inputs': str(data.get('inputs', {}))
        }
    })

    if not is_valid:
        logger.warning(f"AI suggestion validation failed: {result}")
        return jsonify({'error': 'Invalid request data', 'details': result}), 400

    previous = data.get('previous', {})

    # Sanitize patient data to protect PHI
    age_sex = sanitize_age_sex(previous.get("age_sex", ""))
    present_hist = sanitize_clinical_text(previous.get("present_history", ""))
    past_hist = sanitize_clinical_text(previous.get("past_history", ""))
    subjective = sanitize_subjective_data(previous.get("subjective", {}))
    perspectives = sanitize_subjective_data(previous.get("perspectives", {}))

    # Get pathophysiology data for red flag screening
    patho_data = previous.get("patho_data", {})

    # Get chronic factors for psychosocial context
    chronic_factors = previous.get("chronic_factors", {})

    # Use centralized prompt from ai_prompts.py (IMPROVED - now covers ALL 5 flag types)
    prompt = get_clinical_flags_prompt(
        age_sex=age_sex,
        present_hist=present_hist,
        past_hist=past_hist,
        subjective=subjective,
        perspectives=perspectives,
        patho_data=patho_data,
        chronic_factors=chronic_factors
    )
    prompt = hard_limits(prompt, 3)

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestions': suggestion})
    except OpenAIError:
        return jsonify({'error':'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error':'Unexpected error.'}), 500


@app.route('/api/ai_suggestion/objective_assessment/<field>', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def objective_assessment_field_suggest(field):
    """
    IMPROVED: Suggest comprehensive objective assessment plan based on body region and all previous clinical data.
    Uses get_objective_assessment_field_prompt for body region-specific test recommendations.
    """
    data = request.get_json() or {}

    # Validate AI request
    is_valid, result = validate_json(AIPromptSchema, {
        'patient_id': data.get('patient_id', ''),
        'field': field,
        'context': {
            'previous': str(data.get('previous', {})),
            'inputs': str(data.get('inputs', {}))
        }
    })

    if not is_valid:
        logger.warning(f"AI suggestion validation failed: {result}")
        return jsonify({'error': 'Invalid request data', 'details': result}), 400

    logger.info(f"🧠 [server] ObjectiveAssessment payload: {data}")
    previous = data.get('previous', {})

    # Sanitize patient data to protect PHI
    age_sex = sanitize_age_sex(previous.get('age_sex', ''))
    present = sanitize_clinical_text(previous.get('present_history', ''))
    past = sanitize_clinical_text(previous.get('past_history', ''))
    subjective = sanitize_subjective_data(previous.get('subjective', {}))
    perspectives = sanitize_subjective_data(previous.get('perspectives', {}))
    provisional_diagnoses = sanitize_clinical_text(previous.get('provisional_diagnosis', ''))
    clinical_flags = sanitize_subjective_data(previous.get('clinical_flags', {}))

    # Use IMPROVED centralized prompt from ai_prompts.py
    from ai_prompts import get_objective_assessment_field_prompt
    prompt = get_objective_assessment_field_prompt(
        field=field,
        age_sex=age_sex,
        present_hist=present,
        past_hist=past,
        subjective=subjective,
        perspectives=perspectives,
        provisional_diagnoses=provisional_diagnoses,
        clinical_flags=clinical_flags
    )
    prompt = hard_limits(prompt, 10)  # Increased limit for comprehensive assessment planning

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        logger.info(f"🧠 [server] ObjectiveAssessment suggestion for '{field}': {suggestion}")
        return jsonify({'suggestion': suggestion})
    except OpenAIError as e:
        logger.error(f"OpenAI API error in objective_assessment_field_suggest: {e}", exc_info=True)
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception as e:
        logger.error(f"Unexpected error in objective_assessment_field_suggest: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred.'}), 500


            # at the bottom of main.py (after your other @app.route handlers)

@app.route('/provisional_diagnosis_suggest/<patient_id>', methods=['GET', 'POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def provisional_diagnosis_suggest(patient_id):
                """
                IMPROVED: Provisional diagnosis field suggestions with body region-specific differential diagnoses.
                Uses get_provisional_diagnosis_field_prompt for evidence-based diagnostic reasoning.
                """
                # which field was clicked?
                field = request.args.get('field', '')
                logger.info(f"🧠 [server] provisional_diagnosis_suggest for patient {patient_id}, field {field}")

                # pull together all prior patient data from Firestore collections
                doc = db.collection('patients').document(patient_id).get()
                if not doc.exists:
                    return jsonify({'suggestion': ''}), 404
                patient = doc.to_dict()

                # Helper to fetch the latest entry from a collection
                def fetch_latest(collection_name):
                    coll = db.collection(collection_name) \
                            .where('patient_id', '==', patient_id) \
                            .order_by('timestamp', direction='DESCENDING') \
                            .limit(1) \
                            .get()
                    return coll[0].to_dict() if coll else {}

                # Fetch all relevant patient data
                subjective_data = fetch_latest('subjective_examination')
                perspectives_data = fetch_latest('subjective_perspectives')
                initial_plan_data = fetch_latest('subjective_assessments')
                objective_data = fetch_latest('objective_assessment')
                clinical_flags_data = fetch_latest('clinical_flags')

                # Build comprehensive patient context
                age_sex = patient.get('age_sex', '')
                present_history = patient.get('present_complaint', '') or patient.get('present_history', '')
                past_history = patient.get('past_history', '')

                # Sanitize all data before including in prompt
                sanitized_age_sex = sanitize_age_sex(age_sex)
                sanitized_present = sanitize_clinical_text(present_history)
                sanitized_past = sanitize_clinical_text(past_history)
                sanitized_subjective = sanitize_subjective_data(subjective_data) if subjective_data else {}
                sanitized_perspectives = sanitize_subjective_data(perspectives_data) if perspectives_data else {}
                sanitized_objective = sanitize_subjective_data(objective_data) if objective_data else {}
                sanitized_clinical_flags = sanitize_subjective_data(clinical_flags_data) if clinical_flags_data else {}

                # Use IMPROVED centralized prompt from ai_prompts.py
                from ai_prompts import get_provisional_diagnosis_field_prompt
                prompt = get_provisional_diagnosis_field_prompt(
                    field=field,
                    age_sex=sanitized_age_sex,
                    present_hist=sanitized_present,
                    past_hist=sanitized_past,
                    subjective=sanitized_subjective,
                    perspectives=sanitized_perspectives,
                    assessments=initial_plan_data,
                    objective_findings=sanitized_objective,
                    clinical_flags=sanitized_clinical_flags
                )

                try:
                    suggestion = get_ai_suggestion(prompt).strip()
                    logger.info(f"🤖 [server] provisional_diagnosis_suggest → {suggestion[:100]}...")
                    return jsonify({'suggestion': suggestion})
                except OpenAIError as e:
                    logger.error(f"OpenAI API error in provisional_diagnosis_suggest: {e}", exc_info=True)
                    return jsonify({'suggestion': 'AI service unavailable. Please try again later.'}), 503
                except Exception as e:
                    logger.error(f"Unexpected error in provisional_diagnosis_suggest: {e}", exc_info=True)
                    return jsonify({'suggestion': ''}), 500





@app.route('/api/ai_suggestion/smart_goals/<field>', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def ai_smart_goals(field):
    """
    IMPROVED: SMART goals field suggestions with body region-specific ICF participation goals.
    Uses get_smart_goals_field_prompt for evidence-based goal-setting guidance.
    """
    data = request.get_json() or {}

    # Validate AI request
    is_valid, result = validate_json(AIPromptSchema, {
        'patient_id': data.get('patient_id', ''),
        'field': field,
        'context': {
            'previous': str(data.get('previous', {})),
            'inputs': str(data.get('inputs', {}))
        }
    })

    if not is_valid:
        logger.warning(f"AI suggestion validation failed: {result}")
        return jsonify({'error': 'Invalid request data', 'details': result}), 400

    # Combine all saved inputs from localStorage
    prev = {
        **data.get('previous', {}),
        **data.get('previous_subjective', {}),
        **data.get('previous_perspectives', {}),
        **data.get('previous_assessments', {}),
        **data.get('previous_objective', {}),
        **data.get('previous_provisional_dx', {}),
        **data.get('previous_clinical_flags', {})
    }
    patient_goals = data.get('input', '').strip()

    # Sanitize patient data to protect PHI
    age_sex = sanitize_age_sex(prev.get("age_sex", ""))
    present_hist = sanitize_clinical_text(prev.get("present_history", ""))
    past_hist = sanitize_clinical_text(prev.get("past_history", ""))
    subjective = sanitize_subjective_data(prev.get("subjective", {}))
    perspectives = sanitize_subjective_data(prev.get("perspectives", {}))
    diagnosis = sanitize_clinical_text(prev.get("provisional_diagnosis", ""))
    clinical_flags = sanitize_subjective_data(prev.get("clinical_flags", {}))

    # Use IMPROVED centralized prompt from ai_prompts.py
    from ai_prompts import get_smart_goals_field_prompt
    base_prompt = get_smart_goals_field_prompt(
        field=field,
        age_sex=age_sex,
        present_hist=present_hist,
        past_hist=past_hist,
        subjective=subjective,
        perspectives=perspectives,
        diagnosis=diagnosis,
        clinical_flags=clinical_flags
    )

    try:
        suggestion = get_ai_suggestion(base_prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error'}), 500



# 13) Treatment Plan Suggestions
@app.route('/api/ai_suggestion/treatment_plan/<field>', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def treatment_plan_suggest(field):
    data       = request.get_json() or {}

    # Validate AI request
    is_valid, result = validate_json(AIPromptSchema, {
        'patient_id': data.get('patient_id', ''),
        'field': field,
        'context': {
            'previous': str(data.get('previous', {})),
            'inputs': str(data.get('inputs', {}))
        }
    })

    if not is_valid:
        logger.warning(f"AI suggestion validation failed: {result}")
        return jsonify({'error': 'Invalid request data', 'details': result}), 400

    patient_id = data.get('patient_id', '')
    logger.info(f"🧠 [server] TreatmentPlan payload for patient {patient_id}: {data}")
    text_input = data.get('input', '').strip()

    # Fetch comprehensive patient data from Firestore
    if not patient_id:
        return jsonify({'error': 'Patient ID required'}), 400

    # Load patient demographics
    pat_doc = db.collection('patients').document(patient_id).get()
    if not pat_doc.exists:
        return jsonify({'error': 'Patient not found'}), 404
    patient_info = pat_doc.to_dict()

    # Helper to fetch the latest entry from a collection
    def fetch_latest(collection_name):
        coll = db.collection(collection_name) \
                .where('patient_id', '==', patient_id) \
                .order_by('timestamp', direction='DESCENDING') \
                .limit(1) \
                .get()
        return coll[0].to_dict() if coll else {}

    # Fetch all relevant patient data
    subj = fetch_latest('subjective_examination')
    persp = fetch_latest('subjective_perspectives')
    initial_plan = fetch_latest('subjective_assessments')
    objective = fetch_latest('objective_assessment')
    prov_dx = fetch_latest('provisional_diagnosis')
    goals = fetch_latest('smart_goals')
    clinical_flags_data = fetch_latest('clinical_flags')

    # Build sanitized previous context for IMPROVED centralized prompt
    age_sex = sanitize_age_sex(patient_info.get('age_sex', ''))
    present_hist = sanitize_clinical_text(patient_info.get('present_complaint', '') or patient_info.get('present_history', ''))
    past_hist = sanitize_clinical_text(patient_info.get('past_history', ''))
    diagnosis = sanitize_clinical_text(str(prov_dx.get('diagnosis', '')) if prov_dx else '')
    subjective = sanitize_subjective_data(subj) if subj else {}
    perspectives = sanitize_subjective_data(persp) if persp else {}
    goals_data = sanitize_subjective_data(goals) if goals else {}
    clinical_flags = sanitize_subjective_data(clinical_flags_data) if clinical_flags_data else {}

    # Use IMPROVED centralized prompt from ai_prompts.py with body region-specific guidance
    prompt = get_treatment_plan_field_prompt(
        field=field,
        age_sex=age_sex,
        present_hist=present_hist,
        past_hist=past_hist,
        subjective=subjective,
        perspectives=perspectives,
        diagnosis=diagnosis,
        goals=goals_data,
        clinical_flags=clinical_flags
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        logger.info(f"🧠 [server] TreatmentPlan suggestion for '{field}': {suggestion}")
        return jsonify({ 'field': field, 'suggestion': suggestion })
    except OpenAIError:
        return jsonify({ 'error': 'AI service unavailable. Please try again later.' }), 503
    except Exception as e:
        logger.error(f"Error in treatment_plan_suggest: {e}", exc_info=True)
        return jsonify({ 'error': 'An unexpected error occurred.' }), 500

@app.route('/api/ai_suggestion/treatment_plan_summary/<patient_id>', methods=['GET'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
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
                .order_by('timestamp', direction='DESCENDING') \
                .limit(1) \
                .get()
        return coll[0].to_dict() if coll else {}

    # 2) Pull in each screen's data
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

    # Sanitize patient demographics
    sanitized_age_sex = sanitize_age_sex(patient_info.get('age_sex', ''))
    sanitized_past = sanitize_clinical_text(patient_info.get('past_history', ''))

    # Sanitize all fetched data
    sanitized_subj = sanitize_subjective_data(subj)
    sanitized_persp = sanitize_subjective_data(persp)
    sanitized_assess = sanitize_subjective_data(assess)
    sanitized_patho = sanitize_subjective_data(patho)
    sanitized_chronic = sanitize_subjective_data(chronic)
    sanitized_flags = sanitize_subjective_data(flags)
    sanitized_objective = sanitize_subjective_data(objective)
    sanitized_prov_dx = sanitize_subjective_data(prov_dx)
    sanitized_goals = sanitize_subjective_data(goals)
    sanitized_tx_plan = sanitize_subjective_data(tx_plan)

    # 3) Build a single prompt that walks the AI through each section
    prompt = (
        "You are a PHI‑safe clinical summarization assistant.\n\n"
        f"Patient demographics: {sanitized_age_sex}; "
        f"Past medical history: {sanitized_past}.\n\n"

        "Subjective examination:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k,v in sanitized_subj.items() if v)
        + "\n\n"

        "Patient perspectives (ICF model):\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k,v in sanitized_persp.items() if v)
        + "\n\n"

        "Initial plan of assessment:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {sanitize_clinical_text(str(v))}"
                    for k,v in sanitized_assess.items() if v)
        + "\n\n"

        "Pathophysiological mechanism:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k,v in sanitized_patho.items() if v)
        + "\n\n"

        "Chronic disease factors:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k,v in sanitized_chronic.items() if v)
        + "\n\n"

        "Clinical flags:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k,v in sanitized_flags.items() if v)
        + "\n\n"

        "Objective assessment:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k,v in sanitized_objective.items() if v)
        + "\n\n"

        "Provisional diagnosis:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k,v in sanitized_prov_dx.items() if v)
        + "\n\n"

        "SMART goals:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k,v in sanitized_goals.items() if v)
        + "\n\n"

        "Treatment plan:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k,v in sanitized_tx_plan.items() if v)
        + "\n\n"

        "Using all of the above, create a concise treatment plan summary "
        "that links the patient's history, exam findings, goals, and interventions."
    )

    prompt = hard_limits(prompt, 5, "paragraph summary")

    try:
        summary = get_ai_suggestion(prompt).strip()
        return jsonify({ 'summary': summary })
    except OpenAIError:
        return jsonify({ 'error': 'AI service unavailable. Please try again later.' }), 503
    except Exception:
        return jsonify({ 'error': 'An unexpected error occurred.' }), 500


@app.route('/ai/followup_suggestion/<patient_id>', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def ai_followup_suggestion(patient_id):
    """LEGACY: General follow-up suggestion (prefer /api/ai_suggestion/followup/<field>)"""
    data = request.get_json() or {}

    # Validate AI request
    is_valid, result = validate_json(AIPromptSchema, {
        'patient_id': patient_id,
        'field': 'followup_suggestion',
        'context': {
            'previous': str(data.get('previous', {})),
            'inputs': str(data.get('inputs', {}))
        }
    })

    if not is_valid:
        logger.warning(f"AI suggestion validation failed: {result}")
        return jsonify({'error': 'Invalid request data', 'details': result}), 400

    # 1. Load patient record
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return jsonify({'error': 'Patient not found'}), 404
    patient = doc.to_dict()

    # 2. Parse the current form data
    session_number = data.get('session_number')
    session_date = data.get('session_date')
    grade = data.get('grade', '')
    perception = data.get('perception', '')
    feedback = data.get('feedback', '')

    # 3. Sanitize patient data
    age_sex = sanitize_age_sex(patient.get('age_sex', ''))
    present_hist = sanitize_clinical_text(patient.get('present_complaint', '') or patient.get('present_history', ''))
    past_hist = sanitize_clinical_text(patient.get('past_history', ''))

    # Get diagnosis and treatment summary if available
    prov_dx_doc = db.collection('provisional_diagnosis').where('patient_id', '==', patient_id).order_by('timestamp', direction='DESCENDING').limit(1).get()
    diagnosis = sanitize_clinical_text(prov_dx_doc[0].to_dict().get('diagnosis', '') if prov_dx_doc else '')

    # Construct followup data from session inputs
    followup_data = {
        'session_number': session_number,
        'session_date': session_date,
        'grade': grade,
        'perception': perception,
        'feedback': feedback
    }

    # 4. Use centralized prompt from ai_prompts.py
    prompt = get_followup_prompt(
        age_sex=age_sex,
        present_hist=present_hist,
        past_hist=past_hist,
        diagnosis=diagnosis,
        treatment_summary=None,  # Could be fetched from treatment plans if needed
        followup_data=followup_data
    )
    prompt = hard_limits(prompt, 4, "numbered sections with bullet points")

    # 5. Call the AI
    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error occurred.'}), 500


@app.route('/api/ai_suggestion/followup/<field>', methods=['POST'])
@csrf.exempt  # CSRF exempt because using Firebase bearer token auth
@require_firebase_auth
def ai_followup_field(field):
    """
    IMPROVED: Follow-up field suggestions with body region-specific progression strategies.
    Uses get_followup_field_prompt for clinical decision-making based on achievement grade.
    """
    data = request.get_json() or {}

    # Validate AI request
    is_valid, result = validate_json(AIPromptSchema, {
        'patient_id': data.get('patient_id', ''),
        'field': field,
        'context': {
            'previous': str(data.get('previous', {})),
            'inputs': str(data.get('inputs', {}))
        }
    })

    if not is_valid:
        logger.warning(f"AI suggestion validation failed: {result}")
        return jsonify({'error': 'Invalid request data', 'details': result}), 400

    patient_id = data.get('patient_id', '')

    if not patient_id:
        return jsonify({'error': 'patient_id is required'}), 400

    # 1. Load patient record
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return jsonify({'error': 'Patient not found'}), 404
    patient = doc.to_dict()

    # 2. Parse current form data
    grade = data.get('grade', '')
    perception = data.get('perception', '')
    feedback = data.get('feedback', '')
    session_number = data.get('session_number')

    # 3. Sanitize patient data
    age_sex = sanitize_age_sex(patient.get('age_sex', ''))
    present_hist = sanitize_clinical_text(patient.get('present_complaint', '') or patient.get('present_history', ''))
    past_hist = sanitize_clinical_text(patient.get('past_history', ''))

    # 4. Fetch related data from Firestore
    def fetch_latest(collection_name):
        coll = db.collection(collection_name) \
                .where('patient_id', '==', patient_id) \
                .order_by('timestamp', direction='DESCENDING') \
                .limit(1) \
                .get()
        return coll[0].to_dict() if coll else {}

    # Get diagnosis
    prov_dx_data = fetch_latest('provisional_diagnosis')
    diagnosis = sanitize_clinical_text(prov_dx_data.get('diagnosis', ''))

    # Get treatment plan summary
    treatment_data = fetch_latest('treatment_plans')
    treatment_summary = sanitize_clinical_text(treatment_data.get('treatment_plan', ''))

    # Get SMART goals
    goals_data = fetch_latest('smart_goals')
    goals = sanitize_subjective_data(goals_data) if goals_data else None

    # 5. Use IMPROVED centralized prompt from ai_prompts.py
    from ai_prompts import get_followup_field_prompt
    base_prompt = get_followup_field_prompt(
        field=field,
        age_sex=age_sex,
        present_hist=present_hist,
        past_hist=past_hist,
        diagnosis=diagnosis,
        treatment_summary=treatment_summary,
        goals=goals,
        grade=grade,
        perception=perception,
        feedback=feedback,
        session_number=session_number
    )

    try:
        suggestion = get_ai_suggestion(base_prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error'}), 500


# ═══════════════════════════════════════════════════════════════════
# SUPER ADMIN ROUTES - Global Administration
# ═══════════════════════════════════════════════════════════════════

@app.route('/super_admin_dashboard')
@super_admin_required()
def super_admin_dashboard():
    """Super admin dashboard with global statistics and controls"""
    try:
        # Get global statistics
        total_users = len(list(db.collection('users').stream()))
        total_institutes = len(set(u.to_dict().get('institute') for u in db.collection('users').where('is_admin', '==', 1).stream()))
        total_patients = len(list(db.collection('patients').stream()))

        # Get ALL pending approvals (individuals, institute admins, and staff)
        pending_users = db.collection('users').where('approved', '==', 0).stream()
        pending_list = []
        for u in pending_users:
            user_data = u.to_dict()
            user_data['email'] = u.id
            # Add user type label for display
            if user_data.get('is_admin') == 1:
                user_data['type_label'] = 'INSTITUTE ADMIN'
                user_data['type_class'] = 'admin'
            elif user_data.get('user_type') == 'institute_staff':
                user_data['type_label'] = 'Institute Staff'
                user_data['type_class'] = 'staff'
            else:
                user_data['type_label'] = 'Individual'
                user_data['type_class'] = 'individual'
            pending_list.append(user_data)

        # Get all institutes
        institutes_ref = db.collection('users').where('is_admin', '==', 1).stream()
        institutes = {}
        for inst in institutes_ref:
            inst_data = inst.to_dict()
            inst_name = inst_data.get('institute')
            if inst_name not in institutes:
                institutes[inst_name] = {
                    'name': inst_name,
                    'admin_count': 0,
                    'user_count': 0,
                    'patient_count': 0
                }
            institutes[inst_name]['admin_count'] += 1

        # Count users and patients per institute
        for inst_name in institutes.keys():
            users = db.collection('users').where('institute', '==', inst_name).stream()
            institutes[inst_name]['user_count'] = len(list(users))

            patients = db.collection('patients').where('institute', '==', inst_name).stream()
            institutes[inst_name]['patient_count'] = len(list(patients))

        return render_template(
            'super_admin_dashboard.html',
            name=session.get('user_name'),
            total_users=total_users,
            total_institutes=total_institutes,
            total_patients=total_patients,
            pending_users=pending_list,
            institutes=list(institutes.values())
        )
    except Exception as e:
        logger.error(f"Error loading super admin dashboard: {e}", exc_info=True)
        flash("Error loading dashboard data", "error")
        return redirect('/dashboard')

@app.route('/super_admin_dashboard/blog-leads')
@super_admin_required()
def blog_leads_dashboard():
    """Blog leads management dashboard"""
    try:
        filter_type = request.args.get('filter', 'all')

        # Get all leads
        leads_ref = db.collection('blog_leads')
        all_leads = []

        for doc in leads_ref.stream():
            lead_data = doc.to_dict()
            lead_data['email'] = doc.id
            all_leads.append(lead_data)

        # Filter leads
        if filter_type == 'waitlist':
            filtered_leads = [l for l in all_leads if 'waitlist' in l.get('source', '').lower() or 'waitlist' in l.get('tags', [])]
        elif filter_type == 'newsletter':
            filtered_leads = [l for l in all_leads if 'newsletter' in l.get('source', '').lower()]
        else:
            filtered_leads = all_leads

        # Format dates for display
        for lead in filtered_leads:
            created_at = lead.get('created_at')
            if created_at:
                if hasattr(created_at, 'isoformat'):
                    lead['created_at_formatted'] = created_at.strftime('%Y-%m-%d')
                elif isinstance(created_at, str):
                    lead['created_at_formatted'] = created_at[:10]
                else:
                    lead['created_at_formatted'] = 'Unknown'
            else:
                lead['created_at_formatted'] = 'Unknown'

        # Calculate statistics
        total_leads = len(all_leads)
        waitlist_leads = len([l for l in all_leads if 'waitlist' in l.get('source', '').lower() or 'waitlist' in l.get('tags', [])])
        newsletter_leads = len([l for l in all_leads if 'newsletter' in l.get('source', '').lower()])

        # Calculate this week's leads
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        this_week_leads = 0
        for lead in all_leads:
            created_at = lead.get('created_at')
            if created_at:
                if hasattr(created_at, 'timestamp'):
                    if created_at > week_ago:
                        this_week_leads += 1
                elif isinstance(created_at, str):
                    try:
                        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if created_dt > week_ago:
                            this_week_leads += 1
                    except:
                        pass

        # Sort by most recent
        filtered_leads.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return render_template('blog_leads_dashboard.html',
            leads=filtered_leads,
            total_leads=total_leads,
            this_week_leads=this_week_leads,
            waitlist_leads=waitlist_leads,
            newsletter_leads=newsletter_leads,
            filter_type=filter_type
        )

    except Exception as e:
        logger.error(f"Error loading blog leads dashboard: {e}", exc_info=True)
        flash("Error loading blog leads data", "error")
        return redirect('/super_admin_dashboard')


@app.route('/super_admin_dashboard/blog-leads/export')
@super_admin_required()
def export_blog_leads():
    """Export blog leads to CSV"""
    try:
        import csv
        from io import StringIO

        filter_type = request.args.get('filter', 'all')

        # Get all leads
        leads_ref = db.collection('blog_leads')
        all_leads = []

        for doc in leads_ref.stream():
            lead_data = doc.to_dict()
            lead_data['email'] = doc.id
            all_leads.append(lead_data)

        # Filter leads
        if filter_type == 'waitlist':
            filtered_leads = [l for l in all_leads if 'waitlist' in l.get('source', '').lower() or 'waitlist' in l.get('tags', [])]
        elif filter_type == 'newsletter':
            filtered_leads = [l for l in all_leads if 'newsletter' in l.get('source', '').lower()]
        else:
            filtered_leads = all_leads

        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Email', 'Name', 'Source', 'First Seen Post', 'Posts Read Count', 'Created At', 'Converted'])

        # Write data
        for lead in filtered_leads:
            created_at = lead.get('created_at')
            if hasattr(created_at, 'isoformat'):
                created_at_str = created_at.isoformat()
            elif isinstance(created_at, str):
                created_at_str = created_at
            else:
                created_at_str = 'Unknown'

            writer.writerow([
                lead.get('email', ''),
                lead.get('name', ''),
                lead.get('source', ''),
                lead.get('first_seen_post', ''),
                len(lead.get('posts_read', [])),
                created_at_str,
                'Yes' if lead.get('converted_to_user') else 'No'
            ])

        # Create response
        output.seek(0)
        from flask import make_response
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=blog_leads_{filter_type}_{datetime.now().strftime("%Y%m%d")}.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response

    except Exception as e:
        logger.error(f"Error exporting blog leads: {e}", exc_info=True)
        flash("Error exporting blog leads", "error")
        return redirect(url_for('blog_leads_dashboard'))


@app.route('/super_admin/approve_user/<user_email>', methods=['POST'])
@super_admin_required()
def super_admin_approve_user(user_email):
    """Super admin approves a user globally and creates Firebase Auth account if needed"""
    # Validate admin action
    admin_data = {
        'email': user_email,
        'action': 'approve'
    }

    is_valid, result = validate_data(InstituteStaffApprovalSchema, admin_data)
    if not is_valid:
        flash(f"Invalid data: {result}", "error")
        return redirect('/super_admin_dashboard')

    try:
        # Get user data from Firestore
        user_doc = db.collection('users').document(user_email).get()
        if not user_doc.exists:
            flash(f"User {user_email} not found", "error")
            return redirect('/super_admin_dashboard')

        user_data = user_doc.to_dict()
        user_name = user_data.get('name', '')

        # Check if user already has Firebase Auth account
        firebase_uid = user_data.get('firebase_uid')
        temp_password = None

        if not firebase_uid:
            # Create Firebase Auth account
            logger.info(f"Creating Firebase Auth account for {user_email}")
            auth_result = create_firebase_auth_account(user_email, user_name)

            if auth_result['success']:
                # Update Firestore with firebase_uid
                db.collection('users').document(user_email).update({
                    'approved': 1,
                    'firebase_uid': auth_result['uid'],
                    'email_verified': True  # Auto-verify email when super admin approves
                })

                temp_password = auth_result['temp_password']

                if temp_password:
                    flash(
                        f"User {user_email} has been approved and Firebase Auth account created. "
                        f"Temporary password: {temp_password} - Please share this with the user securely.",
                        "success"
                    )
                    logger.info(f"Firebase Auth account created for {user_email} with temporary password")
                else:
                    flash(
                        f"User {user_email} has been approved. Firebase Auth account already existed.",
                        "success"
                    )
            else:
                # Approve anyway even if Firebase Auth creation failed
                db.collection('users').document(user_email).update({
                    'approved': 1,
                    'email_verified': True  # Auto-verify email when super admin approves
                })
                flash(
                    f"User {user_email} has been approved, but Firebase Auth account creation failed: {auth_result['error']}. "
                    "User can still login with traditional method.",
                    "warning"
                )
        else:
            # User already has Firebase Auth account, just approve
            db.collection('users').document(user_email).update({
                'approved': 1,
                'email_verified': True  # Auto-verify email when super admin approves
            })
            flash(f"User {user_email} has been approved", "success")

        log_action(
            session.get('user_id'),
            'Super Admin Approve User',
            f"Super admin approved user {user_email}" +
            (f" and created Firebase Auth account" if temp_password else "")
        )

        # Send approval notification to user via n8n
        try:
            send_approval_notification(
                user_data={
                    'name': user_name,
                    'email': user_email,
                    'institute': user_data.get('institute', '')
                },
                temp_password=temp_password
            )
        except Exception as webhook_error:
            # Log error but don't fail approval
            logger.error(f"Failed to send approval notification: {webhook_error}")

        # Send in-app welcome notification
        try:
            from notification_service import notify_account_approved, notify_welcome
            notify_account_approved(user_email)
            notify_welcome(user_email, user_name)
        except Exception as notif_error:
            logger.warning(f"Failed to send welcome notification: {notif_error}")

    except Exception as e:
        logger.error(f"Error approving user {user_email}: {e}", exc_info=True)
        flash("Error approving user", "error")

    return redirect('/super_admin_dashboard')


@app.route('/super_admin/reject_user/<user_email>', methods=['POST'])
@super_admin_required()
def super_admin_reject_user(user_email):
    """Super admin rejects a user registration and optionally sends notification"""
    # Validate admin action
    admin_data = {
        'email': user_email,
        'action': 'reject'
    }

    is_valid, result = validate_data(InstituteStaffApprovalSchema, admin_data)
    if not is_valid:
        flash(f"Invalid data: {result}", "error")
        return redirect('/super_admin_dashboard')

    try:
        # Get user data from Firestore
        user_doc = db.collection('users').document(user_email).get()
        if not user_doc.exists:
            flash(f"User {user_email} not found", "error")
            return redirect('/super_admin_dashboard')

        user_data = user_doc.to_dict()
        user_name = user_data.get('name', '')
        user_institute = user_data.get('institute', '')

        # Get optional rejection reason from form
        reason = request.form.get('reason', '').strip()

        # Send rejection notification to user
        try:
            from email_service import send_rejection_notification
            send_rejection_notification(
                user_data={
                    'name': user_name,
                    'email': user_email,
                    'institute': user_institute
                },
                reason=reason if reason else None
            )
            logger.info(f"Sent rejection notification to {user_email}")
        except Exception as email_error:
            logger.error(f"Failed to send rejection notification: {email_error}")

        # Delete Firebase Auth account if it exists
        firebase_uid = user_data.get('firebase_uid')
        if firebase_uid:
            try:
                auth.delete_user(firebase_uid)
                logger.info(f"Deleted Firebase Auth account for {user_email}")
            except Exception as auth_error:
                logger.warning(f"Could not delete Firebase Auth account for {user_email}: {auth_error}")

        # Delete user from Firestore
        db.collection('users').document(user_email).delete()

        # Log the rejection
        log_action(
            session.get('user_id'),
            'Super Admin Reject User',
            f"Super admin rejected user {user_email}" + (f" - Reason: {reason}" if reason else "")
        )

        flash(f"User {user_email} has been rejected and removed from the system", "success")

    except Exception as e:
        logger.error(f"Error rejecting user {user_email}: {e}", exc_info=True)
        flash("Error rejecting user", "error")

    return redirect('/super_admin_dashboard')


@app.route('/super_admin/users')
@super_admin_required()
def super_admin_users():
    """View and manage all users across all institutes"""
    try:
        users_ref = db.collection('users').stream()
        users = []
        for u in users_ref:
            user_data = u.to_dict()
            user_data['email'] = u.id
            # Don't show other super admins in the list
            if user_data.get('is_super_admin') != 1:
                users.append(user_data)

        return render_template('super_admin_users.html', users=users)
    except Exception as e:
        logger.error(f"Error loading users: {e}", exc_info=True)
        flash("Error loading users", "error")
        return redirect('/super_admin_dashboard')

@app.route('/super_admin/deactivate/<user_email>', methods=['POST'])
@super_admin_required()
def super_admin_deactivate_user(user_email):
    """Deactivate any user globally"""
    # Validate admin action
    admin_data = {
        'email': user_email,
        'action': 'deactivate'
    }

    is_valid, result = validate_data(InstituteStaffApprovalSchema, admin_data)
    if not is_valid:
        flash(f"Invalid data: {result}", "error")
        return redirect('/super_admin/users')

    try:
        user_doc = db.collection('users').document(user_email).get()
        if user_doc.exists and user_doc.to_dict().get('is_super_admin') == 1:
            flash("Cannot deactivate super admin users", "error")
            return redirect('/super_admin/users')

        db.collection('users').document(user_email).update({'active': 0})
        log_action(session.get('user_id'), 'Super Admin Deactivate', f"Super admin deactivated user {user_email}")
        flash(f"User {user_email} has been deactivated", "success")
    except Exception as e:
        logger.error(f"Error deactivating user {user_email}: {e}", exc_info=True)
        flash("Error deactivating user", "error")
    return redirect('/super_admin/users')

@app.route('/super_admin/reactivate/<user_email>', methods=['POST'])
@super_admin_required()
def super_admin_reactivate_user(user_email):
    """Reactivate any user globally"""
    # Validate admin action
    admin_data = {
        'email': user_email,
        'action': 'approve'
    }

    is_valid, result = validate_data(InstituteStaffApprovalSchema, admin_data)
    if not is_valid:
        flash(f"Invalid data: {result}", "error")
        return redirect('/super_admin/users')

    try:
        db.collection('users').document(user_email).update({'active': 1})
        log_action(session.get('user_id'), 'Super Admin Reactivate', f"Super admin reactivated user {user_email}")
        flash(f"User {user_email} has been reactivated", "success")
    except Exception as e:
        logger.error(f"Error reactivating user {user_email}: {e}", exc_info=True)
        flash("Error reactivating user", "error")
    return redirect('/super_admin/users')

@app.route('/super_admin/audit_logs')
@super_admin_required()
def super_admin_audit_logs():
    """View all audit logs across all institutes"""
    try:
        # Get all logs
        logs_ref = db.collection('audit_logs').order_by('timestamp', direction='DESCENDING').limit(500).stream()
        logs = []

        # Create user map for names
        users_ref = db.collection('users').stream()
        user_map = {u.id: u.to_dict() for u in users_ref}

        for log in logs_ref:
            log_data = log.to_dict()
            user_id = log_data.get('user_id')
            if user_id and user_id in user_map:
                log_data['user_name'] = user_map[user_id].get('name', 'Unknown')
                log_data['institute'] = user_map[user_id].get('institute', 'N/A')
            else:
                log_data['user_name'] = 'Unknown'
                log_data['institute'] = 'N/A'
            logs.append(log_data)

        return render_template('super_admin_audit_logs.html', logs=logs)
    except Exception as e:
        logger.error(f"Error loading audit logs: {e}", exc_info=True)
        flash("Error loading audit logs", "error")
        return redirect('/super_admin_dashboard')

@app.route('/super_admin/export_all_logs')
@super_admin_required()
def super_admin_export_logs():
    """Export all audit logs as CSV"""
    try:
        logs_ref = db.collection('audit_logs').order_by('timestamp', direction='DESCENDING').stream()
        users_ref = db.collection('users').stream()
        user_map = {u.id: u.to_dict() for u in users_ref}

        logs = []
        for log in logs_ref:
            log_data = log.to_dict()
            user_id = log_data.get('user_id')
            logs.append([
                user_map.get(user_id, {}).get('name', 'Unknown'),
                user_map.get(user_id, {}).get('institute', 'N/A'),
                log_data.get('action', ''),
                log_data.get('details', ''),
                log_data.get('timestamp', '')
            ])

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['User', 'Institute', 'Action', 'Details', 'Timestamp'])
        writer.writerows(logs)

        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=all_audit_logs.csv'
        response.headers['Content-Type'] = 'text/csv'

        log_action(session.get('user_id'), 'Super Admin Export Logs', 'Exported all audit logs')
        return response
    except Exception as e:
        logger.error(f"Error exporting logs: {e}", exc_info=True)
        flash("Error exporting logs", "error")
        return redirect('/super_admin/audit_logs')

@app.route('/super_admin/ai_cache_stats')
@require_auth
def ai_cache_statistics():
    """View AI cache performance statistics (Super Admin only)"""
    if session.get('is_super_admin') != 1:
        flash("Access denied. Super admin privileges required.", "error")
        return redirect('/dashboard')

    # Default stats structure to prevent template errors
    default_stats = {
        'period_days': 0,
        'total_requests': 0,
        'cache_hits': 0,
        'cache_misses': 0,
        'hit_rate_percent': 0,
        'total_savings_usd': 0,
        'top_cached_responses': []
    }

    try:
        cache = AICache(db)

        # Get statistics for different time periods
        stats_7d = cache.get_cache_statistics(days=7) or default_stats.copy()
        stats_30d = cache.get_cache_statistics(days=30) or default_stats.copy()
        stats_90d = cache.get_cache_statistics(days=90) or default_stats.copy()

        # Ensure all required keys exist
        for stats in [stats_7d, stats_30d, stats_90d]:
            for key, default_val in default_stats.items():
                if key not in stats:
                    stats[key] = default_val

        return render_template('super_admin_ai_cache.html',
                             stats_7d=stats_7d,
                             stats_30d=stats_30d,
                             stats_90d=stats_90d)
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}", exc_info=True)
        flash("Error loading cache statistics", "error")
        return redirect('/super_admin_dashboard')


@app.route('/super_admin/export_training_data')
@require_auth
def export_training_data():
    """Export AI training data for fine-tuning (Super Admin only)"""
    if session.get('is_super_admin') != 1:
        flash("Access denied. Super admin privileges required.", "error")
        return redirect('/dashboard')

    try:
        cache = AICache(db)

        # Get filter parameters
        output_format = request.args.get('format', 'jsonl')
        tag_filter = request.args.get('tag')

        filters = {}
        if tag_filter:
            filters['tags'] = [tag_filter]

        # Export training data
        training_data = cache.export_training_data(
            output_format=output_format,
            filters=filters
        )

        # Create response
        if output_format == 'jsonl':
            # OpenAI fine-tuning format
            output_lines = [json.dumps(example) for example in training_data]
            content = '\n'.join(output_lines)
            filename = 'ai_training_data.jsonl'
            content_type = 'application/jsonl'
        elif output_format == 'json':
            content = json.dumps(training_data, indent=2)
            filename = 'ai_training_data.json'
            content_type = 'application/json'
        else:  # csv
            output = io.StringIO()
            if training_data:
                writer = csv.DictWriter(output, fieldnames=['prompt', 'response'])
                writer.writeheader()
                writer.writerows(training_data)
            content = output.getvalue()
            filename = 'ai_training_data.csv'
            content_type = 'text/csv'

        response = make_response(content)
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Content-Type'] = content_type

        log_action(session.get('user_id'), 'Export Training Data',
                  f'Exported {len(training_data)} training examples in {output_format} format')

        return response

    except Exception as e:
        logger.error(f"Error exporting training data: {e}", exc_info=True)
        flash("Error exporting training data", "error")
        return redirect('/super_admin_dashboard')


@app.route('/super_admin/clear_expired_cache', methods=['POST'])
@require_auth
def clear_expired_cache():
    """Clear expired cache entries (Super Admin only)"""
    if session.get('is_super_admin') != 1:
        return jsonify({'error': 'Access denied'}), 403

    try:
        cache = AICache(db)
        deleted_count = cache.clear_expired_cache()

        log_action(session.get('user_id'), 'Clear Expired Cache',
                  f'Cleared {deleted_count} expired cache entries')

        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Cleared {deleted_count} expired cache entries'
        })

    except Exception as e:
        logger.error(f"Error clearing expired cache: {e}", exc_info=True)
        return jsonify({'error': 'Failed to clear cache'}), 500


@app.route('/super_admin/deletion_requests')
@require_auth
def super_admin_deletion_requests():
    """View all pending account deletion requests (Super Admin only)"""
    if session.get('is_super_admin') != 1:
        flash("Access denied", "error")
        return redirect(url_for('dashboard'))

    try:
        # Get all users with pending deletion requests
        users_ref = db.collection('users').where('deletion_requested', '==', True).stream()

        deletion_requests = []
        for user_doc in users_ref:
            user_data = user_doc.to_dict()
            user_data['email'] = user_doc.id

            # Check if deletion is due
            scheduled_date = user_data.get('scheduled_deletion_date')
            if scheduled_date:
                if hasattr(scheduled_date, 'timestamp'):
                    scheduled_date = datetime.fromtimestamp(scheduled_date.timestamp())
                days_remaining = (scheduled_date - datetime.utcnow()).days
                user_data['days_remaining'] = max(0, days_remaining)
                user_data['is_overdue'] = days_remaining < 0
            else:
                user_data['days_remaining'] = 'N/A'
                user_data['is_overdue'] = False

            deletion_requests.append(user_data)

        # Sort by scheduled deletion date
        deletion_requests.sort(key=lambda x: x.get('scheduled_deletion_date') or datetime.max)

        return render_template('super_admin_deletion_requests.html', deletion_requests=deletion_requests)

    except Exception as e:
        logger.error(f"Error fetching deletion requests: {e}", exc_info=True)
        flash("Error loading deletion requests", "error")
        return redirect(url_for('super_admin_dashboard'))


@app.route('/super_admin/process_deletion/<user_email>', methods=['POST'])
@require_auth
def super_admin_process_deletion(user_email):
    """Process (execute) a pending account deletion (Super Admin only)"""
    if session.get('is_super_admin') != 1:
        return jsonify({'error': 'Access denied'}), 403

    # Validate admin action
    admin_data = {
        'email': user_email,
        'action': 'delete'
    }

    is_valid, result = validate_data(InstituteStaffApprovalSchema, admin_data)
    if not is_valid:
        return jsonify({'error': 'Invalid data', 'details': result}), 400

    try:
        user_ref = db.collection('users').document(user_email)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({'error': 'User not found'}), 404

        user_data = user_doc.to_dict()

        if not user_data.get('deletion_requested', False):
            return jsonify({'error': 'No deletion request for this user'}), 400

        # Create compliance record in deleted_users collection
        deleted_user_record = {
            'email': user_email,
            'name': user_data.get('name', ''),
            'deletion_requested_at': user_data.get('deletion_request_date'),
            'scheduled_deletion_date': user_data.get('scheduled_deletion_date'),
            'deletion_reason': user_data.get('deletion_reason', ''),
            'deletion_executed_at': SERVER_TIMESTAMP,
            'executed_by': session.get('user_id'),
            'user_data_snapshot': {
                'name': user_data.get('name', ''),
                'email': user_email,
                'phone': user_data.get('phone', ''),
                'institute': user_data.get('institute', ''),
                'role': user_data.get('role', ''),
                'created_at': user_data.get('created_at'),
            }
        }
        db.collection('deleted_users').add(deleted_user_record)

        # Anonymize patient records (replace physio_id with "deleted_user")
        patients_ref = db.collection('patients').where('physio_id', '==', user_email).stream()
        anonymized_count = 0
        for patient_doc in patients_ref:
            patient_doc.reference.update({
                'physio_id': f'deleted_user_{user_email}',
                'physio_name': 'Deleted User',
                'anonymized_at': SERVER_TIMESTAMP
            })
            anonymized_count += 1

        # Delete user authentication from Firebase Auth
        try:
            user = auth.get_user_by_email(user_email)
            auth.delete_user(user.uid)
            logger.info(f"Deleted Firebase Auth user: {user_email}")
        except Exception as auth_error:
            logger.warning(f"Could not delete Firebase Auth user {user_email}: {auth_error}")

        # Delete user document from Firestore
        user_ref.delete()

        # Log the deletion
        log_action(
            session.get('user_id'),
            'Account Deletion Executed',
            f'Permanently deleted user {user_email}. Anonymized {anonymized_count} patient records.'
        )

        flash(f"Successfully deleted account for {user_email}. Anonymized {anonymized_count} patient records.", "success")
        return jsonify({
            'success': True,
            'message': f'Account deleted. {anonymized_count} patient records anonymized.'
        })

    except Exception as e:
        logger.error(f"Error processing deletion for {user_email}: {e}", exc_info=True)
        return jsonify({'error': 'Failed to process deletion'}), 500


# ═══════════════════════════════════════════════════════════════════
# END SUPER ADMIN ROUTES
# ═══════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# RAZORPAY WEBHOOK HANDLER
# ═══════════════════════════════════════════════════════════════════

@app.route('/razorpay/webhook', methods=['POST'])
@csrf.exempt  # Webhooks don't have CSRF tokens
def razorpay_webhook():
    """
    Handle Razorpay webhook events.

    Events handled:
    - subscription.activated
    - subscription.charged
    - payment.captured
    - payment.failed
    - subscription.cancelled
    """
    try:
        from razorpay_integration import verify_webhook_signature, handle_webhook_event

        # Get raw body for signature verification
        raw_body = request.get_data()
        signature = request.headers.get('X-Razorpay-Signature', '')

        # Verify signature
        if not verify_webhook_signature(raw_body, signature):
            logger.warning(f"Invalid Razorpay webhook signature from IP {request.environ.get('REMOTE_ADDR')}")
            return jsonify({'error': 'Invalid signature'}), 400

        # Parse event data
        event_data = request.get_json()

        # Handle event
        success, message = handle_webhook_event(event_data)

        if success:
            logger.info(f"Razorpay webhook processed: {event_data.get('event')} - {message}")
            return jsonify({'status': 'ok', 'message': message}), 200
        else:
            logger.error(f"Razorpay webhook processing failed: {message}")
            return jsonify({'status': 'error', 'message': message}), 500

    except Exception as e:
        logger.error(f"Error processing Razorpay webhook: {e}", exc_info=True)
        return jsonify({'error': 'Webhook processing failed'}), 500


# ═══════════════════════════════════════════════════════════════════
# PAYMENT & SUBSCRIPTION API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/subscription', methods=['GET'])
@require_auth
def api_get_subscription():
    """Get user's current subscription and usage details"""
    try:
        from subscription_manager import get_user_subscription, get_usage_stats

        user_id = session.get('user_id')

        # Get subscription
        subscription, usage = get_user_subscription(user_id)

        if not subscription:
            return jsonify({'error': 'No subscription found'}), 404

        return jsonify({
            'subscription': subscription,
            'usage': usage
        }), 200

    except Exception as e:
        logger.error(f"Error fetching subscription: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch subscription'}), 500


@app.route('/api/subscription/plans', methods=['GET'])
def api_subscription_plans():
    """Get all available subscription plans"""
    try:
        from subscription_manager import PLANS

        # Filter out free_trial from public listing
        public_plans = {k: v for k, v in PLANS.items() if k != 'free_trial'}

        return jsonify({'plans': public_plans}), 200

    except Exception as e:
        logger.error(f"Error fetching plans: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch plans'}), 500


@app.route('/api/subscription/checkout', methods=['POST'])
@require_auth
def api_subscription_checkout():
    """Create a Razorpay subscription checkout session"""
    try:
        from razorpay_integration import create_subscription_checkout

        data = request.get_json() or {}

        # Validate plan type using schema
        checkout_data_input = {
            'plan_type': data.get('plan_type')
        }

        is_valid, result = validate_json(SubscriptionCheckoutSchema, checkout_data_input)
        if not is_valid:
            return jsonify({'error': 'Invalid plan type', 'details': result}), 400

        # Use validated data
        plan_type = result['plan_type']

        # Get user info
        user_id = session.get('user_id')
        user_ref = db.collection('users').document(user_id).get()
        user_data = user_ref.to_dict() if user_ref.exists else {}

        # Create checkout session
        checkout_data = create_subscription_checkout(
            user_id=user_id,
            plan_type=plan_type,
            user_name=user_data.get('name', ''),
            user_email=user_id,
            user_phone=user_data.get('phone', '')
        )

        if not checkout_data:
            return jsonify({'error': 'Failed to create checkout session'}), 500

        return jsonify(checkout_data), 200

    except Exception as e:
        logger.error(f"Error creating subscription checkout: {e}", exc_info=True)
        return jsonify({'error': 'Failed to create checkout'}), 500


@app.route('/api/subscription/verify', methods=['POST'])
@require_auth
def api_subscription_verify():
    """Verify Razorpay subscription payment"""
    try:
        from razorpay_integration import verify_subscription_payment
        from subscription_manager import upgrade_subscription

        data = request.get_json() or {}

        # Validate required fields
        razorpay_payment_id = data.get('razorpay_payment_id', '').strip()
        razorpay_subscription_id = data.get('razorpay_subscription_id', '').strip()
        razorpay_signature = data.get('razorpay_signature', '').strip()
        plan_type = data.get('plan_type', '').strip()

        # Basic validation
        if not all([razorpay_payment_id, razorpay_subscription_id, razorpay_signature, plan_type]):
            return jsonify({'error': 'Missing required payment verification fields'}), 400

        # Validate plan type using schema
        plan_validation = {'plan_type': plan_type}
        is_valid, result = validate_json(SubscriptionCheckoutSchema, plan_validation)
        if not is_valid:
            return jsonify({'error': 'Invalid plan type', 'details': result}), 400

        plan_type = result['plan_type']

        # Verify payment signature
        if not verify_subscription_payment(razorpay_payment_id, razorpay_subscription_id, razorpay_signature):
            return jsonify({'error': 'Payment verification failed'}), 400

        # Activate subscription
        user_id = session.get('user_id')
        success = upgrade_subscription(
            user_id=user_id,
            plan_type=plan_type,
            subscription_id=razorpay_subscription_id,
            transaction_data={
                'payment_id': razorpay_payment_id,
                'subscription_id': razorpay_subscription_id
            }
        )

        if success:
            logger.info(f"Subscription activated for {user_id}: {plan_type}")
            return jsonify({'message': 'Subscription activated successfully'}), 200
        else:
            return jsonify({'error': 'Failed to activate subscription'}), 500

    except Exception as e:
        logger.error(f"Error verifying subscription payment: {e}", exc_info=True)
        return jsonify({'error': 'Payment verification failed'}), 500


@app.route('/api/tokens/packages', methods=['GET'])
def api_token_packages():
    """Get all available token packages"""
    try:
        from subscription_manager import TOKEN_PACKAGES

        return jsonify({'packages': TOKEN_PACKAGES}), 200

    except Exception as e:
        logger.error(f"Error fetching token packages: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch packages'}), 500


@app.route('/api/tokens/checkout', methods=['POST'])
@require_auth
def api_tokens_checkout():
    """Create a Razorpay order for token purchase"""
    try:
        from razorpay_integration import create_token_purchase_order

        data = request.get_json() or {}

        # Validate package using schema
        token_data = {
            'package': data.get('package')
        }

        is_valid, result = validate_json(TokenPurchaseSchema, token_data)
        if not is_valid:
            return jsonify({'error': 'Invalid token package', 'details': result}), 400

        # Use validated data
        package = result['package']

        # Get user info
        user_id = session.get('user_id')
        user_ref = db.collection('users').document(user_id).get()
        user_data = user_ref.to_dict() if user_ref.exists else {}

        # Create order
        order_data = create_token_purchase_order(
            user_id=user_id,
            package=package,
            user_name=user_data.get('name', ''),
            user_email=user_id,
            user_phone=user_data.get('phone', '')
        )

        if not order_data:
            return jsonify({'error': 'Failed to create order'}), 500

        return jsonify(order_data), 200

    except Exception as e:
        logger.error(f"Error creating token checkout: {e}", exc_info=True)
        return jsonify({'error': 'Failed to create checkout'}), 500


@app.route('/api/tokens/verify', methods=['POST'])
@require_auth
def api_tokens_verify():
    """Verify Razorpay token purchase payment"""
    try:
        from razorpay_integration import verify_token_payment
        from subscription_manager import purchase_tokens

        data = request.get_json() or {}

        # Validate payment data using schema
        payment_data = {
            'razorpay_order_id': data.get('razorpay_order_id', '').strip(),
            'razorpay_payment_id': data.get('razorpay_payment_id', '').strip(),
            'razorpay_signature': data.get('razorpay_signature', '').strip()
        }

        is_valid, result = validate_json(PaymentVerificationSchema, payment_data)
        if not is_valid:
            return jsonify({'error': 'Invalid payment data', 'details': result}), 400

        # Validate package
        package_data = {'package': data.get('package')}
        is_valid_pkg, result_pkg = validate_json(TokenPurchaseSchema, package_data)
        if not is_valid_pkg:
            return jsonify({'error': 'Invalid package', 'details': result_pkg}), 400

        # Use validated data
        razorpay_order_id = result['razorpay_order_id']
        razorpay_payment_id = result['razorpay_payment_id']
        razorpay_signature = result['razorpay_signature']
        package = result_pkg['package']

        # Verify payment signature
        if not verify_token_payment(razorpay_order_id, razorpay_payment_id, razorpay_signature):
            return jsonify({'error': 'Payment verification failed'}), 400

        # Add tokens to user account
        user_id = session.get('user_id')
        success = purchase_tokens(
            user_id=user_id,
            package=package,
            payment_id=razorpay_payment_id,
            transaction_data={
                'order_id': razorpay_order_id,
                'payment_id': razorpay_payment_id
            }
        )

        if success:
            logger.info(f"Token purchase completed for {user_id}: {package}")
            return jsonify({'message': 'Tokens added successfully'}), 200
        else:
            return jsonify({'error': 'Failed to add tokens'}), 500

    except Exception as e:
        logger.error(f"Error verifying token payment: {e}", exc_info=True)
        return jsonify({'error': 'Payment verification failed'}), 500


@app.route('/api/subscription/cancel', methods=['POST'])
@require_auth
def api_subscription_cancel():
    """Cancel user's subscription"""
    try:
        from subscription_manager import cancel_subscription

        data = request.get_json() or {}

        # Validate optional cancellation feedback
        cancel_data = {
            'reason': data.get('reason', ''),
            'feedback': data.get('feedback', '')
        }

        is_valid, result = validate_json(SubscriptionCancelSchema, cancel_data)
        if not is_valid:
            return jsonify({'error': 'Invalid cancellation data', 'details': result}), 400

        # Log cancellation reason if provided
        if result.get('reason'):
            logger.info(f"Subscription cancellation reason: {result['reason']}")

        user_id = session.get('user_id')
        success = cancel_subscription(user_id)

        if success:
            logger.info(f"Subscription cancelled for {user_id}")
            return jsonify({'message': 'Subscription cancelled successfully'}), 200
        else:
            return jsonify({'error': 'Failed to cancel subscription'}), 500

    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}", exc_info=True)
        return jsonify({'error': 'Failed to cancel subscription'}), 500


# ═══════════════════════════════════════════════════════════════════
# PAYMENT & SUBSCRIPTION WEB PAGES
# ═══════════════════════════════════════════════════════════════════

@app.route('/pricing')
def pricing():
    """Display pricing and subscription plans page"""
    try:
        from subscription_manager import get_user_subscription

        # Get current subscription if user is logged in
        current_subscription = None
        if session.get('user_id'):
            subscription, _ = get_user_subscription(session['user_id'])
            current_subscription = subscription

        return render_template('pricing.html', current_subscription=current_subscription)

    except Exception as e:
        logger.error(f"Error loading pricing page: {e}", exc_info=True)
        return render_template('pricing.html', current_subscription=None)


@app.route('/checkout')
def checkout():
    """Display checkout page for subscription or token purchase"""
    # Query parameters: plan, package, type (subscription/tokens)
    return render_template('checkout.html')


@app.route('/subscription-dashboard')
@require_auth
def subscription_dashboard():
    """Display user's subscription dashboard with usage stats"""
    return render_template('subscription_dashboard.html')


@app.route('/test-razorpay')
def test_razorpay():
    """Display Razorpay configuration test page"""
    return render_template('test_razorpay.html')


# ═══════════════════════════════════════════════════════════════════
# TEST API ENDPOINTS (for debugging)
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/test/razorpay-config', methods=['GET'])
def test_razorpay_config():
    """Check if Razorpay environment variables are configured"""
    try:
        import os

        config = {
            'RAZORPAY_KEY_ID': bool(os.environ.get('RAZORPAY_KEY_ID')),
            'RAZORPAY_KEY_SECRET': bool(os.environ.get('RAZORPAY_KEY_SECRET')),
            'RAZORPAY_WEBHOOK_SECRET': bool(os.environ.get('RAZORPAY_WEBHOOK_SECRET')),
            'RAZORPAY_PLAN_SOLO': bool(os.environ.get('RAZORPAY_PLAN_SOLO')),
            'RAZORPAY_PLAN_TEAM_5': bool(os.environ.get('RAZORPAY_PLAN_TEAM_5')),
            'RAZORPAY_PLAN_TEAM_10': bool(os.environ.get('RAZORPAY_PLAN_TEAM_10')),
            'RAZORPAY_PLAN_INSTITUTE_15': bool(os.environ.get('RAZORPAY_PLAN_INSTITUTE_15')),
            'RAZORPAY_PLAN_INSTITUTE_20': bool(os.environ.get('RAZORPAY_PLAN_INSTITUTE_20')),
        }

        # Check if key is test mode
        key_id = os.environ.get('RAZORPAY_KEY_ID', '')
        if key_id and not key_id.startswith('rzp_test_'):
            config['WARNING'] = 'Not using test mode key (should start with rzp_test_)'

        return jsonify(config), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/test/razorpay-connection', methods=['GET'])
def test_razorpay_connection():
    """Test Razorpay API connection"""
    try:
        from razorpay_integration import razorpay_client

        if not razorpay_client:
            return jsonify({
                'success': False,
                'error': 'Razorpay client not initialized. Check your environment variables.'
            }), 500

        # Try to fetch a payment (will fail but confirms API is accessible)
        try:
            # This will throw an error but confirms the API key works
            razorpay_client.payment.fetch('pay_test123')
        except Exception as e:
            # If we get a "Payment not found" error, that means API connection works
            if 'not found' in str(e).lower() or 'does not exist' in str(e).lower():
                return jsonify({
                    'success': True,
                    'message': 'Razorpay API connection successful'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': f'API Error: {str(e)}'
                }), 500

        return jsonify({
            'success': True,
            'message': 'Razorpay API connection successful'
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ═══════════════════════════════════════════════════════════════════
# BLOG SYSTEM
# ═══════════════════════════════════════════════════════════════════

@app.route('/blog')
def blog_list():
    """Display list of published blog posts"""
    try:
        # Get published blog posts
        # Note: Sorting is done in Python to avoid needing a composite index
        posts_ref = db.collection('blog_posts').where('status', '==', 'published').limit(100)
        posts_docs = posts_ref.stream()

        posts = []
        for doc in posts_docs:
            post_data = doc.to_dict()
            post_data['id'] = doc.id
            # Format the published_at date for display
            if post_data.get('published_at'):
                pub_date = post_data['published_at']
                # Handle both datetime objects and ISO strings
                if isinstance(pub_date, str):
                    try:
                        pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                        post_data['published_at_datetime'] = pub_date
                    except:
                        pub_date = None
                        post_data['published_at_datetime'] = datetime.min
                else:
                    post_data['published_at_datetime'] = pub_date if pub_date else datetime.min

                if pub_date:
                    post_data['published_at_formatted'] = pub_date.strftime('%B %d, %Y')
                else:
                    post_data['published_at_formatted'] = 'Unknown'
            else:
                post_data['published_at_formatted'] = 'Unknown'
                post_data['published_at_datetime'] = datetime.min
            posts.append(post_data)

        # Sort by publish date (newest first) in Python
        posts.sort(key=lambda x: x.get('published_at_datetime', datetime.min), reverse=True)

        # Limit to 50 posts
        posts = posts[:50]

        return render_template('blog_list.html', posts=posts)
    except Exception as e:
        logger.error(f"Error loading blog list: {e}", exc_info=True)
        flash('Error loading blog posts', 'error')
        return render_template('blog_list.html', posts=[])


@app.route('/blog/<post_id>')
def blog_post(post_id):
    """Display individual blog post"""
    try:
        post_ref = db.collection('blog_posts').document(post_id)
        post_doc = post_ref.get()

        if not post_doc.exists:
            flash('Blog post not found', 'error')
            return redirect(url_for('blog_list'))

        post = post_doc.to_dict()
        post['id'] = post_doc.id

        # Only show published posts (unless user is super admin)
        if post.get('status') != 'published':
            user_email = session.get('user_id')
            if not user_email:
                flash('This post is not published yet', 'error')
                return redirect(url_for('blog_list'))

            # Check if user is super admin
            user_ref = db.collection('users').document(user_email).get()
            if not user_ref.exists or not user_ref.to_dict().get('is_super_admin'):
                flash('This post is not published yet', 'error')
                return redirect(url_for('blog_list'))

        # Format the published date
        if post.get('published_at'):
            pub_date = post['published_at']
            if isinstance(pub_date, str):
                try:
                    pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                except:
                    pub_date = None
            if pub_date:
                post['published_at_formatted'] = pub_date.strftime('%B %d, %Y')
            else:
                post['published_at_formatted'] = 'Unknown'

        # Increment view count
        post_ref.update({'views': Increment(1)})

        return render_template('blog_post.html', post=post)
    except Exception as e:
        logger.error(f"Error loading blog post {post_id}: {e}")
        flash('Error loading blog post', 'error')
        return redirect(url_for('blog_list'))


@app.route('/blog/post/<slug>')
def blog_detail(slug):
    """Display individual blog post by slug"""
    try:
        # Query for post with matching slug
        posts = db.collection('blog_posts').where('slug', '==', slug).limit(1).stream()
        posts_list = list(posts)

        if not posts_list:
            flash('Blog post not found', 'error')
            return redirect(url_for('blog_list'))

        post_doc = posts_list[0]
        post = post_doc.to_dict()
        post['id'] = post_doc.id

        # Only show published posts (unless user is super admin)
        if post.get('status') != 'published':
            user_email = session.get('user_id')
            if not user_email:
                flash('This post is not published yet', 'error')
                return redirect(url_for('blog_list'))

            # Check if user is super admin
            user_ref = db.collection('users').document(user_email).get()
            if not user_ref.exists or not user_ref.to_dict().get('is_super_admin'):
                flash('This post is not published yet', 'error')
                return redirect(url_for('blog_list'))

        # Format the published date
        if post.get('published_at'):
            pub_date = post['published_at']
            if isinstance(pub_date, str):
                try:
                    pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                except:
                    pub_date = None
            if pub_date:
                post['published_at_formatted'] = pub_date.strftime('%B %d, %Y')
            else:
                post['published_at_formatted'] = 'Unknown'

        # Increment view count
        post_ref = db.collection('blog_posts').document(post['id'])
        post_ref.update({'views': Increment(1)})

        return render_template('blog_post.html', post=post)
    except Exception as e:
        logger.error(f"Error loading blog post by slug {slug}: {e}")
        flash('Error loading blog post', 'error')
        return redirect(url_for('blog_list'))


@app.route('/admin/blog')
@super_admin_required()
def blog_admin():
    """Admin interface to manage blog posts (super admin only)"""

    try:
        # Get all blog posts (published and draft)
        # Note: Sorting is done in Python to avoid needing an index
        posts_ref = db.collection('blog_posts').limit(200)
        posts_docs = posts_ref.stream()

        posts = []
        for doc in posts_docs:
            post_data = doc.to_dict()
            post_data['id'] = doc.id
            # Handle created_at date
            if post_data.get('created_at'):
                created = post_data['created_at']
                if isinstance(created, str):
                    try:
                        created = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        post_data['created_at_datetime'] = created
                    except:
                        created = None
                        post_data['created_at_datetime'] = datetime.min
                else:
                    post_data['created_at_datetime'] = created if created else datetime.min

                if created:
                    post_data['created_at_formatted'] = created.strftime('%B %d, %Y %I:%M %p')
                else:
                    post_data['created_at_formatted'] = 'Unknown'
            else:
                post_data['created_at_formatted'] = 'Unknown'
                post_data['created_at_datetime'] = datetime.min

            # Handle published_at date
            if post_data.get('published_at'):
                pub_date = post_data['published_at']
                if isinstance(pub_date, str):
                    try:
                        pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    except:
                        pub_date = None
                if pub_date:
                    post_data['published_at_formatted'] = pub_date.strftime('%B %d, %Y')
                else:
                    post_data['published_at_formatted'] = 'Unknown'
            else:
                post_data['published_at_formatted'] = 'Unknown'
            posts.append(post_data)

        # Sort by created_at (newest first) in Python
        posts.sort(key=lambda x: x.get('created_at_datetime', datetime.min), reverse=True)

        return render_template('blog_admin.html', posts=posts)
    except Exception as e:
        logger.error(f"Error loading blog admin: {e}")
        flash('Error loading blog admin', 'error')
        return render_template('blog_admin.html', posts=[])


@app.route('/admin/blog/new', methods=['GET', 'POST'])
@super_admin_required()
def blog_create():
    """Create new blog post (super admin only)"""
    user_email = session.get('user_id')

    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            slug = request.form.get('slug', '').strip().lower().replace(' ', '-')
            content = request.form.get('content', '').strip()
            excerpt = request.form.get('excerpt', '').strip()
            author = request.form.get('author', user_email).strip()
            tags = request.form.get('tags', '').strip()
            status = request.form.get('status', 'draft')
            meta_description = request.form.get('meta_description', '').strip()

            if not title or not content:
                flash('Title and content are required', 'error')
                return render_template('blog_edit.html', post=None, editing=False)

            # Generate slug from title if not provided
            if not slug:
                slug = title.lower().replace(' ', '-').replace(',', '').replace('.', '')

            # Check if slug already exists
            existing = db.collection('blog_posts').where('slug', '==', slug).limit(1).stream()
            if len(list(existing)) > 0:
                flash(f'A post with slug "{slug}" already exists. Please choose a different slug.', 'error')
                return render_template('blog_edit.html', post={'title': title, 'content': content, 'excerpt': excerpt, 'author': author, 'tags': tags, 'slug': slug, 'meta_description': meta_description}, editing=False)

            # Convert tags to list
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []

            post_data = {
                'title': title,
                'slug': slug,
                'content': content,
                'excerpt': excerpt or content[:200] + '...',
                'author': author,
                'tags': tags_list,
                'status': status,
                'meta_description': meta_description or excerpt or content[:160],
                'created_at': SERVER_TIMESTAMP,
                'updated_at': SERVER_TIMESTAMP,
                'views': 0
            }

            if status == 'published':
                post_data['published_at'] = datetime.now()

            # Create the post
            doc_ref = db.collection('blog_posts').add(post_data)
            flash('Blog post created successfully!', 'success')
            return redirect(url_for('blog_admin'))

        except Exception as e:
            logger.error(f"Error creating blog post: {e}")
            flash(f'Error creating blog post: {str(e)}', 'error')

    return render_template('blog_edit.html', post=None, editing=False)


@app.route('/admin/blog/<post_id>/edit', methods=['GET', 'POST'])
@super_admin_required()
def blog_edit(post_id):
    """Edit existing blog post (super admin only)"""
    user_email = session.get('user_id')

    try:
        post_ref = db.collection('blog_posts').document(post_id)
        post_doc = post_ref.get()

        if not post_doc.exists:
            flash('Blog post not found', 'error')
            return redirect(url_for('blog_admin'))

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            slug = request.form.get('slug', '').strip().lower().replace(' ', '-')
            content = request.form.get('content', '').strip()
            excerpt = request.form.get('excerpt', '').strip()
            author = request.form.get('author', user_email).strip()
            tags = request.form.get('tags', '').strip()
            status = request.form.get('status', 'draft')
            meta_description = request.form.get('meta_description', '').strip()

            if not title or not content:
                flash('Title and content are required', 'error')
                post = post_doc.to_dict()
                post['id'] = post_id
                return render_template('blog_edit.html', post=post, editing=True)

            # Check if slug changed and conflicts
            existing_slug = post_doc.to_dict().get('slug')
            if slug != existing_slug:
                existing = db.collection('blog_posts').where('slug', '==', slug).limit(1).stream()
                if len(list(existing)) > 0:
                    flash(f'A post with slug "{slug}" already exists. Please choose a different slug.', 'error')
                    post = post_doc.to_dict()
                    post['id'] = post_id
                    return render_template('blog_edit.html', post=post, editing=True)

            # Convert tags to list
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []

            update_data = {
                'title': title,
                'slug': slug,
                'content': content,
                'excerpt': excerpt or content[:200] + '...',
                'author': author,
                'tags': tags_list,
                'status': status,
                'meta_description': meta_description or excerpt or content[:160],
                'updated_at': SERVER_TIMESTAMP
            }

            # Update published_at if changing from draft to published
            old_status = post_doc.to_dict().get('status')
            if status == 'published' and old_status != 'published':
                update_data['published_at'] = datetime.now()

            post_ref.update(update_data)
            flash('Blog post updated successfully!', 'success')
            return redirect(url_for('blog_admin'))

        # GET request - show edit form
        post = post_doc.to_dict()
        post['id'] = post_id
        # Convert tags list back to comma-separated string
        if post.get('tags'):
            post['tags_string'] = ', '.join(post['tags'])
        else:
            post['tags_string'] = ''

        return render_template('blog_edit.html', post=post, editing=True)

    except Exception as e:
        logger.error(f"Error editing blog post {post_id}: {e}")
        flash(f'Error editing blog post: {str(e)}', 'error')
        return redirect(url_for('blog_admin'))


@app.route('/admin/blog/<post_id>/delete', methods=['POST'])
@super_admin_required()
def blog_delete(post_id):
    """Delete blog post (super admin only)"""

    try:
        db.collection('blog_posts').document(post_id).delete()
        flash('Blog post deleted successfully!', 'success')
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Error deleting blog post {post_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/blog/seed-posts', methods=['GET', 'POST'])
@super_admin_required()
def seed_blog_posts():
    """Seed the database with initial blog posts (super admin only)"""

    try:
        # Check if posts already exist
        existing_posts_query = db.collection('blog_posts').where('status', '==', 'published').limit(1)
        existing_posts = list(existing_posts_query.stream())

        if len(existing_posts) > 0:
            flash('Blog posts already exist. Use the blog admin interface to manage them.', 'warning')
            return redirect(url_for('blog_admin'))

        # Define initial blog posts
        blog_posts = [
            {
                'title': 'Clinical Reasoning Framework for Physiotherapists',
                'slug': 'clinical-reasoning-framework',
                'content': '''
# Clinical Reasoning Framework for Physiotherapists

Clinical reasoning is the foundation of effective physiotherapy practice. It's the cognitive process that enables physiotherapists to make sound clinical decisions based on patient assessment, evidence, and clinical experience.

## What is Clinical Reasoning?

Clinical reasoning in physiotherapy involves:
- Gathering and analyzing patient data
- Identifying patterns and relationships
- Formulating hypotheses about the patient's condition
- Making evidence-based treatment decisions
- Evaluating outcomes and adjusting interventions

## Key Components

### 1. Subjective Assessment
The subjective examination provides crucial insights into the patient's perspective, including their chief complaint, history, and functional limitations.

### 2. Objective Assessment
Physical examination findings, measurements, and functional tests provide objective data to support clinical hypotheses.

### 3. Clinical Hypothesis Generation
Based on subjective and objective findings, physiotherapists generate hypotheses about:
- Pathophysiology
- Contributing factors
- Prognosis
- Treatment approaches

### 4. Treatment Planning
Evidence-based interventions are selected based on:
- Clinical reasoning
- Patient preferences
- Best available evidence
- Clinical expertise

## The PRISM Approach

PhysiologicPRISM supports clinical reasoning through:
- **Structured documentation** that guides systematic assessment
- **AI-assisted suggestions** based on clinical patterns
- **Evidence integration** linking assessment to treatment
- **Outcome tracking** to evaluate clinical decisions

## Conclusion

Strong clinical reasoning skills develop over time through practice, reflection, and continuous learning. PhysiologicPRISM is designed to support this process by providing structure and evidence-based guidance.
                ''',
                'excerpt': 'Learn about the clinical reasoning process in physiotherapy and how structured documentation supports better clinical decision-making.',
                'author': 'Dr. Sandeep Rao',
                'tags': ['Clinical Reasoning', 'Evidence-Based Practice', 'Assessment'],
                'status': 'published',
                'meta_description': 'Clinical reasoning framework for physiotherapists - learn how to make better clinical decisions through structured assessment and evidence-based practice.',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'published_at': datetime.now(),
                'views': 0
            },
            {
                'title': 'Comprehensive History Taking in Physiotherapy',
                'slug': 'history-taking-physiotherapy',
                'content': '''
# Comprehensive History Taking in Physiotherapy

A thorough patient history is the cornerstone of effective physiotherapy assessment and treatment planning.

## Why History Taking Matters

The subjective examination often provides 80% of the information needed for diagnosis. It helps physiotherapists:
- Understand the patient's presenting complaint
- Identify red flags and contraindications
- Establish treatment goals
- Build therapeutic rapport

## Key Elements of History Taking

### 1. Chief Complaint
- What brought the patient to physiotherapy?
- Current symptoms and their impact on function
- Patient's primary concerns and goals

### 2. History of Present Complaint
- Onset and mechanism of injury
- Progression of symptoms
- Aggravating and easing factors
- Previous treatments and their outcomes
- 24-hour symptom behavior

### 3. Past Medical History
- Previous injuries or surgeries
- Chronic conditions
- Medications
- Relevant family history

### 4. Functional Impact
- Activities of daily living
- Work-related tasks
- Recreational activities
- Sleep quality

### 5. Red Flags
- Serious pathology indicators
- Systemic symptoms
- Progressive neurological deficits
- Contraindications to treatment

## Documentation Best Practices

PhysiologicPRISM structures history taking to ensure:
- **Completeness**: No critical information is missed
- **Consistency**: Standardized approach across patients
- **Efficiency**: AI-assisted documentation reduces time
- **Evidence**: Digital records support clinical reasoning

## Conclusion

Mastering history taking is essential for every physiotherapist. Structured documentation tools like PhysiologicPRISM help ensure comprehensive, consistent patient assessment.
                ''',
                'excerpt': 'Master the art of patient history taking with this comprehensive guide for physiotherapists.',
                'author': 'Dr. Sandeep Rao',
                'tags': ['Assessment', 'Patient History', 'Documentation'],
                'status': 'published',
                'meta_description': 'Learn comprehensive history taking techniques for physiotherapy practice - structured approach to patient assessment and documentation.',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'published_at': datetime.now(),
                'views': 0
            },
            {
                'title': 'Objective Assessment Guide for Physiotherapists',
                'slug': 'objective-assessment-guide',
                'content': '''
# Objective Assessment Guide for Physiotherapists

The objective examination provides measurable, reproducible data to support clinical decision-making and track patient progress.

## Components of Objective Assessment

### 1. Observation
- Posture and alignment
- Gait analysis
- Movement patterns
- Muscle atrophy or swelling
- Skin changes

### 2. Palpation
- Tissue texture and temperature
- Muscle tone and trigger points
- Joint alignment
- Areas of tenderness

### 3. Range of Motion (ROM)
- Active and passive ROM
- End-feel assessment
- Painful arc identification
- Comparison with contralateral side

### 4. Muscle Testing
- Manual muscle testing (MMT)
- Functional strength assessment
- Endurance testing
- Movement quality

### 5. Special Tests
- Joint stability tests
- Neurological examination
- Functional tests
- Outcome measures

### 6. Functional Assessment
- Activities of daily living
- Work-related tasks
- Sport-specific movements
- Balance and coordination

## Documentation and Measurement

### Standardized Outcome Measures
Using validated outcome measures provides:
- Objective baseline data
- Progress tracking
- Treatment effectiveness evaluation
- Evidence for decision-making

### Digital Documentation
PhysiologicPRISM streamlines objective assessment by:
- **Structured templates** for consistency
- **Automated calculations** for scores and measurements
- **Visual documentation** with diagrams
- **Trend analysis** over time

## Clinical Integration

Objective findings should be:
1. Compared with subjective reports
2. Analyzed for patterns and relationships
3. Used to confirm or refute clinical hypotheses
4. Integrated into treatment planning

## Best Practices

- Use standardized, validated tests
- Document measurements accurately
- Compare with normative data
- Track changes over time
- Integrate with subjective findings

## Conclusion

Systematic objective assessment provides the evidence base for clinical reasoning. PhysiologicPRISM supports comprehensive, efficient documentation of objective findings.
                ''',
                'excerpt': 'A systematic guide to objective assessment in physiotherapy practice with evidence-based measurement tools.',
                'author': 'Dr. Sandeep Rao',
                'tags': ['Objective Assessment', 'Clinical Measurement', 'Outcome Measures'],
                'status': 'published',
                'meta_description': 'Comprehensive guide to objective assessment for physiotherapists - learn systematic examination techniques and outcome measures.',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'published_at': datetime.now(),
                'views': 0
            }
        ]

        # Create the three blog posts
        posts_created = 0
        for post_data in blog_posts:
            try:
                # Check if this specific post already exists by slug
                existing = db.collection('blog_posts').where('slug', '==', post_data['slug']).limit(1).stream()
                if len(list(existing)) > 0:
                    logger.info(f"Post {post_data['slug']} already exists, skipping")
                    continue

                # Add the post
                doc_ref = db.collection('blog_posts').add(post_data)
                posts_created += 1
                logger.info(f"Created blog post: {post_data['title']} (ID: {doc_ref[1].id})")
            except Exception as post_error:
                logger.error(f"Error creating post {post_data.get('title', 'unknown')}: {post_error}")
                continue

        if posts_created > 0:
            flash(f'Successfully created {posts_created} blog post(s)!', 'success')
        else:
            flash('No new posts were created.', 'info')

        return redirect(url_for('blog_list'))

    except Exception as e:
        logger.error(f"Error seeding blog posts: {e}", exc_info=True)
        flash(f'Error seeding blog posts: {str(e)}', 'error')
        return redirect(url_for('blog_admin'))


# ═══════════════════════════════════════════════════════════════════
# FOLLOW-UP REMINDER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/patient/<patient_id>/set_next_followup', methods=['POST'])
@login_required()
def set_next_followup(patient_id):
    """Set next follow-up date for a patient"""
    try:
        data = request.get_json() or {}
        next_followup_date = data.get('next_followup_date')

        if not next_followup_date:
            return jsonify({'ok': False, 'error': 'Missing next_followup_date'}), 400

        # Verify patient exists and user has access
        patient_ref = db.collection('patients').document(patient_id)
        patient_doc = patient_ref.get()

        if not patient_doc.exists:
            return jsonify({'ok': False, 'error': 'Patient not found'}), 404

        patient = patient_doc.to_dict()
        user_id = session.get('user_id')

        # Access control
        if session.get('is_admin') == 0 and patient.get('physio_id') != user_id:
            return jsonify({'ok': False, 'error': 'Access denied'}), 403

        # Update patient record with next follow-up date
        patient_ref.update({
            'next_followup_date': next_followup_date,
            'followup_notified': False,
            'followup_notification_sent_at': None,
            'updated_at': SERVER_TIMESTAMP
        })

        log_action(user_id, 'Set Follow-up', f"Set next follow-up for {patient_id} on {next_followup_date}")

        return jsonify({
            'ok': True,
            'message': 'Next follow-up date set successfully',
            'next_followup_date': next_followup_date
        }), 200

    except Exception as e:
        logger.error(f"Error setting next follow-up: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/patient/<patient_id>/mark_followup_notified', methods=['POST'])
@login_required()
def mark_followup_notified(patient_id):
    """Mark that patient has been notified about their follow-up"""
    try:
        # Verify patient exists and user has access
        patient_ref = db.collection('patients').document(patient_id)
        patient_doc = patient_ref.get()

        if not patient_doc.exists:
            return jsonify({'ok': False, 'error': 'Patient not found'}), 404

        patient = patient_doc.to_dict()
        user_id = session.get('user_id')

        # Access control
        if session.get('is_admin') == 0 and patient.get('physio_id') != user_id:
            return jsonify({'ok': False, 'error': 'Access denied'}), 403

        # Update patient record
        patient_ref.update({
            'followup_notified': True,
            'followup_notification_sent_at': SERVER_TIMESTAMP,
            'followup_notified_by': user_id,
            'updated_at': SERVER_TIMESTAMP
        })

        # Create confirmation notification
        from notification_service import notify_followup_confirmation

        patient_name = patient.get('name', 'Patient')
        followup_date = patient.get('next_followup_date', 'upcoming date')

        notify_followup_confirmation(user_id, patient_name, patient_id, followup_date)

        log_action(user_id, 'Patient Notified', f"Marked {patient_id} as notified for follow-up")

        return jsonify({
            'ok': True,
            'message': 'Patient marked as notified'
        }), 200

    except Exception as e:
        logger.error(f"Error marking follow-up notified: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/upcoming_followups', methods=['GET'])
@login_required()
def get_upcoming_followups():
    """Get all patients with upcoming follow-ups for the logged-in user"""
    try:
        user_id = session.get('user_id')
        days_ahead = int(request.args.get('days', 7))  # Default to 7 days

        # Get all patients for this user
        if session.get('is_admin') == 1:
            query = db.collection('patients').where('institute', '==', session.get('institute'))
        else:
            query = db.collection('patients').where('physio_id', '==', user_id)

        patients = query.stream()

        upcoming = []
        today = datetime.now().date()
        cutoff_date = today + timedelta(days=days_ahead)

        for doc in patients:
            patient = doc.to_dict()
            patient['patient_id'] = doc.id

            next_followup = patient.get('next_followup_date')
            if next_followup:
                # Parse the date (assuming format YYYY-MM-DD)
                try:
                    followup_date = datetime.strptime(next_followup, '%Y-%m-%d').date()

                    # Check if within the range
                    if today <= followup_date <= cutoff_date:
                        days_until = (followup_date - today).days

                        upcoming.append({
                            'patient_id': patient['patient_id'],
                            'patient_name': patient.get('name', 'Unknown'),
                            'contact': patient.get('contact', ''),
                            'next_followup_date': next_followup,
                            'days_until': days_until,
                            'followup_notified': patient.get('followup_notified', False),
                            'notification_sent_at': patient.get('followup_notification_sent_at'),
                            'is_today': days_until == 0,
                            'is_overdue': followup_date < today
                        })
                except ValueError:
                    # Invalid date format, skip
                    continue

        # Sort by date (soonest first)
        upcoming.sort(key=lambda x: x['days_until'])

        return jsonify({
            'ok': True,
            'upcoming_followups': upcoming,
            'count': len(upcoming)
        }), 200

    except Exception as e:
        logger.error(f"Error getting upcoming follow-ups: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/check_followup_reminders', methods=['POST'])
@login_required()
def check_followup_reminders():
    """
    Utility endpoint to check for upcoming follow-ups and create notifications
    Can be called manually or via scheduled task
    """
    try:
        # Only super admin or scheduled task can trigger this
        if session.get('is_super_admin') != 1:
            return jsonify({'ok': False, 'error': 'Unauthorized'}), 403

        from notification_service import notify_upcoming_followup

        # Get all patients with upcoming follow-ups (next 7 days)
        today = datetime.now().date()
        reminder_days = [0, 1, 3, 7]  # Send reminders 7 days, 3 days, 1 day, and on the day

        notifications_sent = 0

        # Query all patients
        all_patients = db.collection('patients').stream()

        for doc in all_patients:
            patient = doc.to_dict()
            patient_id = doc.id

            next_followup = patient.get('next_followup_date')
            if not next_followup:
                continue

            try:
                followup_date = datetime.strptime(next_followup, '%Y-%m-%d').date()
                days_until = (followup_date - today).days

                # Check if we should send a reminder
                if days_until in reminder_days and not patient.get('followup_notified', False):
                    # Get the physio who created this patient
                    physio_id = patient.get('physio_id')
                    if physio_id:
                        patient_name = patient.get('name', 'Patient')

                        notify_upcoming_followup(
                            physio_id,
                            patient_name,
                            patient_id,
                            next_followup,
                            days_until
                        )

                        notifications_sent += 1

            except ValueError:
                # Invalid date format
                continue

        return jsonify({
            'ok': True,
            'message': f'Checked follow-up reminders',
            'notifications_sent': notifications_sent
        }), 200

    except Exception as e:
        logger.error(f"Error checking follow-up reminders: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# DRAFT AUTO-SAVE SYSTEM
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/draft/save', methods=['POST'])
@login_required()
def save_draft():
    """
    Auto-save form draft data
    Stores partial form data so users can resume later
    """
    try:
        data = request.get_json() or {}

        # Validate draft data
        draft_data = {
            'patient_id': data.get('patient_id'),
            'section': data.get('form_type'),
            'data': data.get('form_data', {})
        }

        is_valid, result = validate_json(DraftSaveSchema, draft_data)
        if not is_valid:
            return jsonify({'ok': False, 'error': 'Validation failed', 'details': result}), 400

        form_type = result['section']
        patient_id = result['patient_id']
        form_data = result['data']

        if not form_type or not patient_id:
            return jsonify({'ok': False, 'error': 'Missing form_type or patient_id'}), 400

        user_id = session.get('user_id')

        # For new patient forms, skip patient verification since patient doesn't exist yet
        if patient_id != 'new_patient' and form_type != 'add_patient':
            # Verify user has access to this patient
            patient_ref = db.collection('patients').document(patient_id)
            patient_doc = patient_ref.get()

            if not patient_doc.exists:
                return jsonify({'ok': False, 'error': 'Patient not found'}), 404

            patient = patient_doc.to_dict()

            # Access control
            if session.get('is_admin') == 0 and patient.get('physio_id') != user_id:
                return jsonify({'ok': False, 'error': 'Access denied'}), 403

        # Create unique draft ID: user_id + patient_id + form_type
        draft_id = f"{user_id}_{patient_id}_{form_type}"

        # Save or update draft
        draft_ref = db.collection('form_drafts').document(draft_id)
        draft_ref.set({
            'user_id': user_id,
            'patient_id': patient_id,
            'form_type': form_type,
            'form_data': form_data,
            'updated_at': SERVER_TIMESTAMP,
            'created_at': SERVER_TIMESTAMP if not draft_ref.get().exists else draft_ref.get().to_dict().get('created_at')
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


@app.route('/api/draft/get/<patient_id>/<form_type>', methods=['GET'])
@login_required()
def get_draft(patient_id, form_type):
    """
    Retrieve saved draft for a form
    """
    try:
        user_id = session.get('user_id')

        # For new patient forms, skip patient verification since patient doesn't exist yet
        if patient_id != 'new_patient' and form_type != 'add_patient':
            # Verify user has access to this patient
            patient_ref = db.collection('patients').document(patient_id)
            patient_doc = patient_ref.get()

            if not patient_doc.exists:
                return jsonify({'ok': False, 'error': 'Patient not found'}), 404

            patient = patient_doc.to_dict()

            # Access control
            if session.get('is_admin') == 0 and patient.get('physio_id') != user_id:
                return jsonify({'ok': False, 'error': 'Access denied'}), 403

        # Get draft
        draft_id = f"{user_id}_{patient_id}_{form_type}"
        draft_ref = db.collection('form_drafts').document(draft_id)
        draft_doc = draft_ref.get()

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


@app.route('/api/draft/delete/<patient_id>/<form_type>', methods=['DELETE'])
@login_required()
def delete_draft(patient_id, form_type):
    """
    Delete a saved draft (after successful form submission)
    """
    try:
        user_id = session.get('user_id')

        # Delete draft
        draft_id = f"{user_id}_{patient_id}_{form_type}"
        draft_ref = db.collection('form_drafts').document(draft_id)
        draft_ref.delete()

        logger.info(f"Draft deleted: {draft_id}")

        return jsonify({
            'ok': True,
            'message': 'Draft deleted'
        }), 200

    except Exception as e:
        logger.error(f"Error deleting draft: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/draft/cleanup', methods=['POST'])
@login_required()
def cleanup_old_drafts():
    """
    Clean up drafts older than 30 days (super admin only)
    """
    try:
        if session.get('is_super_admin') != 1:
            return jsonify({'ok': False, 'error': 'Unauthorized'}), 403

        cutoff_date = datetime.now() - timedelta(days=30)
        # Convert to ISO format string for Cosmos DB query
        cutoff_date_iso = cutoff_date.isoformat()

        # Query old drafts
        old_drafts = db.collection('form_drafts').where('updated_at', '<', cutoff_date_iso).stream()

        deleted_count = 0
        for draft_doc in old_drafts:
            draft_doc.reference.delete()
            deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} old drafts")

        return jsonify({
            'ok': True,
            'message': f'Deleted {deleted_count} old drafts',
            'deleted_count': deleted_count
        }), 200

    except Exception as e:
        logger.error(f"Error cleaning up drafts: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════

@app.route("/healthz")
def healthz():
    """
    Basic health check endpoint for load balancers.
    Returns 200 if application is running.
    """
    return jsonify({"status": "ok"}), 200


@app.route("/api/health")
def health_check():
    """
    Comprehensive health check endpoint for monitoring.

    Checks the health of all critical systems:
    - Firestore database connection
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
                "firestore": "ok" | "error",
                "redis": "ok" | "degraded" | "error",
                "openai": "ok" | "disabled" | "error"
            }
        }
    """
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'checks': {}
    }

    # Check Firestore connection
    try:
        # Perform a simple read operation to verify Firestore is accessible
        # Using limit(1) to minimize data transfer
        test_query = db.collection('users').limit(1).get()
        health_status['checks']['firestore'] = 'ok'
        logger.debug("Health check: Firestore OK")
    except Exception as e:
        health_status['checks']['firestore'] = 'error'
        health_status['status'] = 'unhealthy'
        logger.error(f"Health check: Firestore failed - {str(e)}")

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

    # Check OpenAI availability
    if not HIPAA_COMPLIANT_MODE and client:
        try:
            # Just check if client exists, don't make actual API call to avoid costs
            health_status['checks']['openai'] = 'ok'
            logger.debug("Health check: OpenAI OK")
        except Exception as e:
            health_status['checks']['openai'] = 'error'
            # OpenAI failure is not critical, don't mark overall status as unhealthy
            logger.warning(f"Health check: OpenAI check failed - {str(e)}")
    else:
        health_status['checks']['openai'] = 'disabled'
        logger.debug("Health check: OpenAI disabled (HIPAA mode or not initialized)")

    # Determine HTTP status code
    status_code = 200 if health_status['status'] == 'healthy' else 503

    return jsonify(health_status), status_code


# ═══════════════════════════════════════════════════════════════════
# SENTRY TEST ENDPOINTS (FOR DEVELOPMENT/TESTING ONLY)
# ═══════════════════════════════════════════════════════════════════

@app.route('/sentry-debug')
def sentry_debug():
    """
    Test endpoint to verify Sentry error tracking.
    Only works in development environment for security.

    Visit: http://localhost:8080/sentry-debug
    Expected: Error captured in Sentry dashboard within 1 minute
    """
    if ENVIRONMENT != 'production':
        # Trigger a test error
        division_by_zero = 1 / 0  # This will raise ZeroDivisionError
    return "This endpoint only works in development mode"


@app.route('/sentry-test-phi')
def sentry_test_phi():
    """
    Test endpoint to verify PHI sanitization in Sentry.
    Only works in development environment for security.

    Visit: http://localhost:8080/sentry-test-phi
    Expected: Error in Sentry with [REDACTED] instead of patient data
    """
    if ENVIRONMENT != 'production':
        # Simulate error with patient data (should be sanitized)
        patient_data = {
            'name': 'John Doe',  # Should be REDACTED
            'email': 'john@example.com',  # Should be REDACTED
            'phone': '+91 98765 43210',  # Should be REDACTED
            'diagnosis': 'Lower back pain',  # Should be REDACTED
        }
        # This error should NOT contain actual patient data in Sentry
        raise ValueError(f"Test error with patient data: {patient_data}")
    return "This endpoint only works in development mode"


@app.route('/sentry-test-message')
def sentry_test_message():
    """
    Test endpoint to send a test message to Sentry.
    Only works in development environment for security.

    Visit: http://localhost:8080/sentry-test-message
    Expected: Message appears in Sentry dashboard
    """
    if ENVIRONMENT != 'production' and SENTRY_DSN:
        sentry_sdk.capture_message(
            "Test message from PhysiologicPRISM! 🎉 Sentry is working correctly.",
            level="info"
        )
        return jsonify({
            'status': 'success',
            'message': 'Test message sent to Sentry!',
            'instructions': 'Check your Sentry dashboard at https://sentry.io'
        }), 200
    elif not SENTRY_DSN:
        return jsonify({
            'status': 'error',
            'message': 'Sentry DSN not configured. Set SENTRY_DSN in .env file.'
        }), 400
    else:
        return jsonify({
            'status': 'disabled',
            'message': 'Test endpoints disabled in production'
        }), 403


# ═══════════════════════════════════════════════════════════════════════════
# BLOG LEAD CAPTURE & WAITLIST ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/coming-soon')
def coming_soon():
    """Pre-launch coming soon / waitlist page"""
    return render_template('coming_soon.html')


@app.route('/api/blog/subscribe', methods=['POST'])
@csrf.exempt
def blog_subscribe():
    """
    Capture newsletter signup from blog posts.
    Creates a lead in the blog_leads collection.
    """
    try:
        data = request.get_json() or {}

        email = data.get('email', '').strip().lower()
        name = data.get('name', '').strip()
        post_slug = data.get('post_slug', 'unknown')
        source = data.get('source', 'blog_newsletter')

        # Validation
        if not email:
            return jsonify({'ok': False, 'message': 'Email is required'}), 400

        # Basic email validation
        if '@' not in email or '.' not in email:
            return jsonify({'ok': False, 'message': 'Invalid email address'}), 400

        # Check if lead already exists
        existing_lead = db.collection('blog_leads').document(email).get()

        if existing_lead.exists:
            # Update existing lead
            lead_data = existing_lead.to_dict()
            posts_read = lead_data.get('posts_read', [])
            if post_slug not in posts_read:
                posts_read.append(post_slug)

            db.collection('blog_leads').document(email).update({
                'last_activity': SERVER_TIMESTAMP,
                'posts_read': posts_read
            })

            return jsonify({
                'ok': True,
                'message': 'You\'re already subscribed! Thank you for your continued interest.'
            }), 200

        # Create new lead
        db.collection('blog_leads').document(email).set({
            'email': email,
            'name': name if name else None,
            'source': source,
            'first_seen_post': post_slug,
            'posts_read': [post_slug],
            'lead_magnet_downloaded': None,
            'status': 'new',
            'created_at': SERVER_TIMESTAMP,
            'last_activity': SERVER_TIMESTAMP,
            'converted_to_user': False,
            'user_email': None,
            'tags': [],
            'partition_key': email
        })

        # Send notification to super admin
        try:
            from email_service import send_blog_lead_notification
            send_blog_lead_notification({
                'email': email,
                'name': name,
                'source': source,
                'post_slug': post_slug,
                'created_at': datetime.now().isoformat()
            })
        except Exception as email_error:
            logger.error(f"Failed to send blog lead notification: {email_error}")

        # Log the lead capture
        log_action(None, 'Blog Lead', f"New newsletter subscriber: {email} from {post_slug}")

        return jsonify({
            'ok': True,
            'message': 'Success! Check your inbox for a welcome email.'
        }), 201

    except Exception as e:
        logger.error(f"Blog subscribe error: {e}", exc_info=True)
        return jsonify({'ok': False, 'message': 'Something went wrong. Please try again.'}), 500


@app.route('/api/blog/waitlist', methods=['POST'])
@csrf.exempt
def blog_waitlist():
    """
    Capture waitlist signup from coming soon page.
    Creates a lead in the blog_leads collection.
    """
    try:
        data = request.get_json() or {}

        email = data.get('email', '').strip().lower()
        name = data.get('name', '').strip()
        source = data.get('source', 'coming_soon_page')

        # Validation
        if not email:
            return jsonify({'ok': False, 'message': 'Email is required'}), 400

        # Basic email validation
        if '@' not in email or '.' not in email:
            return jsonify({'ok': False, 'message': 'Invalid email address'}), 400

        # Check if lead already exists
        existing_lead = db.collection('blog_leads').document(email).get()

        if existing_lead.exists:
            return jsonify({
                'ok': True,
                'message': 'You\'re already on the waitlist! We\'ll notify you at launch.'
            }), 200

        # Create new lead
        db.collection('blog_leads').document(email).set({
            'email': email,
            'name': name if name else None,
            'source': source,
            'first_seen_post': 'waitlist',
            'posts_read': [],
            'lead_magnet_downloaded': None,
            'status': 'new',
            'created_at': SERVER_TIMESTAMP,
            'last_activity': SERVER_TIMESTAMP,
            'converted_to_user': False,
            'user_email': None,
            'tags': ['waitlist'],
            'partition_key': email
        })

        # Send notification to super admin
        try:
            from email_service import send_blog_lead_notification
            send_blog_lead_notification({
                'email': email,
                'name': name,
                'source': source,
                'post_slug': 'waitlist',
                'created_at': datetime.now().isoformat()
            })
        except Exception as email_error:
            logger.error(f"Failed to send waitlist notification: {email_error}")

        # Log the waitlist signup
        log_action(None, 'Waitlist', f"New waitlist signup: {email}")

        return jsonify({
            'ok': True,
            'message': 'Success! You\'re on the waitlist. We\'ll notify you at launch!'
        }), 201

    except Exception as e:
        logger.error(f"Waitlist signup error: {e}", exc_info=True)
        return jsonify({'ok': False, 'message': 'Something went wrong. Please try again.'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))


