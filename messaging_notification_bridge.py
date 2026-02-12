"""
Bridge between in-app notifications and SMS/WhatsApp messaging
Automatically sends important notifications via SMS/WhatsApp
"""

import logging
from typing import Dict, Optional
from messaging_service import MessagingService, MessagePriority, MessageChannel
from message_templates import DeepLinkGenerator
from consent_manager import ConsentManager, ConsentType

logger = logging.getLogger(__name__)


class MessagingNotificationBridge:
    """
    Bridge between notification system and messaging

    Automatically sends SMS/WhatsApp for critical notifications:
    - Subscription expiring/expired
    - Payment failed
    - Quota exceeded
    - Account status changes
    - Security alerts
    """

    # Map notification categories to whether they should trigger SMS/WhatsApp
    NOTIFICATION_MESSAGING_RULES = {
        'subscription': {
            'send_sms': True,
            'priority': MessagePriority.HIGH,
            'keywords': ['expir', 'renew', 'cancel']
        },
        'payment': {
            'send_sms': True,
            'priority': MessagePriority.HIGH,
            'keywords': ['failed', 'success', 'receipt']
        },
        'quota': {
            'send_sms': True,
            'priority': MessagePriority.NORMAL,
            'keywords': ['exceeded', 'warning', '80%']
        },
        'security': {
            'send_sms': True,
            'priority': MessagePriority.CRITICAL,
            'keywords': ['alert', 'unusual', 'suspicious']
        },
        'system': {
            'send_sms': False,  # System notifications usually in-app only
            'priority': MessagePriority.LOW,
            'keywords': []
        },
        'patient': {
            'send_sms': False,  # Patient updates usually in-app only
            'priority': MessagePriority.LOW,
            'keywords': []
        }
    }

    @staticmethod
    def send_notification_via_messaging(
        user_id: str,
        notification_category: str,
        notification_title: str,
        notification_message: str,
        action_url: Optional[str] = None
    ) -> Dict:
        """
        Send notification via SMS/WhatsApp if applicable

        Args:
            user_id: User's email/ID
            notification_category: Category (subscription, payment, etc.)
            notification_title: Notification title
            notification_message: Notification message
            action_url: Optional action URL

        Returns:
            Dict with send status
        """
        try:
            # Check if this category should trigger messaging
            rules = MessagingNotificationBridge.NOTIFICATION_MESSAGING_RULES.get(
                notification_category,
                {'send_sms': False}
            )

            if not rules['send_sms']:
                logger.debug(f"Category '{notification_category}' does not trigger messaging")
                return {
                    'sent': False,
                    'reason': 'Category does not trigger messaging'
                }

            # Check if user has consented
            has_sms_consent = ConsentManager.has_consent(user_id, ConsentType.SMS)
            has_whatsapp_consent = ConsentManager.has_consent(user_id, ConsentType.WHATSAPP)

            if not (has_sms_consent or has_whatsapp_consent):
                logger.debug(f"User {user_id} has not consented to messaging")
                return {
                    'sent': False,
                    'reason': 'User has not consented'
                }

            # Map notification to appropriate template
            template_name = MessagingNotificationBridge._select_template(
                notification_category,
                notification_title,
                notification_message
            )

            if not template_name:
                logger.warning(f"No template found for notification: {notification_title}")
                return {
                    'sent': False,
                    'reason': 'No matching template'
                }

            # Generate app link
            app_link = action_url or DeepLinkGenerator.dashboard()

            # Extract template variables from notification
            template_vars = MessagingNotificationBridge._extract_template_vars(
                notification_category,
                notification_message,
                app_link
            )

            # Send message
            result = MessagingService.send_with_fallback(
                user_id=user_id,
                template_name=template_name,
                priority=rules['priority'],
                **template_vars
            )

            logger.info(f"Sent notification via messaging to {user_id}: {template_name}")

            return {
                'sent': result['success'],
                'channel': result.get('channel'),
                'message_id': result.get('message_id'),
                'template': template_name
            }

        except Exception as e:
            logger.error(f"Failed to send notification via messaging: {e}")
            return {
                'sent': False,
                'error': str(e)
            }

    @staticmethod
    def _select_template(
        category: str,
        title: str,
        message: str
    ) -> Optional[str]:
        """
        Select appropriate message template based on notification

        Args:
            category: Notification category
            title: Notification title
            message: Notification message

        Returns:
            Template name or None
        """
        combined_text = f"{title} {message}".lower()

        # Subscription notifications
        if category == 'subscription':
            if 'expir' in combined_text and 'days' in combined_text:
                return 'SUBSCRIPTION_EXPIRING'
            elif 'expired' in combined_text:
                return 'SUBSCRIPTION_EXPIRED'

        # Payment notifications
        elif category == 'payment':
            if 'success' in combined_text or 'received' in combined_text:
                return 'PAYMENT_SUCCESS'
            elif 'fail' in combined_text:
                return 'PAYMENT_FAILED'

        # Quota notifications
        elif category == 'quota':
            if 'exceed' in combined_text or 'full' in combined_text:
                return 'QUOTA_EXCEEDED'
            elif 'warning' in combined_text or '80%' in combined_text:
                return 'QUOTA_WARNING'

        # Security notifications
        elif category == 'security':
            if 'suspend' in combined_text:
                return 'ACCOUNT_SUSPENDED'
            else:
                return 'SECURITY_ALERT'

        return None

    @staticmethod
    def _extract_template_vars(
        category: str,
        message: str,
        app_link: str
    ) -> Dict:
        """
        Extract variables from notification message for template

        Args:
            category: Notification category
            message: Notification message
            app_link: App deep link

        Returns:
            Dict of template variables
        """
        import re

        vars_dict = {'app_link': app_link}

        # Extract days from subscription messages
        if category == 'subscription':
            days_match = re.search(r'(\d+)\s*days?', message, re.IGNORECASE)
            if days_match:
                vars_dict['days'] = days_match.group(1)

        return vars_dict


# ═══════════════════════════════════════════════════════════════
# INTEGRATION WITH NOTIFICATION SERVICE
# ═══════════════════════════════════════════════════════════════

def create_notification_with_messaging(
    user_id: str,
    title: str,
    message: str,
    notification_type: str = 'info',
    category: str = 'system',
    action_url: Optional[str] = None,
    metadata: Optional[Dict] = None,
    send_sms: bool = True
) -> Optional[str]:
    """
    Create in-app notification and optionally send via SMS/WhatsApp

    Args:
        user_id: User's email/ID
        title: Notification title
        message: Notification message
        notification_type: Type (info, success, warning, error)
        category: Category (subscription, payment, quota, etc.)
        action_url: Optional action URL
        metadata: Optional metadata
        send_sms: Whether to also send via SMS/WhatsApp

    Returns:
        Notification ID

    Example:
        create_notification_with_messaging(
            user_id='user@example.com',
            title='Subscription Expiring',
            message='Your subscription expires in 3 days.',
            category='subscription',
            send_sms=True
        )
    """
    try:
        # Create in-app notification
        from notification_service import NotificationService

        notification_id = NotificationService.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            category=category,
            action_url=action_url,
            metadata=metadata
        )

        # Send via SMS/WhatsApp if requested
        if send_sms:
            MessagingNotificationBridge.send_notification_via_messaging(
                user_id=user_id,
                notification_category=category,
                notification_title=title,
                notification_message=message,
                action_url=action_url
            )

        return notification_id

    except Exception as e:
        logger.error(f"Failed to create notification with messaging: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def notify_subscription_expiring(user_id: str, days_until_expiry: int) -> None:
    """Send subscription expiring notification"""
    create_notification_with_messaging(
        user_id=user_id,
        title='Subscription Expiring Soon',
        message=f'Your subscription expires in {days_until_expiry} days. Renew now to avoid service interruption.',
        notification_type='warning',
        category='subscription',
        action_url='/subscription',
        send_sms=True
    )


def notify_payment_failed(user_id: str) -> None:
    """Send payment failed notification"""
    create_notification_with_messaging(
        user_id=user_id,
        title='Payment Failed',
        message='Your payment could not be processed. Please update your payment method to continue.',
        notification_type='error',
        category='payment',
        action_url='/settings/payment',
        send_sms=True
    )


def notify_quota_exceeded(user_id: str) -> None:
    """Send quota exceeded notification"""
    create_notification_with_messaging(
        user_id=user_id,
        title='Quota Exceeded',
        message='You have reached your plan limit. Upgrade or wait for your quota to reset.',
        notification_type='warning',
        category='quota',
        action_url='/subscription',
        send_sms=True
    )


def notify_account_approved(user_id: str) -> None:
    """Send account approved notification"""
    create_notification_with_messaging(
        user_id=user_id,
        title='Account Approved',
        message='Your account has been approved! You can now log in and start using PhysiologicPRISM.',
        notification_type='success',
        category='system',
        action_url='/dashboard',
        send_sms=True
    )


# ═══════════════════════════════════════════════════════════════
# USAGE EXAMPLES
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Example 1: Subscription expiring
    notify_subscription_expiring('user@example.com', days_until_expiry=3)

    # Example 2: Payment failed
    notify_payment_failed('user@example.com')

    # Example 3: Custom notification with messaging
    create_notification_with_messaging(
        user_id='user@example.com',
        title='Welcome!',
        message='Welcome to PhysiologicPRISM',
        category='system',
        send_sms=True
    )
