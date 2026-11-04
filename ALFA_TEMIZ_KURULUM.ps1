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
$running=@(Get-Process -Name 'AlfaERP','AlfaERPYonetici','AlfaBildirimServisi' -ErrorAction SilentlyContinue)
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
$tokenBytes=$null
$originalToken=Join-Path $DataRoot 'alfa_cihaz.bin'
if (-not $NoPairing -and (Test-Path -LiteralPath $originalToken)) {
  $tokenBytes=[System.IO.File]::ReadAllBytes($originalToken)
}
if (Test-Path -LiteralPath $DataRoot) {
  Move-Item -LiteralPath $DataRoot -Destination $destination -ErrorAction Stop
  Write-Host ('Archived existing local state in: '+$destination)
}
New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null
if ($null -ne $tokenBytes) {
  [System.IO.File]::WriteAllBytes((Join-Path $DataRoot 'alfa_cihaz.bin'),$tokenBytes)
  Write-Host 'Windows pairing token copied to clean data folder.'
} else {
  Write-Host 'No existing pairing token copied; staff device may need enrollment.'
}
Write-Host ('Clean local folder ready: '+$DataRoot)
Write-Host 'Cloud data and backups were NOT deleted.'
Write-Host 'Install the latest ALFA ERP Setup.exe, then open the application.'
