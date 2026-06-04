# Dependency Management Guide

## Overview

This project uses a two-file system for Python dependencies:

- **`requirements.txt`** - Human-readable, direct dependencies only (development)
- **`requirements.lock`** - Complete locked dependencies with exact versions (production)

## Why Lock Dependencies?

### Security Benefits
- **Supply Chain Protection**: Prevents malicious package updates from being auto-installed
- **Integrity Verification**: Ensures you get the exact tested packages
- **Audit Trail**: Know exactly what's running in production

### Uptime Benefits
- **Reproducible Builds**: Same versions across dev, staging, and production
- **No Surprise Breakages**: Updates only when you choose
- **Rollback Safety**: Can confidently roll back to any previous state

## Current Status

- ✅ 282 dependencies locked in `requirements.lock`
- ✅ Dockerfile uses locked dependencies
- ✅ 52 → 3 vulnerabilities (94% reduction)

---

## How to Update Dependencies

### 1. Security Updates (Patch Vulnerabilities)

**When:** You discover vulnerabilities via `pip-audit` or security alerts

**Steps:**

```bash
# 1. Run security audit
python -m pip_audit -r requirements.txt

# 2. Update vulnerable packages in requirements.txt
# Edit requirements.txt and bump versions to fix CVEs

# 3. Regenerate the lock file
pip install -r requirements.txt
pip freeze > requirements.lock

# 4. Test locally
python main.py  # Or your test command

# 5. Commit and push
git add requirements.txt requirements.lock Dockerfile
git commit -m "Security: Update [package] to fix CVE-XXXX"
git push
```

**Example from recent update:**
```bash
# We updated Flask from 3.1.0 → 3.1.3 to fix 2 CVEs
# Then regenerated requirements.lock with all 282 dependencies locked
```

---

### 2. Feature Updates (Add New Packages)

**When:** You need to add a new library for a feature

**Steps:**

```bash
# 1. Add package to requirements.txt
echo "new-package==1.2.3" >> requirements.txt

# 2. Install and regenerate lock
pip install -r requirements.txt
pip freeze > requirements.lock

# 3. Test the new feature
# ... run your tests ...

# 4. Commit and push
git add requirements.txt requirements.lock
git commit -m "feat: Add new-package for [feature]"
git push
```

---

### 3. Major Updates (Upgrade Dependencies)

**When:** Quarterly maintenance or when packages are very outdated

**⚠️ Caution:** Major updates can break functionality. Test thoroughly.

**Steps:**

```bash
# 1. Check for outdated packages
pip list --outdated

# 2. Update packages incrementally in requirements.txt
# Don't update everything at once - do it in small batches

# 3. For each batch:
pip install -r requirements.txt
pip freeze > requirements.lock
# Run full test suite
python -m pytest tests/

# 4. If tests pass, commit
git add requirements.txt requirements.lock
git commit -m "deps: Update [packages] to latest versions"
git push

# 5. Monitor production after deployment
az containerapp logs show --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod --follow
```

---

### 4. Emergency Rollback

**When:** Production breaks after a dependency update

**Steps:**

```bash
# 1. Find the last working commit
git log --oneline requirements.lock

# 2. Revert the lock file
git checkout <last-good-commit> requirements.lock

# 3. Push immediately
git add requirements.lock
git commit -m "rollback: Revert to last working dependencies"
git push

# 4. Monitor deployment
# GitHub Actions will auto-deploy the rolled-back version
```

---

## Automated Checks

### Before Every Deployment

The GitHub Actions workflow automatically:
1. Builds Docker image with `requirements.lock`
2. Runs tests (if configured)
3. Deploys to Azure Container Apps

### Regular Security Audits

**Run quarterly:**
```bash
python -m pip_audit -r requirements.txt
```

**Or set up GitHub Dependabot:**
- Go to: Settings → Security → Dependabot
- Enable: "Dependabot security updates"
- It will auto-create PRs for vulnerabilities

---

## Troubleshooting

### "Dependency conflict" errors

```bash
# Try resolving conflicts by using version ranges
# In requirements.txt, change:
cryptography==46.0.6  # Too strict

# To:
cryptography>=44.0.2,<47  # Allows resolver flexibility

# Then regenerate:
pip install -r requirements.txt
pip freeze > requirements.lock
```

### "Package not found" errors

```bash
# Check if package version exists:
pip index versions package-name

# If not, use an available version:
pip index versions flask-limiter
# Shows: 4.1.1, 4.1.0, 4.0.0, ...
```

### Lock file is huge (> 500 packages)

This is normal! The lock file includes ALL transitive dependencies.

Your `requirements.txt` has ~73 packages, but they depend on 200+ others.

---

## Best Practices

1. **Always test after updates** - Even patch updates can break things
2. **Update incrementally** - Don't update 50 packages at once
3. **Read changelogs** - Check breaking changes before major updates
4. **Monitor production** - Watch logs after every deployment
5. **Keep requirements.txt clean** - Only direct dependencies, no transitive ones
6. **Lock everything** - Always regenerate requirements.lock after changes

---

## Quick Reference

```bash
# Security audit
python -m pip_audit -r requirements.txt

# Update a package
# 1. Edit requirements.txt (bump version)
# 2. pip install -r requirements.txt
# 3. pip freeze > requirements.lock
# 4. git add requirements.txt requirements.lock
# 5. git commit -m "security: Update package to fix CVE"
# 6. git push

# Rollback
git checkout <commit-hash> requirements.lock
git add requirements.lock
git commit -m "rollback: Revert dependencies"
git push

# Check deployment status
# https://github.com/drsandy28783/PhysioPRISMAI-Refresh/actions

# View Azure logs
az containerapp logs show --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod --follow
```

---

## Files Overview

| File | Purpose | Edit Manually? |
|------|---------|----------------|
| `requirements.txt` | Human-readable deps | ✅ Yes |
| `requirements.lock` | All locked deps (282) | ❌ No (use `pip freeze`) |
| `Dockerfile` | Uses `requirements.lock` | ⚠️ Rarely |
| `.github/workflows/azure-container-app.yml` | CI/CD pipeline | ⚠️ Rarely |

---

## Recent Updates

**2026-06-04** - Security update (52→3 vulnerabilities)
- Updated 11 packages to fix 49 CVEs
- Flask 3.1.0 → 3.1.3
- pillow 11.2.1 → 12.2.0
- pypdf 5.4.0 → 6.10.2
- urllib3 2.4.0 → 2.7.0
- And 7 more...

