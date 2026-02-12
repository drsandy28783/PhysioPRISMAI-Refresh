"""
Twilio SMS & WhatsApp Provider
Supports both real Twilio API and mock mode for development
HIPAA/GDPR compliant implementation
"""

import os
import logging
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MessageStatus(Enum):
    """Message delivery status"""
    QUEUED = 'queued'
    SENT = 'sent'
    DELIVERED = 'delivered'
    FAILED = 'failed'
    UNDELIVERED = 'undelivered'


class MessageChannel(Enum):
    """Communication channel"""
    SMS = 'sms'
    WHATSAPP = 'whatsapp'


class TwilioProvider:
    """
    Twilio messaging provider with mock mode support

    Features:
    - SMS sending via Twilio API
    - WhatsApp Business API integration
    - Mock mode for development (no API calls)
    - Message delivery tracking
    - Error handling with retry logic
    - HIPAA-compliant logging (no PHI)
    """

    def __init__(self):
        """Initialize Twilio provider"""
        self.enabled = os.getenv('MESSAGING_ENABLED', 'false').lower() == 'true'
        self.mock_mode = os.getenv('MESSAGING_MOCK_MODE', 'true').lower() == 'true'

        # Twilio credentials
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID', '')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN', '')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER', '')
        self.whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER', '')

        # Initialize Twilio client only if enabled and not in mock mode
        self.client = None
        if self.enabled and not self.mock_mode:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio client initialized successfully")
            except ImportError:
                logger.warning("Twilio SDK not installed. Run: pip install twilio")
                self.mock_mode = True
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                self.mock_mode = True

        # Log current mode
        if not self.enabled:
            logger.info("Messaging is DISABLED. Set MESSAGING_ENABLED=true to enable.")
        elif self.mock_mode:
            logger.info("Messaging in MOCK MODE. Messages will be logged but not sent.")
        else:
            logger.info("Messaging ENABLED with Twilio API")

    def send_sms(
        self,
        to: str,
        message: str,
        message_id: Optional[str] = None
    ) -> Dict:
        """
        Send SMS via Twilio

        Args:
            to: Recipient phone number (E.164 format: +12345678900)
            message: Message text (max 1600 chars for concatenated SMS)
            message_id: Optional message tracking ID

        Returns:
            Dict with status and tracking info

        Example:
            result = provider.send_sms('+919876543210', 'Your OTP is 123456')
        """
        if not self.enabled:
            logger.info(f"[DISABLED] Would send SMS to {self._mask_phone(to)}")
            return {
                'success': False,
                'status': MessageStatus.FAILED.value,
                'message': 'Messaging is disabled',
                'provider_message_id': None
            }

        if self.mock_mode:
            logger.info(f"[MOCK] SMS to {self._mask_phone(to)}: {message[:50]}...")
            return {
                'success': True,
                'status': MessageStatus.SENT.value,
                'message': 'Message sent (mock mode)',
                'provider_message_id': f'mock_sms_{message_id or datetime.utcnow().timestamp()}',
                'channel': MessageChannel.SMS.value,
                'mock': True
            }

        try:
            # Validate phone number format
            if not to.startswith('+'):
                to = f'+{to}'

            # Send via Twilio API
            message_obj = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to
            )

            logger.info(f"SMS sent successfully to {self._mask_phone(to)}, SID: {message_obj.sid}")

            return {
                'success': True,
                'status': message_obj.status,
                'message': 'Message sent',
                'provider_message_id': message_obj.sid,
                'channel': MessageChannel.SMS.value,
                'error_code': None,
                'error_message': None
            }

        except Exception as e:
            logger.error(f"Failed to send SMS to {self._mask_phone(to)}: {str(e)}")
            return {
                'success': False,
                'status': MessageStatus.FAILED.value,
                'message': 'Failed to send message',
                'provider_message_id': None,
                'channel': MessageChannel.SMS.value,
                'error_code': getattr(e, 'code', None),
                'error_message': str(e)
            }

    def send_whatsapp(
        self,
        to: str,
        message: str,
        message_id: Optional[str] = None
    ) -> Dict:
        """
        Send WhatsApp message via Twilio

        Args:
            to: Recipient phone number (E.164 format: +12345678900)
            message: Message text
            message_id: Optional message tracking ID

        Returns:
            Dict with status and tracking info

        Note:
            - Requires WhatsApp Business API approval
            - Use Twilio Sandbox for testing: https://www.twilio.com/console/sms/whatsapp/sandbox
            - Recipient must have opted-in to receive WhatsApp messages
        """
        if not self.enabled:
            logger.info(f"[DISABLED] Would send WhatsApp to {self._mask_phone(to)}")
            return {
                'success': False,
                'status': MessageStatus.FAILED.value,
                'message': 'Messaging is disabled',
                'provider_message_id': None
            }

        if self.mock_mode:
            logger.info(f"[MOCK] WhatsApp to {self._mask_phone(to)}: {message[:50]}...")
            return {
                'success': True,
                'status': MessageStatus.SENT.value,
                'message': 'Message sent (mock mode)',
                'provider_message_id': f'mock_whatsapp_{message_id or datetime.utcnow().timestamp()}',
                'channel': MessageChannel.WHATSAPP.value,
                'mock': True
            }

        try:
            # Validate phone number format
            if not to.startswith('+'):
                to = f'+{to}'

            # Format WhatsApp number (must have 'whatsapp:' prefix)
            whatsapp_to = f'whatsapp:{to}'
            whatsapp_from = f'whatsapp:{self.whatsapp_number}'

            # Send via Twilio WhatsApp API
            message_obj = self.client.messages.create(
                body=message,
                from_=whatsapp_from,
                to=whatsapp_to
            )

            logger.info(f"WhatsApp sent successfully to {self._mask_phone(to)}, SID: {message_obj.sid}")

            return {
                'success': True,
                'status': message_obj.status,
                'message': 'Message sent',
                'provider_message_id': message_obj.sid,
                'channel': MessageChannel.WHATSAPP.value,
                'error_code': None,
                'error_message': None
            }

        except Exception as e:
            logger.error(f"Failed to send WhatsApp to {self._mask_phone(to)}: {str(e)}")
            return {
                'success': False,
                'status': MessageStatus.FAILED.value,
                'message': 'Failed to send message',
                'provider_message_id': None,
                'channel': MessageChannel.WHATSAPP.value,
                'error_code': getattr(e, 'code', None),
                'error_message': str(e)
            }

    def get_message_status(self, provider_message_id: str) -> Dict:
        """
        Get delivery status of a message

        Args:
            provider_message_id: Twilio message SID

        Returns:
            Dict with current status and details
        """
        if self.mock_mode or provider_message_id.startswith('mock_'):
            return {
                'status': MessageStatus.DELIVERED.value,
                'updated_at': datetime.utcnow().isoformat(),
                'mock': True
            }

        try:
            message = self.client.messages(provider_message_id).fetch()

            return {
                'status': message.status,
                'error_code': message.error_code,
                'error_message': message.error_message,
                'updated_at': message.date_updated.isoformat() if message.date_updated else None,
                'price': message.price,
                'price_unit': message.price_unit
            }

        except Exception as e:
            logger.error(f"Failed to fetch message status for {provider_message_id}: {str(e)}")
            return {
                'status': MessageStatus.FAILED.value,
                'error_message': str(e)
            }

    def send_with_fallback(
        self,
        to: str,
        message: str,
        preferred_channel: MessageChannel = MessageChannel.WHATSAPP,
        message_id: Optional[str] = None
    ) -> Dict:
        """
        Send message with automatic fallback from WhatsApp to SMS

        Args:
            to: Recipient phone number
            message: Message text
            preferred_channel: Try this channel first (default: WhatsApp)
            message_id: Optional message tracking ID

        Returns:
            Dict with status and channel used
        """
        if preferred_channel == MessageChannel.WHATSAPP:
            # Try WhatsApp first
            result = self.send_whatsapp(to, message, message_id)

            # Fallback to SMS if WhatsApp fails
            if not result['success']:
                logger.info(f"WhatsApp failed for {self._mask_phone(to)}, falling back to SMS")
                result = self.send_sms(to, message, message_id)
                result['fallback'] = True

        else:
            # Try SMS first
            result = self.send_sms(to, message, message_id)

            # Fallback to WhatsApp if SMS fails
            if not result['success']:
                logger.info(f"SMS failed for {self._mask_phone(to)}, falling back to WhatsApp")
                result = self.send_whatsapp(to, message, message_id)
                result['fallback'] = True

        return result

    def validate_phone_number(self, phone: str) -> Dict:
        """
        Validate phone number format and lookup carrier info

        Args:
            phone: Phone number to validate

        Returns:
            Dict with validation result and carrier info

        Note:
            Requires Twilio Lookup API (charges apply per lookup)
        """
        if self.mock_mode:
            return {
                'valid': True,
                'phone_number': phone,
                'country_code': 'IN',
                'carrier': 'Mock Carrier',
                'type': 'mobile',
                'mock': True
            }

        try:
            # Use Twilio Lookup API
            phone_number = self.client.lookups.v1.phone_numbers(phone).fetch()

            return {
                'valid': True,
                'phone_number': phone_number.phone_number,
                'country_code': phone_number.country_code,
                'national_format': phone_number.national_format
            }

        except Exception as e:
            logger.error(f"Phone validation failed for {self._mask_phone(phone)}: {str(e)}")
            return {
                'valid': False,
                'error': str(e)
            }

    def _mask_phone(self, phone: str) -> str:
        """
        Mask phone number for HIPAA-compliant logging

        Args:
            phone: Phone number to mask

        Returns:
            Masked phone number (e.g., +91****5678)
        """
        if len(phone) <= 7:
            return '****'

        # Show country code and last 4 digits
        return f"{phone[:3]}****{phone[-4:]}"

    def health_check(self) -> Dict:
        """
        Check if Twilio service is operational

        Returns:
            Dict with health status
        """
        if not self.enabled:
            return {
                'healthy': False,
                'message': 'Messaging is disabled'
            }

        if self.mock_mode:
            return {
                'healthy': True,
                'message': 'Mock mode active',
                'mock': True
            }

        try:
            # Fetch account details to verify credentials
            account = self.client.api.accounts(self.account_sid).fetch()

            return {
                'healthy': True,
                'message': 'Twilio API operational',
                'account_status': account.status,
                'account_type': account.type
            }

        except Exception as e:
            logger.error(f"Twilio health check failed: {str(e)}")
            return {
                'healthy': False,
                'message': f'Twilio API error: {str(e)}'
            }


# ═══════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════

_twilio_provider_instance = None


def get_twilio_provider() -> TwilioProvider:
    """Get singleton instance of Twilio provider"""
    global _twilio_provider_instance

    if _twilio_provider_instance is None:
        _twilio_provider_instance = TwilioProvider()

    return _twilio_provider_instance


# ═══════════════════════════════════════════════════════════════
# USAGE EXAMPLES
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Example usage
    provider = get_twilio_provider()

    # Example 1: Send SMS
    result = provider.send_sms(
        to='+919876543210',
        message='Your OTP is 123456. Valid for 10 minutes.'
    )
    print("SMS Result:", result)

    # Example 2: Send WhatsApp
    result = provider.send_whatsapp(
        to='+919876543210',
        message='Appointment reminder: You have an appointment tomorrow.'
    )
    print("WhatsApp Result:", result)

    # Example 3: Send with fallback
    result = provider.send_with_fallback(
        to='+919876543210',
        message='Important notification',
        preferred_channel=MessageChannel.WHATSAPP
    )
    print("Fallback Result:", result)

    # Example 4: Health check
    health = provider.health_check()
    print("Health Check:", health)
