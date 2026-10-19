# OpenKNXValveControl KNX085 - User-operated ONE-SHOT M1 firmware + INA219 bench test.
# DEFAULT is PLAN ONLY. No firmware upload, USB reset, KNX TX or motor motion.
# -Run requires ALL four operator confirmations AND live physical checks.
# Never use while live KNX TP is still connected to the prototype.
[CmdletBinding()]
param(
    [switch]$Run,
    [switch]$ConfirmKnxPhysicallyDisconnected,
    [switch]$ConfirmUpdiPhysicallyDisconnected,
    [switch]$ConfirmUsbOnlyPower,
    [switch]$ConfirmPhysicalPowerCutAvailable,
    [ValidateSet('F','R')][string]$Direction='F',
    [ValidateRange(50,250)][int]$DurationMs=150
)
$ErrorActionPreference='Stop'
$python='C:\Users\ll\.platformio\penv\Scripts\python.exe'
$script=Join-Path $PSScriptRoot 'knx085_one_shot.py'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "KNX085 Python not found: $python"
}
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw "KNX085 one-shot script not found: $script"
}
if (-not $Run) {
    Write-Host 'KNX085 M1 PLAN ONLY: No motor or firmware actions.'
    & $python $script plan
    exit $LASTEXITCODE
}
$all=@(
    $ConfirmKnxPhysicallyDisconnected.IsPresent,
    $ConfirmUpdiPhysicallyDisconnected.IsPresent,
    $ConfirmUsbOnlyPower.IsPresent,
    $ConfirmPhysicalPowerCutAvailable.IsPresent
)
if ($all -contains $false) {
    Write-Host 'KNX085 REFUSED: Physically unplug KNX TP and UPDI/CN1, use USB-only supply and provide an accessible power cut. Then specify all four confirmations.' -ForegroundColor Red
    exit 5
}
$argsList=@(
    $script,'execute',
    '--direction',$Direction,
    '--duration-ms',[string]$DurationMs,
    '--knx-physically-disconnected',
    '--updi-physically-disconnected',
    '--usb-only-power',
    '--physical-power-cut-available'
)
Write-Host 'KNX085 M1 USER-INITIATED TEST: hardware and identity gates will be checked BEFORE firmware flash.'
Write-Host 'No operation will be attempted while CH340/UPDI or KNX bus activity is detected.'
& $python @argsList
exit $LASTEXITCODE
