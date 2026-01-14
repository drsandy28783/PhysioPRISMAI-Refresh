"""
Razorpay Payment Gateway Integration for Physio-Assist
=======================================================

This module handles Razorpay payment integration for:
- Subscription payments
- Token purchases
- Webhook handling
- Payment verification

Setup Requirements:
1. Sign up at https://razorpay.com/
2. Complete KYC verification
3. Create subscription plans in Razorpay dashboard
4. Set environment variables (see below)
"""

import os
import hmac
import hashlib
import logging
from typing import Dict, Optional, Tuple
import razorpay
# Firebase removed - using Azure Cosmos DB
from azure_cosmos_db import SERVER_TIMESTAMP

logger = logging.getLogger("app.razorpay")

# Razorpay credentials from environment
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')
RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET')

# Initialize Razorpay client
razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        logger.info("Razorpay client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Razorpay client: {e}")
else:
    logger.warning("Razorpay credentials not found - payment features disabled")


# Get Cosmos DB client
db = get_cosmos_db()

# ─────────────────────────────────────────────────────────────────────────────
# SUBSCRIPTION PAYMENT
# ─────────────────────────────────────────────────────────────────────────────

def create_subscription_checkout(user_id: str, plan_type: str, user_name: str = "",
                                 user_email: str = "", user_phone: str = "") -> Optional[Dict]:
    """
    Create a Razorpay subscription checkout session.

    Args:
        user_id: User's email or Firebase UID
        plan_type: Plan type (starter, professional, clinic, institute)
        user_name: User's name
        user_email: User's email
        user_phone: User's phone number

    Returns:
        dict: Razorpay subscription data or None if error
    """
    if not razorpay_client:
        logger.error(f"Razorpay client not initialized. RAZORPAY_KEY_ID={'set' if RAZORPAY_KEY_ID else 'NOT SET'}, RAZORPAY_KEY_SECRET={'set' if RAZORPAY_KEY_SECRET else 'NOT SET'}")
        return None

    if not RAZORPAY_KEY_ID:
        logger.error("RAZORPAY_KEY_ID is not set in environment variables")
        return None

    try:
        # Get plan configuration
        from subscription_manager import PLANS

        if plan_type not in PLANS:
            logger.error(f"Invalid plan type: {plan_type}")
            return None

        plan = PLANS[plan_type]

        # Get Razorpay plan ID from environment
        razorpay_plan_id = os.environ.get(f'RAZORPAY_PLAN_{plan_type.upper()}')

        if not razorpay_plan_id:
            logger.error(f"Razorpay plan ID not found for {plan_type}")
            return None

        # Create subscription
        subscription_data = {
            'plan_id': razorpay_plan_id,
            'customer_notify': 1,
            'quantity': 1,
            # total_count not set = indefinite subscription (renews until cancelled)
            # This is standard for SaaS products - customer can cancel anytime
            'notes': {
                'user_id': user_id,
                'plan_type': plan_type
            }
        }

        subscription = razorpay_client.subscription.create(subscription_data)

        logger.info(f"Created Razorpay subscription for {user_id}: {subscription['id']}")

        return {
            'subscription_id': subscription['id'],
            'razorpay_key': RAZORPAY_KEY_ID,
            'plan_name': plan['name'],
            'amount': plan['price'] * 100,  # Razorpay uses paise
            'currency': plan['currency'],
            'name': user_name,
            'email': user_email,
            'phone': user_phone,
            'description': f'{plan["name"]} Subscription'
        }

    except Exception as e:
        logger.error(f"Error creating subscription checkout: {e}")
        return None


def verify_subscription_payment(razorpay_payment_id: str, razorpay_subscription_id: str,
                                razorpay_signature: str) -> bool:
    """
    Verify Razorpay subscription payment signature.

    Args:
        razorpay_payment_id: Payment ID from Razorpay
        razorpay_subscription_id: Subscription ID from Razorpay
        razorpay_signature: Signature from Razorpay

    Returns:
        bool: True if signature is valid
    """
    if not razorpay_client:
        return False

    try:
        # Verify signature
        params = {
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_subscription_id': razorpay_subscription_id,
            'razorpay_signature': razorpay_signature
        }

        razorpay_client.utility.verify_payment_signature(params)
        logger.info(f"Verified subscription payment: {razorpay_payment_id}")
        return True

    except razorpay.errors.SignatureVerificationError as e:
        logger.error(f"Signature verification failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# ONE-TIME PAYMENT (for tokens)
# ─────────────────────────────────────────────────────────────────────────────

def create_token_purchase_order(user_id: str, package: str, user_email: str = "",
                                user_phone: str = "", user_name: str = "") -> Optional[Dict]:
    """
    Create a Razorpay order for token purchase.

    Args:
        user_id: User's email or Firebase UID
        package: Token package name
        user_email: User's email
        user_phone: User's phone number
        user_name: User's name

    Returns:
        dict: Razorpay order data or None if error
    """
    if not razorpay_client:
        logger.error("Razorpay client not initialized")
        return None

    try:
        # Get package configuration
        from subscription_manager import TOKEN_PACKAGES

        if package not in TOKEN_PACKAGES:
            logger.error(f"Invalid token package: {package}")
            return None

        package_info = TOKEN_PACKAGES[package]

        # Create order
        order_data = {
            'amount': package_info['price'] * 100,  # Razorpay uses paise
            'currency': 'INR',
            'receipt': f'token_{user_id}_{package}',
            'notes': {
                'user_id': user_id,
                'package': package,
                'tokens': package_info['calls'],  # AI_CALL_PACKS uses 'calls' key
                'type': 'token_purchase'
            }
        }

        order = razorpay_client.order.create(order_data)

        logger.info(f"Created Razorpay order for {user_id}: {order['id']}")

        return {
            'order_id': order['id'],
            'razorpay_key': RAZORPAY_KEY_ID,
            'amount': order_data['amount'],
            'currency': order_data['currency'],
            'name': user_name,
            'email': user_email,
            'phone': user_phone,
            'description': f'{package_info["calls"]} AI Calls'  # AI_CALL_PACKS uses 'calls' key
        }

    except Exception as e:
        logger.error(f"Error creating token purchase order: {e}")
        return None


def verify_token_payment(razorpay_order_id: str, razorpay_payment_id: str,
                        razorpay_signature: str) -> bool:
    """
    Verify Razorpay order payment signature.

    Args:
        razorpay_order_id: Order ID from Razorpay
        razorpay_payment_id: Payment ID from Razorpay
        razorpay_signature: Signature from Razorpay

    Returns:
        bool: True if signature is valid
    """
    if not razorpay_client:
        return False

    try:
        # Verify signature
        params = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        razorpay_client.utility.verify_payment_signature(params)
        logger.info(f"Verified token payment: {razorpay_payment_id}")
        return True

    except razorpay.errors.SignatureVerificationError as e:
        logger.error(f"Signature verification failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOK HANDLING
# ─────────────────────────────────────────────────────────────────────────────

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify Razorpay webhook signature.

    Args:
        payload: Raw webhook payload (bytes)
        signature: X-Razorpay-Signature header value

    Returns:
        bool: True if signature is valid
    """
    if not RAZORPAY_WEBHOOK_SECRET:
        logger.error("Webhook secret not configured")
        return False

    try:
        # Generate expected signature
        expected_signature = hmac.new(
            RAZORPAY_WEBHOOK_SECRET.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Compare signatures
        return hmac.compare_digest(expected_signature, signature)

    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False


def handle_webhook_event(event_data: Dict) -> Tuple[bool, str]:
    """
    Handle Razorpay webhook event.

    Args:
        event_data: Parsed webhook event data

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        event = event_data.get('event')
        payload = event_data.get('payload', {})

        logger.info(f"Handling webhook event: {event}")

        # Handle different event types
        if event == 'subscription.activated':
            return handle_subscription_activated(payload)

        elif event == 'subscription.charged':
            return handle_subscription_charged(payload)

        elif event == 'payment.captured':
            return handle_payment_captured(payload)

        elif event == 'payment.failed':
            return handle_payment_failed(payload)

        elif event == 'subscription.cancelled':
            return handle_subscription_cancelled(payload)

        else:
            logger.info(f"Unhandled event type: {event}")
            return True, f"Event {event} acknowledged but not processed"

    except Exception as e:
        logger.error(f"Error handling webhook event: {e}")
        return False, str(e)


def handle_subscription_activated(payload: Dict) -> Tuple[bool, str]:
    """Handle subscription.activated event."""
    try:
        subscription = payload.get('subscription', {}).get('entity', {})
        payment = payload.get('payment', {}).get('entity', {})
        subscription_id = subscription.get('id')
        notes = subscription.get('notes', {})
        user_id = notes.get('user_id')
        plan_type = notes.get('plan_type')

        if not user_id or not plan_type:
            return False, "Missing user_id or plan_type in notes"

        # Activate subscription in our system
        from subscription_manager import upgrade_subscription

        success = upgrade_subscription(
            user_id=user_id,
            plan_type=plan_type,
            subscription_id=subscription_id,
            transaction_data={'webhook_event': 'subscription.activated'}
        )

        # Generate invoice and send email for initial subscription payment
        try:
            from invoice_generator import create_and_send_invoice
            amount_in_paise = payment.get('amount', 0) if payment else subscription.get('amount', 0)
            amount = amount_in_paise / 100  # Convert from paise to rupees

            invoice_data = create_and_send_invoice(
                user_id=user_id,
                payment_id=payment.get('id') if payment else subscription_id,
                amount=amount,
                plan_type=plan_type,
                payment_method='Razorpay',
                transaction_type='subscription'
            )
            if invoice_data:
                logger.info(f"Generated and sent invoice {invoice_data.get('invoice_number')} for {user_id}")
            else:
                logger.warning(f"Failed to generate invoice for subscription activation: {user_id}")
        except Exception as e:
            logger.error(f"Error generating invoice for subscription activation: {e}")
            # Don't fail the webhook if invoice generation fails

        if success:
            logger.info(f"Activated subscription for {user_id}: {plan_type}")
            return True, "Subscription activated"
        else:
            return False, "Failed to activate subscription"

    except Exception as e:
        logger.error(f"Error handling subscription.activated: {e}")
        return False, str(e)


def handle_subscription_charged(payload: Dict) -> Tuple[bool, str]:
    """Handle subscription.charged event (renewal)."""
    try:
        payment = payload.get('payment', {}).get('entity', {})
        subscription = payload.get('subscription', {}).get('entity', {})

        subscription_id = subscription.get('id')
        notes = subscription.get('notes', {})
        user_id = notes.get('user_id')
        plan_type = notes.get('plan_type', 'unknown')

        if not user_id:
            return False, "Missing user_id in notes"

        # Reset monthly quota
        from subscription_manager import reset_monthly_quota

        success = reset_monthly_quota(user_id)

        # Get payment amount
        amount_in_paise = payment.get('amount', 0)
        amount = amount_in_paise / 100  # Convert from paise to rupees

        # Log transaction
        db.collection('payment_transactions').add({
            'user_id': user_id,
            'type': 'subscription_renewal',
            'subscription_id': subscription_id,
            'gateway_payment_id': payment.get('id'),
            'amount': amount,
            'currency': payment.get('currency', 'INR'),
            'status': 'success',
            'created_at': SERVER_TIMESTAMP
        })

        # Generate invoice and send email (GST compliance)
        try:
            from invoice_generator import create_and_send_invoice
            invoice_data = create_and_send_invoice(
                user_id=user_id,
                payment_id=payment.get('id'),
                amount=amount,
                plan_type=plan_type,
                payment_method='Razorpay',
                transaction_type='subscription'
            )
            if invoice_data:
                logger.info(f"Generated and sent invoice {invoice_data.get('invoice_number')} for {user_id}")
            else:
                logger.warning(f"Failed to generate invoice for subscription renewal: {user_id}")
        except Exception as e:
            logger.error(f"Error generating invoice for subscription renewal: {e}")
            # Don't fail the webhook if invoice generation fails

        if success:
            logger.info(f"Subscription charged and quota reset for {user_id}")
            return True, "Subscription charged"
        else:
            return False, "Failed to reset quota"

    except Exception as e:
        logger.error(f"Error handling subscription.charged: {e}")
        return False, str(e)


def handle_payment_captured(payload: Dict) -> Tuple[bool, str]:
    """Handle payment.captured event (for one-time payments like tokens)."""
    try:
        payment = payload.get('payment', {}).get('entity', {})
        payment_id = payment.get('id')
        order_id = payment.get('order_id')
        notes = payment.get('notes', {})

        # Check if this is a token purchase
        if notes.get('type') == 'token_purchase':
            user_id = notes.get('user_id')
            package = notes.get('package')

            if not user_id or not package:
                return False, "Missing user_id or package in notes"

            # Add tokens to user's account
            from subscription_manager import purchase_tokens

            success = purchase_tokens(
                user_id=user_id,
                package=package,
                payment_id=payment_id,
                transaction_data={
                    'order_id': order_id,
                    'webhook_event': 'payment.captured'
                }
            )

            # Generate invoice and send email for token purchase
            try:
                from invoice_generator import create_and_send_invoice
                amount_in_paise = payment.get('amount', 0)
                amount = amount_in_paise / 100  # Convert from paise to rupees

                invoice_data = create_and_send_invoice(
                    user_id=user_id,
                    payment_id=payment_id,
                    amount=amount,
                    plan_type=package,
                    payment_method='Razorpay',
                    transaction_type='token_purchase'
                )
                if invoice_data:
                    logger.info(f"Generated and sent invoice {invoice_data.get('invoice_number')} for {user_id}")
                else:
                    logger.warning(f"Failed to generate invoice for token purchase: {user_id}")
            except Exception as e:
                logger.error(f"Error generating invoice for token purchase: {e}")
                # Don't fail the webhook if invoice generation fails

            if success:
                logger.info(f"Token purchase completed for {user_id}: {package}")
                return True, "Token purchase completed"
            else:
                return False, "Failed to add tokens"

        return True, "Payment captured (not a token purchase)"

    except Exception as e:
        logger.error(f"Error handling payment.captured: {e}")
        return False, str(e)


def handle_payment_failed(payload: Dict) -> Tuple[bool, str]:
    """Handle payment.failed event."""
    try:
        payment = payload.get('payment', {}).get('entity', {})
        payment_id = payment.get('id')
        notes = payment.get('notes', {})
        user_id = notes.get('user_id')

        # Log failed transaction
        db.collection('payment_transactions').add({
            'user_id': user_id or 'unknown',
            'type': 'payment_failed',
            'gateway_payment_id': payment_id,
            'amount': payment.get('amount', 0) / 100,
            'currency': payment.get('currency', 'INR'),
            'status': 'failed',
            'error_reason': payment.get('error_reason', 'Unknown'),
            'created_at': SERVER_TIMESTAMP
        })

        logger.warning(f"Payment failed for {user_id}: {payment_id}")
        return True, "Payment failure logged"

    except Exception as e:
        logger.error(f"Error handling payment.failed: {e}")
        return False, str(e)


def handle_subscription_cancelled(payload: Dict) -> Tuple[bool, str]:
    """Handle subscription.cancelled event."""
    try:
        subscription = payload.get('subscription', {}).get('entity', {})
        notes = subscription.get('notes', {})
        user_id = notes.get('user_id')

        if not user_id:
            return False, "Missing user_id in notes"

        # Cancel subscription in our system
        from subscription_manager import cancel_subscription

        success = cancel_subscription(user_id)

        if success:
            logger.info(f"Cancelled subscription for {user_id}")
            return True, "Subscription cancelled"
        else:
            return False, "Failed to cancel subscription"

    except Exception as e:
        logger.error(f"Error handling subscription.cancelled: {e}")
        return False, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_payment_status(payment_id: str) -> Optional[Dict]:
    """
    Get payment status from Razorpay.

    Args:
        payment_id: Razorpay payment ID

    Returns:
        dict: Payment data or None if error
    """
    if not razorpay_client:
        return None

    try:
        payment = razorpay_client.payment.fetch(payment_id)
        return payment
    except Exception as e:
        logger.error(f"Error fetching payment status: {e}")
        return None


def get_subscription_status(subscription_id: str) -> Optional[Dict]:
    """
    Get subscription status from Razorpay.

    Args:
        subscription_id: Razorpay subscription ID

    Returns:
        dict: Subscription data or None if error
    """
    if not razorpay_client:
        return None

    try:
        subscription = razorpay_client.subscription.fetch(subscription_id)
        return subscription
    except Exception as e:
        logger.error(f"Error fetching subscription status: {e}")
        return None


def cancel_razorpay_subscription(subscription_id: str) -> bool:
    """
    Cancel a subscription on Razorpay.

    Args:
        subscription_id: Razorpay subscription ID

    Returns:
        bool: Success status
    """
    if not razorpay_client:
        return False

    try:
        razorpay_client.subscription.cancel(subscription_id)
        logger.info(f"Cancelled Razorpay subscription: {subscription_id}")
        return True
    except Exception as e:
        logger.error(f"Error cancelling Razorpay subscription: {e}")
        return False
