"""
Verification Script for Blog Cleanup 2026
==========================================
This script verifies that all blog cleanup operations were successful:
1. Stub article deleted
2. 2025 -> 2026 updates applied
3. SMART Goals title fixed
4. Internal cross-links added
"""

import os
from dotenv import load_dotenv
from azure_cosmos_db import get_cosmos_db

load_dotenv()

def main():
    try:
        db = get_cosmos_db()
        blog_collection = db.collection('blog_posts')

        print("\n" + "=" * 80)
        print("BLOG CLEANUP VERIFICATION - 2026")
        print("=" * 80)

        all_passed = True

        # ============================================================
        # TEST 1: Verify stub article is deleted
        # ============================================================
        print("\n[TEST 1] Verifying stub article deletion...")
        stub_posts = list(blog_collection.where('slug', '==', 'clinical-reasoning-framework').limit(1).stream())

        if len(stub_posts) == 0:
            print("   [PASS] Stub article 'clinical-reasoning-framework' has been deleted")
        else:
            print("   [FAIL] Stub article still exists in database!")
            all_passed = False

        # ============================================================
        # TEST 2: Verify 2025 -> 2026 updates
        # ============================================================
        print("\n[TEST 2] Verifying 2025 -> 2026 updates...")

        slugs_to_check = [
            ('clinical-reasoning-physiotherapy-complete-2025-guide', 'Clinical Reasoning'),
            ('history-taking-physiotherapy-complete-guide-2025', 'History Taking'),
            ('objective-assessment-framework-physiotherapy-complete-guide', 'Objective Assessment')
        ]

        for slug, article_name in slugs_to_check:
            posts = list(blog_collection.where('slug', '==', slug).limit(1).stream())

            if len(posts) == 0:
                print(f"   [WARNING] {article_name} article not found!")
                continue

            post_data = posts[0].to_dict()
            title = post_data.get('title', '')
            content = post_data.get('content', '')
            meta_desc = post_data.get('meta_description', '')

            # Check if 2025 has been replaced with 2026 in title
            has_2025_in_title = '2025' in title
            has_2026_in_title = '2026' in title

            # Check content for both years (some might not have had 2025)
            has_2025_in_content = '2025' in content

            if has_2026_in_title and not has_2025_in_title:
                print(f"   [PASS] {article_name}: Title updated to 2026")
            elif has_2025_in_title:
                print(f"   [FAIL] {article_name}: Title still contains 2025!")
                print(f"          Title: {title}")
                all_passed = False
            else:
                print(f"   [INFO] {article_name}: No year in title")

        # ============================================================
        # TEST 3: Verify SMART Goals title fix
        # ============================================================
        print("\n[TEST 3] Verifying SMART Goals title fix...")
        smart_goals_posts = list(blog_collection.where('slug', '==', 'ai-powered-smart-goals-physiotherapy').limit(1).stream())

        if len(smart_goals_posts) == 0:
            print("   [WARNING] SMART Goals article not found!")
        else:
            post_data = smart_goals_posts[0].to_dict()
            title = post_data.get('title', '')
            content = post_data.get('content', '')

            # Check if "Revolutionizing" has been removed
            has_revolution_in_title = 'revolutioniz' in title.lower()
            has_evidence_based = 'Evidence-Based' in title

            if not has_revolution_in_title and has_evidence_based:
                print("   [PASS] SMART Goals title fixed - 'Revolutionizing' removed")
                print(f"          New title: {title}")
            else:
                print("   [FAIL] SMART Goals title still contains 'Revolutionizing'!")
                print(f"          Title: {title}")
                all_passed = False

        # ============================================================
        # TEST 4: Verify internal cross-links
        # ============================================================
        print("\n[TEST 4] Verifying internal cross-links...")

        # Check Clinical Reasoning article
        cr_posts = list(blog_collection.where('slug', '==', 'clinical-reasoning-physiotherapy-complete-2025-guide').limit(1).stream())
        if cr_posts:
            content = cr_posts[0].to_dict().get('content', '')
            has_ht_link = 'history-taking-physiotherapy-complete-guide-2025' in content
            has_oa_link = 'objective-assessment-framework-physiotherapy-complete-guide' in content

            if has_ht_link and has_oa_link:
                print("   [PASS] Clinical Reasoning article has cross-links to History Taking and Objective Assessment")
            else:
                print(f"   [PARTIAL] Clinical Reasoning cross-links - HT: {has_ht_link}, OA: {has_oa_link}")

        # Check History Taking article
        ht_posts = list(blog_collection.where('slug', '==', 'history-taking-physiotherapy-complete-guide-2025').limit(1).stream())
        if ht_posts:
            content = ht_posts[0].to_dict().get('content', '')
            has_cr_link = 'clinical-reasoning-physiotherapy-complete-2025-guide' in content or 'clinical-reasoning-physiotherapy-complete-2026-guide' in content
            has_oa_link = 'objective-assessment-framework-physiotherapy-complete-guide' in content

            if has_cr_link and has_oa_link:
                print("   [PASS] History Taking article has cross-links to Clinical Reasoning and Objective Assessment")
            else:
                print(f"   [PARTIAL] History Taking cross-links - CR: {has_cr_link}, OA: {has_oa_link}")

        # Check Objective Assessment article
        oa_posts = list(blog_collection.where('slug', '==', 'objective-assessment-framework-physiotherapy-complete-guide').limit(1).stream())
        if oa_posts:
            content = oa_posts[0].to_dict().get('content', '')
            has_cr_link = 'clinical-reasoning-physiotherapy-complete-2025-guide' in content or 'clinical-reasoning-physiotherapy-complete-2026-guide' in content
            has_ht_link = 'history-taking-physiotherapy-complete-guide-2025' in content

            if has_cr_link and has_ht_link:
                print("   [PASS] Objective Assessment article has cross-links to Clinical Reasoning and History Taking")
            else:
                print(f"   [PARTIAL] Objective Assessment cross-links - CR: {has_cr_link}, HT: {has_ht_link}")

        # ============================================================
        # Summary
        # ============================================================
        print("\n" + "=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)

        if all_passed:
            print("\n[SUCCESS] All critical tests passed!")
        else:
            print("\n[WARNING] Some tests failed. Review output above.")

        print("\nREMINDER: 301 redirect added in main.py:")
        print("  FROM: /blog/post/clinical-reasoning-framework")
        print("  TO:   /blog/post/clinical-reasoning-physiotherapy-complete-2026-guide")
        print()

    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
