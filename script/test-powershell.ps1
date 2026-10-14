#!/usr/bin/env pwsh
<#
.SYNOPSIS
Lints the repo's PowerShell with PSScriptAnalyzer and runs its Pester suites; exits 1 on any finding or failure.
#>

$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

foreach ($module in 'PSScriptAnalyzer', 'Pester') {
    if (-not (Get-Module -ListAvailable $module)) {
        Install-Module $module -Scope CurrentUser -Force -Repository PSGallery
    }
}

$findings = Get-ChildItem -Recurse -Filter *.ps1 obs, script | ForEach-Object { Invoke-ScriptAnalyzer -Path $_.FullName }
$findings | Format-Table -AutoSize ScriptName, Line, RuleName, Message
if ($findings) { exit 1 }

$result = Invoke-Pester -Path obs -PassThru -Output Normal
if ($result.FailedCount -gt 0) { exit 1 }
