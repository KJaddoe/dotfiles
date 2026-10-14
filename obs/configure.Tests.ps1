BeforeAll {
    . (Join-Path $PSScriptRoot 'configure.ps1')

    function Read-Collection([string]$ConfigDir) {
        Get-Content (Join-Path $ConfigDir 'basic/scenes/dotfiles.json') -Raw | ConvertFrom-Json -AsHashtable
    }

    function Get-TestConfigDir {
        Join-Path $TestDrive ([guid]::NewGuid())
    }

    function Get-Source($Collection, [string]$Name) {
        $Collection['sources'] | Where-Object { $_['name'] -eq $Name } | Select-Object -First 1
    }

    $script:MacDevices = @{
        Camera = 'CAMERA-UID'; Screen = $true; ScreenId = 'DISPLAY-UUID'
        MonitoringDeviceId = 'BlackHole2ch_UID'; MonitoringDeviceName = 'BlackHole 2ch'
    }
}

Describe 'Build-ObsSceneCollection' {
    It 'uses the macOS source types and the discovered camera' {
        $collection = Build-ObsSceneCollection -Platform macos -Devices $MacDevices

        $collection['AuxAudioDevice1']['id'] | Should -Be 'coreaudio_input_capture'
        (Get-Source $collection 'Webcam')['id'] | Should -Be 'macos-avcapture'
        (Get-Source $collection 'Webcam')['settings']['device'] | Should -Be 'CAMERA-UID'
        (Get-Source $collection 'Display')['id'] | Should -Be 'screen_capture'
        (Get-Source $collection 'Display')['settings']['display_uuid'] | Should -Be 'DISPLAY-UUID'
    }

    It 'sends the mic to the monitoring device through the four filters in order' {
        $mic = (Build-ObsSceneCollection -Platform macos -Devices $MacDevices)['AuxAudioDevice1']

        $mic['monitoring_type'] | Should -Be 2
        $mic['settings']['device_id'] | Should -Be 'default'
        $mic['filters'].versioned_id | Should -Be @(
            'noise_suppress_filter_v2', 'noise_gate_filter', 'compressor_filter', 'limiter_filter')
        $mic['filters'][0]['settings']['method'] | Should -Be 'rnnoise'
    }

    It 'orders the scenes and places the camera bottom right only when combined with the screen' {
        $collection = Build-ObsSceneCollection -Platform macos -Devices $MacDevices

        $collection['scene_order'].name | Should -Be @('Camera', 'Screen + cam', 'Screen', 'Away')
        $pip = (Get-Source $collection 'Screen + cam')['settings']['items'] |
            Where-Object { $_['name'] -eq 'Webcam' }
        $pip['pos']['x'] + $pip['bounds']['x'] | Should -BeLessOrEqual 1920
        $pip['pos']['y'] + $pip['bounds']['y'] | Should -BeLessOrEqual 1080
        (Get-Source $collection 'Camera')['settings']['items'][0]['bounds']['x'] | Should -Be 1920
    }

    It 'uses the Windows source types and keeps a previously picked screen' {
        $collection = Build-ObsSceneCollection -Platform windows -Devices @{
            Camera = 'Camo:\\?\camo'; Screen = $true; ScreenId = 'DISPLAY1'
        }

        $collection['AuxAudioDevice1']['id'] | Should -Be 'wasapi_input_capture'
        (Get-Source $collection 'Webcam')['settings']['video_device_id'] | Should -Be 'Camo:\\?\camo'
        (Get-Source $collection 'Display')['settings']['monitor_id'] | Should -Be 'DISPLAY1'
    }

    It 'leaves out the screen scenes on Linux' {
        $collection = Build-ObsSceneCollection -Platform linux -Devices @{ Camera = '/dev/video0'; Screen = $false }

        $collection['scene_order'].name | Should -Be @('Camera', 'Away')
        Get-Source $collection 'Display' | Should -BeNullOrEmpty
        (Get-Source $collection 'Webcam')['id'] | Should -Be 'v4l2_input'
    }

    It 'gives every source and scene a unique name, as OBS requires' -ForEach @(
        @{ Platform = 'macos' }, @{ Platform = 'windows' }, @{ Platform = 'linux' }
    ) {
        $names = (Build-ObsSceneCollection -Platform $Platform -Devices @{ Screen = $Platform -ne 'linux' })['sources'].name

        $names.Count | Should -Be @($names | Sort-Object -Unique).Count
    }

    It 'leaves the camera unset rather than failing when none was found' {
        $collection = Build-ObsSceneCollection -Platform macos -Devices @{ Camera = $null; Screen = $true }

        (Get-Source $collection 'Webcam')['settings']['device'] | Should -Be ''
    }
}

Describe 'Merge-IniValue' {
    It 'replaces a key in place and keeps every other line' {
        $content = "[General]`nName=Untitled`nOther=1`n`n[Audio]`nSampleRate=48000`n"

        Merge-IniValue -Content $content -Section 'General' -Values @{ Name = 'dotfiles' } |
            Should -Be "[General]`nName=dotfiles`nOther=1`n`n[Audio]`nSampleRate=48000`n"
    }

    It 'adds a missing key at the end of its section, before the blank line' {
        $content = "[Audio]`nSampleRate=48000`n`n[Video]`nFPSCommon=30`n"

        Merge-IniValue -Content $content -Section 'Audio' -Values @{ MonitoringDeviceId = 'X' } |
            Should -Be "[Audio]`nSampleRate=48000`nMonitoringDeviceId=X`n`n[Video]`nFPSCommon=30`n"
    }

    It 'appends a missing section and creates a file from nothing' {
        Merge-IniValue -Content '' -Section 'Basic' -Values ([ordered]@{ Profile = 'dotfiles'; ProfileDir = 'dotfiles' }) |
            Should -Be "[Basic]`nProfile=dotfiles`nProfileDir=dotfiles`n"
    }

    It 'keeps Windows line endings' {
        Merge-IniValue -Content "[Basic]`r`nProfile=Untitled`r`n" -Section 'Basic' -Values @{ Profile = 'dotfiles' } |
            Should -Be "[Basic]`r`nProfile=dotfiles`r`n"
    }

    It 'does not treat a same-named key in another section as the target' {
        $content = "[General]`nName=keep`n`n[Basic]`nProfile=x`n"

        Merge-IniValue -Content $content -Section 'Basic' -Values @{ Name = 'dotfiles' } |
            Should -Be "[General]`nName=keep`n`n[Basic]`nProfile=x`nName=dotfiles`n"
    }
}

Describe 'Test-ObsSubset' {
    It 'ignores fields OBS adds on save' {
        Test-ObsSubset @{ name = 'Camera'; settings = @{ device = 'A' } } `
            @{ name = 'Camera'; uuid = 'u'; mixers = 255; settings = @{ device = 'A'; preset = 'high' } } |
            Should -BeTrue
    }

    It 'matches named list entries by name, not by position' {
        Test-ObsSubset @(@{ name = 'A' }, @{ name = 'B' }) @(@{ name = 'B'; x = 1 }, @{ name = 'A' }) |
            Should -BeTrue
    }

    It 'treats an integer and the same float as equal' {
        Test-ObsSubset @{ x = 1408 } @{ x = 1408.0 } | Should -BeTrue
    }

    It 'rejects a changed value, a missing key, and an extra list entry' {
        Test-ObsSubset @{ monitoring_type = 2 } @{ monitoring_type = 0 } | Should -BeFalse
        Test-ObsSubset @{ filters = @() } @{} | Should -BeFalse
        Test-ObsSubset @(@{ name = 'A' }) @(@{ name = 'A' }, @{ name = 'Extra' }) | Should -BeFalse
    }

    It 'compares strings case-sensitively and does not confuse a boolean with a number' {
        Test-ObsSubset @{ device = 'default' } @{ device = 'Default' } | Should -BeFalse
        Test-ObsSubset @{ enabled = $true } @{ enabled = 1 } | Should -BeFalse
    }
}

Describe 'Invoke-ObsConfigure' {
    BeforeEach {
        Mock Test-ObsRunning { $false }
    }

    It 'writes the profile, the collection and the user.ini selection' {
        $configDir = Get-TestConfigDir
        $result = Invoke-ObsConfigure -Platform macos -ConfigDir $configDir -Devices $MacDevices

        $result | Should -Match '^changed: '
        Get-Content (Join-Path $configDir 'basic/profiles/dotfiles/basic.ini') -Raw |
            Should -Match 'MonitoringDeviceId=BlackHole2ch_UID'
        (Read-Collection $configDir)['name'] | Should -Be 'dotfiles'
        Get-Content (Join-Path $configDir 'user.ini') -Raw | Should -Match 'SceneCollectionFile=dotfiles\.json'
    }

    It 'changes nothing on a second run' {
        $configDir = Get-TestConfigDir
        Invoke-ObsConfigure -Platform macos -ConfigDir $configDir -Devices $MacDevices | Out-Null

        Invoke-ObsConfigure -Platform macos -ConfigDir $configDir -Devices $MacDevices |
            Should -Not -Match '^changed: '
    }

    It 'stays a no-op after OBS rewrites the collection with its own extra fields' {
        $configDir = Get-TestConfigDir
        Invoke-ObsConfigure -Platform macos -ConfigDir $configDir -Devices $MacDevices | Out-Null
        $collection = Read-Collection $configDir
        $collection['AuxAudioDevice1']['uuid'] = 'added-by-obs'
        foreach ($source in $collection['sources']) { $source['mixers'] = 0 }
        $collection | ConvertTo-Json -Depth 20 | Set-Content (Join-Path $configDir 'basic/scenes/dotfiles.json')

        Invoke-ObsConfigure -Platform macos -ConfigDir $configDir -Devices $MacDevices |
            Should -Not -Match '^changed: '
    }

    It 'puts back a setting changed in OBS, because the repo owns the config' {
        $configDir = Get-TestConfigDir
        Invoke-ObsConfigure -Platform macos -ConfigDir $configDir -Devices $MacDevices | Out-Null
        $path = Join-Path $configDir 'basic/scenes/dotfiles.json'
        $collection = Read-Collection $configDir
        $collection['AuxAudioDevice1']['monitoring_type'] = 0
        $collection | ConvertTo-Json -Depth 20 | Set-Content $path

        Invoke-ObsConfigure -Platform macos -ConfigDir $configDir -Devices $MacDevices |
            Should -Contain "changed: $path"
        (Read-Collection $configDir)['AuxAudioDevice1']['monitoring_type'] | Should -Be 2
    }

    It 'keeps the rest of user.ini' {
        $configDir = Get-TestConfigDir
        New-Item -ItemType Directory -Force $configDir | Out-Null
        "[General]`nFirstRun=true`n`n[Basic]`nProfile=Untitled`nConfigOnNewProfile=true`n" |
            Set-Content (Join-Path $configDir 'user.ini') -NoNewline

        Invoke-ObsConfigure -Platform macos -ConfigDir $configDir -Devices $MacDevices | Out-Null

        $userIni = Get-Content (Join-Path $configDir 'user.ini') -Raw
        $userIni | Should -Match 'FirstRun=true'
        $userIni | Should -Match 'ConfigOnNewProfile=true'
        $userIni | Should -Match 'Profile=dotfiles'
    }

    It 'never touches the stream key file' {
        $configDir = Get-TestConfigDir
        $service = Join-Path $configDir 'basic/profiles/dotfiles/service.json'
        New-Item -ItemType Directory -Force (Split-Path $service) | Out-Null
        '{"settings":{"key":"secret"}}' | Set-Content $service -NoNewline

        Invoke-ObsConfigure -Platform macos -ConfigDir $configDir -Devices $MacDevices | Out-Null

        Get-Content $service -Raw | Should -Be '{"settings":{"key":"secret"}}'
    }

    It 'replaces a corrupt collection instead of failing' {
        $configDir = Get-TestConfigDir
        $path = Join-Path $configDir 'basic/scenes/dotfiles.json'
        New-Item -ItemType Directory -Force (Split-Path $path) | Out-Null
        '{ not json' | Set-Content $path

        Invoke-ObsConfigure -Platform macos -ConfigDir $configDir -Devices $MacDevices -WarningAction SilentlyContinue |
            Should -Contain "changed: $path"
        (Read-Collection $configDir)['name'] | Should -Be 'dotfiles'
    }

    It 'writes a device ID with quotes and backslashes as data, not as JSON' {
        $configDir = Get-TestConfigDir
        $devices = @{ Camera = 'Cam"era\", "injected": "x'; Screen = $true }

        Invoke-ObsConfigure -Platform windows -ConfigDir $configDir -Devices $devices | Out-Null

        $camera = Get-Source (Read-Collection $configDir) 'Webcam'
        $camera['settings']['video_device_id'] | Should -Be 'Cam"era\", "injected": "x'
        $camera['settings'].Keys | Should -Be @('video_device_id')
    }

    It 'refuses to run while OBS is running and writes nothing' {
        $configDir = Get-TestConfigDir
        Mock Test-ObsRunning { $true }

        { Invoke-ObsConfigure -Platform macos -ConfigDir $configDir -Devices $MacDevices } |
            Should -Throw '*OBS is running*'
        Test-Path $configDir | Should -BeFalse
    }
}

Describe 'Find-ObsExistingSetting' {
    It 'finds a device picked in another collection and skips unreadable files' {
        $scenes = Join-Path $TestDrive 'find/basic/scenes'
        New-Item -ItemType Directory -Force $scenes | Out-Null
        '{ broken' | Set-Content (Join-Path $scenes 'a.json')
        @{ sources = @(@{ id = 'dshow_input'; settings = @{ video_device_id = 'Camo:path' } }) } |
            ConvertTo-Json -Depth 5 | Set-Content (Join-Path $scenes 'b.json')

        Find-ObsExistingSetting -ConfigDir (Join-Path $TestDrive 'find') -SourceId 'dshow_input' `
            -Key 'video_device_id' -WarningAction SilentlyContinue | Should -Be 'Camo:path'
    }

    It 'returns nothing when OBS has no collections yet' {
        Find-ObsExistingSetting -ConfigDir (Join-Path $TestDrive 'none') -SourceId 'dshow_input' -Key 'x' |
            Should -BeNullOrEmpty
    }
}
