param(
    [Parameter(Mandatory = $true)][string]$Python,
    [Parameter(Mandatory = $true)][string]$Config,
    [Parameter(Mandatory = $true)][string]$LogDirectory,
    [string]$StateDirectory
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
