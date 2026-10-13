# KNX030: strictly passive Windows operating-system metadata inventory.
# Never opens a device handle, serial COM port, KNX/IP socket, or USB volume file.
# No picotool, pymcuprog, BOOTSEL reset, device programming or motor operation.
$ErrorActionPreference = 'Stop'
# Force UTF-8 for a redirected PowerShell->Python stdout pipe, even on CP1252 hosts.
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding

$present = @(
    Get-PnpDevice -PresentOnly -ErrorAction Stop |
        Where-Object {
            $_.Class -eq 'Ports' -or
            $_.InstanceId -match '^(USB\\VID_|USBSTOR\\|FTDIBUS\\)' -or
            $_.FriendlyName -match '(RPI-RP2|RP2040|Raspberry Pi Pico|CH340|CH341|USB[- ]?Serial|CMSIS[- ]?DAP|UPDI)'
        } |
        ForEach-Object {
            [pscustomobject]@{
                instance_id = [string]$_.InstanceId
                display_name = [string]$_.FriendlyName
                class_name = [string]$_.Class
                status = [string]$_.Status
            }
        }
)
$volumes = @(
    Get-Volume -ErrorAction Stop |
        Where-Object { $_.FileSystemLabel -eq 'RPI-RP2' } |
        ForEach-Object {
            [pscustomobject]@{
                label = [string]$_.FileSystemLabel
                drive_letter = [string]$_.DriveLetter
                file_system = [string]$_.FileSystem
            }
        }
)
$adapters = @(
    Get-NetAdapter -ErrorAction Stop |
        ForEach-Object {
            [pscustomobject]@{
                name = [string]$_.Name
                description = [string]$_.InterfaceDescription
                status = [string]$_.Status
            }
        }
)
[pscustomobject]@{
    source_kind = 'local_os_metadata_only'
    usb_and_ports = $present
    rp2_volumes = $volumes
    local_network_adapters = $adapters
} | ConvertTo-Json -Depth 5 -Compress
