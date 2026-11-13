# Per-user ALFA ERP order notifications, independent of the desktop ERP.
# Interactive Windows logon is required for tray popup / audio to be visible.
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [switch]$Remove
)
$ErrorActionPreference='Stop'
$taskName='ALFA_ERP_OrderNotifications'
$exe=[IO.Path]::GetFullPath($ExePath)
$existing=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($Remove) {
  # Do not remove a task belonging to a different installation.
  if ($existing) {
    $matchesExe=@($existing.Actions | Where-Object {
      [string]::Equals([IO.Path]::GetFullPath($_.Execute),$exe,
        [StringComparison]::OrdinalIgnoreCase)
    }).Count -gt 0
    if ($matchesExe) {
      Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
  }
  exit 0
}
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
  throw "Bildirim EXE bulunamadi: $exe"
}
$user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$action=New-ScheduledTaskAction -Execute $exe -WorkingDirectory ([IO.Path]::GetDirectoryName($exe))
$trigger=New-ScheduledTaskTrigger -AtLogOn -User $user
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2) -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Description 'ALFACOPYCENTER Firebase siparis bildirimleri (kullanici oturumu)' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
# Suite may be installed while logged in. The QLockFile suppresses duplicates.
Start-ScheduledTask -TaskName $taskName
Write-Output "ALFA notification task installed for $user"
