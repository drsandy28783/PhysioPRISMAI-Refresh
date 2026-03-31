#!/usr/bin/env python3
"""
Data Migration Script: Fix Trial Subscription Quotas
====================================================

This script fixes trial subscriptions that have incorrect quota limits.
Common issues:
- ai_calls_limit showing 250 instead of 25
- patients_limit showing wrong values
- voice_minutes_limit showing wrong values

Usage:
    python fix_trial_quotas.py [--dry-run]

Options:
    --dry-run    Show what would be fixed without making changes
"""

import sys
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from azure_cosmos_db import get_cosmos_db, SERVER_TIMESTAMP
from subscription_manager import FREE_TRIAL_PATIENTS, FREE_TRIAL_AI_CALLS, FREE_TRIAL_VOICE_MINUTES

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_trial_quotas(dry_run=False):
    """
    Fix all free trial subscriptions with incorrect quota limits.

    Args:
        dry_run: If True, only report issues without fixing them

    Returns:
        dict: Summary of fixes applied
    """
    try:
        db = get_cosmos_db()

        # Query all free trial subscriptions
        logger.info("Querying all free_trial subscriptions...")
        trial_subs = db.collection('subscriptions').where('plan_type', '==', 'free_trial').stream()

        summary = {
            'total_checked': 0,
            'skipped_super_admin': 0,
            'needs_fix': 0,
            'fixed': 0,
            'errors': 0,
            'fixes_applied': []
        }

        for sub_doc in trial_subs:
            summary['total_checked'] += 1
            user_id = sub_doc.id
            subscription = sub_doc.to_dict()

            # Skip super admin accounts (they have unlimited quotas intentionally)
            if user_id == 'drsandeep@physiologicprism.com':
                logger.info(f"\n⭐ Skipping super admin: {user_id}")
                summary['skipped_super_admin'] += 1
                continue

            # Also skip if subscription has -1 (unlimited) for AI calls - likely another super admin
            if subscription.get('ai_calls_limit') == -1:
                logger.info(f"\n⭐ Skipping super admin (unlimited quotas): {user_id}")
                summary['skipped_super_admin'] += 1
                continue

            logger.info(f"\nChecking subscription for: {user_id}")
            logger.info(f"  Current AI calls limit: {subscription.get('ai_calls_limit')}")
            logger.info(f"  Current patients limit: {subscription.get('patients_limit')}")
            logger.info(f"  Current voice minutes limit: {subscription.get('voice_minutes_limit')}")

            needs_fix = False
            fixes = {}
            issues = []

            # Check AI calls limit
            current_ai_limit = subscription.get('ai_calls_limit')
            if current_ai_limit != FREE_TRIAL_AI_CALLS:
                issues.append(f"AI calls: {current_ai_limit} -> {FREE_TRIAL_AI_CALLS}")
                fixes['ai_calls_limit'] = FREE_TRIAL_AI_CALLS
                needs_fix = True

            # Check patients limit
            current_patients_limit = subscription.get('patients_limit')
            if current_patients_limit != FREE_TRIAL_PATIENTS:
                issues.append(f"Patients: {current_patients_limit} -> {FREE_TRIAL_PATIENTS}")
                fixes['patients_limit'] = FREE_TRIAL_PATIENTS
                needs_fix = True

            # Check voice minutes limit
            current_voice_limit = subscription.get('voice_minutes_limit')
            if current_voice_limit != FREE_TRIAL_VOICE_MINUTES:
                issues.append(f"Voice minutes: {current_voice_limit} -> {FREE_TRIAL_VOICE_MINUTES}")
                fixes['voice_minutes_limit'] = FREE_TRIAL_VOICE_MINUTES
                needs_fix = True

            if needs_fix:
                summary['needs_fix'] += 1
                logger.warning(f"  ⚠️  NEEDS FIX: {', '.join(issues)}")

                if not dry_run:
                    try:
                        # Apply fixes
                        fixes['updated_at'] = SERVER_TIMESTAMP
                        db.collection('subscriptions').document(user_id).update(fixes)
                        logger.info(f"  ✅ FIXED: Applied corrections")
                        summary['fixed'] += 1
                        summary['fixes_applied'].append({
                            'user_id': user_id,
                            'issues': issues,
                            'fixes': fixes
                        })
                    except Exception as e:
                        logger.error(f"  ❌ ERROR: Failed to fix: {e}")
                        summary['errors'] += 1
                else:
                    logger.info(f"  🔍 DRY RUN: Would fix {', '.join(issues)}")
            else:
                logger.info(f"  ✅ OK: All limits correct")

        # Print summary
        logger.info("\n" + "="*60)
        logger.info("SUMMARY")
        logger.info("="*60)
        logger.info(f"Total subscriptions checked: {summary['total_checked']}")
        logger.info(f"Super admin accounts skipped: {summary['skipped_super_admin']}")
        logger.info(f"Subscriptions needing fixes: {summary['needs_fix']}")

        if dry_run:
            logger.info(f"Mode: DRY RUN (no changes made)")
        else:
            logger.info(f"Subscriptions fixed: {summary['fixed']}")
            logger.info(f"Errors encountered: {summary['errors']}")

        logger.info("="*60)

        # Detailed report of fixes
        if summary['fixes_applied']:
            logger.info("\nDETAILED FIX REPORT:")
            for fix in summary['fixes_applied']:
                logger.info(f"\n  User: {fix['user_id']}")
                for issue in fix['issues']:
                    logger.info(f"    - {issue}")

        return summary

    except Exception as e:
        logger.error(f"Fatal error in fix_trial_quotas: {e}")
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

    summary = fix_trial_quotas(dry_run=dry_run)

    # Exit with appropriate code
    if summary['errors'] > 0:
        sys.exit(1)
    elif summary['needs_fix'] > 0 and dry_run:
        logger.info("\n⚠️  Run without --dry-run to apply these fixes")
        sys.exit(2)
    else:
        logger.info("\n✅ All done!")
        sys.exit(0)


if __name__ == '__main__':
    main()
