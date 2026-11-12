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

GITHUB_API="https://api.github.com/repos/alarslan12/alfa-erp/releases?per_page=100"
REPO_PREFIX="https://github.com/alarslan12/alfa-erp/releases/download/"
UPDATE_HOSTS={
    "github.com","release-assets.githubusercontent.com",
    "objects.githubusercontent.com","github-releases.githubusercontent.com",
}
VERSION_PATTERN=re.compile(r"^v?([0-9]+)\.([0-9]+)\.([0-9]+)$")
MAX_SETUP_SIZE=600*1024*1024
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


def _network_error(exc):
    if isinstance(exc,urllib.error.HTTPError):
        if exc.code==403:
            return "HTTP 403: engellenmiş veya API istek sınırı aşılmış"
        if exc.code==429:
            return "HTTP 429: GitHub istek sınırı"
        if exc.code==404:
            return "HTTP 404: yayımlanmış sürüm bulunamadı"
        return f"HTTP {exc.code}"
    reason=getattr(exc,"reason",exc)
    if isinstance(reason,TimeoutError):
        return "bağlantı zaman aşımı"
    message=str(reason).strip()
    if "CERTIFICATE_VERIFY_FAILED" in message or "certificate verify failed" in message:
        return "Windows/Python HTTPS sertifika doğrulaması başarısız"
    if "getaddrinfo failed" in message or "Name or service not known" in message:
        return "DNS alan adı çözümlenemedi"
    if "timed out" in message.lower():
        return "bağlantı zaman aşımı"
    if "proxy" in message.lower():
        return "proxy bağlantı hatası"
    if "refused" in message.lower():
        return "bağlantı reddedildi"
    if "reset" in message.lower():
        return "bağlantı sıfırlandı"
    return (message or type(reason).__name__)[:145]


def check_for_update(current,edition):
    """Find the newest stable *Suite* release, ignoring unrelated legacy tags.

    GitHub /releases/latest can point to the separate v6 ERP release, which
    would permanently break v2 Suite update discovery.
    """
    try:
        with _request(GITHUB_API) as response:
            if response.geturl()!=GITHUB_API:
                raise UpdateError("GitHub sürüm adresi farklı yere yönlendirildi")
            releases=json.load(response)
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,OSError,ValueError) as exc:
        raise UpdateError("Suite sürüm listesi alınamadı: "+_network_error(exc)) from None
    if not isinstance(releases,list):
        raise UpdateError("GitHub sürüm listesi geçersiz")
    running=version_tuple(current)
    valid=[]
    for entry in releases:
        if not isinstance(entry,dict) or entry.get("draft") or entry.get("prerelease"):
            continue
        tag=str(entry.get("tag_name") or "")
        try:
            version=version_tuple(tag)
        except UpdateError:
            continue
        # v1 was the previous edition-selectable ERP, v6 is obsolete/other.
        # Only v2+ Suite assets participate in the unified Suite channel.
        if version[0]!=2:
            continue
        name="ALFACOPYCENTER_Suite_Setup_V"+"_".join(str(n) for n in version)+".exe"
        asset_names={str(a.get("name")) for a in (entry.get("assets") or [])
                     if isinstance(a,dict)}
        if name not in asset_names or "SHA256SUMS.txt" not in asset_names:
            continue
        valid.append((version,entry,name))
    if not valid:
        return {"available":False,"latest":None}
    version,entry,name=max(valid,key=lambda x:x[0])
    tag=str(entry.get("tag_name") or "")
    if version<=running:
        return {"available":False,"latest":tag}
    installer=_asset(entry["assets"],name,tag)
    checksum=_asset(entry["assets"],"SHA256SUMS.txt",tag)
    if not 100000<=installer["size"]<=MAX_SETUP_SIZE:
        raise UpdateError("Suite kurulum dosyasının boyutu geçersiz")
    if not 1<=checksum["size"]<=MAX_CHECKSUM_SIZE:
        raise UpdateError("Suite SHA-256 dosyasının boyutu geçersiz")
    return {
        "available":True,"latest":tag,
        "version":".".join(str(n) for n in version),
        "installer":installer,"checksum":checksum,
        "notes":str(entry.get("body") or "")[:1400],
        "release_url":str(entry.get("html_url") or ""),
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
    [Parameter(Mandatory=$true)][string]$TargetExe,
    [Parameter(Mandatory=$true)][string]$StatusFile
)
$ErrorActionPreference = 'Stop'
$ErrorFile = Join-Path $PSScriptRoot 'last_update_error.txt'
function Write-UpdateStatus([string]$message) {
    [IO.File]::WriteAllText($StatusFile, $message, [Text.Encoding]::UTF8)
}
try {
    Write-UpdateStatus 'ERP uygulamasinin kapanmasi bekleniyor'
    # Exit of the real QMainWindow is required; an open modal update dialog
    # used to leave the ERP process running while this helper waited.
    if (Get-Process -Id $ParentPid -ErrorAction SilentlyContinue) {
        try {
            Wait-Process -Id $ParentPid -Timeout 45 -ErrorAction Stop
        } catch {
            if (Get-Process -Id $ParentPid -ErrorAction SilentlyContinue) {
                throw 'ALFA ERP kapanamadi; kurulum baslatilmadi.'
            }
        }
    }
    Write-UpdateStatus 'Kurulum dosyasi yeniden dogrulaniyor'
    if (-not (Test-Path -LiteralPath $Setup -PathType Leaf)) {
        throw 'Indirilen kurulum dosyasi artik bulunamiyor.'
    }
    $actual = (Get-FileHash -LiteralPath $Setup -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $Sha256.ToLowerInvariant()) {
        throw 'SHA-256 uyusmuyor; kurulum iptal edildi.'
    }
    # One Suite installer contains all components. Inno retains the
    # previously selected components without any embedded admin password.
    $editionArg = if ([IO.Path]::GetFileName($TargetExe) -ieq 'AlfaERPYonetici.exe') {
        '/ALFAOWNER'
    } elseif ([IO.Path]::GetFileName($TargetExe) -ieq 'AlfaBannerStudio.exe') {
        '/ALFABANNER'
    } elseif ([IO.Path]::GetFileName($TargetExe) -ieq 'AlfaPrintSurveillance.exe') {
        '/ALFAPRINT'
    } else {
        '/ALFASTAFF'
    }
    Write-UpdateStatus 'Windows kurulum sihirbazi aciliyor'
    $p = Start-Process -FilePath $Setup -ArgumentList @(
        $editionArg, '/ALFAUPDATE', '/NORESTART', '/CLOSEAPPLICATIONS'
    ) -PassThru -Wait -ErrorAction Stop
    if ($p.ExitCode -ne 0) {
        throw "Kurulum tamamlanmadi (cikis kodu $($p.ExitCode))."
    }
    # A v1->v2 upgrade installs to the new suite directory without
    # deleting the old data/EXE. Start the newly installed edition,
    # NEVER silently start the obsolete v1 binary.
    $suiteRoot = Join-Path $env:LOCALAPPDATA 'Programs\ALFACOPYCENTER'
    $suiteExe = if ($editionArg -eq '/ALFAOWNER') {
        Join-Path $suiteRoot 'Owner\AlfaERPYonetici.exe'
    } elseif ($editionArg -eq '/ALFABANNER') {
        Join-Path $suiteRoot 'BannerStudio\AlfaBannerStudio.exe'
    } elseif ($editionArg -eq '/ALFAPRINT') {
        Join-Path $suiteRoot 'PrintSurveillance\AlfaPrintSurveillance.exe'
    } else {
        Join-Path $suiteRoot 'Staff\AlfaERP.exe'
    }
    if (Test-Path -LiteralPath $suiteExe -PathType Leaf) {
        $TargetExe = $suiteExe
    }
    if (-not (Test-Path -LiteralPath $TargetExe -PathType Leaf)) {
        throw 'Kurulum bitti ama uygulamanin EXE dosyasi bulunamadi.'
    }
    Write-UpdateStatus 'ALFA ERP yeniden baslatiliyor'
    Start-Process -FilePath $TargetExe -WorkingDirectory (Split-Path -Parent $TargetExe) -ErrorAction Stop
    Write-UpdateStatus 'Tamamlandi'
    if (Test-Path -LiteralPath $ErrorFile) {
        Remove-Item -LiteralPath $ErrorFile -Force -ErrorAction SilentlyContinue
    }
} catch {
    # Detailed enough for local troubleshooting; never uploaded to Firebase.
    $message = [string]$_.Exception.Message
    if ($message.Length -gt 350) { $message = $message.Substring(0,350) }
    [IO.File]::WriteAllText($ErrorFile, $message, [Text.Encoding]::UTF8)
    Write-UpdateStatus ('HATA: ' + $message)
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
    if exe.name.lower() not in ("alfaerp.exe","alfaerpyonetici.exe","alfabannerstudio.exe","alfaprintsurveillance.exe"):
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
    status_path=script_dir/"last_update_status.txt"
    status_path.write_text("Güncelleme yardımcısı başlatılıyor",encoding="utf-8")
    # A previous failed attempt must not masquerade as the new attempt.
    (script_dir/"last_update_error.txt").unlink(missing_ok=True)
    # CREATE_NO_WINDOW hides PowerShell only; Inno Setup's interactive
    # edition/password wizard remains visible in the logged-in desktop.
    flags=(getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0) |
           getattr(subprocess,"CREATE_NO_WINDOW",0))
    helper=subprocess.Popen(
        ["powershell.exe","-NoProfile","-NonInteractive",
         "-ExecutionPolicy","Bypass","-File",str(script),
         "-ParentPid",str(os.getpid()),"-Setup",str(setup),
         "-Sha256",expected,"-TargetExe",str(exe),
         "-StatusFile",str(status_path)],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,close_fds=True,creationflags=flags)
    if helper.pid is None:
        raise UpdateError("Windows güncelleme yardımcısı başlatılamadı")
    return True
