"""
Twilio Webhook Handlers for Incoming Messages
Handles STOP/START replies, message status updates, and two-way messaging
"""

import logging
from flask import request, jsonify
from typing import Dict, Optional
from datetime import datetime

from consent_manager import ConsentManager, ConsentType
from message_templates import MessageTemplates
from twilio_provider import get_twilio_provider
from azure_cosmos_db import get_cosmos_db, SERVER_TIMESTAMP

logger = logging.getLogger(__name__)

# Initialize services
twilio = get_twilio_provider()
db = get_cosmos_db()


class TwilioWebhooks:
    """
    Handle Twilio webhooks for SMS and WhatsApp

    Webhooks:
    - Incoming message webhook (handle replies)
    - Message status webhook (delivery updates)
    - Opt-in/opt-out handling (STOP/START keywords)
    """

    # STOP keywords for opt-out (Twilio standard)
    OPT_OUT_KEYWORDS = ['STOP', 'STOPALL', 'UNSUBSCRIBE', 'CANCEL', 'END', 'QUIT']

    # START keywords for opt-in
    OPT_IN_KEYWORDS = ['START', 'YES', 'UNSTOP']

    @staticmethod
    def handle_incoming_message() -> tuple:
        """
        Handle incoming SMS/WhatsApp message from Twilio

        Webhook URL: POST /webhooks/twilio/incoming
        Twilio sends: From, Body, To, MessageSid, etc.

        Returns:
            TwiML response
        """
        try:
            # Get request data from Twilio
            from_number = request.form.get('From', '').replace('whatsapp:', '')
            message_body = request.form.get('Body', '').strip()
            message_sid = request.form.get('MessageSid', '')
            to_number = request.form.get('To', '').replace('whatsapp:', '')

            logger.info(f"Incoming message from {from_number[-4:]}: {message_body[:50]}")

            # Determine channel (SMS or WhatsApp)
            channel = 'whatsapp' if 'whatsapp:' in request.form.get('From', '') else 'sms'

            # Check for opt-out keywords
            message_upper = message_body.upper()

            if any(keyword in message_upper for keyword in TwilioWebhooks.OPT_OUT_KEYWORDS):
                return TwilioWebhooks._handle_opt_out(from_number, channel)

            # Check for opt-in keywords
            if any(keyword in message_upper for keyword in TwilioWebhooks.OPT_IN_KEYWORDS):
                return TwilioWebhooks._handle_opt_in(from_number, channel)

            # Handle two-way message
            return TwilioWebhooks._handle_two_way_message(
                from_number=from_number,
                message_body=message_body,
                message_sid=message_sid,
                channel=channel
            )

        except Exception as e:
            logger.error(f"Error handling incoming message: {e}")
            return TwilioWebhooks._twiml_response("We're experiencing technical difficulties. Please try again later.")

    @staticmethod
    def handle_status_callback() -> tuple:
        """
        Handle message delivery status update from Twilio

        Webhook URL: POST /webhooks/twilio/status
        Twilio sends: MessageSid, MessageStatus, ErrorCode, etc.

        Returns:
            JSON response
        """
        try:
            message_sid = request.form.get('MessageSid', '')
            message_status = request.form.get('MessageStatus', '')
            error_code = request.form.get('ErrorCode')
            error_message = request.form.get('ErrorMessage')

            logger.info(f"Status update for {message_sid}: {message_status}")

            # Find message in database by provider_message_id
            message_query = db.collection('message_log') \
                .where('provider_message_id', '==', message_sid) \
                .limit(1)

            messages = list(message_query.get())

            if messages:
                message_doc = messages[0]
                message_ref = db.collection('message_log').document(message_doc.id)

                # Update status
                update_data = {
                    'status': message_status,
                    'status_updated_at': SERVER_TIMESTAMP
                }

                if error_code:
                    update_data['error_code'] = error_code
                    update_data['error_message'] = error_message

                message_ref.update(update_data)

                logger.info(f"Updated message {message_doc.id} status to {message_status}")

            return jsonify({'success': True}), 200

        except Exception as e:
            logger.error(f"Error handling status callback: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @staticmethod
    def _handle_opt_out(phone_number: str, channel: str) -> tuple:
        """
        Handle opt-out request (STOP keyword)

        Args:
            phone_number: Phone number opting out
            channel: Channel (sms or whatsapp)

        Returns:
            TwiML response
        """
        try:
            # Opt-out from all users with this phone number
            ConsentManager.bulk_opt_out(phone_number)

            logger.info(f"Processed opt-out for {phone_number[-4:]} via {channel}")

            # Send confirmation (required by regulations)
            response_text = MessageTemplates.render('OPT_OUT_CONFIRMATION')

            return TwilioWebhooks._twiml_response(response_text)

        except Exception as e:
            logger.error(f"Error handling opt-out: {e}")
            return TwilioWebhooks._twiml_response("Your request has been processed.")

    @staticmethod
    def _handle_opt_in(phone_number: str, channel: str) -> tuple:
        """
        Handle opt-in request (START keyword)

        Args:
            phone_number: Phone number opting in
            channel: Channel (sms or whatsapp)

        Returns:
            TwiML response
        """
        try:
            # Find users with this phone number
            consent_query = db.collection('messaging_consent') \
                .where('phone_number', '==', phone_number) \
                .limit(5)

            users_opted_in = 0

            for doc in consent_query.get():
                user_id = doc.id
                consent_type = ConsentType.WHATSAPP if channel == 'whatsapp' else ConsentType.SMS

                # Opt-in user
                ConsentManager.opt_in(user_id, consent_type, source='message_reply')
                users_opted_in += 1

            logger.info(f"Processed opt-in for {phone_number[-4:]} via {channel}")

            # Send confirmation
            response_text = MessageTemplates.render('OPT_IN_CONFIRMATION')

            return TwilioWebhooks._twiml_response(response_text)

        except Exception as e:
            logger.error(f"Error handling opt-in: {e}")
            return TwilioWebhooks._twiml_response("Your request has been processed.")

    @staticmethod
    def _handle_two_way_message(
        from_number: str,
        message_body: str,
        message_sid: str,
        channel: str
    ) -> tuple:
        """
        Handle two-way messaging (patient reply)

        Args:
            from_number: Sender's phone number
            message_body: Message text
            message_sid: Twilio message SID
            channel: Channel (sms or whatsapp)

        Returns:
            TwiML response
        """
        try:
            # Find user by phone number
            consent_query = db.collection('messaging_consent') \
                .where('phone_number', '==', from_number) \
                .limit(1)

            users = list(consent_query.get())

            if not users:
                logger.warning(f"Received message from unknown number {from_number[-4:]}")
                return TwilioWebhooks._twiml_response(
                    "We couldn't identify your account. Please contact support."
                )

            user_doc = users[0]
            user_id = user_doc.id

            # Store incoming message
            TwilioWebhooks._store_incoming_message(
                user_id=user_id,
                from_number=from_number,
                message_body=message_body,
                message_sid=message_sid,
                channel=channel
            )

            # Create in-app notification for provider
            TwilioWebhooks._notify_provider_of_message(
                user_id=user_id,
                message_preview=message_body[:100]
            )

            # Send auto-reply
            response_text = MessageTemplates.render('MESSAGE_RECEIVED')

            return TwilioWebhooks._twiml_response(response_text)

        except Exception as e:
            logger.error(f"Error handling two-way message: {e}")
            return TwilioWebhooks._twiml_response("Thank you for your message.")

    @staticmethod
    def _store_incoming_message(
        user_id: str,
        from_number: str,
        message_body: str,
        message_sid: str,
        channel: str
    ) -> None:
        """
        Store incoming message in database

        Args:
            user_id: User's ID
            from_number: Sender's phone number
            message_body: Message text
            message_sid: Twilio message SID
            channel: Channel (sms or whatsapp)
        """
        try:
            message_data = {
                'user_id': user_id,
                'direction': 'inbound',
                'from_number': from_number[-4:],  # Only last 4 digits for HIPAA
                'message_body': message_body[:500],  # Limit storage
                'provider_message_id': message_sid,
                'channel': channel,
                'created_at': SERVER_TIMESTAMP,
                'read': False,
                'retention_days': 90
            }

            db.collection('incoming_messages').add(message_data)

            logger.info(f"Stored incoming message from user {user_id}")

        except Exception as e:
            logger.error(f"Failed to store incoming message: {e}")

    @staticmethod
    def _notify_provider_of_message(user_id: str, message_preview: str) -> None:
        """
        Create in-app notification for healthcare provider

        Args:
            user_id: Patient's user ID
            message_preview: Preview of message
        """
        try:
            # Import here to avoid circular dependency
            from notification_service import NotificationService

            # Get user details
            user_ref = db.collection('users').document(user_id)
            user_data = user_ref.get().to_dict()

            patient_name = user_data.get('name', 'A patient')

            # Create notification
            NotificationService.create_notification(
                user_id=user_id,
                title='New Message Received',
                message=f'{patient_name} sent you a message',
                notification_type='info',
                category='patient',
                action_url=f'/messages?user={user_id}'
            )

        except Exception as e:
            logger.error(f"Failed to create message notification: {e}")

    @staticmethod
    def _twiml_response(message: str) -> tuple:
        """
        Create TwiML response for Twilio

        Args:
            message: Response message to send

        Returns:
            TwiML XML response
        """
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{message}</Message>
</Response>"""

        return twiml, 200, {'Content-Type': 'text/xml'}


# ═══════════════════════════════════════════════════════════════
# FLASK ROUTE REGISTRATION (to be added to main.py)
# ═══════════════════════════════════════════════════════════════

def register_messaging_webhooks(app):
    """
    Register Twilio webhook routes

    Add to main.py:
        from messaging_webhooks import register_messaging_webhooks
        register_messaging_webhooks(app)

    Configure in Twilio Console:
        Messaging > Settings > Webhook URLs:
        - Incoming Messages: https://yourdomain.com/webhooks/twilio/incoming
        - Status Callback: https://yourdomain.com/webhooks/twilio/status
    """
    from flask import Blueprint

    webhooks_bp = Blueprint('messaging_webhooks', __name__, url_prefix='/webhooks/twilio')

    @webhooks_bp.route('/incoming', methods=['POST'])
    def incoming_message():
        """Handle incoming SMS/WhatsApp message"""
        return TwilioWebhooks.handle_incoming_message()

    @webhooks_bp.route('/status', methods=['POST'])
    def status_callback():
        """Handle message delivery status update"""
        return TwilioWebhooks.handle_status_callback()

    # Register blueprint
    app.register_blueprint(webhooks_bp)

    logger.info("Messaging webhooks registered")


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def get_incoming_messages(user_id: str, limit: int = 50) -> list:
    """
    Get incoming messages for a user

    Args:
        user_id: User's ID
        limit: Maximum messages to return

    Returns:
        List of incoming messages
    """
    try:
        messages_query = db.collection('incoming_messages') \
            .where('user_id', '==', user_id) \
            .order_by('created_at', direction='DESCENDING') \
            .limit(limit)

        messages = []
        for doc in messages_query.get():
            messages.append(doc.to_dict())

        return messages

    except Exception as e:
        logger.error(f"Failed to get incoming messages for {user_id}: {e}")
        return []


def mark_message_read(message_id: str) -> bool:
    """
    Mark incoming message as read

    Args:
        message_id: Message ID

    Returns:
        True if successful
    """
    try:
        message_ref = db.collection('incoming_messages').document(message_id)
        message_ref.update({
            'read': True,
            'read_at': SERVER_TIMESTAMP
        })

        return True

    except Exception as e:
        logger.error(f"Failed to mark message as read: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# TESTING HELPERS
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Twilio Webhooks Module")
    print("\nWebhook URLs to configure in Twilio Console:")
    print("1. Incoming Messages: POST /webhooks/twilio/incoming")
    print("2. Status Callback: POST /webhooks/twilio/status")
    print("\nSupported keywords:")
    print(f"- Opt-out: {', '.join(TwilioWebhooks.OPT_OUT_KEYWORDS)}")
    print(f"- Opt-in: {', '.join(TwilioWebhooks.OPT_IN_KEYWORDS)}")
