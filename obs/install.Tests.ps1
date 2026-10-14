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
