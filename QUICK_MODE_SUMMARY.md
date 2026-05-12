# Quick Mode — Full Implementation Summary

## What Quick Mode Is

Quick Mode is a parallel, AI-assisted documentation flow for PhysiologicPRISM.
When a physio enables Quick Mode during patient registration, the app routes them
through `/qm/` screens instead of the normal screens. Each screen is pre-filled
with AI-generated concise bullet points based on patient history (Stage 1) and
later on examination findings (Stage 2). The physio can edit or approve each
field, then save and continue. All data saves to the same Cosmos DB collections
as the normal flow — nothing is duplicated.

---

## Files Created (New)

### 1. `quick_mode_prompts.py`
Contains all AI prompts for every Quick Mode screen.

**Structure per screen:** System prompt + User prompt template + Builder function + Field list/options

| Screen | System Prompt | Builder Function |
|--------|--------------|-----------------|
| Patho Mechanism | `PATHO_MECHANISM_SYSTEM` | `build_patho_mechanism_user_prompt()` |
| Subjective / ICF | `SUBJECTIVE_QUESTIONS_SYSTEM` | `build_subjective_questions_user_prompt()` |
| Initial Plan | `INITIAL_PLAN_SYSTEM` | `build_initial_plan_user_prompt()` |
| Risk Flags | `RISK_FLAGS_SYSTEM` | `build_risk_flags_user_prompt()` |
| Objective Assessment | `OBJ_ASSESSMENT_SYSTEM` | `build_obj_assessment_user_prompt()` |
| Provisional Diagnosis | `PROV_DIAG_SYSTEM` | `build_prov_diag_user_prompt()` |
| SMART Goals | `SMART_GOALS_SYSTEM` | `build_smart_goals_user_prompt()` |
| Treatment Plan | `TREATMENT_PLAN_SYSTEM` | `build_treatment_plan_user_prompt()` |

**Key rule:** SMART Goals and Treatment Plan system prompts enforce "ONLY 2-3 bullet
points per field using '• ' prefix — no paragraphs, no headers". This was deliberately
strict because normal AI output was too verbose for Quick Mode.

**Reference field:** Treatment Plan's `reference` field is always returned as `""` —
the AI is explicitly forbidden from fabricating citations.

**`_format_initial_plan_findings(initial_plan_data)`** — helper that converts the
7-test Initial Plan Cosmos document into a readable string for Stage 2 prompts.

---

### 2. `quick_mode_service.py`
Contains one `generate_X_prefills()` + one `_validate_X_prefills()` function per screen.

**Pattern every function follows:**
1. Check `patient.get("present_history")` — return `{}` if missing
2. Call `get_azure_openai_client()`
3. Build user prompt using the builder from `quick_mode_prompts.py`
4. Call `client.generate_json_response(system_prompt, user_prompt)`
5. If response is empty or contains `"error"` → return `{}`
6. Run through `_validate_X_prefills()` to sanitise values
7. Return clean dict or `{}` on any exception

**Validation rules:**
- Dropdown fields (e.g. `possible_source`, `stage_healing`, `plan`) are checked
  against known allowed values — if AI returns an invalid option, it's blanked
  (physio must choose manually)
- Free-text fields are stripped of whitespace, `None` → `""`
- `reference` in Treatment Plan is always forced to `""` regardless of AI output

---

### 3. `templates/qm/` (8 new HTML templates)

All extend `base.html` and use `render_progress_bar` with `quick_mode=True`.

| Template | Step | Key Features |
|----------|------|-------------|
| `patho_mechanism.html` | 2 | Dropdowns pre-selected with 🤖 badge + reasoning toggle |
| `subjective.html` | 3 | ICF domain textareas pre-filled with suggested questions |
| `initial_plan.html` | 5 | 7 test rows — AI suggests category, physio fills findings |
| `risk_factors_clinical_flags.html` | 6 | Pre-checked checkboxes with 🤖 badge; red alert if red flags present |
| `objective_assessment.html` | 7 | Plan dropdown pre-selected + Assessment Notes textarea pre-filled |
| `provisional_diagnosis.html` | 8 | 5 fields + "📋 Clinical Reasoning" toggle button per field |
| `smart_goals.html` | 9 | 4 fields, 2-3 bullet points each |
| `treatment_plan.html` | 10 | 4 fields + Schedule Follow-up widget (same as normal template) |

**Three field types used across templates:**
- **TYPE B (teal)** — `prefilled-textarea` class, teal left border, `#f0fdfa` background,
  "🤖 AI suggested — edit as needed" label above
- **Blank fallback** — plain white textarea with 🧠 button for manual AI assist,
  shown when AI returned `{}` or a specific field was blank
- **Pre-checked checkbox** — normal checkbox rendered checked, with `🤖 AI` badge beside it

**Fallback warning:** Every template has:
```jinja
{% if not prefills %}
  ⚠️ AI recommendations could not be generated — complete this screen manually.
{% endif %}
```

---

## Files Modified

### `main.py` — 8 new QM routes added (lines ~5900–6380)

All routes follow this pattern:
```
@app.route('/qm/<screen>/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
def qm_<screen>(patient_id):
    from quick_mode_service import generate_X_prefills  # local import avoids circular imports
    ...
    if request.method == 'POST':
        # save to Cosmos (same collection as normal route)
        return redirect(url_for('qm_next_screen', patient_id=patient_id))
    # GET: fetch context from Cosmos, call AI, render template
    prefills = generate_X_prefills(...)
    return render_template('qm/<screen>.html', ...)
```

**The complete redirect chain (POST flow):**
```
add_patient (POST, quick_mode=True)
  → /qm/patho_mechanism
  → /qm/subjective
  → /perspectives  (normal route, but redirects to qm_initial_plan in QM mode)
  → /qm/initial_plan
  → /qm/risk_factors
  → /qm/objective_assessment
  → /qm/provisional_diagnosis
  → /qm/smart_goals
  → /qm/treatment_plan
  → /dashboard
```

**Stage 1 vs Stage 2 AI context:**
- **Stage 1** (patient history only): patho_mechanism, subjective, initial_plan, risk_flags
- **Stage 2** (history + Initial Plan findings + objective assessment): objective_assessment,
  provisional_diagnosis, smart_goals, treatment_plan

Each Stage 2 route fetches multiple Cosmos collections before calling AI:
```python
patho_data        = _fetch_latest('patho_mechanism')
initial_plan_data = _fetch_latest('initial_plan')
obj_data          = _fetch_latest('objective_assessments')
prov_diag_data    = _fetch_latest('provisional_diagnosis')
smart_goals_data  = _fetch_latest('smart_goals')
```

**Original routes completely untouched** — confirmed by checking:
- `/risk_factors_clinical_flags/<patient_id>` (line 6412)
- `/objective_assessment/<patient_id>` (line 6456)
- `/provisional_diagnosis/<patient_id>` (line 6490)
- `/smart_goals/<patient_id>` (line 6544)
- `/treatment_plan/<patient_id>` (line 6596)

---

## Bugs Found and Fixed During Audit

### 1. Broken route URL strings (critical)
Python escape sequences inside route strings were producing control characters:
- `'\qm\risk_factors\...'` → `\r` = carriage return — Flask would never match this URL
- `'\qm\treatment_plan\...'` → `\t` = tab — same problem
- Three other routes used backslashes instead of forward slashes

**Fix:** All 5 routes changed to proper forward-slash strings:
```python
'/qm/risk_factors/<path:patient_id>'
'/qm/objective_assessment/<path:patient_id>'
'/qm/provisional_diagnosis/<path:patient_id>'
'/qm/smart_goals/<path:patient_id>'
'/qm/treatment_plan/<path:patient_id>'
```

### 2. "Skip for now" buttons pointing to normal routes
- `risk_factors_clinical_flags.html` "Skip" was pointing to `objective_assessment`
  (normal) instead of `qm_objective_assessment`
- `objective_assessment.html` "Skip" was pointing to `provisional_diagnosis`
  (normal) instead of `qm_provisional_diagnosis`

**Fix:** Both corrected to use QM route names.

### 3. File truncation
The Python script used to fix the backslash routes caused `main.py` to be truncated
at line 12888 (mid-sentence inside the `blog_waitlist` function).

**Fix:** The missing 68 lines (the `blog_waitlist` function body + `if __name__ == '__main__':` 
block) were restored from `git show HEAD:main.py`. File now ends correctly at line 12956.

---

## If Something Goes Wrong

### App won't start / ImportError
Check that `quick_mode_prompts.py` and `quick_mode_service.py` are in the same
directory as `main.py`. The imports inside QM routes are local (inside the function)
to avoid circular imports — that's intentional.

### QM route returns 404
The URL must use forward slashes: `/qm/risk_factors/PATIENT_ID`. If you see a 404
on any QM screen, check `main.py` for the corresponding `@app.route` and confirm
it uses `/qm/...` with forward slashes.

### AI prefills not appearing (blank form shown instead)
The template's `{% if not prefills %}` fallback triggers when:
- `present_history` is empty on the patient record
- Azure OpenAI API is down or returns an error
- The AI returned an invalid JSON response
Check the app logs for `Quick Mode ... prefill failed` error messages.

### Wrong data in dropdowns (blank instead of pre-selected)
The `_validate_X_prefills()` function blanks any dropdown value that doesn't
exactly match the allowed options list. Check `quick_mode_prompts.py` for the
`PATHO_VALID_OPTIONS`, `OBJ_ASSESSMENT_PLAN_OPTIONS`, and `MAINTENANCE_CAUSE_OPTIONS`
lists — they must exactly match the `<option value="">` strings in the normal templates.

### Normal flow broken after this change
All normal routes are untouched. If a normal route breaks, it is unrelated to Quick Mode.
Quick Mode routes are completely isolated under `/qm/` and share no code with normal routes
except the Cosmos DB write (which uses the same collection names and field names).

### Rollback
To revert only the Quick Mode changes:
```bash
git revert HEAD --no-edit
git push origin main
```
This creates a new commit that undoes the Quick Mode commit without touching git history.
