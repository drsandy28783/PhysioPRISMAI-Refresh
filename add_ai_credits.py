"""
Add AI credits to a user's subscription.

Usage:
    python add_ai_credits.py user@example.com 50    # email and credit amount are both required
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from azure_cosmos_db import get_cosmos_db
db = get_cosmos_db()

if len(sys.argv) < 2:
    print("Usage: python add_ai_credits.py <email> [credits]")
    print("Both email and credits must be given explicitly -- no default target.")
    sys.exit(1)

TARGET_EMAIL = sys.argv[1]
CREDITS_TO_ADD = int(sys.argv[2]) if len(sys.argv) > 2 else 100


def main():
    print(f"Looking up subscription for {TARGET_EMAIL} ...")
    sub_ref = db.collection('subscriptions').document(TARGET_EMAIL)
    sub_doc = sub_ref.get()

    if not sub_doc.exists:
        print("  No subscription document found — cannot add credits.")
        print("  The user may not have logged in yet or uses a different ID.")
        sys.exit(1)

    current = sub_doc.to_dict()
    current_limit = current.get('ai_calls_limit', 0)
    current_used = current.get('ai_calls_this_month', 0)

    print(f"  Current plan:           {current.get('plan_type')}")
    print(f"  Current ai_calls_limit: {current_limit}")
    print(f"  Current ai_calls_used:  {current_used}")

    if current_limit == -1:
        print(f"\n  Account already has unlimited AI calls — no change needed.")
        return

    # Free-trial accounts have a repair loop in get_user_subscription() that resets
    # ai_calls_limit back to FREE_TRIAL_AI_CALLS on every request. Setting -1 (unlimited)
    # is the only value the repair loop skips, so we use that for test accounts.
    sub_ref.update({
        'ai_calls_limit': -1,
        'ai_calls_this_month': 0,
    })

    print(f"\nUpdated successfully:")
    print(f"  ai_calls_limit:     {current_limit} -> -1 (unlimited)")
    print(f"  ai_calls_this_month: {current_used} -> 0 (reset)")
    print(f"  Note: set to unlimited so the free-trial repair loop doesn't overwrite it")


if __name__ == '__main__':
    main()
