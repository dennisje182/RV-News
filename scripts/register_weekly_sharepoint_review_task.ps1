param(
    [string]$TaskName = "RV News weekly SharePoint review"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $PSScriptRoot "run_weekly_sharepoint_review.ps1"
$config = Join-Path $projectRoot "automation\config.json"

if (-not (Test-Path -LiteralPath $config)) {
    throw "Missing $config. First copy automation\\config.example.json to config.json and set staging_drop to the synced RV News Automation\\Incoming folder."
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument (
    "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -ConfigPath `"$config`""
)
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 8:30AM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# InteractiveToken deliberately avoids storing a password and means the job only
# runs after the work laptop is signed in. StartWhenAvailable catches a missed
# Monday while the laptop was asleep.
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal
Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null

Write-Host "Registered '$TaskName' for Mondays at 08:30."
