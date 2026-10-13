# LLO Home reproducible OFFLINE host smoke checks, never uploads or connects a target.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File tools/home_offline_check.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$env:PLATFORMIO_CORE_DIR = 'C:\Users\ll\.platformio'
$python = 'C:\Users\ll\.platformio\penv\Scripts\python.exe'
$pio = 'C:\Users\ll\.platformio\penv\Scripts\pio.exe'
if (!(Test-Path -LiteralPath $python) -or !(Test-Path -LiteralPath $pio)) {
    throw 'Home PlatformIO/Python executable missing'
}
Push-Location $root
try {
    Write-Output '=== KNX028 offline Home smoke tests ==='
    & $python tools/test_usb_flash_controller.py
    if ($LASTEXITCODE -ne 0) { throw 'USB mock tests failed' }
    & $python tools/audit_design.py
    if ($LASTEXITCODE -ne 0) { throw 'Design static audit failed' }
    & $python tools/audit_ash_workflow.py
    if ($LASTEXITCODE -ne 0) { throw 'ASH audit failed' }
    & $pio --version
    if ($LASTEXITCODE -ne 0) { throw 'PlatformIO version probe failed' }
    Write-Output 'PASS: no USB/UPDI/KNX/device upload was used.'
}
finally { Pop-Location }
