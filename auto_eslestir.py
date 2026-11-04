"""Kurulum sırasında özel tek kullanımlık biletle otomatik cihaz eşleştirme."""
import json,os,socket,sys
from pathlib import Path
from alfa_cihaz import api,save_token,get_token
from cihaz_eslestir import enable_startup
ROOT=(Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent)

def main(install_startup=True):
    info=ROOT/'kurulum_bilgisi.json'
    if not get_token():
        if not info.is_file():
            raise RuntimeError('Kurulum bileti bulunamadı. Yönetici Panelinden bu bilgisayar için yeni kurulum paketi üretin.')
        data=json.loads(info.read_text(encoding='utf-8'))
        code=str(data.get('enrollment_code') or '').strip()
        if len(code)!=48:raise RuntimeError('Kurulum bileti eksik veya geçersiz.')
        answer=api('pair',code=code,device_name=socket.gethostname()[:120])
        save_token(answer['device_token'])
    if install_startup:enable_startup()
    # Tek kullanımlık bileti ilk başarılı eşleştirmeden sonra diskte bırakmayalım.
    if info.is_file(): info.unlink()
    print('Cihaz hazır. Windows bildirici başlatıldı.')

if __name__=='__main__':
    try:main()
    except Exception as ex:
        print('ALFA ERP: Cihaz kaydı tamamlanamadı: '+str(ex));sys.exit(1)
