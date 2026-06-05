# Security Checklist

Comprehensive security audit checklist for PhysiologicPRISM.

---

## ✅ Completed Security Checks

### 1. Dependency Vulnerabilities ✓
**Status:** COMPLETED (2026-06-04)

**Tool:** `pip-audit`

**Results:**
- Fixed: 49 CVEs across 11 packages
- Remaining: 3 minor CVEs (cryptography - blocked by dependencies)
- Reduction: 52 → 3 vulnerabilities (94%)

**Next Check:** Quarterly or when new CVEs announced

```bash
python -m pip_audit -r requirements.txt
```

---

### 2. Code Security Scan ✓
**Status:** COMPLETED (2026-06-04)

**Tool:** `bandit`

**Results:**
- High: 0
- Medium: 4 issues
- Low: 148 issues (mostly false positives)

**Critical Findings:**
1. Possible SQL injection in `azure_cosmos_db.py:157` (MEDIUM)
   - Action: Review query construction
2. Subprocess usage in `azure_speech_client.py` (LOW)
   - Action: Validate input before subprocess calls

**Next Check:** Before each major release

```bash
python -m bandit -r . -f json -o bandit-report.json --exclude ./.git,./venv,./env
```

---

### 3. Secrets Exposure ✓
**Status:** VERIFIED (2026-06-04)

**Findings:**
- ✅ No hardcoded API keys or passwords
- ✅ `.env` properly gitignored
- ✅ Only `.env.example` in version control
- ✅ All secrets loaded from environment variables

**Configuration:**
- Secrets stored in Azure Container Apps environment variables
- Local development uses `.env` file (not committed)

---

## ⚠️ Needs Attention

### 4. Docker Security ⚠️
**Status:** PARTIAL

**Current Issues:**

1. **Running as root** ⚠️
   ```dockerfile
   # Current: No USER directive (runs as root)
   # Risk: Container breakout could compromise host
   ```

   **Fix:**
   ```dockerfile
   # Add before CMD:
   RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
   USER appuser
   ```

2. **Base image not minimal** ⚠️
   ```dockerfile
   FROM python:3.11-slim  # Could use distroless
   ```

   **Better:**
   ```dockerfile
   FROM gcr.io/distroless/python3-debian11  # No shell, smaller attack surface
   ```

3. **No image scanning** ⚠️
   - Docker images not scanned for vulnerabilities

   **Fix:** Add to GitHub Actions:
   ```yaml
   - name: Scan Docker image
     uses: aquasecurity/trivy-action@master
     with:
       image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
   ```

---

### 5. Web Application Security 🔴
**Status:** NOT CHECKED

**Critical Areas to Audit:**

#### A. OWASP Top 10

| Risk | Check | Status |
|------|-------|--------|
| SQL Injection | Parameterized queries | ⚠️ Review needed |
| XSS | Template escaping | ❓ Unknown |
| CSRF | Token validation | ❓ Unknown |
| Auth broken | Session management | ❓ Unknown |
| Security misconfig | Headers, CORS | ❓ Unknown |

**Tools to use:**
```bash
# OWASP ZAP (automated web scanner)
docker run -t zaproxy/zap-stable zap-baseline.py -t https://physiologicprism.com

# Or online:
# https://observatory.mozilla.org
# https://securityheaders.com
```

#### B. Security Headers

**Check your site:**
```bash
curl -I https://physiologicprism.com
```

**Required headers:**
- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`

**Flask-Talisman Status:** ✅ Installed (check if configured properly)

---

### 6. Authentication & Authorization 🔴
**Status:** NOT AUDITED

**Critical Checks:**

```bash
# Check auth implementation
grep -r "login\|authenticate\|authorize" main.py app_auth.py

# Check session security
grep -r "session\|cookie" main.py
```

**Questions:**
- [ ] Are passwords hashed with bcrypt/argon2?
- [ ] Is MFA/2FA available?
- [ ] Are sessions properly invalidated on logout?
- [ ] Is there rate limiting on login attempts?
- [ ] Are password reset tokens time-limited and single-use?

**Azure AD B2C Status:** ✅ Integrated (verify configuration)

---

### 7. Data Encryption 🔴
**Status:** NOT VERIFIED

**At Rest:**
- [ ] Azure Cosmos DB encryption enabled?
- [ ] Backup encryption enabled?
- [ ] Patient data encrypted before storage?

**In Transit:**
- [x] HTTPS enforced (check Azure Container Apps config)
- [ ] TLS 1.2+ only?
- [ ] Certificate valid and not self-signed?

**Check:**
```bash
# Test SSL/TLS
nmap --script ssl-enum-ciphers -p 443 physiologicprism.com

# Or use:
https://www.ssllabs.com/ssltest/analyze.html?d=physiologicprism.com
```

---

### 8. HIPAA Compliance 🔴
**Status:** REQUIRES AUDIT

**Critical Requirements:**

- [ ] **PHI Encryption:** At rest and in transit
- [ ] **Access Controls:** Role-based access implemented
- [ ] **Audit Logs:** All PHI access logged
- [ ] **BAA Agreements:** Azure services covered
- [ ] **Data Residency:** PHI stays in compliant regions
- [ ] **Breach Notification:** Process documented
- [ ] **Employee Training:** Security awareness

**Azure Services Status:**
- ✅ Azure Cosmos DB (HIPAA compliant)
- ✅ Azure OpenAI (HIPAA compliant)
- ✅ Azure Speech (HIPAA compliant)
- ⚠️ Check: BAA signed with Microsoft?

**Files to review:**
- `GDPR_COMPLIANCE.md` (exists)
- Need: `HIPAA_COMPLIANCE.md`

---

### 9. Logging & Monitoring 🟡
**Status:** PARTIAL

**Current Setup:**
- ✅ Sentry SDK installed (error tracking)
- ✅ Azure Container Apps logs available

**Missing:**
- [ ] Security event logging (failed logins, permission denied)
- [ ] Anomaly detection
- [ ] Alerting on security events
- [ ] Log retention policy

**Setup:**
```bash
# View logs
az containerapp logs show --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod --follow

# Set up alerts
az monitor metrics alert create \
  --name "High error rate" \
  --resource-group rg-physiologicprism-prod \
  --scopes /subscriptions/.../physiologicprism-app \
  --condition "avg exceptions > 10"
```

---

### 10. Rate Limiting & DDoS 🟡
**Status:** PARTIAL

**Current:**
- ✅ `flask-limiter` installed (version 3.8.0)
- ❓ Configuration status unknown

**Check:**
```python
# In main.py
from flask_limiter import Limiter

# Should see limits like:
@limiter.limit("5 per minute")
def login():
    ...
```

**Azure Protection:**
- [ ] Azure Front Door with WAF?
- [ ] DDoS Protection Standard enabled?

---

### 11. Infrastructure Security 🔴
**Status:** NOT AUDITED

**Azure Security Center:**
```bash
# Check security posture
az security secure-score show

# Check recommendations
az security assessment list
```

**Critical:**
- [ ] Managed Identity enabled (no hardcoded credentials)
- [ ] Network Security Groups configured
- [ ] Private endpoints for Cosmos DB
- [ ] Key Vault for secrets (not env vars)
- [ ] Azure Policy compliance
- [ ] Backup & disaster recovery tested

---

### 12. Third-Party Integrations 🟡
**Status:** NEEDS REVIEW

**Services Integrated:**
- Twilio (SMS/WhatsApp)
- Razorpay (payments)
- Resend (email)
- Firebase (auth - being phased out)

**Checks:**
- [ ] API keys rotated regularly
- [ ] Webhook signatures verified
- [ ] PCI DSS compliance for payments
- [ ] Data sharing agreements signed

---

## 🚀 Recommended Actions (Priority Order)

### Immediate (Do Now)

1. **Fix SQL Injection (MEDIUM)**
   - Review `azure_cosmos_db.py:157`
   - Use parameterized queries

2. **Run OWASP ZAP Scan**
   ```bash
   docker run -t zaproxy/zap-stable zap-baseline.py -t https://physiologicprism.com
   ```

3. **Check Security Headers**
   ```bash
   curl -I https://physiologicprism.com | grep -E "Strict-Transport|Content-Security|X-Frame"
   ```

4. **Verify HTTPS Enforcement**
   ```bash
   curl -I http://physiologicprism.com
   # Should redirect to HTTPS
   ```

---

### This Week

5. **Add Non-Root User to Dockerfile**
   - Create PR with Docker security improvements
   - Test in staging

6. **Enable Docker Image Scanning**
   - Add Trivy to GitHub Actions
   - Fix any HIGH/CRITICAL findings

7. **Audit Authentication**
   - Review password hashing
   - Check session management
   - Verify MFA status

8. **Setup Security Monitoring**
   - Configure Azure Monitor alerts
   - Set up failed login alerts

---

### This Month

9. **HIPAA Compliance Audit**
   - Review all PHI handling
   - Ensure BAA with Azure
   - Document security controls
   - Create `HIPAA_COMPLIANCE.md`

10. **Penetration Testing**
    - Hire security firm OR
    - Use HackerOne bug bounty

11. **Incident Response Plan**
    - Document breach procedures
    - Assign response team
    - Test response process

12. **Security Training**
    - HIPAA training for team
    - Secure coding practices
    - Phishing awareness

---

### Quarterly

13. **Regular Security Audits**
    ```bash
    # Dependencies
    python -m pip_audit -r requirements.txt

    # Code
    python -m bandit -r . -f json -o bandit-report.json

    # Web
    docker run -t zaproxy/zap-stable zap-baseline.py -t https://physiologicprism.com

    # SSL/TLS
    nmap --script ssl-enum-ciphers -p 443 physiologicprism.com
    ```

14. **Access Review**
    - Review Azure RBAC assignments
    - Remove unused accounts
    - Rotate API keys

15. **Disaster Recovery Test**
    - Test backup restoration
    - Verify RTO/RPO metrics
    - Update DR documentation

---

## 🛠️ Security Tools Reference

### Automated Scanning

| Tool | Purpose | Command |
|------|---------|---------|
| pip-audit | Python deps | `python -m pip_audit -r requirements.txt` |
| Bandit | Python code | `bandit -r . -f json -o report.json` |
| Trivy | Docker images | `trivy image myimage:latest` |
| OWASP ZAP | Web app | `zap-baseline.py -t https://example.com` |
| Safety | Python deps | `safety check -r requirements.txt` |
| Snyk | All deps | `snyk test` |

### Manual Checks

| Tool | Purpose | URL |
|------|---------|-----|
| SSL Labs | SSL/TLS config | https://ssllabs.com/ssltest/ |
| Security Headers | HTTP headers | https://securityheaders.com |
| Mozilla Observatory | Overall security | https://observatory.mozilla.org |

---

## 📋 Compliance Checklists

### HIPAA Technical Safeguards
- [ ] Access Control (§164.312(a)(1))
- [ ] Audit Controls (§164.312(b))
- [ ] Integrity Controls (§164.312(c)(1))
- [ ] Transmission Security (§164.312(e)(1))

### GDPR Requirements
- [ ] Right to access
- [ ] Right to erasure
- [ ] Data portability
- [ ] Consent management
- [ ] Breach notification (72 hours)

---

## 📞 Security Contact

**Report Security Issues:**
- Email: security@physiologicprism.com (setup needed?)
- GitHub: Private vulnerability reporting

**Responsible Disclosure:**
- 90-day disclosure timeline
- Security acknowledgments page

---

## 🔄 Update Schedule

| Check | Frequency | Last Run | Next Due |
|-------|-----------|----------|----------|
| Dependency Scan | Quarterly | 2026-06-04 | 2026-09-04 |
| Code Scan | Before release | 2026-06-04 | TBD |
| Web App Scan | Quarterly | Never | ASAP |
| Penetration Test | Annually | Never | 2026 |
| HIPAA Audit | Annually | Never | 2026 |

---

**Last Updated:** 2026-06-04
**Next Review:** 2026-09-04

