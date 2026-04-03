"""Script to fix all broken blog links - convert /blog/{slug} to /blog/post/{slug}"""
import os
from dotenv import load_dotenv
from azure_cosmos_db import get_cosmos_db
import re

load_dotenv()

def fix_blog_links(content, slug_map):
    """Fix blog links in content"""
    # Manual mapping of incorrect slugs to correct ones
    slug_corrections = {
        'history-taking-physiotherapy': 'history-taking-physiotherapy-complete-guide-2025',
        'objective-assessment-guide': 'objective-assessment-framework-physiotherapy-complete-guide',
        'evidence-based-treatment-planning': None,  # Doesn't exist yet
        'digital-documentation-best-practices': None,  # Doesn't exist yet
    }

    # Add exact matches
    for slug in slug_map:
        slug_corrections[slug] = slug

    # Find all /blog/ links
    pattern = r'href="(/blog/([a-z0-9-]+))"'

    def replace_link(match):
        full_link = match.group(1)  # e.g., /blog/history-taking-physiotherapy
        slug = match.group(2)  # e.g., history-taking-physiotherapy

        # Skip if it's a UUID (has hex characters in the right pattern)
        if len(slug) == 36 and slug.count('-') == 4:
            return match.group(0)  # This is a UUID, leave it alone

        # Check if it's in our corrections map
        if slug in slug_corrections:
            correct_slug = slug_corrections[slug]
            if correct_slug:
                new_link = f'/blog/post/{correct_slug}'
                print(f"    Fixing: {full_link} -> {new_link}")
                return f'href="{new_link}"'
            else:
                print(f"    WARNING: No target for {full_link} (post doesn't exist)")
                return match.group(0)

        return match.group(0)  # Return original if no match

    new_content = re.sub(pattern, replace_link, content)
    return new_content

try:
    db = get_cosmos_db()
    blog_collection = db.collection('blog_posts')

    # Get all published blog posts
    posts = list(blog_collection.where('status', '==', 'published').stream())

    # Create a mapping of slugs
    slug_map = {}
    for post in posts:
        post_data = post.to_dict()
        slug = post_data.get('slug', '')
        if slug:
            slug_map[slug] = post.id

    print(f"Found {len(posts)} published blog posts")
    print(f"Slug map: {list(slug_map.keys())}")
    print("\n" + "=" * 80)
    print("FIXING BROKEN LINKS")
    print("=" * 80)

    # Now fix links in each post
    for post in posts:
        post_data = post.to_dict()
        title = post_data.get('title', '')
        content = post_data.get('content', '')

        # Check if content has broken links
        if '/blog/' in content:
            print(f"\nChecking: {title}")
            new_content = fix_blog_links(content, slug_map.keys())

            if new_content != content:
                print(f"  Updating post...")
                # Update the post
                blog_collection.document(post.id).update({
                    'content': new_content
                })
                print(f"  [OK] Updated successfully")
            else:
                print(f"  [OK] No changes needed")

    print("\n" + "=" * 80)
    print("DONE!")
    print("=" * 80)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
