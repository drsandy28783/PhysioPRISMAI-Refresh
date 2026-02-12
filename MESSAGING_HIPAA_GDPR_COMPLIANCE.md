# SMS & WhatsApp Messaging - HIPAA & GDPR Compliance Guide

## Overview

This document outlines how PhysiologicPRISM's messaging implementation complies with HIPAA (Health Insurance Portability and Accountability Act) and GDPR (General Data Protection Regulation) requirements.

---

## Table of Contents

1. [HIPAA Compliance](#hipaa-compliance)
2. [GDPR Compliance](#gdpr-compliance)
3. [Technical Safeguards](#technical-safeguards)
4. [Data Minimization](#data-minimization)
5. [User Rights](#user-rights)
6. [Audit Trail](#audit-trail)
7. [Twilio BAA Setup](#twilio-baa-setup)
8. [Compliance Checklist](#compliance-checklist)

---

## HIPAA Compliance

### Business Associate Agreement (BAA)

**REQUIRED:** You must sign a Business Associate Agreement with Twilio before using their services for healthcare communication.

#### Steps to Sign Twilio BAA:

1. **Log into Twilio Console**: https://www.twilio.com/console
2. **Navigate to Settings**: Account > General Settings
3. **Request BAA**: Click "Request HIPAA compliance" button
4. **Complete Form**: Provide business information
5. **Sign Agreement**: DocuSign will be sent to authorized signer
6. **Enable HIPAA Mode**: After signing, enable HIPAA Eligible products

**Cost:** FREE (but requires a paid Twilio account, not trial)

**Timeline:** 1-3 business days for approval

### PHI Protection in Messages

**CRITICAL RULE: NEVER send Protected Health Information (PHI) via SMS/WhatsApp**

#### What is PHI?

Protected Health Information includes:
- Patient names
- Medical conditions or diagnoses
- Treatment details
- Medication names
- Appointment specifics (doctor name, location, reason)
- Test results
- Any identifiable health information

#### Our Implementation: PHI-Safe Messages

✅ **COMPLIANT - Generic Messages with Deep Links:**

```
"You have an appointment in 24 hours. Open PhysiologicPRISM to view details: https://app.com/appointments/abc123"
```

```
"Reminder: You have a pending follow-up. Check your app for details: https://app.com/follow-ups"
```

```
"Your PhysiologicPRISM subscription expires in 3 days. Renew now: https://app.com/subscription"
```

❌ **NON-COMPLIANT - PHI in Messages:**

```
"Hi John, your physiotherapy appointment with Dr. Smith for lower back pain is tomorrow at 2pm at ABC Clinic"
```

```
"Reminder: Take your prescribed medication (Ibuprofen 400mg) three times daily"
```

### All Templates Are Pre-Configured to be PHI-Safe

All message templates in `message_templates.py` follow HIPAA guidelines:
- No patient names
- No medical conditions
- No specific appointment details
- Generic text with secure app links
- All sensitive data viewed only in app (encrypted, authenticated)

---

## GDPR Compliance

### 1. Lawful Basis for Processing

**Our Basis: Explicit Consent**

Users must explicitly opt-in to receive SMS/WhatsApp messages.

#### Implementation:

- ✅ **Opt-in Required**: Users cannot receive messages without consent
- ✅ **Granular Consent**: Separate opt-ins for SMS, WhatsApp, and marketing
- ✅ **Consent Tracking**: Timestamp, IP address, and source recorded
- ✅ **Easy Opt-out**: Reply "STOP" anytime
- ✅ **Consent Audit Trail**: All changes logged

**Code:** `consent_manager.py`

### 2. Data Minimization

We collect and store only the minimum necessary data:

#### What We Store:

```python
{
    'user_id': 'user@example.com',
    'phone_number': '+919876543210',  # Encrypted at rest
    'sms_consent': True,
    'whatsapp_consent': True,
    'marketing_consent': False,
    'consent_date': '2026-02-12',
    'consent_ip': '192.168.1.1',  # For audit trail
    'consent_source': 'app_settings'
}
```

#### What We DON'T Store:

- ❌ Full message content (only preview for 90 days)
- ❌ Full phone numbers in logs (only last 4 digits)
- ❌ Message content after retention period
- ❌ Any PHI in any form

### 3. Data Retention & Right to Erasure

#### Automatic Deletion:

| Data Type | Retention Period | Cleanup Job |
|-----------|------------------|-------------|
| Message logs | 90 days | Daily cron |
| OTP codes | 24 hours | Every 6 hours |
| Incoming messages | 90 days | Daily cron |
| Reminder logs | 180 days | Daily cron |

#### User Rights Implementation:

**Right to Access:**
```python
# Get all messaging data for a user
consent_data = ConsentManager.get_consent(user_id)
message_history = MessagingService.get_message_history(user_id)
consent_history = ConsentManager.get_consent_history(user_id)
```

**Right to Erasure (Right to be Forgotten):**
```python
# Delete all messaging data
ConsentManager.delete_consent_data(user_id)
# Also deletes: message logs, consent history, incoming messages
```

**Code:** `messaging_cleanup_jobs.py`, `consent_manager.py`

### 4. Opt-Out Mechanism

#### Multiple Ways to Opt-Out:

1. **Reply STOP**: Automatic processing via Twilio webhook
2. **App Settings**: In-app toggle for SMS/WhatsApp
3. **Web Dashboard**: Messaging preferences page
4. **Support Request**: Contact support to opt-out

#### Opt-Out Keywords (Twilio Standard):

- STOP
- STOPALL
- UNSUBSCRIBE
- CANCEL
- END
- QUIT

**Code:** `messaging_webhooks.py`

### 5. Transparency & Privacy Policy

**REQUIRED:** Your Privacy Policy must disclose:

1. What messaging data you collect
2. How you use it
3. Third-party service provider (Twilio)
4. How to opt-out
5. Data retention periods
6. User rights (access, deletion, portability)

**Template Section for Privacy Policy:**

```markdown
## SMS and WhatsApp Messaging

We may send you appointment reminders, important account notifications, and service updates via SMS or WhatsApp.

**What We Collect:**
- Your phone number
- Messaging preferences (opt-in/opt-out status)
- Delivery status of messages

**Third-Party Provider:**
We use Twilio, Inc. for message delivery. Twilio has signed a Business Associate Agreement (HIPAA) and is GDPR-compliant.

**Your Rights:**
- Opt-out anytime by replying STOP
- Request your messaging data
- Request deletion of your messaging data
- Messages are deleted after 90 days

**Data Security:**
We NEVER send your medical information via SMS/WhatsApp. All sensitive data is accessed only through our secure, encrypted app.
```

---

## Technical Safeguards

### 1. Encryption

- **In Transit**: TLS 1.2+ for all Twilio API calls
- **At Rest**: Azure Cosmos DB encryption
- **Phone Numbers**: Encrypted at rest, only last 4 digits logged

### 2. Authentication

- **Webhook Signature Verification**: All incoming Twilio webhooks verified
- **API Authentication**: Bearer tokens for all API calls
- **Rate Limiting**: Prevents abuse and spam

### 3. Access Controls

- **Role-Based Access**: Only authorized users can manage messaging
- **Admin Audit**: All messaging configuration changes logged
- **Consent Required**: Cannot send without explicit opt-in

### 4. Logging & Monitoring

- **HIPAA-Safe Logging**: No PHI in logs, phone numbers masked
- **Sentry Integration**: Errors tracked with PHI sanitization
- **Delivery Tracking**: Message status monitored for failures

**Code:** `twilio_provider.py`, `messaging_service.py`

---

## Data Minimization

### Message Log Storage

**What We Store:**
```python
{
    'user_id': 'user@example.com',
    'phone_number': '****5678',  # Only last 4 digits
    'message_preview': 'You have an appointment in 24 hours...',  # First 50 chars
    'template_name': 'APPOINTMENT_REMINDER_24H',
    'channel': 'whatsapp',
    'status': 'delivered',
    'created_at': '2026-02-12T10:30:00Z',
    'retention_days': 90
}
```

**What We DON'T Store:**
- ❌ Full message text (only preview)
- ❌ Full phone number (masked)
- ❌ Any PHI
- ❌ Messages older than 90 days (auto-deleted)

### OTP Code Storage

OTP codes are:
- ✅ Stored temporarily (10 minutes validity)
- ✅ Deleted within 24 hours
- ✅ Single-use (marked as used after verification)
- ✅ Rate-limited (max 3 attempts)

**Code:** `messaging_service.py`

---

## User Rights

### Right to Access (GDPR Article 15)

Users can request all their messaging data:

```python
GET /api/messaging/my-data

Returns:
{
    'consent': { ... },
    'message_history': [ ... ],
    'consent_history': [ ... ]
}
```

### Right to Rectification (GDPR Article 16)

Users can update their phone number and preferences:

```python
PUT /api/messaging/preferences
{
    'phone_number': '+919876543210',
    'sms_consent': true,
    'whatsapp_consent': true
}
```

### Right to Erasure (GDPR Article 17)

Users can request deletion of all messaging data:

```python
DELETE /api/messaging/my-data

Deletes:
- Consent record
- Message history
- Incoming messages
- Consent audit trail
```

### Right to Data Portability (GDPR Article 20)

Users can export their messaging data in JSON format:

```python
GET /api/messaging/export

Returns: JSON file with all messaging data
```

---

## Audit Trail

### Consent Changes

Every consent change is logged:

```python
{
    'user_id': 'user@example.com',
    'action': 'opt_out',
    'old_consent': {'sms_consent': true},
    'new_consent': {'sms_consent': false},
    'source': 'sms_reply',
    'timestamp': '2026-02-12T10:30:00Z'
}
```

### Message Delivery

Every message sent is logged:

```python
{
    'user_id': 'user@example.com',
    'template_name': 'APPOINTMENT_REMINDER_24H',
    'channel': 'whatsapp',
    'status': 'delivered',
    'created_at': '2026-02-12T10:30:00Z'
}
```

**Code:** `consent_manager.py`, `messaging_service.py`

---

## Twilio BAA Setup

### Step-by-Step Guide

#### 1. Sign Up for Twilio

1. Go to https://www.twilio.com/try-twilio
2. Complete registration
3. Verify your email and phone
4. Add payment method (BAA requires paid account)

#### 2. Request BAA

1. Log into Twilio Console: https://www.twilio.com/console
2. Go to **Account** > **General Settings**
3. Scroll to **HIPAA Compliance**
4. Click **"Request HIPAA compliance"**
5. Fill out business information form
6. Submit request

#### 3. Sign BAA via DocuSign

1. Check email for DocuSign invitation
2. Review BAA terms
3. Sign electronically
4. Wait for Twilio countersignature (1-3 business days)

#### 4. Enable HIPAA Mode

1. After BAA is fully executed, return to Twilio Console
2. Go to **Settings** > **General**
3. Enable **"HIPAA Eligible Products"** toggle
4. Confirm all services are HIPAA-compliant

#### 5. Configure Webhooks (IMPORTANT)

1. Go to **Phone Numbers** > **Manage** > **Active Numbers**
2. Select your SMS phone number
3. Under **Messaging**:
   - **A Message Comes In**: `https://yourdomain.com/webhooks/twilio/incoming`
   - **Status Callback URL**: `https://yourdomain.com/webhooks/twilio/status`
4. Select your WhatsApp number
5. Repeat webhook configuration

#### 6. Test in Sandbox Mode

Before going live, test in Twilio WhatsApp Sandbox:

1. Go to **Messaging** > **Try it out** > **Send a WhatsApp message**
2. Follow instructions to join sandbox
3. Send test WhatsApp from your number
4. Verify webhooks work correctly

---

## Compliance Checklist

### Before Launch

#### Legal & Agreements

- [ ] Sign Twilio Business Associate Agreement (BAA)
- [ ] Update Privacy Policy with messaging disclosure
- [ ] Update Terms of Service with messaging terms
- [ ] Consult legal counsel on compliance

#### Technical Setup

- [ ] Enable HIPAA mode in Twilio Console
- [ ] Configure Twilio webhooks
- [ ] Set `MESSAGING_ENABLED=true` in `.env`
- [ ] Set `MESSAGING_MOCK_MODE=false` in `.env`
- [ ] Add Twilio credentials to environment variables
- [ ] Test message sending and delivery
- [ ] Test opt-out flow (reply STOP)
- [ ] Test opt-in flow (reply START)

#### Data Protection

- [ ] Verify all templates are PHI-safe (no patient data)
- [ ] Set up daily cleanup cron job
- [ ] Configure data retention periods
- [ ] Enable encryption at rest (Azure Cosmos DB)
- [ ] Enable TLS 1.2+ for API calls
- [ ] Test webhook signature verification

#### User Rights

- [ ] Implement consent management UI
- [ ] Test data export functionality
- [ ] Test data deletion functionality
- [ ] Create user-facing documentation

#### Monitoring & Audit

- [ ] Enable Sentry error tracking with PHI sanitization
- [ ] Set up Twilio usage alerts
- [ ] Configure delivery failure notifications
- [ ] Test audit trail logging

---

## Important Notes

### ⚠️ NEVER Send PHI

**THIS IS THE MOST CRITICAL RULE:**

- ❌ NEVER send patient names in messages
- ❌ NEVER send medical conditions
- ❌ NEVER send diagnoses or treatment details
- ❌ NEVER send appointment specifics
- ❌ NEVER send any identifiable health information

**✅ ALWAYS:**
- Use generic message templates
- Include secure app deep links
- Require login to view sensitive data
- Keep all PHI inside the encrypted app

### 🔒 Security Best Practices

1. **Rotate API Keys**: Rotate Twilio credentials every 90 days
2. **Monitor Usage**: Set up alerts for unusual sending patterns
3. **Rate Limiting**: Prevent spam and abuse
4. **Webhook Security**: Always verify Twilio signatures
5. **Incident Response**: Have a plan for data breaches

### 📊 Regular Compliance Audits

Conduct quarterly compliance reviews:

1. **Review message templates** - Ensure no PHI creep
2. **Audit consent records** - Verify opt-in/opt-out flow
3. **Check data retention** - Confirm auto-deletion working
4. **Test user rights** - Verify export/deletion functions
5. **Review logs** - Check for PHI in error logs

---

## Support & Resources

### Twilio Resources

- Twilio HIPAA Compliance: https://www.twilio.com/legal/hipaa
- Twilio BAA Request: https://www.twilio.com/console
- Twilio Security: https://www.twilio.com/security

### HIPAA Resources

- HHS HIPAA Portal: https://www.hhs.gov/hipaa
- HIPAA Privacy Rule: https://www.hhs.gov/hipaa/for-professionals/privacy
- HIPAA Breach Notification: https://www.hhs.gov/hipaa/for-professionals/breach-notification

### GDPR Resources

- GDPR Official Text: https://gdpr-info.eu/
- Data Protection: https://gdpr.eu/
- User Rights: https://gdpr.eu/right-to-be-forgotten/

---

## Contact

For questions about messaging compliance:
- Technical: Check code documentation in each module
- Legal: Consult your legal counsel
- Twilio Support: https://support.twilio.com/

**Last Updated:** February 2026
**Review Frequency:** Quarterly
**Next Review:** May 2026
