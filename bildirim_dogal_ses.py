"""Offline order announcements. No cloud synthesis or customer data transfers.

Canva Ozan M4A clips play directly from assets/notifications using Qt
Multimedia; WAV and MP3 alternatives of the same recordings are accepted.
No Windows TTS, cloud synthesis, or unrelated tones are played.
"""
from pathlib import Path
import random

ANNOUNCEMENTS=(
    "Alfa Copy Center. Yeni siparişiniz var.",
    "Yeni bir sipariş alındı. Lütfen sipariş havuzunu kontrol edin.",
    "Dikkat. Yeni sipariş işleme hazır.",
    "Yeni sipariş bildirimi. Sipariş listesini kontrol ediniz.",
)
_media_player=None
_AUDIO_EXTENSIONS=(".m4a",".wav",".mp3")


def announcement_asset(index):
    """Prefer Canva's native M4A download, then existing WAV/MP3 files."""
    folder=Path(__file__).resolve().parent/"assets"/"notifications"
    paths=[folder/f"ozan_{index+1}{suffix}" for suffix in _AUDIO_EXTENSIONS]
    return next((path for path in paths if path.is_file()),paths[0])


def stop_local_media():
    """Release a previous compressed clip before playing another alert."""
    global _media_player
    player=_media_player
    _media_player=None
    if player is not None:
        player.stop()
        player.deleteLater()


def _play_wav(path):
    try:
        import winsound
        winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
        return True
    except (ImportError,OSError,RuntimeError):
        return False


def _play_compressed(path,fallback):
    """Qt keeps the audio output and decoder alive until the clip finishes."""
    global _media_player
    player=None
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
        from PySide6.QtWidgets import QApplication
        app=QApplication.instance()
        if app is None:
            return False
        stop_local_media()
        player=QMediaPlayer(app)
        audio=QAudioOutput(player)
        audio.setVolume(1.0)
        player.setAudioOutput(audio)
        _media_player=player

        def failed(*_):
            if _media_player is player:
                stop_local_media()
                fallback()

        def status_changed(status):
            if _media_player is not player:
                return
            if status==QMediaPlayer.MediaStatus.InvalidMedia:
                failed()
            elif status==QMediaPlayer.MediaStatus.EndOfMedia:
                stop_local_media()

        player.errorOccurred.connect(failed)
        player.mediaStatusChanged.connect(status_changed)
        player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        # setSource can report failure synchronously. Do not restart a
        # player that has already been retired by its error callback.
        if _media_player is player:
            player.play()
        return True
    except Exception:
        if player is not None and _media_player is player:
            stop_local_media()
        return False


def play_local_announcement(mode):
    index=random.randrange(len(ANNOUNCEMENTS)) if mode=="ozan_karisik" else int(mode[-1])-1
    path=announcement_asset(index)
    def fallback():
        # Only an alternate encoding of the same Ozan recording is permitted.
        wav=path.with_suffix(".wav")
        return path.suffix!=".wav" and wav.is_file() and _play_wav(wav)

    stop_local_media()
    if path.is_file():
        if path.suffix==".wav" and _play_wav(path):
            return True
        if path.suffix in (".m4a",".mp3") and _play_compressed(path,fallback):
            return True
    return fallback()
