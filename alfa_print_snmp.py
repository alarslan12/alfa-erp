"""ALFA ERP: bounded, read-only SNMPv2c Printer-MIB probe for local printers.

Designed for EPSON and Canon but works with standard Printer-MIB devices.
Only GET (0xA0) and GETBULK (0xA5) are encoded; SET/TRAP are impossible.
SNMPv2c sends community in PLAINTEXT on the LAN. It must be enabled only
by explicit operator choice on a trusted private network. Prefer IPP/IPPS
or SNMPv3 when the printer supports them; SNMPv3 is NOT implemented here.

Community strings are encrypted using Windows user-scope DPAPI at rest,
never logged, sent to Firebase, or embedded in a packaged EXE.
All responses, lengths, packet counts, IPs and read rate are bounded.
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
from datetime import datetime,timezone
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import struct

MAX_RESPONSE=16384
MAX_STR=180
TIMEOUT=1.5
OIDS={
    "sys_descr":(1,3,6,1,2,1,1,1,0),
    "sys_object":(1,3,6,1,2,1,1,2,0),
    "sys_name":(1,3,6,1,2,1,1,5,0),
    "printer_name":(1,3,6,1,2,1,43,5,1,1,16),
    "life_count":(1,3,6,1,2,1,43,10,2,1,4),
    "supplies_desc":(1,3,6,1,2,1,43,11,1,1,6),
    "supplies_capacity":(1,3,6,1,2,1,43,11,1,1,8),
    "supplies_level":(1,3,6,1,2,1,43,11,1,1,9),
    "alert_severity":(1,3,6,1,2,1,43,18,1,1,2),
    "alert_desc":(1,3,6,1,2,1,43,18,1,1,8),
}
EPSON_ENTERPRISE=(1,3,6,1,4,1,1248)
CANON_ENTERPRISE=(1,3,6,1,4,1,1602)


class SnmpTelemetryError(RuntimeError):
    pass


def _utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def private_ip(raw):
    value=str(raw or "").strip()
    try:
        addr=ipaddress.ip_address(value)
    except ValueError as exc:
        raise SnmpTelemetryError("SNMP için yerel sayısal yazıcı IP adresi gerekli.") from exc
    if (not (addr.is_private or addr.is_loopback or addr.is_link_local)
            or addr.is_unspecified or addr.is_multicast or addr.is_reserved):
        raise SnmpTelemetryError("Yalnız yerel/özel ağ IP adreslerine SNMP sorgulanabilir.")
    return str(addr)


def _length(n):
    if n<0 or n>65535:
        raise SnmpTelemetryError("SNMP alanı çok büyük.")
    if n<128:return bytes((n,))
    if n<256:return b"\x81"+bytes((n,))
    return b"\x82"+n.to_bytes(2,"big")


def _tlv(tag,data):
    return bytes((tag,))+_length(len(data))+data


def _signed(value):
    value=int(value)
    size=max(1,(value.bit_length()+8)//8)
    return _tlv(0x02,value.to_bytes(size,"big",signed=True))


def _decode_oid(oid):
    if len(oid)<2 or oid[0]>2 or any(
            not isinstance(n,int) or n<0 or n>0xffffffff for n in oid):
        raise SnmpTelemetryError("Geçersiz SNMP OID.")
    if oid[0]<2 and oid[1]>39:
        raise SnmpTelemetryError("Geçersiz SNMP OID ikinci dalı.")
    out=bytearray()
    for value in (40*oid[0]+oid[1],*oid[2:]):
        packed=[value&0x7f]
        value>>=7
        while value:
            packed.append((value&0x7f)|0x80)
            value>>=7
        out+=bytes(reversed(packed))
    return bytes(out)


def _oid(components):
    return _tlv(0x06,_decode_oid(tuple(components)))


def _parse_oid(blob):
    if not blob:return ()
    numbers=[]
    current=0
    for byte in blob:
        current=(current<<7)|(byte&0x7f)
        if current>0xffffffff:
            raise SnmpTelemetryError("SNMP OID uzunluğu sınırı aşıldı.")
        if not byte&0x80:
            if not numbers:
                if current<40:numbers.extend((0,current))
                elif current<80:numbers.extend((1,current-40))
                else:numbers.extend((2,current-80))
            else:numbers.append(current)
            current=0
    if blob[-1]&0x80:
        raise SnmpTelemetryError("Eksik SNMP OID.")
    return tuple(numbers)


def _read(buf,pos=0):
    if pos>=len(buf):raise SnmpTelemetryError("Eksik SNMP alanı.")
    tag=buf[pos];pos+=1
    if pos>=len(buf):raise SnmpTelemetryError("Eksik SNMP alan uzunluğu.")
    size=buf[pos];pos+=1
    if size&0x80:
        width=size&0x7f
        if width==0 or width>2 or pos+width>len(buf):
            raise SnmpTelemetryError("Geçersiz SNMP uzunluğu.")
        size=int.from_bytes(buf[pos:pos+width],"big")
        pos+=width
    end=pos+size
    if end>len(buf) or size>MAX_RESPONSE:
        raise SnmpTelemetryError("SNMP veri uzunluğu sınır dışı.")
    return tag,buf[pos:end],end


def _value(tag,raw):
    if tag in (0x02,0x41,0x42,0x43,0x46):
        if len(raw)<1 or len(raw)>8:
            raise SnmpTelemetryError("Sayısal SNMP cevap biçimi hatalı.")
        return int.from_bytes(raw,"big",signed=tag==0x02)
    if tag==0x04:
        return raw.decode("utf-8","replace")[:MAX_STR]
    if tag==0x06:
        return _parse_oid(raw)
    if tag in (0x05,0x80,0x81,0x82):
        return None
    return None


def _decode_response(blob,expected_id):
    if len(blob)>MAX_RESPONSE:raise SnmpTelemetryError("SNMP cevabı aşırı büyük.")
    tag,outer,at=_read(blob)
    if tag!=0x30 or at!=len(blob):raise SnmpTelemetryError("Geçersiz SNMP cevap zarfı.")
    tag,version,i=_read(outer)
    if tag!=0x02 or int.from_bytes(version,"big",signed=True)!=1:
        raise SnmpTelemetryError("SNMPv2c dışı cevap alındı.")
    tag,community,i=_read(outer,i)
    if tag!=0x04:raise SnmpTelemetryError("SNMP community alanı eksik.")
    tag,pdu,i=_read(outer,i)
    if tag!=0xA2:raise SnmpTelemetryError("SNMP GET cevabı değil.")
    tag,rid,j=_read(pdu)
    if tag!=0x02 or int.from_bytes(rid,"big",signed=True)!=expected_id:
        raise SnmpTelemetryError("SNMP cevap iş kimliği uyuşmuyor.")
    tag,error,j=_read(pdu,j)
    code=int.from_bytes(error,"big",signed=True)
    if code:
        raise SnmpTelemetryError("SNMP yazıcı okuma isteğini reddetti (hata %d)." % code)
    _,_,j=_read(pdu,j)  # error index
    tag,varbinds,j=_read(pdu,j)
    if tag!=0x30:raise SnmpTelemetryError("SNMP değişken listesi eksik.")
    rows=[];pos=0
    while pos<len(varbinds) and len(rows)<24:
        tag,pair,pos=_read(varbinds,pos)
        if tag!=0x30:raise SnmpTelemetryError("Geçersiz SNMP alan çifti.")
        tag,name,k=_read(pair)
        if tag!=0x06:raise SnmpTelemetryError("SNMP OID eksik.")
        oid=_parse_oid(name)
        tag,value,k=_read(pair,k)
        rows.append((oid,_value(tag,value)))
    return rows


def _snmp_packet(community,oid,operation,request_id):
    if operation not in (0xA0,0xA5):
        raise SnmpTelemetryError("SNMP yalnız GET/GETBULK için yetkilidir.")
    varbind=_tlv(0x30,_oid(oid)+_tlv(0x05,b""))
    pdu=(_signed(request_id)+_signed(0)+
         _signed(6 if operation==0xA5 else 0)+
         _tlv(0x30,varbind))
    return _tlv(0x30,_signed(1)+_tlv(0x04,community.encode("utf-8"))+
                _tlv(operation,pdu))


class SnmpReader:
    def __init__(self,timeout=TIMEOUT):
        self.timeout=min(3.0,max(0.5,float(timeout)))

    def _ask(self,ip,community,oid,op):
        private_ip(ip)
        community=str(community or "")
        if not 1<=len(community.encode("utf-8"))<=64:
            raise SnmpTelemetryError("SNMP community 1-64 bayt olmalı.")
        request_id=secrets.randbelow(0x7fffffff)+1
        packet=_snmp_packet(community,oid,op,request_id)
        family=socket.AF_INET6 if ":" in ip else socket.AF_INET
        try:
            with socket.socket(family,socket.SOCK_DGRAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((ip,161))
                sock.send(packet)
                raw=sock.recv(MAX_RESPONSE+1)
        except (OSError,TimeoutError) as exc:
            raise SnmpTelemetryError("SNMP cihazı yanıtlamadı/erişilemiyor.") from exc
        return _decode_response(raw,request_id)

    def _get(self,ip,community,oid):
        rows=self._ask(ip,community,oid,0xA0)
        if not rows or rows[0][0]!=oid:
            return None
        return rows[0][1]

    def _walk(self,ip,community,oid,limit=6):
        rows=self._ask(ip,community,oid,0xA5)
        return [(key[len(oid):],value) for key,value in rows
                if len(key)>len(oid) and key[:len(oid)]==oid][:limit]

    def snapshot(self,ip,community):
        ip=private_ip(ip)
        values={}
        for name in ("sys_descr","sys_object","sys_name"):
            try:values[name]=self._get(ip,community,OIDS[name])
            except SnmpTelemetryError:
                if name=="sys_descr":raise
                values[name]=None
        enterprise=values.get("sys_object")
        brand=("Epson" if isinstance(enterprise,tuple)
               and enterprise[:len(EPSON_ENTERPRISE)]==EPSON_ENTERPRISE
               else "Canon" if isinstance(enterprise,tuple)
               and enterprise[:len(CANON_ENTERPRISE)]==CANON_ENTERPRISE
               else "Bilinmiyor")
        tables={}
        for name in ("printer_name","alert_desc","supplies_desc",
                     "supplies_capacity","supplies_level","life_count"):
            try:tables[name]=dict(self._walk(ip,community,OIDS[name]))
            except SnmpTelemetryError:tables[name]={}
        supplies=[]
        for key,label in list(tables["supplies_desc"].items())[:6]:
            level=tables["supplies_level"].get(key)
            cap=tables["supplies_capacity"].get(key)
            ratio=(round(100*level/cap) if isinstance(level,int) and
                   isinstance(cap,int) and 0<=level and cap>0 else None)
            supplies.append({
                "name":str(label)[:100], "level":level, "capacity":cap,
                "percent":min(100,max(0,ratio)) if ratio is not None else None
            })
        alerts=[str(v)[:120] for v in tables["alert_desc"].values() if v]
        return {
            "source":"SNMPv2c · Printer-MIB (yalnız okuma)",
            "status":"erişilebilir",
            "brand":brand,
            "model":str(values.get("sys_descr") or "")[:150],
            "sys_name":str(values.get("sys_name") or "")[:80],
            "enterprise_oid":".".join(map(str,enterprise or ())),
            "printer_name":next(iter(tables["printer_name"].values()),""),
            "life_count":next(iter(tables["life_count"].values()),None),
            "supplies":supplies,
            "alerts":alerts[:6],
            "seen_at":_utc(),
            "counter_note":"Cihazın toplam sayacı son PDF sayfasını belirlemez"
        }


# Encrypt SNMPv2c community per Windows USER. Never print or log secrets.
class _Blob(ctypes.Structure):
    _fields_=[("size",wintypes.DWORD),("ptr",ctypes.POINTER(ctypes.c_byte))]


def _dpapi(data,protect):
    if os.name!="nt":
        raise SnmpTelemetryError("Community depolama Windows DPAPI gerektirir.")
    crypto=ctypes.WinDLL("crypt32.dll",use_last_error=True)
    func=crypto.CryptProtectData if protect else crypto.CryptUnprotectData
    if protect:
        func.argtypes=[ctypes.POINTER(_Blob),wintypes.LPCWSTR,
                       ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,
                       wintypes.DWORD,ctypes.POINTER(_Blob)]
    else:
        func.argtypes=[ctypes.POINTER(_Blob),ctypes.c_void_p,
                       ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,
                       wintypes.DWORD,ctypes.POINTER(_Blob)]
    func.restype=wintypes.BOOL
    kernel=ctypes.WinDLL("kernel32.dll",use_last_error=True)
    kernel.LocalFree.argtypes=[ctypes.c_void_p]
    kernel.LocalFree.restype=ctypes.c_void_p
    raw=ctypes.create_string_buffer(data,len(data))
    src=_Blob(len(data),ctypes.cast(raw,ctypes.POINTER(ctypes.c_byte)))
    out=_Blob()
    if protect:
        ok=func(ctypes.byref(src),"ALFA ERP SNMP community",
                None,None,None,1,ctypes.byref(out))
    else:
        ok=func(ctypes.byref(src),None,None,None,None,1,ctypes.byref(out))
    if not ok:
        raise SnmpTelemetryError("Windows community koruması açılamadı.")
    try:return ctypes.string_at(out.ptr,out.size)
    finally:kernel.LocalFree(out.ptr)


class SnmpSettings:
    """Local opt-in per-printer SNMPv2c endpoints; DPAPI community."""

    def __init__(self,data_dir):
        self.file=Path(data_dir)/"print_monitor"/"snmp_devices.json"

    def _raw(self):
        try:
            body=json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError,ValueError,TypeError):
            return {}
        return body if isinstance(body,dict) else {}

    def read(self):
        result={}
        for name,entry in list(self._raw().items())[:16]:
            if not isinstance(name,str) or not isinstance(entry,dict):
                continue
            try:
                ip=private_ip(entry.get("ip"))
                cipher=base64.b64decode(entry["community_dpapi"],validate=True)
                comm=_dpapi(cipher,False).decode("utf-8")
                if not comm or len(comm)>64:continue
                result[name]={"ip":ip,"community":comm}
            except (SnmpTelemetryError,KeyError,ValueError,UnicodeError):
                continue
        return result

    def names(self):
        return {str(name):str(item.get("ip") or "")
                for name,item in self._raw().items()
                if isinstance(item,dict) and item.get("ip")}

    def set(self,printer,ip,community):
        name=str(printer or "").strip()[:250]
        ip=private_ip(ip)
        community=str(community or "")
        if not name or not 1<=len(community.encode("utf-8"))<=64:
            raise SnmpTelemetryError("Yazıcı adı ve SNMP community zorunludur.")
        entries=self._raw()
        if name not in entries and len(entries)>=16:
            raise SnmpTelemetryError("En fazla 16 SNMP yazıcısı tanımlanabilir.")
        protected=_dpapi(community.encode("utf-8"),True)
        entries[name]={"ip":ip,
                       "community_dpapi":base64.b64encode(protected).decode("ascii"),
                       "version":"2c"}
        self._save(entries)

    def remove(self,printer):
        entries=self._raw()
        entries.pop(str(printer),None)
        self._save(entries)

    def _save(self,entries):
        self.file.parent.mkdir(parents=True,exist_ok=True)
        temp=self.file.with_suffix(".tmp")
        temp.write_text(json.dumps(entries,ensure_ascii=False,indent=2),
                        encoding="utf-8")
        os.replace(temp,self.file)
