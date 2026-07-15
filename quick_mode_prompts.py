"""
Quick Mode Prompts — PhysiologicPRISM
======================================
AI prompts used to generate pre-fills for each assessment screen in Quick Mode.

Design rules (same as ai_prompts.py):
- Never invent names, dates, addresses, or patient IDs.
- Use only information explicitly present in the patient history.
- If information is absent, say so honestly — never guess.
- All output is JSON so the calling code can safely extract field values.
- Language is clinical but direct — no teaching paragraphs, no waffle.
"""

# ─────────────────────────────────────────────────────────────────────────────
# PATHO MECHANISM — STAGE 1 PRE-FILLS
# Called immediately after Add Patient, before any examination.
# Inputs available: age_sex, present_history, past_history only.
# ─────────────────────────────────────────────────────────────────────────────

PATHO_MECHANISM_SYSTEM = """You are a physiotherapy clinical reasoning assistant generating \
pre-fill suggestions for a Pathophysiological Mechanism assessment form.

You will be given a patient's age/sex, presenting history, and past history.
Your job is to extract and infer ONLY what the history clearly supports.

STRICT RULES:
1. Extract area_involved and presenting_symptom directly from the history — do not invent anatomical detail not mentioned.
2. For possible_source, choose the MOST LIKELY option given the history and provide a concise clinical rationale.
3. For stage_healing, infer from duration cues in the history (e.g. "yesterday", "3 weeks", "6 months"). \
   If no duration is mentioned, return null and explain why.
4. Never fabricate examination findings — none have been performed yet.
5. Use conditional language where appropriate: "likely", "suggests", "consistent with".
6. Return ONLY valid JSON. No markdown, no prose outside the JSON object.
"""

PATHO_MECHANISM_USER_TEMPLATE = """Patient details:
- Age / Sex: {age_sex}
- Present History: {present_history}
- Past History: {past_history}

Generate pre-fill suggestions for the Pathophysiological Mechanism screen.

Return this exact JSON structure (all fields required, use null if genuinely unknown):

{{
  "area_involved": "<anatomical area clearly identified from history, e.g. 'Right shoulder — rotator cuff region'>",
  "presenting_symptom": "<primary symptom as described, e.g. 'Sharp pain on overhead activity, worse at night'>",
  "possible_source": "<one of: Somatic Local | Somatic Referred | Neurogenic | Visceral>",
  "possible_source_reasoning": "<1-2 sentence clinical rationale for physio reference>",
  "stage_healing": "<one of: Acute Inflammatory (0-72h) | Subacute (4-21 days) | Chronic (>3 weeks) | null>",
  "stage_healing_reasoning": "<1 sentence explaining how duration was inferred from history, or why it is unknown>"
}}

Rules for possible_source:
- Somatic Local: pain at the site of injury, well-localised, mechanical pattern
- Somatic Referred: deep aching referred from a structure (e.g. facet joint, disc) without dermatomal pattern
- Neurogenic: radiating/shooting/burning pain in a dermatomal or peripheral nerve distribution, with possible neurological signs
- Visceral: symptoms pattern suggesting organ referral (rare in physio; flag if suspected)

Rules for stage_healing:
- Acute Inflammatory (0-72h): injury within last 3 days
- Subacute (4-21 days): injury 4 days to 3 weeks ago
- Chronic (>3 weeks): symptoms present for more than 3 weeks
- null: if no duration information is available in the history
"""


def build_patho_mechanism_user_prompt(age_sex: str, present_history: str, past_history: str) -> str:
    """Format the user prompt for patho mechanism prefills."""
    return PATHO_MECHANISM_USER_TEMPLATE.format(
        age_sex=age_sex or "Not provided",
        present_history=present_history or "Not provided",
        past_history=past_history or "None reported",
    )


# Valid options for each dropdown — used for server-side validation before
# writing AI suggestions into the DB or rendering into templates.
PATHO_VALID_OPTIONS = {
    "possible_source": [
        "Somatic Local",
        "Somatic Referred",
        "Neurogenic",
        "Visceral",
    ],
    "stage_healing": [
        "Acute Inflammatory (0-72h)",
        "Subacute (4-21 days)",
        "Chronic (>3 weeks)",
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# SUBJECTIVE / PATIENT FUNCTIONING ASSESSMENT — ICF QUESTIONS
# Called when physio reaches the ICF screen in Quick Mode.
# Inputs: patient history + patho mechanism data from previous screen.
# Purpose: Generate 2-3 targeted interview questions per ICF domain so the
#          physio can conduct a focused patient interview rather than open-ended
#          questioning. Physio types patient responses into the text boxes.
# ─────────────────────────────────────────────────────────────────────────────

SUBJECTIVE_QUESTIONS_SYSTEM = """You are a physiotherapy clinical reasoning assistant helping \
a physiotherapist conduct a structured patient interview using the ICF framework \
(International Classification of Functioning, Disability and Health).

You will be given a patient's history and pathophysiological mechanism findings.
Your job is to generate 2-3 specific, targeted interview questions for each ICF domain \
that will help the physiotherapist efficiently gather the most clinically relevant information \
from THIS specific patient.

STRICT RULES:
1. Questions must be directly relevant to the patient's specific condition — not generic.
2. Use plain, patient-friendly language (the physio will read these questions to the patient).
3. Each question should reveal information that cannot already be inferred from the history.
4. 2 questions per domain is ideal; 3 only if the domain is highly relevant to this case.
5. Do NOT repeat information already known from the history — build on it.
6. Return ONLY valid JSON. No markdown, no prose outside the JSON object.
7. Each question list must be an array of strings, even if only 1 question.
"""

SUBJECTIVE_QUESTIONS_USER_TEMPLATE = """Patient details:
- Age / Sex: {age_sex}
- Present History: {present_history}
- Past History: {past_history}

Pathophysiological Mechanism findings (from previous screen):
- Area Involved: {area_involved}
- Presenting Symptom: {presenting_symptom}
- Pain Type: {pain_type}
- Pain Nature: {pain_nature}
- Pain Severity (VAS): {pain_severity}/10
- Possible Source: {possible_source}
- Stage of Healing: {stage_healing}

Generate focused patient interview questions for each ICF domain below.
The physiotherapist will ask these questions directly to the patient and record the answers.

Return this exact JSON structure:

{{
  "body_structure_questions": [
    "<Question about specific anatomical structures, localisation, visible/palpable changes>"
  ],
  "body_function_questions": [
    "<Question about pain behaviour, ROM, strength, sensation, neurological symptoms>"
  ],
  "activity_performance_questions": [
    "<Question about what the patient actually CANNOT do in their daily life right now>"
  ],
  "activity_capacity_questions": [
    "<Question about what the patient CAN do with difficulty — their actual capacity>"
  ],
  "contextual_environmental_questions": [
    "<Question about home setup, work environment, barriers or aids that affect their condition>"
  ],
  "contextual_personal_questions": [
    "<Question about occupation, lifestyle, beliefs about recovery, motivation, support system>"
  ]
}}

Make questions specific to this patient. For example, if the patient has shoulder pain:
- Do NOT ask "Where is your pain?" (already known)
- DO ask "Does the pain travel down your arm, or does it stay in the shoulder region?"
"""


def build_subjective_questions_user_prompt(
    age_sex: str,
    present_history: str,
    past_history: str,
    patho_data: dict,
) -> str:
    """Format the user prompt for ICF question generation."""
    return SUBJECTIVE_QUESTIONS_USER_TEMPLATE.format(
        age_sex=age_sex or "Not provided",
        present_history=present_history or "Not provided",
        past_history=past_history or "None reported",
        area_involved=patho_data.get("area_involved") or "Not recorded",
        presenting_symptom=patho_data.get("presenting_symptom") or "Not recorded",
        pain_type=patho_data.get("pain_type") or "Not recorded",
        pain_nature=patho_data.get("pain_nature") or "Not recorded",
        pain_severity=patho_data.get("pain_severity") or "Not recorded",
        possible_source=patho_data.get("possible_source") or "Not recorded",
        stage_healing=patho_data.get("stage_healing") or "Not recorded",
    )


# ICF field keys — used for validation in the service layer
SUBJECTIVE_ICF_FIELDS = [
    "body_structure_questions",
    "body_function_questions",
    "activity_performance_questions",
    "activity_capacity_questions",
    "contextual_environmental_questions",
    "contextual_personal_questions",
]


# ─────────────────────────────────────────────────────────────────────────────
# INITIAL PLAN OF ASSESSMENT — STAGE 1 PRE-FILLS
# Called when physio reaches the Initial Plan screen in Quick Mode.
# Inputs: patient history + patho mechanism findings.
# Purpose: AI recommends which assessment category applies to each test type
#          (Mandatory / With Precaution / Contraindicated) with a 1-line reason.
#          The details/findings textareas are always left blank — the physio
#          fills those after physically performing the tests.
# ─────────────────────────────────────────────────────────────────────────────

INITIAL_PLAN_SYSTEM = """You are a physiotherapy clinical reasoning assistant helping a \
physiotherapist plan their initial objective assessment for a specific patient.

You will be given patient history and pathophysiological mechanism findings.
Your job is to:
  1. Recommend an assessment category for each of 7 examination types.
  2. List the specific test names the physio should perform within each category.

STRICT RULES:
1. Base recommendations ONLY on the information provided.
2. Stage of healing strongly influences precautions:
   - Acute (0-72h): protect healing tissue.
   - Subacute (4-21 days): progressive loading appropriate.
   - Chronic (>3 weeks): comprehensive assessment generally appropriate.
3. Neurogenic or visceral source warrants neurodynamic testing.
4. "Absolutely Contraindicated" only for genuine clinical reason; set its _tests to [].
5. Reasoning must be ONE concise sentence.
6. _tests: list 2-5 specific named physiotherapy tests for the area and symptom.
   Use standard names (e.g. "Hawkins-Kennedy Test", "Lumbar Flexion ROM", "Slump Test").
7. Return ONLY valid JSON. No markdown, no prose outside the JSON object.
"""

INITIAL_PLAN_USER_TEMPLATE = """Patient details:
- Age / Sex: {age_sex}
- Present History: {present_history}
- Past History: {past_history}

Pathophysiological Mechanism findings:
- Area Involved: {area_involved}
- Presenting Symptom: {presenting_symptom}
- Pain Type: {pain_type}
- Pain Nature: {pain_nature}
- Pain Severity (VAS): {pain_severity}/10
- Pain Irritability: {pain_irritability}
- Possible Source: {possible_source}
- Stage of Healing: {stage_healing}

For each assessment type, recommend a category, give a 1-sentence clinical reason, and list the specific tests.

Valid categories (use EXACTLY as written):
- Mandatory assessment
- Assessment with precaution
- Absolutely Contraindicated

Return this exact JSON structure:

{{
  "active_movements": "<category>",
  "active_movements_reasoning": "<1 sentence>",
  "active_movements_tests": ["<test name>", "<test name>"],
  "passive_movements": "<category>",
  "passive_movements_reasoning": "<1 sentence>",
  "passive_movements_tests": ["<test name>", "<test name>"],
  "passive_over_pressure": "<category>",
  "passive_over_pressure_reasoning": "<1 sentence>",
  "passive_over_pressure_tests": ["<test name>", "<test name>"],
  "resisted_movements": "<category>",
  "resisted_movements_reasoning": "<1 sentence>",
  "resisted_movements_tests": ["<test name>", "<test name>"],
  "combined_movements": "<category>",
  "combined_movements_reasoning": "<1 sentence>",
  "combined_movements_tests": ["<test name>", "<test name>"],
  "special_tests": "<category>",
  "special_tests_reasoning": "<1 sentence>",
  "special_tests_tests": ["<test name>", "<test name>"],
  "neurodynamic": "<category>",
  "neurodynamic_reasoning": "<1 sentence>",
  "neurodynamic_tests": ["<test name>", "<test name>"]
}}
"""



def build_initial_plan_user_prompt(patient: dict, patho_data: dict) -> str:
    """Format the user prompt for initial plan prefills."""
    return INITIAL_PLAN_USER_TEMPLATE.format(
        age_sex=patient.get("age_sex") or "Not provided",
        present_history=patient.get("present_history") or "Not provided",
        past_history=patient.get("past_history") or "None reported",
        area_involved=patho_data.get("area_involved") or "Not recorded",
        presenting_symptom=patho_data.get("presenting_symptom") or "Not recorded",
        pain_type=patho_data.get("pain_type") or "Not recorded",
        pain_nature=patho_data.get("pain_nature") or "Not recorded",
        pain_severity=patho_data.get("pain_severity") or "Not recorded",
        pain_irritability=patho_data.get("pain_irritability") or "Not recorded",
        possible_source=patho_data.get("possible_source") or "Not recorded",
        stage_healing=patho_data.get("stage_healing") or "Not recorded",
    )


# The 7 test keys — field names match the HTML template (form submission keys)
INITIAL_PLAN_TESTS = [
    "active_movements",
    "passive_movements",
    "passive_over_pressure",
    "resisted_movements",
    "combined_movements",
    "special_tests",
    "neurodynamic",
]

INITIAL_PLAN_VALID_CATEGORIES = [
    "Mandatory assessment",
    "Assessment with precaution",
    "Absolutely Contraindicated",
]


# ─────────────────────────────────────────────────────────────────────────────
# RISK FACTORS & CLINICAL FLAGS — STAGE 1 PRE-FILLS
# Called when physio reaches the Risk Factors & Clinical Flags screen in QM.
# Inputs: patient history + patho mechanism findings.
# Purpose:
#   1. Pre-check the relevant chronic disease maintenance cause checkboxes.
#   2. Pre-fill specific_factors with a SHORT 1-sentence summary.
#   3. Pre-fill any clinical flags that are clearly evident from history
#      (short — 1-2 bullet points max per flag, or "" if none identified).
# Output must be deliberately SHORT — the physio reviews and approves,
# not reads a long report.
# ─────────────────────────────────────────────────────────────────────────────

RISK_FLAGS_SYSTEM = """You are a physiotherapy clinical reasoning assistant helping a \
physiotherapist screen for chronic disease maintenance factors and clinical flags.

You will be given a patient's history and pathophysiological mechanism findings.
Your job is to:
1. Identify which maintenance cause categories are likely relevant (from a fixed list).
2. Write a SHORT (1 sentence) summary of the specific maintaining factors.
3. Screen for all 5 clinical flag types — be PROACTIVE and INCLUSIVE.

STRICT RULES:
1. Base assessments ONLY on information stated or reasonably implied by the history.
2. maintenance_causes: include ALL categories that are plausibly relevant. If a category
   could reasonably apply given the history, include it — the physio can deselect if needed.
   Return at minimum 1-2 causes unless the history is completely devoid of context.
3. specific_factors: ONE concise sentence only. No headers, no bullet points.
4. For each flag type: if there is ANY indicator, hint, or implication in the history,
   write 1-2 short bullet points (use "• " prefix). Err on the side of inclusion —
   it is safer to flag something for the physio to review than to miss it.
5. Red flags (serious pathology indicators) must be flagged even if only mildly suggested
   — clinical safety takes priority above all else.
6. Yellow flags: include if there is ANY mention of distress, anxiety, fear, work concerns,
   frustration, or uncertainty about recovery — these are extremely common in physio.
7. Return ONLY valid JSON. No markdown, no prose outside the JSON object.
"""

RISK_FLAGS_USER_TEMPLATE = """Patient details:
- Age / Sex: {age_sex}
- Present History: {present_history}
- Past History: {past_history}

Pathophysiological Mechanism findings:
- Area Involved: {area_involved}
- Presenting Symptom: {presenting_symptom}
- Possible Source: {possible_source}
- Stage of Healing: {stage_healing}
- Pain Severity (VAS): {pain_severity}/10
- Pain Irritability: {pain_irritability}

Subjective Examination findings (ICF model):
- Body Structure: {body_structure}
- Body Function (symptom behaviour, 24-hour pattern, aggravating/easing factors): {body_function}
- Activity Performance: {activity_performance}
- Activity Capacity: {activity_capacity}
- Contextual Factors (Environmental): {contextual_environmental}
- Contextual Factors (Personal): {contextual_personal}

Generate pre-fills for the Risk Factors & Clinical Flags screen.

ALLOWED maintenance cause values (use EXACTLY as written, array may be empty):
{maintenance_cause_options}

Return this exact JSON structure:

{{
  "maintenance_causes": ["<only values from allowed list above>"],
  "specific_factors": "<1 sentence summary of the key maintaining factors — or empty string if none evident>",
  "red_flags": "<1-2 bullet points using '• ' prefix if red flags present — else empty string>",
  "orange_flags": "<1-2 bullet points if psychiatric symptoms evident — else empty string>",
  "yellow_flags": "<1-2 bullet points if psychosocial barriers evident — else empty string>",
  "black_flags": "<1-2 bullet points if system/environmental barriers evident — else empty string>",
  "blue_flags": "<1-2 bullet points if work-related attitudes/demands evident — else empty string>"
}}

Flag type definitions (for your reference):
- Red flags: serious pathology indicators (e.g. night pain, unexplained weight loss, bilateral neuro symptoms, bowel/bladder dysfunction)
- Orange flags: symptoms suggestive of psychiatric illness (severe depression, PTSD, psychosis indicators)
- Yellow flags (psychosocial): fear-avoidance, catastrophising, low self-efficacy, poor recovery expectation
- Black flags (systems/environment): compensation claims, litigation, unsupportive employer or healthcare system
- Blue flags (work-related): beliefs that work caused or worsens condition, low job satisfaction, fear of re-injury at work
"""


def build_risk_flags_user_prompt(patient: dict, patho_data: dict, subjective_data: dict = None) -> str:
    """Format the user prompt for risk factors & clinical flags prefills."""
    options_str = "\n".join(f'- "{o}"' for o in MAINTENANCE_CAUSE_OPTIONS)
    subjective_data = subjective_data or {}
    return RISK_FLAGS_USER_TEMPLATE.format(
        age_sex=patient.get("age_sex") or "Not provided",
        present_history=patient.get("present_history") or "Not provided",
        past_history=patient.get("past_history") or "None reported",
        area_involved=patho_data.get("area_involved") or "Not recorded",
        presenting_symptom=patho_data.get("presenting_symptom") or "Not recorded",
        possible_source=patho_data.get("possible_source") or "Not recorded",
        stage_healing=patho_data.get("stage_healing") or "Not recorded",
        pain_severity=patho_data.get("pain_severity") or "Not recorded",
        pain_irritability=patho_data.get("pain_irritability") or "Not recorded",
        body_structure=subjective_data.get("body_structure") or "Not recorded",
        body_function=subjective_data.get("body_function") or "Not recorded",
        activity_performance=subjective_data.get("activity_performance") or "Not recorded",
        activity_capacity=subjective_data.get("activity_capacity") or "Not recorded",
        contextual_environmental=subjective_data.get("contextual_environmental") or "Not recorded",
        contextual_personal=subjective_data.get("contextual_personal") or "Not recorded",
        maintenance_cause_options=options_str,
    )


# Allowed maintenance cause options — must match the template checkboxes exactly
MAINTENANCE_CAUSE_OPTIONS = [
    "Physical/Biomechanical Issues",
    "Psychological Factors",
    "Social or Environmental Conditions",
    "Lifestyle / Behavioral",
    "Work-related",
    "Others",
]

# Clinical flag field names
FLAG_FIELDS = [
    "red_flags",
    "orange_flags",
    "yellow_flags",
    "black_flags",
    "blue_flags",
]


# ─────────────────────────────────────────────────────────────────────────────
# OBJECTIVE ASSESSMENT — STAGE 2 PRE-FILLS
# Called when physio reaches the Objective Assessment screen in Quick Mode.
#
# This is the SECOND AI call (Stage 2). It has everything from Stage 1 PLUS
# the actual examination findings the physio entered in the Initial Plan.
# The AI now suggests HOW to examine each domain (specific tests, measures)
# based on what the initial plan revealed. Physio reads the guidance card,
# performs the tests, and enters findings in the blank textarea below.
# Blank domains are excluded from report generation and Stage 3 AI.
# ─────────────────────────────────────────────────────────────────────────────

OBJ_ASSESSMENT_SYSTEM = """You are a physiotherapy clinical reasoning assistant helping a \
physiotherapist plan their objective assessment.

This is Stage 2 — you now have BOTH the patient history AND the examination findings from \
the Initial Plan of Assessment. Use this to generate a concise, targeted assessment plan \
for the physiotherapist to follow during their objective examination session.

STRICT RULES:
1. Base recommendations on the history AND the Initial Plan findings combined.
2. Write as a structured clinical note the physio will read and follow — plain, direct language.
3. Include: what structures to observe/palpate, which ROM movements to measure (with reference \
   ranges), which special tests to perform, and any neurological screen if indicated.
4. Keep it concise — this pre-fills a single notes field, not a report.
5. If neurogenic/radicular component is absent, omit neurological screen.
6. Suggest whether the plan is "Comprehensive without modification" or \
   "Comprehensive with modifications" (use the latter if precautions apply).
7. Return ONLY valid JSON. No markdown, no prose outside the JSON object.
"""

OBJ_ASSESSMENT_USER_TEMPLATE = """Patient details:
- Age / Sex: {age_sex}
- Present History: {present_history}
- Past History: {past_history}

Pathophysiological Mechanism findings:
- Area Involved: {area_involved}
- Presenting Symptom: {presenting_symptom}
- Possible Source: {possible_source}
- Stage of Healing: {stage_healing}
- Pain Severity (VAS): {pain_severity}/10
- Pain Irritability: {pain_irritability}

Initial Plan of Assessment — Examination Findings (Stage 1 results):
{initial_plan_findings}

Generate a concise objective assessment plan for this patient.

Return this exact JSON structure:

{{
  "plan": "<one of: 'Comprehensive without modification' | 'Comprehensive with modifications'>",
  "plan_details": "<targeted assessment guidance as a structured clinical note — use line breaks between sections, e.g. Observation: ..., Palpation: ..., ROM: ..., Special Tests: ..., Neuro screen (if indicated): ...>"
}}

Keep plan_details to 5-8 lines maximum. It pre-fills a notes textarea the physio will \
edit after performing the examination.
"""


def _format_initial_plan_findings(initial_plan_data: dict) -> str:
    """
    Convert the initial_plan Cosmos document into a readable string
    for the Stage 2 AI prompt.
    """
    if not initial_plan_data:
        return "No Initial Plan findings available."

    lines = []
    test_labels = {
        "active_movements": "Active Movements",
        "passive_movements": "Passive Movements",
        "passive_over_pressure": "Passive Over Pressure",
        "resisted_movements": "Resisted Movements",
        "combined_movements": "Combined Movements",
        "special_tests": "Special Tests",
        "neurodynamic": "Neurodynamic Examination",
    }
    for key, label in test_labels.items():
        findings = initial_plan_data.get(f"{key}_details", "").strip()
        if findings:
            lines.append(f"- {label}: {findings}")

    return "\n".join(lines) if lines else "No examination findings recorded in Initial Plan."


def build_obj_assessment_user_prompt(
    patient: dict,
    patho_data: dict,
    initial_plan_data: dict,
) -> str:
    """Format the Stage 2 user prompt for objective assessment prefills."""
    return OBJ_ASSESSMENT_USER_TEMPLATE.format(
        age_sex=patient.get("age_sex") or "Not provided",
        present_history=patient.get("present_history") or "Not provided",
        past_history=patient.get("past_history") or "None reported",
        area_involved=patho_data.get("area_involved") or "Not recorded",
        presenting_symptom=patho_data.get("presenting_symptom") or "Not recorded",
        possible_source=patho_data.get("possible_source") or "Not recorded",
        stage_healing=patho_data.get("stage_healing") or "Not recorded",
        pain_severity=patho_data.get("pain_severity") or "Not recorded",
        pain_irritability=patho_data.get("pain_irritability") or "Not recorded",
        initial_plan_findings=_format_initial_plan_findings(initial_plan_data),
    )


# Valid plan dropdown values for objective assessment
OBJ_ASSESSMENT_PLAN_OPTIONS = [
    "Comprehensive without modification",
    "Comprehensive with modifications",
]


# ─────────────────────────────────────────────────────────────────────────────
# PROVISIONAL DIAGNOSIS — STAGE 2 PRE-FILLS
# Called when physio reaches Provisional Diagnosis in Quick Mode.
# By this point Stage 2 has: history + patho + initial plan findings +
# objective assessment notes.
#
# Design:
#   - Each of the 5 fields returns a SHORT pre-fill (1-2 sentences) suitable
#     for direct use in the form.
#   - Each field also returns a _reasoning key with a more detailed clinical
#     explanation — shown only when the physio clicks "Clinical Reasoning".
#   - hypothesis_supported is pre-selected (Yes/No).
# ─────────────────────────────────────────────────────────────────────────────

PROV_DIAG_SYSTEM = """You are a physiotherapy clinical reasoning assistant generating \
a provisional diagnosis for a specific patient based on all available clinical data.

You have access to: patient history, pathophysiological mechanism findings, initial plan \
examination findings, and objective assessment notes.

Your job is to produce a concise provisional diagnosis across 5 structured fields, \
plus a brief but detailed clinical reasoning for each field that the physiotherapist \
can reveal on demand.

STRICT RULES:
1. Base everything ONLY on the clinical data provided — never invent findings.
2. Each field value must be SHORT — 1-2 sentences maximum. This is what pre-fills the form.
3. Each _reasoning must be more detailed — 2-4 sentences explaining the clinical logic. \
   The physio reads this only if they want deeper justification.
4. hypothesis_supported: "Yes" if the overall clinical picture supports a clear diagnosis; \
   "No" if the picture is inconclusive or contradictory.
5. Use conditional language where appropriate (likely, consistent with, suggestive of).
6. findings_reject should be honest — what does NOT fit the diagnosis? If nothing \
   strongly rejects it, say so briefly.
7. Return ONLY valid JSON. No markdown, no prose outside the JSON object.
"""

PROV_DIAG_USER_TEMPLATE = """Patient details:
- Age / Sex: {age_sex}
- Present History: {present_history}
- Past History: {past_history}

Pathophysiological Mechanism findings:
- Area Involved: {area_involved}
- Presenting Symptom: {presenting_symptom}
- Possible Source: {possible_source}
- Stage of Healing: {stage_healing}
- Pain Severity (VAS): {pain_severity}/10
- Pain Nature: {pain_nature}
- Pain Irritability: {pain_irritability}

Initial Plan — Examination Findings:
{initial_plan_findings}

Objective Assessment:
- Plan: {obj_plan}
- Notes / Findings: {obj_notes}

Generate a provisional diagnosis. Keep field values SHORT (1-2 sentences for direct \
form use). _reasoning values should be more detailed (2-4 sentences).

Return this exact JSON structure:

{{
  "likelihood": "<1-2 sentences: most likely diagnosis with estimated probability e.g. 'High likelihood (>75%)'>",
  "likelihood_reasoning": "<2-4 sentences: clinical rationale for this likelihood>",
  "structure_fault": "<1-2 sentences: primary structure at fault, secondary if relevant>",
  "structure_fault_reasoning": "<2-4 sentences: why this structure based on the findings>",
  "symptom": "<1-2 sentences: primary symptom pattern and mechanism>",
  "symptom_reasoning": "<2-4 sentences: how the symptom pattern supports the diagnosis>",
  "findings_support": "<1-2 sentences: key findings that support this diagnosis>",
  "findings_support_reasoning": "<2-4 sentences: detailed explanation of supporting findings>",
  "findings_reject": "<1-2 sentences: findings that argue against this diagnosis, or state none identified>",
  "findings_reject_reasoning": "<2-4 sentences: explanation of why these findings are notable or why none are present>",
  "hypothesis_supported": "<Yes or No>"
}}
"""


def build_prov_diag_user_prompt(
    patient: dict,
    patho_data: dict,
    initial_plan_data: dict,
    obj_data: dict,
) -> str:
    """Format the Stage 2 user prompt for provisional diagnosis prefills."""
    obj_plan = obj_data.get("plan", "") or "Not recorded"
    obj_notes = obj_data.get("plan_details", "") or "Not recorded"

    return PROV_DIAG_USER_TEMPLATE.format(
        age_sex=patient.get("age_sex") or "Not provided",
        present_history=patient.get("present_history") or "Not provided",
        past_history=patient.get("past_history") or "None reported",
        area_involved=patho_data.get("area_involved") or "Not recorded",
        presenting_symptom=patho_data.get("presenting_symptom") or "Not recorded",
        possible_source=patho_data.get("possible_source") or "Not recorded",
        stage_healing=patho_data.get("stage_healing") or "Not recorded",
        pain_severity=patho_data.get("pain_severity") or "Not recorded",
        pain_nature=patho_data.get("pain_nature") or "Not recorded",
        pain_irritability=patho_data.get("pain_irritability") or "Not recorded",
        initial_plan_findings=_format_initial_plan_findings(initial_plan_data),
        obj_plan=obj_plan,
        obj_notes=obj_notes,
    )


# The 5 text field names for provisional diagnosis (matches form and DB keys)
PROV_DIAG_FIELDS = [
    "likelihood",
    "structure_fault",
    "symptom",
    "findings_support",
    "findings_reject",
]


# ─────────────────────────────────────────────────────────────────────────────
# SMART GOALS — STAGE 2 PRE-FILLS
# Called when physio reaches SMART Goals in Quick Mode.
# Context: patient history + patho + provisional diagnosis + perspectives.
#
# CRITICAL OUTPUT CONSTRAINT:
#   Each field must be SHORT — 2-3 bullet points ONLY using "• " prefix.
#   No paragraphs, no headers, no sub-bullets, no lengthy explanations.
#   The physio edits these into their own words before saving.
# ─────────────────────────────────────────────────────────────────────────────

SMART_GOALS_SYSTEM = """You are a physiotherapy clinical reasoning assistant generating \
SMART Goals for a specific patient based on their diagnosis and clinical data.

CRITICAL OUTPUT RULE — STRICTLY ENFORCED:
Each field must contain ONLY 2-3 bullet points using "• " as the prefix.
NO paragraphs. NO headers. NO sub-bullets. NO explanations beyond the bullet point itself.
If you write more than 3 bullets for any field, your response is incorrect.

SMART Goals principles to apply:
- patient_goal: what the PATIENT wants to achieve — use the patient's perspective and any \
  illness beliefs or expectations from perspectives data. Focus on function, not anatomy.
- outcome_timeframe: combine the measurable outcome AND the expected timeframe in each bullet — \
  e.g. "• Achieve 150° shoulder flexion within 6 weeks". 2–3 bullets max, each stating \
  what the patient will achieve and by when, based on diagnosis and tissue healing stage.

Return ONLY valid JSON. No markdown, no prose outside the JSON object.
"""

SMART_GOALS_USER_TEMPLATE = """Patient details:
- Age / Sex: {age_sex}
- Present History: {present_history}
- Past History: {past_history}

Pathophysiological Mechanism:
- Area Involved: {area_involved}
- Stage of Healing: {stage_healing}
- Pain Severity (VAS): {pain_severity}/10

Provisional Diagnosis:
- Likelihood: {likelihood}
- Structure at Fault: {structure_fault}
- Hypothesis Supported: {hypothesis_supported}

Patient Perspectives (if available):
- Knowledge of Illness: {knowledge}
- Expectation About Illness: {expectation}
- Locus of Control: {locus_of_control}
- Affective Aspect: {affective_aspect}

Generate SMART Goals. STRICT LIMIT: 2-3 bullet points per field, "• " prefix, NO paragraphs.

Return this exact JSON structure:

{{
  "patient_goal": "• <goal 1>\\n• <goal 2>\\n• <goal 3 if needed>",
  "outcome_timeframe": "• <outcome + timeframe 1>\\n• <outcome + timeframe 2>\\n• <outcome + timeframe 3 if needed>"
}}
"""


def build_smart_goals_user_prompt(
    patient: dict,
    patho_data: dict,
    prov_diag_data: dict,
    perspectives_data: dict,
) -> str:
    """Format the Stage 2 user prompt for SMART Goals prefills."""
    return SMART_GOALS_USER_TEMPLATE.format(
        age_sex=patient.get("age_sex") or "Not provided",
        present_history=patient.get("present_history") or "Not provided",
        past_history=patient.get("past_history") or "None reported",
        area_involved=patho_data.get("area_involved") or "Not recorded",
        stage_healing=patho_data.get("stage_healing") or "Not recorded",
        pain_severity=patho_data.get("pain_severity") or "Not recorded",
        likelihood=prov_diag_data.get("likelihood") or "Not recorded",
        structure_fault=prov_diag_data.get("structure_fault") or "Not recorded",
        hypothesis_supported=prov_diag_data.get("hypothesis_supported") or "Not recorded",
        knowledge=perspectives_data.get("knowledge") or "Not recorded",
        expectation=perspectives_data.get("expectation") or "Not recorded",
        locus_of_control=perspectives_data.get("locus_of_control") or "Not recorded",
        affective_aspect=perspectives_data.get("affective_aspect") or "Not recorded",
    )


SMART_GOALS_FIELDS = ["patient_goal", "outcome_timeframe"]


# ─────────────────────────────────────────────────────────────────────────────
# TREATMENT PLAN — STAGE 2 PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

TREATMENT_PLAN_SYSTEM = """You are a physiotherapy clinical documentation assistant.
Your job is to generate a concise Treatment Plan based on diagnosis and assessment findings.

CRITICAL OUTPUT RULE — STRICTLY ENFORCED:
Each field (treatment_plan, reasoning) must contain ONLY 2-3 bullet points
using "• " as the prefix. Separate bullets with a newline character.
NO paragraphs. NO headers. NO sub-bullets. NO lengthy explanations.
If you write more than 3 bullets for any field, your response is incorrect.

Return ONLY a valid JSON object — no markdown, no commentary, no extra keys."""

TREATMENT_PLAN_USER_TEMPLATE = """\
Patient: {age_sex}
Present History: {present_history}
Past History: {past_history}

Pathomechanics:
- Area Involved: {area_involved}
- Stage of Healing: {stage_healing}
- Pain Severity: {pain_severity}

Provisional Diagnosis:
- Likelihood: {likelihood}
- Structure at Fault: {structure_fault}
- Hypothesis Supported: {hypothesis_supported}

SMART Goals:
- Patient Goal: {patient_goal}
- Outcomes & Timeframe: {outcome_timeframe}

Objective Assessment Notes: {obj_assessment_notes}

Generate a Treatment Plan. STRICT LIMIT: 2-3 bullet points per field, "• " prefix, NO paragraphs.

Return this exact JSON structure:

{{
  "treatment_plan": "• <intervention 1>\\n• <intervention 2>\\n• <intervention 3 if needed>",
  "reasoning": "• <rationale 1>\\n• <rationale 2>\\n• <rationale 3 if needed>"
}}
"""


def build_treatment_plan_user_prompt(
    patient: dict,
    patho_data: dict,
    prov_diag_data: dict,
    smart_goals_data: dict,
    obj_assessment_data: dict,
) -> str:
    """Format the Stage 2 user prompt for Treatment Plan prefills."""
    return TREATMENT_PLAN_USER_TEMPLATE.format(
        age_sex=patient.get("age_sex") or "Not provided",
        present_history=patient.get("present_history") or "Not provided",
        past_history=patient.get("past_history") or "None reported",
        area_involved=patho_data.get("area_involved") or "Not recorded",
        stage_healing=patho_data.get("stage_healing") or "Not recorded",
        pain_severity=patho_data.get("pain_severity") or "Not recorded",
        likelihood=prov_diag_data.get("likelihood") or "Not recorded",
        structure_fault=prov_diag_data.get("structure_fault") or "Not recorded",
        hypothesis_supported=prov_diag_data.get("hypothesis_supported") or "Not recorded",
        patient_goal=smart_goals_data.get("patient_goal") or "Not recorded",
        outcome_timeframe=smart_goals_data.get("outcome_timeframe") or "Not recorded",
        obj_assessment_notes=obj_assessment_data.get("plan_details") or obj_assessment_data.get("assessment_notes") or "Not recorded",
    )


TREATMENT_PLAN_FIELDS = ["treatment_plan", "reasoning"]
