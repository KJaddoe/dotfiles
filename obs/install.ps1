#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
Installs OBS, Camo and the background removal plugin on Windows, then writes the dotfiles OBS config.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$PluginVersion = '1.4.1'
$PluginSha256 = '7f9c0118c348111bf384c71e23fd056fd26e999bce90132d91db3017c6fa1b94'
$PluginsDir = Join-Path $env:ProgramData 'obs-studio\plugins'


function Install-WingetPackage {
    param([string]$Id)

    winget list --exact --id $Id | Out-Null
    if ($LASTEXITCODE -eq 0) { return "ok: $Id" }
    winget install --exact --id $Id --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "winget could not install $Id (exit code $LASTEXITCODE)" }
    "changed: $Id"
}

function Install-BackgroundRemovalPlugin {
    $marker = Join-Path $PluginsDir 'obs-backgroundremoval\.dotfiles-version'
    if ((Test-Path $marker) -and (Get-Content $marker -Raw).Trim() -eq $PluginVersion) {
        return "ok: obs-backgroundremoval $PluginVersion"
    }

    $zip = Join-Path $env:TEMP "obs-backgroundremoval-$PluginVersion-windows-x64.zip"
    $url = "https://github.com/royshil/obs-backgroundremoval/releases/download/$PluginVersion/" +
        "obs-backgroundremoval-$PluginVersion-windows-x64.zip"
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
    $actual = (Get-FileHash $zip -Algorithm SHA256).Hash
    if ($actual -ne $PluginSha256) {
        Remove-Item $zip
        throw "obs-backgroundremoval download has SHA256 $actual, expected $PluginSha256"
    }

    $staging = Join-Path $env:TEMP "obs-backgroundremoval-$PluginVersion"
    Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive $zip -DestinationPath $staging
    New-Item -ItemType Directory -Force $PluginsDir | Out-Null
    Remove-Item (Join-Path $PluginsDir 'obs-backgroundremoval') -Recurse -Force -ErrorAction SilentlyContinue
    Copy-Item (Join-Path $staging 'obs-backgroundremoval') $PluginsDir -Recurse
    Set-Content $marker $PluginVersion
    Remove-Item $zip, $staging -Recurse -Force
    "changed: obs-backgroundremoval $PluginVersion"
}


Install-WingetPackage -Id 'OBSProject.OBSStudio'
Install-WingetPackage -Id 'ReincubateLtd.CamoStudio'
Install-WingetPackage -Id 'Microsoft.PowerShell'
Install-BackgroundRemovalPlugin

# winget does not refresh PATH in this session, so a freshly installed pwsh is not found by name.
& (Join-Path $env:ProgramFiles 'PowerShell\7\pwsh.exe') -NoProfile -File (Join-Path $PSScriptRoot 'configure.ps1')
if ($LASTEXITCODE -ne 0) { throw "configure.ps1 failed (exit code $LASTEXITCODE)" }
