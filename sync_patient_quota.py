#!/usr/bin/env python3
"""
Sync Patient Quota Script
==========================

This script syncs the patients_created_this_month field in subscriptions
with the actual count of patients created this month.

This fixes the issue where quota wasn't being deducted due to a bug,
causing the subscription field to be out of sync with reality.

Usage:
    python sync_patient_quota.py [--dry-run]
"""

import sys
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from azure_cosmos_db import get_cosmos_db, SERVER_TIMESTAMP

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_created_at(created_at):
    """Parse created_at field which can be ISO string or datetime"""
    if not created_at:
        return None
    if isinstance(created_at, str):
        try:
            return datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    return created_at


def sync_patient_quotas(dry_run=False):
    """
    Sync patients_created_this_month with actual patient counts.

    Args:
        dry_run: If True, only report issues without fixing them

    Returns:
        dict: Summary of fixes applied
    """
    try:
        db = get_cosmos_db()

        # Get all active subscriptions
        logger.info("Querying all active subscriptions...")
        subscriptions = db.collection('subscriptions').where('status', '==', 'active').stream()

        summary = {
            'total_checked': 0,
            'out_of_sync': 0,
            'fixed': 0,
            'errors': 0,
            'details': []
        }

        for sub_doc in subscriptions:
            summary['total_checked'] += 1
            user_id = sub_doc.id
            subscription = sub_doc.to_dict()

            # Get current period start to calculate "this month"
            period_start = subscription.get('current_period_start')
            if not period_start:
                logger.warning(f"No period_start for {user_id}, skipping")
                continue

            # Parse period start
            if isinstance(period_start, str):
                period_start = datetime.fromisoformat(period_start.replace('Z', '+00:00'))

            # Make timezone-aware if needed
            if period_start.tzinfo is None:
                period_start = period_start.replace(tzinfo=timezone.utc)

            # Count actual patients created since period_start
            logger.info(f"\nChecking {user_id}...")
            patients_query = db.collection('patients').where('physio_id', '==', user_id).stream()

            actual_count = 0
            for patient_doc in patients_query:
                patient = patient_doc.to_dict()
                created_at = parse_created_at(patient.get('created_at'))

                if created_at:
                    # Make timezone-aware if needed
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)

                    # Count if created in current billing period
                    if created_at >= period_start:
                        actual_count += 1

            # Compare with subscription field
            stored_count = subscription.get('patients_created_this_month', 0)

            logger.info(f"  Stored count: {stored_count}")
            logger.info(f"  Actual count: {actual_count}")
            logger.info(f"  Patients limit: {subscription.get('patients_limit', 0)}")

            if stored_count != actual_count:
                summary['out_of_sync'] += 1
                logger.warning(f"  ⚠️  OUT OF SYNC: {stored_count} → {actual_count} (difference: {actual_count - stored_count})")

                if not dry_run:
                    try:
                        # Update the subscription
                        db.collection('subscriptions').document(user_id).update({
                            'patients_created_this_month': actual_count,
                            'updated_at': SERVER_TIMESTAMP
                        })
                        logger.info(f"  ✅ FIXED: Updated to {actual_count}")
                        summary['fixed'] += 1
                        summary['details'].append({
                            'user_id': user_id,
                            'old_count': stored_count,
                            'new_count': actual_count,
                            'limit': subscription.get('patients_limit', 0)
                        })
                    except Exception as e:
                        logger.error(f"  ❌ ERROR: Failed to fix: {e}")
                        summary['errors'] += 1
                else:
                    logger.info(f"  🔍 DRY RUN: Would update to {actual_count}")
            else:
                logger.info(f"  ✅ OK: Counts match")

        # Print summary
        logger.info("\n" + "="*60)
        logger.info("SUMMARY")
        logger.info("="*60)
        logger.info(f"Total subscriptions checked: {summary['total_checked']}")
        logger.info(f"Subscriptions out of sync: {summary['out_of_sync']}")

        if dry_run:
            logger.info(f"Mode: DRY RUN (no changes made)")
        else:
            logger.info(f"Subscriptions fixed: {summary['fixed']}")
            logger.info(f"Errors encountered: {summary['errors']}")

        logger.info("="*60)

        # Detailed report
        if summary['details']:
            logger.info("\nDETAILED FIX REPORT:")
            for detail in summary['details']:
                logger.info(f"\n  User: {detail['user_id']}")
                logger.info(f"    Old count: {detail['old_count']}")
                logger.info(f"    New count: {detail['new_count']}")
                logger.info(f"    Limit: {detail['limit']}")
                if detail['new_count'] >= detail['limit'] and detail['limit'] != -1:
                    logger.info(f"    ⚠️  USER HAS EXCEEDED QUOTA!")

        return summary

    except Exception as e:
        logger.error(f"Fatal error in sync_patient_quotas: {e}")
        raise


def main():
    """Main entry point for the script."""
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv

    if dry_run:
        logger.info("🔍 DRY RUN MODE: No changes will be made\n")
    else:
        logger.info("⚠️  LIVE MODE: Changes will be applied to database\n")
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            logger.info("Aborted by user")
            return

    summary = sync_patient_quotas(dry_run=dry_run)

    # Exit with appropriate code
    if summary['errors'] > 0:
        sys.exit(1)
    elif summary['out_of_sync'] > 0 and dry_run:
        logger.info("\n⚠️  Run without --dry-run to apply these fixes")
        sys.exit(2)
    else:
        logger.info("\n✅ All done!")
        sys.exit(0)


if __name__ == '__main__':
    main()
