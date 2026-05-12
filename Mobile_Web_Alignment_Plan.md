# Mobile App ↔ Web App — Complete Alignment Analysis
**Date:** 2026-05-05  
**Web App:** `D:\New folder\New folder\Latest\Recovery`  
**Mobile App:** `D:\New folder\New folder\Latest\New Mobile`  

---

## CATEGORY 1 — Critical: Data Architecture Split-Brain

This is the most fundamental issue and affects everything.

**The problem:** The mobile app saves all assessment data via `PATCH /api/patients/<id>` as nested camelCase objects inside the patient document (`subjectiveExamination`, `patientPerspectives`, `smartGoals`, etc.). But `mobile_api.py` reads data from *separate* Firestore collections (`subjective_examination`, `patient_perspectives`, `smart_goals`, etc.) in two critical places:

1. **Patient list progress flags** — checks `db.collection('smart_goals')` to set `smartGoals: True`. Since mobile never writes to that collection, every patient created on mobile shows 0% progress forever.
2. **Comprehensive report** — calls `fetch_one('smart_goals')`, `fetch_one('patient_perspectives')` etc. Since mobile data lives in the patient document, not these collections, the patient report is always blank.

**Fix needed in `mobile_api.py`:** All the assessment PATCH saves need to be intercepted and written to the correct separate collections (same as the web does), OR the comprehensive-report and progress-check endpoints need to fall back to reading from the patient document.

---

## CATEGORY 2 — Critical: Follow-up Data Completely Lost

**The problem:** A three-way field name mismatch means all follow-up data is silently discarded.

| Layer | Fields used |
|---|---|
| Mobile app sends | `gradeOfAchievement`, `perceptionOfTreatment`, `feedback`, `planForNextTreatment`, `sessionNumber`, `followUpDate` |
| mobile_api.py reads | `date`, `notes`, `subjective`, `objective_findings`, `treatment_given`, `next_plan` |
| Web stores/displays | `session_number`, `session_date`, `grade`, `perception`, `feedback`, `treatment_plan` |

None of the mobile fields match what `mobile_api.py` looks for, so every follow-up is saved with empty strings.

**Fix:** Update `mobile_api.py` `api_create_follow_up` to read the mobile field names and map them to the web storage format (`gradeOfAchievement` → `grade`, `perceptionOfTreatment` → `perception`, `followUpDate` → `session_date`, `sessionNumber` → `session_number`, `planForNextTreatment` → `treatment_plan`, `feedback` → `feedback`).

---

## CATEGORY 3 — Critical: SMART Goals (Recent Changes Not Yet Applied to Mobile)

Three files need updating from the web app changes made on 2026-05-05:

**`app/smart-goals.tsx`**
- Interface still has `baselineStatus`, `measurableOutcomes`, `timeDuration` — needs `outcomeTimeframe` instead
- UI still renders 3 old input blocks (Baseline Status, Measurable Outcomes, Time Duration) — needs single "Outcomes & Timeframe" block
- AI mapping still references `baseline_status`, `measurable_outcome`, `time_duration` — update to `outcome_timeframe`
- Pre-existing broken call: `aiSmartGoals(fieldKey, {})` passes a string as `params` — `params.field` is always `undefined`, so all AI calls silently hit the wrong endpoint and fail

**`src/lib/api.ts`**
- `aiSmartGoals` still has stale `patient_goals` field in body
- Needs the call convention fixed: `aiSmartGoals(fieldKey, {})` → `aiSmartGoals({ field: fieldKey, patient_id: patientId, ... })`

**`app/patient-report.tsx`**
- `SmartGoals` interface uses `short_term_goals`, `long_term_goals`, `patient_goals`, `outcome_measures` — none stored by web app
- Should be `patient_goal` and `outcome_timeframe` (2 fields, not 4)

---

## CATEGORY 4 — Missing Feature: Quick Mode

The web app's Quick Mode is a full parallel workflow — 8 dedicated routes:
- `/qm/patho_mechanism`
- `/qm/subjective`
- `/qm/initial_plan`
- `/qm/risk_factors`
- `/qm/objective_assessment`
- `/qm/provisional_diagnosis`
- `/qm/smart_goals`
- `/qm/treatment_plan`

Powered by `quick_mode_service.py` and `quick_mode_prompts.py`. When enabled at patient creation, AI pre-fills every form field before the clinician sees it — they just review and save instead of typing from scratch.

**The mobile app has zero trace of this feature.** This needs to be built end-to-end:
- Quick Mode toggle when creating a patient
- Dedicated QM screens for each step (or a QM flag that pre-populates regular screens)
- API endpoint in `mobile_api.py` to trigger AI pre-fills
- Equivalent of `quick_mode_service.py` logic accessible via mobile API

---

## CATEGORY 5 — Workflow Navigation Bug

**`app/initial-plan.tsx`** — After saving, the `router.push` goes to `/pathophysiological-mechanism` (the screen that runs *before* subjective examination). The correct next step matching the web's step 6 is `/chronic-disease-factors`. This creates a navigation loop.

**Fix:** One-line change — `router.push('/pathophysiological-mechanism?...')` → `router.push('/chronic-disease-factors?...')`

---

## CATEGORY 6 — Assessment Progress Tracker Missing 3 Steps

**`src/lib/assessmentProgress.ts`** — The tracker has 8 steps but 3 existing screens are untracked:
- `pathoMechanism` (screen exists at `/pathophysiological-mechanism`)
- `chronicDiseases` (screen exists at `/chronic-disease-factors`)
- `clinicalFlags` (screen exists at `/clinical-flags`)

The completion percentage is wrong and `getNextIncompleteStep()` skips these screens entirely. Web has 10 steps in total.

**Fix:** Add the 3 steps to `ASSESSMENT_STEPS` array and `PatientAssessmentStatus` interface in the correct order matching the web workflow:

```
1.  basicInfo
2.  pathoMechanism         ← ADD
3.  subjectiveExamination
4.  patientPerspectives
5.  initialPlan
6.  chronicDiseases        ← ADD
7.  clinicalFlags          ← ADD
8.  objectiveAssessment
9.  provisionalDiagnosis
10. smartGoals
11. treatmentPlan
```

---

## CATEGORY 7 — Field Name Mismatches (Data Never Cross-References)

When web clinicians view a mobile patient or vice versa, these fields show blank because field names differ.

### 7.1 Patient Perspectives
| Web field name | Mobile field name |
|---|---|
| `knowledge` | `knowledgeOfIllness` |
| `attribution` | `illnessAttribution` |
| `expectation` | `expectationAboutIllness` |
| `consequences_awareness` | `awarenessOfConsequences` |
| `locus_of_control` | `locusOfControl` |
| `affective_aspect` | `affectiveAspect` |

Mobile also has extra `*Notes` fields for each item that web doesn't have (e.g. `knowledgeOfIllnessNotes`).

### 7.2 Provisional Diagnosis
| Web field name | Mobile field name |
|---|---|
| `likelihood` | `likelihoodOfDiagnosis` |
| `structure_fault` | `possibleStructureAtFault` |
| `symptom` | `symptom` ✓ |
| `findings_support` | `findingsSupportingDiagnosis` |
| `findings_reject` | `findingsRejectingDiagnosis` |
| `hypothesis_supported` | `hypothesisSupported` |

### 7.3 Initial Plan
| Web field name | Mobile field name |
|---|---|
| `active_movements` | `activeMovements` + `activeMovementsSuggestions` + `activeMovementsObservations` |
| `passive_movements` | `passiveMovements` + `passiveMovementsSuggestions` + `passiveMovementsObservations` |
| `passive_over_pressure` | `passiveOverPressure` + `passiveOverPressureSuggestions` + `passiveOverPressureObservations` |
| `resisted_movements` | `resistedMovements` + ... |
| `combined_movements` | `combinedMovements` + ... |
| `special_tests` | `specialTests` + ... |
| `neurodynamic` | `neurodynamicExamination` + ... |

Web uses predefined dropdown values; mobile is free text with extra sub-fields.

### 7.4 Pathophysiological Mechanism
| Web field name | Mobile field name |
|---|---|
| `area_involved` | `areaInvolved` |
| `presenting_symptom` | `presentingSymptom` |
| `pain_type` | `painType` |
| `pain_nature` | `painNature` |
| `pain_severity` | `painSeverity` |
| `pain_irritability` | `painIrritability` |
| `possible_source` | `possibleSourceOfSymptoms` |
| `stage_healing` | `stageOfTissueHealing` |

### 7.5 Clinical Flags
| Web field name | Mobile field name |
|---|---|
| `red_flags` | `redFlag` |
| `orange_flags` | `orangeFlag` |
| `yellow_flags` | `yellowFlag` |
| `black_flags` | `blackFlag` |
| `blue_flags` | `blueFlag` |

### 7.6 Objective Assessment
| Web | Mobile |
|---|---|
| `plan` (dropdown: no_mod / mod / contraindicated) | `plan` (free text string) |
| `plan_details` (textarea) | `assessmentNotes` (textarea) |

Web has per-field AI buttons. Mobile has one AI button for the entire form.

---

## CATEGORY 8 — Production Readiness

**`src/lib/config.ts`** — `console.log` and `console.warn` fire at module load in production, exposing the API base URL and Firebase project ID in device logs. Should be gated with `__DEV__`.

**`src/lib/api.ts`** — 84 `console.log/error/warn` statements throughout. Should be guarded with `__DEV__` checks.

**`package.json`** — App name is still `"bolt-expo-starter"`. Should be `"PhysioPRISM"` to match `app.json`.

---

## Priority Summary

| # | Category | Files affected | Priority |
|---|---|---|---|
| 1 | Data architecture — PATCH vs separate collections | `mobile_api.py` | 🔴 Critical |
| 2 | Follow-up fields entirely lost | `mobile_api.py` | 🔴 Critical |
| 3 | SMART Goals — 3 files (today's web changes) | `app/smart-goals.tsx`, `src/lib/api.ts`, `app/patient-report.tsx` | 🔴 Critical |
| 4 | Quick Mode completely missing | New mobile screens + `mobile_api.py` | 🟠 Major |
| 5 | Initial plan navigation loop | `app/initial-plan.tsx` | 🟠 Major |
| 6 | Progress tracker missing 3 steps | `src/lib/assessmentProgress.ts` | 🟠 Major |
| 7 | 6 screens with mismatched field keys | `mobile_api.py` PATCH handler + mobile screens | 🟡 Significant |
| 8 | Production console leaks + app name | `src/lib/config.ts`, `src/lib/api.ts`, `package.json` | 🟡 Polish |
