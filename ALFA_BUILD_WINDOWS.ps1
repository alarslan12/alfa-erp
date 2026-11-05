param([ValidateSet('personel','yonetici')][string]$Edition='personel')
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
 # Generic Firebase installer: no secrets or legacy Supabase enrollment
 # tickets are embedded in executable assets.
 Run $Virtual @('-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
  '--name','AlfaERP','--icon=assets\icons\alfa_personel.ico','--add-data','KİTAPS.xlsx;.','--add-data','katalog.json;.',
  '--add-data','assets;assets','main.py')
 Run $Virtual @('-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
  '--name','AlfaBildirim','--icon=assets\icons\alfa_personel.ico','bildirim_servisi.py')
 $iss='alfa_personel.iss'
} else {
 Run $Virtual @('-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
  '--name','AlfaERPYonetici','--icon=assets\icons\alfa_yonetici.ico','--add-data','YONETICI_SURUMU.flag;.',
  '--add-data','KİTAPS.xlsx;.','--add-data','katalog.json;.',
  '--add-data','assets;assets','--hidden-import=yonetici_kompakt','main.py')
 $iss='alfa_yonetici.iss'
}
$Candidates=@(
 "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
 "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
 "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$Iscc=$Candidates | Where-Object {$_ -and (Test-Path $_)} | Select-Object -First 1
if(-not $Iscc) {
 if(-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
  throw 'Inno Setup 6 bulunamadı ve winget yok; sadece derleme bilgisayarına Inno Setup 6 kurulmalıdır.'
 }
 Write-Host 'Sadece derleme bilgisayarına Inno Setup kuruluyor...'
 Run 'winget.exe' @('install','-e','--id','JRSoftware.InnoSetup','--silent',
  '--accept-package-agreements','--accept-source-agreements')
 $Iscc=$Candidates | Where-Object {$_ -and (Test-Path $_)} | Select-Object -First 1
 if(-not $Iscc){throw 'Inno Setup kuruldu fakat ISCC.exe bulunamadı.'}
}
Run $Iscc @($iss)
Write-Host 'Tamamlandı: output klasöründe Windows Setup.exe oluşturuldu.'
