# Quick Mode AI Pre-fills - Implementation Plan

**Version:** 1.0
**Date:** 2026-04-28
**Objective:** Add AI-powered documentation pre-fills as an OPTIONAL feature WITHOUT breaking existing app flow

---

## 🎯 Executive Summary

### What is Quick Mode?
Quick Mode uses AI to automatically pre-fill clinical documentation across multiple assessment screens based solely on patient history. This saves time for practicing physiotherapists while maintaining clinical accuracy through manual review.

### Key Principles
1. **100% Optional** - Existing workflow remains untouched
2. **Non-Breaking** - Feature toggle at patient level
3. **Pre-fills Only** - All data requires explicit Save by physiotherapist
4. **No Auto-Save** - Pre-fills populate form fields but don't commit to database
5. **Transparent** - Visual indicators show AI-generated vs manual content

---

## 📊 Current vs. New Flow

### Current Flow (Unchanged)
```
Add Patient
  ↓
Patho Mechanism (manual entry)
  ↓
Subjective Assessment (manual entry with per-field AI suggestions)
  ↓
Patient Perspectives (manual interview)
  ↓
Chronic Disease (manual entry)
  ↓
Clinical Flags (manual entry)
  ↓
Initial Plan (manual entry)
  ↓
Objective Assessment (manual entry)
  ↓
Provisional Diagnosis (manual entry)
  ↓
SMART Goals (manual entry)
  ↓
Treatment Plan (manual entry)
```

### New Optional Flow (Quick Mode Enabled)
```
Add Patient [✓ Quick Mode checkbox]
  ↓
Save → AI generates Stage 1 pre-fills in background
  ↓
Patho Mechanism (AI PRE-FILLED → physio reviews/edits → Save)
  ↓
Subjective Assessment (AI PRE-FILLED → review/edit → Save)
  ↓
Patient Perspectives (SKIPPED - requires direct interview)
  ↓
Chronic Disease (AI PRE-FILLED → review/edit → Save)
  ↓
Clinical Flags (AI PRE-FILLED → review/edit → Save)
  ↓
Initial Plan - Tests Recommended (AI PRE-FILLED → review/edit → Save)
  ↓
Initial Plan - Findings (MANUAL ENTRY by physio after examination)
  ↓
  → AI generates Stage 2 pre-fills
  ↓
Objective Assessment (AI PRE-FILLED → review/edit → Save)
  ↓
Provisional Diagnosis (AI PRE-FILLED → review/edit → Save)
  ↓
SMART Goals (AI PRE-FILLED → review/edit → Save)
  ↓
Treatment Plan (AI PRE-FILLED → review/edit → Save)
```

---

## 🗄️ Database Changes

### New Cosmos DB Collections

#### 1. `ai_prefills` Collection
Stores temporary AI-generated pre-fills (cache).

```python
{
  "id": "{patient_id}_stage1",  # or {patient_id}_stage2
  "patient_id": "user123-001",
  "stage": 1,  # 1 or 2
  "generated_at": "2026-04-28T10:00:00Z",
  "generated_by": "user@example.com",  # physio who enabled Quick Mode
  "invalidated": false,
  "data": {
    # Full JSON output from AI (see prompt structure)
    "patho_mechanism": { ... },
    "subjective": { ... },
    "chronic_disease": { ... },
    # etc.
  },
  "ai_model": "gpt-4-turbo",  # Track which model was used
  "token_usage": 2000,  # For cost tracking
  "ttl": 2592000  # Auto-delete after 30 days (Cosmos TTL)
}
```

#### 2. Update `patients` Collection
Add Quick Mode flag to patient documents:

```python
{
  # ... existing fields ...
  "quick_mode_enabled": true,  # NEW FIELD
  "quick_mode_stage1_completed": true,  # NEW: Track generation status
  "quick_mode_stage2_completed": false  # NEW
}
```

#### 3. Update `audit_logs` Collection
Track Quick Mode usage:

```python
{
  "user_id": "physio@example.com",
  "action": "Quick Mode AI Pre-fill Generated",
  "details": "Stage 1 pre-fills for patient user123-001",
  "timestamp": SERVER_TIMESTAMP,
  "token_cost": 2000,  # For usage monitoring
  "ai_model": "gpt-4-turbo"
}
```

---

## 🔧 Backend Changes

### 1. New File: `quick_mode_service.py`
Handles all Quick Mode logic (isolated from main.py).

```python
"""
Quick Mode Service - AI Pre-fill Generation
Handles two-stage pre-fill generation for Quick Mode
"""

import logging
from typing import Dict, Optional, Tuple
from azure_openai_client import get_ai_suggestion
from azure_cosmos_db import get_cosmos_db, SERVER_TIMESTAMP
from data_sanitization import sanitize_clinical_text
import json

logger = logging.getLogger("app.quick_mode")

def generate_stage1_prefills(
    patient_id: str,
    age_sex: str,
    present_history: str,
    past_history: str,
    physio_email: str
) -> Tuple[bool, Optional[Dict]]:
    """
    Generate Stage 1 pre-fills from patient history alone.

    Returns: (success: bool, data: dict or error_message: str)
    """
    try:
        # Import prompt from your Quick Mode prompts file
        from quick_mode_prompts import get_stage1_prefill_prompt

        # Sanitize inputs
        age_sex = sanitize_clinical_text(age_sex)
        present_history = sanitize_clinical_text(present_history)
        past_history = sanitize_clinical_text(past_history) if past_history else ""

        # Generate prompt
        prompt = get_stage1_prefill_prompt(age_sex, present_history, past_history)

        # Call AI (with retry logic)
        ai_response = get_ai_suggestion(prompt)

        # Parse JSON response
        prefill_data = json.loads(ai_response)

        # Store in cache
        db = get_cosmos_db()
        cache_doc = {
            "id": f"{patient_id}_stage1",
            "patient_id": patient_id,
            "stage": 1,
            "generated_at": SERVER_TIMESTAMP,
            "generated_by": physio_email,
            "invalidated": False,
            "data": prefill_data,
            "ai_model": "gpt-4-turbo",
            "ttl": 2592000  # 30 days
        }

        db.collection('ai_prefills').document(f"{patient_id}_stage1").set(cache_doc)

        # Update patient document
        db.collection('patients').document(patient_id).update({
            'quick_mode_stage1_completed': True
        })

        logger.info(f"Stage 1 pre-fills generated for patient {patient_id}")
        return True, prefill_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI JSON response: {e}")
        return False, "AI returned invalid JSON"
    except Exception as e:
        logger.error(f"Stage 1 prefill generation failed: {e}", exc_info=True)
        return False, str(e)


def get_cached_prefills(patient_id: str, stage: int) -> Optional[Dict]:
    """
    Retrieve cached pre-fills for a patient.

    Returns: dict of pre-fills or None if not found/invalidated
    """
    try:
        db = get_cosmos_db()
        cache_doc = db.collection('ai_prefills').document(f"{patient_id}_stage{stage}").get()

        if not cache_doc.exists:
            return None

        cache_data = cache_doc.to_dict()

        # Check if invalidated
        if cache_data.get('invalidated'):
            logger.info(f"Cached prefills for {patient_id} stage {stage} are invalidated")
            return None

        return cache_data.get('data')

    except Exception as e:
        logger.error(f"Error fetching cached prefills: {e}")
        return None


def invalidate_prefills(patient_id: str):
    """
    Invalidate cached pre-fills when patient history is edited.
    """
    try:
        db = get_cosmos_db()

        # Invalidate both stages
        for stage in [1, 2]:
            doc_id = f"{patient_id}_stage{stage}"
            cache_ref = db.collection('ai_prefills').document(doc_id)
            cache_doc = cache_ref.get()

            if cache_doc.exists:
                cache_ref.update({'invalidated': True})
                logger.info(f"Invalidated prefills for {patient_id} stage {stage}")

    except Exception as e:
        logger.error(f"Error invalidating prefills: {e}")
```

### 2. New File: `quick_mode_prompts.py`
**Action:** Move the prompts you provided into this file as-is.

### 3. Update `main.py`

#### a. Add Quick Mode endpoints

```python
from quick_mode_service import (
    generate_stage1_prefills,
    generate_stage2_prefills,
    get_cached_prefills,
    invalidate_prefills
)

@app.route('/api/quick_mode/generate_stage1/<patient_id>', methods=['POST'])
@require_auth
def quick_mode_generate_stage1(patient_id):
    """
    Background endpoint to generate Stage 1 pre-fills.
    Called after Add Patient form submission when Quick Mode is enabled.
    """
    try:
        # Verify patient exists and user has access
        patient_doc = db.collection('patients').document(patient_id).get()
        if not patient_doc.exists:
            return jsonify({'success': False, 'error': 'Patient not found'}), 404

        patient = patient_doc.to_dict()

        # Check access
        if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        # Generate pre-fills
        success, result = generate_stage1_prefills(
            patient_id=patient_id,
            age_sex=patient.get('age_sex', ''),
            present_history=patient.get('present_history', ''),
            past_history=patient.get('past_history', ''),
            physio_email=session.get('user_id')
        )

        if success:
            log_action(session.get('user_id'), 'Quick Mode Stage 1 Generated',
                      f"Generated pre-fills for {patient_id}")
            return jsonify({'success': True, 'message': 'Pre-fills generated'})
        else:
            return jsonify({'success': False, 'error': result}), 500

    except Exception as e:
        logger.error(f"Quick Mode Stage 1 generation failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Generation failed'}), 500
```

#### b. Modify `/add_patient` route

```python
@app.route('/add_patient', methods=['GET', 'POST'])
@require_auth
@require_patient_quota
def add_patient():
    if request.method == 'POST':
        # ... existing validation code ...

        # NEW: Check if Quick Mode is enabled
        quick_mode_enabled = request.form.get('quick_mode') == 'true'

        data = {
            # ... existing fields ...
            'quick_mode_enabled': quick_mode_enabled,  # NEW
            'quick_mode_stage1_completed': False,      # NEW
            'quick_mode_stage2_completed': False       # NEW
        }

        # Write the patient document
        db.collection('patients').document(patient_id).set(data)

        # NEW: If Quick Mode enabled, trigger background generation
        if quick_mode_enabled:
            try:
                # Generate in background (non-blocking)
                from threading import Thread

                def generate_async():
                    with app.app_context():
                        generate_stage1_prefills(
                            patient_id=patient_id,
                            age_sex=data['age_sex'],
                            present_history=data['present_history'],
                            past_history=data.get('past_history', ''),
                            physio_email=session.get('user_id')
                        )

                Thread(target=generate_async).start()
                logger.info(f"Quick Mode Stage 1 generation started for {patient_id}")

            except Exception as e:
                # Don't fail the patient creation if AI generation fails
                logger.error(f"Quick Mode generation failed: {e}")

        # Redirect to pathophysiological mechanism
        return redirect(url_for('patho_mechanism', patient_id=patient_id))

    # GET → render the blank form
    return render_template('add_patient.html')
```

#### c. Modify assessment screen routes (example: `patho_mechanism`)

```python
@app.route('/patho_mechanism/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
def patho_mechanism(patient_id):
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return "Patient not found."
    patient = doc.to_dict()
    if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
        return "Access denied."

    if request.method == 'POST':
        # ... existing save logic (unchanged) ...
        entry['patient_id'] = patient_id
        entry['timestamp'] = SERVER_TIMESTAMP
        db.collection('patho_mechanism').add(entry)
        return redirect(url_for('subjective', patient_id=patient_id))

    # GET: NEW - Check if Quick Mode is enabled and pre-fills available
    prefill_data = None
    is_quick_mode = patient.get('quick_mode_enabled', False)

    if is_quick_mode:
        cached = get_cached_prefills(patient_id, stage=1)
        if cached:
            prefill_data = cached.get('patho_mechanism')

    return render_template(
        'patho_mechanism.html',
        patient_id=patient_id,
        prefill_data=prefill_data,      # NEW
        is_quick_mode=is_quick_mode     # NEW
    )
```

**Repeat this pattern for:**
- `subjective`
- `chronic_disease`
- `risk_factors_clinical_flags`
- `initial_plan`
- `objective_assessment`
- `provisional_diagnosis`
- `smart_goals`
- `treatment_plan`

---

## 🎨 Frontend Changes

### 1. Update `templates/add_patient.html`
**Change:** Rename existing checkbox from "Skip optional screens" to "Enable Quick Mode"

```html
<div class="form-group" style="margin-top: 24px; border-top: 1px solid #ddd; padding-top: 24px;">
    <div style="display: flex; align-items: center; gap: 12px;">
        <label class="toggle-switch" style="margin: 0;">
            <input type="checkbox" id="quick_mode" name="quick_mode" value="true">
            <span class="toggle-slider"></span>
        </label>
        <label for="quick_mode" style="margin: 0; cursor: pointer; font-weight: 600;">
            Quick Mode — AI-assisted pre-fills (BETA)
        </label>
    </div>
    <p style="margin: 8px 0 0 44px; font-size: 0.9em; color: #666;">
        Auto-populate forms from patient history using AI. You can review and edit all suggestions before saving.
    </p>
</div>
```

### 2. Update Assessment Templates (Pattern)

#### Example: `templates/patho_mechanism.html`

```html
{% extends "base.html" %}
{% from 'progress_bar_macro.html' import render_progress_bar %}

{% block content %}
<div class="container">
    {{ render_progress_bar(current_step=2, patient_id=patient_id) }}

    <!-- NEW: Quick Mode Indicator -->
    {% if is_quick_mode %}
    <div class="alert alert-info" style="margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
        <i class="fas fa-robot"></i>
        <div>
            <strong>Quick Mode Active</strong> — AI suggestions loaded. Review and edit before saving.
        </div>
    </div>
    {% endif %}

    <h2>Pathophysiological Mechanism</h2>
    <form method="POST">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

        <div class="form-group">
            <label for="area_involved">Area Involved:</label>
            <textarea
                id="area_involved"
                name="area_involved"
                rows="3"
                required
            >{{ prefill_data.area_involved if prefill_data else '' }}</textarea>
        </div>

        <div class="form-group">
            <label for="presenting_symptom">Presenting Symptom:</label>
            <textarea
                id="presenting_symptom"
                name="presenting_symptom"
                rows="3"
                required
            >{{ prefill_data.presenting_symptom if prefill_data else '' }}</textarea>
        </div>

        <div class="form-group">
            <label for="pain_type">Pain Type:</label>
            <select id="pain_type" name="pain_type" required>
                <option value="">Select...</option>
                {% set pain_types = ['Pulling', 'Burning', 'Stabbing', 'Aching', 'Throbbing', 'Shooting', 'Tingling', 'Numbness', 'Mixed'] %}
                {% for type in pain_types %}
                <option value="{{ type }}"
                    {% if prefill_data and prefill_data.pain_type == type %}selected{% endif %}>
                    {{ type }}
                </option>
                {% endfor %}
            </select>
        </div>

        <!-- Continue pattern for all other fields... -->

        <button type="submit" class="button">Save & Next</button>
    </form>
</div>
{% endblock %}
```

**Apply this pattern to ALL assessment templates:**
- `patho_mechanism.html` ✓
- `subjective.html`
- `chronic_disease.html`
- `risk_factors_clinical_flags.html`
- `initial_plan.html`
- `objective_assessment.html`
- `provisional_diagnosis.html`
- `smart_goals.html`
- `treatment_plan.html`

### 3. Add Loading Indicator

Create new partial: `templates/_quick_mode_loading.html`

```html
<!-- Show while AI generates in background -->
<div id="quick-mode-loading" style="display: none; position: fixed; top: 80px; right: 20px; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); z-index: 1000;">
    <div style="display: flex; align-items: center; gap: 10px;">
        <div class="spinner-border spinner-border-sm" role="status"></div>
        <span>Generating AI suggestions...</span>
    </div>
</div>

<script nonce="{{ csp_nonce() }}">
// Check generation status
async function checkQuickModeStatus(patientId) {
    try {
        const response = await fetch(`/api/quick_mode/status/${patientId}`);
        const data = await response.json();

        if (data.stage1_completed) {
            document.getElementById('quick-mode-loading').style.display = 'none';
        } else {
            // Check again in 2 seconds
            setTimeout(() => checkQuickModeStatus(patientId), 2000);
        }
    } catch (error) {
        console.error('Error checking Quick Mode status:', error);
    }
}

// Start checking if Quick Mode is enabled
if ('{{ is_quick_mode }}' === 'True') {
    document.getElementById('quick-mode-loading').style.display = 'block';
    checkQuickModeStatus('{{ patient_id }}');
}
</script>
```

---

## 🧪 Testing Strategy

### Phase 1: Unit Tests
```python
# tests/test_quick_mode_service.py

def test_generate_stage1_prefills_valid_input():
    """Test Stage 1 generation with valid patient data"""
    success, data = generate_stage1_prefills(
        patient_id="test-001",
        age_sex="45/M",
        present_history="Right shoulder pain for 3 weeks",
        past_history="No significant history",
        physio_email="test@example.com"
    )

    assert success == True
    assert 'patho_mechanism' in data
    assert 'subjective' in data
    assert data['patho_mechanism']['pain_severity'] is not None

def test_cached_prefills_retrieval():
    """Test retrieving cached pre-fills"""
    # ... test cache retrieval logic

def test_invalidate_prefills():
    """Test cache invalidation when patient history changes"""
    # ... test invalidation logic
```

### Phase 2: Integration Tests
1. **Quick Mode OFF** → Verify existing flow unchanged
2. **Quick Mode ON** → Verify pre-fills appear correctly
3. **API Failure** → Verify graceful degradation (empty forms)
4. **Edit Patient History** → Verify cache invalidation
5. **Stage 2 Trigger** → Verify Stage 2 uses updated data

### Phase 3: User Acceptance Testing
Create test patient scenarios:

```
Test Patient 1: Simple Acute Case
- Age/Sex: 28/M
- Present History: Twisted left ankle playing basketball yesterday. Pain and swelling over lateral malleolus.
- Past History: No significant history.

Test Patient 2: Complex Chronic Case
- Age/Sex: 62/F
- Present History: Progressive right knee pain over 6 months. Worse with stairs and prolonged standing.
- Past History: Type 2 diabetes, hypertension, previous left knee arthroscopy 10 years ago.

Test Patient 3: Ambiguous Case (Test Conditional Language)
- Age/Sex: 34/F
- Present History: Neck pain.
- Past History: None.
```

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] All prompt injection protections added
- [ ] JSON parsing error handling implemented
- [ ] Dropdown value validation added
- [ ] Cache TTL configured (30 days)
- [ ] Cost monitoring/logging added
- [ ] Rate limiting for AI endpoints
- [ ] Environment variables configured:
  - `QUICK_MODE_ENABLED` (feature flag)
  - `AZURE_OPENAI_QUICK_MODE_DEPLOYMENT`

### Database Migration
```python
# migration_add_quick_mode.py

def migrate_patients_collection():
    """Add Quick Mode fields to existing patient documents"""
    db = get_cosmos_db()
    patients = db.collection('patients').stream()

    for patient_doc in patients:
        patient_ref = db.collection('patients').document(patient_doc.id)
        patient_ref.update({
            'quick_mode_enabled': False,  # Default OFF for existing patients
            'quick_mode_stage1_completed': False,
            'quick_mode_stage2_completed': False
        })

    print("Migration completed")

if __name__ == "__main__":
    migrate_patients_collection()
```

### Deployment Steps
1. Deploy `quick_mode_service.py` and `quick_mode_prompts.py`
2. Run database migration
3. Deploy updated `main.py` with new routes
4. Deploy updated templates
5. Test with Quick Mode OFF (verify no regression)
6. Enable Quick Mode for beta testers
7. Monitor AI token usage and costs
8. Gather feedback
9. Roll out to all users

### Rollback Plan
If critical issues found:

1. **Immediate**: Set environment variable `QUICK_MODE_ENABLED=false`
2. **Code Rollback**: Revert to previous deployment
3. **Database**: Quick Mode fields are non-breaking (can remain)
4. **User Impact**: Minimal - existing flow unaffected

---

## 💰 Cost Estimation

### Per-Patient Cost (GPT-4 Turbo)
- **Stage 1**: ~2,000 tokens × $0.01/1K = **$0.02**
- **Stage 2**: ~2,000 tokens × $0.01/1K = **$0.02**
- **Total**: **$0.04 per patient** with Quick Mode

### Monthly Projection
- 50 patients/day × 30 days = 1,500 patients/month
- Assuming 60% adoption: 900 patients use Quick Mode
- **Monthly cost**: 900 × $0.04 = **$36/month**

### ROI Calculation
- Time saved per patient: **~10 minutes** (typing/documentation)
- 900 patients × 10 min = **150 hours saved/month**
- At average physio billing rate ($100/hour): **$15,000 value**
- Cost: $36
- **ROI: 41,666%** 🚀

---

## 📋 Field Mapping Verification

### CRITICAL: Verify JSON keys match database schemas

**Status:** ⚠️ **REQUIRES VERIFICATION**

Before implementation, verify these mappings:

| Quick Mode JSON Key | Database Collection | Database Field Name |
|---------------------|---------------------|---------------------|
| `patho_mechanism.area_involved` | `patho_mechanism` | `area_involved` |
| `patho_mechanism.presenting_symptom` | `patho_mechanism` | `presenting_symptom` |
| `patho_mechanism.pain_type` | `patho_mechanism` | `pain_type` |
| `subjective.body_structure` | `subjective` | `body_structure` |
| (etc.) | (etc.) | (etc.) |

**Action Required**: Run this verification script:

```python
# verify_field_mapping.py

def verify_field_mappings():
    """Compare JSON schema to actual database field names"""

    # Get actual field names from database
    db = get_cosmos_db()
    sample_patient = db.collection('patho_mechanism').limit(1).get()[0].to_dict()
    actual_fields = set(sample_patient.keys())

    # Expected fields from Quick Mode JSON
    expected_fields = {
        'area_involved', 'presenting_symptom', 'pain_type',
        'pain_nature', 'pain_severity', 'pain_irritability',
        'possible_source', 'stage_healing'
    }

    # Check for mismatches
    missing = expected_fields - actual_fields
    extra = actual_fields - expected_fields

    if missing:
        print(f"⚠️ Missing fields in database: {missing}")
    if extra:
        print(f"ℹ️ Extra fields in database: {extra}")

    if not missing and not extra:
        print("✅ All fields match!")
```

---

## 🎛️ Configuration & Settings

### Add User Preference Toggle

Create settings page option for users to enable/disable Quick Mode globally:

**Location**: `templates/edit_profile.html`

```html
<div class="form-group">
    <label>
        <input type="checkbox" name="quick_mode_preference" value="enabled"
            {% if user.quick_mode_preference == 'enabled' %}checked{% endif %}>
        Enable Quick Mode by default for new patients
    </label>
    <p class="help-text">Auto-populate assessment forms using AI. You can override this per-patient.</p>
</div>
```

---

## 📊 Analytics & Monitoring

### Track Quick Mode Usage

Add to audit logs:
- Quick Mode enabled/disabled per patient
- AI generation success/failure rates
- Token usage per generation
- User adoption rate
- Time-to-completion comparison (Quick Mode vs Manual)

### Dashboard Metrics

Create admin dashboard showing:
- % patients using Quick Mode
- Average tokens consumed
- Monthly AI costs
- User satisfaction ratings
- Error rate tracking

---

## ⚠️ Known Limitations & Future Enhancements

### Current Limitations
1. **Patient Perspectives** - Not pre-filled (requires direct interview)
2. **No Multi-Language Support** - English only initially
3. **Token Limits** - Very long histories may exceed context limits
4. **Offline Mode** - Requires internet for AI generation

### Future Enhancements (Post-V1)
1. **Iterative Refinement** - Allow physio to regenerate specific sections
2. **Learning from Edits** - Track which pre-fills are edited most
3. **Custom Prompts** - Allow power users to customize AI instructions
4. **Voice Input Integration** - Pre-fill from voice-recorded history
5. **Multi-Language** - Support regional languages
6. **Specialty Templates** - Different prompts for sports vs geriatric vs neuro cases

---

## ✅ Implementation Checklist

### Backend (10 tasks)
- [ ] Create `quick_mode_prompts.py` (copy provided prompts)
- [ ] Create `quick_mode_service.py` with all functions
- [ ] Add `/api/quick_mode/generate_stage1/<patient_id>` endpoint
- [ ] Add `/api/quick_mode/generate_stage2/<patient_id>` endpoint
- [ ] Add `/api/quick_mode/status/<patient_id>` endpoint
- [ ] Modify `/add_patient` route to capture `quick_mode` checkbox
- [ ] Modify all 9 assessment routes to pass `prefill_data` and `is_quick_mode`
- [ ] Add cache invalidation to patient edit endpoints
- [ ] Run database migration script
- [ ] Add audit logging for all Quick Mode operations

### Frontend (11 tasks)
- [ ] Update `add_patient.html` checkbox label
- [ ] Update `patho_mechanism.html` with prefill support
- [ ] Update `subjective.html` with prefill support
- [ ] Update `chronic_disease.html` with prefill support
- [ ] Update `risk_factors_clinical_flags.html` with prefill support
- [ ] Update `initial_plan.html` with prefill support
- [ ] Update `objective_assessment.html` with prefill support
- [ ] Update `provisional_diagnosis.html` with prefill support
- [ ] Update `smart_goals.html` with prefill support
- [ ] Update `treatment_plan.html` with prefill support
- [ ] Create `_quick_mode_loading.html` partial

### Testing (8 tasks)
- [ ] Write unit tests for `quick_mode_service.py`
- [ ] Test Quick Mode OFF (verify no regression)
- [ ] Test Quick Mode ON (verify pre-fills work)
- [ ] Test API failure handling
- [ ] Test cache invalidation
- [ ] Test Stage 2 generation
- [ ] Test dropdown value validation
- [ ] User acceptance testing with 3 test patients

### Documentation (3 tasks)
- [ ] Add user guide to help docs
- [ ] Document API endpoints
- [ ] Create troubleshooting guide

### Deployment (5 tasks)
- [ ] Configure environment variables
- [ ] Run database migration in production
- [ ] Deploy code changes
- [ ] Monitor initial usage
- [ ] Gather user feedback

---

## 📞 Support & Questions

During implementation, key decision points:

1. **AI Model Choice**: GPT-4 Turbo vs Claude Sonnet vs GPT-4o?
   - Recommendation: GPT-4o (good balance of cost/quality)

2. **Background vs Synchronous Generation**:
   - Stage 1: Background (don't block navigation)
   - Stage 2: Could be synchronous (happens after exam)

3. **Cache Expiry**: 30 days sufficient?
   - Yes, aligns with typical treatment duration

4. **User Preference Default**: Quick Mode ON or OFF by default?
   - Recommendation: OFF initially, ON after beta period

---

## 🎯 Success Criteria

Quick Mode V1 is successful if:

1. ✅ **Zero Breaking Changes** - Existing users see no regression
2. ✅ **>40% Adoption** - 40%+ of new patients use Quick Mode within 30 days
3. ✅ **>80% Accuracy** - Users edit <20% of AI-generated content
4. ✅ **Time Savings** - Average assessment completion time reduced by >30%
5. ✅ **Cost Efficiency** - Monthly AI costs <$50 for 100 users
6. ✅ **User Satisfaction** - >4/5 rating from beta testers

---

**End of Implementation Plan**

*Next Step: Review this plan, confirm approach, then proceed with implementation*
