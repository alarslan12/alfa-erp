"""Only the four bundled Ozan recordings are used for order alerts.

Automatic notifications choose a random clip; explicit IDs are for preview.
"""
SOUND_CHOICES=(("ozan_karisik","Ozan · otomatik rastgele"),)
SOUND_IDS={"ozan_karisik","ozan_1","ozan_2","ozan_3","ozan_4"}


def play_order_sound(mode="ozan_karisik",directory=None,on_error=None):
    from bildirim_dogal_ses import play_local_announcement
    mode=str(mode or "ozan_karisik")
    if mode not in SOUND_IDS:
        mode="ozan_karisik"
    return (play_local_announcement(mode,on_error=on_error)
            if on_error is not None else play_local_announcement(mode))


def configured_sound(directory=None):
    """Legacy preferences cannot select a removed sound."""
    return "ozan_karisik"
