"""Book-code correctness and zero-page snapshot regression, all offline."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook
from database import ERPDatabase
from alfa_rtdb import Workstation
from rtdb_owner_admin import _catalog
from mobil_siparis_donusum import convert_mobile_order


class FakeFirebase:
    def __init__(self):
        self.books={
            "old508":{"id":"old508","code":"508","name":"TIPDEMY Eski Soru",
                      "page_count":0,"is_active":True,"version":1},
            "old509":{"id":"old509","code":"509","name":"TIPDEMY Patoloji HT",
                      "page_count":119,"is_active":True,"version":1},
            "old510":{"id":"old510","code":"510","name":"TIPDEMY Patoloji Konu",
                      "page_count":353,"is_active":True,"version":1},
            "old346":{"id":"old346","code":"346","name":"TIPDEMY SST Patoloji",
                      "page_count":0,"is_active":True,"version":1},
        }
        self.public={}
        self.catalog_revision=10
        self.bumped=0
    def _get(self,path):
        if path=="books":return copy.deepcopy(self.books)
        if path=="public_catalog":return copy.deepcopy(self.public)
        raise AssertionError(path)
    def _request(self,method,path,data=None,**kwargs):
        if method=="PATCH" and path=="books":
            self.books.update(copy.deepcopy(data))
        elif method=="PUT" and path.startswith("books/"):
            self.books[path.split("/",1)[1]]=copy.deepcopy(data)
        elif method=="PUT" and path=="public_catalog":
            self.public=copy.deepcopy(data)
        else:raise AssertionError((method,path))
        return None,None,200
    def _bump(self,kind):
        assert kind=="catalog"
        self.bumped+=1
        self.catalog_revision+=1


class BookCatalogRegressionTests(unittest.TestCase):
    def test_exact_code_replaces_old_firebase_shift(self):
        from unittest.mock import patch
        client=FakeFirebase()
        excel=[
            {"code":"346","name":"TIPDEMY SST Patoloji","page_count":386,
             "group_name":"TIPDEMY","supports_color":True},
            {"code":"508","name":"TIPDEMY Patoloji HT","page_count":118,
             "group_name":"TIPDEMY","supports_color":True},
            {"code":"509","name":"TIPDEMY Patoloji Konu","page_count":353,
             "group_name":"TIPDEMY","supports_color":True},
            {"code":"510","name":"TIPDEMY Protetik SST","page_count":192,
             "group_name":"TIPDEMY","supports_color":True},
        ]
        with tempfile.TemporaryDirectory() as folder, \
             patch("cihaz_sifreleme.DATA",Path(folder)):
            result=_catalog(client,excel)
            self.assertTrue(result["verified"])
            self.assertEqual(result["count"],4)
            self.assertEqual(client.bumped,1)
            self.assertTrue(Path(result["backup"]).is_file())
            self.assertEqual(client.public["509"]["name"],"TIPDEMY Patoloji Konu")
            self.assertEqual(client.public["508"]["page_count"],118)
            self.assertEqual(client.public["346"]["page_count"],386)
            active={book["code"]:book for book in client.books.values()
                    if book.get("is_active") is True}
            self.assertEqual(active["509"]["name"],"TIPDEMY Patoloji Konu")
            self.assertEqual(active["510"]["name"],"TIPDEMY Protetik SST")

    def test_legacy_zero_snapshot_uses_correct_catalog_pages(self):
        catalog={"509":{"kod":"509","isim":"TIPDEMY Patoloji Konu","sayfa":353}}
        order={"id":"a-b","status":"havuz","version":1,"order_number":1}
        remote=[{"book_code":"509","print_type":"SB","quantity":2,
                 "page_count_snapshot":0,"prepared_count":0,"boxed_count":0}]
        result=convert_mobile_order(order,remote,catalog)
        self.assertEqual(result["kitaplar"][0]["sayfa_birim"],353)

    def test_new_order_carries_page_count_into_firebase(self):
        with tempfile.TemporaryDirectory() as folder:
            excel=Path(folder)/"source.xlsx"
            w=Workbook();ws=w.active
            ws.append(["Kitap Kodu","Kitap Adı","Sayfa Sayısı","Grup"])
            ws.append([509,"TIPDEMY Patoloji Konu",353,"TIPDEMY"])
            w.save(excel)
            db=ERPDatabase(excel,data_dir=folder)
            normalized=db._temiz_kitaplar([{"kod":"509","tur":"SB",
                "adet":2,"hazir":0,"koli":0}])
            self.assertEqual(normalized[0]["sayfa"],353)
            self.assertEqual(normalized[0]["sayfa_birim"],353)
            self.assertEqual(normalized[0]["isim"],"TIPDEMY Patoloji Konu")
            import uuid
            result=Workstation._make_items(str(uuid.uuid4()),normalized)
            item=list(result.values())[0]
            self.assertEqual(item["page_count_snapshot"],353)
            self.assertEqual(item["book_name_snapshot"],"TIPDEMY Patoloji Konu")

    def test_unchanged_name_blank_excel_does_not_erase_known_pages(self):
        client=FakeFirebase()
        client.books["old509"]["name"]="TIPDEMY Patoloji Konu"
        client.books["old509"]["page_count"]=353
        rows=[{"code":"509","name":"TIPDEMY Patoloji Konu",
               "page_count":0,"group_name":"TIPDEMY","supports_color":True}]
        with tempfile.TemporaryDirectory() as folder, \
             patch("cihaz_sifreleme.DATA",Path(folder)):
            _catalog(client,rows)
            self.assertEqual(client.public["509"]["page_count"],353)

    def test_failed_catalog_readback_keeps_revision_unchanged(self):
        client=FakeFirebase()
        old_get=client._get
        def stale(path):
            if path=="books":return copy.deepcopy(FakeFirebase().books)
            return old_get(path)
        client._get=stale
        with tempfile.TemporaryDirectory() as folder, \
             patch("cihaz_sifreleme.DATA",Path(folder)):
            from alfa_rtdb import DeviceError
            with self.assertRaises(DeviceError):
                _catalog(client,[{"code":"509","name":"TIPDEMY Patoloji Konu",
                                  "page_count":353,"group_name":"TIPDEMY",
                                  "supports_color":True}])
            self.assertEqual(client.bumped,0)


if __name__=="__main__":
    unittest.main()
