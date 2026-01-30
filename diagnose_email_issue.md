# Email Notification Issue Diagnosis

You mentioned a user registered recently but you didn't receive an email notification. Let's investigate what happened.

## Step 1: Check Your Super Admin Dashboard

1. Go to https://physiologicprism.com/super_admin_dashboard
2. Log in with drsandeep@physiologicprism.com
3. Look for users with "Pending Approval" status
4. Check if the recent user registration appears there

**This is the quickest way to confirm the registration was successful.**

## Step 2: Check When the Registration Happened

Can you provide:
- Approximate date/time when the user registered?
- User's name or email if you know it?

This will help narrow down the logs to check.

## Step 3: Check Resend Email Dashboard

1. Go to https://resend.com/emails
2. Log in to your Resend account
3. Filter emails by:
   - Recipient: drsandeep@physiologicprism.com
   - Date range: When the registration happened
4. Check if an email was sent but maybe bounced or failed

Look for:
- ✅ **Delivered**: Email was sent successfully (check spam folder)
- ❌ **Bounced**: Email was rejected by your email server
- ⏳ **Queued**: Email is still being processed
- ⚠️ **Failed**: Email sending failed

## Step 4: Check Your Email Settings

The user registration email comes from: **noreply@physiologicprism.com**

Check if:
1. This email is in your spam/junk folder
2. Your email provider is blocking emails from this sender
3. You have any email filters that might be moving these emails

## Step 5: Run Diagnostic Query in Azure

You can run this command to check recent application logs for errors:

```bash
az containerapp logs show \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --tail 1000 \
  --follow false \
  | grep -E "(ERROR|Failed to send|registration)" \
  | tail -100
```

Look for lines like:
- "Failed to send registration notification"
- "Error in send_registration_notification"
- Any error messages with timestamps matching the registration time

## Common Causes & Solutions

### Cause 1: Email Went to Spam
**Solution**:
- Check spam/junk folder for emails from noreply@physiologicprism.com
- Add noreply@physiologicprism.com to your safe senders list
- Mark the email as "Not Spam" if found

### Cause 2: Email Was Bounced by Your Email Server
**Solution**:
- Check Resend dashboard for bounce notifications
- Verify drsandeep@physiologicprism.com is a valid, active email
- Contact your email administrator if corporate email policies are blocking it

### Cause 3: Resend API Rate Limit or Quota Exceeded
**Solution**:
- Check Resend dashboard for any rate limit warnings
- Verify your Resend account is active and in good standing
- Check if you've hit any sending limits

### Cause 4: Application Error During Registration
**Solution**:
- Check if the user appears in your Super Admin Dashboard
  - If YES: Registration succeeded, but email failed to send
  - If NO: Registration itself failed (different issue)

### Cause 5: User Registered Through Different Path
**Solution**:
- Check if user registered as:
  - Regular user (/register) → Email sent to super admin
  - Institute admin (/register_institute) → Email sent to super admin
  - Staff member (/register_with_institute) → Email sent to institute admin (NOT you)

**If user registered as staff member for an existing institute, the email went to the institute admin, not you!**

## What To Do Next

### If User IS in Your Dashboard:
- Registration worked, but you didn't get the email
- **Action**: Check spam folder and Resend dashboard
- The test emails worked, so this is likely an email delivery issue

### If User is NOT in Your Dashboard:
- Registration failed before completion
- **Action**: Ask the user if they received any error messages
- Check application logs for errors around that time

## Quick Test Right Now

Run the test script again to verify email system is still working:

```bash
cd "D:\New folder\New folder\Recovery"
python test_email.py
```

If you receive the test emails, the system is working fine - the issue is specific to that registration.

## Need More Help?

If none of the above helps, please provide:

1. Approximate date/time of the registration (e.g., "yesterday at 3pm")
2. User's email or name if you know it
3. Whether the user appears in your Super Admin Dashboard
4. Screenshot of your Resend dashboard showing recent emails

With this information, I can dig deeper into the specific logs and pinpoint exactly what happened.

---

**Most Likely Scenario**: The email was sent but ended up in your spam folder. Check there first!
