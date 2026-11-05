#!/usr/bin/env python3
"""Backup and optionally deploy ONLY additive RTDB error-report rules.

Never writes business data. Validates current live rules against the checked-in
baseline after removing the two NEW error rule branches. If another operator
changed existing rules, STOP instead of overwriting their changes.

Cloud Shell:
  python3 tools/firebase_error_rules_cutover.py
  python3 tools/firebase_error_rules_cutover.py --apply
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request,urlopen

PROJECT="alfa-erp-8700c"
RULES_URL="https://alfa-erp-8700c-default-rtdb.europe-west1.firebasedatabase.app/.settings/rules.json"
NEW_BRANCHES=("error_reports","error_acks")


def _oauth():
    result=subprocess.run(
        ["gcloud","auth","print-access-token"],
        check=True,capture_output=True,text=True,timeout=30)
    token=result.stdout.strip()
    if not token:raise RuntimeError("Google Cloud yetkilendirmesi bulunamadı")
    return token


def _rules_call(method,token,data=None):
    query=urlencode({"access_token":token})
    body=None if data is None else json.dumps(
        data,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    req=Request(RULES_URL+"?"+query,data=body,method=method,headers={
        "Accept":"application/json",
        **({"Content-Type":"application/json"} if body else {}),
    })
    try:
        with urlopen(req,timeout=35) as response:
            return json.loads(response.read())
    except HTTPError as error:
        raise RuntimeError(
            "Firebase Rules API erişimi reddedildi (HTTP "+
            str(error.code)+"). Yetkileri kontrol edin.") from None
    except (URLError,OSError,TimeoutError):
        raise RuntimeError("Firebase Rules API bağlantısı başarısız.") from None


def _without_extras(payload):
    clean=copy.deepcopy(payload)
    workspace=clean["rules"]["alfa"]["$workspace"]
    for node in NEW_BRANCHES:workspace.pop(node,None)
    return clean


def _backup(payload):
    root=Path.home()/"alfa_erp_private_backups"
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(root,0o700)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path=root/("rtdb_rules_before_error_inbox_"+stamp+".json")
    raw=json.dumps(payload,ensure_ascii=False,indent=2).encode("utf-8")
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as handle:handle.write(raw)
    digest=hashlib.sha256(raw).hexdigest()
    return path,digest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    active=subprocess.run(
        ["gcloud","config","get-value","project"],
        check=True,capture_output=True,text=True,timeout=20).stdout.strip()
    if active!=PROJECT:
        raise RuntimeError("Yanlış GCP projesi: "+active+". İşlem iptal.")
    source=Path(__file__).resolve().parents[1]/"firebase"/"database.rules.json"
    desired=json.loads(source.read_text(encoding="utf-8"))
    extra=desired["rules"]["alfa"]["$workspace"]
    if any(x not in extra for x in NEW_BRANCHES):
        raise RuntimeError("Hata raporu kuralları kaynak kodda eksik")
    token=_oauth()
    current=_rules_call("GET",token)
    if _without_extras(current)!=_without_extras(desired):
        raise RuntimeError(
            "CANLI kurallar ile depodaki önceki güvenlik kuralları farklı. "
            "Üzerine yazılmadı; önce farkları elle incele.")
    backup,digest=_backup(current)
    print("GCP projesi:",active)
    print("Canlı kuralların özel yedeği:",backup)
    print("SHA256:",digest)
    if current==desired:
        print("Hata raporu kuralları zaten yayında. İşlem gerekmiyor.")
        return 0
    if not args.apply:
        print("ÖN KONTROL BAŞARILI. Canlı Firebase değişmedi.")
        print("Yedek dosyasını güvenli bir yere kopyaladıktan sonra")
        print("  python3 tools/firebase_error_rules_cutover.py --apply")
        return 0
    if not sys.stdin.isatty():
        raise RuntimeError("Güvenlik kuralları için terminal onayı gerekli")
    print("Yalnız error_reports ve error_acks kuralları eklenecek.")
    print("Kitaplar, siparişler, stoklar, kullanıcılar SİLİNMEYECEK.")
    approve=input("Devam için ALFA-HATA-KURALLARINI-AC yaz: ").strip()
    if approve!="ALFA-HATA-KURALLARINI-AC":
        print("İptal edildi. Kurallar değiştirilmedi.")
        return 2
    # Re-read immediately before overwrite. Abort if live changed meanwhile.
    now=_rules_call("GET",token)
    if now!=current:
        raise RuntimeError("Ön kontrolden sonra canlı kurallar değişti; işlem iptal")
    _rules_call("PUT",token,desired)
    verified=_rules_call("GET",token)
    if verified!=desired:
        raise RuntimeError("Yayın sonrası Rules doğrulanamadı; yedeği kontrol et")
    print("FIREBASE ERROR RULES VERIFIED — Yalnız rapor erişimi açıldı.")
    return 0


if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception as exc:
        print("DURDURULDU:",str(exc),file=sys.stderr)
        raise SystemExit(1)
