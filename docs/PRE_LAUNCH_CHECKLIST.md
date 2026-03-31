# Pre-Launch Testing Checklist
## PhysiologicPRISM - Social Media Campaign Launch

**Status**: 🔴 BLOCKING ISSUES FOUND - DO NOT LAUNCH YET

---

## Critical Bugs Fixed Today

### ✅ FIXED: Patient Quota Enforcement
- **Issue**: Users could create unlimited patients despite 5-patient trial limit
- **Root Cause**: Redirect responses (302) weren't triggering quota deduction
- **Fix**: Updated `quota_middleware.py` to handle 2xx and 3xx status codes
- **Verification**: Run `python sync_patient_quota.py` to sync existing data

### ✅ FIXED: AI Calls Display Wrong Limit
- **Issue**: Dashboard showed 250 AI calls instead of 25 for trial users
- **Fix**: Auto-correction logic in `subscription_manager.py`
- **Verification**: Check dashboard after refresh

### ✅ FIXED: Quota Sync Issues
- **Issue**: Database counts out of sync with subscription limits
- **Fix**: Created sync script to correct historical data
- **Verification**: All subscriptions synced successfully

---

## 🔴 CRITICAL - Must Test Before Launch

### 1. User Registration & Onboarding
- [ ] Sign up with new email
- [ ] Email verification works
- [ ] Free trial starts automatically
- [ ] Correct quotas assigned (5 patients, 25 AI calls, 30 voice minutes)
- [ ] Dashboard shows correct limits immediately
- [ ] Welcome email sent (if configured)

### 2. Patient Creation Quota
- [ ] Can create patients 1-5 successfully
- [ ] Attempting patient #6 shows clear error message
- [ ] Error directs to upgrade page
- [ ] Quota counter updates after each creation
- [ ] Mobile app also enforces quota correctly

### 3. AI Features Quota
- [ ] Can use AI suggestions up to 25 times
- [ ] Attempt #26 shows clear error message
- [ ] Error directs to upgrade or token purchase
- [ ] AI quota counter updates in real-time
- [ ] Cache hits don't deduct from quota

### 4. Payment & Upgrade Flow
- [ ] Can view pricing page without errors
- [ ] Razorpay integration works for INR
- [ ] Stripe integration works for USD (if enabled)
- [ ] Subscription activates immediately after payment
- [ ] Quotas update to paid plan limits
- [ ] Receipt/invoice generated and emailed
- [ ] Can purchase AI call packs separately

### 5. Trial Expiration
- [ ] Trial expires after 14 days (or configured period)
- [ ] User receives expiration warning (7, 3, 1 days before)
- [ ] Dashboard shows clear expiration notice
- [ ] Features disabled after expiration
- [ ] Clear upgrade path shown

### 6. Mobile App Compatibility
- [ ] Mobile API enforces same quotas
- [ ] Patient creation blocked at limit
- [ ] AI features blocked when quota exhausted
- [ ] Error messages are user-friendly
- [ ] Quota info returned in API responses

---

## 🟡 HIGH PRIORITY - Should Test

### 7. Error Handling
- [ ] Quota exceeded errors are user-friendly (not technical)
- [ ] Network errors handled gracefully
- [ ] Database errors don't expose sensitive info
- [ ] Payment failures show clear next steps
- [ ] All error pages branded and professional

### 8. Performance Under Load
- [ ] Dashboard loads quickly (< 2 seconds)
- [ ] Patient creation is fast
- [ ] AI suggestions respond in < 5 seconds
- [ ] Multiple concurrent users don't cause issues
- [ ] Database queries optimized

### 9. Security
- [ ] CSRF protection enabled on all forms
- [ ] Firebase auth tokens validated
- [ ] No sensitive data in client-side code
- [ ] SQL injection protection (using Cosmos DB SDK)
- [ ] XSS protection enabled
- [ ] Rate limiting on API endpoints

### 10. Data Integrity
- [ ] Patient data persists correctly
- [ ] Subscription data consistent
- [ ] Quota counters accurate
- [ ] No data loss on errors
- [ ] Audit logs working

---

## 🟢 MEDIUM PRIORITY - Nice to Have

### 11. User Experience
- [ ] All pages mobile-responsive
- [ ] Loading spinners show for slow operations
- [ ] Success messages confirm actions
- [ ] Help text clear and useful
- [ ] Navigation intuitive

### 12. Analytics & Monitoring
- [ ] Google Analytics tracking (if configured)
- [ ] Error logging to Sentry (if configured)
- [ ] Usage metrics being collected
- [ ] Can track conversion funnel
- [ ] Dashboard analytics accurate

### 13. Email Communications
- [ ] Welcome email on signup
- [ ] Quota warning emails (80%, 90%, 100%)
- [ ] Trial expiration reminders
- [ ] Payment confirmations
- [ ] Password reset emails
- [ ] Unsubscribe links work

### 14. Content & Copy
- [ ] No typos on public pages
- [ ] Legal pages up to date (Terms, Privacy)
- [ ] Pricing clearly explained
- [ ] Feature comparisons accurate
- [ ] Blog posts (if any) professional

---

## 🔍 ADDITIONAL ISSUES TO INVESTIGATE

### Potential Similar Bugs
1. **AI Quota Enforcement** - Does it have same redirect issue?
   - Check: Do AI routes return redirects?
   - Check: Is deduction logic correct?

2. **Voice Quota Enforcement** - Same issue possible?
   - Check: Voice transcription routes
   - Check: Deduction timing

3. **Race Conditions**
   - Check: Multiple simultaneous patient creations
   - Check: Concurrent AI calls
   - Check: Payment processing conflicts

4. **Mobile API Parity**
   - Check: All quotas enforced identically
   - Check: Error responses consistent
   - Check: Status codes match web app

---

## Test Accounts Needed

Create these test accounts:
1. **Fresh Trial User** - Test full signup flow
2. **Quota Exhausted User** - Test limits and errors
3. **Paid Subscriber** - Test unlimited features
4. **Expired Trial User** - Test expiration flow
5. **Super Admin** - Verify no restrictions

---

## Deployment Checklist

### Before Deploying Fix
- [ ] Code reviewed by team (if applicable)
- [ ] Tests pass locally
- [ ] Environment variables confirmed on Azure
- [ ] Database backups taken
- [ ] Rollback plan documented

### After Deploying Fix
- [ ] Run `sync_patient_quota.py` on production
- [ ] Monitor logs for 1 hour
- [ ] Test critical flows on production
- [ ] Check error rates in monitoring
- [ ] Verify quotas working correctly

### Campaign Launch
- [ ] All critical tests passing
- [ ] No P0/P1 bugs outstanding
- [ ] Support team briefed on new features
- [ ] FAQ updated with common questions
- [ ] Social media posts scheduled
- [ ] Tracking pixels installed
- [ ] Budget and spend limits set

---

## Emergency Contacts & Rollback

### If Critical Bug Found During Campaign
1. **Pause ad spend immediately** - Don't waste money with broken experience
2. **Add notice to homepage** - Be transparent about issues
3. **Email affected users** - Apologize and offer extension
4. **Fix and deploy ASAP** - Test thoroughly first
5. **Resume campaign** - Only after verification

### Rollback Procedure
```bash
# If deployment breaks something
az containerapp update --name physiologicprism --resource-group PhysioPrism --image <previous-version>

# If database changes break something
# Use Cosmos DB point-in-time restore (if enabled)
# Or run corrective scripts
```

---

## Sign-Off

**Tested By**: _________________
**Date**: _________________
**Ready for Launch**: ☐ YES  ☐ NO (issues below)

**Blocking Issues**:
-

**Notes**:
-

---

## Post-Launch Monitoring (First 48 Hours)

### Watch These Metrics
- [ ] New user signups
- [ ] Trial activations (should be 100%)
- [ ] Error rates (should be < 1%)
- [ ] Patient creation success rate
- [ ] AI call success rate
- [ ] Payment success rate
- [ ] User complaints/support tickets
- [ ] Page load times
- [ ] Server resource usage

### Daily Checks
- Morning: Check overnight signups and errors
- Afternoon: Review support tickets
- Evening: Check conversion rates and user engagement
- End of day: Review full analytics dashboard

---

**Last Updated**: March 30, 2026
**Version**: 1.0
