# KNX085 M1 main launcher: current live test setup with removed R17
# and documented KNX076/081/084 successful connected-bus flashing.
# KNX and UPDI are no longer blanket blockers; the INA219 baseline
# and 3.3 V supply still must pass before M1 may move.
[CmdletBinding()]
param(
    [switch]$Run,
    [switch]$Flash,
    [ValidateRange(50,250)][int]$DurationMs=150
)
$ErrorActionPreference='Stop'
$next=Join-Path $PSScriptRoot 'Start-KNX086-LiveM1.ps1'
if (-not (Test-Path -LiteralPath $next -PathType Leaf)) {
    throw "KNX086 connected bench launcher missing: $next"
}
if ($Run -and $Flash) {throw 'Choose either Run or Flash, not both.'}
if ($Run) {
    & $next -Run -DurationMs $DurationMs
} elseif ($Flash) {
    & $next -Flash
} else {
    & $next -Status
}
exit $LASTEXITCODE
