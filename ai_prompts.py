"""
Centralized AI Prompts for PhysiologicPRISM
============================================

IMPROVED VERSION - More specific clinical reasoning outputs

All production AI prompts live here and are used by BOTH:

- main.py (web app)
- mobile_api_ai.py (mobile API)

Design goals:
- Crisp, clinically useful outputs (no waffle, no teaching paragraphs).
- Strong physiotherapy clinical reasoning and ICF alignment.
- Stable, predictable formats (numbered lists, short statements).
- De-identified by design: never invent names, dates, addresses, or IDs.
- SPECIFIC clinical guidance tied to the exact case presentation
"""

from typing import Dict, Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
# COMMON PROMPT COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_ROLES = {
    "clinical_reasoning": (
        "You are a physiotherapy clinical reasoning assistant. "
        "You receive de-identified patient information and generate concise, "
        "clinically useful outputs only."
    ),
    "clinical_specialist": (
        "You are a senior physiotherapist providing evidence-based clinical reasoning support. "
        "You focus on clear, practical reasoning for THIS individual case."
    ),
    "decision_support": (
        "You are a physiotherapy clinical decision-support assistant. "
        "You give focused, actionable suggestions only."
    ),
    "icf_specialist": (
        "You are a physiotherapy clinical reasoning assistant specializing in ICF-based assessment "
        "of body structures, functions, activities, participation, and contextual factors."
    ),
    "biopsychosocial": (
        "You are a physiotherapy assistant specializing in patient-centred, biopsychosocial assessment "
        "using the ICF framework and Common Sense Model."
    ),
}

AGE_APPROPRIATE_GUIDANCE = (
    "Always ensure suggestions are age-appropriate:\n"
    "- Children/adolescents: consider growth, development, sport overuse.\n"
    "- Adults: consider acute/mechanical and occupation/sport demands.\n"
    "- Older adults: consider degenerative change, comorbidities, fall risk."
)

ICF_FRAMEWORK_GUIDE = (
    "ICF components to consider:\n"
    "- Body Structures: Anatomical regions involved\n"
    "- Body Functions: Pain, ROM, strength, sensory, motor control\n"
    "- Activity Limitations (capacity vs performance)\n"
    "- Participation Restrictions\n"
    "- Environmental Factors\n"
    "- Personal Factors"
)

# ─────────────────────────────────────────────────────────────────────────────
# ICF CORE SETS - Evidence-based categories for common conditions
# ─────────────────────────────────────────────────────────────────────────────

ICF_CORE_SETS = {
    'shoulder': {
        'name': 'Shoulder Conditions',
        'body_structures': ['shoulder joint (s72001)', 'shoulder region (s7200)', 'ligaments and tendons of shoulder (s73020)'],
        'body_functions': ['sensation of pain (b280)', 'mobility of shoulder joint (b7100)', 'muscle power (b730)', 'sleep (b134)'],
        'activities': ['lifting and carrying (d430)', 'reaching (d4452)', 'dressing (d540)', 'washing oneself (d510)'],
        'participation': ['work/employment (d850)', 'recreation and leisure (d920)', 'community life (d910)']
    },
    'lumbar': {
        'name': 'Low Back Pain',
        'body_structures': ['vertebral column (s7600)', 'spinal cord and nerves (s12001)', 'muscles of trunk (s73010)'],
        'body_functions': ['sensation of pain (b280)', 'mobility of spine (b7101)', 'muscle endurance (b740)', 'sleep (b134)'],
        'activities': ['lifting and carrying (d430)', 'bending (d4105)', 'walking (d450)', 'standing (d4154)', 'sitting (d4153)'],
        'participation': ['work/employment (d850)', 'housework (d640)', 'family relationships (d760)']
    },
    'cervical': {
        'name': 'Neck Pain',
        'body_structures': ['cervical vertebral column (s76001)', 'neck muscles (s73011)'],
        'body_functions': ['sensation of pain (b280)', 'mobility of cervical spine (b7101)', 'muscle power (b730)'],
        'activities': ['looking (d110)', 'driving (d4751)', 'reading (d166)', 'computer work (d1701)'],
        'participation': ['work/employment (d850)', 'recreation (d920)']
    },
    'knee': {
        'name': 'Knee Conditions',
        'body_structures': ['knee joint (s75001)', 'ligaments of knee (s75021)', 'meniscus (s75011)'],
        'body_functions': ['sensation of pain (b280)', 'mobility of knee joint (b7102)', 'muscle power (b730)', 'gait pattern (b770)'],
        'activities': ['walking (d450)', 'climbing stairs (d4551)', 'squatting/kneeling (d4105)', 'running (d4552)'],
        'participation': ['work/employment (d850)', 'sports (d9201)', 'community mobility (d460)']
    },
    'hip': {
        'name': 'Hip Conditions',
        'body_structures': ['hip joint (s75002)', 'pelvic region (s7500)'],
        'body_functions': ['sensation of pain (b280)', 'mobility of hip joint (b7102)', 'gait pattern (b770)'],
        'activities': ['walking (d450)', 'climbing stairs (d4551)', 'putting on footwear (d5401)', 'sexual activities (d7702)'],
        'participation': ['work/employment (d850)', 'housework (d640)', 'recreation (d920)']
    },
    'ankle': {
        'name': 'Ankle/Foot Conditions',
        'body_structures': ['ankle joint (s75003)', 'foot structure (s7502)'],
        'body_functions': ['sensation of pain (b280)', 'mobility of ankle (b7103)', 'muscle power (b730)', 'gait pattern (b770)'],
        'activities': ['walking (d450)', 'running (d4552)', 'standing (d4154)', 'using transportation (d470)'],
        'participation': ['work/employment (d850)', 'sports (d9201)', 'community life (d910)']
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# INTRA-FORM ADAPTIVE AI - Analyze existing inputs to guide suggestions
# ─────────────────────────────────────────────────────────────────────────────

def analyze_objective_findings(inputs: Dict[str, str]) -> Dict[str, Any]:
    """
    Analyze existing objective assessment inputs to detect which areas have been tested
    and whether findings are normal (clear) or abnormal (pathology detected).

    This enables INTRA-FORM ADAPTIVE AI - suggestions adapt based on what's already filled
    on the SAME form, not just previous screens.

    Clinical Logic:
    - If proximal joint tested and clear → Tone down proximal suggestions, focus elsewhere
    - If palpation shows tenderness → Dig deeper with related special tests
    - If all MSK clear → Prioritize neural assessment

    Conservative Approach:
    - When unclear, classify as 'tested' rather than 'clear' or 'abnormal'
    - Always include brief mentions of other areas even when cleared
    - Err on side of comprehensiveness

    Args:
        inputs: Dict of current form field values {field_name: field_value}

    Returns:
        Dict containing:
        {
            'proximal_status': 'clear' | 'abnormal' | 'untested',
            'distal_status': 'clear' | 'abnormal' | 'untested',
            'local_status': 'clear' | 'abnormal' | 'untested',
            'neural_status': 'clear' | 'abnormal' | 'untested',
            'palpation_status': 'clear' | 'abnormal' | 'untested',
            'special_tests_status': 'clear' | 'abnormal' | 'untested',
            'abnormal_areas': ['biceps tendon', 'lateral epicondyle'],
            'clear_areas': ['shoulder', 'elbow ROM'],
            'tested_fields': ['proximal_joint', 'palpation'],
            'untested_fields': ['distal_joint', 'neurological'],
            'priority_focus': 'local' | 'proximal' | 'distal' | 'neural' | 'complete_assessment',
            'has_findings': True/False
        }
    """
    # Keywords for classifying findings (conservative - broad matching)
    CLEAR_KEYWORDS = [
        'full rom', 'pain-free', 'pain free', 'painfree', 'negative', 'normal',
        '5/5', 'no pain', 'no tenderness', 'no swelling', 'no restriction',
        'intact', 'within normal limits', 'wnl', 'unremarkable',
        'full range', 'complete rom', 'symmetrical', 'non-tender',
        'no abnormality', 'no deficit', 'clear'
    ]

    ABNORMAL_KEYWORDS = [
        'limited', 'reduced', 'painful', 'pain on', 'pain with', 'positive',
        'weak', 'weakness', 'tenderness', 'tender', 'swelling', 'swollen',
        'restricted', 'restriction', 'instability', 'unstable', 'reduced strength',
        'guarding', 'spasm', 'trigger point', 'decreased', 'diminished',
        'clicking', 'crepitus', 'catching', 'locking', 'giving way',
        'unable to', 'difficulty', 'asymmetry', 'deformity'
    ]

    # Initialize analysis result
    analysis = {
        'proximal_status': 'untested',
        'distal_status': 'untested',
        'local_status': 'untested',
        'neural_status': 'untested',
        'palpation_status': 'untested',
        'special_tests_status': 'untested',
        'abnormal_areas': [],
        'clear_areas': [],
        'tested_fields': [],
        'untested_fields': [],
        'priority_focus': 'complete_assessment',
        'has_findings': False
    }

    if not inputs:
        return analysis

    # Helper function to classify a field value
    def classify_finding(value: str) -> str:
        """Returns 'clear', 'abnormal', or 'tested' (unclear)"""
        if not value or len(value.strip()) < 3:
            return 'untested'

        value_lower = value.lower()

        # Check for clear indicators (need stronger evidence for "clear" due to conservative approach)
        clear_matches = sum(1 for keyword in CLEAR_KEYWORDS if keyword in value_lower)
        abnormal_matches = sum(1 for keyword in ABNORMAL_KEYWORDS if keyword in value_lower)

        # Conservative: if ANY abnormal keywords, classify as abnormal
        if abnormal_matches > 0:
            return 'abnormal'

        # Conservative: need MULTIPLE clear keywords or very specific ones to classify as clear
        if clear_matches >= 2 or any(keyword in value_lower for keyword in ['pain-free', 'pain free', 'full rom', 'negative', '5/5']):
            return 'clear'

        # Uncertain - just mark as tested
        return 'tested'

    # Analyze each field
    for field_name, field_value in inputs.items():
        if not field_value or len(str(field_value).strip()) < 3:
            analysis['untested_fields'].append(field_name)
            continue

        analysis['tested_fields'].append(field_name)
        field_status = classify_finding(str(field_value))

        # Map field names to anatomical categories
        field_lower = field_name.lower()

        # Proximal joint assessment
        if 'proximal' in field_lower:
            if field_status == 'clear':
                analysis['proximal_status'] = 'clear'
                analysis['clear_areas'].append('proximal joint')
            elif field_status == 'abnormal':
                analysis['proximal_status'] = 'abnormal'
                analysis['abnormal_areas'].append('proximal joint')
                analysis['has_findings'] = True
            else:
                analysis['proximal_status'] = 'tested'

        # Distal joint assessment
        elif 'distal' in field_lower:
            if field_status == 'clear':
                analysis['distal_status'] = 'clear'
                analysis['clear_areas'].append('distal joint')
            elif field_status == 'abnormal':
                analysis['distal_status'] = 'abnormal'
                analysis['abnormal_areas'].append('distal joint')
                analysis['has_findings'] = True
            else:
                analysis['distal_status'] = 'tested'

        # Local/primary joint assessment
        elif 'local' in field_lower or 'primary' in field_lower or 'main' in field_lower:
            if field_status == 'clear':
                analysis['local_status'] = 'clear'
                analysis['clear_areas'].append('local joint')
            elif field_status == 'abnormal':
                analysis['local_status'] = 'abnormal'
                analysis['abnormal_areas'].append('local joint')
                analysis['has_findings'] = True
            else:
                analysis['local_status'] = 'tested'

        # Neurological assessment
        elif 'neuro' in field_lower or 'neural' in field_lower or 'nerve' in field_lower:
            if field_status == 'clear':
                analysis['neural_status'] = 'clear'
                analysis['clear_areas'].append('neurological')
            elif field_status == 'abnormal':
                analysis['neural_status'] = 'abnormal'
                analysis['abnormal_areas'].append('neurological')
                analysis['has_findings'] = True
            else:
                analysis['neural_status'] = 'tested'

        # Palpation
        elif 'palpat' in field_lower:
            if field_status == 'clear':
                analysis['palpation_status'] = 'clear'
                analysis['clear_areas'].append('palpation')
            elif field_status == 'abnormal':
                analysis['palpation_status'] = 'abnormal'
                analysis['abnormal_areas'].append('palpation findings')
                analysis['has_findings'] = True
            else:
                analysis['palpation_status'] = 'tested'

        # Special tests
        elif 'special' in field_lower or 'test' in field_lower:
            if field_status == 'clear':
                analysis['special_tests_status'] = 'clear'
                analysis['clear_areas'].append('special tests')
            elif field_status == 'abnormal':
                analysis['special_tests_status'] = 'abnormal'
                analysis['abnormal_areas'].append('special tests')
                analysis['has_findings'] = True
            else:
                analysis['special_tests_status'] = 'tested'

    # Determine priority focus based on findings
    if analysis['abnormal_areas']:
        # Focus on first abnormal area found
        if 'proximal' in str(analysis['abnormal_areas']):
            analysis['priority_focus'] = 'proximal'
        elif 'local' in str(analysis['abnormal_areas']):
            analysis['priority_focus'] = 'local'
        elif 'distal' in str(analysis['abnormal_areas']):
            analysis['priority_focus'] = 'distal'
        elif 'palpation' in str(analysis['abnormal_areas']):
            analysis['priority_focus'] = 'local'  # Palpation findings suggest local pathology
        else:
            analysis['priority_focus'] = 'investigate_abnormality'
    elif analysis['proximal_status'] == 'clear' and analysis['distal_status'] == 'clear' and analysis['local_status'] == 'clear':
        # All MSK areas clear - prioritize neural assessment
        analysis['priority_focus'] = 'neural'
    elif 'untested' in [analysis['proximal_status'], analysis['distal_status']]:
        # Still have major areas untested
        analysis['priority_focus'] = 'complete_assessment'
    else:
        # Some areas tested, continue comprehensive assessment
        analysis['priority_focus'] = 'complete_assessment'

    return analysis


def detect_body_region(presenting_complaint: str) -> Optional[str]:
    """
    Detect the primary body region from the presenting complaint.

    Args:
        presenting_complaint: Patient's chief complaint text

    Returns:
        str: Body region key (e.g., 'shoulder', 'lumbar', 'knee') or None
    """
    if not presenting_complaint:
        return None

    complaint_lower = presenting_complaint.lower()

    # Region detection keywords (order matters - more specific first)
    region_keywords = {
        'shoulder': ['shoulder', 'rotator cuff', 'subacromial', 'glenohumeral', 'scapula'],
        'lumbar': ['low back', 'lower back', 'lumbar', 'l4', 'l5', 's1', 'lumbosacral', 'sciatica'],
        'cervical': ['neck', 'cervical', 'c5', 'c6', 'c7', 'whiplash'],
        'knee': ['knee', 'patella', 'meniscus', 'acl', 'pcl', 'mcl', 'lcl', 'tibiofemoral'],
        'hip': ['hip', 'groin', 'trochanter', 'femoroacetabular'],
        'ankle': ['ankle', 'foot', 'achilles', 'plantar', 'heel']
    }

    for region, keywords in region_keywords.items():
        if any(keyword in complaint_lower for keyword in keywords):
            return region

    return None


# Brief per-field guidance for subjective exam
SUBJECTIVE_FIELD_GUIDANCE: Dict[str, str] = {
    "body_structure": (
        "Clarify anatomical region, involved tissues, and structural irritability "
        "(e.g. joint, tendon, muscle, nerve)."
    ),
    "body_function": (
        "Explore pain behaviour, movement-related symptoms, strength, endurance, and sensorimotor changes."
    ),
    "activity_performance": (
        "Ask about what the patient ACTUALLY does in their routine daily life and normal environment. "
        "Focus on real-world functional limitations in their usual settings (home, work, community). "
        "Examples: difficulty with stairs at home, struggles with household chores, limitations during usual work tasks, "
        "reduced participation in regular social/leisure activities."
    ),
    "activity_capacity": (
        "Ask about what the patient CAN potentially do in ideal, standardized conditions (CAPACITY), "
        "not what they actually do in daily life (performance) or underlying body functions. "
        "Focus on their highest achievable level of activity-based functioning without real-world barriers. "
        "Examples: maximum walking distance on flat surface without obstacles, best stair climbing ability in controlled setting, "
        "optimal lifting capacity in ideal conditions, highest sustainable activity level they could achieve clinically."
    ),
    "contextual_environmental": (
        "Ask about physical environment, workplace setup, aids, social support, and environmental barriers."
    ),
    "contextual_personal": (
        "Ask about occupation, hobbies, lifestyle activities, fitness routines, personal habits (smoking, sleep, diet, exercise), "
        "and daily routines. Focus on WHAT ACTIVITIES the patient does personally, not their beliefs or feelings."
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _format_dict_block(title: str, data: Optional[Dict[str, Any]]) -> str:
    """Turn a dict into a titled bullet block, skipping empty values."""
    if not data:
        return ""
    lines = []
    for key, value in data.items():
        if isinstance(value, str):
            v = value.strip()
            if not v:
                continue
        if value:
            label = key.replace("_", " ").title()
            lines.append(f"- {label}: {value}")
    if not lines:
        return ""
    return f"{title}:\n" + "\n".join(lines) + "\n"


def build_patient_profile(age_sex: str, present: str = "", past: str = "") -> str:
    """Standardized patient profile section."""
    profile_lines = ["PATIENT PROFILE (DE-IDENTIFIED):"]
    profile_lines.append(f"- Age/Sex: {age_sex or 'Not specified'}")
    if present:
        profile_lines.append(f"- Presenting Complaint: {present}")
    if past:
        profile_lines.append(f"- Relevant History: {past}")
    return "\n".join(profile_lines)


def build_clinical_context(
    age_sex: str = "",
    present: str = "",
    past: str = "",
    subjective: Optional[Dict[str, Any]] = None,
    perspectives: Optional[Dict[str, Any]] = None,
    assessments: Optional[Dict[str, Any]] = None,
    diagnosis: Optional[str] = None,
    goals: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Standardized multi-section clinical context used by many prompts.
    Only includes sections that have non-empty content.
    """
    parts = []

    if age_sex or present or past:
        parts.append(build_patient_profile(age_sex, present, past))

    subj_block = _format_dict_block("Subjective Findings", subjective)
    if subj_block:
        parts.append(subj_block.strip())

    persp_block = _format_dict_block("Patient Perspectives", perspectives)
    if persp_block:
        parts.append(persp_block.strip())

    assess_block = _format_dict_block("Assessment / Examination Findings", assessments)
    if assess_block:
        parts.append(assess_block.strip())

    if diagnosis:
        parts.append(f"Current Working Diagnosis / Impression:\n- {diagnosis}")

    goals_block = _format_dict_block("SMART Goals", goals)
    if goals_block:
        parts.append(goals_block.strip())

    return "\n\n".join(p for p in parts if p).strip()


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY TAKING PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

def get_past_questions_prompt(age_sex: str, present_hist: str) -> str:
    """
    Generate targeted past medical history questions.

    Endpoint: /api/ai_suggestion/past_questions
    """
    return f"""{SYSTEM_ROLES['clinical_reasoning']}

{build_patient_profile(age_sex, present_hist)}

TASK:
Generate EXACTLY 5 concise, targeted past history questions that a physiotherapist should ask NOW.

MANDATORY RULES:
1. Questions must be specific to this patient's probable body region and mechanism implied by the presenting complaint.
2. Cover: previous similar episodes, major medical/surgical history, medications, red-flag conditions, and relevant lifestyle factors.
3. Do NOT give explanations, teaching paragraphs, or differential diagnoses.
4. Do NOT ask about names, dates of birth, addresses, or any identifiers.
5. Open-ended or focused yes/no follow-up questions are both allowed if clinically appropriate.

OUTPUT:
- A numbered list, questions 1–5, one question per line, no extra text.
"""


# ─────────────────────────────────────────────────────────────────────────────
# SUBJECTIVE EXAMINATION PROMPTS (ICF) - IMPROVED VERSION
# ─────────────────────────────────────────────────────────────────────────────

def get_subjective_field_prompt(
    field: str,
    age_sex: str,
    present_hist: str,
    past_hist: str,
    existing_inputs: Dict[str, Any],
    patho_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    IMPROVED: Provides BOTH questions AND clinical reasoning guidance specific to the ICF component.
    This gives the physiotherapist actionable direction rather than just generic questions.
    Uses ICF Core Sets for evidence-based, condition-specific guidance.

    NEW: Includes pathophysiological mechanism context to guide examination approach based on
    pain mechanism, severity, and irritability. This helps identify contraindications early.
    """

    icf_names = {
        'impairment_body_structure': 'Body Structures',
        'impairment_body_function': 'Body Functions',
        'activity_limitation_performance': 'Activity Performance',
        'activity_limitation_capacity': 'Activity Capacity',
        'contextual_environmental': 'Environmental Factors',
        'contextual_personal': 'Personal Factors'
    }
    component = icf_names.get(field, field.replace('_', ' ').title())

    existing = "\n".join(
        f"- {k.replace('_',' ').title()}: {v}"
        for k, v in existing_inputs.items()
        if v and k != field
    )

    # Detect body region and get ICF Core Set
    body_region = detect_body_region(present_hist)
    icf_core_set = ICF_CORE_SETS.get(body_region) if body_region else None

    # Build ICF Core Set guidance if available
    icf_core_guidance = ""
    if icf_core_set:
        icf_core_guidance = f"\n\nICF CORE SET FOR {icf_core_set['name'].upper()}:\n"

        # Map field to relevant ICF Core Set category
        field_to_icf_category = {
            'impairment_body_structure': 'body_structures',
            'impairment_body_function': 'body_functions',
            'activity_limitation_performance': 'activities',
            'activity_limitation_capacity': 'activities',
        }

        icf_category = field_to_icf_category.get(field)
        if icf_category and icf_category in icf_core_set:
            relevant_categories = icf_core_set[icf_category]
            icf_core_guidance += f"Evidence-based {component} categories for this condition:\n"
            for category in relevant_categories:
                icf_core_guidance += f"  • {category}\n"
            icf_core_guidance += "\nIMPORTANT: Focus your questions on these evidence-based categories.\n"

    # Field-specific clinical reasoning templates - STRICT ICF BOUNDARIES
    field_specific_guidance = {
        'impairment_body_structure': """
For BODY STRUCTURES ONLY - You are assessing anatomical structures:
INCLUDE ONLY:
- Specific tissues (bones, joints, ligaments, tendons, muscles, nerves, bursa)
- Location/depth of structural involvement (deep vs superficial, medial vs lateral)
- Structural integrity (swelling, deformity, instability, alignment)
- Anatomical irritability (which specific structure hurts)

DO NOT INCLUDE (these belong in OTHER fields):
- Movement or function questions (e.g., "Can you lift your arm?" = Body Function)
- Activity questions (e.g., "Can you dress yourself?" = Activity)
- Participation questions (e.g., "Can you go to work?" = Participation)
- Pain behavior or ROM (= Body Function)

Provide 2-3 questions about STRUCTURES ONLY and 2-3 clinical reasoning points about which anatomical tissues are involved.""",

        'impairment_body_function': """
For BODY FUNCTIONS ONLY - You are assessing physiological functions:
INCLUDE ONLY:
- Pain behavior (constant/intermittent, sharp/ache, at rest/with movement)
- Range of motion and end-feel
- Strength, power, endurance
- Sensory function (numbness, tingling, altered sensation)
- Motor control and coordination

DO NOT INCLUDE (these belong in OTHER fields):
- Anatomical structures alone (e.g., "Which tendon hurts?" = Body Structure)
- Functional tasks (e.g., "Can you walk to the shops?" = Activity Performance)
- Work or social roles (e.g., "Can you do your job?" = Participation)

Provide 2-3 questions about FUNCTIONS ONLY and 2-3 clinical reasoning points about physiological impairments.""",

        'activity_limitation_performance': """
For ACTIVITY PERFORMANCE ONLY - You are assessing what they DO in real life:
INCLUDE ONLY:
- Real-world functional tasks (dressing, bathing, walking to car, cooking)
- Actual performance in their environment (work duties, household chores)
- Difficulty level and compensatory strategies used
- What they actually do vs avoid

DO NOT INCLUDE (these belong in OTHER fields):
- Isolated joint movements (e.g., "How much can you flex your shoulder?" = Body Function)
- Anatomical questions (e.g., "Which muscle is weak?" = Body Structure)
- Work/social roles (e.g., "Can you be a parent?" = Participation)
- Capacity in ideal conditions (= Activity Capacity)

Provide 2-3 questions about ACTUAL PERFORMANCE ONLY and 2-3 clinical reasoning points about real-world task limitations.""",

        'activity_limitation_capacity': """
For ACTIVITY CAPACITY ONLY - You are assessing what they CAN do in ideal conditions:
INCLUDE ONLY:
- Maximum ACTIVITY-BASED ability in controlled/optimal settings (e.g., walking distance, stair climbing, lifting tasks)
- Measurable activity thresholds without real-world barriers (distance, time, repetitions for functional tasks)
- Best-case FUNCTIONAL performance in standardized clinical environment
- Capacity vs performance gap for activities (NOT body functions)

DO NOT INCLUDE (these belong in OTHER fields):
- What they actually do at home (= Activity Performance)
- Isolated body functions like joint ROM, muscle strength tests, or reflexes (= Body Function)
- Work or social participation (= Participation)

Focus on ACTIVITIES the patient can perform at their maximum potential, not underlying body functions or structures.

Provide 2-3 questions about ACTIVITY CAPACITY ONLY and 2-3 clinical reasoning points about maximum functional ability in ideal conditions.""",

        'contextual_environmental': """
For ENVIRONMENTAL FACTORS ONLY - You are assessing external world barriers/facilitators:
INCLUDE ONLY:
- Physical environment (stairs, surfaces, lighting, temperature)
- Equipment and technology (aids, braces, assistive devices)
- Work/home setup (ergonomics, accessibility)
- Social support and attitudes of others

DO NOT INCLUDE (these belong in OTHER fields):
- Personal beliefs or motivation (= Personal Factors)
- Actual task performance (= Activity Performance)
- Social roles (= Participation)

Provide 2-3 questions about ENVIRONMENT ONLY and 2-3 clinical reasoning points about external barriers/facilitators.""",

        'contextual_personal': """
For PERSONAL FACTORS ONLY - You are assessing personal activities and lifestyle characteristics:
INCLUDE ONLY:
- Occupation and work-related activities
- Hobbies, sports, and recreational activities
- Fitness routines and physical activity level
- Personal habits affecting health (smoking, alcohol, sleep patterns, diet, exercise habits)
- Daily lifestyle routines and personal schedules

DO NOT INCLUDE (these belong in OTHER fields):
- Beliefs, expectations, illness perceptions (= Patient Perspectives screen)
- Coping strategies, psychological state, motivation (= Patient Perspectives screen)
- Physical environment or support (= Environmental Factors)
- Task performance limitations (= Activity Performance)
- Social roles (= Participation)

Focus on WHAT ACTIVITIES the patient engages in personally, NOT their feelings, beliefs, or psychological state.

Provide 2-3 questions about PERSONAL ACTIVITIES/LIFESTYLE ONLY and 2-3 clinical reasoning points about how personal activities may relate to their condition."""
    }

    specific_guidance = field_specific_guidance.get(field, "")

    # NEW: Add pathophysiological mechanism context (helps identify contraindications)
    patho_context = ""
    if patho_data:
        pain_mechanism = patho_data.get('possible_source', '')
        pain_type = patho_data.get('pain_type', '')
        pain_severity = patho_data.get('pain_severity', '')
        pain_irritability = patho_data.get('pain_irritability', '')
        healing_stage = patho_data.get('stage_healing', '')

        if any([pain_mechanism, pain_type, pain_severity, pain_irritability]):
            patho_context = "\n\nPAIN MECHANISM & CONTRAINDICATION CONSIDERATIONS:\n"
            if pain_mechanism:
                patho_context += f"- Pain Source: {pain_mechanism}\n"
            if pain_type:
                patho_context += f"- Pain Type: {pain_type}\n"
            if pain_severity:
                patho_context += f"- Pain Severity (VAS): {pain_severity}/10\n"
            if pain_irritability:
                patho_context += f"- Pain Irritability: {pain_irritability}\n"
            if healing_stage:
                patho_context += f"- Tissue Healing Stage: {healing_stage}\n"
            patho_context += "\nIMPORTANT: Consider contraindications based on pain mechanism and irritability when suggesting examination approaches.\n"

    return f"""
{SYSTEM_ROLES['icf_specialist']}

PATIENT SNAPSHOT
- Age/Sex: {age_sex}
- Presenting complaint: {present_hist}
- Relevant past history: {past_hist}

OTHER SUBJECTIVE FINDINGS ALREADY GATHERED
{existing if existing else 'None recorded yet.'}
{patho_context}

TARGET ICF COMPONENT: {component}
{icf_core_guidance}
{specific_guidance}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 REGIONAL ASSESSMENT CONSIDERATION (If Relevant)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**NOTE: Consider Adjacent Regions Where Clinically Relevant**

During subjective examination, it may be appropriate to briefly ask about adjacent regions:

- **Shoulder pain** → Brief question about neck symptoms (referred pain)
- **Elbow pain** → Brief question about shoulder or neck symptoms
- **Hip pain** → Brief question about lumbar spine symptoms
- **Knee pain** → Brief question about hip or ankle symptoms

**APPLICATION:**
- If the presenting complaint suggests possible referred pain or kinetic chain involvement
- Include 1 brief clarifying question about proximal/distal region if clinically relevant
- DO NOT force this if not applicable
- This should be SUBTLE - don't derail the ICF component focus

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL: STAY WITHIN THE ICF FIELD "{component}"

STRICT RULES FOR YOUR RESPONSE:
1) ICF FIELD BOUNDARY ENFORCEMENT (MOST IMPORTANT)
   - You are ONLY assessing: {component}
   - Read the "INCLUDE ONLY" section above carefully
   - Read the "DO NOT INCLUDE" section above carefully
   - If a question belongs to a different ICF field, DO NOT include it
   - Every question must be directly relevant to {component} ONLY

2) ANATOMICAL SPECIFICITY
   - Always use the EXACT body region and side from the presenting complaint (e.g. "right shoulder", "lumbar spine", "left knee")
   - NEVER use placeholders like "the affected area" or "your condition"
   - Be specific to the case (e.g., for shoulder pain mention specific movements like "overhead reach")

3) CASE-SPECIFIC CLINICAL REASONING
   - Reference the patient's specific complaint
   - Connect to likely pathoanatomy for THIS case
   - Consider age-appropriate factors
   - Avoid generic textbook answers

4) TWO-PART OUTPUT REQUIRED:

   PART 1 - KEY QUESTIONS (2-3 questions):
   Questions that will clarify THIS SPECIFIC ICF component ({component}) for THIS case.
   Every question must be strictly within {component} boundaries.

   PART 2 - CLINICAL REASONING POINTS (2-3 brief points):
   What to look for, what tissues/functions are likely involved, what this tells you about the case.
   All reasoning must relate to {component} ONLY.

5) FORMAT (STRICT):
   Questions:
   1. [Specific question for {component} only]
   2. [Specific question for {component} only]

   Clinical Reasoning:
   - [Brief reasoning point about {component} specific to this case]
   - [Brief reasoning point about {component} specific to this case]

6) WHAT TO AVOID:
   - Questions from other ICF fields (check DO NOT INCLUDE section)
   - Generic rehabilitation advice or exercises
   - Teaching paragraphs
   - Asking about patient identifiers
   - Vague or non-specific language

OUTPUT (Follow this format exactly):
"""


def get_subjective_diagnosis_prompt(
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective_inputs: Dict[str, Any],
) -> str:
    """
    Generate provisional diagnoses based on subjective examination alone.

    Endpoint: /api/ai_suggestion/subjective_diagnosis
    """
    profile = build_patient_profile(age_sex, present_hist, past_hist)
    subj_block = _format_dict_block("Subjective Findings", subjective_inputs)

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{profile}

{subj_block}

TASK:
Based ONLY on the subjective data above, generate the TOP 3 most likely provisional diagnoses.

MANDATORY RULES:
1. Use specific diagnostic terminology (e.g., "subacromial impingement syndrome" not "shoulder pain").
2. Order by likelihood (most likely first).
3. Each diagnosis must be 1 brief sentence explaining why it fits this case.
4. Do NOT recommend objective tests yet (that comes next).
5. Do NOT suggest treatment.

OUTPUT FORMAT:
1. [Diagnosis] - [Brief justification based on subjective findings]
2. [Diagnosis] - [Brief justification]
3. [Diagnosis] - [Brief justification]
"""


# ─────────────────────────────────────────────────────────────────────────────
# PATIENT PERSPECTIVES (CSM)
# ─────────────────────────────────────────────────────────────────────────────

def get_patient_perspectives_field_prompt(
    field: str,
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective_inputs: Optional[Dict[str, Any]] = None,
    existing_perspectives: Optional[Dict[str, Any]] = None,
    patho_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    FIELD-SPECIFIC patient perspectives prompts based on Common Sense Model (CSM).
    Provides targeted questions and clinical reasoning for each perspective component.

    NEW: Includes pathophysiological mechanism context to tailor perspective questions
    to pain type and mechanism (e.g., neurogenic vs somatic pain affects expectations).

    Endpoint: /api/ai_suggestion/perspectives/<field>
    """

    # Field names mapping to readable labels
    field_names = {
        'knowledge': 'Knowledge of the Illness (Illness Identity)',
        'attribution': 'Illness Attribution (Perceived Cause)',
        'expectation': 'Expectation About Illness (Timeline)',
        'consequences_awareness': 'Awareness of Consequences',
        'locus_of_control': 'Locus of Control',
        'affective_aspect': 'Affective Aspect (Emotional Response)'
    }
    component = field_names.get(field, field.replace('_', ' ').title())

    # Build existing perspectives context
    existing = ""
    if existing_perspectives:
        existing = "\n".join(
            f"- {k.replace('_',' ').title()}: {v}"
            for k, v in existing_perspectives.items()
            if v and k != field
        )

    # Field-specific clinical reasoning templates for each CSM component
    field_specific_guidance = {
        'knowledge': """
For KNOWLEDGE OF THE ILLNESS (Illness Identity) - Understanding their mental model of the condition:

WHAT THIS CSM COMPONENT ASSESSES:
- Specific labels/diagnostic terms they use (medical vs lay language)
- Their mental model of tissue pathology or dysfunction
- Understanding of structural vs functional problems
- Accuracy of their illness representation

INCLUDE ONLY - Ask about their conceptual understanding:
- What specific words/terms do they use? (e.g., "torn muscle", "pinched nerve", "wear and tear", "arthritis")
- Do they view it as structural damage, tissue injury, or functional problem?
- What explanation were they given by healthcare providers, online sources, or others?
- Are they using catastrophic language suggesting serious pathology?
- Do they understand the difference between hurt and harm?

DO NOT INCLUDE (these belong in OTHER fields):
- What caused it (= Illness Attribution)
- How long they think it will last (= Expectation/Timeline)
- How serious they think it is (= Consequences Awareness)
- How they feel about it emotionally (= Affective Aspect)

CLINICAL REASONING FOCUS - Consider impact on treatment:
- Catastrophic labels ("degeneration", "bone-on-bone", "slipped disc") drive fear-avoidance and predict poor outcomes
- Structural damage beliefs increase perceived threat and reduce self-efficacy
- Misalignment with modern pain science creates barriers to active treatment
- Health literacy level determines education approach needed
- Correcting misconceptions early improves engagement and outcomes

Provide 2-3 targeted questions exploring their illness representation and 2-3 reasoning points about therapeutic implications.""",

        'attribution': """
For ILLNESS ATTRIBUTION (Perceived Cause) - Understanding causal beliefs and attribution style:

WHAT THIS CSM COMPONENT ASSESSES:
- Causal attribution model (monocausal vs multicausal)
- Attribution style (biomechanical, psychosocial, behavioral, multifactorial)
- Self-blame vs external blame patterns
- Alignment with biopsychosocial model

INCLUDE ONLY - Explore their causal model:
- Do they identify a single cause (e.g., "I lifted wrong") or multiple contributing factors?
- Is attribution purely structural/mechanical (e.g., "my disc moved") or do they recognize behavioral/psychological factors?
- Do they blame themselves, bad luck, work demands, past injury, or aging?
- Can they identify modifiable vs non-modifiable factors?
- Are they attributing pain to inevitable tissue damage or viewing it as a modifiable experience?

DO NOT INCLUDE (these belong in OTHER fields):
- What they call the condition (= Knowledge)
- How long recovery will take (= Expectation/Timeline)
- How serious it is (= Consequences Awareness)
- Their emotional response (= Affective Aspect)

CLINICAL REASONING FOCUS - Therapeutic target identification:
- Monocausal attributions (e.g., "it's just my posture") oversimplify and limit treatment engagement with multifactorial approaches
- Purely structural attributions increase fear-avoidance and reduce activity participation
- Self-blame increases distress; reframe toward controllable contributing factors
- External/fatalistic attribution (e.g., "it's just aging") reduces self-efficacy and active engagement
- Recognizing multiple modifiable factors (sleep, stress, movement patterns, beliefs) enables targeted intervention

Provide 2-3 specific questions assessing their causal attribution model and 2-3 reasoning points about treatment implications.""",

        'expectation': """
For EXPECTATION ABOUT ILLNESS (Timeline) - Understanding temporal beliefs and recovery expectations:

WHAT THIS CSM COMPONENT ASSESSES:
- Specific recovery timeline expectations (days, weeks, months, permanent)
- Trajectory beliefs (linear improvement vs fluctuating vs plateauing)
- Acute vs chronic illness perception
- Prognostic certainty vs uncertainty

INCLUDE ONLY - Explore their temporal model:
- What specific timeframe do they expect for recovery? (e.g., "better in 2 weeks" vs "this is permanent")
- Do they expect linear steady improvement, ups and downs, or no change?
- Are they viewing this as acute and resolvable or chronic and manageable?
- How certain or uncertain are they about the prognosis?
- Are their timeline expectations realistic for this condition/presentation?
- Do past experiences with similar conditions shape their current timeline beliefs?

DO NOT INCLUDE (these belong in OTHER fields):
- What they think is wrong (= Knowledge)
- What caused it (= Attribution)
- How serious the consequences are (= Consequences Awareness)
- Their feelings about it (= Affective Aspect)

CLINICAL REASONING FOCUS - Manage expectations proactively:
- Unrealistically short timelines ("should be gone in days") predict disappointment, perceived treatment failure, and disengagement
- Chronic/permanent beliefs in acute conditions become self-fulfilling prophecies and impair recovery
- Excessive prognostic uncertainty increases anxiety and catastrophizing
- Mismatch between patient timeline and evidence-based prognosis creates adherence barriers
- Acknowledging normal fluctuation patterns prevents crisis response to setbacks

Provide 2-3 specific questions about recovery timeline expectations and 2-3 reasoning points about managing temporal beliefs.""",

        'consequences_awareness': """
For AWARENESS OF CONSEQUENCES - Understanding perceived threat level and life impact:

WHAT THIS CSM COMPONENT ASSESSES:
- Perceived severity and threat level (minor annoyance to life-threatening)
- Awareness of functional consequences (activity and participation impact)
- Catastrophizing vs minimizing cognitive patterns
- Short-term vs long-term consequence understanding

INCLUDE ONLY - Assess their threat appraisal:
- On a scale from "minor nuisance" to "serious threat", where do they place this condition?
- What specific life domains do they believe will be affected? (work capacity, family roles, independence, identity)
- Are they catastrophizing worst-case scenarios? (e.g., "I'll end up in a wheelchair", "I'll lose my job", "I'll never be the same")
- Are they minimizing or dismissing potential consequences? (e.g., "it's nothing, I'll just push through")
- Do they understand the difference between temporary limitations and permanent disability?
- Are they aware of secondary consequences of inactivity/avoidance?

DO NOT INCLUDE (these belong in OTHER fields):
- What they call it (= Knowledge)
- What caused it (= Attribution)
- How long it will last (= Expectation)
- Their emotional response (= Affective Aspect)
- Whether they can control it (= Locus of Control)

CLINICAL REASONING FOCUS - Identify catastrophizing or minimization:
- Catastrophizing consequences (especially regarding participation/identity threats) is the strongest predictor of chronic disability and poor outcomes
- Minimization prevents engagement with treatment and leads to delayed recovery or re-injury
- Overstated threat perception drives protective behaviors (guarding, avoidance, hypervigilance)
- Balanced awareness (realistic acknowledgment without catastrophizing) optimizes motivation and engagement
- Consequence beliefs directly inform goal-setting priorities and treatment buy-in

Provide 2-3 targeted questions exploring perceived severity and life impact, and 2-3 reasoning points about catastrophizing or minimization patterns.""",

        'locus_of_control': """
For LOCUS OF CONTROL - Understanding perceived agency and self-efficacy:

WHAT THIS CSM COMPONENT ASSESSES:
- Internal locus (self-directed, active agency) vs External locus (passive, dependent on others/fate)
- Self-efficacy beliefs about influencing symptoms and recovery
- Active participant vs passive recipient role
- Controllability beliefs and learned helplessness

INCLUDE ONLY - Determine their control beliefs:
- Do they believe THEY can influence their recovery through their own actions?
- What specific things do they think THEY can do to improve? (vs waiting for external fixes)
- Are they relying primarily on healthcare professionals, medications, or injections to "fix" them?
- Do they see recovery as dependent on their own behavior change or external interventions?
- Are they expressing learned helplessness? (e.g., "nothing helps", "I've tried everything")
- Do they believe pain/symptoms are something they can modulate or completely outside their control?

DO NOT INCLUDE (these belong in OTHER fields):
- What the condition is (= Knowledge)
- What caused it (= Attribution)
- How long it will last (= Expectation)
- How serious it is (= Consequences)
- How they feel emotionally (= Affective Aspect)

CLINICAL REASONING FOCUS - Build self-efficacy and agency:
- Internal locus of control is one of the strongest predictors of successful rehabilitation outcomes and adherence
- External locus (passive recipient mentality) predicts poor engagement, non-adherence, and dependence on passive treatments
- Learned helplessness from repeated failed treatments requires graded mastery experiences to rebuild self-efficacy
- Pain neuroscience education can shift locus from "something wrong with my body" to "I can influence my nervous system"
- Cultural and socioeconomic factors may shape control beliefs; some cultures emphasize external authority/expertise

Provide 2-3 specific questions assessing their sense of agency and controllability, and 2-3 reasoning points about building internal locus.""",

        'affective_aspect': """
For AFFECTIVE ASPECT (Emotional Response) - Understanding dominant emotional responses and psychological distress:

WHAT THIS CSM COMPONENT ASSESSES:
- Primary emotional response patterns (fear, anxiety, anger, sadness, frustration, hopelessness, acceptance)
- Emotional intensity and distress level
- Fear-avoidance and kinesiophobia indicators
- Emotional regulation and coping capacity

INCLUDE ONLY - Identify emotional responses to the condition:
- What is their dominant emotional response when they think about this condition? (fear, worry, anger, sadness, frustration)
- Are they expressing fear of movement or re-injury (kinesiophobia)?
- Are there signs of anxiety or catastrophizing? (excessive worry, worst-case thinking)
- Are they expressing hopelessness, helplessness, or low mood related to the condition?
- Is there anger or frustration—at themselves, healthcare system, or circumstances?
- Are they showing acceptance and adjustment, or struggling emotionally?
- How intense is the emotional distress (mild irritation to severe distress affecting function)?

DO NOT INCLUDE (these belong in OTHER fields):
- What they think is wrong (= Knowledge)
- What caused it (= Attribution)
- How long it will last (= Expectation)
- How serious it is (= Consequences)
- Whether they can control it (= Locus of Control)

CLINICAL REASONING FOCUS - Identify yellow flags and emotional barriers:
- Fear-avoidance beliefs (fear of movement/re-injury) are the strongest predictor of transition from acute to chronic disability
- Kinesiophobia drives protective behaviors (guarding, avoidance) that perpetuate dysfunction
- Anxiety and catastrophizing amplify pain perception via central sensitization mechanisms
- Depression and hopelessness reduce treatment engagement, adherence, and self-management
- Anger/frustration may indicate unmet expectations, lack of validation, or perceived injustice—requires acknowledgment and reframing
- Acceptance and psychological flexibility predict better outcomes than emotional suppression or struggle
- Yellow flag identification (distress, catastrophizing, hopelessness) triggers biopsychosocial approach

Provide 2-3 specific questions identifying emotional responses and distress patterns, and 2-3 reasoning points about emotional barriers and yellow flags."""
    }

    specific_guidance = field_specific_guidance.get(field, "")

    # NEW: Add pathophysiological mechanism context (helps tailor perspective questions)
    patho_context = ""
    if patho_data:
        pain_mechanism = patho_data.get('possible_source', '')
        pain_type = patho_data.get('pain_type', '')
        pain_severity = patho_data.get('pain_severity', '')
        pain_irritability = patho_data.get('pain_irritability', '')

        if any([pain_mechanism, pain_type, pain_severity]):
            patho_context = "\n\nPAIN MECHANISM CONTEXT:\n"
            if pain_mechanism:
                patho_context += f"- Pain Source: {pain_mechanism}\n"
            if pain_type:
                patho_context += f"- Pain Type: {pain_type}\n"
            if pain_severity:
                patho_context += f"- Pain Severity (VAS): {pain_severity}/10\n"
            if pain_irritability:
                patho_context += f"- Pain Irritability: {pain_irritability}\n"
            patho_context += "\nNOTE: Tailor perspective questions to pain mechanism (e.g., neurogenic pain may affect timeline expectations differently than acute somatic pain).\n"

    return f"""
{SYSTEM_ROLES['biopsychosocial']}

PATIENT SNAPSHOT
- Age/Sex: {age_sex}
- Presenting complaint: {present_hist}
- Relevant past history: {past_hist}

SUBJECTIVE FINDINGS ALREADY GATHERED
{_format_dict_block("Subjective", subjective_inputs) if subjective_inputs else 'None recorded yet.'}

OTHER PATIENT PERSPECTIVES ALREADY GATHERED
{existing if existing else 'None recorded yet.'}
{patho_context}

TARGET CSM COMPONENT: {component}

{specific_guidance}

CRITICAL: STAY WITHIN THE CSM FIELD "{component}"

STRICT RULES FOR YOUR RESPONSE:
1) CSM FIELD BOUNDARY ENFORCEMENT (MOST IMPORTANT)
   - You are ONLY assessing: {component}
   - Read the "INCLUDE ONLY" section above carefully
   - Read the "DO NOT INCLUDE" section above carefully
   - If a question belongs to a different CSM field, DO NOT include it
   - Every question must be directly relevant to {component} ONLY

2) CASE-SPECIFIC AND CONVERSATIONAL
   - Use the patient's specific complaint (e.g., "your right shoulder pain", "your low back problem")
   - NEVER use placeholders like "the condition" or "your problem" - be specific
   - Use natural, conversational language (not academic jargon)
   - Open-ended questions that encourage elaboration

3) CLINICAL REASONING ALIGNMENT
   - Connect to Common Sense Model theory
   - Consider how this perspective component affects outcomes
   - Identify therapeutic implications
   - Consider age and context

4) TWO-PART OUTPUT REQUIRED:

   PART 1 - KEY QUESTIONS (2-3 questions):
   Conversational, open-ended questions that explore THIS SPECIFIC CSM component ({component}) for THIS case.
   Every question must be strictly within {component} boundaries.

   PART 2 - CLINICAL REASONING POINTS (2-3 brief points):
   What this perspective tells you, therapeutic implications, and how it affects treatment planning.
   All reasoning must relate to {component} ONLY.

5) FORMAT (STRICT):
   Questions:
   1. [Conversational question for {component} only]
   2. [Conversational question for {component} only]

   Clinical Reasoning:
   - [Brief reasoning point about {component} specific to this case]
   - [Brief reasoning point about {component} specific to this case]

6) WHAT TO AVOID:
   - Questions from other CSM fields (check DO NOT INCLUDE section)
   - Academic or jargon-heavy language
   - Closed yes/no questions (unless for specific clarification)
   - Treatment recommendations or advice
   - Generic textbook questions not tied to this case

OUTPUT (Follow this format exactly):
"""


def get_patient_perspectives_prompt(
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective_inputs: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate Common Sense Model questions for patient perspectives.

    Endpoint: /api/ai_suggestion/patient_perspectives
    NOTE: This is a LEGACY/GENERIC function. Prefer get_patient_perspectives_field_prompt() for field-specific guidance.
    """
    context = build_clinical_context(age_sex, present_hist, past_hist, subjective=subjective_inputs)

    return f"""{SYSTEM_ROLES['biopsychosocial']}

{context}

TASK:
Generate EXACTLY 3 targeted Common Sense Model (CSM) questions to explore this patient's illness perceptions.

CSM DOMAINS (choose most relevant):
- Identity: What do they think is wrong?
- Cause: What do they believe caused it?
- Timeline: How long do they think it will last?
- Consequences: How serious do they perceive it?
- Control/Cure: Do they believe it's controllable or curable?

MANDATORY RULES:
1. Questions must be relevant to THIS case and the presenting complaint.
2. Use conversational language, not academic jargon.
3. Open-ended questions only.
4. Do NOT give explanations or teaching content.

OUTPUT:
- Numbered list 1–3, one question per line.
"""


# ─────────────────────────────────────────────────────────────────────────────
# ASSESSMENT & DIAGNOSIS
# ─────────────────────────────────────────────────────────────────────────────

def get_provisional_diagnosis_prompt(
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective_inputs: Optional[Dict[str, Any]] = None,
    patient_perspectives: Optional[Dict[str, Any]] = None,
    assessments: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate comprehensive provisional diagnosis after assessment.

    Endpoint: /api/ai_suggestion/provisional_diagnosis
    """
    context = build_clinical_context(
        age_sex, present_hist, past_hist,
        subjective=subjective_inputs,
        perspectives=patient_perspectives,
        assessments=assessments
    )

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{context}

TASK:
Generate a comprehensive provisional diagnosis / working impression for this case.

MANDATORY RULES:
1. Use specific diagnostic terminology with ICF classification.
2. Include primary pathology, contributing factors, and key clinical flags if any.
3. Structure: Primary diagnosis + Contributing factors + Clinical considerations (if any).
4. Keep concise (max 100 words total).
5. Do NOT include treatment recommendations here.

OUTPUT FORMAT:
Primary Diagnosis: [Specific diagnosis]
Contributing Factors: [2-3 key factors]
Clinical Considerations: [Any red/yellow flags or comorbidities]
"""


def get_provisional_diagnosis_field_prompt(
    field: str,
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective: Optional[Dict[str, Any]] = None,
    perspectives: Optional[Dict[str, Any]] = None,
    assessments: Optional[Dict[str, Any]] = None,
    objective_findings: Optional[Dict[str, Any]] = None,
    clinical_flags: Optional[Dict[str, Any]] = None,
    patho_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    IMPROVED: Field-specific provisional diagnosis guidance with body region-specific differential diagnoses.
    Provides evidence-based diagnostic reasoning for each field based on clinical presentation.

    NEW: Integrates pain mechanism classification into differential diagnosis reasoning.

    Endpoint: /api/ai_suggestion/provisional_diagnosis/<field>
    """

    # Detect body region for specific differential diagnoses
    body_region = detect_body_region(present_hist)
    icf_core_set = ICF_CORE_SETS.get(body_region) if body_region else None

    # Build comprehensive context
    context = build_clinical_context(
        age_sex, present_hist, past_hist,
        subjective=subjective,
        perspectives=perspectives,
        assessments=objective_findings
    )

    # Add clinical flags if available
    if clinical_flags:
        red_flags = clinical_flags.get('red_flags', '')
        yellow_flags = clinical_flags.get('yellow_flags', '')
        if red_flags:
            context += f"\n\n🔴 RED FLAGS:\n{red_flags}"
        if yellow_flags:
            context += f"\n\n🟡 YELLOW FLAGS:\n{yellow_flags}"

    field_label = field.replace("_", " ").title()

    # ICF Core Set context
    icf_guidance = ""
    if icf_core_set:
        icf_guidance = f"\nRELEVANT CONDITION CATEGORY: {icf_core_set['name']}\n"

    # Body region-specific common diagnoses and differential diagnoses
    region_specific_diagnoses = ""
    if body_region == 'shoulder':
        region_specific_diagnoses = """
SHOULDER-SPECIFIC DIFFERENTIAL DIAGNOSES (Evidence-Based):

**COMMON SHOULDER CONDITIONS BY AGE:**

**Young Adults (<40 years):**
- Rotator cuff tendinopathy
- Shoulder instability (anterior/posterior/multidirectional)
- Subacromial impingement syndrome
- AC joint sprain/injury
- Labral tears (SLAP lesion)
- Referred pain from cervical spine

**Middle-Aged (40-60 years):**
- Rotator cuff tendinopathy/partial tears
- Subacromial impingement syndrome
- Adhesive capsulitis (frozen shoulder)
- Rotator cuff tear (partial/full thickness)
- AC joint arthritis
- Calcific tendinitis

**Older Adults (>60 years):**
- Rotator cuff tear (degenerative)
- Glenohumeral osteoarthritis
- Adhesive capsulitis
- Subacromial impingement
- Polymyalgia rheumatica (if bilateral)

**STRUCTURES COMMONLY AT FAULT:**
- **Rotator cuff**: Supraspinatus (most common), infraspinatus, subscapularis, teres minor
- **Bursa**: Subacromial bursa (impingement)
- **Joint capsule**: Glenohumeral capsule (adhesive capsulitis)
- **Labrum**: Glenoid labrum (instability, SLAP)
- **Tendon**: Long head biceps
- **Joint**: AC joint, GH joint
- **Nerve**: Suprascapular nerve (rare)

**KEY DIFFERENTIAL DIAGNOSTIC FEATURES:**
- **Rotator cuff tendinopathy**: Painful arc 60-120°, positive Neer's/Hawkins-Kennedy, weakness with resisted tests
- **Adhesive capsulitis**: Global ROM restriction (capsular pattern: ER > ABD > IR), passive = active loss
- **Rotator cuff tear**: Weakness + pain, positive drop arm, atrophy (chronic)
- **Instability**: Apprehension sign positive, young athlete, history of dislocation
- **AC joint**: Tenderness over AC joint, pain with horizontal adduction
- **Referred cervical**: Spurling's positive, neck movements reproduce shoulder pain, neurological signs
"""
    elif body_region == 'lumbar':
        region_specific_diagnoses = """
LUMBAR SPINE-SPECIFIC DIFFERENTIAL DIAGNOSES (Evidence-Based):

**COMMON LUMBAR CONDITIONS BY AGE:**

**Young Adults (<40 years):**
- Mechanical low back pain (muscle/ligament strain)
- Disc herniation with radiculopathy
- Facet joint dysfunction
- Sacroiliac joint dysfunction
- Spondylolysis/spondylolisthesis (athletes)
- Inflammatory spondyloarthropathy (if morning stiffness >1h)

**Middle-Aged (40-60 years):**
- Degenerative disc disease
- Facet joint arthritis
- Disc herniation/prolapse
- Spinal stenosis (early)
- Mechanical low back pain
- Piriformis syndrome

**Older Adults (>60 years):**
- Spinal stenosis (neurogenic claudication)
- Degenerative spondylolisthesis
- Compression fracture (osteoporotic)
- Facet joint arthritis
- Disc degeneration

**STRUCTURES COMMONLY AT FAULT:**
- **Disc**: Intervertebral disc (herniation, prolapse, degeneration, annular tear)
- **Facet joints**: Zygapophyseal joints L4-L5, L5-S1
- **Nerve roots**: L5, S1 (sciatica), L4 (femoral nerve)
- **Muscles**: Multifidus, erector spinae, psoas, quadratus lumborum
- **Ligaments**: Iliolumbar ligament, interspinous ligaments
- **SI joint**: Sacroiliac joint
- **Vertebrae**: Compression fracture, spondylolysis

**KEY DIFFERENTIAL DIAGNOSTIC FEATURES:**
- **Disc herniation/radiculopathy**: Positive SLR, dermatomal pain/numbness, myotomal weakness, reflex changes
- **Spinal stenosis**: Neurogenic claudication (better with flexion/sitting), bilateral leg symptoms, walking tolerance limited
- **Facet joint**: Unilateral LBP, worse with extension/rotation, localized tenderness
- **SI joint**: Pain over PSIS, positive provocation tests (FABER, Gaenslen's, thigh thrust)
- **Mechanical LBP**: No neurological signs, movement-related, no red flags
- **Cauda equina (RED FLAG)**: Saddle anesthesia, bilateral symptoms, bowel/bladder dysfunction
"""
    elif body_region == 'knee':
        region_specific_diagnoses = """
KNEE-SPECIFIC DIFFERENTIAL DIAGNOSES (Evidence-Based):

**COMMON KNEE CONDITIONS BY AGE:**

**Young Adults/Athletes (<40 years):**
- ACL tear (acute trauma)
- Meniscal tear (sports injury)
- Patellar tendinopathy (jumper's knee)
- Patellofemoral pain syndrome
- MCL/LCL sprain
- Patellar instability/dislocation
- IT band syndrome

**Middle-Aged (40-60 years):**
- Degenerative meniscal tear
- Early osteoarthritis
- Patellofemoral pain syndrome
- Pes anserine bursitis
- Baker's cyst

**Older Adults (>60 years):**
- Knee osteoarthritis
- Degenerative meniscal tear
- Quadriceps/patellar tendinopathy
- Referred pain from hip

**STRUCTURES COMMONLY AT FAULT:**
- **Ligaments**: ACL, PCL, MCL, LCL
- **Meniscus**: Medial meniscus (more common), lateral meniscus
- **Cartilage**: Patellofemoral cartilage, tibiofemoral cartilage (OA)
- **Tendons**: Patellar tendon, quadriceps tendon
- **Bursa**: Pes anserine bursa, prepatellar bursa
- **Patella**: Patellar tracking dysfunction, chondromalacia patellae
- **IT band**: Iliotibial band friction syndrome

**KEY DIFFERENTIAL DIAGNOSTIC FEATURES:**
- **ACL tear**: Positive Lachman, anterior drawer, pivot shift; acute effusion, mechanism (non-contact pivot)
- **Meniscal tear**: Joint line tenderness, McMurray's positive, locking/catching, effusion
- **Patellofemoral pain**: Anterior knee pain, worse with stairs/squatting, positive Clarke's test
- **MCL sprain**: Valgus stress positive, medial joint line tenderness
- **OA**: Crepitus, morning stiffness <30min, bony enlargement, age >50
- **Patellar tendinopathy**: Inferior pole tenderness, load-related, jumpers/runners
"""
    elif body_region == 'cervical':
        region_specific_diagnoses = """
CERVICAL SPINE-SPECIFIC DIFFERENTIAL DIAGNOSES (Evidence-Based):

**COMMON CERVICAL CONDITIONS BY AGE:**

**Young Adults (<40 years):**
- Mechanical neck pain (muscle strain, whiplash)
- Cervical disc herniation with radiculopathy
- Facet joint dysfunction
- Postural neck pain
- Thoracic outlet syndrome

**Middle-Aged (40-60 years):**
- Cervical spondylosis (degenerative disc/facet)
- Cervical radiculopathy (nerve root compression)
- Mechanical neck pain
- Myofascial pain syndrome

**Older Adults (>60 years):**
- Cervical spondylotic myelopathy (CRITICAL - spinal cord compression)
- Cervical spondylosis
- Cervical radiculopathy
- Cervical spinal stenosis

**STRUCTURES COMMONLY AT FAULT:**
- **Disc**: Intervertebral disc (herniation C5-C6, C6-C7 most common)
- **Facet joints**: Zygapophyseal joints (C2-C3 to C7-T1)
- **Nerve roots**: C5, C6, C7 (most commonly compressed)
- **Muscles**: Upper trapezius, levator scapulae, suboccipitals, SCM
- **Ligaments**: Ligamentum flavum, facet capsules
- **Spinal cord**: Myelopathy (if upper motor neuron signs)

**KEY DIFFERENTIAL DIAGNOSTIC FEATURES:**
- **Cervical radiculopathy**: Spurling's positive, dermatomal pain/numbness (arm), myotomal weakness, reflex changes
- **Myelopathy (RED FLAG)**: Gait disturbance, hyperreflexia, clonus, Babinski positive, bilateral UL symptoms
- **Facet joint**: Unilateral neck pain, worse with extension/rotation, no neurological signs
- **Mechanical neck pain**: No neurological signs, movement-related, postural aggravation
- **Whiplash**: History of trauma, multiple symptoms (neck pain, headache, dizziness)
- **Referred shoulder pain**: Shoulder symptoms from C5-C6 nerve root
"""
    elif body_region == 'hip':
        region_specific_diagnoses = """
HIP-SPECIFIC DIFFERENTIAL DIAGNOSES (Evidence-Based):

**COMMON HIP CONDITIONS BY AGE:**

**Young Adults (<40 years):**
- Femoroacetabular impingement (FAI)
- Labral tear
- Hip flexor strain (iliopsoas)
- Adductor strain (groin pain)
- Athletic pubalgia (sports hernia)
- Trochanteric bursitis

**Middle-Aged (40-60 years):**
- Early hip osteoarthritis
- Trochanteric bursitis/gluteal tendinopathy
- Labral tear
- FAI
- Referred pain from lumbar spine

**Older Adults (>60 years):**
- Hip osteoarthritis
- Gluteal tendinopathy
- Trochanteric bursitis
- Hip fracture (if trauma/osteoporosis)
- Referred lumbar spine pain

**STRUCTURES COMMONLY AT FAULT:**
- **Joint**: Hip joint (acetabulofemoral), osteoarthritis
- **Labrum**: Acetabular labrum (tear)
- **Bursa**: Trochanteric bursa, iliopsoas bursa
- **Tendons**: Gluteal tendons (medius/minimus), iliopsoas, adductors
- **Muscles**: Hip flexors, adductors, gluteals
- **Femur**: Greater trochanter, femoral head/neck
- **Lumbar spine**: L1-L3 nerve roots (referred)

**KEY DIFFERENTIAL DIAGNOSTIC FEATURES:**
- **Hip OA**: Groin pain, capsular pattern (IR > ABD > flexion), morning stiffness <30min, age >50
- **Labral tear**: Positive FADIR, clicking/catching, C-sign (cup groin with hand)
- **FAI**: Positive FADIR, young active patient, groin pain with hip flexion
- **Trochanteric bursitis**: Lateral hip pain, tender over greater trochanter, pain lying on side
- **Gluteal tendinopathy**: Lateral hip pain, Trendelenburg positive, weakness with hip ABD
- **Referred lumbar**: Positive lumbar provocation, back pain present, no hip ROM restriction
"""
    elif body_region == 'ankle':
        region_specific_diagnoses = """
ANKLE/FOOT-SPECIFIC DIFFERENTIAL DIAGNOSES (Evidence-Based):

**COMMON ANKLE/FOOT CONDITIONS BY AGE:**

**Young Adults/Athletes (<40 years):**
- Ankle sprain (lateral ligament - most common)
- Achilles tendinopathy
- Plantar fasciitis
- Stress fracture (metatarsal, calcaneus)
- Ankle instability (chronic)
- Peroneal tendinopathy

**Middle-Aged (40-60 years):**
- Plantar fasciitis
- Achilles tendinopathy
- Ankle arthritis (post-traumatic)
- Tibialis posterior tendinopathy (flatfoot)
- Morton's neuroma

**Older Adults (>60 years):**
- Plantar fasciitis
- Ankle/foot osteoarthritis
- Achilles tendinopathy
- Peripheral neuropathy
- Tarsal tunnel syndrome

**STRUCTURES COMMONLY AT FAULT:**
- **Ligaments**: ATFL (most common sprain), CFL, deltoid ligament, syndesmosis
- **Tendons**: Achilles, tibialis posterior, peroneal tendons, tibialis anterior
- **Fascia**: Plantar fascia
- **Bones**: Metatarsals (stress fracture), talus, calcaneus, navicular
- **Nerve**: Tibial nerve (tarsal tunnel), interdigital nerve (Morton's)
- **Joint**: Talocrural joint, subtalar joint, 1st MTP (hallux rigidus)

**KEY DIFFERENTIAL DIAGNOSTIC FEATURES:**
- **Lateral ankle sprain**: Anterior drawer positive, talar tilt positive, inversion mechanism, ATFL tender
- **Achilles tendinopathy**: Painful palpation 2-6cm above insertion, pain with heel raises, worse morning
- **Plantar fasciitis**: Plantar heel pain, worse first steps in morning, tender medial calcaneal tubercle
- **Achilles rupture (RED FLAG)**: Thompson test positive, palpable gap, inability to plantarflex
- **Ankle fracture**: Ottawa rules positive, inability to weight bear, bony tenderness
- **Syndesmosis injury**: Squeeze test positive, external rotation test positive, high ankle mechanism
"""
    else:
        region_specific_diagnoses = """
GENERAL MUSCULOSKELETAL DIFFERENTIAL DIAGNOSES:

**Common Patterns:**
- Acute traumatic injury vs chronic overuse
- Inflammatory vs mechanical
- Local vs referred pain
- Neuropathic vs nociceptive vs nociplastic pain

**Structures to Consider:**
- **Joints**: Arthritis, capsulitis, instability
- **Muscles**: Strain, spasm, trigger points
- **Tendons**: Tendinopathy, tear, rupture
- **Ligaments**: Sprain, tear
- **Nerves**: Radiculopathy, neuropathy, nerve entrapment
- **Bursa**: Bursitis
- **Bone**: Fracture, stress fracture, bone pathology

**Key Diagnostic Categories:**
- Degenerative conditions
- Inflammatory conditions
- Traumatic injuries
- Overuse syndromes
- Referred pain
- Serious pathology (red flags)
"""

    # Field-specific guidance
    field_specific_guidance = {
        'likelihood': f"""
TARGET FIELD: LIKELIHOOD OF DIAGNOSIS

PURPOSE:
Assess the probability that the current working hypothesis/provisional diagnosis is correct based on ALL available clinical data (subjective, perspectives, objective findings, clinical flags).

WHAT TO INCLUDE:
1. **Probability Assessment**
   - High likelihood (>70%): Strong clinical evidence supports this diagnosis
   - Moderate likelihood (40-70%): Some evidence supports, but differentials remain
   - Low likelihood (<40%): Limited evidence, differentials more likely

2. **Evidence Strength Analysis**
   - How many key clinical features are present vs absent?
   - Do objective findings confirm subjective presentation?
   - Are there pathognomonic signs/tests specific to this diagnosis?
   - Is the clinical presentation typical or atypical?

3. **Body Region Context: {body_region.upper() if body_region else 'GENERAL MSK'}**
   - Consider age-appropriate common diagnoses for this region
   - Reference prevalence data (e.g., rotator cuff tears increase with age)
   - Consider mechanism of injury if traumatic

4. **Differential Diagnosis Strength**
   - Are there competing diagnoses that better explain the presentation?
   - Have key differentials been ruled out with objective tests?
   - Is this diagnosis of exclusion or confirmed by specific findings?

CRITICAL CONSIDERATIONS:
- HIGH likelihood requires multiple converging lines of evidence (history + exam + special tests)
- MODERATE likelihood when 1-2 key features missing or differentials not fully excluded
- LOW likelihood when presentation doesn't fit typical pattern or red flags suggest alternative
- Consider sensitivity/specificity of positive tests
- Age, mechanism, and timeline matter for probability

✅ GOOD PATIENT-SPECIFIC EXAMPLE:
"High likelihood (75%). This 52-year-old female presents with classic adhesive capsulitis pattern: global ROM restriction in capsular pattern (ER>ABD>IR), both active and passive loss, gradual onset over 3 months. Objective findings confirm: ER <30° (normal 90°), ABD <90° (normal 180°), IR <40° (normal 70°). No neurological signs. Age, sex, and progressive ROM loss typical for primary frozen shoulder."

❌ AVOID GENERIC RESPONSES LIKE:
"Patient may have frozen shoulder. Consider ROM testing and assess for capsular pattern."
""",
        'structure_fault': f"""
TARGET FIELD: POSSIBLE STRUCTURE AT FAULT

PURPOSE:
Identify the specific anatomical structure(s) most likely responsible for the patient's symptoms based on clinical reasoning and objective findings.

WHAT TO INCLUDE:
1. **Primary Structure(s)**
   - Be SPECIFIC (e.g., "supraspinatus tendon" not "rotator cuff")
   - State exact anatomical location
   - Consider depth (superficial vs deep structures)
   - Specify side (left/right) if unilateral

2. **Tissue Type Classification**
   - Contractile tissue (muscle/tendon) → Painful with resisted tests
   - Inert tissue (joint capsule, ligament, bursa) → Painful with passive tests
   - Neural tissue → Positive neurodynamic tests, dermatomal/nerve territory distribution

3. **Body Region Context: {body_region.upper() if body_region else 'GENERAL MSK'}**
   - Reference the common structures listed above for this body region
   - Consider age-related tissue changes (degeneration vs acute injury)
   - Match structure to mechanism of injury

4. **Clinical Evidence for Structure**
   - Which objective tests specifically stress/load this structure?
   - Is pain reproduced with palpation of this structure?
   - Does ROM pattern fit this structure's involvement?
   - Do resisted tests isolate this structure?

5. **Differential Structural Considerations**
   - Could multiple structures be involved (e.g., shoulder: supraspinatus + subacromial bursa)?
   - Is there a primary structure with secondary compensatory issues?
   - Rule out referred pain from other regions

CRITICAL CONSIDERATIONS:
- Use EXACT anatomical terminology (not vague like "soft tissue")
- Match structure to pain location and pattern
- Consider whether structure matches provocation tests
- Contractile structures = painful resisted tests
- Non-contractile structures = painful passive tests
- Neural structures = neurodynamic tests + distribution

✅ GOOD PATIENT-SPECIFIC EXAMPLE:
"Primary structure at fault: Right supraspinatus tendon (musculotendinous junction).

Evidence from THIS patient's exam:
- Painful arc 70-110° abduction (classic subacromial impingement pattern)
- Empty can test positive (pain and weakness with resisted abduction at 90° in scaption)
- Tender on palpation 2cm inferior to acromion at supraspinatus insertion site
- Pain reproduced with Neer's impingement test

Tissue type: Contractile (tendon) - confirmed by positive resisted tests
Secondary structure: Subacromial bursa (reactive bursitis from chronic impingement)
Age consideration: 48-year-old - consistent with age-related tendon degeneration"

❌ AVOID GENERIC RESPONSES LIKE:
"Rotator cuff injury. Test shoulder movement and strength."
""",
        'symptom': f"""
TARGET FIELD: SYMPTOM

PURPOSE:
Describe the PRIMARY symptom(s) driving the patient's clinical presentation using precise clinical terminology.

WHAT TO INCLUDE:
1. **Primary Symptom Category**
   - Pain (most common)
   - Weakness
   - Stiffness/restricted movement
   - Instability/giving way
   - Swelling
   - Numbness/tingling (neurological)
   - Loss of function

2. **Pain Characterization (if pain is primary symptom):**
   - **Quality**: Sharp, aching, burning, stabbing, throbbing
   - **Location**: Specific anatomical location (e.g., "anterior knee pain" not "knee pain")
   - **Pattern**: Constant vs intermittent, worse with specific movements
   - **Intensity**: VAS score (0-10)
   - **Timing**: Worse morning/evening, with activity/rest
   - **Radiation**: Does it spread/refer elsewhere?

3. **Neurological Symptoms (if present):**
   - Numbness distribution (dermatomal pattern?)
   - Tingling/pins & needles
   - Weakness pattern (myotomal pattern?)
   - Altered sensation

4. **Functional Impact**
   - How does this symptom limit activities?
   - What can they NOT do because of this symptom?
   - Is this symptom the primary barrier to participation?

5. **Symptom Irritability**
   - How easily is it provoked?
   - How long to settle?
   - Does it interfere with sleep?

CRITICAL CONSIDERATIONS:
- Use patient's OWN words where appropriate (quoted)
- Be SPECIFIC to location (e.g., "lateral epicondyle pain" not "elbow pain")
- Describe DOMINANT symptom if multiple present
- Connect symptom to ICF body function impairment
- Consider whether symptom matches proposed structure at fault

EXAMPLE OUTPUT:
"Primary symptom: Sharp, anterior knee pain (VAS 6/10) localized to inferior pole of patella. Pain is intermittent, provoked by jumping, landing, and stairs (especially descending). Patient describes 'stabbing sensation' with squat past 90°. Pain settles within 5-10 minutes of rest. No neurological symptoms. Functional impact: Unable to play basketball (main participation restriction)."
""",
        'findings_support': f"""
TARGET FIELD: FINDINGS SUPPORTING THE DIAGNOSIS

PURPOSE:
List the POSITIVE clinical findings (from subjective AND objective examination) that SUPPORT and CONFIRM the provisional diagnosis.

WHAT TO INCLUDE:
1. **Subjective Findings That Support**
   - History details that match this diagnosis
   - Mechanism of injury consistent with diagnosis
   - Symptom pattern typical for this condition
   - Timeline/onset fits expected course
   - Aggravating/easing factors match pathology
   - Age-appropriate presentation

2. **Objective Findings That Support**
   - Positive special tests (name specific tests with results)
   - ROM patterns consistent with diagnosis
   - Strength deficits matching expected pattern
   - Palpation findings (tenderness, swelling, deformity)
   - Gait/functional movement abnormalities
   - Neurological findings (if relevant)

3. **Clinical Flags That Support**
   - Absence of red flags (confirms non-serious pathology)
   - Yellow flags present (support biopsychosocial model)
   - Pattern recognition from clinical experience

4. **Evidence-Based Diagnostic Criteria**
   - Does presentation meet established diagnostic criteria?
   - Are pathognomonic signs present?
   - Is there a cluster of positive tests (higher diagnostic accuracy)?

5. **Body Region Context: {body_region.upper() if body_region else 'GENERAL MSK'}**
   - Reference expected findings for common diagnoses in this region
   - Match findings to typical presentation of suspected diagnosis

CRITICAL CONSIDERATIONS:
- Be SPECIFIC with test names and results (e.g., "Lachman test positive with soft end-feel")
- Quantify where possible (ROM degrees, VAS scores, strength grades)
- Connect subjective to objective (do they corroborate?)
- Consider diagnostic accuracy of tests (sensitivity/specificity)
- List findings in order of diagnostic weight (strongest evidence first)
- Include both clinical exam AND patient-reported outcomes

✅ GOOD PATIENT-SPECIFIC EXAMPLE:
"Supporting findings for ACL tear in this 24-year-old male footballer:
1. **History**: Non-contact pivot mechanism during match yesterday, immediate 'pop' sensation, knee giving way, large effusion within 2 hours (hemarthrosis - highly specific for ACL)
2. **Positive tests**: Lachman test grade 3 positive (>10mm translation, soft/mushy end-feel), anterior drawer positive, pivot shift apprehension positive
3. **Current ROM**: Full extension maintained, flexion limited to 110° due to joint effusion (swelling restricts motion)
4. **Functional limitation**: Unable to perform single leg hop test, marked apprehension with cutting/pivoting movements
5. **Test cluster**: Positive Lachman + pivot shift + mechanism = >95% diagnostic accuracy for ACL tear"

❌ AVOID GENERIC RESPONSES LIKE:
"Patient may have ligament tear. Consider special testing for knee instability."
""",
        'findings_reject': f"""
TARGET FIELD: FINDINGS REJECTING THE DIAGNOSIS

PURPOSE:
List the clinical findings (from subjective AND objective examination) that CONTRADICT or make the provisional diagnosis LESS LIKELY. This is critical for differential diagnosis and avoiding diagnostic error.

WHAT TO INCLUDE:
1. **Missing Expected Findings**
   - Key clinical features that SHOULD be present but are NOT
   - Negative special tests that would typically be positive
   - Absence of pathognomonic signs
   - ROM patterns that don't fit the diagnosis
   - Timeline doesn't match expected course

2. **Contradictory Objective Findings**
   - Test results that point toward a different diagnosis
   - Strength/ROM better than expected for this diagnosis
   - Pain pattern inconsistent with proposed structure
   - Palpation negative for expected tender points

3. **Atypical Presentation Features**
   - Age atypical for this diagnosis
   - Mechanism doesn't fit expected pathology
   - Symptom behavior unusual for this condition
   - Response to treatment not as expected

4. **Red Flags or Serious Pathology Indicators**
   - Findings suggesting serious pathology instead
   - Red flags that contradict mechanical diagnosis
   - Systemic symptoms not explained by proposed diagnosis

5. **Alternative Diagnoses More Likely**
   - Findings that better fit a different diagnosis
   - Differential diagnoses not yet ruled out
   - Competing explanations for presentation

6. **Body Region Context: {body_region.upper() if body_region else 'GENERAL MSK'}**
   - Consider what findings would be expected for common diagnoses
   - What's missing that should be there?

CRITICAL CONSIDERATIONS:
- This field is CRITICAL for avoiding diagnostic error
- Be honest about contradictory evidence
- Missing expected findings are as important as present findings
- Consider alternative diagnoses explicitly
- Highlight red flags that suggest serious pathology
- Note if presentation is atypical for the proposed diagnosis
- Use this to guide further assessment or referral

EXAMPLE OUTPUT:
"Findings rejecting rotator cuff tear diagnosis:
1. **Negative tests**: Drop arm test negative, full strength with resisted external rotation (infraspinatus intact)
2. **Full ROM**: Patient has full active shoulder abduction to 180° (unlikely with significant rotator cuff tear)
3. **No weakness**: Manual muscle testing 5/5 for all rotator cuff muscles (not consistent with tear)
4. **Atypical age**: 28-year-old without significant trauma (tears uncommon in this age group without major trauma)
5. **Alternative diagnosis**: Findings more consistent with subacromial impingement without tear (positive Neer's/Hawkins, painful arc, but strength intact)
6. **Imaging not indicated**: Ottawa shoulder rules negative for fracture, strength intact rules out complete tear"
"""
    }

    specific_guidance = field_specific_guidance.get(field, f"""
TARGET FIELD: {field_label}

Provide clinically relevant, evidence-based suggestions for this field based on the patient's presentation and diagnostic reasoning.
""")

    # NEW: Add pathophysiological mechanism context for diagnosis integration
    patho_context = ""
    if patho_data:
        pain_mechanism = patho_data.get('possible_source', '')
        pain_type = patho_data.get('pain_type', '')
        healing_stage = patho_data.get('stage_healing', '')

        if any([pain_mechanism, pain_type, healing_stage]):
            patho_context = "\n\nPAIN MECHANISM CLASSIFICATION (INTEGRATE INTO DIAGNOSIS):\n"
            if pain_mechanism:
                patho_context += f"- Pain Source: {pain_mechanism}\n"
            if pain_type:
                patho_context += f"- Pain Type: {pain_type}\n"
            if healing_stage:
                patho_context += f"- Tissue Healing Stage: {healing_stage}\n"
            patho_context += "\nIMPORTANT: Integrate pain mechanism into provisional diagnosis (e.g., 'subacromial impingement with nociceptive pain mechanism' or 'lumbar radiculopathy with neurogenic pain').\n"

    return f"""{SYSTEM_ROLES['clinical_specialist']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 CRITICAL: ANALYZE THIS SPECIFIC PATIENT'S DATA FIRST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{context}
{icf_guidance}
{patho_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  MANDATORY FIRST STEP - PATIENT DATA ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BEFORE generating your response, you MUST:

1. **IDENTIFY THE SPECIFIC PATIENT DETAILS:**
   - What is this patient's age and sex?
   - What is their EXACT presenting complaint (body region + symptom)?
   - What specific findings have been documented above?
   - What objective test results are available?

2. **EXTRACT KEY CLINICAL FEATURES:**
   - Pain location (be specific: "right lateral shoulder" not "shoulder")
   - Aggravating/easing factors mentioned
   - Timeline (acute <6 weeks, subacute 6-12 weeks, chronic >12 weeks)
   - Mechanism if traumatic (fall, twist, gradual onset, etc.)
   - Any positive/negative special tests
   - ROM limitations or strength deficits

3. **YOUR RESPONSE MUST:**
   - START with patient-specific findings ("This 45-year-old presents with...")
   - QUOTE actual data from above ("VAS pain 7/10, worse with overhead reaching")
   - AVOID generic textbook answers
   - CONNECT your suggestion directly to THIS patient's presentation
   - USE the body region detected: {body_region.upper() if body_region else 'GENERAL MSK'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{specific_guidance}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANDATORY RULES FOR YOUR RESPONSE:

🎯 **PATIENT-SPECIFICITY IS NON-NEGOTIABLE:**
   1. START your response by referencing THIS patient's specifics:
      - Age/sex: Mention the patient's age and sex from the data above
      - Body region: Use EXACT location from patient data (e.g., "right shoulder", "L4-L5 lumbar spine")
      - Mechanism: Reference the specific mechanism if mentioned

   2. QUOTE ACTUAL FINDINGS from the patient data:
      - Don't say "patient may have pain" - say "patient reports VAS 7/10 pain"
      - Don't say "consider ROM testing" - say "given limited flexion to 110°..."
      - Don't say "assess for red flags" - say "no red flags present: no fever, no weight loss..."

   3. AVOID GENERIC RESPONSES:
      ❌ BAD: "Consider rotator cuff pathology. Test with Neer's and Hawkins-Kennedy."
      ✅ GOOD: "This 52-year-old female presents with 3-month history of right shoulder pain (VAS 7/10), worse with overhead activities. Given age and gradual onset, consider rotator cuff tendinopathy. Positive Hawkins-Kennedy test supports subacromial impingement."

🔍 **CLINICAL REASONING FRAMEWORK:**
   - Step 1: Analyze THIS patient's presentation using data above
   - Step 2: Match presentation to age-appropriate differentials for {body_region or 'this region'}
   - Step 3: Identify which findings SUPPORT vs CONTRADICT each differential
   - Step 4: Rule out serious pathology based on red flags section
   - Step 5: Provide specific diagnostic hypothesis with supporting evidence

📊 **EVIDENCE-BASED DIAGNOSIS:**
   - Reference actual test results by name ("Lachman test positive" not "instability tests")
   - Use specific diagnostic terminology ("supraspinatus tendinopathy" not "shoulder problem")
   - Quantify findings (ROM in degrees, strength grades, VAS scores)
   - Consider test sensitivity/specificity

⚠️ **DIFFERENTIAL THINKING:**
   - State top 2-3 most likely diagnoses for THIS patient
   - Explain WHY this diagnosis fits THIS patient's presentation
   - State what findings would RULE OUT each differential
   - Acknowledge diagnostic uncertainty honestly

🎯 **FIELD-SPECIFIC OUTPUT:**
   - Follow guidance for: **{field_label}**
   - Be concise (3-5 sentences) but specific to THIS patient
   - Connect to ICF framework (impairments → activity limitations)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 REGIONAL EXAMINATION PRINCIPLE (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**IMPORTANT: Consider Adjacent Joint Assessment**

When formulating your diagnosis and assessment plan, ALWAYS consider:

1. **ONE JOINT PROXIMAL** (above the presenting area)
   - Shoulder pain → Check cervical spine/neck
   - Elbow pain → Check shoulder and cervical spine
   - Wrist pain → Check elbow
   - Hip pain → Check lumbar spine/sacroiliac joint
   - Knee pain → Check hip and lumbar spine
   - Ankle pain → Check knee

2. **ONE JOINT DISTAL** (below the presenting area)
   - Neck pain → Check shoulder/thoracic mobility
   - Shoulder pain → Check elbow/wrist function
   - Elbow pain → Check wrist/hand
   - Lumbar pain → Check hip mobility
   - Hip pain → Check knee function
   - Knee pain → Check ankle/foot biomechanics

**RATIONALE:**
- Pain may be referred from proximal structures
- Distal dysfunction may compensate or contribute to proximal symptoms
- Biomechanical chains mean adjacent joints influence each other
- Complete clinical reasoning requires regional assessment, not isolated joint focus

**APPLICATION:**
- Include brief mention of proximal/distal joint screening needs where clinically relevant
- Don't force this if clearly not applicable (e.g., obvious acute trauma to isolated joint)
- Subtle integration into your clinical reasoning, not a separate section

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 REFERENCE: BODY REGION-SPECIFIC DIFFERENTIAL DIAGNOSES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use this as REFERENCE ONLY to inform your patient-specific response:

{region_specific_diagnoses}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 FINAL REMINDER:
Your response must be SPECIFIC to the patient data provided above.
Do NOT give generic textbook answers.
QUOTE actual findings and connect them to your clinical reasoning.
"""


def get_objective_assessment_prompt(
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective: Optional[Dict[str, Any]] = None,
    provisional_diagnoses: Optional[str] = None,
) -> str:
    """
    Suggest objective tests and measures based on subjective findings.
    LEGACY FUNCTION - Consider using get_objective_assessment_field_prompt for field-specific guidance.

    Endpoint: /api/ai_suggestion/objective_assessment
    """
    context = build_clinical_context(age_sex, present_hist, past_hist, subjective=subjective)
    if provisional_diagnoses:
        context += f"\n\nProvisional Diagnoses from Subjective:\n{provisional_diagnoses}"

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{context}

TASK:
Suggest TOP 5 most important objective assessments/tests for this case.

MANDATORY RULES:
1. Each test must be:
   - Specific to the case and body region
   - Evidence-based for the provisional diagnoses
   - Clinically feasible in a typical physiotherapy setting
2. Format: Test name + Brief purpose (what it tests/rules out)
3. Order by priority (most important first)
4. Do NOT suggest imaging unless for red flag concerns

OUTPUT FORMAT:
1. [Test name] - [What it assesses/rules out]
2. [Test name] - [What it assesses/rules out]
3. [Test name] - [What it assesses/rules out]
4. [Test name] - [What it assesses/rules out]
5. [Test name] - [What it assesses/rules out]
"""


def get_objective_assessment_field_prompt(
    field: str,
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective: Optional[Dict[str, Any]] = None,
    perspectives: Optional[Dict[str, Any]] = None,
    provisional_diagnoses: Optional[str] = None,
    clinical_flags: Optional[Dict[str, Any]] = None,
    patho_data: Optional[Dict[str, Any]] = None,
    existing_inputs: Optional[Dict[str, str]] = None,  # NEW: Current form inputs for adaptive AI
) -> str:
    """
    IMPROVED: Field-specific objective assessment planning guidance.
    Provides comprehensive, body region-specific test recommendations based on all previous data.

    NEW: Includes pain mechanism context to guide test selection and approach.
    NEW: INTRA-FORM ADAPTIVE AI - Adapts suggestions based on previous fields filled on THIS form.

    Endpoint: /api/ai_suggestion/objective_assessment/<field>
    """

    # Detect body region for specific test recommendations
    body_region = detect_body_region(present_hist)
    icf_core_set = ICF_CORE_SETS.get(body_region) if body_region else None

    # Build comprehensive context
    context = build_clinical_context(
        age_sex, present_hist, past_hist,
        subjective=subjective,
        perspectives=perspectives
    )

    if provisional_diagnoses:
        context += f"\n\nProvisional Diagnoses from Subjective:\n{provisional_diagnoses}"

    if clinical_flags:
        red_flags = clinical_flags.get('red_flags', '')
        yellow_flags = clinical_flags.get('yellow_flags', '')
        if red_flags:
            context += f"\n\n🔴 RED FLAGS IDENTIFIED:\n{red_flags}"
        if yellow_flags:
            context += f"\n\n🟡 YELLOW FLAGS IDENTIFIED:\n{yellow_flags}"

    # ICF Core Set guidance
    icf_guidance = ""
    if icf_core_set:
        icf_guidance = f"\nRELEVANT CONDITION: {icf_core_set['name']}\n"
        icf_guidance += "Evidence-based body functions to assess:\n"
        for func in icf_core_set.get('body_functions', []):
            icf_guidance += f"  • {func}\n"

    # Field-specific guidance (currently only 'plan', but extensible)
    field_guidance = ""
    if field == "plan":
        field_guidance = """
TARGET FIELD: OBJECTIVE ASSESSMENT PLAN

PURPOSE:
You are helping the physiotherapist decide:
1. Whether to perform a COMPREHENSIVE or MODIFIED objective assessment
2. What specific tests to perform
3. What precautions to consider
4. Expected positive findings

ASSESSMENT APPROACH DECISION:

**COMPREHENSIVE WITHOUT MODIFICATION** - Use when:
- No red flags present
- Patient is medically stable
- Low irritability (can tolerate multiple tests)
- No severe pain or acute inflammation
- No contraindications to movement testing
- Need full diagnostic clarity

**COMPREHENSIVE WITH MODIFICATIONS** - Use when:
- Yellow flags present (fear-avoidance, anxiety about testing)
- Moderate irritability (need to pace testing)
- Subacute presentation (4-12 weeks)
- Comorbidities requiring adapted testing
- Need diagnostic clarity but with caution
- Patient fatigue or deconditioning

**Important Note:** If RED FLAGS are present, objective assessment may be LIMITED or CONTRAINDICATED until medical clearance is obtained.
"""

    # Body region-specific test categories
    region_specific_tests = ""
    if body_region == 'shoulder':
        region_specific_tests = """
SHOULDER-SPECIFIC OBJECTIVE TESTS (Evidence-Based):

**1. OBSERVATION & POSTURE:**
- Shoulder position (elevation, protraction, winging)
- Muscle atrophy (supraspinatus, infraspinatus)
- Scapular position and movement patterns

**2. ACTIVE RANGE OF MOTION (AROM):**
- Shoulder flexion, abduction, external rotation, internal rotation
- Functional movements: hand behind head, hand behind back
- Observe for painful arc (60-120° suggests subacromial impingement)
- Scapulohumeral rhythm assessment

**3. PASSIVE RANGE OF MOTION (PROM):**
- Compare to AROM to differentiate contractile vs non-contractile
- Assess end-feel (capsular pattern: ER > ABD > IR suggests adhesive capsulitis)
- Glenohumeral vs scapulothoracic contribution

**4. RESISTED TESTS (Muscle/Tendon):**
- Resisted abduction (supraspinatus)
- Resisted ER (infraspinatus, teres minor)
- Resisted IR (subscapularis)
- Resisted elbow flexion (long head biceps)
- Speed's test, Yergason's test (biceps tendinopathy)

**5. SPECIAL TESTS (High Sensitivity/Specificity):**
- Neer's impingement test (subacromial impingement)
- Hawkins-Kennedy test (subacromial impingement)
- Empty can test (supraspinatus tear)
- Drop arm test (rotator cuff tear)
- Apprehension/relocation test (anterior instability)
- Sulcus sign (inferior instability)
- AC joint stress tests if relevant

**6. NEUROLOGICAL SCREENING:**
- C5-C6 myotomes/dermatomes if radicular symptoms
- Upper limb neurodynamic tests (ULNT) if nerve involvement suspected

**7. FUNCTIONAL ASSESSMENT:**
- Reaching overhead (cupboard)
- Reaching behind back (fastening bra)
- Lifting/carrying tasks
- Work/sport-specific movements
"""
    elif body_region == 'lumbar':
        region_specific_tests = """
LUMBAR SPINE-SPECIFIC OBJECTIVE TESTS (Evidence-Based):

**1. OBSERVATION & POSTURE:**
- Lumbar lordosis (increased, decreased, flattened)
- Pelvic tilt and alignment
- Leg length discrepancy
- Gait pattern observation

**2. ACTIVE RANGE OF MOTION (AROM):**
- Lumbar flexion (finger-to-floor distance, modified Schober's)
- Extension, lateral flexion (left/right), rotation
- Observe for painful arc or deviation
- Assess willingness to move (fear-avoidance)

**3. PASSIVE RANGE OF MOTION (PROM):**
- Passive physiological movements (PPMs)
- Passive accessory movements (PAMs) - central/unilateral PA pressures
- End-feel assessment

**4. NEUROLOGICAL EXAMINATION (CRITICAL for radiculopathy):**
- Straight leg raise (SLR) - L5/S1 nerve root tension
- Femoral nerve stretch test - L2/L3/L4
- Myotomes: L2 (hip flexion), L3 (knee extension), L4 (ankle DF), L5 (great toe extension), S1 (ankle PF)
- Dermatomes: L4 (medial leg), L5 (dorsum of foot), S1 (lateral foot)
- Reflexes: Knee jerk (L3/4), ankle jerk (S1)
- Slump test for neurodynamics

**5. PALPATION:**
- Spinous process tenderness
- Paraspinal muscle spasm/tenderness
- Sacroiliac joint tenderness
- Pelvic landmarks

**6. SPECIAL TESTS:**
- Centralization/peripheralization (McKenzie assessment)
- Instability tests (passive lumbar extension test, prone instability test)
- Sacroiliac joint provocation tests (if SIJ suspected)
- Hip screening tests (FABER, FADIR) - rule out hip pathology

**7. FUNCTIONAL ASSESSMENT:**
- Sit to stand
- Lifting mechanics (squat vs stoop)
- Repeated movements (McKenzie protocol)
- Endurance tests (prone plank, side plank if tolerated)

**8. RED FLAG SCREENING (CRITICAL):**
- Saddle anesthesia (cauda equina)
- Bilateral leg symptoms (cauda equina)
- Bowel/bladder changes (cauda equina)
- Progressive neurological deficit
"""
    elif body_region == 'knee':
        region_specific_tests = """
KNEE-SPECIFIC OBJECTIVE TESTS (Evidence-Based):

**1. OBSERVATION & GAIT:**
- Knee alignment (varus, valgus, hyperextension)
- Swelling/effusion (patellar tap test, sweep test)
- Muscle atrophy (quadriceps, especially VMO)
- Gait pattern (antalgic, Trendelenburg, foot progression angle)

**2. ACTIVE RANGE OF MOTION (AROM):**
- Knee flexion (normal 0-135°)
- Knee extension (check for extension lag)
- Patellar tracking during flexion/extension

**3. PASSIVE RANGE OF MOTION (PROM):**
- Compare to AROM
- End-feel assessment (soft tissue vs bony vs springy block)
- Capsular pattern (flexion > extension)

**4. LIGAMENT STRESS TESTS:**
- Anterior drawer test (ACL)
- Lachman test (ACL) - GOLD STANDARD
- Posterior drawer test (PCL)
- Valgus stress test (MCL) - 0° and 30°
- Varus stress test (LCL) - 0° and 30°

**5. MENISCAL TESTS:**
- McMurray's test (posterior horn tears)
- Thessaly test (high sensitivity/specificity)
- Joint line tenderness (medial/lateral)

**6. PATELLOFEMORAL TESTS:**
- Patellar apprehension test (instability)
- Clarke's test (patellofemoral pain)
- Patellar glide/tilt assessment
- Q-angle measurement if relevant

**7. MUSCLE STRENGTH TESTING:**
- Quadriceps strength (isometric, manual muscle test)
- Hamstring strength
- Hip abductor strength (important for knee control)
- Single leg squat assessment (dynamic valgus)

**8. FUNCTIONAL TESTS:**
- Single leg stance
- Single leg squat
- Step up/step down
- Hop tests (if appropriate - single hop, triple hop, crossover hop)
- Stair climbing

**9. SPECIAL CONSIDERATIONS:**
- IT band tightness (Ober's test)
- Ankle/hip screening (influence on knee mechanics)
"""
    elif body_region == 'cervical':
        region_specific_tests = """
CERVICAL SPINE-SPECIFIC OBJECTIVE TESTS (Evidence-Based):

**1. OBSERVATION & POSTURE:**
- Forward head posture
- Cervical lordosis
- Shoulder elevation
- Thoracic kyphosis

**2. ACTIVE RANGE OF MOTION (AROM):**
- Flexion, extension, lateral flexion (L/R), rotation (L/R)
- Combined movements if needed
- Observe for deviation or painful arc

**3. PASSIVE RANGE OF MOTION (PROM):**
- Passive physiological movements
- Passive accessory movements (PAMs)
- End-feel assessment

**4. NEUROLOGICAL EXAMINATION:**
- Upper limb myotomes (C5-T1)
- Dermatomes (C5-T1)
- Reflexes (biceps C5/6, triceps C7, brachioradialis C6)
- Upper limb neurodynamic tests (ULNT1, ULNT2, ULNT3)

**5. SPECIAL TESTS:**
- Spurling's test (cervical radiculopathy) - HIGH SPECIFICITY
- Distraction test (relief suggests radiculopathy)
- Vertebral artery test (pre-manipulation screening - USE WITH CAUTION)
- Cervical flexion-rotation test (C1-C2 dysfunction)

**6. PALPATION:**
- Cervical spinous processes
- Facet joints (unilateral tenderness)
- Muscle spasm (upper trapezius, levator scapulae, suboccipital)
- Trigger points

**7. FUNCTIONAL ASSESSMENT:**
- Driving (rotation for blind spot check)
- Computer work posture
- Reading posture
- Overhead activities

**8. RED FLAG SCREENING:**
- Drop attacks (vertebrobasilar insufficiency)
- Bilateral upper limb symptoms (myelopathy)
- Gait disturbance (myelopathy)
- Upper motor neuron signs (hyperreflexia, clonus, Babinski)
"""
    elif body_region == 'hip':
        region_specific_tests = """
HIP-SPECIFIC OBJECTIVE TESTS (Evidence-Based):

**1. OBSERVATION & GAIT:**
- Trendelenburg gait (hip abductor weakness)
- Antalgic gait
- Leg length discrepancy
- Pelvic obliquity

**2. ACTIVE RANGE OF MOTION (AROM):**
- Hip flexion, extension, abduction, adduction, IR, ER
- Functional: putting on shoes/socks, sitting cross-legged

**3. PASSIVE RANGE OF MOTION (PROM):**
- Compare to AROM
- Capsular pattern (flexion > abduction > IR)
- End-feel assessment

**4. SPECIAL TESTS:**
- FABER test (Patrick's test) - hip pathology, SI joint
- FADIR test (impingement)
- Scour test (labral tear, OA)
- Trendelenburg test (hip abductor strength)
- Thomas test (hip flexor tightness)
- Ober's test (IT band tightness)

**5. MUSCLE STRENGTH:**
- Hip flexors, extensors, abductors, adductors
- Gluteus medius (single leg stance)

**6. FUNCTIONAL TESTS:**
- Single leg stance
- Squat
- Step up/down
- Gait analysis

**7. LUMBAR SPINE SCREENING:**
- Rule out referred pain from lumbar spine
"""
    elif body_region == 'ankle':
        region_specific_tests = """
ANKLE/FOOT-SPECIFIC OBJECTIVE TESTS (Evidence-Based):

**1. OBSERVATION:**
- Swelling, bruising, deformity
- Foot alignment (pes planus, pes cavus)
- Gait pattern (antalgic, foot drop)

**2. ACTIVE RANGE OF MOTION (AROM):**
- Ankle DF, PF, inversion, eversion
- Subtalar joint motion
- 1st MTP joint (great toe) flexion/extension

**3. PASSIVE RANGE OF MOTION (PROM):**
- Compare to AROM
- End-feel assessment

**4. LIGAMENT STRESS TESTS:**
- Anterior drawer test (ATFL)
- Talar tilt test (CFL)
- Syndesmosis squeeze test
- External rotation stress test (syndesmosis)

**5. SPECIAL TESTS:**
- Thompson test (Achilles tendon rupture)
- Windlass test (plantar fascia)
- Tinel's sign (tarsal tunnel syndrome)

**6. PALPATION:**
- Lateral ligaments (ATFL, CFL)
- Medial ligaments (deltoid)
- Achilles tendon
- Plantar fascia
- Malleoli

**7. FUNCTIONAL TESTS:**
- Single leg stance
- Single leg heel raise (Achilles/calf strength)
- Hop test
- Balance assessment

**8. NEUROLOGICAL SCREENING:**
- L5/S1 if radicular symptoms suspected
"""
    else:
        region_specific_tests = """
GENERAL MUSCULOSKELETAL OBJECTIVE ASSESSMENT:

**1. OBSERVATION:**
- Posture and alignment
- Gait analysis
- Muscle atrophy
- Swelling, bruising, deformity

**2. ACTIVE RANGE OF MOTION (AROM):**
- Test all relevant planes of motion
- Note pain, restriction, compensations

**3. PASSIVE RANGE OF MOTION (PROM):**
- Compare to AROM
- Assess end-feel
- Identify capsular patterns

**4. RESISTED TESTING:**
- Isolate contractile structures
- Assess strength and pain provocation

**5. SPECIAL TESTS:**
- Evidence-based tests for provisional diagnoses
- Cluster tests for higher diagnostic accuracy

**6. NEUROLOGICAL SCREENING:**
- If radicular symptoms present
- Myotomes, dermatomes, reflexes
- Neurodynamic tests

**7. PALPATION:**
- Identify tender structures
- Assess tissue texture, temperature, swelling

**8. FUNCTIONAL ASSESSMENT:**
- Test movements relevant to patient's goals
- Assess activity limitations
"""

    # NEW: Add pathophysiological mechanism context
    patho_context = ""
    if patho_data:
        pain_mechanism = patho_data.get('possible_source', '')
        pain_severity = patho_data.get('pain_severity', '')
        pain_irritability = patho_data.get('pain_irritability', '')

        if any([pain_mechanism, pain_severity, pain_irritability]):
            patho_context = "\n\nPAIN MECHANISM CONTEXT FOR ASSESSMENT APPROACH:\n"
            if pain_mechanism:
                patho_context += f"- Pain Source Classification: {pain_mechanism}\n"
            if pain_severity:
                patho_context += f"- Pain Severity (VAS): {pain_severity}/10\n"
            if pain_irritability:
                patho_context += f"- Pain Irritability: {pain_irritability}\n"
            patho_context += "\nNOTE: Consider pain mechanism when selecting test approach (e.g., neurogenic pain requires gentle neurodynamic testing).\n"

    # NEW: Intra-form adaptive context - learn from fields already filled on THIS form
    intra_form_context = ""
    if existing_inputs:
        analysis = analyze_objective_findings(existing_inputs)

        if analysis['tested_fields']:
            intra_form_context = "\n\n🔄 INTRA-FORM ADAPTIVE CONTEXT (Learning from previous fields on THIS objective assessment form):\n\n"

            # Show what's been tested and findings
            intra_form_context += "FIELDS ALREADY COMPLETED ON THIS FORM:\n"
            for field_name in analysis['tested_fields']:
                field_value = existing_inputs.get(field_name, '')
                # Determine status indicator
                if field_name in str(analysis['clear_areas']):
                    status = "✅ CLEAR"
                elif field_name in str(analysis['abnormal_areas']):
                    status = "⚠️ ABNORMAL"
                else:
                    status = "📝 TESTED"

                # Truncate long values
                display_value = field_value[:80] + "..." if len(field_value) > 80 else field_value
                intra_form_context += f"- {field_name.replace('_', ' ').title()}: {status}\n"
                intra_form_context += f"  Input: \"{display_value}\"\n"

            intra_form_context += "\n🎯 ADAPTIVE GUIDANCE FOR THIS FIELD:\n\n"

            # Conservative approach - always mention but adjust emphasis
            if analysis['clear_areas']:
                intra_form_context += f"✅ AREAS ALREADY CLEARED: {', '.join(analysis['clear_areas'])}\n"
                intra_form_context += "   → These areas show normal findings. Tone down suggestions for these (brief mention OK).\n"
                intra_form_context += "   → CONSERVATIVE NOTE: If clinically feasible and time permits, brief reassessment is acceptable for thoroughness.\n\n"

            if analysis['abnormal_areas']:
                intra_form_context += f"⚠️ AREAS WITH ABNORMAL FINDINGS: {', '.join(analysis['abnormal_areas'])}\n"
                intra_form_context += "   → DIG DEEPER: Provide detailed, specific tests to further investigate these findings.\n"
                intra_form_context += "   → Suggest tests that correlate with abnormal findings already documented.\n\n"

            if analysis['untested_fields']:
                intra_form_context += f"🔍 AREAS NOT YET TESTED: {', '.join(analysis['untested_fields'])}\n"
                intra_form_context += "   → If relevant to this field, provide comprehensive suggestions.\n\n"

            # Priority focus guidance
            intra_form_context += f"💡 PRIORITY FOCUS: {analysis['priority_focus'].replace('_', ' ').title()}\n\n"

            # Special cases
            if analysis['priority_focus'] == 'neural' and analysis['proximal_status'] == 'clear' and analysis['distal_status'] == 'clear':
                intra_form_context += "⚡ CLINICAL REASONING: Proximal and distal joints cleared → Consider neurogenic source.\n"
                intra_form_context += "   Suggest comprehensive neurological assessment (dermatomes, myotomes, reflexes, neurodynamics).\n\n"
            elif analysis['has_findings']:
                intra_form_context += "⚡ CLINICAL REASONING: Abnormal findings detected → Focus on confirming/ruling out suspected pathology.\n"
                intra_form_context += "   Suggest tests that provide differential diagnostic value.\n\n"
            elif len(analysis['clear_areas']) >= 2:
                intra_form_context += "⚡ CLINICAL REASONING: Multiple areas cleared → Consider referred pain, neural, or systemic causes.\n"
                intra_form_context += "   Don't over-test cleared structures; focus on untested areas and alternative diagnoses.\n\n"

            # Conservative reminder
            intra_form_context += "🔔 CONSERVATIVE APPROACH: Even for cleared areas, include brief mention like:\n"
            intra_form_context += "   'Proximal joint already assessed and clear, but if time permits, brief screen acceptable for completeness.'\n"
            intra_form_context += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{context}
{icf_guidance}
{patho_context}
{intra_form_context}

{field_guidance}

{region_specific_tests}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 REGIONAL EXAMINATION PRINCIPLE (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**IMPORTANT: Include Adjacent Joint Assessment in Your Objective Plan**

When planning objective tests, ALWAYS include screening for:

1. **ONE JOINT PROXIMAL** (above the presenting area)
   - Shoulder pain → Include cervical spine screen (Spurling's, ROM, neurological if needed)
   - Elbow pain → Include shoulder screen (AROM, impingement tests if relevant)
   - Wrist pain → Include elbow screen (resisted tests, neurodynamic)
   - Hip pain → Include lumbar spine/SI joint screen (ROM, neurological if needed)
   - Knee pain → Include hip screen (FABER, FADIR, AROM)
   - Ankle pain → Include knee screen (alignment, ROM)

2. **ONE JOINT DISTAL** (below the presenting area)
   - Neck pain → Include shoulder mobility screen (AROM, functional movements)
   - Shoulder pain → Include elbow/wrist screen (grip strength, functional assessment)
   - Elbow pain → Include wrist/hand function screen
   - Lumbar pain → Include hip mobility screen (FABER, FADIR, ROM)
   - Hip pain → Include knee function screen (gait, squat, alignment)
   - Knee pain → Include ankle/foot assessment (dorsiflexion, subtalar joint, foot posture)

**RATIONALE:**
- Referred pain patterns (e.g., cervical radiculopathy mimicking shoulder pain)
- Kinetic chain dysfunction (e.g., poor hip mobility contributing to knee pain)
- Compensatory patterns (e.g., ankle stiffness leading to knee valgus)
- Regional interdependence principle

**APPLICATION IN YOUR RESPONSE:**
- Briefly mention proximal/distal joint screening in your test recommendations
- Example: "Also screen cervical spine (Spurling's, ROM) to rule out referred pain"
- Keep it concise - 1-2 sentences max
- Don't include this if clearly not clinically relevant (e.g., obvious isolated acute trauma)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CLINICAL REASONING PROCESS FOR OBJECTIVE ASSESSMENT PLANNING:

STEP 1: SAFETY FIRST (Red Flags)
- Review any red flags identified in previous screens
- If serious pathology suspected → LIMIT objective assessment, recommend medical referral FIRST
- If cauda equina suspected → URGENT neurological examination ONLY

STEP 2: ASSESS IRRITABILITY
- HIGH irritability (severe pain, constant symptoms, easily aggravated) → MODIFIED approach with minimal provocation
- MODERATE irritability → MODIFIED approach with careful pacing
- LOW irritability → COMPREHENSIVE approach feasible

STEP 3: PRIORITIZE TESTS BASED ON PROVISIONAL DIAGNOSIS
- Start with tests most likely to confirm/rule out top differential diagnoses
- Use evidence-based test clusters (higher diagnostic accuracy)
- Order tests from least to most provocative

STEP 4: CONSIDER PSYCHOSOCIAL FACTORS (Yellow Flags)
- Fear-avoidance present → Explain tests clearly, start with least threatening
- Catastrophizing → Reassure, educate about what you're assessing
- Anxiety → Take time, build trust, explain expected sensations

STEP 5: PLAN MODIFICATION CRITERIA
Modify assessment if:
- Acute presentation (<48 hours) with high inflammation
- Severe pain (VAS >7/10 at rest)
- Marked fear of movement
- Recent trauma with possible fracture risk
- Neurological deficit that's progressive
- Patient fatigue or medical comorbidities

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANDATORY RULES FOR YOUR RESPONSE:

1. RECOMMENDATION CLARITY
   - State clearly: "COMPREHENSIVE WITHOUT MODIFICATION" OR "COMPREHENSIVE WITH MODIFICATIONS"
   - If red flags present, state "MODIFIED/LIMITED ASSESSMENT - Medical clearance recommended first"

2. CASE-SPECIFIC TEST SELECTION
   - Choose 6-10 specific tests from the region-specific list above
   - Prioritize based on provisional diagnosis
   - Explain WHY each test is important for THIS case

3. PRECAUTIONS & CONTRAINDICATIONS
   - Clearly state any tests that should be AVOIDED
   - Explain modification strategies if needed
   - Highlight safety considerations

4. EXPECTED FINDINGS
   - Based on subjective findings and provisional diagnosis
   - Predict likely positive tests
   - Explain how findings will guide diagnosis

5. STRUCTURED OUTPUT FORMAT (STRICT):

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OUTPUT FORMAT (Follow this exactly):

**RECOMMENDED ASSESSMENT APPROACH:**
[State clearly: "COMPREHENSIVE WITHOUT MODIFICATION" OR "COMPREHENSIVE WITH MODIFICATIONS" OR "MODIFIED/LIMITED - Medical clearance needed"]

**RATIONALE:**
[1-2 sentences explaining why this approach is appropriate based on irritability, red/yellow flags, and patient presentation]

**PRIORITY OBJECTIVE TESTS (in order):**

1. [Specific test name] - [What it assesses] - [Expected finding for this case]
2. [Specific test name] - [What it assesses] - [Expected finding for this case]
3. [Specific test name] - [What it assesses] - [Expected finding for this case]
4. [Specific test name] - [What it assesses] - [Expected finding for this case]
5. [Specific test name] - [What it assesses] - [Expected finding for this case]
6. [Specific test name] - [What it assesses] - [Expected finding for this case]
[Continue up to 8-10 tests if comprehensive assessment]

**PRECAUTIONS & CONTRAINDICATIONS:**
[List any tests to AVOID or perform with caution, with brief reasoning]
[If none, state "No specific contraindications identified"]

**EXPECTED POSITIVE FINDINGS:**
[Based on provisional diagnosis, list 2-3 tests most likely to be positive and why]

**CLINICAL REASONING SUMMARY:**
[1-2 sentences tying the test selection to the provisional diagnosis and treatment planning goals]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANT REMINDERS:
- Be SPECIFIC to this patient's body region (use exact anatomical terms from presenting complaint)
- Reference the provisional diagnosis in your reasoning
- Consider age-appropriate testing
- Think about diagnostic accuracy (sensitivity/specificity of test clusters)
- Safety first - if in doubt, modify or defer testing until medical clearance
"""


def get_pathophysiology_prompt(
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective: Optional[Dict[str, Any]] = None,
    diagnosis: Optional[str] = None,
    patho_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    IMPROVED: Determine the POSSIBLE SOURCE OF SYMPTOMS - helps classify pain mechanism.
    This helps determine if pain is: Somatic Local, Somatic Referred, Neurogenic, or Visceral.

    Endpoint: /api/ai_suggestion/patho/possible_source
    """
    context = build_clinical_context(age_sex, present_hist, past_hist, subjective=subjective, diagnosis=diagnosis)

    # Extract pathophysiology data if provided
    pain_info = ""
    if patho_data:
        area = patho_data.get('area_involved', '')
        symptom = patho_data.get('presenting_symptom', '')
        pain_type = patho_data.get('pain_type', '')
        pain_nature = patho_data.get('pain_nature', '')
        pain_severity = patho_data.get('pain_severity', '')
        irritability = patho_data.get('pain_irritability', '')
        healing_stage = patho_data.get('stage_healing', '')

        if any([area, symptom, pain_type, pain_nature]):
            pain_info = "\nPAIN CHARACTERISTICS:\n"
            if area: pain_info += f"- Area Involved: {area}\n"
            if symptom: pain_info += f"- Presenting Symptom: {symptom}\n"
            if pain_type: pain_info += f"- Pain Type: {pain_type}\n"
            if pain_nature: pain_info += f"- Pain Nature: {pain_nature}\n"
            if pain_severity: pain_info += f"- Pain Severity (VAS): {pain_severity}/10\n"
            if irritability: pain_info += f"- Pain Irritability: {irritability}\n"
            if healing_stage: pain_info += f"- Healing Stage: {healing_stage}\n"

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{context}
{pain_info}

TASK:
Determine the MOST LIKELY SOURCE OF SYMPTOMS for this case by classifying the pain mechanism.

THE 4 PAIN SOURCE CATEGORIES:

1. **SOMATIC LOCAL** - Pain from local tissue damage at the site of symptoms
   - Characteristics: Well-localized, sharp/aching, mechanical patterns
   - Tissue sources: Muscles, tendons, ligaments, joint capsule, bone, fascia at the SAME site
   - Examples: Acute ankle sprain, local muscle strain, tendinopathy
   - Key features: Pain location = tissue damage location, clear mechanical aggravating factors

2. **SOMATIC REFERRED** - Pain perceived away from the actual tissue pathology
   - Characteristics: Diffuse, poorly localized, may not follow dermatomal patterns
   - Tissue sources: Deep somatic structures (facet joints, discs, muscles, ligaments) projecting to distant areas
   - Examples: Cervical facet → shoulder pain, lumbar facet → buttock pain, myofascial trigger points
   - Key features: Pain location ≠ tissue damage location, visceral-like diffuse pattern, no neurological signs

3. **NEUROGENIC** - Pain from nervous system pathology
   - Characteristics: Burning, shooting, electric, follows dermatomal/nerve distribution, may have sensory changes
   - Tissue sources: Nerve root, peripheral nerve, spinal cord
   - Types:
     * Radicular: Dermatomal distribution, often with neuro signs (weakness, reflex changes, sensory loss)
     * Peripheral neuropathic: Follows peripheral nerve distribution
   - Examples: Sciatica (L5/S1 radiculopathy), carpal tunnel syndrome, thoracic outlet syndrome
   - Key features: Dermatomal/nerve territory distribution, neurological signs often present, shooting/burning quality

4. **VISCERAL** - Pain from internal organs
   - Characteristics: Deep, poorly localized, diffuse, may refer to somatic structures
   - Organ sources: Heart, lungs, GI tract, kidneys, reproductive organs
   - Examples: Cardiac → left shoulder/jaw, gallbladder → right shoulder, kidney → flank/groin
   - Key features: NOT mechanical (doesn't change with movement/position), may have autonomic signs (nausea, sweating), serious red flags

---

CLINICAL REASONING PROCESS:

STEP 1: RULE OUT VISCERAL (MOST IMPORTANT - RED FLAGS)
- Is pain completely unaffected by movement, position, or mechanical loading?
- Are there autonomic symptoms (nausea, sweating, palpitations)?
- Are there organ-specific symptoms (chest pain + SOB, abdominal pain + vomiting)?
- If YES → Likely VISCERAL, requires urgent medical referral

STEP 2: ASSESS FOR NEUROGENIC FEATURES
- Does pain follow a dermatomal or specific nerve distribution?
- Is there burning, shooting, electric, or stabbing quality?
- Are there neurological signs (weakness, numbness, altered reflexes)?
- Positive neurodynamic tests (SLR, ULNT, slump)?
- If YES → Likely NEUROGENIC (radicular or peripheral neuropathic)

STEP 3: DIFFERENTIATE SOMATIC LOCAL vs SOMATIC REFERRED
- Is pain well-localized and precisely points to tissue damage site? → SOMATIC LOCAL
- Is pain diffuse, poorly localized, doesn't match tissue damage site, no neuro signs? → SOMATIC REFERRED
- Consider: Trigger points, facet joints, discs can all cause referred somatic pain

---

MANDATORY RULES:
1. Analyze ALL available clinical data (subjective findings, pain characteristics, assessment findings)
2. Provide SPECIFIC reasoning for why you classify this case into one of the 4 categories
3. Reference specific clinical features that support your classification
4. If multiple sources are possible, rank by likelihood and explain why
5. If visceral source is suspected, clearly state RED FLAG and recommend immediate medical referral
6. Use evidence-based pain science and neurophysiology

OUTPUT FORMAT (STRICT):

Most Likely Pain Source: [Choose ONE: Somatic Local / Somatic Referred / Neurogenic / Visceral]

Clinical Reasoning:
1. [Key feature from history/exam that supports this classification]
2. [Key feature from history/exam that supports this classification]
3. [Key feature from history/exam that supports this classification]

Differential Considerations:
- [If other source types are possible, briefly explain why they're less likely]

Red Flags / Urgent Referral:
- [State "None identified" OR list specific red flags if visceral/serious pathology suspected]

Next Steps for Confirmation:
- [1-2 specific tests or findings that would further confirm the pain source classification]
"""


def get_chronic_factors_prompt(
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective: Optional[Dict[str, Any]] = None,
    diagnosis: Optional[str] = None,
    perspectives: Optional[Dict[str, Any]] = None,
    patho_data: Optional[Dict[str, Any]] = None,
    selected_categories: Optional[list] = None,
    existing_factors: Optional[str] = None,
) -> str:
    """
    IMPROVED: Identify SPECIFIC factors contributing to symptom maintenance and chronicity.
    Uses biopsychosocial framework and pain science principles.

    Endpoint: /api/ai_suggestion/chronic/specific_factors
    """
    context = build_clinical_context(age_sex, present_hist, past_hist, subjective=subjective, diagnosis=diagnosis, perspectives=perspectives)

    # Add pathophysiology context if available
    patho_context = ""
    if patho_data:
        pain_severity = patho_data.get('pain_severity', '')
        pain_nature = patho_data.get('pain_nature', '')
        irritability = patho_data.get('pain_irritability', '')
        healing_stage = patho_data.get('stage_healing', '')

        if any([pain_severity, pain_nature, irritability, healing_stage]):
            patho_context = "\nPAIN CHARACTERISTICS:\n"
            if pain_severity: patho_context += f"- Pain Severity: {pain_severity}/10\n"
            if pain_nature: patho_context += f"- Pain Nature: {pain_nature}\n"
            if irritability: patho_context += f"- Irritability: {irritability}\n"
            if healing_stage: patho_context += f"- Healing Stage: {healing_stage}\n"

    # User's selected categories
    categories_context = ""
    if selected_categories:
        categories_context = f"\n\nUSER'S SELECTED MAINTENANCE CATEGORIES:\n{', '.join(selected_categories)}\nFocus your analysis on these categories.\n"

    # User's existing input
    existing_context = ""
    if existing_factors:
        existing_context = f"\n\nUSER'S INITIAL THOUGHTS:\n{existing_factors}\nExpand on this with evidence-based reasoning and additional factors they may have missed.\n"

    return f"""{SYSTEM_ROLES['biopsychosocial']}

{context}
{patho_context}
{categories_context}
{existing_context}

TASK:
Identify SPECIFIC MODIFIABLE FACTORS that are maintaining or contributing to chronicity for THIS case.
Use the biopsychosocial model to analyze across all domains.

THE 5 DOMAINS OF MAINTENANCE FACTORS (Biopsychosocial Model):

1. **PHYSICAL / BIOMECHANICAL FACTORS**
   - Tissue pathology still present (incomplete healing, ongoing inflammation)
   - Movement dysfunction (poor motor control, compensatory patterns, guarding)
   - Deconditioning (muscle weakness, reduced endurance, cardiovascular fitness loss)
   - Postural stress (sustained positions at work/home)
   - Joint stiffness or muscle tightness
   - Altered movement patterns avoiding pain
   - Poor ergonomics
   Examples for musculoskeletal:
   - Rotator cuff weakness maintaining shoulder impingement
   - Hip abductor weakness contributing to knee valgus and patellofemoral pain
   - Poor lumbar control and endurance in chronic low back pain

2. **PSYCHOLOGICAL FACTORS** (Yellow Flags)
   - Fear-avoidance beliefs ("movement will cause more damage")
   - Pain catastrophizing (magnifying threat value of pain)
   - Anxiety about pain or re-injury
   - Depression or low mood
   - Poor self-efficacy ("I can't control this")
   - Hypervigilance to body sensations
   - External locus of control (passive coping)
   - Stress and emotional distress
   - Pain-related worry and rumination
   Examples:
   - Fear of bending maintaining protective movement patterns
   - Catastrophizing beliefs reducing activity participation
   - Low self-efficacy preventing engagement in exercise

3. **SOCIAL / ENVIRONMENTAL CONDITIONS**
   - Lack of social support (isolation, unsupportive family)
   - Financial stress (inability to afford treatment, fear of job loss)
   - Poor living conditions (stairs with mobility issues, no safe exercise space)
   - Cultural beliefs about pain and disability
   - Language barriers affecting healthcare access
   - Litigation or compensation issues
   - Overprotective family members reinforcing sick role
   Examples:
   - Lack of family support reducing exercise adherence
   - Financial stress increasing central sensitization
   - Home environment barriers preventing activity

4. **LIFESTYLE / BEHAVIORAL FACTORS**
   - Sedentary behavior and physical inactivity
   - Poor sleep quality or quantity (< 7 hours, fragmented)
   - Smoking (delays healing, increases pain sensitivity)
   - Excessive alcohol use
   - Poor nutrition (obesity, inflammatory diet)
   - Medication overuse (opioids, NSAIDs)
   - Boom-bust activity patterns (overdo then crash)
   - Avoidance of valued activities
   - Poor pacing strategies
   Examples:
   - Sleep deprivation lowering pain threshold
   - Boom-bust cycles perpetuating flare-ups
   - Obesity increasing joint loading

5. **WORK-RELATED FACTORS**
   - Heavy physical demands (lifting, repetitive strain)
   - Prolonged static postures (computer work, driving)
   - Unsupportive work environment
   - Job dissatisfaction or high work stress
   - Fear of job loss due to injury
   - Inadequate workplace accommodations
   - Return to work pressure
   - Poor ergonomic setup
   Examples:
   - Prolonged sitting with poor lumbar support
   - Repetitive overhead work maintaining shoulder pain
   - High job stress increasing muscle tension

---

PAIN SCIENCE CONSIDERATIONS (Why Pain Persists):

**Central Sensitization Indicators:**
- Pain out of proportion to tissue damage
- Widespread pain beyond original area
- Allodynia (non-painful stimuli cause pain)
- Hyperalgesia (increased pain sensitivity)
- Multiple body sites affected
→ If present, psychological and lifestyle factors become MORE important

**Acute vs Chronic Transition (>3 months):**
- Acute: Tissue damage is primary driver → Physical factors dominate
- Subacute (4-12 weeks): Transition phase → Mix of tissue + nervous system changes
- Chronic (>3 months): Central nervous system changes dominant → Biopsychosocial factors critical

**Modifiable vs Non-Modifiable:**
- FOCUS on factors that can be changed with physiotherapy, education, behavior change
- Acknowledge non-modifiable (age, genetics) but don't dwell on them

---

CLINICAL REASONING PROCESS:

STEP 1: Review the PAIN DURATION and HEALING STAGE
- Acute (0-72h): Focus on tissue protection, inflammation management
- Subacute (4-21 days): Begin addressing biomechanical and behavioral factors
- Chronic (>3 weeks): Strong focus on psychosocial and lifestyle factors

STEP 2: Analyze ACROSS ALL 5 DOMAINS
- Physical: What movement dysfunctions, deconditioning, or biomechanical issues?
- Psychological: Any fear-avoidance, catastrophizing, low self-efficacy?
- Social: Support system? Environmental barriers?
- Lifestyle: Sleep, activity levels, smoking, weight?
- Work: Job demands? Ergonomics? Stress?

STEP 3: Prioritize MODIFIABLE FACTORS
- What can be addressed with physiotherapy?
- What requires education or behavior change?
- What needs multidisciplinary input (psychology, occupational therapy)?

STEP 4: Connect to CLINICAL FINDINGS
- Reference specific findings from subjective/objective assessment
- Explain HOW each factor maintains symptoms
- Use pain science to explain mechanisms

---

MANDATORY RULES:
1. Identify 4-6 SPECIFIC factors across multiple domains (not just physical!)
2. Each factor must be MODIFIABLE (can be addressed with intervention)
3. Be CASE-SPECIFIC - reference actual findings from this patient
4. Explain HOW each factor maintains or worsens symptoms (mechanism)
5. Prioritize factors by importance and modifiability
6. If chronic pain (>3 months), MUST include psychosocial factors
7. Use pain science language (central sensitization, fear-avoidance, etc.)
8. Do NOT suggest treatments - only identify maintaining factors

OUTPUT FORMAT (STRICT):

Maintenance Factor Analysis:

**PHYSICAL / BIOMECHANICAL:**
- [Specific factor] → [How it maintains symptoms]

**PSYCHOLOGICAL:**
- [Specific factor] → [How it maintains symptoms]
- [If none evident, state "No significant psychological barriers identified"]

**SOCIAL / ENVIRONMENTAL:**
- [Specific factor] → [How it maintains symptoms]
- [If none evident, state "No significant social barriers identified"]

**LIFESTYLE / BEHAVIORAL:**
- [Specific factor] → [How it maintains symptoms]

**WORK-RELATED:**
- [Specific factor] → [How it maintains symptoms]
- [If not applicable, state "Not work-related"]

Priority Ranking (Top 3 to address first):
1. [Most important modifiable factor and why it's priority]
2. [Second most important]
3. [Third most important]

Clinical Reasoning Summary:
[1-2 sentences explaining overall pattern - e.g., "This chronic case shows strong biopsychosocial maintenance with fear-avoidance and deconditioning as primary drivers" OR "Acute presentation with primarily biomechanical factors and no psychosocial barriers"]
"""


def get_clinical_flags_prompt(
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective: Optional[Dict[str, Any]] = None,
    perspectives: Optional[Dict[str, Any]] = None,
    patho_data: Optional[Dict[str, Any]] = None,
    chronic_factors: Optional[Dict[str, Any]] = None,
) -> str:
    """
    IMPROVED: Comprehensive clinical flags screening covering ALL 5 flag types.
    Critical for identifying serious pathology, psychosocial barriers, and occupational risks.

    Endpoint: /api/ai_suggestion/clinical_flags/<patient_id>/suggest
    """
    context = build_clinical_context(age_sex, present_hist, past_hist, subjective=subjective, perspectives=perspectives)

    # Add pathophysiology context
    patho_context = ""
    if patho_data:
        pain_severity = patho_data.get('pain_severity', '')
        pain_nature = patho_data.get('pain_nature', '')
        possible_source = patho_data.get('possible_source', '')

        if any([pain_severity, pain_nature, possible_source]):
            patho_context = "\nPAIN ANALYSIS:\n"
            if pain_severity: patho_context += f"- Severity: {pain_severity}/10\n"
            if pain_nature: patho_context += f"- Nature: {pain_nature}\n"
            if possible_source: patho_context += f"- Possible Source: {possible_source}\n"

    # Add chronic factors context
    chronic_context = ""
    if chronic_factors:
        factors = chronic_factors.get('maintenance_factors', '')
        if factors:
            chronic_context = f"\n\nIDENTIFIED MAINTENANCE FACTORS:\n{factors}\n"

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{context}
{patho_context}
{chronic_context}

TASK:
Perform COMPREHENSIVE CLINICAL FLAGS SCREENING across ALL 5 flag categories.
This is a CRITICAL SAFETY screening to identify serious pathology, barriers to recovery, and occupational risks.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

THE 5 TYPES OF CLINICAL FLAGS:

🔴 **RED FLAGS** - SERIOUS PATHOLOGY (URGENT MEDICAL REFERRAL REQUIRED)

**PURPOSE:** Identify signs/symptoms suggesting serious underlying disease requiring immediate medical attention

**Key Categories:**
1. **Fracture Red Flags:**
   - Significant trauma history
   - Prolonged corticosteroid use + minor trauma
   - Age >50 with minor trauma (osteoporotic fracture risk)
   - Inability to weight bear

2. **Infection Red Flags:**
   - Fever, night sweats, chills
   - Recent bacterial infection or immunosuppression
   - IV drug use
   - Unwell, systemically ill

3. **Cancer Red Flags:**
   - Age >50 with new onset pain
   - History of cancer
   - Unexplained weight loss
   - Pain at night not relieved by rest
   - Constant progressive pain

4. **Cauda Equina Syndrome (Spinal):**
   - Saddle anesthesia
   - Bilateral leg weakness or numbness
   - Bowel/bladder dysfunction (loss of control, retention)
   - Sexual dysfunction
   - Progressive neurological deficit

5. **Inflammatory/Systemic Disease:**
   - Morning stiffness >1 hour (inflammatory arthritis)
   - Age <20 with back pain (ankylosing spondylitis)
   - Peripheral joint symptoms (RA, psoriatic arthritis)
   - Inflammatory markers elevated

6. **Vascular/Cardiac:**
   - Chest pain with exertion (cardiac)
   - Calf pain with walking that stops with rest (claudication)
   - Pulselessness, color changes
   - Left shoulder/arm/jaw pain with exertion

7. **Serious Neurological:**
   - Rapidly progressing weakness
   - Upper motor neuron signs (hyperreflexia, clonus, Babinski+)
   - Drop attacks, loss of consciousness
   - Severe unrelenting headache

**CRITICAL:** If ANY red flags present → STATE "URGENT MEDICAL REFERRAL REQUIRED"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟠 **ORANGE FLAGS** - PSYCHIATRIC/PSYCHOLOGICAL DISTRESS

**PURPOSE:** Identify mental health conditions that require specialist referral (beyond PT scope)

**Indicators:**
- **Severe Depression:** Suicidal ideation, severe functional impairment, inability to engage
- **Severe Anxiety:** Panic disorder, severe generalized anxiety affecting daily life
- **PTSD:** Trauma-related symptoms, flashbacks, severe avoidance
- **Substance Abuse:** Alcohol or drug dependency
- **Personality Disorders:** Severe emotional dysregulation
- **Active Psychiatric Crisis:** Psychosis, mania, severe self-harm

**Differentiate from Yellow Flags:**
- **Orange** = Clinical psychiatric disorder requiring specialist treatment
- **Yellow** = Psychosocial risk factors within PT scope (fear-avoidance, mild anxiety, low mood)

**CRITICAL:** If present → STATE "PSYCHIATRIC/PSYCHOLOGY REFERRAL RECOMMENDED"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟡 **YELLOW FLAGS** - PSYCHOSOCIAL RISK FACTORS FOR CHRONICITY

**PURPOSE:** Identify modifiable psychological/social factors that predict poor outcome and chronicity

**Key Indicators:**
1. **Beliefs and Appraisals:**
   - Fear-avoidance beliefs ("movement will cause more damage")
   - Pain catastrophizing (thinking worst will happen)
   - Belief that pain is harmful and disabling
   - Expectation of passive treatment only

2. **Emotional Responses:**
   - Anxiety about pain or re-injury (not clinical anxiety disorder)
   - Low mood, irritability, frustration (not clinical depression)
   - Loss of sense of enjoyment

3. **Pain Behaviors:**
   - Reduced activity levels, avoidance of normal activity
   - Increased rest, withdrawal from social activities
   - Excessive reliance on aids (braces, walking sticks when not needed)

4. **Compensation/Medico-legal:**
   - Pending litigation or compensation claim
   - Belief that work caused problem and someone is at fault
   - Financial incentive for ongoing disability

5. **Family/Social:**
   - Overprotective family or lack of support
   - Socially isolated
   - Excessive solicitous behavior from spouse

6. **Treatment Expectations:**
   - Expectation of "magic cure"
   - Passive attitude to rehabilitation
   - Poor compliance with previous treatment

**These are MODIFIABLE within PT scope with education, graded exposure, cognitive-behavioral approaches**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚫ **BLACK FLAGS** - OCCUPATIONAL/SYSTEMIC/ENVIRONMENTAL BARRIERS

**PURPOSE:** Identify system-level, organizational, and environmental obstacles to recovery

**Key Indicators:**
1. **Healthcare System Barriers:**
   - Delays in accessing treatment
   - Conflicting advice from multiple healthcare providers
   - Iatrogenic factors (medical system causing harm)
   - Inappropriate imaging/investigations creating fear

2. **Policy/Insurance:**
   - Insurance company disputes or denials
   - Complex compensation systems
   - Workplace injury claim complications

3. **Occupational System Issues:**
   - Employer unwilling to accommodate modified duties
   - No graded return-to-work option available
   - Unsafe working conditions
   - Organizational culture (blame, lack of support)

4. **Environmental Barriers:**
   - Physical environment barriers (no wheelchair access, stairs)
   - Lack of transport to attend treatment
   - Geographic isolation (rural, no services nearby)

5. **Social/Economic Systems:**
   - Poverty, financial hardship
   - Language/cultural barriers to care
   - Systemic discrimination or racism

**These require advocacy, system navigation, multidisciplinary collaboration**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔵 **BLUE FLAGS** - WORK-RELATED PERCEPTUAL/ATTITUDINAL FACTORS

**PURPOSE:** Identify individual's perceptions and beliefs about their work and its relationship to their injury

**Key Indicators:**
1. **Job Satisfaction:**
   - High job dissatisfaction or stress
   - Belief that current job is too demanding
   - Desire to change jobs or career

2. **Work-Related Beliefs:**
   - Strong belief that work caused the injury
   - Fear that returning to work will re-injure
   - Perception that workplace is dangerous
   - All-or-nothing thinking about work capacity

3. **Worker Attitudes:**
   - Reluctance to return to current workplace
   - Belief that modified/light duties are not "real work"
   - Perception of poor workplace relationships

4. **Job Demands (Perceived):**
   - Belief that physical demands are too high (even if objectively manageable)
   - Overestimation of job demands
   - Underestimation of own capacity

**Different from Black Flags:**
- **Blue** = Individual's perceptions and attitudes about work
- **Black** = Actual systemic/organizational barriers

**These require work-focused CBT, graded return-to-work, workplace liaison**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CLINICAL REASONING PROCESS:

STEP 1: RED FLAGS FIRST (Safety Priority)
- Systematically screen for serious pathology across all categories
- If ANY red flags present → IMMEDIATE medical referral
- Document specific findings that raise concern

STEP 2: ORANGE FLAGS (Mental Health Crisis)
- Screen for psychiatric conditions beyond PT scope
- If present → Referral to psychology/psychiatry BEFORE continuing PT

STEP 3: YELLOW FLAGS (Psychosocial Risks)
- Identify modifiable psychological/social factors
- Multiple yellow flags = high chronicity risk
- These ARE within PT scope to address

STEP 4: BLACK FLAGS (System Barriers)
- Identify obstacles in healthcare system, policy, environment
- Require advocacy and collaboration with other professionals

STEP 5: BLUE FLAGS (Work Perceptions)
- Assess work-related beliefs and attitudes
- Important for return-to-work planning

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANDATORY RULES:
1. Screen SYSTEMATICALLY across ALL 5 flag categories (don't skip any)
2. Be SPECIFIC to this case - reference actual findings from patient history
3. If NO flags in a category, state "None identified"
4. For red flags: Use language like "CONCERN FOR..." or "SUGGESTIVE OF..."
5. Prioritize patient safety - err on the side of caution with red flags
6. Do NOT list generic possibilities - only flag what is actually present
7. Connect flags to clinical findings and patient statements

OUTPUT FORMAT (STRICT):

🔴 RED FLAGS (Serious Pathology):
[If ANY present → state each flag specifically and conclude with "→ URGENT MEDICAL REFERRAL REQUIRED"]
[If none → "None identified"]

🟠 ORANGE FLAGS (Psychiatric):
[If present → state specific concern and "→ PSYCHIATRIC/PSYCHOLOGY REFERRAL RECOMMENDED"]
[If none → "None identified"]

🟡 YELLOW FLAGS (Psychosocial Risk):
[List each flag identified with brief explanation of how it affects prognosis]
[If none → "None identified"]

⚫ BLACK FLAGS (System/Environmental Barriers):
[List each barrier identified]
[If none → "None identified"]

🔵 BLUE FLAGS (Work-Related Perceptions):
[List each work-related belief/attitude identified]
[If not applicable → "Not applicable - not work-related injury" OR "None identified"]

Overall Risk Assessment:
[1-2 sentences summarizing overall clinical picture regarding safety, barriers to recovery, and prognosis]
"""


# ─────────────────────────────────────────────────────────────────────────────
# TREATMENT PLANNING
# ─────────────────────────────────────────────────────────────────────────────

def get_proximal_distal_joints(body_region: Optional[str], present_hist: str) -> str:
    """
    Determine which proximal and distal joints should be assessed based on the affected region.
    This follows the clinical principle of always assessing one joint above and one joint below.
    """
    # Joint assessment mapping
    joint_chains = {
        'shoulder': {
            'affected': 'shoulder (glenohumeral joint)',
            'proximal': 'cervical spine and scapulothoracic joint',
            'distal': 'elbow',
            'rationale': 'Cervical pathology can refer to shoulder; scapular dyskinesis affects shoulder mechanics; elbow issues can alter shoulder biomechanics'
        },
        'elbow': {
            'affected': 'elbow',
            'proximal': 'shoulder and scapulothoracic joint',
            'distal': 'wrist and hand',
            'rationale': 'Shoulder instability affects elbow stress; wrist/hand mechanics influence elbow loading'
        },
        'wrist': {
            'affected': 'wrist',
            'proximal': 'elbow and forearm',
            'distal': 'hand and fingers (MCP, PIP, DIP joints)',
            'rationale': 'Elbow/forearm position affects wrist mechanics; hand pathology can cause compensatory wrist stress'
        },
        'hand': {
            'affected': 'hand/fingers',
            'proximal': 'wrist',
            'distal': 'individual finger joints (MCP, PIP, DIP)',
            'rationale': 'Wrist position affects hand function; assess each finger joint for comprehensive evaluation'
        },
        'hip': {
            'affected': 'hip',
            'proximal': 'lumbar spine and sacroiliac joint',
            'distal': 'knee',
            'rationale': 'Lumbar/SI pathology commonly refers to hip; knee mechanics affect hip loading'
        },
        'knee': {
            'affected': 'knee',
            'proximal': 'hip',
            'distal': 'ankle and foot',
            'rationale': 'Hip weakness/restriction alters knee biomechanics; ankle/foot dysfunction increases knee stress'
        },
        'ankle': {
            'affected': 'ankle',
            'proximal': 'knee',
            'distal': 'foot (midfoot, forefoot, and toes)',
            'rationale': 'Knee alignment affects ankle stress; foot mechanics directly influence ankle function'
        },
        'foot': {
            'affected': 'foot',
            'proximal': 'ankle',
            'distal': 'individual toe joints and metatarsals',
            'rationale': 'Ankle dorsiflexion affects forefoot loading; toe pathology alters foot mechanics'
        },
        'lumbar': {
            'affected': 'lumbar spine',
            'proximal': 'thoracic spine',
            'distal': 'hip and sacroiliac joint',
            'rationale': 'Thoracic stiffness increases lumbar stress; hip/SI dysfunction causes compensatory lumbar loading'
        },
        'cervical': {
            'affected': 'cervical spine',
            'proximal': 'thoracic spine and scapular region',
            'distal': 'shoulder',
            'rationale': 'Thoracic kyphosis affects cervical alignment; shoulder dysfunction can cause cervical compensation'
        },
        'thoracic': {
            'affected': 'thoracic spine',
            'proximal': 'cervical spine',
            'distal': 'lumbar spine and rib cage',
            'rationale': 'Cervical dysfunction affects upper thoracic; lumbar issues can cause thoracolumbar junction stress'
        }
    }

    if not body_region or body_region not in joint_chains:
        return "\nREGIONAL ASSESSMENT: Unable to determine specific region. Assess adjacent structures based on clinical presentation."

    joint_info = joint_chains[body_region]

    return f"""
REGIONAL ASSESSMENT STRATEGY (One Joint Above, One Joint Below):

Primary Region: {joint_info['affected']}
Proximal Joint to Assess: {joint_info['proximal']}
Distal Joint to Assess: {joint_info['distal']}

Clinical Rationale: {joint_info['rationale']}

MANDATORY: Include screening of proximal and distal joints in your test recommendations.
"""

def get_initial_plan_field_prompt(
    field: str,
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective: Optional[Dict[str, Any]] = None,
    diagnosis: Optional[str] = None,
    selection: Optional[str] = None,
    perspectives: Optional[Dict[str, Any]] = None,
    patho_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    IMPROVED: Field-specific ASSESSMENT planning guidance (not treatment planning).
    This screen is about deciding which physical examination tests to perform.

    Now includes:
    - Proximal and distal joint assessment recommendations
    - Test modifications based on patient perspectives (fear, pain, expectations)
    - Specific restrictions and precautions
    - NEW: Contraindications based on pain mechanism, severity, and irritability

    Endpoint: /api/ai_suggestion/initial_plan/<field>
    """

    # Field names mapping to readable labels
    field_names = {
        'active_movements': 'Active Movements Examination',
        'passive_movements': 'Passive Movements Examination',
        'passive_over_pressure': 'Passive Over Pressure Testing',
        'resisted_movements': 'Resisted Movements Testing',
        'combined_movements': 'Combined Movements Testing',
        'special_tests': 'Special Tests',
        'neurodynamic': 'Neurodynamic Examination',
        'neurodynamic_examination': 'Neurodynamic Examination',
    }
    component = field_names.get(field, field.replace('_', ' ').title())

    context = build_clinical_context(age_sex, present_hist, past_hist, subjective=subjective, diagnosis=diagnosis, perspectives=perspectives)

    # Detect body region for specific test recommendations
    body_region = detect_body_region(present_hist)
    icf_core_set = ICF_CORE_SETS.get(body_region) if body_region else None

    # Determine proximal and distal joints to assess
    proximal_distal_guidance = get_proximal_distal_joints(body_region, present_hist)

    # Field-specific assessment guidance
    field_specific_guidance = {
        'active_movements': """
For ACTIVE MOVEMENTS EXAMINATION - Patient performs movements independently:

PURPOSE:
- Assess willingness to move (pain behavior, kinesiophobia)
- Screen for ROM limitations and pain patterns
- Observe movement quality, compensations, and functional patterns
- Identify which movements reproduce symptoms

INCLUDE IN YOUR SUGGESTIONS:
- Specific active movements to test for THIS body region (e.g., shoulder flexion, abduction, ER, IR)
- Expected pain patterns based on subjective findings
- What to observe (ROM, quality, compensations, symptom reproduction)
- Functional movements relevant to patient's goals

CLINICAL REASONING TO PROVIDE:
- Why these movements are priority for this case
- Expected positive findings based on subjective examination
- How findings will guide further testing
- Safety considerations if marked as "precaution"
- Why contraindicated if marked as such""",

        'passive_movements': """
For PASSIVE MOVEMENTS EXAMINATION - Examiner moves the limb while patient relaxes:

PURPOSE:
- Assess available ROM (capsular vs muscular restrictions)
- Differentiate contractile vs non-contractile structures
- Assess end-feel (normal, hard, soft, empty, springy)
- Compare to active ROM findings

INCLUDE IN YOUR SUGGESTIONS:
- Specific passive movements to test for THIS body region
- Expected end-feel for each movement
- Comparison to active ROM findings
- Capsular pattern assessment if relevant

CLINICAL REASONING TO PROVIDE:
- Why passive testing is indicated for this case
- Expected findings based on subjective/active movement findings
- End-feel significance for diagnosis
- Precautions if joint effusion, acute inflammation, or instability present""",

        'passive_over_pressure': """
For PASSIVE OVER PRESSURE TESTING - Gentle overpressure at end of available ROM:

PURPOSE:
- Stress specific structures (capsule, ligaments, tendons)
- Differentiate between pain and restriction
- Assess end-feel quality
- Provocation testing for diagnosis

INCLUDE IN YOUR SUGGESTIONS:
- Which movements should receive overpressure for THIS case
- Expected positive findings
- Structures being stressed
- When to apply vs when to avoid

CLINICAL REASONING TO PROVIDE:
- Why overpressure is indicated
- Red flags that contraindicate overpressure (acute injury, severe irritability, instability)
- Expected symptom reproduction
- Diagnostic implications""",

        'resisted_movements': """
For RESISTED MOVEMENTS TESTING - Isometric muscle contraction against resistance:

PURPOSE:
- Assess contractile tissue integrity (muscle, tendon, MTJ)
- Isolate muscle/tendon from joint structures
- Differentiate tendinopathy from joint pathology
- Assess muscle strength and pain provocation

INCLUDE IN YOUR SUGGESTIONS:
- Specific resisted tests for THIS body region
- Expected findings (strong/painful, weak/painful, weak/painless)
- Muscles being tested
- Testing positions

CLINICAL REASONING TO PROVIDE:
- Why these tests are priority for this case
- Expected pattern (e.g., painful arc in subacromial impingement)
- Tendinopathy vs muscle strain differentiation
- Precautions for acute muscle tears or severe tendinopathy""",

        'combined_movements': """
For COMBINED MOVEMENTS TESTING - Testing movements in combination to stress specific structures:

PURPOSE:
- Stress specific anatomical structures that single-plane movements miss
- Reproduce functional movement patterns
- Assess for instability or impingement
- Provocation testing for complex pathologies

INCLUDE IN YOUR SUGGESTIONS:
- Relevant combined movement tests for THIS case
- What structures are being stressed
- Expected positive findings
- Functional relevance

CLINICAL REASONING TO PROVIDE:
- Why combined movements are necessary
- Specific pathologies being tested for
- Interpretation of positive findings
- Safety considerations""",

        'special_tests': """
For SPECIAL TESTS - Specific orthopedic/neurological tests for diagnosis:

PURPOSE:
- Confirm or rule out specific diagnoses
- Assess structural integrity (ligaments, meniscus, labrum, etc.)
- Neurological screening (reflexes, sensation, myotomes, dermatomes)
- Provocative tests for specific pathologies

INCLUDE IN YOUR SUGGESTIONS:
- TOP 3-5 most relevant special tests for THIS case
- What each test assesses (e.g., "Neer's test for subacromial impingement")
- Sensitivity/specificity if high
- Positive test interpretation

CLINICAL REASONING TO PROVIDE:
- Why these specific tests are indicated
- Expected cluster of positive tests
- Differential diagnosis implications
- Red flag tests that should be included (if any)""",

        'neurodynamic': """
For NEURODYNAMIC EXAMINATION - Neural tissue mechanosensitivity and mobility:

PURPOSE:
- Assess peripheral nerve mechanosensitivity
- Differentiate neural vs musculoskeletal pain
- Screen for nerve compression or entrapment
- Assess nervous system mobility

INCLUDE IN YOUR SUGGESTIONS:
- Relevant neurodynamic tests for THIS case (e.g., ULNT, SLR, slump)
- Nerve distributions being tested
- Differentiating maneuvers (structural vs symptomatic)
- Expected findings

CLINICAL REASONING TO PROVIDE:
- Why neurodynamic testing is indicated
- Expected positive findings based on symptoms
- Interpretation (positive vs negative)
- Precautions for acute radiculopathy or myelopathy
- Red flags that contraindicate testing""",

        'neurodynamic_examination': """
For NEURODYNAMIC EXAMINATION - Neural tissue mechanosensitivity and mobility:

PURPOSE:
- Assess peripheral nerve mechanosensitivity
- Differentiate neural vs musculoskeletal pain
- Screen for nerve compression or entrapment
- Assess nervous system mobility

INCLUDE IN YOUR SUGGESTIONS:
- Relevant neurodynamic tests for THIS case (e.g., ULNT, SLR, slump)
- Nerve distributions being tested
- Differentiating maneuvers (structural vs symptomatic)
- Expected findings

CLINICAL REASONING TO PROVIDE:
- Why neurodynamic testing is indicated
- Expected positive findings based on symptoms
- Interpretation (positive vs negative)
- Precautions for acute radiculopathy or myelopathy
- Red flags that contraindicate testing"""
    }

    specific_guidance = field_specific_guidance.get(field, "")

    # User's selection context
    selection_context = ""
    if selection:
        selection_context = f"\n\nUSER'S SELECTION: {selection}\n"
        if selection == "Mandatory assessment":
            selection_context += "Provide guidance on essential tests that MUST be performed for safe and effective diagnosis."
        elif selection == "Assessment with precaution":
            selection_context += "Explain what precautions are needed, why they're necessary, and how to safely perform the assessment."
        elif selection == "Absolutely Contraindicated":
            selection_context += "Explain WHY these tests are unsafe for this patient and what alternative assessments should be used instead."

    # ICF Core Set guidance
    icf_guidance = ""
    if icf_core_set:
        icf_guidance = f"\nRELEVANT CONDITION: {icf_core_set['name']}\nFocus your test recommendations on this condition.\n"

    # Patient perspectives-based modifications
    modification_guidance = ""
    if perspectives:
        affective = perspectives.get('affective_aspect', '')
        locus = perspectives.get('locus_of_control', '')
        awareness = perspectives.get('consequences_awareness', '')

        if affective or locus or awareness:
            modification_guidance = "\n\nPATIENT PSYCHOLOGICAL PROFILE - Modify testing accordingly:\n"
            if 'fear' in str(affective).lower() or 'anxiety' in str(affective).lower():
                modification_guidance += "- Patient exhibits fear/anxiety: Use gradual progression, explain each test before performing, start with less provocative tests\n"
            if 'anger' in str(affective).lower() or 'frustration' in str(affective).lower():
                modification_guidance += "- Patient shows frustration/anger: Be empathetic, explain rationale clearly, involve patient in decision-making\n"
            if locus == 'External':
                modification_guidance += "- External locus of control: Provide clear guidance, take active role in directing assessment\n"
            elif locus == 'Internal':
                modification_guidance += "- Internal locus of control: Encourage self-monitoring, explain how they can help during tests\n"
            if awareness == 'Unaware':
                modification_guidance += "- Limited consequence awareness: Educate during testing about what you're assessing and why\n"

    # NEW: Add pathophysiological mechanism context for contraindication warnings
    patho_contraindications = ""
    if patho_data:
        pain_mechanism = patho_data.get('possible_source', '')
        pain_severity = patho_data.get('pain_severity', '')
        pain_irritability = patho_data.get('pain_irritability', '')
        healing_stage = patho_data.get('stage_healing', '')

        if any([pain_mechanism, pain_severity, pain_irritability]):
            patho_contraindications = "\n\n⚠️ CONTRAINDICATION WARNINGS (PAIN MECHANISM BASED):\n"
            if pain_severity:
                try:
                    severity_num = int(pain_severity)
                    if severity_num >= 7:
                        patho_contraindications += f"- HIGH PAIN SEVERITY ({severity_num}/10): Limit aggressive testing, prioritize gentle examination\n"
                except (ValueError, TypeError):
                    pass
            if pain_irritability and 'high' in str(pain_irritability).lower():
                patho_contraindications += "- HIGH IRRITABILITY: Avoid provocative tests that may flare symptoms significantly\n"
            if healing_stage and 'acute' in str(healing_stage).lower():
                patho_contraindications += "- ACUTE HEALING STAGE: Protect healing tissues, avoid end-range stressing\n"
            if pain_mechanism:
                if 'neurogenic' in str(pain_mechanism).lower():
                    patho_contraindications += "- NEUROGENIC PAIN: Caution with neurodynamic testing, may provoke significant symptoms\n"
                elif 'visceral' in str(pain_mechanism).lower():
                    patho_contraindications += "- VISCERAL PAIN SUSPECTED: Contraindicated for musculoskeletal testing - requires medical referral\n"
            patho_contraindications += "\n⚠️ MANDATORY: Flag any contraindicated tests based on above warnings.\n"

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{context}
{icf_guidance}
{proximal_distal_guidance}
TARGET ASSESSMENT CATEGORY: {component}
{selection_context}
{modification_guidance}
{patho_contraindications}

{specific_guidance}

CRITICAL INSTRUCTIONS:
This is an ASSESSMENT PLANNING screen, NOT a treatment planning screen.
Your job is to suggest which PHYSICAL EXAMINATION TESTS to perform, not treatment interventions.

STRICT RULES FOR YOUR RESPONSE:
1) ASSESSMENT FOCUS (MOST IMPORTANT)
   - Suggest specific TESTS/EXAMINATIONS to perform
   - DO NOT suggest treatments, exercises, or interventions
   - Focus on WHAT to test and WHAT to look for

2) CASE-SPECIFIC RECOMMENDATIONS
   - Tailor test suggestions to THIS patient's body region (e.g., "right shoulder", "lumbar spine")
   - Reference the subjective findings to predict expected test results
   - Consider age-appropriate testing
   - NEVER use generic placeholders

3) PROXIMAL & DISTAL JOINT ASSESSMENT (MANDATORY)
   - ALWAYS include screening tests for the proximal joint (one above)
   - ALWAYS include screening tests for the distal joint (one below)
   - Explain why these adjacent joints matter for this case

4) TEST MODIFICATIONS (IMPORTANT)
   - If patient has high fear/anxiety: Suggest gentler progressions and clear communication
   - If marked as "precaution": Specify exact modifications (e.g., "reduce ROM by 50%", "avoid end-range", "monitor pain levels")
   - If irritability is high: Suggest limited repetitions, avoid provocative end-ranges
   - If marked "contraindicated": Explain WHY and suggest ALTERNATIVE tests

5) FOUR-PART OUTPUT REQUIRED:

   PART 1 - PRIMARY REGION TESTS (3-4 tests):
   List exact tests for the affected region ({component})

   PART 2 - PROXIMAL JOINT SCREENING (1-2 tests):
   Specific tests for the proximal joint

   PART 3 - DISTAL JOINT SCREENING (1-2 tests):
   Specific tests for the distal joint

   PART 4 - CLINICAL REASONING & MODIFICATIONS:
   - Why these tests are priority for THIS case
   - Expected positive findings based on subjective data
   - Specific modifications based on patient perspectives (if applicable)
   - Safety considerations or restrictions
   - Alternative tests if contraindicated

6) FORMAT (STRICT):
   PRIMARY REGION TESTS:
   1. [Specific test name] - [What it assesses]
   2. [Specific test name] - [What it assesses]
   3. [Specific test name] - [What it assesses]

   PROXIMAL JOINT SCREENING:
   1. [Joint name] - [Specific test] - [Why relevant]

   DISTAL JOINT SCREENING:
   1. [Joint name] - [Specific test] - [Why relevant]

   CLINICAL REASONING & MODIFICATIONS:
   - [Why these tests matter for this case]
   - [Expected findings based on subjective examination]
   - [Specific modifications: "Start with...", "Avoid...", "Monitor for..."]
   - [Safety considerations or alternative approaches]

7) WHAT TO AVOID:
   - Treatment recommendations or exercises
   - Generic test lists not tailored to this case
   - Tests irrelevant to the body region
   - Vague suggestions without specifics
   - Forgetting proximal/distal joint screening

OUTPUT (Follow this format exactly):
"""


def get_initial_plan_summary_prompt(
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective: Optional[Dict[str, Any]] = None,
    diagnosis: Optional[str] = None,
    plan_fields: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Summarize the initial treatment plan.

    Endpoint: /api/ai_suggestion/initial_plan_summary
    """
    context = build_clinical_context(age_sex, present_hist, past_hist, subjective=subjective, diagnosis=diagnosis)
    plan_block = _format_dict_block("Initial Plan Components", plan_fields)

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{context}

{plan_block}

TASK:
Provide a concise summary of the initial treatment approach for this case.

MANDATORY RULES:
1. Synthesize the plan components into a coherent 4-5 sentence summary.
2. Include: main treatment focus, key interventions, expected timeline, and patient education priorities.
3. Keep practical and implementation-focused.

OUTPUT:
[4-5 sentence treatment plan summary]
"""


def get_smart_goals_prompt(
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective: Optional[Dict[str, Any]] = None,
    perspectives: Optional[Dict[str, Any]] = None,
    diagnosis: Optional[str] = None,
) -> str:
    """
    Generate SMART goals for treatment.
    LEGACY FUNCTION - Consider using get_smart_goals_field_prompt for field-specific guidance.

    Endpoint: /api/ai_suggestion/smart_goals
    """
    context = build_clinical_context(
        age_sex, present_hist, past_hist,
        subjective=subjective,
        perspectives=perspectives,
        diagnosis=diagnosis
    )

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{context}

TASK:
Generate 2-3 SMART goals for this patient's treatment.

SMART CRITERIA:
- Specific: Clear and unambiguous
- Measurable: Quantifiable outcome
- Achievable: Realistic given the case
- Relevant: Aligned with patient's priorities and functional needs
- Time-bound: Specific timeframe

MANDATORY RULES:
1. Goals must reflect patient's activity limitations and participation restrictions from the case.
2. Include measurement criteria (e.g., ROM degrees, pain scale, functional task).
3. Specify realistic timeframe (e.g., 2 weeks, 4 weeks, 6 weeks).
4. Order by priority.

OUTPUT FORMAT:
1. [SMART goal with measurement and timeline]
2. [SMART goal with measurement and timeline]
(3. [SMART goal with measurement and timeline] if applicable)
"""


def get_smart_goals_field_prompt(
    field: str,
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective: Optional[Dict[str, Any]] = None,
    perspectives: Optional[Dict[str, Any]] = None,
    diagnosis: Optional[str] = None,
    clinical_flags: Optional[Dict[str, Any]] = None,
    patho_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    IMPROVED: Field-specific SMART goals guidance with body region-specific ICF participation goals.
    Provides evidence-based, condition-specific goal-setting recommendations.

    NEW: Adjusts goal timeframes and expectations based on pain severity, irritability, and healing stage.

    Endpoint: /api/ai_suggestion/smart_goals/<field>
    """

    # Detect body region for specific participation restrictions
    body_region = detect_body_region(present_hist)
    icf_core_set = ICF_CORE_SETS.get(body_region) if body_region else None

    # Build comprehensive context
    context = build_clinical_context(
        age_sex, present_hist, past_hist,
        subjective=subjective,
        perspectives=perspectives,
        diagnosis=diagnosis
    )

    # Add clinical flags if available
    if clinical_flags:
        yellow_flags = clinical_flags.get('yellow_flags', '')
        if yellow_flags:
            context += f"\n\n🟡 YELLOW FLAGS TO ADDRESS IN GOALS:\n{yellow_flags}"

    field_label = field.replace("_", " ").title()

    # ICF Core Set participation guidance
    icf_participation_guidance = ""
    if icf_core_set:
        icf_participation_guidance = f"\nRELEVANT CONDITION: {icf_core_set['name']}\n"
        icf_participation_guidance += "Evidence-based participation goals to consider:\n"
        for participation in icf_core_set.get('participation', []):
            icf_participation_guidance += f"  • {participation}\n"

    # Body region-specific goal examples and measurement criteria
    region_specific_goals = ""
    if body_region == 'shoulder':
        region_specific_goals = """
SHOULDER-SPECIFIC SMART GOAL EXAMPLES (Evidence-Based):

**COMMON PARTICIPATION RESTRICTIONS FOR SHOULDER CONDITIONS:**
- Reaching overhead (cupboards, shelves)
- Reaching behind back (fastening bra, tucking in shirt)
- Lifting and carrying (groceries, children)
- Self-care activities (washing hair, dressing)
- Work tasks (overhead work, computer use)
- Sports/recreation (swimming, tennis, throwing)
- Sleeping on affected side

**MEASUREMENT CRITERIA FOR SHOULDER:**

**ROM Measurements:**
- Shoulder flexion: Normal 180°, Functional minimum 120° (reach cupboard)
- Shoulder abduction: Normal 180°, Functional minimum 90° (reach side)
- External rotation: Normal 90°, Functional minimum 60° (hand behind head)
- Internal rotation: Normal 70-90°, Functional minimum reach to T7 (hand behind back)

**Pain Measurements:**
- VAS (0-10 scale)
- NPRS (Numeric Pain Rating Scale)
- Pain-free ROM vs total ROM
- Night pain (yes/no, frequency)

**Functional Measurements:**
- QuickDASH score (Disabilities of Arm, Shoulder, Hand)
- SPADI score (Shoulder Pain and Disability Index)
- Specific task completion (e.g., "can reach top shelf without pain")
- Work capacity (hours of overhead work tolerated)

**Strength Measurements:**
- Manual muscle testing (0-5 scale)
- Resisted tests (pain-free strength)
- Functional strength (kg lifted overhead)

**TIMEFRAMES FOR SHOULDER CONDITIONS:**
- Acute rotator cuff tendinopathy: 4-6 weeks
- Adhesive capsulitis (frozen shoulder): 6-12 months (staged goals)
- Rotator cuff tear (partial): 8-12 weeks
- Post-surgical repair: 12-16 weeks minimum

**EXAMPLE SMART GOALS:**
1. "Patient will achieve 150° of active shoulder flexion (measured by goniometer) to enable independent overhead reaching for cupboards, within 6 weeks."
2. "Patient will report ≤3/10 pain on NPRS during functional reaching tasks (washing hair, dressing) within 4 weeks."
3. "Patient will demonstrate 4/5 strength on manual muscle testing for shoulder external rotation to enable return to swimming 2x/week within 8 weeks."
"""
    elif body_region == 'lumbar':
        region_specific_goals = """
LUMBAR SPINE-SPECIFIC SMART GOAL EXAMPLES (Evidence-Based):

**COMMON PARTICIPATION RESTRICTIONS FOR LUMBAR CONDITIONS:**
- Sitting tolerance (work, driving, meals)
- Standing tolerance (cooking, queues, work)
- Walking distance/duration
- Lifting and carrying (children, groceries, work tasks)
- Bending and stooping (tying shoes, gardening)
- Household activities (vacuuming, making bed)
- Work duties (manual labor, desk work)
- Sports/recreation (running, cycling, golf)
- Sleep quality (pain-free sleep, bed transfers)

**MEASUREMENT CRITERIA FOR LUMBAR:**

**Pain Measurements:**
- VAS/NPRS (0-10 scale) at rest and with activity
- Oswestry Disability Index (ODI) score (0-100%)
- Centralization/peripheralization of symptoms (McKenzie)
- Night pain frequency

**Functional Measurements:**
- Sitting tolerance (minutes before pain >5/10)
- Standing tolerance (minutes)
- Walking distance (meters/km before exacerbation)
- Lifting capacity (kg without symptom increase)
- Roland-Morris Disability Questionnaire score

**ROM Measurements:**
- Lumbar flexion: Finger-to-floor distance (cm), Modified Schober's test
- Lumbar extension: Degrees or functional (can stand upright)
- Lateral flexion: Degrees or functional

**Neurological:**
- SLR angle (if radiculopathy)
- Dermatomal/myotomal changes
- Reflexes normalization

**TIMEFRAMES FOR LUMBAR CONDITIONS:**
- Acute mechanical LBP: 2-4 weeks
- Subacute LBP: 4-12 weeks
- Chronic LBP: 3-6 months (staged goals)
- Post-disc herniation: 6-12 weeks
- Spinal stenosis: 8-12 weeks

**EXAMPLE SMART GOALS:**
1. "Patient will achieve 60 minutes of continuous sitting (at work desk) with pain ≤3/10 on NPRS, within 4 weeks."
2. "Patient will demonstrate ability to lift 10kg from floor using proper mechanics without pain exacerbation (no peripheralization) within 6 weeks."
3. "Patient will walk 2km continuously without leg symptoms (neurogenic claudication) to enable community ambulation within 8 weeks."
4. "Patient will reduce ODI score from current 60% to ≤30% indicating minimal disability within 12 weeks."
"""
    elif body_region == 'knee':
        region_specific_goals = """
KNEE-SPECIFIC SMART GOAL EXAMPLES (Evidence-Based):

**COMMON PARTICIPATION RESTRICTIONS FOR KNEE CONDITIONS:**
- Stairs (ascending/descending)
- Squatting/kneeling (gardening, childcare, prayer)
- Walking distance
- Running/jumping (sports)
- Getting in/out of car
- Sitting to standing transitions
- Work tasks (prolonged standing, kneeling trades)
- Sports participation (soccer, basketball, running)

**MEASUREMENT CRITERIA FOR KNEE:**

**Pain Measurements:**
- VAS/NPRS (0-10 scale)
- KOOS (Knee Injury and Osteoarthritis Outcome Score)
- Anterior knee pain scale
- Pain location (anterior, medial, lateral, posterior)

**ROM Measurements:**
- Knee flexion: Normal 135°, Functional minimum 110° (stairs), 90° (sitting)
- Knee extension: Normal 0°, Extension lag indicates quad weakness
- Patellar mobility

**Functional Measurements:**
- Single leg stance time (seconds)
- Single leg squat quality (valgus control)
- Step up/down height and repetitions
- Hop tests: Single hop distance, triple hop, crossover hop (% of uninvolved side)
- Stairs: Number of steps without pain, speed
- Walking distance/speed
- Lysholm knee score

**Strength Measurements:**
- Quadriceps strength (kg on dynamometer, or % of uninvolved side)
- Hamstring strength
- Hip abductor strength (critical for knee control)
- Quadriceps lag

**TIMEFRAMES FOR KNEE CONDITIONS:**
- ACL reconstruction: 6-9 months return to sport (staged goals every 4-6 weeks)
- Meniscal tear (conservative): 6-12 weeks
- Patellofemoral pain: 6-12 weeks
- Knee OA: 8-12 weeks for pain/function improvement
- Patellar tendinopathy: 12-16 weeks

**EXAMPLE SMART GOALS:**
1. "Patient will descend one flight of stairs (12 steps) using reciprocal pattern with pain ≤2/10 on NPRS within 4 weeks."
2. "Patient will achieve single leg hop distance ≥85% of uninvolved limb (measured in cm) to enable return to recreational basketball within 12 weeks post-ACL reconstruction."
3. "Patient will demonstrate 4/5 quadriceps strength on manual muscle testing with no extension lag to enable pain-free community ambulation within 6 weeks."
"""
    elif body_region == 'cervical':
        region_specific_goals = """
CERVICAL SPINE-SPECIFIC SMART GOAL EXAMPLES (Evidence-Based):

**COMMON PARTICIPATION RESTRICTIONS FOR CERVICAL CONDITIONS:**
- Computer work (prolonged sitting, screen time)
- Driving (checking blind spots, reversing)
- Reading (looking down at books/phone)
- Overhead work
- Sleep quality
- Work concentration (pain interference)
- Social activities (unable to attend due to headaches/neck pain)

**MEASUREMENT CRITERIA FOR CERVICAL:**

**Pain Measurements:**
- VAS/NPRS (0-10 scale)
- Neck Disability Index (NDI) score (0-100%)
- Headache frequency and intensity
- Neurological symptoms (arm pain, numbness, weakness)

**ROM Measurements:**
- Cervical flexion: Normal 50-60°
- Cervical extension: Normal 60-75°
- Cervical rotation: Normal 80-90° (functional for driving ~70°)
- Cervical lateral flexion: Normal 45°

**Functional Measurements:**
- Sitting tolerance at computer (minutes)
- Driving duration tolerance
- Reading duration
- Work productivity (hours without significant pain interference)

**Neurological (if radiculopathy):**
- Dermatomal sensation
- Myotomal strength
- Upper limb neurodynamic test results

**TIMEFRAMES FOR CERVICAL CONDITIONS:**
- Acute mechanical neck pain/whiplash: 4-6 weeks
- Cervical radiculopathy: 6-12 weeks
- Chronic neck pain: 8-12 weeks
- Post-surgical: 12+ weeks

**EXAMPLE SMART GOALS:**
1. "Patient will achieve 80° of cervical rotation bilaterally (measured by goniometer) to enable safe driving with blind spot checks within 6 weeks."
2. "Patient will tolerate 4 hours of computer work with neck pain ≤3/10 on NPRS through improved ergonomics and posture within 4 weeks."
3. "Patient will reduce NDI score from current 45% (moderate disability) to ≤20% (mild disability) within 8 weeks."
"""
    elif body_region == 'hip':
        region_specific_goals = """
HIP-SPECIFIC SMART GOAL EXAMPLES (Evidence-Based):

**COMMON PARTICIPATION RESTRICTIONS FOR HIP CONDITIONS:**
- Walking distance
- Stairs
- Sitting tolerance (especially low chairs)
- Putting on shoes/socks
- Getting in/out of car
- Standing from sitting
- Sexual activity
- Sports (running, cycling, dancing)
- Work tasks (walking, standing, manual labor)

**MEASUREMENT CRITERIA FOR HIP:**

**Pain Measurements:**
- VAS/NPRS (0-10 scale)
- HOOS (Hip disability and Osteoarthritis Outcome Score)
- Harris Hip Score
- Groin pain vs lateral hip pain

**ROM Measurements:**
- Hip flexion: Normal 120°, Functional minimum 90° (sitting, stairs)
- Hip abduction: Normal 45°
- Hip internal rotation: Normal 35°, Early OA shows IR loss
- Hip external rotation: Normal 45°
- Capsular pattern: IR > ABD > flexion (suggests OA)

**Functional Measurements:**
- Walking distance without pain exacerbation (meters/km)
- Single leg stance time (seconds)
- Trendelenburg sign (positive/negative)
- Sit to stand ability
- Donning socks/shoes independently
- Stairs (step-over-step vs step-to pattern)

**Strength Measurements:**
- Hip abductor strength (Trendelenburg, manual muscle testing)
- Hip flexor strength
- Hip extensor strength

**TIMEFRAMES FOR HIP CONDITIONS:**
- Hip OA: 8-12 weeks (conservative management)
- Trochanteric bursitis/gluteal tendinopathy: 8-12 weeks
- Labral tear (conservative): 8-12 weeks
- Hip arthroscopy: 12-16 weeks
- Total hip replacement: 12 weeks minimum

**EXAMPLE SMART GOALS:**
1. "Patient will walk 2km continuously on level ground with groin pain ≤3/10 on NPRS to enable community ambulation within 8 weeks."
2. "Patient will independently don shoes and socks without assistive device (measured by ability to perform task) to improve self-care independence within 6 weeks."
3. "Patient will achieve negative Trendelenburg sign with single leg stance >30 seconds to improve gait mechanics and reduce lateral hip pain within 8 weeks."
"""
    elif body_region == 'ankle':
        region_specific_goals = """
ANKLE/FOOT-SPECIFIC SMART GOAL EXAMPLES (Evidence-Based):

**COMMON PARTICIPATION RESTRICTIONS FOR ANKLE/FOOT CONDITIONS:**
- Walking distance/duration
- Running/jumping sports
- Standing tolerance (work, queues)
- Stairs
- Uneven ground navigation
- Work tasks (prolonged standing, walking)
- Balance confidence
- Recreational activities (hiking, dancing)

**MEASUREMENT CRITERIA FOR ANKLE:**

**Pain Measurements:**
- VAS/NPRS (0-10 scale)
- Foot and Ankle Ability Measure (FAAM) score
- First step pain in morning (plantar fasciitis)
- Weight-bearing pain

**ROM Measurements:**
- Ankle dorsiflexion: Normal 20° (knee extended), 30° (knee flexed)
  - Functional minimum: 10° (normal gait)
- Ankle plantarflexion: Normal 50°
- Inversion/eversion: Normal 30-35° / 15-20°
- 1st MTP extension: Normal 70-90° (functional gait 65°)

**Functional Measurements:**
- Single leg stance time (seconds)
- Single leg heel raise repetitions
- Hop test distance (% of uninvolved side)
- Star Excursion Balance Test scores
- Walking distance before pain
- Gait speed
- Cumberland Ankle Instability Tool (CAIT) score

**Strength Measurements:**
- Calf strength (heel raise reps, height)
- Ankle DF/PF/inversion/eversion strength

**TIMEFRAMES FOR ANKLE CONDITIONS:**
- Acute ankle sprain (grade I-II): 4-6 weeks
- Severe ankle sprain (grade III): 6-12 weeks
- Achilles tendinopathy: 12-16 weeks
- Plantar fasciitis: 6-12 weeks
- Chronic ankle instability: 8-12 weeks

**EXAMPLE SMART GOALS:**
1. "Patient will demonstrate 15° of ankle dorsiflexion (measured by weight-bearing lunge test) to enable normal gait mechanics within 6 weeks."
2. "Patient will perform 20 consecutive single leg heel raises on affected limb to restore calf strength for return to running within 10 weeks."
3. "Patient will walk 5km on varied terrain without ankle instability or giving way episodes (measured by CAIT score >24/30) within 8 weeks."
"""
    else:
        region_specific_goals = """
GENERAL MUSCULOSKELETAL SMART GOAL EXAMPLES:

**COMMON PARTICIPATION RESTRICTIONS:**
- Work activities
- Self-care and ADLs
- Household tasks
- Recreation and leisure
- Social participation
- Community mobility

**MEASUREMENT CRITERIA:**
- Pain scales (VAS, NPRS 0-10)
- ROM measurements (goniometer, tape measure)
- Strength (manual muscle testing 0-5 scale, dynamometer)
- Functional tests (timed tests, distance, repetitions)
- Condition-specific outcome measures
- Activity tolerance (time, distance, load)

**TIMEFRAMES:**
- Acute conditions: 2-6 weeks
- Subacute: 6-12 weeks
- Chronic: 12+ weeks (staged goals)
"""

    # Field-specific guidance
    field_specific_guidance = {
        'patient_goal': f"""
TARGET FIELD: PATIENT-CENTRIC GOALS

PURPOSE:
Define what the PATIENT wants to achieve from physiotherapy, stated in THEIR language and priorities. This field captures the patient's perspective on meaningful participation and activity.

WHAT TO INCLUDE:

1. **ICF Participation Level (Highest Priority)**
   - Return to work (specific duties)
   - Sports/recreation participation
   - Social activities and hobbies
   - Self-care independence
   - Family/caregiver roles
   - Community participation

2. **Patient's Own Words**
   - Use language the patient would actually use
   - Quote specific activities they mentioned (e.g., "play with my grandchildren", "return to gardening")
   - Reference their values and what matters MOST to them

3. **Body Region Context: {body_region.upper() if body_region else 'GENERAL MSK'}**
   - Reference common participation restrictions for this condition (see list above)
   - Match goals to typical functional demands for this body region
   - Consider age-appropriate activities

4. **Link to Perspectives Data**
   - What did they say in the perspectives section about their priorities?
   - What functional tasks do they value most?
   - What are their fears or concerns?

5. **Realistic and Meaningful**
   - Goals should be achievable within physiotherapy scope
   - Must be meaningful to THIS patient (not generic)
   - Consider patient's lifestyle, work, hobbies

CRITICAL CONSIDERATIONS:
- State in patient-centric language (first person or "patient will...")
- Focus on PARTICIPATION (what they want to DO) not impairments (ROM, strength)
- Connect to patient's life roles (worker, parent, athlete, etc.)
- Must be important and motivating to the patient
- Consider cultural and personal values

EXAMPLE OUTPUTS by body region:

**Shoulder Example:**
"Patient wants to return to full-time work as a painter (overhead work) without shoulder pain interfering with productivity. Additionally, patient wants to play recreational tennis 2x/week and be able to wash and style own hair independently without pain."

**Lumbar Example:**
"Patient wants to sit through full workday at desk (8 hours) without needing to stand/walk breaks every 20 minutes. Also wants to lift and carry 18-month-old grandson without fear of back giving out, and sleep through the night without waking from back pain."

**Knee Example:**
"Patient wants to return to playing soccer at competitive level (training 3x/week, matches on weekends). Also wants to climb stairs at work (4 flights) without knee pain or swelling, and kneel to play with children on floor."

**Cervical Example:**
"Patient wants to work at computer for 6+ hours without debilitating headaches forcing them to leave work early. Additionally, wants to drive safely (check blind spots) and read books without neck pain limiting these activities."
""",
        'baseline_status': f"""
TARGET FIELD: BASELINE STATUS

PURPOSE:
Document the CURRENT state of the patient's function, pain, and activity level to establish a MEASURABLE starting point. This enables you to track progress objectively.

WHAT TO INCLUDE:

1. **Current Pain Level**
   - VAS/NPRS score at rest and with activity
   - Pain pattern (constant, intermittent, activity-related)
   - Pain location and radiation
   - Night pain presence/absence
   - Example: "Current pain: 6/10 at rest, 8/10 with overhead reaching, constant ache with sharp catches"

2. **Current ROM/Strength (Quantified)**
   - Specific measurements from objective assessment
   - Compare to normal values and/or uninvolved side
   - Example: "Shoulder flexion 90° (limited by pain), normal 180°"
   - Example: "Quadriceps strength 3/5, cannot perform single leg squat"

3. **Current Functional Limitations (Quantified)**
   - What CAN'T they do now? (or how limited is it?)
   - Quantify with time, distance, weight, frequency
   - Example: "Can only sit 15 minutes before needing to stand (work requires 2-hour meetings)"
   - Example: "Walking limited to 500m before calf pain forces rest"

4. **Current Activity/Participation Level**
   - Work status (off work, modified duties, full duties with difficulty)
   - Sports/recreation (unable, modified, reduced frequency)
   - Self-care independence (needs assistance yes/no, which tasks)
   - Social participation (avoids activities due to pain/limitation)

5. **Outcome Measure Scores (if available)**
   - NDI, ODI, QuickDASH, KOOS, HOOS, FAAM scores
   - Example: "Oswestry Disability Index: 62% (severe disability)"

6. **Body Region Context: {body_region.upper() if body_region else 'GENERAL MSK'}**
   - Use region-specific measures from the list above
   - Quantify using appropriate functional tests

CRITICAL CONSIDERATIONS:
- Be SPECIFIC and QUANTIFIABLE (not vague like "limited ROM")
- Use NUMBERS wherever possible (degrees, cm, kg, minutes, meters, VAS scores)
- Document what they CAN'T do or how limited current function is
- This creates the "before" picture for measuring progress
- Should correlate with objective assessment findings

EXAMPLE OUTPUTS by body region:

**Shoulder Example:**
"Baseline: Shoulder flexion 85° active (limited by pain 7/10), ER 20° (normal 90°). Cannot reach overhead cupboards, unable to wash hair without pain. QuickDASH score 68/100 (severe disability). Currently on modified work duties (no overhead work), unable to play tennis (recreational 2x/week pre-injury). Night pain waking 3-4x/night."

**Lumbar Example:**
"Baseline: Sitting tolerance 15 minutes before pain increases from 4/10 to 8/10 NPRS. SLR limited to 30° with leg pain (suggests nerve root tension). Cannot lift >5kg without fear of pain flare-up. ODI score 64% (severe disability). Currently off work (desk job requires 6+ hours sitting). Walking limited to 200m before leg symptoms force rest."

**Knee Example:**
"Baseline: Anterior knee pain 5/10 with stairs, 8/10 with jumping. Knee flexion 105° (limited by pain and swelling). Cannot descend stairs step-over-step (uses step-to pattern). Single leg squat shows marked valgus collapse. Not currently playing soccer (competitive level pre-injury 6 weeks ago). KOOS score 45/100."

**Cervical Example:**
"Baseline: Neck pain 6/10, headache 7/10 (3-4x/week, limits work). Cervical rotation 50° bilaterally (limited compared to normal 80-90°, insufficient for safe driving blind spot checks). Cannot work at computer >2 hours without severe headache forcing break. NDI score 46% (moderate-severe disability). Currently working part-time hours due to symptoms."
""",
        'measurable_outcome': f"""
TARGET FIELD: MEASURABLE OUTCOMES EXPECTED

PURPOSE:
Define the SPECIFIC, QUANTIFIABLE outcomes that indicate goal achievement. These are the objective markers of success that both patient and physio can track.

WHAT TO INCLUDE:

1. **Impairment-Level Measures (Body Structure/Function)**
   - ROM targets (specific degrees)
   - Strength targets (MMT grade, % of uninvolved, kg lifted)
   - Pain reduction targets (VAS/NPRS score)
   - Swelling reduction
   - Example: "Achieve 160° shoulder flexion (current 85°, normal 180°)"

2. **Activity-Level Measures**
   - Functional task performance
   - Timed tests (6-minute walk, timed up-and-go)
   - Distance (walking, running)
   - Load capacity (weight lifted)
   - Repetitions (heel raises, sit-to-stands)
   - Example: "Perform 25 single leg heel raises on affected side"

3. **Participation-Level Measures**
   - Return to work (full duties, hours)
   - Sports participation (frequency, intensity, duration)
   - Social activities resumed
   - Self-care independence
   - Example: "Return to work full-time (8 hours/day, 5 days/week) without restrictions"

4. **Outcome Measure Scores**
   - Target scores on validated outcome measures
   - MCID (Minimal Clinically Important Difference) values
   - Example: "Reduce ODI from 64% to ≤30% (MCID = 10-point reduction)"

5. **Body Region Context: {body_region.upper() if body_region else 'GENERAL MSK'}**
   - Use region-specific measures from the evidence-based list above
   - Reference functional minimums (e.g., 10° ankle DF for normal gait)
   - Consider normal values vs functional thresholds

6. **Progression/Stages (if long-term goals)**
   - Short-term milestone (2-4 weeks)
   - Medium-term milestone (6-8 weeks)
   - Long-term target (12+ weeks)

CRITICAL CONSIDERATIONS:
- Must be OBJECTIVELY MEASURABLE (can you test/observe it?)
- Use NUMBERS (degrees, reps, kg, minutes, meters, scores)
- Realistic based on diagnosis and timeframe
- Should align with patient goals
- Reference MCID values for outcome measures where known
- Distinguish between "normal" and "functional" (don't always need normal ROM to achieve function)

EXAMPLE OUTPUTS by body region:

**Shoulder Example:**
"Measurable outcomes expected:
1. **ROM**: Achieve 150° shoulder flexion, 80° external rotation (sufficient for overhead reaching and hair washing)
2. **Pain**: Reduce pain to ≤2/10 NPRS during functional activities (dressing, reaching, sleeping)
3. **Strength**: 4/5 strength on MMT for all rotator cuff muscles
4. **Functional**: Complete QuickDASH score ≤20/100 (mild-minimal disability, MCID 10 points)
5. **Participation**: Return to full work duties without restrictions, resume tennis 2x/week"

**Lumbar Example:**
"Measurable outcomes expected:
1. **Pain**: Reduce pain to ≤3/10 NPRS during sitting and daily activities
2. **Functional sitting**: Achieve 60-minute sitting tolerance (sufficient for meetings)
3. **Lifting**: Demonstrate ability to lift 15kg from floor using proper mechanics without pain exacerbation
4. **Walking**: Walk 2km continuously without leg symptoms
5. **ODI score**: Reduce from 64% to ≤30% (moderate to mild disability, exceeds MCID)
6. **Work**: Return to full-time desk work (8 hours/day)"

**Knee Example:**
"Measurable outcomes expected:
1. **ROM**: Achieve full knee extension (0°) and ≥125° flexion (normal function)
2. **Pain**: Reduce anterior knee pain to ≤2/10 with stairs and sports activities
3. **Strength**: Single leg squat with neutral knee alignment (no valgus collapse)
4. **Functional**: Single hop distance ≥90% of uninvolved limb
5. **Participation**: Return to competitive soccer (training 3x/week, match play)
6. **KOOS score**: Increase from 45 to ≥75 (MCID 8-10 points)"

**Cervical Example:**
"Measurable outcomes expected:
1. **ROM**: Achieve 75° cervical rotation bilaterally (sufficient for safe driving)
2. **Pain/Headache**: Reduce neck pain to ≤2/10, headache frequency to <1x/week
3. **Work tolerance**: Achieve 6+ hours computer work without significant symptoms
4. **NDI score**: Reduce from 46% to ≤20% (moderate to mild disability, exceeds MCID 7.5 points)
5. **Participation**: Return to full-time work hours (40 hours/week)"
""",
        'time_duration': f"""
TARGET FIELD: TIME DURATION

PURPOSE:
Specify the realistic TIMEFRAME for achieving each goal based on tissue healing, diagnosis, evidence, and patient factors. The timeline creates urgency and accountability.

WHAT TO INCLUDE:

1. **Overall Treatment Duration**
   - Total expected time from baseline to goal achievement
   - Example: "6 weeks total treatment duration"

2. **Staged Timeframes (for long-term goals)**
   - Short-term goals (2-4 weeks): Early improvements, pain reduction
   - Medium-term goals (6-8 weeks): Function restoration, strength building
   - Long-term goals (12+ weeks): Return to sport, full participation
   - Example: "Short-term (4 weeks), Medium-term (8 weeks), Long-term (12 weeks)"

3. **Body Region & Diagnosis-Specific Timeframes**
   - Use evidence-based timeframes from the list above for each condition
   - Consider tissue healing times
   - Account for severity and chronicity

4. **Frequency of Intervention**
   - Clinic visits per week (e.g., "2x/week for 4 weeks, then 1x/week for 4 weeks")
   - Home exercise program frequency (e.g., "Daily HEP")
   - Total number of sessions (e.g., "12 sessions over 8 weeks")

5. **Milestone Checkpoints**
   - When to reassess progress (e.g., "Reassess at 4 weeks")
   - Decision points for progression or modification
   - Example: "If not achieving 50% improvement by 4 weeks, consider imaging/referral"

6. **Factors Affecting Timeframe**
   - Acute vs chronic presentation
   - Patient compliance expected
   - Severity of condition
   - Presence of yellow flags (may slow progress)
   - Age-related healing (slower in older adults)
   - Work demands (earlier RTS pressure)

CRITICAL CONSIDERATIONS:
- Must be REALISTIC based on diagnosis (not overly optimistic)
- Reference evidence-based timeframes for specific conditions
- Account for tissue healing biology (e.g., tendon healing 12+ weeks)
- Consider patient factors (age, comorbidities, compliance)
- Staged goals for long timeframes (>12 weeks)
- Build in reassessment checkpoints
- State intervention frequency clearly
- Don't promise unrealistic short timeframes to please patient

EVIDENCE-BASED TIMEFRAME GUIDANCE:

**Tissue Healing Times:**
- Acute muscle strain: 4-6 weeks
- Ligament sprain (grade I-II): 4-6 weeks
- Ligament sprain (grade III): 8-12 weeks
- Tendinopathy: 12-16 weeks minimum
- Bone healing: 6-8 weeks
- Surgical repair: 12+ weeks depending on procedure

**Condition-Specific (see body region-specific lists above):**
- Acute mechanical pain: 2-4 weeks
- Subacute presentations: 6-12 weeks
- Chronic pain: 3-6 months
- Post-surgical: 12-24 weeks

EXAMPLE OUTPUTS by body region:

**Shoulder Example (Rotator Cuff Tendinopathy):**
"Time duration:
**Overall timeframe**: 8 weeks total treatment (evidence-based for rotator cuff rehab)

**Staged goals:**
- **Short-term (4 weeks)**: Reduce pain to ≤4/10 at rest, improve ROM to 120° flexion (functional reaching), strengthen rotator cuff to 3+/5 strength. Intervention: 2x/week clinic + daily HEP.

- **Medium-term (8 weeks)**: Achieve full or near-full painless ROM (150-160° flexion), 4/5 strength all RC muscles, return to light work duties. Intervention: 1x/week clinic + daily HEP.

**Total sessions**: Approximately 12 sessions over 8 weeks.

**Reassessment checkpoint**: Week 4 - expect 50% improvement in pain and ROM. If not improving, consider imaging to rule out tear.

**Rationale**: Rotator cuff tendinopathy typically requires 8-12 weeks for functional recovery. 8 weeks is realistic for return to work; full return to overhead sports may require 12 weeks."

**Lumbar Example (Chronic LBP with Radiculopathy):**
"Time duration:
**Overall timeframe**: 12 weeks total treatment (evidence-based for subacute radiculopathy)

**Staged goals:**
- **Short-term (4 weeks)**: Centralization of leg pain, reduce pain to ≤5/10, improve sitting to 30 minutes, begin core stabilization. Intervention: 2x/week clinic + daily HEP focused on directional preference.

- **Medium-term (8 weeks)**: Achieve 60-minute sitting tolerance, lift 10kg safely, reduce ODI to <40%, negative SLR. Intervention: 1x/week clinic + daily strengthening HEP.

- **Long-term (12 weeks)**: Return to full work duties, ODI ≤30%, walk 2km without leg symptoms. Intervention: Discharge to independent HEP with 1-month follow-up.

**Total sessions**: Approximately 16 sessions over 12 weeks.

**Reassessment checkpoint**: Week 4 - expect centralization and 30% pain reduction. If peripheralizing or no improvement, consider MRI/specialist referral.

**Rationale**: Radiculopathy can take 8-12 weeks to resolve. Chronic LBP requires addressing psychosocial factors which takes time. 12 weeks allows for comprehensive biopsychosocial approach."

**Knee Example (ACL Reconstruction - Post-Surgical):**
"Time duration:
**Overall timeframe**: 9 months for full return to competitive sport (evidence-based post-ACL reconstruction)

**Staged goals:**
- **Phase 1 (0-6 weeks)**: Achieve full extension, 110° flexion, independent gait without crutches, quad activation. Intervention: 2x/week clinic + daily HEP.

- **Phase 2 (6-12 weeks)**: Achieve full ROM, 4/5 quad strength, single leg balance >30 seconds, begin jogging. Intervention: 2x/week clinic + daily HEP.

- **Phase 3 (12-24 weeks)**: Progressive running, agility drills, plyometrics, strength ≥80% uninvolved side. Intervention: 1-2x/week clinic + gym program.

- **Phase 4 (24-36 weeks)**: Sport-specific training, return to team training (non-contact). Intervention: 1x/week clinic.

- **Return to Sport (9 months)**: Full clearance if passing functional tests (hop tests ≥90%, strength ≥90%, psychological readiness). Intervention: Maintenance HEP, monitor.

**Total sessions**: Approximately 60+ sessions over 9 months.

**Rationale**: ACL reconstruction requires minimum 9 months return to sport per current evidence (reduces re-injury risk). Earlier return increases risk of graft failure and re-injury."

**Cervical Example (Mechanical Neck Pain):**
"Time duration:
**Overall timeframe**: 6 weeks total treatment (evidence-based for mechanical neck pain)

**Staged goals:**
- **Short-term (3 weeks)**: Reduce pain/headache to ≤4/10, improve rotation to 65°, improve sitting tolerance to 3 hours. Intervention: 2x/week clinic (manual therapy + exercise) + daily HEP.

- **Medium-term (6 weeks)**: Achieve 75° rotation (driving safe), reduce NDI to ≤25%, work full-time without headache limitation. Intervention: 1x/week clinic + daily HEP.

**Total sessions**: Approximately 9 sessions over 6 weeks.

**Reassessment checkpoint**: Week 3 - expect 40-50% improvement. If headaches not improving, consider imaging to rule out upper cervical pathology.

**Rationale**: Mechanical neck pain typically resolves within 6-8 weeks with appropriate intervention. Persistent headaches beyond 6 weeks warrant further investigation."
"""
    }

    specific_guidance = field_specific_guidance.get(field, f"""
TARGET FIELD: {field_label}

Provide clinically relevant, evidence-based SMART goal suggestions for this field based on the patient's presentation, diagnosis, and patient priorities.
""")

    # NEW: Add pathophysiological mechanism context for realistic goal setting
    patho_context = ""
    if patho_data:
        pain_severity = patho_data.get('pain_severity', '')
        pain_irritability = patho_data.get('pain_irritability', '')
        healing_stage = patho_data.get('stage_healing', '')

        if any([pain_severity, pain_irritability, healing_stage]):
            patho_context = "\n\nPAIN & HEALING CONTEXT FOR GOAL TIMEFRAMES:\n"
            if pain_severity:
                patho_context += f"- Pain Severity (VAS): {pain_severity}/10\n"
            if pain_irritability:
                patho_context += f"- Pain Irritability: {pain_irritability}\n"
            if healing_stage:
                patho_context += f"- Tissue Healing Stage: {healing_stage}\n"
            patho_context += "\nIMPORTANT: Adjust goal timeframes based on severity and healing stage.\n"
            patho_context += "- High severity/irritability → Conservative timelines, stage goals carefully\n"
            patho_context += "- Acute healing → Protect tissue, don't overpromise quick return to high-level activity\n"
            patho_context += "- Chronic → May need longer timeframes, address psychosocial factors\n"

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{context}
{icf_participation_guidance}
{patho_context}

{specific_guidance}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{region_specific_goals}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SMART GOAL-SETTING FRAMEWORK:

**S - SPECIFIC:**
- Clearly define WHAT the patient wants to achieve
- Include the activity/task/participation goal
- State WHO is involved (usually "patient will...")
- Avoid vague terms like "improve" - specify what improvement means

**M - MEASURABLE:**
- Include objective measurement (degrees, cm, kg, VAS score, time, distance, reps)
- Use validated outcome measures where appropriate
- Specify baseline AND target values
- Must be observable/testable

**A - ACHIEVABLE:**
- Realistic given diagnosis, severity, timeframe
- Consider patient's age, comorbidities, lifestyle
- Based on evidence for similar cases
- Account for tissue healing biology
- Consider patient motivation and compliance

**R - RELEVANT:**
- Meaningful to THIS patient's life and priorities
- Addresses participation restrictions (ICF framework)
- Aligns with patient's stated goals and values
- Focuses on functional outcomes, not just impairments
- Connected to work/sport/self-care/social participation

**T - TIME-BOUND:**
- Specific deadline or timeframe (e.g., "within 6 weeks")
- Realistic based on diagnosis (see evidence-based timeframes above)
- Staged for long-term goals (short, medium, long-term milestones)
- Includes intervention frequency

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANDATORY RULES FOR YOUR RESPONSE:

1. CASE-SPECIFIC GOALS
   - Reference THIS patient's body region (e.g., "right shoulder", "lumbar spine")
   - Use their age and diagnosis
   - Match their specific participation restrictions
   - Quote their stated priorities from perspectives

2. EVIDENCE-BASED MEASUREMENT
   - Use validated outcome measures for this condition
   - Reference normal values AND functional thresholds
   - Include MCID (Minimal Clinically Important Difference) where known
   - Quantify with numbers (degrees, scores, time, distance)

3. ICF FRAMEWORK INTEGRATION
   - Prioritize PARTICIPATION-level goals (highest level)
   - Include ACTIVITY-level measures
   - Body function/structure impairments are means to functional ends
   - Frame goals in terms of what patient can DO, not just impairment reduction

4. REALISTIC TIMEFRAMES
   - Use evidence-based timeframes for the specific diagnosis
   - Account for tissue healing biology
   - Stage long-term goals into milestones
   - Don't overpromise quick results to please patient

5. PATIENT-CENTERED LANGUAGE
   - Use language patient would understand
   - Connect to their life roles and values
   - Make goals motivating and meaningful
   - Involve patient in goal-setting process

6. FIELD-SPECIFIC OUTPUT
   - Follow the detailed guidance above for the specific field: **{field_label}**
   - Provide comprehensive, actionable suggestions
   - Use clinical terminology appropriately
   - Be specific and avoid generic statements

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANT REMINDERS:
- Be SPECIFIC to this patient's body region, diagnosis, age, and life context
- Use EXACT measurements and numbers (quantify everything)
- Reference EVIDENCE-based timeframes for this condition
- Prioritize PARTICIPATION (what they want to do) over impairments
- Make goals MEANINGFUL and motivating to THIS patient
- Be REALISTIC - don't overpromise outcomes or timelines
- Connect to ICF framework (body function → activity → participation)
- Consider psychosocial factors (yellow flags) that may affect goal achievement
"""


def get_treatment_plan_field_prompt(
    field: str,
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective: Optional[Dict[str, Any]] = None,
    perspectives: Optional[Dict[str, Any]] = None,
    diagnosis: Optional[str] = None,
    goals: Optional[Dict[str, Any]] = None,
    clinical_flags: Optional[Dict[str, Any]] = None,
    patho_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    IMPROVED: Body region-specific treatment interventions for each field.
    Provides evidence-based, condition-specific treatment recommendations.

    NEW: Tailors treatment interventions to pain mechanism (e.g., neurogenic vs somatic pain
    requires different approaches) and respects irritability levels.

    Endpoint: /api/ai_suggestion/treatment_plan/<field>
    """
    # Detect body region for specific intervention recommendations
    body_region = detect_body_region(present_hist)
    icf_core_set = ICF_CORE_SETS.get(body_region) if body_region else None

    # Build comprehensive context
    context = build_clinical_context(
        age_sex, present_hist, past_hist,
        subjective=subjective,
        perspectives=perspectives,
        diagnosis=diagnosis,
        goals=goals
    )

    # Add clinical flags context if available
    if clinical_flags:
        yellow_flags = clinical_flags.get('yellow_flags', '')
        if yellow_flags:
            context += f"\n\n🟡 YELLOW FLAGS TO ADDRESS:\n{yellow_flags}"

    field_label = field.replace("_", " ").title()

    # ICF Core Set participation guidance
    icf_participation_guidance = ""
    if icf_core_set:
        icf_participation_guidance = f"\nRELEVANT CONDITION: {icf_core_set['name']}\n"
        icf_participation_guidance += "Evidence-based participation goals:\n"
        for participation in icf_core_set.get('participation', []):
            icf_participation_guidance += f"  • {participation}\n"

    # Body region-specific evidence-based interventions
    region_specific_interventions = ""
    if body_region == 'shoulder':
        region_specific_interventions = """
SHOULDER-SPECIFIC EVIDENCE-BASED INTERVENTIONS:

**MANUAL THERAPY:**
- Glenohumeral joint mobilizations (grades I-IV based on irritability)
- Scapulothoracic mobilizations
- Soft tissue release (pectoralis minor, upper trapezius, levator scapulae)
- Myofascial trigger point release

**THERAPEUTIC EXERCISE:**
- Scapular stabilization exercises (serratus anterior, lower/middle trapezius)
- Rotator cuff strengthening (progressive resistance, internal/external rotation)
- Postural correction exercises
- Range of motion exercises (pendulum, wall walks, pulley exercises)
- Proprioception and neuromuscular control training

**MODALITIES (if appropriate):**
- Cryotherapy (acute inflammation)
- Therapeutic ultrasound (tendinopathy, calcific deposits)
- TENS (pain modulation)

**FUNCTIONAL TRAINING:**
- Overhead reaching tasks
- Reaching behind back
- Lifting and carrying progressions
- Sport/work-specific training

**EDUCATION:**
- Pain neurophysiology education
- Activity modification strategies
- Ergonomic advice (desk setup, sleeping positions)
- Self-management strategies
"""
    elif body_region == 'lumbar':
        region_specific_interventions = """
LUMBAR SPINE-SPECIFIC EVIDENCE-BASED INTERVENTIONS:

**MANUAL THERAPY:**
- Lumbar mobilizations (central/unilateral PA pressures)
- Soft tissue release (paraspinals, gluteals, piriformis)
- Muscle energy techniques
- Neural mobilization (if neurogenic pain)

**THERAPEUTIC EXERCISE:**
- Core stabilization (transversus abdominis, multifidus activation)
- Lumbar flexion/extension exercises (based on directional preference - McKenzie)
- Hip and gluteal strengthening (gluteus maximus, medius)
- Lumbar endurance training (McGill's Big 3: curl-up, side plank, bird-dog)
- Flexibility exercises (hip flexors, hamstrings)

**MOVEMENT RE-EDUCATION:**
- Lifting mechanics training (squat vs stoop)
- Functional movement patterns
- Motor control retraining
- Graded exposure for fear-avoidance

**MODALITIES:**
- Heat therapy (muscle spasm)
- TENS (acute pain modulation)
- Traction (if indicated for radiculopathy)

**EDUCATION (CRITICAL for chronic LBP):**
- Pain neurophysiology education (Explain Pain)
- Fear-avoidance reduction
- Pacing and graded activity
- Ergonomic education (workstation, driving)
- Sleep hygiene and positioning
"""
    elif body_region == 'knee':
        region_specific_interventions = """
KNEE-SPECIFIC EVIDENCE-BASED INTERVENTIONS:

**MANUAL THERAPY:**
- Tibiofemoral joint mobilizations
- Patellofemoral joint mobilizations (medial/lateral glides)
- Soft tissue release (quadriceps, IT band, hamstrings)
- Hip and ankle mobilization (address kinetic chain)

**THERAPEUTIC EXERCISE:**
- Quadriceps strengthening (straight leg raises, terminal knee extension, squats)
- VMO-specific exercises (terminal extension with ER bias)
- Hip abductor strengthening (critical for knee control - clamshells, side-lying hip ABD)
- Hamstring strengthening (Nordic curls, bridges)
- Proprioception training (single leg stance, wobble board)
- Plyometric training (if appropriate for return to sport)

**GAIT RE-EDUCATION:**
- Single leg stance training
- Dynamic valgus correction
- Step training (up/down)
- Running gait analysis and correction (if applicable)

**TAPING/BRACING:**
- Patellar taping (McConnell taping for PFP)
- Knee sleeve for proprioception

**MODALITIES:**
- Ice (acute inflammation, post-exercise)
- Compression (effusion management)
- TENS (pain modulation)

**EDUCATION:**
- Activity modification
- Footwear advice
- Weight management (if relevant)
- Return to sport progression
"""
    elif body_region == 'cervical':
        region_specific_interventions = """
CERVICAL SPINE-SPECIFIC EVIDENCE-BASED INTERVENTIONS:

**MANUAL THERAPY:**
- Cervical mobilizations (avoid high-velocity thrust if VBI risk)
- Thoracic spine mobilization (critical for cervical function)
- Soft tissue release (upper trapezius, levator scapulae, suboccipitals)
- Neural mobilization (if neurogenic symptoms)

**THERAPEUTIC EXERCISE:**
- Deep neck flexor strengthening (cranio-cervical flexion)
- Scapular stabilization
- Cervical range of motion exercises
- Postural correction (forward head posture correction)
- Cervico-thoracic strengthening

**ERGONOMIC INTERVENTIONS:**
- Workstation assessment and modification (monitor height, keyboard position)
- Driving posture optimization
- Sleeping posture and pillow advice

**MODALITIES:**
- Heat (muscle spasm, chronic pain)
- TENS (pain modulation)

**EDUCATION:**
- Posture awareness training
- Activity modification (reading, computer use)
- Self-mobilization techniques
- Pain neurophysiology education (if chronic)
"""
    elif body_region == 'hip':
        region_specific_interventions = """
HIP-SPECIFIC EVIDENCE-BASED INTERVENTIONS:

**MANUAL THERAPY:**
- Hip joint mobilizations (long-axis distraction, inferior glide)
- Soft tissue release (hip flexors, gluteals, TFL, piriformis)
- Lumbar spine mobilization (L1-L3 segments)
- Neural mobilization (if neurogenic)

**THERAPEUTIC EXERCISE:**
- Hip abductor strengthening (gluteus medius - critical for gait and stability)
- Hip extensor strengthening (gluteus maximus - bridges, squats)
- Hip flexor stretching (Thomas stretch, lunge stretches)
- Core stabilization
- Balance and proprioception training
- Functional training (sit to stand, stairs, gait)

**GAIT RE-EDUCATION:**
- Trendelenburg gait correction
- Single leg stance training
- Step training

**MODALITIES:**
- Ice (acute inflammation)
- Heat (muscle spasm, chronic stiffness)
- TENS (pain modulation)

**EDUCATION:**
- Weight management (if OA present)
- Activity modification (low-impact exercise)
- Footwear advice
- Joint protection strategies
"""
    elif body_region == 'ankle':
        region_specific_interventions = """
ANKLE/FOOT-SPECIFIC EVIDENCE-BASED INTERVENTIONS:

**MANUAL THERAPY:**
- Ankle joint mobilizations (talocrural, subtalar)
- Soft tissue release (gastrocnemius, soleus, plantar fascia)
- Achilles tendon mobilization
- Neural mobilization (if neurogenic)

**THERAPEUTIC EXERCISE:**
- Ankle strengthening (dorsiflexion, plantarflexion, inversion, eversion)
- Calf strengthening (heel raises - eccentric for Achilles tendinopathy)
- Intrinsic foot muscle strengthening
- Proprioception training (single leg stance, wobble board - critical post-sprain)
- Balance training
- Plyometric training (return to sport)

**GAIT RE-EDUCATION:**
- Normal heel-toe gait pattern
- Push-off power training
- Running mechanics (if applicable)

**TAPING/BRACING:**
- Ankle taping (for instability)
- Ankle brace/lace-up support
- Arch support/orthotics (if biomechanical foot issues)

**MODALITIES:**
- Ice (acute inflammation, post-exercise)
- Contrast baths (subacute)
- Ultrasound (plantar fasciitis, Achilles tendinopathy)

**EDUCATION:**
- Footwear advice (proper support, heel-toe drop)
- Activity modification
- Return to sport progression (graded)
- Fall prevention (if elderly)
"""
    else:
        region_specific_interventions = """
GENERAL MUSCULOSKELETAL TREATMENT INTERVENTIONS:

**MANUAL THERAPY:**
- Joint mobilizations (grades based on irritability and goals)
- Soft tissue techniques
- Neural mobilization (if neurogenic component)

**THERAPEUTIC EXERCISE:**
- Strength training (progressive resistance)
- Range of motion exercises
- Proprioception and balance training
- Functional task training
- Endurance training

**MODALITIES:**
- Thermotherapy (heat/ice as indicated)
- Electrotherapy (TENS, ultrasound as appropriate)

**EDUCATION:**
- Pain neurophysiology education
- Activity modification and pacing
- Self-management strategies
- Ergonomic advice
"""

    # NEW: Add pathophysiological mechanism context for treatment selection
    patho_context = ""
    if patho_data:
        pain_mechanism = patho_data.get('possible_source', '')
        pain_type = patho_data.get('pain_type', '')
        pain_severity = patho_data.get('pain_severity', '')
        pain_irritability = patho_data.get('pain_irritability', '')
        healing_stage = patho_data.get('stage_healing', '')

        if any([pain_mechanism, pain_type, pain_severity, pain_irritability, healing_stage]):
            patho_context = "\n\n⚕️ PAIN MECHANISM CONTEXT FOR TREATMENT SELECTION:\n"
            if pain_mechanism:
                patho_context += f"- Pain Source Classification: {pain_mechanism}\n"
            if pain_type:
                patho_context += f"- Pain Type: {pain_type}\n"
            if pain_severity:
                patho_context += f"- Pain Severity (VAS): {pain_severity}/10\n"
            if pain_irritability:
                patho_context += f"- Pain Irritability: {pain_irritability}\n"
            if healing_stage:
                patho_context += f"- Tissue Healing Stage: {healing_stage}\n"

            patho_context += "\n🎯 TREATMENT IMPLICATIONS:\n"

            # Pain mechanism-specific treatment guidance
            if pain_mechanism:
                if 'neurogenic' in str(pain_mechanism).lower():
                    patho_context += "- NEUROGENIC PAIN: Prioritize graded exposure, pain education, neural mobilization (gentle), avoid aggressive stretching\n"
                elif 'visceral' in str(pain_mechanism).lower():
                    patho_context += "- VISCERAL PAIN SUSPECTED: Treatment contraindicated - medical referral required\n"
                elif 'somatic referred' in str(pain_mechanism).lower():
                    patho_context += "- SOMATIC REFERRED: Treat source region, consider myofascial trigger points, educate on referred pain patterns\n"
                elif 'somatic local' in str(pain_mechanism).lower():
                    patho_context += "- SOMATIC LOCAL: Direct treatment appropriate, manual therapy + exercise, load management\n"

            # Irritability-based treatment modifications
            if pain_irritability:
                if 'present' in str(pain_irritability).lower() or 'high' in str(pain_irritability).lower():
                    patho_context += "- HIGH IRRITABILITY: Gentle progression, avoid flare-ups, prioritize education and desensitization\n"
                else:
                    patho_context += "- LOW IRRITABILITY: More aggressive treatment appropriate, can progress quickly\n"

            # Healing stage-based modifications
            if healing_stage:
                if 'acute' in str(healing_stage).lower():
                    patho_context += "- ACUTE STAGE: Protect healing tissues, PRICE principles, avoid end-range stress, gentle AROM\n"
                elif 'subacute' in str(healing_stage).lower():
                    patho_context += "- SUBACUTE STAGE: Progressive loading, functional exercises, manual therapy appropriate\n"
                elif 'chronic' in str(healing_stage).lower():
                    patho_context += "- CHRONIC STAGE: Focus on graded exposure, pain education, address fear-avoidance, functional restoration\n"

    # Field-specific guidance
    field_specific_guidance = {
        'treatment_plan': f"""
TARGET FIELD: TREATMENT PLAN

PURPOSE:
Provide a comprehensive, evidence-based treatment plan specific to THIS patient's:
- Body region: {body_region if body_region else 'not detected - use general MSK approach'}
- Provisional diagnosis
- Activity limitations and participation restrictions (ICF framework)
- Identified barriers to recovery (yellow flags, environmental/personal factors)

WHAT TO INCLUDE:
1. **Primary Interventions (3-5 specific techniques/exercises)**
   - Manual therapy techniques
   - Therapeutic exercises with dosage (sets, reps, frequency)
   - Functional training
   - Modalities (if evidence-based for this condition)

2. **Progression Criteria**
   - How to progress exercises (increase resistance, complexity, etc.)
   - Timeline for expected improvement
   - Criteria for advancing to next phase

3. **Frequency and Duration**
   - Treatment frequency (e.g., 2x/week for 4 weeks)
   - Home exercise program frequency
   - Estimated total treatment duration

4. **Barriers to Address**
   - Yellow flags strategies (fear-avoidance, catastrophizing)
   - Environmental modifications needed
   - Psychosocial support required

CRITICAL CONSIDERATIONS:
- Align with SMART goals provided
- Address ICF participation restrictions (work, sport, self-care)
- Consider age-appropriate interventions
- Evidence-based for the diagnosis
- Practical and feasible for the patient's context
""",
        'goal_targeted': f"""
TARGET FIELD: GOAL TARGETED

PURPOSE:
Specify which SMART goal(s) this intervention is targeting and explain the connection.

WHAT TO INCLUDE:
1. **Specific Goal Reference**
   - State the exact SMART goal from the goals section
   - Reference measurable outcome (ROM, strength, functional task)

2. **ICF Component Being Addressed**
   - Body function (pain, ROM, strength)
   - Activity (walking, reaching, lifting)
   - Participation (return to work, sport, self-care)

3. **Rationale for Goal Selection**
   - Why this goal is priority for the patient
   - Connection to patient's values and perspectives
   - Impact on quality of life and participation

CRITICAL CONSIDERATIONS:
- Be specific (e.g., "Goal 1: Return to overhead reaching without pain")
- Connect to patient perspectives (what matters to THEM)
- Prioritize based on patient's functional needs
- Address participation restrictions ({icf_core_set['name'] if icf_core_set else 'general participation'})
""",
        'reasoning': f"""
TARGET FIELD: CLINICAL REASONING

PURPOSE:
Provide the clinical reasoning justification for your treatment plan based on:
- Pathophysiology
- Evidence base
- Clinical guidelines
- ICF framework
- Biopsychosocial factors

WHAT TO INCLUDE:
1. **Pathophysiological Rationale**
   - Why these interventions target the underlying pathology
   - Mechanism of action (e.g., "Manual therapy reduces pain via gate control theory")
   - Tissue healing timeline and intervention phasing

2. **Evidence-Based Justification**
   - Clinical practice guidelines for this condition
   - Key research supporting chosen interventions
   - Effect sizes for primary interventions (if known)

3. **ICF-Based Reasoning**
   - How interventions address body function impairments
   - How they improve activity limitations
   - How they reduce participation restrictions
   - Connection to ICF Core Set for {icf_core_set['name'] if icf_core_set else 'this condition'}

4. **Biopsychosocial Integration**
   - How interventions address yellow flags
   - Patient education strategies for fear-avoidance
   - Behavioral change strategies
   - Contextual factors consideration

CRITICAL CONSIDERATIONS:
- Use evidence-based language
- Reference clinical prediction rules or diagnostic criteria
- Explain why THIS treatment for THIS patient
- Address barriers to recovery (yellow flags, environmental)
- Consider age-appropriate reasoning
""",
        'reference': f"""
TARGET FIELD: REFERENCE (Literature/Evidence)

PURPOSE:
Provide key evidence-based references supporting your treatment plan.

WHAT TO INCLUDE:
1. **Clinical Practice Guidelines**
   - Most recent guidelines for this condition
   - Example: "NICE Guidelines for Low Back Pain (2020)"
   - Example: "AAOS Clinical Practice Guideline on Rotator Cuff Problems (2019)"

2. **Systematic Reviews/Meta-Analyses (Gold Standard)**
   - Key systematic reviews supporting primary interventions
   - Example: "Cochrane Review: Exercise therapy for chronic low back pain (2019)"
   - Include effect sizes if available

3. **High-Quality RCTs (if specific intervention)**
   - Landmark trials for condition-specific interventions
   - Example: "Lewis et al. (2015) - Exercise for rotator cuff tendinopathy"

4. **Theoretical Frameworks**
   - ICF framework references
   - Pain science references (Explain Pain, pain neurophysiology)
   - Fear-Avoidance Model references (if yellow flags present)

FORMAT:
- Author(s), Year, Title, Journal
- OR: Organization, Year, Guideline Title
- Prioritize most recent and high-quality evidence (last 5-10 years)

CRITICAL CONSIDERATIONS:
- Focus on ACTIONABLE evidence (what works for THIS condition)
- Include guidelines specific to body region: {icf_core_set['name'] if icf_core_set else 'general MSK'}
- Reference both treatment efficacy AND prognostic factors
- Include yellow flag management literature if psychosocial barriers present
"""
    }

    specific_guidance = field_specific_guidance.get(field, f"""
TARGET FIELD: {field_label}

Provide clinically relevant, evidence-based suggestions for this field based on the patient's presentation, diagnosis, and goals.
""")

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{context}
{icf_participation_guidance}
{patho_context}

{specific_guidance}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{region_specific_interventions}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANDATORY RULES FOR YOUR RESPONSE:

1. CASE-SPECIFIC RECOMMENDATIONS
   - Use the exact body region from presenting complaint (e.g., "right shoulder", "lumbar spine")
   - Reference the provisional diagnosis explicitly
   - Align with stated SMART goals
   - Consider patient's age, comorbidities, and context

2. EVIDENCE-BASED PRACTICE
   - Choose interventions with strong evidence for THIS diagnosis
   - Reference clinical guidelines where available
   - Provide dosage parameters (sets, reps, frequency) for exercises
   - Explain WHY the intervention works (mechanism)

3. ICF FRAMEWORK INTEGRATION
   - Address body function impairments
   - Target activity limitations
   - Focus on participation restrictions
   - Consider environmental and personal factors

4. YELLOW FLAG MANAGEMENT
   - If fear-avoidance present → Include graded exposure and education
   - If catastrophizing → Pain neurophysiology education critical
   - If external locus of control → Emphasize active participation
   - Address psychosocial barriers explicitly

5. STRUCTURED OUTPUT

OUTPUT FORMAT (depends on field):

{f'''For 'treatment_plan' field:
**PHASE 1: [Acute/Subacute/Return to Function] (Weeks 1-X)**
Intervention 1: [Specific technique] - [Sets/reps/frequency] - [Rationale]
Intervention 2: [Specific technique] - [Sets/reps/frequency] - [Rationale]
Intervention 3: [Specific technique] - [Sets/reps/frequency] - [Rationale]

**PHASE 2: [Next phase] (Weeks X-Y)**
[Progression details]

**Home Exercise Program:**
[2-3 key exercises with clear dosage]

**Frequency:** 2x/week clinic + daily HEP for 4-6 weeks
''' if field == 'treatment_plan' else ''}

{f'''For 'goal_targeted' field:
**Primary Goal:** [Exact SMART goal from goals section]
**ICF Component:** [Body function / Activity / Participation]
**Rationale:** [2-3 sentences explaining why this goal is priority and how treatment addresses it]
''' if field == 'goal_targeted' else ''}

{f'''For 'reasoning' field:
**Pathophysiological Rationale:**
[2-3 sentences explaining mechanism]

**Evidence-Based Justification:**
[Reference guidelines/systematic reviews supporting interventions]

**ICF-Based Reasoning:**
[How treatment addresses impairments → activities → participation]

**Biopsychosocial Integration:**
[How yellow flags/psychosocial factors are addressed]
''' if field == 'reasoning' else ''}

{f'''For 'reference' field:
**Clinical Practice Guidelines:**
1. [Guideline citation]

**Systematic Reviews/Meta-Analyses:**
1. [Author, Year, Title, Journal]
2. [Author, Year, Title, Journal]

**Key RCTs (if applicable):**
1. [Author, Year, Title, Journal]

**Pain Science/Psychosocial References (if yellow flags):**
1. [Reference for fear-avoidance, pain neuroscience education, etc.]
''' if field == 'reference' else ''}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANT REMINDERS:
- Be SPECIFIC to this patient (use their body region, diagnosis, goals)
- Provide ACTIONABLE suggestions (clear dosage, frequency, technique descriptions)
- Reference EVIDENCE (guidelines, systematic reviews)
- Address BARRIERS (yellow flags, environmental/personal factors)
- Think FUNCTIONALLY (how does this help them return to work/sport/life?)
- Consider AGE-APPROPRIATE interventions
- Safety first - if high irritability or red flags, modify intensity
"""


def get_treatment_plan_summary_prompt(
    patient_id: str,
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective: Optional[Dict[str, Any]] = None,
    diagnosis: Optional[str] = None,
    goals: Optional[Dict[str, Any]] = None,
    treatment_fields: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Comprehensive treatment plan summary.

    Endpoint: /api/ai_suggestion/treatment_plan_summary/<patient_id>
    """
    context = build_clinical_context(
        age_sex, present_hist, past_hist,
        subjective=subjective,
        diagnosis=diagnosis,
        goals=goals
    )
    treatment_block = _format_dict_block("Treatment Components", treatment_fields)

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{context}

{treatment_block}

TASK:
Provide a comprehensive treatment plan summary for this case.

MANDATORY RULES:
1. Synthesize all treatment components into a coherent plan
2. Structure: Phase-based approach (acute/subacute/return to function)
3. Include: interventions, progression criteria, patient education, discharge criteria
4. Keep concise (6-8 sentences max)
5. End with estimated treatment duration

OUTPUT:
[6-8 sentence comprehensive treatment plan]
"""


# ─────────────────────────────────────────────────────────────────────────────
# FOLLOW-UP
# ─────────────────────────────────────────────────────────────────────────────

def get_followup_prompt(
    age_sex: str,
    present_hist: str,
    past_hist: str,
    diagnosis: Optional[str] = None,
    treatment_summary: Optional[str] = None,
    followup_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate follow-up visit guidance and reassessment suggestions.
    LEGACY FUNCTION - Consider using get_followup_field_prompt for field-specific guidance.

    Endpoint: /api/ai_suggestion/followup
    """
    context = build_clinical_context(age_sex, present_hist, past_hist, diagnosis=diagnosis)

    if treatment_summary:
        context += f"\n\nTreatment to Date:\n{treatment_summary}"

    followup_block = _format_dict_block("Follow-up Visit Data", followup_data)
    if followup_block:
        context += f"\n\n{followup_block}"

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{context}

TASK:
Based on the patient's progress (or lack thereof), provide follow-up management suggestions.

MANDATORY RULES:
1. Assess response to treatment: better, same, or worse
2. Suggest 2-4 next steps based on the response
3. Each suggestion should be specific and actionable
4. Consider: treatment progression, modification, or referral if appropriate

OUTPUT:
1. [Management suggestion based on progress]
2. [Management suggestion based on progress]
3. [Management suggestion based on progress]
(4. [Management suggestion based on progress] if applicable)
"""


def get_followup_field_prompt(
    field: str,
    age_sex: str,
    present_hist: str,
    past_hist: str,
    diagnosis: Optional[str] = None,
    treatment_summary: Optional[str] = None,
    goals: Optional[Dict[str, Any]] = None,
    grade: Optional[str] = None,
    perception: Optional[str] = None,
    feedback: Optional[str] = None,
    session_number: Optional[int] = None,
) -> str:
    """
    IMPROVED: Field-specific follow-up guidance with body region-specific progression strategies.
    Provides evidence-based reassessment and treatment modification recommendations.

    Endpoint: /api/ai_suggestion/followup/<field>
    """

    # Detect body region for specific progression strategies
    body_region = detect_body_region(present_hist)
    icf_core_set = ICF_CORE_SETS.get(body_region) if body_region else None

    # Build comprehensive context
    context = build_clinical_context(age_sex, present_hist, past_hist, diagnosis=diagnosis, goals=goals)

    if treatment_summary:
        context += f"\n\nTREATMENT TO DATE:\n{treatment_summary}"

    # Add follow-up session context
    followup_context = ""
    if session_number:
        followup_context += f"\n\nSESSION NUMBER: {session_number}"
    if grade:
        followup_context += f"\nGRADE OF ACHIEVEMENT: {grade}"
    if perception:
        followup_context += f"\nPATIENT PERCEPTION: {perception}"
    if feedback:
        followup_context += f"\nPATIENT FEEDBACK: {feedback}"

    context += followup_context

    field_label = field.replace("_", " ").title()

    # ICF Core Set context
    icf_guidance = ""
    if icf_core_set:
        icf_guidance = f"\nRELEVANT CONDITION: {icf_core_set['name']}\n"

    # Body region-specific progression and modification strategies
    region_specific_strategies = ""
    if body_region == 'shoulder':
        region_specific_strategies = """
SHOULDER-SPECIFIC FOLLOW-UP STRATEGIES (Evidence-Based):

**REASSESSMENT PRIORITIES:**
1. **Pain Level**: VAS/NPRS at rest and with functional activities (overhead reaching, sleeping)
2. **ROM**: Shoulder flexion, abduction, ER, IR (compare to baseline)
3. **Strength**: Rotator cuff strength (manual muscle testing, pain-free strength)
4. **Functional Tests**: Painful arc, overhead reaching, hand behind back
5. **Outcome Measures**: QuickDASH or SPADI score changes (MCID = 10 points)
6. **Sleep Quality**: Night pain frequency (major QOL indicator)

**PROGRESSION STRATEGIES (If Fully/Partially Achieved):**

**If ROM Improving:**
- Advance passive ROM → active ROM → resisted ROM
- Increase end-range mobilization grades (II-III → III-IV)
- Add functional reaching tasks (cupboards, overhead)
- Progress scapular stabilization exercises (add resistance)

**If Strength Improving:**
- Progress theraband resistance (light → medium → heavy)
- Advance from open chain → closed chain exercises
- Add functional weight-bearing tasks (wall push-ups → table push-ups → floor push-ups)
- Increase rotator cuff resistance training

**If Pain Decreasing:**
- Reduce manual therapy frequency (2x/week → 1x/week)
- Increase exercise intensity and complexity
- Add sport-specific or work-specific training
- Consider discharge planning if pain ≤2/10 and functional goals met

**MODIFICATION STRATEGIES (If Not Achieved/Plateaued):**

**If ROM Plateau:**
- Reassess capsular pattern (adhesive capsulitis vs impingement)
- Consider adding Grade IV+ mobilizations or MWM techniques
- Assess for neural tension (cervical contribution)
- Consider imaging if no progress after 6-8 weeks (possible tear)

**If Strength Plateau:**
- Review exercise compliance and technique
- Assess for kinetic chain deficits (scapular dyskinesis, thoracic stiffness)
- Consider adding manual resistance or biofeedback
- Rule out rotator cuff tear (drop arm test, strength asymmetry >20%)

**If Pain Persists:**
- Re-evaluate diagnosis (is it impingement, tear, adhesive capsulitis, or referred cervical?)
- Address yellow flags (fear-avoidance, catastrophizing)
- Consider corticosteroid injection if inflammatory (not for tears)
- Refer for imaging if red flags or no improvement after 8 weeks

**DISCHARGE CRITERIA:**
- Pain ≤2/10 with functional activities
- ROM within 10° of normal or sufficient for patient's functional needs
- 4/5 or better rotator cuff strength
- QuickDASH ≤20 or patient-reported functional goals met
- Independent with HEP
"""
    elif body_region == 'lumbar':
        region_specific_strategies = """
LUMBAR SPINE-SPECIFIC FOLLOW-UP STRATEGIES (Evidence-Based):

**REASSESSMENT PRIORITIES:**
1. **Pain Level**: VAS/NPRS at rest, with sitting, standing, walking, lifting
2. **Centralization/Peripheralization**: McKenzie assessment (critical for decision-making)
3. **Functional Tolerance**: Sitting time, standing time, walking distance, lifting capacity
4. **Neurological**: SLR, myotomes, dermatomes, reflexes (if radiculopathy)
5. **Outcome Measures**: ODI or Roland-Morris score (MCID ODI = 10 points)
6. **Red Flags**: Monitor for cauda equina, progressive neurological deficit

**PROGRESSION STRATEGIES (If Fully/Partially Achieved):**

**If Pain Centralizing:**
- Continue directional preference exercises (McKenzie protocol)
- Progress to sustained end-range positions
- Add repeated movements in beneficial direction
- Begin strengthening once centralized and pain <4/10

**If Function Improving:**
- Progress core stabilization (transversus abdominis activation → multifidus → integrated exercises)
- Advance from static → dynamic stability exercises (dead bug → bird-dog → plank variations)
- Increase lifting capacity progressively (5kg → 10kg → 15kg)
- Add functional task training (floor to waist, waist to overhead)

**If Sitting/Standing Tolerance Improving:**
- Extend sitting tolerance goals (30min → 60min → 2 hours)
- Progress to more challenging work simulations
- Add ergonomic training for prolonged sitting
- Consider return to work discussions

**MODIFICATION STRATEGIES (If Not Achieved/Plateaued):**

**If Pain Peripheralizing:**
- STOP current approach immediately
- Reassess directional preference (may have incorrect direction)
- Consider alternate diagnosis (spinal stenosis, SI joint)
- Refer for imaging if progressive neurological signs or persistent peripheralization

**If Neurological Symptoms Not Improving:**
- Document progression (myotome weakness, reflex changes, dermatomal numbness)
- Consider urgent MRI if progressive motor weakness
- Refer to spine specialist if no improvement after 6-8 weeks conservative care
- Monitor for cauda equina symptoms (RED FLAG)

**If Functional Plateau:**
- Address yellow flags (fear-avoidance, catastrophizing) - major barrier in chronic LBP
- Consider pain neurophysiology education (Explain Pain approach)
- Reassess movement patterns and motor control
- Consider graded exposure for fear of movement
- Multidisciplinary approach (psychology, pain clinic)

**If Chronic Pain Pattern (>3 months):**
- Shift focus from tissue healing → pain management and function
- Emphasize pacing, graded activity, cognitive-behavioral strategies
- Set realistic expectations (may not be pain-free, but functionally independent)
- Focus on participation restrictions (work, social, family roles)

**DISCHARGE CRITERIA:**
- Pain ≤3/10 with daily activities
- ODI <30% (minimal disability) or patient-reported functional goals met
- Able to sit >60 minutes, stand >30 minutes, walk >2km
- Lift >10kg safely with proper mechanics
- Independent with HEP and self-management strategies
"""
    elif body_region == 'knee':
        region_specific_strategies = """
KNEE-SPECIFIC FOLLOW-UP STRATEGIES (Evidence-Based):

**REASSESSMENT PRIORITIES:**
1. **Pain Level**: VAS/NPRS with stairs, squatting, walking, weight-bearing
2. **ROM**: Knee flexion (should reach ≥110° for stairs), extension (check for lag)
3. **Strength**: Quadriceps strength (critical), hip abductor strength
4. **Functional Tests**: Single leg squat (valgus control), step-down test, hop tests (if appropriate)
5. **Swelling**: Effusion (patellar tap, sweep test)
6. **Outcome Measures**: KOOS score (MCID = 8-10 points)

**PROGRESSION STRATEGIES (If Fully/Partially Achieved):**

**If ROM Improving:**
- Progress knee flexion: heel slides → wall slides → squats (increase depth)
- Advance extension work: prone hangs → weighted extension stretches
- Add functional ROM tasks (stairs, sit-to-stand, cycling)

**If Strength Improving:**
- Progress quadriceps: straight leg raises → terminal knee extension → leg press → squats
- Advance hip abductors (CRITICAL for knee control): side-lying ABD → standing ABD → single leg stance → single leg squat
- Add dynamic valgus control exercises
- Progress to plyometrics if returning to sport (single leg hops, box jumps)

**If Function Improving:**
- Progress stairs: step-to pattern → step-over-step pattern → running stairs
- Advance single leg tasks: stance time → single leg squat → hop tests
- Add sport-specific agility drills (cutting, pivoting)
- Increase walking/running distance progressively

**MODIFICATION STRATEGIES (If Not Achieved/Plateaued):**

**If Swelling Persists:**
- Reassess for meniscal tear, ligament injury, or synovitis
- Review activity level (may be overloading)
- Increase compression, ice, elevation
- Consider aspiration if tense effusion limiting ROM
- Refer for imaging if persistent swelling >4-6 weeks

**If Quadriceps Weakness Persists:**
- Check for VMO activation (may need EMG biofeedback or NMES)
- Assess for arthrogenic muscle inhibition (pain → reflex inhibition)
- Review exercise technique and dosage
- Consider joint mobilizations to reduce inhibition
- Rule out femoral nerve pathology (rare)

**If Patellofemoral Pain Not Improving:**
- Reassess patellar tracking and maltracking
- Address hip abductor weakness (major contributor to PFPS)
- Consider patellar taping (McConnell technique)
- Modify aggravating activities (stairs, squats)
- Review footwear and foot biomechanics

**If Post-ACL Reconstruction Not Progressing:**
- Refer back to surgeon if not meeting expected milestones
- Check rehabilitation protocol adherence (may be too aggressive or too conservative)
- Assess graft protection (avoid early pivoting, cutting)
- Document hop test asymmetry (should progress toward 90%)
- Psychological readiness is critical for return to sport

**DISCHARGE CRITERIA:**
- Pain ≤2/10 with functional activities
- Full or near-full ROM (0-135°)
- Quadriceps strength ≥90% of uninvolved side
- Single leg hop ≥85% of uninvolved (for athletes)
- KOOS sport/recreation subscale >80 (if athlete)
- Independent with HEP
"""
    elif body_region == 'cervical':
        region_specific_strategies = """
CERVICAL SPINE-SPECIFIC FOLLOW-UP STRATEGIES (Evidence-Based):

**REASSESSMENT PRIORITIES:**
1. **Pain/Headache**: VAS/NPRS, headache frequency and intensity
2. **ROM**: Cervical rotation (critical for driving), flexion, extension, lateral flexion
3. **Neurological**: Upper limb symptoms, myotomes, dermatomes, reflexes (if radiculopathy)
4. **Functional Tolerance**: Computer work duration, driving duration, reading
5. **Outcome Measures**: NDI score (MCID = 7.5 points)
6. **Red Flags**: Monitor for myelopathy signs (gait changes, hyperreflexia, clonus)

**PROGRESSION STRATEGIES (If Fully/Partially Achieved):**

**If Pain/Headache Reducing:**
- Reduce manual therapy frequency (2x/week → 1x/week → discharge)
- Progress to independent self-mobilization techniques
- Advance postural endurance exercises
- Increase work tolerance progressively

**If ROM Improving:**
- Progress from gentle ROM → full ROM → resisted ROM
- Add cervical strengthening (deep neck flexors, extensors)
- Functional ROM training (driving simulation, work tasks)
- Progress scapular and thoracic mobility (critical for cervical function)

**If Neurological Improving:**
- Document dermatomal/myotomal changes
- Continue neurodynamic exercises (ULNT progressions)
- Monitor for full resolution before discharge
- Refer for imaging if NOT improving after 6-8 weeks

**MODIFICATION STRATEGIES (If Not Achieved/Plateaued):**

**If Headaches Persist:**
- Reassess cervicogenic vs tension vs migraine
- Check upper cervical (C1-C2) contribution
- Address jaw/TMJ contribution if relevant
- Consider trigger point release (suboccipital, upper trap, SCM)
- Refer for imaging if persistent >6 weeks or red flags

**If Neurological Symptoms Not Resolving:**
- Document progression or worsening (CRITICAL)
- Urgent MRI if progressive motor weakness
- Refer to spine specialist if no improvement after 6 weeks
- Monitor for myelopathy (RED FLAG - upper motor neuron signs)

**If ROM Plateau:**
- Reassess for thoracic stiffness contribution (T1-T4)
- Check for facet joint restriction (unilateral restriction pattern)
- Consider muscle energy techniques or contract-relax
- Address forward head posture and ergonomics

**If Work Tolerance Not Improving:**
- Workstation ergonomic assessment and modification
- Graded return to work (part-time → full-time)
- Micro-break strategies (every 30 minutes)
- Postural awareness training
- Consider occupational therapy referral

**DISCHARGE CRITERIA:**
- Pain ≤2/10, headache frequency <1x/week
- Cervical rotation ≥70° bilaterally (sufficient for safe driving)
- NDI <20% (mild disability) or functional goals met
- Full work tolerance without symptom exacerbation
- No neurological deficits
- Independent with HEP and ergonomic strategies
"""
    elif body_region == 'hip':
        region_specific_strategies = """
HIP-SPECIFIC FOLLOW-UP STRATEGIES (Evidence-Based):

**REASSESSMENT PRIORITIES:**
1. **Pain Level**: VAS/NPRS with walking, stairs, sitting, hip flexion activities
2. **ROM**: Hip flexion, IR (early OA shows IR loss), abduction, extension
3. **Strength**: Hip abductors (Trendelenburg test), hip flexors, extensors
4. **Functional Tests**: Walking distance, single leg stance, sit-to-stand, donning shoes/socks
5. **Gait**: Trendelenburg gait, antalgic gait, step length symmetry
6. **Outcome Measures**: HOOS score

**PROGRESSION STRATEGIES (If Fully/Partially Achieved):**

**If Pain Reducing:**
- Reduce manual therapy frequency
- Increase weight-bearing exercise intensity
- Progress walking distance (1km → 2km → 5km)
- Add impact activities if appropriate (light jogging, cycling)

**If ROM Improving:**
- Progress from passive → active → resisted ROM
- Advance hip flexor stretching (Thomas test position → standing lunge)
- Add functional ROM tasks (stairs, squatting, donning shoes/socks)

**If Strength Improving:**
- Progress hip abductors: side-lying → standing → single leg stance → step-ups
- Advance hip extensors: bridges → single leg bridges → deadlifts
- Add functional strengthening (stairs, squats, lunges)
- Negative Trendelenburg = major milestone

**MODIFICATION STRATEGIES (If Not Achieved/Plateaued):**

**If Pain From Hip OA Persists:**
- Reassess load management (may be overloading)
- Emphasize low-impact exercise (swimming, cycling)
- Consider corticosteroid injection if inflammatory flare
- Weight management discussion if relevant
- Refer to orthopedic surgeon for joint replacement consideration if severe

**If Trendelenburg Persists:**
- Focus intensively on gluteus medius strengthening
- Add EMG biofeedback if available
- Check for superior gluteal nerve pathology (rare)
- Assess lumbar contribution (L5 radiculopathy can cause hip ABD weakness)

**If Groin Pain Not Improving:**
- Differentiate: intra-articular (OA, labral tear, FAI) vs extra-articular (adductor strain, athletic pubalgia)
- Positive FADIR persistent → consider imaging for labral tear or FAI
- Refer to hip specialist if no improvement after 8-12 weeks conservative care

**DISCHARGE CRITERIA:**
- Pain ≤3/10 with walking and daily activities
- Walk ≥2km without significant pain
- Negative Trendelenburg sign
- Independent with shoes/socks
- HOOS >70 or functional goals met
"""
    elif body_region == 'ankle':
        region_specific_strategies = """
ANKLE/FOOT-SPECIFIC FOLLOW-UP STRATEGIES (Evidence-Based):

**REASSESSMENT PRIORITIES:**
1. **Pain Level**: VAS/NPRS with weight-bearing, walking, stairs
2. **ROM**: Ankle DF (weight-bearing lunge test), PF, inversion, eversion
3. **Strength**: Calf strength (single leg heel raises - reps and height), ankle DF/PF strength
4. **Balance**: Single leg stance time, SEBT scores, giving way episodes
5. **Functional Tests**: Walking distance, running (if athlete), hop tests
6. **Outcome Measures**: FAAM score, CAIT (Cumberland Ankle Instability Tool)

**PROGRESSION STRATEGIES (If Fully/Partially Achieved):**

**If ROM Improving:**
- Progress DF stretching: wall stretches → weight-bearing lunge → slant board
- Add functional ROM: stairs, squats, heel-toe walking

**If Strength Improving:**
- Progress calf: double leg heel raises → single leg heel raises → add weight → eccentric focus (for Achilles)
- Advance ankle strengthening: theraband → weighted → functional movements
- Increase heel raise reps (goal 20-25 single leg)

**If Balance/Proprioception Improving:**
- Progress: Double leg stance → single leg stance → eyes closed → unstable surface → dynamic tasks
- Add sport-specific balance challenges
- Advance to plyometric training (box jumps, hopping)

**If Function Improving:**
- Increase walking distance progressively
- Add jogging/running program (Couch to 5K protocol)
- Progress to sport-specific drills
- Add agility and cutting movements

**MODIFICATION STRATEGIES (If Not Achieved/Plateaued):**

**If Chronic Instability Persists:**
- Reassess for mechanical instability (ATFL, CFL laxity)
- Intensive proprioception training (wobble board, single leg tasks)
- Consider ankle brace for high-risk activities
- Refer for surgical consultation if severe instability affecting QOL

**If Achilles Pain Not Improving:**
- Ensure eccentric loading protocol (gold standard for mid-portion Achilles tendinopathy)
- Check for insertional vs mid-portion (different management)
- Assess for heel lift in shoes (reduces strain)
- Consider shockwave therapy or PRP if no improvement after 12-16 weeks
- Rule out partial tear or rupture (Thompson test)

**If Plantar Fasciitis Persists:**
- Reassess biomechanics (pes planus, tight gastrocnemius)
- Consider orthotics or arch supports
- Night splints for morning pain
- Ensure proper stretching technique (gastrocnemius + plantar fascia)
- Consider corticosteroid injection if severe (use cautiously - rupture risk)

**DISCHARGE CRITERIA:**
- Pain ≤2/10 with functional activities
- Ankle DF ≥10° (sufficient for normal gait)
- 20+ single leg heel raises
- Single leg balance >30 seconds
- CAIT score >24 (if had instability)
- Return to sport/activity without giving way
"""
    else:
        region_specific_strategies = """
GENERAL MUSCULOSKELETAL FOLLOW-UP STRATEGIES:

**REASSESSMENT PRIORITIES:**
1. **Pain Level**: VAS/NPRS at rest and with activities
2. **ROM**: Compare to baseline and functional requirements
3. **Strength**: Manual muscle testing, functional strength
4. **Functional Activities**: Task-specific limitations
5. **Outcome Measures**: Condition-specific tools

**PROGRESSION STRATEGIES:**
- Increase exercise difficulty, resistance, complexity
- Advance from simple → complex → functional → sport-specific
- Progress from pain management → tissue healing → strengthening → return to function
- Consider discharge when functional goals met

**MODIFICATION STRATEGIES:**
- If no progress after 6-8 weeks, consider imaging or referral
- Address barriers (yellow flags, compliance, environmental factors)
- Modify approach if current strategy not effective
- Consider multidisciplinary input if complex case
"""

    # Field-specific guidance
    if field == 'plan_next':
        field_guidance = f"""
TARGET FIELD: PLAN FOR NEXT TREATMENT

PURPOSE:
Based on the patient's progress (grade of achievement, perception, feedback), provide a specific, actionable plan for the next treatment session. This should be body region-specific and evidence-based.

CURRENT PROGRESS INDICATORS:
- **Grade of Achievement**: {grade or 'Not provided'}
- **Patient Perception**: {perception or 'Not provided'}
- **Patient Feedback**: {feedback or 'Not provided'}
- **Session Number**: {session_number or 'Not provided'}

WHAT TO INCLUDE:

1. **PROGRESS INTERPRETATION**
   - Assess response to treatment (better, same, worse)
   - Identify what's working and what's not
   - Determine if on track with expected timeline

2. **REASSESSMENT PLAN**
   - What specific tests to repeat from baseline
   - What new tests to add based on progress
   - Red flags to monitor

3. **TREATMENT MODIFICATIONS/PROGRESSIONS**
   - If FULLY ACHIEVED:
     * Progress exercises (increase resistance, complexity, reps)
     * Advance functional training
     * Reduce intervention frequency (consider discharge planning)
     * Set new goals if original goals met

   - If PARTIALLY ACHIEVED:
     * Continue current approach with minor modifications
     * Address barriers to full achievement
     * Adjust exercise dosage or technique
     * Consider adding complementary interventions

   - If NOT ACHIEVED:
     * Reassess diagnosis and treatment approach
     * Identify barriers (compliance, psychosocial, biomechanical)
     * Consider alternative interventions
     * Refer for imaging or specialist if no progress after 6-8 weeks

4. **SPECIFIC INTERVENTIONS FOR NEXT SESSION**
   - Manual therapy techniques (specific technique, grade, dosage)
   - Exercise modifications or progressions (specific exercises with reps/sets)
   - Education topics to address
   - Home exercise program adjustments

5. **DISCHARGE PLANNING (If Appropriate)**
   - Criteria being met for discharge
   - Timeline to discharge (e.g., "2 more sessions")
   - Transition to independent HEP
   - Return to work/sport readiness

6. **REFERRAL CONSIDERATION (If Not Progressing)**
   - When to refer (red flags, no improvement after X weeks)
   - Who to refer to (orthopedic surgeon, pain specialist, imaging)
   - What to communicate in referral

7. **BODY REGION CONTEXT: {body_region.upper() if body_region else 'GENERAL MSK'}**
   - Use body region-specific strategies listed above
   - Reference expected timeframes for this condition
   - Consider stage of tissue healing

CRITICAL CONSIDERATIONS:
- Be SPECIFIC (not "continue exercises" but "progress theraband ER from red to blue, 3x15 reps")
- Be REALISTIC about progress expectations
- Address patient's perception and feedback
- Consider yellow flags affecting progress (fear-avoidance, low motivation)
- Safety first - monitor red flags
- Document progress objectively (ROM degrees, strength grades, VAS scores)

EXAMPLE OUTPUTS by grade:

**FULLY ACHIEVED Example (Shoulder, Session 6):**
"Excellent progress! Patient has achieved ROM goals (flexion 165°, ER 75°) and pain reduced to 2/10.

**Next Session Plan:**
1. **Reassess**: QuickDASH score, rotator cuff strength testing, overhead functional tasks
2. **Progress**: Increase theraband ER resistance (red → blue), add overhead functional training (reaching cupboards, washing hair simulation), progress to closed-chain exercises (wall push-ups → table push-ups)
3. **Reduce manual therapy**: Only if specific restriction found on reassessment (decrease from 2x/week to 1x/week)
4. **Education**: Return to work discussion (can resume overhead painting 50% of workday, full duties in 2 weeks)
5. **Discharge Planning**: If maintains progress, plan discharge in 2 sessions with independent HEP and 1-month follow-up call

**PARTIALLY ACHIEVED Example (Lumbar, Session 4):**
"Moderate progress. Sitting tolerance improved from 15min to 40min (goal 60min), pain reduced from 7/10 to 4/10, but still experiencing leg symptoms with prolonged walking.

**Next Session Plan:**
1. **Reassess**: SLR angle (check if improving), centralization status, ODI score
2. **Continue**: Directional preference exercises (extension bias), core stabilization (add bird-dog progressions), neural mobilization
3. **Modify**: Add McKenzie sustained extension positions (prone on elbows 3x3min), review HEP compliance (patient reports doing exercises only 3x/week instead of daily)
4. **Address barriers**: Patient expressed fear of bending - provide pain neurophysiology education, reassurance about tissue healing
5. **Timeline**: Expect 4-6 more weeks to achieve sitting goal; currently on track
6. **Monitoring**: If leg symptoms peripheralize or worsen, consider MRI referral

**NOT ACHIEVED Example (Knee, Session 8):**
"Minimal progress despite 8 weeks of treatment. Knee flexion only improved from 105° to 110° (goal 125°), persistent swelling after activity, pain unchanged at 6/10.

**Next Session Plan:**
1. **Comprehensive Reassessment**:
   - Check for meniscal tear signs (McMurray, joint line tenderness, locking/catching)
   - Reassess effusion (may indicate intra-articular pathology)
   - Review compliance with HEP (patient may be overloading or under-loading)

2. **Modify Approach**:
   - STOP current exercises temporarily (may be aggravating)
   - Focus on swelling reduction (ice, compression, elevation, reduce activity)
   - Consider joint mobilizations to improve ROM (tibiofemoral, patellofemoral)
   - Address possible hip or ankle contribution to poor knee mechanics

3. **Investigations**:
   - Refer for MRI to rule out meniscal tear, cartilage damage, or other intra-articular pathology
   - Document lack of progress for imaging justification

4. **Address Yellow Flags**:
   - Patient reports frustration and fear that 'something is wrong' (catastrophizing)
   - Provide reassurance, explain next steps clearly
   - Set realistic expectations for timeline with imaging and potential follow-up

5. **Contingency**:
   - If MRI shows significant pathology → refer to orthopedic surgeon
   - If MRI negative → reassess approach, consider alternative diagnosis (PFPS, fat pad impingement)"
"""
    else:
        field_guidance = f"""
TARGET FIELD: {field_label}

Provide specific, actionable follow-up suggestions based on patient's progress and current presentation.
"""

    return f"""{SYSTEM_ROLES['clinical_specialist']}

{context}
{icf_guidance}

{field_guidance}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{region_specific_strategies}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CLINICAL DECISION-MAKING FRAMEWORK FOR FOLLOW-UP:

STEP 1: ASSESS RESPONSE TO TREATMENT
- **Better**: Goals progressing, pain reducing, function improving
- **Same**: No change (plateau) - reassess after 2-3 sessions
- **Worse**: Increasing pain, decreasing function - modify immediately

STEP 2: COMPARE TO EXPECTED TIMELINE
- Is progress on track for this diagnosis?
- Should they be further along by this session number?
- Are we hitting expected milestones (e.g., 50% improvement by 4 weeks)?

STEP 3: IDENTIFY BARRIERS TO PROGRESS
- **Biomechanical**: Technique errors, compensatory patterns, kinetic chain issues
- **Compliance**: Not doing HEP, missing sessions, overloading
- **Psychosocial**: Fear-avoidance, catastrophizing, low motivation (yellow flags)
- **Environmental**: Work demands, family stress, financial barriers
- **Diagnostic**: Wrong diagnosis, missed pathology, co-morbidities

STEP 4: DECISION TREE

**If FULLY ACHIEVED (on track or ahead):**
→ PROGRESS interventions
→ Increase intensity, complexity, functional demands
→ Reduce frequency if appropriate
→ Consider discharge planning

**If PARTIALLY ACHIEVED (slower than expected but improving):**
→ CONTINUE with minor modifications
→ Address identified barriers
→ Adjust dosage or add complementary interventions
→ Re-evaluate in 2-3 sessions

**If NOT ACHIEVED (plateau or worsening):**
→ MODIFY approach significantly
→ Reassess diagnosis
→ Consider imaging or referral (especially if >6-8 weeks no progress)
→ Address psychosocial barriers intensively

STEP 5: RED FLAG MONITORING
- Any new symptoms suggesting serious pathology?
- Progressive neurological deficit?
- Cauda equina symptoms?
- Worsening despite appropriate treatment?
→ If YES, urgent referral indicated

STEP 6: DISCHARGE READINESS
- Functional goals met?
- Patient independent with HEP?
- Pain managed (may not be zero, but tolerable)?
- Return to work/sport achieved?
→ If YES, discharge with follow-up PRN

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANDATORY RULES FOR YOUR RESPONSE:

1. PROGRESS-SPECIFIC RECOMMENDATIONS
   - Reference the grade of achievement explicitly
   - Match recommendations to patient's progress level
   - Be realistic about expected timeline

2. BODY REGION-SPECIFIC INTERVENTIONS
   - Use specific tests and exercises for this body region
   - Reference expected timeframes for this condition
   - Consider stage of tissue healing

3. EVIDENCE-BASED MODIFICATIONS
   - Progression should follow evidence-based protocols
   - Cite reassessment measures appropriate for the region
   - Reference MCID values for outcome measures

4. BARRIER IDENTIFICATION
   - Address why goals not fully achieved
   - Consider biomechanical, psychosocial, compliance factors
   - Provide specific solutions to identified barriers

5. SAFETY AND REFERRAL
   - Monitor red flags explicitly
   - State when imaging or referral indicated
   - Protect patient from harm (stop ineffective treatment)

6. ACTIONABLE SPECIFICITY
   - "Progress theraband from red to blue" NOT "progress exercises"
   - "Increase ROM to 140° flexion" NOT "improve ROM"
   - "2x/week for 3 more weeks then discharge" NOT "continue treatment"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANT REMINDERS:
- Use THIS patient's body region, diagnosis, and progress data
- Be SPECIFIC with interventions (exercises, dosages, techniques)
- Consider TIMELINE (how many weeks into treatment?)
- Address BARRIERS honestly (why not fully achieved?)
- Monitor RED FLAGS and refer when appropriate
- DISCHARGE planning when goals met
- Evidence-based PROGRESSION or MODIFICATION strategies
"""


# ─────────────────────────────────────────────────────────────────────────────
# GENERIC / FALLBACK PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

def get_generic_field_prompt(field: str, context: str) -> str:
    """
    Generic AI suggestion for any field (FALLBACK).

    Endpoint: /api/ai_suggestion/field/<field>

    NOTE: This is a safety net; specific endpoints are preferred.
    """
    field_label = field.replace("_", " ").title()

    return f"""{SYSTEM_ROLES['decision_support']}

CONTEXT:
{context}

TASK:
Provide 2–3 brief, sensible suggestions for **{field_label}**.

MANDATORY RULES:
1. Suggestions must be plausible within a physiotherapy clinical reasoning workflow.
2. Keep each suggestion short (max ~20 words).
3. Do NOT invent or repeat PHI (names, dates of birth, addresses, IDs).

OUTPUT:
- Numbered list 1–3, one suggestion per line.
"""


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT CATALOG & METADATA
# ─────────────────────────────────────────────────────────────────────────────

PROMPT_CATALOG = {
    # History Taking
    "past_questions": {
        "function": get_past_questions_prompt,
        "category": "history_taking",
        "endpoint": "/api/ai_suggestion/past_questions",
        "description": "Generate targeted past medical history questions",
        "version": "2025-01-improved",
    },

    # Subjective Examination (ICF) - IMPROVED
    "subjective_field": {
        "function": get_subjective_field_prompt,
        "category": "subjective_examination",
        "endpoint": "/api/ai_suggestion/subjective/<field>",
        "description": "Generate ICF-based subjective examination questions WITH clinical reasoning",
        "version": "2025-01-improved",
        "changelog": "Now provides both questions AND clinical reasoning guidance specific to the case"
    },
    "subjective_diagnosis": {
        "function": get_subjective_diagnosis_prompt,
        "category": "subjective_examination",
        "endpoint": "/api/ai_suggestion/subjective_diagnosis",
        "description": "Generate provisional diagnoses from subjective data only",
        "version": "2025-01-improved",
    },

    # Patient Perspectives
    "patient_perspectives_field": {
        "function": get_patient_perspectives_field_prompt,
        "category": "biopsychosocial",
        "endpoint": "/api/ai_suggestion/perspectives/<field>",
        "description": "Generate FIELD-SPECIFIC CSM-based patient perspective questions WITH clinical reasoning",
        "version": "2025-01-improved",
        "changelog": "Now provides field-specific questions AND clinical reasoning for each CSM component"
    },
    "patient_perspectives": {
        "function": get_patient_perspectives_prompt,
        "category": "biopsychosocial",
        "endpoint": "/api/ai_suggestion/patient_perspectives",
        "description": "Generate CSM-based patient perspective questions (LEGACY - prefer field-specific)",
        "note": "Use patient_perspectives_field for better field-specific guidance",
        "version": "2025-01-improved",
    },

    # Assessment & Diagnosis
    "provisional_diagnosis": {
        "function": get_provisional_diagnosis_prompt,
        "category": "diagnosis",
        "endpoint": "/api/ai_suggestion/provisional_diagnosis",
        "description": "Generate comprehensive provisional diagnosis from all data",
        "version": "2025-01-improved",
    },
    "provisional_diagnosis_field": {
        "function": get_provisional_diagnosis_field_prompt,
        "category": "diagnosis",
        "endpoint": "/api/ai_suggestion/provisional_diagnosis/<field>",
        "description": "FIELD-SPECIFIC provisional diagnosis with body region-specific differential diagnoses",
        "version": "2025-01-improved",
        "changelog": "Now provides body region-specific differential diagnoses (shoulder, lumbar, knee, etc.) with age-appropriate conditions and field-specific guidance for likelihood, structure_fault, symptom, findings_support, findings_reject"
    },
    "objective_assessment": {
        "function": get_objective_assessment_prompt,
        "category": "assessment",
        "endpoint": "/api/ai_suggestion/objective_assessment",
        "description": "Suggest objective tests and measures (LEGACY - prefer objective_assessment_field)",
        "note": "Use objective_assessment_field for body region-specific guidance",
        "version": "2025-01-improved",
    },
    "objective_assessment_field": {
        "function": get_objective_assessment_field_prompt,
        "category": "assessment",
        "endpoint": "/api/ai_suggestion/objective_assessment/<field>",
        "description": "FIELD-SPECIFIC objective assessment planning with body region-specific tests",
        "version": "2025-01-improved",
        "changelog": "Now provides body region-specific test recommendations based on ICF Core Sets and clinical flags"
    },

    # Clinical Reasoning
    "pathophysiology": {
        "function": get_pathophysiology_prompt,
        "category": "clinical_reasoning",
        "endpoint": "/api/ai_suggestion/patho_possible_source",
        "description": "Explain pathophysiological mechanisms",
        "version": "2025-01-improved",
    },
    "chronic_factors": {
        "function": get_chronic_factors_prompt,
        "category": "clinical_reasoning",
        "endpoint": "/api/ai_suggestion/chronic_factors_suggest",
        "description": "Identify chronic disease or maintenance factors",
        "version": "2025-01-improved",
    },
    "clinical_flags": {
        "function": get_clinical_flags_prompt,
        "category": "clinical_reasoning",
        "endpoint": "/api/ai_suggestion/clinical_flags_suggest",
        "description": "Identify red and yellow flags",
        "version": "2025-01-improved",
    },

    # Treatment Planning
    "initial_plan_field": {
        "function": get_initial_plan_field_prompt,
        "category": "treatment_planning",
        "endpoint": "/api/ai_suggestion/initial_plan/<field>",
        "description": "Initial treatment plan field suggestions",
        "version": "2025-01-improved",
    },
    "initial_plan_summary": {
        "function": get_initial_plan_summary_prompt,
        "category": "treatment_planning",
        "endpoint": "/api/ai_suggestion/initial_plan_summary",
        "description": "Summarize initial treatment plan",
        "version": "2025-01-improved",
    },
    "smart_goals": {
        "function": get_smart_goals_prompt,
        "category": "treatment_planning",
        "endpoint": "/api/ai_suggestion/smart_goals",
        "description": "Generate SMART goals (LEGACY - prefer smart_goals_field)",
        "note": "Use smart_goals_field for body region-specific ICF participation goals",
        "version": "2025-01-improved",
    },
    "smart_goals_field": {
        "function": get_smart_goals_field_prompt,
        "category": "treatment_planning",
        "endpoint": "/api/ai_suggestion/smart_goals/<field>",
        "description": "FIELD-SPECIFIC SMART goals with body region-specific ICF participation guidance",
        "version": "2025-01-improved",
        "changelog": "Now provides body region-specific participation restrictions, measurement criteria, evidence-based timeframes, and detailed field-specific guidance for patient_goal, baseline_status, measurable_outcome, and time_duration"
    },
    "treatment_plan_field": {
        "function": get_treatment_plan_field_prompt,
        "category": "treatment_planning",
        "endpoint": "/api/ai_suggestion/treatment_plan/<field>",
        "description": "FIELD-SPECIFIC treatment interventions with body region-specific evidence-based guidance",
        "version": "2025-01-improved",
        "changelog": "Now provides body region-specific interventions (shoulder, lumbar, knee, etc.) with field-specific guidance for treatment_plan, goal_targeted, reasoning, and reference fields"
    },
    "treatment_plan_summary": {
        "function": get_treatment_plan_summary_prompt,
        "category": "treatment_planning",
        "endpoint": "/api/ai_suggestion/treatment_plan_summary/<patient_id>",
        "description": "Summarize complete treatment plan",
        "version": "2025-01-improved",
    },

    # Follow-up
    "followup": {
        "function": get_followup_prompt,
        "category": "followup",
        "endpoint": "/api/ai_suggestion/followup",
        "description": "Follow-up visit guidance and reassessment (LEGACY - prefer followup_field)",
        "note": "Use followup_field for body region-specific progression strategies",
        "version": "2025-01-improved",
    },
    "followup_field": {
        "function": get_followup_field_prompt,
        "category": "followup",
        "endpoint": "/api/ai_suggestion/followup/<field>",
        "description": "FIELD-SPECIFIC follow-up with body region-specific progression strategies",
        "version": "2025-01-improved",
        "changelog": "Provides progression/modification strategies based on achievement grade (Fully/Partially/Not Achieved) with body region-specific reassessment priorities, discharge criteria, and clinical decision frameworks"
    },

    # Generic Fallback
    "generic_field": {
        "function": get_generic_field_prompt,
        "category": "generic",
        "endpoint": "/api/ai_suggestion/field/<field>",
        "description": "Generic field suggestions (FALLBACK)",
        "warning": "REDUNDANT - Prefer specific endpoints where available",
        "version": "2025-01-improved",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# USAGE STATISTICS (OPTIONAL UTILITY)
# ─────────────────────────────────────────────────────────────────────────────

def get_prompt_statistics() -> Dict[str, Any]:
    """
    Get simple statistics about prompt usage and organization.
    """
    categories: Dict[str, int] = {}
    for prompt_id, info in PROMPT_CATALOG.items():
        cat = info["category"]
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total_prompts": len(PROMPT_CATALOG),
        "categories": categories,
        "prompts_by_category": {
            cat: [p for p, i in PROMPT_CATALOG.items() if i["category"] == cat]
            for cat in categories.keys()
        },
        "redundancy_candidates": [
            p for p, i in PROMPT_CATALOG.items()
            if "warning" in i or "note" in i
        ],
        "versions": {
            p: i.get("version", "unknown") for p, i in PROMPT_CATALOG.items()
        },
    }
