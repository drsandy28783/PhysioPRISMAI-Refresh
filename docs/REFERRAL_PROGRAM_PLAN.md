# PhysiologicPRISM Referral Program Plan

> **Version**: 1.0
> **Date**: April 7, 2026
> **Status**: Planning Phase
> **Owner**: Product Team

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Trial Structure](#current-trial-structure)
3. [Reward Structure](#reward-structure)
4. [Qualification Criteria](#qualification-criteria)
5. [User Experience Flow](#user-experience-flow)
6. [Technical Implementation](#technical-implementation)
7. [Cost-Benefit Analysis](#cost-benefit-analysis)
8. [Success Metrics](#success-metrics)
9. [Marketing & Promotion](#marketing--promotion)
10. [Anti-Abuse Measures](#anti-abuse-measures)
11. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

### Objective
Launch a referral program to incentivize early adopters to refer physiotherapists to PhysiologicPRISM, driving organic growth through word-of-mouth marketing.

### Key Principles
- ✅ **No cash rewards** - Platform credits and discounts only
- ✅ **Win-win rewards** - Both referrer and referred user benefit
- ✅ **Extended trials** - Give referred users more time to experience value
- ✅ **Simple & transparent** - Easy to understand and track
- ✅ **Scalable** - Rewards grow with user engagement

### Expected Impact
- **Target**: 100 successful referrals in Year 1
- **Projected ROI**: ~1,550% (₹3.45L cost → ₹57L revenue)
- **Referred user conversion rate**: 20-23% (vs. 12% standard)
- **Customer Acquisition Cost (CAC)**: ₹3,450 per customer (vs. paid ads ₹8,000+)

---

## Current Trial Structure

### Standard Free Trial
- **Duration**: 14 days
- **Patients Limit**: 5 patients
- **AI Calls Limit**: 25 AI calls
- **Voice Minutes**: 30 minutes
- **Credit Card**: Not required

### Configuration
```python
# From subscription_manager.py
FREE_TRIAL_DAYS = 14
FREE_TRIAL_PATIENTS = 5
FREE_TRIAL_AI_CALLS = 25
FREE_TRIAL_VOICE_MINUTES = 30
```

---

## Reward Structure

### For Referrer (Person Sharing the Code)

#### Milestone-Based Rewards

| Milestone | Reward Options (Choose One) | Value (₹) |
|-----------|----------------------------|-----------|
| **1st referral** | • ₹1,500 platform credit<br>• 20% off next renewal | ₹1,500<br>₹950 |
| **3rd referral** | • 1 month FREE subscription<br>• ₹5,000 platform credit | ₹4,750<br>₹5,000 |
| **5th referral** | • 2 months FREE<br>• "Champion" badge | ₹9,500 |
| **10th referral** | • 3 months FREE<br>• **Lifetime 15% discount** | ₹14,250 + ∞ |
| **20th referral** | • 6 months FREE<br>• **Lifetime 20% discount**<br>• Featured on website | ₹28,500 + ∞ |

#### Platform Credits Usage
Credits can be used for:
- ✅ Subscription renewals
- ✅ AI Call Packs purchase
- ✅ Upgrading to higher tiers
- ✅ Adding extra users (team plans)
- ❌ **NOT** withdrawable as cash

**Credit Expiry**: 12 months from earning date

---

### For Referred User (Person Using the Code)

#### Immediate Benefits on Signup

**1. Extended Trial Period**
- Standard: **14 days**
- With referral code: **21 days** (+7 days / 50% longer)

**2. Enhanced Trial Quotas**
| Resource | Standard | With Referral Code | Boost |
|----------|----------|-------------------|-------|
| Patients | 5 | **7** | +40% |
| AI Calls | 25 | **40** | +60% |
| Voice Minutes | 30 | **45** | +50% |

**3. First Subscription Discount**
- **10% off first paid subscription** (any plan)
- Auto-applied at checkout
- Example: Solo Plan ₹4,750 → ₹4,275 (save ₹475)

#### Visual Benefits Display
```
🎁 Referral Code Applied: PRISM-SANDY2025

Your Extended Trial Benefits:
✓ 21-day trial (vs. standard 14 days)
✓ 7 patients to test with (vs. 5)
✓ 40 AI assists (vs. 25)
✓ 45 minutes voice typing (vs. 30)
✓ 10% off your first month!

Value of benefits: ₹1,500+
```

---

## Qualification Criteria

### When Does a Referral Count as "Successful"?

A referral is marked as **qualified** when ALL conditions are met:

1. ✅ **Signup**: Referred user creates account with valid referral code
2. ✅ **Conversion**: User converts from trial to paid subscription (any plan)
3. ✅ **Retention**: User stays active for minimum **30 days** after first payment
4. ✅ **Usage Threshold**: During trial, user must:
   - Create at least **2 patients** (shows genuine usage)
   - Use at least **10 AI calls** (shows feature adoption)

### Referral Status Flow

```
Pending → Qualified → Rewarded
   ↓
Cancelled (if user doesn't convert or churns within 30 days)
```

**Timeline:**
- Day 0: User signs up (status: `pending`)
- Day 1-21: User in extended trial (status: `pending`)
- Day 22: User subscribes (status: `qualified`)
- Day 52: User completes 30 days (status: `rewarded` - referrer gets reward)

---

## Tier System & Status Perks

Beyond just credits/discounts, users earn **status tiers** with real benefits:

| Tier | Referrals | Title | Badge | Special Benefits |
|------|-----------|-------|-------|------------------|
| 🥉 **Bronze** | 1-2 | Early Adopter | 🥉 | • Priority support queue |
| 🥈 **Silver** | 3-4 | Ambassador | 🥈 | • Exclusive webinar access<br>• Beta feature early access |
| 🥇 **Gold** | 5-9 | Champion | 🥇 | • Featured testimonial opportunity<br>• Direct access to product roadmap |
| 💎 **Platinum** | 10-19 | Elite | 💎 | • Lifetime 15% discount<br>• Direct line to founder<br>• Input on new features |
| 💠 **Diamond** | 20+ | Legend | 💠 | • Lifetime 20% discount<br>• Co-marketing opportunities<br>• Annual VIP dinner invite<br>• Revenue sharing discussion |

---

## User Experience Flow

### Step 1: Referrer Gets Their Code

**Location**: Dashboard → Referrals tab

**UI Elements:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Your Referral Program
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your Unique Referral Code: PRISM-SANDY2025

[Copy Code] [Share via WhatsApp] [Share via Email]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Your Stats
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Successful Referrals: 7
Pending (in trial): 2
Total Rewards Earned: ₹12,500

Your Status: 🥇 GOLD CHAMPION
Next Milestone: 3 more referrals = 2 FREE months!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Available Rewards
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Platform Credits: ₹3,500
Free Months Earned: 1 month

[Apply Credit to Next Invoice] [Redeem Free Month]
```

---

### Step 2: Referrer Shares Code

**Pre-written Share Templates:**

#### WhatsApp Message
```
Hey! I've been using PhysiologicPRISM for my physio practice and it's
been a game-changer for clinical documentation.

Use my referral code PRISM-SANDY2025 when you sign up and you'll get:
✓ 21-day trial (instead of 14)
✓ 7 patients to test with
✓ 40 AI assists
✓ 10% off your first month

Try it out: physiologicprism.com/register
```

#### Email Template
```
Subject: Try PhysiologicPRISM - Extended Trial + Discount

Hi [Name],

I wanted to share a clinical tool that's made my documentation workflow
much easier. PhysiologicPRISM uses AI to help structure patient
assessments while maintaining clinical reasoning.

If you sign up with my referral code, you get extra benefits:
- Extended 21-day trial (vs. standard 14 days)
- More patients and AI calls to test
- 10% off your first subscription

Code: PRISM-SANDY2025
Sign up: physiologicprism.com/register

Let me know if you have questions!

Best,
[Your Name]
```

---

### Step 3: Referred User Signs Up

**Registration Page Changes:**

Add optional field:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Email: [                    ]
🔒 Password: [                 ]

🎁 Have a referral code? (Optional)
   [PRISM-SANDY2025         ] [Apply]

   ✓ Code applied! You'll get 21-day trial + 10% off
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**After code validation:**
- Show benefits preview
- Display referrer's name (for trust): "Referred by Dr. Sandy"
- Highlight trial extensions clearly

---

### Step 4: Trial Period (21 Days)

**Email Sequence for Referred Users:**

**Day 1**: Welcome + Benefits Reminder
```
Subject: Welcome to PhysiologicPRISM - Your Extended Trial Starts Now!

You have 21 days to explore:
✓ Create up to 7 patients
✓ Use 40 AI-powered clinical assists
✓ 45 minutes of voice-to-text

Plus, you'll get 10% off when you subscribe!
```

**Day 7**: Mid-trial check-in
**Day 14**: Trial ending soon (7 days left)
**Day 18**: Last chance (3 days left) + discount reminder
**Day 21**: Trial ending today - Subscribe with 10% off

---

### Step 5: Conversion & Reward

**User subscribes → Auto-apply 10% discount**

Checkout screen shows:
```
Solo Professional Plan
Monthly: ₹4,750

Referral Discount (10%): -₹475
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Today: ₹4,275

Next billing: ₹4,750 (full price from 2nd month)
```

**After 30 days of active subscription:**
- Referrer gets notification: "🎉 Your referral succeeded! Rewards unlocked."
- Referrer can now redeem rewards in dashboard

---

## Technical Implementation

### Database Schema

#### 1. `referral_codes` Table

```sql
{
  "id": "string",           // Unique code ID
  "code": "string",          // e.g., "PRISM-SANDY2025"
  "user_id": "string",       // Owner of the code
  "created_date": "datetime",
  "is_active": "boolean",    // Can be disabled if needed
  "total_signups": "int",    // Total users who used code
  "total_conversions": "int", // Successful paid conversions
  "total_qualified": "int",   // Qualified after 30 days
  "total_rewards_earned": "float", // In ₹
  "expiry_date": "datetime"  // Optional expiry
}
```

**Indexes**: `code` (unique), `user_id`

---

#### 2. `referral_tracking` Table

```sql
{
  "id": "string",
  "referral_code_id": "string", // FK to referral_codes
  "referrer_user_id": "string", // Person who shared code
  "referred_user_id": "string", // Person who used code
  "signup_date": "datetime",
  "trial_start_date": "datetime",
  "trial_end_date": "datetime",
  "conversion_date": "datetime",  // When they subscribed
  "qualification_date": "datetime", // After 30 days retention
  "status": "string",  // pending/qualified/rewarded/cancelled
  "reward_amount": "float",
  "reward_type": "string",  // credit/discount/free_month
  "subscription_plan": "string",  // Plan they chose
  "usage_stats": {
    "patients_created": "int",
    "ai_calls_used": "int",
    "trial_days_used": "int"
  }
}
```

**Indexes**: `referred_user_id` (unique - one referral per user), `referrer_user_id`, `status`

---

#### 3. `referral_rewards` Table

```sql
{
  "id": "string",
  "user_id": "string",  // Recipient of reward
  "referral_tracking_id": "string", // FK
  "reward_type": "string",  // credit/discount/free_month
  "reward_value": "float",  // Amount in ₹
  "earned_date": "datetime",
  "applied_date": "datetime",  // When redeemed
  "expiry_date": "datetime",  // 12 months from earned
  "status": "string",  // pending/applied/expired
  "applied_to": "string"  // subscription_id or invoice_id
}
```

**Indexes**: `user_id`, `status`

---

#### 4. Extend `subscriptions` Table

Add fields:
```sql
{
  "referred_by_code": "string",  // Referral code used
  "referral_discount_applied": "boolean",
  "trial_extension_days": "int",  // 0 or 7
  "trial_quota_boost": "object" {
    "patients": 7,
    "ai_calls": 40,
    "voice_minutes": 45
  }
}
```

---

### Code Generation Logic

**Referral Code Format**: `PRISM-{USERNAME}{YEAR}`

**Examples**:
- `PRISM-SANDY2025`
- `PRISM-AMIT2025`
- `PRISM-PRIYA2025`

**Generation Function**:
```python
def generate_referral_code(user_id, user_name):
    """
    Generate unique referral code for user
    """
    import re
    from datetime import datetime

    # Clean username (remove special chars, take first 10 chars)
    clean_name = re.sub(r'[^A-Za-z0-9]', '', user_name)[:10].upper()
    year = datetime.now().year

    base_code = f"PRISM-{clean_name}{year}"

    # Check if exists, add suffix if needed
    code = base_code
    suffix = 1
    while referral_code_exists(code):
        code = f"{base_code}-{suffix}"
        suffix += 1

    return code
```

**Alternative**: Random codes like `PRISM-X7K9M2` for privacy

---

### Reward Calculation Logic

**Algorithm**:
```python
def calculate_referral_reward(referrer_user_id, milestone):
    """
    Calculate reward based on milestone reached
    """
    successful_referrals = get_successful_referral_count(referrer_user_id)

    rewards = {
        1: {"credit": 1500, "discount_pct": 20},
        3: {"free_months": 1, "credit": 5000},
        5: {"free_months": 2, "badge": "Champion"},
        10: {"free_months": 3, "lifetime_discount": 15},
        20: {"free_months": 6, "lifetime_discount": 20}
    }

    if successful_referrals in rewards:
        return rewards[successful_referrals]

    return None
```

---

### Trial Extension Implementation

**On signup with referral code**:
```python
def create_trial_subscription_with_referral(user_id, referral_code):
    """
    Create trial subscription with extended benefits
    """
    # Validate referral code
    referral = validate_referral_code(referral_code)
    if not referral:
        return create_standard_trial(user_id)

    # Extended trial
    trial_end = datetime.now() + timedelta(days=21)  # vs. 14

    subscription = {
        'user_id': user_id,
        'plan_type': 'free_trial',
        'status': 'trial',
        'trial_end': trial_end,
        'patients_limit': 7,  # vs. 5
        'ai_calls_limit': 40,  # vs. 25
        'voice_minutes_limit': 45,  # vs. 30
        'referred_by_code': referral_code,
        'referral_discount_pending': True,  # Apply 10% on conversion
        'created_date': datetime.now()
    }

    # Track referral
    create_referral_tracking(
        referral_code_id=referral['id'],
        referrer_user_id=referral['user_id'],
        referred_user_id=user_id,
        status='pending'
    )

    return subscription
```

---

### Discount Application at Checkout

**When trial user converts**:
```python
def apply_referral_discount(user_id, subscription_plan):
    """
    Apply 10% discount to first month if referred
    """
    subscription = get_current_subscription(user_id)

    if subscription.get('referred_by_code') and subscription.get('referral_discount_pending'):
        plan_price = get_plan_price(subscription_plan)
        discount = plan_price * 0.10

        # Create one-time discount
        create_discount_coupon(
            user_id=user_id,
            discount_amount=discount,
            reason="Referral discount - first month 10% off",
            valid_until=datetime.now() + timedelta(days=30)
        )

        # Mark as applied
        update_subscription(user_id, {
            'referral_discount_pending': False,
            'referral_discount_applied': True
        })

        return discount

    return 0
```

---

### Qualification Check (After 30 Days)

**Cron job runs daily**:
```python
def check_referral_qualification():
    """
    Check if referred users have completed 30 days and qualify referrer for reward
    """
    # Get all pending referrals
    pending_referrals = get_referrals_by_status('qualified')

    for referral in pending_referrals:
        # Check if 30 days have passed since conversion
        if referral.conversion_date + timedelta(days=30) <= datetime.now():
            # Check if user is still active
            subscription = get_subscription(referral.referred_user_id)

            if subscription['status'] == 'active':
                # Qualify the referral
                update_referral_status(referral.id, 'rewarded')

                # Credit referrer
                issue_referral_reward(
                    user_id=referral.referrer_user_id,
                    referral_id=referral.id
                )

                # Send notifications
                send_referral_success_email(referral.referrer_user_id)
            else:
                # User cancelled - mark referral as failed
                update_referral_status(referral.id, 'cancelled')
```

---

## Cost-Benefit Analysis

### Scenario: 100 Successful Referrals in Year 1

#### Cost Breakdown

| Cost Component | Calculation | Amount (₹) | Amount ($) |
|----------------|-------------|-----------|-----------|
| **Referrer Platform Credits** | 100 × ₹1,500 avg | ₹1,50,000 | $1,785 |
| **Referred User Discounts** | 100 × ₹475 (10% of ₹4,750) | ₹47,500 | $565 |
| **Free Months Issued** | ~30 months @ ₹4,750 | ₹1,42,500 | $1,695 |
| **Extended Trial Costs** | Cloud/infrastructure only | ₹5,000 | $60 |
| **TOTAL COST** | | **₹3,45,000** | **$4,105** |

**Note**: All costs are **deferred revenue**, not cash outflows. No actual money leaves the business.

---

#### Revenue Gain

| Revenue Component | Calculation | Amount (₹) | Amount ($) |
|-------------------|-------------|-----------|-----------|
| **New User Revenue (Year 1)** | 100 × ₹4,750/mo × 12 mo | ₹57,00,000 | $67,857 |
| **Less: Costs** | From above | -₹3,45,000 | -$4,105 |
| **NET GAIN (Year 1)** | | **₹53,55,000** | **$63,750** |

**Retention projection**: If 70% retain into Year 2, that's ₹39,90,000 recurring revenue.

---

#### ROI Calculation

```
ROI = (Revenue - Cost) / Cost × 100
    = (₹57,00,000 - ₹3,45,000) / ₹3,45,000 × 100
    = 1,552%
```

**Customer Acquisition Cost (CAC)**:
```
CAC = Total Cost / New Customers
    = ₹3,45,000 / 100
    = ₹3,450 per customer
```

**Comparison to Paid Ads**:
- Google Ads CAC: ₹8,000-12,000
- Facebook Ads CAC: ₹6,000-10,000
- **Referral CAC: ₹3,450** ✅ (58-71% cheaper!)

---

#### Conversion Rate Analysis

| User Type | Trial Length | Conversion Rate | Avg LTV (12 mo) |
|-----------|--------------|-----------------|-----------------|
| **Organic User** | 14 days | 12% | ₹57,000 |
| **Referred User** | 21 days | 20-23% | ₹57,000 |

**Why referred users convert better**:
1. ✅ Longer trial (21 vs 14 days) = More time to see value
2. ✅ Higher trial quotas = Better product experience
3. ✅ Social proof (trusted referral from peer)
4. ✅ Discount incentive (10% off)
5. ✅ Pre-qualified (referred by active user)

---

## Success Metrics

### Primary KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Referral Participation Rate** | 25% | % of active users who share their code |
| **Referred User Conversion Rate** | 20% | % of referred signups who become paid |
| **Viral Coefficient** | >0.5 | (Referrers × Conversion) per user |
| **Average Referrals per Active Referrer** | 3-5 | Total referrals / Active referrers |
| **Reward Redemption Rate** | >80% | % of earned rewards actually used |
| **30-Day Retention (Referred Users)** | >75% | % who stay past 30 days |

---

### Secondary KPIs

| Metric | Description | How to Track |
|--------|-------------|--------------|
| **Code Share Rate** | % who share code at least once | Track share button clicks |
| **Multi-referrer Rate** | % who refer 3+ people | Users with 3+ successful referrals |
| **Reward Type Preference** | Credit vs. Free month vs. Discount | Which rewards are chosen most |
| **Referred User LTV** | Lifetime value of referred users | Compare to organic user LTV |
| **Time to First Referral** | Days from signup to first share | Avg days between signup and share |

---

### Tracking Dashboard (Admin)

**Metrics to Display**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Referral Program Analytics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overview (Last 30 Days)
• Total Referral Codes Generated: 250
• Active Referrers: 125 (50% participation)
• Total Signups via Referral: 85
• Successful Conversions: 23 (27% conversion)
• Total Rewards Issued: ₹45,000

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Top Referrers (All Time)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Dr. Sandy (PRISM-SANDY2025): 15 conversions
2. Dr. Amit (PRISM-AMIT2025): 12 conversions
3. Dr. Priya (PRISM-PRIYA2025): 8 conversions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Conversion Funnel
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Code Shared: 300
 ↓ Signups: 85 (28%)
 ↓ Trial Completion: 60 (71%)
 ↓ Paid Conversion: 23 (27%)
 ↓ 30-Day Retention: 18 (78%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Financial Impact
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Revenue from Referred Users: ₹12,50,000
Total Rewards Cost: ₹75,000
Net Gain: ₹11,75,000
ROI: 1,567%
```

---

## Marketing & Promotion

### Launch Campaign

#### Phase 1: Announce to Existing Users (Week 1)

**Email Blast**:
```
Subject: 🎁 New Referral Program - Earn FREE Months!

Hi [Name],

Great news! We're launching our Early Adopter Referral Program.

When you refer a fellow physiotherapist who subscribes:
• You get ₹1,500 credit or 20% off your next renewal
• They get 21-day trial + 10% off first month

Your unique code: PRISM-SANDY2025

[Start Referring] [Learn More]

Plus, first 50 referrers get DOUBLE rewards! 🎉
```

**In-App Banner**:
- Top banner on dashboard for first week
- "New: Refer & Earn - Get Started →"

**Blog Post**:
- Title: "Introducing Early Adopter Rewards: Help Physios, Get Rewarded"
- Explain program details, success stories, FAQs

---

#### Phase 2: Ongoing Promotion

**1. Dashboard Widget** (Persistent)
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Refer a Colleague
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Share PRISM and earn rewards!

Your code: PRISM-SANDY2025 [Copy]

2 referrals away from a FREE month!
[Learn More]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**2. Email Reminders**
- Monthly newsletter: "Referral spotlight" section
- Post-trial conversion email: "Love PRISM? Share with colleagues"
- Invoice emails: "Reduce your bill by referring"

**3. Social Proof**
- Success stories: "Dr. X referred 10 colleagues and saved ₹20,000"
- Leaderboard (optional, with user permission)
- Testimonials from referrers

---

#### Phase 3: Special Campaigns

**Quarterly Challenges**:
```
🏆 Q1 Referral Challenge!

Top 10 referrers this quarter win:
1st Place: 6 months FREE
2nd-3rd: 3 months FREE
4th-10th: 1 month FREE

Current leaders:
1. Dr. Sandy - 8 referrals
2. Dr. Amit - 6 referrals
3. Dr. Priya - 5 referrals

[View Full Leaderboard]
```

**Time-limited Bonuses**:
- "Double rewards week" - Refer in next 7 days, get 2x credits
- "New year boost" - January referrals get extra month free

---

### Content Marketing

**Blog Posts**:
1. "How Dr. Sandy Saved ₹15,000 Through Our Referral Program"
2. "5 Easy Ways to Share PhysiologicPRISM with Colleagues"
3. "Why Referred Users Convert 2x Better (Data Analysis)"

**Social Media**:
- LinkedIn posts highlighting top referrers
- Instagram stories showing reward redemption
- Facebook community posts about success stories

---

## Anti-Abuse Measures

### Fraud Prevention Rules

#### 1. Signup Validation
```python
# Prevent self-referrals
if referred_email_domain == referrer_email_domain:
    if same_organization:
        allow()  # Legitimate (same clinic)
    else:
        flag_for_review()

# Prevent fake signups
if suspicious_patterns:
    require_phone_verification()
```

**Checks**:
- ❌ Same IP address for referrer and referred
- ❌ Same payment method
- ❌ Disposable email domains
- ❌ Multiple signups from same device fingerprint

---

#### 2. Usage Validation

**Minimum trial activity required**:
```python
def validate_genuine_usage(user_id):
    stats = get_trial_usage_stats(user_id)

    if stats['patients_created'] < 2:
        return False  # Not a real user

    if stats['ai_calls_used'] < 10:
        return False  # Didn't use key features

    if stats['trial_days_active'] < 7:
        return False  # Didn't engage enough

    return True
```

---

#### 3. Referral Limits

**Per user**:
- Max **50 referrals** per account (lifetime)
- Max **10 pending referrals** at once
- Max **5 referrals per month** (prevents spam)

**Per referred user**:
- Can only use **1 referral code** (first one entered)
- Cannot switch codes after signup

---

#### 4. Geographic/Pattern Analysis

**Flag for review if**:
- All referrals from same small town (population < 10,000)
- All signups within 24 hours
- Referrer creates patterns of refer → cancel → refer
- Payment failures on multiple referred accounts

---

#### 5. Reward Clawback

**If fraud detected**:
```python
def handle_fraudulent_referral(referral_id):
    # Revoke reward
    revoke_reward(referral_id)

    # Update referral status
    update_referral_status(referral_id, 'cancelled_fraud')

    # Deduct from user's balance if already used
    deduct_credits(user_id, amount)

    # Flag user account
    flag_account_for_review(user_id)

    # Send notification
    notify_admin_of_fraud(referral_id)
```

---

#### 6. Manual Review Triggers

**Send to manual review queue if**:
- User reaches 10+ referrals (rare, needs verification)
- 3+ chargebacks on referred user accounts
- Multiple referrals from same credit card
- Referral spike (5+ in 24 hours)

---

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)

**Tasks**:
- [ ] Create database schema
  - [ ] `referral_codes` table
  - [ ] `referral_tracking` table
  - [ ] `referral_rewards` table
  - [ ] Extend `subscriptions` table
- [ ] Build referral code generator
- [ ] Implement trial extension logic
- [ ] Add referral code field to signup form
- [ ] Create basic validation functions

**Deliverable**: Users can signup with referral codes and get extended trials

---

### Phase 2: Tracking & Rewards (Week 3-4)

**Tasks**:
- [ ] Build referral tracking system
  - [ ] Track signup → conversion → qualification
  - [ ] Status management (pending/qualified/rewarded)
- [ ] Implement reward calculation logic
- [ ] Create reward issuance system
  - [ ] Platform credits
  - [ ] Free month vouchers
  - [ ] Discount application
- [ ] Build cron job for qualification check (30-day retention)
- [ ] Add email notifications
  - [ ] Referrer: "Your referral signed up"
  - [ ] Referrer: "Your referral qualified - reward unlocked!"
  - [ ] Referred: "Welcome - extended trial benefits"

**Deliverable**: Full referral lifecycle tracked, rewards automatically issued

---

### Phase 3: User Dashboard (Week 5-6)

**Tasks**:
- [ ] Create referral dashboard page
  - [ ] Display unique referral code
  - [ ] Show referral stats (pending/qualified/total)
  - [ ] List recent referrals with status
  - [ ] Display available rewards
  - [ ] Show tier/badge status
- [ ] Add reward redemption UI
  - [ ] Apply credits to invoice
  - [ ] Redeem free months
  - [ ] View reward history
- [ ] Build share functionality
  - [ ] Copy code button
  - [ ] WhatsApp share
  - [ ] Email share (pre-filled templates)
  - [ ] Social media share

**Deliverable**: Users can view stats and redeem rewards

---

### Phase 4: Admin Tools (Week 7)

**Tasks**:
- [ ] Build admin analytics dashboard
  - [ ] Program overview metrics
  - [ ] Top referrers leaderboard
  - [ ] Conversion funnel visualization
  - [ ] Financial impact tracking
- [ ] Create fraud detection tools
  - [ ] Flagged referrals queue
  - [ ] Manual review interface
  - [ ] Reward clawback function
- [ ] Add admin controls
  - [ ] Disable/enable codes
  - [ ] Manually issue rewards
  - [ ] Adjust qualification criteria

**Deliverable**: Admin can monitor and manage program

---

### Phase 5: Marketing & Launch (Week 8)

**Tasks**:
- [ ] Write launch announcement email
- [ ] Create blog post explaining program
- [ ] Add dashboard banner/widget
- [ ] Prepare social media content
- [ ] Update help docs/FAQs
- [ ] Set up tracking analytics (Google Analytics events)
- [ ] Soft launch to 10% of users
- [ ] Monitor for issues
- [ ] Full launch to all users

**Deliverable**: Program live and promoted

---

### Phase 6: Optimization (Week 9+)

**Tasks**:
- [ ] A/B test reward structures
  - [ ] Test different discount percentages
  - [ ] Test trial extension durations
- [ ] Analyze conversion data
- [ ] Gather user feedback
- [ ] Iterate on UI/UX
- [ ] Add gamification elements
  - [ ] Achievement badges
  - [ ] Progress bars
  - [ ] Milestone celebrations
- [ ] Create quarterly challenges

**Deliverable**: Optimized, high-performing referral program

---

## Success Stories & Use Cases

### Scenario 1: Solo Practitioner

**Dr. Sandy** (Solo Professional Plan, ₹4,750/month)

**Timeline**:
- Month 1: Refers 2 colleagues → Earns ₹3,000 credits
- Month 3: Refers 3rd colleague → Gets 1 FREE month (saves ₹4,750)
- Month 6: Refers 5th colleague → Gets 2 FREE months + Champion badge
- Month 12: Refers 10th colleague → Gets 3 FREE months + Lifetime 15% discount

**Total Value in Year 1**:
- 6 free months = ₹28,500
- Lifetime 15% discount = ₹713/month ongoing
- Platform credits = ₹3,000
- **Total: ₹31,500+ in Year 1, then ₹8,556/year forever**

---

### Scenario 2: Clinic Owner

**Dr. Amit** (Team 5 Plan, ₹19,999/month)

**Strategy**: Refers other clinic owners in his city

**Timeline**:
- Month 1: Refers 2 clinics → Earns ₹3,000 credits (uses for AI packs)
- Month 2: Refers 3rd clinic → Gets 1 FREE month (saves ₹19,999)
- Month 4: Refers 5th clinic → Gets 2 FREE months (saves ₹39,998)
- Month 8: Refers 10th clinic → Gets 3 FREE months + Lifetime 15% discount

**Total Value in Year 1**:
- 6 free months = ₹1,19,994
- Lifetime 15% discount = ₹3,000/month ongoing
- **Total: ₹1,22,994 in Year 1, then ₹36,000/year forever**

---

### Scenario 3: University Professor

**Dr. Priya** (Solo Plan, ₹4,750/month)

**Strategy**: Recommends to students graduating as physiotherapists

**Timeline**:
- Refers 25 students over 6 months
- 8 convert to paid (32% conversion - high because of trust)
- Reaches Gold tier → Champion badge

**Total Value**:
- Month 3: 1 FREE month
- Month 5: 2 FREE months
- Month 6: 3 FREE months + Lifetime 15% discount
- Total: 6 FREE months + ongoing ₹713/month discount
- **Plus featured on website as "Ambassador"**

---

## Frequently Asked Questions (FAQs)

### For Referrers

**Q: How do I get my referral code?**
A: Go to Dashboard → Referrals tab. Your unique code is displayed at the top.

**Q: How many people can I refer?**
A: Up to 50 total. Max 5 per month to prevent spam.

**Q: When do I get my reward?**
A: After the referred user subscribes and stays active for 30 days.

**Q: Can I choose between credits and free months?**
A: Yes! At certain milestones, you can choose your preferred reward type.

**Q: Do credits expire?**
A: Yes, after 12 months. But lifetime discounts never expire!

**Q: Can I refer someone from the same clinic?**
A: Yes, that's fine. Just not yourself from a different email.

---

### For Referred Users

**Q: Where do I enter a referral code?**
A: On the registration page, there's an optional "Referral Code" field.

**Q: Can I use a code after signing up?**
A: No, codes must be entered during signup.

**Q: What if my trial is already active?**
A: Unfortunately, referral codes can't be applied retroactively.

**Q: Does the 10% discount apply every month?**
A: No, only the first month. But you still get the extended trial benefits!

**Q: Can I use multiple referral codes?**
A: No, only one code per account.

---

### General

**Q: What happens if the referred user cancels?**
A: If they cancel within 30 days, the referral doesn't qualify and no reward is given.

**Q: Are there any restrictions on who I can refer?**
A: They must be a physiotherapist and a new user (not an existing customer).

**Q: Can corporate/institute customers participate?**
A: Yes! Higher plan values mean bigger rewards.

---

## Appendix

### A. Email Templates

#### Referral Success Email (to Referrer)
```
Subject: 🎉 Great News! Your Referral Just Subscribed

Hi [Referrer Name],

Congratulations! [Referred Name] just subscribed to PhysiologicPRISM
using your referral code.

Once they complete 30 days as an active subscriber, you'll receive:
• ₹1,500 platform credits OR
• 20% off your next renewal

Track your referral status: [Dashboard Link]

Thanks for spreading the word!

Best,
The PhysiologicPRISM Team
```

---

#### Reward Unlocked Email (to Referrer)
```
Subject: 💰 Reward Unlocked! ₹1,500 Credits Earned

Hi [Referrer Name],

Your reward is ready! [Referred Name] has been an active subscriber
for 30 days, so your referral is now qualified.

You've earned: ₹1,500 Platform Credits

These credits can be used for:
✓ Subscription renewals
✓ AI Call Packs
✓ Upgrading your plan

Redeem now: [Dashboard Link]

Credits expire in 12 months, so don't wait!

Keep referring to unlock bigger rewards:
• 3 referrals = 1 FREE month
• 5 referrals = 2 FREE months
• 10 referrals = Lifetime 15% discount!

Best,
The PhysiologicPRISM Team
```

---

#### Welcome Email (to Referred User)
```
Subject: Welcome to PhysiologicPRISM - Your Extended Trial Starts Now! 🎁

Hi [Referred Name],

Welcome! You signed up with [Referrer Name]'s referral code, so
you're getting exclusive benefits:

✓ 21-day trial (vs. standard 14 days)
✓ 7 patients to test with (vs. 5)
✓ 40 AI assists (vs. 25)
✓ 10% off your first subscription

Make the most of your extended trial:
1. Create your first patient
2. Try the AI clinical reasoning assistant
3. Generate a PDF report

[Get Started]

Questions? Reply to this email anytime.

Best,
The PhysiologicPRISM Team
```

---

### B. Share Message Templates

#### WhatsApp Template (Short)
```
Hey! Check out PhysiologicPRISM - it's helped me streamline my clinical
documentation.

Use code PRISM-SANDY2025 for:
✓ 21-day trial
✓ 10% off first month

Sign up: physiologicprism.com/register
```

---

#### LinkedIn Post Template
```
I've been using PhysiologicPRISM for [X months] and it's transformed
my clinical workflow. The AI-assisted documentation saves me hours
every week while improving the quality of my patient assessments.

If you're a physiotherapist looking to reduce admin time and enhance
clinical reasoning, I highly recommend trying it out.

Use my referral code PRISM-SANDY2025 for an extended trial and
discount: [link]

#Physiotherapy #ClinicalDocumentation #HealthTech
```

---

### C. Technical API Endpoints

**Referral-related endpoints to build**:

```
GET  /api/referral/code              # Get user's referral code
POST /api/referral/validate          # Validate a referral code
GET  /api/referral/stats             # Get referrer's stats
GET  /api/referral/rewards           # Get available rewards
POST /api/referral/redeem            # Redeem a reward
GET  /api/referral/history           # Get referral history
POST /api/referral/share             # Track share button clicks

# Admin endpoints
GET  /api/admin/referrals/overview   # Program analytics
GET  /api/admin/referrals/leaderboard # Top referrers
GET  /api/admin/referrals/flagged    # Fraud review queue
POST /api/admin/referrals/manual-reward # Manually issue reward
```

---

### D. Metrics Tracking (Google Analytics)

**Events to track**:
```javascript
// User views referral page
gtag('event', 'referral_page_view', {
  'event_category': 'Referral',
  'event_label': 'Dashboard Visit'
});

// User copies referral code
gtag('event', 'referral_code_copy', {
  'event_category': 'Referral',
  'event_label': 'Code Copied',
  'value': user_id
});

// User clicks share button
gtag('event', 'referral_share', {
  'event_category': 'Referral',
  'event_label': 'WhatsApp/Email/Social',
  'value': share_method
});

// New signup uses referral code
gtag('event', 'referral_signup', {
  'event_category': 'Referral',
  'event_label': 'Code Used',
  'value': referral_code
});

// Referral converts to paid
gtag('event', 'referral_conversion', {
  'event_category': 'Referral',
  'event_label': 'Paid Conversion',
  'value': plan_price
});

// Reward redeemed
gtag('event', 'referral_reward_redeemed', {
  'event_category': 'Referral',
  'event_label': 'Credit/Free Month',
  'value': reward_amount
});
```

---

## Conclusion

This referral program is designed to:
1. ✅ Reward early adopters for spreading the word
2. ✅ Provide substantial value to both parties
3. ✅ Drive sustainable, high-quality growth
4. ✅ Minimize customer acquisition costs
5. ✅ Build a community of advocates

**Expected Outcome**: If executed well, this program could drive **20-30% of new signups** through referrals within 6 months, significantly reducing dependence on paid advertising.

**Next Steps**:
1. Review and approve reward structure
2. Finalize technical requirements
3. Begin Phase 1 development
4. Set launch date

---

**Document Version**: 1.0
**Last Updated**: April 7, 2026
**Next Review**: Before implementation begins

---

**Questions or Feedback?**
Contact: Product Team
