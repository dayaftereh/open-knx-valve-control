# KNX043 passive PicoScope 3205D MSO Channel A capture, USB-only.
# READS ONLY: no RP2040 USB command, no KNX TP frame, no motor/GPIO output.
# Use x86 PowerShell to load bundled 32-bit PicoScope6 ps3000a.dll.
[CmdletBinding()]
param(
    [ValidateRange(1000,250000)][int]$Samples=100000,
    [ValidateRange(5,100000)][uint32]$Timebase=625,
    [ValidateRange(1,8)][int]$Repeats=4,
    [ValidateSet(1,10)][int]$ProbeRatio=1,
    [double]$InputRangeVolts=5,
    [ValidateSet("KNX_TX","GND","UNSPECIFIED")][string]$ProbePoint="UNSPECIFIED",
    [string]$OutputDir="C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX043-PicoScope-20261015"
)
$ErrorActionPreference="Stop"
if([IntPtr]::Size -ne 4){throw "Requires x86 PowerShell for PicoScope6 x86 DLL"}
$dll="C:\Program Files (x86)\Pico Technology\PicoScope6\ps3000a.dll"
if(-not(Test-Path -LiteralPath $dll)){throw "Required Pico SDK DLL missing"}
$src=@'
using System;
using System.Runtime.InteropServices;
public static class Knx043Pico3000a {
 const string D="C:\\Program Files (x86)\\Pico Technology\\PicoScope6\\ps3000a.dll";
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aOpenUnit(out short h,IntPtr serial);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aCloseUnit(short h);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aGetUnitInfo(short h,[Out] byte[] b,short length,out short required,int type);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aSetChannel(short h,int channel,short enabled,int coupling,int range,float offset);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aSetSimpleTrigger(short h,short enabled,int channel,short threshold,int direction,uint delay,short ms);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aGetTimebase2(short h,uint timebase,int samples,out float intervalNs,short oversample,out int maxSamples,uint segment);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aRunBlock(short h,int pre,int post,uint timebase,short oversample,IntPtr busy,uint segment,IntPtr ready,IntPtr parameter);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aIsReady(short h,out short ready);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aSetDataBuffer(short h,int channel,IntPtr buffer,int length,uint segment,int mode);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aGetValues(short h,uint start,ref uint count,uint downsample,int mode,uint segment,out short overflow);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aMaximumValue(short h,out short max);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aStop(short h);
}
'@
Add-Type -TypeDefinition $src
function Check([string]$n,[uint32]$status){
    if($status -ne 0){throw "PICO SDK $n error $status"}
}
function Info([int16]$handle,[int]$kind) {
    $bytes=New-Object byte[] 96
    $needed=[int16]0
    Check "unit info $kind" ([Knx043Pico3000a]::ps3000aGetUnitInfo($handle,$bytes,96,[ref]$needed,$kind))
    return [Text.Encoding]::ASCII.GetString($bytes).Trim([char]0)
}
$handle=[int16]0
try {
    Check "open" ([Knx043Pico3000a]::ps3000aOpenUnit([ref]$handle,[IntPtr]::Zero))
    $model=Info $handle 3
    $serial=Info $handle 4
    if($model -notmatch '^3205D'){throw "Unexpected PicoScope model $model"}
    if($InputRangeVolts -eq 0.5){$sdkRange=5}
    elseif($InputRangeVolts -eq 5){$sdkRange=8}
    else{throw "Supported PicoScope input ranges: +/-0.5V and +/-5V"}
    Check "channel A DC +/-$InputRangeVolts V" ([Knx043Pico3000a]::ps3000aSetChannel($handle,0,1,1,$sdkRange,[single]0))
    Check "trigger disabled" ([Knx043Pico3000a]::ps3000aSetSimpleTrigger($handle,0,0,0,2,0,0))
    $maxAdc=[int16]0
    Check "ADC max" ([Knx043Pico3000a]::ps3000aMaximumValue($handle,[ref]$maxAdc))
    if($maxAdc -le 0){throw "Invalid ADC max"}
    $TipScale=[double]($InputRangeVolts*$ProbeRatio)
    $intervalNs=[single]0
    $maxSamples=[int]0
    Check "timebase" ([Knx043Pico3000a]::ps3000aGetTimebase2($handle,$Timebase,$Samples,[ref]$intervalNs,1,[ref]$maxSamples,0))
    if($maxSamples -lt $Samples){throw "Not enough PicoScope memory"}
    [IO.Directory]::CreateDirectory($OutputDir)|Out-Null
    $results=@()
    for($n=1;$n -le $Repeats;$n++){
        $buf=New-Object 'Int16[]' $Samples
        $pin=$null
        try {
            $pin=[Runtime.InteropServices.GCHandle]::Alloc($buf,[Runtime.InteropServices.GCHandleType]::Pinned)
            Check "SetDataBuffer" ([Knx043Pico3000a]::ps3000aSetDataBuffer($handle,0,$pin.AddrOfPinnedObject(),$Samples,0,0))
            $startedUtc=[DateTime]::UtcNow.ToString("o")
            Check "RunBlock" ([Knx043Pico3000a]::ps3000aRunBlock($handle,0,$Samples,$Timebase,1,[IntPtr]::Zero,0,[IntPtr]::Zero,[IntPtr]::Zero))
            $ready=[int16]0
            $deadline=[DateTime]::UtcNow.AddSeconds(12)
            do {
                Start-Sleep -Milliseconds 20
                Check "IsReady" ([Knx043Pico3000a]::ps3000aIsReady($handle,[ref]$ready))
            }while($ready -eq 0 -and [DateTime]::UtcNow -lt $deadline)
            if($ready -eq 0){throw "Capture timed out"}
            $actual=[uint32]$Samples
            $overflow=[int16]0
            Check "GetValues" ([Knx043Pico3000a]::ps3000aGetValues($handle,0,[ref]$actual,1,0,0,[ref]$overflow))
            if($actual -ne $Samples){throw "Partial acquisition returned $actual"}
            $low=[int]32767;$high=[int]-32768;$sum=[double]0;$highCount=0
            for($i=0;$i -lt $actual;$i++){
                $value=[int]$buf[$i]
                if($value -lt $low){$low=$value}
                if($value -gt $high){$high=$value}
                $sum+=$value
                if($value*$TipScale/$maxAdc -gt 0.5){$highCount++}
            }
            $data=New-Object byte[] ($actual*2)
            [Buffer]::BlockCopy($buf,0,$data,0,$actual*2)
            $bin="chA_usb_only_$($n.ToString('00')).i16le"
            [IO.File]::WriteAllBytes([IO.Path]::Combine($OutputDir,$bin),$data)
            $results+=@{
                capture=$n;started_utc=$startedUtc;
                sample_count=$actual;interval_ns=$intervalNs;
                duration_ms=[Math]::Round($actual*$intervalNs/1000000,3);
                minimum_volts=[Math]::Round($low*$TipScale/$maxAdc,5);
                maximum_volts=[Math]::Round($high*$TipScale/$maxAdc,5);
                mean_volts=[Math]::Round($sum*$TipScale/$maxAdc/$actual,5);
                samples_above_0_5_volts=$highCount;overflow=$overflow;
                raw_adc_file=$bin
            }
            [Console]::WriteLine("CAPTURE $n N=$actual duration_ms=$([Math]::Round($actual*$intervalNs/1000000,3)) minV=$([Math]::Round($low*$TipScale/$maxAdc,5)) maxV=$([Math]::Round($high*$TipScale/$maxAdc,5)) meanV=$([Math]::Round($sum*$TipScale/$maxAdc/$actual,5)) above0.5V=$highCount overflow=$overflow")
        }finally {
            if($pin -and $pin.IsAllocated){$pin.Free()}
        }
    }
    $result=@{
       schema="knx043-picoscope-passive-usb-only/v1";
       measured_utc=[DateTime]::UtcNow.ToString("o");
       workstation="LLO Desktop";
       probe_ratio=$ProbeRatio;probe_user_setting=("$($ProbeRatio)x");
       analog_channel="A";coupling="DC";input_range_volts_peak=$InputRangeVolts;tip_range_volts_peak=$TipScale;
       actual_probe_position=("Probe tip on "+$ProbePoint+" according to user; exact location/ground clip not independently observed");
       probe_position_source="operator report (not optically/electrically verified)";
       hardware_model=$model;hardware_serial=$serial;adc_full_scale=$maxAdc;
       scope_driver="ps3000a PicoScope6 x86 bundled DLL";
       trigger="disabled";samples_per_capture=$Samples;timebase=$Timebase;
       captures=$results;
       no_knx_bus_physical_isolation_independently_verified=$false;
       board_firmware_controlled=$false;
       no_reset_or_bootsel_transition_requested_or_measured=$true;
       disclaimer="Voltage describes the user-attached channel A; probe loading, quantization and DC offset may affect weakly biased nets. No KNX bus approval."
    }
    $json=ConvertTo-Json -InputObject $result -Depth 10
    $path=[IO.Path]::Combine($OutputDir,"knx043_picoscope_chA_summary.json")
    [IO.File]::WriteAllText($path,$json+[Environment]::NewLine,[Text.Encoding]::UTF8)
    [Console]::WriteLine("SUMMARY_PATH $path")
}finally {
    if($handle -gt 0){
        [Knx043Pico3000a]::ps3000aStop($handle)|Out-Null
        [Knx043Pico3000a]::ps3000aCloseUnit($handle)|Out-Null
    }
}
