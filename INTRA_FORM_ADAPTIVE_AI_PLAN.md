# Intra-Form Adaptive AI - Implementation Plan

## Overview
Enhance AI suggestions to adapt based on findings from previous fields **within the same form**, not just previous screens.

## Clinical Rationale

### Current Problem:
- AI suggests "test proximal and distal joints" for every field independently
- Even if user already tested proximal joint and found it normal, AI keeps suggesting it
- No learning/adaptation within the same assessment form

### Desired Behavior:
**Scenario 1: Normal Findings → Tone Down**
- Field 1 (Proximal Joint): User enters "Shoulder ROM full, pain-free, MMT 5/5"
- Field 2 (Distal Joint): AI should recognize shoulder is **clear** and tone down shoulder suggestions
- AI should focus on other areas (local, distal, neural)

**Scenario 2: Abnormal Findings → Dig Deeper**
- Field 1 (Proximal Joint): User enters "Shoulder limited abduction 90°, pain on IR, weakness"
- Field 2 (Special Tests): AI should recognize shoulder has **pathology** and suggest more shoulder-specific tests
- AI should prioritize shoulder impingement tests, RC tests, labral tests

**Scenario 3: Mixed Findings → Prioritize**
- Field 1: Proximal clear, distal shows issues
- Field 2: AI focuses on distal joint assessment
- Field 3: AI suggests functional tests related to distal pathology

---

## Technical Implementation

### Current Data Flow:
1. User clicks 🧠 button on a field
2. Frontend sends POST to `/api/ai_suggestion/objective_assessment/<field>`
3. Request includes:
   ```json
   {
     "patient_id": "123",
     "field": "distal_joint",
     "inputs": {
       "proximal_joint": "Shoulder ROM full and pain-free",
       "palpation": "Tenderness over bicipital groove",
       "special_tests": ""  // Empty - not filled yet
     },
     "previous": { /* data from previous screens */ }
   }
   ```
4. Backend calls `get_objective_assessment_field_prompt()` with this data
5. AI generates suggestion

### Enhancement Needed:
Add **intra-form context analysis** to the prompt to:
1. Parse existing field inputs (`inputs` dict)
2. Classify findings as normal/abnormal for each anatomical area
3. Adjust suggestions based on what's already been tested and results

---

## Prompt Restructuring Strategy

### Step 1: Add Intra-Form Context Analyzer

Create a function to analyze existing inputs and extract clinical insights:

```python
def analyze_objective_findings(inputs: Dict[str, str]) -> Dict[str, Any]:
    """
    Analyze existing objective assessment inputs to guide AI suggestions.

    Returns:
        {
            'proximal_status': 'clear' | 'abnormal' | 'untested',
            'distal_status': 'clear' | 'abnormal' | 'untested',
            'local_status': 'clear' | 'abnormal' | 'untested',
            'neural_status': 'clear' | 'abnormal' | 'untested',
            'abnormal_areas': ['shoulder', 'biceps tendon'],
            'clear_areas': ['elbow', 'wrist'],
            'priority_focus': 'local' | 'proximal' | 'distal' | 'neural'
        }
    """
```

**Detection Logic:**
- **Clear/Normal indicators**: "full ROM", "pain-free", "negative", "normal", "5/5 strength", "no tenderness"
- **Abnormal indicators**: "limited", "reduced", "painful", "positive", "weak", "tenderness", "swelling", "instability"
- **Untested**: Field is empty or contains placeholder text

### Step 2: Update Prompt Structure

Add a new section to `get_objective_assessment_field_prompt()`:

```
INTRA-FORM ADAPTIVE CONTEXT:

Previous Fields Completed on This Form:
- Proximal Joint Assessment: [status: CLEAR/ABNORMAL/UNTESTED]
  Input: "{proximal_joint_input}"
  Interpretation: Shoulder shows full ROM and no pain → CLEAR, no further proximal testing needed

- Palpation: [status: ABNORMAL]
  Input: "{palpation_input}"
  Interpretation: Tenderness over bicipital groove → LOCAL PATHOLOGY detected

- Special Tests: [status: UNTESTED]
  Input: ""

ADAPTIVE GUIDANCE FOR CURRENT FIELD ({field}):

✅ AREAS ALREADY CLEARED (tone down suggestions):
- Shoulder (proximal joint tested, normal findings)

⚠️ AREAS WITH ABNORMALITIES (prioritize related tests):
- Biceps tendon (tenderness on palpation)

🔍 AREAS NOT YET TESTED (maintain standard suggestions):
- Distal joints
- Neural structures

SUGGESTION STRATEGY:
1. If this field relates to CLEARED areas → Provide brief/minimal suggestions, note area already assessed
2. If this field relates to ABNORMAL areas → Provide detailed, specific tests to further investigate pathology
3. If this field relates to UNTESTED areas → Standard comprehensive suggestions

For current field '{field}':
[AI determines which category applies and adjusts detail level accordingly]
```

### Step 3: Field-Specific Adaptation Examples

#### Example 1: Distal Joint Field (after proximal tested clear)
**Without adaptation:**
```
Suggestion: "Assess elbow, wrist, and shoulder ROM. Test flexion, extension, pronation, supination..."
```

**With adaptation:**
```
Suggestion: "Focus on distal joints (elbow, wrist) as proximal shoulder already assessed and clear.
- Elbow: Flexion/extension ROM, varus/valgus stress
- Wrist: Flexion/extension, radial/ulnar deviation
Note: Shoulder ROM already documented as full and pain-free."
```

#### Example 2: Special Tests (after palpation shows biceps tenderness)
**Without adaptation:**
```
Suggestion: "Consider impingement tests, labral tests, RC tests, biceps tests..."
```

**With adaptation:**
```
Suggestion: "PRIORITY: Biceps-specific tests (tenderness noted on palpation):
- Speed's test (biceps tendon)
- Yergason's test (biceps tendon)
- Upper cut test (SLAP lesion)

Secondary: Impingement tests if shoulder motion was limited
Note: Palpation revealed bicipital groove tenderness - correlate with these provocative tests."
```

#### Example 3: Neurological Tests (after all MSK tests clear)
**Without adaptation:**
```
Suggestion: "Test dermatomes, myotomes, reflexes for C5-T1..."
```

**With adaptation:**
```
Suggestion: "Comprehensive neural screening warranted as proximal/distal/local structures tested clear:
- Consider neurogenic source given normal MSK findings
- Dermatomes: C5-C6-C7-C8-T1 sensation
- Myotomes: Shoulder, elbow, wrist, hand strength
- Reflexes: Biceps (C5-6), triceps (C7), brachioradialis
- Neurodynamic tests: ULNT (upper limb neural tension)

Note: MSK structures show minimal findings - neural involvement should be ruled out."
```

---

## Implementation Steps

### Phase 1: Create Analysis Function
**File**: `ai_prompts.py`

```python
def analyze_objective_findings(inputs: Dict[str, str]) -> Dict[str, Any]:
    """
    Analyze existing objective assessment inputs to detect:
    1. Which areas have been tested
    2. Which areas show normal findings (clear)
    3. Which areas show abnormal findings (pathology)
    4. What the priority focus should be
    """

    # Keywords for classification
    CLEAR_KEYWORDS = [
        'full rom', 'pain-free', 'pain free', 'negative', 'normal',
        '5/5', 'no pain', 'no tenderness', 'no swelling', 'no restriction',
        'intact', 'within normal limits', 'wnl'
    ]

    ABNORMAL_KEYWORDS = [
        'limited', 'reduced', 'painful', 'pain on', 'positive',
        'weak', 'weakness', 'tenderness', 'tender', 'swelling',
        'restricted', 'instability', 'reduced strength', 'guarding',
        'spasm', 'trigger point', 'decreased'
    ]

    analysis = {
        'proximal_status': 'untested',
        'distal_status': 'untested',
        'local_status': 'untested',
        'neural_status': 'untested',
        'abnormal_areas': [],
        'clear_areas': [],
        'tested_fields': [],
        'untested_fields': []
    }

    # Analyze each field
    for field_name, field_value in inputs.items():
        if not field_value or len(field_value.strip()) < 5:
            analysis['untested_fields'].append(field_name)
            continue

        analysis['tested_fields'].append(field_name)
        value_lower = field_value.lower()

        # Check for clear findings
        is_clear = any(keyword in value_lower for keyword in CLEAR_KEYWORDS)
        is_abnormal = any(keyword in value_lower for keyword in ABNORMAL_KEYWORDS)

        # Classify by anatomical area
        if 'proximal' in field_name.lower():
            analysis['proximal_status'] = 'clear' if is_clear else ('abnormal' if is_abnormal else 'tested')
            if is_clear:
                analysis['clear_areas'].append('proximal joint')
            if is_abnormal:
                analysis['abnormal_areas'].append('proximal joint')

        if 'distal' in field_name.lower():
            analysis['distal_status'] = 'clear' if is_clear else ('abnormal' if is_abnormal else 'tested')
            if is_clear:
                analysis['clear_areas'].append('distal joint')
            if is_abnormal:
                analysis['abnormal_areas'].append('distal joint')

        # Add more classification logic...

    # Determine priority focus
    if analysis['abnormal_areas']:
        analysis['priority_focus'] = analysis['abnormal_areas'][0]  # Focus on first abnormality
    elif 'untested' in [analysis['proximal_status'], analysis['distal_status']]:
        analysis['priority_focus'] = 'complete assessment'
    else:
        analysis['priority_focus'] = 'neural/referred sources'

    return analysis
```

### Phase 2: Update get_objective_assessment_field_prompt()
**File**: `ai_prompts.py`

Add `existing_inputs` parameter:
```python
def get_objective_assessment_field_prompt(
    field: str,
    age_sex: str,
    present_hist: str,
    past_hist: str,
    subjective: Optional[Dict[str, Any]] = None,
    assessments: Optional[Dict[str, Any]] = None,
    patho_data: Optional[Dict[str, Any]] = None,
    existing_inputs: Optional[Dict[str, str]] = None  # NEW: Current form inputs
) -> str:
```

Add intra-form context section:
```python
# NEW: Analyze existing inputs from this form
intra_form_context = ""
if existing_inputs:
    analysis = analyze_objective_findings(existing_inputs)

    if analysis['tested_fields']:
        intra_form_context = "\n\n🔄 INTRA-FORM ADAPTIVE CONTEXT (Learning from previous fields on THIS form):\n\n"

        # Show what's been tested
        intra_form_context += "FIELDS ALREADY COMPLETED:\n"
        for field_name in analysis['tested_fields']:
            field_value = existing_inputs.get(field_name, '')
            status = "✅ CLEAR" if field_name in str(analysis['clear_areas']) else "⚠️ ABNORMAL" if field_name in str(analysis['abnormal_areas']) else "📝 TESTED"
            intra_form_context += f"- {field_name}: {status}\n  Input: \"{field_value[:100]}...\"\n"

        # Adaptive guidance
        intra_form_context += "\n🎯 ADAPTIVE GUIDANCE FOR THIS FIELD:\n"

        if analysis['clear_areas']:
            intra_form_context += f"✅ AREAS CLEARED (minimize further testing): {', '.join(analysis['clear_areas'])}\n"
            intra_form_context += "   → If this field relates to cleared areas, acknowledge they're already assessed and suggest moving focus elsewhere.\n"

        if analysis['abnormal_areas']:
            intra_form_context += f"⚠️ AREAS WITH PATHOLOGY (dig deeper): {', '.join(analysis['abnormal_areas'])}\n"
            intra_form_context += "   → If this field relates to abnormal areas, provide detailed/specific tests to further investigate.\n"

        if analysis['untested_fields']:
            intra_form_context += f"🔍 AREAS NOT YET TESTED: {', '.join(analysis['untested_fields'])}\n"
            intra_form_context += "   → If this field relates to untested areas, provide comprehensive standard suggestions.\n"

        intra_form_context += f"\n💡 PRIORITY FOCUS: {analysis['priority_focus']}\n"
        intra_form_context += "\nIMPORTANT: Adjust your suggestion detail/emphasis based on what's already been found. Don't repeat tests for cleared areas. Dig deeper into abnormal findings.\n"
```

### Phase 3: Update API Endpoint
**File**: `main.py`

Modify `objective_assessment_field_suggest()` to pass existing inputs:

```python
@app.route('/api/ai_suggestion/objective_assessment/<field>', methods=['POST'])
@csrf.exempt
@require_firebase_auth
@require_ai_quota
def objective_assessment_field_suggest(field):
    data = request.get_json() or {}

    # ... existing code to fetch patient data ...

    # NEW: Get current form inputs
    existing_inputs = data.get('inputs', {})  # Frontend sends current form state

    # Call prompt with existing inputs
    prompt = get_objective_assessment_field_prompt(
        field=field,
        age_sex=sanitized_age_sex,
        present_hist=sanitized_present,
        past_hist=sanitized_past,
        subjective=sanitized_subjective,
        assessments=sanitized_initial_plan,
        patho_data=sanitized_patho,
        existing_inputs=existing_inputs  # NEW: Pass intra-form context
    )
```

### Phase 4: Frontend Update (if needed)
**File**: `static/ai_suggestions.js`

Ensure frontend sends current form inputs when requesting AI suggestions:

```javascript
// When user clicks AI button
const formData = new FormData(document.getElementById('objective-form'));
const currentInputs = {};
formData.forEach((value, key) => {
    currentInputs[key] = value;
});

fetch(`/api/ai_suggestion/objective_assessment/${field}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        patient_id: patientId,
        field: field,
        inputs: currentInputs,  // Send current form state
        previous: { /* previous screen data */ }
    })
});
```

---

## Expected Outcomes

### Clinical Benefits:
1. ✅ **Smarter Suggestions**: AI doesn't repeat tests for cleared areas
2. ✅ **Deeper Investigation**: AI focuses on abnormal findings
3. ✅ **Efficient Workflow**: Clinicians don't waste time on redundant suggestions
4. ✅ **Clinical Reasoning**: Mirrors how physios actually think (if proximal clear → focus local/distal)

### Example Workflow:

**Patient: 45M with right elbow pain**

1. **Field 1: Proximal Joint Assessment**
   - AI suggests: "Assess shoulder ROM, strength, referred pain patterns"
   - User enters: "Shoulder ROM full and pain-free, MMT 5/5, no referred pain"
   - Status: ✅ Proximal CLEAR

2. **Field 2: Local Joint Assessment**
   - AI receives: "Proximal clear, focus on local elbow"
   - AI suggests: "Focus on elbow (proximal cleared): Flexion/extension ROM, varus/valgus stress, lateral/medial epicondyle palpation"
   - User enters: "Elbow ROM full, tenderness over lateral epicondyle, pain on resisted wrist extension"
   - Status: ⚠️ Local ABNORMAL (lateral epicondylitis suspected)

3. **Field 3: Special Tests**
   - AI receives: "Proximal clear, local abnormal (lateral epicondyle), dig deeper"
   - AI suggests: "PRIORITY - Lateral epicondylitis tests (tenderness noted): Cozen's test, Mill's test, Maudsley's test (resisted middle finger extension)"
   - User confirms: "All positive for lateral epicondylitis"

4. **Field 4: Distal Joint Assessment**
   - AI receives: "Proximal clear, local pathology confirmed, check distal for completeness"
   - AI suggests: "Brief distal screen (proximal/local already assessed): Wrist ROM, grip strength. Primary pathology appears local (lateral epicondyle)."

5. **Field 5: Neurological Assessment**
   - AI receives: "MSK pathology confirmed (lateral epicondylitis), neural screen for completeness"
   - AI suggests: "Brief neural screen to rule out radial nerve involvement: C6-C7 dermatomes, wrist/finger extensors (already tested), triceps reflex. Expected normal given clear MSK diagnosis."

---

## Implementation Timeline

- **Phase 1**: Create `analyze_objective_findings()` function - 2 hours
- **Phase 2**: Update `get_objective_assessment_field_prompt()` - 2 hours
- **Phase 3**: Update API endpoint - 1 hour
- **Phase 4**: Frontend update (if needed) - 1 hour
- **Testing**: Full workflow testing - 2 hours
- **Total**: ~8 hours

---

## Extensibility

This pattern can be extended to other forms:
- **Subjective Examination**: If activity limitations already documented, tone down repetitive questions
- **Patient Perspectives**: If identity/cause already explored, focus on timeline/consequences
- **Treatment Plan**: If manual therapy already comprehensive, focus on exercise prescription

---

## Risks & Mitigation

### Risk 1: AI misclassifies findings
**Mitigation**: Conservative keyword matching, err on side of "tested" rather than "clear/abnormal"

### Risk 2: Over-suppression of important tests
**Mitigation**: Only tone down, never eliminate suggestions. Always provide at least brief mention.

### Risk 3: Complex logic increases token usage
**Mitigation**: Keep analysis concise, only include relevant context for current field

---

## Success Metrics

After implementation, verify:
1. ✅ AI stops suggesting shoulder tests after shoulder documented as clear
2. ✅ AI provides detailed special tests when palpation reveals tenderness
3. ✅ AI prioritizes neural tests when all MSK areas cleared
4. ✅ Clinicians report more relevant, context-aware suggestions
5. ✅ Reduced time spent dismissing irrelevant AI suggestions
