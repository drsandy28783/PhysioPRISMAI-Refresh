"""
Clear AI Cache Script
Removes all cached AI responses to ensure fresh responses with proper patient context isolation.
Run this after fixing the AI context bleed bug to remove any corrupted cached responses.
"""

import sys
import os
from dotenv import load_dotenv
from azure_cosmos_db import get_cosmos_db
from ai_cache import AICache
import logging

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_all_cache():
    """Clear all AI cache entries from Cosmos DB."""
    try:
        # Get database connection
        db = get_cosmos_db()

        logger.info("Connecting to Azure Cosmos DB...")

        # Initialize AI cache
        cache = AICache(db)

        logger.info("Fetching all cache entries...")

        # Get all cache entries
        cache_collection = db.collection(cache.cache_collection)
        all_cache_docs = list(cache_collection.stream())

        total_entries = len(all_cache_docs)

        if total_entries == 0:
            logger.info("✅ No cache entries found. Cache is already empty.")
            return

        logger.info(f"Found {total_entries} cache entries to delete...")

        # Delete in batches (Cosmos DB batch limit is 500 operations)
        deleted_count = 0
        batch = db.batch()
        batch_count = 0

        for doc in all_cache_docs:
            # Get document reference from the collection
            doc_ref = cache_collection.document(doc.id)
            batch.delete(doc_ref)
            batch_count += 1
            deleted_count += 1

            # Commit batch every 500 operations
            if batch_count >= 500:
                batch.commit()
                logger.info(f"  Deleted {deleted_count}/{total_entries} entries...")
                batch = db.batch()
                batch_count = 0

        # Commit remaining deletions
        if batch_count > 0:
            batch.commit()

        logger.info(f"✅ Successfully deleted {deleted_count} cache entries!")
        logger.info("All AI responses will now be freshly generated with proper patient context.")

        # Optionally clear training data (uncomment if needed)
        # clear_training_data(db, cache)

    except Exception as e:
        logger.error(f"❌ Error clearing cache: {e}", exc_info=True)
        sys.exit(1)


def clear_training_data(db, cache):
    """Optional: Clear training data entries as well."""
    try:
        logger.info("\nClearing training data entries...")

        training_collection = db.collection(cache.training_data_collection)
        training_docs = list(training_collection.stream())

        if not training_docs:
            logger.info("✅ No training data entries found.")
            return

        logger.info(f"Found {len(training_docs)} training data entries to delete...")

        deleted_count = 0
        batch = db.batch()
        batch_count = 0

        for doc in training_docs:
            doc_ref = training_collection.document(doc.id)
            batch.delete(doc_ref)
            batch_count += 1
            deleted_count += 1

            if batch_count >= 500:
                batch.commit()
                logger.info(f"  Deleted {deleted_count}/{len(training_docs)} training entries...")
                batch = db.batch()
                batch_count = 0

        if batch_count > 0:
            batch.commit()

        logger.info(f"✅ Successfully deleted {deleted_count} training data entries!")

    except Exception as e:
        logger.error(f"⚠️ Warning: Could not clear training data: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("AI CACHE CLEARING UTILITY")
    print("=" * 60)
    print("\nThis will delete all cached AI responses.")
    print("After clearing, all AI suggestions will be freshly generated.")
    print("\nThis is necessary after fixing the AI context bleed bug to ensure")
    print("no patient receives AI responses that reference another patient's data.")
    print("=" * 60)

    # Check for --force flag
    force = len(sys.argv) > 1 and sys.argv[1] == '--force'

    if not force:
        # Confirm before proceeding
        response = input("\nAre you sure you want to clear the AI cache? (yes/no): ").strip().lower()
        if response != 'yes':
            print("\n❌ Operation cancelled. Cache was not cleared.")
            sys.exit(0)

    print("\nClearing AI cache...\n")
    clear_all_cache()
    print("\n" + "=" * 60)
    print("✅ CACHE CLEARED SUCCESSFULLY")
    print("=" * 60)
