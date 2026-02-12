"""
Messaging Data Cleanup Cron Jobs
GDPR/HIPAA compliance - automatic data retention enforcement
"""

import logging
from datetime import datetime, timedelta
from azure_cosmos_db import get_cosmos_db
from messaging_service import MessagingService

logger = logging.getLogger(__name__)

# Initialize database
db = get_cosmos_db()


class MessagingCleanupJobs:
    """
    Scheduled cleanup jobs for messaging data

    GDPR/HIPAA Compliance:
    - Delete old message logs (default: 90 days)
    - Delete expired OTP codes (default: 24 hours)
    - Delete old incoming messages (default: 90 days)
    - Clean up old reminder logs (default: 180 days)
    """

    @staticmethod
    def cleanup_old_messages(retention_days: int = 90) -> dict:
        """
        Delete message logs older than retention period

        Args:
            retention_days: Number of days to retain messages

        Returns:
            Dict with cleanup statistics
        """
        try:
            deleted_count = MessagingService.cleanup_old_messages(days=retention_days)

            logger.info(f"Cleaned up {deleted_count} old message logs (>{retention_days} days)")

            return {
                'success': True,
                'deleted_count': deleted_count,
                'retention_days': retention_days
            }

        except Exception as e:
            logger.error(f"Failed to cleanup old messages: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def cleanup_expired_otps(retention_hours: int = 24) -> dict:
        """
        Delete expired OTP codes

        Args:
            retention_hours: Hours after creation to delete OTPs

        Returns:
            Dict with cleanup statistics
        """
        try:
            deleted_count = MessagingService.cleanup_old_otps(hours=retention_hours)

            logger.info(f"Cleaned up {deleted_count} expired OTP codes (>{retention_hours} hours)")

            return {
                'success': True,
                'deleted_count': deleted_count,
                'retention_hours': retention_hours
            }

        except Exception as e:
            logger.error(f"Failed to cleanup expired OTPs: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def cleanup_old_incoming_messages(retention_days: int = 90) -> dict:
        """
        Delete old incoming messages (patient replies)

        Args:
            retention_days: Number of days to retain messages

        Returns:
            Dict with cleanup statistics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            # Query old incoming messages
            old_messages = db.collection('incoming_messages') \
                .where('created_at', '<', cutoff_date) \
                .get()

            deleted_count = 0

            for doc in old_messages:
                doc.reference.delete()
                deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old incoming messages (>{retention_days} days)")

            return {
                'success': True,
                'deleted_count': deleted_count,
                'retention_days': retention_days
            }

        except Exception as e:
            logger.error(f"Failed to cleanup old incoming messages: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def cleanup_old_reminder_logs(retention_days: int = 180) -> dict:
        """
        Delete old reminder logs

        Args:
            retention_days: Number of days to retain reminder logs

        Returns:
            Dict with cleanup statistics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            # Cleanup reminder logs
            old_reminders = db.collection('reminder_log') \
                .where('sent_at', '<', cutoff_date) \
                .get()

            deleted_count = 0

            for doc in old_reminders:
                doc.reference.delete()
                deleted_count += 1

            # Cleanup overdue reminder logs
            old_overdue = db.collection('overdue_reminder_log') \
                .where('sent_at', '<', cutoff_date) \
                .get()

            for doc in old_overdue:
                doc.reference.delete()
                deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old reminder logs (>{retention_days} days)")

            return {
                'success': True,
                'deleted_count': deleted_count,
                'retention_days': retention_days
            }

        except Exception as e:
            logger.error(f"Failed to cleanup old reminder logs: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def run_all_cleanup_jobs() -> dict:
        """
        Run all cleanup jobs

        Returns:
            Dict with all cleanup statistics
        """
        results = {
            'message_logs': MessagingCleanupJobs.cleanup_old_messages(),
            'otp_codes': MessagingCleanupJobs.cleanup_expired_otps(),
            'incoming_messages': MessagingCleanupJobs.cleanup_old_incoming_messages(),
            'reminder_logs': MessagingCleanupJobs.cleanup_old_reminder_logs()
        }

        total_deleted = sum(
            r.get('deleted_count', 0)
            for r in results.values()
            if r.get('success')
        )

        logger.info(f"All cleanup jobs complete. Total records deleted: {total_deleted}")

        results['total_deleted'] = total_deleted

        return results


# ═══════════════════════════════════════════════════════════════
# FLASK CRON JOB ENDPOINTS
# ═══════════════════════════════════════════════════════════════

def register_messaging_cleanup_jobs(app):
    """
    Register messaging cleanup cron job endpoints

    Add to main.py:
        from messaging_cleanup_jobs import register_messaging_cleanup_jobs
        register_messaging_cleanup_jobs(app)

    Configure in Cloud Scheduler:
        - Daily cleanup: POST /cron/messaging-cleanup
    """
    from flask import jsonify

    @app.route('/cron/messaging-cleanup', methods=['POST', 'GET'])
    def cron_messaging_cleanup():
        """Run all messaging cleanup jobs"""
        results = MessagingCleanupJobs.run_all_cleanup_jobs()
        return jsonify(results), 200

    @app.route('/cron/cleanup-expired-otps', methods=['POST', 'GET'])
    def cron_cleanup_otps():
        """Cleanup expired OTP codes (can run more frequently)"""
        results = MessagingCleanupJobs.cleanup_expired_otps()
        return jsonify(results), 200

    logger.info("Messaging cleanup jobs registered")


# ═══════════════════════════════════════════════════════════════
# USAGE EXAMPLES
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Messaging Cleanup Jobs")
    print("\nScheduled Jobs:")
    print("- Daily: Run all cleanup jobs")
    print("- Every 6 hours: Cleanup expired OTPs")
    print("\nEndpoints:")
    print("- POST /cron/messaging-cleanup (run daily)")
    print("- POST /cron/cleanup-expired-otps (run every 6 hours)")
    print("\nData Retention:")
    print("- Message logs: 90 days")
    print("- OTP codes: 24 hours")
    print("- Incoming messages: 90 days")
    print("- Reminder logs: 180 days")
