"""
One-time script to add voice_minutes_limit to existing subscriptions in Cosmos DB
Run this to fix subscriptions that are missing the voice quota field
"""

import os
import logging
from dotenv import load_dotenv
from azure_cosmos_db import get_cosmos_db

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    try:
        db = get_cosmos_db()

        # Get subscriptions collection
        subscriptions_collection = db.collection('subscriptions')

        # Get all subscription documents
        subscription_docs = subscriptions_collection.stream()

        fixed_count = 0
        skipped_count = 0
        error_count = 0

        for sub_doc in subscription_docs:
            try:
                sub = sub_doc.to_dict()
                sub_id = sub_doc.id

                # Check if voice_minutes_limit is missing or None
                if 'voice_minutes_limit' not in sub or sub.get('voice_minutes_limit') is None:
                    plan_type = sub.get('plan_type', 'free_trial')
                    voice_limit = VOICE_MINUTES_BY_PLAN.get(plan_type, 30)  # Default to 30 if plan not found

                    # Prepare update data
                    update_data = {
                        'voice_minutes_limit': voice_limit
                    }

                    # Also add voice_minutes_used_this_month if missing
                    if 'voice_minutes_used_this_month' not in sub:
                        update_data['voice_minutes_used_this_month'] = 0

                    # Update the document
                    doc_ref = subscriptions_collection.document(sub_id)
                    doc_ref.update(update_data)

                    logger.info(f"Fixed subscription for {sub.get('user_id', sub_id)}: plan={plan_type}, voice_limit={voice_limit}")
                    fixed_count += 1
                else:
                    skipped_count += 1

            except Exception as e:
                logger.error(f"Error updating subscription {sub_doc.id}: {e}")
                error_count += 1

        print(f"\nMigration complete!")
        print(f"   Fixed: {fixed_count} subscriptions")
        print(f"   Skipped: {skipped_count} subscriptions (already had voice_minutes_limit)")
        print(f"   Errors: {error_count} subscriptions")

    except Exception as e:
        logger.error(f"Error connecting to Cosmos DB: {e}")
        print(f"ERROR: {e}")

if __name__ == '__main__':
    print("Starting voice quota field migration for Cosmos DB...")
    print("This will add voice_minutes_limit to subscriptions that don't have it\n")

    fix_subscriptions()
