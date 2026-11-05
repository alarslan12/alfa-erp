"""ALFA ERP secure-enough stable-release updater (no background polling).

Only public, non-prerelease GitHub Releases from alarslan12/alfa-erp are
accepted. Downloaded Windows setups require a matching SHA256SUMS.txt entry.
A detached PowerShell helper waits for the ERP to exit BEFORE installing.
No order data, authentication secret, device UID or customer file is uploaded.

IMPORTANT: Updates remain unavailable until the owner publishes a
durable GitHub Release with the unified setup and SHA256SUMS.txt.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

GITHUB_API="https://api.github.com/repos/alarslan12/alfa-erp/releases/latest"
REPO_PREFIX="https://github.com/alarslan12/alfa-erp/releases/download/"
UPDATE_HOSTS={
    "github.com","release-assets.githubusercontent.com",
    "objects.githubusercontent.com","github-releases.githubusercontent.com",
}
VERSION_PATTERN=re.compile(r"^v?([0-9]+)\.([0-9]+)\.([0-9]+)$")
MAX_SETUP_SIZE=230*1024*1024
MAX_CHECKSUM_SIZE=32768


class UpdateError(RuntimeError):
    pass


def version_tuple(value):
    match=VERSION_PATTERN.fullmatch(str(value or "").strip())
    if not match:
        raise UpdateError("Sürüm biçimi geçersiz")
    return tuple(int(item) for item in match.groups())


def _request(url,timeout=18):
    req=urllib.request.Request(url,headers={
        "Accept":"application/vnd.github+json",
        "User-Agent":"AlfaERP-Windows-Update/1",
        "X-GitHub-Api-Version":"2022-11-28"})
    return urllib.request.urlopen(req,timeout=timeout)


def _is_allowed_download(original,final):
    first=urllib.parse.urlparse(original)
    last=urllib.parse.urlparse(final)
    return (
        first.scheme=="https" and
        first.hostname=="github.com" and
        original.startswith(REPO_PREFIX) and
        last.scheme=="https" and last.hostname in UPDATE_HOSTS
    )


def _asset(assets,name,release_tag):
    for item in assets:
        if item.get("name")==name:
            url=str(item.get("browser_download_url") or "")
            prefix=REPO_PREFIX+urllib.parse.quote(release_tag,safe="")+"/"
            if not url.startswith(prefix):
                raise UpdateError("Güncelleme dosyası doğrulanamadı")
            if urllib.parse.urlparse(url).scheme!="https":
                raise UpdateError("Güncelleme dosyası HTTPS kullanmıyor")
            return {"name":name,"url":url,"size":int(item.get("size") or 0)}
    raise UpdateError("Kararlı sürümün gerekli dosyaları eksik: "+name)


def check_for_update(current,edition):
    """At most one GET to the public GitHub latest endpoint."""
    try:
        with _request(GITHUB_API) as response:
            if response.geturl()!=GITHUB_API:
                raise UpdateError("GitHub sürüm adresi değiştirildi")
            data=json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code==404:
            raise UpdateError(
                "GitHub'da henüz kalıcı kararlı sürüm yayımlanmadı. "
                "Yönetici Releases sayfasından yayınlamalı.") from None
        raise UpdateError("GitHub güncelleme servisi HTTP "+str(exc.code)) from None
    except (urllib.error.URLError,OSError,TimeoutError,ValueError):
        raise UpdateError("GitHub sürüm kontrolüne erişilemiyor") from None
    if data.get("draft") or data.get("prerelease"):
        raise UpdateError("Önizleme sürümleri otomatik yüklenmez")
    tag=str(data.get("tag_name") or "")
    available=version_tuple(tag)
    if available<=version_tuple(current):
        return {"available":False,"latest":tag}
    # Both editions are distributed in ONE setup; the user selects the
    # edition in the installer and owner installs require the setup password.
    version="_".join(str(x) for x in available)
    name=f"ALFA_ERP_Setup_V{version}.exe"
    assets=data.get("assets") or []
    installer=_asset(assets,name,tag)
    checksum=_asset(assets,"SHA256SUMS.txt",tag)
    if not 100000<=installer["size"]<=MAX_SETUP_SIZE:
        raise UpdateError("Güncelleme kurulum dosyasının boyutu geçersiz")
    return {
        "available":True,"latest":tag,"version":".".join(map(str,available)),
        "installer":installer,"checksum":checksum,
        "notes":str(data.get("body") or "")[:1400],
        "release_url":str(data.get("html_url") or ""),
    }


def _download_asset(asset,destination,max_bytes,progress=None):
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=".alfa_up_",suffix=".part",dir=destination.parent)
    total=0
    digest=hashlib.sha256()
    try:
        with os.fdopen(fd,"wb") as out, _request(asset["url"],timeout=35) as response:
            if not _is_allowed_download(asset["url"],response.geturl()):
                raise UpdateError("GitHub dışında güvenilmeyen bir indirme yönlendirmesi")
            while True:
                block=response.read(128*1024)
                if not block:break
                total+=len(block)
                if total>max_bytes:
                    raise UpdateError("Güncelleme boyut sınırını aşıyor")
                out.write(block);digest.update(block)
                if progress:
                    progress(total,asset.get("size") or 0)
        if total==0:
            raise UpdateError("İndirilen dosya boş")
        os.replace(name,destination)
        return digest.hexdigest()
    finally:
        if os.path.exists(name):
            os.unlink(name)



def _file_hash(path):
    digest=hashlib.sha256()
    with open(path,"rb") as reader:
        while True:
            chunk=reader.read(512*1024)
            if not chunk:break
            digest.update(chunk)
    return digest.hexdigest()


def _expected_checksum(content,filename):
    for line in content.splitlines():
        columns=line.strip().split(None,1)
        if len(columns)!=2:continue
        checksum,rawname=columns
        rawname=rawname.lstrip("*").strip()
        if rawname==filename and re.fullmatch(r"[a-fA-F0-9]{64}",checksum):
            return checksum.lower()
    raise UpdateError("Güvenilir SHA-256 listesinde kurulum dosyası bulunamadı")


def download_update(release,storage,progress=None):
    """Download verified installer, atomic rename, never execute arbitrary URL."""
    if not release.get("available"):
        raise UpdateError("İndirilecek daha yeni kararlı sürüm yok")
    target=Path(storage)/"updates"/str(release["version"])
    target.mkdir(parents=True,exist_ok=True)
    checksum_path=target/"SHA256SUMS.txt"
    _download_asset(release["checksum"],checksum_path,MAX_CHECKSUM_SIZE)
    expected=_expected_checksum(
        checksum_path.read_text(encoding="utf-8-sig"),
        release["installer"]["name"])
    setup=target/release["installer"]["name"]
    if setup.exists():
        sha=_file_hash(setup)
        if sha==expected:
            if progress:progress(setup.stat().st_size,setup.stat().st_size)
            return {"path":str(setup),"sha256":expected,
                    "version":release["version"]}
        setup.unlink()
    received=_download_asset(release["installer"],setup,MAX_SETUP_SIZE,progress)
    if received!=expected:
        setup.unlink(missing_ok=True)
        raise UpdateError("SHA-256 uyuşmuyor; indirme silindi")
    return {"path":str(setup),"sha256":expected,
            "version":release["version"]}


HELPER_PS=r'''
param(
    [Parameter(Mandatory=$true)][int]$ParentPid,
    [Parameter(Mandatory=$true)][string]$Setup,
    [Parameter(Mandatory=$true)][string]$Sha256,
    [Parameter(Mandatory=$true)][string]$TargetExe
)
$ErrorActionPreference = 'Stop'
try {
    # It is unsafe to replace an executable while the ERP is still running.
    try {
        Wait-Process -Id $ParentPid -Timeout 180 -ErrorAction Stop
    } catch {
        $process = Get-Process -Id $ParentPid -ErrorAction SilentlyContinue
        if ($process) { throw 'ERP did not exit; update cancelled' }
    }
    if (-not (Test-Path -LiteralPath $Setup -PathType Leaf)) { throw 'Installer missing' }
    $actual = (Get-FileHash -LiteralPath $Setup -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $Sha256.ToLowerInvariant()) { throw 'SHA256 verification failed' }
    # Unified setup MUST run interactively. In particular, the owner
    # password page must never be bypassed by a silent upgrade.
    $editionArg = if ([IO.Path]::GetFileName($TargetExe) -ieq 'AlfaERPYonetici.exe') {
        '/ALFAOWNER'
    } else { '/ALFASTAFF' }
    $p=Start-Process -FilePath $Setup -ArgumentList @(
        $editionArg,'/NORESTART','/CLOSEAPPLICATIONS'
    ) -PassThru -Wait
    if ($p.ExitCode -ne 0) { throw "Installer exited with $($p.ExitCode)" }
    if (Test-Path -LiteralPath $TargetExe -PathType Leaf) {
        Start-Process -FilePath $TargetExe
    }
} catch {
    # Local-only diagnostic; never send process paths to the cloud.
    $errorText='Update failed: '+$_.Exception.GetType().Name
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'last_update_error.txt'),$errorText)
    exit 1
}
'''


def launch_update(verified,storage,app_executable,pending=0):
    """Only after explicit user click, after all order writes are delivered."""
    if pending:
        raise UpdateError(
            f"{pending} işlem buluta gönderilmeyi bekliyor. "
            "Önce eşitlemenin bitmesini bekleyin.")
    if not getattr(sys,"frozen",False) or os.name!="nt":
        raise UpdateError("Otomatik yükleme yalnız kurulu Windows uygulamasında çalışır")
    exe=Path(app_executable).resolve()
    if exe.name.lower() not in ("alfaerp.exe","alfaerpyonetici.exe"):
        raise UpdateError("Bilinmeyen ALFA ERP uygulaması")
    setup=Path(str(verified["path"])).resolve()
    if setup.suffix.lower()!=".exe" or not setup.is_file():
        raise UpdateError("Güncelleme dosyası bulunamıyor")
    expected=str(verified.get("sha256") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}",expected):
        raise UpdateError("Güncelleme SHA-256 geçersiz")
    actual=_file_hash(setup)
    if actual!=expected:
        raise UpdateError("Güncelleme dosyası değişmiş; işlem iptal edildi")
    script_dir=Path(storage)/"updates"
    script_dir.mkdir(parents=True,exist_ok=True)
    script=script_dir/"alfa_safe_installer.ps1"
    script.write_text(HELPER_PS,encoding="utf-8")
    flags=(getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0) |
           getattr(subprocess,"DETACHED_PROCESS",0))
    subprocess.Popen(
        ["powershell.exe","-NoProfile","-NonInteractive",
         "-ExecutionPolicy","Bypass","-File",str(script),
         "-ParentPid",str(os.getpid()),"-Setup",str(setup),
         "-Sha256",expected,"-TargetExe",str(exe)],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,close_fds=True,creationflags=flags)
    return True
