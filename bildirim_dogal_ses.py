"""Offline order announcements. No cloud synthesis or customer data transfers.

If licensed Canva Ozan WAV clips are provided, they are played directly from
assets/notifications. Without them, the same scripts use installed Turkish
Windows speech; the engine's voice must not be described as Canva Ozan.
"""
from pathlib import Path
import random

ANNOUNCEMENTS=(
    "Alfa Copy Center. Yeni siparişiniz var.",
    "Yeni bir sipariş alındı. Lütfen sipariş havuzunu kontrol edin.",
    "Dikkat. Yeni sipariş işleme hazır.",
    "Yeni sipariş bildirimi. Sipariş listesini kontrol ediniz.",
)
_speaker=None


def announcement_asset(index):
    return Path(__file__).resolve().parent/"assets"/"notifications"/f"ozan_{index+1}.wav"


def play_windows_voice(mode, text=None):
    """Use only an installed Turkish voice, with no network/API fallback."""
    global _speaker
    try:
        from PySide6.QtTextToSpeech import QTextToSpeech,QVoice
        from PySide6.QtWidgets import QApplication
        if QApplication.instance() is None:
            return False
        if _speaker is None:
            engines=QTextToSpeech.availableEngines()
            selected="winrt" if "winrt" in engines else ("sapi" if "sapi" in engines else "")
            _speaker=QTextToSpeech(selected) if selected else QTextToSpeech()
        turkish=next((x for x in _speaker.availableLocales()
                      if x.name().lower().startswith("tr")),None)
        if turkish is None:
            return False
        _speaker.setLocale(turkish)
        voices=list(_speaker.availableVoices())
        if not voices:
            return False
        preferred=QVoice.Gender.Female if mode=="tts_kadin" else QVoice.Gender.Male
        matching=[v for v in voices if v.gender()==preferred]
        choice=random.choice(voices) if mode=="tts_karisik" else (matching or voices)[0]
        _speaker.setVoice(choice)
        _speaker.say(text or ANNOUNCEMENTS[0])
        return True
    except Exception:
        return False


def play_local_announcement(mode):
    index=random.randrange(len(ANNOUNCEMENTS)) if mode=="ozan_karisik" else int(mode[-1])-1
    path=announcement_asset(index)
    if path.is_file():
        try:
            import winsound
            winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
            return True
        except (ImportError,OSError,RuntimeError):
            pass
    return play_windows_voice("tts_erkek",ANNOUNCEMENTS[index])
