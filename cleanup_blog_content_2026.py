"""
Blog Content Cleanup Script for 2026
======================================
This script performs the following operations:
1. Deletes the stub article "Clinical Reasoning Framework for Physiotherapists"
2. Updates "2025" to "2026" in three articles (titles, meta descriptions, H1s)
3. Fixes SMART Goals title brand violation (removes "Revolutionizing")
4. Adds internal cross-links between related articles

Run this script to update the blog content for 2026.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from azure_cosmos_db import get_cosmos_db

# Load environment variables
load_dotenv()

# Article slugs for easy reference
STUB_SLUG = 'clinical-reasoning-framework'
CLINICAL_REASONING_SLUG = 'clinical-reasoning-physiotherapy-complete-2025-guide'
HISTORY_TAKING_SLUG = 'history-taking-physiotherapy-complete-guide-2025'
OBJECTIVE_ASSESSMENT_SLUG = 'objective-assessment-framework-physiotherapy-complete-guide'
SMART_GOALS_SLUG = 'ai-powered-smart-goals-physiotherapy'

def get_post_by_slug(db, slug):
    """Fetch a blog post by its slug"""
    blog_collection = db.collection('blog_posts')
    posts = list(blog_collection.where('slug', '==', slug).limit(1).stream())
    if posts:
        post = posts[0]
        return post.id, post.to_dict()
    return None, None

def update_post(db, post_id, updated_data):
    """Update a blog post in the database"""
    blog_collection = db.collection('blog_posts')
    updated_data['updated_at'] = datetime.now().isoformat()
    blog_collection.document(post_id).set(updated_data)

def delete_post(db, post_id):
    """Delete a blog post from the database"""
    blog_collection = db.collection('blog_posts')
    blog_collection.document(post_id).delete()

def main():
    try:
        db = get_cosmos_db()

        print("\n" + "=" * 80)
        print("BLOG CONTENT CLEANUP FOR 2026")
        print("=" * 80)

        changes_made = []

        # ============================================================
        # TASK 1: Delete stub article
        # ============================================================
        print("\n[1/4] Deleting stub article...")
        post_id, post_data = get_post_by_slug(db, STUB_SLUG)

        if post_id:
            title = post_data.get('title', 'Unknown')
            content_length = len(post_data.get('content', ''))
            print(f"   Found: {title}")
            print(f"   Slug: {STUB_SLUG}")
            print(f"   Content length: {content_length} chars")

            delete_post(db, post_id)
            print(f"   [OK] DELETED stub article")
            changes_made.append(f"DELETED stub article: {title}")
        else:
            print(f"   [WARNING] Stub article not found (may have been already deleted)")

        # ============================================================
        # TASK 2: Update 2025 -> 2026 in three articles
        # ============================================================
        print("\n[2/4] Updating 2025 -> 2026 references...")

        articles_to_update = [
            (CLINICAL_REASONING_SLUG, "Clinical Reasoning"),
            (HISTORY_TAKING_SLUG, "History Taking"),
            (OBJECTIVE_ASSESSMENT_SLUG, "Objective Assessment")
        ]

        for slug, article_name in articles_to_update:
            post_id, post_data = get_post_by_slug(db, slug)

            if post_id:
                print(f"\n   Processing: {article_name}")
                updated = False

                # Update title
                if '2025' in post_data.get('title', ''):
                    old_title = post_data['title']
                    post_data['title'] = post_data['title'].replace('2025', '2026')
                    print(f"   - Title: '{old_title}' -> '{post_data['title']}'")
                    updated = True

                # Update meta description
                if '2025' in post_data.get('meta_description', ''):
                    post_data['meta_description'] = post_data['meta_description'].replace('2025', '2026')
                    print(f"   - Meta description updated")
                    updated = True

                # Update H1s and content (first H1 should match title)
                if '2025' in post_data.get('content', ''):
                    post_data['content'] = post_data['content'].replace('2025', '2026')
                    print(f"   - Content H1s and references updated")
                    updated = True

                if updated:
                    update_post(db, post_id, post_data)
                    print(f"   [OK] UPDATED {article_name}")
                    changes_made.append(f"UPDATED {article_name}: 2025 -> 2026")
                else:
                    print(f"   [INFO] No 2025 references found")
            else:
                print(f"   [WARNING] {article_name} not found")

        # ============================================================
        # TASK 3: Fix SMART Goals title brand violation
        # ============================================================
        print("\n[3/4] Fixing SMART Goals title brand violation...")
        post_id, post_data = get_post_by_slug(db, SMART_GOALS_SLUG)

        if post_id:
            old_title = post_data.get('title', '')
            print(f"   Old title: {old_title}")

            # Update title
            new_title = "AI-Powered SMART Goal Setting: Evidence-Based Goal Planning for Physiotherapists"
            post_data['title'] = new_title

            # Update H1 in content (first line should be the title as H1)
            content = post_data.get('content', '')
            if old_title in content:
                post_data['content'] = content.replace(old_title, new_title, 1)  # Replace first occurrence only

            # Update meta description if it contains "Revolutionizing"
            if 'revolutionizing' in post_data.get('meta_description', '').lower():
                post_data['meta_description'] = post_data['meta_description'].replace(
                    'revolutionizing', 'transforming'
                ).replace('Revolutionizing', 'Transforming')

            update_post(db, post_id, post_data)
            print(f"   New title: {new_title}")
            print(f"   [OK] UPDATED SMART Goals title (removed 'Revolutionizing')")
            changes_made.append(f"FIXED SMART Goals title: removed 'Revolutionizing'")
        else:
            print(f"   [WARNING] SMART Goals article not found")

        # ============================================================
        # TASK 4: Add internal cross-links between related articles
        # ============================================================
        print("\n[4/4] Adding internal cross-links between related articles...")

        # Get all three articles
        cr_id, cr_data = get_post_by_slug(db, CLINICAL_REASONING_SLUG)
        ht_id, ht_data = get_post_by_slug(db, HISTORY_TAKING_SLUG)
        oa_id, oa_data = get_post_by_slug(db, OBJECTIVE_ASSESSMENT_SLUG)

        links_added = 0

        # Define the links to add
        clinical_reasoning_url = f'/blog/post/{CLINICAL_REASONING_SLUG}'
        history_taking_url = f'/blog/post/{HISTORY_TAKING_SLUG}'
        objective_assessment_url = f'/blog/post/{OBJECTIVE_ASSESSMENT_SLUG}'

        # Add links to Clinical Reasoning article
        if cr_id and cr_data:
            content = cr_data.get('content', '')

            # Check if links already exist
            has_ht_link = HISTORY_TAKING_SLUG in content
            has_oa_link = OBJECTIVE_ASSESSMENT_SLUG in content

            if not has_ht_link or not has_oa_link:
                # Find a good place to add links (look for "Subjective Assessment" section)
                if '## Key Components' in content and '### 1. Subjective Assessment' in content:
                    # Add link after Subjective Assessment description
                    old_text = "The subjective examination provides crucial insights into the patient's perspective, including their chief complaint, history, and functional limitations."
                    new_text = "The subjective examination provides crucial insights into the patient's perspective, including their chief complaint, history, and functional limitations. For a comprehensive guide, see our detailed article on [history taking in physiotherapy](" + history_taking_url + ")."

                    if old_text in content:
                        content = content.replace(old_text, new_text)

                # Add link for Objective Assessment
                if '### 2. Objective Assessment' in content:
                    old_text = "Physical examination findings, measurements, and functional tests provide objective data to support clinical hypotheses."
                    new_text = "Physical examination findings, measurements, and functional tests provide objective data to support clinical hypotheses. Learn more in our complete [objective assessment framework](" + objective_assessment_url + ")."

                    if old_text in content:
                        content = content.replace(old_text, new_text)

                cr_data['content'] = content
                update_post(db, cr_id, cr_data)
                print(f"   [OK] Added cross-links to Clinical Reasoning article")
                links_added += 1
            else:
                print(f"   [INFO] Clinical Reasoning article already has cross-links")

        # Add links to History Taking article
        if ht_id and ht_data:
            content = ht_data.get('content', '')

            # Check if links already exist
            has_cr_link = CLINICAL_REASONING_SLUG in content
            has_oa_link = OBJECTIVE_ASSESSMENT_SLUG in content

            if not has_cr_link or not has_oa_link:
                # Add link to clinical reasoning in introduction
                if '## Why History Taking Matters' in content:
                    old_text = "The subjective examination often provides 80% of the information needed for diagnosis."
                    new_text = "The subjective examination often provides 80% of the information needed for diagnosis. It forms a critical component of the [clinical reasoning process](" + clinical_reasoning_url + ")."

                    if old_text in content:
                        content = content.replace(old_text, new_text)

                # Add link to objective assessment
                if '## Conclusion' in content or '## Documentation Best Practices' in content:
                    # Add before conclusion
                    insertion_point = content.rfind('## Conclusion')
                    if insertion_point == -1:
                        insertion_point = content.rfind('## Documentation Best Practices')

                    if insertion_point > 0:
                        new_section = "\n\n## Integration with Clinical Assessment\n\nA thorough patient history naturally leads to a focused physical examination. After completing your subjective assessment, proceed to [objective assessment](" + objective_assessment_url + ") to gather measurable data that confirms or refutes your clinical hypotheses. Together, these assessment components form the foundation of effective [clinical reasoning](" + clinical_reasoning_url + ").\n\n"
                        content = content[:insertion_point] + new_section + content[insertion_point:]

                ht_data['content'] = content
                update_post(db, ht_id, ht_data)
                print(f"   [OK] Added cross-links to History Taking article")
                links_added += 1
            else:
                print(f"   [INFO] History Taking article already has cross-links")

        # Add links to Objective Assessment article
        if oa_id and oa_data:
            content = oa_data.get('content', '')

            # Check if links already exist
            has_cr_link = CLINICAL_REASONING_SLUG in content
            has_ht_link = HISTORY_TAKING_SLUG in content

            if not has_cr_link or not has_ht_link:
                # Add link to history taking in introduction
                if '## Components of Objective Assessment' in content:
                    # Add before first section
                    old_text = "The objective examination provides measurable, reproducible data to support clinical decision-making and track patient progress."
                    new_text = "The objective examination provides measurable, reproducible data to support clinical decision-making and track patient progress. It builds upon the information gathered during [patient history taking](" + history_taking_url + ") to form a complete clinical picture."

                    if old_text in content:
                        content = content.replace(old_text, new_text)

                # Add link to clinical reasoning
                if '## Clinical Integration' in content:
                    old_text = "Objective findings should be:"
                    new_text = "As part of the [clinical reasoning process](" + clinical_reasoning_url + "), objective findings should be:"

                    if old_text in content:
                        content = content.replace(old_text, new_text)

                oa_data['content'] = content
                update_post(db, oa_id, oa_data)
                print(f"   [OK] Added cross-links to Objective Assessment article")
                links_added += 1
            else:
                print(f"   [INFO] Objective Assessment article already has cross-links")

        if links_added > 0:
            changes_made.append(f"ADDED internal cross-links to {links_added} article(s)")

        # ============================================================
        # Summary
        # ============================================================
        print("\n" + "=" * 80)
        print("SUMMARY OF CHANGES")
        print("=" * 80)

        if changes_made:
            for i, change in enumerate(changes_made, 1):
                print(f"{i}. {change}")
            print(f"\n[SUCCESS] Successfully completed {len(changes_made)} operation(s)")
        else:
            print("[INFO] No changes were needed (all updates may have been applied previously)")

        print("\n" + "=" * 80)
        print("NEXT STEP: Update main.py to add 301 redirect")
        print("=" * 80)
        print(f"\nAdd this redirect in main.py:")
        print(f"FROM: /blog/post/{STUB_SLUG}")
        print(f"TO:   /blog/post/{CLINICAL_REASONING_SLUG}")
        print()

    except Exception as e:
        print(f"\n[ERROR] Failed to update blog content: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
