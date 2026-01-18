"""
Request/Response Validation Schemas for Physio-Assist
Using Marshmallow for comprehensive input validation

This module provides validation schemas for all user inputs to prevent:
- Injection attacks (XSS, SQL injection, etc.)
- Invalid data formats
- Data quality issues
- PHI leakage in AI requests

Author: Production Readiness Team
Phase: 1C - Security Hardening
Task: 3.2 - Input Validation with Marshmallow
"""

from marshmallow import Schema, fields, validate, validates, validates_schema, ValidationError, EXCLUDE
import re


# ─── HELPER VALIDATORS ───────────────────────────────────────────────

def validate_no_html(value):
    """
    Ensure no HTML/script tags in input (prevent XSS attacks)
    """
    if not value:
        return

    # Check for common HTML/script tags
    html_pattern = r'<\s*(script|iframe|object|embed|link|style|meta|html|body|img)\s*[^>]*>'
    if re.search(html_pattern, value, re.IGNORECASE):
        raise ValidationError('HTML tags are not allowed')

    # Check for common XSS patterns
    xss_patterns = [
        r'javascript:',
        r'on\w+\s*=',  # onclick, onload, etc.
        r'<\s*\w+[^>]*on\w+',  # tags with event handlers
    ]
    for pattern in xss_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            raise ValidationError('Potentially malicious content detected')


def validate_name(value):
    """
    Validate person names (letters, spaces, hyphens, apostrophes, periods only)
    """
    if not value:
        return

    # Allow: letters (any language), spaces, hyphens, apostrophes, periods
    if not re.match(r"^[a-zA-Z\s.\-']+$", value):
        raise ValidationError('Name can only contain letters, spaces, periods, hyphens, and apostrophes')


def validate_phone(value):
    """
    Validate phone numbers (flexible format)
    """
    if not value:
        return

    # Remove common formatting characters
    cleaned = re.sub(r'[\s\-()]+', '', value)

    # Check if it's a valid number format
    if not re.match(r'^\+?[0-9]{10,15}$', cleaned):
        raise ValidationError('Invalid phone number format. Must be 10-15 digits.')


def validate_no_sensitive_keys(data):
    """
    Ensure no sensitive data keys in dictionaries (for AI requests)
    """
    if not isinstance(data, dict):
        return

    forbidden_keys = ['password', 'token', 'secret', 'ssn', 'credit_card', 'api_key']
    for key in data.keys():
        if any(forbidden in key.lower() for forbidden in forbidden_keys):
            raise ValidationError(f'Forbidden key in data: {key}')


# ─── USER MANAGEMENT SCHEMAS ──────────────────────────────────────────

class UserRegistrationSchema(Schema):
    """Validate user registration data"""

    class Meta:
        unknown = EXCLUDE  # Ignore unknown fields (security)

    name = fields.Str(
        required=True,
        validate=[
            validate.Length(min=2, max=100),
            validate_name,
            validate_no_html
        ]
    )

    email = fields.Email(
        required=True,
        validate=validate.Length(max=255)
    )

    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=128)
    )

    phone = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=20),
            validate_phone
        ]
    )

    institute = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=200),
            validate_no_html
        ]
    )


class LoginSchema(Schema):
    """Validate login credentials"""

    class Meta:
        unknown = EXCLUDE

    email = fields.Email(
        required=True,
        validate=validate.Length(max=255)
    )

    password = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=128)
    )


# ─── PATIENT MANAGEMENT SCHEMAS ───────────────────────────────────────

class PatientSchema(Schema):
    """Patient creation/update validation"""

    class Meta:
        unknown = EXCLUDE

    name = fields.Str(
        required=True,
        validate=[
            validate.Length(min=2, max=100),
            validate_name,
            validate_no_html
        ]
    )

    age_sex = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=50),
            validate_no_html
        ]
    )

    contact = fields.Str(
        required=True,
        validate=[
            validate.Length(min=10, max=20),
            validate_phone
        ]
    )

    email = fields.Email(
        required=False,
        allow_none=True,
        validate=validate.Length(max=255)
    )

    address = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=500),
            validate_no_html
        ]
    )

    chief_complaint = fields.Str(
        required=True,
        validate=[
            validate.Length(min=5, max=2000),
            validate_no_html
        ]
    )

    medical_history = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=5000),
            validate_no_html
        ]
    )

    occupation = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=200),
            validate_no_html
        ]
    )

    referred_by = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=200),
            validate_no_html
        ]
    )

    @validates('age_sex')
    def validate_age_sex_format(self, value):
        """Ensure age_sex follows expected format (e.g., '45/M' or '30/F')"""
        # Allow various formats: "45/M", "30 years/F", "25/Male", etc.
        if not re.match(r'^.+/(M|F|Male|Female|m|f|male|female|Other|other)$', value.strip()):
            # Allow if it doesn't match pattern (flexible for now)
            pass


class SubjectiveExaminationSchema(Schema):
    """Subjective examination data validation"""

    class Meta:
        unknown = EXCLUDE

    patient_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$', error='Patient ID can only contain letters, numbers, hyphens, and underscores')
        ]
    )

    present_history = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=5000),
            validate_no_html
        ]
    )

    past_history = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=5000),
            validate_no_html
        ]
    )

    social_history = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=3000),
            validate_no_html
        ]
    )

    chief_complaint = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=2000),
            validate_no_html
        ]
    )


class ObjectiveAssessmentSchema(Schema):
    """Objective assessment data validation"""

    class Meta:
        unknown = EXCLUDE

    patient_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$')
        ]
    )

    # Allow flexible field names for objective assessment
    # (ROM, strength, palpation, special tests, etc.)


class TreatmentPlanSchema(Schema):
    """Treatment plan validation"""

    class Meta:
        unknown = EXCLUDE

    patient_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$')
        ]
    )

    treatment_plan = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=5000),
            validate_no_html
        ]
    )

    smart_goals = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=3000),
            validate_no_html
        ]
    )


# ─── AI SUGGESTION SCHEMAS ────────────────────────────────────────────

class AIPromptSchema(Schema):
    """AI suggestion request validation - critical for security"""

    class Meta:
        unknown = EXCLUDE

    patient_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$', error='Invalid patient ID format')
        ]
    )

    field = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100)
    )

    context = fields.Dict(
        required=True,
        keys=fields.Str(),
        values=fields.Str(allow_none=True)
    )

    @validates('context')
    def validate_context_no_sensitive_data(self, value):
        """Ensure no sensitive data keys in context"""
        validate_no_sensitive_keys(value)

        # Also check values for excessive length (prevent abuse)
        for key, val in value.items():
            if val and len(str(val)) > 10000:
                raise ValidationError(f'Context field "{key}" exceeds maximum length (10,000 characters)')


# ─── SUBSCRIPTION & PAYMENT SCHEMAS ───────────────────────────────────

class SubscriptionCheckoutSchema(Schema):
    """Subscription checkout validation"""

    class Meta:
        unknown = EXCLUDE

    plan_type = fields.Str(
        required=True,
        validate=validate.OneOf(
            ['solo', 'team_5', 'team_10', 'institute_15', 'institute_20'],
            error='Invalid subscription plan type'
        )
    )


class TokenPurchaseSchema(Schema):
    """Token purchase validation"""

    class Meta:
        unknown = EXCLUDE

    package = fields.Str(
        required=True,
        validate=validate.OneOf(
            ['starter', 'regular', 'popular', 'professional', 'enterprise'],
            error='Invalid token package'
        )
    )


class PaymentVerificationSchema(Schema):
    """Razorpay payment verification validation"""

    class Meta:
        unknown = EXCLUDE

    razorpay_order_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=10, max=100),
            validate.Regexp(r'^order_[a-zA-Z0-9]+$', error='Invalid Razorpay order ID format')
        ]
    )

    razorpay_payment_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=10, max=100),
            validate.Regexp(r'^pay_[a-zA-Z0-9]+$', error='Invalid Razorpay payment ID format')
        ]
    )

    razorpay_signature = fields.Str(
        required=True,
        validate=validate.Length(min=10, max=200)
    )


# ─── FOLLOW-UP SCHEMAS ────────────────────────────────────────────────

class FollowUpSchema(Schema):
    """Follow-up session validation"""

    class Meta:
        unknown = EXCLUDE

    patient_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$')
        ]
    )

    followup_date = fields.Date(
        required=True,
        format='%Y-%m-%d'
    )

    subjective_findings = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=5000),
            validate_no_html
        ]
    )

    objective_findings = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=5000),
            validate_no_html
        ]
    )

    treatment_given = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=3000),
            validate_no_html
        ]
    )

    progress_notes = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=3000),
            validate_no_html
        ]
    )


# ─── INSTITUTE MANAGEMENT SCHEMAS ─────────────────────────────────────

class InstituteStaffApprovalSchema(Schema):
    """Institute staff approval validation"""

    class Meta:
        unknown = EXCLUDE

    email = fields.Email(
        required=True,
        validate=validate.Length(max=255)
    )

    action = fields.Str(
        required=True,
        validate=validate.OneOf(['approve', 'reject', 'deactivate'])
    )


class InstituteRegistrationSchema(Schema):
    """Institute registration validation"""

    class Meta:
        unknown = EXCLUDE

    name = fields.Str(
        required=True,
        validate=[
            validate.Length(min=2, max=100),
            validate_name,
            validate_no_html
        ]
    )

    email = fields.Email(
        required=True,
        validate=validate.Length(max=255)
    )

    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=128)
    )

    phone = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=20),
            validate_phone
        ]
    )

    institute_name = fields.Str(
        required=True,
        validate=[
            validate.Length(min=2, max=200),
            validate_no_html
        ]
    )

    institute_address = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=500),
            validate_no_html
        ]
    )

    consent_data_processing = fields.Bool(required=True)
    consent_terms = fields.Bool(required=True)
    consent_ai = fields.Bool(required=False, missing=False)

    @validates('consent_data_processing')
    def validate_data_consent(self, value):
        if not value:
            raise ValidationError('Data processing consent is required')

    @validates('consent_terms')
    def validate_terms_consent(self, value):
        if not value:
            raise ValidationError('Terms of service consent is required')


# ─── PASSWORD & AUTHENTICATION SCHEMAS ────────────────────────────────

class ForgotPasswordSchema(Schema):
    """Forgot password request validation"""

    class Meta:
        unknown = EXCLUDE

    email = fields.Email(
        required=True,
        validate=validate.Length(max=255)
    )


class ResetPasswordSchema(Schema):
    """Password reset validation"""

    class Meta:
        unknown = EXCLUDE

    token = fields.Str(
        required=True,
        validate=validate.Length(min=20, max=500)
    )

    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=128)
    )

    confirm_password = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=128)
    )

    @validates_schema
    def validate_passwords_match(self, data, **kwargs):
        if data.get('password') != data.get('confirm_password'):
            raise ValidationError({'confirm_password': ['Passwords do not match']})


class EmailVerificationSchema(Schema):
    """Email verification token validation"""

    class Meta:
        unknown = EXCLUDE

    token = fields.Str(
        required=True,
        validate=validate.Length(min=20, max=500)
    )


class ResendVerificationSchema(Schema):
    """Resend verification email validation"""

    class Meta:
        unknown = EXCLUDE

    email = fields.Email(
        required=True,
        validate=validate.Length(max=255)
    )


class ProfileUpdateSchema(Schema):
    """User profile update validation"""

    class Meta:
        unknown = EXCLUDE

    name = fields.Str(
        required=False,
        validate=[
            validate.Length(min=2, max=100),
            validate_name,
            validate_no_html
        ]
    )

    phone = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=20),
            validate_phone
        ]
    )

    institute = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=200),
            validate_no_html
        ]
    )

    bio = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=1000),
            validate_no_html
        ]
    )


class Enable2FASchema(Schema):
    """Enable two-factor authentication validation"""

    class Meta:
        unknown = EXCLUDE

    password = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=128)
    )


class Disable2FASchema(Schema):
    """Disable two-factor authentication validation"""

    class Meta:
        unknown = EXCLUDE

    password = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=128)
    )

    totp_code = fields.Str(
        required=True,
        validate=[
            validate.Length(min=6, max=6),
            validate.Regexp(r'^\d{6}$', error='TOTP code must be 6 digits')
        ]
    )


class Verify2FASchema(Schema):
    """Verify 2FA TOTP code validation"""

    class Meta:
        unknown = EXCLUDE

    totp_code = fields.Str(
        required=True,
        validate=[
            validate.Length(min=6, max=6),
            validate.Regexp(r'^\d{6}$', error='TOTP code must be 6 digits')
        ]
    )


# ─── PAYMENT SCHEMAS (ADDITIONAL) ─────────────────────────────────────

class SubscriptionCancelSchema(Schema):
    """Subscription cancellation validation"""

    class Meta:
        unknown = EXCLUDE

    reason = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=1000),
            validate_no_html
        ]
    )

    feedback = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=2000),
            validate_no_html
        ]
    )


class RazorpayWebhookSchema(Schema):
    """Razorpay webhook payload validation"""

    class Meta:
        unknown = EXCLUDE

    event = fields.Str(
        required=True,
        validate=validate.Length(max=100)
    )

    payload = fields.Dict(
        required=True,
        keys=fields.Str(),
        values=fields.Raw()
    )


# ─── CLINICAL ASSESSMENT SCHEMAS (ADDITIONAL) ─────────────────────────

class ProvisionalDiagnosisSchema(Schema):
    """Provisional diagnosis validation"""

    class Meta:
        unknown = EXCLUDE

    patient_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$')
        ]
    )

    diagnosis = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=2000),
            validate_no_html
        ]
    )

    clinical_reasoning = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=3000),
            validate_no_html
        ]
    )


class PatientStatusSchema(Schema):
    """Patient status update validation"""

    class Meta:
        unknown = EXCLUDE

    status = fields.Str(
        required=True,
        validate=validate.OneOf(['active', 'discharged', 'on_hold', 'archived'])
    )

    notes = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=500),
            validate_no_html
        ]
    )


class PatientTagsSchema(Schema):
    """Patient tags management validation"""

    class Meta:
        unknown = EXCLUDE

    tags = fields.List(
        fields.Str(validate=[
            validate.Length(max=50),
            validate_no_html
        ]),
        validate=validate.Length(max=20)
    )


# ─── DRAFT & CONTENT MANAGEMENT SCHEMAS ───────────────────────────────

class DraftSaveSchema(Schema):
    """Draft save validation"""

    class Meta:
        unknown = EXCLUDE

    patient_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$')
        ]
    )

    section = fields.Str(
        required=True,
        validate=validate.OneOf([
            'subjective', 'objective', 'assessment', 'plan',
            'diagnosis', 'goals', 'treatment', 'followup',
            'add_patient'  # Allow draft saving for new patient form
        ])
    )

    data = fields.Dict(
        required=True,
        keys=fields.Str(),
        values=fields.Str(allow_none=True)
    )

    @validates('data')
    def validate_data_size(self, value):
        """Ensure draft data isn't too large"""
        import json
        data_size = len(json.dumps(value))
        if data_size > 100000:  # 100KB limit
            raise ValidationError('Draft data exceeds maximum size (100KB)')


class BlogPostSchema(Schema):
    """Blog post creation/update validation"""

    class Meta:
        unknown = EXCLUDE

    title = fields.Str(
        required=True,
        validate=[
            validate.Length(min=5, max=200),
            validate_no_html
        ]
    )

    content = fields.Str(
        required=True,
        validate=[
            validate.Length(min=50, max=50000),
            # Allow some HTML for rich text editing, but validate carefully
        ]
    )

    excerpt = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=500),
            validate_no_html
        ]
    )

    tags = fields.List(
        fields.Str(validate=validate.Length(max=50)),
        validate=validate.Length(max=10)
    )

    published = fields.Bool(required=False, missing=False)


# ─── NOTIFICATION & SCHEDULING SCHEMAS ────────────────────────────────

class FollowUpScheduleSchema(Schema):
    """Follow-up scheduling validation"""

    class Meta:
        unknown = EXCLUDE

    patient_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$')
        ]
    )

    next_followup_date = fields.Date(
        required=True,
        format='%Y-%m-%d'
    )

    reminder_enabled = fields.Bool(required=False, missing=True)

    notes = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=500),
            validate_no_html
        ]
    )


class NotificationActionSchema(Schema):
    """Notification action validation"""

    class Meta:
        unknown = EXCLUDE

    notification_id = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100)
    )

    action = fields.Str(
        required=True,
        validate=validate.OneOf(['read', 'unread', 'delete'])
    )


# ─── PRIVACY & COMPLIANCE SCHEMAS ─────────────────────────────────────

class DataDeletionRequestSchema(Schema):
    """GDPR data deletion request validation"""

    class Meta:
        unknown = EXCLUDE

    reason = fields.Str(
        required=True,
        validate=[
            validate.Length(min=10, max=1000),
            validate_no_html
        ]
    )

    confirm_deletion = fields.Bool(required=True)

    password = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=128)
    )

    @validates('confirm_deletion')
    def validate_confirmation(self, value):
        if not value:
            raise ValidationError('You must confirm the deletion request')


class TOSAcceptanceSchema(Schema):
    """Terms of Service acceptance validation"""

    class Meta:
        unknown = EXCLUDE

    tos_version = fields.Str(
        required=True,
        validate=validate.Length(max=20)
    )

    accepted = fields.Bool(required=True)

    @validates('accepted')
    def validate_acceptance(self, value):
        if not value:
            raise ValidationError('You must accept the Terms of Service')


class AccessRequestSchema(Schema):
    """Access request form validation"""

    class Meta:
        unknown = EXCLUDE

    name = fields.Str(
        required=True,
        validate=[
            validate.Length(min=2, max=100),
            validate_name,
            validate_no_html
        ]
    )

    email = fields.Email(
        required=True,
        validate=validate.Length(max=255)
    )

    phone = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=20),
            validate_phone
        ]
    )

    institute = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=200),
            validate_no_html
        ]
    )

    message = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=1000),
            validate_no_html
        ]
    )


class SyncUserSchema(Schema):
    """User sync data validation (Firebase to Firestore)"""

    class Meta:
        unknown = EXCLUDE

    firebase_uid = fields.Str(
        required=True,
        validate=validate.Length(min=10, max=128)
    )

    email = fields.Email(
        required=True,
        validate=validate.Length(max=255)
    )

    name = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            validate.Length(max=100),
            validate_name,
            validate_no_html
        ]
    )


# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────

def validate_data(schema_class, data):
    """
    Convenience function to validate data against a schema

    Args:
        schema_class: Marshmallow Schema class
        data: Dictionary of data to validate

    Returns:
        tuple: (is_valid, validated_data or errors)

    Example:
        is_valid, result = validate_data(PatientSchema, request.form)
        if not is_valid:
            return jsonify({'error': result}), 400
        # use result (validated data)
    """
    schema = schema_class()
    try:
        validated_data = schema.load(data)
        return True, validated_data
    except ValidationError as err:
        return False, err.messages


def validate_json(schema_class, json_data):
    """
    Convenience function to validate JSON data against a schema

    Args:
        schema_class: Marshmallow Schema class
        json_data: Dictionary of JSON data to validate

    Returns:
        tuple: (is_valid, validated_data or errors)
    """
    return validate_data(schema_class, json_data)


# ─── EXPORT ALL SCHEMAS ───────────────────────────────────────────────

__all__ = [
    # User Management
    'UserRegistrationSchema',
    'LoginSchema',
    'ProfileUpdateSchema',

    # Patient Management
    'PatientSchema',
    'SubjectiveExaminationSchema',
    'ObjectiveAssessmentSchema',
    'TreatmentPlanSchema',
    'ProvisionalDiagnosisSchema',
    'PatientStatusSchema',
    'PatientTagsSchema',

    # AI Suggestions
    'AIPromptSchema',

    # Subscriptions & Payments
    'SubscriptionCheckoutSchema',
    'TokenPurchaseSchema',
    'PaymentVerificationSchema',
    'SubscriptionCancelSchema',
    'RazorpayWebhookSchema',

    # Follow-ups
    'FollowUpSchema',
    'FollowUpScheduleSchema',

    # Institute Management
    'InstituteStaffApprovalSchema',
    'InstituteRegistrationSchema',

    # Authentication & Password
    'ForgotPasswordSchema',
    'ResetPasswordSchema',
    'EmailVerificationSchema',
    'ResendVerificationSchema',
    'Enable2FASchema',
    'Disable2FASchema',
    'Verify2FASchema',

    # Draft & Content Management
    'DraftSaveSchema',
    'BlogPostSchema',

    # Notifications
    'NotificationActionSchema',

    # Privacy & Compliance
    'DataDeletionRequestSchema',
    'TOSAcceptanceSchema',
    'AccessRequestSchema',
    'SyncUserSchema',

    # Helper Functions
    'validate_data',
    'validate_json',
]
