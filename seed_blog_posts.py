"""
Seed Blog Posts to Cosmos DB
This script populates the blog_posts collection with initial content.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from azure_cosmos_db import get_cosmos_db

# Load environment variables
load_dotenv()

def seed_blog_posts():
    """Seed the database with initial blog posts"""

    try:
        db = get_cosmos_db()

        # Check if posts already exist
        print("Checking for existing blog posts...")
        existing_posts_query = db.collection('blog_posts').where('status', '==', 'published').limit(1)
        existing_posts = list(existing_posts_query.stream())

        if len(existing_posts) > 0:
            print(f"[WARNING] Blog posts already exist ({len(existing_posts)} found).")
            response = input("Do you want to continue and add more posts? (y/n): ")
            if response.lower() != 'y':
                print("Aborted.")
                return

        # Define initial blog posts
        blog_posts = [
            {
                'title': 'Clinical Reasoning Framework for Physiotherapists',
                'slug': 'clinical-reasoning-framework',
                'content': '''
# Clinical Reasoning Framework for Physiotherapists

Clinical reasoning is the foundation of effective physiotherapy practice. It's the cognitive process that enables physiotherapists to make sound clinical decisions based on patient assessment, evidence, and clinical experience.

## What is Clinical Reasoning?

Clinical reasoning in physiotherapy involves:
- Gathering and analyzing patient data
- Identifying patterns and relationships
- Formulating hypotheses about the patient's condition
- Making evidence-based treatment decisions
- Evaluating outcomes and adjusting interventions

## Key Components

### 1. Subjective Assessment
The subjective examination provides crucial insights into the patient's perspective, including their chief complaint, history, and functional limitations.

### 2. Objective Assessment
Physical examination findings, measurements, and functional tests provide objective data to support clinical hypotheses.

### 3. Clinical Hypothesis Generation
Based on subjective and objective findings, physiotherapists generate hypotheses about:
- Pathophysiology
- Contributing factors
- Prognosis
- Treatment approaches

### 4. Treatment Planning
Evidence-based interventions are selected based on:
- Clinical reasoning
- Patient preferences
- Best available evidence
- Clinical expertise

## The PRISM Approach

PhysiologicPRISM supports clinical reasoning through:
- **Structured documentation** that guides systematic assessment
- **AI-assisted suggestions** based on clinical patterns
- **Evidence integration** linking assessment to treatment
- **Outcome tracking** to evaluate clinical decisions

## Conclusion

Strong clinical reasoning skills develop over time through practice, reflection, and continuous learning. PhysiologicPRISM is designed to support this process by providing structure and evidence-based guidance.
                ''',
                'excerpt': 'Learn about the clinical reasoning process in physiotherapy and how structured documentation supports better clinical decision-making.',
                'author': 'Dr. Sandeep Rao',
                'tags': ['Clinical Reasoning', 'Evidence-Based Practice', 'Assessment'],
                'status': 'published',
                'meta_description': 'Clinical reasoning framework for physiotherapists - learn how to make better clinical decisions through structured assessment and evidence-based practice.',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'published_at': datetime.now().isoformat(),
                'views': 0
            },
            {
                'title': 'Comprehensive History Taking in Physiotherapy',
                'slug': 'history-taking-physiotherapy',
                'content': '''
# Comprehensive History Taking in Physiotherapy

A thorough patient history is the cornerstone of effective physiotherapy assessment and treatment planning.

## Why History Taking Matters

The subjective examination often provides 80% of the information needed for diagnosis. It helps physiotherapists:
- Understand the patient's presenting complaint
- Identify red flags and contraindications
- Establish treatment goals
- Build therapeutic rapport

## Key Elements of History Taking

### 1. Chief Complaint
- What brought the patient to physiotherapy?
- Current symptoms and their impact on function
- Patient's primary concerns and goals

### 2. History of Present Complaint
- Onset and mechanism of injury
- Progression of symptoms
- Aggravating and easing factors
- Previous treatments and their outcomes
- 24-hour symptom behavior

### 3. Past Medical History
- Previous injuries or surgeries
- Chronic conditions
- Medications
- Relevant family history

### 4. Functional Impact
- Activities of daily living
- Work-related tasks
- Recreational activities
- Sleep quality

### 5. Red Flags
- Serious pathology indicators
- Systemic symptoms
- Progressive neurological deficits
- Contraindications to treatment

## Documentation Best Practices

PhysiologicPRISM structures history taking to ensure:
- **Completeness**: No critical information is missed
- **Consistency**: Standardized approach across patients
- **Efficiency**: AI-assisted documentation reduces time
- **Evidence**: Digital records support clinical reasoning

## Conclusion

Mastering history taking is essential for every physiotherapist. Structured documentation tools like PhysiologicPRISM help ensure comprehensive, consistent patient assessment.
                ''',
                'excerpt': 'Master the art of patient history taking with this comprehensive guide for physiotherapists.',
                'author': 'Dr. Sandeep Rao',
                'tags': ['Assessment', 'Patient History', 'Documentation'],
                'status': 'published',
                'meta_description': 'Learn comprehensive history taking techniques for physiotherapy practice - structured approach to patient assessment and documentation.',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'published_at': datetime.now().isoformat(),
                'views': 0
            },
            {
                'title': 'Objective Assessment Guide for Physiotherapists',
                'slug': 'objective-assessment-guide',
                'content': '''
# Objective Assessment Guide for Physiotherapists

The objective assessment is where theoretical knowledge meets practical clinical skills, providing measurable data to support clinical decision-making.

## Purpose of Objective Assessment

Objective assessment serves to:
- Validate or refute hypotheses from the subjective examination
- Establish baseline measurements
- Identify impairments and functional limitations
- Guide treatment planning
- Track progress over time

## Key Components

### 1. Observation
Visual assessment provides immediate clinical information:
- Posture and alignment
- Gait pattern
- Movement quality
- Skin condition
- Swelling or deformity

### 2. Palpation
Manual examination reveals:
- Tissue temperature and texture
- Muscle tone and tenderness
- Joint position and alignment
- Areas of sensitivity

### 3. Range of Motion Testing
Assessment of movement includes:
- Active range of motion (patient-performed)
- Passive range of motion (therapist-performed)
- End-feel characteristics
- Pain patterns during movement

### 4. Strength Testing
Manual muscle testing or dynamometry assesses:
- Muscle strength
- Endurance
- Power
- Functional capacity

### 5. Special Tests
Condition-specific tests help:
- Confirm or rule out diagnoses
- Assess tissue integrity
- Identify specific impairments
- Guide treatment selection

### 6. Functional Testing
Real-world performance measures:
- Activities of daily living
- Work-specific tasks
- Sport-specific movements
- Balance and coordination

## Documentation Best Practices

Effective objective assessment documentation should:
- Use standardized measurements
- Record specific findings
- Note asymmetries and abnormalities
- Include patient responses
- Link findings to functional impact

## The PRISM Advantage

PhysiologicPRISM enhances objective assessment through:
- Standardized assessment templates
- Built-in measurement tools
- Automated progress tracking
- AI-assisted pattern recognition
- Evidence-based clinical suggestions

## Conclusion

Thorough objective assessment is essential for evidence-based physiotherapy practice. Systematic documentation ensures nothing is missed and creates a strong foundation for treatment planning.
                ''',
                'excerpt': 'A comprehensive guide to conducting systematic objective assessments in physiotherapy practice.',
                'author': 'Dr. Sandeep Rao',
                'tags': ['Assessment', 'Objective Examination', 'Clinical Skills'],
                'status': 'published',
                'meta_description': 'Master objective assessment techniques in physiotherapy - systematic approach to physical examination and functional testing.',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'published_at': datetime.now().isoformat(),
                'views': 0
            },
            {
                'title': 'Evidence-Based Treatment Planning in Physiotherapy',
                'slug': 'evidence-based-treatment-planning',
                'content': '''
# Evidence-Based Treatment Planning in Physiotherapy

Creating effective treatment plans requires integration of clinical evidence, patient preferences, and clinical expertise.

## The Evidence-Based Practice Model

Evidence-based practice combines three essential elements:

### 1. Best Research Evidence
- Systematic reviews and meta-analyses
- Randomized controlled trials
- Clinical practice guidelines
- Outcome studies

### 2. Clinical Expertise
- Professional experience
- Clinical reasoning skills
- Pattern recognition
- Practical wisdom

### 3. Patient Values and Preferences
- Individual goals
- Personal circumstances
- Cultural considerations
- Treatment preferences

## Treatment Planning Process

### Step 1: Problem Identification
Based on assessment findings:
- Primary impairments
- Functional limitations
- Activity restrictions
- Participation barriers

### Step 2: Goal Setting
SMART goals should be:
- Specific
- Measurable
- Achievable
- Relevant
- Time-bound

### Step 3: Intervention Selection
Choose interventions based on:
- Evidence of effectiveness
- Patient suitability
- Available resources
- Therapist competence

### Step 4: Implementation
Effective delivery includes:
- Clear instructions
- Appropriate progression
- Patient education
- Home exercise programs

### Step 5: Outcome Measurement
Track progress using:
- Standardized outcome measures
- Functional assessments
- Patient-reported outcomes
- Objective measurements

## Common Treatment Approaches

### Manual Therapy
- Joint mobilization
- Soft tissue techniques
- Manipulation
- Myofascial release

### Exercise Therapy
- Strengthening exercises
- Flexibility training
- Motor control exercises
- Functional training

### Electrophysical Agents
- Therapeutic ultrasound
- Electrical stimulation
- Laser therapy
- Shockwave therapy

### Education and Advice
- Pain neuroscience education
- Activity modification
- Ergonomic advice
- Self-management strategies

## Documentation and Review

Regular documentation should include:
- Treatment provided
- Patient response
- Progress toward goals
- Plan modifications

## The PRISM Approach

PhysiologicPRISM supports evidence-based practice through:
- Treatment templates based on clinical guidelines
- AI-suggested interventions from latest evidence
- Progress tracking and outcome measurement
- Integration of assessment and treatment planning

## Conclusion

Evidence-based treatment planning ensures optimal patient outcomes by combining the best available evidence with clinical expertise and patient preferences.
                ''',
                'excerpt': 'Learn how to create effective, evidence-based treatment plans that integrate research, clinical expertise, and patient preferences.',
                'author': 'Dr. Sandeep Rao',
                'tags': ['Treatment Planning', 'Evidence-Based Practice', 'Clinical Guidelines'],
                'status': 'published',
                'meta_description': 'Evidence-based treatment planning in physiotherapy - integrate research evidence, clinical expertise, and patient preferences for optimal outcomes.',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'published_at': datetime.now().isoformat(),
                'views': 0
            },
            {
                'title': 'Digital Documentation Best Practices for Physiotherapists',
                'slug': 'digital-documentation-best-practices',
                'content': '''
# Digital Documentation Best Practices for Physiotherapists

Effective documentation is essential for quality patient care, legal protection, and professional communication.

## Why Documentation Matters

Good clinical documentation:
- Supports continuity of care
- Provides legal protection
- Facilitates communication
- Enables outcome tracking
- Supports reimbursement
- Contributes to research

## Core Documentation Principles

### 1. Accuracy
Record exactly what you observe and do:
- Objective findings
- Patient statements (use quotes)
- Interventions provided
- Patient responses

### 2. Completeness
Include all relevant information:
- Subjective complaints
- Objective findings
- Assessment and diagnosis
- Plan of care

### 3. Timeliness
Document promptly:
- Same-day documentation
- Real-time notes when possible
- Immediate recording of critical findings

### 4. Clarity
Write clearly and professionally:
- Use standard terminology
- Avoid ambiguous statements
- Define abbreviations
- Organize logically

### 5. Confidentiality
Protect patient information:
- HIPAA compliance
- Secure storage
- Limited access
- Privacy safeguards

## SOAP Note Format

### Subjective
- Chief complaint
- Symptom description
- Patient's perspective
- Relevant history

### Objective
- Observation findings
- Measurement results
- Test outcomes
- Clinical findings

### Assessment
- Clinical impression
- Progress evaluation
- Problem list
- Prognosis

### Plan
- Treatment interventions
- Goals and objectives
- Patient education
- Follow-up schedule

## Digital Documentation Advantages

Modern EMR systems offer:
- Faster documentation
- Better legibility
- Enhanced accessibility
- Automated tracking
- Data analytics
- Integration capabilities

## Common Documentation Pitfalls

Avoid these mistakes:
- Incomplete records
- Delayed documentation
- Copy-paste errors
- Vague descriptions
- Missing signatures
- Inconsistent formats

## HIPAA Compliance

Ensure you:
- Use secure systems
- Protect passwords
- Limit access
- Encrypt data
- Audit access logs
- Train staff

## The PRISM Solution

PhysiologicPRISM enhances documentation through:
- Structured templates
- AI-assisted note generation
- Automated progress tracking
- HIPAA-compliant cloud storage
- Mobile accessibility
- Integrated outcome measures

## Best Practice Checklist

✓ Document same day
✓ Use standardized formats
✓ Include all SOAP components
✓ Record objective measurements
✓ Note patient education provided
✓ Document informed consent
✓ Review and sign notes
✓ Back up data regularly

## Conclusion

Excellent documentation is a cornerstone of professional physiotherapy practice. Digital tools like PhysiologicPRISM make it easier to maintain high-quality records while saving time.
                ''',
                'excerpt': 'Essential guide to digital documentation for physiotherapists - best practices for accurate, complete, and HIPAA-compliant clinical records.',
                'author': 'Dr. Sandeep Rao',
                'tags': ['Documentation', 'HIPAA', 'Best Practices', 'EMR'],
                'status': 'published',
                'meta_description': 'Digital documentation best practices for physiotherapists - learn how to create accurate, complete, and HIPAA-compliant clinical records.',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'published_at': datetime.now().isoformat(),
                'views': 0
            }
        ]

        # Insert blog posts
        print(f"\nInserting {len(blog_posts)} blog posts...")
        blog_collection = db.collection('blog_posts')

        for i, post in enumerate(blog_posts, 1):
            try:
                doc_ref = blog_collection.add(post)
                print(f"[OK] [{i}/{len(blog_posts)}] Added: {post['title']}")
            except Exception as e:
                print(f"[FAIL] [{i}/{len(blog_posts)}] Failed to add '{post['title']}': {e}")

        print(f"\n[SUCCESS] Successfully seeded {len(blog_posts)} blog posts!")
        print(f"\nYou can now view them at: /blog")

    except Exception as e:
        print(f"\n[ERROR] Error seeding blog posts: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 60)
    print("BLOG POSTS SEEDING SCRIPT")
    print("=" * 60)
    seed_blog_posts()
