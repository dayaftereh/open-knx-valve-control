# KNX043 passive simultaneous KNX_TX and USB5V dual-channel capture.
# NO automatic board reset, KNX telegram, motor command, GPIO write, flash, siggen, or external power.
# Run using x86 Windows PowerShell; bundled PicoScope6 ps3000a.dll is x86.
[CmdletBinding()]
param(
    [ValidateSet("Test","Arm")][string]$Mode="Test",
    [ValidateRange(1.0,7.0)][double]$TriggerTipVolts=2.5,
    [ValidateSet(1,10)][int]$ProbeRatioB=10,
    [ValidateSet(1,5,10)][int]$BInputRangeVolts=10,
    [ValidateRange(10,3600)][int]$MaxWaitSeconds=1800,
    [ValidateRange(100,2500)][uint32]$Timebase=1000,
    [ValidateRange(10000,150000)][int]$PreSamples=100000,
    [ValidateRange(20000,400000)][int]$PostSamples=400000,
    [string]$OutputDir="C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX043-PicoScope-20261015\reset_trigger_test",
    [string]$ExpectedScopeSerial="GX118/0047",
    [string]$ExpectedBoardUsbSerial="E464401787522D33",
    [string]$BoardComPort="COM7",
    [switch]$PhysicalProbesVerified
)
$ErrorActionPreference="Stop"
if($Mode -eq "Arm" -and -not $PhysicalProbesVerified){throw "Refusing to arm: operator must confirm CH A and B x10, B USB 5V, common PCB GND and KNX/motors disconnected"}
if([IntPtr]::Size -ne 4){throw "Requires x86 Windows PowerShell for PicoSDK x86 library"}
$lib="C:\Program Files (x86)\Pico Technology\PicoScope6\ps3000a.dll"
if(-not(Test-Path -LiteralPath $lib)){throw "Missing PicoSDK x86 DLL"}
if(Test-Path -LiteralPath $OutputDir){throw "Refusing to reuse a previous capture directory: $OutputDir"}
[IO.Directory]::CreateDirectory($OutputDir)|Out-Null
$stateFile=[IO.Path]::Combine($OutputDir,"capture_state.json")
$stopFile=[IO.Path]::Combine($OutputDir,"stop-request.txt")
function State([string]$status,[object]$info) {
    $d=@{status=$status;updated_utc=[DateTime]::UtcNow.ToString("o");mode=$Mode;
        scope="PicoScope 3205D MSO";probe_ratio_A=10;probe_ratio_B=$ProbeRatioB;channels="A:KNX_TX B:USB5V";coupling="DC";
        A_tip_range_volts=5;B_tip_range_volts=($ProbeRatioB*$BInputRangeVolts);
        threshold_tip_volts=$TriggerTipVolts;trigger_channel="B";
        current_capture_dir=$OutputDir;
        board_com=$BoardComPort;
        board_usb_serial_expected=$ExpectedBoardUsbSerial;
        user_reported_probe_position="A:JMP3 pad2 KNX_TX x10; B:USB 5V board pad x$ProbeRatioB; common PCB GND per user, not independently verified";
        electrical_condition="USB only per user; KNX bus/motors unconnected per prior user instructions, not independently verified";
        info=$info}
    [IO.File]::WriteAllText($stateFile,((ConvertTo-Json -InputObject $d -Depth 10)+[Environment]::NewLine),[Text.Encoding]::UTF8)
    [Console]::WriteLine("STATE "+$status+" "+([DateTime]::UtcNow.ToString("o")))
}
State "STARTING" @{notes="Dual scope read-only, do not unplug/replug board USB until ARMED; test has no board commands"}
$csharp=@'
using System;
using System.Runtime.InteropServices;
public static class Knx043ResetScope {
 const string D="C:\\Program Files (x86)\\Pico Technology\\PicoScope6\\ps3000a.dll";
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aOpenUnit(out short h,IntPtr serial);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aCloseUnit(short h);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aGetUnitInfo(short h,[Out] byte[] b,short length,out short required,int type);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aSetChannel(short h,int channel,short enabled,int coupling,int range,float offset);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aSetSimpleTrigger(short h,short enabled,int channel,short threshold,int direction,uint delay,short autoTriggerMs);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aGetTimebase2(short h,uint timebase,int samples,out float intervalNs,short oversample,out int maxSamples,uint segmentIndex);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aSetDataBuffer(short h,int channel,IntPtr data,int length,uint segmentIndex,int mode);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aRunBlock(short h,int preTriggerSamples,int postTriggerSamples,uint timebase,short oversample,IntPtr timeIndisposed,uint segmentIndex,IntPtr callback,IntPtr parameter);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aIsReady(short h,out short ready);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aGetValues(short h,uint start,ref uint count,uint downsample,int mode,uint segmentIndex,out short overflow);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aMaximumValue(short h,out short adcMax);
 [DllImport(D,CallingConvention=CallingConvention.Cdecl)] public static extern uint ps3000aStop(short h);
}
'@
Add-Type -TypeDefinition $csharp
function Check([string]$name,[uint32]$code) {if($code -ne 0){throw "PicoSDK $name status=$code"}}
function UnitInfo([int16]$h,[int]$which) {
    $b=New-Object byte[] 96;$need=[int16]0
    Check "GetUnitInfo $which" ([Knx043ResetScope]::ps3000aGetUnitInfo($h,$b,96,[ref]$need,$which))
    return [Text.Encoding]::ASCII.GetString($b).Trim([char]0)
}
$handle=[int16]0
$pinA=$null
$pinB=$null
$durationMs=0
$usbLog=New-Object System.Collections.ArrayList
$startedAt=[DateTime]::UtcNow
try {
    Check "OpenUnit" ([Knx043ResetScope]::ps3000aOpenUnit([ref]$handle,[IntPtr]::Zero))
    $model=UnitInfo $handle 3
    $serial=UnitInfo $handle 4
    if($model -notmatch '^3205D'){throw "Unexpected PicoScope model: $model"}
    if($serial -ne $ExpectedScopeSerial){throw "Unexpected PicoScope USB serial: $serial"}
    $total=$PreSamples+$PostSamples
    if($total -gt 500000){throw "Refusing oversized capture"}
    $maxAdc=[int16]0
    Check "MaximumValue" ([Knx043ResetScope]::ps3000aMaximumValue($handle,[ref]$maxAdc))
    if($maxAdc -le 0){throw "Invalid PicoSDK ADC max"}
    Check "ChannelA_KNX_TX_halfVolt" ([Knx043ResetScope]::ps3000aSetChannel($handle,0,1,1,5,[single]0))
    if($BInputRangeVolts -eq 1){$bSdkRange=6}
    elseif($BInputRangeVolts -eq 5){$bSdkRange=8}
    elseif($BInputRangeVolts -eq 10){$bSdkRange=9}
    else{throw "Invalid Pico B scope input range"}
    $bTipFullscale=[double]($BInputRangeVolts*$ProbeRatioB)
    Check "ChannelB_USB_5V_DC_range_$BInputRangeVolts" ([Knx043ResetScope]::ps3000aSetChannel($handle,1,1,1,$bSdkRange,[single]0))
    $intervalNs=[single]0;$maxSamples=[int]0
    Check "GetTimebase2" ([Knx043ResetScope]::ps3000aGetTimebase2($handle,$Timebase,$total,[ref]$intervalNs,1,[ref]$maxSamples,0))
    if($maxSamples -lt $total){throw "Not enough PicoScope memory for $total samples"}
    $durationMs=$intervalNs*$total/1000000
    $bufA=New-Object 'Int16[]' $total
    $bufB=New-Object 'Int16[]' $total
    $pinA=[Runtime.InteropServices.GCHandle]::Alloc($bufA,[Runtime.InteropServices.GCHandleType]::Pinned)
    $pinB=[Runtime.InteropServices.GCHandle]::Alloc($bufB,[Runtime.InteropServices.GCHandleType]::Pinned)
    Check "SetDataBufferA" ([Knx043ResetScope]::ps3000aSetDataBuffer($handle,0,$pinA.AddrOfPinnedObject(),$total,0,0))
    Check "SetDataBufferB" ([Knx043ResetScope]::ps3000aSetDataBuffer($handle,1,$pinB.AddrOfPinnedObject(),$total,0,0))
    $thresholdAdc=[int16][Math]::Round($TriggerTipVolts/$bTipFullscale*$maxAdc)
    if($Mode -eq "Arm") {
        # Physical CH B 5V rise at 2.5V tip; no synthetic auto-trigger.
        # Channel A KNX_TX sampled simultaneously with Channel B.
        Check "HardwareTrigger_ChannelB_USB5V" ([Knx043ResetScope]::ps3000aSetSimpleTrigger($handle,1,1,$thresholdAdc,2,0,0))
    }else{
        Check "DisableTriggerForPipelineSelfTest" ([Knx043ResetScope]::ps3000aSetSimpleTrigger($handle,0,0,0,2,0,0))
    }
    Check "RunBlock" ([Knx043ResetScope]::ps3000aRunBlock($handle,$PreSamples,$PostSamples,$Timebase,1,[IntPtr]::Zero,0,[IntPtr]::Zero,[IntPtr]::Zero))
    $armed=[DateTime]::UtcNow
    $info=@{armed_utc=$armed.ToString("o");scope_model=$model;scope_serial=$serial;
        ADC_max=$maxAdc;trigger_threshold_ADC=$thresholdAdc;
        sample_interval_ns=$intervalNs;pretrigger_samples=$PreSamples;posttrigger_samples=$PostSamples;
        acquisition_window_ms=[Math]::Round($durationMs,3);trigger_channel="B";trigger_mode= $(if($Mode -eq "Arm"){"B USB 5V hardware rising, no auto-trigger"}else{"disabled self test"});
        trigger_delay_samples=0;reset_initiated_by_agent=$false}
    State $(if($Mode -eq "Arm"){"ARMED"}else{"TEST_CAPTURING"}) $info
    $ready=[int16]0
    $lastUsb=$null
    $poll=0
    do{
        Start-Sleep -Milliseconds 75
        Check "IsReady" ([Knx043ResetScope]::ps3000aIsReady($handle,[ref]$ready))
        # Device enumeration sampling only; do NOT open or command RP2040 serial port.
        $poll++
        if($poll%2 -eq 0) {
            try{
                $names=[System.IO.Ports.SerialPort]::GetPortNames()
                $present=($names -contains $BoardComPort)
                if($null -eq $lastUsb -or $lastUsb -ne $present){
                    [void]$usbLog.Add(@{utc=[DateTime]::UtcNow.ToString("o");com_port_visible=$present})
                    $lastUsb=$present
                    [Console]::WriteLine("USB_PORT "+$BoardComPort+" visible="+$present)
                }
            }catch {
                # OS COM enumeration not mandatory for the PicoScope trigger capture.
            }
        }
        if($ready -ne 0){break}
        if(Test-Path -LiteralPath $stopFile){
            State "STOP_REQUESTED_NO_TRIGGER" @{scope=$info;usb_events=@($usbLog);board_reset_not_independently_confirmed=$true}
            exit 0
        }
        if(([DateTime]::UtcNow-$armed).TotalSeconds -ge $MaxWaitSeconds){
            State "TIMEOUT_NO_TRIGGER" @{scope=$info;usb_events=@($usbLog);physical_reset_not_independently_confirmed=$true}
            exit 0
        }
    }while($true)
    $actual=[uint32]$total;$overflow=[int16]0
    Check "GetValues" ([Knx043ResetScope]::ps3000aGetValues($handle,0,[ref]$actual,1,0,0,[ref]$overflow))
    if($actual -ne $total){throw "PicoSDK incomplete triggered capture: $actual of $total"}
    $fileA=[IO.Path]::Combine($OutputDir,"chA_KNX_TX_i16le.bin")
    $fileB=[IO.Path]::Combine($OutputDir,"chB_USB_5V_i16le.bin")
    $dataA=New-Object byte[] ($total*2)
    $dataB=New-Object byte[] ($total*2)
    [Buffer]::BlockCopy($bufA,0,$dataA,0,$dataA.Length)
    [Buffer]::BlockCopy($bufB,0,$dataB,0,$dataB.Length)
    [IO.File]::WriteAllBytes($fileA,$dataA)
    [IO.File]::WriteAllBytes($fileB,$dataB)
    $hashA=(Get-FileHash -Algorithm SHA256 -LiteralPath $fileA).Hash.ToLowerInvariant()
    $hashB=(Get-FileHash -Algorithm SHA256 -LiteralPath $fileB).Hash.ToLowerInvariant()
    $aMin=[int]32767;$aMax=[int]-32768;$bMin=[int]32767;$bMax=[int]-32768
    $aSum=[double]0;$bSum=[double]0;$aAbove05=0
    $bRiseCount=0;$bFallCount=0;$powerHigh=$false
    $powerChanges=New-Object System.Collections.ArrayList
    for($i=0;$i -lt $total;$i++){
        $a=[int]$bufA[$i];$b=[int]$bufB[$i]
        if($a -lt $aMin){$aMin=$a};if($a -gt $aMax){$aMax=$a}
        if($b -lt $bMin){$bMin=$b};if($b -gt $bMax){$bMax=$b}
        $aSum+=$a;$bSum+=$b
        $av=$a*5.0/$maxAdc;$bv=$b*$bTipFullscale/$maxAdc
        if($av -gt 0.5){$aAbove05++}
        # Hysteresis to ignore minor jitter on the USB5V rail.
        if((-not $powerHigh) -and $bv -gt 3.0){
            $powerHigh=$true;$bRiseCount++
            if($powerChanges.Count -lt 100){[void]$powerChanges.Add(@{event="USB5V_HIGH";at_sample=$i;relative_to_trigger_ms=[Math]::Round(($i-$PreSamples)*$intervalNs/1000000,3);value_v=[Math]::Round($bv,3)})}
        }elseif($powerHigh -and $bv -lt 2.0){
            $powerHigh=$false;$bFallCount++
            if($powerChanges.Count -lt 100){[void]$powerChanges.Add(@{event="USB5V_LOW";at_sample=$i;relative_to_trigger_ms=[Math]::Round(($i-$PreSamples)*$intervalNs/1000000,3);value_v=[Math]::Round($bv,3)})}
        }
    }
    $result=@{
        schema="knx043-dual-USB5V-KNXTX-capture/v1"
        mode=$Mode
        status=$(if($Mode -eq "Test"){"TEST_PIPELINE_COMPLETED"}else{"TRIGGERED_CAPTURE_COMPLETED"})
        captured_utc=[DateTime]::UtcNow.ToString("o")
        armed_utc=$armed.ToString("o")
        hardware_model=$model
        hardware_serial=$serial
        trigger_channel="B_USB_5V"
        trigger_tip_threshold_v=$TriggerTipVolts
        trigger_ADC=$thresholdAdc
        trigger_direction="rising"
        auto_trigger_enabled=$false
        sample_interval_ns=$intervalNs
        sample_count=$actual
        pretrigger_samples=$PreSamples
        posttrigger_samples=$PostSamples
        time_window_ms=[Math]::Round($durationMs,4)
        physical_probes_confirmed_by_user=([bool]$PhysicalProbesVerified)
        physical_probes_independently_inspected_by_agent=$false
        channel_A=@{signal="KNX_TX at JMP3 pad2 per user";scope_range_v_peak=0.5;probe_ratio=10;tip_range_v_peak=5;
            minimum_tip_v=[Math]::Round($aMin*5.0/$maxAdc,6);maximum_tip_v=[Math]::Round($aMax*5.0/$maxAdc,6);
            mean_tip_v_uncorrected=[Math]::Round($aSum/$total*5.0/$maxAdc,6);
            samples_above_0p5_tip_v=$aAbove05;raw_file=$fileA;sha256=$hashA}
        channel_B=@{signal="USB VBUS +5V at board per user";scope_range_v_peak=$BInputRangeVolts;probe_ratio=$ProbeRatioB;tip_range_v_peak=$bTipFullscale;
            minimum_tip_v=[Math]::Round($bMin*$bTipFullscale/$maxAdc,6);maximum_tip_v=[Math]::Round($bMax*$bTipFullscale/$maxAdc,6);
            mean_tip_v_uncorrected=[Math]::Round($bSum/$total*$bTipFullscale/$maxAdc,6);
            high_edges_above_3V=$bRiseCount;low_edges_below_2V=$bFallCount;
            voltage_transition_events=@($powerChanges);raw_file=$fileB;sha256=$hashB}
        USB_COM_enumeration_events=@($usbLog)
        no_firmware_or_KNX_bus_or_motor_commands_by_agent=$true
        caution="Probe attenuation must match physical switch (B ratio recorded separately). Ground should be shared PCB GND, never KNX TP A/B. Hardware CH B trigger records A and B synchronously. First capture may finish before subsequent contact bounce; no KNX bus authorization."
    }
    $resultPath=[IO.Path]::Combine($OutputDir,"dual_capture_result.json")
    [IO.File]::WriteAllText($resultPath,((ConvertTo-Json -InputObject $result -Depth 12)+[Environment]::NewLine),[Text.Encoding]::UTF8)
    State $result.status $result
    [Console]::WriteLine("DUAL_CAPTURE_DONE A_TX_peakV="+$result.channel_A.maximum_tip_v+" B_USB5V_peakV="+$result.channel_B.maximum_tip_v+" B_rises="+$bRiseCount+" B_falls="+$bFallCount+" duration_ms="+[Math]::Round($durationMs,3))
    [Console]::WriteLine("RAW_A "+$fileA)
    [Console]::WriteLine("RAW_B "+$fileB)
}catch{
    $errorString=$_.Exception.Message
    try{State "ERROR" @{error=$errorString;reset_not_commanded=$true}}catch{}
    [Console]::Error.WriteLine("PICOSCOPE_CAPTURE_ERROR "+$errorString)
    exit 2
}finally{
    if($pinA -and $pinA.IsAllocated){$pinA.Free()}
    if($pinB -and $pinB.IsAllocated){$pinB.Free()}
    if($handle -gt 0){
        [Knx043ResetScope]::ps3000aStop($handle)|Out-Null
        [Knx043ResetScope]::ps3000aCloseUnit($handle)|Out-Null
    }
}
