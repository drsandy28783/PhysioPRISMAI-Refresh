"""
Email Verification Module

Handles email verification tokens and verification workflow.
"""

import os
import logging
from azure_cosmos_db import get_cosmos_db, SERVER_TIMESTAMP

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger("app.email_verification")

# Initialize Cosmos DB
db = get_cosmos_db()

# Token expiry duration (24 hours)
TOKEN_EXPIRY_HOURS = 24


def generate_verification_token() -> str:
    """
    Generate a cryptographically secure verification token.

    Returns:
        str: 32-character hex token
    """
    return secrets.token_hex(32)


def hash_token(token: str) -> str:
    """
    Hash the token using SHA-256 for secure storage.

    Args:
        token: Raw verification token

    Returns:
        str: SHA-256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def create_verification_token(email: str) -> str:
    """
    Create a new email verification token for a user.

    Args:
        email: User's email address

    Returns:
        str: Verification token (not hashed - send this in email)
    """
    try:
        # Generate token
        token = generate_verification_token()
        token_hash = hash_token(token)

        # Calculate expiry time
        from datetime import timezone
        expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)

        # Store in Cosmos DB
        db.collection('email_verification_tokens').document(email).set({
            'email': email,
            'token_hash': token_hash,
            'created_at': SERVER_TIMESTAMP,
            'expires_at': expires_at.isoformat(),  # Convert to ISO string for JSON serialization
            'verified': False,
            'attempts': 0  # Track verification attempts for security
        })

        logger.info(f"Created verification token for {email}")
        return token

    except Exception as e:
        logger.error(f"Error creating verification token for {email}: {e}", exc_info=True)
        raise


def verify_token(email: str, token: str) -> tuple[bool, str]:
    """
    Verify an email verification token.

    Args:
        email: User's email address
        token: Token from verification link

    Returns:
        tuple[bool, str]: (Success status, Message)
    """
    try:
        # Get token document
        token_doc = db.collection('email_verification_tokens').document(email).get()

        if not token_doc.exists:
            return False, "No verification token found for this email"

        token_data = token_doc.to_dict()

        # Check if already verified
        if token_data.get('verified', False):
            return False, "Email already verified"

        # Check expiry
        expires_at = token_data.get('expires_at')
        if expires_at:
            # Handle both ISO string and datetime object
            from datetime import timezone
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            # Make expires_at timezone-aware if it's not
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if current_time > expires_at:
                return False, "Verification token has expired. Please request a new one"

        # Check attempts limit (prevent brute force)
        attempts = token_data.get('attempts', 0)
        if attempts >= 5:
            return False, "Too many verification attempts. Please request a new token"

        # Verify token hash
        token_hash = hash_token(token)
        if token_hash != token_data.get('token_hash'):
            # Increment attempts (manual increment for Cosmos DB)
            db.collection('email_verification_tokens').document(email).update({
                'attempts': attempts + 1
            })
            return False, "Invalid verification token"

        # Token is valid - mark as verified
        db.collection('email_verification_tokens').document(email).update({
            'verified': True,
            'verified_at': SERVER_TIMESTAMP
        })

        # Update user document
        db.collection('users').document(email).update({
            'email_verified': True,
            'email_verified_at': SERVER_TIMESTAMP
        })

        logger.info(f"Email verified successfully for {email}")
        return True, "Email verified successfully!"

    except Exception as e:
        logger.error(f"Error verifying token for {email}: {e}", exc_info=True)
        return False, "An error occurred during verification"


def is_email_verified(email: str) -> bool:
    """
    Check if a user's email is verified.

    Args:
        email: User's email address

    Returns:
        bool: True if email is verified, False otherwise
    """
    try:
        user_doc = db.collection('users').document(email).get()
        if not user_doc.exists:
            return False

        user_data = user_doc.to_dict()
        return user_data.get('email_verified', False)

    except Exception as e:
        logger.error(f"Error checking email verification status for {email}: {e}", exc_info=True)
        return False


def delete_verification_token(email: str) -> bool:
    """
    Delete a verification token (useful for cleanup or resend).

    Args:
        email: User's email address

    Returns:
        bool: True if deleted, False otherwise
    """
    try:
        db.collection('email_verification_tokens').document(email).delete()
        logger.info(f"Deleted verification token for {email}")
        return True
    except Exception as e:
        logger.error(f"Error deleting verification token for {email}: {e}", exc_info=True)
        return False


def resend_verification_token(email: str) -> Optional[str]:
    """
    Resend verification token (creates new token, deletes old one).

    Args:
        email: User's email address

    Returns:
        str: New verification token, or None if failed
    """
    try:
        # Check if user exists
        user_doc = db.collection('users').document(email).get()
        if not user_doc.exists:
            logger.warning(f"Attempted to resend verification for non-existent user: {email}")
            return None

        # Check if already verified
        if is_email_verified(email):
            logger.info(f"Email already verified for {email}, skipping resend")
            return None

        # Delete old token
        delete_verification_token(email)

        # Create new token
        token = create_verification_token(email)
        logger.info(f"Resent verification token for {email}")
        return token

    except Exception as e:
        logger.error(f"Error resending verification token for {email}: {e}", exc_info=True)
        return None
