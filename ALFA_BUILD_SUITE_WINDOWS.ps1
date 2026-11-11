param([switch]$SkipInstaller)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Run([string]$exe,[string[]]$argv) {
  & $exe @argv
  if ($LASTEXITCODE -ne 0) {
    throw "Build failed: $exe (exit $LASTEXITCODE)"
  }
}

# The existing owner/staff sources remain the ERP source of truth.
# Build their EXEs first, without publishing any old v1 setup.
& .\ALFA_BUILD_WINDOWS.ps1 -Edition yonetici -SkipInstaller
if ($LASTEXITCODE -ne 0) { throw 'Owner ERP build failed' }
& .\ALFA_BUILD_WINDOWS.ps1 -Edition personel -SkipInstaller
if ($LASTEXITCODE -ne 0) { throw 'Staff ERP / print agent build failed' }

$python = Join-Path $PSScriptRoot '.buildvenv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Missing Python build environment' }
Run $python @('tools\build_icons.py')

# Tiny user-session watchdog. It requires no Qt UI and never runs
# with higher privileges than the account installing the suite.
Run $python @(
  '-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
  '--name','AlfaPrintSupervisor',
  '--icon=assets\icons\alfa_print.ico',
  'alfa_print_supervisor.py'
)

# Bundle the self-contained browser editor. It serves ONLY 127.0.0.1.
# Each user keeps previous covers, prices and layout history in LOCALAPPDATA.
Run $python @(
  '-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
  '--name','AlfaBannerStudio',
  '--icon=assets\icons\alfa_banner.ico',
  '--paths','banner_studio',
  '--paths','.',
  '--add-data','banner_studio\static;static',
  '--add-data','KİTAPS.xlsx;ornek',
  '--add-data','assets\branding;assets\branding',
  'banner_studio\studio_server.py'
)

# The visible multi-printer dashboard; the background agent is a separate
# user-session process whose startup requires explicit installer selection.
Run $python @(
  '-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
  '--name','AlfaPrintSurveillance',
  '--icon=assets\icons\alfa_print.ico',
  '--add-data','assets;assets',
  'alfa_print_standalone.py'
)

foreach ($needed in @(
  'dist\AlfaERP\AlfaERP.exe',
  'dist\AlfaERPYonetici\AlfaERPYonetici.exe',
  'dist\AlfaBildirim\AlfaBildirim.exe',
  'dist\AlfaBannerStudio\AlfaBannerStudio.exe',
  'dist\AlfaPrintSurveillance\AlfaPrintSurveillance.exe',
  'dist\AlfaPrintAgent\AlfaPrintAgent.exe',
  'dist\AlfaPrintSupervisor\AlfaPrintSupervisor.exe',
  'assets\icons\alfa_company.ico'
)) {
  if (-not (Test-Path $needed)) {
    throw "Missing suite component: $needed"
  }
}

if ($SkipInstaller) {
  Write-Host 'All four desktop apps + optional agent built (no installer).'
  return
}

$candidates = @(
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
  "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $candidates | Where-Object { $_ -and (Test-Path $_) } |
  Select-Object -First 1
if (-not $iscc) { throw 'Inno Setup 6 ISCC.exe is required' }

Run $iscc @('ALFACOPYCENTER_Suite.iss')
$setup = Join-Path $PSScriptRoot 'output\ALFACOPYCENTER_Suite_Setup_V2_0_8.exe'
if (-not (Test-Path $setup)) { throw 'Suite Setup.exe not created' }
Get-FileHash -Path $setup -Algorithm SHA256 | Format-Table
Write-Host "ALFACOPYCENTER suite ready: $setup"
