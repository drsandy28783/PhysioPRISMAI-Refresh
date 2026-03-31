"""
Update Blog Post Authors in Database
This script updates all blog posts to change the author from
"Dr. Sandeep Rao" to "Dr Roopa Rao"
"""

import os
from dotenv import load_dotenv
from azure_cosmos_db import get_cosmos_db

# Load environment variables
load_dotenv()

def update_blog_authors():
    """Update blog post authors from Dr. Sandeep Rao to Dr Roopa Rao"""

    try:
        db = get_cosmos_db()
        blog_collection = db.collection('blog_posts')

        # Get all blog posts
        print("Fetching all blog posts...")
        all_posts_query = blog_collection.stream()
        posts = list(all_posts_query)

        print(f"Found {len(posts)} total blog posts\n")

        updated_count = 0
        unchanged_count = 0
        old_authors = set()

        for post in posts:
            post_data = post.to_dict()
            post_id = post.id
            title = post_data.get('title', 'Unknown')
            current_author = post_data.get('author', 'Unknown')

            old_authors.add(current_author)

            # Check if author needs to be updated (any variation of Sandeep)
            if 'sandeep' in current_author.lower():
                # Update the author
                post_data['author'] = 'Dr Roopa Rao'
                blog_collection.document(post_id).set(post_data)
                print(f"[OK] UPDATED: {title}")
                print(f"     Changed: '{current_author}' -> 'Dr Roopa Rao'")
                updated_count += 1
            else:
                print(f"  OK (no change needed): {title} (author: {current_author})")
                unchanged_count += 1

        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Updated: {updated_count} posts")
        print(f"  Unchanged: {unchanged_count} posts")
        print(f"  Total: {len(posts)} posts")
        print(f"\n  Old author names found: {old_authors}")
        print(f"{'='*60}")

        if updated_count > 0:
            print(f"\n[SUCCESS] Updated {updated_count} blog post(s) author to 'Dr Roopa Rao'!")
        else:
            print("\n[SUCCESS] All blog posts already have the correct author name!")

    except Exception as e:
        print(f"\n[ERROR] Error updating blog post authors: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("="*60)
    print("UPDATE BLOG POST AUTHORS")
    print("="*60)
    print()
    update_blog_authors()
