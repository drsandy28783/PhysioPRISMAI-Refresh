"""
List ALL users in Cosmos DB to find the actual user
"""

import os
import sys
import json
from azure.cosmos import CosmosClient

# Configuration
COSMOS_ENDPOINT = os.environ.get('COSMOS_DB_ENDPOINT', 'https://physiologicprism-cosmosdb.documents.azure.com:443/')
COSMOS_KEY = os.environ.get('COSMOS_DB_KEY')
DATABASE_NAME = os.environ.get('COSMOS_DB_DATABASE_NAME', 'physiologicprism')

if not COSMOS_KEY:
    print("❌ Error: COSMOS_DB_KEY environment variable not set")
    sys.exit(1)

try:
    # Initialize Cosmos DB client
    client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
    database = client.get_database_client(DATABASE_NAME)
    users_container = database.get_container_client('users')

    print("🔍 Listing ALL users in Cosmos DB...\n")

    # Query all users
    query = "SELECT * FROM c"
    users = list(users_container.query_items(query=query, enable_cross_partition_query=True))

    if not users:
        print("❌ No users found in Cosmos DB!")
        print("\nThe users container is empty.")
    else:
        print(f"✅ Found {len(users)} user(s) in Cosmos DB:\n")
        print("=" * 80)

        for i, user in enumerate(users, 1):
            print(f"\n👤 User #{i}:")
            print(f"  ID: {user.get('id')}")
            print(f"  Email: {user.get('email')}")
            print(f"  Name: {user.get('name')}")
            print(f"  Email Verified: {user.get('email_verified')}")
            print(f"  Approved: {user.get('approved')}")
            print(f"  Active: {user.get('active')}")
            print(f"  Is Super Admin: {user.get('is_super_admin')}")
            print(f"  Is Admin: {user.get('is_admin')}")
            print(f"  Created: {user.get('created_at', 'N/A')}")
            print("-" * 80)

        print(f"\n📋 Full JSON for first user:")
        print(json.dumps(users[0], indent=2, default=str))

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
