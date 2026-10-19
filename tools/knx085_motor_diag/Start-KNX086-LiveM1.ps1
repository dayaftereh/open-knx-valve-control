# KNX086 manual launcher for KNX084/KNX085 previously proven live KNX+UPDI bench.
# This setup was explicitly tested during KNX084 flash on 2026-10-18.
# No blanket "unplug KNX/UPDI" refusal. Still fails closed if firmware,
# board identity, 3.3 V rail, INA219 or bounded STOP gates fail.
[CmdletBinding()]
param(
    [switch]$Status,
    [switch]$Flash,
    [switch]$Run,
    [ValidateRange(50,250)][int]$DurationMs=150
)
$ErrorActionPreference='Stop'
$python='C:\Users\ll\.platformio\penv\Scripts\python.exe'
$script=Join-Path $PSScriptRoot 'knx086_live_connected.py'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Python not found: $python" }
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) { throw "KNX086 script missing: $script" }
if (@($Status.IsPresent,$Flash.IsPresent,$Run.IsPresent).Where({$_}).Count -gt 1) {
    throw 'Choose only one mode: Status, Flash or Run.'
}
if ($Flash) {
    Write-Host 'KNX086: Verified KNX084 -> KNX085 flash on already tested live bench. No automatic motor pulse.'
    & $python $script flash
} elseif ($Run) {
    Write-Host "KNX086: M1 forward $DurationMs ms; INA219 and power rail must be VALID."
    & $python $script m1 --duration-ms $DurationMs
} else {
    Write-Host 'KNX086: Non-actuating KNX085 status and INA219 temperature/current readout.'
    & $python $script diagnose
}
exit $LASTEXITCODE
