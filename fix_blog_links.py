"""Script to check and fix blog post links"""
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

    # Create a mapping of titles to post IDs and slugs
    post_map = {}
    for post in posts:
        post_data = post.to_dict()
        title = post_data.get('title', '')
        post_id = post.id
        slug = post_data.get('slug', '')

        post_map[title] = {
            'id': post_id,
            'slug': slug,
            'title': title
        }

        print(f"Title: {title}")
        print(f"  ID: {post_id}")
        print(f"  Slug: {slug}")
        print()

    print("\n" + "=" * 80)
    print("CHECKING FOR BROKEN LINKS")
    print("=" * 80)

    # Now check for links in blog posts
    for post in posts:
        post_data = post.to_dict()
        title = post_data.get('title', '')
        content = post_data.get('content', '')

        # Look for links to /blog/ pages
        if '/blog/' in content:
            print(f"\n{title}:")
            # Find all blog links
            import re
            links = re.findall(r'href="(/blog/[^"]+)"', content)
            for link in links:
                print(f"  - {link}")
                # Check if this link exists
                if '/blog/post/' in link:
                    # Slug-based link
                    slug = link.replace('/blog/post/', '')
                    found = False
                    for p_title, p_data in post_map.items():
                        if p_data['slug'] == slug:
                            found = True
                            print(f"    [OK] Valid (points to: {p_title})")
                            break
                    if not found:
                        print(f"    [X] BROKEN - slug '{slug}' not found")
                else:
                    # ID-based link
                    post_id = link.replace('/blog/', '')
                    found = False
                    for p_title, p_data in post_map.items():
                        if p_data['id'] == post_id:
                            found = True
                            print(f"    [OK] Valid (points to: {p_title})")
                            break
                    if not found:
                        print(f"    [X] BROKEN - post ID '{post_id}' not found")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
