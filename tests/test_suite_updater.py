"""Unified Suite update contracts with mocked GitHub data (offline)."""
import unittest
from unittest.mock import patch
from alfa_guncelleme import check_for_update,GITHUB_API,HELPER_PS,UpdateError


def release(v,legacy=False):
    n='v'+v
    name=('ALFA_ERP_Personel_Setup_' if legacy else 'ALFACOPYCENTER_Suite_Setup_V')+v.replace('.','_')+'.exe'
    return {'tag_name':n,'draft':False,'prerelease':False,
        'html_url':'https://github.com/alarslan12/alfa-erp/releases/tag/'+n,
        'body':'Release notes for '+v,
        'assets':[{'name':name,'size':300000,
                   'browser_download_url':'https://github.com/alarslan12/alfa-erp/releases/download/'+n+'/'+name},
                  {'name':'SHA256SUMS.txt','size':100,
                   'browser_download_url':'https://github.com/alarslan12/alfa-erp/releases/download/'+n+'/SHA256SUMS.txt'}]}


class Response:
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def geturl(self):return GITHUB_API


class SuiteUpdaterTests(unittest.TestCase):
    def check(self,current,releases):
        with patch('alfa_guncelleme._request',return_value=Response()), \
             patch('alfa_guncelleme.json.load',return_value=releases):
            return check_for_update(current,'staff')

    def test_does_not_install_unrelated_v6_release(self):
        result=self.check('2.0.12',[release('6.2.3',legacy=True),
                                    release('2.0.12'),release('2.0.13')])
        self.assertTrue(result['available'])
        self.assertEqual(result['latest'],'v2.0.13')
        self.assertEqual(result['installer']['name'],
                         'ALFACOPYCENTER_Suite_Setup_V2_0_13.exe')

    def test_latest_compatible_suite_does_not_downgrade(self):
        result=self.check('2.0.13',[release('6.2.3',legacy=True),
                                     release('2.0.12')])
        self.assertFalse(result['available'])
        self.assertEqual(result['latest'],'v2.0.12')

    def test_missing_suite_binary_not_accepted(self):
        result=self.check('2.0.12',[release('6.2.3',legacy=True)])
        self.assertFalse(result['available'])

    def test_beta_or_draft_never_selected(self):
        newer=release('2.0.99')
        newer['prerelease']=True
        result=self.check('2.0.12',[newer,release('2.0.13')])
        self.assertEqual(result['latest'],'v2.0.13')

    def test_cancelled_shipping_label_release_is_skipped(self):
        result=self.check('2.0.28',[release('2.0.29'),release('2.0.28')])
        self.assertFalse(result['available'])
        result=self.check('2.0.28',[release('2.0.29'),release('2.0.30')])
        self.assertEqual(result['latest'],'v2.0.30')

    def test_helper_preserves_suite_layout_and_print_restart(self):
        self.assertIn('/ALFAPRINT',HELPER_PS)
        self.assertIn('PrintSurveillance\\AlfaPrintSurveillance.exe',HELPER_PS)
        self.assertIn('ALFAUPDATE',HELPER_PS)


if __name__=='__main__':
    unittest.main()
