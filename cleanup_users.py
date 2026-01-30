#!/usr/bin/env python3
"""
Clean up all users except super admin
Keeps: drsandeep@physiologicprism.com
Deletes: All other users
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
    """List all users in the system"""
    print("\n" + "="*70)
    print("CURRENT USERS IN SYSTEM")
    print("="*70)

    users = db.collection('users').stream()
    user_list = []

    for user_doc in users:
        user_data = user_doc.to_dict()
        email = user_doc.id
        user_list.append({
            'email': email,
            'name': user_data.get('name', 'N/A'),
            'role': user_data.get('role', 'N/A'),
            'is_super_admin': user_data.get('is_super_admin', 0),
            'is_admin': user_data.get('is_admin', 0),
            'approved': user_data.get('approved', 0)
        })

    if not user_list:
        print("No users found in system")
        return []

    # Print summary
    for user in user_list:
        status = []
        if user['is_super_admin'] == 1:
            status.append('SUPER_ADMIN')
        elif user['is_admin'] == 1:
            status.append('ADMIN')
        if user['approved'] == 1:
            status.append('APPROVED')
        else:
            status.append('PENDING')

        status_str = ' | '.join(status)

        if user['email'] == KEEP_USER:
            print(f"  [KEEP] {user['email']}")
            print(f"         Name: {user['name']}, Role: {user['role']}, Status: {status_str}")
        else:
            print(f"  [DELETE] {user['email']}")
            print(f"           Name: {user['name']}, Role: {user['role']}, Status: {status_str}")

    print("="*70)
    return user_list


def delete_users(dry_run=True):
    """Delete all users except super admin"""
    users = db.collection('users').stream()

    deleted_count = 0
    kept_count = 0

    for user_doc in users:
        email = user_doc.id

        if email == KEEP_USER:
            kept_count += 1
            print(f"  [KEEP] {email} (Super Admin)")
            continue

        if dry_run:
            print(f"  [DELETE] Would delete: {email}")
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
    print("USER CLEANUP SCRIPT")
    print("="*70)
    print(f"This script will DELETE all users except: {KEEP_USER}")
    print("="*70)

    # List all users
    user_list = list_all_users()

    if not user_list:
        print("\nNo users to delete. Exiting.")
        return

    users_to_delete = [u for u in user_list if u['email'] != KEEP_USER]

    if not users_to_delete:
        print(f"\nOnly super admin exists. Nothing to delete.")
        return

    print(f"\nFound {len(users_to_delete)} user(s) to delete")
    print(f"Will keep: {KEEP_USER}")

    # Dry run first
    print("\n" + "="*70)
    print("DRY RUN - Showing what would be deleted")
    print("="*70)
    deleted_count, kept_count = delete_users(dry_run=True)

    print("\n" + "="*70)
    print(f"Summary: Would delete {deleted_count} users, keep {kept_count} user")
    print("="*70)

    # Confirm deletion
    print("\n[WARNING] This action cannot be undone!")

    if auto_confirm:
        print("\n[AUTO-CONFIRMED] Proceeding with deletion (--yes flag used)")
        response = 'DELETE ALL'
    else:
        response = input("\nType 'DELETE ALL' to confirm deletion: ")

    if response != 'DELETE ALL':
        print("\n[CANCELLED] Deletion cancelled. No changes made.")
        return

    # Actual deletion
    print("\n" + "="*70)
    print("DELETING USERS...")
    print("="*70)
    deleted_count, kept_count = delete_users(dry_run=False)

    print("\n" + "="*70)
    print("[SUCCESS] CLEANUP COMPLETE")
    print(f"   Deleted: {deleted_count} users")
    print(f"   Kept: {kept_count} user (super admin)")
    print("="*70)

    # Show remaining users
    print("\nVerifying remaining users...")
    list_all_users()


if __name__ == '__main__':
    main()
