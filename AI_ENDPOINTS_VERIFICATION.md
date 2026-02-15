# AI Endpoints Verification

## Frontend → Backend Matching

| Frontend Call (static/main.js) | Backend Route (main.py) | Status |
|--------------------------------|-------------------------|--------|
| `/api/ai_suggestion/past_questions` | `/api/ai_suggestion/past_questions` | ✅ Match |
| `/api/ai_suggestion/provisional_diagnosis` | `/api/ai_suggestion/provisional_diagnosis` | ✅ Match |
| `/api/ai_suggestion/subjective/${field}` | `/api/ai_suggestion/subjective/<field>` | ✅ Match |
| `/api/ai_suggestion/subjective_diagnosis` | `/api/ai_suggestion/subjective_diagnosis` | ✅ Match |
| `/api/ai_suggestion/perspectives/${field}` | `/api/ai_suggestion/perspectives/<field>` | ✅ Match |
| `/api/ai_suggestion/initial_plan/${field}` | `/api/ai_suggestion/initial_plan/<field>` | ✅ Match |
| `/api/ai_suggestion/initial_plan_summary` | `/api/ai_suggestion/initial_plan_summary` | ✅ Match |
| `/api/ai_suggestion/patho/possible_source` | `/api/ai_suggestion/patho/possible_source` | ✅ Match |
| `/api/ai_suggestion/chronic/specific_factors` | `/api/ai_suggestion/chronic/specific_factors` | ✅ Match |
| `/api/ai_suggestion/clinical_flags/${patient_id}/suggest` | `/api/ai_suggestion/clinical_flags/<patient_id>/suggest` | ✅ Match |
| `/api/ai_suggestion/objective_assessment/${field}` | `/api/ai_suggestion/objective_assessment/<field>` | ✅ Match |
| `/api/ai_suggestion/smart_goals/${field}` | `/api/ai_suggestion/smart_goals/<field>` | ✅ Match |
| `/api/ai_suggestion/treatment_plan/${field}` | `/api/ai_suggestion/treatment_plan/<field>` | ✅ Match |
| `/api/ai_suggestion/treatment_plan_summary/${patient_id}` | `/api/ai_suggestion/treatment_plan_summary/<patient_id>` | ✅ Match |
| `/ai/followup_suggestion/${patient_id}` | `/ai/followup_suggestion/<patient_id>` | ⚠️ Legacy endpoint |

## Unused Backend Routes

These routes exist in backend but are not called from frontend:
- `/api/ai_suggestion/perspectives_diagnosis` (diagnosis generation for perspectives)
- `/api/ai_suggestion/followup/<field>` (newer version, not used yet)

## Summary

✅ **All active AI endpoints match correctly between frontend and backend**

⚠️ **One legacy endpoint** (`/ai/followup_suggestion/`) is still in use but works fine

## Recommendation

The legacy followup endpoint works, but consider migrating to the new standardized endpoint in future updates.
