"""
GDPR/HIPAA-Compliant Consent Management
Tracks user consent for SMS and WhatsApp messaging
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List
from azure_cosmos_db import get_cosmos_db, SERVER_TIMESTAMP
from enum import Enum

logger = logging.getLogger(__name__)

# Initialize Cosmos DB
db = get_cosmos_db()


class ConsentType(Enum):
    """Types of messaging consent"""
    SMS = 'sms'
    WHATSAPP = 'whatsapp'
    MARKETING = 'marketing'  # Promotional messages
    TRANSACTIONAL = 'transactional'  # OTP, reminders, etc.


class ConsentSource(Enum):
    """Where consent was obtained"""
    APP_SETTINGS = 'app_settings'
    REGISTRATION = 'registration'
    WEB_SETTINGS = 'web_settings'
    PHONE_VERIFICATION = 'phone_verification'
    OPT_IN_MESSAGE = 'opt_in_message'


class ConsentManager:
    """
    Manage user messaging consent with GDPR/HIPAA compliance

    Features:
    - Explicit opt-in tracking
    - Consent source and timestamp recording
    - Opt-out mechanism (reply STOP)
    - Consent history audit trail
    - GDPR "right to be forgotten" support
    """

    @staticmethod
    def create_or_update_consent(
        user_id: str,
        phone_number: str,
        sms_consent: bool = False,
        whatsapp_consent: bool = False,
        marketing_consent: bool = False,
        source: str = ConsentSource.APP_SETTINGS.value,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Create or update user's messaging consent

        Args:
            user_id: User's email/ID
            phone_number: User's phone number (E.164 format)
            sms_consent: Consent for SMS messages
            whatsapp_consent: Consent for WhatsApp messages
            marketing_consent: Consent for marketing messages
            source: Where consent was obtained
            ip_address: IP address where consent was given (for audit)
            user_agent: User agent where consent was given

        Returns:
            True if successful, False otherwise
        """
        try:
            consent_ref = db.collection('messaging_consent').document(user_id)
            existing_consent = consent_ref.get()

            consent_data = {
                'user_id': user_id,
                'phone_number': phone_number,
                'sms_consent': sms_consent,
                'whatsapp_consent': whatsapp_consent,
                'marketing_consent': marketing_consent,
                'transactional_consent': True,  # Always true (critical messages)
                'updated_at': SERVER_TIMESTAMP,
                'consent_source': source,
                'ip_address': ip_address,
                'user_agent': user_agent
            }

            if existing_consent.exists:
                # Update existing consent
                consent_ref.update(consent_data)
                logger.info(f"Updated consent for user {user_id}")

                # Record consent change in audit trail
                ConsentManager._record_consent_change(
                    user_id=user_id,
                    action='updated',
                    old_consent=existing_consent.to_dict(),
                    new_consent=consent_data,
                    source=source
                )
            else:
                # Create new consent record
                consent_data['created_at'] = SERVER_TIMESTAMP
                consent_ref.set(consent_data)
                logger.info(f"Created consent for user {user_id}")

                # Record consent creation in audit trail
                ConsentManager._record_consent_change(
                    user_id=user_id,
                    action='created',
                    old_consent=None,
                    new_consent=consent_data,
                    source=source
                )

            return True

        except Exception as e:
            logger.error(f"Failed to create/update consent for user {user_id}: {e}")
            return False

    @staticmethod
    def get_consent(user_id: str) -> Optional[Dict]:
        """
        Get user's current messaging consent

        Args:
            user_id: User's email/ID

        Returns:
            Consent data dict or None if not found
        """
        try:
            consent_ref = db.collection('messaging_consent').document(user_id)
            consent = consent_ref.get()

            if consent.exists:
                return consent.to_dict()

            return None

        except Exception as e:
            logger.error(f"Failed to get consent for user {user_id}: {e}")
            return None

    @staticmethod
    def has_consent(user_id: str, consent_type: ConsentType) -> bool:
        """
        Check if user has given specific consent

        Args:
            user_id: User's email/ID
            consent_type: Type of consent to check

        Returns:
            True if user has consented, False otherwise
        """
        consent_data = ConsentManager.get_consent(user_id)

        if not consent_data:
            return False

        # Map consent type to field name
        consent_field_map = {
            ConsentType.SMS: 'sms_consent',
            ConsentType.WHATSAPP: 'whatsapp_consent',
            ConsentType.MARKETING: 'marketing_consent',
            ConsentType.TRANSACTIONAL: 'transactional_consent'
        }

        field_name = consent_field_map.get(consent_type)
        return consent_data.get(field_name, False)

    @staticmethod
    def opt_out(
        user_id: str,
        consent_type: ConsentType,
        source: str = 'sms_reply'
    ) -> bool:
        """
        Opt-out user from specific message type

        Args:
            user_id: User's email/ID
            consent_type: Type of consent to revoke
            source: How opt-out was initiated (e.g., 'sms_reply', 'app_settings')

        Returns:
            True if successful, False otherwise
        """
        try:
            consent_ref = db.collection('messaging_consent').document(user_id)
            existing_consent = consent_ref.get()

            if not existing_consent.exists:
                logger.warning(f"Cannot opt-out: No consent record for user {user_id}")
                return False

            # Map consent type to field name
            consent_field_map = {
                ConsentType.SMS: 'sms_consent',
                ConsentType.WHATSAPP: 'whatsapp_consent',
                ConsentType.MARKETING: 'marketing_consent'
            }

            field_name = consent_field_map.get(consent_type)

            if not field_name:
                logger.error(f"Invalid consent type for opt-out: {consent_type}")
                return False

            # Update consent
            update_data = {
                field_name: False,
                'updated_at': SERVER_TIMESTAMP,
                f'{field_name}_opted_out_at': SERVER_TIMESTAMP,
                'opt_out_source': source
            }

            consent_ref.update(update_data)

            # Record opt-out in audit trail
            ConsentManager._record_consent_change(
                user_id=user_id,
                action='opt_out',
                old_consent=existing_consent.to_dict(),
                new_consent={field_name: False},
                source=source
            )

            logger.info(f"User {user_id} opted out of {consent_type.value} via {source}")
            return True

        except Exception as e:
            logger.error(f"Failed to opt-out user {user_id}: {e}")
            return False

    @staticmethod
    def opt_in(
        user_id: str,
        consent_type: ConsentType,
        source: str = 'app_settings'
    ) -> bool:
        """
        Opt-in user to specific message type

        Args:
            user_id: User's email/ID
            consent_type: Type of consent to grant
            source: How opt-in was initiated

        Returns:
            True if successful, False otherwise
        """
        try:
            consent_ref = db.collection('messaging_consent').document(user_id)
            existing_consent = consent_ref.get()

            if not existing_consent.exists:
                logger.warning(f"Cannot opt-in: No consent record for user {user_id}")
                return False

            # Map consent type to field name
            consent_field_map = {
                ConsentType.SMS: 'sms_consent',
                ConsentType.WHATSAPP: 'whatsapp_consent',
                ConsentType.MARKETING: 'marketing_consent'
            }

            field_name = consent_field_map.get(consent_type)

            if not field_name:
                logger.error(f"Invalid consent type for opt-in: {consent_type}")
                return False

            # Update consent
            update_data = {
                field_name: True,
                'updated_at': SERVER_TIMESTAMP,
                f'{field_name}_opted_in_at': SERVER_TIMESTAMP,
                'opt_in_source': source
            }

            consent_ref.update(update_data)

            # Record opt-in in audit trail
            ConsentManager._record_consent_change(
                user_id=user_id,
                action='opt_in',
                old_consent=existing_consent.to_dict(),
                new_consent={field_name: True},
                source=source
            )

            logger.info(f"User {user_id} opted in to {consent_type.value} via {source}")
            return True

        except Exception as e:
            logger.error(f"Failed to opt-in user {user_id}: {e}")
            return False

    @staticmethod
    def get_phone_number(user_id: str) -> Optional[str]:
        """
        Get user's registered phone number

        Args:
            user_id: User's email/ID

        Returns:
            Phone number or None if not found
        """
        consent_data = ConsentManager.get_consent(user_id)

        if consent_data:
            return consent_data.get('phone_number')

        return None

    @staticmethod
    def _record_consent_change(
        user_id: str,
        action: str,
        old_consent: Optional[Dict],
        new_consent: Dict,
        source: str
    ) -> None:
        """
        Record consent change in audit trail (GDPR requirement)

        Args:
            user_id: User's email/ID
            action: Action performed (created, updated, opt_in, opt_out)
            old_consent: Previous consent state
            new_consent: New consent state
            source: Source of change
        """
        try:
            audit_data = {
                'user_id': user_id,
                'action': action,
                'old_consent': old_consent,
                'new_consent': new_consent,
                'source': source,
                'timestamp': SERVER_TIMESTAMP
            }

            db.collection('consent_audit_trail').add(audit_data)

        except Exception as e:
            logger.error(f"Failed to record consent change audit: {e}")

    @staticmethod
    def get_consent_history(user_id: str, limit: int = 50) -> List[Dict]:
        """
        Get consent change history for a user (GDPR right to access)

        Args:
            user_id: User's email/ID
            limit: Maximum number of records to return

        Returns:
            List of consent change records
        """
        try:
            audit_query = db.collection('consent_audit_trail') \
                .where('user_id', '==', user_id) \
                .order_by('timestamp', direction='DESCENDING') \
                .limit(limit)

            history = []
            for doc in audit_query.get():
                history.append(doc.to_dict())

            return history

        except Exception as e:
            logger.error(f"Failed to get consent history for user {user_id}: {e}")
            return []

    @staticmethod
    def delete_consent_data(user_id: str) -> bool:
        """
        Delete all consent data for a user (GDPR right to be forgotten)

        Args:
            user_id: User's email/ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete consent record
            consent_ref = db.collection('messaging_consent').document(user_id)
            consent_ref.delete()

            # Delete audit trail (or keep for compliance - check your legal requirements)
            # Note: Some jurisdictions require keeping audit trail even after deletion
            # Consult legal counsel before implementing this

            logger.info(f"Deleted consent data for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete consent data for user {user_id}: {e}")
            return False

    @staticmethod
    def bulk_opt_out(phone_number: str) -> bool:
        """
        Opt-out all users with a specific phone number (e.g., after STOP reply)

        Args:
            phone_number: Phone number to opt-out

        Returns:
            True if successful, False otherwise
        """
        try:
            # Find all users with this phone number
            consent_query = db.collection('messaging_consent') \
                .where('phone_number', '==', phone_number)

            users_opted_out = 0

            for doc in consent_query.get():
                user_id = doc.id

                # Opt-out from SMS and WhatsApp
                ConsentManager.opt_out(user_id, ConsentType.SMS, source='sms_stop_reply')
                ConsentManager.opt_out(user_id, ConsentType.WHATSAPP, source='sms_stop_reply')

                users_opted_out += 1

            logger.info(f"Opted out {users_opted_out} users with phone {phone_number[-4:]}")
            return True

        except Exception as e:
            logger.error(f"Failed to bulk opt-out phone number: {e}")
            return False


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def can_send_sms(user_id: str) -> bool:
    """Quick check if user can receive SMS"""
    return ConsentManager.has_consent(user_id, ConsentType.SMS)


def can_send_whatsapp(user_id: str) -> bool:
    """Quick check if user can receive WhatsApp"""
    return ConsentManager.has_consent(user_id, ConsentType.WHATSAPP)


def can_send_marketing(user_id: str) -> bool:
    """Quick check if user can receive marketing messages"""
    return ConsentManager.has_consent(user_id, ConsentType.MARKETING)


# ═══════════════════════════════════════════════════════════════
# USAGE EXAMPLES
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Example 1: Create consent during registration
    ConsentManager.create_or_update_consent(
        user_id='user@example.com',
        phone_number='+919876543210',
        sms_consent=True,
        whatsapp_consent=True,
        marketing_consent=False,
        source=ConsentSource.REGISTRATION.value,
        ip_address='192.168.1.1'
    )

    # Example 2: Check consent before sending message
    if can_send_whatsapp('user@example.com'):
        print("User has consented to WhatsApp messages")

    # Example 3: Opt-out (e.g., after STOP reply)
    ConsentManager.opt_out('user@example.com', ConsentType.SMS, source='sms_reply')

    # Example 4: Get consent history
    history = ConsentManager.get_consent_history('user@example.com')
    print(f"Consent changes: {len(history)}")

    # Example 5: GDPR deletion
    # ConsentManager.delete_consent_data('user@example.com')
