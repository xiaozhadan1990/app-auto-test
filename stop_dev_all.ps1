Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Stop-PortOwners {
    param(
        [int]$Port,
        [string]$Label
    )
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

    $owners = @($pids)
    if ($owners.Length -eq 0) {
        Write-Host "[$Label] Port $Port has no listener."
        return
    }

    Write-Host "[$Label] Stopping listeners on port $Port ..."
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

Stop-PortOwners -Port 17999 -Label "backend"
Stop-PortOwners -Port 5173 -Label "frontend"
Stop-PortOwners -Port 5174 -Label "frontend-alt"

Write-Host "Done."
