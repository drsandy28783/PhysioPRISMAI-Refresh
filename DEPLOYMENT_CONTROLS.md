# Deployment Controls

## Current Status: AUTO-DEPLOYMENT DISABLED ⏸️

Auto-deployment from GitHub to Azure has been **temporarily disabled**. You can now:
- ✅ Push to GitHub for backup and version control
- ✅ Test changes locally
- ✅ Deploy manually when ready
- ❌ Changes will NOT auto-deploy to Azure

---

## How It Works Now

### Pushing to GitHub (for backup)
```bash
git add .
git commit -m "your message"
git push origin main
```
**Result**: Code is backed up to GitHub, but Azure won't deploy it automatically.

---

## How to Deploy to Azure (When Ready)

### Option 1: Manual Deployment via GitHub Actions (Recommended)

1. Go to your GitHub repository: https://github.com/drsandy28783/PhysioPRISMAI-Refresh
2. Click **Actions** tab
3. Click **Build and Deploy to Azure Container Apps** workflow
4. Click **Run workflow** button
5. Select branch: `main`
6. Click **Run workflow**

This will build and deploy your current code to Azure.

### Option 2: Deploy via Azure CLI (Local)

```bash
# Build Docker image locally
docker build -t physiologicprismacr.azurecr.io/physiologicprism-app:test .

# Login to Azure Container Registry
az acr login --name physiologicprismacr

# Push image
docker push physiologicprismacr.azurecr.io/physiologicprism-app:test

# Update Container App
az containerapp update \
  --name physiologicprism-app \
  --resource-group rg-physiologicprism-prod \
  --image physiologicprismacr.azurecr.io/physiologicprism-app:test
```

---

## How to Re-Enable Auto-Deployment

When you're ready to go back to automatic deployments:

1. Edit `.github/workflows/azure-container-app.yml`
2. Find lines 4-8:
```yaml
# Auto-deployment disabled - push to GitHub for backup only
# Uncomment the lines below to re-enable auto-deployment
# push:
#   branches:
#     - main
```
3. Uncomment them (remove the `#`):
```yaml
# Auto-deployment re-enabled
push:
  branches:
    - main
```
4. Commit and push:
```bash
git add .github/workflows/azure-container-app.yml
git commit -m "Re-enable auto-deployment"
git push origin main
```

**Result**: Every push to `main` will automatically deploy to Azure again.

---

## Testing Workflow

**Recommended workflow while testing:**

```bash
# 1. Make changes to your code
# Edit files...

# 2. Test locally
python main.py
# OR
docker build -t test-app .
docker run -p 8080:8080 test-app

# 3. When happy, backup to GitHub
git add .
git commit -m "Testing new feature"
git push origin main

# 4. ONLY when fully tested, deploy manually
# Use GitHub Actions UI (Option 1 above)
# OR use Azure CLI (Option 2 above)

# 5. If something breaks, revert easily
git revert HEAD
git push origin main
# Then deploy the reverted version manually
```

---

## Quick Reference

| Action | Auto-Deploys? |
|--------|---------------|
| `git push origin main` | ❌ No (currently disabled) |
| GitHub Actions → Run workflow | ✅ Yes (manual trigger) |
| `az containerapp update` | ✅ Yes (manual CLI) |

---

## Notes

- **Current deployment state**: Your production app is still running with the last deployed version
- **GitHub backup**: All your code is safely backed up on GitHub
- **No data loss**: Disabling auto-deployment doesn't affect your database or running app
- **Re-enable anytime**: Just uncomment 3 lines in the workflow file

---

Last updated: 2026-04-28
Status: Auto-deployment disabled for testing
