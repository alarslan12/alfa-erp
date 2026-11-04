"""Hazır/Koli butonlarının ortak ilerleme kuralları (Qt bağımsız)."""


def sonraki_ilerleme(adet, hazir, koli, alan, fark):
    """(yeni_hazir, yeni_koli) döndür. Hazırlanmamış kitap kolilenemez.

    Sınırda eksi/artı basıldığında değişiklik yapmaz; 0 <= koli <= hazir <= adet
    koşulu her zaman korunur.
    """
    adet, hazir, koli = int(adet), int(hazir), int(koli)
    if adet < 0 or not 0 <= koli <= hazir <= adet:
        raise ValueError('Geçersiz kitap ilerlemesi.')
    if alan not in ('hazir', 'koli') or fark not in (-1, 1):
        raise ValueError('Geçersiz ilerleme işlemi.')
    if alan == 'hazir':
        hazir = max(0, min(adet, hazir + fark))
        # Hazır sayısı koli sayısından bağımsız değiştirilebilir;
        # aşağı çekildiğinde koli otomatik olarak yeni sınıra iner.
        koli = min(koli, hazir)
    else:
        koli = max(0, min(hazir, koli + fark))
    return hazir, koli


def buton_durumlari(adet, hazir, koli, etkin=True):
    """Doğrudan Qt düğmelerine bağlanabilen enabled durumları."""
    adet, hazir, koli = int(adet), int(hazir), int(koli)
    return {
        ('hazir', -1): bool(etkin and hazir > 0),
        ('hazir', 1): bool(etkin and hazir < adet),
        ('koli', -1): bool(etkin and koli > 0),
        ('koli', 1): bool(etkin and koli < hazir),
    }
