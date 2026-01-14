"""
Subscription Management Module for Physio-Assist
=================================================

This module handles all subscription-related logic including:
- Plan management and limits
- Quota tracking (patients, AI calls)
- Free trial management
- Token purchases and balance
- Usage validation and deduction

Compatible with both web and mobile apps.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
# Firebase removed - using Azure Cosmos DB
from azure_cosmos_db import SERVER_TIMESTAMP
from typing import Dict, Optional, Tuple

logger = logging.getLogger("app.subscription")

# Get Cosmos DB client
db = get_cosmos_db()

# ─────────────────────────────────────────────────────────────────────────────
# PLAN CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Free trial configuration (can be disabled via environment variable)
FREE_TRIAL_ENABLED = os.environ.get('FREE_TRIAL_ENABLED', 'true').lower() == 'true'
FREE_TRIAL_DAYS = int(os.environ.get('FREE_TRIAL_DAYS', '14'))
FREE_TRIAL_PATIENTS = int(os.environ.get('FREE_TRIAL_PATIENTS', '5'))
FREE_TRIAL_AI_CALLS = int(os.environ.get('FREE_TRIAL_AI_CALLS', '25'))

# Plan definitions with limits (SIMPLIFIED STRUCTURE - December 2025)
PLANS = {
    'free_trial': {
        'name': 'Free Trial',
        'price': 0,
        'currency': 'INR',
        'patients_limit': 10,  # Limited to 10 during trial only
        'ai_calls_limit': FREE_TRIAL_AI_CALLS,
        'duration_days': FREE_TRIAL_DAYS,
        'max_users': 1,
        'features': [
            '10 patients (trial)',
            f'{FREE_TRIAL_AI_CALLS} AI suggestions',
            'All features',
            'PDF reports',
            'Email support'
        ]
    },
    'solo': {
        'name': 'Solo Professional',
        'price': 899,
        'currency': 'INR',
        'patients_limit': -1,  # -1 = UNLIMITED
        'ai_calls_limit': 100,
        'max_users': 1,
        'features': [
            'UNLIMITED patients',
            '100 AI calls/month',
            'All workflows',
            'PDF reports',
            'Priority email support',
            'Usage analytics'
        ]
    },
    'team_5': {
        'name': 'Team (5 Users)',
        'price': 3999,
        'currency': 'INR',
        'patients_limit': -1,  # -1 = UNLIMITED
        'ai_calls_limit': 500,
        'max_users': 5,
        'features': [
            'UNLIMITED patients',
            '500 AI calls/month',
            'Up to 5 users',
            'All workflows',
            'PDF reports',
            'Priority support',
            'Usage analytics',
            'Team dashboard'
        ]
    },
    'team_10': {
        'name': 'Team Pro (10 Users)',
        'price': 7499,
        'currency': 'INR',
        'patients_limit': -1,  # -1 = UNLIMITED
        'ai_calls_limit': 1000,
        'max_users': 10,
        'features': [
            'UNLIMITED patients',
            '1,000 AI calls/month',
            'Up to 10 users',
            'All workflows',
            'Advanced analytics',
            'Custom branding',
            'Dedicated account manager'
        ]
    },
    'institute_15': {
        'name': 'Institute (15 Users)',
        'price': 10999,
        'currency': 'INR',
        'patients_limit': -1,  # -1 = UNLIMITED
        'ai_calls_limit': 1500,
        'max_users': 15,
        'features': [
            'UNLIMITED patients',
            '1,500 AI calls/month',
            'Up to 15 users',
            'All workflows',
            'API access',
            'White-label options',
            'Priority phone support'
        ]
    },
    'institute_20': {
        'name': 'Institute Plus (20 Users)',
        'price': 14499,
        'currency': 'INR',
        'patients_limit': -1,  # -1 = UNLIMITED
        'ai_calls_limit': 2000,
        'max_users': 20,
        'features': [
            'UNLIMITED patients',
            '2,000 AI calls/month',
            'Up to 20 users',
            'All workflows',
            'Custom integrations',
            'Onboarding support',
            'SLA guarantees'
        ]
    }
}

# AI Call Packs (70% profit margin - December 2025)
# Cost per AI call: ₹3.83 (with 70% cache) → Sell at ₹13/call for 70% margin
AI_CALL_PACKS = {
    'starter': {
        'calls': 25,
        'price': 325,
        'per_call': 13.00,
        'savings': '0%',
        'name': 'Starter Pack'
    },
    'regular': {
        'calls': 50,
        'price': 599,
        'per_call': 11.98,
        'savings': '8%',
        'name': 'Regular Pack',
        'badge': 'Good Value'
    },
    'popular': {
        'calls': 100,
        'price': 1099,
        'per_call': 10.99,
        'savings': '15%',
        'name': 'Popular Pack',
        'badge': 'MOST POPULAR'
    },
    'professional': {
        'calls': 250,
        'price': 2499,
        'per_call': 9.99,
        'savings': '23%',
        'name': 'Professional Pack',
        'badge': 'Best Value'
    },
    'enterprise': {
        'calls': 500,
        'price': 4499,
        'per_call': 8.99,
        'savings': '31%',
        'name': 'Enterprise Pack',
        'badge': 'Maximum Value'
    }
}

# Legacy token packages (DEPRECATED - use AI_CALL_PACKS instead)
# Kept for backward compatibility with existing code
TOKEN_PACKAGES = AI_CALL_PACKS  # Alias to new packs


# ─────────────────────────────────────────────────────────────────────────────
# SUBSCRIPTION MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def get_user_subscription(user_id: str) -> Dict:
    """
    Get user's subscription details from Cosmos DB.
    Creates a free trial subscription if none exists and free trial is enabled.

    Args:
        user_id: User's email or Firebase UID

    Returns:
        dict: Subscription data
    """
    try:
        # Try to get existing subscription
        sub_doc = db.collection('subscriptions').document(user_id).get()

        if sub_doc.exists:
            subscription = sub_doc.to_dict()
            subscription['user_id'] = user_id

            # Check if subscription is expired
            if subscription.get('status') == 'active':
                if subscription.get('plan_type') == 'free_trial':
                    trial_end = subscription.get('trial_end_date')
                    if trial_end and isinstance(trial_end, datetime):
                        # Make trial_end timezone-aware if it isn't already
                        if trial_end.tzinfo is None:
                            trial_end = trial_end.replace(tzinfo=timezone.utc)
                        if datetime.now(timezone.utc) > trial_end:
                            # Expire the trial
                            db.collection('subscriptions').document(user_id).update({
                                'status': 'expired',
                                'updated_at': SERVER_TIMESTAMP
                            })
                            subscription['status'] = 'expired'
                else:
                    # Check if paid subscription is expired
                    period_end = subscription.get('current_period_end')
                    if period_end and isinstance(period_end, datetime):
                        # Make period_end timezone-aware if it isn't already
                        if period_end.tzinfo is None:
                            period_end = period_end.replace(tzinfo=timezone.utc)
                        if datetime.now(timezone.utc) > period_end:
                            db.collection('subscriptions').document(user_id).update({
                                'status': 'expired',
                                'updated_at': SERVER_TIMESTAMP
                            })
                            subscription['status'] = 'expired'

            return subscription

        # No subscription exists - create free trial if enabled
        if FREE_TRIAL_ENABLED:
            trial_end = datetime.now(timezone.utc) + timedelta(days=FREE_TRIAL_DAYS)

            new_subscription = {
                'user_id': user_id,
                'plan_type': 'free_trial',
                'status': 'active',
                'trial_end_date': trial_end,
                'current_period_start': datetime.now(timezone.utc),
                'current_period_end': trial_end,
                'price_amount': 0,
                'currency': 'INR',
                'patients_created_this_month': 0,
                'patients_limit': FREE_TRIAL_PATIENTS,
                'ai_calls_this_month': 0,
                'ai_calls_limit': FREE_TRIAL_AI_CALLS,
                'ai_tokens_balance': 0,
                'ai_tokens_purchased_total': 0,
                'max_users': 1,
                'created_at': SERVER_TIMESTAMP,
                'updated_at': SERVER_TIMESTAMP
            }

            db.collection('subscriptions').document(user_id).set(new_subscription)
            logger.info(f"Created free trial subscription for {user_id}")

            return new_subscription

        # No trial, return inactive subscription
        return {
            'user_id': user_id,
            'plan_type': None,
            'status': 'inactive',
            'patients_limit': 0,
            'ai_calls_limit': 0,
            'ai_tokens_balance': 0
        }

    except Exception as e:
        logger.error(f"Error getting subscription for {user_id}: {e}")
        raise


def check_patient_limit(user_id: str) -> Tuple[bool, str]:
    """
    Check if user can create more patients.

    Args:
        user_id: User's email or Firebase UID

    Returns:
        tuple: (can_create: bool, message: str)
    """
    try:
        subscription = get_user_subscription(user_id)

        # Check if subscription is active
        if subscription.get('status') != 'active':
            return False, "Your subscription has expired. Please upgrade to continue."

        # Get limits
        patients_limit = subscription.get('patients_limit', 0)
        patients_created = subscription.get('patients_created_this_month', 0)

        # Unlimited patients (institute plan)
        if patients_limit == -1:
            return True, ""

        # Check limit
        if patients_created >= patients_limit:
            return False, f"Patient limit reached ({patients_limit}). Upgrade your plan or wait for next billing cycle."

        return True, ""

    except Exception as e:
        logger.error(f"Error checking patient limit for {user_id}: {e}")
        return False, "Error checking patient limit. Please try again."


def check_user_limit(institute_id: str) -> Tuple[bool, str, int, int]:
    """
    Check if institute can add more users.

    Args:
        institute_id: Institute ID (usually email of admin or institute identifier)

    Returns:
        tuple: (can_add_user: bool, message: str, current_users: int, max_users: int)
    """
    try:
        # Get institute subscription
        subscription = get_user_subscription(institute_id)

        # Check if subscription is active
        if subscription.get('status') != 'active':
            return False, "Institute subscription is not active", 0, 0

        # Get max users for this plan
        plan_type = subscription.get('plan_type')
        max_users = subscription.get('max_users', 1)

        # If no max_users in subscription, get from plan definition
        if not max_users or max_users == 0:
            plan_info = PLANS.get(plan_type, {})
            max_users = plan_info.get('max_users', 1)

        # Count current users in this institute
        # Assuming users have an 'institute_id' field
        users_query = db.collection('users').where('institute_id', '==', institute_id).stream()
        current_users = sum(1 for _ in users_query)

        # Check limit
        if current_users >= max_users:
            # Suggest upgrade path
            upgrade_message = f"User limit reached ({current_users}/{max_users}). "

            # Suggest next tier
            if plan_type == 'clinic':
                upgrade_message += "Upgrade to Institute (5 Users) plan for more users."
            elif plan_type == 'institute_5':
                upgrade_message += "Upgrade to Institute (10 Users) plan to add 5 more users (₹999/user)."
            elif plan_type == 'institute_10':
                upgrade_message += "Upgrade to Institute (15 Users) plan to add 5 more users (₹999/user)."
            elif plan_type == 'institute_15':
                upgrade_message += "Upgrade to Institute (20 Users) plan to add 5 more users (₹999/user)."
            elif plan_type == 'institute_20':
                upgrade_message += "Contact us for custom enterprise pricing for 25+ users."
            else:
                upgrade_message += "Upgrade your plan to add more users."

            return False, upgrade_message, current_users, max_users

        return True, "", current_users, max_users

    except Exception as e:
        logger.error(f"Error checking user limit for {institute_id}: {e}")
        return False, "Error checking user limit. Please try again.", 0, 0


def check_ai_limit(user_id: str) -> Tuple[bool, bool, str]:
    """
    Check if user can make AI calls.

    Args:
        user_id: User's email or Firebase UID

    Returns:
        tuple: (can_use_ai: bool, will_use_token: bool, message: str)
    """
    try:
        subscription = get_user_subscription(user_id)

        # Check if subscription is active
        if subscription.get('status') != 'active':
            return False, False, "Your subscription has expired. Please upgrade to continue using AI features."

        # Get limits
        ai_calls_limit = subscription.get('ai_calls_limit', 0)
        ai_calls_used = subscription.get('ai_calls_this_month', 0)
        ai_tokens = subscription.get('ai_tokens_balance', 0)

        # Check if within quota
        if ai_calls_used < ai_calls_limit:
            return True, False, ""

        # Quota exhausted, check if user has tokens
        if ai_tokens > 0:
            return True, True, "Using AI token from your balance"

        # No quota, no tokens
        return False, False, f"AI quota exhausted ({ai_calls_limit} calls). Purchase tokens or upgrade your plan."

    except Exception as e:
        logger.error(f"Error checking AI limit for {user_id}: {e}")
        return False, False, "Error checking AI quota. Please try again."


def deduct_patient_usage(user_id: str) -> bool:
    """
    Deduct one patient from user's quota.

    Args:
        user_id: User's email or Firebase UID

    Returns:
        bool: Success status
    """
    try:
        sub_ref = db.collection('subscriptions').document(user_id)
        sub_doc = sub_ref.get()

        if not sub_doc.exists:
            return False

        subscription = sub_doc.to_dict()
        patients_created = subscription.get('patients_created_this_month', 0)

        # Update count
        sub_ref.update({
            'patients_created_this_month': patients_created + 1,
            'updated_at': SERVER_TIMESTAMP
        })

        logger.info(f"Deducted patient usage for {user_id}: {patients_created + 1}")

        # Check and send quota notifications
        try:
            check_and_notify_quota(user_id, 'patients')
        except Exception as e:
            logger.warning(f"Failed to check quota notifications: {e}")

        return True

    except Exception as e:
        logger.error(f"Error deducting patient usage for {user_id}: {e}")
        return False


def deduct_ai_usage(user_id: str, use_token: bool = False, cache_hit: bool = False) -> bool:
    """
    Deduct AI usage from user's quota or token balance.

    Args:
        user_id: User's email or Firebase UID
        use_token: Whether to use a token instead of quota
        cache_hit: Whether this was a cache hit (free, don't deduct)

    Returns:
        bool: Success status
    """
    try:
        # Cache hits are free
        if cache_hit:
            logger.info(f"Cache hit for {user_id} - no usage deducted")
            return True

        sub_ref = db.collection('subscriptions').document(user_id)
        sub_doc = sub_ref.get()

        if not sub_doc.exists:
            return False

        subscription = sub_doc.to_dict()

        if use_token:
            # Deduct from token balance
            tokens = subscription.get('ai_tokens_balance', 0)
            if tokens <= 0:
                logger.error(f"No tokens available for {user_id}")
                return False

            sub_ref.update({
                'ai_tokens_balance': tokens - 1,
                'updated_at': SERVER_TIMESTAMP
            })

            logger.info(f"Deducted 1 token from {user_id}, remaining: {tokens - 1}")
        else:
            # Deduct from monthly quota
            ai_calls = subscription.get('ai_calls_this_month', 0)

            sub_ref.update({
                'ai_calls_this_month': ai_calls + 1,
                'updated_at': SERVER_TIMESTAMP
            })

            logger.info(f"Deducted AI quota for {user_id}: {ai_calls + 1}")

        # Log usage
        db.collection('ai_usage_logs').add({
            'user_id': user_id,
            'charged': not cache_hit,
            'used_token': use_token,
            'cache_hit': cache_hit,
            'timestamp': SERVER_TIMESTAMP
        })

        # Check and send quota notifications (only for quota usage, not tokens)
        if not use_token:
            try:
                check_and_notify_quota(user_id, 'ai')
            except Exception as e:
                logger.warning(f"Failed to check quota notifications: {e}")

        return True

    except Exception as e:
        logger.error(f"Error deducting AI usage for {user_id}: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# SUBSCRIPTION OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

def upgrade_subscription(user_id: str, plan_type: str, subscription_id: str = None,
                         payment_id: str = None, transaction_data: Dict = None) -> bool:
    """
    Upgrade user's subscription to a new plan.

    Args:
        user_id: User's email or Firebase UID
        plan_type: New plan type (starter, professional, clinic, institute)
        subscription_id: Razorpay subscription ID
        payment_id: Payment ID
        transaction_data: Additional transaction data

    Returns:
        bool: Success status
    """
    try:
        if plan_type not in PLANS:
            logger.error(f"Invalid plan type: {plan_type}")
            return False

        plan = PLANS[plan_type]
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)  # Monthly billing

        subscription_data = {
            'user_id': user_id,
            'plan_type': plan_type,
            'status': 'active',
            'subscription_id': subscription_id,
            'current_period_start': now,
            'current_period_end': period_end,
            'price_amount': plan['price'],
            'currency': plan['currency'],
            'patients_created_this_month': 0,
            'patients_limit': plan['patients_limit'],
            'ai_calls_this_month': 0,
            'ai_calls_limit': plan['ai_calls_limit'],
            'max_users': plan.get('max_users', 1),
            'updated_at': SERVER_TIMESTAMP
        }

        # Check if subscription already exists
        sub_ref = db.collection('subscriptions').document(user_id)
        sub_doc = sub_ref.get()

        if sub_doc.exists:
            # Update existing subscription
            existing_tokens = sub_doc.to_dict().get('ai_tokens_balance', 0)
            subscription_data['ai_tokens_balance'] = existing_tokens  # Preserve tokens
            sub_ref.update(subscription_data)
        else:
            # Create new subscription
            subscription_data['created_at'] = SERVER_TIMESTAMP
            subscription_data['ai_tokens_balance'] = 0
            subscription_data['ai_tokens_purchased_total'] = 0
            sub_ref.set(subscription_data)

        # Log transaction
        if transaction_data:
            db.collection('payment_transactions').add({
                'user_id': user_id,
                'type': 'subscription',
                'plan_type': plan_type,
                'amount': plan['price'],
                'currency': plan['currency'],
                'gateway_payment_id': payment_id,
                'subscription_id': subscription_id,
                'status': 'success',
                'created_at': SERVER_TIMESTAMP,
                **transaction_data
            })

        logger.info(f"Upgraded {user_id} to {plan_type} plan")
        return True

    except Exception as e:
        logger.error(f"Error upgrading subscription for {user_id}: {e}")
        return False


def cancel_subscription(user_id: str) -> bool:
    """
    Cancel user's subscription (will remain active until period end).

    Args:
        user_id: User's email or Firebase UID

    Returns:
        bool: Success status
    """
    try:
        db.collection('subscriptions').document(user_id).update({
            'status': 'cancelled',
            'cancelled_at': SERVER_TIMESTAMP,
            'updated_at': SERVER_TIMESTAMP
        })

        logger.info(f"Cancelled subscription for {user_id}")
        return True

    except Exception as e:
        logger.error(f"Error cancelling subscription for {user_id}: {e}")
        return False


def purchase_ai_calls(user_id: str, package: str, payment_id: str = None,
                     transaction_data: Dict = None) -> bool:
    """
    Add purchased AI calls to user's balance.

    Args:
        user_id: User's email or Firebase UID
        package: AI call package name (starter, regular, popular, professional, enterprise)
        payment_id: Payment ID
        transaction_data: Additional transaction data

    Returns:
        bool: Success status
    """
    try:
        if package not in AI_CALL_PACKS:
            logger.error(f"Invalid AI call package: {package}")
            return False

        package_info = AI_CALL_PACKS[package]
        calls_to_add = package_info['calls']

        # Get current subscription
        sub_ref = db.collection('subscriptions').document(user_id)
        sub_doc = sub_ref.get()

        if not sub_doc.exists:
            # Create minimal subscription if doesn't exist
            sub_ref.set({
                'user_id': user_id,
                'plan_type': None,
                'status': 'inactive',
                'ai_tokens_balance': calls_to_add,  # Using same field for compatibility
                'ai_tokens_purchased_total': calls_to_add,
                'created_at': SERVER_TIMESTAMP,
                'updated_at': SERVER_TIMESTAMP
            })
        else:
            # Add AI calls to existing balance
            current_balance = sub_doc.to_dict().get('ai_tokens_balance', 0)
            total_purchased = sub_doc.to_dict().get('ai_tokens_purchased_total', 0)

            sub_ref.update({
                'ai_tokens_balance': current_balance + calls_to_add,
                'ai_tokens_purchased_total': total_purchased + calls_to_add,
                'updated_at': SERVER_TIMESTAMP
            })

        # Log AI call pack purchase
        db.collection('ai_call_purchases').add({
            'user_id': user_id,
            'package': package,
            'calls': calls_to_add,
            'amount_paid': package_info['price'],
            'created_at': SERVER_TIMESTAMP
        })

        # Log transaction
        if transaction_data:
            db.collection('payment_transactions').add({
                'user_id': user_id,
                'type': 'ai_call_purchase',
                'ai_calls_purchased': calls_to_add,
                'amount': package_info['price'],
                'currency': 'INR',
                'gateway_payment_id': payment_id,
                'status': 'success',
                'created_at': SERVER_TIMESTAMP,
                **transaction_data
            })

        logger.info(f"Added {calls_to_add} AI calls to {user_id}")
        return True

    except Exception as e:
        logger.error(f"Error purchasing AI calls for {user_id}: {e}")
        return False


# Legacy function (DEPRECATED - use purchase_ai_calls instead)
def purchase_tokens(user_id: str, package: str, payment_id: str = None,
                   transaction_data: Dict = None) -> bool:
    """DEPRECATED: Use purchase_ai_calls instead. Kept for backward compatibility."""
    return purchase_ai_calls(user_id, package, payment_id, transaction_data)


def reset_monthly_quota(user_id: str) -> bool:
    """
    Reset monthly usage quotas (called by cron job).

    Args:
        user_id: User's email or Firebase UID

    Returns:
        bool: Success status
    """
    try:
        sub_ref = db.collection('subscriptions').document(user_id)
        sub_doc = sub_ref.get()

        if not sub_doc.exists:
            return False

        subscription = sub_doc.to_dict()

        # Only reset if subscription is active
        if subscription.get('status') == 'active':
            # Update billing period
            now = datetime.now(timezone.utc)
            period_end = now + timedelta(days=30)

            sub_ref.update({
                'patients_created_this_month': 0,
                'ai_calls_this_month': 0,
                'current_period_start': now,
                'current_period_end': period_end,
                'updated_at': SERVER_TIMESTAMP
            })

            logger.info(f"Reset monthly quota for {user_id}")

        return True

    except Exception as e:
        logger.error(f"Error resetting quota for {user_id}: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_usage_stats(user_id: str) -> Dict:
    """
    Get detailed usage statistics for a user.

    Args:
        user_id: User's email or Firebase UID

    Returns:
        dict: Usage statistics
    """
    try:
        subscription = get_user_subscription(user_id)

        patients_used = subscription.get('patients_created_this_month', 0)
        patients_limit = subscription.get('patients_limit', 0)
        ai_calls_used = subscription.get('ai_calls_this_month', 0)
        ai_calls_limit = subscription.get('ai_calls_limit', 0)
        tokens = subscription.get('ai_tokens_balance', 0)

        # Calculate percentages
        patients_percent = (patients_used / patients_limit * 100) if patients_limit > 0 else 0
        ai_percent = (ai_calls_used / ai_calls_limit * 100) if ai_calls_limit > 0 else 0

        return {
            'plan_type': subscription.get('plan_type'),
            'status': subscription.get('status'),
            'patients_used': patients_used,
            'patients_limit': patients_limit,
            'patients_percent': round(patients_percent, 1),
            'ai_calls_used': ai_calls_used,
            'ai_calls_limit': ai_calls_limit,
            'ai_percent': round(ai_percent, 1),
            'tokens_balance': tokens,
            'period_end': subscription.get('current_period_end'),
            'trial_end': subscription.get('trial_end_date')
        }

    except Exception as e:
        logger.error(f"Error getting usage stats for {user_id}: {e}")
        return {}


def get_plan_info(plan_type: str) -> Optional[Dict]:
    """
    Get plan configuration details.

    Args:
        plan_type: Plan type (starter, professional, etc.)

    Returns:
        dict: Plan information or None if invalid
    """
    return PLANS.get(plan_type)


def get_all_plans() -> Dict:
    """Get all available plans."""
    return PLANS


def get_ai_call_packs() -> Dict:
    """Get all available AI call packages."""
    return AI_CALL_PACKS


def get_token_packages() -> Dict:
    """DEPRECATED: Get all available token packages. Use get_ai_call_packs() instead."""
    return AI_CALL_PACKS  # Return AI call packs for backward compatibility


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATION TRIGGERS
# ─────────────────────────────────────────────────────────────────────────────

def check_and_notify_quota(user_id: str, quota_type: str = 'all') -> None:
    """
    Check usage thresholds and create notifications if needed.

    Args:
        user_id: User's email or Firebase UID
        quota_type: 'ai', 'patients', or 'all'
    """
    try:
        from notification_service import notify_quota_warning

        subscription = get_user_subscription(user_id)

        if subscription.get('status') != 'active':
            return

        # Check AI quota
        if quota_type in ['ai', 'all']:
            ai_calls_used = subscription.get('ai_calls_this_month', 0)
            ai_calls_limit = subscription.get('ai_calls_limit', 0)

            if ai_calls_limit > 0:
                ai_percent = (ai_calls_used / ai_calls_limit) * 100

                # Create notification at 80%, 90%, and 100% thresholds
                if ai_percent >= 100 and ai_calls_used == ai_calls_limit:
                    notify_quota_warning(user_id, 'AI Calls', 100, ai_calls_used, ai_calls_limit)
                    logger.info(f"Sent 100% AI quota notification to {user_id}")
                elif ai_percent >= 90 and ai_calls_used == int(ai_calls_limit * 0.9):
                    notify_quota_warning(user_id, 'AI Calls', 90, ai_calls_used, ai_calls_limit)
                    logger.info(f"Sent 90% AI quota notification to {user_id}")
                elif ai_percent >= 80 and ai_calls_used == int(ai_calls_limit * 0.8):
                    notify_quota_warning(user_id, 'AI Calls', 80, ai_calls_used, ai_calls_limit)
                    logger.info(f"Sent 80% AI quota notification to {user_id}")

        # Check patient quota
        if quota_type in ['patients', 'all']:
            patients_used = subscription.get('patients_created_this_month', 0)
            patients_limit = subscription.get('patients_limit', 0)

            if patients_limit > 0 and patients_limit != -1:  # -1 means unlimited
                patients_percent = (patients_used / patients_limit) * 100

                # Create notification at 80%, 90%, and 100% thresholds
                if patients_percent >= 100 and patients_used == patients_limit:
                    notify_quota_warning(user_id, 'Patients', 100, patients_used, patients_limit)
                    logger.info(f"Sent 100% patient quota notification to {user_id}")
                elif patients_percent >= 90 and patients_used == int(patients_limit * 0.9):
                    notify_quota_warning(user_id, 'Patients', 90, patients_used, patients_limit)
                    logger.info(f"Sent 90% patient quota notification to {user_id}")
                elif patients_percent >= 80 and patients_used == int(patients_limit * 0.8):
                    notify_quota_warning(user_id, 'Patients', 80, patients_used, patients_limit)
                    logger.info(f"Sent 80% patient quota notification to {user_id}")

    except Exception as e:
        logger.error(f"Error checking quota notifications for {user_id}: {e}")


def check_subscription_reminders() -> Dict:
    """
    Check all subscriptions and send renewal/expiry reminders.
    Should be called daily by a scheduled job.

    Returns:
        dict: Summary of notifications sent
    """
    try:
        from notification_service import notify_renewal_reminder, notify_trial_expiring

        summary = {
            'renewal_reminders': 0,
            'trial_expiring': 0,
            'errors': 0
        }

        # Get all active subscriptions
        subscriptions = db.collection('subscriptions').where('status', '==', 'active').stream()

        now = datetime.now(timezone.utc)
        reminder_days = [7, 3, 1]  # Days before expiry to send reminders

        for sub_doc in subscriptions:
            try:
                subscription = sub_doc.to_dict()
                user_id = sub_doc.id
                plan_type = subscription.get('plan_type')

                if plan_type == 'free_trial':
                    # Check trial expiry
                    trial_end = subscription.get('trial_end_date')
                    if trial_end and isinstance(trial_end, datetime):
                        # Make trial_end timezone-aware if it isn't already
                        if trial_end.tzinfo is None:
                            trial_end = trial_end.replace(tzinfo=timezone.utc)
                        days_remaining = (trial_end - now).days

                        if days_remaining in reminder_days:
                            notify_trial_expiring(user_id, days_remaining)
                            summary['trial_expiring'] += 1
                            logger.info(f"Sent trial expiring notification to {user_id} ({days_remaining} days)")
                else:
                    # Check subscription renewal
                    period_end = subscription.get('current_period_end')
                    if period_end and isinstance(period_end, datetime):
                        # Make period_end timezone-aware if it isn't already
                        if period_end.tzinfo is None:
                            period_end = period_end.replace(tzinfo=timezone.utc)
                        days_remaining = (period_end - now).days

                        if days_remaining in reminder_days:
                            plan_name = PLANS.get(plan_type, {}).get('name', plan_type)
                            renewal_date = period_end.strftime('%B %d, %Y')
                            notify_renewal_reminder(user_id, plan_name, days_remaining, renewal_date)
                            summary['renewal_reminders'] += 1
                            logger.info(f"Sent renewal reminder to {user_id} ({days_remaining} days)")

            except Exception as e:
                logger.error(f"Error processing subscription for {sub_doc.id}: {e}")
                summary['errors'] += 1

        logger.info(f"Subscription reminder check complete: {summary}")
        return summary

    except Exception as e:
        logger.error(f"Error checking subscription reminders: {e}")
        return {'error': str(e)}
