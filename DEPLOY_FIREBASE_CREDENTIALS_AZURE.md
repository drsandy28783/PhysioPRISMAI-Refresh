# Deploy Firebase Credentials to Azure Container Apps

**URGENT:** Follow these steps to fix the 401 login error

---

## Quick Start (5 minutes)

### Step 1: Get Firebase Service Account Key

1. **Go to Firebase Console:**
   ```
   https://console.firebase.google.com/project/physiologicprism-474610/settings/serviceaccounts/adminsdk
   ```

2. **Generate New Private Key:**
   - Click "Generate New Private Key" button
   - Download the JSON file
   - Save as: `firebase-service-account.json`

3. **Verify the file contains:**
   ```json
   {
     "type": "service_account",
     "project_id": "physiologicprism-474610",
     "private_key_id": "...",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...",
     "client_email": "firebase-adminsdk-xxxxx@physiologicprism-474610.iam.gserviceaccount.com",
     ...
   }
   ```

---

### Step 2: Deploy to Azure (Choose ONE method)

#### **Method A: Azure Portal (Recommended - Easy)**

1. **Open Azure Portal:**
   ```
   https://portal.azure.com
   ```

2. **Navigate to Container App:**
   - Search for "Container Apps"
   - Select: `physiologicprism-app`

3. **Add Secret (HIPAA-compliant way):**
   - Left sidebar → "Secrets"
   - Click "Add" button
   - **Name:** `firebase-creds`
   - **Value:** (paste entire contents of `firebase-service-account.json`)
   - Click "Add"

4. **Add Environment Variable:**
   - Left sidebar → "Containers"
   - Click "Edit and deploy"
   - Go to "Environment variables" tab
   - Click "Add" button
   - **Name:** `GOOGLE_APPLICATION_CREDENTIALS_JSON`
   - **Source:** Secret reference
   - **Value:** `firebase-creds`
   - Click "Create" (bottom of page)

5. **Wait for deployment:**
   - Status will show "Provisioning succeeded"
   - Usually takes 2-3 minutes

---

#### **Method B: Azure CLI (Advanced - Faster)**

```bash
# 1. Login to Azure
az login

# 2. Set subscription
az account set --subscription "33b7366e-4815-4987-9d92-a1fed4227c97"

# 3. Store Firebase credentials as secret
az containerapp secret set \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --secrets firebase-creds="$(cat firebase-service-account.json | tr -d '\n')"

# 4. Add environment variable pointing to secret
az containerapp update \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --set-env-vars "GOOGLE_APPLICATION_CREDENTIALS_JSON=secretref:firebase-creds"

# 5. Verify deployment
az containerapp revision list \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --output table
```

---

### Step 3: Verify the Fix

1. **Check Application Logs:**
   ```bash
   az containerapp logs show \
     --name physiologicprism-app \
     --resource-group rg-physiologicprism-prod \
     --follow
   ```

   **Look for this line:**
   ```
   Firebase Admin SDK initialized with explicit credentials for project physiologicprism-474610
   ```

   **NOT this line:**
   ```
   No explicit Firebase credentials found. Using Application Default Credentials (may fail on Azure).
   ```

2. **Test Login:**
   - Open: `https://physiologicprism-app.whitebeach-b88404fa.eastus.azurecontainerapps.io/login/firebase`
   - Enter: `drsandeep@physiologicprism.com`
   - Enter password
   - **Expected:** Login succeeds → redirects to dashboard
   - **NOT:** 401 error in console

3. **Check Browser Console:**
   - Press F12 → Console tab
   - **Should see:**
     ```
     Firebase Auth sign-in successful: drsandeep@physiologicprism.com
     Session verified, redirecting to: /dashboard
     ```
   - **Should NOT see:**
     ```
     Failed to load resource: the server responded with a status of 401
     ```

---

## Troubleshooting

### ❌ Still getting 401 error?

**Check 1: Verify credentials are loaded**
```bash
# Get current environment variables
az containerapp show \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --query "properties.template.containers[0].env" \
  --output table
```

Look for: `GOOGLE_APPLICATION_CREDENTIALS_JSON`

---

**Check 2: Verify secret exists**
```bash
# List secrets
az containerapp secret list \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --output table
```

Look for: `firebase-creds`

---

**Check 3: Check application logs for errors**
```bash
az containerapp logs show \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --follow
```

Look for error messages containing: `Firebase`, `credentials`, or `401`

---

### ❌ "Invalid Firebase credentials JSON" error?

**Problem:** JSON is malformed or contains newlines

**Fix (Azure CLI):**
```bash
# Use tr to remove all newlines before uploading
az containerapp secret set \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --secrets firebase-creds="$(cat firebase-service-account.json | jq -c .)"
```

**Fix (Azure Portal):**
1. Open `firebase-service-account.json` in text editor
2. Copy entire contents
3. Go to: https://www.minifyjson.com/
4. Paste JSON → Click "Minify"
5. Copy minified output
6. Paste into Azure Portal secret value

---

### ❌ "No module named 'firebase_admin.credentials'" error?

**Problem:** Code change not deployed

**Fix:**
```bash
# Rebuild and redeploy container
# (Your existing deployment process)

# OR force revision reload
az containerapp revision restart \
  --resource-group rg-physiologicprism-prod \
  --app physiologicprism-app \
  --revision <revision-name>
```

---

## Security Best Practices

### ✅ DO:
- Store credentials as Azure Container App **Secrets** (not plain environment variables)
- Use secret references in environment variables: `secretref:firebase-creds`
- Rotate Firebase service account keys annually
- Delete old keys from Firebase Console after rotation

### ❌ DON'T:
- Don't commit `firebase-service-account.json` to Git
- Don't share the service account JSON file
- Don't store credentials in plain environment variables
- Don't use the same credentials for dev/staging/production

---

## Production Deployment Checklist

### Before Deploying:

- [ ] Downloaded Firebase service account JSON from Firebase Console
- [ ] Verified JSON file contains `private_key` field
- [ ] Added secret to Azure Container App: `firebase-creds`
- [ ] Added environment variable: `GOOGLE_APPLICATION_CREDENTIALS_JSON=secretref:firebase-creds`
- [ ] Deployed updated `app_auth.py` code (with credentials support)
- [ ] Verified logs show: "Firebase Admin SDK initialized with explicit credentials"

### After Deploying:

- [ ] Tested login with valid user account
- [ ] Verified no 401 errors in browser console
- [ ] Checked Azure logs for Firebase errors
- [ ] Tested logout and re-login
- [ ] Tested on different browser/device
- [ ] Verified homepage loads without login prompt

---

## Rollback Plan

If deployment fails:

```bash
# 1. Get previous working revision
az containerapp revision list \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --output table

# 2. Activate previous revision
az containerapp revision activate \
  --resource-group rg-physiologicprism-prod \
  --app physiologicprism-app \
  --revision <previous-revision-name>

# 3. Deactivate current revision
az containerapp revision deactivate \
  --resource-group rg-physiologicprism-prod \
  --app physiologicprism-app \
  --revision <current-revision-name>
```

---

## Alternative: Test Locally First

Before deploying to Azure, test locally:

```bash
# 1. Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS_JSON=$(cat firebase-service-account.json | tr -d '\n')

# 2. Run the app
python main.py

# 3. Check logs
# Should see: "Firebase Admin SDK initialized with explicit credentials"

# 4. Test login at http://localhost:5000/login
```

---

## Contact Support

If issues persist after following this guide:

1. **Azure Support:** https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade
2. **Firebase Support:** https://firebase.google.com/support

Include:
- Azure Container App logs
- Browser console errors (screenshot)
- Steps you've already tried

---

**Document Version:** 1.0
**Last Updated:** January 14, 2026
