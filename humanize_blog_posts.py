"""
Humanize Blog Posts - Remove AI-Generated Formatting
Cleans up markdown symbols, asterisks, and makes content look naturally written
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from azure_cosmos_db import get_cosmos_db
import re

# Load environment variables
load_dotenv()

def clean_markdown_to_html(content):
    """Convert markdown to clean HTML that looks human-written"""

    # Remove excessive asterisks for bold - convert **text** to <strong>text</strong>
    content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', content)

    # Remove single asterisks for italic
    content = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', content)

    # Convert markdown headers to proper HTML headers
    # ### Header → <h3>Header</h3>
    content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
    content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
    content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)

    # Convert markdown lists to HTML lists
    # Find bullet points and convert to proper lists
    lines = content.split('\n')
    in_list = False
    cleaned_lines = []

    for i, line in enumerate(lines):
        # Check if line is a bullet point
        if re.match(r'^\s*[-•]\s+', line):
            if not in_list:
                cleaned_lines.append('<ul>')
                in_list = True
            # Clean the bullet point
            item = re.sub(r'^\s*[-•]\s+', '', line)
            # Remove bold from list items for more natural look
            item = item.replace('**', '')
            cleaned_lines.append(f'<li>{item}</li>')
        else:
            if in_list:
                cleaned_lines.append('</ul>')
                in_list = False
            cleaned_lines.append(line)

    if in_list:
        cleaned_lines.append('</ul>')

    content = '\n'.join(cleaned_lines)

    # Remove markdown links and make them HTML - [text](url) → <a href="url">text</a>
    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', content)

    # Clean up excessive emphasis markers
    content = content.replace('→', '—')  # Replace arrows with em dash
    content = content.replace('✓', '')    # Remove checkmarks (or keep if you like them)
    content = content.replace('✅', '')    # Remove emoji checkmarks
    content = content.replace('❌', '')    # Remove X marks

    # Remove any remaining hashtag-style headers (### without space)
    content = re.sub(r'###\s*', '', content)
    content = re.sub(r'##\s*', '', content)

    # Clean up multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    # Remove horizontal rules
    content = re.sub(r'^---+$', '', content, flags=re.MULTILINE)
    content = re.sub(r'^___+$', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\*\*\*+$', '', content, flags=re.MULTILINE)

    # Fix image tags - ensure they're properly formatted
    content = re.sub(
        r'<img src="([^"]+)" alt="([^"]+)"[^>]*>',
        r'<img src="\1" alt="\2" style="max-width: 100%; height: auto; margin: 20px 0; border: 1px solid #ddd; border-radius: 8px;">',
        content
    )

    # Wrap paragraphs in <p> tags (text between blank lines)
    paragraphs = content.split('\n\n')
    formatted_paragraphs = []

    for para in paragraphs:
        para = para.strip()
        if para and not para.startswith('<') and not para.endswith('>'):
            # Only wrap if it's not already an HTML tag
            formatted_paragraphs.append(f'<p>{para}</p>')
        else:
            formatted_paragraphs.append(para)

    content = '\n\n'.join(formatted_paragraphs)

    # Final cleanup: remove any stray markdown symbols
    content = content.replace('**', '')
    content = content.replace('__', '')

    return content

def humanize_blog_posts():
    """Update all blog posts to look naturally written"""

    try:
        db = get_cosmos_db()
        blog_collection = db.collection('blog_posts')

        # Get all published blog posts
        print("\nFetching all blog posts...")
        query = blog_collection.where('status', '==', 'published').stream()
        posts = list(query)

        print(f"Found {len(posts)} blog posts to humanize\n")

        updated_count = 0

        for post in posts:
            post_data = post.to_dict()
            post_id = post.id
            title = post_data.get('title', 'Unknown')

            print(f"Processing: {title}")

            # Get current content
            current_content = post_data.get('content', '')

            # Clean and humanize the content
            cleaned_content = clean_markdown_to_html(current_content)

            # Update the post
            doc_ref = blog_collection.document(post_id)
            doc_ref.update({
                'content': cleaned_content,
                'updated_at': datetime.now().isoformat()
            })

            updated_count += 1
            print(f"  [OK] Cleaned up markdown and formatting")
            print()

        print(f"\n{'='*60}")
        print(f"SUCCESS: Updated {updated_count} blog posts")
        print(f"{'='*60}")
        print("\nChanges made:")
        print("- Converted ** to <strong> tags")
        print("- Converted ### headers to <h3> tags")
        print("- Converted bullet points to <ul><li> tags")
        print("- Removed excessive symbols (arrows, checkmarks)")
        print("- Cleaned up markdown links to HTML")
        print("- Wrapped paragraphs in <p> tags")
        print("- Removed horizontal rules and extra formatting")
        print("\nBlog posts now look naturally human-written!")

    except Exception as e:
        print(f"\n[ERROR] Error updating blog posts: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 60)
    print("HUMANIZING BLOG POSTS")
    print("Removing AI-generated formatting...")
    print("=" * 60)
    humanize_blog_posts()
