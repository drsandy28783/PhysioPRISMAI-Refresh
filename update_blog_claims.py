"""
Update Blog Posts to Remove Unsubstantiated Claims
This script updates existing blog posts in the database to replace
"Real-World Impact" sections with "How This Can Help Your Practice" sections.
"""

import os
from dotenv import load_dotenv
from azure_cosmos_db import get_cosmos_db

# Load environment variables
load_dotenv()

def update_blog_claims():
    """Update blog posts to remove unsubstantiated claims"""

    try:
        db = get_cosmos_db()
        blog_collection = db.collection('blog_posts')

        # Define the replacements
        replacements = [
            # Patient History
            {
                'old': """## Real-World Impact

Physiotherapists using PhysiologicPRISM's AI-powered history taking report:

- **50% reduction** in history-taking time
- **Zero missed red flags** through systematic AI prompts
- **Improved patient satisfaction** from better eye contact and engagement
- **Enhanced clinical reasoning** from more comprehensive data
- **Better treatment outcomes** from thorough initial assessment""",
                'new': """## How This Can Help Your Practice

PhysiologicPRISM's AI-powered history taking can:

- Save valuable time during patient assessments
- Help ensure comprehensive red flag screening through systematic prompts
- Allow more eye contact and engagement with patients
- Support thorough data collection for clinical reasoning
- Provide a strong foundation for treatment planning"""
            },
            # Pathophysiological Analysis
            {
                'old': """## Real-World Clinical Impact

Physiotherapists using AI-powered pathophysiological analysis report:

- **65% reduction** in analysis time
- **Improved diagnostic accuracy** through systematic differential reasoning
- **Enhanced clinical confidence** from evidence-based support
- **Better patient education** using clear AI-generated explanations
- **Stronger documentation** meeting professional standards""",
                'new': """## How This Can Help Your Practice

PhysiologicPRISM's AI-powered pathophysiological analysis can:

- Streamline the analysis process
- Support systematic differential reasoning
- Provide evidence-based clinical support
- Generate clear explanations for patient education
- Help create documentation that meets professional standards"""
            },
            # Provisional Diagnosis
            {
                'old': """## Real-World Impact

Physiotherapists using AI-assisted provisional diagnosis report:

- **40% reduction** in diagnostic formulation time
- **Increased diagnostic confidence** through systematic reasoning
- **Improved documentation quality** meeting all professional standards
- **Enhanced patient communication** using clear AI-generated explanations
- **Reduced medico-legal risk** through comprehensive differential documentation""",
                'new': """## How This Can Help Your Practice

PhysiologicPRISM's AI-assisted provisional diagnosis can:

- Streamline the diagnostic formulation process
- Support systematic clinical reasoning
- Help create documentation that meets professional standards
- Provide clear explanations for patient communication
- Support comprehensive differential documentation"""
            },
            # Treatment Planning
            {
                'old': """## Real-World Impact

Physiotherapists using AI-powered treatment planning report:

- **75% reduction** in planning and documentation time
- **Improved patient outcomes** through evidence-based interventions
- **Enhanced clinical confidence** from research-supported decisions
- **Better insurance approval rates** with detailed documentation
- **Reduced clinical stress** from simplified workflow""",
                'new': """## How This Can Help Your Practice

PhysiologicPRISM's AI-powered treatment planning can:

- Reduce time spent on planning and documentation
- Support selection of evidence-based interventions
- Provide research-supported decision making
- Help create detailed documentation for insurance requirements
- Simplify your clinical workflow"""
            },
            # SMART Goals
            {
                'old': """## Real-World Impact

Physiotherapists using PhysiologicPRISM's AI-powered goal setting report:

- **70% reduction** in time spent on goal documentation
- **Improved patient engagement** through more personalized, meaningful goals
- **Better treatment outcomes** from clearer, more specific objectives
- **Enhanced insurance compliance** with comprehensive, well-documented goals
- **Reduced clinical stress** from streamlined documentation""",
                'new': """## How This Can Help Your Practice

PhysiologicPRISM's AI-powered goal setting can:

- Reduce time spent on goal documentation
- Support more personalized, meaningful goals for patient engagement
- Help create clearer, more specific treatment objectives
- Provide comprehensive, well-documented goals for insurance compliance
- Streamline your clinical documentation workflow"""
            }
        ]

        # Get all published blog posts
        print("Fetching published blog posts...")
        posts_query = blog_collection.where('status', '==', 'published').stream()
        posts = list(posts_query)

        print(f"Found {len(posts)} published blog posts\n")

        updated_count = 0
        unchanged_count = 0

        for post in posts:
            post_data = post.to_dict()
            post_id = post.id
            title = post_data.get('title', 'Unknown')
            content = post_data.get('content', '')
            original_content = content

            # Check if any replacements are needed
            needs_update = False
            for replacement in replacements:
                if replacement['old'] in content:
                    content = content.replace(replacement['old'], replacement['new'])
                    needs_update = True

            if needs_update:
                # Update the post
                post_data['content'] = content
                blog_collection.document(post_id).set(post_data)
                print(f"✓ UPDATED: {title}")
                updated_count += 1
            else:
                print(f"  OK (no changes needed): {title}")
                unchanged_count += 1

        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Updated: {updated_count} posts")
        print(f"  Unchanged: {unchanged_count} posts")
        print(f"  Total: {len(posts)} posts")
        print(f"{'='*60}")

        if updated_count > 0:
            print(f"\n✓ Successfully updated {updated_count} blog post(s) to remove unsubstantiated claims!")
        else:
            print("\n✓ All blog posts are already up to date!")

    except Exception as e:
        print(f"\n✗ Error updating blog posts: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("="*60)
    print("UPDATE BLOG POSTS - REMOVE UNSUBSTANTIATED CLAIMS")
    print("="*60)
    print()
    update_blog_claims()
