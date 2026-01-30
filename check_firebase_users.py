#!/usr/bin/env python3
"""
Check Firebase Auth users
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import firebase_admin
from firebase_admin import auth

# Initialize Firebase Admin if not already initialized
try:
    firebase_admin.get_app()
    print("Firebase Admin SDK already initialized")
except ValueError:
    # Try to initialize with credentials from env or Azure secret
    sa_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON', '').strip()

    if not sa_json:
        # Try to get from Azure secret
        import subprocess
        try:
            result = subprocess.run([
                'az', 'containerapp', 'secret', 'show',
                '--name', 'physiologicprism-app',
                '--resource-group', 'rg-physiologicprism-prod',
                '--secret-name', 'firebase-creds',
                '--query', 'value',
                '--output', 'tsv'
            ], capture_output=True, text=True, check=True)
            sa_json = result.stdout.strip()
            print("Got Firebase credentials from Azure")
        except Exception as e:
            print(f"ERROR: Could not get Firebase credentials: {e}")
            print("\nTo fix this, set GOOGLE_APPLICATION_CREDENTIALS_JSON in .env")
            print("Or run this script from Azure where the secret is available")
            exit(1)

    if sa_json:
        import json
        from firebase_admin import credentials
        cred_dict = json.loads(sa_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized")
    else:
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS_JSON not found")
        exit(1)

print("\n" + "="*70)
print("FIREBASE AUTH USERS")
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

from azure_cosmos_db import get_cosmos_db
db = get_cosmos_db()

cosmos_users = list(db.collection('users').stream())
cosmos_emails = set(doc.id for doc in cosmos_users)
firebase_emails = set(u['email'] for u in users if u['email'])

print(f"\nCosmos DB users: {len(cosmos_emails)}")
print(f"Firebase Auth users: {len(firebase_emails)}")

# Users in Firebase but not in Cosmos DB
firebase_only = firebase_emails - cosmos_emails
if firebase_only:
    print(f"\n⚠️  Users in Firebase Auth but NOT in Cosmos DB ({len(firebase_only)}):")
    for email in firebase_only:
        print(f"  - {email}")

# Users in Cosmos DB but not in Firebase
cosmos_only = cosmos_emails - firebase_emails
if cosmos_only:
    print(f"\n⚠️  Users in Cosmos DB but NOT in Firebase Auth ({len(cosmos_only)}):")
    for email in cosmos_only:
        print(f"  - {email}")

if not firebase_only and not cosmos_only:
    print("\n✓ All users are in sync between Firebase Auth and Cosmos DB")

print("="*70)
