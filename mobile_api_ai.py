"""
Mobile API - AI Suggestion Endpoints
======================================

AI-powered clinical decision support endpoints for the mobile app.
These endpoints provide suggestions for clinical documentation and assessment.

All endpoints use Firebase Bearer token authentication and PHI sanitization.
"""

import os
import logging
from flask import Blueprint, request, jsonify, g
from azure_cosmos_db import get_cosmos_db
from app_auth import require_firebase_auth, require_auth
import re

# Import centralized AI prompts
from ai_prompts import (
    get_past_questions_prompt,
    get_subjective_field_prompt,
    get_subjective_diagnosis_prompt,
    get_patient_perspectives_field_prompt,
    get_patient_perspectives_prompt,
    get_provisional_diagnosis_prompt,
    get_objective_assessment_prompt,
    get_objective_assessment_field_prompt,  # IMPROVED version
    get_pathophysiology_prompt,
    get_chronic_factors_prompt,
    get_clinical_flags_prompt,
    get_initial_plan_field_prompt,
    get_initial_plan_summary_prompt,
    get_smart_goals_prompt,
    get_smart_goals_field_prompt,  # IMPROVED version
    get_treatment_plan_field_prompt,
    get_treatment_plan_summary_prompt,
    get_provisional_diagnosis_field_prompt,
    get_followup_prompt,
    get_generic_field_prompt
)

logger = logging.getLogger("app.mobile_api_ai")

# Create Blueprint for AI endpoints
mobile_api_ai = Blueprint('mobile_api_ai', __name__, url_prefix='/api/ai_suggestion')

# Get Cosmos DB client
db = get_cosmos_db()

# Import AI functions and configuration from main module
# These will be imported when the blueprint is registered
get_ai_suggestion = None
get_ai_suggestion_with_cache = None
HIPAA_COMPLIANT_MODE = None
client = None
AzureOpenAIError = None
USE_AZURE_OPENAI = None

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS (PHI Sanitization & Data Normalization)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_patient_data(data):
    """
    Normalize patient data field names for backward compatibility.

    Handles field name inconsistency between patient storage and AI endpoints:
    - Storage uses: chief_complaint, medical_history
    - AI expects: present_history, past_history

    Args:
        data: Request data dictionary

    Returns:
        Normalized data dictionary with consistent field names
    """
    normalized = data.copy() if data else {}

    # Map chief_complaint -> present_history (if present_history not already set)
    if 'chief_complaint' in normalized and 'present_history' not in normalized:
        normalized['present_history'] = normalized['chief_complaint']

    # Map medical_history -> past_history (if past_history not already set)
    if 'medical_history' in normalized and 'past_history' not in normalized:
        normalized['past_history'] = normalized['medical_history']

    # Also handle 'previous' nested object (used in many endpoints)
    if 'previous' in normalized and isinstance(normalized['previous'], dict):
        prev = normalized['previous']
        if 'chief_complaint' in prev and 'present_history' not in prev:
            prev['present_history'] = prev['chief_complaint']
        if 'medical_history' in prev and 'past_history' not in prev:
            prev['past_history'] = prev['medical_history']

    return normalized


def sanitize_age_sex(age_sex_str):
    """Convert exact age to age range to protect PHI."""
    if not age_sex_str:
        return "Age/Sex not specified"

    # Extract age and sex (handle various formats: "35 M", "35/M", "35 / Male", etc.)
    match = re.search(r'(\d+)\s*/?\s*([MF]|male|female)', age_sex_str.strip(), re.IGNORECASE)
    if not match:
        return "Demographics: Adult"

    age = int(match.group(1))
    sex = match.group(2).upper()[0]  # M or F

    # Convert to age ranges
    if age < 18:
        age_range = "Under 18"
    elif age < 30:
        age_range = "20s"
    elif age < 40:
        age_range = "30s"
    elif age < 50:
        age_range = "40s"
    elif age < 60:
        age_range = "50s"
    elif age < 70:
        age_range = "60s"
    else:
        age_range = "70+"

    return f"{age_range} {sex}"


def sanitize_clinical_text(text):
    """Remove PHI from clinical text while preserving clinical information."""
    if not text:
        return ""

    sanitized = text

    # Remove specific dates
    sanitized = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '[date removed]', sanitized)
    sanitized = re.sub(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4}\b', '[date removed]', sanitized, flags=re.IGNORECASE)

    # Remove proper names
    medical_terms = {'MRI', 'CT', 'X', 'Xray', 'PT', 'OT', 'Dr', 'Hospital', 'Clinic', 'Emergency', 'Department',
                     'Pain', 'Back', 'Knee', 'Shoulder', 'Hip', 'Neck', 'Arm', 'Leg', 'Referred', 'Patient',
                     'Injury', 'Surgery', 'Contact', 'Office', 'Residence', 'Lives', 'Underwent', 'Scan', 'Shows',
                     'First', 'Call', 'Flat', 'House', 'Plot', 'Apartment'}
    words = sanitized.split()
    sanitized_words = []
    for word in words:
        clean_word = re.sub(r'[^\w]', '', word)
        # Check if word starts with capital AND is not in medical terms whitelist AND is longer than 2 chars
        if clean_word.istitle() and clean_word not in medical_terms and len(clean_word) > 2:
            sanitized_words.append('[name removed]')
        else:
            sanitized_words.append(word)
    sanitized = ' '.join(sanitized_words)

    # Remove email addresses
    sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[email removed]', sanitized)

    # Remove phone numbers (multiple formats including Indian)
    # First remove country codes to avoid leaving them behind
    sanitized = re.sub(r'\+\d{1,3}[-.\s]?', '', sanitized)  # Remove +91, +1, etc. with separators
    # US format: 123-456-7890, (123) 456-7890
    sanitized = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[phone removed]', sanitized)
    # Indian format: 9876543210, 98765 43210
    sanitized = re.sub(r'\b\d{10}\b', '[phone removed]', sanitized)
    sanitized = re.sub(r'\b\d{5}[-.\s]?\d{5}\b', '[phone removed]', sanitized)
    # Generic international: 234 567 8901
    sanitized = re.sub(r'\b\d{3}\s?\d{3}\s?\d{4}\b', '[phone removed]', sanitized)

    # Remove addresses (including Indian formats)
    sanitized = re.sub(r'\b\d+\s+\w+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Marg|Nagar|Colony|Block|Sector|Phase)\b', '[address removed]', sanitized, flags=re.IGNORECASE)
    # Flat/House numbers
    sanitized = re.sub(r'\b(Flat|House|Plot|Apartment|Apt|Room|Unit)\s*(No\.?|Number|#)?\s*\d+\b', '[address removed]', sanitized, flags=re.IGNORECASE)

    # Clean up multiple spaces
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()

    return sanitized


def sanitize_subjective_data(inputs_dict):
    """Sanitize subjective examination data to remove PHI."""
    if not inputs_dict:
        return {}

    sanitized = {}
    for key, value in inputs_dict.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_clinical_text(value)
        else:
            sanitized[key] = value

    return sanitized


def build_patient_context(raw: dict) -> dict:
    """
    Create a unified, sanitized, PHI-safe context object from ANY patient payload.
    This ensures ALL AI endpoints receive consistent clinical data.

    It supports both frontend formats:
    1. { age_sex: "...", present_history: "...", ... }
    2. { previous: { age_sex: "...", present_history: "...", ... }, inputs: {...} }
    """
    if not isinstance(raw, dict):
        raw = {}

    base = raw.get("previous")
    if isinstance(base, dict):
        data = normalize_patient_data(base)
    else:
        data = normalize_patient_data(raw)

    ctx = {
        "age_sex": sanitize_age_sex(data.get("age_sex", "")),
        "present_history": sanitize_clinical_text(data.get("present_history", "")),
        "past_history": sanitize_clinical_text(data.get("past_history", "")),
        "subjective": sanitize_subjective_data(data.get("subjective", {})),
        "perspectives": sanitize_subjective_data(data.get("perspectives", {})),
        "assessments": sanitize_subjective_data(data.get("assessments", {})),
        "smart_goals": sanitize_subjective_data(data.get("smart_goals", {})),
    }

    return ctx


def get_ai_suggestion_safe(prompt, metadata=None, patient_context="", user_id=None):
    """
    Safe wrapper for get_ai_suggestion that handles imports and errors.
    Now uses Claude Sonnet 4.5 on Vertex AI (transparent to mobile app).

    Args:
        prompt: The AI prompt text
        metadata: Optional metadata for analytics
        patient_context: Patient-specific context (age/sex) to ensure unique cache per patient
        user_id: User ID for GDPR "Right to be Forgotten" compliance
    """
    global get_ai_suggestion, get_ai_suggestion_with_cache, HIPAA_COMPLIANT_MODE, client, AzureOpenAIError, USE_AZURE_OPENAI

    # Import from main module if not already imported
    if get_ai_suggestion is None:
        try:
            import main
            get_ai_suggestion = main.get_ai_suggestion
            get_ai_suggestion_with_cache = main.get_ai_suggestion_with_cache
            HIPAA_COMPLIANT_MODE = main.HIPAA_COMPLIANT_MODE
            client = main.client
            USE_AZURE_OPENAI = getattr(main, 'USE_AZURE_OPENAI', True)  # Azure OpenAI GPT-4o

            # Import Azure OpenAI error class
            try:
                from azure_openai_client import AzureOpenAIError as AzureError
                AzureOpenAIError = AzureError
            except:
                AzureOpenAIError = Exception

            logger.info(f"Mobile API using Azure OpenAI GPT-4o")

        except Exception as e:
            logger.error(f"Failed to import AI functions from main: {e}")
            return "AI service temporarily unavailable."

    # HIPAA mode is ENABLED with Azure OpenAI (BAA covered)
    if client is None:
        return "AI service temporarily unavailable."

    try:
        # Using Azure OpenAI GPT-4o
        model = "gpt-4o"

        # Use the caching system (works with both OpenAI and Vertex AI)
        from ai_cache import get_ai_suggestion_with_cache
        response = get_ai_suggestion_with_cache(
            db=db,
            prompt=prompt,
            model=model,
            openai_client=client,
            metadata=metadata or {},
            patient_context=patient_context,  # Pass patient context for cache uniqueness
            user_id=user_id  # For GDPR "Right to be Forgotten" compliance
        )
        return response

    except AzureOpenAIError as e:
        logger.error(f"Azure OpenAI API error: {e}")
        return "AI service temporarily unavailable. Please try again."
    except Exception as e:
        logger.error(f"AI suggestion error: {e}")
        return "Error generating suggestion. Please try again."


# ─────────────────────────────────────────────────────────────────────────────
# AI SUGGESTION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api_ai.route('/past_questions', methods=['POST'])
@require_auth
def api_ai_past_questions():
    """AI suggestions for past history questions"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)
        data = normalize_patient_data(request.get_json() or {})
        age_sex = sanitize_age_sex(data.get('age_sex', ''))
        present_hist = sanitize_clinical_text(data.get('present_history', '').strip())

        # Use centralized prompt
        prompt = get_past_questions_prompt(age_sex, present_hist)

        user_id = g.user.get('uid', g.user.get('email'))
        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': 'past_questions',
            'tags': ['past_history', 'questions'],
            'user_id': user_id
        }, patient_context=age_sex, user_id=user_id)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI past questions error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/provisional_diagnosis', methods=['POST'])
@require_auth
def api_ai_provisional_diagnosis():
    """AI provisional diagnosis based on all available data"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)
        data = normalize_patient_data(request.get_json() or {})
        previous = data.get('previous', {})

        # Extract and sanitize patient context
        age_sex = sanitize_age_sex(previous.get('age_sex', ''))
        present = sanitize_clinical_text(previous.get('present_history', ''))
        past = sanitize_clinical_text(previous.get('past_history', ''))
        subjective = sanitize_subjective_data(previous.get('subjective', {}))
        perspectives = sanitize_subjective_data(previous.get('perspectives', {}))
        assessments = sanitize_subjective_data(previous.get('assessments', {}))

        # Use centralized prompt
        prompt = get_provisional_diagnosis_prompt(
            age_sex=age_sex,
            present_hist=present,
            past_hist=past,
            subjective_inputs=subjective,
            patient_perspectives=perspectives,
            assessments=assessments
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': 'provisional_diagnosis',
            'tags': ['diagnosis', 'provisional'],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion, 'diagnosis': suggestion}), 200

    except Exception as e:
        logger.error(f"AI provisional diagnosis error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/subjective/<field>', methods=['POST'])
@require_auth
def api_ai_subjective_field(field):
    """AI suggestions for subjective examination fields"""
    try:
        raw = request.get_json() or {}

        # Build unified PHI-safe clinical context (supports both flat and nested payloads)
        ctx = build_patient_context(raw)

        age_sex = ctx["age_sex"]
        present_hist = ctx["present_history"]
        past_hist = ctx["past_history"]

        # Inputs = current subjective field content
        existing_inputs = sanitize_subjective_data(raw.get("inputs", {}))

        # Use centralized prompt
        prompt = get_subjective_field_prompt(
            field=field,
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            existing_inputs=existing_inputs
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': f'subjective_{field}',
            'tags': ['subjective', 'examination', field],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI subjective field error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/subjective_diagnosis', methods=['POST'])
@require_auth
def api_ai_subjective_diagnosis():
    """AI diagnostic suggestions based on subjective examination"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)
        data = normalize_patient_data(request.get_json() or {})
        age_sex = sanitize_age_sex(data.get('age_sex', ''))
        present_hist = sanitize_clinical_text(data.get('present_history', '').strip())
        past_hist = sanitize_clinical_text(data.get('past_history', '').strip())
        subjective_inputs = sanitize_subjective_data(data.get('inputs', {}))

        # Use centralized prompt
        prompt = get_subjective_diagnosis_prompt(
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            subjective_inputs=subjective_inputs
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': 'subjective_diagnosis',
            'tags': ['subjective', 'diagnosis'],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI subjective diagnosis error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/perspectives/<field>', methods=['POST'])
@require_auth
def api_ai_perspectives_field(field):
    """AI suggestions for patient perspectives fields (CSM components)"""
    try:
        raw = request.get_json() or {}

        # Build unified PHI-safe clinical context (supports both flat and nested payloads)
        ctx = build_patient_context(raw)

        age_sex = ctx["age_sex"]
        present_hist = ctx["present_history"]
        past_hist = ctx["past_history"]

        # Get subjective findings from previous context
        previous = raw.get('previous', {})
        subjective = sanitize_subjective_data(previous.get('subjective', {}))

        # Inputs = current perspectives field content
        existing_perspectives = sanitize_subjective_data(raw.get("inputs", {}))

        # Use centralized FIELD-SPECIFIC prompt
        prompt = get_patient_perspectives_field_prompt(
            field=field,
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            subjective_inputs=subjective,
            existing_perspectives=existing_perspectives
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': f'perspectives_{field}',
            'tags': ['perspectives', 'patient-centered', 'csm', field],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI perspectives field error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/patient_perspectives', methods=['POST'])
@require_auth
def api_ai_patient_perspectives():
    """AI suggestions for patient perspectives (LEGACY - prefer /perspectives/<field>)"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)
        data = normalize_patient_data(request.get_json() or {})
        previous = data.get('previous', {})
        inputs = data.get('inputs', {})

        age_sex = sanitize_age_sex(previous.get('age_sex', ''))
        present = sanitize_clinical_text(previous.get('present_history', ''))
        past = sanitize_clinical_text(previous.get('past_history', ''))
        subjective = sanitize_subjective_data(previous.get('subjective', {}))

        # Use centralized prompt
        prompt = get_patient_perspectives_prompt(
            age_sex=age_sex,
            present_hist=present,
            past_hist=past,
            subjective_inputs=subjective
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': 'patient_perspectives',
            'tags': ['perspectives', 'patient-centered'],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI patient perspectives error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/initial_plan/<field>', methods=['POST'])
@require_auth
def api_ai_initial_plan_field(field):
    """AI suggestions for initial ASSESSMENT plan fields (IMPROVED - focuses on physical examination tests, not treatment)"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)
        raw = request.get_json() or {}
        data = normalize_patient_data(raw)
        previous = data.get('previous', {})
        selection = raw.get('selection', '')  # "Mandatory assessment", "Assessment with precaution", or "Absolutely Contraindicated"

        # Extract and sanitize patient context
        age_sex = sanitize_age_sex(previous.get('age_sex', ''))
        present_hist = sanitize_clinical_text(previous.get('present_history', ''))
        past_hist = sanitize_clinical_text(previous.get('past_history', ''))
        subjective = sanitize_subjective_data(previous.get('subjective', {}))
        diagnosis = sanitize_clinical_text(previous.get('provisional_diagnosis', ''))

        # Use centralized prompt (IMPROVED - now focuses on ASSESSMENT planning, not treatment)
        prompt = get_initial_plan_field_prompt(
            field=field,
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            subjective=subjective,
            diagnosis=diagnosis,
            selection=selection
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': f'initial_plan_{field}',
            'tags': ['initial_plan', 'assessment', field],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI initial plan error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/initial_plan_summary', methods=['POST'])
@require_auth
def api_ai_initial_plan_summary():
    """AI summary of initial treatment plan"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)

        data = normalize_patient_data(request.get_json() or {})
        previous = data.get('previous', {})
        inputs = data.get('inputs', {})

        # Extract and sanitize patient context
        age_sex = sanitize_age_sex(previous.get('age_sex', ''))
        present_hist = sanitize_clinical_text(previous.get('present_history', ''))
        past_hist = sanitize_clinical_text(previous.get('past_history', ''))
        subjective = sanitize_subjective_data(previous.get('subjective', {}))
        diagnosis = sanitize_clinical_text(previous.get('provisional_diagnosis', ''))
        plan_fields = sanitize_subjective_data(inputs)

        # Use centralized prompt
        prompt = get_initial_plan_summary_prompt(
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            subjective=subjective,
            diagnosis=diagnosis,
            plan_fields=plan_fields
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': 'initial_plan_summary',
            'tags': ['initial_plan', 'summary'],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI initial plan summary error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/patho_possible_source', methods=['POST'])
@require_auth
def api_ai_patho_source():
    """AI suggestions for PAIN SOURCE CLASSIFICATION (IMPROVED - now provides specific pain mechanism analysis)"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)
        raw = request.get_json() or {}
        data = normalize_patient_data(raw)
        previous = data.get('previous', {})

        # Extract pathophysiology data from the current form
        patho_inputs = raw.get('patho_data', {})

        # Extract and sanitize patient context
        age_sex = sanitize_age_sex(previous.get('age_sex', ''))
        present_hist = sanitize_clinical_text(previous.get('present_history', ''))
        past_hist = sanitize_clinical_text(previous.get('past_history', ''))
        subjective = sanitize_subjective_data(previous.get('subjective', {}))
        diagnosis = sanitize_clinical_text(previous.get('provisional_diagnosis', ''))

        # Sanitize pathophysiology data
        patho_data = {
            'area_involved': sanitize_clinical_text(patho_inputs.get('area_involved', '')),
            'presenting_symptom': sanitize_clinical_text(patho_inputs.get('presenting_symptom', '')),
            'pain_type': patho_inputs.get('pain_type', ''),
            'pain_nature': patho_inputs.get('pain_nature', ''),
            'pain_severity': patho_inputs.get('pain_severity', ''),
            'pain_irritability': patho_inputs.get('pain_irritability', ''),
            'stage_healing': patho_inputs.get('stage_healing', ''),
        }

        # Use centralized prompt (IMPROVED - now focuses on pain source classification)
        prompt = get_pathophysiology_prompt(
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            subjective=subjective,
            diagnosis=diagnosis,
            patho_data=patho_data
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': 'patho_possible_source',
            'tags': ['pathophysiology', 'pain_mechanism', 'classification'],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI patho source error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/chronic_factors_suggest', methods=['POST'])
@require_auth
def api_ai_chronic_factors():
    """AI suggestions for MAINTENANCE FACTORS using biopsychosocial framework (IMPROVED)"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)
        raw = request.get_json() or {}
        data = normalize_patient_data(raw)
        previous = data.get('previous', {})

        # Extract chronic factors form data
        chronic_inputs = raw.get('chronic_data', {})
        selected_categories = chronic_inputs.get('selected_categories', [])
        existing_factors = sanitize_clinical_text(chronic_inputs.get('specific_factors', ''))

        # Extract and sanitize patient context
        age_sex = sanitize_age_sex(previous.get('age_sex', ''))
        present_hist = sanitize_clinical_text(previous.get('present_history', ''))
        past_hist = sanitize_clinical_text(previous.get('past_history', ''))
        subjective = sanitize_subjective_data(previous.get('subjective', {}))
        diagnosis = sanitize_clinical_text(previous.get('provisional_diagnosis', ''))
        perspectives = sanitize_subjective_data(previous.get('perspectives', {}))

        # Get pathophysiology data for pain characteristics
        patho_data = previous.get('patho_data', {})

        # Use centralized prompt (IMPROVED - now uses biopsychosocial framework and pain science)
        prompt = get_chronic_factors_prompt(
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            subjective=subjective,
            diagnosis=diagnosis,
            perspectives=perspectives,
            patho_data=patho_data,
            selected_categories=selected_categories,
            existing_factors=existing_factors
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': 'chronic_factors',
            'tags': ['chronic', 'maintenance', 'biopsychosocial'],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI chronic factors error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/clinical_flags_suggest', methods=['POST'])
@require_auth
def api_ai_clinical_flags():
    """AI suggestions for comprehensive clinical flags screening - ALL 5 flag types (IMPROVED)"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)
        raw = request.get_json() or {}
        data = normalize_patient_data(raw)
        previous = data.get('previous', {})

        # Extract and sanitize patient context
        age_sex = sanitize_age_sex(previous.get('age_sex', ''))
        present_hist = sanitize_clinical_text(previous.get('present_history', ''))
        past_hist = sanitize_clinical_text(previous.get('past_history', ''))
        subjective = sanitize_subjective_data(previous.get('subjective', {}))
        perspectives = sanitize_subjective_data(previous.get('perspectives', {}))

        # Get pathophysiology data for red flag screening
        patho_data = previous.get('patho_data', {})

        # Get chronic factors for psychosocial context
        chronic_factors = previous.get('chronic_factors', {})

        # Use centralized prompt (IMPROVED - now covers ALL 5 flag types: Red, Orange, Yellow, Black, Blue)
        prompt = get_clinical_flags_prompt(
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            subjective=subjective,
            perspectives=perspectives,
            patho_data=patho_data,
            chronic_factors=chronic_factors
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': 'clinical_flags',
            'tags': ['flags', 'screening', 'safety', 'red_flags', 'yellow_flags'],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI clinical flags error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/objective_assessment', methods=['POST'])
@require_auth
def api_ai_objective_assessment():
    """IMPROVED: AI suggestions for objective assessment with body region-specific test recommendations"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)

        data = normalize_patient_data(request.get_json() or {})
        previous = data.get('previous', {})
        field = data.get('field', 'plan')  # Default to 'plan' field if not specified

        # Extract and sanitize patient context
        age_sex = sanitize_age_sex(previous.get('age_sex', ''))
        present = sanitize_clinical_text(previous.get('present_history', ''))
        past = sanitize_clinical_text(previous.get('past_history', ''))
        subjective = sanitize_subjective_data(previous.get('subjective', {}))
        perspectives = sanitize_subjective_data(previous.get('perspectives', {}))
        provisional_diagnoses = sanitize_clinical_text(previous.get('provisional_diagnosis', ''))
        clinical_flags = sanitize_subjective_data(previous.get('clinical_flags', {}))

        # Use IMPROVED centralized prompt with body region-specific guidance
        prompt = get_objective_assessment_field_prompt(
            field=field,
            age_sex=age_sex,
            present_hist=present,
            past_hist=past,
            subjective=subjective,
            perspectives=perspectives,
            provisional_diagnoses=provisional_diagnoses,
            clinical_flags=clinical_flags
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': 'objective_assessment',
            'tags': ['objective', 'assessment'],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI objective assessment error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/provisional_diagnosis/<field>', methods=['POST'])
@require_auth
def api_ai_provisional_diagnosis_field(field):
    """IMPROVED: AI suggestions for specific provisional diagnosis fields with body region-specific differential diagnoses"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)

        data = normalize_patient_data(request.get_json() or {})
        previous = data.get('previous', {})

        # Extract and sanitize patient context
        age_sex = sanitize_age_sex(previous.get('age_sex', ''))
        present_hist = sanitize_clinical_text(previous.get('present_history', ''))
        past_hist = sanitize_clinical_text(previous.get('past_history', ''))
        subjective = sanitize_subjective_data(previous.get('subjective', {}))
        perspectives = sanitize_subjective_data(previous.get('perspectives', {}))
        assessments = sanitize_subjective_data(previous.get('assessments', {}))
        objective_findings = sanitize_subjective_data(previous.get('objective', {}))
        clinical_flags = sanitize_subjective_data(previous.get('clinical_flags', {}))

        # Use IMPROVED centralized prompt with body region-specific guidance
        prompt = get_provisional_diagnosis_field_prompt(
            field=field,
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            subjective=subjective,
            perspectives=perspectives,
            assessments=assessments,
            objective_findings=objective_findings,
            clinical_flags=clinical_flags
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': f'provisional_diagnosis_{field}',
            'tags': ['diagnosis', field],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI provisional diagnosis error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/smart_goals', methods=['POST'])
@require_auth
def api_ai_smart_goals():
    """AI suggestions for SMART goals (LEGACY - general goals)"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)

        data = normalize_patient_data(request.get_json() or {})
        previous = data.get('previous', {})
        patient_goals = data.get('patient_goals', '')

        # Extract and sanitize patient context
        age_sex = sanitize_age_sex(previous.get('age_sex', ''))
        present_hist = sanitize_clinical_text(previous.get('present_history', ''))
        past_hist = sanitize_clinical_text(previous.get('past_history', ''))
        subjective = sanitize_subjective_data(previous.get('subjective', {}))
        perspectives = sanitize_subjective_data(previous.get('perspectives', {}))
        diagnosis = sanitize_clinical_text(previous.get('provisional_diagnosis', ''))

        # Use centralized prompt
        prompt = get_smart_goals_prompt(
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            subjective=subjective,
            perspectives=perspectives,
            diagnosis=diagnosis
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': 'smart_goals',
            'tags': ['goals', 'treatment_planning'],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI SMART goals error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/smart_goals/<field>', methods=['POST'])
@require_auth
def api_ai_smart_goals_field(field):
    """IMPROVED: AI suggestions for SMART goals fields with body region-specific ICF participation guidance"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)

        data = normalize_patient_data(request.get_json() or {})
        previous = data.get('previous', {})

        # Extract and sanitize patient context
        age_sex = sanitize_age_sex(previous.get('age_sex', ''))
        present_hist = sanitize_clinical_text(previous.get('present_history', ''))
        past_hist = sanitize_clinical_text(previous.get('past_history', ''))
        subjective = sanitize_subjective_data(previous.get('subjective', {}))
        perspectives = sanitize_subjective_data(previous.get('perspectives', {}))
        diagnosis = sanitize_clinical_text(previous.get('provisional_diagnosis', ''))
        clinical_flags = sanitize_subjective_data(previous.get('clinical_flags', {}))

        # Use IMPROVED centralized prompt with body region-specific guidance
        prompt = get_smart_goals_field_prompt(
            field=field,
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            subjective=subjective,
            perspectives=perspectives,
            diagnosis=diagnosis,
            clinical_flags=clinical_flags
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': f'smart_goals_{field}',
            'tags': ['goals', 'treatment_planning', field],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI SMART goals field error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/treatment_plan/<field>', methods=['POST'])
@require_auth
def api_ai_treatment_plan_field(field):
    """IMPROVED: AI suggestions for treatment plan fields with body region-specific interventions"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)

        data = normalize_patient_data(request.get_json() or {})
        patient_id = data.get('patient_id', '')
        previous = data.get('previous', {})

        # Extract and sanitize patient context
        age_sex = sanitize_age_sex(previous.get('age_sex', ''))
        present_hist = sanitize_clinical_text(previous.get('present_history', ''))
        past_hist = sanitize_clinical_text(previous.get('past_history', ''))
        diagnosis = sanitize_clinical_text(previous.get('provisional_diagnosis', ''))
        subjective = sanitize_subjective_data(previous.get('subjective', {}))
        perspectives = sanitize_subjective_data(previous.get('perspectives', {}))
        goals = sanitize_subjective_data(previous.get('smart_goals', {}))
        clinical_flags = sanitize_subjective_data(previous.get('clinical_flags', {}))

        # Use IMPROVED centralized prompt with body region-specific guidance
        prompt = get_treatment_plan_field_prompt(
            field=field,
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            subjective=subjective,
            perspectives=perspectives,
            diagnosis=diagnosis,
            goals=goals,
            clinical_flags=clinical_flags
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': f'treatment_plan_{field}',
            'tags': ['treatment', field],
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI treatment plan error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/treatment_plan_summary/<patient_id>', methods=['GET'])
@require_auth
def api_ai_treatment_plan_summary(patient_id):
    """Get AI summary of treatment plan for a patient"""
    try:
        # Get patient data
        patient_doc = db.collection('patients').document(patient_id).get()
        if not patient_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404

        patient_data = patient_doc.to_dict()
        user_email = g.user.get('email') or g.user.get('uid')

        # Check access
        if patient_data.get('physio_id') != user_email and g.user.get('is_admin', 0) != 1:
            return jsonify({'error': 'Unauthorized'}), 403

        # Extract and sanitize patient context
        age_sex = sanitize_age_sex(patient_data.get('age_sex', ''))
        present_hist = sanitize_clinical_text(patient_data.get('present_complaint', '') or patient_data.get('present_history', ''))
        past_hist = sanitize_clinical_text(patient_data.get('past_history', ''))
        subjective = sanitize_subjective_data(patient_data.get('subjective', {}))
        diagnosis = sanitize_clinical_text(patient_data.get('provisional_diagnosis', ''))
        goals = sanitize_subjective_data(patient_data.get('smart_goals', {}))
        treatment_fields = sanitize_subjective_data(patient_data.get('treatment_plan', {}))

        # Use centralized prompt
        prompt = get_treatment_plan_summary_prompt(
            patient_id=patient_id,
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            subjective=subjective,
            diagnosis=diagnosis,
            goals=goals,
            treatment_fields=treatment_fields
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': 'treatment_plan_summary',
            'tags': ['treatment', 'summary'],
            'patient_id': patient_id,
            'user_id': user_email
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI treatment summary error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/followup', methods=['POST'])
@require_auth
def api_ai_followup():
    """AI suggestions for follow-up visit (LEGACY - prefer /followup/<field>)"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)

        data = normalize_patient_data(request.get_json() or {})
        patient_id = data.get('patient_id', '')
        session_number = data.get('session_number', '')
        session_date = data.get('session_date', '')
        grade = data.get('grade', '')
        perception = data.get('perception', '')
        feedback = sanitize_clinical_text(data.get('feedback', ''))

        # Get patient data for the prompt
        age_sex = ""
        present_hist = ""
        past_hist = ""
        diagnosis = ""
        if patient_id:
            try:
                patient_doc = db.collection('patients').document(patient_id).get()
                if patient_doc.exists:
                    patient_data = patient_doc.to_dict()
                    age_sex = sanitize_age_sex(patient_data.get('age_sex', ''))
                    present_hist = sanitize_clinical_text(patient_data.get('present_complaint', '') or patient_data.get('present_history', ''))
                    past_hist = sanitize_clinical_text(patient_data.get('past_history', ''))
                    diagnosis = sanitize_clinical_text(patient_data.get('provisional_diagnosis', ''))
            except:
                pass  # If we can't get patient data, continue without it

        # Construct followup data from session inputs
        followup_data = {
            'session_number': session_number,
            'session_date': session_date,
            'grade': grade,
            'perception': perception,
            'feedback': feedback
        }

        # Use centralized prompt
        prompt = get_followup_prompt(
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            diagnosis=diagnosis,
            treatment_summary=None,
            followup_data=followup_data
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': 'followup',
            'tags': ['followup', 'reassessment'],
            'patient_id': patient_id,
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI followup error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/followup/<field>', methods=['POST'])
@require_auth
def api_ai_followup_field(field):
    """
    IMPROVED: AI suggestions for follow-up field with body region-specific progression strategies.
    Uses get_followup_field_prompt for clinical decision-making based on achievement grade.
    """
    try:
        data = normalize_patient_data(request.get_json() or {})
        patient_id = data.get('patient_id', '')

        if not patient_id:
            return jsonify({'error': 'patient_id is required'}), 400

        # Parse current form data
        grade = data.get('grade', '')
        perception = data.get('perception', '')
        feedback = sanitize_clinical_text(data.get('feedback', ''))
        session_number = data.get('session_number')

        # Get patient data
        age_sex = ""
        present_hist = ""
        past_hist = ""
        diagnosis = ""
        treatment_summary = ""
        goals = None

        try:
            # Get patient record
            patient_doc = db.collection('patients').document(patient_id).get()
            if patient_doc.exists:
                patient_data = patient_doc.to_dict()
                age_sex = sanitize_age_sex(patient_data.get('age_sex', ''))
                present_hist = sanitize_clinical_text(patient_data.get('present_complaint', '') or patient_data.get('present_history', ''))
                past_hist = sanitize_clinical_text(patient_data.get('past_history', ''))

            # Fetch related data from Cosmos DB
            def fetch_latest(collection_name):
                coll = db.collection(collection_name) \
                        .where('patient_id', '==', patient_id) \
                        .order_by('timestamp', direction='DESCENDING') \
                        .limit(1) \
                        .get()
                return coll[0].to_dict() if coll else {}

            # Get diagnosis
            prov_dx_data = fetch_latest('provisional_diagnosis')
            diagnosis = sanitize_clinical_text(prov_dx_data.get('diagnosis', ''))

            # Get treatment plan summary
            treatment_data = fetch_latest('treatment_plans')
            treatment_summary = sanitize_clinical_text(treatment_data.get('treatment_plan', ''))

            # Get SMART goals
            goals_data = fetch_latest('smart_goals')
            goals = sanitize_subjective_data(goals_data) if goals_data else None

        except Exception as e:
            logger.warning(f"Error fetching patient data for followup field: {e}")
            # Continue with available data

        # Use IMPROVED centralized prompt from ai_prompts.py
        from ai_prompts import get_followup_field_prompt
        prompt = get_followup_field_prompt(
            field=field,
            age_sex=age_sex,
            present_hist=present_hist,
            past_hist=past_hist,
            diagnosis=diagnosis,
            treatment_summary=treatment_summary,
            goals=goals,
            grade=grade,
            perception=perception,
            feedback=feedback,
            session_number=session_number
        )

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': f'followup_{field}',
            'tags': ['followup', 'field-specific', field],
            'patient_id': patient_id,
            'user_id': g.user.get('uid', g.user.get('email'))
        }, patient_context=age_sex)

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI followup field error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


@mobile_api_ai.route('/field/<field>', methods=['POST'])
@require_auth
def api_ai_generic_field(field):
    """Generic AI suggestions for any field"""
    try:
        # Normalize field names (chief_complaint -> present_history, medical_history -> past_history)

        data = normalize_patient_data(request.get_json() or {})
        context = sanitize_clinical_text(data.get('context', ''))

        # Use centralized prompt
        prompt = get_generic_field_prompt(field, context)

        suggestion = get_ai_suggestion_safe(prompt, metadata={
            'endpoint': f'field_{field}',
            'tags': ['generic', field],
            'user_id': g.user.get('uid', g.user.get('email'))
        })

        return jsonify({'suggestion': suggestion}), 200

    except Exception as e:
        logger.error(f"AI generic field error: {e}")
        return jsonify({'error': 'AI suggestion failed'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# AUDIO TRANSCRIPTION (if using OpenAI Whisper)
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api_ai.route('/transcribe', methods=['POST'], endpoint='api_transcribe')
@require_auth
def api_transcribe_audio():
    """Transcribe audio file to text using OpenAI Whisper"""
    try:
        # Check if file was uploaded
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400

        audio_file = request.files['audio']

        # Check HIPAA mode
        if HIPAA_COMPLIANT_MODE or client is None:
            return jsonify({'error': 'Transcription disabled in HIPAA mode'}), 403

        # Transcribe using OpenAI Whisper
        try:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            return jsonify({'text': transcript.text}), 200

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return jsonify({'error': 'Transcription failed'}), 500

    except Exception as e:
        logger.error(f"Audio transcription error: {e}")
        return jsonify({'error': 'Transcription request failed'}), 500
