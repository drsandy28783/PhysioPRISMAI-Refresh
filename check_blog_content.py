"""Quick script to check blog post content in database"""
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
    print("=" * 80)

    for post in posts:
        post_data = post.to_dict()
        title = post_data.get('title', 'Unknown')
        content = post_data.get('content', '')

        print(f"\nPost: {title}")
        print("-" * 80)

        # Check for old unsubstantiated claims
        if "Real-World Impact" in content or "Real-World Clinical Impact" in content:
            print("[X] STILL HAS OLD CLAIMS")
            # Show a snippet
            if "Real-World Impact" in content:
                idx = content.find("Real-World Impact")
                print(content[idx:idx+500])
        else:
            print("[OK] Updated (no 'Real-World Impact' found)")
            # Check if it has the new section
            if "How This Can Help Your Practice" in content:
                print("[OK] Has new 'How This Can Help Your Practice' section")

        print()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
