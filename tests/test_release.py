"""Build hygiene: catch regressions before Windows installers are published."""
import ast
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ReleaseContractTests(unittest.TestCase):
    def test_all_python_sources_parse(self):
        paths=list(ROOT.rglob('*.py'))
        self.assertGreaterEqual(len(paths),30)
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                ast.parse(path.read_text('utf-8'),filename=str(path))

    def test_project_source_contract(self):
        outcome=subprocess.run([sys.executable,str(ROOT/'KONTROL_DOSYA_UYUMU.py')],
                               cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                               text=True,timeout=20)
        self.assertEqual(outcome.returncode,0,outcome.stdout+'\n'+outcome.stderr)

    def test_no_hardcoded_enrollment_ticket(self):
        self.assertFalse((ROOT/'kurulum_bilgisi.json').exists(),
                         'Private one-time pairing token must never be published in the repository')
        ignore=(ROOT/'.gitignore').read_text('utf-8')
        self.assertIn('kurulum_bilgisi.json',ignore)
        self.assertIn('alfa_outbox.json',ignore)

    def test_setup_versions_match(self):
        src=(ROOT/'main.py').read_text('utf-8')
        app_version=re.search(r"^VERSION\s*=\s*['\"]([^'\"]+)",src,re.MULTILINE)
        self.assertIsNotNone(app_version)
        for filename in ('alfa_personel.iss','alfa_yonetici.iss'):
            text=(ROOT/filename).read_text('utf-8')
            found=re.search(r'#define MyAppVersion "([^"]+)"',text)
            self.assertIsNotNone(found,filename)
            self.assertEqual(found.group(1),app_version.group(1),filename)
        self.assertIn('external', (ROOT/'alfa_personel.iss').read_text('utf-8'))

if __name__ == '__main__': unittest.main()
