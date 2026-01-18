#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add History Taking blog post to Cosmos DB
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
    'title': 'History Taking in Physiotherapy: The Complete 2025 Guide for Clinicians',
    'slug': 'history-taking-physiotherapy-complete-guide-2025',
    'excerpt': 'Master the art of subjective examination in physiotherapy. This comprehensive guide covers essential questions, red flag screening, ICF integration, and how to conduct efficient, accurate patient histories.',
    'meta_description': 'Complete guide to history taking in physiotherapy. Learn essential questions, red & yellow flag screening, ICF framework integration, and AI-enhanced documentation workflows.',
    'author': 'Dr. Sandeep',
    'tags': ['history taking', 'subjective examination', 'clinical assessment', 'red flags', 'yellow flags', 'ICF framework', 'patient interview', 'physiotherapy documentation'],
    'category': 'Clinical Practice',
    'featured_image': 'https://images.unsplash.com/photo-1551076805-e1869033e561?w=1200&q=80',  # Doctor-patient consultation
    'status': 'published',
    'published_at': datetime.now(),
    'created_at': datetime.now(),
    'updated_at': datetime.now(),
    'content': '''
<article class="blog-post-content">
    <div class="post-intro">
        <p class="lead">History taking is the most powerful diagnostic tool a physiotherapist has — yet it's also the most underestimated.</p>

        <p>Studies across multiple clinical settings show that <strong>up to 80% of physiotherapy diagnoses can be made from the subjective examination alone</strong>, before any special test or objective measure is performed.</p>

        <p>A structured, thoughtful history not only uncovers pathology patterns but also reveals the patient's beliefs, red flags, psychosocial factors, functional limitations, and personal goals — all critical components of the ICF framework.</p>
    </div>

    <blockquote class="key-insight">
        <p>Whether you're a new graduate learning to organize your assessment or a busy clinician seeking efficiency, mastering history taking reduces uncertainty, improves outcomes, and strengthens therapeutic alliance.</p>
    </blockquote>

    <div class="section-intro">
        <p>In this comprehensive guide, we'll break down:</p>
        <ul>
            <li>The essential elements of high-quality history taking</li>
            <li>The exact questions that lead to accurate, fast, clinically sound reasoning</li>
            <li>How to identify red & yellow flags early</li>
            <li>How to integrate the ICF model seamlessly into your interview</li>
            <li>How AI tools like PhysioPRISM can streamline the process</li>
        </ul>
        <p><em>This guide pairs with our <a href="/blog/clinical-reasoning-physiotherapy-complete-2025-guide">Clinical Reasoning framework</a> and <a href="/blog/objective-assessment-framework-physiotherapy-complete-guide">Objective Assessment guide</a> for complete patient evaluation.</em></p>
    </div>

    <h2>1. Why History Taking Matters More Than Any Special Test</h2>

    <p>Many physiotherapists jump too quickly into objective tests — but evidence continually shows:</p>

    <ul>
        <li><strong>Mechanical patterns, not isolated tests, predict diagnosis</strong></li>
        <li><strong>Symptoms + behavior over time</strong> reveal irritability, severity, stage, and prognosis</li>
        <li><strong>Patient beliefs and fears</strong> influence chronicity far more than biomechanics</li>
        <li><strong>Flag screening during history taking</strong> is the first line of safety in physiotherapy practice</li>
    </ul>

    <div class="highlight-box" style="background: #fff3cd; padding: 1.5rem; border-left: 4px solid #ffc107; margin: 2rem 0;">
        <p><strong>Most importantly, history taking is where the clinician:</strong></p>
        <ul style="margin-bottom: 0;">
            <li>Builds trust</li>
            <li>Understands the patient as a person</li>
            <li>Defines goals collaboratively</li>
            <li>Determines which objective tests are even necessary</li>
        </ul>
    </div>

    <blockquote>
        <p><strong>A clear history leads to a focused objective exam.<br>A poor history leads to confusion.</strong></p>
    </blockquote>

    <div class="cta-box" style="background: linear-gradient(135deg, #f8fffe 0%, #e6f7f5 100%); padding: 2rem; border-radius: 12px; margin: 2rem 0; text-align: center;">
        <h3 style="color: #1a5f5a; margin-bottom: 1rem;">Experience Structured History Taking</h3>
        <p style="margin-bottom: 1.5rem;">PhysioPRISM guides you through comprehensive patient histories with AI-suggested questions and automatic flag detection.</p>
        <a href="/request-access" class="cta-button" style="display: inline-block; background: #1a5f5a; color: white; padding: 1rem 2rem; border-radius: 8px; text-decoration: none; font-weight: 600;">Try PhysioPRISM Free →</a>
    </div>

    <h2>2. Core Components of an Excellent Subjective Examination</h2>

    <p>Below is the universally accepted structure that aligns with best physiotherapy practice — and is identical to the workflow inside PhysioPRISM's documentation system.</p>

    <h3>2.1 Chief Complaint</h3>

    <p>The patient's main reason for seeking care — <em>in their own words</em>.</p>

    <div class="example-box" style="background: #f8f9fa; padding: 1.5rem; border-left: 4px solid #1a5f5a; margin: 1.5rem 0;">
        <p><strong>Key questions:</strong></p>
        <ul>
            <li>"What brings you in today?"</li>
            <li>"What is the biggest limitation this problem is causing?"</li>
        </ul>
        <p><strong>Clinical goal:</strong> Captures the primary functional issue and patient priorities.</p>
    </div>

    <h3>2.2 Onset & Mechanism of Injury</h3>

    <p>Understanding the "how" sets the direction of reasoning.</p>

    <div class="example-box" style="background: #f8f9fa; padding: 1.5rem; border-left: 4px solid #1a5f5a; margin: 1.5rem 0;">
        <p><strong>Ask:</strong></p>
        <ul>
            <li>"When did this start?"</li>
            <li>"What were you doing when it happened?"</li>
            <li>"Was the onset sudden or gradual?"</li>
        </ul>
        <p><strong>Why it matters:</strong></p>
        <ul style="margin-bottom: 0;">
            <li>Sudden onset → structural injury</li>
            <li>Gradual onset → overload, postural, degenerative conditions</li>
        </ul>
    </div>

    <p class="highlight">PhysioPRISM integrates these details into age-appropriate reasoning patterns (e.g., frozen shoulder risk in diabetics aged 40+).</p>

    <h3>2.3 Pain Description & Behavior</h3>

    <p>Your roadmap to identifying the tissue and irritability.</p>

    <p><strong>Cover:</strong></p>
    <ul>
        <li>Location (primary vs referred)</li>
        <li>Type of pain (sharp, dull, burning, throbbing)</li>
        <li>Irritating & easing factors</li>
        <li>24-hour pattern</li>
        <li>Severity (VAS)</li>
    </ul>

    <div class="highlight-box" style="background: #e6f7f5; padding: 1.5rem; border-left: 4px solid #1a5f5a; margin: 2rem 0;">
        <p><strong>Key insight:</strong> The 24-hour pattern reveals inflammatory vs mechanical nature.</p>
        <p><strong>Example:</strong></p>
        <ul style="margin-bottom: 0;">
            <li>Morning stiffness lasting >1 hour → <strong>inflammatory</strong></li>
            <li>Pain worsening with activity and easing with rest → <strong>mechanical overload</strong></li>
        </ul>
    </div>

    <h3>2.4 Functional Limitations (ICF: Activity Level)</h3>

    <p>Not "what hurts," but <strong>what the patient can no longer do</strong>.</p>

    <div class="example-box" style="background: #f8f9fa; padding: 1.5rem; border-left: 4px solid #1a5f5a; margin: 1.5rem 0;">
        <p><strong>Ask:</strong></p>
        <ul>
            <li>"What specific tasks are affected?"</li>
            <li>"What can you do now that you couldn't last week/month?"</li>
        </ul>
        <p style="margin-bottom: 0;">This ties directly into PhysioPRISM's ICF-based documentation structure and SMART goal formulation workflows.</p>
    </div>

    <h3>2.5 Participation Restrictions (ICF: Social Roles)</h3>

    <p><strong>Examples:</strong></p>
    <ul>
        <li>Job limitations</li>
        <li>Reduced recreational/sports participation</li>
        <li>Home management difficulties</li>
    </ul>

    <p class="highlight">This component shapes prognosis & treatment planning.</p>

    <h3>2.6 Past Medical History & Comorbidities</h3>

    <p>Critical for safe decision-making.</p>

    <p><strong>Examples:</strong></p>
    <ul>
        <li><strong>Diabetes</strong> → frozen shoulder risk</li>
        <li><strong>Osteoporosis</strong> → fracture risk</li>
        <li><strong>Cardiovascular disease</strong> → exercise tolerance issues</li>
    </ul>

    <p>PhysioPRISM's AI engine automatically prompts relevant questions based on age group and clinical presentation.</p>

    <h3>2.7 Medications & Investigations</h3>

    <p><strong>Important because:</strong></p>
    <ul>
        <li>Steroids mask symptoms</li>
        <li>Anticoagulants alter manual therapy choices</li>
        <li>Imaging findings often correlate poorly and may mislead patients</li>
    </ul>

    <div class="example-box" style="background: #f8f9fa; padding: 1.5rem; border-left: 4px solid #1a5f5a; margin: 1.5rem 0;">
        <p><strong>Ask:</strong> "Have you had any X-rays/MRI/CT scans? What did the doctor tell you?"</p>
    </div>

    <h3>2.8 Special Questions: Red & Yellow Flags</h3>

    <p><strong>These must be asked in every assessment, regardless of complaint.</strong></p>

    <div class="warning-box" style="background: #fff5f5; padding: 1.5rem; border-left: 4px solid #e74c3c; margin: 2rem 0;">
        <h4 style="color: #e74c3c; margin-top: 0;">Red Flag Screening Includes:</h4>
        <ul>
            <li>Unexplained weight loss</li>
            <li>Night pain unrelieved by rest</li>
            <li>Previous history of cancer</li>
            <li>Bowel/bladder changes</li>
            <li>Saddle anesthesia</li>
            <li>Fever, chills, systemic signs</li>
        </ul>
        <p style="margin-bottom: 0;"><em>This mirrors the red flag documentation criteria used inside PhysioPRISM's clinical reasoning engine.</em></p>
    </div>

    <div class="caution-box" style="background: #fffbf0; padding: 1.5rem; border-left: 4px solid #f39c12; margin: 2rem 0;">
        <h4 style="color: #d68910; margin-top: 0;">Yellow Flags (Psychosocial Indicators):</h4>
        <ul style="margin-bottom: 0.5rem;">
            <li>Fear-avoidance beliefs</li>
            <li>Catastrophizing</li>
            <li>Low expectations of recovery</li>
            <li>Job dissatisfaction</li>
        </ul>
        <p style="margin-bottom: 0;"><strong>These influence chronicity and treatment outcomes.</strong></p>
    </div>

    <h3>2.9 Patient Goals (The Heart of Patient-Centered Care)</h3>

    <div class="example-box" style="background: #f8f9fa; padding: 1.5rem; border-left: 4px solid #1a5f5a; margin: 1.5rem 0;">
        <p><strong>Ask:</strong> "What does successful treatment look like to you?"</p>
        <p style="margin-bottom: 0;">Goal-setting is essential for building therapeutic buy-in and aligns directly with SMART goal generation inside PhysioPRISM's treatment planning workflow.</p>
    </div>

    <h2>3. Putting It All Together: A Sample History Taking Flow</h2>

    <p>Below is a professional, compassionate, clinician-friendly script you can use in your practice.</p>

    <div class="clinical-script" style="background: #f8fffe; padding: 2rem; border-radius: 12px; margin: 2rem 0;">
        <h3 style="color: #1a5f5a; margin-top: 0;">Sample Clinical Interview Script</h3>

        <div class="script-section" style="margin-bottom: 1.5rem;">
            <p><strong>Opening (Building Rapport):</strong></p>
            <p style="font-style: italic; color: #555; margin-left: 1rem;">"Hi [Name], I'm [Your Name], a physiotherapist here. Before we start, I'd like to understand your story properly so we can work out the best plan together. Is that okay?"</p>
        </div>

        <div class="script-section" style="margin-bottom: 1.5rem;">
            <p><strong>Chief Complaint:</strong></p>
            <p style="font-style: italic; color: #555; margin-left: 1rem;">"What's brought you in today?"<br>
            "Of all the problems this is causing, what's the one thing you'd most like to get back to?"</p>
        </div>

        <div class="script-section" style="margin-bottom: 1.5rem;">
            <p><strong>Onset & Mechanism:</strong></p>
            <p style="font-style: italic; color: #555; margin-left: 1rem;">"When did you first notice this?"<br>
            "Do you remember doing anything specific that might have triggered it?"<br>
            "Did it come on suddenly or build up gradually over time?"</p>
        </div>

        <div class="script-section" style="margin-bottom: 1.5rem;">
            <p><strong>Pain Behavior:</strong></p>
            <p style="font-style: italic; color: #555; margin-left: 1rem;">"Can you point to exactly where you feel it?"<br>
            "How would you describe the pain — sharp, dull, burning, aching?"<br>
            "On a scale of 0 to 10, where 0 is no pain and 10 is the worst pain imaginable, where would you rate it right now?"<br>
            "What makes it worse? What makes it better?"<br>
            "How does it feel first thing in the morning compared to the end of the day?"</p>
        </div>

        <div class="script-section" style="margin-bottom: 1.5rem;">
            <p><strong>Functional Impact:</strong></p>
            <p style="font-style: italic; color: #555; margin-left: 1rem;">"What everyday activities are being affected?"<br>
            "Are you able to work/exercise/sleep normally?"</p>
        </div>

        <div class="script-section" style="margin-bottom: 1.5rem;">
            <p><strong>Past Medical History:</strong></p>
            <p style="font-style: italic; color: #555; margin-left: 1rem;">"Do you have any other medical conditions I should know about?"<br>
            "Are you taking any medications?"<br>
            "Have you had any scans or tests for this?"</p>
        </div>

        <div class="script-section" style="margin-bottom: 1.5rem;">
            <p><strong>Red Flag Screening:</strong></p>
            <p style="font-style: italic; color: #555; margin-left: 1rem;">"I need to ask a few safety questions — these are routine for everyone:"<br>
            • "Have you had any unexpected weight loss recently?"<br>
            • "Any trouble with bladder or bowel control?"<br>
            • "Any numbness around your groin or buttocks?"<br>
            • "Does the pain wake you at night even when you're lying still?"</p>
        </div>

        <div class="script-section" style="margin-bottom: 0;">
            <p><strong>Patient Goals:</strong></p>
            <p style="font-style: italic; color: #555; margin-left: 1rem;">"If we could fix one thing by the end of treatment, what would matter most to you?"</p>
        </div>
    </div>

    <p class="highlight"><strong>This entire flow can be documented in real-time inside PhysioPRISM with AI-suggested follow-up questions based on your patient's responses.</strong> <a href="/homepage#how-it-works" style="color: #667eea; text-decoration: underline;">See the complete workflow in action</a>.</p>

    <div class="cta-box" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 12px; margin: 2rem 0; text-align: center; color: white;">
        <h3 style="color: white; margin-bottom: 1rem;">Never Miss a Critical Question Again</h3>
        <p style="margin-bottom: 1.5rem;">PhysioPRISM's AI prompts you with context-specific questions based on your patient's presentation.</p>
        <a href="/pilot-program" class="cta-button" style="display: inline-block; background: white; color: #764ba2; padding: 1rem 2rem; border-radius: 8px; text-decoration: none; font-weight: 600;">Join Our Pilot Program →</a>
    </div>

    <h2>4. Common Mistakes Physiotherapists Make in History Taking (And How to Fix Them)</h2>

    <h3>Mistake #1: Asking Closed Questions Too Early</h3>
    <div class="mistake-box" style="background: #fff5f5; padding: 1.5rem; margin: 1.5rem 0; border-radius: 8px;">
        <p><strong>❌ Wrong:</strong> "Does your shoulder hurt when you lift your arm?"</p>
        <p><strong>✅ Better:</strong> "Tell me what happens when you try to lift your arm."</p>
        <p><em>Open questions early = richer information. Close questions later = specific confirmation.</em></p>
    </div>

    <h3>Mistake #2: Jumping to Solutions Before Understanding the Problem</h3>
    <div class="mistake-box" style="background: #fff5f5; padding: 1.5rem; margin: 1.5rem 0; border-radius: 8px;">
        <p><strong>The trap:</strong> "Okay, sounds like a rotator cuff issue. Let's get you on the table."</p>
        <p><strong>The fix:</strong> Spend 80% of your time listening, 20% guiding. Let the patient finish their story.</p>
    </div>

    <h3>Mistake #3: Ignoring Psychosocial Factors</h3>
    <div class="mistake-box" style="background: #fff5f5; padding: 1.5rem; margin: 1.5rem 0; border-radius: 8px;">
        <p><strong>Reality:</strong> Fear, stress, job dissatisfaction, and catastrophizing predict chronicity better than tissue damage.</p>
        <p><strong>Solution:</strong> Always screen for yellow flags. PhysioPRISM includes validated questionnaires like the Fear-Avoidance Beliefs Questionnaire (FABQ) integrated into its workflow.</p>
    </div>

    <h3>Mistake #4: Not Documenting Red Flags Properly</h3>
    <div class="mistake-box" style="background: #fff5f5; padding: 1.5rem; margin: 1.5rem 0; border-radius: 8px;">
        <p><strong>Legal risk:</strong> If you didn't document it, legally you didn't ask it.</p>
        <p><strong>Solution:</strong> Use structured templates (like PhysioPRISM's) that include mandatory red flag fields.</p>
    </div>

    <h3>Mistake #5: Skipping Goal-Setting</h3>
    <div class="mistake-box" style="background: #fff5f5; padding: 1.5rem; margin: 1.5rem 0; border-radius: 8px;">
        <p><strong>Problem:</strong> You treat what you think matters. The patient wants something else.</p>
        <p><strong>Fix:</strong> Co-create SMART goals. PhysioPRISM auto-generates SMART goals from patient responses.</p>
    </div>

    <h3>Mistake #6: Over-Relying on Imaging Results</h3>
    <div class="mistake-box" style="background: #fff5f5; padding: 1.5rem; margin: 1.5rem 0; border-radius: 8px;">
        <p><strong>Evidence:</strong> MRI findings like disc bulges, labral tears, and rotator cuff changes are common in asymptomatic people.</p>
        <p><strong>Clinical pearl:</strong> Treat the patient, not the scan. History reveals the true clinical picture.</p>
    </div>

    <h2>5. How AI Can Enhance History Taking Without Replacing Clinical Judgment</h2>

    <p>PhysioPRISM supports clinicians by:</p>

    <div class="features-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin: 2rem 0;">
        <div class="feature-card" style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0;">Context-Specific Questions</h4>
            <p style="margin-bottom: 0;">AI suggests relevant follow-up questions based on patient age, presentation, and body region</p>
        </div>
        <div class="feature-card" style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0;">Automatic Flag Detection</h4>
            <p style="margin-bottom: 0;">Real-time alerts when patient responses indicate potential red or yellow flags</p>
        </div>
        <div class="feature-card" style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0;">Differential Diagnosis Support</h4>
            <p style="margin-bottom: 0;">AI generates possible diagnoses based on subjective findings to guide objective exam</p>
        </div>
        <div class="feature-card" style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0;">ICF Auto-Mapping</h4>
            <p style="margin-bottom: 0;">Automatically maps patient responses to ICF domains for comprehensive documentation</p>
        </div>
        <div class="feature-card" style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0;">10x Faster Documentation</h4>
            <p style="margin-bottom: 0;">Structured fields and AI assistance speed up documentation while maintaining quality</p>
        </div>
        <div class="feature-card" style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0;">SMART Goal Generation</h4>
            <p style="margin-bottom: 0;">AI converts patient goals into proper SMART format automatically</p>
        </div>
    </div>

    <blockquote>
        <p><strong>AI enhances structure and consistency — but clinical judgment remains with the physiotherapist.</strong></p>
    </blockquote>

    <h2>6. Key Takeaways</h2>

    <ul>
        <li>History taking is the most powerful diagnostic tool in physiotherapy</li>
        <li>80% of diagnoses can be made from subjective examination alone</li>
        <li>Always screen for red and yellow flags in every patient</li>
        <li>Use open questions early, closed questions for confirmation</li>
        <li>Integrate ICF domains throughout your history taking</li>
        <li>Co-create goals with patients for better outcomes</li>
        <li>Document thoroughly — what isn't documented doesn't exist legally</li>
        <li>AI tools like PhysioPRISM enhance efficiency without replacing judgment</li>
    </ul>

    <hr style="margin: 3rem 0; border: none; border-top: 2px solid #e6f7f5;">

    <h2>Conclusion</h2>

    <p>A structured, comprehensive history is the foundation of excellent physiotherapy practice. When done systematically, it accelerates diagnosis, identifies safety concerns early, reveals psychosocial factors, and builds therapeutic alliance.</p>

    <p>In 2025, modern tools like <strong>PhysioPRISM</strong> support clinicians with AI-guided questions, automatic flag detection, and ICF-integrated documentation — allowing you to focus on patient interaction while maintaining clinical precision and compliance.</p>

    <blockquote class="conclusion-quote" style="font-size: 1.2rem; text-align: center; padding: 2rem; background: #f8fffe; border-left: 4px solid #1a5f5a; margin: 2rem 0;">
        <p><strong>Master your history taking.<br>
        Build better relationships.<br>
        Deliver better outcomes.</strong></p>
    </blockquote>

    <div class="cta-box" style="background: linear-gradient(135deg, #1a5f5a 0%, #2d8b7f 100%); padding: 3rem; border-radius: 12px; margin: 3rem 0; text-align: center; color: white;">
        <h3 style="color: white; margin-bottom: 1rem; font-size: 1.8rem;">Ready to Transform Your History Taking?</h3>
        <p style="margin-bottom: 2rem; font-size: 1.1rem;">Join physiotherapists who are conducting more efficient, comprehensive patient assessments with PhysioPRISM.</p>
        <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
            <a href="/request-access" class="cta-button" style="display: inline-block; background: white; color: #1a5f5a; padding: 1rem 2.5rem; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 1.1rem;">Request Early Access →</a>
            <a href="/pilot-program" class="cta-button" style="display: inline-block; background: transparent; color: white; border: 2px solid white; padding: 1rem 2.5rem; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 1.1rem;">Explore Pilot Program</a>
        </div>
    </div>

    <div class="related-resources" style="background: #f8f9fa; padding: 2rem; border-radius: 8px; margin-top: 3rem;">
        <h3 style="color: #1a5f5a; margin-bottom: 1rem;">Related Reading</h3>
        <ul>
            <li><a href="/blog/objective-assessment-framework-physiotherapy-complete-guide">Objective Assessment Framework: The Complete Guide</a></li>
            <li><a href="/blog/clinical-reasoning-physiotherapy-complete-2025-guide">Clinical Reasoning in Physiotherapy: The Complete 2025 Guide</a></li>
            <li><a href="/homepage#how-it-works">See the Complete Assessment Workflow in Action</a></li>
            <li><a href="/security">How PhysioPRISM Protects Patient Data</a></li>
            <li><a href="/pilot-program">Join Our 30-Day Clinical Assessment Pilot</a></li>
            <li><a href="/pricing">View Subscription Plans</a></li>
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

.blog-post-content h4 {
    color: #1a5f5a;
    font-size: 1.2rem;
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
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
    display: block;
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

    .features-grid {
        grid-template-columns: 1fr !important;
    }
}
</style>
'''
}

# Add to Cosmos DB
try:
    doc_ref = db.collection('blog_posts').add(blog_post)
    print("\n" + "="*70)
    print("[SUCCESS] Blog post added to Cosmos DB successfully!")
    print("="*70)
    print(f"Document ID: {doc_ref[1].id}")
    print(f"Title: {blog_post['title']}")
    print(f"URL: /blog/{blog_post['slug']}")
    print(f"Status: {blog_post['status']}")
    print(f"Published: {blog_post['published_at']}")
    print("\n" + "-"*70)
    print("View your blog post at:")
    print(f"  Local:      http://localhost:5000/blog/{blog_post['slug']}")
    print(f"  Production: https://physiologicprism.com/blog/{blog_post['slug']}")
    print("\nEdit or manage at:")
    print(f"  Admin:      http://localhost:5000/admin/blog")
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
