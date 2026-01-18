#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add Objective Assessment blog post to Cosmos DB
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
    'title': 'Objective Assessment Framework for Physiotherapists: A Complete Guide (2025)',
    'slug': 'objective-assessment-framework-physiotherapy-complete-guide',
    'excerpt': 'Master the 8-step objective examination framework. Learn functional testing, AROM/PROM interpretation, special test clusters, neurological screening, and ICF-aligned documentation for accurate diagnosis.',
    'meta_description': 'Complete guide to objective assessment in physiotherapy. Learn the 8-step framework including functional testing, ROM assessment, special tests, palpation, and neurological examination.',
    'author': 'Dr. Sandeep',
    'tags': ['objective assessment', 'physical examination', 'functional testing', 'ROM assessment', 'special tests', 'neurological examination', 'ICF framework', 'clinical diagnosis'],
    'category': 'Clinical Practice',
    'featured_image': 'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=1200&q=80',  # Physiotherapy examination
    'status': 'published',
    'published_at': datetime.now(),
    'created_at': datetime.now(),
    'updated_at': datetime.now(),
    'content': '''
<article class="blog-post-content">
    <div class="post-intro">
        <p class="lead">The objective examination is the moment where your clinical reasoning either gains clarity — or falls apart.</p>

        <p>After <a href="/blog/history-taking-physiotherapy-complete-guide-2025">a strong subjective assessment</a>, your next job is to <strong>confirm, challenge, or refine your working hypotheses</strong>. The objective exam is where theory meets reality, where your differential diagnosis gets tested, and where your treatment plan takes shape.</p>

        <p>But many physiotherapists fall into common traps:</p>
        <ul>
            <li>Doing too many tests without clear purpose</li>
            <li>Performing tests in the wrong order</li>
            <li>Over-relying on special tests with poor diagnostic accuracy</li>
            <li>Skipping functional assessment entirely</li>
            <li>Not connecting findings back to the ICF model</li>
            <li>Documenting poorly or inconsistently</li>
        </ul>
    </div>

    <blockquote class="key-insight">
        <p>This guide outlines a clean, repeatable <strong>8-step framework</strong> that ensures you never miss important information and always arrive at a clinically reasoned diagnosis.</p>
    </blockquote>

    <div class="framework-overview" style="background: linear-gradient(135deg, #f8fffe 0%, #e6f7f5 100%); padding: 2rem; border-radius: 12px; margin: 2rem 0;">
        <h3 style="color: #1a5f5a; margin-top: 0;">The 8-Step Objective Assessment Framework</h3>
        <ol style="margin-bottom: 0; padding-left: 1.5rem;">
            <li><strong>Observation</strong> — What you see before touching</li>
            <li><strong>Functional Assessment</strong> — Test real-world movements</li>
            <li><strong>Active Range of Motion (AROM)</strong> — Patient-controlled movement</li>
            <li><strong>Passive Range of Motion (PROM)</strong> — Clinician-controlled movement</li>
            <li><strong>Resisted Tests</strong> — Muscle/tendon integrity</li>
            <li><strong>Palpation</strong> — Confirm, don't explore randomly</li>
            <li><strong>Special Tests</strong> — Use clusters, not single tests</li>
            <li><strong>Neurological Examination</strong> — When indicated</li>
        </ol>
    </div>

    <p>By following this structured sequence, you progress from <strong>general → specific</strong>, reduce cognitive overload, avoid confirmation bias, and build a differential diagnosis grounded in evidence. This framework integrates seamlessly with our <a href="/blog/clinical-reasoning-physiotherapy-complete-2025-guide">clinical reasoning model</a>.</p>

    <div class="cta-box" style="background: linear-gradient(135deg, #f8fffe 0%, #e6f7f5 100%); padding: 2rem; border-radius: 12px; margin: 2rem 0; text-align: center;">
        <h3 style="color: #1a5f5a; margin-bottom: 1rem;">See Structured Assessment in Action</h3>
        <p style="margin-bottom: 1.5rem;">PhysiologicPRISM guides you through complete objective assessments with AI-suggested tests based on your subjective findings.</p>
        <a href="/request-access" class="cta-button" style="display: inline-block; background: #1a5f5a; color: white; padding: 1rem 2rem; border-radius: 8px; text-decoration: none; font-weight: 600;">Try PhysiologicPRISM Free →</a>
    </div>

    <h2>Step 1: Observation — Your Assessment Starts Before You Touch</h2>

    <p>The best clinicians observe everything before speaking or touching the patient.</p>

    <h3>What to Look For</h3>

    <div class="observation-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
        <div class="obs-item" style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0; font-size: 1.1rem;">Posture</h4>
            <p style="margin-bottom: 0; font-size: 0.95rem;">Forward head, rounded shoulders, pelvic tilt, asymmetry</p>
        </div>
        <div class="obs-item" style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0; font-size: 1.1rem;">Muscle Bulk</h4>
            <p style="margin-bottom: 0; font-size: 0.95rem;">Atrophy, hypertrophy, asymmetry between sides</p>
        </div>
        <div class="obs-item" style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0; font-size: 1.1rem;">Swelling</h4>
            <p style="margin-bottom: 0; font-size: 0.95rem;">Joint effusion, soft tissue edema, localized inflammation</p>
        </div>
        <div class="obs-item" style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0; font-size: 1.1rem;">Skin Changes</h4>
            <p style="margin-bottom: 0; font-size: 0.95rem;">Color, temperature, surgical scars, bruising</p>
        </div>
        <div class="obs-item" style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0; font-size: 1.1rem;">Movement Aversion</h4>
            <p style="margin-bottom: 0; font-size: 0.95rem;">Guarding, protective patterns, fear of movement</p>
        </div>
        <div class="obs-item" style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0; font-size: 1.1rem;">Gait</h4>
            <p style="margin-bottom: 0; font-size: 0.95rem;">Antalgic pattern, limping, reduced stride length</p>
        </div>
    </div>

    <div class="clinical-pearl" style="background: #fff3cd; padding: 1.5rem; border-left: 4px solid #ffc107; margin: 2rem 0;">
        <p style="margin-bottom: 0;"><strong>Clinical Pearl:</strong> Observation provides non-verbal clues that often align strongly with mechanism of injury and functional limitation. A patient who guards their shoulder during observation likely has high irritability — adjust your exam intensity accordingly.</p>
    </div>

    <h2>Step 2: Functional Assessment — The Most Clinically Relevant Test</h2>

    <p>This is where you test what actually matters to the patient.</p>

    <p><strong>Ask yourself:</strong> "What function is limited based on their subjective exam?"</p>

    <p>Then <strong>recreate that functional pattern safely</strong>.</p>

    <h3>Examples of Functional Tests</h3>

    <div class="functional-examples" style="background: #f8fffe; padding: 2rem; border-radius: 12px; margin: 2rem 0;">
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background: #1a5f5a; color: white;">
                    <th style="padding: 1rem; text-align: left; border-radius: 8px 0 0 0;">Patient Complaint</th>
                    <th style="padding: 1rem; text-align: left; border-radius: 0 8px 0 0;">Functional Test</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid #e6f7f5;">
                    <td style="padding: 1rem;">Shoulder pain reaching overhead</td>
                    <td style="padding: 1rem;">Overhead reach task (functional arc)</td>
                </tr>
                <tr style="border-bottom: 1px solid #e6f7f5;">
                    <td style="padding: 1rem;">Knee pain with stairs</td>
                    <td style="padding: 1rem;">Step-up/step-down test</td>
                </tr>
                <tr style="border-bottom: 1px solid #e6f7f5;">
                    <td style="padding: 1rem;">Low back pain bending forward</td>
                    <td style="padding: 1rem;">Sit-to-stand, forward bend test</td>
                </tr>
                <tr style="border-bottom: 1px solid #e6f7f5;">
                    <td style="padding: 1rem;">Hip pain with running</td>
                    <td style="padding: 1rem;">Single-leg hop, running gait analysis</td>
                </tr>
                <tr>
                    <td style="padding: 1rem;">Ankle instability</td>
                    <td style="padding: 1rem;">Single-leg balance, lateral hop test</td>
                </tr>
            </tbody>
        </table>
    </div>

    <blockquote>
        <p>Functional testing bridges the gap between <strong>impairment → participation restriction</strong> (ICF framework).</p>
    </blockquote>

    <p>It tells you whether the problem is:</p>
    <ul>
        <li>Movement control</li>
        <li>Pain inhibition</li>
        <li>Strength deficit</li>
        <li>Fear avoidance</li>
        <li>Structural limitation</li>
    </ul>

    <h2>Step 3: Active Range of Motion (AROM)</h2>

    <p>AROM reflects how the patient controls movement under their own neuromuscular system.</p>

    <h3>Key Things to Observe</h3>

    <ul>
        <li><strong>Pain reproduction:</strong> Where in the range does pain occur?</li>
        <li><strong>Pain arc:</strong> Does pain appear mid-range and disappear at end-range?</li>
        <li><strong>Movement quality:</strong> Smooth or jerky? Compensatory patterns?</li>
        <li><strong>Willingness to move:</strong> Does the patient hesitate or guard?</li>
        <li><strong>Symmetry:</strong> Compare left vs right</li>
        <li><strong>Range:</strong> Full, limited, hypermobile?</li>
    </ul>

    <div class="example-box" style="background: #f8f9fa; padding: 1.5rem; border-left: 4px solid #1a5f5a; margin: 1.5rem 0;">
        <h4 style="color: #1a5f5a; margin-top: 0;">Example: Shoulder Abduction AROM</h4>
        <p><strong>Patient:</strong> 52-year-old with suspected rotator cuff pathology</p>
        <p><strong>Observation:</strong> Pain appears at 70° abduction, peaks at 100°, then reduces slightly. Patient uses scapular elevation to compensate.</p>
        <p><strong>Interpretation:</strong> Classic painful arc suggesting subacromial impingement or rotator cuff tendinopathy. Compensation indicates weak rotator cuff control.</p>
    </div>

    <h3>AROM Interpretation Guide</h3>

    <table style="width: 100%; border-collapse: collapse; margin: 1.5rem 0;">
        <thead>
            <tr style="background: #e6f7f5;">
                <th style="padding: 0.75rem; text-align: left; border: 1px solid #d0e7e4;">Finding</th>
                <th style="padding: 0.75rem; text-align: left; border: 1px solid #d0e7e4;">Interpretation</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Full range, no pain</td>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">No active movement restriction</td>
            </tr>
            <tr>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Limited range, painful</td>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Structural or pain-related limitation</td>
            </tr>
            <tr>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Full range with compensation</td>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Motor control deficit or weakness</td>
            </tr>
            <tr>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Painful arc mid-range</td>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Impingement or tendon pathology</td>
            </tr>
            <tr>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">End-range pain only</td>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Capsular tightness or joint restriction</td>
            </tr>
        </tbody>
    </table>

    <h2>Step 4: Passive Range of Motion (PROM)</h2>

    <p>PROM helps distinguish between <strong>contractile vs non-contractile</strong> tissue issues.</p>

    <h3>What PROM Reveals</h3>

    <ul>
        <li><strong>End-feel:</strong> Soft, firm, hard, empty, springy?</li>
        <li><strong>Capsular patterns:</strong> Specific joint limitation patterns</li>
        <li><strong>Joint play:</strong> Accessory movements</li>
        <li><strong>Symptom provocation:</strong> Where does pain occur?</li>
        <li><strong>Comparison to AROM:</strong> Is PROM greater than AROM?</li>
    </ul>

    <div class="clinical-pearl" style="background: #fff3cd; padding: 1.5rem; border-left: 4px solid #ffc107; margin: 2rem 0;">
        <p style="margin-bottom: 0;"><strong>Clinical Pearl:</strong> If PROM > AROM, the problem is likely muscular weakness or motor control. If PROM = AROM and both limited, suspect capsular restriction or joint pathology.</p>
    </div>

    <h3>Capsular Patterns (Key Joints)</h3>

    <table style="width: 100%; border-collapse: collapse; margin: 1.5rem 0;">
        <thead>
            <tr style="background: #1a5f5a; color: white;">
                <th style="padding: 0.75rem; text-align: left;">Joint</th>
                <th style="padding: 0.75rem; text-align: left;">Capsular Pattern</th>
            </tr>
        </thead>
        <tbody>
            <tr style="border-bottom: 1px solid #e6f7f5;">
                <td style="padding: 0.75rem;">Shoulder</td>
                <td style="padding: 0.75rem;">External rotation > Abduction > Internal rotation</td>
            </tr>
            <tr style="border-bottom: 1px solid #e6f7f5;">
                <td style="padding: 0.75rem;">Hip</td>
                <td style="padding: 0.75rem;">Flexion, Internal rotation, Abduction > Extension</td>
            </tr>
            <tr style="border-bottom: 1px solid #e6f7f5;">
                <td style="padding: 0.75rem;">Knee</td>
                <td style="padding: 0.75rem;">Flexion > Extension</td>
            </tr>
            <tr>
                <td style="padding: 0.75rem;">Ankle</td>
                <td style="padding: 0.75rem;">Plantarflexion > Dorsiflexion</td>
            </tr>
        </tbody>
    </table>

    <div class="cta-box" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 12px; margin: 2rem 0; text-align: center; color: white;">
        <h3 style="color: white; margin-bottom: 1rem;">Document ROM Findings Instantly</h3>
        <p style="margin-bottom: 1.5rem;">PhysiologicPRISM auto-organizes your AROM/PROM findings with ICF-aligned interpretation.</p>
        <a href="/pilot-program" class="cta-button" style="display: inline-block; background: white; color: #764ba2; padding: 1rem 2rem; border-radius: 8px; text-decoration: none; font-weight: 600;">Explore Our Pilot Program →</a>
    </div>

    <h2>Step 5: Resisted Tests</h2>

    <p>Resisted tests help clarify if the problem involves contractile tissue (muscle/tendon) or non-contractile structures.</p>

    <h3>Interpretation Triangle</h3>

    <div class="interpretation-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin: 2rem 0;">
        <div style="background: #fff5f5; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #e74c3c;">
            <h4 style="color: #e74c3c; margin-top: 0;">Weak + Painless</h4>
            <p style="margin-bottom: 0;">Likely <strong>neurological issue</strong> (nerve root, peripheral nerve, or complete tendon rupture)</p>
        </div>
        <div style="background: #fffbf0; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #f39c12;">
            <h4 style="color: #d68910; margin-top: 0;">Weak + Painful</h4>
            <p style="margin-bottom: 0;">Likely <strong>muscle or tendon pathology</strong> (strain, tendinopathy, partial tear)</p>
        </div>
        <div style="background: #f0fff4; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #27ae60;">
            <h4 style="color: #27ae60; margin-top: 0;">Strong + Painful</h4>
            <p style="margin-bottom: 0;">Likely <strong>mild tissue irritation</strong> or early-stage tendinopathy</p>
        </div>
    </div>

    <h3>Common Resisted Tests by Region</h3>

    <ul>
        <li><strong>Shoulder:</strong> Resisted abduction, external rotation, internal rotation</li>
        <li><strong>Elbow:</strong> Resisted wrist extension (tennis elbow), wrist flexion (golfer's elbow)</li>
        <li><strong>Hip:</strong> Resisted hip flexion, abduction, external rotation</li>
        <li><strong>Knee:</strong> Resisted knee extension, hamstring contraction</li>
        <li><strong>Ankle:</strong> Resisted plantarflexion, dorsiflexion</li>
    </ul>

    <h2>Step 6: Palpation — Confirm, Don't Explore Randomly</h2>

    <p>Palpation should <strong>confirm your hypotheses</strong>, not replace them.</p>

    <p><strong>Purpose:</strong> To add clarity to findings from observation, functional tests, and ROM assessment.</p>

    <h3>What to Feel For</h3>

    <ul>
        <li><strong>Tenderness:</strong> Specific anatomical structures</li>
        <li><strong>Temperature differences:</strong> Hot = inflammation, cold = reduced circulation</li>
        <li><strong>Tissue texture changes:</strong> Tightness, thickening, nodules</li>
        <li><strong>Swelling:</strong> Joint effusion, soft tissue edema</li>
        <li><strong>Trigger points:</strong> Myofascial pain referral patterns</li>
    </ul>

    <div class="warning-box" style="background: #fff5f5; padding: 1.5rem; border-left: 4px solid #e74c3c; margin: 2rem 0;">
        <p style="margin-bottom: 0;"><strong>Warning:</strong> Avoid relying on palpation alone for diagnosis. Studies show palpation has poor inter-rater reliability for many conditions. Use it as a <em>supportive</em> finding, not a primary diagnostic tool.</p>
    </div>

    <h2>Step 7: Special Tests — Use Clusters, Not Single Tests</h2>

    <p>Most special tests have <strong>limited diagnostic value when used alone</strong>.</p>

    <h3>Best Practice Approach</h3>

    <ol>
        <li><strong>Choose 2–3 tests backed by evidence</strong></li>
        <li><strong>Use test clusters</strong> to increase accuracy</li>
        <li><strong>Consider sensitivity vs specificity</strong>:
            <ul>
                <li>High sensitivity = good for <strong>ruling out</strong> (SnNOut)</li>
                <li>High specificity = good for <strong>ruling in</strong> (SpPIn)</li>
            </ul>
        </li>
        <li><strong>Use tests to confirm clinical reasoning</strong>, not replace it</li>
    </ol>

    <h3>Example: Rotator Cuff Test Cluster</h3>

    <div class="test-cluster" style="background: #f8fffe; padding: 1.5rem; border-radius: 8px; margin: 1.5rem 0;">
        <p><strong>For suspected rotator cuff tear, use this cluster:</strong></p>
        <ul>
            <li>Painful arc (AROM)</li>
            <li>Positive drop arm test</li>
            <li>Weakness in external rotation</li>
        </ul>
        <p><strong>Result:</strong> If all 3 are positive, likelihood of full-thickness tear significantly increases.</p>
    </div>

    <h3>Special Test Selection by Body Region</h3>

    <table style="width: 100%; border-collapse: collapse; margin: 1.5rem 0;">
        <thead>
            <tr style="background: #e6f7f5;">
                <th style="padding: 0.75rem; text-align: left; border: 1px solid #d0e7e4;">Region</th>
                <th style="padding: 0.75rem; text-align: left; border: 1px solid #d0e7e4;">Suspected Pathology</th>
                <th style="padding: 0.75rem; text-align: left; border: 1px solid #d0e7e4;">Evidence-Based Tests</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Shoulder</td>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Rotator cuff tear</td>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Drop arm, Painful arc, External rotation lag</td>
            </tr>
            <tr>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Knee</td>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">ACL tear</td>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Lachman, Pivot shift, Anterior drawer</td>
            </tr>
            <tr>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Ankle</td>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Ankle instability</td>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Anterior drawer, Talar tilt test</td>
            </tr>
            <tr>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Lumbar spine</td>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">Nerve root compression</td>
                <td style="padding: 0.75rem; border: 1px solid #d0e7e4;">SLR, Slump test, Crossed SLR</td>
            </tr>
        </tbody>
    </table>

    <h2>Step 8: Neurological Examination (When Indicated)</h2>

    <p>Not every patient requires a full neurological exam — but it's <strong>essential</strong> when symptoms suggest:</p>

    <ul>
        <li>Radiculopathy (nerve root compression)</li>
        <li>Peripheral nerve involvement</li>
        <li>Cauda equina risk (medical emergency)</li>
        <li>Paresthesia or numbness</li>
        <li>Weakness disproportionate to mechanical findings</li>
    </ul>

    <h3>Components of Neurological Screening</h3>

    <div class="neuro-components" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0; font-size: 1.1rem;">Dermatomes</h4>
            <p style="margin-bottom: 0; font-size: 0.95rem;">Sensory distribution patterns for each nerve root</p>
        </div>
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0; font-size: 1.1rem;">Myotomes</h4>
            <p style="margin-bottom: 0; font-size: 0.95rem;">Motor strength testing for each nerve root</p>
        </div>
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0; font-size: 1.1rem;">Reflexes</h4>
            <p style="margin-bottom: 0; font-size: 0.95rem;">Deep tendon reflexes (biceps, triceps, patellar, Achilles)</p>
        </div>
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0; font-size: 1.1rem;">Neural Tension</h4>
            <p style="margin-bottom: 0; font-size: 0.95rem;">SLR, slump test, upper limb tension tests</p>
        </div>
    </div>

    <div class="warning-box" style="background: #fff5f5; padding: 1.5rem; border-left: 4px solid #e74c3c; margin: 2rem 0;">
        <h4 style="color: #e74c3c; margin-top: 0;">Red Flag: Cauda Equina Syndrome</h4>
        <p>If patient presents with:</p>
        <ul>
            <li>Bilateral leg pain/weakness</li>
            <li>Saddle anesthesia</li>
            <li>Bowel/bladder dysfunction</li>
        </ul>
        <p style="margin-bottom: 0;"><strong>→ Immediate medical referral required.</strong></p>
    </div>

    <h2>How This Framework Improves Clinical Reasoning</h2>

    <p>By following this 8-step sequence, you:</p>

    <ul>
        <li>✓ <strong>Progress from general → specific</strong>, reducing premature closure</li>
        <li>✓ <strong>Reduce cognitive overload</strong> with a clear structure</li>
        <li>✓ <strong>Avoid confirmation bias</strong> by testing multiple hypotheses</li>
        <li>✓ <strong>Build differential diagnoses</strong> grounded in evidence</li>
        <li>✓ <strong>Link impairments to function</strong> using the ICF framework</li>
        <li>✓ <strong>Create defensible documentation</strong> for legal and clinical compliance</li>
    </ul>

    <blockquote>
        <p>This framework aligns with evidence-based physiotherapy standards and is easy to teach to interns, students, and junior clinicians.</p>
    </blockquote>

    <h2>Case Example: Applying the 8-Step Framework</h2>

    <div class="case-study" style="background: linear-gradient(135deg, #f8fffe 0%, #e6f7f5 100%); padding: 2rem; border-radius: 12px; margin: 2rem 0;">
        <h3 style="color: #1a5f5a; margin-top: 0;">Patient: 38-year-old office worker with right shoulder pain</h3>

        <div style="margin-bottom: 1.5rem;">
            <h4 style="color: #2d8b7f;">Step 1: Observation</h4>
            <p>Forward head posture, rounded shoulders, guarding right arm in adduction</p>
        </div>

        <div style="margin-bottom: 1.5rem;">
            <h4 style="color: #2d8b7f;">Step 2: Functional Assessment</h4>
            <p>Pain with overhead reaching (simulating shelf access task)</p>
        </div>

        <div style="margin-bottom: 1.5rem;">
            <h4 style="color: #2d8b7f;">Step 3: AROM</h4>
            <p>Abduction limited to 110°, painful arc 70-110°, compensation via scapular elevation</p>
        </div>

        <div style="margin-bottom: 1.5rem;">
            <h4 style="color: #2d8b7f;">Step 4: PROM</h4>
            <p>Abduction 140° (greater than AROM), end-feel firm but not restricted</p>
        </div>

        <div style="margin-bottom: 1.5rem;">
            <h4 style="color: #2d8b7f;">Step 5: Resisted Tests</h4>
            <p>Resisted abduction: strong but painful. Resisted external rotation: strong but painful</p>
        </div>

        <div style="margin-bottom: 1.5rem;">
            <h4 style="color: #2d8b7f;">Step 6: Palpation</h4>
            <p>Tenderness over supraspinatus insertion, no swelling</p>
        </div>

        <div style="margin-bottom: 1.5rem;">
            <h4 style="color: #2d8b7f;">Step 7: Special Tests</h4>
            <p>Painful arc test: positive. Hawkins-Kennedy: positive. Drop arm: negative</p>
        </div>

        <div style="margin-bottom: 1.5rem;">
            <h4 style="color: #2d8b7f;">Step 8: Neurological Screen</h4>
            <p>C5-C6 dermatomes/myotomes intact, reflexes normal</p>
        </div>

        <div style="background: white; padding: 1.5rem; border-radius: 8px; margin-top: 1.5rem;">
            <h4 style="color: #1a5f5a; margin-top: 0;">Clinical Impression</h4>
            <p style="margin-bottom: 0;"><strong>Subacromial pain syndrome / Rotator cuff tendinopathy</strong><br>
            Contributing factors: Poor posture, repetitive overhead movements, motor control deficits in scapular stabilizers</p>
        </div>
    </div>

    <h2>How PhysiologicPRISM Supports Objective Assessment</h2>

    <p>PhysiologicPRISM enhances each stage of your objective exam through AI-guided assistance:</p>

    <div class="features-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin: 2rem 0;">
        <div class="feature-card" style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0;">Smart Test Suggestions</h4>
            <p style="margin-bottom: 0;">AI suggests relevant functional tests and special test clusters based on your subjective findings</p>
        </div>
        <div class="feature-card" style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0;">ICF-Aligned Documentation</h4>
            <p style="margin-bottom: 0;">Automatically organizes findings into ICF domains for comprehensive reporting</p>
        </div>
        <div class="feature-card" style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0;">Structured ROM Recording</h4>
            <p style="margin-bottom: 0;">Simple interface for documenting AROM/PROM with automatic interpretation</p>
        </div>
        <div class="feature-card" style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0;">Differential Diagnosis Support</h4>
            <p style="margin-bottom: 0;">AI helps organize findings to support or refute working hypotheses</p>
        </div>
        <div class="feature-card" style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0;">Instant PDF Reports</h4>
            <p style="margin-bottom: 0;">Generate structured, professional assessment reports in seconds</p>
        </div>
        <div class="feature-card" style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1a5f5a;">
            <h4 style="color: #1a5f5a; margin-top: 0;">Evidence-Based Guidance</h4>
            <p style="margin-bottom: 0;">Access to evidence-informed test clusters and interpretation frameworks</p>
        </div>
    </div>

    <blockquote>
        <p>PhysiologicPRISM turns your objective exam from a time-consuming process into a <strong>structured, efficient, evidence-based workflow</strong>. <a href="/homepage#how-it-works" style="color: #1a5f5a; text-decoration: underline;">See how it works in practice</a>.</p>
    </blockquote>

    <h2>Key Takeaways</h2>

    <ul>
        <li>A strong objective assessment follows a logical sequence: general → specific</li>
        <li>Functional testing is the most clinically relevant component</li>
        <li>AROM vs PROM comparison reveals motor control vs structural issues</li>
        <li>Use special test clusters, not single tests, for better accuracy</li>
        <li>Palpation confirms hypotheses; it doesn't create them</li>
        <li>Neurological screening is essential when symptoms suggest nerve involvement</li>
        <li>ICF framework links impairments to activity and participation restrictions</li>
        <li>Structured documentation protects you legally and clinically</li>
    </ul>

    <hr style="margin: 3rem 0; border: none; border-top: 2px solid #e6f7f5;">

    <h2>Conclusion</h2>

    <p>A strong objective assessment is not about performing more tests — it's about performing the <strong>right tests, in the right order, for the right clinical question</strong>.</p>

    <p>This 8-step framework provides the structure you need to conduct thorough, efficient, and defensible examinations that directly inform your treatment planning.</p>

    <p>When combined with structured subjective examination and clinical reasoning, this approach elevates your diagnostic accuracy, builds patient confidence, and ensures you never miss critical findings.</p>

    <blockquote class="conclusion-quote" style="font-size: 1.2rem; text-align: center; padding: 2rem; background: #f8fffe; border-left: 4px solid #1a5f5a; margin: 2rem 0;">
        <p><strong>Master this framework.<br>
        Your accuracy and confidence will elevate immediately.<br>
        Your patients will feel the difference.</strong></p>
    </blockquote>

    <div class="cta-box" style="background: linear-gradient(135deg, #1a5f5a 0%, #2d8b7f 100%); padding: 3rem; border-radius: 12px; margin: 3rem 0; text-align: center; color: white;">
        <h3 style="color: white; margin-bottom: 1rem; font-size: 1.8rem;">Ready to Structure Your Objective Assessments?</h3>
        <p style="margin-bottom: 2rem; font-size: 1.1rem;">Join physiotherapists using PhysiologicPRISM for complete, efficient, evidence-based examinations.</p>
        <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
            <a href="/request-access" class="cta-button" style="display: inline-block; background: white; color: #1a5f5a; padding: 1rem 2.5rem; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 1.1rem;">Request Early Access →</a>
            <a href="/pilot-program" class="cta-button" style="display: inline-block; background: transparent; color: white; border: 2px solid white; padding: 1rem 2.5rem; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 1.1rem;">Explore Pilot Program</a>
        </div>
    </div>

    <div class="related-resources" style="background: #f8f9fa; padding: 2rem; border-radius: 8px; margin-top: 3rem;">
        <h3 style="color: #1a5f5a; margin-bottom: 1rem;">Continue Your Learning</h3>
        <ul>
            <li><a href="/blog/history-taking-physiotherapy-complete-guide-2025">History Taking in Physiotherapy: The Complete 2025 Guide</a></li>
            <li><a href="/blog/clinical-reasoning-physiotherapy-complete-2025-guide">Clinical Reasoning in Physiotherapy: The Complete 2025 Guide</a></li>
            <li><a href="/homepage#how-it-works">See the Complete Assessment Workflow Walkthrough</a></li>
            <li><a href="/security">Learn About Our Security & Compliance Standards</a></li>
            <li><a href="/pilot-program">Join Our Clinical Assessment Pilot Program</a></li>
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

.blog-post-content table {
    font-size: 0.95rem;
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

    .features-grid, .observation-grid, .neuro-components, .interpretation-grid {
        grid-template-columns: 1fr !important;
    }

    .blog-post-content table {
        font-size: 0.85rem;
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
