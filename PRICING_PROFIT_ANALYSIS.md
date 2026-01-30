# PhysiologicPRISM - Pricing vs Cost Analysis
**Date:** January 18, 2026
**Currency:** INR (₹) | Exchange Rate: $1 = ₹83

---

## 📊 AZURE INFRASTRUCTURE COSTS

### Fixed Monthly Costs (Base Infrastructure)

| Service | Beta Cost (USD) | Production Cost (USD) | INR (₹) |
|---------|----------------|----------------------|---------|
| **Azure Cosmos DB** | $0.28 | $0.28 | ₹23 |
| **Azure Container Apps** | $3-5 | $73.44 | ₹6,095 |
| **Azure Container Registry** | $5.00 | $5.00 | ₹415 |
| **Firebase Auth** | FREE | FREE | FREE |
| **Resend Email** | FREE | FREE | FREE |
| **TOTAL FIXED** | **$8.28-10.28** | **$78.72** | **₹6,533** |

### Variable Costs (Usage-Based)

#### Azure OpenAI GPT-4o Pricing:
- **Input tokens:** $2.50 per 1M tokens
- **Output tokens:** $10 per 1M tokens
- **Cached input:** $1.25 per 1M tokens (50% discount)

#### Per AI Call Cost Calculation:
**Assumptions:**
- Average 500 input tokens + 1,000 output tokens per AI call
- 50% of inputs cached (from repeated prompts)

**Cost per AI call:**
```
Regular input:  250 tokens × $2.50/1M = $0.000625
Cached input:   250 tokens × $1.25/1M = $0.0003125
Output:        1000 tokens × $10/1M   = $0.010

Total per call: $0.0109375 ≈ $0.011 (₹0.91)
```

#### Storage Costs (Cosmos DB):
- **Per GB stored:** $0.25/month
- **Per million RUs:** Variable (serverless)
- **Typical per user:** ~0.5MB = negligible
- **Per 1000 patients:** ~500MB = $0.125/month

---

## 💰 PROFIT ANALYSIS BY PLAN

### Exchange Rate Used: $1 = ₹83

---

### 1. SOLO PROFESSIONAL PLAN

**Pricing:**
- Monthly Revenue: ₹899
- AI Calls Included: 100
- Users: 1

**Monthly Costs:**

| Item | Calculation | Cost (₹) |
|------|------------|----------|
| **Fixed Infrastructure** | $78.72 × ₹83 | ₹6,534 |
| **AI Calls** | 100 × ₹0.91 | ₹91 |
| **Storage** | Negligible | ₹5 |
| **Payment Gateway** | 2% of ₹899 | ₹18 |
| **TOTAL COST** | | **₹6,648** |

**Profit Analysis:**
```
Revenue:        ₹899
Cost:          -₹6,648
────────────────────
LOSS:          -₹5,749 per user
```

**Break-Even Point:** 8 solo users sharing infrastructure = ₹831 per user cost

---

### 2. TEAM (5 USERS) PLAN - MOST POPULAR

**Pricing:**
- Monthly Revenue: ₹3,999
- AI Calls Included: 500
- Users: 5
- Per user: ₹799/user

**Monthly Costs:**

| Item | Calculation | Cost (₹) |
|------|------------|----------|
| **Fixed Infrastructure** | $78.72 × ₹83 | ₹6,534 |
| **AI Calls** | 500 × ₹0.91 | ₹455 |
| **Storage** | Minimal | ₹10 |
| **Payment Gateway** | 2% of ₹3,999 | ₹80 |
| **TOTAL COST** | | **₹7,079** |

**Profit Analysis:**
```
Revenue:        ₹3,999
Cost:          -₹7,079
────────────────────
LOSS:          -₹3,080
Margin:        -77.0%
```

**Note:** Still losing money per customer at this tier.

---

### 3. TEAM PRO (10 USERS) PLAN

**Pricing:**
- Monthly Revenue: ₹7,499
- AI Calls Included: 1,000
- Users: 10
- Per user: ₹749/user

**Monthly Costs:**

| Item | Calculation | Cost (₹) |
|------|------------|----------|
| **Fixed Infrastructure** | $78.72 × ₹83 | ₹6,534 |
| **AI Calls** | 1,000 × ₹0.91 | ₹910 |
| **Storage** | Minimal | ₹15 |
| **Payment Gateway** | 2% of ₹7,499 | ₹150 |
| **TOTAL COST** | | **₹7,609** |

**Profit Analysis:**
```
Revenue:        ₹7,499
Cost:          -₹7,609
────────────────────
LOSS:          -₹110
Margin:        -1.5%
```

**Note:** Nearly break-even! First plan approaching profitability.

---

### 4. INSTITUTE (15 USERS) PLAN

**Pricing:**
- Monthly Revenue: ₹10,999
- AI Calls Included: 1,500
- Users: 15
- Per user: ₹733/user

**Monthly Costs:**

| Item | Calculation | Cost (₹) |
|------|------------|----------|
| **Fixed Infrastructure** | $78.72 × ₹83 | ₹6,534 |
| **AI Calls** | 1,500 × ₹0.91 | ₹1,365 |
| **Storage** | Moderate | ₹20 |
| **Payment Gateway** | 2% of ₹10,999 | ₹220 |
| **TOTAL COST** | | **₹8,139** |

**Profit Analysis:**
```
Revenue:        ₹10,999
Cost:          -₹8,139
────────────────────
PROFIT:        +₹2,860
Margin:        +26.0% ✅
```

**First profitable tier!**

---

### 5. INSTITUTE PLUS (20 USERS) PLAN

**Pricing:**
- Monthly Revenue: ₹14,499
- AI Calls Included: 2,000
- Users: 20
- Per user: ₹724/user

**Monthly Costs:**

| Item | Calculation | Cost (₹) |
|------|------------|----------|
| **Fixed Infrastructure** | $78.72 × ₹83 | ₹6,534 |
| **AI Calls** | 2,000 × ₹0.91 | ₹1,820 |
| **Storage** | Moderate | ₹25 |
| **Payment Gateway** | 2% of ₹14,499 | ₹290 |
| **TOTAL COST** | | **₹8,669** |

**Profit Analysis:**
```
Revenue:        ₹14,499
Cost:          -₹8,669
────────────────────
PROFIT:        +₹5,830
Margin:        +40.2% ✅
```

---

## 📦 AI CALL PACKS PROFIT ANALYSIS

### Cost Per AI Call: ₹0.91

| Pack | Price | Calls | Revenue/Call | Cost/Call | Profit/Call | Total Profit | Margin |
|------|-------|-------|--------------|-----------|-------------|--------------|--------|
| **25 Calls** | ₹325 | 25 | ₹13.00 | ₹0.91 | ₹12.09 | ₹302 | **93.0%** ✅ |
| **50 Calls** | ₹599 | 50 | ₹11.98 | ₹0.91 | ₹11.07 | ₹554 | **92.4%** ✅ |
| **100 Calls** | ₹1,099 | 100 | ₹10.99 | ₹0.91 | ₹10.08 | ₹1,008 | **91.7%** ✅ |
| **250 Calls** | ₹2,499 | 250 | ₹9.99 | ₹0.91 | ₹9.08 | ₹2,271 | **90.9%** ✅ |
| **500 Calls** | ₹4,499 | 500 | ₹8.99 | ₹0.91 | ₹8.08 | ₹4,040 | **89.8%** ✅ |

**Verdict:** AI Call Packs are HIGHLY profitable! 90%+ margins.

---

## 🎯 PROFITABILITY SUMMARY

### Subscription Plans

| Plan | Monthly Revenue | Monthly Cost | Profit | Margin | Status |
|------|----------------|--------------|---------|--------|--------|
| **Solo** | ₹899 | ₹6,648 | **-₹5,749** | -639% | ❌ LOSS |
| **Team (5)** | ₹3,999 | ₹7,079 | **-₹3,080** | -77% | ❌ LOSS |
| **Team Pro (10)** | ₹7,499 | ₹7,609 | **-₹110** | -1.5% | ⚠️ BREAK-EVEN |
| **Institute (15)** | ₹10,999 | ₹8,139 | **+₹2,860** | +26% | ✅ PROFIT |
| **Institute Plus (20)** | ₹14,499 | ₹8,669 | **+₹5,830** | +40% | ✅ PROFIT |

### Key Findings:

1. **❌ Solo & Team (5) Plans: NOT PROFITABLE**
   - Solo plan loses ₹5,749/month per customer
   - Team (5) plan loses ₹3,080/month per customer
   - Fixed infrastructure cost (₹6,534) is too high relative to revenue

2. **⚠️ Team Pro (10): BARELY BREAK-EVEN**
   - Only ₹110/month loss
   - Could be profitable with slight price increase

3. **✅ Institute Plans (15+): PROFITABLE**
   - Institute (15): 26% margin
   - Institute Plus (20): 40% margin
   - Revenue finally exceeds fixed infrastructure costs

4. **🌟 AI Call Packs: EXTREMELY PROFITABLE**
   - 90%+ profit margins on all packs
   - No additional infrastructure costs
   - Pure margin after ₹0.91/call AI cost

---

## 💡 REVENUE SCENARIOS

### Scenario 1: Current Pricing (Mixed Customer Base)

**Assumptions:**
- 5 Solo customers
- 3 Team (5) customers
- 2 Team Pro (10) customers
- 1 Institute (15) customer
- 1 Institute Plus (20) customer

**Monthly Revenue:**
```
Solo:          5 × ₹899      = ₹4,495
Team (5):      3 × ₹3,999    = ₹11,997
Team Pro:      2 × ₹7,499    = ₹14,998
Institute:     1 × ₹10,999   = ₹10,999
Institute+:    1 × ₹14,499   = ₹14,499
AI Packs:      ~10 × ₹1,099  = ₹10,990 (estimated)

TOTAL REVENUE: ₹67,978/month
```

**Monthly Costs:**
```
Fixed Infrastructure:           ₹6,534
AI Calls (total across all):   ₹4,550
Payment Gateway (2%):           ₹1,360
Storage:                        ₹100

TOTAL COST: ₹12,544
```

**Net Profit:**
```
Revenue:  ₹67,978
Cost:    -₹12,544
────────────────
PROFIT:   ₹55,434/month
Margin:   81.5% ✅
```

---

### Scenario 2: Only Profitable Customers (Institute+ Only)

**Assumptions:**
- 10 Institute (15) customers
- 5 Institute Plus (20) customers
- AI Call Pack sales: ₹25,000/month

**Monthly Revenue:**
```
Institute (15):   10 × ₹10,999 = ₹109,990
Institute+ (20):   5 × ₹14,499 = ₹72,495
AI Packs:                       = ₹25,000

TOTAL REVENUE: ₹207,485/month
```

**Monthly Costs:**
```
Fixed Infrastructure:           ₹6,534
AI Calls:                       ₹13,650
Payment Gateway (2%):           ₹4,150
Storage:                        ₹200

TOTAL COST: ₹24,534
```

**Net Profit:**
```
Revenue:  ₹207,485
Cost:    -₹24,534
────────────────
PROFIT:   ₹182,951/month
Margin:   88.2% ✅
```

**Annual:** ₹2,195,412 (~₹22 lakhs/year profit)

---

## 🚨 CRITICAL ISSUES WITH CURRENT PRICING

### Problem 1: Solo Plan is Hemorrhaging Money
**Loss:** ₹5,749 per customer per month

**Why:**
- Fixed infrastructure costs ₹6,534/month
- Solo customer only pays ₹899/month
- You'd need 8 Solo customers just to break even on infrastructure

**Solutions:**
1. **Increase Solo price to ₹2,499/month** (still competitive)
2. **Reduce Solo AI calls to 50** (reduce costs)
3. **Eliminate Solo plan entirely** (focus on teams)
4. **Offer Solo as Beta trial only** (convert to Team plans)

---

### Problem 2: Team (5) Plan is Also Unprofitable
**Loss:** ₹3,080 per customer per month

**Solutions:**
1. **Increase price to ₹6,999/month** (+75% revenue)
2. **Reduce AI calls to 300** (-40% AI costs)
3. **Position as "Starter Team" with upsell to Team Pro**

---

### Problem 3: Fixed Infrastructure Cost Too High for Small Plans

**Current Infrastructure:** $78.72/month (₹6,534)

**This includes:**
- Azure Container Apps (always-on): $73.44
- Azure Container Registry: $5.00
- Azure Cosmos DB: $0.28

**Optimization Options:**

1. **Use Scale-to-Zero for Small Customers**
   - Reduce to $10/month infrastructure
   - Add cold start notice for Solo/Team (5) customers
   - Keep always-on only for Institute+ customers

2. **Multi-Tenant Architecture**
   - Share infrastructure across all customers
   - Reduces per-customer cost significantly

---

## ✅ RECOMMENDED PRICING REVISIONS

### Option A: Aggressive Price Increases

| Plan | Current | New | Change | New Margin |
|------|---------|-----|--------|------------|
| **Solo** | ₹899 | ₹2,499 | **+178%** | Break-even |
| **Team (5)** | ₹3,999 | ₹6,999 | **+75%** | +20% margin |
| **Team Pro (10)** | ₹7,499 | ₹9,999 | **+33%** | +35% margin |
| **Institute (15)** | ₹10,999 | ₹13,999 | **+27%** | +45% margin |
| **Institute+ (20)** | ₹14,499 | ₹17,999 | **+24%** | +52% margin |

**AI Call Packs:** Keep current pricing (already highly profitable)

---

### Option B: Reduce Costs + Moderate Price Increases

**Infrastructure Optimization:**
- Use scale-to-zero for Solo & Team (5): Saves ₹5,500/month
- New fixed cost: ₹1,033/month

**New Pricing:**

| Plan | New Price | AI Calls | Cost | Profit | Margin |
|------|-----------|----------|------|---------|--------|
| **Solo** | ₹1,499 | 50 | ₹1,129 | **+₹370** | +25% ✅ |
| **Team (5)** | ₹4,999 | 400 | ₹1,497 | **+₹3,502** | +70% ✅ |
| **Team Pro (10)** | ₹8,999 | 800 | ₹1,761 | **+₹7,238** | +80% ✅ |
| **Institute (15)** | ₹12,999 | 1,500 | ₹2,398 | **+₹10,601** | +82% ✅ |
| **Institute+ (20)** | ₹16,999 | 2,000 | ₹2,853 | **+₹14,146** | +83% ✅ |

**Result:** ALL plans profitable with moderate price increases + infrastructure optimization!

---

### Option C: Eliminate Unprofitable Plans

**Keep Only:**
- Team Pro (10 users) - ₹9,999/month
- Institute (15 users) - ₹13,999/month
- Institute+ (20 users) - ₹17,999/month
- Custom Enterprise (25+ users) - Custom pricing

**Eliminate:**
- Solo Professional (unprofitable)
- Team (5 users) (unprofitable)

**Benefits:**
- Focus on profitable customers only
- Simpler pricing page
- Higher average revenue per customer
- Better resource utilization

---

## 🎯 FINAL RECOMMENDATIONS

### **RECOMMENDED STRATEGY: Option B (Cost Reduction + Price Optimization)**

1. **Enable Scale-to-Zero for Small Plans**
   - Solo & Team (5): Use beta infrastructure ($10/month)
   - Team Pro+: Use production infrastructure ($78/month)
   - **Savings:** ₹5,500/month per customer

2. **Adjust Pricing:**
   - Solo: ₹899 → **₹1,499** (+67%)
   - Team (5): ₹3,999 → **₹4,999** (+25%)
   - Team Pro: ₹7,499 → **₹8,999** (+20%)
   - Institute: ₹10,999 → **₹12,999** (+18%)
   - Institute+: ₹14,499 → **₹16,999** (+17%)

3. **Reduce AI Calls Slightly:**
   - Solo: 100 → **50 calls** (still generous for solo use)
   - Others: Keep current allocation

4. **Upsell AI Call Packs Aggressively**
   - 90%+ profit margins
   - Offer in-app purchase prompts
   - Send notifications at 80% usage

5. **Focus Marketing on Institute+ Plans**
   - Highest margins (83%+)
   - Target clinics with 10+ physiotherapists
   - Offer custom demos

---

## 📈 PROJECTED OUTCOMES (Option B Implementation)

### With 50 Customers (Mixed Tiers)

**Customer Mix:**
- 15 Solo: 15 × ₹1,499 = ₹22,485
- 10 Team (5): 10 × ₹4,999 = ₹49,990
- 12 Team Pro: 12 × ₹8,999 = ₹107,988
- 8 Institute: 8 × ₹12,999 = ₹103,992
- 5 Institute+: 5 × ₹16,999 = ₹84,995
- AI Packs: ₹50,000/month (estimated)

**Total Monthly Revenue:** ₹419,450

**Total Monthly Costs:**
- Infrastructure (mixed): ₹20,000
- AI Calls: ₹35,000
- Payment Gateway (2%): ₹8,389
- **Total:** ₹63,389

**Net Monthly Profit:**
```
Revenue:  ₹419,450
Cost:    -₹63,389
────────────────
PROFIT:   ₹356,061/month
Margin:   84.9% ✅

ANNUAL:   ₹4,272,732 (~₹42.7 lakhs/year)
```

---

## 💰 PROFITABILITY TIMELINE

### Current Pricing (No Changes):
- **Break-even customers:** 8 Team Pro (10) customers
- **Profitable after:** 1 Institute (15) customer
- **Risk:** Solo & Team (5) customers dilute profits

### Recommended Pricing (Option B):
- **All plans profitable immediately** ✅
- **Break-even:** 1 customer (any tier)
- **Scalable:** Margins improve with volume

---

## 📊 FINAL VERDICT

### Current Pricing Analysis:
- ❌ **Solo: HIGHLY unprofitable** (-640% margin)
- ❌ **Team (5): Unprofitable** (-77% margin)
- ⚠️ **Team Pro (10): Break-even** (-1.5% margin)
- ✅ **Institute (15): Profitable** (+26% margin)
- ✅ **Institute+ (20): Profitable** (+40% margin)
- ✅ **AI Call Packs: VERY profitable** (+90% margin)

### **Recommended Action:**
**Implement Option B immediately:**
1. ✅ Enable scale-to-zero for small plans
2. ✅ Increase prices by 15-67% across all tiers
3. ✅ Reduce Solo AI calls to 50
4. ✅ Focus sales on Institute+ plans
5. ✅ Aggressively upsell AI Call Packs

### **Expected Outcome:**
- All plans become profitable ✅
- 80%+ overall margins ✅
- Sustainable growth ✅
- Annual profit: ₹40+ lakhs with 50 customers ✅

---

**Document Created:** January 18, 2026
**Next Review:** After first 10 paying customers
**Status:** REQUIRES IMMEDIATE PRICING REVISION
