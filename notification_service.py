"""
Notification Service for PhysiologicPRISM
Handles creation, retrieval, and management of user notifications
"""

from datetime import datetime, timedelta
# Firebase removed - using Azure Cosmos DB
from typing import List, Dict, Optional
import logging
from azure_cosmos_db import get_cosmos_db, SERVER_TIMESTAMP


logger = logging.getLogger(__name__)

# Initialize Cosmos DB
db = get_cosmos_db()

class NotificationService:
    """Service for managing user notifications"""

    NOTIFICATION_TYPES = {
        'info': 'info',
        'success': 'success',
        'warning': 'warning',
        'error': 'error'
    }

    NOTIFICATION_CATEGORIES = {
        'subscription': 'Subscription',
        'quota': 'Quota',
        'system': 'System',
        'payment': 'Payment',
        'patient': 'Patient',
        'security': 'Security'
    }

    @staticmethod
    def create_notification(
        user_id: str,
        title: str,
        message: str,
        notification_type: str = 'info',
        category: str = 'system',
        action_url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Create a new notification for a user

        Args:
            user_id: Email/ID of the user to notify
            title: Notification title
            message: Notification message
            notification_type: Type (info, success, warning, error)
            category: Category (subscription, quota, system, etc.)
            action_url: Optional URL for action button
            metadata: Optional metadata dictionary

        Returns:
            Notification ID if successful, None otherwise
        """
        try:
            notification_data = {
                'user_id': user_id,
                'title': title,
                'message': message,
                'type': notification_type,
                'category': category,
                'read': False,
                'created_at': SERVER_TIMESTAMP,
                'action_url': action_url,
                'metadata': metadata or {}
            }

            # Add to notifications collection
            notification_ref = db.collection('notifications').add(notification_data)
            notification_id = notification_ref[1].id

            logger.info(f"Created notification {notification_id} for user {user_id}")
            return notification_id

        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None

    @staticmethod
    def get_user_notifications(
        user_id: str,
        limit: int = 50,
        unread_only: bool = False,
        category: Optional[str] = None
    ) -> List[Dict]:
        """
        Get notifications for a user

        Args:
            user_id: User email/ID
            limit: Maximum number of notifications to return
            unread_only: If True, only return unread notifications
            category: Optional category filter

        Returns:
            List of notification dictionaries
        """
        try:
            query = db.collection('notifications').where('user_id', '==', user_id)

            if unread_only:
                query = query.where('read', '==', False)

            if category:
                query = query.where('category', '==', category)

            # Order by created_at descending
            query = query.order_by('created_at', direction='DESCENDING')
            query = query.limit(limit)

            notifications = []
            for doc in query.stream():
                notification = doc.to_dict()
                notification['id'] = doc.id
                notifications.append(notification)

            logger.info(f"Retrieved {len(notifications)} notifications for user {user_id}")
            return notifications

        except Exception as e:
            logger.error(f"Error retrieving notifications: {e}")
            return []

    @staticmethod
    def get_unread_count(user_id: str) -> int:
        """
        Get count of unread notifications for a user

        Args:
            user_id: User email/ID

        Returns:
            Count of unread notifications
        """
        try:
            query = db.collection('notifications').where('user_id', '==', user_id).where('read', '==', False)
            unread_notifications = list(query.stream())
            count = len(unread_notifications)

            logger.info(f"User {user_id} has {count} unread notifications")
            return count

        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0

    @staticmethod
    def mark_as_read(notification_id: str, user_id: str) -> bool:
        """
        Mark a notification as read

        Args:
            notification_id: Notification document ID
            user_id: User email/ID (for security check)

        Returns:
            True if successful, False otherwise
        """
        try:
            notification_ref = db.collection('notifications').document(notification_id)
            notification = notification_ref.get()

            if not notification.exists:
                logger.warning(f"Notification {notification_id} not found")
                return False

            # Security check - ensure notification belongs to user
            if notification.to_dict().get('user_id') != user_id:
                logger.warning(f"User {user_id} attempted to mark notification {notification_id} belonging to another user")
                return False

            notification_ref.update({'read': True})
            logger.info(f"Marked notification {notification_id} as read")
            return True

        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False

    @staticmethod
    def mark_all_as_read(user_id: str) -> int:
        """
        Mark all notifications as read for a user

        Args:
            user_id: User email/ID

        Returns:
            Count of notifications marked as read
        """
        try:
            query = db.collection('notifications').where('user_id', '==', user_id).where('read', '==', False)
            unread_notifications = list(query.stream())

            count = 0
            for doc in unread_notifications:
                doc.reference.update({'read': True})
                count += 1

            logger.info(f"Marked {count} notifications as read for user {user_id}")
            return count

        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            return 0

    @staticmethod
    def delete_notification(notification_id: str, user_id: str) -> bool:
        """
        Delete a notification

        Args:
            notification_id: Notification document ID
            user_id: User email/ID (for security check)

        Returns:
            True if successful, False otherwise
        """
        try:
            notification_ref = db.collection('notifications').document(notification_id)
            notification = notification_ref.get()

            if not notification.exists:
                logger.warning(f"Notification {notification_id} not found")
                return False

            # Security check
            if notification.to_dict().get('user_id') != user_id:
                logger.warning(f"User {user_id} attempted to delete notification {notification_id} belonging to another user")
                return False

            notification_ref.delete()
            logger.info(f"Deleted notification {notification_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            return False

    @staticmethod
    def delete_old_notifications(days: int = 90) -> int:
        """
        Delete notifications older than specified days

        Args:
            days: Age threshold in days

        Returns:
            Count of deleted notifications
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            # Convert to ISO format string for Cosmos DB query
            cutoff_date_iso = cutoff_date.isoformat()
            query = db.collection('notifications').where('created_at', '<', cutoff_date_iso)

            deleted_count = 0
            for doc in query.stream():
                doc.reference.delete()
                deleted_count += 1

            logger.info(f"Deleted {deleted_count} notifications older than {days} days")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting old notifications: {e}")
            return 0


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATION GENERATORS (Auto-create notifications based on events)
# ─────────────────────────────────────────────────────────────────────────────

def notify_quota_warning(user_id: str, quota_type: str, percentage: float, used: int, limit: int):
    """Create notification for quota warning (>80% usage)"""
    NotificationService.create_notification(
        user_id=user_id,
        title=f"{quota_type} Quota Alert",
        message=f"You've used {percentage:.0f}% of your {quota_type.lower()} quota ({used}/{limit}). Consider upgrading or purchasing tokens.",
        notification_type='warning',
        category='quota',
        action_url='/pricing',
        metadata={'quota_type': quota_type, 'percentage': percentage, 'used': used, 'limit': limit}
    )


def notify_renewal_reminder(user_id: str, plan_name: str, days_remaining: int, renewal_date: str):
    """Create notification for subscription renewal reminder"""
    NotificationService.create_notification(
        user_id=user_id,
        title="Subscription Renewal Reminder",
        message=f"Your {plan_name} subscription renews in {days_remaining} days (on {renewal_date}).",
        notification_type='info',
        category='subscription',
        action_url='/pricing',
        metadata={'plan_name': plan_name, 'days_remaining': days_remaining, 'renewal_date': renewal_date}
    )


def notify_trial_expiring(user_id: str, days_remaining: int):
    """Create notification for trial expiring soon"""
    NotificationService.create_notification(
        user_id=user_id,
        title="Trial Expiring Soon",
        message=f"Your free trial expires in {days_remaining} days. Upgrade now to continue using all features.",
        notification_type='warning',
        category='subscription',
        action_url='/pricing',
        metadata={'days_remaining': days_remaining, 'trial': True}
    )


def notify_payment_success(user_id: str, amount: float, plan_name: str, invoice_id: str):
    """Create notification for successful payment"""
    NotificationService.create_notification(
        user_id=user_id,
        title="Payment Successful",
        message=f"Your payment of ₹{amount:.2f} for {plan_name} was successful. Thank you!",
        notification_type='success',
        category='payment',
        action_url=f'/invoices/{invoice_id}',
        metadata={'amount': amount, 'plan_name': plan_name, 'invoice_id': invoice_id}
    )


def notify_payment_failed(user_id: str, amount: float, plan_name: str, reason: str = ""):
    """Create notification for failed payment"""
    NotificationService.create_notification(
        user_id=user_id,
        title="Payment Failed",
        message=f"Your payment of ₹{amount:.2f} for {plan_name} failed. {reason}",
        notification_type='error',
        category='payment',
        action_url='/pricing',
        metadata={'amount': amount, 'plan_name': plan_name, 'reason': reason}
    )


def notify_welcome(user_id: str, user_name: str):
    """Create welcome notification for new users"""
    NotificationService.create_notification(
        user_id=user_id,
        title=f"Welcome to Physiologic PRISM, {user_name}!",
        message="Get started by adding your first patient. Explore our AI-powered suggestions to enhance your treatment plans.",
        notification_type='success',
        category='system',
        action_url='/add-patient',
        metadata={'welcome': True}
    )


def notify_tos_update(user_id: str, version: str, is_major: bool = False):
    """Create notification for Terms of Service update"""
    if is_major:
        NotificationService.create_notification(
            user_id=user_id,
            title="Important: Terms of Service Updated",
            message=f"Our Terms of Service have been significantly updated (v{version}). Please review and accept the new terms.",
            notification_type='warning',
            category='system',
            action_url='/accept-updated-tos',
            metadata={'tos_version': version, 'is_major': True}
        )
    else:
        NotificationService.create_notification(
            user_id=user_id,
            title="Terms of Service Updated",
            message=f"Our Terms of Service have been updated (v{version}). You can review the changes in Settings.",
            notification_type='info',
            category='system',
            action_url='/terms-of-service',
            metadata={'tos_version': version, 'is_major': False}
        )


def notify_staff_approval_request(admin_id: str, staff_name: str, staff_email: str):
    """Create notification for institute admin when staff requests approval"""
    NotificationService.create_notification(
        user_id=admin_id,
        title="New Staff Approval Request",
        message=f"{staff_name} ({staff_email}) has requested to join your institute. Review their request.",
        notification_type='info',
        category='system',
        action_url='/admin_dashboard',
        metadata={'staff_name': staff_name, 'staff_email': staff_email}
    )


def notify_account_approved(user_id: str):
    """Create notification when user account is approved"""
    NotificationService.create_notification(
        user_id=user_id,
        title="Account Approved!",
        message="Great news! Your account has been approved. You can now access all features.",
        notification_type='success',
        category='system',
        action_url='/dashboard',
        metadata={'approved': True}
    )


def notify_password_changed(user_id: str):
    """Create notification when password is changed"""
    NotificationService.create_notification(
        user_id=user_id,
        title="Password Changed",
        message="Your password has been successfully changed. If you didn't make this change, please contact support immediately.",
        notification_type='info',
        category='security',
        action_url=None,
        metadata={'security_event': 'password_change'}
    )


def notify_upcoming_followup(user_id: str, patient_name: str, patient_id: str, followup_date: str, days_until: int):
    """Create notification for upcoming patient follow-up"""
    if days_until == 0:
        message = f"Reminder: {patient_name}'s follow-up is scheduled for today ({followup_date})."
        title = "Follow-up Today"
    elif days_until == 1:
        message = f"Reminder: {patient_name}'s follow-up is scheduled for tomorrow ({followup_date})."
        title = "Follow-up Tomorrow"
    else:
        message = f"Reminder: {patient_name}'s follow-up is scheduled in {days_until} days ({followup_date})."
        title = f"Upcoming Follow-up"

    NotificationService.create_notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type='info',
        category='patient',
        action_url=f'/view_follow_ups/{patient_id}',
        metadata={
            'patient_name': patient_name,
            'patient_id': patient_id,
            'followup_date': followup_date,
            'days_until': days_until,
            'notification_type': 'followup_reminder'
        }
    )


def notify_followup_confirmation(user_id: str, patient_name: str, patient_id: str, followup_date: str):
    """Create notification confirming patient has been notified about follow-up"""
    NotificationService.create_notification(
        user_id=user_id,
        title="Patient Notified",
        message=f"Confirmation: {patient_name} has been notified about their follow-up on {followup_date}.",
        notification_type='success',
        category='patient',
        action_url=f'/view_follow_ups/{patient_id}',
        metadata={
            'patient_name': patient_name,
            'patient_id': patient_id,
            'followup_date': followup_date,
            'notification_type': 'followup_confirmation'
        }
    )
