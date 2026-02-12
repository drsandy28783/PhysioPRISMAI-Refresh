"""
Appointment Reminder Scheduler
Automatically sends SMS/WhatsApp reminders for upcoming appointments
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict
from azure_cosmos_db import get_cosmos_db
from messaging_service import MessagingService, MessagePriority
from message_templates import DeepLinkGenerator

logger = logging.getLogger(__name__)

# Initialize database
db = get_cosmos_db()


class AppointmentReminderScheduler:
    """
    Schedule and send appointment reminders

    Features:
    - 24-hour advance reminders
    - 2-hour advance reminders
    - Configurable reminder windows
    - Duplicate reminder prevention
    - Failed delivery retry logic
    """

    @staticmethod
    def send_upcoming_reminders(hours_before: int = 24) -> Dict:
        """
        Send reminders for appointments in the next X hours

        Args:
            hours_before: How many hours before appointment to remind

        Returns:
            Dict with send statistics

        Usage:
            # Run as cron job every hour
            AppointmentReminderScheduler.send_upcoming_reminders(hours_before=24)
        """
        try:
            # Calculate time window
            now = datetime.utcnow()
            window_start = now + timedelta(hours=hours_before - 1)
            window_end = now + timedelta(hours=hours_before + 1)

            logger.info(f"Checking for appointments between {window_start} and {window_end}")

            # Find appointments in window
            appointments_query = db.collection('follow_ups') \
                .where('follow_up_date', '>=', window_start) \
                .where('follow_up_date', '<=', window_end) \
                .where('status', '==', 'scheduled')

            appointments = list(appointments_query.get())

            stats = {
                'total_found': len(appointments),
                'sent': 0,
                'skipped': 0,
                'failed': 0
            }

            for appointment_doc in appointments:
                appointment_id = appointment_doc.id
                appointment_data = appointment_doc.to_dict()

                # Check if reminder already sent
                if AppointmentReminderScheduler._reminder_already_sent(
                    appointment_id=appointment_id,
                    hours_before=hours_before
                ):
                    stats['skipped'] += 1
                    continue

                # Send reminder
                success = AppointmentReminderScheduler._send_appointment_reminder(
                    appointment_id=appointment_id,
                    appointment_data=appointment_data,
                    hours_before=hours_before
                )

                if success:
                    stats['sent'] += 1
                else:
                    stats['failed'] += 1

            logger.info(f"Reminder job complete: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to send appointment reminders: {e}")
            return {
                'error': str(e)
            }

    @staticmethod
    def _send_appointment_reminder(
        appointment_id: str,
        appointment_data: Dict,
        hours_before: int
    ) -> bool:
        """
        Send single appointment reminder

        Args:
            appointment_id: Appointment/follow-up ID
            appointment_data: Appointment details
            hours_before: Hours before appointment

        Returns:
            True if successful
        """
        try:
            # Get patient ID (user who will receive reminder)
            patient_id = appointment_data.get('patient_id')

            if not patient_id:
                logger.warning(f"No patient_id for appointment {appointment_id}")
                return False

            # Get provider ID (who created the appointment)
            provider_id = appointment_data.get('created_by') or appointment_data.get('email')

            # Select template based on time
            template_map = {
                24: 'APPOINTMENT_REMINDER_24H',
                2: 'APPOINTMENT_REMINDER_2H'
            }

            template_name = template_map.get(hours_before, 'APPOINTMENT_REMINDER_24H')

            # Generate deep link
            app_link = DeepLinkGenerator.appointment_details(appointment_id)

            # Send reminder
            result = MessagingService.send_with_fallback(
                user_id=patient_id,
                template_name=template_name,
                priority=MessagePriority.HIGH,
                app_link=app_link
            )

            # Log reminder sent
            if result['success']:
                AppointmentReminderScheduler._log_reminder_sent(
                    appointment_id=appointment_id,
                    patient_id=patient_id,
                    hours_before=hours_before,
                    message_id=result.get('message_id')
                )

                logger.info(f"Sent {hours_before}h reminder for appointment {appointment_id}")
                return True
            else:
                logger.error(f"Failed to send reminder for appointment {appointment_id}: {result.get('error')}")
                return False

        except Exception as e:
            logger.error(f"Error sending appointment reminder: {e}")
            return False

    @staticmethod
    def _reminder_already_sent(appointment_id: str, hours_before: int) -> bool:
        """
        Check if reminder already sent for this appointment

        Args:
            appointment_id: Appointment ID
            hours_before: Reminder window

        Returns:
            True if already sent
        """
        try:
            reminder_query = db.collection('reminder_log') \
                .where('appointment_id', '==', appointment_id) \
                .where('hours_before', '==', hours_before) \
                .limit(1)

            reminders = list(reminder_query.get())

            return len(reminders) > 0

        except Exception as e:
            logger.error(f"Error checking reminder status: {e}")
            return False

    @staticmethod
    def _log_reminder_sent(
        appointment_id: str,
        patient_id: str,
        hours_before: int,
        message_id: str
    ) -> None:
        """
        Log that reminder was sent

        Args:
            appointment_id: Appointment ID
            patient_id: Patient ID
            hours_before: Reminder window
            message_id: Message tracking ID
        """
        try:
            from azure_cosmos_db import SERVER_TIMESTAMP

            reminder_data = {
                'appointment_id': appointment_id,
                'patient_id': patient_id,
                'hours_before': hours_before,
                'message_id': message_id,
                'sent_at': SERVER_TIMESTAMP
            }

            db.collection('reminder_log').add(reminder_data)

        except Exception as e:
            logger.error(f"Failed to log reminder: {e}")

    @staticmethod
    def send_follow_up_reminders() -> Dict:
        """
        Send reminders for overdue follow-ups

        Returns:
            Dict with send statistics
        """
        try:
            now = datetime.utcnow()

            # Find overdue follow-ups (past due date, not completed)
            followup_query = db.collection('follow_ups') \
                .where('follow_up_date', '<', now) \
                .where('status', '==', 'pending')

            followups = list(followup_query.get())

            stats = {
                'total_found': len(followups),
                'sent': 0,
                'skipped': 0,
                'failed': 0
            }

            for followup_doc in followups:
                followup_id = followup_doc.id
                followup_data = followup_doc.to_dict()

                # Check if overdue reminder already sent in last 7 days
                if AppointmentReminderScheduler._overdue_reminder_sent_recently(followup_id):
                    stats['skipped'] += 1
                    continue

                # Send overdue reminder
                success = AppointmentReminderScheduler._send_overdue_reminder(
                    followup_id=followup_id,
                    followup_data=followup_data
                )

                if success:
                    stats['sent'] += 1
                else:
                    stats['failed'] += 1

            logger.info(f"Follow-up reminder job complete: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to send follow-up reminders: {e}")
            return {
                'error': str(e)
            }

    @staticmethod
    def _send_overdue_reminder(followup_id: str, followup_data: Dict) -> bool:
        """
        Send overdue follow-up reminder

        Args:
            followup_id: Follow-up ID
            followup_data: Follow-up details

        Returns:
            True if successful
        """
        try:
            patient_id = followup_data.get('patient_id')

            if not patient_id:
                return False

            # Generate deep link
            app_link = DeepLinkGenerator.follow_up_schedule(patient_id)

            # Send reminder
            result = MessagingService.send_with_fallback(
                user_id=patient_id,
                template_name='FOLLOW_UP_OVERDUE',
                priority=MessagePriority.NORMAL,
                app_link=app_link
            )

            # Log reminder
            if result['success']:
                from azure_cosmos_db import SERVER_TIMESTAMP

                db.collection('overdue_reminder_log').add({
                    'followup_id': followup_id,
                    'patient_id': patient_id,
                    'sent_at': SERVER_TIMESTAMP
                })

                return True

            return False

        except Exception as e:
            logger.error(f"Error sending overdue reminder: {e}")
            return False

    @staticmethod
    def _overdue_reminder_sent_recently(followup_id: str, days: int = 7) -> bool:
        """
        Check if overdue reminder sent in last X days

        Args:
            followup_id: Follow-up ID
            days: Days to check

        Returns:
            True if recently sent
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            reminder_query = db.collection('overdue_reminder_log') \
                .where('followup_id', '==', followup_id) \
                .where('sent_at', '>=', cutoff_date) \
                .limit(1)

            reminders = list(reminder_query.get())

            return len(reminders) > 0

        except Exception as e:
            logger.error(f"Error checking overdue reminder: {e}")
            return False


# ═══════════════════════════════════════════════════════════════
# CRON JOB ENDPOINTS (to be added to main.py)
# ═══════════════════════════════════════════════════════════════

def register_reminder_cron_jobs(app):
    """
    Register reminder cron job endpoints

    Add to main.py:
        from appointment_reminder_scheduler import register_reminder_cron_jobs
        register_reminder_cron_jobs(app)

    Configure in Cloud Scheduler:
        - 24h reminders: Every hour, call POST /cron/appointment-reminders-24h
        - 2h reminders: Every 30 minutes, call POST /cron/appointment-reminders-2h
        - Follow-ups: Daily, call POST /cron/follow-up-reminders
    """
    from flask import jsonify

    @app.route('/cron/appointment-reminders-24h', methods=['POST', 'GET'])
    def cron_24h_reminders():
        """Send 24-hour appointment reminders"""
        stats = AppointmentReminderScheduler.send_upcoming_reminders(hours_before=24)
        return jsonify(stats), 200

    @app.route('/cron/appointment-reminders-2h', methods=['POST', 'GET'])
    def cron_2h_reminders():
        """Send 2-hour appointment reminders"""
        stats = AppointmentReminderScheduler.send_upcoming_reminders(hours_before=2)
        return jsonify(stats), 200

    @app.route('/cron/follow-up-reminders', methods=['POST', 'GET'])
    def cron_followup_reminders():
        """Send overdue follow-up reminders"""
        stats = AppointmentReminderScheduler.send_follow_up_reminders()
        return jsonify(stats), 200

    logger.info("Reminder cron jobs registered")


# ═══════════════════════════════════════════════════════════════
# MANUAL REMINDER SENDING
# ═══════════════════════════════════════════════════════════════

def send_manual_reminder(appointment_id: str, user_id: str) -> Dict:
    """
    Manually send appointment reminder

    Args:
        appointment_id: Appointment ID
        user_id: User ID (patient)

    Returns:
        Dict with send status
    """
    app_link = DeepLinkGenerator.appointment_details(appointment_id)

    return MessagingService.send_with_fallback(
        user_id=user_id,
        template_name='APPOINTMENT_REMINDER_24H',
        priority=MessagePriority.HIGH,
        app_link=app_link
    )


# ═══════════════════════════════════════════════════════════════
# USAGE EXAMPLES
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Appointment Reminder Scheduler")
    print("\nCron Job Schedule:")
    print("- 24h reminders: Every hour")
    print("- 2h reminders: Every 30 minutes")
    print("- Follow-up reminders: Daily")
    print("\nEndpoints:")
    print("- POST /cron/appointment-reminders-24h")
    print("- POST /cron/appointment-reminders-2h")
    print("- POST /cron/follow-up-reminders")
