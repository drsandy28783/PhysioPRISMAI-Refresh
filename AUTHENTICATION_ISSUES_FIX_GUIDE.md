# Authentication Issues - Root Cause Analysis & Fix Guide

**Date:** January 14, 2026
**Status:** 🔴 CRITICAL - Login Broken on Azure Deployment

---

## 🔍 Issues Identified

### Issue #1: Login Returns 401 Error
**Symptom:** `/api/verify-login` endpoint returns 401 Unauthorized
**User Impact:** Users cannot log in to the application
**Error Location:** `app_auth.py:76-158` (`@require_firebase_auth` decorator)

### Issue #2: Homepage Prompting for Login
**Symptom:** Homepage (public marketing page) may redirect logged-in users
**User Impact:** Marketing page becomes inaccessible to authenticated users
**Error Location:** `templates/base.html` Firebase initialization on all pages

---

## 🔬 Root Cause Analysis

### **Issue #1: Missing Firebase Credentials on Azure**

#### What's Happening:
1. **Frontend:** Firebase Auth sign-in **succeeds** ✅
   - Console shows: `"Firebase Auth sign-in successful: drsandeep@physiologicprism.com"`
   - Firebase ID token is generated

2. **Backend:** Firebase Admin SDK **cannot verify** the token ❌
   - Returns `401 Unauthorized`
   - Token verification fails in `app_auth.py:118-120`

#### Why It's Failing:

The Firebase Admin SDK requires **service account credentials** to verify ID tokens. Currently:

**Local/GCP Deployment:**
```python
# app_auth.py lines 33-44
firebase_admin.initialize_app(options={
    'projectId': FIREBASE_PROJECT_ID  # ✅ Works with Application Default Credentials
})
```

**Azure Deployment:**
```python
# Same code, BUT Azure doesn't have Application Default Credentials
firebase_admin.initialize_app(options={
    'projectId': FIREBASE_PROJECT_ID  # ⚠️ Initializes but CAN'T verify tokens!
})
```

**The Problem:**
- Firebase Admin SDK initializes successfully with just `projectId`
- BUT token verification requires **private keys** from service account
- Without credentials, `auth.verify_id_token()` fails silently → 401 error

#### Evidence:

**Current .env configuration:**
```bash
# No Firebase credentials!
COSMOS_DB_ENDPOINT=https://physiologicprism-cosmosdb.documents.azure.com:443/
COSMOS_DB_KEY=<your-cosmos-db-key-here>
AZURE_OPENAI_ENDPOINT=https://physiologicprism-openai.openai.azure.com/
# ... but no GOOGLE_APPLICATION_CREDENTIALS or FIREBASE credentials
```

**Expected configuration (from `.env.example`):**
```bash
FIREBASE_PROJECT_ID=physiologicprism-474610
GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type": "service_account", "project_id": "physiologicprism-474610", "private_key": "...", ...}'
```

---

### **Issue #2: Firebase Auth Code on Public Homepage**

#### What's Happening:

`homepage.html` extends `base.html`, which includes:
- **Lines 90-107:** Firebase app initialization (all pages)
- **Lines 154-180:** Notification polling (authenticated users only)

This means Firebase Auth runs on **every page** including marketing pages.

#### Why It's a Problem:

**Current Structure:**
```
homepage.html (PUBLIC marketing page)
  ↓ extends
base.html (contains Firebase init + auth logic)
  ↓ includes
Firebase auto-login check
```

**Impact:**
- Logged-in users visiting homepage might be auto-redirected to dashboard
- Unnecessary Firebase initialization on public pages
- Potential for unwanted authentication flows on marketing site

---

## ✅ Solutions

### **Solution #1: Add Firebase Credentials to Azure Deployment**

Firebase Admin SDK needs credentials to verify tokens. Three options:

#### **Option A: Environment Variable (RECOMMENDED for Azure)**

1. **Get Firebase Service Account JSON:**
   ```bash
   # From Firebase Console
   # Project Settings → Service Accounts → Generate New Private Key
   ```

2. **Add to Azure Container App Environment Variables:**
   ```bash
   # Option 1: Via Azure Portal
   az containerapp update \
     --name physiologicprism-app \
     --resource-group rg-physiologicprism-prod \
     --set-env-vars \
       "FIREBASE_PROJECT_ID=physiologicprism-474610" \
       "GOOGLE_APPLICATION_CREDENTIALS_JSON='{\"type\":\"service_account\",\"project_id\":\"physiologicprism-474610\",\"private_key\":\"-----BEGIN PRIVATE KEY-----\\n...\",\"client_email\":\"firebase-adminsdk-xxxxx@physiologicprism-474610.iam.gserviceaccount.com\"}'"

   # Option 2: Via Azure Portal UI
   # Container Apps → physiologicprism-app → Environment Variables
   # Add: GOOGLE_APPLICATION_CREDENTIALS_JSON (paste entire JSON)
   ```

3. **Update `app_auth.py` to use credentials:**
   ```python
   # Lines 35-44 - ALREADY IMPLEMENTED!
   try:
       firebase_admin.get_app()
   except ValueError:
       sa_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON', '')
       if sa_json.strip():
           cred_dict = json.loads(sa_json)
           cred = credentials.Certificate(cred_dict)
           firebase_admin.initialize_app(cred, {'projectId': cred_dict.get('project_id')})
       else:
           # Fallback to Application Default Credentials (current behavior)
           firebase_admin.initialize_app(options={'projectId': FIREBASE_PROJECT_ID})
   ```

**UPDATE:** Looking at `app_auth.py`, I notice it currently **doesn't** check for `GOOGLE_APPLICATION_CREDENTIALS_JSON`. Let me check the actual initialization code.

---

#### **Option B: Managed Identity (Azure-Native Solution)**

**NOT RECOMMENDED** because:
- Firebase doesn't natively support Azure Managed Identity
- Would require custom token proxy service
- Adds complexity without security benefit

---

#### **Option C: Azure Key Vault (HIPAA-Compliant Option)**

For production environments requiring strict secrets management:

1. **Store Firebase credentials in Azure Key Vault:**
   ```bash
   az keyvault secret set \
     --vault-name physiologicprism-kv \
     --name firebase-service-account \
     --value @firebase-service-account.json
   ```

2. **Grant Container App access to Key Vault:**
   ```bash
   az containerapp identity assign \
     --name physiologicprism-app \
     --resource-group rg-physiologicprism-prod \
     --system-assigned

   az keyvault set-policy \
     --name physiologicprism-kv \
     --object-id <container-app-identity-id> \
     --secret-permissions get
   ```

3. **Update app to fetch from Key Vault:**
   ```python
   from azure.identity import DefaultAzureCredential
   from azure.keyvault.secrets import SecretClient

   credential = DefaultAzureCredential()
   client = SecretClient(vault_url="https://physiologicprism-kv.vault.azure.net/", credential=credential)
   firebase_creds = client.get_secret("firebase-service-account").value
   ```

---

### **Solution #2: Fix Homepage Firebase Auto-Login**

#### **Option A: Create Separate Base Template for Public Pages**

**Create `templates/base_public.html`:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}PhysiologicPRISM{% endblock %}</title>
    <link rel="icon" type="image/png" href="{{ url_for('static', filename='logo.png') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}?v=3">

    {% block head %}{% endblock %}
</head>
<body>
    <div class="container">
        {% block content %}{% endblock %}
    </div>

    {% block scripts %}{% endblock %}

    <!-- NO Firebase initialization -->
    <!-- NO authentication checks -->
    <!-- NO notification polling -->
</body>
</html>
```

**Update `homepage.html` line 1:**
```html
{% extends "base_public.html" %}  <!-- Changed from base.html -->
```

**Also update other public pages:**
- `templates/security_page.html`
- `templates/pilot_program.html`
- `templates/request_access.html`
- `templates/pricing.html`

---

#### **Option B: Conditional Firebase Loading (Quick Fix)**

**Update `templates/base.html` lines 90-107:**
```html
<!-- Firebase Initialization - ONLY for authenticated pages -->
{% if request.endpoint not in ['homepage', 'security_page', 'pilot_program', 'request_access', 'login', 'register'] %}
<script type="module" nonce="{{ csp_nonce() }}">
    import { initializeApp } from 'https://www.gstatic.com/firebasejs/9.23.0/firebase-app.js';
    import { getAuth } from 'https://www.gstatic.com/firebasejs/9.23.0/firebase-auth.js';

    const firebaseConfig = {
        apiKey: "AIzaSyAI2QaNaJuA6cV_KSJlgsyus11-GKzxee8",
        authDomain: "physiologicprism-474610.firebaseapp.com",
        projectId: "physiologicprism-474610",
        storageBucket: "physiologicprism-474610.firebasestorage.app",
        messagingSenderId: "292385113403",
        appId: "1:292385113403:web:02abf02787ba4e02cba31e"
    };

    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    window.__FIREBASE_READY__ = true;
</script>
{% endif %}
```

**Recommended:** Option A (separate template) for cleaner separation of concerns.

---

## 🚀 Implementation Steps

### **STEP 1: Fix Firebase Credentials (URGENT)**

**1.1 Download Firebase Service Account:**
```bash
# Go to Firebase Console
https://console.firebase.google.com/project/physiologicprism-474610/settings/serviceaccounts/adminsdk

# Click "Generate New Private Key"
# Save as: firebase-service-account.json
```

**1.2 Update `app_auth.py` to support credentials:**

**Current code (lines 29-44):**
```python
# Initialize Firebase Admin SDK using Application Default Credentials
FIREBASE_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('FIREBASE_PROJECT_ID') or 'physiologicprism-474610'

try:
    firebase_admin.get_app()
    logger.info("Firebase Admin SDK already initialized")
except ValueError:
    firebase_admin.initialize_app(options={
        'projectId': FIREBASE_PROJECT_ID
    })
    logger.info(f"Firebase Admin SDK initialized successfully for project {FIREBASE_PROJECT_ID}")
```

**NEEDS TO BE CHANGED TO:**
```python
import json
from firebase_admin import credentials

FIREBASE_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('FIREBASE_PROJECT_ID') or 'physiologicprism-474610'

try:
    firebase_admin.get_app()
    logger.info("Firebase Admin SDK already initialized")
except ValueError:
    # Try to initialize with explicit credentials
    sa_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON', '').strip()

    if sa_json:
        # Parse JSON credentials from environment variable
        try:
            cred_dict = json.loads(sa_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'projectId': cred_dict.get('project_id')})
            logger.info(f"Firebase Admin SDK initialized with explicit credentials for project {FIREBASE_PROJECT_ID}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
            raise ValueError("Invalid Firebase credentials JSON")
    else:
        # Fallback to Application Default Credentials (for local/GCP)
        logger.warning("No explicit Firebase credentials found. Using Application Default Credentials.")
        firebase_admin.initialize_app(options={
            'projectId': FIREBASE_PROJECT_ID
        })
        logger.info(f"Firebase Admin SDK initialized with ADC for project {FIREBASE_PROJECT_ID}")
```

**1.3 Add credentials to Azure Container App:**

**Via Azure CLI:**
```bash
# Read the service account file
FIREBASE_CREDS=$(cat firebase-service-account.json | jq -c .)

# Update Azure Container App
az containerapp update \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --set-env-vars \
    "FIREBASE_PROJECT_ID=physiologicprism-474610" \
    "GOOGLE_APPLICATION_CREDENTIALS_JSON=${FIREBASE_CREDS}"

# Restart the app
az containerapp restart \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod
```

**Via Azure Portal:**
1. Navigate to: Azure Portal → Container Apps → `physiologicprism-app`
2. Click "Containers" → "Edit and deploy"
3. Go to "Environment variables" tab
4. Add new variable:
   - **Name:** `GOOGLE_APPLICATION_CREDENTIALS_JSON`
   - **Value:** (paste entire contents of `firebase-service-account.json`)
5. Click "Create" to deploy new revision

---

### **STEP 2: Fix Homepage Auto-Login**

**2.1 Create `base_public.html` template** (recommended approach)

**2.2 Update all public pages to use `base_public.html`:**
- `homepage.html`
- `security_page.html` (if exists)
- `pilot_program.html` (if exists)
- `request_access.html` (if exists)

---

## 🧪 Testing Checklist

After implementing fixes:

### **Test #1: Login Functionality**
- [ ] Navigate to `/login`
- [ ] Enter email: `drsandeep@physiologicprism.com`
- [ ] Enter correct password
- [ ] Verify: Login succeeds (no 401 error)
- [ ] Verify: Redirects to dashboard
- [ ] Check browser console: No errors

### **Test #2: Homepage Access (Unauthenticated)**
- [ ] Open incognito/private window
- [ ] Navigate to `/homepage`
- [ ] Verify: Page loads without login prompt
- [ ] Verify: "Request early access" button visible
- [ ] Verify: No Firebase errors in console

### **Test #3: Homepage Access (Authenticated)**
- [ ] Login first
- [ ] Navigate to `/homepage`
- [ ] Verify: Page loads normally
- [ ] Verify: NO auto-redirect to dashboard
- [ ] Verify: Can navigate to other public pages

### **Test #4: Token Verification Backend**
- [ ] Check Azure Container App logs:
   ```bash
   az containerapp logs show \
     --name physiologicprism-app \
     --resource-group rg-physiologicprism-prod \
     --follow
   ```
- [ ] Verify log entry: `"Firebase Admin SDK initialized with explicit credentials"`
- [ ] Verify log entry: `"Authenticated user: <uid>"` on login
- [ ] Verify NO errors: `"Invalid token"` or `"Authentication failed"`

---

## 📋 Deployment Checklist

### **Production Deployment:**

```bash
# 1. Backup current configuration
az containerapp show \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  > backup-config-$(date +%Y%m%d).json

# 2. Update environment variables
az containerapp update \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --set-env-vars \
    "GOOGLE_APPLICATION_CREDENTIALS_JSON@firebase-creds-secret"  # Using secret reference

# 3. Store credentials in Azure Container App secrets (HIPAA-compliant)
az containerapp secret set \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --secrets firebase-creds-secret="$(cat firebase-service-account.json | jq -c .)"

# 4. Deploy updated code
# (Your existing deployment process)

# 5. Verify deployment
az containerapp revision list \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --output table

# 6. Test login endpoint
curl -X POST https://physiologicprism-app.whitebeach-b88404fa.eastus.azurecontainerapps.io/api/verify-login \
  -H "Authorization: Bearer <test-token>" \
  -H "Content-Type: application/json"
```

---

## 🔐 Security Considerations

### **Firebase Credentials in Azure:**

1. **Use Azure Container App Secrets (REQUIRED for production)**
   - Don't store credentials in environment variables directly
   - Use secret references: `GOOGLE_APPLICATION_CREDENTIALS_JSON@firebase-creds-secret`

2. **Rotate credentials regularly:**
   ```bash
   # Generate new service account key annually
   # Update Azure Container App secret
   # Delete old key from Firebase Console
   ```

3. **Limit service account permissions:**
   - Firebase Console → Service Accounts → Permissions
   - Grant only "Firebase Admin SDK Administrator Service Agent"
   - Remove unnecessary roles

4. **Monitor credential usage:**
   ```bash
   # Check Firebase logs for authentication events
   gcloud logging read "resource.type=firebase" --limit 50
   ```

---

## 📊 Alternative: Migrate to Azure AD B2C (Long-term Solution)

**Current State:**
- Frontend: Firebase Auth ✅
- Backend: Firebase Admin SDK → Cosmos DB ⚠️
- AI: Azure OpenAI ✅

**Proposed State (Full Azure Migration):**
- Frontend: MSAL.js (Microsoft Authentication Library)
- Backend: Azure AD B2C → Cosmos DB
- AI: Azure OpenAI ✅

**Benefits:**
- Single cloud provider (Azure)
- Native HIPAA compliance
- Integrated with Azure security tools
- Lower cost (no Firebase dependencies)

**Migration Steps:**
1. Set up Azure AD B2C tenant
2. Configure user flows (sign-up, sign-in, password reset)
3. Update frontend to use MSAL.js
4. Update backend to verify Azure AD B2C tokens
5. Migrate existing user accounts
6. Decommission Firebase Auth

**Estimated Effort:** 16-24 hours
**Recommended Timeline:** After stabilizing current Firebase Auth implementation

---

## 🎯 Summary

### **Root Causes:**
1. ❌ Firebase Admin SDK missing service account credentials on Azure
2. ⚠️ Firebase auto-login running on public homepage

### **Immediate Fixes:**
1. ✅ Add `GOOGLE_APPLICATION_CREDENTIALS_JSON` to Azure Container App
2. ✅ Update `app_auth.py` to use explicit credentials
3. ✅ Create `base_public.html` for public pages

### **Long-term Recommendation:**
- Migrate to Azure AD B2C for full Azure integration
- Eliminates Firebase dependency
- Simpler credential management

---

## 📞 Support

**If issues persist after implementing fixes:**

1. Check Azure Container App logs:
   ```bash
   az containerapp logs show \
     --name physiologicprism-app \
     --resource-group rg-physiologicprism-prod \
     --follow
   ```

2. Verify Firebase credentials are valid:
   ```bash
   # Test locally first
   export GOOGLE_APPLICATION_CREDENTIALS_JSON='$(cat firebase-service-account.json | jq -c .)'
   python -c "import firebase_admin; from firebase_admin import credentials; firebase_admin.initialize_app(credentials.Certificate(json.loads(os.environ['GOOGLE_APPLICATION_CREDENTIALS_JSON'])))"
   ```

3. Contact:
   - Firebase Support: https://firebase.google.com/support
   - Azure Support: https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade

---

**Document Version:** 1.0
**Last Updated:** January 14, 2026
**Next Review:** After fixes are deployed
