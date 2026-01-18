"""
Import all 3 comprehensive blog posts from GCP deployment to Cosmos DB
Run this script on Azure deployment where Cosmos DB credentials are available.
"""

import subprocess
import sys

def run_script(script_name, blog_title):
    """Run a blog import script"""
    print("\n" + "=" * 80)
    print(f"IMPORTING: {blog_title}")
    print("=" * 80)

    result = subprocess.run([sys.executable, script_name], capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        print(f"[ERROR] Failed to import {blog_title}")
        return False

    return True

def main():
    print("\n" + "=" * 80)
    print("IMPORTING ALL GCP BLOG POSTS TO COSMOS DB")
    print("=" * 80)
    print("\nThis will add 3 comprehensive blog posts:")
    print("  1. Clinical Reasoning in Physiotherapy: The Complete 2025 Guide")
    print("  2. History Taking in Physiotherapy: The Complete 2025 Guide")
    print("  3. Objective Assessment Framework: A Complete Guide (2025)")
    print("\n")

    response = input("Do you want to continue? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        return

    # Import all three blogs
    success_count = 0

    if run_script('import_blog_1.py', 'Clinical Reasoning'):
        success_count += 1

    if run_script('import_blog_2.py', 'History Taking'):
        success_count += 1

    if run_script('import_blog_3.py', 'Objective Assessment'):
        success_count += 1

    # Summary
    print("\n" + "=" * 80)
    print(f"IMPORT COMPLETE: {success_count}/3 blog posts successfully added")
    print("=" * 80)

    if success_count == 3:
        print("\n[SUCCESS] All blog posts have been imported!")
        print("\nView them at:")
        print("  - /blog")
        print("  - Homepage carousel")
        print("  - /admin/blog (super admin only)")
    else:
        print(f"\n[WARNING] Only {success_count} out of 3 blog posts were imported successfully")
        print("Please check the error messages above")

    print("\n")

if __name__ == '__main__':
    main()
