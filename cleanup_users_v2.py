#!/usr/bin/env python3
"""
Clean up all users except super admin - Version 2
Properly handles deletion by collecting IDs first
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from azure_cosmos_db import get_cosmos_db

# Initialize Cosmos DB
db = get_cosmos_db()

# Super admin to keep (DO NOT DELETE)
KEEP_USER = 'drsandeep@physiologicprism.com'

def list_all_users():
    """List all unique users in the system"""
    print("\n" + "="*70)
    print("CURRENT USERS IN SYSTEM")
    print("="*70)

    users = db.collection('users').stream()
    user_emails = set()

    for user_doc in users:
        user_emails.add(user_doc.id)

    print(f"Total unique users: {len(user_emails)}\n")

    for email in sorted(user_emails):
        # Get user data
        user_doc = db.collection('users').document(email).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            name = user_data.get('name', 'N/A')
            is_super_admin = user_data.get('is_super_admin', 0)
            is_admin = user_data.get('is_admin', 0)
            approved = user_data.get('approved', 0)

            status = []
            if is_super_admin == 1:
                status.append('SUPER_ADMIN')
            elif is_admin == 1:
                status.append('ADMIN')
            if approved == 1:
                status.append('APPROVED')
            else:
                status.append('PENDING')

            status_str = ' | '.join(status)

            if email == KEEP_USER:
                print(f"  [KEEP] {email}")
                print(f"         Name: {name}, Status: {status_str}")
            else:
                print(f"  [DELETE] {email}")
                print(f"           Name: {name}, Status: {status_str}")

    print("="*70)
    return user_emails

def delete_users(user_emails, dry_run=True):
    """Delete users by email"""
    deleted_count = 0
    kept_count = 0

    for email in sorted(user_emails):
        if email == KEEP_USER:
            kept_count += 1
            print(f"  [KEEP] {email} (Super Admin)")
            continue

        if dry_run:
            print(f"  [WILL DELETE] {email}")
            deleted_count += 1
        else:
            try:
                db.collection('users').document(email).delete()
                print(f"  [DELETED] {email}")
                deleted_count += 1
            except Exception as e:
                print(f"  [ERROR] Failed to delete {email}: {e}")

    return deleted_count, kept_count

def main():
    # Check for auto-confirm flag
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv

    print("\n" + "="*70)
    print("USER CLEANUP SCRIPT v2")
    print("="*70)
    print(f"This script will DELETE all users except: {KEEP_USER}")
    print("="*70)

    # List all users
    user_emails = list_all_users()

    if not user_emails:
        print("\nNo users found. Exiting.")
        return

    users_to_delete = [email for email in user_emails if email != KEEP_USER]

    if not users_to_delete:
        print(f"\nOnly super admin exists. Nothing to delete.")
        return

    print(f"\nFound {len(users_to_delete)} user(s) to delete")
    print(f"Will keep: {KEEP_USER}")

    # Dry run
    print("\n" + "="*70)
    print("DRY RUN - What will be deleted:")
    print("="*70)
    deleted_count, kept_count = delete_users(user_emails, dry_run=True)

    print("\n" + "="*70)
    print(f"Summary: Will delete {deleted_count} users, keep {kept_count} user")
    print("="*70)

    # Confirm deletion
    print("\n[WARNING] This action cannot be undone!")

    if auto_confirm:
        print("\n[AUTO-CONFIRMED] Proceeding with deletion (--yes flag used)")
        response = 'DELETE ALL'
    else:
        try:
            response = input("\nType 'DELETE ALL' to confirm deletion: ")
        except EOFError:
            print("\n[ERROR] Cannot get confirmation in non-interactive mode.")
            print("Use --yes flag to auto-confirm: python cleanup_users_v2.py --yes")
            return

    if response != 'DELETE ALL':
        print("\n[CANCELLED] Deletion cancelled. No changes made.")
        return

    # Actual deletion
    print("\n" + "="*70)
    print("DELETING USERS...")
    print("="*70)
    deleted_count, kept_count = delete_users(user_emails, dry_run=False)

    print("\n" + "="*70)
    print("[SUCCESS] CLEANUP COMPLETE")
    print(f"   Deleted: {deleted_count} users")
    print(f"   Kept: {kept_count} user (super admin)")
    print("="*70)

    # Verify final state
    print("\nVerifying final state...")
    import time
    time.sleep(2)  # Wait for Cosmos DB to propagate changes

    final_emails = list_all_users()

    if len(final_emails) == 1 and KEEP_USER in final_emails:
        print("\n[SUCCESS] Only super admin remains. Cleanup verified!")
    else:
        print(f"\n[WARNING] Expected 1 user, found {len(final_emails)} users.")
        print("This might be a Cosmos DB propagation delay. Check again in a moment.")

if __name__ == '__main__':
    main()
