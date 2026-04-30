---
name: mobile-web-debug
description: >
  Use this skill to debug the PhysiologicPRISM Expo/React Native mobile app against the
  Flask web app it is based on. Triggers when Sandeep says the mobile app is broken in
  production but works in Expo Go, when features work on web but not mobile, when there
  are API connection errors in the built app, when EAS build behaves differently from
  local dev, when authentication fails in production, or when the mobile and web app are
  out of sync. Also triggers for phrases like "mobile app not working", "Expo Go works 
  but build doesn't", "production build fails", "API not connecting on phone", "why does
  web work but not mobile", "check mobile against web code", or any request to compare
  mobile and web feature parity. This is the definitive skill for all PRISM mobile 
  debugging — use it even if the user doesn't mention Expo by name.
---

# Mobile ↔ Web Debug Skill — PhysiologicPRISM

## Stack Overview

| Layer | Web App | Mobile App |
|---|---|---|
| Framework | Flask (Python) | React Native + Expo |
| Auth | Firebase Auth → Flask session | Firebase Auth → Azure token |
| Database | Azure Cosmos DB | Azure Cosmos DB (same) |
| AI | Azure OpenAI (via Flask routes) | Azure OpenAI (via Flask API) |
| Storage | Azure Blob Storage | Azure Blob Storage |
| Hosting | Azure Container Apps | EAS Build → Play Store / App Store |
| Dev tool | Flask dev server | Expo Go (dev) / EAS Build (prod) |

---

## The Core Problem: Expo Go ≠ Production Build

This is the #1 source of mobile-specific bugs. Here's why they differ:

| Behaviour | Expo Go | EAS Production Build |
|---|---|---|
| Native modules | Uses Expo's pre-built bundle | Must be declared in `app.json` plugins |
| Environment variables | Read from `.env` directly | Must be baked in via `eas.json` or `app.config.js` |
| Network | Uses dev machine's network | Uses device's real network (no localhost) |
| SSL certificates | Dev certs accepted | Must be valid HTTPS only |
| Firebase config | Loaded from JS at runtime | Must be bundled — no runtime file reads |
| Deep links | Not enforced | Must match `scheme` in `app.json` |
| Permissions | Often auto-granted | Must be declared in `app.json` |

---

## Diagnosis Framework

When the user reports a bug, run through these phases **in order**. Each phase has specific files to check and commands to run.

### Phase 1 — Environment Variables (Most common cause)

**Symptom:** App works in Expo Go, API calls fail in production build.

**Check:**
```bash
# In mobile project root
cat .env                    # What's set for dev?
cat eas.json                # What's set for production?
cat app.config.js           # Is EXPO_PUBLIC_ prefix used?
```

**What to look for:**
```js
// WRONG — undefined in production builds
const API_URL = process.env.API_URL;

// CORRECT — Expo requires EXPO_PUBLIC_ prefix
const API_URL = process.env.EXPO_PUBLIC_API_URL;
```

**Check `eas.json`:**
```json
{
  "build": {
    "production": {
      "env": {
        "EXPO_PUBLIC_API_URL": "https://physiologicprism.azurecontainerapps.io",
        "EXPO_PUBLIC_FIREBASE_API_KEY": "...",
        "EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN": "..."
      }
    },
    "preview": {
      "env": {
        "EXPO_PUBLIC_API_URL": "http://192.168.x.x:5000"
      }
    }
  }
}
```

**Compare against web app's config:**
```python
# Flask app.py / config.py
AZURE_COSMOS_URL = os.environ.get("COSMOS_DB_URL")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")
```

---

### Phase 2 — API Base URL (Second most common)

**Symptom:** All API calls 404 or timeout in production.

**Files to check in mobile app:**
```
src/api/client.js   OR   src/services/api.js   OR   src/config.js
```

**Look for:**
```js
// BUG — hardcoded localhost never works on a real device
const BASE_URL = 'http://localhost:5000';

// BUG — private IP only works on same WiFi network
const BASE_URL = 'http://192.168.1.10:5000';

// CORRECT — production Azure URL
const BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'https://physiologicprism.azurecontainerapps.io';
```

**Cross-check against Flask CORS config:**
```python
# app.py — mobile app's origin must be in allowed list
CORS(app, supports_credentials=True, origins=[
    "https://physiologicprism.com",
    "https://physiologicprism.web.app",
    # ↓ Is Expo/React Native bundle origin allowed?
    "capacitor://localhost",
    "http://localhost",
])
```

---

### Phase 3 — Firebase Authentication Flow

**Symptom:** Login works in Expo Go, fails in production build. OR: tokens not passing to Flask API.

**Files to check:**
```
src/services/firebase.js
src/services/auth.js
src/hooks/useAuth.js
```

**Common bugs:**

```js
// BUG 1 — Firebase not initialized before use
import { initializeApp } from 'firebase/app';
const app = initializeApp(firebaseConfig); // Must happen at module load, not inside a function

// BUG 2 — Wrong persistence for native builds
// Web uses browserLocalPersistence, React Native needs AsyncStorage
import { initializeAuth, getReactNativePersistence } from 'firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';

const auth = initializeAuth(app, {
  persistence: getReactNativePersistence(AsyncStorage)  // ← Required for production
});

// BUG 3 — Token not attached to API calls
const token = await user.getIdToken();  // Get Firebase token
// Must be sent as: Authorization: Bearer {token}
// Check that Flask @login_required reads this header, not just cookies
```

**Web app uses Flask sessions (cookies). Mobile must use Bearer tokens.** Check Flask routes:
```python
# If Flask auth only checks session cookie, mobile will always get 401
# Must also accept:
auth_header = request.headers.get('Authorization')
if auth_header and auth_header.startswith('Bearer '):
    token = auth_header.split(' ')[1]
    # verify Firebase token with firebase-admin
```

---

### Phase 4 — Native Module Mismatches

**Symptom:** Crash on launch in production, or specific feature crashes (camera, file picker, etc.).

**Check `app.json` plugins:**
```json
{
  "expo": {
    "plugins": [
      "expo-camera",
      "expo-file-system",
      "expo-document-picker",
      ["expo-build-properties", {
        "android": { "compileSdkVersion": 34 }
      }]
    ],
    "android": {
      "permissions": [
        "CAMERA",
        "READ_EXTERNAL_STORAGE",
        "WRITE_EXTERNAL_STORAGE",
        "INTERNET"
      ]
    }
  }
}
```

**Any native module used in code must be declared here.** Expo Go bundles everything; production builds only include what you declare.

---

### Phase 5 — Feature Parity Audit (Web vs Mobile)

Compare PRISM module coverage. For each module, check:
1. Does the mobile screen exist?
2. Does it call the same Flask API endpoint as the web form?
3. Are all form fields present in mobile that exist in web?
4. Does the AI button call the same `/api/ai/...` route?

**Run this audit:**
```bash
# List all Flask AI routes in web app
grep -n "@app.route('/api/ai" app.py

# List all API calls in mobile app
grep -rn "fetch\|axios\|api.get\|api.post" src/ | grep -v node_modules
```

**Then diff the two lists** — missing endpoints in mobile = missing features.

---

### Phase 6 — EAS Build Logs

When a production build crashes or behaves differently:

```bash
# View latest build logs
eas build:list
eas build:view {BUILD_ID}

# Run a preview build (closer to production than Expo Go)
eas build --profile preview --platform android

# Install preview APK directly on device for testing
# (Much faster debug loop than full production build)

# Check build environment variables are set
eas env:list
```

**Useful PowerShell equivalents:**
```powershell
# View EAS builds
npx eas-cli build:list

# Trigger build
npx eas-cli build --profile production --platform android

# Check env vars
npx eas-cli env:list --scope project
```

---

### Phase 7 — Network & SSL Issues

**Symptom:** Works on WiFi (same network as dev server), fails on mobile data or after deployment.

```js
// Check for any HTTP (non-HTTPS) calls — Android blocks these by default in prod
// Search mobile codebase:
// grep -rn "http://" src/

// Fix: Ensure ALL production URLs use https://
// Azure Container Apps gives HTTPS by default ✓
// Azure Blob Storage SAS URLs use HTTPS ✓

// For Android cleartext traffic (dev only, never production):
// app.json → android → usesCleartextTraffic: true  ← NEVER in production
```

---

## Side-by-Side Code Comparison Template

When comparing a specific feature between web and mobile, use this structure:

```
FEATURE: [e.g., "Present History AI Suggestion"]

WEB (Flask):
  Route: POST /api/ai/subjective-suggestions
  Auth:  Flask session cookie (@login_required)
  Input: { patient_id, chief_complaint }
  Output: { suggestions: [...] }

MOBILE:
  File: src/screens/PresentHistoryScreen.js
  Call: api.post('/api/ai/subjective-suggestions', { ... })
  Auth: Bearer token header ✓/✗
  Input matches web: ✓/✗
  Handles loading state: ✓/✗
  Handles error state: ✓/✗
  Displays response: ✓/✗

MISMATCH FOUND: [describe]
FIX: [describe]
```

---

## Common Bug Patterns Specific to PRISM Mobile

| Bug | Symptom | Cause | Fix |
|---|---|---|---|
| API 401 Unauthorized | All requests fail after login | Bearer token not attached | Add Authorization header to all requests |
| API 404 | Specific module doesn't load | Mobile calling old Firestore URL instead of Azure | Update BASE_URL, check all api calls |
| Empty AI response | Brain icon tapped, nothing appears | Timeout too low, or AI route not CORS-whitelisted for mobile | Increase timeout, add mobile origin to CORS |
| Crash on PDF | Report generation crashes | expo-print or expo-sharing not declared in plugins | Add to app.json plugins |
| Login loop | Login succeeds then redirects to login | AsyncStorage persistence not set for Firebase Auth | Use getReactNativePersistence |
| Build succeeds, blank screen | White screen on launch | Entry point mismatch or metro bundler error | Check `main` in package.json, check metro.config.js |
| Forms don't save | Save button taps but no navigation | patient_id undefined (from Cosmos vs Firestore ID format) | Log patient_id at each step |

---

## Files to Always Inspect First

In the mobile project:
```
app.json              ← plugins, permissions, scheme, version
eas.json              ← build profiles, env vars per profile
app.config.js         ← dynamic config (if used instead of app.json)
src/config.js         ← BASE_URL, Firebase config
src/services/api.js   ← axios/fetch client, auth headers
src/services/auth.js  ← Firebase init, token management
package.json          ← SDK version, native module versions
```

In the web app:
```
app.py                ← Flask routes, CORS config, auth decorators
config.py             ← Azure keys, allowed origins
requirements.txt      ← Python dependencies
```

---

## Reference Files

- `references/expo-go-vs-production.md` — Exhaustive list of all known Expo Go vs production differences
- `references/flask-mobile-auth.md` — How to make Flask accept both session cookies (web) and Bearer tokens (mobile) on the same routes

Read these when the Phase diagnosis above doesn't resolve the issue.
