"""Read-only, opt-in local IPP printer telemetry (RFC 8010/8011).

Only Get-Printer-Attributes (0x000B) and Get-Job-Attributes (0x0009)
are sent. No Print-Job, Cancel-Job or Set-Printer operations exist.
Device job IDs must be linked manually: Windows JobId != IPP job-id.
An "impression" or "media sheet" counter does NOT prove a source PDF page.
"""
from __future__ import annotations

from datetime import datetime, timezone
import http.client
import ipaddress
import json
import os
from pathlib import Path
import ssl
import struct
from urllib.parse import urlsplit

MAX_IPP_BYTES = 256 * 1024
MAX_ATTR_BYTES = 8192
REQUESTED_PRINTER = (
    "printer-name", "printer-state", "printer-state-reasons",
    "printer-state-message", "queued-job-count",
    "printer-pages-completed", "printer-is-accepting-jobs"
)
REQUESTED_JOB = (
    "job-id", "job-name", "job-state", "job-state-reasons",
    "job-impressions", "job-impressions-completed",
    "job-media-sheets", "job-media-sheets-completed",
    "job-pages-completed",
    "job-state-message"
)
PRINTER_STATES = {3:"hazır", 4:"işleniyor", 5:"durdu"}
JOB_STATES = {
    3:"bekliyor",4:"beklemede",5:"işleniyor",6:"duraklatıldı",
    7:"iptal edildi",8:"durduruldu",9:"bitti (cihaz raporu)"
}


class IppTelemetryError(ValueError):
    pass


def _utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _endpoint(uri):
    """Require a deliberately configured LOCAL numeric-IP printer URI.

    IP literals eliminate DNS rebinding and cloud/Internet endpoints.
    No HTTP proxy, redirect, credential embedding, or TLS verification
    bypass is supported. IPPS requires a trusted certificate for the IP.
    """
    uri=str(uri or "").strip()
    try:
        u=urlsplit(uri)
        port=u.port or 631
        ip=ipaddress.ip_address(u.hostname or "")
    except ValueError as exc:
        raise IppTelemetryError(
            "IPP adresinde yerel IP kullan (örn. ipp://192.168.1.20/ipp/print)."
        ) from exc
    if (u.scheme not in ("ipp","ipps") or u.username or u.password
            or u.query or u.fragment or not u.path.startswith("/")
            or not 1<=port<=65535):
        raise IppTelemetryError("Yalnız ipp:// veya ipps:// ve yazıcı yolu geçerli.")
    if (not (ip.is_private or ip.is_loopback or ip.is_link_local)
            or ip.is_unspecified or ip.is_multicast
            or ip.is_reserved or getattr(ip,"scope_id",None)):
        raise IppTelemetryError("Yalnız özel ağda/yerel IPP yazıcısı izlenebilir.")
    if len(uri)>280 or len(u.path)>160:
        raise IppTelemetryError("IPP yazıcı adresi fazla uzun.")
    return u,port


def validate_uri(uri):
    _endpoint(uri)
    return str(uri).strip()


def _attr(tag,name,value,again=False):
    n=("" if again else name).encode("utf-8")
    raw=(value if isinstance(value,bytes)
         else str(value).encode("utf-8"))
    if len(n)>255 or len(raw)>MAX_ATTR_BYTES:
        raise IppTelemetryError("IPP isteği alanı çok büyük.")
    return bytes([tag])+struct.pack(">H",len(n))+n+struct.pack(">H",len(raw))+raw


def _request_body(operation,uri,fields,job_id=None):
    # IPP 2.0 header, requested operations only, request-id=1.
    if operation not in (0x0009,0x000A,0x000B):
        raise IppTelemetryError("Yazdırma komutu yasak; yalnız okuma yapılabilir.")
    data=bytearray(struct.pack(">BBHI",2,0,operation,1))
    data.append(0x01)  # operation-attributes-tag
    data+=_attr(0x47,"attributes-charset","utf-8")
    data+=_attr(0x48,"attributes-natural-language","en")
    data+=_attr(0x45,"printer-uri",uri)
    if job_id is not None:
        data+=_attr(0x21,"job-id",struct.pack(">I",int(job_id)))
    if operation==0x000A:  # Get-Jobs, read-only and strictly bounded
        data+=_attr(0x21,"limit",struct.pack(">I",20))
        data+=_attr(0x44,"which-jobs","not-completed")
    for index,name in enumerate(fields):
        data+=_attr(0x44,"requested-attributes",name,again=index>0)
    data.append(0x03)  # end-of-attributes-tag (no document data)
    return bytes(data)


def _parse_ipp(raw,grouped=False):
    if len(raw)<9 or len(raw)>MAX_IPP_BYTES:
        raise IppTelemetryError("IPP cevabı geçersiz veya çok büyük.")
    major,minor,code,request_id=struct.unpack_from(">BBHI",raw,0)
    if major not in (1,2) or request_id!=1:
        raise IppTelemetryError("Beklenmeyen IPP cevap sürümü/kimliği.")
    if code>=0x0100:
        raise IppTelemetryError("IPP yazıcısı okuma isteğini reddetti (0x%04x)." % code)
    cursor=8
    result={}
    current_name=None
    active_group=None
    group_kind=None
    output=[]
    count=0
    while cursor<len(raw):
        tag=raw[cursor]
        cursor+=1
        if tag==0x03:
            if grouped and group_kind is not None and active_group:
                output.append((group_kind,active_group))
            return output if grouped else result
        if tag<=0x0F:
            if grouped and group_kind is not None and active_group:
                output.append((group_kind,active_group))
            group_kind=tag
            active_group={} if grouped else None
            current_name=None
            continue
        if cursor+2>len(raw):
            raise IppTelemetryError("IPP cevap sınırı geçersiz.")
        length=struct.unpack_from(">H",raw,cursor)[0]
        cursor+=2
        if cursor+length+2>len(raw):
            raise IppTelemetryError("IPP alan adı kırpılmış.")
        name_bytes=raw[cursor:cursor+length]
        cursor+=length
        value_len=struct.unpack_from(">H",raw,cursor)[0]
        cursor+=2
        if value_len>MAX_ATTR_BYTES or cursor+value_len>len(raw):
            raise IppTelemetryError("IPP alan değeri geçersiz/çok büyük.")
        value=raw[cursor:cursor+value_len]
        cursor+=value_len
        count+=1
        if count>400:
            raise IppTelemetryError("IPP cevabı çok sayıda alan içeriyor.")
        if length:
            current_name=name_bytes.decode("utf-8","replace")[:120]
        if not current_name:
            continue
        if tag in (0x21,0x23) and len(value)==4:  # integer / enum
            decoded=struct.unpack(">i",value)[0]
        elif tag==0x22 and len(value)==1:
            decoded=bool(value[0])
        elif tag in (0x41,0x42,0x44,0x45,0x47,0x48,0x49,0x4A):
            decoded=value.decode("utf-8","replace")[:250]
        else:
            continue
        dest=active_group if grouped and active_group is not None else result
        original=dest.get(current_name)
        if original is None:
            dest[current_name]=decoded
        elif isinstance(original,list):
            if len(original)<25:original.append(decoded)
        else:
            dest[current_name]=[original,decoded]
    raise IppTelemetryError("IPP yanıtında bitiş etiketi yok.")


def _one(values,name):
    value=values.get(name)
    return value[0] if isinstance(value,list) else value


def _strings(values,name):
    value=values.get(name)
    return ([str(x)[:100] for x in value] if isinstance(value,list)
            else [str(value)[:100]] if value is not None else [])


class IppReader:
    """Local-IP-only, bounded read-only HTTP(S) IPP client."""

    def __init__(self,timeout=3.0):
        self.timeout=max(1.0,min(5.0,float(timeout)))

    def _read(self,uri,operation,fields,job_id=None,grouped=False):
        u,port=_endpoint(uri)
        body=_request_body(operation,uri,fields,job_id=job_id)
        host=str(u.hostname)
        conn=(http.client.HTTPSConnection(
                host,port,timeout=self.timeout,context=ssl.create_default_context())
              if u.scheme=="ipps" else
              http.client.HTTPConnection(host,port,timeout=self.timeout))
        try:
            # http.client never follows redirects; TLS certificates are
            # validated by the default SSLContext for IPPS.
            conn.request("POST",u.path,body,{
                "Content-Type":"application/ipp",
                "Accept":"application/ipp",
                "Connection":"close"
            })
            response=conn.getresponse()
            if response.status!=200:
                raise IppTelemetryError(
                    "IPP yazıcısı HTTP %d döndürdü; adres/yetkiyi kontrol edin."
                    % response.status)
            media_type=str(response.getheader("Content-Type") or "").lower()
            if "application/ipp" not in media_type:
                raise IppTelemetryError("Yazıcı IPP cevabı vermedi.")
            raw=response.read(MAX_IPP_BYTES+1)
            return _parse_ipp(raw,grouped=grouped)
        except (OSError,ssl.SSLError,http.client.HTTPException) as exc:
            raise IppTelemetryError("Yerel IPP yazıcısına erişilemedi: "+str(exc)[:150]) from exc
        finally:
            conn.close()

    def printer(self,uri):
        data=self._read(uri,0x000B,REQUESTED_PRINTER)
        state=_one(data,"printer-state")
        if not isinstance(state,int):
            raise IppTelemetryError("Cihaz IPP printer-state bilgisi sağlamıyor.")
        return {
            "source":"IPP doğrudan cihaz",
            "name":str(_one(data,"printer-name") or "")[:130],
            "state_code":state,
            "state":PRINTER_STATES.get(state,"bilinmiyor"),
            "reasons":_strings(data,"printer-state-reasons"),
            "message":str(_one(data,"printer-state-message") or "")[:160],
            "queued_jobs":_one(data,"queued-job-count"),
            "pages_completed":_one(data,"printer-pages-completed"),
            "accepting":_one(data,"printer-is-accepting-jobs"),
            "seen_at":_utc()
        }

    def jobs(self,uri):
        """List at most 20 unfinished device jobs (never spool commands).

        IPP returns one job-attributes group per job. This list is shown
        to the operator for explicit selection, not auto-matched by name.
        """
        groups=self._read(uri,0x000A,(
            "job-id","job-name","job-state",
            "job-impressions-completed","job-media-sheets-completed",
            "job-pages-completed"
        ),grouped=True)
        output=[]
        for kind,data in groups:
            if kind!=0x02:continue
            job_id=_one(data,"job-id")
            state=_one(data,"job-state")
            if not isinstance(job_id,int) or not 1<=job_id<2**31:
                continue
            output.append({
                "ipp_job_id":job_id,
                "name":str(_one(data,"job-name") or "Belge adı bilinmiyor")[:130],
                "state":JOB_STATES.get(state,"bilinmiyor"),
                "sheets":_one(data,"job-media-sheets-completed"),
                "impressions":_one(data,"job-impressions-completed"),
                "document_pages":_one(data,"job-pages-completed")
            })
            if len(output)>=20:break
        return output

    def job(self,uri,ipp_job_id):
        try:job_id=int(ipp_job_id)
        except (ValueError,TypeError) as exc:
            raise IppTelemetryError("IPP iş kimliği sayısal olmalı.") from exc
        if not 1<=job_id<2**31:
            raise IppTelemetryError("IPP iş kimliği geçersiz.")
        data=self._read(uri,0x0009,REQUESTED_JOB,job_id=job_id)
        returned=_one(data,"job-id")
        if returned!=job_id:
            raise IppTelemetryError("IPP yazıcısı farklı iş kimliği döndürdü.")
        state=_one(data,"job-state")
        if not isinstance(state,int):
            raise IppTelemetryError("Cihaz IPP iş durumu sağlamıyor.")
        return {
            "ipp_job_id":job_id,
            "state_code":state,
            "state":JOB_STATES.get(state,"bilinmiyor"),
            "reasons":_strings(data,"job-state-reasons"),
            "name":str(_one(data,"job-name") or "")[:130],
            "impressions":_one(data,"job-impressions-completed"),
            "sheets":_one(data,"job-media-sheets-completed"),
            "document_pages":_one(data,"job-pages-completed"),
            "message":str(_one(data,"job-state-message") or "")[:160],
            "seen_at":_utc()
        }


class IppSettings:
    """Opt-in endpoints, no secret credentials, saved on local machine only."""

    def __init__(self,data_dir):
        self.file=Path(data_dir)/"print_monitor"/"ipp_devices.json"

    def read(self):
        try:
            body=json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError,ValueError,TypeError):
            return {}
        if not isinstance(body,dict):return {}
        result={}
        for name,entry in list(body.items())[:16]:
            if not isinstance(name,str) or not isinstance(entry,str):continue
            try:
                result[name[:250]]=validate_uri(entry)
            except IppTelemetryError:
                pass
        return result

    def save(self,printers):
        allowed={}
        for name,url in list(printers.items())[:16]:
            if not str(name).strip():continue
            allowed[str(name)[:250]]=validate_uri(url)
        self.file.parent.mkdir(parents=True,exist_ok=True)
        temp=self.file.with_suffix(".tmp")
        temp.write_text(json.dumps(allowed,ensure_ascii=False,indent=2),
                        encoding="utf-8")
        os.replace(temp,self.file)
