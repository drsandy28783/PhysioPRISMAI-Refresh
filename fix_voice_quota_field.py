"""
One-time script to add voice_minutes_limit to existing subscriptions
Run this to fix subscriptions that are missing the voice quota field
"""

import os
from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv()

# Initialize Firestore
db = firestore.Client()

# Voice minutes per plan
VOICE_MINUTES_BY_PLAN = {
    'free_trial': 30,
    'solo': 120,
    'team_5': 600,
    'team_10': 1200,
    'institute_15': 1800,
    'institute_20': 2400,
    'super_admin': -1  # Unlimited
}

def fix_subscriptions():
    """Add voice_minutes_limit to subscriptions that don't have it"""

    subscriptions_ref = db.collection('subscriptions')
    docs = subscriptions_ref.stream()

    fixed_count = 0
    skipped_count = 0

    for doc in docs:
        data = doc.to_dict()

        # Check if voice_minutes_limit is missing
        if 'voice_minutes_limit' not in data or data.get('voice_minutes_limit') is None:
            plan_type = data.get('plan_type', 'free_trial')
            voice_limit = VOICE_MINUTES_BY_PLAN.get(plan_type, 30)  # Default to 30 if plan not found

            # Update the subscription
            doc.reference.update({
                'voice_minutes_limit': voice_limit,
                'voice_minutes_used_this_month': data.get('voice_minutes_used_this_month', 0)
            })

            print(f"Fixed subscription for {doc.id}: plan={plan_type}, voice_limit={voice_limit}")
            fixed_count += 1
        else:
            skipped_count += 1

    print(f"\nMigration complete!")
    print(f"   Fixed: {fixed_count} subscriptions")
    print(f"   Skipped: {skipped_count} subscriptions (already had voice_minutes_limit)")

if __name__ == '__main__':
    print("Starting voice quota field migration...")
    print("This will add voice_minutes_limit to subscriptions that don't have it\n")

    fix_subscriptions()
