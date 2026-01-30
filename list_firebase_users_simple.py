#!/usr/bin/env python3
"""
Simple script to list Firebase Auth users using the existing app_auth initialization
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# IMPORTANT: Load .env BEFORE importing app_auth
from dotenv import load_dotenv
load_dotenv()

try:
    # Import Firebase Admin - this will use the initialization from app_auth
    import app_auth
    from firebase_admin import auth
    from azure_cosmos_db import get_cosmos_db

    print("\n" + "="*70)
    print("FIREBASE AUTHENTICATION USERS")
    print("="*70)

    # List all users
    page = auth.list_users()

    users = []
    while page:
        for user in page.users:
            users.append({
                'uid': user.uid,
                'email': user.email,
                'email_verified': user.email_verified,
                'disabled': user.disabled,
                'display_name': user.display_name,
                'creation_time': user.user_metadata.creation_timestamp if user.user_metadata else None
            })

        # Get next page
        page = page.get_next_page() if page.has_next_page else None

    if not users:
        print("No users found in Firebase Auth")
    else:
        print(f"Total users: {len(users)}\n")

        for user in users:
            print(f"Email: {user['email']}")
            print(f"  UID: {user['uid']}")
            print(f"  Display Name: {user['display_name']}")
            print(f"  Email Verified: {user['email_verified']}")
            print(f"  Disabled: {user['disabled']}")
            print(f"  Created: {user['creation_time']}")
            print()

    print("="*70)

    # Compare with Cosmos DB
    print("\n" + "="*70)
    print("COMPARING WITH COSMOS DB")
    print("="*70)

    db = get_cosmos_db()
    cosmos_users = list(db.collection('users').stream())
    cosmos_emails = set(doc.id for doc in cosmos_users)
    firebase_emails = set(u['email'] for u in users if u['email'])

    print(f"\nCosmos DB users: {len(cosmos_emails)}")
    print(f"Firebase Auth users: {len(firebase_emails)}")

    # Users in Firebase but not in Cosmos DB
    firebase_only = firebase_emails - cosmos_emails
    if firebase_only:
        print(f"\n[WARNING] Users in Firebase Auth but NOT in Cosmos DB ({len(firebase_only)}):")
        for email in sorted(firebase_only):
            print(f"  - {email}")

    # Users in Cosmos DB but not in Firebase
    cosmos_only = cosmos_emails - firebase_emails
    if cosmos_only:
        print(f"\n[WARNING] Users in Cosmos DB but NOT in Firebase Auth ({len(cosmos_only)}):")
        for email in sorted(cosmos_only):
            print(f"  - {email}")

    if not firebase_only and not cosmos_only:
        print("\n[OK] All users are in sync between Firebase Auth and Cosmos DB")

    print("="*70)

except ValueError as e:
    if "Firebase credentials" in str(e):
        print("\n[ERROR] Firebase credentials not found in environment")
        print("\nThe GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set.")
        print("This is needed to connect to Firebase Authentication.")
        print("\nOptions:")
        print("1. Get credentials from Azure Container App secret 'firebase-creds'")
        print("2. Add credentials to .env file as GOOGLE_APPLICATION_CREDENTIALS_JSON")
        sys.exit(1)
    else:
        raise

except Exception as e:
    print(f"\n[ERROR] Failed to list Firebase users: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
