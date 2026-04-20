"""List all blog posts with detailed information"""
import os
from dotenv import load_dotenv
from azure_cosmos_db import get_cosmos_db

load_dotenv()

try:
    db = get_cosmos_db()
    blog_collection = db.collection('blog_posts')

    # Get all published blog posts
    posts = list(blog_collection.where('status', '==', 'published').stream())

    print(f"\nFound {len(posts)} published blog posts\n")
    print("=" * 100)

    for i, post in enumerate(posts, 1):
        post_data = post.to_dict()
        print(f"\n{i}. TITLE: {post_data.get('title', 'Unknown')}")
        print(f"   SLUG: {post_data.get('slug', 'Unknown')}")
        print(f"   URL: /blog/post/{post_data.get('slug', 'Unknown')}")
        print(f"   AUTHOR: {post_data.get('author', 'Unknown')}")
        print(f"   META: {post_data.get('meta_description', 'None')[:100]}...")
        print(f"   CONTENT LENGTH: {len(post_data.get('content', ''))} chars")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
