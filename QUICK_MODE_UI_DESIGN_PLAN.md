# Quick Mode – UI/UX Design Plan
**Version:** 1.0  
**Date:** 2026-05-04  
**Scope:** How each field on each assessment screen should look and behave in Quick Mode  
**Principle:** No code changes yet — this is the design blueprint only.

---

## Core Concept: Three Field Types

In normal mode, every field is a blank form element. In Quick Mode, every field falls into one of three types depending on whether AI can pre-fill it and what kind of input is needed.

---

### TYPE A — "Confirm" fields
**What:** AI has already picked the right discrete option (dropdown, yes/no). The physio just confirms or taps a different option.  
**Why:** These are multiple-choice fields — no typing needed, just one tap.  
**UI:** Visual pill/chip selector replacing the dropdown. All options shown inline as tappable pills. The AI-selected option is pre-highlighted in teal. Clicking any other pill switches the selection. A hidden `<input>` carries the actual form value so the backend is unchanged.

Example — Pain Type:  
`[Pulling]  [Sharp ✓ AI]  [Dull]  [Stabbing]  [Radiating]`

For binary (yes/no) fields:  
`Pain Irritability:  [● Present]  [○ Absent]`

---

### TYPE B — "Review & Edit" fields  
**What:** AI has generated a text suggestion based on patient history. Physio reads it, edits if needed, and saves.  
**Why:** Free-text clinical reasoning that AI can sensibly draft from history.  
**UI:** Same textarea as normal mode BUT:
- 3px left border in teal/blue
- Small `🤖 AI` badge in the top-right corner of the field
- Light blue background tint (#f0f9ff or similar)
- Physio can type directly into it — no "accept" button needed, just edit and save
- The 🧠 AI suggestion button still present for regeneration

---

### TYPE D — "Enter Findings" fields  
**What:** AI cannot pre-fill this — it requires physical examination findings the physio is about to gather.  
**Why:** These fields represent actual examination data (range of motion measured, special test results, etc.) — no history-based AI can substitute.  
**UI:**
- 3px left border in amber/orange
- `⚠️ Manual entry required` badge next to the label
- Placeholder text: `"🔬 Enter your examination findings here"`
- Light amber background tint (#fffbeb or similar)
- No AI badge, no pre-fill

---

## Quick Mode Banner (All Screens)

At the top of every assessment screen when Quick Mode is active, before the form:

```
┌─────────────────────────────────────────────────────────────────┐
│ ⚡ Quick Mode Active                                            │
│ AI has pre-suggested fields based on patient history.           │
│ Review each field, enter any examination findings, then save.   │
└─────────────────────────────────────────────────────────────────┘
```

Color: teal/blue background, white text. Kept compact — one thin bar, not a modal.

---

## Screen-by-Screen Field Design

---

### Screen 1: Patho Mechanism

| Field | Current UI | Quick Mode Type | Quick Mode UI |
|-------|-----------|-----------------|---------------|
| Area Involved | Textarea | TYPE B | Pre-filled textarea, teal border, 🤖 badge |
| Presenting Symptom | Textarea | TYPE B | Pre-filled textarea, teal border, 🤖 badge |
| Pain Type | Dropdown (5 options) | TYPE A | Horizontal pill selector, AI option highlighted |
| Pain Nature | Dropdown (3 options) | TYPE A | Horizontal pill selector |
| Pain Severity / VAS | Slider 0–10 | TYPE A | Same slider, pre-set to AI value, small `🤖 X/10` label |
| Pain Irritability | Dropdown (Present/Absent) | TYPE A | Two large toggle buttons: `[● Present]` `[○ Absent]` |
| Possible Source | Dropdown (4 options) | TYPE A | Horizontal pill selector |
| Stage of Healing | Dropdown (3 options) | TYPE A | Horizontal pill selector |

**Notes:**  
- This is the most mixed screen (TYPE A + TYPE B together).  
- Stage of Healing pill options are longer — stack vertically if needed on mobile.  
- The 🧠 "Possible Source" AI button can remain for regeneration.

---

### Screen 2: Subjective / Patient Functioning Assessment

| Field | Current UI | Quick Mode Type | Quick Mode UI |
|-------|-----------|-----------------|---------------|
| Body Structure | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Body Function | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Activity – Performance | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Activity – Capacity | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Contextual – Environmental | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Contextual – Personal | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |

**Notes:**  
- This is a pure TYPE B screen — all AI-generated, all just review.  
- The 🧠 buttons remain on each field for targeted regeneration.  
- Consider a screen-level "🤖 Regenerate all" button since all 6 are AI.  
- Rows should be generous (5–6 rows) because AI content will be detailed.

---

### Screen 3: Risk Factors & Clinical Flags (merged screen)

**Section 1 — Chronic Disease Maintenance Factors**

| Field | Current UI | Quick Mode Type | Quick Mode UI |
|-------|-----------|-----------------|---------------|
| Maintenance Causes | 6 Checkboxes | TYPE C (pre-checked) | Same checkboxes, AI-relevant ones pre-checked. Each AI-checked box gets a small `🤖` indicator next to it. |
| Specific Factors | Textarea (optional) | TYPE B | Pre-filled if AI identifies relevant factors, teal border |

**Section 2 — Clinical Flags**

| Field | Current UI | Quick Mode Type | Quick Mode UI |
|-------|-----------|-----------------|---------------|
| Red Flags | Textarea | TYPE B ⚠️ | Pre-filled BUT with a mandatory clinical warning (see below) |
| Orange Flags | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Yellow Flags | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Black Flags | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Blue Flags | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |

**Special treatment for Red Flags:**  
Red Flags are safety-critical. Add a non-dismissable warning inline:

```
⚠️ Red Flag suggestions are based on history only.
You must clinically verify each flag before proceeding.
```

This appears immediately below the Red Flags textarea in Quick Mode. Same teal border (AI pre-fill) but with the amber warning text underneath.

---

### Screen 4: Initial Plan of Assessment (Stage 1 AI)

This screen is the most nuanced. AI can suggest *whether* to do each test (Mandatory / With Precaution / Contraindicated) but **cannot fill findings** because no examination has happened yet.

Each of the 7 movement rows becomes a two-part row:

**Top half of row: TYPE A — Assessment category**

| Field | Current UI | Quick Mode Type | Quick Mode UI |
|-------|-----------|-----------------|---------------|
| Active Movements | Dropdown (3 options) | TYPE A | Pill selector: `[Mandatory ✓]` `[With Precaution]` `[Contraindicated]` |
| Passive Movements | Dropdown | TYPE A | Same pill pattern |
| Passive Over Pressure | Dropdown | TYPE A | Same pill pattern |
| Resisted Movements | Dropdown | TYPE A | Same pill pattern |
| Combined Movements | Dropdown | TYPE A | Same pill pattern |
| Special Tests | Dropdown | TYPE A | Same pill pattern |
| Neurodynamic | Dropdown | TYPE A | Same pill pattern |

**Bottom half of row: TYPE D — Findings (all blank)**

| Field | Current UI | Quick Mode Type | Quick Mode UI |
|-------|-----------|-----------------|---------------|
| Active Movements Details | Textarea | TYPE D | Amber border, `"🔬 Enter ROM findings from examination"` |
| Passive Movements Details | Textarea | TYPE D | Amber border, `"🔬 Enter findings"` |
| ... (all 7 detail fields) | Textarea | TYPE D | Amber border throughout |

**Layout suggestion:**  
Use a card-per-test layout instead of the current linear list. Each card has:
- Test name as card header
- Pill selector (AI pre-selected) at top
- Findings textarea (blank, amber) at bottom

This makes it very clear: top row = AI does the thinking, bottom row = physio does the examination.

---

### Screen 5: Objective Assessment (Stage 2 AI)

| Field | Current UI | Quick Mode Type | Quick Mode UI |
|-------|-----------|-----------------|---------------|
| Plan | Dropdown (2 options) | TYPE A | Two large toggle buttons: `[Comprehensive]` `[With Modifications]` |
| Assessment Notes / Modifications | Textarea | TYPE D | Amber border, `"🔬 Enter your examination observations and findings"` |

**Notes:**  
- Stage 2 AI fires after Initial Plan examination findings are saved.  
- So by the time the physio reaches this screen, AI actually has examination data.  
- However, plan_details is still a free observations field — best left as TYPE D.
- The Plan toggle can be pre-selected by AI based on Stage 2 analysis.

---

### Screen 6: Provisional Diagnosis (Stage 2 AI)

| Field | Current UI | Quick Mode Type | Quick Mode UI |
|-------|-----------|-----------------|---------------|
| Likelihood of Diagnosis | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Possible Structure at Fault | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Symptom | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Findings Supporting | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Findings Rejecting | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Hypothesis Supported? | Dropdown (Yes/No) | TYPE A | Two large toggle buttons: `[✓ Yes]` `[✗ No]` |

**Notes:**  
- Mostly a TYPE B review screen.  
- Hypothesis Supported should be a deliberate physio decision — the Yes/No toggle forces conscious confirmation rather than leaving a pre-selected dropdown that might be overlooked.  
- Consider making Hypothesis Supported always blank (require active choice) even in Quick Mode.

---

### Screen 7: SMART Goals (Stage 2 AI)

| Field | Current UI | Quick Mode Type | Quick Mode UI |
|-------|-----------|-----------------|---------------|
| Goals (Patient-Centric) | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Baseline Status | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Measurable Outcomes Expected | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Time Duration | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |

**Notes:**  
- Pure TYPE B screen, all AI review.  
- Time Duration is likely to be edited most — physio will have their own clinical judgment on rehab timeline.  
- Consider making the Time Duration field slightly more prominent (editable field clearly visible).

---

### Screen 8: Treatment Plan (Stage 2 AI)

| Field | Current UI | Quick Mode Type | Quick Mode UI |
|-------|-----------|-----------------|---------------|
| Treatment Plan | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Goal Targeted | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Reasoning | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |
| Reference | Textarea | TYPE B | Pre-filled, teal border, 🤖 badge |

**Notes:**  
- Another pure TYPE B review screen.  
- Treatment Plan and Reasoning tend to be long — increase textarea rows to 6–8 in Quick Mode.  
- Reference field: AI may suggest evidence-based references; physio should verify these exist (hallucination risk). Add small note: `"Verify references before saving."`

---

## Summary Table: All Fields Across All Screens

| Screen | TYPE A (Confirm) | TYPE B (Review) | TYPE D (Findings) |
|--------|-----------------|-----------------|-------------------|
| Patho Mechanism | pain_type, pain_nature, pain_severity, pain_irritability, possible_source, stage_healing | area_involved, presenting_symptom | — |
| Subjective | — | 6 ICF fields | — |
| Risk & Flags | maintenance_causes (checkboxes) | specific_factors, 5 flags | — |
| Initial Plan | 7 movement dropdowns | — | 7 detail textareas |
| Objective Assessment | plan | — | plan_details |
| Provisional Diagnosis | hypothesis_supported | likelihood, structure_fault, symptom, findings_support, findings_reject | — |
| SMART Goals | — | patient_goal, baseline_status, measurable_outcome, time_duration | — |
| Treatment Plan | — | treatment_plan, goal_targeted, reasoning, reference | — |
| **Totals** | **15 fields** | **22 fields** | **8 fields** |

---

## What Does NOT Change in Quick Mode

1. **Normal mode flow** — completely untouched. If `quick_mode_enabled = False`, physio sees identical screens to today.
2. **Form submission** — all POSTs send exactly the same field names and values. Backend doesn't need to know the UI type.
3. **Draft auto-save** — still runs in Quick Mode (pre-filled content gets saved as draft too).
4. **Voice input** — `data-voice-enabled` attributes stay; voice can override pre-filled content.
5. **The 🧠 per-field AI buttons** — remain for on-demand regeneration of specific fields.
6. **CSRF tokens, quota middleware** — unchanged.
7. **Patient Perspectives screen** — still skipped in Quick Mode (requires direct patient interview).

---

## Implementation Components Needed

### 1. CSS Component: `.qm-pill-selector`
A reusable CSS+JS component to replace `<select>` elements with pill buttons. Clicking a pill sets a hidden `<input>` value. Used across all TYPE A fields.

### 2. CSS Component: `.qm-field-ai` (TYPE B styling)
Add to existing `field-block` class when in Quick Mode: teal left border, light blue background, 🤖 badge. No structural change — just additional styling class applied via Jinja `{% if is_quick_mode %}`.

### 3. CSS Component: `.qm-field-manual` (TYPE D styling)
Same as above but amber border + amber background. Applied to findings fields when `is_quick_mode` is true.

### 4. Quick Mode Banner partial: `_quick_mode_banner.html`
Single reusable Jinja include added at top of each assessment template when `is_quick_mode` is true.

### 5. Quick Mode JS helper: `quickMode.js` (or inline)
Handles:
- Pill selector initialization (click → set hidden input value)
- Pill selector pre-selection from prefill data
- Visual toggle between Yes/No buttons
- Existing status-check polling (already planned in implementation plan)

### 6. Backend: Pass prefill data per field to each template
Each route passes both `is_quick_mode` (bool) and `prefill_data` (dict) to template. Template uses `{{ prefill_data.field_name if prefill_data else '' }}` in textareas and `{% if prefill_data and prefill_data.field == opt %}selected{% endif %}` in pill selectors.

---

## Design Decisions Made

1. **Pill selectors instead of dropdowns** — faster for confirm-type fields, no scroll, all options visible at once. Especially good on mobile/tablet.

2. **No "Accept All" button at screen level** — considered and rejected. A physio MUST consciously read each AI suggestion. A one-click accept-all creates liability risk (they could save hallucinated content without review). Instead, the design makes review fast but not skippable.

3. **No per-field "Accept / Edit" toggle** — considered and rejected. Too much friction and too many clicks. The teal border already signals "AI-generated." Physio edits if needed and saves. Simple.

4. **Hypothesis Supported always requires active choice** — even in Quick Mode, this is a clinical judgment call. Deliberate blank forces the physio to actually think yes or no.

5. **Red Flags warning is non-dismissable** — safety-critical. Cannot be a pop-up or banner that they close. It stays inline below the field every time.

6. **TYPE D fields are always blank** — never pre-filled, even if Stage 2 AI has some context. Examination findings must come from examination. No exceptions.

---

## Next Steps

Once this plan is reviewed and approved:

1. Build `quick_mode_prompts.py` — define the exact JSON schema the AI must return (field names must match this plan exactly).
2. Build `quick_mode_service.py` — Stage 1 and Stage 2 generation + Cosmos caching.
3. Write the CSS components (`.qm-pill-selector`, `.qm-field-ai`, `.qm-field-manual`).
4. Update each template with Quick Mode conditional blocks.
5. Update `main.py` routes to pass `is_quick_mode` and `prefill_data`.
6. Test with the 3 test patients defined in the Implementation Plan.

