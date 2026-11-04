"""Yönetici cihazında tek seferlik kullanımlı çalışan kurulum arşivi oluşturur.
Yetki kodu tek kullanımlıktır; hiçbir admin JWT veya servis anahtarı bu pakete girmez.
"""
import io,json,zipfile
from pathlib import Path

SKIP={
  'yonetici_paneli.py','yonetici_ayarlar.py','yonetici_giris.py','yonetici_kompakt.py','personel_paketi.py',
  'islem_gunlugu.py','YONETICI_WINDOWS.bat','YONETICI_SURUMU.flag',
  'ALFA_ERP_SAHiP_SETUP.bat',
}
STAFF_AUDIT='''"""Personel paketi: yerel veya okunabilir denetim günlüğü tutma."""\nclass AuditLog:\n    def __init__(self,*_a,**_k): pass\n    def record_diff(self,*_a,**_k):return 0\n    def record_action(self,*_a,**_k):return None\n    def read(self,*_a,**_k):return []\n'''

def create_staff_package(target,code,root):
    target=Path(target);root=Path(root)
    if not (len(code)==48 and all(c in '0123456789ABCDEF' for c in code)):
        raise ValueError('Eşleştirme bileti geçersiz.')
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for file in root.iterdir():
            if file.is_file() and file.name not in SKIP and file.suffix.lower() in ('.py','.bat','.ps1','.txt','.xlsx','.json','.iss'):
                if file.name.startswith('SURUM_NOTLARI') or file.name.startswith('TEST_') or file.name.startswith('KONTROL_V'):
                    continue
                z.write(file,arcname=file.name)
        for asset in (root/'assets').rglob('*') if (root/'assets').exists() else []:
            if asset.is_file(): z.write(asset,arcname=asset.relative_to(root).as_posix())
        z.writestr('islem_gunlugu.py',STAFF_AUDIT)
        z.writestr('kurulum_bilgisi.json',json.dumps({'enrollment_code':code}))
        z.writestr('README_PERSONEL.txt','ALFA ERP Personel 6.0.\n'
            'ZIP dosyasini yonetici PCde acip URET_SETUP_EXE_WINDOWS.bat ile Setup.exe olusturun.\n'
            'Personel PCye yalnizca elde ettiginiz Setup.exe dosyasini gonderin.\n'
            'Internet baglantisi gereklidir. Cihaz icin giris veya sifre sorulmaz.\n'
            'Tek kurulum bileti YALNIZCA BIR bilgisayari eslestirir; 14 gun siniri yoktur.\n'
            'Analitik ekrani sifre korumalidir. Bulut yonetici islemleri bu pakette yoktur.\n')
    return target


def create_staff_installer_bundle(destination, installer, code):
    """Package an existing universal Setup.exe with a one-use enrollment ticket.

    The secret lives only in the user-owned ZIP, never in GitHub or build logs.
    """
    import json
    import zipfile
    from pathlib import Path
    source=Path(installer)
    if not source.is_file() or source.suffix.lower()!='.exe':
        raise ValueError('Hazır Windows Setup.exe dosyasını seçin.')
    if len(str(code))!=48 or any(c not in '0123456789abcdefABCDEF' for c in str(code)):
        raise ValueError('Eşleştirme kodu geçersiz.')
    dest=Path(destination)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(source,arcname=source.name)
        archive.writestr('kurulum_bilgisi.json',
            json.dumps({'enrollment_code':str(code).upper()},ensure_ascii=False))
        archive.writestr('KURULUM.txt',
            '1) Bu ZIP dosyasını yalnızca yetkilendireceğiniz PCye gönderin.\n'
            '2) Setup.exe ve kurulum_bilgisi.json aynı klasörde olacak şekilde çıkarın.\n'
            '3) Setup.exe dosyasını çalıştırın. Tek kullanımlık kod bir kere kullanılır.\n'
            '4) Sonraki sürümler için aynı genel Setup.exe kullanılabilir; eşleşmiş PC yeni kod istemez.\n')
    return str(dest)
