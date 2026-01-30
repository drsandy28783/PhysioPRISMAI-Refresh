# PhysioPRISM Code Cleanup Script - Simplified Version
# Run from: D:\New folder\New folder\Recovery

Write-Host ""
Write-Host "========================================"
Write-Host "  PHYSIOPRISM CODE CLEANUP SCRIPT"
Write-Host "========================================"
Write-Host ""

function Ask-Continue {
    param([string]$msg)
    Write-Host ""
    Write-Host $msg -ForegroundColor Yellow
    $resp = Read-Host "Continue? (y/n)"
    if ($resp -ne 'y') {
        Write-Host "Stopped. No changes made." -ForegroundColor Red
        exit
    }
}

function Test-Application {
    Write-Host ""
    Write-Host "[TEST] Please test the app now:" -ForegroundColor Magenta
    Write-Host "1. Open new PowerShell window"
    Write-Host "2. Run: python main.py"
    Write-Host "3. Check for errors"
    Write-Host "4. Try http://localhost:5000"
    Write-Host ""
    $resp = Read-Host "Did app start successfully? (y/n)"
    if ($resp -ne 'y') {
        Write-Host ""
        Write-Host "[ROLLBACK] Run: git reset --hard v1.0-before-cleanup" -ForegroundColor Red
        exit
    }
}

# PHASE 0: Create Baseline
Write-Host "PHASE 0: Creating Safety Baseline" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

Ask-Continue "Create git baseline and ZIP backup?"

if (-not (Test-Path ".git")) {
    Write-Host "[INIT] Initializing git..." -ForegroundColor Cyan
    git init
}

Write-Host "[GIT] Creating baseline commit..." -ForegroundColor Cyan
git add .
git commit -m 'BASELINE: Before cleanup'
git tag v1.0-before-cleanup

Write-Host "[SUCCESS] Git baseline created" -ForegroundColor Green

Write-Host "[BACKUP] Creating ZIP backup..." -ForegroundColor Cyan
$date = Get-Date -Format "yyyy-MM-dd-HHmm"
$backupPath = "..\Recovery-BACKUP-$date.zip"
Compress-Archive -Path "." -DestinationPath $backupPath -Force

Write-Host "[SUCCESS] Backup created: $backupPath" -ForegroundColor Green
Write-Host ""
Write-Host "Backups ready:" -ForegroundColor White
Write-Host "1. Git tag: v1.0-before-cleanup" -ForegroundColor White
Write-Host "2. ZIP file: $backupPath" -ForegroundColor White

# PHASE 1: Cleanup
Write-Host ""
Write-Host ""
Write-Host "PHASE 1: Safe Deletions" -ForegroundColor Green
Write-Host "=======================" -ForegroundColor Green

# Step 1.1: Delete backup files
Ask-Continue "STEP 1.1: Delete 9 .backup files?"

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
        Write-Host "  Deleted: $file" -ForegroundColor Gray
    }
}

git add -A
git commit -m 'CLEANUP: Remove backup files'
Write-Host "[COMMIT] Step 1.1 done" -ForegroundColor Green

Test-Application

# Step 1.2: Delete migration files
Ask-Continue "STEP 1.2: Delete 3 migration instruction files?"

Write-Host "[DELETE] Removing migration files..." -ForegroundColor Cyan

$migFiles = @(
    "ai_cache_updates.py",
    "main_py_updates.py",
    "mobile_api_ai_updates.py"
)

foreach ($file in $migFiles) {
    if (Test-Path $file) {
        Remove-Item $file
        Write-Host "  Deleted: $file" -ForegroundColor Gray
    }
}

git add -A
git commit -m 'CLEANUP: Remove migration instruction files'
Write-Host "[COMMIT] Step 1.2 done" -ForegroundColor Green

Test-Application

# Step 1.3: Delete diagnostic scripts
Ask-Continue "STEP 1.3: Delete 7 diagnostic scripts?"

Write-Host "[DELETE] Removing diagnostic scripts..." -ForegroundColor Cyan

$diagFiles = @(
    "check_blog_posts.py",
    "check_firebase_users.py",
    "check_partition_key.py",
    "check_recent_users.py",
    "check_super_admin.py",
    "check_user.py",
    "check_user_cosmos.py"
)

foreach ($file in $diagFiles) {
    if (Test-Path $file) {
        Remove-Item $file
        Write-Host "  Deleted: $file" -ForegroundColor Gray
    }
}

git add -A
git commit -m 'CLEANUP: Remove diagnostic scripts'
Write-Host "[COMMIT] Step 1.3 done" -ForegroundColor Green

Test-Application

# Step 1.4: Delete blog import scripts
Ask-Continue "STEP 1.4: Delete 5 blog import scripts?"

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
        Write-Host "  Deleted: $file" -ForegroundColor Gray
    }
}

git add -A
git commit -m 'CLEANUP: Remove blog import scripts'
Write-Host "[COMMIT] Step 1.4 done" -ForegroundColor Green

Test-Application

# Step 1.5: Delete n8n_webhooks.py
Ask-Continue "STEP 1.5: Delete n8n_webhooks.py (CRITICAL - dead code)?"

Write-Host "[DELETE] Removing n8n_webhooks.py..." -ForegroundColor Cyan

if (Test-Path "n8n_webhooks.py") {
    Remove-Item "n8n_webhooks.py"
    Write-Host "  Deleted: n8n_webhooks.py" -ForegroundColor Gray
}

git add -A
git commit -m 'CLEANUP: Remove n8n webhooks (replaced by Resend)'
Write-Host "[COMMIT] Step 1.5 done" -ForegroundColor Green

Write-Host ""
Write-Host "[CRITICAL TEST]" -ForegroundColor Red
Write-Host "This deleted actual code!" -ForegroundColor Red
Write-Host "If you see ModuleNotFoundError, ROLLBACK!" -ForegroundColor Red
Write-Host ""

Test-Application

# Step 1.6: Archive documentation
Ask-Continue "STEP 1.6: Archive outdated documentation?"

Write-Host "[ARCHIVE] Creating docs_archive folder..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path "docs_archive" -Force | Out-Null

Write-Host "[ARCHIVE] Moving outdated docs..." -ForegroundColor Cyan

$docs = @(
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

foreach ($doc in $docs) {
    if (Test-Path $doc) {
        Move-Item $doc "docs_archive\" -Force
        Write-Host "  Archived: $doc" -ForegroundColor Gray
    }
}

git add -A
git commit -m 'CLEANUP: Archive outdated documentation'
Write-Host "[COMMIT] Step 1.6 done" -ForegroundColor Green

Write-Host "[INFO] Docs archived - no testing needed" -ForegroundColor Cyan

# Step 1.7: Update .gitignore
Ask-Continue "STEP 1.7: Update .gitignore?"

Write-Host "[UPDATE] Adding patterns to .gitignore..." -ForegroundColor Cyan

$additions = @"

# Code Cleanup Patterns (Added 2026-01-30)
*.backup
*_backup.py
*_old.py
*_updates.py
check_*.py
import_blog_*.py
cleanup_*.py
migrate_*.py
fix_*.py
verify_*.py
docs_archive/
"@

Add-Content -Path ".gitignore" -Value $additions

git add .gitignore
git commit -m 'CLEANUP: Update gitignore'
Write-Host "[COMMIT] Step 1.7 done" -ForegroundColor Green

# COMPLETE
Write-Host ""
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  CLEANUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

git tag v1.1-cleanup-complete

Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Deleted 9 .backup files" -ForegroundColor White
Write-Host "  Deleted 3 migration files" -ForegroundColor White
Write-Host "  Deleted 7 diagnostic scripts" -ForegroundColor White
Write-Host "  Deleted 5 blog import scripts" -ForegroundColor White
Write-Host "  Deleted n8n_webhooks.py" -ForegroundColor White
Write-Host "  Archived 15+ docs" -ForegroundColor White
Write-Host "  Updated .gitignore" -ForegroundColor White

Write-Host ""
Write-Host "Git Tags:" -ForegroundColor Cyan
Write-Host "  v1.0-before-cleanup (rollback point)" -ForegroundColor White
Write-Host "  v1.1-cleanup-complete (current)" -ForegroundColor White

Write-Host ""
Write-Host "Backup: $backupPath" -ForegroundColor Cyan

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Do final comprehensive test" -ForegroundColor White
Write-Host "2. Test login, patients, AI" -ForegroundColor White
Write-Host "3. If all works: DONE!" -ForegroundColor White
Write-Host "4. If broken: git reset --hard v1.0-before-cleanup" -ForegroundColor White

Write-Host ""
Write-Host "[DONE] Cleanup completed successfully!" -ForegroundColor Green
Write-Host ""
