"""Small original Windows WAV notification tones shared by ERP and tray agent.

No external audio assets or background polling. Generated on first playback in
the same LOCALAPPDATA/AlfaERP directory as UserSettings. Modes are preserved
across app upgrades and reread by the independent notification agent.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import random
import struct
import tempfile
import wave

SOUND_CHOICES=(
    ("klasik","Windows varsayılan uyarı"),
    ("yumusak","Yumuşak çift ton"),
    ("net","Belirgin üçlü ton"),
    ("kisa","Kısa çift uyarı"),
    ("karisik","Her yeni siparişte farklı ton"),
    ("tts_kadin","Kadın konuşma sesi (Windows)"),
    ("tts_erkek","Erkek konuşma sesi (Windows)"),
    ("tts_karisik","Konuşma sesi (rastgele)"),
    ("ozan_1","Sipariş anonsu 1"),
    ("ozan_2","Sipariş anonsu 2"),
    ("ozan_3","Sipariş anonsu 3"),
    ("ozan_4","Sipariş anonsu 4"),
    ("ozan_karisik","Sipariş anonsları (rastgele)"),
    ("sessiz","Sessiz (yalnız görsel bildirim)"),
)
SOUND_IDS={key for key,_label in SOUND_CHOICES}
PATTERNS={
    "yumusak":((659,0.24),(784,0.34)),
    "net":((740,0.19),(987,0.19),(1175,0.34)),
    "kisa":((1060,0.13),(1060,0.17)),
}


def _default_directory():
    base=os.environ.get("ALFA_ERP_DATA_DIR")
    if base:
        return Path(base)
    local=os.environ.get("LOCALAPPDATA")
    return Path(local)/"AlfaERP" if local else Path.home()/".local"/"share"/"AlfaERP"


def _ensure_tone(directory,mode):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    output=directory/("alfa_bildirim_"+mode+"_v1.wav")
    if output.is_file() and output.stat().st_size>5000:
        return output
    sample_rate=22050
    samples=[]
    for frequency,duration in PATTERNS[mode]:
        count=int(sample_rate*duration)
        for i in range(count):
            t=i/sample_rate
            fade=min(1.0,t/0.022,(duration-t)/0.060)
            amp=max(0.0,fade)*0.35
            # Two soft harmonics for distinctive, non-harsh notification tones.
            value=amp*(math.sin(2*math.pi*frequency*t)+
                       0.16*math.sin(4*math.pi*frequency*t))
            samples.append(int(max(-1,min(1,value))*32767))
        samples.extend([0]*int(sample_rate*0.075))
    fd,temp=tempfile.mkstemp(prefix=".alfa_tone_",suffix=".wav",dir=directory)
    os.close(fd)
    try:
        with wave.open(temp,"wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(sample_rate)
            writer.writeframes(struct.pack("<"+"h"*len(samples),*samples))
        os.replace(temp,output)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    return output


def play_order_sound(mode="klasik",directory=None):
    """Play a user-selected or alternating tone without blocking GUI."""
    mode=str(mode or "klasik")
    if mode not in SOUND_IDS:
        mode="klasik"
    if mode=="sessiz":
        return True
    if mode.startswith("tts_"):
        from bildirim_dogal_ses import play_windows_voice
        if play_windows_voice(mode):
            return True
        mode="klasik"  # Windows Turkish speech engine unavailable.
    elif mode.startswith("ozan_"):
        from bildirim_dogal_ses import play_local_announcement
        if play_local_announcement(mode):
            return True
        mode="klasik"  # Missing local WAV and Turkish TTS unavailable.
    if mode=="karisik":
        mode=random.choice(("yumusak","net","kisa"))
    try:
        import winsound
        if mode=="klasik":
            winsound.PlaySound("SystemExclamation",
                winsound.SND_ALIAS|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
        else:
            path=_ensure_tone(directory or _default_directory(),mode)
            winsound.PlaySound(str(path),
                winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
        return True
    except (ImportError,OSError,RuntimeError,ValueError):
        return False


def configured_sound(directory=None):
    """Read current preference at notification time, no extra watcher."""
    import json
    path=Path(directory or _default_directory())/"alfa_ayarlar.json"
    try:
        values=json.loads(path.read_text(encoding="utf-8"))
        mode=str(values.get("bildirim_sesi") or "klasik")
        if mode.startswith("eleven_"):
            mode="ozan_karisik"
        return mode if mode in SOUND_IDS else "klasik"
    except (OSError,ValueError,TypeError):
        return "klasik"
