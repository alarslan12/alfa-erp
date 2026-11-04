param(
  [string]$DataRoot = '',
  [switch]$NoPairing,
  [switch]$NonInteractive
)
# ALFA ERP clean local reset: backup first; never touches cloud database.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if ($NonInteractive -and [string]::IsNullOrWhiteSpace($DataRoot)) {
  throw 'NonInteractive needs an explicit sandbox DataRoot.'
}
if ([string]::IsNullOrWhiteSpace($DataRoot)) {
  $local = [Environment]::GetFolderPath('LocalApplicationData')
  $DataRoot=Join-Path $local 'AlfaERP'
}
$DataRoot=[System.IO.Path]::GetFullPath($DataRoot)
$running=@(Get-Process -Name 'AlfaERP','AlfaERPYonetici','AlfaBildirim','AlfaBildirimServisi' -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
  throw 'Close ALFA ERP owner/staff and the notification agent before resetting.'
}
if (-not $NonInteractive) {
  Write-Host ''
  Write-Host 'ALFA ERP - TEMIZ YEREL BASLANGIC'
  Write-Host 'Cloud orders, stock, audit logs and database are NOT deleted.'
  Write-Host 'ALL local queues and cached data are backed up, not discarded.'
  Write-Host 'Backup folder is separate from the new empty app data folder.'
  if ($NoPairing) {
    Write-Host 'Device pairing token will NOT be carried over.'
  } else {
    Write-Host 'Existing Windows device pairing will be preserved if available.'
  }
  $answer=Read-Host 'To continue, type SIFIRLA'
  if ($answer -cne 'SIFIRLA') {
    Write-Host 'Cancelled; nothing changed.'
    return
  }
}
$parent=Split-Path -Parent $DataRoot
$backups=Join-Path $parent 'AlfaERP_Temiz_Kurulum_Yedekleri'
New-Item -ItemType Directory -Force -Path $backups | Out-Null
$stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
$destination=Join-Path $backups ('Onceki_Cihaz_Verisi_'+$stamp)
$suffix=1
while (Test-Path -LiteralPath $destination) {
  $destination=Join-Path $backups ('Onceki_Cihaz_Verisi_'+$stamp+'_'+$suffix)
  $suffix++
}
$tokenBytes=@{}
if (-not $NoPairing) {
  foreach ($tokenFile in @('alfa_cihaz.bin','alfa_owner_cihaz.bin')) {
    $existing=Join-Path $DataRoot $tokenFile
    if (Test-Path -LiteralPath $existing) {
      $tokenBytes[$tokenFile]=[System.IO.File]::ReadAllBytes($existing)
    }
  }
}
if (Test-Path -LiteralPath $DataRoot) {
  Move-Item -LiteralPath $DataRoot -Destination $destination -ErrorAction Stop
  Write-Host ('Archived existing local state in: '+$destination)
}
New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null
if ($tokenBytes.Count -gt 0) {
  foreach ($name in $tokenBytes.Keys) {
    [System.IO.File]::WriteAllBytes((Join-Path $DataRoot $name),$tokenBytes[$name])
  }
  Write-Host 'Existing staff/owner device authorizations were preserved.'
} else {
  Write-Host 'No device authorization copied; first-time cloud activation is available in app.'
}
Write-Host ('Clean local folder ready: '+$DataRoot)
Write-Host 'Cloud data and backups were NOT deleted.'
Write-Host 'Install the latest ALFA ERP Setup.exe, then open the application.'
