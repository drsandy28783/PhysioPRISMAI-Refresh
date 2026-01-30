# Sentry Setup Guide - Step by Step
**PhysioPRISM Error Tracking - CRITICAL for Production**

---

## 🎯 What is Sentry?

**Sentry** is error tracking software that:
- ✅ Catches all Python exceptions automatically
- ✅ Emails you when errors occur
- ✅ Shows exact error details + stack trace
- ✅ Tells you which user hit the error
- ✅ Groups similar errors together
- ✅ Shows error trends over time

**Cost:** FREE (up to 5,000 errors/month - more than enough for you)

**Setup time:** 15 minutes

**Your app already has Sentry integrated** - you just need to add your DSN key!

---

## 📋 Setup Steps

### Step 1: Create Sentry Account (5 minutes)

1. **Go to:** https://sentry.io/signup/

2. **Sign up** with:
   - Your email
   - Create password
   - Or use Google/GitHub login

3. **Choose plan:** Select **"Developer" (FREE)**

4. **Skip team invitation** (or add yourself only)

---

### Step 2: Create Project (3 minutes)

1. **After login**, click "**Create Project**"

2. **Select platform:**
   - Choose "**Python**"
   - Then "**Flask**"

3. **Name your project:**
   - Name: `PhysioPRISM`
   - Team: (use default)

4. **Click "Create Project"**

---

### Step 3: Get Your DSN Key (2 minutes)

After creating project, you'll see:

```
Configure your SDK:

export SENTRY_DSN="https://abc123...@o123456.ingest.sentry.io/789012"
```

**Copy that URL** - that's your SENTRY_DSN!

It looks like:
```
https://1234567890abcdef@o123456.ingest.sentry.io/789012
```

---

### Step 4: Add DSN to Your App (5 minutes)

#### For Local Development:

1. **Open:** `D:\New folder\New folder\Recovery\.env`

2. **Find the line:**
   ```
   SENTRY_DSN=
   ```

3. **Update it:**
   ```
   SENTRY_DSN=https://YOUR_SENTRY_DSN_HERE
   ```
   *(Paste the DSN you copied)*

4. **Save the file**

#### For Azure Production:

1. **Go to Azure Portal:** https://portal.azure.com

2. **Navigate to:** Your Container App → Settings → Environment Variables

3. **Add new variable:**
   - Name: `SENTRY_DSN`
   - Value: `https://YOUR_SENTRY_DSN_HERE`

4. **Save** (app will restart automatically)

---

### Step 5: Test Sentry (5 minutes)

Let's verify Sentry is working by triggering a test error:

#### Create test file:

Create: `D:\New folder\New folder\Recovery\test_sentry.py`

```python
"""
Test script to verify Sentry error tracking is working.
Run this AFTER setting up Sentry DSN.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Sentry (same as in main.py)
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

SENTRY_DSN = os.environ.get('SENTRY_DSN')

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            FlaskIntegration(),
            LoggingIntegration(
                level=None,
                event_level=None
            )
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=os.environ.get('FLASK_ENV', 'production')
    )
    print("✅ Sentry initialized successfully")
else:
    print("❌ SENTRY_DSN not found in environment")
    exit(1)

# Trigger test error
print("\n🧪 Triggering test error...")
print("This will send an error to Sentry dashboard.\n")

try:
    # This will cause a division by zero error
    result = 1 / 0
except Exception as e:
    # Capture the exception in Sentry
    sentry_sdk.capture_exception(e)
    print(f"✅ Test error captured: {type(e).__name__}")
    print("\n📧 Check your Sentry dashboard and email!")
    print("   You should receive an error notification.\n")

# Send a test message
sentry_sdk.capture_message("🧪 Test message from PhysioPRISM - Sentry is working!", level="info")
print("✅ Test message sent to Sentry")

print("\n" + "="*50)
print("✅ SENTRY TEST COMPLETE")
print("="*50)
print("\n📋 Next steps:")
print("1. Go to https://sentry.io")
print("2. Check your project dashboard")
print("3. You should see the test error")
print("4. Check your email for notification")
print("\nIf you see the error in Sentry → Setup successful! 🎉")
```

#### Run the test:

```bash
cd "D:\New folder\New folder\Recovery"
python test_sentry.py
```

#### Expected output:
```
✅ Sentry initialized successfully

🧪 Triggering test error...
✅ Test error captured: ZeroDivisionError

📧 Check your Sentry dashboard and email!
✅ Test message sent to Sentry

==================================================
✅ SENTRY TEST COMPLETE
==================================================
```

#### Verify in Sentry:

1. Go to https://sentry.io
2. Click on your "PhysioPRISM" project
3. You should see:
   - **1 error:** "ZeroDivisionError: division by zero"
   - **1 message:** "Test message from PhysioPRISM"
4. Check your email for notification

**If you see these → Sentry is working!** ✅

---

## 🎉 Congratulations!

Sentry is now catching errors in your app!

### What Happens Now:

**Whenever an error occurs:**
1. ✅ Sentry automatically captures it
2. ✅ You get an email notification
3. ✅ Error details appear in Sentry dashboard
4. ✅ You can see:
   - Error message
   - Stack trace (where it happened)
   - User info (who hit the error)
   - Request data (what they were doing)

### Example Real-World Scenario:

**Without Sentry:**
- User: "Something's not working"
- You: "What did you do? What error?"
- User: "I don't remember..."
- You: 🤷 *No idea what went wrong*

**With Sentry:**
- Error happens → Email arrives immediately
- Email says: "Error in /api/patients endpoint"
- Dashboard shows: User test@example.com tried to create patient
- Stack trace shows: Database connection failed at line 234
- You: Fix the issue in 10 minutes! ✅

---

## 📊 Using Sentry Dashboard

### Key Features:

1. **Issues Tab** - All errors grouped
2. **Performance** - Slow endpoints
3. **Releases** - Track which version has bugs
4. **Alerts** - Configure email/Slack notifications

### Recommended Alerts:

1. **Go to:** Project Settings → Alerts

2. **Create alert:**
   - **When:** An issue is first seen
   - **Then:** Send email to you
   - **Save**

3. **Create another alert:**
   - **When:** Error happens more than 10 times in 1 hour
   - **Then:** Send email to you
   - **Save** (this catches recurring issues)

---

## ⚙️ Advanced Configuration (Optional)

### Filter Out Noisy Errors:

In your `.env`, you can add:

```env
# Ignore specific errors (optional)
SENTRY_IGNORE_ERRORS=KeyboardInterrupt,SystemExit
```

### Set Environment:

```env
# Helps you differentiate prod vs dev errors
FLASK_ENV=production  # or "development" or "staging"
```

Sentry will tag errors with environment, so you know where they came from.

---

## 🔍 Troubleshooting

### Problem: No errors appearing in Sentry

**Check:**
1. Is SENTRY_DSN set in `.env`?
   ```bash
   cat .env | grep SENTRY_DSN
   ```

2. Did you restart the app after setting DSN?
   ```bash
   # Stop and restart: python main.py
   ```

3. Run the test script:
   ```bash
   python test_sentry.py
   ```

4. Check Sentry dashboard within 1 minute

### Problem: "dsn not found" error

**Solution:** Your `.env` file isn't being loaded.

```python
# Add this at the top of main.py (should already be there)
from dotenv import load_dotenv
load_dotenv()
```

### Problem: Too many error emails

**Solution:** Configure alert rules to reduce noise.

1. Go to Sentry → Alerts
2. Edit alert rules
3. Change frequency to "At most once every hour"

---

## 📱 Mobile App Integration (Optional)

Want Sentry for your React Native mobile app too?

1. Create separate Sentry project: "PhysioPRISM-Mobile"
2. Select "React Native" as platform
3. Follow their setup instructions
4. Add to your mobile app

**Note:** Focus on backend first. Mobile can come later.

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Sentry account created
- [ ] PhysioPRISM project created
- [ ] SENTRY_DSN added to `.env`
- [ ] Test script ran successfully
- [ ] Error visible in Sentry dashboard
- [ ] Email notification received
- [ ] SENTRY_DSN added to Azure (for production)
- [ ] Alert rules configured

---

## 🎯 Next Steps After Sentry

Now that you have error tracking:

1. **Run your tests** (pytest) - See if any errors get logged
2. **Deploy to production** - Confident you'll know if something breaks
3. **Monitor Sentry** - First few days, check daily
4. **Fix errors** - As they appear in dashboard

---

## 💰 Cost Monitoring

**Free tier limits:**
- 5,000 errors/month
- 10,000 transactions/month
- 1 GB attachments

**If you exceed:**
- Sentry will email you
- You can upgrade ($26/month for 50K errors)
- Or optimize to reduce error volume

**For your app:** 5,000 errors/month is plenty!

---

## 📞 Support

**Sentry Support:**
- Docs: https://docs.sentry.io/platforms/python/guides/flask/
- Community: https://forum.sentry.io/

**If you need help:**
- Come back to me (Claude)
- Show me the error in Sentry
- I'll help you fix it!

---

## 🎉 Success!

**You now have production-grade error tracking!**

With Sentry + automated tests, you can deploy confidently knowing:
- ✅ Tests catch bugs before deployment
- ✅ Sentry catches bugs that slip through
- ✅ You're alerted immediately
- ✅ You have all the info to fix issues fast

**This is huge progress toward production readiness!** 🚀

---

**Document Version:** 1.0
**Status:** Ready to Use
**Next:** Run automated tests with pytest
