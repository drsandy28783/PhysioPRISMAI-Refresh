"""
Check Blog Posts in Cosmos DB
This script checks what blog posts exist in the database.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from azure_cosmos_db import get_cosmos_db

# Load environment variables
load_dotenv()

def check_blog_posts():
    """Check existing blog posts in the database"""

    try:
        db = get_cosmos_db()

        print("Checking blog_posts collection...")

        # Get all blog posts
        all_posts_query = db.collection('blog_posts').limit(100)
        all_posts = list(all_posts_query.stream())

        print(f"\nTotal blog posts: {len(all_posts)}")

        # Get published posts
        published_posts_query = db.collection('blog_posts').where('status', '==', 'published').limit(100)
        published_posts = list(published_posts_query.stream())

        print(f"Published blog posts: {len(published_posts)}")

        if len(all_posts) > 0:
            print("\nBlog posts found:")
            print("-" * 80)
            for post_doc in all_posts:
                post = post_doc.to_dict()
                print(f"\nID: {post_doc.id}")
                print(f"Title: {post.get('title', 'N/A')}")
                print(f"Slug: {post.get('slug', 'N/A')}")
                print(f"Author: {post.get('author', 'N/A')}")
                print(f"Status: {post.get('status', 'N/A')}")
                print(f"Published: {post.get('published_at', 'N/A')}")
                print(f"Views: {post.get('views', 0)}")
        else:
            print("\nNo blog posts found in database!")
            print("Run 'python seed_blog_posts.py' to add initial blog posts.")

    except Exception as e:
        print(f"\n[ERROR] Error checking blog posts: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 80)
    print("BLOG POSTS CHECK")
    print("=" * 80)
    check_blog_posts()
