#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add Clinical Reasoning blog post to Cosmos DB
Migrated from GCP Firestore deployment
"""

from azure_cosmos_db import get_cosmos_db
from datetime import datetime
import os
import sys

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("[INFO] Connecting to Cosmos DB...")
db = get_cosmos_db()
print("[SUCCESS] Connected to Cosmos DB")

# Blog post content
blog_post = {
    'title': 'Clinical Reasoning in Physiotherapy: The Complete 2025 Guide',
    'slug': 'clinical-reasoning-physiotherapy-complete-2025-guide',
    'excerpt': 'Master the art and science of clinical reasoning in physiotherapy. This comprehensive guide covers reasoning models, differential diagnosis, ICF framework, common errors, and how AI supports better clinical decisions in 2025.',
    'meta_description': 'Complete guide to clinical reasoning in physiotherapy for students, new grads & experienced clinicians. Learn ICF framework, avoid reasoning errors & improve outcomes.',
    'author': 'Dr. Sandeep',
    'tags': ['clinical reasoning', 'physiotherapy education', 'ICF framework', 'clinical decision making', 'evidence-based practice', 'differential diagnosis', 'biopsychosocial model', 'AI in physiotherapy'],
    'category': 'Clinical Practice',
    'featured_image': 'https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=1200&q=80',  # Physiotherapy clinical image
    'status': 'published',
    'published_at': datetime.now(),
    'created_at': datetime.now(),
    'updated_at': datetime.now(),
    'content': '''
<article class="blog-post-content">
    <div class="post-intro">
        <p class="lead">Clinical reasoning is the heartbeat of physiotherapy.</p>

        <p>It is the invisible process behind every question you ask, every test you choose, every hypothesis you generate, and every decision you make. Yet—despite being central to physiotherapy—it remains one of the most difficult skills to teach, learn, and consistently apply in real practice.</p>

        <p>Many physiotherapists say they "just do it," but expert reasoning is not instinct. <strong>It is a structured, trainable cognitive process</strong> that can be strengthened like any clinical skill.</p>
    </div>

    <div class="challenges-2025">
        <p>In 2025, physiotherapists face challenges unlike any previous generation:</p>
        <ul>
            <li>Increasingly complex patient presentations</li>
            <li>Higher documentation and compliance expectations</li>
            <li>Stronger demand for evidence-based practice</li>
            <li>Greater need for structured reasoning frameworks</li>
            <li>Rapid changes in healthcare delivery across settings</li>
            <li>Emergence of AI-supported clinical tools</li>
        </ul>
    </div>

    <blockquote class="key-insight">
        <p>For students and new graduates, clinical reasoning can feel overwhelming.<br>
        For experienced clinicians, reasoning becomes automatic—and blind spots can quietly form.<br>
        For educators, ensuring consistency across learners is a constant struggle.<br>
        For clinics, variability in documentation and reasoning is a major risk.</p>
    </blockquote>

    <p>This guide brings clarity, structure, and practical strategies for every physiotherapist who wants to reason with greater confidence, precision, and consistency.</p>

    <div class="cta-box" style="background: linear-gradient(135deg, #f8fffe 0%, #e6f7f5 100%); padding: 2rem; border-radius: 12px; margin: 2rem 0; text-align: center;">
        <h3 style="color: #1a5f5a; margin-bottom: 1rem;">See Clinical Reasoning in Action</h3>
        <p style="margin-bottom: 1.5rem;">PhysioPRISM guides you through complete, structured clinical reasoning workflows with AI assistance at every step.</p>
        <a href="/request-access" class="cta-button" style="display: inline-block; background: #1a5f5a; color: white; padding: 1rem 2rem; border-radius: 8px; text-decoration: none; font-weight: 600;">Try PhysioPRISM Free →</a>
    </div>

    <h2>1. What Is Clinical Reasoning? A Clear Definition</h2>

    <p>Clinical reasoning is the cognitive process physiotherapists use to:</p>
    <ul>
        <li>Gather patient information</li>
        <li>Interpret findings</li>
        <li>Generate hypotheses</li>
        <li>Make clinical decisions</li>
        <li>Implement treatment</li>
        <li>Reassess and refine understanding</li>
    </ul>

    <p>It is <strong>dynamic, non-linear, and constantly evolving</strong> as new information emerges.</p>

    <h3>Novice vs Expert Clinicians</h3>
    <p><strong>Novices</strong> tend to follow checklists and gather large amounts of information—but often struggle to identify what is meaningful.</p>
    <p><strong>Experts</strong> quickly filter information, recognize patterns, and narrow hypotheses early. They know which details are noise and which drive the clinical picture.</p>
    <p>This expertise is not mysterious; <em>it is structured and intentional</em>.</p>

    <h3>Core Components of Clinical Reasoning</h3>
    <ol>
        <li><strong>Information gathering</strong></li>
        <li><strong>Pattern recognition</strong></li>
        <li><strong>Hypothesis formation</strong></li>
        <li><strong>Hypothesis testing</strong></li>
        <li><strong>Decision-making</strong></li>
        <li><strong>Re-evaluation</strong></li>
    </ol>
    <p class="highlight">Most reasoning errors occur when one of these steps is skipped.</p>

    <h2>2. Models of Clinical Reasoning (Made Simple)</h2>

    <p>Understanding models helps clinicians move from instinct to intention.</p>

    <h3>1. Hypothetico–Deductive Reasoning</h3>
    <ul>
        <li>Generate hypotheses</li>
        <li>Test them</li>
        <li>Accept or reject</li>
    </ul>
    <p>Useful for complex or unfamiliar cases.</p>

    <h3>2. Pattern Recognition</h3>
    <p>Fast, experience-driven matching. Powerful for experts—but prone to bias.</p>

    <h3>3. Narrative Reasoning</h3>
    <p>Understanding the patient's story, expectations, and lived experience.</p>

    <h3>4. Biopsychosocial Reasoning</h3>
    <p>Integrates biological, psychological, and social influences.</p>

    <h3>5. ICF-Based Reasoning (The Most Complete Framework)</h3>
    <p>The ICF considers:</p>
    <ul>
        <li>Body functions</li>
        <li>Activities</li>
        <li>Participation</li>
        <li>Environmental factors</li>
        <li>Personal factors</li>
    </ul>
    <p><strong>PhysioLogic PRISM incorporates the ICF model directly</strong> into its structured assessments and reporting.</p>

    <h2>3. The Subjective Examination: The Engine of Reasoning</h2>

    <blockquote>
        <p>"80% of the diagnosis is made before you even touch the patient."</p>
    </blockquote>

    <p>A strong subjective exam builds the foundation for everything that follows. <a href="/blog/history-taking-physiotherapy-complete-guide-2025">Learn our complete framework for mastering history taking here</a>.</p>

    <h3>Essential Domains</h3>
    <ul>
        <li>Symptom behavior</li>
        <li>Aggravating/easing factors</li>
        <li>24-hour pattern</li>
        <li>Functional limitations</li>
        <li>Past medical history</li>
        <li>Red and yellow flags</li>
        <li>Patient expectations</li>
        <li>Patient goals</li>
    </ul>

    <p>A thorough subjective exam creates:</p>
    <ul>
        <li>A clear clinical picture</li>
        <li>A shortlist of differential diagnoses</li>
        <li>A targeted plan for the objective assessment</li>
    </ul>

    <h3>Common Mistakes</h3>
    <ul>
        <li>Asking generic, nonspecific questions</li>
        <li>Ignoring psychosocial factors</li>
        <li>Failing to clarify mechanism of injury</li>
        <li>Jumping to conclusions too early</li>
        <li>Spending insufficient time listening</li>
    </ul>

    <h3>Quick Example</h3>
    <div class="example-box" style="background: #f8f9fa; padding: 1.5rem; border-left: 4px solid #1a5f5a; margin: 1.5rem 0;">
        <p><strong>Patient:</strong> 45-year-old software engineer<br>
        <strong>Complaint:</strong> Neck pain for 2 months</p>

        <p><strong>❌ Weak subjective:</strong><br>
        "Neck pain, worse with work."</p>

        <p><strong>✅ Strong subjective:</strong></p>
        <ul>
            <li>Worsens after long static postures</li>
            <li>Improves with movement</li>
            <li>Associated headaches</li>
            <li>No red flags</li>
            <li>High job stress</li>
            <li>Poor sleep</li>
            <li>Moderate fear of persistent pain</li>
        </ul>
        <p><em>Now the reasoning has direction.</em></p>
    </div>

    <h2>4. Objective Examination: Testing With Purpose</h2>

    <p>The objective exam should <strong>confirm or refute your hypotheses</strong>, not replace them. <a href="/blog/objective-assessment-framework-physiotherapy-complete-guide">Read our complete 8-step objective assessment framework here</a>.</p>

    <h3>Key Components</h3>
    <ul>
        <li>Observation and posture</li>
        <li>Functional tasks</li>
        <li>Range of motion</li>
        <li>Strength testing</li>
        <li>Neurological screening</li>
        <li>Special tests</li>
    </ul>

    <h3>The Problem With Special Tests</h3>
    <p>Used alone, most special tests lack diagnostic power.<br>
    <strong>Used within clusters, they increase accuracy significantly.</strong></p>

    <p class="highlight">Objective tests should be hypothesis-driven, not a random checklist.</p>

    <h2>5. Differential Diagnosis: Thinking Like an Expert</h2>

    <p>Experts focus on <strong>mechanisms, not labels</strong>.</p>

    <h3>Case Example: Chronic Low Back Pain</h3>
    <p>Possible contributors:</p>
    <ul>
        <li>Facet joint irritation</li>
        <li>Discogenic pain</li>
        <li>SIJ involvement</li>
        <li>Neuropathic features</li>
        <li>Central sensitization</li>
        <li>Hip mobility deficits</li>
        <li>Yellow flags</li>
    </ul>
    <p>Experts maintain multiple hypotheses, refining them with each finding.</p>

    <h3>Avoid These Traps</h3>
    <ul>
        <li><strong>Confirmation bias</strong></li>
        <li><strong>Anchoring</strong></li>
        <li><strong>Early closure</strong></li>
        <li><strong>Over-reliance on imaging</strong></li>
        <li><strong>Testing without purpose</strong></li>
    </ul>

    <div class="cta-box" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 12px; margin: 2rem 0; text-align: center; color: white;">
        <h3 style="color: white; margin-bottom: 1rem;">Structure Your Clinical Reasoning</h3>
        <p style="margin-bottom: 1.5rem;">PhysioPRISM's workflow ensures you never miss a critical step in differential diagnosis.</p>
        <a href="/pilot-program" class="cta-button" style="display: inline-block; background: white; color: #764ba2; padding: 1rem 2rem; border-radius: 8px; text-decoration: none; font-weight: 600;">Learn About Our Pilot Program →</a>
    </div>

    <h2>6. The Biopsychosocial Model: Practical Application</h2>

    <p><strong>Pain is never purely mechanical.</strong></p>

    <h3>Biological</h3>
    <ul>
        <li>Tissue load</li>
        <li>Inflammation</li>
        <li>Degeneration</li>
        <li>Neurodynamics</li>
    </ul>

    <h3>Psychological</h3>
    <ul>
        <li>Fear avoidance</li>
        <li>Anxiety</li>
        <li>Catastrophizing</li>
        <li>Low self-efficacy</li>
    </ul>

    <h3>Social</h3>
    <ul>
        <li>Work demands</li>
        <li>Family dynamics</li>
        <li>Lifestyle factors</li>
        <li>Access to support</li>
    </ul>

    <h3>Example</h3>
    <div class="example-box" style="background: #f8f9fa; padding: 1.5rem; border-left: 4px solid #1a5f5a; margin: 1.5rem 0;">
        <p><strong>28-year-old runner with knee pain</strong></p>
        <ul>
            <li>Mild patellar tendinopathy</li>
            <li>High training load</li>
            <li>Fear of worsening</li>
            <li>Poor sleep</li>
            <li>Competitive pressure</li>
        </ul>
        <p><em>A purely biomechanical approach would fail.<br>
        A BPS approach treats the person, not just the tissue.</em></p>
    </div>

    <h2>7. The ICF Framework: The Most Underused Tool in Physiotherapy</h2>

    <p>ICF offers a structured way to map patient problems holistically.</p>

    <h3>Why ICF Improves Reasoning</h3>
    <ul>
        <li>Ensures contextual factors are explored</li>
        <li>Improves clarity and documentation</li>
        <li>Standardizes reasoning across clinicians</li>
        <li>Supports evidence-based treatment planning</li>
    </ul>

    <h3>Example (Rotator Cuff Pain)</h3>
    <ul>
        <li><strong>Body function:</strong> Pain, weakness</li>
        <li><strong>Activity:</strong> Difficulty lifting overhead</li>
        <li><strong>Participation:</strong> Unable to perform work tasks</li>
        <li><strong>Environmental:</strong> Poor workstation ergonomics</li>
        <li><strong>Personal:</strong> Fear of re-injury</li>
    </ul>
    <p><strong>PRISM uses ICF as the backbone of its entire workflow.</strong></p>

    <h2>8. Common Clinical Reasoning Errors (And How to Fix Them)</h2>

    <h3>1. Early Closure</h3>
    <p><strong>Error:</strong> Deciding too soon.<br>
    <strong>Fix:</strong> Keep multiple hypotheses open.</p>

    <h3>2. Confirmation Bias</h3>
    <p><strong>Error:</strong> Seeking evidence that supports your initial thought.<br>
    <strong>Fix:</strong> Look for disconfirming findings.</p>

    <h3>3. Over-Testing</h3>
    <p><strong>Error:</strong> Tests without purpose.<br>
    <strong>Fix:</strong> Test strategically.</p>

    <h3>4. Ignoring Psychosocial Factors</h3>
    <p><strong>Error:</strong> Leads to treatment failure.<br>
    <strong>Fix:</strong> Screen early and integrate meaningfully.</p>

    <h3>5. Not Reassessing</h3>
    <p><strong>Error:</strong> No adaptation = poor outcomes.<br>
    <strong>Fix:</strong> Reassess every session.</p>

    <h2>9. Clinical Reasoning in 2025: The Role of AI</h2>

    <p><strong>AI does not diagnose.<br>
    AI does not replace physiotherapists.</strong></p>

    <p>But it can significantly improve structure, clarity, and consistency.</p>

    <h3>What AI Can Support</h3>
    <ul>
        <li>Suggesting key follow-up questions</li>
        <li>Identifying missing information</li>
        <li>Flagging red/yellow flags</li>
        <li>Recommending relevant tests</li>
        <li>Offering evidence-informed insights</li>
        <li>Structuring documentation</li>
    </ul>

    <h3>What AI Cannot Do</h3>
    <ul>
        <li>Replace clinical judgment</li>
        <li>Feel patient context or emotion</li>
        <li>Perform manual therapy</li>
        <li>Build therapeutic alliance</li>
    </ul>

    <blockquote>
        <p>The future of physiotherapy is hybrid: <strong>clinical expertise + AI-supported structure</strong>.</p>
    </blockquote>

    <p>PhysioLogic PRISM was built to support this exact model.</p>

    <h2>10. Step-by-Step Framework for Stronger Reasoning</h2>

    <ol>
        <li><strong>STEP 1 — Collect information</strong><br>Subjective exam + goals + red flags</li>
        <li><strong>STEP 2 — Identify key cues</strong><br>Extract meaningful patterns</li>
        <li><strong>STEP 3 — Form hypotheses</strong><br>Keep multiple possibilities</li>
        <li><strong>STEP 4 — Objective exam</strong><br>Test with intention</li>
        <li><strong>STEP 5 — Interpret findings</strong><br>Strengthen or eliminate hypotheses</li>
        <li><strong>STEP 6 — Diagnosis + ICF mapping</strong></li>
        <li><strong>STEP 7 — Treatment planning</strong><br>Evidence-based, functional, goal-aligned</li>
        <li><strong>STEP 8 — Reassess & refine</strong><br>Adapt every session</li>
    </ol>

    <p><strong>This framework is woven directly into PRISM's clinical workflow.</strong> <a href="/homepage#how-it-works">See how the complete workflow works in practice</a>.</p>

    <h2>11. Case Example: Chronic LBP in a 60-Year-Old</h2>

    <h3>Subjective Summary</h3>
    <ul>
        <li>Slow, insidious onset</li>
        <li>Morning stiffness > pain</li>
        <li>Disturbed sleep</li>
        <li>No red flags</li>
        <li>Lives alone</li>
        <li>Fear of falling</li>
        <li>Reduced daily walking</li>
    </ul>

    <h3>Hypotheses</h3>
    <ul>
        <li>Mechanical LBP (facet-related)</li>
        <li>Hip mobility limitation</li>
        <li>Deconditioning</li>
        <li>Psychosocial fear-avoidance</li>
        <li>Mild neuropathic mix</li>
    </ul>

    <h3>Objective Findings</h3>
    <ul>
        <li>Limited extension</li>
        <li>Tight hip flexors</li>
        <li>Motor control deficits</li>
        <li>Normal neurological screen</li>
        <li>Facet tenderness</li>
        <li>Balance impairment</li>
    </ul>

    <h3>ICF Map</h3>
    <ul>
        <li><strong>Body function:</strong> Pain, stiffness, weak extensors</li>
        <li><strong>Activity:</strong> Difficulty bending, stairs</li>
        <li><strong>Participation:</strong> Reduced social engagement</li>
        <li><strong>Environment:</strong> Limited home support</li>
        <li><strong>Personal:</strong> Fear of movement</li>
    </ul>

    <h3>Working Impression</h3>
    <p>Degenerative, age-related LBP with mobility deficits, motor control impairment, and psychosocial contributors.</p>

    <h3>Treatment Plan</h3>
    <ul>
        <li>Education ("pain ≠ damage")</li>
        <li>Graded mobility</li>
        <li>Hip mobility training</li>
        <li>Strengthening + balance work</li>
        <li>Functional goal: Walk 20 minutes daily</li>
        <li>Reassess every session</li>
    </ul>

    <p class="highlight"><strong>A structured reasoning pathway → clearer decisions → better outcomes.</strong></p>

    <h2>12. Key Takeaways</h2>

    <ul>
        <li>Clinical reasoning is the core skill of physiotherapy.</li>
        <li>Strong subjective exams drive accurate diagnoses.</li>
        <li>Objective tests should be targeted and hypothesis-driven.</li>
        <li>Differential diagnosis is dynamic, not fixed.</li>
        <li>BPS + ICF provide holistic clarity.</li>
        <li>Avoid biases like early closure and confirmation bias.</li>
        <li>AI can enhance structure—but clinicians remain in control.</li>
    </ul>

    <hr style="margin: 3rem 0; border: none; border-top: 2px solid #e6f7f5;">

    <h2>Conclusion</h2>

    <p>Clinical reasoning isn't a talent reserved for experts. <strong>It is a trainable, repeatable framework</strong> that strengthens with structure, reflection, and intentional practice.</p>

    <p>In today's fast-evolving clinical landscape, physiotherapists who master clear, structured reasoning will deliver better outcomes, better documentation, and better patient experiences.</p>

    <p>Tools like <strong>PhysioLogic PRISM</strong> support this evolution by guiding clinicians through complete, evidence-informed workflows—ensuring no detail is missed and every decision is defensible.</p>

    <blockquote class="conclusion-quote" style="font-size: 1.2rem; text-align: center; padding: 2rem; background: #f8fffe; border-left: 4px solid #1a5f5a; margin: 2rem 0;">
        <p><strong>Your clinical mind is your superpower.<br>
        This guide is your roadmap.<br>
        Your growth starts now.</strong></p>
    </blockquote>

    <div class="cta-box" style="background: linear-gradient(135deg, #1a5f5a 0%, #2d8b7f 100%); padding: 3rem; border-radius: 12px; margin: 3rem 0; text-align: center; color: white;">
        <h3 style="color: white; margin-bottom: 1rem; font-size: 1.8rem;">Ready to Experience Structured Clinical Reasoning?</h3>
        <p style="margin-bottom: 2rem; font-size: 1.1rem;">Join physiotherapists who are elevating their clinical practice with PhysioPRISM's AI-guided workflow.</p>
        <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
            <a href="/request-access" class="cta-button" style="display: inline-block; background: white; color: #1a5f5a; padding: 1rem 2.5rem; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 1.1rem;">Request Early Access →</a>
            <a href="/pilot-program" class="cta-button" style="display: inline-block; background: transparent; color: white; border: 2px solid white; padding: 1rem 2.5rem; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 1.1rem;">Learn About Pilot Program</a>
        </div>
    </div>

    <div class="related-resources" style="background: #f8f9fa; padding: 2rem; border-radius: 8px; margin-top: 3rem;">
        <h3 style="color: #1a5f5a; margin-bottom: 1rem;">Further Reading</h3>
        <ul>
            <li><a href="/blog/history-taking-physiotherapy-complete-guide-2025">History Taking in Physiotherapy: The Complete 2025 Guide</a></li>
            <li><a href="/blog/objective-assessment-framework-physiotherapy-complete-guide">Objective Assessment Framework: A Complete Guide</a></li>
            <li><a href="/homepage#how-it-works">See How the Clinical Reasoning Workflow Works</a></li>
            <li><a href="/security">How PhysioPRISM Protects Patient Data</a></li>
            <li><a href="/pilot-program">Join Our 30-Day Clinical Reasoning Pilot</a></li>
            <li><a href="/pricing">View Our Subscription Plans</a></li>
        </ul>
    </div>
</article>

<style>
.blog-post-content {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem 1rem;
    font-size: 1.1rem;
    line-height: 1.8;
    color: #2c3e50;
}

.blog-post-content h2 {
    color: #1a5f5a;
    font-size: 2rem;
    margin-top: 3rem;
    margin-bottom: 1rem;
    font-weight: 700;
    line-height: 1.3;
}

.blog-post-content h3 {
    color: #2d8b7f;
    font-size: 1.5rem;
    margin-top: 2rem;
    margin-bottom: 0.75rem;
    font-weight: 600;
}

.blog-post-content p {
    margin-bottom: 1.5rem;
}

.blog-post-content ul,
.blog-post-content ol {
    margin-bottom: 1.5rem;
    padding-left: 2rem;
}

.blog-post-content li {
    margin-bottom: 0.5rem;
}

.blog-post-content blockquote {
    border-left: 4px solid #1a5f5a;
    padding-left: 1.5rem;
    margin: 2rem 0;
    font-style: italic;
    color: #555;
    background: #f8fffe;
    padding: 1.5rem;
    border-radius: 4px;
}

.blog-post-content .lead {
    font-size: 1.4rem;
    font-weight: 500;
    color: #1a5f5a;
    line-height: 1.6;
    margin-bottom: 1.5rem;
}

.blog-post-content .highlight {
    background: #fff3cd;
    padding: 0.5rem 1rem;
    border-left: 4px solid #ffc107;
    margin: 1.5rem 0;
    font-weight: 500;
}

.blog-post-content strong {
    color: #1a5f5a;
    font-weight: 600;
}

.blog-post-content a {
    color: #1a5f5a;
    text-decoration: underline;
}

.blog-post-content a:hover {
    color: #2d8b7f;
}

@media (max-width: 768px) {
    .blog-post-content {
        font-size: 1rem;
        padding: 1rem;
    }

    .blog-post-content h2 {
        font-size: 1.6rem;
    }

    .blog-post-content h3 {
        font-size: 1.3rem;
    }

    .cta-box {
        padding: 1.5rem !important;
    }
}
</style>
'''
}

# Add to Cosmos DB
try:
    # Add the blog post
    doc_ref = db.collection('blog_posts').add(blog_post)
    print("\n" + "="*70)
    print("[SUCCESS] Blog post added to Cosmos DB successfully!")
    print("="*70)
    print(f"Document ID: {doc_ref[1].id}")
    print(f"Title: {blog_post['title']}")
    print(f"Slug: {blog_post['slug']}")
    print(f"Status: {blog_post['status']}")
    print("\n" + "-"*70)
    print("View your blog post at:")
    print(f"  /blog")
    print(f"  /blog/{blog_post['slug']}")
    print("\nEdit or manage at:")
    print(f"  /admin/blog")
    print("="*70 + "\n")

except Exception as e:
    print("\n" + "="*70)
    print(f"[ERROR] Failed to add blog post")
    print("="*70)
    print(f"Error: {e}")
    print("Please check:")
    print("  1. Cosmos DB credentials are configured")
    print("  2. Database permissions allow write access")
    print("  3. 'blog_posts' collection exists")
    print("="*70 + "\n")
    import traceback
    traceback.print_exc()
    exit(1)
