# Domain Migration: physiologicprism.com from GCP to Azure
**Date:** January 18, 2026
**Domain:** physiologicprism.com
**Source:** Google Cloud Platform (Firebase Hosting / Cloud Run)
**Target:** Azure Container Apps

---

## 🎯 MIGRATION OVERVIEW

### Current Setup (GCP):
- **Domain:** physiologicprism.com
- **Hosting:** Firebase Hosting OR Google Cloud Run
- **DNS:** Google Domains / Cloudflare / Other
- **SSL:** Auto-managed by Firebase/GCP

### Target Setup (Azure):
- **Domain:** physiologicprism.com
- **Hosting:** Azure Container Apps
- **Current Azure URL:** physiologicprism-app.whitebeach-b88404fa.eastus.azurecontainerapps.io
- **DNS:** Update to point to Azure
- **SSL:** Free managed certificate from Azure

---

## 📋 PRE-MIGRATION CHECKLIST

Before you start, verify:

- [ ] You have access to your domain registrar (where you bought physiologicprism.com)
- [ ] Current DNS provider is identified (Google Domains / GoDaddy / Cloudflare / etc.)
- [ ] Application is running successfully on Azure Container Apps
- [ ] You have Azure CLI access with admin permissions
- [ ] Backup of current DNS records (export from current DNS provider)

---

## 🔍 STEP 1: IDENTIFY CURRENT SETUP

### Check where your domain is registered:

Common registrars:
- **Google Domains** (if bought through Google)
- **GoDaddy**
- **Namecheap**
- **Cloudflare**
- **Others**

### Check current DNS records:

Go to your domain registrar and note down:
- **A records** (points to IP addresses)
- **CNAME records** (points to other domains)
- **TXT records** (verification, SPF, DKIM)
- **MX records** (email, if any)

**Current GCP Setup Likely:**
```
Type: CNAME
Name: physiologicprism.com (or @)
Value: [project-name].web.app OR [service-name].run.app
```

---

## 🚀 STEP 2: ADD CUSTOM DOMAIN TO AZURE CONTAINER APPS

### Option A: Using Azure Portal (Easiest)

1. **Open Azure Portal:**
   - Go to https://portal.azure.com
   - Navigate to: Resource Groups → rg-physiologicprism-prod → physiologicprism-app

2. **Add Custom Domain:**
   - Click "Custom domains" in left menu
   - Click "+ Add custom domain"
   - Enter: `physiologicprism.com`
   - Click "Validate"

3. **Get DNS Verification Records:**
   Azure will show you the DNS records you need to add:

   **For Root Domain (physiologicprism.com):**
   ```
   Type: TXT
   Name: asuid.physiologicprism.com
   Value: [Azure-provided-verification-token]
   ```

   **And:**
   ```
   Type: A
   Name: @ (or leave blank for root)
   Value: [Azure-provided-IP-address]
   ```

   **For www subdomain (www.physiologicprism.com):**
   ```
   Type: CNAME
   Name: www
   Value: physiologicprism-app.whitebeach-b88404fa.eastus.azurecontainerapps.io
   ```

4. **Keep this tab open** - you'll need these values

---

### Option B: Using Azure CLI (Advanced)

```bash
# 1. Add custom domain to Container App
az containerapp hostname add \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --hostname physiologicprism.com

# 2. Get verification details
az containerapp hostname list \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --output table

# This will show the verification token and IP address you need
```

**Expected Output:**
```
Hostname                    BindingType    CertificateId
--------------------------  -------------  ---------------
physiologicprism.com        SniEnabled     (pending)
```

**Get the IP address:**
```bash
az containerapp show \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv
```

**Note:** Azure Container Apps uses a shared IP that's provided during domain verification.

---

## 🌐 STEP 3: UPDATE DNS RECORDS

### Go to Your Domain Registrar/DNS Provider

**Examples for common providers:**

### A. Google Domains (https://domains.google.com)

1. Log in to Google Domains
2. Click on physiologicprism.com
3. Go to "DNS" tab
4. Scroll to "Custom resource records"

**Add these records:**

**Step 1: Add TXT record for verification**
```
Name: asuid
Type: TXT
TTL: 3600 (1 hour)
Data: [Paste Azure-provided verification token from Portal]
```

**Step 2: Update/Add A record for root domain**
```
Name: @ (or leave blank)
Type: A
TTL: 3600
Data: [Azure-provided IP address]
```

**Step 3: Add CNAME for www**
```
Name: www
Type: CNAME
TTL: 3600
Data: physiologicprism-app.whitebeach-b88404fa.eastus.azurecontainerapps.io
```

**Step 4: REMOVE old GCP records**
- Delete any existing CNAME pointing to *.web.app or *.run.app
- Delete old A records if different from Azure IP

---

### B. Cloudflare (https://dash.cloudflare.com)

1. Log in to Cloudflare
2. Select physiologicprism.com
3. Go to "DNS" section

**Add these records:**

**Verification TXT record:**
```
Type: TXT
Name: asuid
Content: [Azure verification token]
TTL: Auto
Proxy status: DNS only (grey cloud)
```

**A record for root:**
```
Type: A
Name: @ (or physiologicprism.com)
Content: [Azure IP address]
TTL: Auto
Proxy status: DNS only (grey cloud) - IMPORTANT!
```

**CNAME for www:**
```
Type: CNAME
Name: www
Target: physiologicprism-app.whitebeach-b88404fa.eastus.azurecontainerapps.io
TTL: Auto
Proxy status: DNS only (grey cloud) - IMPORTANT!
```

**⚠️ IMPORTANT for Cloudflare:**
- Set Proxy Status to "DNS only" (grey cloud icon)
- Orange cloud will break Azure SSL certificate verification
- You can enable proxy AFTER SSL certificate is issued

---

### C. GoDaddy (https://dcc.godaddy.com)

1. Log in to GoDaddy
2. Go to "My Products" → "Domains"
3. Click "DNS" next to physiologicprism.com

**Add/Update records:**

**TXT record:**
```
Type: TXT
Name: asuid
Value: [Azure verification token]
TTL: 1 Hour
```

**A record:**
```
Type: A
Name: @
Value: [Azure IP address]
TTL: 1 Hour
```

**CNAME record:**
```
Type: CNAME
Name: www
Value: physiologicprism-app.whitebeach-b88404fa.eastus.azurecontainerapps.io
TTL: 1 Hour
```

---

### D. Namecheap (https://www.namecheap.com)

1. Log in to Namecheap
2. Domain List → Manage → Advanced DNS

**Add records:**

**TXT Record:**
```
Type: TXT Record
Host: asuid
Value: [Azure verification token]
TTL: Automatic
```

**A Record:**
```
Type: A Record
Host: @
Value: [Azure IP address]
TTL: Automatic
```

**CNAME Record:**
```
Type: CNAME Record
Host: www
Value: physiologicprism-app.whitebeach-b88404fa.eastus.azurecontainerapps.io
TTL: Automatic
```

---

## ⏱️ STEP 4: WAIT FOR DNS PROPAGATION

DNS changes take time to propagate globally:
- **Minimum:** 15 minutes - 1 hour
- **Typical:** 2-4 hours
- **Maximum:** 24-48 hours (rare)

**Check DNS propagation:**
- Online tool: https://dnschecker.org
- Enter: physiologicprism.com
- Check A record shows Azure IP
- Check from multiple locations (USA, Europe, Asia)

**Command-line check:**
```bash
# Check A record
nslookup physiologicprism.com

# Expected: Azure IP address

# Check CNAME for www
nslookup www.physiologicprism.com

# Expected: physiologicprism-app.whitebeach-b88404fa.eastus.azurecontainerapps.io
```

---

## 🔐 STEP 5: VERIFY DOMAIN IN AZURE

### Via Azure Portal:

1. Go back to Azure Portal → Container App → Custom domains
2. Next to physiologicprism.com, click "Validate"
3. If DNS is propagated, it will show "Validation successful"
4. Click "Add" to finalize

**Azure will automatically:**
- Issue free SSL/TLS certificate (Let's Encrypt)
- Configure HTTPS redirection
- Enable certificate auto-renewal

**Time for SSL certificate:** 5-15 minutes after validation

---

### Via Azure CLI:

```bash
# Verify domain ownership
az containerapp hostname bind \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --hostname physiologicprism.com \
  --environment [environment-name] \
  --validation-method CNAME

# Check status
az containerapp hostname list \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod
```

---

## ✅ STEP 6: TEST THE MIGRATION

### Test URLs:

1. **Root domain:** https://physiologicprism.com
   - Should load your Azure app
   - Should show green padlock (SSL)
   - Certificate issued by Let's Encrypt

2. **www subdomain:** https://www.physiologicprism.com
   - Should load your Azure app
   - Should show SSL certificate

3. **HTTP redirect:** http://physiologicprism.com
   - Should redirect to https://physiologicprism.com

### Test from different locations:
- https://www.uptrends.com/tools/uptime-test
- Test from USA, Europe, Asia to ensure global DNS propagation

### Browser checks:
- Chrome: Click padlock → Certificate → Should show "Let's Encrypt"
- Firefox: Click padlock → Connection secure → More information
- Edge: Click padlock → Connection is secure

---

## 🧹 STEP 7: CLEANUP GCP RESOURCES

**ONLY after confirming Azure domain works perfectly!**

### Firebase Hosting (if used):

```bash
# Remove domain from Firebase Hosting
firebase hosting:channel:delete physiologicprism.com

# Or via Firebase Console:
# 1. Go to https://console.firebase.google.com
# 2. Select project
# 3. Hosting → Domain → Remove physiologicprism.com
```

### Google Cloud Run (if used):

```bash
# Remove domain mapping
gcloud run domain-mappings delete \
  --domain physiologicprism.com \
  --region us-central1

# Or via Cloud Console:
# Cloud Run → Service → Custom domains → Delete mapping
```

### Verify GCP cleanup:

```bash
# List Firebase hosting sites
firebase hosting:sites:list

# List Cloud Run domain mappings
gcloud run domain-mappings list
```

---

## 🔧 OPTIONAL: CONFIGURE WWW REDIRECT

If you want www.physiologicprism.com to redirect to physiologicprism.com (or vice versa):

### Option 1: DNS-level (Simplest)

Just keep both domains pointing to same Azure app. Azure will serve content on both.

### Option 2: Application-level Redirect

Add redirect logic in your Flask app:

```python
# In main.py, add this near the top after app creation

@app.before_request
def redirect_to_non_www():
    """Redirect www to non-www domain"""
    if request.host.startswith('www.'):
        url = request.url.replace('www.', '', 1)
        return redirect(url, code=301)
```

Or redirect non-www to www:

```python
@app.before_request
def redirect_to_www():
    """Redirect non-www to www domain"""
    if not request.host.startswith('www.') and 'localhost' not in request.host:
        url = request.url.replace('://', '://www.', 1)
        return redirect(url, code=301)
```

---

## 📧 STEP 8: UPDATE EMAIL DNS (If Applicable)

If you use email with your domain (e.g., support@physiologicprism.com):

### Preserve existing MX records:

**Important:** When updating DNS, DON'T delete MX records if you have email configured!

**Typical email providers:**
- **Google Workspace (G Suite):** MX records point to google.com
- **Microsoft 365:** MX records point to outlook.com
- **Zoho Mail:** MX records point to zoho.com

**Example MX records to preserve:**
```
Type: MX
Name: @ (or blank)
Priority: 1
Value: aspmx.l.google.com (Google Workspace)
TTL: 3600
```

### Add SPF record if needed:
```
Type: TXT
Name: @ (or blank)
Value: v=spf1 include:_spf.google.com ~all
```

---

## 🚨 TROUBLESHOOTING

### Issue 1: "Domain validation failed"

**Cause:** DNS not propagated yet or incorrect records

**Solution:**
```bash
# Check DNS from your location
nslookup physiologicprism.com

# Check globally
# Visit https://dnschecker.org

# Wait 1-2 hours and retry validation
```

---

### Issue 2: "SSL certificate provisioning failed"

**Cause:**
- Domain not fully validated
- CAA records blocking Let's Encrypt
- Cloudflare proxy enabled (orange cloud)

**Solution:**
```bash
# Check CAA records
dig physiologicprism.com CAA

# If CAA exists, ensure it allows Let's Encrypt:
# Type: CAA
# Name: @
# Value: 0 issue "letsencrypt.org"
```

**For Cloudflare users:** Disable proxy (set to DNS only) until certificate issues

---

### Issue 3: "Certificate issued but site shows insecure"

**Cause:** Browser cache or mixed content (HTTP resources on HTTPS page)

**Solution:**
```bash
# Clear browser cache
# Test in incognito/private mode
# Check browser console for mixed content warnings
```

---

### Issue 4: "Old GCP site still showing"

**Cause:** DNS caching or old DNS records still active

**Solution:**
```bash
# Flush local DNS cache (Windows)
ipconfig /flushdns

# Flush local DNS cache (Mac)
sudo dscacheutil -flushcache

# Flush local DNS cache (Linux)
sudo systemd-resolve --flush-caches

# Wait for DNS TTL to expire (1-24 hours)
```

---

### Issue 5: "Domain works but www doesn't (or vice versa)"

**Cause:** Missing CNAME record for www

**Solution:**
Add CNAME record:
```
Type: CNAME
Name: www
Value: physiologicprism-app.whitebeach-b88404fa.eastus.azurecontainerapps.io
```

Then add www.physiologicprism.com as second custom domain in Azure

---

## 📊 VERIFICATION CHECKLIST

After migration, verify:

- [ ] https://physiologicprism.com loads correctly
- [ ] https://www.physiologicprism.com loads correctly
- [ ] http://physiologicprism.com redirects to https://
- [ ] http://www.physiologicprism.com redirects to https://
- [ ] SSL certificate is valid (green padlock)
- [ ] Certificate auto-renews (Azure handles this)
- [ ] DNS resolves globally (check https://dnschecker.org)
- [ ] Old GCP hosting is removed (no duplicate content)
- [ ] Email still works (if using custom domain email)
- [ ] Firebase/GCP billing stopped (remove domain from GCP)

---

## 🎯 STEP-BY-STEP SUMMARY

**Timeline: 2-4 hours total (mostly waiting for DNS)**

1. **Prep (5 min):** Get Azure verification details from Portal
2. **DNS Update (10 min):** Add TXT, A, CNAME records to your registrar
3. **Wait (1-4 hours):** DNS propagation
4. **Verify (5 min):** Validate domain in Azure Portal
5. **SSL Wait (5-15 min):** Azure provisions certificate
6. **Test (10 min):** Verify https:// works globally
7. **Cleanup (10 min):** Remove domain from GCP/Firebase
8. **Done!** ✅

---

## 💰 COST IMPLICATIONS

**Azure Custom Domain:**
- **Domain binding:** FREE
- **SSL certificate:** FREE (auto-renewed)
- **Traffic:** Same as before (no change)

**GCP Cleanup:**
- **Firebase Hosting:** FREE tier, but good to clean up
- **Cloud Run:** Stop any unused services to avoid charges

**Total Cost Change:** $0 (custom domains are free on Azure Container Apps)

---

## 🔐 SECURITY CONSIDERATIONS

**After migration:**

1. **Enable HTTPS-only:**
   - Azure automatically redirects HTTP → HTTPS
   - Verify with: http://physiologicprism.com

2. **Set security headers:**
   Update your Flask app to add security headers:
   ```python
   @app.after_request
   def set_security_headers(response):
       response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
       response.headers['X-Content-Type-Options'] = 'nosniff'
       response.headers['X-Frame-Options'] = 'DENY'
       response.headers['X-XSS-Protection'] = '1; mode=block'
       return response
   ```

3. **Monitor certificate renewal:**
   - Azure auto-renews 30 days before expiry
   - Check Azure Portal → Container Apps → Custom domains
   - Certificate valid for 90 days (Let's Encrypt)

---

## 📞 SUPPORT RESOURCES

**Azure Support:**
- Docs: https://learn.microsoft.com/azure/container-apps/custom-domains
- Support: Azure Portal → Help + support

**DNS Support:**
- Google Domains: https://support.google.com/domains
- Cloudflare: https://support.cloudflare.com
- GoDaddy: https://www.godaddy.com/help

**SSL Certificate Issues:**
- Let's Encrypt status: https://letsencrypt.status.io
- SSL checker: https://www.ssllabs.com/ssltest/

---

## 🚀 NEXT STEPS AFTER MIGRATION

1. **Update Paddle business profile:**
   - Website: https://physiologicprism.com
   - Looks more professional than Azure default domain

2. **Update marketing materials:**
   - Email signatures
   - Business cards
   - LinkedIn company page
   - Social media profiles

3. **Set up email (if needed):**
   - Google Workspace: support@physiologicprism.com
   - Or use Resend with custom domain for transactional emails

4. **Configure analytics:**
   - Google Analytics: Add physiologicprism.com
   - Update tracking codes if needed

5. **SEO considerations:**
   - Submit new domain to Google Search Console
   - Update sitemap if you have one
   - Set up 301 redirects from old URLs if any

---

**Document Created:** January 18, 2026
**Status:** Ready for migration
**Estimated Time:** 2-4 hours (including DNS propagation)
**Risk Level:** LOW (reversible if issues occur)
