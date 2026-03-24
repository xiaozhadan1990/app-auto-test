param(
    [ValidateSet("smoke", "full", "all")]
    [string]$Suite = "smoke",

    [ValidateSet("all", "lysora", "ruijieCloud")]
    [string]$Component = "all",

    [switch]$OpenReport,
    [switch]$GenerateReport,
    [switch]$ServeReport
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$resultsDir = Join-Path $projectRoot "reports\allure-results"
$htmlDir = Join-Path $projectRoot "reports\allure-html"
$env:UV_CACHE_DIR = Join-Path $projectRoot ".uv-cache"

Push-Location $projectRoot
try {
    $markerParts = @()
    if ($Suite -ne "all") {
        $markerParts += $Suite
    }
    if ($Component -ne "all") {
        $markerParts += $Component
    }

    if (Test-Path -LiteralPath $resultsDir) {
        Remove-Item -LiteralPath $resultsDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null

    $pytestArgs = @("run", "pytest", "tests/", "--alluredir", $resultsDir, "--clean-alluredir")
    if ($markerParts.Count -gt 0) {
        $pytestArgs += @("-m", ($markerParts -join " and "))
    }

    Write-Host "[pytest] Running: uv $($pytestArgs -join ' ')"
    & uv @pytestArgs
    $pytestExit = $LASTEXITCODE
    if ($pytestExit -ne 0) {
        Write-Host "[pytest] Exit code: $pytestExit" -ForegroundColor Yellow
    }

    $needReport = $GenerateReport -or $OpenReport -or $ServeReport
    if (-not $needReport) {
        exit $pytestExit
    }

    $allureCmd = Get-Command allure -ErrorAction SilentlyContinue
    if (-not $allureCmd) {
        Write-Host "[WARN] allure command not found in PATH, skipping report generation." -ForegroundColor Yellow
        exit $pytestExit
    }

    if (-not (Test-Path -LiteralPath $resultsDir)) {
        Write-Host "[WARN] Allure results directory not found: $resultsDir" -ForegroundColor Yellow
        exit $pytestExit
    }

    Write-Host "[allure] Generating HTML report..."
    & allure generate $resultsDir -o $htmlDir --clean
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to generate Allure report." -ForegroundColor Red
        exit $LASTEXITCODE
    }

    if ($OpenReport) {
        Write-Host "[allure] Opening report..."
        & allure open $htmlDir
    } elseif ($ServeReport) {
        Write-Host "[allure] Serving report..."
        & allure serve $resultsDir
    }

    exit $pytestExit
}
finally {
    Pop-Location
}
