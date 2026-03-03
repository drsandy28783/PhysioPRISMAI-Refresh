#!/usr/bin/env python3
"""
Set Unlimited Quota for Test Users
===================================
Gives specified test users unlimited quota for all features
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import Cosmos DB setup
from azure_cosmos_db import get_cosmos_db

# Initialize database
db = get_cosmos_db()

# Test users to give unlimited quota
TEST_USERS = [
    "drsandeep@physiologicprism.com",
    "rp1234ram@gmail.com"
]

# Unlimited quota values (-1 means unlimited)
UNLIMITED_QUOTA = {
    # Subscription details
    "plan_type": "super_admin",  # Super admin plan
    "status": "active",
    "trial_end_date": None,  # Not on trial
    "current_period_start": datetime.now(timezone.utc).isoformat(),
    "current_period_end": (datetime.now(timezone.utc) + timedelta(days=3650)).isoformat(),  # 10 years
    "price_amount": 0,
    "currency": "INR",

    # Patient quota (-1 = unlimited)
    "patients_limit": -1,
    "patients_created_this_month": 0,

    # AI quota (-1 = unlimited)
    "ai_calls_limit": -1,
    "ai_calls_this_month": 0,

    # Voice quota (-1 = unlimited)
    "voice_minutes_limit": -1,
    "voice_minutes_used_this_month": 0,

    # AI tokens
    "ai_tokens_balance": 0,
    "ai_tokens_purchased_total": 0,

    # Max users
    "max_users": 999,

    # Metadata
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "quota_updated_by": "set_unlimited_quota.py",
    "is_test_user": True,
}


def set_unlimited_quota(user_email: str):
    """Set unlimited quota for a user"""
    try:
        print(f"\n{'='*60}")
        print(f"Setting unlimited quota for: {user_email}")
        print(f"{'='*60}")

        # Get subscription document (using email as document ID)
        sub_doc_ref = db.collection('subscriptions').document(user_email)
        sub_doc = sub_doc_ref.get()

        if sub_doc.exists:
            # Get current data
            current_data = sub_doc.to_dict()
            print(f"\n[INFO] Current quota:")
            print(f"   Plan: {current_data.get('plan_type', 'free_trial')}")
            print(f"   Status: {current_data.get('status', 'inactive')}")
            print(f"   Patients: {current_data.get('patients_created_this_month', 0)}/{current_data.get('patients_limit', 0)}")
            print(f"   AI calls: {current_data.get('ai_calls_this_month', 0)}/{current_data.get('ai_calls_limit', 0)}")
            print(f"   Voice minutes: {current_data.get('voice_minutes_used_this_month', 0)}/{current_data.get('voice_minutes_limit', 0)}")

            # Update with unlimited quota
            sub_doc_ref.update(UNLIMITED_QUOTA)
            print(f"\n[OK] Updated quota:")
        else:
            print(f"[INFO] No subscription found for {user_email}")
            print(f"   Creating new subscription with unlimited quota...")

            # Create new subscription with unlimited quota
            subscription_data = {
                'user_id': user_email,
                'created_at': datetime.now(timezone.utc).isoformat(),
                **UNLIMITED_QUOTA
            }
            sub_doc_ref.set(subscription_data)
            print(f"\n[OK] Created subscription with unlimited quota:")

        print(f"   Plan: super_admin (unlimited)")
        print(f"   Status: active")
        print(f"   Patients: UNLIMITED (-1)")
        print(f"   AI calls: UNLIMITED (-1)")
        print(f"   Voice minutes: UNLIMITED (-1)")
        print(f"   All features: enabled")

        return True

    except Exception as e:
        print(f"[ERROR] Error setting quota for {user_email}: {e}")
        import traceback
        traceback.print_exc()
        return False


def reset_usage_counters(user_email: str):
    """Reset usage counters to 0 for a user"""
    try:
        sub_doc_ref = db.collection('subscriptions').document(user_email)
        sub_doc = sub_doc_ref.get()

        if not sub_doc.exists:
            print(f"[WARN] Subscription not found: {user_email}")
            return False

        sub_doc_ref.update({
            'patients_created_this_month': 0,
            'ai_calls_this_month': 0,
            'voice_minutes_used_this_month': 0,
        })

        print(f"[OK] Reset usage counters for: {user_email}")
        return True

    except Exception as e:
        print(f"[ERROR] Error resetting counters for {user_email}: {e}")
        return False


def main():
    """Main function"""
    print("="*60)
    print("Set Unlimited Quota for Test Users")
    print("="*60)

    success_count = 0

    for user_email in TEST_USERS:
        if set_unlimited_quota(user_email):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"[OK] Successfully updated {success_count}/{len(TEST_USERS)} users")
    print(f"{'='*60}")

    # Ask if user wants to reset counters
    print(f"\nWould you like to reset usage counters to 0? (y/n)")
    choice = input().strip().lower()

    if choice == 'y':
        print(f"\nResetting usage counters...")
        for user_email in TEST_USERS:
            reset_usage_counters(user_email)

    print(f"\n[OK] Done!")


if __name__ == "__main__":
    main()
