# utils.py - Açık Adres, Harf ve Kargo Kodu Formatlama Motoru
import re

def tr_kucult(t):
    """Türkçe İ/I/ı ve Unicode birleşik nokta (\u0307) sorununu çözen normalizasyon."""
    if not t:
        return ""
    return (
        str(t)
        .replace('İ', 'i').replace('I', 'i').replace('ı', 'i')
        .replace('Ş', 's').replace('ş', 's')
        .replace('Ğ', 'g').replace('ğ', 'g')
        .replace('Ü', 'u').replace('ü', 'u')
        .replace('Ö', 'o').replace('ö', 'o')
        .replace('Ç', 'c').replace('ç', 'c')
        .lower()
        .replace('\u0307', '')
    )

def parse_siparis_kodu(ham_kod):
    if not ham_kod:
        return "", "SB"
    temiz = str(ham_kod).strip()
    if "-RENKLİ" in temiz or "-RENKLI" in temiz:
        return temiz.replace("-RENKLİ", "").replace("-RENKLI", "").strip(), "RENKLİ"
    elif "-SB" in temiz:
        return temiz.replace("-SB", "").strip(), "SB"
    return temiz, "SB"

def is_acik_adres_veya_metin(metin):
    if not metin:
        return False
    s_metin = str(metin).strip()
    if not s_metin:
        return False
    # İçinde 1 tane bile harf veya adres noktalama işareti varsa kesinlikle Açık Adres / Metindir
    if re.search(r'[a-zA-ZçğıöşüÇĞİÖŞÜ.,/:;()\#@]', s_metin):
        return True
    return False

def otomatik_platform_bul(kod_str):
    if not kod_str or not str(kod_str).strip():
        return "Dolap"
    s = str(kod_str).strip()
    if is_acik_adres_veya_metin(s):
        return "Açık Adres / Manuel"
    rakamlar = re.sub(r'\D', '', s)
    if len(rakamlar) == 9:
        return "Gardrops"
    elif len(rakamlar) >= 10:
        return "Dolap"
    return "Dolap"

def format_kargo_kodu(kod_str, platform="Dolap"):
    if not kod_str:
        return ""
    s_metin = str(kod_str)
    # Harf veya adres işareti varsa metne dokunma, olduğu gibi bırak
    if is_acik_adres_veya_metin(s_metin):
        return s_metin

    temiz = re.sub(r'\D', '', s_metin)
    if not temiz:
        return s_metin

    # Dolap: last FOUR digits must be their own block, even for long
    # 16-digit codes. 2624140909632909 -> 262 414 090 963 2909.
    # Keep Gardrops (9 digits) and other short references unchanged.
    if len(temiz)>=13 and platform!="Gardrops":
        prefix=temiz[:-4]
        blocks=[prefix[i:i+3] for i in range(0,len(prefix),3)]
        return " ".join([*blocks,temiz[-4:]])
    return " ".join(temiz[i:i+3] for i in range(0,len(temiz),3))

def metin_eslesiyor_mu(arama, kitap_veri):
    if not arama or not str(arama).strip():
        return True
    a_temiz = tr_kucult(arama.strip())
    arama_kelimeleri = [k for k in a_temiz.split() if k]
    if not arama_kelimeleri:
        return True

    if isinstance(kitap_veri, dict):
        hedef_metin = tr_kucult(
            f"{kitap_veri.get('kod', '')} {kitap_veri.get('isim', '')} "
            f"{kitap_veri.get('grup', '')} {kitap_veri.get('grup_temiz', '')}"
        )
    else:
        hedef_metin = tr_kucult(str(kitap_veri))

    return all(kelime in hedef_metin for kelime in arama_kelimeleri)