# LLO Home/Desktop reproducible software-only QA for OpenKNXValveControl (KNX028).
# Usage:
# powershell -NoProfile -ExecutionPolicy Bypass -File tools/home_offline_check.ps1
# powershell -NoProfile -ExecutionPolicy Bypass -File tools/home_offline_check.ps1 -Native
# powershell -NoProfile -ExecutionPolicy Bypass -File tools/home_offline_check.ps1 -Native -ControllerBuild
# No USB/UPDI/KNX/ETS/device upload or real motor actions.
param(
    [switch]$Native,
    [switch]$ControllerBuild
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
# Resolve the PlatformIO environment on either LLO Home or LLO Desktop.
$platformioRoot = $null
foreach ($candidate in @('C:\Users\ll\.platformio', 'C:\Users\LLO\.platformio')) {
    $candidatePy = Join-Path $candidate 'penv\Scripts\python.exe'
    $candidatePio = Join-Path $candidate 'penv\Scripts\pio.exe'
    if ((Test-Path -LiteralPath $candidatePy) -and (Test-Path -LiteralPath $candidatePio)) {
        $platformioRoot = $candidate
        break
    }
}
if ($null -eq $platformioRoot) { throw 'LLO PlatformIO/Python executables are missing' }
$env:PLATFORMIO_CORE_DIR = $platformioRoot
# Git is invoked by the SYSTEM agent on a repository owned by user 'll'.
# This grants trust to this process and its children only, not globally.
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'safe.directory'
$env:GIT_CONFIG_VALUE_0 = $root.Replace('\', '/')
$python = Join-Path $platformioRoot 'penv\Scripts\python.exe'
$pio = Join-Path $platformioRoot 'penv\Scripts\pio.exe'
Push-Location $root
try {
    function Run-PythonTest([string]$script) {
        Write-Output "RUN $script"
        & $python $script
        if ($LASTEXITCODE -ne 0) { throw "FAIL $script exit $LASTEXITCODE" }
    }
    Write-Output '=== OpenKNXValveControl LLO Home OFFLINE smoke tests ==='
    foreach ($script in @('tools/test_usb_flash_controller.py',
                          'tools/audit_design.py',
                          'tools/audit_knx026_hmi_scope.py',
                          'tools/audit_knx027_usb_flash_scope.py',
                          'tools/test_knx029_bringup_kit.py',
                          'tools/audit_knx029_bringup_scope.py',
                          'tools/test_knx030_passive_inventory.py',
                          'tools/audit_knx030_passive_scope.py',
                          'tools/test_knx031_uart_trace.py',
                          'tools/audit_knx031_uart_scope.py',
                          'tools/audit_knx032_replay_scope.py',
                          'tools/audit_knx033_asbuilt.py',
                          'tools/test_knx033_asbuilt_gate.py',
                          'tools/audit_knx034_usb_only.py',
                          'tools/test_knx034_usb_only.py',
                          'tools/audit_knx035_stknx_tx.py',
                          'tools/test_knx035_tx_hazard.py',
                          'tools/test_knx036_usb_diag.py',
                          'tools/test_knx037_rp_usb_workflow.py',
                          'tools/test_knx038_updi_readiness.py',
                          'tools/test_knx039_live_readback.py',
                          'tools/audit_ash_workflow.py')) {
        Run-PythonTest $script
    }
    & $pio --version
    if ($LASTEXITCODE -ne 0) { throw 'PlatformIO version probe failed' }

    if ($Native) {
        $compiler = 'C:\_myspace\Tools\winlibs-gcc-16.2.0-ucrt\mingw64\bin\g++.exe'
        if (!(Test-Path -LiteralPath $compiler)) {
            throw "Missing host C++ compiler: $compiler. Run tools/install_home_host_compiler.ps1 first."
        }
        $env:CXX = $compiler
        Write-Output "CXX=$compiler"
        foreach ($script in @(
            'tools/test_knx008_zones.py',
            'tools/test_temperature_sampler.py',
            'tools/test_temperature_uart.py',
            'tools/test_temperature_telemetry.py',
            'tools/test_room_pi_controller.py',
            'tools/test_motor_queue_simulator.py',
            'tools/test_knx021_end_to_end.py',
            'tools/test_knx023_room_control_runtime.py',
            'tools/test_knx024_room_dpt_adapter.py',
            'tools/test_knx025_fault_supervisor.py',
            'tools/test_knx026_hmi_diagnostics.py',
            'tools/test_knx032_replay_contract.py'
        )) { Run-PythonTest $script }
        Write-Output 'PASS all twelve native-script groups (each can contain multiple C++ binaries)'
    }

    if ($ControllerBuild) {
        $producer = 'C:\_myspace\Tools\OpenKNXproducer-3.12.2\tools\Windows\OpenKNXproducer-x64.exe'
        if (!(Test-Path -LiteralPath $producer)) { throw "Missing OpenKNXproducer: $producer" }
        $env:PIO_EXECUTABLE = $pio
        $env:OPENKNXPRODUCER_EXECUTABLE = $producer
        $env:OPENKNX_PRODUCER = $producer
        & $python tools/usb_flash_controller.py build
        if ($LASTEXITCODE -ne 0) { throw 'Isolated RP2040 firmware build failed' }
    }
    Write-Output 'PASS: Home offline checks complete. No USB reset or target flashing performed.'
}
finally { Pop-Location }
