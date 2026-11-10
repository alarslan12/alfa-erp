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


def _release_page_fallback(current, reason):
    """Fallback only through the official GitHub release redirect, never a mirror."""
    page="https://github.com/alarslan12/alfa-erp/releases/latest"
    request=urllib.request.Request(page,headers={
        "User-Agent":"ALFACOPYCENTER-Update/2",
        "Accept":"text/html"})
    try:
        with urllib.request.urlopen(request,timeout=20) as response:
            final=response.geturl()
            # GitHub may serve a page instead of redirecting. Never parse
            # untrusted arbitrary HTML to decide what executable to install.
            response.read(256)
    except urllib.error.HTTPError as exc:
        raise UpdateError(
            f"GitHub API kontrolü başarısız ({reason}); "
            f"GitHub sürüm sayfası da HTTP {exc.code} döndürdü.") from None
    except (urllib.error.URLError,TimeoutError,OSError) as exc:
        why=_network_error(exc)
        raise UpdateError(
            f"GitHub API kontrolü başarısız ({reason}); "
            f"GitHub sürüm sayfası da açılamadı ({why}).") from None
    prefix="https://github.com/alarslan12/alfa-erp/releases/tag/"
    if not final.startswith(prefix):
        raise UpdateError(
            f"GitHub API kontrolü başarısız ({reason}); "
            "alternatif sürüm adresi doğrulanamadı.")
    tag=urllib.parse.unquote(final[len(prefix):].strip("/"))
    try:
        available=version_tuple(tag)
    except UpdateError:
        raise UpdateError("GitHub sürüm etiketi geçersiz: "+tag[:45]) from None
    if available<=version_tuple(current):
        return {"available":False,"latest":tag}
    version="_".join(map(str,available))
    filename=(f"ALFACOPYCENTER_Suite_Setup_V{version}.exe"
              if available[0]>=2 else f"ALFA_ERP_Setup_V{version}.exe")
    url=REPO_PREFIX+urllib.parse.quote(tag,safe="")+"/"
    return {"available":True,"latest":tag,
            "version":".".join(map(str,available)),
            "installer":{"name":filename,"url":url+filename,"size":0},
            "checksum":{"name":"SHA256SUMS.txt",
                        "url":url+"SHA256SUMS.txt","size":0},
            "notes":"Resmî GitHub API erişimi kısıtlı. Sürüm etiketi "
                    "GitHub'ın kendi sürüm sayfasından doğrulandı; "
                    "güncelleme SHA-256 ile kontrol edilecektir.",
            "release_url":final}


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
    """Use the GitHub Releases API; fallback to a verified official redirect."""
    try:
        with _request(GITHUB_API) as response:
            if response.geturl()!=GITHUB_API:
                raise UpdateError("GitHub API farklı adrese yönlendirildi")
            data=json.load(response)
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,OSError,ValueError) as exc:
        return _release_page_fallback(current,_network_error(exc))
    if data.get("draft") or data.get("prerelease"):
        raise UpdateError("Önizleme sürümleri otomatik yüklenmez")
    tag=str(data.get("tag_name") or "")
    available=version_tuple(tag)
    running=version_tuple(current)
    if (running[0]==1 and available[0]>=6) or available<=running:
        return {"available":False,"latest":tag}
    version="_".join(str(x) for x in available)
    name=(f"ALFACOPYCENTER_Suite_Setup_V{version}.exe"
          if available[0]>=2 else f"ALFA_ERP_Setup_V{version}.exe")
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
    # One installer contains both editions. The existing edition is
    # preselected; the owner still enters the normal setup password.
    $editionArg = if ([IO.Path]::GetFileName($TargetExe) -ieq 'AlfaERPYonetici.exe') {
        '/ALFAOWNER'
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
