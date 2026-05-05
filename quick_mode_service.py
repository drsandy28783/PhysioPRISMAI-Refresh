"""
Quick Mode Service — PhysiologicPRISM
=======================================
Generates AI pre-fills for each Quick Mode assessment screen.

Design principles:
- Every public function returns a plain dict (never raises).
- On any failure (AI timeout, JSON parse error, bad response), the function
  returns an empty dict so the caller can fall back to a blank form gracefully.
- Validation against known dropdown values happens here before the dict is
  returned — so templates can trust the values are safe to use in <select>
  and <option> elements.
- No caching in v1 — prefills are generated on first GET of each QM screen.
  Caching can be layered in later via Cosmos TTL documents.
"""

import logging
from typing import Dict, Any

from azure_openai_client import get_azure_openai_client
from quick_mode_prompts import (
    PATHO_MECHANISM_SYSTEM,
    PATHO_VALID_OPTIONS,
    build_patho_mechanism_user_prompt,
    SUBJECTIVE_QUESTIONS_SYSTEM,
    SUBJECTIVE_ICF_FIELDS,
    build_subjective_questions_user_prompt,
    INITIAL_PLAN_SYSTEM,
    INITIAL_PLAN_TESTS,
    INITIAL_PLAN_VALID_CATEGORIES,
    build_initial_plan_user_prompt,
    RISK_FLAGS_SYSTEM,
    MAINTENANCE_CAUSE_OPTIONS,
    FLAG_FIELDS,
    build_risk_flags_user_prompt,
    OBJ_ASSESSMENT_SYSTEM,
    OBJ_ASSESSMENT_PLAN_OPTIONS,
    build_obj_assessment_user_prompt,
    PROV_DIAG_SYSTEM,
    PROV_DIAG_FIELDS,
    build_prov_diag_user_prompt,
    SMART_GOALS_SYSTEM,
    SMART_GOALS_FIELDS,
    build_smart_goals_user_prompt,
    TREATMENT_PLAN_SYSTEM,
    TREATMENT_PLAN_FIELDS,
    build_treatment_plan_user_prompt,
)

logger = logging.getLogger("app.quick_mode")


# ─────────────────────────────────────────────────────────────────────────────
# PATHO MECHANISM
# ─────────────────────────────────────────────────────────────────────────────

def generate_patho_prefills(patient: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate AI pre-fills for the Pathophysiological Mechanism screen.

    Args:
        patient: Patient document dict from Firestore (must contain
                 age_sex, present_history, past_history).

    Returns:
        Dict with keys:
            area_involved           (str or "")
            presenting_symptom      (str or "")
            possible_source         (str — validated against dropdown options, or "")
            possible_source_reasoning (str or "")
            stage_healing           (str — validated against dropdown options, or "")
            stage_healing_reasoning (str or "")

        Returns {} on any error so callers can fall back to a blank form.
    """
    try:
        age_sex          = patient.get("age_sex", "")
        present_history  = patient.get("present_history", "")
        past_history     = patient.get("past_history", "")

        if not present_history:
            logger.warning("Quick Mode patho prefill: no present_history available")
            return {}

        client = get_azure_openai_client()

        user_prompt = build_patho_mechanism_user_prompt(
            age_sex=age_sex,
            present_history=present_history,
            past_history=past_history,
        )

        raw = client.generate_json_response(
            system_prompt=PATHO_MECHANISM_SYSTEM,
            user_prompt=user_prompt,
        )

        if not raw or "error" in raw:
            logger.error(f"Quick Mode patho prefill: AI returned error — {raw}")
            return {}

        prefills = _validate_patho_prefills(raw)
        logger.info("Quick Mode patho prefills generated successfully")
        return prefills

    except Exception as e:
        logger.error(f"Quick Mode patho prefill failed: {e}", exc_info=True)
        return {}


def _validate_patho_prefills(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitise and validate the raw AI JSON for the patho mechanism screen.

    - String fields are stripped; None/missing become "".
    - Dropdown fields are checked against the allowed values list.
      If the AI returns an invalid option, the field is blanked so the
      physio has to choose manually — we never silently accept a bad value.
    """
    def safe_str(key: str) -> str:
        val = raw.get(key)
        if val is None:
            return ""
        return str(val).strip()

    def safe_dropdown(key: str, allowed: list) -> str:
        val = safe_str(key)
        if val in allowed:
            return val
        if val:
            logger.warning(
                f"Quick Mode: AI returned invalid '{key}' value '{val}' — blanking field"
            )
        return ""

    return {
        "area_involved": safe_str("area_involved"),
        "presenting_symptom": safe_str("presenting_symptom"),
        "possible_source": safe_dropdown("possible_source", PATHO_VALID_OPTIONS["possible_source"]),
        "possible_source_reasoning": safe_str("possible_source_reasoning"),
        "stage_healing": safe_dropdown("stage_healing", PATHO_VALID_OPTIONS["stage_healing"]),
        "stage_healing_reasoning": safe_str("stage_healing_reasoning"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SUBJECTIVE / PATIENT FUNCTIONING ASSESSMENT — ICF QUESTIONS
# ─────────────────────────────────────────────────────────────────────────────

def generate_subjective_questions(
    patient: Dict[str, Any],
    patho_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate targeted interview questions for each ICF domain.

    Args:
        patient:    Patient document dict (age_sex, present_history, past_history).
        patho_data: Most recent patho_mechanism document for this patient.

    Returns:
        Dict with one key per ICF field, each holding a list of question strings:
            body_structure_questions        (list[str])
            body_function_questions         (list[str])
            activity_performance_questions  (list[str])
            activity_capacity_questions     (list[str])
            contextual_environmental_questions (list[str])
            contextual_personal_questions   (list[str])

        Returns {} on any error — template falls back to plain blank text areas.
    """
    try:
        present_history = patient.get("present_history", "")
        if not present_history:
            logger.warning("Quick Mode subjective questions: no present_history available")
            return {}

        client = get_azure_openai_client()

        user_prompt = build_subjective_questions_user_prompt(
            age_sex=patient.get("age_sex", ""),
            present_history=present_history,
            past_history=patient.get("past_history", ""),
            patho_data=patho_data or {},
        )

        raw = client.generate_json_response(
            system_prompt=SUBJECTIVE_QUESTIONS_SYSTEM,
            user_prompt=user_prompt,
        )

        if not raw or "error" in raw:
            logger.error(f"Quick Mode subjective questions: AI returned error — {raw}")
            return {}

        questions = _validate_subjective_questions(raw)
        logger.info("Quick Mode subjective questions generated successfully")
        return questions

    except Exception as e:
        logger.error(f"Quick Mode subjective questions failed: {e}", exc_info=True)
        return {}


def _validate_subjective_questions(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitise the AI's question lists.

    - Each field must be a list of strings.
    - Non-list values are wrapped or discarded.
    - Empty strings within lists are stripped out.
    - If a field is missing entirely, it gets an empty list (template shows
      a plain text area with no question card).
    """
    result = {}
    for field in SUBJECTIVE_ICF_FIELDS:
        val = raw.get(field)
        if isinstance(val, list):
            cleaned = [str(q).strip() for q in val if str(q).strip()]
            result[field] = cleaned
        elif isinstance(val, str) and val.strip():
            result[field] = [val.strip()]
        else:
            result[field] = []
    return result


# ─────────────────────────────────────────────────────────────────────────────
# INITIAL PLAN OF ASSESSMENT — STAGE 1 PRE-FILLS
# ─────────────────────────────────────────────────────────────────────────────

def generate_initial_plan_prefills(
    patient: Dict[str, Any],
    patho_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate AI-recommended assessment categories for each test type.

    Returns a dict with, for each of the 7 tests:
        {test}            (str) — one of the 3 valid categories, or ""
        {test}_reasoning  (str) — 1-sentence clinical rationale

    Details/findings textareas are never pre-filled — physio enters those
    after performing the tests. Tests with empty details are excluded from
    Stage 2 AI generation and report output.

    Returns {} on any error so the template falls back gracefully.
    """
    try:
        if not patient.get("present_history"):
            logger.warning("Quick Mode initial plan: no present_history available")
            return {}

        client = get_azure_openai_client()

        user_prompt = build_initial_plan_user_prompt(patient, patho_data or {})

        raw = client.generate_json_response(
            system_prompt=INITIAL_PLAN_SYSTEM,
            user_prompt=user_prompt,
        )

        if not raw or "error" in raw:
            logger.error(f"Quick Mode initial plan prefill: AI returned error — {raw}")
            return {}

        prefills = _validate_initial_plan_prefills(raw)
        logger.info("Quick Mode initial plan prefills generated successfully")
        return prefills

    except Exception as e:
        logger.error(f"Quick Mode initial plan prefill failed: {e}", exc_info=True)
        return {}


def _validate_initial_plan_prefills(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate AI categories against the 3 allowed values.
    Invalid category → blank string so physio must choose manually.
    Reasoning strings are passed through after stripping.
    """
    result = {}
    for test in INITIAL_PLAN_TESTS:
        category = str(raw.get(test, "")).strip()
        if category not in INITIAL_PLAN_VALID_CATEGORIES:
            if category:
                logger.warning(
                    f"Quick Mode initial plan: invalid category '{category}' for '{test}' — blanking"
                )
            category = ""
        result[test] = category
        result[f"{test}_reasoning"] = str(raw.get(f"{test}_reasoning", "")).strip()
    return result


# ─────────────────────────────────────────────────────────────────────────────
# RISK FACTORS & CLINICAL FLAGS — STAGE 1 PRE-FILLS
# ─────────────────────────────────────────────────────────────────────────────

def generate_risk_flags_prefills(
    patient: Dict[str, Any],
    patho_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate AI pre-fills for the Risk Factors & Clinical Flags screen.

    Returns a dict with:
        maintenance_causes   (list[str]) — subset of MAINTENANCE_CAUSE_OPTIONS
        specific_factors     (str)       — 1-sentence summary, or ""
        red_flags            (str)       — short bullets or ""
        orange_flags         (str)       — short bullets or ""
        yellow_flags         (str)       — short bullets or ""
        black_flags          (str)       — short bullets or ""
        blue_flags           (str)       — short bullets or ""

    Returns {} on any error so the template falls back to blank form.
    """
    try:
        if not patient.get("present_history"):
            logger.warning("Quick Mode risk flags: no present_history available")
            return {}

        client = get_azure_openai_client()
        user_prompt = build_risk_flags_user_prompt(patient, patho_data or {})

        raw = client.generate_json_response(
            system_prompt=RISK_FLAGS_SYSTEM,
            user_prompt=user_prompt,
        )

        if not raw or "error" in raw:
            logger.error(f"Quick Mode risk flags prefill: AI returned error — {raw}")
            return {}

        prefills = _validate_risk_flags_prefills(raw)
        logger.info("Quick Mode risk flags prefills generated successfully")
        return prefills

    except Exception as e:
        logger.error(f"Quick Mode risk flags prefill failed: {e}", exc_info=True)
        return {}


def _validate_risk_flags_prefills(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitise and validate the raw AI JSON for the risk flags screen.

    - maintenance_causes: each item validated against MAINTENANCE_CAUSE_OPTIONS;
      invalid items are silently dropped (physio can re-check manually).
    - specific_factors and each flag field: stripped strings, never None.
    """
    # Validate maintenance causes
    raw_causes = raw.get("maintenance_causes", [])
    if not isinstance(raw_causes, list):
        raw_causes = []
    valid_causes = [c for c in raw_causes if c in MAINTENANCE_CAUSE_OPTIONS]
    invalid = [c for c in raw_causes if c not in MAINTENANCE_CAUSE_OPTIONS]
    if invalid:
        logger.warning(f"Quick Mode risk flags: dropped invalid causes — {invalid}")

    result = {"maintenance_causes": valid_causes}

    # specific_factors — short string
    result["specific_factors"] = str(raw.get("specific_factors", "") or "").strip()

    # Flag fields — short strings or ""
    for field in FLAG_FIELDS:
        result[field] = str(raw.get(field, "") or "").strip()

    return result


# ─────────────────────────────────────────────────────────────────────────────
# OBJECTIVE ASSESSMENT — STAGE 2 PRE-FILLS
# ─────────────────────────────────────────────────────────────────────────────

def generate_obj_assessment_prefills(
    patient: Dict[str, Any],
    patho_data: Dict[str, Any],
    initial_plan_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate Stage 2 AI pre-fills for the Objective Assessment screen.

    This is the second AI call in Quick Mode. It has access to:
    - Patient history
    - Pathophysiological mechanism findings
    - Initial Plan examination findings (active/passive/resisted movements etc.)

    Returns a dict with:
        plan         (str) — validated plan type, or ""
        plan_details (str) — AI-generated assessment guidance, or ""

    Returns {} on any error so the template falls back to a blank form.
    """
    try:
        if not patient.get("present_history"):
            logger.warning("Quick Mode obj assessment: no present_history available")
            return {}

        client = get_azure_openai_client()
        user_prompt = build_obj_assessment_user_prompt(patient, patho_data or {}, initial_plan_data or {})

        raw = client.generate_json_response(
            system_prompt=OBJ_ASSESSMENT_SYSTEM,
            user_prompt=user_prompt,
        )

        if not raw or "error" in raw:
            logger.error(f"Quick Mode obj assessment: AI returned error — {raw}")
            return {}

        prefills = _validate_obj_assessment_prefills(raw)
        logger.info("Quick Mode objective assessment prefills generated successfully (Stage 2)")
        return prefills

    except Exception as e:
        logger.error(f"Quick Mode obj assessment prefill failed: {e}", exc_info=True)
        return {}


def _validate_obj_assessment_prefills(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitise the AI JSON for the objective assessment screen.

    - plan: validated against the two allowed dropdown values; blanked if invalid.
    - plan_details: stripped string.
    """
    plan = str(raw.get("plan", "") or "").strip()
    if plan not in OBJ_ASSESSMENT_PLAN_OPTIONS:
        if plan:
            logger.warning(f"Quick Mode obj assessment: invalid plan value '{plan}' — blanking")
        plan = ""

    return {
        "plan": plan,
        "plan_details": str(raw.get("plan_details", "") or "").strip(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PROVISIONAL DIAGNOSIS — STAGE 2 PRE-FILLS
# ─────────────────────────────────────────────────────────────────────────────

def generate_prov_diag_prefills(
    patient: Dict[str, Any],
    patho_data: Dict[str, Any],
    initial_plan_data: Dict[str, Any],
    obj_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate Stage 2 AI pre-fills for the Provisional Diagnosis screen.

    Returns a dict with:
        likelihood               (str) — short 1-2 sentence diagnosis + probability
        likelihood_reasoning     (str) — detailed clinical rationale
        structure_fault          (str) — short primary structure at fault
        structure_fault_reasoning (str)
        symptom                  (str) — short symptom pattern
        symptom_reasoning        (str)
        findings_support         (str) — short supporting findings
        findings_support_reasoning (str)
        findings_reject          (str) — short rejecting findings or "None identified"
        findings_reject_reasoning (str)
        hypothesis_supported     (str) — "Yes" or "No"

    Returns {} on any error so the template falls back to a blank form.
    """
    try:
        if not patient.get("present_history"):
            logger.warning("Quick Mode prov diag: no present_history available")
            return {}

        client = get_azure_openai_client()
        user_prompt = build_prov_diag_user_prompt(
            patient, patho_data or {}, initial_plan_data or {}, obj_data or {}
        )

        raw = client.generate_json_response(
            system_prompt=PROV_DIAG_SYSTEM,
            user_prompt=user_prompt,
        )

        if not raw or "error" in raw:
            logger.error(f"Quick Mode prov diag: AI returned error — {raw}")
            return {}

        prefills = _validate_prov_diag_prefills(raw)
        logger.info("Quick Mode provisional diagnosis prefills generated successfully (Stage 2)")
        return prefills

    except Exception as e:
        logger.error(f"Quick Mode prov diag prefill failed: {e}", exc_info=True)
        return {}


def _validate_prov_diag_prefills(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitise provisional diagnosis AI output.
    - All 5 field + _reasoning pairs: stripped strings.
    - hypothesis_supported: must be "Yes" or "No"; blanked otherwise.
    """
    result = {}
    for field in PROV_DIAG_FIELDS:
        result[field] = str(raw.get(field, "") or "").strip()
        result[f"{field}_reasoning"] = str(raw.get(f"{field}_reasoning", "") or "").strip()

    hypothesis = str(raw.get("hypothesis_supported", "") or "").strip()
    if hypothesis not in ("Yes", "No"):
        if hypothesis:
            logger.warning(f"Quick Mode prov diag: invalid hypothesis_supported '{hypothesis}' — blanking")
        hypothesis = ""
    result["hypothesis_supported"] = hypothesis

    return result


# ─────────────────────────────────────────────────────────────────────────────
# SMART GOALS — STAGE 2 PRE-FILLS
# ─────────────────────────────────────────────────────────────────────────────

def generate_smart_goals_prefills(
    patient: Dict[str, Any],
    patho_data: Dict[str, Any],
    prov_diag_data: Dict[str, Any],
    perspectives_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate Stage 2 AI pre-fills for the SMART Goals screen.

    Output is deliberately SHORT — 2-3 bullet points per field.
    The prompt explicitly enforces this constraint to avoid the verbose
    output that the normal AI suggestion produces.

    Returns dict with: patient_goal, baseline_status, measurable_outcome,
    time_duration — all short bullet-point strings, or "" on failure.

    Returns {} on any error so the template falls back to a blank form.
    """
    try:
        if not patient.get("present_history"):
            logger.warning("Quick Mode SMART goals: no present_history available")
            return {}

        client = get_azure_openai_client()
        user_prompt = build_smart_goals_user_prompt(
            patient,
            patho_data or {},
            prov_diag_data or {},
            perspectives_data or {},
        )

        raw = client.generate_json_response(
            system_prompt=SMART_GOALS_SYSTEM,
            user_prompt=user_prompt,
        )

        if not raw or "error" in raw:
            logger.error(f"Quick Mode SMART goals: AI returned error — {raw}")
            return {}

        prefills = _validate_smart_goals_prefills(raw)
        logger.info("Quick Mode SMART Goals prefills generated successfully (Stage 2)")
        return prefills

    except Exception as e:
        logger.error(f"Quick Mode SMART goals prefill failed: {e}", exc_info=True)
        return {}


def _validate_smart_goals_prefills(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitise SMART Goals AI output.
    All 4 fields are free-text strings — just strip and pass through.
    No dropdown validation needed.
    """
    result = {}
    for field in SMART_GOALS_FIELDS:
        result[field] = str(raw.get(field, "") or "").strip()
    return result


# ─────────────────────────────────────────────────────────────────────────────
# TREATMENT PLAN — STAGE 2 PRE-FILLS
# ─────────────────────────────────────────────────────────────────────────────

def generate_treatment_plan_prefills(
    patient: Dict[str, Any],
    patho_data: Dict[str, Any],
    prov_diag_data: Dict[str, Any],
    smart_goals_data: Dict[str, Any],
    obj_assessment_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate Stage 2 AI pre-fills for the Treatment Plan screen.

    Fills: treatment_plan, goal_targeted, reasoning — all 2-3 bullet points.
    Leaves 'reference' blank (AI must not fabricate citations).

    Returns {} on any error so the template falls back to a blank form.
    """
    try:
        if not patient.get("present_history"):
            logger.warning("Quick Mode Treatment Plan: no present_history available")
            return {}

        client = get_azure_openai_client()
        user_prompt = build_treatment_plan_user_prompt(
            patient,
            patho_data or {},
            prov_diag_data or {},
            smart_goals_data or {},
            obj_assessment_data or {},
        )

        raw = client.generate_json_response(
            system_prompt=TREATMENT_PLAN_SYSTEM,
            user_prompt=user_prompt,
        )

        if not raw or "error" in raw:
            logger.error(f"Quick Mode Treatment Plan: AI returned error — {raw}")
            return {}

        prefills = _validate_treatment_plan_prefills(raw)
        logger.info("Quick Mode Treatment Plan prefills generated successfully (Stage 2)")
        return prefills

    except Exception as e:
        logger.error(f"Quick Mode Treatment Plan prefill failed: {e}", exc_info=True)
        return {}


def _validate_treatment_plan_prefills(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitise Treatment Plan AI output.
    - treatment_plan, goal_targeted, reasoning: free-text bullet strings.
    - reference: always returned as "" regardless of what AI produces.
    """
    result = {}
    for field in TREATMENT_PLAN_FIELDS:
        if field == "reference":
            result[field] = ""  # never pre-fill — no fabricated citations
        else:
            result[field] = str(raw.get(field, "") or "").strip()
    return result
