#!/usr/bin/env python3
"""
Script to check if user document exists in Cosmos DB and verify its structure.
"""
import os
from azure_cosmos_db import get_cosmos_db

# Initialize Cosmos DB
db = get_cosmos_db()

# Email to check
email = "drsandeep@physiologicprism.com"

print(f"Checking user document for: {email}")
print("=" * 60)

try:
    # Try to get the user document
    user_doc = db.collection('users').document(email).get()

    if user_doc.exists:
        user_data = user_doc.to_dict()
        print("✓ User document EXISTS")
        print("\nDocument structure:")
        print("-" * 60)

        # Print important fields
        important_fields = [
            'email',
            'name',
            'password_hash',
            'firebase_uid',
            'approved',
            'active',
            'email_verified',
            'role',
            'is_admin',
            'is_super_admin',
            'tos_version'
        ]

        for field in important_fields:
            value = user_data.get(field, 'NOT SET')
            if field == 'password_hash':
                # Don't print full hash, just show if it exists
                value = 'EXISTS' if value and value != 'NOT SET' else 'NOT SET'
            print(f"  {field}: {value}")

        print("\nAll fields in document:")
        print("-" * 60)
        for key in sorted(user_data.keys()):
            if key == 'password_hash':
                print(f"  {key}: [REDACTED]")
            else:
                print(f"  {key}: {user_data[key]}")

    else:
        print("✗ User document DOES NOT EXIST")
        print(f"\nTrying to find documents with similar email...")

        # Try to query for similar emails
        users = db.collection('users').where('email', '==', email).limit(5).stream()
        found = False
        for doc in users:
            found = True
            print(f"  Found: {doc.id}")

        if not found:
            print("  No documents found with query either")

        print("\nListing first 10 user documents in collection:")
        all_users = db.collection('users').limit(10).stream()
        for doc in all_users:
            print(f"  - {doc.id}")

except Exception as e:
    print(f"✗ ERROR: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()

print("=" * 60)
