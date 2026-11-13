"""Optional natural Turkish order alerts with Windows speech / ElevenLabs.

No order/customer data is transmitted: the remote model receives a single
fixed sentence. API key is DPAPI-encrypted per Windows user, never bundled,
committed, logged, or stored in plain settings. Clips are generated once per
voice and then played offline from a bounded cache.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import random
import re
import tempfile
import urllib.request
import wave

VOICE_TEXT="Alfa Copy Center. Yeni bir siparişiniz var. Sipariş havuzunu kontrol ediniz."
ELEVEN_MODEL="eleven_flash_v2_5"
ELEVEN_ENDPOINT="https://api.elevenlabs.io/v1/text-to-speech/"
SECRET_FILE="alfa_elevenlabs_key.bin"
CACHE_FOLDER="notification_voice_cache"
MAX_PCM=700000
_KEY_RE=re.compile(r"^[A-Za-z0-9]{10,64}$")
_speaker=None
_manager=None


def voice_key_path(directory):
    return Path(directory)/SECRET_FILE


def store_api_key(directory,key):
    from cihaz_sifreleme import crypt
    key=str(key or "").strip()
    if len(key)<15 or len(key)>512 or "\n" in key or "\r" in key:
        raise ValueError("ElevenLabs anahtarı geçersiz.")
    path=voice_key_path(directory)
    path.parent.mkdir(parents=True,exist_ok=True)
    encrypted=crypt(key.encode("utf-8"))
    fd,tmp=tempfile.mkstemp(prefix=".alfa_secret_",dir=str(path.parent))
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(encrypted)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def remove_api_key(directory):
    try:voice_key_path(directory).unlink()
    except FileNotFoundError:pass


def load_api_key(directory):
    from cihaz_sifreleme import crypt
    path=voice_key_path(directory)
    if not path.is_file():
        return None
    try:
        return crypt(path.read_bytes(),decrypt=True).decode("utf-8")
    except (OSError,ValueError,RuntimeError,UnicodeDecodeError):
        return None


def validate_voice_id(value):
    value=str(value or "").strip()
    if value and not _KEY_RE.fullmatch(value):
        raise ValueError("ElevenLabs Voice ID 10–64 harf/rakamdan oluşmalı.")
    return value


def _voice_for_mode(mode,directory):
    from ayar_yonetimi import UserSettings
    options=UserSettings(directory)
    slots=[
        validate_voice_id(options.get("elevenlabs_voice_a") or ""),
        validate_voice_id(options.get("elevenlabs_voice_b") or ""),
    ]
    if mode=="eleven_a":return slots[0]
    if mode=="eleven_b":return slots[1]
    return random.choice([s for s in slots if s]) if any(slots) else ""


def cached_voice_path(directory,voice_id):
    if not _KEY_RE.fullmatch(str(voice_id or "")):
        raise ValueError("Geçersiz ElevenLabs ses kimliği")
    fingerprint=hashlib.sha256(
        (ELEVEN_MODEL+"\n"+voice_id+"\n"+VOICE_TEXT).encode("utf-8")
    ).hexdigest()[:24]
    return Path(directory)/CACHE_FOLDER/("alfa_voice_"+fingerprint+".wav")


def generate_voice_clip(directory,voice_id):
    """Network operation: call ONLY in worker thread, never from Qt GUI."""
    voice_id=validate_voice_id(voice_id)
    if not voice_id:raise RuntimeError("ElevenLabs ses kimliği girilmedi.")
    cached=cached_voice_path(directory,voice_id)
    if cached.is_file() and cached.stat().st_size>1500:return cached
    api_key=load_api_key(directory)
    if not api_key:raise RuntimeError("ElevenLabs API anahtarı tanımlı değil.")
    request=urllib.request.Request(
        ELEVEN_ENDPOINT+voice_id+"/stream?output_format=pcm_16000",
        data=json.dumps({"text":VOICE_TEXT,"model_id":ELEVEN_MODEL,
                         "voice_settings":{"stability":0.65,
                                           "similarity_boost":0.75}}).encode("utf-8"),
        headers={"Content-Type":"application/json",
                 "xi-api-key":api_key},
        method="POST")
    try:
        with urllib.request.urlopen(request,timeout=22) as response:
            mime=response.headers.get("Content-Type","")
            if "json" in mime:
                raise RuntimeError("ElevenLabs ses verisi döndürmedi.")
            pcm=response.read(MAX_PCM+1)
    except Exception:
        # Never include network exception text; some transports print headers.
        raise RuntimeError("ElevenLabs yanıtı alınamadı; yerel sese geçildi.") from None
    if len(pcm)<3200 or len(pcm)>MAX_PCM or len(pcm)%2:
        raise RuntimeError("ElevenLabs ses biçimi doğrulanamadı.")
    cached.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=".alfa_voice_",suffix=".wav",dir=cached.parent)
    os.close(fd)
    try:
        with wave.open(temp,"wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(16000)
            writer.writeframes(pcm)
        os.replace(temp,cached)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    return cached


def _play_wav(path):
    import winsound
    winsound.PlaySound(str(path),
        winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)


def play_windows_voice(mode):
    """Qt WinRT voices are relatively natural and work without API keys."""
    global _speaker
    try:
        from PySide6.QtCore import QLocale
        from PySide6.QtTextToSpeech import QTextToSpeech,QVoice
        from PySide6.QtWidgets import QApplication
        if QApplication.instance() is None:
            return False
        if _speaker is None:
            engines=QTextToSpeech.availableEngines()
            selected="winrt" if "winrt" in engines else (
                "sapi" if "sapi" in engines else "")
            _speaker=QTextToSpeech(selected) if selected else QTextToSpeech()
        locales=_speaker.availableLocales()
        turkish=next((x for x in locales if x.name().lower().startswith("tr")),None)
        if turkish is not None:
            _speaker.setLocale(turkish)
        voices=list(_speaker.availableVoices())
        if not voices:return False
        preferred=(QVoice.Gender.Female if mode=="tts_kadin" else QVoice.Gender.Male)
        filtered=[v for v in voices if v.gender()==preferred]
        if mode=="tts_karisik":
            choice=random.choice(voices)
        else:
            choice=filtered[0] if filtered else voices[0]
        _speaker.setVoice(choice)
        _speaker.say(VOICE_TEXT)
        return True
    except Exception:
        return False


def _start_voice_fetch(manager,directory,voice_id):
    """Daemon Python thread: safe across GUI shutdown and setup upgrades."""
    import threading
    def job():
        try:
            path=generate_voice_clip(directory,voice_id)
            manager.ready.emit(str(path))
        except Exception:
            manager.failed.emit()
        finally:
            manager.completed.emit(voice_id)
    threading.Thread(target=job,daemon=True,
                     name="ALFA-ElevenLabs-Voice").start()


def play_elevenlabs(mode,directory):
    """Play a cached natural voice or schedule synthesis without blocking UI."""
    global _manager
    try:
        voice_id=_voice_for_mode(mode,directory)
        if not voice_id:
            return False
        cached=cached_voice_path(directory,voice_id)
        if cached.exists() and cached.stat().st_size>1500:
            _play_wav(cached)
            return True
        from PySide6.QtCore import QObject,Slot
        from PySide6.QtWidgets import QApplication
        app=QApplication.instance()
        if app is None or not load_api_key(directory):
            return False
        if _manager is None:
            from PySide6.QtCore import Signal
            class Manager(QObject):
                ready=Signal(str)
                failed=Signal()
                completed=Signal(str)
                def __init__(self,parent):
                    super().__init__(parent)
                    self.pending=set()
                    self.ready.connect(self._play_ready)
                    self.completed.connect(self._clear_pending)
                def submit(self,voice,directory):
                    if voice in self.pending:return
                    self.pending.add(voice)
                    _start_voice_fetch(self,directory,voice)
                @Slot(str)
                def _play_ready(self,path):
                    try:_play_wav(Path(path))
                    except Exception:pass
                @Slot(str)
                def _clear_pending(self,voice):
                    self.pending.discard(voice)
            _manager=Manager(app)
        _manager.submit(voice_id,directory)
        return True
    except Exception:
        return False
