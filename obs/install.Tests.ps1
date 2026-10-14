BeforeAll {
    . (Join-Path $PSScriptRoot 'install.ps1')

    function Get-TestObsDir {
        [IO.Path]::GetFullPath((Join-Path $TestDrive 'obs-studio'))
    }
}

Describe 'Get-PluginTargetPath' {
    It 'puts the DLL where OBS loads plugins from' {
        $obsDir = Get-TestObsDir

        Get-PluginTargetPath -EntryName 'obs-backgroundremoval/bin/64bit/obs-backgroundremoval.dll' -ObsDir $obsDir |
            Should -Be ([IO.Path]::GetFullPath((Join-Path $obsDir 'obs-plugins/64bit/obs-backgroundremoval.dll')))
    }

    It 'puts data under the module name, keeping subfolders' {
        $obsDir = Get-TestObsDir

        Get-PluginTargetPath -EntryName 'obs-backgroundremoval/data/models/a.ort' -ObsDir $obsDir |
            Should -Be ([IO.Path]::GetFullPath((Join-Path $obsDir 'data/obs-plugins/obs-backgroundremoval/models/a.ort')))
    }

    It 'skips directory entries and files outside the plugin folders' {
        $obsDir = Get-TestObsDir

        Get-PluginTargetPath -EntryName 'obs-backgroundremoval/data/' -ObsDir $obsDir | Should -BeNullOrEmpty
        Get-PluginTargetPath -EntryName 'How to install plugin on Windows.txt' -ObsDir $obsDir | Should -BeNullOrEmpty
        Get-PluginTargetPath -EntryName 'remove-old-installation.bat' -ObsDir $obsDir | Should -BeNullOrEmpty
    }

    It 'rejects an entry that climbs out of the OBS directory' -ForEach @(
        @{ Entry = 'obs-backgroundremoval/data/../../../../evil.dll' }
        @{ Entry = 'obs-backgroundremoval/bin/64bit/../../../../../Windows/evil.dll' }
    ) {
        { Get-PluginTargetPath -EntryName $Entry -ObsDir (Get-TestObsDir) } | Should -Throw '*resolves outside*'
    }

    It 'does not treat a sibling directory with the same prefix as inside' {
        $obsDir = Get-TestObsDir

        { Get-PluginTargetPath -EntryName 'obs-backgroundremoval/data/../../../../obs-studio-evil/x.dll' -ObsDir $obsDir } |
            Should -Throw '*resolves outside*'
    }

    It 'matches the archive prefix case-sensitively' {
        Get-PluginTargetPath -EntryName 'OBS-BACKGROUNDREMOVAL/bin/64bit/x.dll' -ObsDir (Get-TestObsDir) |
            Should -BeNullOrEmpty
    }
}

Describe 'Test-InstalledApp' {
    It 'finds an app installed outside winget by publisher and name' {
        $entries = @(
            [pscustomobject]@{ DisplayName = 'Something else'; Publisher = 'Other' }
            [pscustomobject]@{ DisplayName = 'Camo Studio'; Publisher = 'Reincubate Ltd' }
        )

        Test-InstalledApp -Entries $entries -Publisher 'Reincubate*' -DisplayName 'Camo*' | Should -BeTrue
    }

    It 'does not match on the name alone when the publisher differs' {
        $entries = @([pscustomobject]@{ DisplayName = 'Camo Studio'; Publisher = 'Someone Else' })

        Test-InstalledApp -Entries $entries -Publisher 'Reincubate*' -DisplayName 'Camo*' | Should -BeFalse
    }

    It 'skips entries Windows recorded without a name or publisher' {
        $entries = @(
            [pscustomobject]@{ DisplayName = 'Camo Studio' }
            [pscustomobject]@{ Publisher = 'Reincubate Ltd' }
        )

        Test-InstalledApp -Entries $entries -Publisher 'Reincubate*' -DisplayName 'Camo*' | Should -BeFalse
    }

    It 'returns false for an empty app list' {
        Test-InstalledApp -Entries @() -Publisher 'Reincubate*' -DisplayName 'Camo*' | Should -BeFalse
    }
}

Describe 'Install-WingetPackage' {
    BeforeAll {
        function winget { $global:LASTEXITCODE = 1; $script:WingetCalls += , $args }
        function Get-AppxPackage { param($Name) throw "Get-AppxPackage $Name is not mocked" }
    }

    BeforeEach {
        $script:WingetCalls = @()
        Mock Get-InstalledAppEntry { @() }
    }

    It 'skips a copy installed from the Microsoft Store' {
        Mock Get-AppxPackage { [pscustomobject]@{ Name = 'ReincubateLtd.CamoStudio' } }

        Install-WingetPackage -Id 'ReincubateLtd.CamoStudio' -Publisher 'Reincubate*' -DisplayName 'Camo*' -AppxName '*Camo*' |
            Should -Be 'ok: ReincubateLtd.CamoStudio (installed from the Microsoft Store)'
        $script:WingetCalls | Where-Object { $_[0] -eq 'install' } | Should -BeNullOrEmpty
    }

    It 'installs with winget when no copy is found anywhere' {
        Mock Get-AppxPackage { }

        { Install-WingetPackage -Id 'ReincubateLtd.CamoStudio' -Publisher 'Reincubate*' -DisplayName 'Camo*' -AppxName '*Camo*' } |
            Should -Throw '*winget could not install*'
        @($script:WingetCalls | Where-Object { $_[0] -eq 'install' }).Count | Should -Be 1
    }

    It 'does not ask the Store when no package name is given' {
        Mock Get-AppxPackage { [pscustomobject]@{ Name = 'Anything' } }

        { Install-WingetPackage -Id 'OBSProject.OBSStudio' -Publisher 'OBS Project*' -DisplayName 'OBS Studio*' } |
            Should -Throw '*winget could not install*'
        Should -Invoke Get-AppxPackage -Times 0
    }
}

Describe 'Get-PwshPath' {
    It 'returns the first candidate that exists, skipping empty and missing ones' {
        $alias = Join-Path $TestDrive 'WindowsApps/pwsh.exe'
        New-Item -ItemType File -Force $alias | Out-Null

        Get-PwshPath -Candidates @($null, (Join-Path $TestDrive 'Program Files/pwsh.exe'), $alias) | Should -Be $alias
    }

    It 'does not accept a directory named pwsh.exe' {
        $dir = Join-Path $TestDrive 'dir/pwsh.exe'
        New-Item -ItemType Directory -Force $dir | Out-Null

        { Get-PwshPath -Candidates @($dir) } | Should -Throw '*PowerShell 7 is not in*'
    }

    It 'names every place it looked when PowerShell 7 is missing' {
        { Get-PwshPath -Candidates @('/nope/a/pwsh.exe', '/nope/b/pwsh.exe') } |
            Should -Throw '*/nope/a/pwsh.exe, /nope/b/pwsh.exe*'
    }
}
