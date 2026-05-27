# GDPR Compliance Documentation
## Data Protection & Right to Erasure

**Last Updated:** May 27, 2026
**Regulation:** GDPR (General Data Protection Regulation) - EU Regulation 2016/679
**Key Articles:** Article 17 (Right to Erasure), Article 5 (Data Minimization)

---

## Overview

PhysiologicPRISM is fully compliant with GDPR requirements for data protection and user privacy. This document outlines our data deletion mechanisms and compliance measures.

## Data Categories Stored

### 1. User Account Data
- Email address (used as unique identifier)
- Name
- Phone number
- Institute affiliation
- Role (admin/staff/physio)
- Account creation timestamp
- Firebase Authentication UID
- Subscription information
- Messaging consent records

### 2. Patient Health Data (PHI/PII)
- Patient demographics (name, age, sex, contact)
- Medical history
- Assessment data (subjective, objective, diagnosis)
- Treatment plans
- Follow-up session records
- Clinical notes and flags
- Chronic disease information
- SMART goals

### 3. System Data
- Form drafts (auto-saved partially completed forms)
- Saved search filters
- AI cache entries (cached AI-generated suggestions)
- AI training data
- Audit logs
- Patient counters (for ID generation)

---

## GDPR Rights Implemented

### ✅ Right to Erasure (Article 17)

Users have two deletion options:

#### Option 1: Individual Patient Deletion
**Scope:** Delete a single patient and all associated data
**Initiated by:** Physiotherapist via UI or API
**Implementation:** See [Patient Deletion Process](#patient-deletion-process)

#### Option 2: Complete Account Deletion
**Scope:** Delete entire user account and ALL associated data
**Initiated by:** User via account settings
**Process:** 7-day grace period, then permanent deletion
**Implementation:** See [Account Deletion Process](#account-deletion-process)

---

## Patient Deletion Process

### What Gets Deleted (GDPR Compliant)

When a patient is deleted via:
- **Web UI:** Patient List → Delete button
- **API:** `DELETE /api/patients/{patient_id}`
- **Script:** `python delete_patient.py {patient_id}`

The following data is **permanently and irreversibly deleted**:

| Data Type | Collection | Deletion Method |
|-----------|-----------|-----------------|
| Patient Record | `patients` | Hard delete |
| Follow-Up Sessions | `follow_ups` | Query by `patient_id`, batch delete |
| Form Drafts | `form_drafts` | Delete all 13+ draft types |
| AI Cache Entries | `ai_cache` | Delete entries containing `patient_id` |
| AI Training Data | `ai_training_data` | Delete entries with matching `patient_id` |

### Code Implementation

**File:** `mobile_api.py:1573-1667`

```python
@mobile_api.route('/patients/<patient_id>', methods=['DELETE'])
@require_auth
def api_delete_patient(patient_id):
    """GDPR-Compliant Patient Deletion"""

    # 1. Delete all follow-ups
    follow_ups = db.collection('follow_ups').where('patient_id', '==', patient_id).stream()
    for follow_up in follow_ups:
        follow_up.reference.delete()

    # 2. Delete all form drafts (13 types)
    for draft_type in ['subjective', 'objective', 'treatment_plan', ...]:
        db.collection('form_drafts').document(f'{draft_type}_{patient_id}').delete()

    # 3. Delete AI cache
    AICache().delete_patient_cache(patient_id)

    # 4. Delete patient record
    db.collection('patients').document(patient_id).delete()
```

### Deletion Confirmation

The system provides:
- **Double confirmation** dialog before deletion
- **Summary of data** to be deleted
- **Irreversibility warning**
- **Audit log** entry of deletion (retains only: user who deleted, timestamp, patient_id, patient_name)

---

## Account Deletion Process

### What Gets Deleted (GDPR Compliant)

When a user requests account deletion:
- User initiates deletion → 7-day grace period → Permanent deletion

The following data is **completely and permanently deleted**:

| Data Type | Collection | Count | Notes |
|-----------|-----------|-------|-------|
| All Patient Records | `patients` | Variable | Includes ALL patients created by user |
| All Follow-Ups | `follow_ups` | Variable | For all user's patients |
| All Form Drafts | `form_drafts` | Variable | All auto-saved forms |
| Saved Searches | `saved_searches` | Variable | User's custom search filters |
| Subscription Data | `subscriptions` | 1 | Payment and quota information |
| Messaging Consent | `messaging_consent` | 1 | SMS/email consent records |
| Consent Audit Trail | `consent_audit_trail` | Variable | Consent change history |
| AI Cache Entries | `ai_cache` | Variable | Cached AI suggestions |
| AI Training Data | `ai_training_data` | Variable | Training examples |
| Patient Counters | `patient_counters` | 1 | Sequential ID counter |
| Firebase Auth User | Firebase Auth | 1 | Authentication credentials |
| User Document | `users` | 1 | Main user record |

### What Is Retained (GDPR Compliant)

Only the minimum data required for **legal compliance and audit purposes**:

| Data Type | Retention | Justification |
|-----------|-----------|---------------|
| Deletion Record | `deleted_users` | GDPR Article 17(3)(e) - Legal claims defense |
| Audit Logs (deletion event) | `audit_logs` | GDPR Article 5(2) - Accountability principle |

**Retention Details:**
```json
{
  "email": "user@example.com",  // For legal identification only
  "deletion_requested_at": "2026-05-20T10:00:00Z",
  "deletion_executed_at": "2026-05-27T10:00:00Z",
  "executed_by": "admin@example.com",
  "deletion_stats": {
    "patients": 15,
    "follow_ups": 42,
    "form_drafts": 38
  }
}
```

**NO patient health data is retained after account deletion.**

### Code Implementation

**File:** `main.py:10064-10231`

```python
@app.route('/super_admin/process_deletion/<user_email>', methods=['POST'])
def super_admin_process_deletion(user_email):
    """GDPR-Compliant Complete Account Deletion"""

    # For each patient:
    for patient in user's patients:
        # Delete follow-ups
        # Delete form drafts
        # Delete AI cache
        # Delete patient record

    # Delete user-level data
    db.collection('saved_searches').where('user_id', '==', user_email).delete()
    db.collection('subscriptions').document(user_email).delete()
    db.collection('messaging_consent').document(user_email).delete()
    db.collection('patient_counters').document(user_email).delete()

    # Delete authentication
    auth.delete_user(firebase_uid)

    # Delete user record
    db.collection('users').document(user_email).delete()
```

---

## Audit Logs and GDPR

### What We Log

Deletion events are logged for **accountability** (GDPR Article 5(2)):

```json
{
  "action": "GDPR Account Deletion Executed",
  "user_id": "admin@example.com",
  "timestamp": "2026-05-27T10:00:00Z",
  "details": "Deleted user user@example.com. Stats: {patients: 15, follow_ups: 42}"
}
```

### What We DO NOT Log

- ❌ Patient health information
- ❌ Medical history or diagnoses
- ❌ Contact information of deleted patients
- ❌ Assessment details
- ❌ Treatment plans

Only **metadata** (counts, IDs, timestamps) is retained for audit purposes.

---

## Data Retention Periods

| Data Category | Retention Period | GDPR Justification |
|---------------|------------------|-------------------|
| Active Patient Records | Until deleted by physio | Consent (Article 6(1)(a)) |
| Active User Accounts | Until deletion requested | Consent (Article 6(1)(a)) |
| Deletion Audit Records | 7 years | Legal obligation (Article 17(3)(e)) |
| Form Drafts | 90 days (auto-cleanup) | Data minimization (Article 5(1)(c)) |
| AI Cache | 90 days (auto-expire) | Data minimization (Article 5(1)(c)) |

---

## Data Minimization (Article 5)

### Automatic Cleanup

1. **Form Drafts:** Deleted after 90 days of inactivity
   - **File:** `main.py` - `/cleanup_old_drafts` cron job
   - **Schedule:** Daily at 2 AM

2. **AI Cache:** Expired after 90 days
   - **File:** `ai_cache.py` - `cleanup_expired_cache()`
   - **Schedule:** Daily

3. **Temporary Tokens:** Expired after 24 hours
   - **Collection:** `password_reset_tokens`
   - **Auto-cleanup:** On use or expiry

---

## User Rights Implementation

### Right to Access (Article 15)
- **Implementation:** Patient Report feature (`/patient_report`)
- **Format:** Comprehensive PDF with all patient data
- **Scope:** Individual patient or all patients

### Right to Rectification (Article 16)
- **Implementation:** Edit Patient feature (`/edit_patient`)
- **Scope:** All patient fields editable by physio

### Right to Data Portability (Article 20)
- **Implementation:** Export feature (planned)
- **Format:** JSON export of patient data
- **Status:** Roadmap for Q3 2026

### Right to Erasure (Article 17)
- **Implementation:** This document ✅
- **Status:** Fully implemented

---

## Technical Safeguards

### Deletion Verification

1. **Idempotency:** Deletion endpoints can be called multiple times safely
2. **Cascade Delete:** All related data automatically deleted
3. **Batch Operations:** Large deletions use Firestore batching (500 ops/batch)
4. **Error Handling:** Partial failures logged, deletion continues
5. **Audit Trail:** Every deletion logged with summary statistics

### Security

- **Ownership Verification:** Users can only delete their own data
- **Admin Override:** Super admins can process deletion requests
- **Double Confirmation:** UI requires two confirmations for deletion
- **Grace Period:** 7-day waiting period for account deletion

---

## Compliance Checklist

- ✅ **Patient Deletion:** Complete erasure of all patient data
- ✅ **Account Deletion:** Complete erasure of all user data
- ✅ **Audit Logging:** Minimal metadata retained for legal compliance
- ✅ **Data Minimization:** Automatic cleanup of temporary data
- ✅ **User Consent:** Explicit consent required for data processing
- ✅ **Access Control:** Role-based access to data
- ✅ **Encryption:** Data encrypted in transit (HTTPS) and at rest (Cosmos DB)
- ✅ **Data Portability:** Patient reports exportable as PDF
- ⚠️ **JSON Export:** Planned for Q3 2026

---

## Code References

### Patient Deletion
- **API Endpoint:** `mobile_api.py:1573-1667`
- **UI Component:** `templates/view_patients.html:482` (Delete button)
- **CLI Tool:** `delete_patient.py`

### Account Deletion
- **Request:** `main.py` - `/request_account_deletion`
- **Execution:** `main.py:10064-10231`
- **Grace Period:** 7 days (configurable)

### AI Cache Deletion
- **Patient Cache:** `ai_cache.py:630-704`
- **User Cache:** `ai_cache.py:588-627`
- **Training Data:** `ai_cache.py:707-742`

---

## Contact

For GDPR compliance questions or data deletion requests:

- **Email:** privacy@physiologicprism.com
- **DPO (Data Protection Officer):** Dr. Sandy (drsandy28783@gmail.com)
- **Response Time:** Within 30 days (GDPR requirement)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-27 | Initial GDPR compliance implementation |
| - | - | Complete data deletion for patients and users |
| - | - | AI cache deletion added |
| - | - | Audit logging implemented |

---

**Last Reviewed:** May 27, 2026
**Next Review:** August 27, 2026 (Quarterly)
