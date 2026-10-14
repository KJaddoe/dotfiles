#Requires -Version 5.1
<#
.SYNOPSIS
Installs OBS, Camo and the background removal plugin on Windows, then writes the dotfiles OBS config.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$PluginName = 'obs-backgroundremoval'
$PluginVersion = '1.4.1'
$PluginSha256 = '7f9c0118c348111bf384c71e23fd056fd26e999bce90132d91db3017c6fa1b94'


<#
.SYNOPSIS
Tells whether an installed-apps entry from the Windows uninstall registry matches a publisher and name.

.PARAMETER Entries
Uninstall registry entries, each with DisplayName and Publisher properties when Windows recorded them.

.PARAMETER Publisher
A -like pattern for the publisher.

.PARAMETER DisplayName
A -like pattern for the app name.
#>
function Test-InstalledApp {
    param([object[]]$Entries, [string]$Publisher, [string]$DisplayName)

    foreach ($entry in $Entries) {
        $names = $entry.PSObject.Properties.Name
        if ($names -contains 'DisplayName' -and $names -contains 'Publisher' -and
            $entry.DisplayName -like $DisplayName -and $entry.Publisher -like $Publisher) {
            return $true
        }
    }
    $false
}

function Get-InstalledAppEntry {
    $keys = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
    Get-ItemProperty $keys -ErrorAction SilentlyContinue
}

<#
.SYNOPSIS
Installs a winget package unless winget, Windows' app list or the Microsoft Store already has it.

.PARAMETER Id
The winget package ID.

.PARAMETER Publisher
A -like pattern for the publisher in Windows' app list, for a copy winget cannot match to its package.

.PARAMETER DisplayName
A -like pattern for the app name in Windows' app list.

.PARAMETER AppxName
A wildcard for the app package name, for a copy installed from the Microsoft Store, which neither
winget nor Windows' app list sees.
#>
function Install-WingetPackage {
    param([string]$Id, [string]$Publisher, [string]$DisplayName, [string]$AppxName)

    Write-Progress -Activity 'Installing OBS' -Status "Checking $Id"
    winget list --exact --id $Id --accept-source-agreements | Out-Null
    if ($LASTEXITCODE -eq 0) { return "ok: $Id" }
    if (Test-InstalledApp -Entries @(Get-InstalledAppEntry) -Publisher $Publisher -DisplayName $DisplayName) {
        return "ok: $Id (installed outside winget)"
    }
    if ($AppxName -and (Get-AppxPackage -Name $AppxName)) {
        return "ok: $Id (installed from the Microsoft Store)"
    }
    winget install --exact --id $Id --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "winget could not install $Id (exit code $LASTEXITCODE)" }
    "changed: $Id"
}

<#
.SYNOPSIS
Maps a plugin archive entry onto OBS's own plugin layout, or returns $null for an entry it does not install.

.PARAMETER EntryName
The entry's path inside the archive, with forward slashes.

.PARAMETER ObsDir
The OBS install directory. An entry that would resolve outside it throws.
#>
function Get-PluginTargetPath {
    param([string]$EntryName, [string]$ObsDir)

    if ($EntryName.EndsWith('/')) { return $null }
    $layout = [ordered]@{
        "$PluginName/bin/64bit/" = Join-Path $ObsDir 'obs-plugins/64bit'
        "$PluginName/data/" = Join-Path $ObsDir "data/obs-plugins/$PluginName"
    }
    foreach ($prefix in $layout.Keys) {
        if ($EntryName.StartsWith($prefix, [StringComparison]::Ordinal)) {
            $target = [IO.Path]::GetFullPath((Join-Path $layout[$prefix] $EntryName.Substring($prefix.Length)))
            $root = [IO.Path]::GetFullPath($ObsDir).TrimEnd([IO.Path]::DirectorySeparatorChar) +
                [IO.Path]::DirectorySeparatorChar
            if (-not $target.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
                throw "Plugin archive entry $EntryName resolves outside $ObsDir"
            }
            return $target
        }
    }
    $null
}

<#
.SYNOPSIS
Installs the plugin into OBS's install directory, which only administrators can write.

.PARAMETER ObsDir
The OBS install directory.
#>
function Install-BackgroundRemovalPlugin {
    param([string]$ObsDir)

    $dataDir = Join-Path $ObsDir "data/obs-plugins/$PluginName"
    $marker = Join-Path $dataDir '.dotfiles-version'
    if ((Test-Path $marker) -and (Get-Content $marker -Raw).Trim() -eq $PluginVersion) {
        return "ok: $PluginName $PluginVersion"
    }

    # Verified and extracted in memory: a file on disk could be swapped between the check and the copy.
    Write-Progress -Activity 'Installing OBS' -Status "Downloading $PluginName $PluginVersion (about 50 MB)"
    $url = "https://github.com/royshil/$PluginName/releases/download/$PluginVersion/" +
        "$PluginName-$PluginVersion-windows-x64.zip"
    $bytes = (New-Object System.Net.WebClient).DownloadData($url)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $actual = [BitConverter]::ToString($sha256.ComputeHash($bytes)).Replace('-', '')
    if ($actual -ne $PluginSha256) {
        throw "$PluginName download has SHA256 $actual, expected $PluginSha256"
    }

    Add-Type -AssemblyName System.IO.Compression
    $archive = New-Object System.IO.Compression.ZipArchive (New-Object System.IO.MemoryStream (, $bytes))
    try {
        Remove-Item (Join-Path $ObsDir "obs-plugins/64bit/$PluginName.dll") -Force -ErrorAction SilentlyContinue
        Remove-Item $dataDir -Recurse -Force -ErrorAction SilentlyContinue
        foreach ($entry in $archive.Entries) {
            $target = Get-PluginTargetPath -EntryName $entry.FullName -ObsDir $ObsDir
            if (-not $target) { continue }
            New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
            $source = $entry.Open()
            $destination = [IO.File]::Create($target)
            try { $source.CopyTo($destination) } finally { $destination.Dispose(); $source.Dispose() }
        }
    } finally {
        $archive.Dispose()
    }
    Set-Content $marker $PluginVersion
    "changed: $PluginName $PluginVersion"
}


if ($MyInvocation.InvocationName -ne '.') {
    $principal = New-Object Security.Principal.WindowsPrincipal ([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run this from an elevated PowerShell: it installs into Program Files.'
    }

    Install-WingetPackage -Id 'OBSProject.OBSStudio' -Publisher 'OBS Project*' -DisplayName 'OBS Studio*'
    Install-WingetPackage -Id 'ReincubateLtd.CamoStudio' -Publisher 'Reincubate*' -DisplayName 'Camo*' `
        -AppxName '*Camo*'
    Install-WingetPackage -Id 'Microsoft.PowerShell' -Publisher 'Microsoft Corporation' -DisplayName 'PowerShell 7*'

    $obsDir = Join-Path $env:ProgramFiles 'obs-studio'
    if (-not (Test-Path (Join-Path $obsDir 'bin/64bit/obs64.exe'))) {
        throw "OBS is not in $obsDir, where winget installs it by default"
    }
    Install-BackgroundRemovalPlugin -ObsDir $obsDir

    Write-Progress -Activity 'Installing OBS' -Status 'Writing the OBS config'
    # winget does not refresh PATH in this session, so a freshly installed pwsh is not found by name.
    & (Join-Path $env:ProgramFiles 'PowerShell\7\pwsh.exe') -NoProfile -File (Join-Path $PSScriptRoot 'configure.ps1')
    if ($LASTEXITCODE -ne 0) { throw "configure.ps1 failed (exit code $LASTEXITCODE)" }
}
