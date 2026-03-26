"""
Fix Super Admin Subscription Limits
====================================

This script updates the Super Admin subscription to have unlimited quotas:
- patients_limit: -1 (unlimited)
- ai_calls_limit: -1 (unlimited)
- voice_minutes_limit: -1 (unlimited)

Run this script once to fix the subscription data in Cosmos DB.
"""

import os
import logging
from azure_cosmos_db import get_cosmos_db, SERVER_TIMESTAMP
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Cosmos DB client
db = get_cosmos_db()

# Super Admin email (from environment variable)
SUPER_ADMIN_EMAIL = os.environ.get('SUPER_ADMIN_EMAIL', 'admin@drsandeepphysiologicprism.onmicrosoft.com')

def fix_super_admin_subscription():
    """Fix Super Admin subscription to have unlimited quotas."""
    try:
        logger.info(f"Fixing subscription for Super Admin: {SUPER_ADMIN_EMAIL}")

        # Get current subscription
        sub_ref = db.collection('subscriptions').document(SUPER_ADMIN_EMAIL)
        sub_doc = sub_ref.get()

        if not sub_doc.exists:
            logger.info("No subscription found. Creating Super Admin subscription...")
            # Create new subscription
            new_subscription = {
                'user_id': SUPER_ADMIN_EMAIL,
                'plan_type': 'super_admin',
                'status': 'active',
                'current_period_start': datetime.now(timezone.utc).isoformat(),
                'current_period_end': datetime(2099, 12, 31, tzinfo=timezone.utc).isoformat(),  # Far future
                'price_amount': 0,
                'currency': 'INR',
                'patients_created_this_month': 0,
                'patients_limit': -1,  # UNLIMITED
                'ai_calls_this_month': 0,
                'ai_calls_limit': -1,  # UNLIMITED
                'voice_minutes_used_this_month': 0,
                'voice_minutes_limit': -1,  # UNLIMITED
                'ai_tokens_balance': 0,
                'ai_tokens_purchased_total': 0,
                'max_users': 1,
                'created_at': SERVER_TIMESTAMP,
                'updated_at': SERVER_TIMESTAMP
            }
            sub_ref.set(new_subscription)
            logger.info("✅ Created Super Admin subscription with unlimited quotas")
        else:
            # Update existing subscription
            subscription = sub_doc.to_dict()
            logger.info(f"Current subscription: plan_type={subscription.get('plan_type')}, "
                       f"patients_limit={subscription.get('patients_limit')}, "
                       f"ai_calls_limit={subscription.get('ai_calls_limit')}")

            # Update to unlimited quotas
            updates = {
                'plan_type': 'super_admin',
                'status': 'active',
                'patients_limit': -1,  # UNLIMITED
                'ai_calls_limit': -1,  # UNLIMITED
                'voice_minutes_limit': -1,  # UNLIMITED
                'current_period_end': datetime(2099, 12, 31, tzinfo=timezone.utc).isoformat(),
                'updated_at': SERVER_TIMESTAMP
            }

            # Preserve existing usage counts (don't reset them)
            if 'patients_created_this_month' not in subscription:
                updates['patients_created_this_month'] = 0
            if 'ai_calls_this_month' not in subscription:
                updates['ai_calls_this_month'] = 0
            if 'voice_minutes_used_this_month' not in subscription:
                updates['voice_minutes_used_this_month'] = 0

            sub_ref.update(updates)
            logger.info("✅ Updated Super Admin subscription to unlimited quotas")

        # Verify the update
        updated_sub = sub_ref.get().to_dict()
        logger.info(f"Verified: plan_type={updated_sub.get('plan_type')}, "
                   f"patients_limit={updated_sub.get('patients_limit')}, "
                   f"ai_calls_limit={updated_sub.get('ai_calls_limit')}, "
                   f"voice_minutes_limit={updated_sub.get('voice_minutes_limit')}")

        return True

    except Exception as e:
        logger.error(f"Error fixing Super Admin subscription: {e}")
        return False


if __name__ == '__main__':
    print(f"\n{'='*60}")
    print("Super Admin Subscription Fix Script")
    print(f"{'='*60}\n")
    print(f"Super Admin Email: {SUPER_ADMIN_EMAIL}\n")

    success = fix_super_admin_subscription()

    if success:
        print("\n✅ SUCCESS: Super Admin subscription fixed!")
        print("\nNext steps:")
        print("1. Refresh your dashboard")
        print("2. Create a test patient to verify quota tracking")
        print("3. Check that 'Patients This Month' increments correctly")
    else:
        print("\n❌ FAILED: Could not fix Super Admin subscription")
        print("Check the error logs above for details")

    print(f"\n{'='*60}\n")
