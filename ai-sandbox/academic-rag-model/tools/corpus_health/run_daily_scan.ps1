param(
    [Parameter(Mandatory = $true)][string]$Python,
    [Parameter(Mandatory = $true)][string]$Config,
    [Parameter(Mandatory = $true)][string]$LogDirectory,
    [string]$StateDirectory,
    [switch]$OncePerDay,
    [switch]$Notify
)

$ErrorActionPreference = 'Stop'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$exitCode = 2
$logPath = $null

function Resolve-ConfiguredRoot([string]$configBase, [string]$value) {
    if ([System.IO.Path]::IsPathRooted($value)) {
        return [System.IO.Path]::GetFullPath($value)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $configBase $value))
}

function Assert-OutsideCorpus([string]$candidate, [string[]]$roots) {
    foreach ($root in $roots) {
        $root = $root.TrimEnd('\', '/')
        if ($candidate.Equals($root, [System.StringComparison]::OrdinalIgnoreCase) -or
            $candidate.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar,
                                  [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "scheduled scan output/state must be outside corpus root $root"
        }
    }
}

function Test-ScannedToday([string]$logRoot) {
    # Complete scan already logged today (exit=0 line): a logon trigger fires on every sign-in.
    $prefix = 'corpus-health-' + (Get-Date -Format 'yyyyMMdd') + '-*.log'
    foreach ($log in Get-ChildItem -Path (Join-Path ([WildcardPattern]::Escape($logRoot)) $prefix) -ErrorAction SilentlyContinue) {
        if ((Get-Content -LiteralPath $log.FullName -Raw -ErrorAction SilentlyContinue) -match 'finished=\S+ exit=0\b') {
            return $true
        }
    }
    return $false
}

function Get-ScanAlerts([string]$reportPath, [int]$code) {
    # Findings alone never change the exit code, so surface the ones that mean "paths drifted".
    $alerts = @()
    if ($code -ne 0) { $alerts += "scan exited $code (incomplete or configuration error); see the log" }
    if (Test-Path -LiteralPath $reportPath) {
        $report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($notice in @($report.notices)) {
            if ($notice -match 'exact moves waiting|need review') { $alerts += $notice }
        }
        foreach ($warning in @($report.warnings)) { $alerts += "WARNING: $warning" }
        foreach ($kind in 'duplicate_hub_id', 'relink', 'orphan_card') {
            $count = @($report.findings | Where-Object { $_.kind -eq $kind }).Count
            if ($count -gt 0) { $alerts += "$count $kind finding(s)" }
        }
    }
    elseif ($code -eq 0) { $alerts += 'scan reported success but wrote no report' }
    return $alerts
}

function Show-Alerts([string]$logRoot, [string[]]$alerts, [bool]$notify) {
    $alertFile = Join-Path $logRoot 'latest-alerts.txt'
    if ($alerts.Count -eq 0) {
        Remove-Item -LiteralPath $alertFile -ErrorAction SilentlyContinue
        return
    }
    $text = "corpus-health $(Get-Date -Format o)`n" + ($alerts -join "`n") + "`n"
    [System.IO.File]::WriteAllText($alertFile, $text, $utf8)
    if ($notify) {
        try {
            Add-Type -AssemblyName System.Windows.Forms
            $icon = New-Object System.Windows.Forms.NotifyIcon
            $icon.Icon = [System.Drawing.SystemIcons]::Warning
            $icon.Visible = $true
            $icon.ShowBalloonTip(15000, 'Corpus health needs attention', ($alerts -join "`n"), 'Warning')
            Start-Sleep -Seconds 16
            $icon.Dispose()
        }
        catch { }
    }
}

try {
    $pythonPath = (Resolve-Path -LiteralPath $Python).Path
    $configPath = (Resolve-Path -LiteralPath $Config).Path
    $configData = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    $configBase = Split-Path -Parent $configPath
    $corpusRoots = @((Resolve-ConfiguredRoot $configBase $configData.academic_hub_root))
    if ($configData.academic_notes_root) {
        $corpusRoots += Resolve-ConfiguredRoot $configBase $configData.academic_notes_root
    }
    $logRoot = [System.IO.Path]::GetFullPath($LogDirectory)
    Assert-OutsideCorpus $logRoot $corpusRoots
    if ($StateDirectory) {
        Assert-OutsideCorpus ([System.IO.Path]::GetFullPath($StateDirectory)) $corpusRoots
    }
    [System.IO.Directory]::CreateDirectory($logRoot) | Out-Null
    if ($OncePerDay -and (Test-ScannedToday $logRoot)) { exit 0 }
    $reportPath = Join-Path $logRoot "corpus-health-$stamp.json"
    $logPath = Join-Path $logRoot "corpus-health-$stamp.log"
    $packageRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path

    $arguments = @('-X', 'utf8', '-m', 'tools.corpus_health', 'scan',
                   '--config', $configPath, '--format', 'json', '--output', $reportPath)
    if ($StateDirectory) {
        $arguments += @('--state-dir', [System.IO.Path]::GetFullPath($StateDirectory))
    }
    Push-Location -LiteralPath $packageRoot
    try {
        & $pythonPath @arguments 1> $null 2> $logPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    Show-Alerts $logRoot (Get-ScanAlerts $reportPath $exitCode) $Notify.IsPresent
    [System.IO.File]::AppendAllText(
        $logPath,
        "finished=$(Get-Date -Format o) exit=$exitCode report=$reportPath`n",
        $utf8
    )
}
catch {
    $message = "finished=$(Get-Date -Format o) exit=2 error=$($_.Exception.Message)`n"
    if ($logPath) {
        [System.IO.File]::AppendAllText($logPath, $message, $utf8)
    }
    else {
        [Console]::Error.WriteLine($message)
    }
    $exitCode = 2
}

exit $exitCode
