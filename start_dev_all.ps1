param(
    [switch]$NoInstall,
    [int]$FrontendPort = 5173
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-EnvValueFromFile {
    param(
        [string]$FilePath,
        [string]$Key
    )
    if (-not (Test-Path -LiteralPath $FilePath)) {
        return $null
    }
    foreach ($rawLine in Get-Content -LiteralPath $FilePath -Encoding UTF8) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) { continue }
        $idx = $line.IndexOf("=")
        if ($idx -lt 1) { continue }
        $k = $line.Substring(0, $idx).Trim()
        if ($k -ne $Key) { continue }
        return $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
    }
    return $null
}

function Get-PortOwners {
    param([int]$Port)
    $lines = netstat -ano -p TCP | Select-String ":$Port\s"
    $pids = @()
    foreach ($line in $lines) {
        $text = ($line.ToString() -replace "\s+", " ").Trim()
        if (-not $text) { continue }
        $parts = $text.Split(" ")
        if ($parts.Count -lt 5) { continue }
        if ($parts[3] -ne "LISTENING") { continue }
        $ownerPid = 0
        if ([int]::TryParse($parts[4], [ref]$ownerPid)) {
            if ($ownerPid -gt 0 -and -not $pids.Contains($ownerPid)) {
                $pids += $ownerPid
            }
        }
    }
    return @($pids)
}

function Stop-PortOwners {
    param(
        [int]$Port,
        [string]$Label
    )
    $owners = @(Get-PortOwners -Port $Port)
    if ($owners.Length -eq 0) {
        Write-Host "[$Label] Port $Port is free."
        return
    }
    Write-Host "[$Label] Port $Port is occupied, stopping processes..."
    foreach ($ownerPid in $owners) {
        $proc = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host ("  stopping PID={0}, Name={1}" -f $proc.Id, $proc.ProcessName)
        } else {
            Write-Host ("  stopping PID={0}, Name=<unknown>" -f $ownerPid)
        }
        Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue
    }
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$webUiRoot = Join-Path $projectRoot "web-ui"
$envPath = Join-Path $projectRoot ".env"

if (-not (Test-Path -LiteralPath $webUiRoot)) {
    Write-Host "[ERROR] web-ui directory not found." -ForegroundColor Red
    exit 1
}

$backendHost = Get-EnvValueFromFile -FilePath $envPath -Key "DESKTOP_WEB_HOST"
if (-not $backendHost) { $backendHost = "127.0.0.1" }
$backendPortRaw = Get-EnvValueFromFile -FilePath $envPath -Key "DESKTOP_WEB_PORT"
$backendPort = 17999
if ($backendPortRaw) {
    $n = 0
    if ([int]::TryParse($backendPortRaw, [ref]$n)) { $backendPort = $n }
}

Write-Host "Project root : $projectRoot"
Write-Host "Backend host : $backendHost"
Write-Host "Backend port : $backendPort"
Write-Host "Frontend port: $FrontendPort"

Stop-PortOwners -Port $backendPort -Label "backend"
Stop-PortOwners -Port $FrontendPort -Label "frontend"

if (-not $NoInstall) {
    $nodeModules = Join-Path $webUiRoot "node_modules"
    Write-Host "[backend] Syncing Python dependencies with uv..."
    Push-Location $projectRoot
    try {
        uv sync
    } finally {
        Pop-Location
    }
    if (-not (Test-Path -LiteralPath $nodeModules)) {
        Write-Host "[frontend] Installing dependencies (yarn install)..."
        Push-Location $webUiRoot
        try {
            yarn install
        } finally {
            Pop-Location
        }
    }
}

$backendCmd = "Set-Location '$projectRoot'; uv run python desktop_web_app.py"
$frontendCmd = "Set-Location '$webUiRoot'; yarn dev"

Write-Host "[backend] Starting desktop_web_app.py with uv..."
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCmd | Out-Null

Write-Host "[frontend] Starting yarn dev..."
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCmd | Out-Null

Write-Host ""
Write-Host "Started:"
Write-Host ("  Backend : http://{0}:{1}" -f $backendHost, $backendPort)
Write-Host ("  Frontend: http://127.0.0.1:{0}" -f $FrontendPort)
Write-Host ""
Write-Host "Tip: use -NoInstall to skip dependency check."
