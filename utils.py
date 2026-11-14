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
    query = tr_kucult(str(arama).strip())
    if isinstance(kitap_veri, dict):
        code = tr_kucult(kitap_veri.get('kod', ''))
        description = tr_kucult(
            f"{kitap_veri.get('isim', '')} "
            f"{kitap_veri.get('grup', '')} {kitap_veri.get('grup_temiz', '')}"
        )
    else:
        code = ''
        description = tr_kucult(kitap_veri)

    def tokens(value):
        # Also recognize joined series notation, e.g. TUSDATA24.
        value = re.sub(r'\b(tus|dus)\s+data\b', r'\1data', value)
        return re.findall(r'[a-z]+|[0-9]+', value)

    terms = tokens(query)
    if not terms:
        return False
    numbers = [term for term in terms if term.isdecimal()]
    letters = [term for term in terms if not term.isdecimal()]
    if not numbers:
        # Preserve existing partial-word search for ordinary text.
        return all(word in (code + ' ' + description)
                   for word in query.split())

    words = tokens(description)
    series_numbers = {str(int(word)) for word in words if word.isdecimal()}
    wanted_numbers = {str(int(word)) for word in numbers}
    if not letters:
        # A direct code search is exact: 24 must not match code 424.
        if len(numbers) == 1 and code.isdecimal() and int(code) == int(numbers[0]):
            return True
        return wanted_numbers.issubset(series_numbers)

    # Mixed name/number queries must match the real book title/category,
    # never a fragment of an unrelated catalog code or publisher name.
    word_set = {word for word in words if not word.isdecimal()}
    aliases = {'tus': 'tusdata', 'dus': 'dusdata'}
    return wanted_numbers.issubset(series_numbers) and all(
        aliases[term] in word_set if term in aliases else
        any(word.startswith(term) for word in word_set)
        for term in letters
    )
