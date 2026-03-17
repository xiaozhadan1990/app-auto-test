param(
    [switch]$SkipPortCheck
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
        $v = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
        return $v
    }
    return $null
}

function Get-DesktopPort {
    param([string]$Root)
    $envFile = Join-Path $Root ".env"
    $fromFile = Get-EnvValueFromFile -FilePath $envFile -Key "DESKTOP_WEB_PORT"
    if ($fromFile) {
        $num = 0
        if ([int]::TryParse($fromFile, [ref]$num)) {
            return $num
        }
    }
    return 17999
}

function Get-DesktopHost {
    param([string]$Root)
    $envFile = Join-Path $Root ".env"
    $fromFile = Get-EnvValueFromFile -FilePath $envFile -Key "DESKTOP_WEB_HOST"
    if ($fromFile) { return $fromFile }
    return "127.0.0.1"
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
    return $pids
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$bindHost = Get-DesktopHost -Root $projectRoot
$port = Get-DesktopPort -Root $projectRoot

Write-Host "Desktop UI host: $bindHost"
Write-Host "Desktop UI port: $port"

if (-not $SkipPortCheck) {
    $owners = @(Get-PortOwners -Port $port)
    if ($owners.Length -gt 0) {
        Write-Host ""
        Write-Host "[ERROR] Port $port is occupied. desktop_web_app.py cannot start." -ForegroundColor Red
        Write-Host "Port owners:"
        foreach ($ownerPid in $owners) {
            $proc = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host ("  PID={0}, Name={1}" -f $proc.Id, $proc.ProcessName)
            } else {
                Write-Host ("  PID={0}, Name=<unknown>" -f $ownerPid)
            }
        }
        Write-Host ""
        Write-Host "What to do next:"
        Write-Host "  1) Stop the process and retry"
        Write-Host "  2) Change DESKTOP_WEB_PORT in .env"
        Write-Host "  3) Skip this check: .\start_desktop_ui.ps1 -SkipPortCheck"
        exit 1
    }
}

Write-Host "Starting desktop_web_app.py ..."
python desktop_web_app.py
