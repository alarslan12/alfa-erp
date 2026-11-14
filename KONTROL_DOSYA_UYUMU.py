"""ALFA ERP Firebase v1.1.2 - source compatibility inspection.
This checks only currently used application modules. Retired cloud settings UI
(ekran_bulut.py / CloudPage) is NOT a project requirement.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_REQUIRED = {
    'main.py': {'AlfaMain', 'start'},
    'alfa_rtdb.py': {'Workstation', 'DeviceError'},
    'cihaz_sifreleme.py': {'crypt'},
    'ekran_baslangic.py': {'StartupSplash', 'launch_with_splash'},
    'bulut_canli.py': {'Sync'},
    'mobil_siparis_donusum.py': {'convert_mobile_order'},
    'ekran_envanter.py': {'EnvanterView'},
    'widgets.py': {'fallback_cover_pixmap', 'refresh_cover_placeholders', 'cover_label'},
    'kart_siparis.py': {'ProgressCover', 'SiparisKarti'},
    'editor_siparis.py': {'SiparisTakipSekmeleri', 'SiparisEditor'},
}
ADMIN_REQUIRED = {
    'rtdb_owner_admin.py': {'admin_request'},
    'yonetici_kompakt.py': {'OwnerSettingsPage'},
}

def main():
    required = dict(BASE_REQUIRED)
    if (ROOT / 'YONETICI_SURUMU.flag').exists():
        required.update(ADMIN_REQUIRED)
    problems = []
    for filename, symbols in required.items():
        path = ROOT / filename
        if not path.is_file():
            problems.append('Eksik dosya: ' + filename)
            continue
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=filename)
            found = {node.name for node in tree.body if isinstance(node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        except (SyntaxError, OSError, UnicodeError) as exc:
            problems.append('Okunamayan dosya: ' + filename + ': ' + str(exc))
            continue
        for name in sorted(symbols - found):
            problems.append(filename + ' icinde tanim bulunamadi: ' + name)
    if problems:
        print('ALFA ERP: KAYNAK DOSYA KONTROLU HATASI')
        for item in problems:
            print(' -', item)
        print('Bu sorun kurulum paketinden kaynaklanabilir.')
        return 1
    print('ALFA ERP V6.1.2: Dosya kontrolu basarili')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
