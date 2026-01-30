#!/usr/bin/env python3
"""
Clean up Firebase Auth users - keep only super admin
Keeps: drsandeep@physiologicprism.com
Deletes: All other users
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# IMPORTANT: Load .env BEFORE importing app_auth
from dotenv import load_dotenv
load_dotenv()

import app_auth
from firebase_admin import auth

# Super admin to keep (DO NOT DELETE)
KEEP_USER = 'drsandeep@physiologicprism.com'

def list_all_firebase_users():
    """List all users in Firebase Auth"""
    print("\n" + "="*70)
    print("FIREBASE AUTH USERS")
    print("="*70)

    page = auth.list_users()

    users = []
    while page:
        for user in page.users:
            users.append({
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name
            })

        # Get next page
        page = page.get_next_page() if page.has_next_page else None

    if not users:
        print("No users found in Firebase Auth")
        return []

    print(f"Total users: {len(users)}\n")

    for user in users:
        if user['email'] == KEEP_USER:
            print(f"  [KEEP] {user['email']} (Super Admin)")
            print(f"         UID: {user['uid']}, Name: {user['display_name']}")
        else:
            print(f"  [DELETE] {user['email']}")
            print(f"           UID: {user['uid']}, Name: {user['display_name']}")

    print("="*70)
    return users


def delete_firebase_users(users, dry_run=True):
    """Delete Firebase Auth users by UID"""
    deleted_count = 0
    kept_count = 0

    for user in users:
        email = user['email']
        uid = user['uid']

        if email == KEEP_USER:
            kept_count += 1
            print(f"  [KEEP] {email} (Super Admin)")
            continue

        if dry_run:
            print(f"  [WILL DELETE] {email} (UID: {uid})")
            deleted_count += 1
        else:
            try:
                auth.delete_user(uid)
                print(f"  [DELETED] {email} (UID: {uid})")
                deleted_count += 1
            except Exception as e:
                print(f"  [ERROR] Failed to delete {email}: {e}")

    return deleted_count, kept_count


def main():
    # Check for auto-confirm flag
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv

    print("\n" + "="*70)
    print("FIREBASE AUTH USER CLEANUP SCRIPT")
    print("="*70)
    print(f"This script will DELETE all users except: {KEEP_USER}")
    print("="*70)

    # List all users
    users = list_all_firebase_users()

    if not users:
        print("\nNo users found. Exiting.")
        return

    users_to_delete = [u for u in users if u['email'] != KEEP_USER]

    if not users_to_delete:
        print(f"\nOnly super admin exists. Nothing to delete.")
        return

    print(f"\nFound {len(users_to_delete)} user(s) to delete")
    print(f"Will keep: {KEEP_USER}")

    # Dry run
    print("\n" + "="*70)
    print("DRY RUN - What will be deleted:")
    print("="*70)
    deleted_count, kept_count = delete_firebase_users(users, dry_run=True)

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
            print("Use --yes flag to auto-confirm: python cleanup_firebase_users.py --yes")
            return

    if response != 'DELETE ALL':
        print("\n[CANCELLED] Deletion cancelled. No changes made.")
        return

    # Actual deletion
    print("\n" + "="*70)
    print("DELETING FIREBASE AUTH USERS...")
    print("="*70)
    deleted_count, kept_count = delete_firebase_users(users, dry_run=False)

    print("\n" + "="*70)
    print("[SUCCESS] FIREBASE AUTH CLEANUP COMPLETE")
    print(f"   Deleted: {deleted_count} users")
    print(f"   Kept: {kept_count} user (super admin)")
    print("="*70)

    # Verify final state
    print("\nVerifying final state...")
    import time
    time.sleep(2)  # Wait for Firebase to propagate changes

    final_users = list_all_firebase_users()

    if len(final_users) == 1 and any(u['email'] == KEEP_USER for u in final_users):
        print("\n[SUCCESS] Only super admin remains in Firebase Auth. Cleanup verified!")
    else:
        print(f"\n[WARNING] Expected 1 user, found {len(final_users)} users.")
        print("This might be a Firebase propagation delay. Check again in a moment.")


if __name__ == '__main__':
    main()
