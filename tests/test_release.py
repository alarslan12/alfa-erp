"""Firebase release contracts: no cloud secrets or obsolete backend packages."""
import ast, re, subprocess, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ReleaseContractTests(unittest.TestCase):
    def test_all_python_sources_parse(self):
        files=list(ROOT.rglob('*.py'))
        self.assertGreaterEqual(len(files),25)
        for p in files:
            with self.subTest(path=p.relative_to(ROOT)):
                ast.parse(p.read_text('utf-8'),filename=str(p))

    def test_project_source_contract(self):
        p=subprocess.run([sys.executable,str(ROOT/'KONTROL_DOSYA_UYUMU.py')],
            cwd=ROOT,capture_output=True,text=True,timeout=25)
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)

    def test_firebase_is_the_only_cloud_transport(self):
        for name in ('alfa_bulut.py','alfa_cihaz.py','auto_eslestir.py',
                     'cihaz_eslestir.py','yonetici_giris.py','bulut_gelen_kutusu.py'):
            self.assertFalse((ROOT/name).exists(),name)
        self.assertFalse((ROOT/'supabase').exists())
        main=(ROOT/'main.py').read_text('utf-8')
        self.assertIn('from alfa_rtdb import Workstation',main)
        self.assertNotIn('Supabase',main)
        crypto=(ROOT/'cihaz_sifreleme.py').read_text('utf-8')
        self.assertNotIn('urllib',crypto)

    def test_versions_and_unified_suite_match(self):
        src=(ROOT/'main.py').read_text('utf-8')
        version=re.search(r"^VERSION='([^']+)'",src,re.MULTILINE).group(1)
        suite=(ROOT/'ALFACOPYCENTER_Suite.iss').read_text('utf-8')
        self.assertIn('#define SuiteVersion "'+version+'"',suite)
        self.assertIn('ALFACOPYCENTER_Suite_Setup_V'+version.replace('.','_'),suite)
        self.assertIn('AppId=ALFACOPYCENTER.Suite',suite)
        self.assertIn('GetSHA256OfString',suite)
        self.assertIn('OwnerPasswordValid',suite)
        self.assertIn("WizardIsComponentSelected('owner')",suite)
        self.assertIn('PrepareToInstall',suite)
        self.assertIn("OwnerPasswordPage.Add('Yönetici kurulum şifresi:', True)",suite)
        for name in ('staff','owner','banner','print','print\\agent'):
            self.assertIn('Name: "'+name+'";',suite)
        self.assertEqual(version, re.search(r"^SUITE_VERSION='([^']+)'",
            (ROOT/'banner_studio/studio_server.py').read_text('utf-8'),
            re.MULTILINE).group(1))
        self.assertFalse((ROOT/'alfa_tek_kurulum.iss').exists())
        self.assertFalse((ROOT/'alfa_personel.iss').exists())
        self.assertFalse((ROOT/'alfa_yonetici.iss').exists())

    def test_excel_import_keeps_named_books_without_page_count(self):
        import tempfile
        from openpyxl import Workbook
        from katalog_excel_aktar import preview_excel_catalog
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"books.xlsx"
            book=Workbook()
            ws=book.active
            ws.append(["Kitap Kodu","Kitap Adı","Sayfa Sayısı","Grup"])
            ws.append([101,"Klinik Kitap",None,"TTS Klinik"])
            ws.append([102,None,None,"TTS Klinik"])
            ws.append([103,"Temel Kitap",240,"TTS Temel"])
            book.save(path)
            imported=preview_excel_catalog(path)
            self.assertEqual(len(imported),2)
            values={v["code"]:v for v in imported}
            self.assertEqual(values["101"]["page_count"],0)
            self.assertEqual(values["103"]["page_count"],240)

    def test_history_and_staff_excel_contracts(self):
        from surum_gecmisi import release_history_markdown
        notes=release_history_markdown("2.0.15")
        for release in ("2.0.15","2.0.14","2.0.13","2.0.12","2.0.11",
                        "2.0.10","2.0.9","1.1.1","1.1.0","1.0.0"):
            self.assertIn("v"+release,notes)
        staff=(ROOT/"ekran_ayarlar.py").read_text("utf-8")
        self.assertIn("def _staff_send_excel",staff)
        self.assertIn("Excel Katalog",staff)
        rules=__import__("json").loads(
            (ROOT/"firebase/database.rules.json").read_text("utf-8"))["rules"]["alfa"]["$workspace"]
        self.assertIn("staff",rules["books"]["$id"][".write"])
        self.assertIn("staff",rules["public_catalog"][".write"])
        self.assertIn("!newData.exists()",rules["members"]["$uid"][".write"])
        self.assertIn("!newData.exists()",rules["error_acks"]["$id"][".write"])

    def test_no_embedded_secret_ticket(self):
        self.assertFalse((ROOT/'kurulum_bilgisi.json').exists())
        ignore=(ROOT/'.gitignore').read_text('utf-8')
        self.assertIn('kurulum_bilgisi.json',ignore)
        self.assertIn('alfa_outbox.json',ignore)

if __name__=='__main__':
    unittest.main()
