# KNX043 passive PicoScope hardware rising-edge capture for externally operated RP2040 RUN/RESET.
# NO automatic board reset, KNX telegram, motor command, GPIO write, flash, siggen, or external power.
# Run using x86 Windows PowerShell; bundled PicoScope6 ps3000a.dll is x86.
[CmdletBinding()]
param(
    [ValidateSet("Test","Arm")][string]$Mode="Test",
    [ValidateRange(0.2,1.5)][double]$TriggerTipVolts=0.35,
    [ValidateRange(10,3600)][int]$MaxWaitSeconds=1800,
    [ValidateRange(100,2500)][uint32]$Timebase=250,
    [ValidateRange(10000,150000)][int]$PreSamples=100000,
    [ValidateRange(20000,350000)][int]$PostSamples=300000,
    [string]$OutputDir="C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX043-PicoScope-20261015\reset_trigger_test",
    [string]$ExpectedScopeSerial="GX118/0047",
    [string]$ExpectedBoardUsbSerial="E464401787522D33",
    [string]$BoardComPort="COM7"
)
$ErrorActionPreference="Stop"
if([IntPtr]::Size -ne 4){throw "Requires x86 Windows PowerShell for PicoSDK x86 library"}
$lib="C:\Program Files (x86)\Pico Technology\PicoScope6\ps3000a.dll"
if(-not(Test-Path -LiteralPath $lib)){throw "Missing PicoSDK x86 DLL"}
if(Test-Path -LiteralPath $OutputDir){throw "Refusing to reuse a previous capture directory: $OutputDir"}
[IO.Directory]::CreateDirectory($OutputDir)|Out-Null
$stateFile=[IO.Path]::Combine($OutputDir,"capture_state.json")
$stopFile=[IO.Path]::Combine($OutputDir,"stop-request.txt")
function State([string]$status,[object]$info) {
    $d=@{status=$status;updated_utc=[DateTime]::UtcNow.ToString("o");mode=$Mode;
        scope="PicoScope 3205D MSO";probe_ratio=10;channel="A";coupling="DC";
        input_fullscale_volts=0.5;tip_fullscale_volts=5;
        threshold_tip_volts=$TriggerTipVolts;
        current_capture_dir=$OutputDir;
        board_com=$BoardComPort;
        board_usb_serial_expected=$ExpectedBoardUsbSerial;
        user_reported_probe_position="KNX_TX at JMP3 pad 2; independently_unverified";
        electrical_condition="USB only per user; KNX bus/motors unconnected per prior user instructions, not independently verified";
        info=$info}
    [IO.File]::WriteAllText($stateFile,((ConvertTo-Json -InputObject $d -Depth 10)+[Environment]::NewLine),[Text.Encoding]::UTF8)
    [Console]::WriteLine("STATE "+$status+" "+([DateTime]::UtcNow.ToString("o")))
}
State "STARTING" @{notes="PicoScope only; do not operate reset until ARMED is verified"}
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
$pin=$null
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
    Check "ChannelA_DC_halfVolt" ([Knx043ResetScope]::ps3000aSetChannel($handle,0,1,1,5,[single]0))
    $intervalNs=[single]0;$maxSamples=[int]0
    Check "GetTimebase2" ([Knx043ResetScope]::ps3000aGetTimebase2($handle,$Timebase,$total,[ref]$intervalNs,1,[ref]$maxSamples,0))
    if($maxSamples -lt $total){throw "Not enough PicoScope memory for $total samples"}
    $durationMs=$intervalNs*$total/1000000
    $buf=New-Object 'Int16[]' $total
    $pin=[Runtime.InteropServices.GCHandle]::Alloc($buf,[Runtime.InteropServices.GCHandleType]::Pinned)
    Check "SetDataBuffer" ([Knx043ResetScope]::ps3000aSetDataBuffer($handle,0,$pin.AddrOfPinnedObject(),$total,0,0))
    $thresholdAdc=[int16][Math]::Round($TriggerTipVolts/5.0*$maxAdc)
    if($Mode -eq "Arm") {
        # Simple positive-edge hardware trigger: CH A 0.35 V AT THE 10x PROBE TIP.
        # autoTriggerMs=0 => NO synthetic auto-trigger. Only a real threshold crossing fills block.
        Check "SetHardwareRisingTrigger" ([Knx043ResetScope]::ps3000aSetSimpleTrigger($handle,1,0,$thresholdAdc,2,0,0))
    }else{
        Check "DisableTriggerForPipelineSelfTest" ([Knx043ResetScope]::ps3000aSetSimpleTrigger($handle,0,0,0,2,0,0))
    }
    Check "RunBlock" ([Knx043ResetScope]::ps3000aRunBlock($handle,$PreSamples,$PostSamples,$Timebase,1,[IntPtr]::Zero,0,[IntPtr]::Zero,[IntPtr]::Zero))
    $armed=[DateTime]::UtcNow
    $info=@{armed_utc=$armed.ToString("o");scope_model=$model;scope_serial=$serial;
        ADC_max=$maxAdc;trigger_threshold_ADC=$thresholdAdc;
        sample_interval_ns=$intervalNs;pretrigger_samples=$PreSamples;posttrigger_samples=$PostSamples;
        acquisition_window_ms=[Math]::Round($durationMs,3);trigger_mode= $(if($Mode -eq "Arm"){"hardware rising edge, no auto-trigger"}else{"disabled self test"});
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
    $file=[IO.Path]::Combine($OutputDir,"chA_reset_rising_i16le.bin")
    $data=New-Object byte[] ($total*2)
    [Buffer]::BlockCopy($buf,0,$data,0,$data.Length)
    [IO.File]::WriteAllBytes($file,$data)
    $hash=(Get-FileHash -Algorithm SHA256 -LiteralPath $file).Hash.ToLowerInvariant()
    $peak=[int]-32768;$min=[int]32767
    $above035=0;$above05=0;$above10=0
    $runMax05=0;$run05=0
    for($i=0;$i -lt $total;$i++) {
        $v=[int]$buf[$i]
        if($v -lt $min){$min=$v};if($v -gt $peak){$peak=$v}
        $tipV=$v*5.0/$maxAdc
        if($tipV -gt 0.35){$above035++}
        if($tipV -gt 0.5){
            $above05++;$run05++
            if($run05 -gt $runMax05){$runMax05=$run05}
        }else{$run05=0}
        if($tipV -gt 1.0){$above10++}
    }
    $result=@{
        schema="knx043-reset-rising-capture/v1";
        status=$(if($Mode -eq "Test"){"TEST_PIPELINE_COMPLETED"}else{"TRIGGERED_CAPTURE_COMPLETED"});
        captured_utc=[DateTime]::UtcNow.ToString("o");
        armed_utc=$armed.ToString("o");
        hardware_model=$model;hardware_serial=$serial;
        board_USB_com=$BoardComPort;board_USB_serial_user_expected=$ExpectedBoardUsbSerial;
        no_board_reset_or_GPIO_triggered_by_agent=$true;
        mode=$Mode;trigger_source="PicoScope CH A, rising-edge";
        hardware_trigger_tip_threshold_volts=$TriggerTipVolts;
        hardware_trigger_ADC=$thresholdAdc;trigger_delay_samples=0;
        sample_interval_ns=$intervalNs;sample_count=$actual;
        pretrigger_samples=$PreSamples;posttrigger_samples=$PostSamples;
        record_window_ms=[Math]::Round($durationMs,3);
        analog_range_Pico_input_volts_peak=0.5;physical_probe_tip_attenuation_user_reported=10;probe_tip_fullscale_volts_peak=5;
        user_reported_probe_tip_position="JMP3 pad2 KNX_TX U9 pin24; not independently visually confirmed";
        sample_min_tip_volts=[Math]::Round($min*5.0/$maxAdc,6);
        sample_max_tip_volts=[Math]::Round($peak*5.0/$maxAdc,6);
        samples_above_0p35_tip_volts=$above035;
        samples_above_0p5_tip_volts=$above05;
        samples_above_1p0_tip_volts=$above10;
        max_contiguous_above_0p5_tip_samples=$runMax05;
        max_contiguous_above_0p5_duration_us=[Math]::Round($runMax05*$intervalNs/1000,4);
        overflow=$overflow;
        USB_COM_enumeration_events=@($usbLog);
        raw_adc_file=$file;raw_adc_SHA256=$hash;
        caveat="Triggered captures indicate a threshold crossing, not a qualified KNX TP bus safety gate; no real KNX load/rail/U9/U11 current was measured; fast glitches shorter than sample interval may be underrepresented."
    }
    $resultFile=[IO.Path]::Combine($OutputDir,"capture_result.json")
    [IO.File]::WriteAllText($resultFile,((ConvertTo-Json -InputObject $result -Depth 10)+[Environment]::NewLine),[Text.Encoding]::UTF8)
    State $result.status $result
    [Console]::WriteLine("CAPTURE_DONE peak_tip_V="+$result.sample_max_tip_volts+" >0.5V_samples="+$above05+" duration_ms="+[Math]::Round($durationMs,3))
    [Console]::WriteLine("RAW_FILE "+$file)
}catch{
    $errorString=$_.Exception.Message
    try{State "ERROR" @{error=$errorString;reset_not_commanded=$true}}catch{}
    [Console]::Error.WriteLine("PICOSCOPE_CAPTURE_ERROR "+$errorString)
    exit 2
}finally{
    if($pin -and $pin.IsAllocated){$pin.Free()}
    if($handle -gt 0){
        [Knx043ResetScope]::ps3000aStop($handle)|Out-Null
        [Knx043ResetScope]::ps3000aCloseUnit($handle)|Out-Null
    }
}
