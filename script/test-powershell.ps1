#!/usr/bin/env pwsh
<#
.SYNOPSIS
Lints the repo's PowerShell with PSScriptAnalyzer; exits 1 on any finding.
#>

$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

if (-not (Get-Module -ListAvailable PSScriptAnalyzer)) {
    Install-Module PSScriptAnalyzer -Scope CurrentUser -Force -Repository PSGallery
}

$findings = Get-ChildItem -Recurse -Filter *.ps1 script | ForEach-Object { Invoke-ScriptAnalyzer -Path $_.FullName }
$findings | Format-Table -AutoSize ScriptName, Line, RuleName, Message
if ($findings) { exit 1 }
