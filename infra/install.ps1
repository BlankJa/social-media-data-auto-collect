# 安装 Windows 定时任务（每天增量 + 每周日全量）。
# 用法：powershell -ExecutionPolicy Bypass -File infra\install.ps1
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..").Path
$uv = (Get-Command uv).Source

$dailyAction = New-ScheduledTaskAction -Execute $uv `
    -Argument "run python cli.py collect all" -WorkingDirectory $repo
$dailyTrigger = New-ScheduledTaskTrigger -Daily -At 8am
Register-ScheduledTask -TaskName "FudanCollectorDaily" `
    -Action $dailyAction -Trigger $dailyTrigger -Force

$weeklyAction = New-ScheduledTaskAction -Execute $uv `
    -Argument "run python cli.py collect all --full" -WorkingDirectory $repo
$weeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 9am
Register-ScheduledTask -TaskName "FudanCollectorWeekly" `
    -Action $weeklyAction -Trigger $weeklyTrigger -Force

Write-Host "✓ Registered FudanCollectorDaily and FudanCollectorWeekly"
