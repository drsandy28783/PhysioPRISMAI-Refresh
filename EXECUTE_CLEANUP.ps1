# PhysioPRISM Code Cleanup - Step-by-Step Execution Script
# Run this in PowerShell from D:\New folder\New folder\Recovery

Write-Host "`n" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PHYSIOP RISM CODE CLEANUP SCRIPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`n"

# Function to prompt user before each step
function Prompt-Continue {
    param([string]$message)
    Write-Host "`n$message" -ForegroundColor Yellow
    $response = Read-Host "Continue? (y/n)"
    if ($response -ne 'y') {
        Write-Host "Stopped by user. No changes made to this step." -ForegroundColor Red
        exit
    }
}

# Function to test app
function Test-App {
    Write-Host "`n[TEST] Please test the app now:" -ForegroundColor Magenta
    Write-Host "1. Open new terminal" -ForegroundColor White
    Write-Host "2. Run: python main.py" -ForegroundColor White
    Write-Host "3. Verify app starts WITHOUT errors" -ForegroundColor White
    Write-Host "4. Try to access http://localhost:5000" -ForegroundColor White
    Write-Host "`n"
    $response = Read-Host "Did app start successfully? (y/n)"
    if ($response -ne 'y') {
        Write-Host "`n[ROLLBACK]" -ForegroundColor Red
        Write-Host "Run this command to rollback:" -ForegroundColor Red
        Write-Host "git reset --hard v1.0-before-cleanup" -ForegroundColor White
        exit
    }
}

# ============================================
# PHASE 0: SAFETY BASELINE
# ============================================

Write-Host "PHASE 0: Creating Safety Baseline" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

Prompt-Continue "This will create a git baseline and ZIP backup. Ready?"

# Initialize git if not already
if (-not (Test-Path ".git")) {
    Write-Host "[INIT] Initializing git repository..." -ForegroundColor Cyan
    git init
}

# Create git baseline
Write-Host "[GIT] Creating baseline commit..." -ForegroundColor Cyan
git add .
git commit -m 'BASELINE: Before cleanup - DO NOT DELETE THIS COMMIT'
git tag v1.0-before-cleanup

Write-Host "[SUCCESS] Git baseline created with tag: v1.0-before-cleanup" -ForegroundColor Green

# Create ZIP backup
Write-Host "[BACKUP] Creating ZIP backup..." -ForegroundColor Cyan
$date = Get-Date -Format "yyyy-MM-dd-HHmm"
$backupPath = "..\Recovery-BACKUP-$date.zip"
Compress-Archive -Path "." -DestinationPath $backupPath -Force

Write-Host "[SUCCESS] Backup created: $backupPath" -ForegroundColor Green

Write-Host "`n[PHASE 0 COMPLETE]" -ForegroundColor Green
Write-Host "You now have TWO backups:" -ForegroundColor White
Write-Host "1. Git tag: v1.0-before-cleanup" -ForegroundColor White
Write-Host "2. ZIP file: $backupPath" -ForegroundColor White

# ============================================
# PHASE 1: SAFE DELETIONS
# ============================================

Write-Host "`n`nPHASE 1: Safe Deletions" -ForegroundColor Green
Write-Host "=======================" -ForegroundColor Green

# ----------------------------------------
# Step 1.1: Delete backup files
# ----------------------------------------

Prompt-Continue "STEP 1.1: Delete 9 .backup files?"

Write-Host "[DELETE] Removing .backup files..." -ForegroundColor Cyan

$backupFiles = @(
    "ai_cache.py.backup",
    "email_verification.py.backup",
    "invoice_generator.py.backup",
    "main.py.backup",
    "mobile_api.py.backup",
    "mobile_api_ai.py.backup",
    "notification_service.py.backup",
    "razorpay_integration.py.backup",
    "subscription_manager.py.backup"
)

foreach ($file in $backupFiles) {
    if (Test-Path $file) {
        Remove-Item $file
        Write-Host "  ✓ Deleted: $file" -ForegroundColor Gray
    } else {
        Write-Host "  ⊘ Not found: $file" -ForegroundColor Yellow
    }
}

git add -A
git commit -m 'CLEANUP: Remove .backup files (9 files)'
Write-Host "[COMMIT] Step 1.1 committed to git" -ForegroundColor Green

Test-App

# ----------------------------------------
# Step 1.2: Delete migration instruction files
# ----------------------------------------

Prompt-Continue "STEP 1.2: Delete 3 migration instruction files (*_updates.py)?"

Write-Host "[DELETE] Removing migration instruction files..." -ForegroundColor Cyan

$migrationFiles = @(
    "ai_cache_updates.py",
    "main_py_updates.py",
    "mobile_api_ai_updates.py"
)

foreach ($file in $migrationFiles) {
    if (Test-Path $file) {
        Remove-Item $file
        Write-Host "  ✓ Deleted: $file" -ForegroundColor Gray
    } else {
        Write-Host "  ⊘ Not found: $file" -ForegroundColor Yellow
    }
}

git add -A
git commit -m 'CLEANUP: Remove unexecuted Vertex AI migration instruction files'
Write-Host "[COMMIT] Step 1.2 committed to git" -ForegroundColor Green

Test-App

# ----------------------------------------
# Step 1.3: Delete diagnostic scripts
# ----------------------------------------

Prompt-Continue "STEP 1.3: Delete 7 diagnostic scripts (check_*.py)?"

Write-Host "[DELETE] Removing diagnostic scripts..." -ForegroundColor Cyan

$checkFiles = @(
    "check_blog_posts.py",
    "check_firebase_users.py",
    "check_partition_key.py",
    "check_recent_users.py",
    "check_super_admin.py",
    "check_user.py",
    "check_user_cosmos.py"
)

foreach ($file in $checkFiles) {
    if (Test-Path $file) {
        Remove-Item $file
        Write-Host "  ✓ Deleted: $file" -ForegroundColor Gray
    } else {
        Write-Host "  ⊘ Not found: $file" -ForegroundColor Yellow
    }
}

git add -A
git commit -m 'CLEANUP: Remove one-time diagnostic scripts (7 files)'
Write-Host "[COMMIT] Step 1.3 committed to git" -ForegroundColor Green

Test-App

# ----------------------------------------
# Step 1.4: Delete blog import scripts
# ----------------------------------------

Prompt-Continue "STEP 1.4: Delete 5 blog import scripts?"

Write-Host "[DELETE] Removing blog import scripts..." -ForegroundColor Cyan

$blogFiles = @(
    "import_all_blogs.py",
    "import_blog_1.py",
    "import_blog_2.py",
    "import_blog_3.py",
    "blog_import_instructions.txt"
)

foreach ($file in $blogFiles) {
    if (Test-Path $file) {
        Remove-Item $file
        Write-Host "  ✓ Deleted: $file" -ForegroundColor Gray
    } else {
        Write-Host "  ⊘ Not found: $file" -ForegroundColor Yellow
    }
}

git add -A
git commit -m 'CLEANUP: Remove one-time blog import scripts (5 files)'
Write-Host "[COMMIT] Step 1.4 committed to git" -ForegroundColor Green

Test-App

# ----------------------------------------
# Step 1.5: Delete n8n_webhooks.py (DEAD CODE)
# ----------------------------------------

Prompt-Continue "STEP 1.5: Delete n8n_webhooks.py (DEAD CODE - NOT imported anywhere)? THIS IS THE CRITICAL STEP!"

Write-Host "[DELETE] Removing n8n_webhooks.py..." -ForegroundColor Cyan

if (Test-Path "n8n_webhooks.py") {
    Remove-Item "n8n_webhooks.py"
    Write-Host "  ✓ Deleted: n8n_webhooks.py" -ForegroundColor Gray
} else {
    Write-Host "  ⊘ Not found: n8n_webhooks.py" -ForegroundColor Yellow
}

git add -A
git commit -m 'CLEANUP: Remove n8n_webhooks.py (replaced by Resend email service)'
Write-Host "[COMMIT] Step 1.5 committed to git" -ForegroundColor Green

Write-Host "`n[CRITICAL TEST]" -ForegroundColor Red
Write-Host "This step deleted actual code (n8n_webhooks.py)" -ForegroundColor Red
Write-Host "If you see 'ModuleNotFoundError: n8n_webhooks', ROLLBACK IMMEDIATELY!" -ForegroundColor Red
Write-Host "`n"

Test-App

# ----------------------------------------
# Step 1.6: Archive outdated documentation
# ----------------------------------------

Prompt-Continue "STEP 1.6: Archive 15+ outdated .md documentation files?"

Write-Host "[ARCHIVE] Creating docs_archive folder..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path "docs_archive" -Force | Out-Null

Write-Host "[ARCHIVE] Moving outdated docs..." -ForegroundColor Cyan

$docsToArchive = @(
    "MIGRATION_README.md",
    "MIGRATION_GUIDE.md",
    "MIGRATION_100_PERCENT_COMPLETE.md",
    "MIGRATION_COMPLETE_SUMMARY.md",
    "MIGRATION_STATUS_AND_NEXT_STEPS.md",
    "AZURE_MIGRATION_PROGRESS.md",
    "AZURE_MIGRATION_COMPLETE_GUIDE.md",
    "REMAINING_FILE_UPDATES_GUIDE.md",
    "ROLLBACK_PLAN.md",
    "AI_MODEL_ANALYSIS.md",
    "DEPLOYMENT_FILE_SUMMARY.md",
    "SESSION_SUMMARY_2026-01-11.md",
    "SESSION_SYNTAX_ERRORS_FIX_2026-01-14.md",
    "AZURE_CREDENTIALS_CONFIRMED.md",
    "COMPLETE_CODE_AUDIT_REPORT.md"
)

foreach ($doc in $docsToArchive) {
    if (Test-Path $doc) {
        Move-Item $doc "docs_archive\" -Force
        Write-Host "  ✓ Archived: $doc" -ForegroundColor Gray
    } else {
        Write-Host "  ⊘ Not found: $doc" -ForegroundColor Yellow
    }
}

git add -A
git commit -m 'CLEANUP: Archive outdated migration documentation (15 files)'
Write-Host "[COMMIT] Step 1.6 committed to git" -ForegroundColor Green

Write-Host "[INFO] Documentation archived - no app testing needed" -ForegroundColor Cyan

# ----------------------------------------
# Step 1.7: Update .gitignore
# ----------------------------------------

Prompt-Continue "STEP 1.7: Update .gitignore to prevent future clutter?"

Write-Host "[UPDATE] Adding cleanup patterns to .gitignore..." -ForegroundColor Cyan

$gitignoreAdditions = @"

# ============================================
# Code Cleanup Patterns (Added 2026-01-30)
# ============================================

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
"@

Add-Content -Path ".gitignore" -Value $gitignoreAdditions

git add .gitignore
git commit -m 'CLEANUP: Update .gitignore to prevent future clutter'
Write-Host "[COMMIT] Step 1.7 committed to git" -ForegroundColor Green

# ============================================
# PHASE 1 COMPLETE
# ============================================

Write-Host "`n`n" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✅ PHASE 1 CLEANUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Create final tag
git tag v1.1-cleanup-complete

Write-Host "`nSummary:" -ForegroundColor Cyan
Write-Host "  ✓ Deleted 9 .backup files" -ForegroundColor White
Write-Host "  ✓ Deleted 3 migration instruction files" -ForegroundColor White
Write-Host "  ✓ Deleted 7 diagnostic scripts" -ForegroundColor White
Write-Host "  ✓ Deleted 5 blog import scripts" -ForegroundColor White
Write-Host "  ✓ Deleted n8n_webhooks.py (dead code)" -ForegroundColor White
Write-Host "  ✓ Archived 15+ outdated docs" -ForegroundColor White
Write-Host "  ✓ Updated .gitignore" -ForegroundColor White

Write-Host "`nGit Tags Created:" -ForegroundColor Cyan
Write-Host "  • v1.0-before-cleanup (rollback point)" -ForegroundColor White
Write-Host "  • v1.1-cleanup-complete (current)" -ForegroundColor White

Write-Host "`nBackup Location:" -ForegroundColor Cyan
Write-Host "  $backupPath" -ForegroundColor White

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Do a final comprehensive test of your app" -ForegroundColor White
Write-Host "2. Test login, patient creation, AI suggestions" -ForegroundColor White
Write-Host "3. If everything works: KEEP the cleanup" -ForegroundColor White
Write-Host "4. If anything broken: git reset --hard v1.0-before-cleanup" -ForegroundColor White

Write-Host "`n[DONE] Cleanup script completed successfully!" -ForegroundColor Green
Write-Host "`n"
