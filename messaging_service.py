"""
Unified Messaging Service for PhysiologicPRISM
Handles SMS and WhatsApp messaging with HIPAA/GDPR compliance
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from enum import Enum

from azure_cosmos_db import get_cosmos_db, SERVER_TIMESTAMP
from twilio_provider import get_twilio_provider, MessageChannel
from consent_manager import ConsentManager, ConsentType
from message_templates import MessageTemplates, DeepLinkGenerator

logger = logging.getLogger(__name__)

# Initialize services
db = get_cosmos_db()
twilio = get_twilio_provider()


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    CRITICAL = 'critical'


class MessagingService:
    """
    Unified messaging service with HIPAA/GDPR compliance

    Features:
    - Send SMS/WhatsApp with consent checks
    - OTP generation and verification
    - Message tracking and delivery status
    - Automatic retry for failed messages
    - PHI-safe message templates
    - Data retention compliance
    """

    # ═══════════════════════════════════════════════════════════════
    # CORE MESSAGING METHODS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def send_message(
        user_id: str,
        template_name: str,
        channel: MessageChannel = MessageChannel.WHATSAPP,
        priority: MessagePriority = MessagePriority.NORMAL,
        **template_vars
    ) -> Dict:
        """
        Send a message to a user using a template

        Args:
            user_id: User's email/ID
            template_name: Name of template from MessageTemplates
            channel: Preferred channel (SMS or WhatsApp)
            priority: Message priority
            **template_vars: Variables to pass to template

        Returns:
            Dict with send status and message ID

        Example:
            MessagingService.send_message(
                user_id='user@example.com',
                template_name='APPOINTMENT_REMINDER_24H',
                channel=MessageChannel.WHATSAPP,
                app_link=DeepLinkGenerator.appointment_details('appt_123')
            )
        """
        try:
            # Get user's phone number from consent record
            phone_number = ConsentManager.get_phone_number(user_id)

            if not phone_number:
                logger.warning(f"No phone number for user {user_id}")
                return {
                    'success': False,
                    'error': 'No phone number registered'
                }

            # Check consent (unless it's a security/critical message)
            if MessageTemplates.requires_consent(template_name):
                consent_type = ConsentType.WHATSAPP if channel == MessageChannel.WHATSAPP else ConsentType.SMS

                if not ConsentManager.has_consent(user_id, consent_type):
                    logger.info(f"User {user_id} has not consented to {consent_type.value}")
                    return {
                        'success': False,
                        'error': f'User has not consented to {consent_type.value}'
                    }

            # Render message from template
            message_text = MessageTemplates.render(template_name, **template_vars)

            # Send message via Twilio
            if channel == MessageChannel.WHATSAPP:
                result = twilio.send_whatsapp(phone_number, message_text)
            else:
                result = twilio.send_sms(phone_number, message_text)

            # Log message in database
            message_id = MessagingService._log_message(
                user_id=user_id,
                phone_number=phone_number,
                message_text=message_text,
                template_name=template_name,
                channel=channel.value,
                priority=priority.value,
                provider_message_id=result.get('provider_message_id'),
                status=result.get('status'),
                error=result.get('error_message')
            )

            return {
                'success': result['success'],
                'message_id': message_id,
                'channel': channel.value,
                'status': result.get('status'),
                'provider_message_id': result.get('provider_message_id')
            }

        except Exception as e:
            logger.error(f"Failed to send message to {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def send_with_fallback(
        user_id: str,
        template_name: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        **template_vars
    ) -> Dict:
        """
        Send message with automatic fallback from WhatsApp to SMS

        Args:
            user_id: User's email/ID
            template_name: Name of template
            priority: Message priority
            **template_vars: Template variables

        Returns:
            Dict with send status
        """
        # Try WhatsApp first
        result = MessagingService.send_message(
            user_id=user_id,
            template_name=template_name,
            channel=MessageChannel.WHATSAPP,
            priority=priority,
            **template_vars
        )

        # Fallback to SMS if WhatsApp fails
        if not result['success'] and 'not consented' not in result.get('error', ''):
            logger.info(f"WhatsApp failed for {user_id}, trying SMS")
            result = MessagingService.send_message(
                user_id=user_id,
                template_name=template_name,
                channel=MessageChannel.SMS,
                priority=priority,
                **template_vars
            )
            result['fallback_used'] = True

        return result

    # ═══════════════════════════════════════════════════════════════
    # OTP / 2FA METHODS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def send_otp(
        user_id: str,
        phone_number: str,
        purpose: str = 'verification',
        validity_minutes: int = 10,
        channel: MessageChannel = MessageChannel.SMS
    ) -> Dict:
        """
        Send OTP code to user

        Args:
            user_id: User's email/ID
            phone_number: Phone number to send OTP
            purpose: Purpose of OTP (verification, login, password_reset)
            validity_minutes: OTP validity in minutes
            channel: Channel to use (SMS or WhatsApp)

        Returns:
            Dict with send status (OTP code NOT included for security)
        """
        try:
            # Generate 6-digit OTP
            otp_code = MessagingService._generate_otp()

            # Store OTP in database with expiration
            otp_ref = db.collection('otp_codes').add({
                'user_id': user_id,
                'phone_number': phone_number,
                'code': otp_code,
                'purpose': purpose,
                'created_at': SERVER_TIMESTAMP,
                'expires_at': datetime.utcnow() + timedelta(minutes=validity_minutes),
                'verified': False,
                'attempts': 0
            })

            otp_id = otp_ref[1].id

            # Select template based on purpose
            template_map = {
                'verification': 'OTP_VERIFICATION',
                'login': 'OTP_LOGIN',
                'password_reset': 'PASSWORD_RESET'
            }

            template_name = template_map.get(purpose, 'OTP_VERIFICATION')

            # Render message
            message_text = MessageTemplates.render(
                template_name,
                code=otp_code,
                validity=validity_minutes
            )

            # Send OTP (bypass consent check for security messages)
            if channel == MessageChannel.WHATSAPP:
                result = twilio.send_whatsapp(phone_number, message_text)
            else:
                result = twilio.send_sms(phone_number, message_text)

            # Log message
            MessagingService._log_message(
                user_id=user_id,
                phone_number=phone_number,
                message_text=message_text,
                template_name=template_name,
                channel=channel.value,
                priority=MessagePriority.CRITICAL.value,
                provider_message_id=result.get('provider_message_id'),
                status=result.get('status'),
                metadata={'otp_id': otp_id, 'purpose': purpose}
            )

            logger.info(f"OTP sent to user {user_id} via {channel.value}")

            return {
                'success': result['success'],
                'otp_id': otp_id,
                'expires_in_minutes': validity_minutes,
                'channel': channel.value
            }

        except Exception as e:
            logger.error(f"Failed to send OTP to {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def verify_otp(
        user_id: str,
        otp_code: str,
        purpose: str = 'verification',
        max_attempts: int = 3
    ) -> Dict:
        """
        Verify OTP code

        Args:
            user_id: User's email/ID
            otp_code: OTP code to verify
            purpose: Purpose of OTP
            max_attempts: Maximum verification attempts

        Returns:
            Dict with verification result
        """
        try:
            # Find OTP record
            otp_query = db.collection('otp_codes') \
                .where('user_id', '==', user_id) \
                .where('purpose', '==', purpose) \
                .where('verified', '==', False) \
                .order_by('created_at', direction='DESCENDING') \
                .limit(1)

            otp_docs = list(otp_query.get())

            if not otp_docs:
                logger.warning(f"No OTP found for user {user_id}, purpose {purpose}")
                return {
                    'valid': False,
                    'error': 'No OTP found or already verified'
                }

            otp_doc = otp_docs[0]
            otp_data = otp_doc.to_dict()
            otp_ref = db.collection('otp_codes').document(otp_doc.id)

            # Check expiration
            if datetime.utcnow() > otp_data['expires_at']:
                logger.warning(f"OTP expired for user {user_id}")
                return {
                    'valid': False,
                    'error': 'OTP has expired'
                }

            # Check attempts
            attempts = otp_data.get('attempts', 0)

            if attempts >= max_attempts:
                logger.warning(f"Max OTP attempts exceeded for user {user_id}")
                return {
                    'valid': False,
                    'error': 'Maximum verification attempts exceeded'
                }

            # Increment attempts
            otp_ref.update({'attempts': attempts + 1})

            # Verify code
            if otp_code == otp_data['code']:
                # Mark as verified
                otp_ref.update({
                    'verified': True,
                    'verified_at': SERVER_TIMESTAMP
                })

                logger.info(f"OTP verified successfully for user {user_id}")

                return {
                    'valid': True,
                    'otp_id': otp_doc.id
                }
            else:
                logger.warning(f"Invalid OTP code for user {user_id}")
                return {
                    'valid': False,
                    'error': 'Invalid OTP code',
                    'attempts_remaining': max_attempts - attempts - 1
                }

        except Exception as e:
            logger.error(f"Failed to verify OTP for {user_id}: {e}")
            return {
                'valid': False,
                'error': str(e)
            }

    # ═══════════════════════════════════════════════════════════════
    # MESSAGE TRACKING & HISTORY
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _log_message(
        user_id: str,
        phone_number: str,
        message_text: str,
        template_name: str,
        channel: str,
        priority: str,
        provider_message_id: Optional[str] = None,
        status: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Log message in database for tracking and compliance

        Returns:
            Message ID
        """
        try:
            # Sanitize message text for storage (remove actual content after X days)
            message_data = {
                'user_id': user_id,
                'phone_number': phone_number[-4:],  # Only store last 4 digits (HIPAA)
                'message_preview': message_text[:50],  # Store preview only
                'template_name': template_name,
                'channel': channel,
                'priority': priority,
                'provider_message_id': provider_message_id,
                'status': status,
                'error': error,
                'metadata': metadata or {},
                'created_at': SERVER_TIMESTAMP,
                'retention_days': 90  # Auto-delete after 90 days
            }

            message_ref = db.collection('message_log').add(message_data)
            message_id = message_ref[1].id

            return message_id

        except Exception as e:
            logger.error(f"Failed to log message: {e}")
            return None

    @staticmethod
    def get_message_history(
        user_id: str,
        limit: int = 50,
        channel: Optional[str] = None
    ) -> List[Dict]:
        """
        Get message history for a user

        Args:
            user_id: User's email/ID
            limit: Maximum messages to return
            channel: Filter by channel (optional)

        Returns:
            List of message records
        """
        try:
            query = db.collection('message_log') \
                .where('user_id', '==', user_id)

            if channel:
                query = query.where('channel', '==', channel)

            query = query.order_by('created_at', direction='DESCENDING') \
                .limit(limit)

            messages = []
            for doc in query.get():
                messages.append(doc.to_dict())

            return messages

        except Exception as e:
            logger.error(f"Failed to get message history for {user_id}: {e}")
            return []

    @staticmethod
    def update_message_status(message_id: str, new_status: str) -> bool:
        """
        Update message delivery status (called by webhook)

        Args:
            message_id: Message ID
            new_status: New delivery status

        Returns:
            True if successful
        """
        try:
            message_ref = db.collection('message_log').document(message_id)
            message_ref.update({
                'status': new_status,
                'status_updated_at': SERVER_TIMESTAMP
            })

            return True

        except Exception as e:
            logger.error(f"Failed to update message status: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _generate_otp(length: int = 6) -> str:
        """Generate secure OTP code"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])

    @staticmethod
    def cleanup_old_messages(days: int = 90) -> int:
        """
        Delete messages older than specified days (GDPR compliance)

        Args:
            days: Delete messages older than this

        Returns:
            Number of messages deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Query old messages
            old_messages = db.collection('message_log') \
                .where('created_at', '<', cutoff_date) \
                .get()

            deleted_count = 0

            for doc in old_messages:
                doc.reference.delete()
                deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old messages (>{days} days)")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old messages: {e}")
            return 0

    @staticmethod
    def cleanup_old_otps(hours: int = 24) -> int:
        """
        Delete expired OTP codes

        Args:
            hours: Delete OTPs older than this

        Returns:
            Number of OTPs deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(hours=hours)

            # Query old OTPs
            old_otps = db.collection('otp_codes') \
                .where('created_at', '<', cutoff_date) \
                .get()

            deleted_count = 0

            for doc in old_otps:
                doc.reference.delete()
                deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old OTP codes (>{hours} hours)")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old OTPs: {e}")
            return 0


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def send_appointment_reminder(user_id: str, appointment_id: str, hours_until: int = 24) -> Dict:
    """Send appointment reminder to user"""
    template_map = {
        24: 'APPOINTMENT_REMINDER_24H',
        2: 'APPOINTMENT_REMINDER_2H'
    }

    template_name = template_map.get(hours_until, 'APPOINTMENT_REMINDER_24H')
    app_link = DeepLinkGenerator.appointment_details(appointment_id)

    return MessagingService.send_with_fallback(
        user_id=user_id,
        template_name=template_name,
        priority=MessagePriority.HIGH,
        app_link=app_link
    )


def send_subscription_expiry(user_id: str, days_until_expiry: int) -> Dict:
    """Send subscription expiry notification"""
    app_link = DeepLinkGenerator.subscription_manage()

    return MessagingService.send_with_fallback(
        user_id=user_id,
        template_name='SUBSCRIPTION_EXPIRING',
        priority=MessagePriority.HIGH,
        days=days_until_expiry,
        app_link=app_link
    )


def send_payment_confirmation(user_id: str) -> Dict:
    """Send payment success notification"""
    app_link = DeepLinkGenerator.subscription_manage()

    return MessagingService.send_with_fallback(
        user_id=user_id,
        template_name='PAYMENT_SUCCESS',
        priority=MessagePriority.NORMAL,
        app_link=app_link
    )


# ═══════════════════════════════════════════════════════════════
# USAGE EXAMPLES
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Example 1: Send OTP
    result = MessagingService.send_otp(
        user_id='user@example.com',
        phone_number='+919876543210',
        purpose='login',
        channel=MessageChannel.SMS
    )
    print("OTP Result:", result)

    # Example 2: Verify OTP
    verify_result = MessagingService.verify_otp(
        user_id='user@example.com',
        otp_code='123456',
        purpose='login'
    )
    print("Verify Result:", verify_result)

    # Example 3: Send appointment reminder
    reminder_result = send_appointment_reminder(
        user_id='user@example.com',
        appointment_id='appt_123',
        hours_until=24
    )
    print("Reminder Result:", reminder_result)

    # Example 4: Get message history
    history = MessagingService.get_message_history('user@example.com', limit=10)
    print(f"Message History: {len(history)} messages")
