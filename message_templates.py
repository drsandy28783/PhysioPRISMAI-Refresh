"""
HIPAA/GDPR-Compliant Message Templates
NO PHI (Protected Health Information) in messages
All messages use generic text with deep links to app
"""

from typing import Dict, Any
import os

APP_NAME = os.getenv('APP_NAME', 'PhysiologicPRISM')
APP_URL = os.getenv('APP_URL', 'https://physiologicprism.com')


class MessageTemplates:
    """
    PHI-Safe Message Templates

    CRITICAL COMPLIANCE RULES:
    1. NO patient names in messages
    2. NO medical conditions or diagnoses
    3. NO specific appointment details (time, location)
    4. Use generic text with secure app links
    5. All messages include opt-out instructions
    """

    # ═══════════════════════════════════════════════════════════════
    # OTP / AUTHENTICATION MESSAGES
    # ═══════════════════════════════════════════════════════════════

    OTP_VERIFICATION = {
        'template': "{code} is your {app_name} verification code. Valid for {validity} minutes. Do not share this code.",
        'variables': ['code', 'validity'],
        'type': 'authentication',
        'opt_out': False  # No opt-out for security messages
    }

    OTP_LOGIN = {
        'template': "{code} is your {app_name} login code. Valid for {validity} minutes. If you didn't request this, please secure your account.",
        'variables': ['code', 'validity'],
        'type': 'authentication',
        'opt_out': False
    }

    PASSWORD_RESET = {
        'template': "Your {app_name} password reset code is {code}. Valid for {validity} minutes. If you didn't request this, ignore this message.",
        'variables': ['code', 'validity'],
        'type': 'authentication',
        'opt_out': False
    }

    # ═══════════════════════════════════════════════════════════════
    # APPOINTMENT REMINDERS (PHI-SAFE)
    # ═══════════════════════════════════════════════════════════════

    APPOINTMENT_REMINDER_24H = {
        'template': "Reminder: You have an appointment in 24 hours. Open {app_name} to view details: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    APPOINTMENT_REMINDER_2H = {
        'template': "Your appointment is in 2 hours. Check {app_name} for details: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    APPOINTMENT_CONFIRMED = {
        'template': "Appointment confirmed. View details in {app_name}: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    APPOINTMENT_CANCELLED = {
        'template': "Appointment update. Open {app_name} to view changes: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    APPOINTMENT_RESCHEDULED = {
        'template': "Appointment rescheduled. Check {app_name} for new details: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    # ═══════════════════════════════════════════════════════════════
    # FOLLOW-UP REMINDERS
    # ═══════════════════════════════════════════════════════════════

    FOLLOW_UP_DUE = {
        'template': "Follow-up reminder from {app_name}. Open the app to schedule: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    FOLLOW_UP_OVERDUE = {
        'template': "Follow-up needed. Check {app_name} for details: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    # ═══════════════════════════════════════════════════════════════
    # SUBSCRIPTION & PAYMENT NOTIFICATIONS
    # ═══════════════════════════════════════════════════════════════

    SUBSCRIPTION_EXPIRING = {
        'template': "Your {app_name} subscription expires in {days} days. Renew now to avoid service interruption: {app_link}\n\nReply STOP to opt out.",
        'variables': ['days', 'app_link'],
        'type': 'utility',
        'opt_out': True
    }

    SUBSCRIPTION_EXPIRED = {
        'template': "Your {app_name} subscription has expired. Renew to restore access: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    PAYMENT_SUCCESS = {
        'template': "Payment received. Your {app_name} subscription is now active. View receipt: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    PAYMENT_FAILED = {
        'template': "Payment failed for {app_name}. Update payment method to continue: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    QUOTA_WARNING = {
        'template': "You've used 80% of your {app_name} quota. View usage details: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    QUOTA_EXCEEDED = {
        'template': "Your {app_name} quota is full. Upgrade or wait for reset: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    # ═══════════════════════════════════════════════════════════════
    # ACCOUNT & SYSTEM NOTIFICATIONS
    # ═══════════════════════════════════════════════════════════════

    ACCOUNT_APPROVED = {
        'template': "Your {app_name} account has been approved! Log in to get started: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    ACCOUNT_SUSPENDED = {
        'template': "Important: Your {app_name} account status has changed. Log in for details: {app_link}",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': False  # Critical security message
    }

    TOS_UPDATED = {
        'template': "Terms of Service updated. Review changes in {app_name}: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    SECURITY_ALERT = {
        'template': "Security alert: Unusual activity detected on your {app_name} account. Review now: {app_link}",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': False  # Critical security message
    }

    # ═══════════════════════════════════════════════════════════════
    # TWO-WAY MESSAGING (FROM PROVIDER TO PATIENT)
    # ═══════════════════════════════════════════════════════════════

    NEW_MESSAGE = {
        'template': "New message in {app_name}. Open the app to read: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    MESSAGE_RECEIVED = {
        'template': "Your message was received. You'll get a response in {app_name} soon.",
        'variables': [],
        'type': 'utility',
        'opt_out': False  # Confirmation message
    }

    # ═══════════════════════════════════════════════════════════════
    # WELCOME & ONBOARDING
    # ═══════════════════════════════════════════════════════════════

    WELCOME_NEW_USER = {
        'template': "Welcome to {app_name}! Get started here: {app_link}\n\nReply STOP to opt out.",
        'variables': ['app_link'],
        'type': 'utility',
        'opt_out': True
    }

    TRIAL_STARTING = {
        'template': "Your {days}-day {app_name} trial has started! Explore all features: {app_link}\n\nReply STOP to opt out.",
        'variables': ['days', 'app_link'],
        'type': 'utility',
        'opt_out': True
    }

    TRIAL_ENDING = {
        'template': "Your {app_name} trial ends in {days} days. Subscribe to continue: {app_link}\n\nReply STOP to opt out.",
        'variables': ['days', 'app_link'],
        'type': 'utility',
        'opt_out': True
    }

    # ═══════════════════════════════════════════════════════════════
    # OPT-OUT RESPONSES
    # ═══════════════════════════════════════════════════════════════

    OPT_OUT_CONFIRMATION = {
        'template': "You've been unsubscribed from {app_name} messages. You'll only receive critical security alerts. To opt back in, update your preferences in the app.",
        'variables': [],
        'type': 'utility',
        'opt_out': False
    }

    OPT_IN_CONFIRMATION = {
        'template': "You're now subscribed to {app_name} notifications. Reply STOP anytime to unsubscribe.",
        'variables': [],
        'type': 'utility',
        'opt_out': False
    }

    # ═══════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    def render(cls, template_name: str, **kwargs) -> str:
        """
        Render a message template with variables

        Args:
            template_name: Name of template (e.g., 'OTP_VERIFICATION')
            **kwargs: Variables to substitute in template

        Returns:
            Rendered message string

        Example:
            MessageTemplates.render('OTP_VERIFICATION', code='123456', validity=10)
        """
        template_config = getattr(cls, template_name, None)

        if not template_config:
            raise ValueError(f"Template '{template_name}' not found")

        template = template_config['template']

        # Add default variables
        kwargs.setdefault('app_name', APP_NAME)
        kwargs.setdefault('app_link', APP_URL)

        # Render template
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required variable for template '{template_name}': {e}")

    @classmethod
    def get_template_type(cls, template_name: str) -> str:
        """Get the message type (authentication, utility, marketing)"""
        template_config = getattr(cls, template_name, None)
        if template_config:
            return template_config.get('type', 'utility')
        return 'utility'

    @classmethod
    def requires_consent(cls, template_name: str) -> bool:
        """Check if template requires user consent (has opt-out)"""
        template_config = getattr(cls, template_name, None)
        if template_config:
            return template_config.get('opt_out', True)
        return True

    @classmethod
    def list_templates(cls) -> Dict[str, Dict[str, Any]]:
        """Get all available templates"""
        templates = {}
        for attr_name in dir(cls):
            if attr_name.isupper() and not attr_name.startswith('_'):
                attr = getattr(cls, attr_name)
                if isinstance(attr, dict) and 'template' in attr:
                    templates[attr_name] = attr
        return templates


# ═══════════════════════════════════════════════════════════════
# DEEP LINK GENERATOR
# ═══════════════════════════════════════════════════════════════

class DeepLinkGenerator:
    """Generate deep links for app navigation"""

    @staticmethod
    def appointment_details(appointment_id: str) -> str:
        """Link to appointment details"""
        return f"{APP_URL}/appointments/{appointment_id}"

    @staticmethod
    def follow_up_schedule(patient_id: str) -> str:
        """Link to follow-up scheduling"""
        return f"{APP_URL}/follow-ups/{patient_id}"

    @staticmethod
    def subscription_manage() -> str:
        """Link to subscription management"""
        return f"{APP_URL}/subscription"

    @staticmethod
    def payment_update() -> str:
        """Link to payment method update"""
        return f"{APP_URL}/settings/payment"

    @staticmethod
    def messages_inbox() -> str:
        """Link to messages inbox"""
        return f"{APP_URL}/messages"

    @staticmethod
    def account_settings() -> str:
        """Link to account settings"""
        return f"{APP_URL}/settings"

    @staticmethod
    def dashboard() -> str:
        """Link to main dashboard"""
        return f"{APP_URL}/dashboard"


# ═══════════════════════════════════════════════════════════════
# USAGE EXAMPLES
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Example 1: OTP message
    otp_message = MessageTemplates.render('OTP_VERIFICATION', code='123456', validity=10)
    print("OTP Message:", otp_message)

    # Example 2: Appointment reminder
    appointment_link = DeepLinkGenerator.appointment_details('appt_12345')
    reminder = MessageTemplates.render('APPOINTMENT_REMINDER_24H', app_link=appointment_link)
    print("Appointment Reminder:", reminder)

    # Example 3: Subscription expiring
    subscription_link = DeepLinkGenerator.subscription_manage()
    expiry_msg = MessageTemplates.render('SUBSCRIPTION_EXPIRING', days=3, app_link=subscription_link)
    print("Subscription Expiring:", expiry_msg)

    # Example 4: List all templates
    print("\nAll available templates:")
    for name, config in MessageTemplates.list_templates().items():
        print(f"  - {name}: {config['type']}")
