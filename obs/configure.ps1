#Requires -Version 7
<#
.SYNOPSIS
Writes the dotfiles OBS profile and scene collection and makes OBS open them.

.PARAMETER ConfigDir
The OBS config directory. Defaults to OBS's own location for the current OS.
#>
[CmdletBinding()]
param(
    [string]$ConfigDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ObsName = 'dotfiles'
$CanvasWidth = 1920
$CanvasHeight = 1080


function Get-ObsPlatform {
    if ($IsMacOS) { return 'macos' }
    if ($IsLinux) { return 'linux' }
    'windows'
}

function Get-ObsConfigDir {
    param([string]$Platform)

    switch ($Platform) {
        'macos' { Join-Path $HOME 'Library/Application Support/obs-studio' }
        'linux' {
            $base = if ($env:XDG_CONFIG_HOME) { $env:XDG_CONFIG_HOME } else { Join-Path $HOME '.config' }
            Join-Path $base 'obs-studio'
        }
        'windows' { Join-Path $env:APPDATA 'obs-studio' }
    }
}

function Test-ObsRunning {
    [bool](Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -in 'obs', 'obs64' })
}

<#
.SYNOPSIS
Finds a source setting in the scene collections OBS already has, so a device picked once survives.

.PARAMETER ConfigDir
The OBS config directory.

.PARAMETER SourceId
The OBS source type to look for, such as dshow_input.

.PARAMETER Key
The setting to return from the first source of that type that has it.
#>
function Find-ObsExistingSetting {
    param([string]$ConfigDir, [string]$SourceId, [string]$Key)

    $scenesDir = Join-Path $ConfigDir 'basic/scenes'
    if (-not (Test-Path $scenesDir)) { return $null }

    foreach ($file in Get-ChildItem $scenesDir -Filter '*.json') {
        try {
            $collection = Get-Content $file.FullName -Raw | ConvertFrom-Json -AsHashtable
        } catch {
            Write-Warning "Skipping unreadable scene collection $($file.FullName): $_"
            continue
        }
        foreach ($source in @($collection['sources'])) {
            if ($source -is [System.Collections.IDictionary] -and $source['id'] -eq $SourceId) {
                $value = $source['settings'][$Key]
                if ($value) { return $value }
            }
        }
    }
    $null
}

function Get-ObsMacCamera {
    $cameras = (system_profiler SPCameraDataType -json | ConvertFrom-Json).SPCameraDataType
    $builtIn = $cameras | Where-Object { $_.'spcamera_model-id' -match 'MacBook|FaceTime|Built-in' } |
        Select-Object -First 1
    if ($builtIn) { $builtIn.'spcamera_unique-id' }
}

<#
.SYNOPSIS
Returns the main display's UUID, which OBS's screen capture needs at load time.
#>
function Get-ObsMacDisplay {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class ObsMacDisplay {
    const string CoreGraphics = "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics";
    const string ColorSync = "/System/Library/Frameworks/ColorSync.framework/ColorSync";
    const string CoreFoundation = "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation";
    const uint Utf8 = 0x08000100;

    [DllImport(CoreGraphics)] static extern uint CGMainDisplayID();
    [DllImport(ColorSync)] static extern IntPtr CGDisplayCreateUUIDFromDisplayID(uint display);
    [DllImport(CoreFoundation)] static extern IntPtr CFUUIDCreateString(IntPtr allocator, IntPtr uuid);
    [DllImport(CoreFoundation)] static extern bool CFStringGetCString(IntPtr str, StringBuilder buffer, long size, uint encoding);
    [DllImport(CoreFoundation)] static extern void CFRelease(IntPtr obj);

    public static string MainDisplayUuid() {
        IntPtr uuid = CGDisplayCreateUUIDFromDisplayID(CGMainDisplayID());
        if (uuid == IntPtr.Zero) return null;
        IntPtr str = CFUUIDCreateString(IntPtr.Zero, uuid);
        var buffer = new StringBuilder(64);
        bool ok = CFStringGetCString(str, buffer, buffer.Capacity, Utf8);
        CFRelease(str);
        CFRelease(uuid);
        return ok ? buffer.ToString() : null;
    }
}
'@
    [ObsMacDisplay]::MainDisplayUuid()
}

<#
.SYNOPSIS
Returns the WASAPI endpoint ID OBS uses for a playback device, or $null when it is not installed.

.PARAMETER Name
The device name as Windows lists it, such as CABLE Input.
#>
function Get-ObsWindowsRenderDevice {
    param([string]$Name)

    $root = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render'
    $nameProperty = '{a45c254e-df1c-4efd-8020-67d146a850e0},2'
    foreach ($endpoint in Get-ChildItem $root -ErrorAction SilentlyContinue) {
        $properties = Get-ItemProperty (Join-Path $endpoint.PSPath 'Properties') -ErrorAction SilentlyContinue
        if ($properties -and $properties.$nameProperty -eq $Name) {
            return "{0.0.0.00000000}.$($endpoint.PSChildName)"
        }
    }
    $null
}

<#
.SYNOPSIS
Looks up this machine's camera, screen and monitoring device for the generated config.

.PARAMETER Platform
macos, windows or linux.

.PARAMETER ConfigDir
The OBS config directory, searched on Windows for devices already picked in OBS.
#>
function Get-ObsDevice {
    param([string]$Platform, [string]$ConfigDir)

    switch ($Platform) {
        'macos' {
            @{
                Camera = Get-ObsMacCamera
                Screen = $true
                ScreenId = Get-ObsMacDisplay
                MonitoringDeviceId = 'BlackHole2ch_UID'
                MonitoringDeviceName = 'BlackHole 2ch'
            }
        }
        'windows' {
            $cableId = Get-ObsWindowsRenderDevice -Name 'CABLE Input'
            @{
                Camera = Find-ObsExistingSetting -ConfigDir $ConfigDir -SourceId 'dshow_input' -Key 'video_device_id'
                Screen = $true
                ScreenId = Find-ObsExistingSetting -ConfigDir $ConfigDir -SourceId 'monitor_capture' -Key 'monitor_id'
                MonitoringDeviceId = $cableId
                MonitoringDeviceName = if ($cableId) { 'CABLE Input' }
            }
        }
        'linux' {
            @{
                Camera = Get-ChildItem '/dev/video*' -ErrorAction SilentlyContinue | Sort-Object Name |
                    Select-Object -First 1 -ExpandProperty FullName
                Screen = $false
            }
        }
    }
}

function Build-ObsSource {
    param([string]$Name, [string]$Id, [string]$VersionedId = $Id, [hashtable]$Settings = @{})

    [ordered]@{ name = $Name; id = $Id; versioned_id = $VersionedId; settings = $Settings }
}

function Build-ObsSceneItem {
    param([string]$Name, [int]$Id, [double]$X = 0, [double]$Y = 0,
        [double]$Width = $CanvasWidth, [double]$Height = $CanvasHeight)

    [ordered]@{
        name = $Name
        id = $Id
        visible = $true
        locked = $false
        pos = [ordered]@{ x = $X; y = $Y }
        rot = 0.0
        align = 5
        bounds_type = 2
        bounds_align = 0
        bounds = [ordered]@{ x = $Width; y = $Height }
    }
}

function Build-ObsScene {
    param([string]$Name, [string[]]$Sources)

    $items = for ($i = 0; $i -lt $Sources.Count; $i++) {
        if ($Sources[$i] -eq 'Webcam' -and $Sources.Count -gt 1) {
            Build-ObsSceneItem -Name 'Webcam' -Id ($i + 1) -X 1408 -Y 778 -Width 480 -Height 270
        } else {
            Build-ObsSceneItem -Name $Sources[$i] -Id ($i + 1)
        }
    }
    Build-ObsSource -Name $Name -Id 'scene' -Settings @{
        id_counter = $Sources.Count
        custom_size = $false
        items = @($items)
    }
}

function Build-ObsMicFilter {
    @(
        [ordered]@{
            name = 'Noise Suppression'; id = 'noise_suppress_filter'; versioned_id = 'noise_suppress_filter_v2'
            enabled = $true; settings = @{ method = 'rnnoise'; suppress_level = -30 }
        }
        [ordered]@{
            name = 'Noise Gate'; id = 'noise_gate_filter'; versioned_id = 'noise_gate_filter'
            enabled = $true; settings = @{}
        }
        [ordered]@{
            name = 'Compressor'; id = 'compressor_filter'; versioned_id = 'compressor_filter'
            enabled = $true; settings = @{}
        }
        [ordered]@{
            name = 'Limiter'; id = 'limiter_filter'; versioned_id = 'limiter_filter'
            enabled = $true; settings = @{}
        }
    )
}

<#
.SYNOPSIS
Builds the scene collection OBS loads, as an ordered dictionary ready for ConvertTo-Json.

.PARAMETER Platform
macos, windows or linux; picks the OS-specific source types.

.PARAMETER Devices
The result of Get-ObsDevice. A missing camera or screen ID leaves that source for a one-time pick
in OBS.
#>
function Build-ObsSceneCollection {
    param([string]$Platform, [hashtable]$Devices)

    $camera = $Devices['Camera']
    $sources = [System.Collections.Generic.List[object]]::new()

    switch ($Platform) {
        'macos' {
            $micId = 'coreaudio_input_capture'
            $sources.Add((Build-ObsSource -Name 'Webcam' -Id 'macos-avcapture' -Settings @{ device = "$camera" }))
            $display = @{ type = 0 }
            if ($Devices['ScreenId']) { $display['display_uuid'] = $Devices['ScreenId'] }
            $sources.Add((Build-ObsSource -Name 'Display' -Id 'screen_capture' -Settings $display))
        }
        'windows' {
            $micId = 'wasapi_input_capture'
            $sources.Add((Build-ObsSource -Name 'Webcam' -Id 'dshow_input' -Settings @{ video_device_id = "$camera" }))
            $screen = if ($Devices['ScreenId']) { @{ monitor_id = $Devices['ScreenId'] } } else { @{} }
            $sources.Add((Build-ObsSource -Name 'Display' -Id 'monitor_capture' -Settings $screen))
        }
        'linux' {
            $micId = 'pulse_input_capture'
            $sources.Add((Build-ObsSource -Name 'Webcam' -Id 'v4l2_input' -Settings @{ device_id = "$camera" }))
        }
    }
    $sources.Add((Build-ObsSource -Name 'Away background' -Id 'color_source' -VersionedId 'color_source_v3' -Settings @{
                color = 4280295456; width = $CanvasWidth; height = $CanvasHeight
            }))

    $scenes = [ordered]@{ 'Camera' = @('Webcam') }
    if ($Devices['Screen']) {
        $scenes['Screen + cam'] = @('Display', 'Webcam')
        $scenes['Screen'] = @('Display')
    }
    $scenes['Away'] = @('Away background')
    foreach ($scene in $scenes.GetEnumerator()) {
        $sources.Add((Build-ObsScene -Name $scene.Key -Sources $scene.Value))
    }

    $mic = Build-ObsSource -Name 'Mic/Aux' -Id $micId -Settings @{ device_id = 'default' }
    $mic['monitoring_type'] = 2
    $mic['filters'] = Build-ObsMicFilter

    [ordered]@{
        name = $ObsName
        AuxAudioDevice1 = $mic
        sources = $sources.ToArray()
        groups = @()
        scene_order = @($scenes.Keys | ForEach-Object { [ordered]@{ name = $_ } })
        current_scene = 'Camera'
        current_program_scene = 'Camera'
        current_transition = 'Fade'
        transition_duration = 300
        transitions = @()
    }
}

<#
.SYNOPSIS
Sets keys in one section of an INI document, keeping every other line as it is.

.PARAMETER Content
The current file content; empty for a new file.

.PARAMETER Section
The section name without brackets; appended when missing.

.PARAMETER Values
Key/value pairs to set; keys already in the section are replaced in place.
#>
function Merge-IniValue {
    param([string]$Content, [string]$Section, [System.Collections.IDictionary]$Values)

    $newline = if ($Content -match "`r`n") { "`r`n" } else { "`n" }
    $lines = [System.Collections.Generic.List[string]]::new()
    if ($Content) { $lines.AddRange([string[]]($Content -split '\r?\n')) }
    while ($lines.Count -and $lines[$lines.Count - 1] -eq '') { $lines.RemoveAt($lines.Count - 1) }

    $start = $lines.IndexOf("[$Section]")
    if ($start -lt 0) {
        if ($lines.Count) { $lines.Add('') }
        $lines.Add("[$Section]")
        $start = $lines.Count - 1
    }
    $end = $start + 1
    while ($end -lt $lines.Count -and $lines[$end] -notmatch '^\[') { $end++ }

    $pending = [ordered]@{}
    foreach ($key in $Values.Keys) { $pending[$key] = $Values[$key] }
    for ($i = $start + 1; $i -lt $end; $i++) {
        $key = ($lines[$i] -split '=', 2)[0]
        if ($pending.Contains($key)) {
            $lines[$i] = "$key=$($pending[$key])"
            $pending.Remove($key)
        }
    }

    $insertAt = $end
    while ($insertAt -gt $start + 1 -and $lines[$insertAt - 1] -eq '') { $insertAt-- }
    foreach ($key in $pending.Keys) {
        $lines.Insert($insertAt, "$key=$($pending[$key])")
        $insertAt++
    }
    ($lines -join $newline) + $newline
}

<#
.SYNOPSIS
Tells whether every value in Expected is also in Actual, ignoring the extra fields OBS adds on save.

.PARAMETER Expected
The generated value.

.PARAMETER Actual
The value read back from OBS's file. Lists of named objects are matched by name.
#>
function Test-ObsSubset {
    param($Expected, $Actual)

    if ($Expected -is [System.Collections.IDictionary]) {
        if ($Actual -isnot [System.Collections.IDictionary]) { return $false }
        foreach ($key in $Expected.Keys) {
            if (-not $Actual.Contains($key)) { return $false }
            if (-not (Test-ObsSubset $Expected[$key] $Actual[$key])) { return $false }
        }
        return $true
    }
    if ($Expected -is [System.Collections.IList]) {
        if ($Actual -isnot [System.Collections.IList] -or $Actual.Count -ne $Expected.Count) { return $false }
        for ($i = 0; $i -lt $Expected.Count; $i++) {
            $match = $Actual[$i]
            if ($Expected[$i] -is [System.Collections.IDictionary] -and $Expected[$i].Contains('name')) {
                $match = $Actual | Where-Object {
                    $_ -is [System.Collections.IDictionary] -and $_['name'] -eq $Expected[$i]['name']
                } | Select-Object -First 1
            }
            if (-not (Test-ObsSubset $Expected[$i] $match)) { return $false }
        }
        return $true
    }
    if ($Expected -is [bool] -or $Actual -is [bool]) {
        return $Expected -is [bool] -and $Actual -is [bool] -and $Expected -eq $Actual
    }
    if ($Expected -is [ValueType] -and $Actual -is [ValueType]) {
        return [double]$Expected -eq [double]$Actual
    }
    $Expected -ceq $Actual
}

function Write-ObsFile {
    param([string]$Path, [string]$Content)

    New-Item -ItemType Directory -Force -Path (Split-Path $Path) | Out-Null
    [System.IO.File]::WriteAllText($Path, $Content)
}

function Sync-ObsIni {
    param([string]$Path, [string]$Section, [System.Collections.IDictionary]$Values)

    $current = if (Test-Path $Path) { [System.IO.File]::ReadAllText($Path) } else { '' }
    $updated = Merge-IniValue -Content $current -Section $Section -Values $Values
    if ($updated -ceq $current) { return "ok: $Path" }
    Write-ObsFile -Path $Path -Content $updated
    "changed: $Path"
}

function Sync-ObsSceneCollection {
    param([string]$Path, [System.Collections.IDictionary]$Collection)

    if (Test-Path $Path) {
        try {
            $current = Get-Content $Path -Raw | ConvertFrom-Json -AsHashtable
            $roundTripped = $Collection | ConvertTo-Json -Depth 20 | ConvertFrom-Json -AsHashtable
            if (Test-ObsSubset $roundTripped $current) { return "ok: $Path" }
        } catch {
            Write-Warning "Replacing unreadable scene collection ${Path}: $_"
        }
    }
    Write-ObsFile -Path $Path -Content ($Collection | ConvertTo-Json -Depth 20)
    "changed: $Path"
}

<#
.SYNOPSIS
Writes the profile, the scene collection and the user.ini selection; prints changed or ok per file.

.PARAMETER Platform
macos, windows or linux.

.PARAMETER ConfigDir
The OBS config directory.

.PARAMETER Devices
The result of Get-ObsDevice.
#>
function Invoke-ObsConfigure {
    param([string]$Platform, [string]$ConfigDir, [hashtable]$Devices)

    if (Test-ObsRunning) {
        throw 'OBS is running. Quit it first: OBS writes its config when it exits and would undo this.'
    }

    $profileIni = Join-Path $ConfigDir "basic/profiles/$ObsName/basic.ini"
    Sync-ObsIni -Path $profileIni -Section 'General' -Values ([ordered]@{ Name = $ObsName })
    Sync-ObsIni -Path $profileIni -Section 'Video' -Values ([ordered]@{
            BaseCX = $CanvasWidth; BaseCY = $CanvasHeight; OutputCX = $CanvasWidth; OutputCY = $CanvasHeight
        })
    if ($Devices['MonitoringDeviceId']) {
        Sync-ObsIni -Path $profileIni -Section 'Audio' -Values ([ordered]@{
                MonitoringDeviceId = $Devices['MonitoringDeviceId']
                MonitoringDeviceName = $Devices['MonitoringDeviceName']
            })
    }

    Sync-ObsSceneCollection -Path (Join-Path $ConfigDir "basic/scenes/$ObsName.json") `
        -Collection (Build-ObsSceneCollection -Platform $Platform -Devices $Devices)

    Sync-ObsIni -Path (Join-Path $ConfigDir 'user.ini') -Section 'Basic' -Values ([ordered]@{
            Profile = $ObsName; ProfileDir = $ObsName
            SceneCollection = $ObsName; SceneCollectionFile = "$ObsName.json"
        })
}


if ($MyInvocation.InvocationName -ne '.') {
    $platform = Get-ObsPlatform
    if (-not $ConfigDir) { $ConfigDir = Get-ObsConfigDir -Platform $platform }
    Invoke-ObsConfigure -Platform $platform -ConfigDir $ConfigDir `
        -Devices (Get-ObsDevice -Platform $platform -ConfigDir $ConfigDir)
}
