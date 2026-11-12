$ErrorActionPreference = 'Stop'
$Source = $PSScriptRoot
$Install = Join-Path $env:LOCALAPPDATA 'Programs\ALFA ERP Personel'
try {
  if (-not (Test-Path $Install)) { New-Item -Path $Install -ItemType Directory -Force | Out-Null }
  if ([IO.Path]::GetFullPath($Source).TrimEnd('\') -ne [IO.Path]::GetFullPath($Install).TrimEnd('\')) {
    Get-ChildItem -LiteralPath $Source -Force | Where-Object { $_.Name -notin @('.venv','__pycache__') } | ForEach-Object {
      Copy-Item -LiteralPath $_.FullName -Destination $Install -Force -Recurse
    }
  }
  Set-Location -LiteralPath $Install
  $Python = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'
  $Launcher = Get-Command py.exe -ErrorAction SilentlyContinue
  if ($Launcher) {
    & py.exe -3.13 --version *> $null
    if ($LASTEXITCODE -eq 0) { $Python = 'py.exe'; $UsesLauncher=$true }
  }
  if ($Python -ne 'py.exe' -and -not (Test-Path $Python)) {
    Write-Host 'Python 3.13 otomatik kuruluyor (internet gerektirir)...'
    $PythonInstaller=Join-Path $env:TEMP 'python-3.13.17-amd64-alfa.exe'
    Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.13.17/python-3.13.17-amd64.exe' -OutFile $PythonInstaller -UseBasicParsing
    $Signature=Get-AuthenticodeSignature -FilePath $PythonInstaller
    if ($Signature.Status -ne 'Valid' -or $Signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
      throw 'Python resmi kurulum dosyası imzası doğrulanamadı.'
    }
    $target=Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313'
    $proc=Start-Process -FilePath $PythonInstaller -ArgumentList @('/quiet','InstallAllUsers=0','PrependPath=0','Include_launcher=1','Include_pip=1',"TargetDir=$target") -Wait -PassThru
    if($proc.ExitCode -ne 0) {throw "Python kurulamadı: $($proc.ExitCode)"}
    $Python=Join-Path $target 'python.exe'
    if(-not (Test-Path $Python)) {throw 'Python kurulum yolu bulunamadı.'}
  }
  $Virtual=Join-Path $Install '.venv\Scripts\python.exe'
  if(-not (Test-Path $Virtual)) {
    if ($Python -eq 'py.exe') { & py.exe -3.13 -m venv (Join-Path $Install '.venv') }
    else { & $Python -m venv (Join-Path $Install '.venv') }
    if($LASTEXITCODE -ne 0) {throw 'Python sanal ortamı oluşturulamadı.'}
  }
  Write-Host 'ALFA ERP gerekli bileşenleri kuruluyor...'
  & $Virtual -m pip install -r (Join-Path $Install 'requirements.txt') --disable-pip-version-check
  if($LASTEXITCODE -ne 0) {throw 'Python modülleri kurulamadı.'}
  Write-Host 'Firebase cihaz yetkisi uygulama içerisinden bir defa onaylanır.'
  $Pythonw=Join-Path $Install '.venv\Scripts\pythonw.exe'
  $ws=New-Object -ComObject WScript.Shell
  $link=Join-Path ([Environment]::GetFolderPath('Desktop')) 'ALFA ERP Personel.lnk'
  $sc=$ws.CreateShortcut($link);$sc.TargetPath=$Pythonw
  $sc.Arguments='"'+(Join-Path $Install 'main.py')+'"'
  $sc.WorkingDirectory=$Install;$sc.Description='ALFA ERP Personel';$sc.Save()
  Write-Host 'Kurulum tamamlandı. Masaüstü kısayolu oluşturuldu.'
  Start-Process -FilePath $Pythonw -ArgumentList ('"'+(Join-Path $Install 'main.py')+'"') -WorkingDirectory $Install
  exit 0
}
catch {
  Write-Host ('HATA: '+$_.Exception.Message) -ForegroundColor Red
  exit 1
}
