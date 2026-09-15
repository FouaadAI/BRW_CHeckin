# Query the Copilot Resource Registry
# Usage: .\query-registry.ps1 [-Type agent|skill|tool|plugin] [-Tag <tag>] [-Keyword <keyword>]
param(
    [string]$Type,
    [string]$Tag,
    [string]$Keyword,
    [switch]$ListTags
)

$registryPath = Join-Path $PSScriptRoot "..\copilot-registry.yml"
if (-not (Test-Path $registryPath)) {
    Write-Error "Registry not found at $registryPath"
    exit 1
}

$content = Get-Content $registryPath -Raw

function Get-Section($name) {
    $pattern = "(?sm)$name\:(.+?)(?=\n\w+\:|\z)"
    $match = [regex]::Match($content, $pattern)
    if ($match.Success) { return $match.Groups[1].Value }
    return ""
}

function Parse-Items($sectionText) {
    $items = @()
    $entries = [regex]::Matches($sectionText, '(?sm)- name\: (.+?)\n(?=  - name\:|\z)')
    foreach ($m in $entries) {
        $block = $m.Value
        $name = if ($block -match '- name\: (.+)') { $Matches[1].Trim() } else { "" }
        $path = if ($block -match 'path\: (.+)') { $Matches[1].Trim() } else { "" }
        $desc = if ($block -match 'description\: (.+)') { $Matches[1].Trim() } else { "" }
        $tags = if ($block -match 'tags\: \[(.+?)\]') { $Matches[1].Trim() } else { "" }
        $source = if ($block -match 'source\: (.+)') { $Matches[1].Trim() } else { "" }
        $items += [PSCustomObject]@{ Name=$name; Path=$path; Description=$desc; Tags=$tags; Source=$source }
    }
    return $items
}

$allItems = @()
foreach ($sec in @('agents','skills','tools','plugins')) {
    $section = Get-Section $sec
    $items = Parse-Items $section
    foreach ($i in $items) { $i | Add-Member -NotePropertyName Type -NotePropertyValue $sec -Force }
    $allItems += $items
}

if ($ListTags) {
    $allItems | ForEach-Object { $_.Tags -split ',' } | ForEach-Object { $_.Trim() } | Sort-Object -Unique | ForEach-Object { Write-Host $_ }
    exit
}

$filtered = $allItems

if ($Type) {
    $filtered = $filtered | Where-Object { $_.Type -eq $Type }
}

if ($Tag) {
    $filtered = $filtered | Where-Object { $_.Tags -like "*$Tag*" }
}

if ($Keyword) {
    $filtered = $filtered | Where-Object {
        $_.Name -like "*$Keyword*" -or
        $_.Description -like "*$Keyword*" -or
        $_.Tags -like "*$Keyword*"
    }
}

$filtered | Select-Object Name, Type, Source, Description, Tags, Path | Format-Table -AutoSize
Write-Host "`nTotal: $($filtered.Count) of $($allItems.Count) resources" -ForegroundColor Cyan
