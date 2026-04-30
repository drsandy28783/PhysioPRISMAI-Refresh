# PhysiologicPRISM - Complete QA Testing Plan
**Before Public Launch**

## Timeline Overview
- **Total Estimated Time:** 8-10 hours (spread over 2-3 days)
- **Clinical Workflows:** Handled by you separately
- **Technical Features:** Covered in this plan

---

## Pre-Testing Setup
**Time: 15 minutes**

### Test Accounts Needed
Create these test accounts to cover all scenarios:

1. **Individual Physiotherapist** (fresh registration)
   - Email: test.individual@gmail.com
   - Should go through full approval flow

2. **Institute Admin** (fresh registration)
   - Email: test.admin@gmail.com
   - Institute: "Test Physio Center"
   - Should go through full approval flow

3. **Institute Staff Member** (fresh registration)
   - Email: test.staff@gmail.com
   - Institute: Same as admin above
   - Should request to join admin's institute

4. **Existing User** (use your current account)
   - For testing logged-in user flows

---

## 1. PUBLIC PAGES & FIRST IMPRESSIONS
**Time: 30 minutes**

### A. Website Access (Without Login)
- [ ] Visit https://physiologicprism.com in incognito mode
- [ ] Check homepage loads properly
- [ ] Test all navigation menu links work
- [ ] Click "Pricing" - page loads correctly
- [ ] Click "Privacy Policy" - page loads without login popup
- [ ] Click "Terms of Service" - page loads without login popup
- [ ] Click "Blog" (if available) - no login required
- [ ] Try accessing /dashboard without login - should redirect to login
- [ ] Try accessing /patients without login - should redirect to login

### B. Mobile Responsiveness
- [ ] Open site on mobile phone (Chrome/Safari)
- [ ] Check homepage looks good
- [ ] Test navigation menu works
- [ ] Try scrolling - everything readable
- [ ] Test on tablet if available

**Issues Found:**
```
(Write any issues here)
```

---

## 2. REGISTRATION & ONBOARDING
**Time: 45 minutes**

### A. Individual Physiotherapist Registration
**Test Account: test.individual@gmail.com**

- [ ] Click "Sign Up" button
- [ ] Select "Individual Physiotherapist"
- [ ] Fill in all fields correctly
- [ ] Submit registration
- [ ] Check you see "Registration Successful" message
- [ ] Check you see "Waiting for Approval" message
- [ ] Try to login before approval - should show "Account not approved"
- [ ] Check super admin dashboard for approval request

**Approve the Account (as Super Admin):**
- [ ] Login as super admin
- [ ] Go to approval dashboard
- [ ] Approve test.individual@gmail.com
- [ ] Check system sends email notification

**Login as Approved User:**
- [ ] Login with test.individual@gmail.com
- [ ] Check welcome notification appears
- [ ] Check approval notification appears
- [ ] Check dashboard loads properly
- [ ] Verify no errors in browser console (F12)

### B. Institute Admin Registration
**Test Account: test.admin@gmail.com**

- [ ] Register as Institute Admin
- [ ] Institute Name: "Test Physio Center"
- [ ] Fill all required fields
- [ ] Submit and wait for approval message
- [ ] Approve account (as super admin)
- [ ] Login as institute admin
- [ ] Check notifications received

### C. Institute Staff Registration
**Test Account: test.staff@gmail.com**

- [ ] Register as Staff Physiotherapist
- [ ] Select Institute: "Test Physio Center"
- [ ] Submit registration
- [ ] Check institute admin sees approval request
- [ ] Approve as institute admin (Tier 1)
- [ ] Check super admin sees Tier 2 approval request
- [ ] Approve as super admin (Tier 2)
- [ ] Login as staff member
- [ ] Verify belongs to correct institute

### D. Registration Security Tests
- [ ] Try registering with invalid email format - should show error
- [ ] Try registering with existing email - should show error
- [ ] Try registering with weak password - should show validation error
- [ ] Try registering with mismatched passwords - should show error
- [ ] Leave required fields empty - should show validation errors
- [ ] Try SQL injection in name field: `admin'; DROP TABLE users--` - should be safely handled

**Issues Found:**
```
(Write any issues here)
```

---

## 3. AUTHENTICATION & SESSION MANAGEMENT
**Time: 30 minutes**

### A. Login Flows
- [ ] Login with correct credentials - works
- [ ] Login with wrong password - shows error
- [ ] Login with non-existent email - shows error
- [ ] Login with unapproved account - shows "not approved" message
- [ ] Check "Remember Me" checkbox - session persists
- [ ] Don't check "Remember Me" - session expires appropriately

### B. Password Management
- [ ] Click "Forgot Password"
- [ ] Enter valid email
- [ ] Check email received with reset link
- [ ] Click reset link
- [ ] Enter new password
- [ ] Confirm password reset successful
- [ ] Login with new password - works
- [ ] Try using old password - should fail

### C. Session Security
- [ ] Login to account
- [ ] Copy session cookie (F12 > Application > Cookies)
- [ ] Try using session in different browser - should work until logout
- [ ] Logout from first browser
- [ ] Check second browser session invalidated
- [ ] Leave logged in for 30+ minutes idle
- [ ] Try to perform action - should prompt re-login or handle gracefully

### D. Two-Factor Authentication (if enabled)
- [ ] Enable 2FA in settings
- [ ] Logout and login again
- [ ] Check 2FA code required
- [ ] Enter correct code - login successful
- [ ] Try wrong code - login fails

**Issues Found:**
```
(Write any issues here)
```

---

## 4. USER DASHBOARD & NAVIGATION
**Time: 20 minutes**

### A. Dashboard Layout
- [ ] Login and check dashboard loads
- [ ] All widgets/cards display properly
- [ ] Statistics show correct numbers
- [ ] No broken images or missing data
- [ ] All navigation menu items work
- [ ] Sidebar collapses/expands (if applicable)

### B. Navigation Tests
- [ ] Click each menu item
- [ ] Verify each page loads without errors
- [ ] Check breadcrumbs work correctly
- [ ] Test "Back" button works properly
- [ ] Test direct URL access to protected pages

### C. User Profile
- [ ] Go to Profile/Settings page
- [ ] Update name - saves successfully
- [ ] Update phone number - saves successfully
- [ ] Update profile picture - uploads correctly
- [ ] Check updated info appears everywhere
- [ ] Try uploading invalid file types - should reject

**Issues Found:**
```
(Write any issues here)
```

---

## 5. NOTIFICATIONS SYSTEM
**Time: 30 minutes**

### A. In-App Notifications
- [ ] Check notification bell icon shows unread count
- [ ] Click notification bell - dropdown appears
- [ ] Click a notification - marks as read
- [ ] Check notification count decreases
- [ ] Go to /notifications page
- [ ] Verify you see ONLY your own notifications
- [ ] Check notification types: welcome, approval, system
- [ ] Click "Mark All as Read" - all marked read
- [ ] Delete a notification - successfully removed
- [ ] Refresh page - deleted notification stays deleted

### B. Security Test (CRITICAL)
**This is the bug we just fixed - must verify:**

- [ ] Login as User A (e.g., test.individual@gmail.com)
- [ ] Check notifications - note the count
- [ ] Login as User B (e.g., test.admin@gmail.com) in different browser
- [ ] Check notifications for User B
- [ ] VERIFY: User A's notifications DO NOT appear for User B
- [ ] VERIFY: Each user sees ONLY their own notifications
- [ ] Create new user (User C) and approve
- [ ] Login as User C
- [ ] VERIFY: Only sees their own welcome/approval notifications

### C. Email Notifications (if enabled)
- [ ] Perform action that triggers email (e.g., approval)
- [ ] Check email received
- [ ] Verify email content is correct
- [ ] Click links in email - work properly

**Issues Found:**
```
(Write any issues here)
```

---

## 6. SUBSCRIPTION & PRICING
**Time: 45 minutes**

### A. Pricing Page
- [ ] Visit /pricing page
- [ ] Check all plans display correctly
- [ ] Prices showing in correct currency
- [ ] Feature comparisons clear
- [ ] "Sign Up" buttons work

### B. Free Trial
- [ ] Register new account with free trial
- [ ] Check trial period shows correctly
- [ ] Verify trial features are accessible
- [ ] Check trial expiration date displayed
- [ ] Wait for trial to expire (or manually set expiry date in DB)
- [ ] Check trial expiration notification appears
- [ ] Verify restricted access after expiry

### C. Subscription Purchase (Use Test Mode)
**IMPORTANT: Use Razorpay/Stripe test mode**

- [ ] Click "Upgrade to Premium"
- [ ] Select a plan (e.g., Monthly Professional)
- [ ] Click "Subscribe"
- [ ] Payment gateway loads
- [ ] Use test card: 4111 1111 1111 1111 (Visa test card)
- [ ] Complete payment
- [ ] Check redirected back to app
- [ ] Verify subscription activated
- [ ] Check invoice generated
- [ ] Download invoice PDF - opens correctly
- [ ] Check subscription shows in account settings
- [ ] Verify new features unlocked

### D. Subscription Management
- [ ] Go to subscription settings
- [ ] View current plan details
- [ ] Change plan (upgrade/downgrade)
- [ ] Verify plan changed successfully
- [ ] Cancel subscription
- [ ] Check cancellation confirmation
- [ ] Verify access until period end
- [ ] Reactivate subscription
- [ ] Check reactivation successful

### E. Token/Quota System
- [ ] Check quota/token balance in dashboard
- [ ] Perform action that consumes tokens (e.g., AI suggestions)
- [ ] Verify token count decreases
- [ ] Use all tokens/reach quota limit
- [ ] Check warning notification appears
- [ ] Try to use feature after limit - should block or prompt upgrade
- [ ] Purchase additional tokens
- [ ] Verify token balance increased

**Issues Found:**
```
(Write any issues here)
```

---

## 7. FILE UPLOADS & DOWNLOADS
**Time: 30 minutes**

### A. Profile Picture Upload
- [ ] Upload JPG image - works
- [ ] Upload PNG image - works
- [ ] Try uploading very large file (>10MB) - should reject with message
- [ ] Try uploading wrong file type (PDF) - should reject
- [ ] Upload image with special characters in filename - handles correctly

### B. Document Uploads (if applicable)
- [ ] Upload patient document/report
- [ ] Verify file saved successfully
- [ ] Download uploaded file
- [ ] Verify downloaded file opens correctly
- [ ] Delete uploaded file
- [ ] Check file actually deleted

### C. Export Features
- [ ] Export data as PDF
- [ ] PDF opens correctly
- [ ] Data in PDF is accurate
- [ ] Export data as Excel/CSV
- [ ] File downloads successfully
- [ ] Open in Excel - data formatted correctly

**Issues Found:**
```
(Write any issues here)
```

---

## 8. SEARCH & FILTERING
**Time: 30 minutes**

### A. Search Functionality
- [ ] Use search bar to find patients
- [ ] Search by name - finds correct results
- [ ] Search by partial name - autocomplete works
- [ ] Search with special characters - handles safely
- [ ] Search with empty query - handles gracefully
- [ ] Search for non-existent item - shows "No results"

### B. Filters
- [ ] Apply date range filter
- [ ] Apply status filter (e.g., Active/Inactive)
- [ ] Apply multiple filters together
- [ ] Clear filters - returns to full list
- [ ] Check filter preserves after page refresh

### C. Sorting
- [ ] Sort by name (A-Z)
- [ ] Sort by name (Z-A)
- [ ] Sort by date (newest first)
- [ ] Sort by date (oldest first)
- [ ] Check sorting persists across pages

**Issues Found:**
```
(Write any issues here)
```

---

## 9. FORMS & DATA VALIDATION
**Time: 30 minutes**

### A. Form Validation
Test on any major form (e.g., Add Patient, Update Profile):

- [ ] Submit empty form - shows all required field errors
- [ ] Enter invalid email format - shows email error
- [ ] Enter invalid phone format - shows phone error
- [ ] Enter past date where future date required - shows error
- [ ] Enter negative numbers in age field - shows error
- [ ] Enter very long text in name field - truncates or shows error
- [ ] Try XSS attack: `<script>alert('XSS')</script>` in text field - should be sanitized

### B. Form Submission
- [ ] Fill form correctly
- [ ] Submit form
- [ ] Check success message appears
- [ ] Verify data saved in database
- [ ] Refresh page - data persists
- [ ] Edit saved data
- [ ] Save changes - updates successfully

### C. Form Usability
- [ ] Tab through form fields - tab order logical
- [ ] Required fields marked with asterisk
- [ ] Help text/tooltips available where needed
- [ ] Error messages clear and helpful
- [ ] Form doesn't lose data on validation error

**Issues Found:**
```
(Write any issues here)
```

---

## 10. PERMISSIONS & ACCESS CONTROL
**Time: 45 minutes**

### A. Individual Physiotherapist Permissions
Login as Individual Physiotherapist:

- [ ] Can add own patients - YES
- [ ] Can view own patients - YES
- [ ] Can edit own patients - YES
- [ ] Can delete own patients - YES
- [ ] CANNOT view other therapists' patients - BLOCKED
- [ ] CANNOT access admin dashboard - BLOCKED
- [ ] CANNOT approve users - BLOCKED

### B. Institute Staff Permissions
Login as Institute Staff:

- [ ] Can add patients to own institute - YES
- [ ] Can view institute patients (if sharing enabled) - Check policy
- [ ] Can view other staff's patients - Check policy
- [ ] CANNOT access admin functions - BLOCKED
- [ ] CANNOT approve institute staff - BLOCKED

### C. Institute Admin Permissions
Login as Institute Admin:

- [ ] Can view all institute staff - YES
- [ ] Can approve pending staff - YES
- [ ] Can view institute analytics - YES
- [ ] Can manage institute settings - YES
- [ ] CANNOT access super admin dashboard - BLOCKED
- [ ] CANNOT approve other institutes' staff - BLOCKED

### D. Super Admin Permissions
Login as Super Admin:

- [ ] Can approve all pending users - YES
- [ ] Can view all users - YES
- [ ] Can access audit logs - YES
- [ ] Can manage system settings - YES
- [ ] Can view all data across institutes - YES

### E. URL Manipulation Security
Try accessing restricted URLs directly:

- [ ] As regular user, access /super_admin_dashboard - BLOCKED
- [ ] As regular user, access /admin_dashboard - BLOCKED
- [ ] As staff, access admin functions - BLOCKED
- [ ] As non-logged-in user, access /dashboard - REDIRECTED TO LOGIN

**Issues Found:**
```
(Write any issues here)
```

---

## 11. MOBILE APP TESTING (If Applicable)
**Time: 1 hour**

### A. Installation
- [ ] Download app from Play Store/App Store
- [ ] Install successfully
- [ ] Open app - splash screen loads
- [ ] Login screen appears

### B. Core Features
- [ ] Login works
- [ ] Dashboard displays correctly
- [ ] Navigation works smoothly
- [ ] Forms usable on small screen
- [ ] Camera integration works (if applicable)
- [ ] Notifications appear
- [ ] Logout works

### C. Offline Functionality (if applicable)
- [ ] Turn off internet
- [ ] Check what features still work offline
- [ ] Make changes offline
- [ ] Turn on internet
- [ ] Verify changes sync to server

**Issues Found:**
```
(Write any issues here)
```

---

## 12. PERFORMANCE & LOAD TESTING
**Time: 30 minutes**

### A. Page Load Speed
- [ ] Dashboard loads in <3 seconds
- [ ] Patient list loads in <3 seconds
- [ ] Reports generate in <5 seconds
- [ ] Image uploads complete in <10 seconds

### B. Large Data Sets
- [ ] Create 50+ patient records
- [ ] Check list page still loads quickly
- [ ] Search still works fast
- [ ] Pagination works correctly

### C. Concurrent Users
- [ ] Login from 3 different devices simultaneously
- [ ] Perform actions on all devices
- [ ] Verify no conflicts or errors
- [ ] Check data consistency across devices

**Issues Found:**
```
(Write any issues here)
```

---

## 13. BROWSER COMPATIBILITY
**Time: 45 minutes**

Test on these browsers:

### Google Chrome (Latest)
- [ ] All features work
- [ ] Layout looks correct
- [ ] No console errors

### Firefox (Latest)
- [ ] All features work
- [ ] Layout looks correct
- [ ] No console errors

### Safari (Mac/iPhone)
- [ ] All features work
- [ ] Layout looks correct
- [ ] No console errors

### Microsoft Edge
- [ ] All features work
- [ ] Layout looks correct
- [ ] No console errors

**Issues Found:**
```
(Write any issues here)
```

---

## 14. SECURITY TESTING
**Time: 1 hour**

### A. SQL Injection Tests
Try these in various input fields:
- [ ] `' OR '1'='1` - should not bypass authentication
- [ ] `admin'--` - should not grant access
- [ ] `'; DROP TABLE users--` - should be sanitized

### B. XSS (Cross-Site Scripting) Tests
- [ ] Enter `<script>alert('XSS')</script>` in text fields - should be escaped
- [ ] Enter `<img src=x onerror=alert('XSS')>` - should be sanitized
- [ ] Check stored XSS - data with scripts doesn't execute when displayed

### C. Session Hijacking Prevention
- [ ] Copy session cookie
- [ ] Try using in different browser/location
- [ ] Check if session timeout works
- [ ] Verify HTTPS is enforced (check URL has padlock)

### D. Data Privacy
- [ ] Patient data not visible in URL parameters
- [ ] Sensitive data not logged in browser console
- [ ] Downloaded files not accessible via direct URL
- [ ] Check no PHI (Protected Health Information) leaked

### E. CSRF Protection
- [ ] Check forms have CSRF tokens
- [ ] Try submitting form without CSRF token - should fail

**Issues Found:**
```
(Write any issues here)
```

---

## 15. ERROR HANDLING
**Time: 30 minutes**

### A. 404 Pages
- [ ] Access non-existent URL: /this-page-does-not-exist
- [ ] Check friendly 404 page shows
- [ ] Check "Go Home" button works

### B. 500 Errors
- [ ] Intentionally cause server error (disconnect database temporarily)
- [ ] Check friendly error page shows
- [ ] Check error logged for debugging
- [ ] Restore database, verify app recovers

### C. Network Issues
- [ ] Turn off internet during form submission
- [ ] Check error message appears
- [ ] Turn on internet
- [ ] Retry submission - works

### D. Validation Errors
- [ ] Submit invalid data
- [ ] Check error messages are clear
- [ ] Check errors highlight specific fields
- [ ] Fix errors and resubmit - works

**Issues Found:**
```
(Write any issues here)
```

---

## 16. AUDIT & COMPLIANCE
**Time: 30 minutes**

### A. Audit Logs (for admins)
- [ ] Perform actions (add/edit/delete)
- [ ] Check audit logs record all actions
- [ ] Verify logs show: user, action, timestamp
- [ ] Check logs cannot be edited by users

### B. Data Export (for users)
- [ ] Request data export (GDPR compliance)
- [ ] Verify all user data included
- [ ] Check data downloadable
- [ ] Verify format is readable (JSON/CSV/PDF)

### C. Account Deletion
- [ ] Request account deletion
- [ ] Check confirmation required
- [ ] Delete account
- [ ] Verify data actually deleted
- [ ] Try to login with deleted account - should fail

**Issues Found:**
```
(Write any issues here)
```

---

## 17. FINAL CHECKS
**Time: 30 minutes**

### A. Footer Links
- [ ] Privacy Policy link works
- [ ] Terms of Service link works
- [ ] Contact Us link works
- [ ] Social media links work (if applicable)

### B. Help & Support
- [ ] Help/FAQ page accessible
- [ ] Contact form works (if applicable)
- [ ] Support email works
- [ ] Knowledge base searchable (if applicable)

### C. Legal & Compliance
- [ ] Cookie consent banner appears (if GDPR applicable)
- [ ] Privacy policy up to date
- [ ] Terms of service up to date
- [ ] HIPAA compliance notice (if applicable in your region)

### D. Branding & Content
- [ ] Logo displays correctly everywhere
- [ ] No spelling errors in UI text
- [ ] Brand colors consistent
- [ ] All images load
- [ ] No Lorem Ipsum placeholder text

**Issues Found:**
```
(Write any issues here)
```

---

## TEST RESULTS SUMMARY

### Critical Issues (Must Fix Before Launch)
```
1.
2.
3.
```

### High Priority Issues (Fix Soon)
```
1.
2.
3.
```

### Medium Priority Issues (Post-Launch OK)
```
1.
2.
3.
```

### Low Priority Issues (Nice to Have)
```
1.
2.
3.
```

---

## SIGN-OFF

**Testing Completed By:** ___________________

**Date:** ___________________

**Ready for Launch?** ☐ YES  ☐ NO (Reason: ___________________)

---

## NOTES

### What Worked Well
```
(Write what worked smoothly)
```

### What Needs Improvement
```
(Write areas for improvement)
```

### Questions for Development Team
```
(Write any technical questions)
```

---

## RECOMMENDED TESTING SCHEDULE

### Day 1 (3-4 hours)
- Sections 1-6: Public pages, Registration, Authentication, Dashboard, Notifications, Subscriptions

### Day 2 (3-4 hours)
- Sections 7-12: File uploads, Search, Forms, Permissions, Mobile (if applicable), Performance

### Day 3 (2-3 hours)
- Sections 13-17: Browser compatibility, Security, Error handling, Audit, Final checks

**Total: 8-11 hours spread over 3 days**

---

## TIPS FOR EFFECTIVE TESTING

1. **Use Incognito/Private Browsing:** Start each test session fresh
2. **Take Screenshots:** Capture any errors or issues
3. **Document Everything:** Even small issues matter
4. **Test Like a User:** Don't just click - think about real user workflows
5. **Break Things:** Try to make the app fail - that's how you find bugs
6. **Check Mobile:** 50%+ users will be on mobile
7. **Test Edge Cases:** Empty data, maximum values, special characters
8. **Don't Rush:** Quality over speed

---

## EMERGENCY CONTACTS

**Development Team:**
- Email: [Your email]
- Phone: [Your phone]

**Hosting/Infrastructure:**
- Azure Support: [Support email]
- Database Issues: [DBA contact]

**Payment Gateway:**
- Razorpay Support: [Support contact]

---

*Generated for PhysiologicPRISM Pre-Launch QA*
*Last Updated: March 9, 2026*
