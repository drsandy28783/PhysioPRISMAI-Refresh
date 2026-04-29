# Development Workflow Guide
**PhysiologicPrism - Safe Development & Deployment Procedures**

---

## Quick Reference Commands

### When User Says: "Don't deploy to Azure" or "I want to test changes safely"

**Follow this workflow:**

```bash
# 1. Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/YOUR-FEATURE-NAME

# 2. Make changes to any files (main.py, templates, etc.)

# 3. Commit and push to feature branch (NO deployment triggered)
git add .
git commit -m "Description of changes"
git push origin feature/YOUR-FEATURE-NAME

# 4. Test changes locally if needed
python main.py  # or whatever testing is needed

# 5a. IF CHANGES WORK - Merge to main and deploy:
git checkout main
git merge feature/YOUR-FEATURE-NAME
git push origin main  # ✅ DEPLOYS TO AZURE

# 5b. IF CHANGES DON'T WORK - Abandon and revert:
git checkout main
git branch -D feature/YOUR-FEATURE-NAME
git push origin --delete feature/YOUR-FEATURE-NAME  # Optional: delete remote branch
# ✅ Back to original working state, no damage done
```

---

## Auto-Deployment Status

**Current Configuration:**
- Auto-deployment is **ENABLED** on pushes to `main` branch
- Workflow file: `.github/workflows/azure-container-app.yml`
- Triggers on: `push` to `main` branch
- Also allows: Manual trigger via `workflow_dispatch`

**To Check Status:**
- Look at `.github/workflows/azure-container-app.yml` line 3-7
- If `push:` section is uncommented → Auto-deploy is ON
- If `push:` section is commented out → Auto-deploy is OFF

---

## Deployment Control Options

### Option 1: Feature Branch Workflow (RECOMMENDED)
**Use when:** Testing changes without risk to production

**Pros:**
- ✅ Zero risk to main branch
- ✅ Can push to GitHub for backup
- ✅ Easy rollback (just delete branch)
- ✅ Clean git history
- ✅ Industry standard practice

**Cons:**
- Requires branch switching

**Commands:** See Quick Reference above

---

### Option 2: Disable Auto-Deployment in GitHub UI
**Use when:** Need to push to main without deploying

**Steps:**
1. Go to: https://github.com/drsandy28783/PhysioPRISMAI-Refresh/actions
2. Click "Build and Deploy to Azure Container Apps" (left sidebar)
3. Click `...` menu (top right)
4. Click **"Disable workflow"**
5. Push changes to main (no deployment)
6. When ready to deploy: Re-enable workflow (same menu)

**Pros:**
- ✅ Instant (no code changes)
- ✅ Can push to main safely
- ✅ Easy to re-enable

**Cons:**
- Have to remember to re-enable
- Still risky if changes break main branch

---

### Option 3: Commit Message Skip Pattern
**Use when:** Occasionally skipping deployment

**Setup Required:**
Add this to `.github/workflows/azure-container-app.yml` under `jobs:`:

```yaml
jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    if: "!contains(github.event.head_commit.message, '[skip-deploy]')"
```

**Then use:**
```bash
git commit -m "[skip-deploy] Testing changes to main.py"
git push  # Won't deploy
```

**Pros:**
- ✅ Granular control per commit
- ✅ Clear in git history

**Cons:**
- Requires workflow modification
- Easy to forget to add tag

---

## Emergency Rollback Procedures

### If Bad Changes Were Deployed to Azure

**Option A: Revert via Git**
```bash
# Find the last good commit
git log --oneline -10

# Revert to last good commit (example)
git revert HEAD
git push origin main  # Triggers re-deployment with reverted code

# OR hard reset (use with caution)
git reset --hard <last-good-commit-hash>
git push --force origin main  # Force push and re-deploy
```

**Option B: Manual Azure Rollback**
1. Go to Azure Portal → Container Apps → physiologicprism-app
2. Go to "Revisions"
3. Select previous working revision
4. Click "Activate"

---

## Safety Best Practices

### Before Making Risky Changes:

1. **Create a safety tag:**
   ```bash
   git tag safety-$(date +%Y%m%d-%H%M)
   git push origin --tags
   ```

2. **Or create a backup branch:**
   ```bash
   git branch backup-before-changes
   git push origin backup-before-changes
   ```

3. **Use feature branch workflow** (see Option 1 above)

### After Changes Work:

1. Delete feature branches you don't need:
   ```bash
   git branch -d feature/old-feature
   git push origin --delete feature/old-feature
   ```

2. Clean up old tags if needed:
   ```bash
   git tag -d safety-old-tag
   git push origin --delete safety-old-tag
   ```

---

## Common Scenarios

### "I want to experiment with main.py without deploying"
→ Use **Feature Branch Workflow** (Option 1)

### "I need to push to main but not deploy right now"
→ Use **Disable Workflow in GitHub UI** (Option 2)

### "I deployed something broken and need to rollback NOW"
→ Use **Emergency Rollback** procedures above

### "I want to test locally before any commit"
→ Make changes, test with `python main.py`, then commit to feature branch

---

## Repository Information

- **Repo:** https://github.com/drsandy28783/PhysioPRISMAI-Refresh
- **Main Branch:** `main`
- **Deployment Target:** Azure Container Apps
- **Container App Name:** physiologicprism-app
- **Resource Group:** rg-physiologicprism-prod
- **Registry:** physiologicprismacr.azurecr.io

---

## Testing Checklist Before Merging to Main

- [ ] Changes tested locally
- [ ] No syntax errors (`python -m py_compile main.py`)
- [ ] Templates render correctly (if modified)
- [ ] No breaking changes to database schema
- [ ] Environment variables documented (if new ones added)
- [ ] No secrets committed to code
- [ ] Ready for deployment

---

**Last Updated:** 2026-04-29
**Maintained By:** Development Team
