"""
Script to update super admin subscription to unlimited plan
Run this once to give super admin unlimited AI calls and patients
"""

from azure_cosmos_db import get_cosmos_db, SERVER_TIMESTAMP
from datetime import datetime, timezone, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_super_admin_subscription():
    """Update drsandeep@physiologicprism.com to super_admin plan with unlimited AI calls"""

    try:
        db = get_cosmos_db()
        user_email = 'drsandeep@physiologicprism.com'

        logger.info(f"Updating subscription for {user_email}...")

        # Get or create subscription document
        sub_ref = db.collection('subscriptions').document(user_email)
        sub_doc = sub_ref.get()

        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=365)  # 1 year validity

        subscription_data = {
            'user_id': user_email,
            'plan_type': 'super_admin',
            'status': 'active',
            'price_amount': 0,
            'price_currency': 'INR',
            'current_period_start': now.isoformat(),
            'current_period_end': period_end.isoformat(),
            'patients_limit': -1,  # -1 = UNLIMITED
            'ai_calls_limit': -1,  # -1 = UNLIMITED
            'patients_created_this_month': 0,
            'ai_calls_this_month': 0,
            'ai_tokens_balance': 0,
            'max_users': 1,
            'updated_at': SERVER_TIMESTAMP
        }

        if sub_doc.exists:
            # Update existing subscription
            logger.info("Updating existing subscription...")
            sub_ref.update(subscription_data)
            logger.info("✅ Subscription updated successfully!")
        else:
            # Create new subscription
            logger.info("Creating new subscription...")
            subscription_data['created_at'] = SERVER_TIMESTAMP
            sub_ref.set(subscription_data)
            logger.info("✅ Subscription created successfully!")

        # Verify the update
        updated_sub = sub_ref.get()
        if updated_sub.exists:
            data = updated_sub.to_dict()
            logger.info("\n📋 Updated Subscription Details:")
            logger.info(f"  Plan: {data.get('plan_type')}")
            logger.info(f"  Status: {data.get('status')}")
            logger.info(f"  Patients Limit: {'UNLIMITED' if data.get('patients_limit') == -1 else data.get('patients_limit')}")
            logger.info(f"  AI Calls Limit: {'UNLIMITED' if data.get('ai_calls_limit') == -1 else data.get('ai_calls_limit')}")
            logger.info(f"  Period End: {data.get('current_period_end')}")
            logger.info("\n🎉 Super admin now has unlimited AI calls and patients!")

        return True

    except Exception as e:
        logger.error(f"❌ Error updating subscription: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\n" + "="*70)
    print("SUPER ADMIN SUBSCRIPTION UPDATE")
    print("="*70)
    print("\nThis script will update drsandeep@physiologicprism.com to:")
    print("  - Plan: super_admin")
    print("  - Patients: UNLIMITED (-1)")
    print("  - AI Calls: UNLIMITED (-1)")
    print("  - Status: active")
    print("\n" + "="*70 + "\n")

    success = update_super_admin_subscription()

    if success:
        print("\n✅ SUCCESS: Super admin subscription updated!")
        print("You can now test unlimited AI calls in the dashboard.")
    else:
        print("\n❌ FAILED: Check error messages above")
