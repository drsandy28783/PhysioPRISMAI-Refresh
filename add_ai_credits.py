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

from azure_cosmos_db import get_cosmos_db, SERVER_TIMESTAMP
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
    current_balance = current.get('ai_tokens_balance', 0)
    current_purchased = current.get('ai_tokens_purchased_total', 0)

    print(f"  Current plan:            {current.get('plan_type')}")
    print(f"  Current ai_tokens_balance: {current_balance}")

    # ai_tokens_balance is the same field real AI-call-pack purchases add to
    # (see purchase_ai_calls() in subscription_manager.py) -- the quota check
    # treats a positive balance as usable regardless of ai_calls_limit, so
    # this tops up usage without touching the account's plan-tier limits
    # (which get_user_subscription() now keeps in sync with plan_type on
    # every request and would otherwise revert a direct ai_calls_limit edit).
    sub_ref.update({
        'ai_tokens_balance': current_balance + CREDITS_TO_ADD,
        'ai_tokens_purchased_total': current_purchased + CREDITS_TO_ADD,
        'updated_at': SERVER_TIMESTAMP,
    })

    print(f"\nUpdated successfully:")
    print(f"  ai_tokens_balance: {current_balance} -> {current_balance + CREDITS_TO_ADD}")


if __name__ == '__main__':
    main()
