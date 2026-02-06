# Production Readiness: Cost Control & Limits Checklist

**Date**: 2026-02-06
**Purpose**: Document hard-coded limits to prevent misuse of expensive features (AI & Voice)

---

## ✅ YES - You Can Publish After Testing

The app is production-ready **with one critical addition needed** (voice typing limits - see below).

---

## 💰 MOST EXPENSIVE FEATURES - COST BREAKDOWN

### 1. **AI Suggestions (OpenAI GPT-4o)** 🧠
- **Cost**: ₹0.91 per call (with caching)
- **Selling Price**: ₹8.99 - ₹13.00 per call (90%+ profit margin)
- **Status**: ✅ **LIMITS ENFORCED** (Hard-coded per plan)

### 2. **Voice Typing (Azure Speech Services)** 🎤
- **Cost**: $1 USD per hour = ₹83/hour ≈ ₹1.38/minute ≈ **₹0.023/second**
- **Typical Usage**: 1-2 minute notes = ₹1.38-2.76 per note
- **Status**: ⚠️ **NO LIMITS CURRENTLY** (Needs implementation!)

---

## ✅ AI LIMITS - ALREADY ENFORCED

### Current Implementation:
- **File**: `subscription_manager.py` (lines 40-142)
- **Enforcement**: `quota_middleware.py` with `@require_ai_quota` decorator
- **Tracking**: `check_ai_limit()`, `deduct_ai_usage()`

### Hard-Coded Limits by Plan:

| Plan | Price | AI Calls/Month | Cost | Notes |
|------|-------|----------------|------|-------|
| **Free Trial** | ₹0 | 25 calls | ₹23 | 14 days only |
| **Solo** | ₹1,499 | 50 calls | ₹46 | Unlimited patients |
| **Team (5)** | ₹4,999 | 400 calls | ₹364 | 5 users |
| **Team Pro (10)** | ₹8,999 | 800 calls | ₹728 | 10 users |
| **Institute (15)** | ₹12,999 | 1,500 calls | ₹1,365 | 15 users |
| **Institute+ (20)** | ₹16,999 | 2,000 calls | ₹1,820 | 20 users |

### AI Token Packs (Top-Up for Overages):

| Pack | Calls | Price | Per Call | Profit Margin |
|------|-------|-------|----------|---------------|
| Starter | 25 | ₹325 | ₹13.00 | 93% |
| Regular | 50 | ₹599 | ₹11.98 | 92% |
| Popular | 100 | ₹1,099 | ₹10.99 | 92% |
| Professional | 250 | ₹2,499 | ₹9.99 | 91% |
| Enterprise | 500 | ₹4,499 | ₹8.99 | 90% |

### How AI Limits Work:

1. **Check Before Use**: `@require_ai_quota` decorator checks limit before AI call
2. **Monthly Quota**: Each plan has fixed monthly AI calls
3. **Auto-Refill**: Quotas reset on billing cycle
4. **Token Fallback**: If quota exhausted, uses purchased tokens
5. **Cache Optimization**: Repeated queries are free (cached)
6. **403 Error**: Blocks API call if quota exhausted and no tokens

### AI Endpoints Protected:

✅ All 18 AI endpoints have `@require_ai_quota`:
- `/ai_suggestion/past_questions`
- `/ai_suggestion/provisional_diagnosis`
- `/ai_suggestion/subjective/*`
- `/ai_suggestion/perspectives/*`
- `/ai_suggestion/initial_plan/*`
- `/ai_suggestion/pathophysiology/*`
- `/ai_suggestion/clinical_flags/*`
- `/ai_suggestion/smart_goals/*`
- `/ai_suggestion/treatment_plan/*`
- `/ai_suggestion/followup/*`

**Result**: ✅ **AI is fully protected from abuse**

---

## ⚠️ VOICE TYPING LIMITS - NEEDS IMPLEMENTATION

### Current Status:
- **File**: `main.py` line 10230 (`/api/transcribe`)
- **Protection**: ❌ **NONE** - Only has `@login_required()`, no quota check
- **Tracking**: ✅ Logs duration but doesn't enforce limits
- **Risk**: **Users can transcribe unlimited audio = unlimited costs**

### Recommended Limits (Based on Azure Pricing):

**Azure Speech Cost**: $1/hour = ₹83/hour ≈ **₹1.38/minute**

Suggested monthly limits by plan:

| Plan | Monthly Minutes | Cost to You | Notes |
|------|----------------|-------------|-------|
| **Free Trial** | 10 minutes | ₹14 | ~5 notes (2 min each) |
| **Solo** | 60 minutes | ₹83 | ~30 notes |
| **Team (5)** | 300 minutes | ₹414 | ~150 notes (5 users) |
| **Team Pro (10)** | 600 minutes | ₹828 | ~300 notes (10 users) |
| **Institute (15)** | 900 minutes | ₹1,242 | ~450 notes (15 users) |
| **Institute+ (20)** | 1,200 minutes | ₹1,656 | ~600 notes (20 users) |

**Optional**: Sell voice minutes top-up packs at 2-3x cost (similar to AI tokens)

---

## 🔨 HOW TO ADD VOICE TYPING LIMITS (CRITICAL!)

### Step 1: Add Voice Limits to Plans

**File**: `subscription_manager.py` (lines 40-142)

```python
PLANS = {
    'free_trial': {
        'name': 'Free Trial',
        'price': 0,
        'currency': 'INR',
        'patients_limit': 10,
        'ai_calls_limit': FREE_TRIAL_AI_CALLS,
        'voice_minutes_limit': 10,  # ← ADD THIS
        'duration_days': FREE_TRIAL_DAYS,
        # ...
    },
    'solo': {
        'name': 'Solo Professional',
        'price': 1499,
        'currency': 'INR',
        'patients_limit': -1,
        'ai_calls_limit': 50,
        'voice_minutes_limit': 60,  # ← ADD THIS
        'max_users': 1,
        # ...
    },
    # Add to all other plans...
}
```

### Step 2: Add Voice Tracking Functions

**File**: `subscription_manager.py` (after line 538)

```python
def check_voice_limit(user_id: str) -> Tuple[bool, str]:
    """
    Check if user can use voice transcription.

    Args:
        user_id: User's email or Firebase UID

    Returns:
        tuple: (can_use_voice: bool, message: str)
    """
    try:
        subscription = get_user_subscription(user_id)

        # Check if subscription is active
        if subscription.get('status') != 'active':
            return False, "Your subscription has expired. Please upgrade to continue using voice typing."

        # Get limits
        voice_minutes_limit = subscription.get('voice_minutes_limit', 0)
        voice_minutes_used = subscription.get('voice_minutes_this_month', 0)

        # Check if within quota
        if voice_minutes_used < voice_minutes_limit:
            return True, ""

        # Quota exhausted
        return False, f"Voice typing quota exhausted ({voice_minutes_limit} minutes). Please upgrade your plan."

    except Exception as e:
        logger.error(f"Error checking voice limit for {user_id}: {e}")
        return False, "Error checking voice quota. Please try again."


def deduct_voice_usage(user_id: str, duration_seconds: float) -> bool:
    """
    Deduct voice usage from user's quota.

    Args:
        user_id: User's email or Firebase UID
        duration_seconds: Audio duration in seconds

    Returns:
        bool: Success status
    """
    try:
        duration_minutes = duration_seconds / 60.0

        sub_ref = db.collection('subscriptions').document(user_id)
        sub_doc = sub_ref.get()

        if not sub_doc.exists:
            return False

        subscription = sub_doc.to_dict()
        voice_minutes_used = subscription.get('voice_minutes_this_month', 0)

        # Update usage
        sub_ref.update({
            'voice_minutes_this_month': voice_minutes_used + duration_minutes,
            'updated_at': SERVER_TIMESTAMP
        })

        logger.info(f"Deducted voice usage for {user_id}: {duration_minutes:.2f} minutes")

        # Log usage for billing
        db.collection('voice_usage_logs').add({
            'user_id': user_id,
            'duration_seconds': duration_seconds,
            'duration_minutes': duration_minutes,
            'timestamp': SERVER_TIMESTAMP
        })

        return True

    except Exception as e:
        logger.error(f"Error deducting voice usage for {user_id}: {e}")
        return False
```

### Step 3: Add Voice Quota Middleware

**File**: `quota_middleware.py` (after line 158)

```python
def require_voice_quota(f):
    """
    Decorator to check voice transcription quota before executing function.

    Usage:
        @app.route('/api/transcribe')
        @require_auth
        @require_voice_quota
        def api_transcribe_audio():
            # Transcription logic
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get user ID from g.user (set by @require_auth)
            user_id = g.user.get('email') or g.user.get('uid')

            if not user_id:
                return jsonify({'error': 'User not authenticated'}), 401

            # Check voice quota
            can_use_voice, message = check_voice_limit(user_id)

            if not can_use_voice:
                logger.warning(f"Voice quota exceeded for {user_id}: {message}")
                return jsonify({
                    'error': 'Quota exceeded',
                    'message': message,
                    'quota_type': 'voice_minutes',
                    'action_required': 'upgrade'
                }), 403

            # Execute the function
            result = f(*args, **kwargs)

            # Check if the response indicates success
            if isinstance(result, tuple):
                response, status_code = result[0], result[1] if len(result) > 1 else 200
            else:
                response, status_code = result, 200

            # Only deduct if request was successful (2xx status)
            if 200 <= status_code < 300:
                # Get duration from response
                if isinstance(response, dict) or hasattr(response, 'get_json'):
                    response_data = response if isinstance(response, dict) else response.get_json()
                    duration = response_data.get('duration', 0)

                    if duration > 0:
                        deduct_voice_usage(user_id, duration)
                        logger.info(f"Deducted voice quota for {user_id}: {duration:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Error in voice quota middleware: {e}")
            return jsonify({'error': 'Quota check failed'}), 500

    return decorated_function
```

### Step 4: Protect Transcribe Endpoint

**File**: `main.py` line 10230

**BEFORE**:
```python
@app.route('/api/transcribe', methods=['POST'])
@login_required()
def api_transcribe_audio():
```

**AFTER**:
```python
@app.route('/api/transcribe', methods=['POST'])
@login_required()
@require_voice_quota  # ← ADD THIS
def api_transcribe_audio():
```

**Also add import** at top of `main.py`:
```python
from quota_middleware import require_patient_quota, require_ai_quota, require_voice_quota  # ← Add require_voice_quota
```

### Step 5: Update Subscription Dashboard

**File**: `templates/subscription_dashboard.html`

Add voice usage display similar to AI calls:

```html
<div class="usage-item">
    <div class="usage-header">
        <span>🎤 Voice Typing</span>
        <span class="usage-value" id="voice-usage">
            {{ usage_stats.voice_minutes_used|round(1) }}/{{ usage_stats.voice_minutes_limit }} min
        </span>
    </div>
    <div class="progress-bar">
        <div class="progress-fill" style="width: {{ (usage_stats.voice_minutes_used / usage_stats.voice_minutes_limit * 100)|round }}%"></div>
    </div>
</div>
```

---

## 📋 ADDITIONAL SAFETY MEASURES

### 1. Rate Limiting (Already Implemented)

**File**: `rate_limiter.py`

- **Default**: 1000 requests/hour, 100 requests/minute per user
- **Storage**: Redis-based (persistent)
- **Fallback**: In-memory if Redis unavailable

### 2. Login Protection (Already Implemented)

- **Max Failed Attempts**: 5
- **Lockout Duration**: 15 minutes
- **Storage**: Redis with TTL

### 3. Additional Recommendations

**Add per-endpoint rate limits for expensive operations**:

```python
# In main.py, for voice typing endpoint
@app.route('/api/transcribe', methods=['POST'])
@limiter.limit("20 per hour")  # ← ADD THIS (max 20 transcriptions/hour)
@login_required()
@require_voice_quota
def api_transcribe_audio():
    # ...
```

**Add maximum audio duration check**:

```python
# In main.py, api_transcribe_audio function
MAX_AUDIO_DURATION = 300  # 5 minutes max

# After getting audio blob
audio_size_mb = len(audio_blob) / (1024 * 1024)
estimated_duration = audio_size_mb * 60  # Rough estimate

if estimated_duration > MAX_AUDIO_DURATION:
    return jsonify({
        'success': False,
        'error': f'Audio too long. Maximum {MAX_AUDIO_DURATION} seconds allowed.'
    }), 400
```

---

## 🎯 PRODUCTION DEPLOYMENT CHECKLIST

### Critical (Must Do Before Launch):

- [ ] **Add voice typing limits** (Steps 1-5 above)
- [ ] **Test quota enforcement** (try exceeding limits)
- [ ] **Test token top-ups** (AI tokens purchase flow)
- [ ] **Set up monitoring** (CloudWatch/Sentry for quota alerts)
- [ ] **Configure Redis** (for rate limiting persistence)
- [ ] **Set environment variables**:
  - `AZURE_SPEECH_KEY` (voice typing)
  - `AZURE_OPENAI_KEY` (AI suggestions)
  - `REDIS_HOST`, `REDIS_PASSWORD` (rate limiting)

### Recommended (Nice to Have):

- [ ] Add voice minutes top-up packs (like AI tokens)
- [ ] Add quota warning notifications (80%, 90%, 100%)
- [ ] Add usage analytics dashboard for admins
- [ ] Add max audio duration limit (5 minutes)
- [ ] Add per-endpoint rate limits (20 transcriptions/hour)
- [ ] Set up cost alerts in Azure (email when >$X/day)

---

## 💵 COST ESTIMATES (Monthly)

### Worst-Case Scenario (All Users Max Out):

**Assumptions**:
- 100 Solo users (₹1,499/month each)
- All use full AI quota (50 calls/month)
- All use full voice quota (60 minutes/month)

**Costs**:
- **AI**: 100 users × 50 calls × ₹0.91 = ₹4,550/month
- **Voice**: 100 users × 60 min × ₹1.38 = ₹8,280/month
- **Total**: ₹12,830/month
- **Revenue**: 100 × ₹1,499 = ₹1,49,900/month
- **Gross Profit**: ₹1,37,070/month (91% margin)

**Conclusion**: ✅ Even at full utilization, highly profitable!

---

## 🚨 CRITICAL WARNING SIGNS TO MONITOR

Once live, watch for these abuse patterns:

1. **Single user exceeding typical usage by 10x** (investigate)
2. **Rapid successive API calls** (possible script/bot abuse)
3. **Same prompt repeated 100+ times** (cache should catch this)
4. **Voice transcriptions >5 minutes** (unusual for clinical notes)
5. **Sudden spike in costs** (Azure cost alerts)

**Action**: Implement CloudWatch alerts for these patterns.

---

## ✅ FINAL ANSWER TO YOUR QUESTION

### Can you publish as-is after testing?

**YES**, but with **ONE CRITICAL ADDITION**:

1. ✅ **AI limits** - Fully implemented and enforced
2. ⚠️ **Voice limits** - **NOT IMPLEMENTED** (must add before production)
3. ✅ **Rate limiting** - Fully implemented
4. ✅ **Authentication** - Fully implemented

### Priority 1 (Before Production):
- **Add voice typing limits** (follow Steps 1-5 above) - **~2 hours work**

### Priority 2 (First Week of Production):
- Add CloudWatch cost alerts
- Monitor usage patterns
- Add voice minutes top-up packs

### Priority 3 (First Month):
- Add quota warning notifications
- Add admin usage analytics
- Optimize cache hit rate

---

**Estimated Time to Production Ready**: 2-3 hours (just voice limits)

**Risk Level Without Voice Limits**: 🔴 **HIGH** - Unlimited transcription costs

**Risk Level With Voice Limits**: 🟢 **LOW** - All expensive features protected

---

**Last Updated**: 2026-02-06
**Next Review**: After adding voice limits and initial testing
