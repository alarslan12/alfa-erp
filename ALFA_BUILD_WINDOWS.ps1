param([ValidateSet('personel','yonetici','ortak')][string]$Edition='personel',[switch]$SkipInstaller)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
function Run([string]$exe,[string[]]$argv) {
 & $exe @argv
 if($LASTEXITCODE -ne 0) { throw "$exe işleminde hata: $LASTEXITCODE" }
}
$Python=$null
if(Get-Command py.exe -ErrorAction SilentlyContinue) {
 & py.exe -3.13 --version *> $null
 if($LASTEXITCODE -eq 0){$Python='py.exe'}
}
if(-not $Python -and (Get-Command python.exe -ErrorAction SilentlyContinue)) {
 & python.exe --version *> $null
 if($LASTEXITCODE -eq 0){$Python='python.exe'}
}
if(-not $Python) {
 if(-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
   throw 'Windows App Installer (winget) yok. Python 3.13 kurulumu icin winget gerekiyor.'
 }
 Write-Host 'Sadece derleme bilgisayarına Python kuruluyor...'
 Run 'winget.exe' @('install','-e','--id','Python.Python.3.13','--scope','user','--silent',
   '--accept-package-agreements','--accept-source-agreements')
 $p=Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'
 if(Test-Path $p){$Python=$p}else{$Python='py.exe'}
}
$Virtual=Join-Path $PSScriptRoot '.buildvenv\Scripts\python.exe'
if(-not (Test-Path $Virtual)) {
 if($Python -eq 'py.exe'){Run $Python @('-3.13','-m','venv','.buildvenv')}
 else {Run $Python @('-m','venv','.buildvenv')}
}
Run $Virtual @('-m','pip','install','--disable-pip-version-check','-r','requirements.txt','pyinstaller==6.16.0','Pillow==11.3.0')
# Generate branded multi-resolution .ico assets before PyInstaller and Inno Setup.
Run $Virtual @('tools\build_icons.py')
if($Edition -eq 'personel') {
 # Generic Firebase installer: no service credentials or private tickets
 # are embedded in executable assets.
 Run $Virtual @('-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
  '--name','AlfaERP','--icon=assets\icons\alfa_personel.ico','--add-data','KİTAPS.xlsx;.','--add-data','katalog.json;.',
  '--add-data','assets;assets','--hidden-import=PySide6.QtPdf','main.py')
 Run $Virtual @('-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
  '--name','AlfaBildirim','--icon=assets\icons\alfa_personel.ico',
  '--hidden-import=PySide6.QtTextToSpeech',
  '--hidden-import=PySide6.QtMultimedia','bildirim_servisi.py')
 Run $Virtual @('-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
  '--name','AlfaPrintAgent','--icon=assets\icons\alfa_print.ico',
  '--add-data','assets;assets','alfa_print_agent.py')
} elseif($Edition -eq 'yonetici') {
 Run $Virtual @('-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
  '--name','AlfaERPYonetici','--icon=assets\icons\alfa_yonetici.ico','--add-data','YONETICI_SURUMU.flag;.',
  '--add-data','KİTAPS.xlsx;.','--add-data','katalog.json;.',
  '--add-data','assets;assets','--hidden-import=PySide6.QtPdf','--hidden-import=yonetici_kompakt','main.py')

} else {
 throw 'ALFA_BUILD_WINDOWS.ps1 sadece ERP personel / yonetici bilesenlerini derler. Suite icin ALFA_BUILD_SUITE_WINDOWS.ps1 kullanin.'
}
if(-not $SkipInstaller) {
 Write-Host 'Tek dagitim bicimi Suite Setup. ALFA_BUILD_SUITE_WINDOWS.ps1 dosyasini kullanin.'
}
