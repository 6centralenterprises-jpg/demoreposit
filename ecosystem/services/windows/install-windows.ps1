# Windows: install deps, run the API + dispatcher under pm2, and restore them at logon.
# Run in PowerShell from the ecosystem folder:  powershell -ExecutionPolicy Bypass -File services\windows\install-windows.ps1
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

if ($Root -match 'OneDrive|Dropbox|Google Drive|iCloud' -or $Root -like "$env:USERPROFILE\Desktop*" -or $Root -like "$env:USERPROFILE\Documents*") {
  Write-Error "$Root looks cloud-synced. Move the folder to C:\Ecosystem first, then rerun."
}

if (-not (Get-Command pm2 -ErrorAction SilentlyContinue)) { npm install -g pm2 }
Push-Location (Join-Path $Root 'mission-control-api'); npm install --omit=dev --foreground-scripts; Pop-Location
Push-Location $Root; pm2 start ecosystem.config.js; pm2 save; Pop-Location

# 'pm2 startup' does not work on Windows. A logon task runs 'pm2 resurrect' instead,
# through a headless console so no window flashes at login.
$pm2 = (Get-Command pm2.cmd).Source
$action = New-ScheduledTaskAction -Execute 'conhost.exe' -Argument "--headless cmd.exe /c `"$pm2`" resurrect"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0
Register-ScheduledTask -TaskName 'Ecosystem pm2 resurrect' -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "Done. Services are running and will come back at every logon."
pm2 ls
