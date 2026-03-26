# Razorpay Plan Setup Guide - USD & INR Pricing

This guide walks you through setting up subscription plans in Razorpay for PhysiologicPRISM.

## Prerequisites

1. **Razorpay Account Setup**
   - Sign up at https://razorpay.com/
   - Complete KYC verification (required for live mode)
   - Activate your account

2. **API Keys**
   - Go to Dashboard ’ Settings ’ API Keys
   - Generate API keys for Test Mode (for testing)
   - Generate API keys for Live Mode (after KYC approval)

## Plan Configuration Overview

PhysiologicPRISM has **6 subscription plans** with volume-based pricing:

| Plan | Users | Price (INR) | Price (USD) | AI Calls/Month | Patient Limit | Voice Minutes |
|------|-------|-------------|-------------|----------------|---------------|---------------|
| Solo Professional | 1 | ¹4,200 | $50 | 250 | Unlimited | 120 min |
| Team (5 Users) | 5 | ¹19,999 | $238 | 1,250 (250/user) | Unlimited | 600 min |
| Team Pro (10 Users) | 10 | ¹37,799 | $450 | 2,500 (250/user) | Unlimited | 1,200 min |
| Institute (15 Users) | 15 | ¹53,599 | $638 | 3,750 (250/user) | Unlimited | 1,800 min |
| Institute Plus (20 Users) | 20 | ¹71,399 | $850 | 5,000 (250/user) | Unlimited | 2,400 min |
| Free Trial | 1 | ¹0 | $0 | 25 | 5 patients | 30 min |

**Volume Discounts:**
- 5 users: 5% discount ($47.50/user vs $50/user base)
- 10 users: 10% discount ($45/user)
- 15-20 users: 15% discount ($42.50/user)

## Step 1: Create Subscription Plans in Razorpay

### 1.1 Login to Razorpay Dashboard

1. Go to https://dashboard.razorpay.com/
2. Login with your credentials
3. Switch to **Test Mode** for initial setup

### 1.2 Navigate to Subscriptions

1. Click **Subscriptions** in the left sidebar
2. Click **Plans** tab
3. Click **+ Create Plan** button

### 1.3 Create Each Plan

For each plan, create **TWO versions** - one for INR and one for USD (for international customers):

---

#### **Plan 1: Solo Professional (INR)**

- **Plan Name:** `Solo Professional - INR`
- **Plan ID:** `solo_inr` (auto-generated, save this for later)
- **Billing Frequency:** Monthly
- **Billing Amount:** `420000` (¹4,200 in paise)
- **Currency:** INR
- **Trial Period:** 0 days (Free trial handled separately in app)
- **Description:** Unlimited patients, 250 AI calls/month, 120 min voice typing
- Click **Create Plan**

#### **Plan 1b: Solo Professional (USD)**

- **Plan Name:** `Solo Professional - USD`
- **Plan ID:** `solo_usd`
- **Billing Frequency:** Monthly
- **Billing Amount:** `5000` ($50.00 in cents)
- **Currency:** USD
- **Trial Period:** 0 days
- **Description:** Unlimited patients, 250 AI calls/month, 120 min voice typing
- Click **Create Plan**

---

#### **Plan 2: Team (5 Users) - INR**

- **Plan Name:** `Team (5 Users) - INR`
- **Plan ID:** `team_5_inr`
- **Billing Frequency:** Monthly
- **Billing Amount:** `1999900` (¹19,999 in paise)
- **Currency:** INR
- **Description:** 5 users, unlimited patients, 1,250 AI calls/month, 600 min voice typing

#### **Plan 2b: Team (5 Users) - USD**

- **Plan Name:** `Team (5 Users) - USD`
- **Plan ID:** `team_5_usd`
- **Billing Frequency:** Monthly
- **Billing Amount:** `23800` ($238.00 in cents)
- **Currency:** USD
- **Description:** 5 users, unlimited patients, 1,250 AI calls/month, 600 min voice typing

---

#### **Plan 3: Team Pro (10 Users) - INR**

- **Plan Name:** `Team Pro (10 Users) - INR`
- **Plan ID:** `team_10_inr`
- **Billing Frequency:** Monthly
- **Billing Amount:** `3779900` (¹37,799 in paise)
- **Currency:** INR
- **Description:** 10 users, unlimited patients, 2,500 AI calls/month, 1,200 min voice typing

#### **Plan 3b: Team Pro (10 Users) - USD**

- **Plan Name:** `Team Pro (10 Users) - USD`
- **Plan ID:** `team_10_usd`
- **Billing Frequency:** Monthly
- **Billing Amount:** `45000` ($450.00 in cents)
- **Currency:** USD
- **Description:** 10 users, unlimited patients, 2,500 AI calls/month, 1,200 min voice typing

---

#### **Plan 4: Institute (15 Users) - INR**

- **Plan Name:** `Institute (15 Users) - INR`
- **Plan ID:** `institute_15_inr`
- **Billing Frequency:** Monthly
- **Billing Amount:** `5359900` (¹53,599 in paise)
- **Currency:** INR
- **Description:** 15 users, unlimited patients, 3,750 AI calls/month, 1,800 min voice typing

#### **Plan 4b: Institute (15 Users) - USD**

- **Plan Name:** `Institute (15 Users) - USD`
- **Plan ID:** `institute_15_usd`
- **Billing Frequency:** Monthly
- **Billing Amount:** `63800` ($638.00 in cents)
- **Currency:** USD
- **Description:** 15 users, unlimited patients, 3,750 AI calls/month, 1,800 min voice typing

---

#### **Plan 5: Institute Plus (20 Users) - INR**

- **Plan Name:** `Institute Plus (20 Users) - INR`
- **Plan ID:** `institute_20_inr`
- **Billing Frequency:** Monthly
- **Billing Amount:** `7139900` (¹71,399 in paise)
- **Currency:** INR
- **Description:** 20 users, unlimited patients, 5,000 AI calls/month, 2,400 min voice typing

#### **Plan 5b: Institute Plus (20 Users) - USD**

- **Plan Name:** `Institute Plus (20 Users) - USD`
- **Plan ID:** `institute_20_usd`
- **Billing Frequency:** Monthly
- **Billing Amount:** `85000` ($850.00 in cents)
- **Currency:** USD
- **Description:** 20 users, unlimited patients, 5,000 AI calls/month, 2,400 min voice typing

---

## Step 2: Save Plan IDs

After creating each plan, Razorpay will generate a **Plan ID** (e.g., `plan_MXXXxxxXXXxxx`).

**Save these IDs** - you'll need them for environment variables.

## Step 3: Configure Environment Variables

Add these environment variables to your deployment environment (Azure Container Apps, Docker, etc.):

```bash
# Razorpay API Credentials
RAZORPAY_KEY_ID=rzp_test_XXXXXXXXXXXXXXXX          # Test mode key (replace with live key in production)
RAZORPAY_KEY_SECRET=YOUR_SECRET_KEY_HERE            # Test mode secret (replace with live secret in production)
RAZORPAY_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET_HERE    # For webhook signature verification

# Razorpay Plan IDs (replace with your actual plan IDs from Step 2)

# INR Plans (for Indian customers)
RAZORPAY_PLAN_SOLO=plan_XXXXXXXXXXXXX              # Solo Professional - INR
RAZORPAY_PLAN_TEAM_5=plan_XXXXXXXXXXXXX            # Team (5 Users) - INR
RAZORPAY_PLAN_TEAM_10=plan_XXXXXXXXXXXXX           # Team Pro (10 Users) - INR
RAZORPAY_PLAN_INSTITUTE_15=plan_XXXXXXXXXXXXX      # Institute (15 Users) - INR
RAZORPAY_PLAN_INSTITUTE_20=plan_XXXXXXXXXXXXX      # Institute Plus (20 Users) - INR

# USD Plans (for international customers) - Optional
RAZORPAY_PLAN_SOLO_USD=plan_XXXXXXXXXXXXX          # Solo Professional - USD
RAZORPAY_PLAN_TEAM_5_USD=plan_XXXXXXXXXXXXX        # Team (5 Users) - USD
RAZORPAY_PLAN_TEAM_10_USD=plan_XXXXXXXXXXXXX       # Team Pro (10 Users) - USD
RAZORPAY_PLAN_INSTITUTE_15_USD=plan_XXXXXXXXXXXXX  # Institute (15 Users) - USD
RAZORPAY_PLAN_INSTITUTE_20_USD=plan_XXXXXXXXXXXXX  # Institute Plus (20 Users) - USD

# Free Trial Configuration (handled in-app, not in Razorpay)
FREE_TRIAL_ENABLED=true
FREE_TRIAL_DAYS=14
FREE_TRIAL_PATIENTS=5
FREE_TRIAL_AI_CALLS=25
FREE_TRIAL_VOICE_MINUTES=30
```

### How to Set Environment Variables in Azure Container Apps:

```bash
# Set all environment variables at once
az containerapp update \
  --name physiologic-prism \
  --resource-group your-resource-group \
  --set-env-vars \
    RAZORPAY_KEY_ID=rzp_test_XXXXXXXXXXXXXXXX \
    RAZORPAY_KEY_SECRET=YOUR_SECRET_KEY_HERE \
    RAZORPAY_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET_HERE \
    RAZORPAY_PLAN_SOLO=plan_XXXXXXXXXXXXX \
    RAZORPAY_PLAN_TEAM_5=plan_XXXXXXXXXXXXX \
    RAZORPAY_PLAN_TEAM_10=plan_XXXXXXXXXXXXX \
    RAZORPAY_PLAN_INSTITUTE_15=plan_XXXXXXXXXXXXX \
    RAZORPAY_PLAN_INSTITUTE_20=plan_XXXXXXXXXXXXX
```

## Step 4: Setup Webhook (for Automated Subscription Management)

Webhooks enable automatic subscription renewal, cancellation, and payment notifications.

### 4.1 Create Webhook in Razorpay

1. Go to **Settings ’ Webhooks** in Razorpay Dashboard
2. Click **+ Create New Webhook**
3. **Webhook URL:** `https://your-domain.com/webhook/razorpay`
4. **Alert Email:** Your email address
5. **Active Events:** Select the following:
   -  `subscription.activated`
   -  `subscription.charged` (renewals)
   -  `subscription.cancelled`
   -  `subscription.paused`
   -  `subscription.resumed`
   -  `payment.captured` (for one-time AI call pack purchases)
   -  `payment.failed`
6. **Secret:** Generate a strong random secret (save this for `RAZORPAY_WEBHOOK_SECRET`)
7. Click **Create Webhook**

### 4.2 Test Webhook

1. Use Razorpay's webhook testing tool to send test events
2. Check your application logs to verify webhook processing
3. Verify subscription status updates in your Cosmos DB

## Step 5: Create AI Call Packs (One-Time Purchases)

AI Call Packs are one-time purchases (not subscriptions). They don't require plan creation in Razorpay.

The app creates Razorpay Orders on-the-fly when users purchase AI call packs:

| Package | AI Calls | Price (INR) | Per Call Cost | Profit Margin |
|---------|----------|-------------|---------------|---------------|
| Starter | 25 | ¹325 | ¹13.00 | 93% |
| Regular | 50 | ¹599 | ¹11.98 | 92% |
| Popular | 100 | ¹1,099 | ¹10.99 | 92% |
| Professional | 250 | ¹2,499 | ¹9.99 | 91% |
| Enterprise | 500 | ¹4,499 | ¹8.99 | 90% |

**Cost per AI call:** ¹0.91 (Azure OpenAI GPT-4o with caching)

No action needed - these are handled automatically by the app via Razorpay Orders API.

## Step 6: Switch to Live Mode (Production)

  **Do this ONLY after thorough testing in Test Mode**

### 6.1 Activate Live Mode in Razorpay

1. Complete KYC verification
2. Get live mode API keys from Dashboard ’ Settings ’ API Keys
3. Recreate all plans in **Live Mode** (same steps as above)
4. Update webhook URL to production domain

### 6.2 Update Environment Variables

```bash
# Replace test keys with live keys
RAZORPAY_KEY_ID=rzp_live_XXXXXXXXXXXXXXXX           # Live key
RAZORPAY_KEY_SECRET=YOUR_LIVE_SECRET_KEY_HERE        # Live secret
RAZORPAY_WEBHOOK_SECRET=YOUR_LIVE_WEBHOOK_SECRET     # Live webhook secret

# Update plan IDs with live mode plan IDs
RAZORPAY_PLAN_SOLO=plan_XXXXXXXXXXXXX                # Live plan ID
# ... repeat for all plans
```

### 6.3 Production Checklist

- [ ] KYC verification completed
- [ ] Live API keys generated
- [ ] All 10 plans created in live mode (5 INR + 5 USD)
- [ ] Plan IDs saved and environment variables updated
- [ ] Webhook configured with production URL
- [ ] Webhook secret configured
- [ ] Test subscription created successfully
- [ ] Test payment processed successfully
- [ ] Subscription renewal working (webhook test)
- [ ] Invoice generation working
- [ ] AI quota tracking verified
- [ ] Voice quota tracking verified

## Step 7: Testing Checklist

### Test Mode Testing (Before Going Live)

1. **Free Trial Test**
   - [ ] New user gets 14-day free trial automatically
   - [ ] 5 patients limit enforced
   - [ ] 25 AI calls limit enforced
   - [ ] 30 min voice typing limit enforced
   - [ ] Trial expiry notification sent

2. **Subscription Upgrade Test**
   - [ ] User can upgrade from trial to Solo plan
   - [ ] Payment page loads correctly
   - [ ] Test payment succeeds (use Razorpay test cards)
   - [ ] Subscription activated via webhook
   - [ ] Quota updated to Solo limits (250 AI calls, unlimited patients)
   - [ ] Invoice generated and emailed

3. **AI Call Pack Purchase Test**
   - [ ] User can purchase AI call pack
   - [ ] Payment succeeds
   - [ ] Balance updated via webhook
   - [ ] AI calls deducted from pack when quota exhausted
   - [ ] Invoice generated

4. **Quota Enforcement Test**
   - [ ] AI calls tracked correctly (web + mobile)
   - [ ] Voice typing minutes tracked
   - [ ] Patient creation tracked
   - [ ] Quota exceeded error shown
   - [ ] Token balance used when quota exhausted

5. **Subscription Renewal Test**
   - [ ] Webhook receives `subscription.charged` event
   - [ ] Monthly quota reset to plan limits
   - [ ] Invoice generated for renewal
   - [ ] Email sent to user

6. **Cancellation Test**
   - [ ] User can cancel subscription
   - [ ] Razorpay subscription cancelled
   - [ ] Subscription remains active until period end
   - [ ] Analytics logged

## Troubleshooting

### Issue: "Razorpay client not initialized"

**Cause:** Environment variables not set
**Solution:** Verify `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are set correctly

### Issue: "Razorpay plan ID not found"

**Cause:** Plan ID environment variable not set
**Solution:** Check that `RAZORPAY_PLAN_SOLO` etc. are configured with actual plan IDs from Razorpay

### Issue: Webhook not receiving events

**Cause:** Webhook URL incorrect or secret mismatch
**Solution:**
1. Verify webhook URL is accessible from internet
2. Check webhook secret matches `RAZORPAY_WEBHOOK_SECRET`
3. Check Razorpay dashboard for webhook delivery logs

### Issue: Payment succeeds but subscription not activated

**Cause:** Webhook processing error
**Solution:** Check application logs for webhook errors. Verify webhook signature validation is working.

## Support

- **Razorpay Docs:** https://razorpay.com/docs/subscriptions/
- **Razorpay Support:** https://razorpay.com/support/
- **Test Cards:** https://razorpay.com/docs/payments/payments/test-card-details/

## Security Best Practices

1. **Never commit API keys to git** - Use environment variables only
2. **Use separate keys for test and live mode**
3. **Rotate keys periodically** (every 6 months)
4. **Enable 2FA on Razorpay account**
5. **Verify webhook signatures** (already implemented in code)
6. **Use HTTPS only** for webhook URLs
7. **Monitor failed payments** and suspicious activity
8. **Keep webhook secret secure** - don't share publicly

## Revenue & Profit Analysis

### Monthly Recurring Revenue (MRR) Projections

**10 Solo Customers:**
- Revenue: ¹42,000/month ($500 USD)
- AI Cost: ¹2,275 (10 users × 250 calls × ¹0.91)
- **Profit: ¹39,725 (95% margin)**

**5 Team (10 Users) Customers:**
- Revenue: ¹1,88,995/month ($2,250 USD)
- AI Cost: ¹11,375 (50 users × 250 calls × ¹0.91)
- **Profit: ¹1,77,620 (94% margin)**

**Total (mixed customer base):**
- MRR: ¹2,30,995 ($2,750 USD/month)
- Annual Revenue: ¹27,71,940 ($33,000 USD/year)
- **Profit Margin: 94%+**

### AI Call Pack Revenue (One-Time)

**100 Popular Packs sold per month:**
- Revenue: ¹1,09,900
- AI Cost: ¹9,100 (10,000 calls × ¹0.91)
- **Profit: ¹1,00,800 (92% margin)**

---

**Created:** March 2026
**Last Updated:** March 2026
**Version:** 1.0
