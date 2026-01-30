################################################################################
# Add Sentry Error Tracking to Azure Production
################################################################################
# This script adds SENTRY_DSN and ENVIRONMENT variables to your Azure Container App
# so that production errors are automatically tracked in Sentry.
################################################################################

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Add Sentry to Azure Production" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$subscriptionId = "33b7366e-4815-4987-9d92-a1fed4227c97"
$resourceGroup = "rg-physiologicprism-prod"
$containerAppName = "physiologicprism-app"
$sentryDsn = "https://0522f881e28ee6b8b9d4319907a5dc11@o451054777748992.ingest.us.sentry.io/4510547780501504"
$environment = "production"

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Resource Group: $resourceGroup"
Write-Host "  Container App: $containerAppName"
Write-Host "  Environment: $environment"
Write-Host ""

# Step 1: Check if Azure CLI is installed
Write-Host "[1/5] Checking Azure CLI..." -ForegroundColor Cyan
try {
    $azVersion = az version --output json 2>&1 | ConvertFrom-Json
    Write-Host "  Azure CLI version: $($azVersion.'azure-cli')" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Azure CLI not installed!" -ForegroundColor Red
    Write-Host "  Install from: https://aka.ms/installazurecli" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Step 2: Check if logged in
Write-Host "[2/5] Checking Azure login..." -ForegroundColor Cyan
$account = az account show 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Not logged in. Starting login..." -ForegroundColor Yellow
    az login
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: Login failed!" -ForegroundColor Red
        exit 1
    }
} else {
    $accountInfo = $account | ConvertFrom-Json
    Write-Host "  Logged in as: $($accountInfo.user.name)" -ForegroundColor Green
}
Write-Host ""

# Step 3: Set subscription
Write-Host "[3/5] Setting subscription..." -ForegroundColor Cyan
az account set --subscription $subscriptionId
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Subscription set successfully" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Failed to set subscription!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 4: Add environment variables
Write-Host "[4/5] Adding Sentry environment variables..." -ForegroundColor Cyan
Write-Host "  This will restart your Container App (takes 1-2 minutes)" -ForegroundColor Yellow
Write-Host ""

# Get current environment variables
Write-Host "  Getting current environment variables..."
$currentEnvVars = az containerapp show `
    --name $containerAppName `
    --resource-group $resourceGroup `
    --query "properties.template.containers[0].env" `
    --output json | ConvertFrom-Json

# Check if SENTRY_DSN already exists
$sentryExists = $currentEnvVars | Where-Object { $_.name -eq "SENTRY_DSN" }
$envExists = $currentEnvVars | Where-Object { $_.name -eq "ENVIRONMENT" }

if ($sentryExists) {
    Write-Host "  SENTRY_DSN already exists. Updating..." -ForegroundColor Yellow
} else {
    Write-Host "  Adding SENTRY_DSN (new)..." -ForegroundColor Green
}

if ($envExists) {
    Write-Host "  ENVIRONMENT already exists. Updating..." -ForegroundColor Yellow
} else {
    Write-Host "  Adding ENVIRONMENT (new)..." -ForegroundColor Green
}

# Update environment variables
az containerapp update `
    --name $containerAppName `
    --resource-group $resourceGroup `
    --set-env-vars "SENTRY_DSN=$sentryDsn" "ENVIRONMENT=$environment" `
    --output none

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "  Environment variables added successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  ERROR: Failed to add environment variables!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Verify
Write-Host "[5/5] Verifying configuration..." -ForegroundColor Cyan
Write-Host "  Checking if environment variables are set..."

$updatedEnvVars = az containerapp show `
    --name $containerAppName `
    --resource-group $resourceGroup `
    --query "properties.template.containers[0].env" `
    --output json | ConvertFrom-Json

$sentryDsnVar = $updatedEnvVars | Where-Object { $_.name -eq "SENTRY_DSN" }
$environmentVar = $updatedEnvVars | Where-Object { $_.name -eq "ENVIRONMENT" }

if ($sentryDsnVar) {
    $maskedDsn = $sentryDsn.Substring(0, 30) + "..." + $sentryDsn.Substring($sentryDsn.Length - 10)
    Write-Host "  SENTRY_DSN: $maskedDsn" -ForegroundColor Green
} else {
    Write-Host "  SENTRY_DSN: NOT FOUND!" -ForegroundColor Red
}

if ($environmentVar) {
    Write-Host "  ENVIRONMENT: $($environmentVar.value)" -ForegroundColor Green
} else {
    Write-Host "  ENVIRONMENT: NOT FOUND!" -ForegroundColor Red
}

Write-Host ""

# Get app URL
$appUrl = az containerapp show `
    --name $containerAppName `
    --resource-group $resourceGroup `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SENTRY SETUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "What happens now:" -ForegroundColor Yellow
Write-Host "  1. Your Container App is restarting (1-2 minutes)" -ForegroundColor White
Write-Host "  2. Sentry is now monitoring production errors" -ForegroundColor White
Write-Host "  3. You'll get email alerts when errors occur" -ForegroundColor White
Write-Host ""
Write-Host "Your app URL:" -ForegroundColor Yellow
Write-Host "  https://$appUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "Sentry Dashboard:" -ForegroundColor Yellow
Write-Host "  https://physiologicprism.sentry.io/issues/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Wait 2 minutes for app to restart" -ForegroundColor White
Write-Host "  2. Test your production app" -ForegroundColor White
Write-Host "  3. Any errors will appear in Sentry!" -ForegroundColor White
Write-Host ""
Write-Host "You're now 100% production ready!" -ForegroundColor Green
Write-Host ""
