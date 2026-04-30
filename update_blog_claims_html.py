"""
Update Blog Posts to Remove Unsubstantiated Claims (HTML Version)
This script updates existing blog posts in the database to replace
"Real-World Impact" sections with "How This Can Help Your Practice" sections.
Updated to work with HTML formatted content.
"""

import os
from dotenv import load_dotenv
from azure_cosmos_db import get_cosmos_db

# Load environment variables
load_dotenv()

def update_blog_claims_html():
    """Update blog posts to remove unsubstantiated claims (HTML version)"""

    try:
        db = get_cosmos_db()
        blog_collection = db.collection('blog_posts')

        # Define the replacements for HTML content
        replacements = [
            # Patient History
            {
                'old': """<h2>Real-World Impact</h2>

<p>Physiotherapists using PhysiologicPRISM's AI-powered history taking report:</p>

<ul>
<li><strong>50% reduction</strong> in history-taking time</li>
<li><strong>Zero missed red flags</strong> through systematic AI prompts</li>
<li><strong>Improved patient satisfaction</strong> from better eye contact and engagement</li>
<li><strong>Enhanced clinical reasoning</strong> from more comprehensive data</li>
<li><strong>Better treatment outcomes</strong> from thorough initial assessment</li>
</ul>""",
                'new': """<h2>How This Can Help Your Practice</h2>

<p>PhysiologicPRISM's AI-powered history taking can:</p>

<ul>
<li>Save valuable time during patient assessments</li>
<li>Help ensure comprehensive red flag screening through systematic prompts</li>
<li>Allow more eye contact and engagement with patients</li>
<li>Support thorough data collection for clinical reasoning</li>
<li>Provide a strong foundation for treatment planning</li>
</ul>"""
            },
            # Pathophysiological Analysis
            {
                'old': """<h2>Real-World Clinical Impact</h2>

<p>Physiotherapists using AI-powered pathophysiological analysis report:</p>

<ul>
<li><strong>65% reduction</strong> in analysis time</li>
<li><strong>Improved diagnostic accuracy</strong> through systematic differential reasoning</li>
<li><strong>Enhanced clinical confidence</strong> from evidence-based support</li>
<li><strong>Better patient education</strong> using clear AI-generated explanations</li>
<li><strong>Stronger documentation</strong> meeting professional standards</li>
</ul>""",
                'new': """<h2>How This Can Help Your Practice</h2>

<p>PhysiologicPRISM's AI-powered pathophysiological analysis can:</p>

<ul>
<li>Streamline the analysis process</li>
<li>Support systematic differential reasoning</li>
<li>Provide evidence-based clinical support</li>
<li>Generate clear explanations for patient education</li>
<li>Help create documentation that meets professional standards</li>
</ul>"""
            },
            # Provisional Diagnosis
            {
                'old': """<h2>Real-World Impact</h2>

<p>Physiotherapists using AI-assisted provisional diagnosis report:</p>

<ul>
<li><strong>40% reduction</strong> in diagnostic formulation time</li>
<li><strong>Increased diagnostic confidence</strong> through systematic reasoning</li>
<li><strong>Improved documentation quality</strong> meeting all professional standards</li>
<li><strong>Enhanced patient communication</strong> using clear AI-generated explanations</li>
<li><strong>Reduced medico-legal risk</strong> through comprehensive differential documentation</li>
</ul>""",
                'new': """<h2>How This Can Help Your Practice</h2>

<p>PhysiologicPRISM's AI-assisted provisional diagnosis can:</p>

<ul>
<li>Streamline the diagnostic formulation process</li>
<li>Support systematic clinical reasoning</li>
<li>Help create documentation that meets professional standards</li>
<li>Provide clear explanations for patient communication</li>
<li>Support comprehensive differential documentation</li>
</ul>"""
            },
            # Treatment Planning
            {
                'old': """<h2>Real-World Impact</h2>

<p>Physiotherapists using AI-powered treatment planning report:</p>

<ul>
<li><strong>75% reduction</strong> in planning and documentation time</li>
<li><strong>Improved patient outcomes</strong> through evidence-based interventions</li>
<li><strong>Enhanced clinical confidence</strong> from research-supported decisions</li>
<li><strong>Better insurance approval rates</strong> with detailed documentation</li>
<li><strong>Reduced clinical stress</strong> from simplified workflow</li>
</ul>""",
                'new': """<h2>How This Can Help Your Practice</h2>

<p>PhysiologicPRISM's AI-powered treatment planning can:</p>

<ul>
<li>Reduce time spent on planning and documentation</li>
<li>Support selection of evidence-based interventions</li>
<li>Provide research-supported decision making</li>
<li>Help create detailed documentation for insurance requirements</li>
<li>Simplify your clinical workflow</li>
</ul>"""
            },
            # SMART Goals
            {
                'old': """<h2>Real-World Impact</h2>

<p>Physiotherapists using PhysiologicPRISM's AI-powered goal setting report:</p>

<ul>
<li><strong>70% reduction</strong> in time spent on goal documentation</li>
<li><strong>Improved patient engagement</strong> through more personalized, meaningful goals</li>
<li><strong>Better treatment outcomes</strong> from clearer, more specific objectives</li>
<li><strong>Enhanced insurance compliance</strong> with comprehensive, well-documented goals</li>
<li><strong>Reduced clinical stress</strong> from streamlined documentation</li>
</ul>""",
                'new': """<h2>How This Can Help Your Practice</h2>

<p>PhysiologicPRISM's AI-powered goal setting can:</p>

<ul>
<li>Reduce time spent on goal documentation</li>
<li>Support more personalized, meaningful goals for patient engagement</li>
<li>Help create clearer, more specific treatment objectives</li>
<li>Provide comprehensive, well-documented goals for insurance compliance</li>
<li>Streamline your clinical documentation workflow</li>
</ul>"""
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
                    print(f"  - Found and replaced in: {title}")

            if needs_update:
                # Update the post
                post_data['content'] = content
                blog_collection.document(post_id).set(post_data)
                print(f"[OK] UPDATED: {title}")
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
            print(f"\n[OK] Successfully updated {updated_count} blog post(s) to remove unsubstantiated claims!")
        else:
            print("\n[OK] All blog posts are already up to date!")

    except Exception as e:
        print(f"\n[ERROR] Error updating blog posts: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("="*60)
    print("UPDATE BLOG POSTS - REMOVE UNSUBSTANTIATED CLAIMS (HTML)")
    print("="*60)
    print()
    update_blog_claims_html()
