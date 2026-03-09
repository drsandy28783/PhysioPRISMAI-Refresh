"""
Cleanup script to remove orphaned notifications
Removes notifications that have missing or invalid user_id values
"""

import os
import logging
from dotenv import load_dotenv
from azure_cosmos_db import get_cosmos_db

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cleanup_orphaned_notifications():
    """
    Remove notifications with invalid user_id values
    This fixes the security issue where users could see other users' notifications
    """
    try:
        db = get_cosmos_db()

        # Query all notifications
        logger.info("Querying all notifications...")
        all_notifications = list(db.collection('notifications').stream())
        logger.info(f"Found {len(all_notifications)} total notifications")

        # Find orphaned notifications (no user_id or empty user_id)
        orphaned = []
        for doc in all_notifications:
            notification = doc.to_dict()
            user_id = notification.get('user_id')

            if not user_id or not isinstance(user_id, str) or not user_id.strip():
                orphaned.append({
                    'id': doc.id,
                    'title': notification.get('title', 'N/A'),
                    'user_id': user_id
                })

        logger.info(f"Found {len(orphaned)} orphaned notifications (no valid user_id)")

        if orphaned:
            logger.info("Orphaned notifications:")
            for notif in orphaned:
                logger.info(f"  - ID: {notif['id']}, Title: {notif['title']}, user_id: {notif['user_id']}")

            # Ask for confirmation
            response = input(f"\nDelete {len(orphaned)} orphaned notifications? (yes/no): ")

            if response.lower() == 'yes':
                deleted_count = 0
                for notif in orphaned:
                    try:
                        db.collection('notifications').document(notif['id']).delete()
                        deleted_count += 1
                        logger.info(f"Deleted notification {notif['id']}")
                    except Exception as e:
                        logger.error(f"Failed to delete notification {notif['id']}: {e}")

                logger.info(f"Successfully deleted {deleted_count} orphaned notifications")
            else:
                logger.info("Cleanup cancelled")
        else:
            logger.info("No orphaned notifications found - database is clean!")

        # Also log notifications grouped by user_id for verification
        logger.info("\n--- Notification counts by user ---")
        user_counts = {}
        for doc in all_notifications:
            notification = doc.to_dict()
            user_id = notification.get('user_id', 'NO_USER_ID')
            user_counts[user_id] = user_counts.get(user_id, 0) + 1

        for user_id, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {user_id}: {count} notifications")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("Starting notification cleanup script...")
    cleanup_orphaned_notifications()
    logger.info("Cleanup complete!")
