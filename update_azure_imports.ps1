# ================================================================
# Azure Migration - Batch File Updater
# ================================================================
# This script updates all Python files to use Azure services
# instead of Firebase/GCP services
#
# Usage: powershell -ExecutionPolicy Bypass -File update_azure_imports.ps1
# ================================================================

Write-Host "`n" -NoNewline
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Azure Migration - Batch File Updater" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# List of files to update
$files = @(
    "mobile_api.py",
    "subscription_manager.py",
    "notification_service.py",
    "invoice_generator.py",
    "email_verification.py",
    "razorpay_integration.py"
)

$successCount = 0
$failCount = 0

foreach ($file in $files) {
    Write-Host "Processing: $file" -ForegroundColor Yellow

    if (-not (Test-Path $file)) {
        Write-Host "  File not found - skipping" -ForegroundColor Red
        $failCount++
        continue
    }

    try {
        # Create backup
        $backupFile = "$file.backup"
        Copy-Item $file $backupFile -Force
        Write-Host "  Backup created: $backupFile" -ForegroundColor Gray

        # Read content
        $content = Get-Content $file -Raw

        # Track changes
        $changesMade = @()

        # Replace Firebase Firestore imports
        if ($content -match 'from firebase_admin import firestore') {
            $content = $content -replace 'from firebase_admin import firestore', '# Firebase removed - using Azure Cosmos DB'
            $changesMade += "Removed firebase_admin.firestore import"
        }

        # Replace SERVER_TIMESTAMP import
        if ($content -match 'from firebase_admin\.firestore import SERVER_TIMESTAMP') {
            $content = $content -replace 'from firebase_admin\.firestore import SERVER_TIMESTAMP', 'from azure_cosmos_db import SERVER_TIMESTAMP'
            $changesMade += "Updated SERVER_TIMESTAMP import"
        }

        # Add Azure Cosmos DB import if not present
        if ($content -notmatch 'from azure_cosmos_db import') {
            # Find the import section (after docstring, before first function/class)
            $importSection = "import logging`nfrom azure_cosmos_db import get_cosmos_db, SERVER_TIMESTAMP`n"
            $content = $content -replace '(import logging)', $importSection
            $changesMade += "Added Azure Cosmos DB import"
        }

        # Replace Firestore client initialization
        if ($content -match 'db = firestore\.client\(\)') {
            $content = $content -replace 'db = firestore\.client\(\)', 'db = get_cosmos_db()'
            $changesMade += "Updated database client initialization"
        }

        # Replace Vertex AI imports
        if ($content -match 'from vertex_ai_client import') {
            $content = $content -replace 'from vertex_ai_client import', 'from azure_openai_client import'
            $changesMade += "Updated AI client import"
        }

        # Replace AI client calls
        if ($content -match 'get_vertex_client') {
            $content = $content -replace 'get_vertex_client', 'get_azure_openai_client'
            $changesMade += "Updated AI client function"
        }

        # Replace model names
        if ($content -match 'claude-sonnet-4-5') {
            $content = $content -replace 'claude-sonnet-4-5[^"]*', 'gpt-4o'
            $changesMade += "Updated model name to gpt-4o"
        }

        if ($content -match 'gpt-4-turbo') {
            $content = $content -replace 'gpt-4-turbo', 'gpt-4o'
            $changesMade += "Updated model name to gpt-4o"
        }

        # Replace Firestore comments with Cosmos DB
        $cosmosReplacement = "Cosmos DB"
        $content = $content -replace 'Firestore', $cosmosReplacement

        # Save updated content
        $content | Set-Content $file -NoNewline

        # Report changes
        if ($changesMade.Count -gt 0) {
            Write-Host "  Updated successfully:" -ForegroundColor Green
            foreach ($change in $changesMade) {
                Write-Host "     - $change" -ForegroundColor Gray
            }
        } else {
            Write-Host "  No changes needed" -ForegroundColor Cyan
        }

        $successCount++

    } catch {
        Write-Host "  Error updating file: $_" -ForegroundColor Red
        $failCount++

        # Restore from backup on error
        if (Test-Path $backupFile) {
            Copy-Item $backupFile $file -Force
            Write-Host "  Restored from backup" -ForegroundColor Yellow
        }
    }

    Write-Host ""
}

# Summary
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Update Summary" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Success: $successCount files" -ForegroundColor Green
Write-Host "  Failed:  $failCount files" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Backups saved with .backup extension" -ForegroundColor Cyan
Write-Host "You can restore by running: Copy-Item *.backup" -ForegroundColor Gray
Write-Host ""

if ($successCount -gt 0) {
    Write-Host "Migration complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Copy .env.azure to .env" -ForegroundColor Gray
    Write-Host "  2. Fill in Azure credentials in .env" -ForegroundColor Gray
    Write-Host "  3. Test: python main.py" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "No files were updated successfully" -ForegroundColor Yellow
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
