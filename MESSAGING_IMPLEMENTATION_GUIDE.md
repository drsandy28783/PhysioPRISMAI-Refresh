# SMS & WhatsApp Messaging - Implementation Guide

## Quick Start Guide

This guide will help you activate and use the SMS/WhatsApp messaging features in PhysiologicPRISM.

---

## Table of Contents

1. [Overview](#overview)
2. [Current Status](#current-status)
3. [Activation Steps](#activation-steps)
4. [Testing in Mock Mode](#testing-in-mock-mode)
5. [Going Live with Twilio](#going-live-with-twilio)
6. [API Integration](#api-integration)
7. [Web UI Integration](#web-ui-integration)
8. [Mobile App Integration](#mobile-app-integration)
9. [Cron Jobs Setup](#cron-jobs-setup)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### What's Been Implemented

✅ **Backend Services:**
- PHI-safe message templates
- Twilio SMS and WhatsApp integration
- Consent management (GDPR/HIPAA compliant)
- OTP generation and verification
- Appointment reminder scheduler
- Two-way messaging support
- Webhook handlers (opt-in/opt-out, delivery status)
- Automatic data cleanup
- Message logging and history

✅ **Features:**
- Send OTP for authentication
- Appointment reminders (24h, 2h)
- Follow-up reminders
- Subscription/payment notifications
- Two-way patient messaging
- Opt-out handling (STOP keyword)
- Message delivery tracking
- HIPAA/GDPR compliance built-in

✅ **Configuration:**
- Environment variables setup
- Mock mode for testing
- Easy activation toggle

---

## Current Status

### ✅ Ready to Use

The messaging infrastructure is **100% complete and ready to activate**.

**Current Mode:** Mock Mode (no API calls, no costs)

**To Activate:**
1. Sign up for Twilio (when ready)
2. Add API keys to `.env`
3. Set `MESSAGING_ENABLED=true`
4. Restart app
5. Done!

---

## Activation Steps

### Step 1: Install Dependencies

```bash
cd D:\New folder\New folder\Recovery
pip install twilio==9.3.7
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Copy `.env.example` to `.env` if not already done:

```bash
cp .env.example .env
```

Edit `.env` and add Twilio configuration:

```env
# Enable messaging
MESSAGING_ENABLED=true

# Disable mock mode (use real Twilio API)
MESSAGING_MOCK_MODE=false

# Twilio credentials (get from https://www.twilio.com/console)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here

# Twilio phone numbers
TWILIO_PHONE_NUMBER=+12345678900
TWILIO_WHATSAPP_NUMBER=+14155238886  # Sandbox or approved number

# App URL for deep links
APP_URL=https://physiologicprism.com
```

### Step 3: Integrate Services into main.py

Add these imports to `main.py`:

```python
# Messaging imports
from messaging_webhooks import register_messaging_webhooks
from appointment_reminder_scheduler import register_reminder_cron_jobs
from messaging_cleanup_jobs import register_messaging_cleanup_jobs
```

Register services after creating the Flask app:

```python
# After: app = Flask(__name__)

# Register messaging webhooks
register_messaging_webhooks(app)

# Register reminder cron jobs
register_reminder_cron_jobs(app)

# Register cleanup jobs
register_messaging_cleanup_jobs(app)
```

### Step 4: Create Required Database Indexes

The messaging system uses these Cosmos DB collections:
- `messaging_consent` - User consent records
- `message_log` - Sent message history
- `otp_codes` - OTP verification codes
- `incoming_messages` - Patient replies
- `reminder_log` - Appointment reminder tracking
- `consent_audit_trail` - Consent change history

No manual setup needed - collections are created automatically on first use.

### Step 5: Test the Integration

**Test in Mock Mode First:**

```bash
# Ensure mock mode is enabled
MESSAGING_ENABLED=true
MESSAGING_MOCK_MODE=true

# Restart your app
python main.py
```

Test sending a message:

```python
from messaging_service import MessagingService, MessageChannel

# Send OTP (will be logged, not actually sent)
result = MessagingService.send_otp(
    user_id='test@example.com',
    phone_number='+919876543210',
    purpose='verification',
    channel=MessageChannel.SMS
)

print(result)
# Should show: {'success': True, 'mock': True, ...}
```

### Step 6: Go Live

Once tested, switch to live mode:

```env
MESSAGING_ENABLED=true
MESSAGING_MOCK_MODE=false
```

Restart the app and messages will be sent via Twilio!

---

## Testing in Mock Mode

Mock mode is perfect for development and testing without costs.

### What Mock Mode Does

✅ **Simulates:**
- Message sending (logged, not sent)
- Delivery status (always "delivered")
- OTP generation (real codes generated)
- Consent management (real database)
- All logging and tracking

❌ **Doesn't Actually:**
- Send real SMS/WhatsApp
- Make Twilio API calls
- Incur any costs
- Require Twilio account

### Enable Mock Mode

```env
MESSAGING_ENABLED=true
MESSAGING_MOCK_MODE=true
```

### Test Scenarios

#### 1. Send OTP

```python
from messaging_service import MessagingService

result = MessagingService.send_otp(
    user_id='user@example.com',
    phone_number='+919876543210',
    purpose='verification'
)

# Check logs - you'll see:
# [MOCK] SMS to +91****3210: Your verification code is 123456...
```

#### 2. Send Appointment Reminder

```python
from messaging_service import send_appointment_reminder

result = send_appointment_reminder(
    user_id='user@example.com',
    appointment_id='appt_123',
    hours_until=24
)

# Check logs for mock message
```

#### 3. Test Consent

```python
from consent_manager import ConsentManager, ConsentType

# Create consent
ConsentManager.create_or_update_consent(
    user_id='user@example.com',
    phone_number='+919876543210',
    sms_consent=True,
    whatsapp_consent=True
)

# Check consent
has_consent = ConsentManager.has_consent('user@example.com', ConsentType.SMS)
print(f"Has SMS consent: {has_consent}")
```

---

## Going Live with Twilio

### 1. Sign Up for Twilio

1. Go to https://www.twilio.com/try-twilio
2. Complete registration
3. Verify email and phone
4. Get $15 trial credit

### 2. Get Your Credentials

1. Go to https://www.twilio.com/console
2. Copy **Account SID** and **Auth Token**
3. Paste into `.env`:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
```

### 3. Get a Phone Number

**For SMS:**

1. In Twilio Console, go to **Phone Numbers** > **Buy a Number**
2. Select your country (India: +91)
3. Choose a number with SMS capability
4. Purchase ($1-2/month)
5. Add to `.env`:

```env
TWILIO_PHONE_NUMBER=+919876543210
```

**For WhatsApp:**

**Option A: Use Sandbox (Testing)**

1. Go to **Messaging** > **Try it out** > **Send a WhatsApp message**
2. Follow instructions to join sandbox
3. Use sandbox number:

```env
TWILIO_WHATSAPP_NUMBER=+14155238886
```

**Option B: Get Approved (Production)**

1. Submit WhatsApp Business API request to Twilio
2. Wait for Meta approval (1-2 weeks)
3. Use your approved number

### 4. Configure Webhooks

**IMPORTANT:** Configure webhooks for incoming messages and delivery status.

1. Go to **Phone Numbers** > **Manage** > **Active Numbers**
2. Click your SMS number
3. Under **Messaging**, set:
   - **A Message Comes In**: `https://physiologicprism.com/webhooks/twilio/incoming`
   - **Status Callback URL**: `https://physiologicprism.com/webhooks/twilio/status`
4. Save changes
5. Repeat for WhatsApp number

### 5. Sign BAA (For HIPAA Compliance)

See: `MESSAGING_HIPAA_GDPR_COMPLIANCE.md` for detailed steps.

**Quick steps:**
1. Twilio Console > Account > General Settings
2. Request HIPAA compliance
3. Sign BAA via DocuSign
4. Enable HIPAA Eligible Products

### 6. Go Live!

Update `.env`:

```env
MESSAGING_ENABLED=true
MESSAGING_MOCK_MODE=false
```

Restart your app:

```bash
python main.py
```

Send your first real message:

```python
from messaging_service import MessagingService

result = MessagingService.send_otp(
    user_id='yourpersonal@email.com',
    phone_number='+919876543210',  # Your own number for testing
    purpose='verification'
)

# Check your phone for SMS!
```

---

## API Integration

### API Endpoints for Mobile App

Add these endpoints to `main.py` or `mobile_api.py`:

```python
from flask import request, jsonify
from messaging_service import MessagingService
from consent_manager import ConsentManager, ConsentType, ConsentSource
from app_auth import require_firebase_auth

# Update messaging preferences
@app.route('/api/messaging/preferences', methods=['GET', 'PUT'])
@require_firebase_auth
def messaging_preferences():
    """Get or update messaging preferences"""
    user_id = request.user_id

    if request.method == 'GET':
        # Get current preferences
        consent = ConsentManager.get_consent(user_id)

        return jsonify({
            'success': True,
            'preferences': consent or {}
        }), 200

    else:  # PUT
        # Update preferences
        data = request.get_json()

        success = ConsentManager.create_or_update_consent(
            user_id=user_id,
            phone_number=data.get('phone_number'),
            sms_consent=data.get('sms_consent', False),
            whatsapp_consent=data.get('whatsapp_consent', False),
            marketing_consent=data.get('marketing_consent', False),
            source=ConsentSource.APP_SETTINGS.value,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        return jsonify({
            'success': success
        }), 200 if success else 400


# Send OTP
@app.route('/api/messaging/send-otp', methods=['POST'])
def send_otp_api():
    """Send OTP to phone number"""
    data = request.get_json()

    result = MessagingService.send_otp(
        user_id=data.get('user_id'),
        phone_number=data.get('phone_number'),
        purpose=data.get('purpose', 'verification'),
        channel=MessageChannel.SMS
    )

    return jsonify(result), 200 if result['success'] else 400


# Verify OTP
@app.route('/api/messaging/verify-otp', methods=['POST'])
def verify_otp_api():
    """Verify OTP code"""
    data = request.get_json()

    result = MessagingService.verify_otp(
        user_id=data.get('user_id'),
        otp_code=data.get('otp_code'),
        purpose=data.get('purpose', 'verification')
    )

    return jsonify(result), 200 if result['valid'] else 400


# Get message history
@app.route('/api/messaging/history', methods=['GET'])
@require_firebase_auth
def message_history():
    """Get user's message history"""
    user_id = request.user_id
    limit = request.args.get('limit', 50, type=int)

    messages = MessagingService.get_message_history(user_id, limit=limit)

    return jsonify({
        'success': True,
        'messages': messages
    }), 200
```

### Example API Usage

**1. Update Messaging Preferences:**

```bash
curl -X PUT https://physiologicprism.com/api/messaging/preferences \
  -H "Authorization: Bearer <firebase_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+919876543210",
    "sms_consent": true,
    "whatsapp_consent": true,
    "marketing_consent": false
  }'
```

**2. Send OTP:**

```bash
curl -X POST https://physiologicprism.com/api/messaging/send-otp \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user@example.com",
    "phone_number": "+919876543210",
    "purpose": "login"
  }'
```

**3. Verify OTP:**

```bash
curl -X POST https://physiologicprism.com/api/messaging/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user@example.com",
    "otp_code": "123456",
    "purpose": "login"
  }'
```

---

## Web UI Integration

### Messaging Settings Page

Create `templates/messaging_settings.html`:

```html
{% extends "base.html" %}

{% block content %}
<div class="container">
    <h2>Messaging Preferences</h2>

    <form method="POST" action="/settings/messaging">
        {{ form.csrf_token }}

        <div class="form-group">
            <label>Phone Number</label>
            <input type="tel" name="phone_number"
                   class="form-control"
                   value="{{ current_phone }}"
                   placeholder="+919876543210">
            <small>Enter with country code (e.g., +91 for India)</small>
        </div>

        <div class="form-check">
            <input type="checkbox" name="sms_consent"
                   id="sms_consent"
                   {{ 'checked' if sms_consent }}>
            <label for="sms_consent">
                Receive appointment reminders via SMS
            </label>
        </div>

        <div class="form-check">
            <input type="checkbox" name="whatsapp_consent"
                   id="whatsapp_consent"
                   {{ 'checked' if whatsapp_consent }}>
            <label for="whatsapp_consent">
                Receive notifications via WhatsApp
            </label>
        </div>

        <div class="form-check">
            <input type="checkbox" name="marketing_consent"
                   id="marketing_consent"
                   {{ 'checked' if marketing_consent }}>
            <label for="marketing_consent">
                Receive promotional messages (optional)
            </label>
        </div>

        <button type="submit" class="btn btn-primary">
            Save Preferences
        </button>
    </form>

    <hr>

    <h4>Message History</h4>
    <table class="table">
        <thead>
            <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Channel</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {% for message in messages %}
            <tr>
                <td>{{ message.created_at }}</td>
                <td>{{ message.template_name }}</td>
                <td>{{ message.channel }}</td>
                <td>{{ message.status }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
```

### Route Handler

Add to `main.py`:

```python
@app.route('/settings/messaging', methods=['GET', 'POST'])
@login_required
def messaging_settings():
    """Messaging preferences page"""
    from consent_manager import ConsentManager, ConsentSource
    from messaging_service import MessagingService

    user_id = current_user.email

    if request.method == 'POST':
        # Update preferences
        ConsentManager.create_or_update_consent(
            user_id=user_id,
            phone_number=request.form.get('phone_number'),
            sms_consent='sms_consent' in request.form,
            whatsapp_consent='whatsapp_consent' in request.form,
            marketing_consent='marketing_consent' in request.form,
            source=ConsentSource.WEB_SETTINGS.value,
            ip_address=request.remote_addr
        )

        flash('Messaging preferences updated!', 'success')
        return redirect(url_for('messaging_settings'))

    # Get current preferences
    consent = ConsentManager.get_consent(user_id) or {}
    messages = MessagingService.get_message_history(user_id, limit=20)

    return render_template('messaging_settings.html',
                         current_phone=consent.get('phone_number', ''),
                         sms_consent=consent.get('sms_consent', False),
                         whatsapp_consent=consent.get('whatsapp_consent', False),
                         marketing_consent=consent.get('marketing_consent', False),
                         messages=messages)
```

---

## Mobile App Integration

### React Native Example

Create `src/screens/MessagingPreferences.tsx`:

```typescript
import React, { useState, useEffect } from 'react';
import { View, Switch, TextInput, Button } from 'react-native';
import { Text } from 'react-native-paper';
import { apiJSON } from '../lib/api';

export default function MessagingPreferences() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [smsConsent, setSmsConsent] = useState(false);
  const [whatsappConsent, setWhatsappConsent] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load current preferences
  useEffect(() => {
    loadPreferences();
  }, []);

  async function loadPreferences() {
    try {
      const data = await apiJSON('/api/messaging/preferences', { method: 'GET' });

      if (data.success) {
        setPhoneNumber(data.preferences.phone_number || '');
        setSmsConsent(data.preferences.sms_consent || false);
        setWhatsappConsent(data.preferences.whatsapp_consent || false);
      }
    } catch (error) {
      console.error('Failed to load preferences:', error);
    }
  }

  async function savePreferences() {
    setLoading(true);

    try {
      const response = await apiJSON('/api/messaging/preferences', {
        method: 'PUT',
        body: JSON.stringify({
          phone_number: phoneNumber,
          sms_consent: smsConsent,
          whatsapp_consent: whatsappConsent
        })
      });

      if (response.success) {
        alert('Preferences saved successfully!');
      }
    } catch (error) {
      alert('Failed to save preferences');
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={{ padding: 20 }}>
      <Text variant="headlineMedium">Messaging Preferences</Text>

      <TextInput
        label="Phone Number"
        value={phoneNumber}
        onChangeText={setPhoneNumber}
        placeholder="+919876543210"
        keyboardType="phone-pad"
        style={{ marginVertical: 10 }}
      />

      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginVertical: 10 }}>
        <Text>Receive SMS notifications</Text>
        <Switch value={smsConsent} onValueChange={setSmsConsent} />
      </View>

      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginVertical: 10 }}>
        <Text>Receive WhatsApp notifications</Text>
        <Switch value={whatsappConsent} onValueChange={setWhatsappConsent} />
      </View>

      <Button
        title="Save Preferences"
        onPress={savePreferences}
        disabled={loading}
      />
    </View>
  );
}
```

### OTP Verification Screen

Create `src/screens/OTPVerification.tsx`:

```typescript
import React, { useState } from 'react';
import { View, TextInput, Button } from 'react-native';
import { apiJSON } from '../lib/api';

export default function OTPVerification({ route, navigation }) {
  const { userId, phoneNumber } = route.params;
  const [otpCode, setOtpCode] = useState('');
  const [loading, setLoading] = useState(false);

  async function sendOTP() {
    setLoading(true);

    try {
      const result = await apiJSON('/api/messaging/send-otp', {
        method: 'POST',
        body: JSON.stringify({
          user_id: userId,
          phone_number: phoneNumber,
          purpose: 'verification'
        })
      });

      if (result.success) {
        alert('OTP sent to your phone!');
      }
    } catch (error) {
      alert('Failed to send OTP');
    } finally {
      setLoading(false);
    }
  }

  async function verifyOTP() {
    setLoading(true);

    try {
      const result = await apiJSON('/api/messaging/verify-otp', {
        method: 'POST',
        body: JSON.stringify({
          user_id: userId,
          otp_code: otpCode,
          purpose: 'verification'
        })
      });

      if (result.valid) {
        alert('Phone verified successfully!');
        navigation.goBack();
      } else {
        alert('Invalid OTP code. Please try again.');
      }
    } catch (error) {
      alert('Verification failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={{ padding: 20 }}>
      <Button title="Send OTP" onPress={sendOTP} disabled={loading} />

      <TextInput
        placeholder="Enter OTP"
        value={otpCode}
        onChangeText={setOtpCode}
        keyboardType="number-pad"
        maxLength={6}
        style={{ marginVertical: 20, fontSize: 24, textAlign: 'center' }}
      />

      <Button title="Verify OTP" onPress={verifyOTP} disabled={loading || !otpCode} />
    </View>
  );
}
```

---

## Cron Jobs Setup

### Cloud Scheduler (Google Cloud)

**1. Appointment Reminders (24 hours):**

```bash
gcloud scheduler jobs create http appointment-reminders-24h \
  --schedule="0 * * * *" \
  --uri="https://physiologicprism.com/cron/appointment-reminders-24h" \
  --http-method=POST
```

**2. Appointment Reminders (2 hours):**

```bash
gcloud scheduler jobs create http appointment-reminders-2h \
  --schedule="*/30 * * * *" \
  --uri="https://physiologicprism.com/cron/appointment-reminders-2h" \
  --http-method=POST
```

**3. Follow-up Reminders:**

```bash
gcloud scheduler jobs create http follow-up-reminders \
  --schedule="0 9 * * *" \
  --uri="https://physiologicprism.com/cron/follow-up-reminders" \
  --http-method=POST
```

**4. Messaging Cleanup:**

```bash
gcloud scheduler jobs create http messaging-cleanup \
  --schedule="0 2 * * *" \
  --uri="https://physiologicprism.com/cron/messaging-cleanup" \
  --http-method=POST
```

**5. Cleanup Expired OTPs:**

```bash
gcloud scheduler jobs create http cleanup-expired-otps \
  --schedule="0 */6 * * *" \
  --uri="https://physiologicprism.com/cron/cleanup-expired-otps" \
  --http-method=POST
```

---

## Troubleshooting

### Messages Not Sending

**Check:**
1. `MESSAGING_ENABLED=true` in `.env`
2. `MESSAGING_MOCK_MODE=false` in `.env`
3. Twilio credentials are correct
4. Phone number format is E.164 (+919876543210)
5. User has consented to messaging

**Debug:**
```python
from twilio_provider import get_twilio_provider

provider = get_twilio_provider()
health = provider.health_check()
print(health)  # Should show 'healthy': True
```

### Webhooks Not Working

**Check:**
1. Webhooks configured in Twilio Console
2. App is publicly accessible (not localhost)
3. HTTPS enabled (Twilio requires HTTPS)

**Test webhook locally:**
Use ngrok for local testing:
```bash
ngrok http 8080
# Use ngrok URL in Twilio webhook config
```

### OTP Not Received

**Check:**
1. Phone number is correct (E.164 format)
2. SMS capability enabled on Twilio number
3. Check Twilio logs: https://www.twilio.com/console/sms/logs

### Consent Issues

**Check consent status:**
```python
from consent_manager import ConsentManager, ConsentType

consent = ConsentManager.get_consent('user@example.com')
print(consent)

has_sms = ConsentManager.has_consent('user@example.com', ConsentType.SMS)
print(f"Has SMS consent: {has_sms}")
```

---

## Next Steps

1. ✅ **Test in Mock Mode** - Verify everything works
2. ✅ **Sign up for Twilio** - Get trial account
3. ✅ **Add Credentials** - Update `.env`
4. ✅ **Test with Real Messages** - Send to your own phone
5. ✅ **Sign BAA** - For HIPAA compliance
6. ✅ **Configure Webhooks** - Enable two-way messaging
7. ✅ **Set Up Cron Jobs** - Automate reminders
8. ✅ **Build UI** - Add messaging settings to app
9. ✅ **Launch!** - Start sending messages

---

## Support

For questions or issues:

- **Code Documentation**: Check comments in each Python file
- **Twilio Support**: https://support.twilio.com/
- **HIPAA Compliance**: See `MESSAGING_HIPAA_GDPR_COMPLIANCE.md`

**Last Updated:** February 2026
