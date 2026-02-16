# Pathophysiological Mechanism Screen Reorder - Implementation Plan

## Overview
Move pathophysiological mechanism from position 5 to position 2 (immediately after Add Patient).

## New Workflow Order
1. **Add Patient** → Demographics + chief complaint
2. **Pathophysiological Mechanism** ⭐ MOVED HERE → Pain classification
3. **Subjective Examination** → ICF fields
4. **Patient Perspectives** → CSM components
5. **Initial Plan** → Assessment planning
6. **Chronic Disease Factors** → Maintenance factors
7. **Clinical Flags** → Flag screening
8. **Objective Assessment** → Assessment plan
9. **Provisional Diagnosis** → Diagnosis
10. **SMART Goals** → Goals
11. **Treatment Plan** → Treatment

## Clinical Rationale
✅ **Pain mechanism diagnosed early** → Physios know what tests are contraindicated
✅ **ROM restrictions identified upfront** → Informs subjective examination approach
✅ **Better clinical decision-making** → Downstream screens have pain context
✅ **Matches clinical practice** → Pain assessment happens early in real clinical encounters

---

## FILES TO MODIFY

### 1. Backend Routes (main.py)
**Changes needed:**
- Update `add_patient` route: redirect to `patho_mechanism` instead of `subjective`
- Update `patho_mechanism` route: redirect to `subjective` instead of `chronic_disease`
- Update `subjective` route: back button should return to `patho_mechanism`
- Update all downstream routes to fetch and pass `patho_data` in context

### 2. Templates
**Files to update:**
- `templates/patho_mechanism.html` - Update continue/back buttons
- `templates/subjective.html` - Update back button to patho_mechanism
- `templates/chronic_disease.html` - Update back button to initial_plan

### 3. AI Prompts (ai_prompts.py)
**Major changes needed - detailed below**

---

## AI PROMPT RESTRUCTURING

### Screen 2: Pathophysiological Mechanism (NEW POSITION)

**CURRENT (at position 5):**
- Has access to: subjective examination, perspectives, initial plan data
- Uses detailed clinical examination findings

**NEW (at position 2):**
- Only has: age_sex, present_history, past_history
- Focus on chief complaint analysis for pain mechanism classification
- Use clinical reasoning from history alone

**New prompt approach:**
- Analyze chief complaint (location, onset, nature, aggravating/easing factors)
- Identify pain characteristics from history
- Classify likely pain mechanism (nociceptive, neuropathic, nociplastic, mixed)
- Suggest tissue source based on complaint description
- Guide pain severity/irritability assessment

### Screen 3: Subjective Examination (NEW CONTEXT ADDED)

**BEFORE:**
- Had: age_sex, present_history, past_history

**AFTER:**
- **NOW ALSO HAS: patho_data** (pain mechanism, severity, irritability, tissue source)
- Use pain mechanism to guide examination suggestions
- Consider contraindications based on pain type
- Tailor activity limitation questions to pain mechanism

**Major benefit:** AI can now suggest examination approaches that respect pain mechanisms!

### Screen 4: Patient Perspectives (NEW CONTEXT ADDED)

**AFTER:**
- **NOW ALSO HAS: patho_data**
- Can address patient concerns about specific pain mechanisms
- Guide expectations based on pain classification
- Tailor support needs to pain severity/irritability

### Screen 5: Initial Plan (NEW CONTEXT ADDED)

**AFTER:**
- **NOW ALSO HAS: patho_data early in context**
- **Can flag contraindicated tests based on pain mechanism** ← KEY BENEFIT
- Consider pain irritability when suggesting assessment plan
- Respect tissue healing stage

### Screens 6-11: All receive patho_data

All downstream screens (Chronic Disease, Clinical Flags, Objective Assessment, Provisional Diagnosis, SMART Goals, Treatment Plan) will now have patho_data available in their AI prompts.

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Backup & Preparation
- [ ] Create git branch: `feature/patho-mechanism-reorder`
- [ ] Backup current ai_prompts.py
- [ ] Document current workflow

### Phase 2: Update Backend Routes (main.py)
- [ ] Update `add_patient` POST: Change redirect to `patho_mechanism`
- [ ] Update `patho_mechanism` POST: Change redirect to `subjective`
- [ ] Update `subjective` route: Fetch patho_data and pass to template
- [ ] Update `perspectives` route: Fetch patho_data and pass to context
- [ ] Update `initial_plan` route: Fetch patho_data and pass to context
- [ ] Update `objective_assessment` route: Fetch patho_data and pass to context
- [ ] Update `provisional_diagnosis` route: Fetch patho_data and pass to context
- [ ] Update `smart_goals` route: Fetch patho_data and pass to context
- [ ] Update `treatment_plan` route: Fetch patho_data and pass to context

### Phase 3: Update Templates
- [ ] `patho_mechanism.html`: Update back button to `add_patient`
- [ ] `subjective.html`: Update back button to `patho_mechanism`
- [ ] `chronic_disease.html`: Update back button to `initial_plan`

### Phase 4: Update AI Prompts (ai_prompts.py)
- [ ] Redesign `get_pathophysiology_prompt()` for limited context
- [ ] Update `get_subjective_field_prompt()` - add patho_data parameter
- [ ] Update `get_patient_perspectives_field_prompt()` - add patho_data
- [ ] Update `get_initial_plan_field_prompt()` - ensure patho_data included
- [ ] Update `get_objective_assessment_field_prompt()` - add patho_data
- [ ] Update `get_provisional_diagnosis_field_prompt()` - add patho_data
- [ ] Update `get_smart_goals_field_prompt()` - add patho_data
- [ ] Update `get_treatment_plan_field_prompt()` - add patho_data

### Phase 5: Update API Call Sites
- [ ] Update all route handlers that call AI prompt functions
- [ ] Update mobile API if needed (mobile_api_ai.py)

### Phase 6: Testing
- [ ] Test full workflow: Add Patient → Patho → Subjective → ... → Treatment
- [ ] Test back button navigation
- [ ] Test AI suggestions with new context
- [ ] Verify patho_data passed correctly
- [ ] Test existing patient data compatibility

### Phase 7: Deployment
- [ ] Merge to main
- [ ] Deploy to Azure
- [ ] Monitor for errors
- [ ] User acceptance testing

---

## RISKS & MITIGATION

### Risk 1: Patho mechanism AI less accurate with limited context
**Mitigation:** Focus prompt on chief complaint analysis - matches real clinical practice

### Risk 2: Existing patient records won't have patho_data
**Mitigation:** Make patho_data optional in all prompts with fallback logic

### Risk 3: Navigation confusion
**Mitigation:** Clear button text, consistent with new flow

### Risk 4: Firestore query issues
**Mitigation:** Error handling, default to empty dict if not found

---

## ESTIMATED EFFORT
- Backend routes: 2-3 hours
- Template updates: 1 hour
- AI prompt redesign: 4-5 hours
- Testing: 2-3 hours
- **Total: ~10-12 hours**

---

## BENEFITS SUMMARY

1. ✅ **Early pain mechanism classification** - guides all subsequent assessment
2. ✅ **Contraindications identified upfront** - safer clinical practice
3. ✅ **Better AI context** - downstream screens have pain data
4. ✅ **Matches clinical workflow** - how physios actually work
5. ✅ **ROM/pain restrictions known early** - informs examination approach
