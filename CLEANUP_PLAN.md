# PhysioPRISM Code Cleanup Plan
**Date:** 2026-01-30
**Prepared by:** Senior Software Engineer (AI Assistant)
**For:** Dr. Sandeep Rao (Non-technical founder)

---

## 🎯 OBJECTIVE

Clean up technical debt accumulated from multiple iterations and platform migrations:
- GCP → Azure migration leftovers
- OpenAI → Vertex AI → OpenAI artifacts
- n8n → Resend email service transition
- Multiple backup files from iterative development

**Goal:** Remove 50+ unnecessary files (~100KB+ of dead code) while maintaining 100% app functionality.

---

## 📊 AUDIT FINDINGS

### ✅ What's SAFE (Keep These)

1. **rate_limiter.py** - Has built-in fallback from Redis → in-memory storage
   - ✅ Works perfectly without Redis
   - ✅ No changes needed

2. **azure_cosmos_db.py** - Firestore-compatible wrapper
   - ✅ Good abstraction layer
   - ✅ Intentional, not dead code

3. **All core application files** - main.py, mobile_api.py, schemas.py, etc.
   - ✅ Active production code

### 🗑️ What's DEAD (Delete These)

#### Category 1: Dead Code (NOT imported anywhere)
- ❌ **n8n_webhooks.py** (580 lines) - Replaced by Resend email service
  - Searched entire codebase: ZERO imports found
  - Per .env.example: "Migration to Resend completed - these are no longer needed"

#### Category 2: Backup Files (9 files)
- ❌ ai_cache.py.backup
- ❌ email_verification.py.backup
- ❌ invoice_generator.py.backup
- ❌ main.py.backup
- ❌ mobile_api.py.backup
- ❌ mobile_api_ai.py.backup
- ❌ notification_service.py.backup
- ❌ razorpay_integration.py.backup
- ❌ subscription_manager.py.backup

#### Category 3: Migration Instruction Files (3 files)
These are NOT code - they're instructions for a Vertex AI migration that never happened:
- ❌ ai_cache_updates.py - "How to update ai_cache.py"
- ❌ main_py_updates.py - "How to update main.py"
- ❌ mobile_api_ai_updates.py - "How to update mobile_api_ai.py"

#### Category 4: One-Time Diagnostic Scripts (7 files)
Used once for debugging, never needed again:
- ❌ check_blog_posts.py
- ❌ check_firebase_users.py
- ❌ check_partition_key.py
- ❌ check_recent_users.py
- ❌ check_super_admin.py
- ❌ check_user.py
- ❌ check_user_cosmos.py

#### Category 5: One-Time Import Scripts (4 files)
Used once to seed blog data, never needed again:
- ❌ import_all_blogs.py
- ❌ import_blog_1.py
- ❌ import_blog_2.py
- ❌ import_blog_3.py

#### Category 6: Outdated Documentation (20+ files)
Migration docs for platforms/features no longer relevant:
- Migration guides (MIGRATION_*.md) - 6 files
- Azure migration progress docs - 5 files
- Vertex AI documentation - 10+ files
- Session summaries - 2 files

**Total to Delete:** 44+ files

---

## 🔐 SAFETY PROTOCOL

### Before ANY Changes:

```bash
# 1. Create Git Baseline
cd "D:\New folder\New folder\Recovery"
git init
git add .
git commit -m "BASELINE: Before cleanup - DO NOT DELETE THIS COMMIT"
git tag v1.0-before-cleanup

# 2. Create ZIP Backup (outside project)
cd "D:\New folder\New folder"
powershell -Command "Compress-Archive -Path 'Recovery' -DestinationPath 'Recovery-BACKUP-$(Get-Date -Format yyyy-MM-dd).zip'"
```

### Rollback Plan:
```bash
# If ANYTHING breaks, instant rollback:
git reset --hard v1.0-before-cleanup

# Or restore from ZIP backup
```

---

## 📋 PHASE 1: SAFE DELETIONS (Days 1-3)

### Step 1.1: Delete Backup Files (5 minutes)
```bash
cd "D:\New folder\New folder\Recovery"

# Delete all .backup files
Remove-Item "ai_cache.py.backup"
Remove-Item "email_verification.py.backup"
Remove-Item "invoice_generator.py.backup"
Remove-Item "main.py.backup"
Remove-Item "mobile_api.py.backup"
Remove-Item "mobile_api_ai.py.backup"
Remove-Item "notification_service.py.backup"
Remove-Item "razorpay_integration.py.backup"
Remove-Item "subscription_manager.py.backup"

# Commit
git add -A
git commit -m "CLEANUP: Remove .backup files (9 files)"
```

**Test:** Run app, verify it starts normally.

---

### Step 1.2: Delete Migration Instruction Files (5 minutes)
```bash
# These are text instructions, not actual code
Remove-Item "ai_cache_updates.py"
Remove-Item "main_py_updates.py"
Remove-Item "mobile_api_ai_updates.py"

# Commit
git add -A
git commit -m "CLEANUP: Remove unexecuted Vertex AI migration instruction files"
```

**Test:** Run app, verify it starts normally.

---

### Step 1.3: Delete Diagnostic Scripts (5 minutes)
```bash
# One-time debugging scripts, never imported
Remove-Item "check_blog_posts.py"
Remove-Item "check_firebase_users.py"
Remove-Item "check_partition_key.py"
Remove-Item "check_recent_users.py"
Remove-Item "check_super_admin.py"
Remove-Item "check_user.py"
Remove-Item "check_user_cosmos.py"

# Commit
git add -A
git commit -m "CLEANUP: Remove one-time diagnostic scripts (7 files)"
```

**Test:** Run app, verify it starts normally.

---

### Step 1.4: Delete Blog Import Scripts (5 minutes)
```bash
# One-time data import scripts
Remove-Item "import_all_blogs.py"
Remove-Item "import_blog_1.py"
Remove-Item "import_blog_2.py"
Remove-Item "import_blog_3.py"

# Also delete the instructions file
Remove-Item "blog_import_instructions.txt"

# Commit
git add -A
git commit -m "CLEANUP: Remove one-time blog import scripts (5 files)"
```

**Test:** Run app, verify it starts normally.

---

### Step 1.5: Delete n8n Webhooks (DEAD CODE) (10 minutes)

**IMPORTANT:** This is the ONLY actual code file we're deleting. But it's safe because:
1. Not imported anywhere (verified via grep search)
2. Replaced by Resend email service
3. Environment vars for n8n commented out in .env.example

```bash
# Delete the dead code file
Remove-Item "n8n_webhooks.py"

# Commit
git add -A
git commit -m "CLEANUP: Remove n8n_webhooks.py (replaced by Resend email service)"
```

**Test:**
```bash
# Start the app
python main.py

# Should start WITHOUT any import errors
# If you see "ModuleNotFoundError: No module named 'n8n_webhooks'",
# something is still importing it - ROLLBACK IMMEDIATELY
```

---

### Step 1.6: Archive Outdated Documentation (15 minutes)

**Strategy:** Don't delete docs, move them to an archive folder.

```bash
# Create archive folder
New-Item -ItemType Directory -Path "docs_archive" -Force

# Move migration-related docs
Move-Item "MIGRATION_README.md" "docs_archive/"
Move-Item "MIGRATION_GUIDE.md" "docs_archive/"
Move-Item "MIGRATION_100_PERCENT_COMPLETE.md" "docs_archive/"
Move-Item "MIGRATION_COMPLETE_SUMMARY.md" "docs_archive/"
Move-Item "MIGRATION_STATUS_AND_NEXT_STEPS.md" "docs_archive/"
Move-Item "AZURE_MIGRATION_PROGRESS.md" "docs_archive/"
Move-Item "AZURE_MIGRATION_COMPLETE_GUIDE.md" "docs_archive/"
Move-Item "REMAINING_FILE_UPDATES_GUIDE.md" "docs_archive/"
Move-Item "ROLLBACK_PLAN.md" "docs_archive/"
Move-Item "AI_MODEL_ANALYSIS.md" "docs_archive/"
Move-Item "DEPLOYMENT_FILE_SUMMARY.md" "docs_archive/"
Move-Item "SESSION_SUMMARY_2026-01-11.md" "docs_archive/"
Move-Item "SESSION_SYNTAX_ERRORS_FIX_2026-01-14.md" "docs_archive/"
Move-Item "AZURE_CREDENTIALS_CONFIRMED.md" "docs_archive/"
Move-Item "COMPLETE_CODE_AUDIT_REPORT.md" "docs_archive/"

# Commit
git add -A
git commit -m "CLEANUP: Archive outdated migration documentation (15 files)"
```

**Test:** Docs are just docs - no testing needed.

---

### Step 1.7: Update .gitignore (5 minutes)

Add cleanup patterns to prevent future clutter:

```bash
# Add to .gitignore:
cat >> .gitignore << 'EOF'

# Backup files from iterative development
*.backup
*_backup.py
*_old.py

# Migration instruction files
*_updates.py

# One-time scripts
check_*.py
import_blog_*.py
cleanup_*.py
migrate_*.py
fix_*.py
verify_*.py

# Archived docs
docs_archive/
EOF

# Commit
git add .gitignore
git commit -m "CLEANUP: Update .gitignore to prevent future clutter"
```

---

## ✅ PHASE 1 COMPLETE: Testing Checklist

After all Phase 1 steps, perform comprehensive testing:

### Backend Testing:
```bash
# 1. Start the app
python main.py

# Should see:
# ✅ "[OK] All required environment variables configured"
# ✅ "Rate limiter initialized with storage: Memory"  # Redis fallback working
# ✅ "Firebase Admin SDK initialized"
# ❌ NO import errors
```

### Web App Testing:
1. Open browser: http://localhost:5000
2. Test login page loads
3. Test a successful login
4. Test patient list loads
5. Test creating a test patient
6. Test AI suggestion (if you have API keys configured)

### Mobile API Testing:
```bash
# Test mobile API endpoint
curl -X GET http://localhost:5000/health
# Should return: {"status": "ok"}
```

### If Anything Fails:
```bash
# ROLLBACK IMMEDIATELY
git reset --hard v1.0-before-cleanup

# Then investigate which specific file caused the issue
# Report to AI assistant for analysis
```

---

## 📊 PHASE 1 RESULTS

**Files Deleted:** 44+
**Code Removed:** ~2,000+ lines (dead code + backups)
**Functionality Lost:** ZERO
**Risk Level:** MINIMAL (mostly non-code files)

**Before:**
```
Recovery/
├── 150+ files
├── main.py (402KB - bloated)
├── 9 .backup files
├── 14 one-time scripts
├── 33 .md docs (many outdated)
└── 1 dead code file (n8n_webhooks.py)
```

**After:**
```
Recovery/
├── ~100 files (active code only)
├── main.py (402KB - to be refactored in Phase 2)
├── 0 .backup files ✅
├── 0 one-time scripts ✅
├── ~18 relevant .md docs ✅
├── docs_archive/ (historical reference)
└── 0 dead code files ✅
```

---

## 🚦 NEXT STEPS

### Phase 2 (Optional, Week 2):
1. **Refactor main.py** - Split 402KB file into modules
2. **Remove unused imports** - Clean up import statements
3. **Consolidate remaining docs** - Create single README.md

### Phase 3 (Recommended, Week 3):
1. **Add basic tests** - Smoke tests for critical paths
2. **Set up monitoring** - Application Insights or similar
3. **Create deployment checklist** - Document production deployment

---

## 📞 SUPPORT

**If you encounter ANY issues during cleanup:**

1. **STOP immediately**
2. **DO NOT proceed to next step**
3. **Take a screenshot of the error**
4. **Run rollback command:**
   ```bash
   git reset --hard v1.0-before-cleanup
   ```
5. **Contact AI assistant with:**
   - Error screenshot
   - Which step you were on
   - What command you ran

**Remember:** We have TWO backups (git + ZIP), so nothing can be permanently lost.

---

## ✅ COMPLETION CHECKLIST

Phase 1 - Safe Deletions:
- [ ] Git baseline created (`v1.0-before-cleanup` tag exists)
- [ ] ZIP backup created outside project folder
- [ ] Step 1.1: Deleted 9 .backup files
- [ ] Step 1.2: Deleted 3 migration instruction files
- [ ] Step 1.3: Deleted 7 diagnostic scripts
- [ ] Step 1.4: Deleted 5 blog import scripts
- [ ] Step 1.5: Deleted n8n_webhooks.py (dead code)
- [ ] Step 1.6: Archived 15+ outdated docs
- [ ] Step 1.7: Updated .gitignore
- [ ] ✅ App tested and working
- [ ] ✅ Git commit for each step
- [ ] ✅ Final tag: `v1.1-cleanup-complete`

---

**Document Version:** 1.0
**Last Updated:** 2026-01-30
**Status:** Ready for Execution
