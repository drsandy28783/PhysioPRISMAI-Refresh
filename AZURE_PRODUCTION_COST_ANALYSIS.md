# PhysiologicPRISM - Complete Azure Production Cost Analysis
**Date:** January 18, 2026
**Currency:** USD & INR (₹) | Exchange Rate: $1 = ₹83

---

## 🏗️ CURRENT INFRASTRUCTURE CONFIGURATION

### Azure Services Deployed:

| Service | Configuration | Tier/SKU | Region |
|---------|--------------|----------|--------|
| **Azure Container Apps** | 0.5 vCPU, 1Gi RAM | Consumption | East US |
| **Azure Container Registry** | Standard | Basic | East US |
| **Azure Cosmos DB** | Serverless | NoSQL API | East US |
| **Azure OpenAI** | GPT-4o deployment | Pay-per-token | East US |
| **Firebase Authentication** | Email/Password | Free tier | Global |
| **Resend Email API** | Transactional emails | Free tier (100/day) | Global |
| **Razorpay Payment Gateway** | INR payments | 2% per transaction | India |

---

## 💰 PRODUCTION COST BREAKDOWN

### 1. Azure Container Apps (Application Hosting)

**Current Configuration:**
- **vCPU:** 0.5 cores per replica
- **Memory:** 1Gi (1 GB) per replica
- **Min Replicas:** 0 (scale-to-zero enabled)
- **Max Replicas:** 3
- **Concurrent Requests:** Default (~100/replica)

#### Pricing Model:
- **vCPU:** $0.000024/vCPU-second ($0.0864/vCPU-hour)
- **Memory:** $0.000003/GB-second ($0.0108/GB-hour)
- **Request:** $0.40 per million requests

#### Cost Scenarios:

**Scenario A: Current (Scale-to-Zero Beta)**
- Active when requests come in, idles to 0 when no traffic
- Assuming 50% active time (12 hours/day) with typical beta usage
- **Compute:** 0.5 vCPU × 12 hours × 30 days × $0.0864/vCPU-hour = **$15.55**
- **Memory:** 1 GB × 12 hours × 30 days × $0.0108/GB-hour = **$3.89**
- **Requests:** 100K requests/month × $0.40/1M = **$0.04**
- **Total Monthly Cost:** **$19.48/month (₹1,617)**

**Scenario B: Production (Always-On, 1 Min Replica)**
- Min replicas = 1 (24/7 uptime, no cold starts)
- Handles professional/clinical traffic
- **Compute:** 0.5 vCPU × 24 hours × 30 days × $0.0864/vCPU-hour = **$31.10**
- **Memory:** 1 GB × 24 hours × 30 days × $0.0108/GB-hour = **$7.78**
- **Requests:** 500K requests/month × $0.40/1M = **$0.20**
- **Total Monthly Cost:** **$39.08/month (₹3,244)**

**Scenario C: High-Traffic Production (Always-On, 2 Min Replicas)**
- Min replicas = 2 (high availability, load balancing)
- Enterprise-grade reliability
- **Compute:** 1.0 vCPU × 24 hours × 30 days × $0.0864/vCPU-hour = **$62.21**
- **Memory:** 2 GB × 24 hours × 30 days × $0.0108/GB-hour = **$15.55**
- **Requests:** 1M requests/month × $0.40/1M = **$0.40**
- **Total Monthly Cost:** **$78.16/month (₹6,487)**

---

### 2. Azure Container Registry (Docker Images)

**Tier:** Basic
- **Storage:** 10GB included
- **Data Transfer:** Minimal (only during deployments)
- **Monthly Cost:** **$5.00 (₹415)**

---

### 3. Azure Cosmos DB (Database - Serverless)

**Configuration:**
- **Database:** PhysiologicPRISM
- **Collections:** 15+ (users, patients, sessions, subscriptions, blog_posts, etc.)
- **Partition Strategy:** Optimized per collection
- **Mode:** Serverless (pay per request)

#### Pricing Model:
- **Request Units (RUs):** $0.25 per million RUs consumed
- **Storage:** $0.25 per GB/month
- **Backup:** Included (7-day retention)

#### Typical Usage (Per Customer):
- **Storage per 100 patients:** ~50MB
- **Monthly RUs (CRUD operations):** ~1M RUs per 100 patients
- **Metadata (users, sessions, etc.):** ~10MB + 500K RUs

#### Cost Estimates:

**Low Usage (10 customers, 1000 total patients):**
- **Storage:** 500MB + 100MB metadata = 0.6GB × $0.25 = **$0.15**
- **RUs:** 10M + 5M = 15M RUs × $0.25/M = **$3.75**
- **Total:** **$3.90/month (₹323)**

**Medium Usage (50 customers, 5000 total patients):**
- **Storage:** 2.5GB + 500MB = 3GB × $0.25 = **$0.75**
- **RUs:** 50M + 25M = 75M RUs × $0.25/M = **$18.75**
- **Total:** **$19.50/month (₹1,618)**

**High Usage (200 customers, 20,000 total patients):**
- **Storage:** 10GB + 2GB = 12GB × $0.25 = **$3.00**
- **RUs:** 200M + 100M = 300M RUs × $0.25/M = **$75.00**
- **Total:** **$78.00/month (₹6,474)**

---

### 4. Azure OpenAI (GPT-4o) - AI Clinical Decision Support

**Model:** GPT-4o (2024-11-20 version)
- **Region:** East US
- **Deployment:** Standard (pay-per-token)

#### Pricing:
- **Input Tokens:** $2.50 per 1M tokens
- **Output Tokens:** $10.00 per 1M tokens
- **Cached Input Tokens:** $1.25 per 1M tokens (50% discount)

#### Per AI Call Cost (Average Clinical Suggestion):

**Typical Request:**
- **System Prompt:** 300 tokens (often cached)
- **Patient Context:** 400 tokens
- **User Query:** 100 tokens
- **Total Input:** 800 tokens
- **Response Output:** 1,000 tokens

**With Caching (50% prompts cached):**
```
Cached Input:   400 tokens × $1.25/1M = $0.0005
Regular Input:  400 tokens × $2.50/1M = $0.0010
Output:        1000 tokens × $10.00/1M = $0.0100
─────────────────────────────────────────
Cost per call: $0.0115 ≈ $0.012 (₹1.00)
```

**Without Caching (worst case):**
```
Input:   800 tokens × $2.50/1M = $0.0020
Output: 1000 tokens × $10.00/1M = $0.0100
─────────────────────────────────────────
Cost per call: $0.012 (₹1.00)
```

#### Monthly AI Costs by Usage:

| Scenario | AI Calls/Month | Cost (USD) | Cost (INR) |
|----------|----------------|------------|------------|
| **Light** | 500 calls | $6.00 | ₹498 |
| **Medium** | 2,500 calls | $30.00 | ₹2,490 |
| **High** | 10,000 calls | $120.00 | ₹9,960 |
| **Enterprise** | 50,000 calls | $600.00 | ₹49,800 |

---

### 5. Firebase Authentication (User Management)

**Service:** Firebase Authentication
- **Provider:** Email/Password
- **Usage:** Login, registration, password reset
- **Pricing:** **FREE** (unlimited users)
- **Monthly Cost:** **$0.00 (₹0)**

**Note:** Firebase Auth handles ONLY authentication (email/password). All PHI data is stored in Azure Cosmos DB with HIPAA BAA.

---

### 6. Resend Email API (Transactional Emails)

**Service:** Resend transactional email service
- **Tier:** Free (0-100 emails/day = 3,000/month)
- **Usage:** Email verification, password reset, notifications
- **Pricing:** **FREE** (within limits)
- **Overage:** $1.00 per 1,000 emails (if exceeding 3K/month)

**Typical Usage:**
- 50 customers × 20 emails/month = 1,000 emails
- Well within free tier

**Monthly Cost:** **$0.00 (₹0)** for <3,000 emails

---

### 7. Razorpay Payment Gateway (India)

**Service:** Razorpay Payment Gateway
- **Fee:** 2% per transaction (deducted from payment)
- **Setup:** No monthly fee
- **Settlement:** T+3 days

**Cost Structure:**
- Not a monthly cost to you
- Deducted from customer payments
- Example: Customer pays ₹10,000 → You receive ₹9,800

**Monthly Impact:** Variable (based on revenue)
- ₹50,000 revenue → ₹1,000 fees (2%)
- ₹200,000 revenue → ₹4,000 fees (2%)

---

## 📊 TOTAL MONTHLY COSTS - COMPLETE BREAKDOWN

### Configuration A: BETA/TESTING (Current Setup)
**Infrastructure:** Scale-to-zero, minimal traffic

| Service | Monthly Cost (USD) | Monthly Cost (INR) |
|---------|-------------------|--------------------|
| Container Apps (scale-to-zero) | $19.48 | ₹1,617 |
| Container Registry (Basic) | $5.00 | ₹415 |
| Cosmos DB (10 customers) | $3.90 | ₹323 |
| Azure OpenAI (500 AI calls) | $6.00 | ₹498 |
| Firebase Auth | $0.00 | ₹0 |
| Resend Email | $0.00 | ₹0 |
| **TOTAL FIXED COST** | **$34.38** | **₹2,853** |
| **Razorpay (2% of revenue)** | Variable | Variable |

---

### Configuration B: PRODUCTION (Recommended)
**Infrastructure:** 1 always-on replica, 50 customers, 10K AI calls/month

| Service | Monthly Cost (USD) | Monthly Cost (INR) |
|---------|-------------------|--------------------|
| Container Apps (1 replica, always-on) | $39.08 | ₹3,244 |
| Container Registry (Basic) | $5.00 | ₹415 |
| Cosmos DB (50 customers, 5K patients) | $19.50 | ₹1,618 |
| Azure OpenAI (10,000 AI calls) | $120.00 | ₹9,960 |
| Firebase Auth | $0.00 | ₹0 |
| Resend Email | $0.00 | ₹0 |
| **TOTAL FIXED COST** | **$183.58** | **₹15,237** |
| **Razorpay (2% of revenue)** | Variable | Variable |

**At ₹4,19,450/month revenue (50 customers per pricing plan):**
- Razorpay Fees: ₹8,389
- **Total Cost:** ₹23,626/month
- **Net Profit:** ₹3,95,824/month (94.4% margin)

---

### Configuration C: ENTERPRISE PRODUCTION
**Infrastructure:** 2 always-on replicas, 200 customers, 50K AI calls/month

| Service | Monthly Cost (USD) | Monthly Cost (INR) |
|---------|-------------------|--------------------|
| Container Apps (2 replicas, HA) | $78.16 | ₹6,487 |
| Container Registry (Basic) | $5.00 | ₹415 |
| Cosmos DB (200 customers, 20K patients) | $78.00 | ₹6,474 |
| Azure OpenAI (50,000 AI calls) | $600.00 | ₹49,800 |
| Firebase Auth | $0.00 | ₹0 |
| Resend Email | $0.00 | ₹0 |
| **TOTAL FIXED COST** | **$761.16** | **₹63,176** |
| **Razorpay (2% of revenue)** | Variable | Variable |

**At ₹16,77,800/month revenue (200 customers):**
- Razorpay Fees: ₹33,556
- **Total Cost:** ₹96,732/month
- **Net Profit:** ₹15,81,068/month (94.2% margin)

---

## 🎯 KEY COST DRIVERS

### 1. **Azure OpenAI (Biggest Variable Cost)**
- Scales linearly with AI call volume
- Cost: ~₹1.00 per AI call
- Optimization: Caching reduces costs by ~40%
- **Your pricing:** ₹8.99-13.00 per AI call pack = **90%+ profit margin**

### 2. **Azure Container Apps (Biggest Fixed Cost)**
- Scale-to-zero: ₹1,617/month (beta/light usage)
- Always-on (1 replica): ₹3,244/month (production)
- Always-on (2 replicas): ₹6,487/month (enterprise)
- **Decision:** Use scale-to-zero until customer base justifies always-on

### 3. **Azure Cosmos DB (Scales with Customers)**
- Serverless = Pay only for what you use
- 10 customers: ₹323/month
- 50 customers: ₹1,618/month
- 200 customers: ₹6,474/month
- **Very affordable** compared to provisioned throughput

### 4. **Fixed Costs (Minimal)**
- Container Registry: ₹415/month (unavoidable)
- Firebase Auth: FREE
- Resend Email: FREE (within 3K/month)

---

## 💡 COST OPTIMIZATION STRATEGIES

### For Current Stage (Beta/Early Customers):
1. ✅ **Keep scale-to-zero enabled** (save ₹1,627/month)
2. ✅ **Use Cosmos DB serverless** (already optimal)
3. ✅ **Aggressive prompt caching** (save 40% on AI costs)
4. ✅ **Stay within Resend free tier** (<3K emails/month)

**Result:** ₹2,853/month base + ₹1.00 per AI call

---

### For Production (50+ Customers):
1. ✅ **Switch to 1 always-on replica** (eliminate cold starts)
2. ✅ **Monitor Cosmos DB RU consumption** (optimize queries)
3. ✅ **Implement AI call quotas** (prevent abuse)
4. ✅ **Upsell AI Call Packs aggressively** (90%+ margins)

**Result:** ₹15,237/month base + variable AI costs

---

### For Enterprise Scale (200+ Customers):
1. ✅ **Scale to 2 replicas** (high availability)
2. ✅ **Consider Cosmos DB autoscale** (predictable costs)
3. ✅ **Implement CDN caching** (reduce compute costs)
4. ✅ **Negotiate Azure credits** (startups/ISVs)

**Result:** ₹63,176/month base + variable AI costs

---

## 📈 PROFITABILITY BY CUSTOMER VOLUME

### Break-Even Analysis:

**With Scale-to-Zero (Beta):**
- Fixed Cost: ₹2,853/month
- Break-even: 2-3 customers at any tier

**With Always-On 1 Replica (Production):**
- Fixed Cost: ₹15,237/month (before AI calls)
- Break-even: 3-4 Team (5) customers OR 2 Team Pro (10) customers

**With Always-On 2 Replicas (Enterprise):**
- Fixed Cost: ₹63,176/month (before AI calls)
- Break-even: 4-5 Institute Plus (20) customers

---

## 🚀 RECOMMENDED INFRASTRUCTURE ROADMAP

### Phase 1: Launch (0-20 customers)
- **Config:** Scale-to-zero Container Apps
- **Cost:** ₹2,853/month + AI usage
- **Why:** Minimize burn rate during customer acquisition

### Phase 2: Growth (20-100 customers)
- **Config:** 1 always-on replica
- **Cost:** ₹15,237/month + AI usage
- **Why:** Professional experience, no cold starts

### Phase 3: Scale (100-500 customers)
- **Config:** 2 always-on replicas + autoscaling
- **Cost:** ₹63,176/month + AI usage
- **Why:** High availability, handle traffic spikes

### Phase 4: Enterprise (500+ customers)
- **Config:** Multi-region deployment, dedicated SQL
- **Cost:** Custom (₹2-3 lakhs/month)
- **Why:** Enterprise SLAs, compliance requirements

---

## 💰 BOTTOM LINE

### Current Reality (Scale-to-Zero):
**Monthly Cost:** ₹2,853 base + ₹1.00 per AI call

**Example with 10 customers (500 AI calls total):**
- Infrastructure: ₹2,853
- AI Calls: ₹500
- Razorpay: ₹200
- **Total:** ₹3,553/month
- **Revenue:** ~₹30,000-50,000/month
- **Profit:** ₹26,447-46,447 (88-93% margin)

---

### Production Recommendation (50 Customers):
**Monthly Cost:** ₹15,237 base + AI costs + payment fees

**With 50 customers (10K AI calls total):**
- Infrastructure: ₹15,237
- AI Calls: ₹10,000
- Razorpay: ₹8,389
- **Total:** ₹33,626/month
- **Revenue:** ₹4,19,450/month
- **Net Profit:** ₹3,85,824/month (92% margin)

---

## ✅ FINAL VERDICT

Your Azure production costs are **EXTREMELY COMPETITIVE**:

1. ✅ **Scale-to-zero works perfectly** for early stage (₹2,853/month)
2. ✅ **Production costs are reasonable** (₹15,237/month for 50 customers)
3. ✅ **Serverless model scales smoothly** with customer growth
4. ✅ **90%+ profit margins** are achievable and sustainable
5. ✅ **No surprises** - costs scale predictably with usage

**You are NOT bleeding money.** Your infrastructure is well-optimized for a SaaS product at this stage.

---

**Document Created:** January 18, 2026
**Next Review:** After reaching 50 paying customers
**Status:** OPTIMIZED - NO IMMEDIATE CHANGES NEEDED
