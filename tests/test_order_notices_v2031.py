"""v2.0.31 notice regression tests without production network/data."""
import copy
import tempfile
import unittest
import uuid
from pathlib import Path
from siparis_uyari import make_notice, pending_notice, revision, acknowledge, initial_note_notice
from alfa_rtdb import Workstation, DeviceError
from database import ERPDatabase

ROOT=Path(__file__).resolve().parents[1]

def local(note="", code="TEST", book="101"):
    return {"id":1,"kod":code,"platform":"Dolap","siparis_turu":"Normal Sipariş",
            "ciro":100,"durum":"havuz","order_note":note,
            "kitaplar":[{"kod":book,"tur":"SB","adet":2,"hazir":0,"koli":0}]}

class FakeStation:
    uid="ci-device"
    role="owner"
    commit=Workstation.commit
    transition=Workstation.transition
    progress=Workstation.progress
    _apply_events=Workstation._apply_events
    _apply_progress_events=Workstation._apply_progress_events
    acknowledge_order_notice=Workstation.acknowledge_order_notice
    acknowledge_notices=Workstation.acknowledge_notices
    _make_items=staticmethod(Workstation._make_items)

    def __init__(self):
        self.rows={}

    def _atomic_order(self,order_id,mutate,allow_create=False):
        updated,result=mutate(copy.deepcopy(self.rows.get(order_id)))
        if updated is not None:
            self.rows[order_id]=updated
        return result

    def _reserve_order_number(self):
        return len(self.rows)+1

    def _get(self,path):
        if path.startswith("members/"):
            return {"role":self.role,"active":True}
        raise AssertionError("Unexpected fake GET")

class NoticeTests(unittest.TestCase):
    def test_initial_note_and_update_are_distinct(self):
        order=local("23 numaralı kitap")
        order["order_notice"]=make_notice(None,order)
        self.assertTrue(initial_note_notice(order))
        legacy=copy.deepcopy(order)
        legacy["order_notice"].pop("kind")
        self.assertTrue(initial_note_notice(legacy))
        edited=copy.deepcopy(order)
        edited["order_note"]="24 numaralı kitap"
        edited["order_notice"]=make_notice(order,edited)
        self.assertFalse(initial_note_notice(edited))
        self.assertIsNone(make_notice(None,local()))

    def test_offline_ack_then_start_progress_and_complete_before_initial_sync(self):
        with tempfile.TemporaryDirectory() as directory:
            db=ERPDatabase(ROOT/"KİTAPS.xlsx",data_dir=directory)
            code=next(iter(db.katalog))
            station=FakeStation()
            class NoNetwork:
                uid="ci-device"
            db.cloud_api=NoNetwork()
            order=db.yeni_siparis_olustur(local("Ayrı koli",book=code),local(book=code)["kitaplar"])
            expected=revision(order)
            db.queue_notice_ack(order,expected)
            self.assertFalse(pending_notice(order))
            db.siparis_durumunu_degistir(order,"aktif")
            db.siparis_ilerleme_degistir(order,code,"SB",2,2)
            db.siparis_durumunu_degistir(order,"tamamlandi")
            db=ERPDatabase(ROOT/"KİTAPS.xlsx",data_dir=directory)
            order=db.siparisler[0]
            self.assertFalse(pending_notice(order))
            kinds=[]
            for _ in range(8):
                batch=db.next_outbox_batch()
                if not batch:break
                kind=batch["kind"];kinds.append(kind)
                if kind=="commit":
                    self.assertEqual(batch["edits"][0]["order"]["durum"],"havuz")
                    result=station.commit(batch["edits"])
                elif kind=="notice_ack":
                    self.assertTrue(batch["events"][0]["order_id"])
                    result=station.acknowledge_notices(batch["events"])
                elif kind=="status":result=station.transition(batch["events"])
                else:result=station.progress(batch["events"])
                db.confirm_outbox(batch,result)
                self.assertFalse(pending_notice(order))
            self.assertEqual(kinds,["commit","notice_ack","status","progress","status"])
            self.assertEqual(db.pending_count,0)
            remote=station.rows[order["bulut_id"]]
            self.assertEqual(remote["status"],"tamamlandi")
            self.assertFalse(pending_notice(remote))

    def test_old_ack_rejection_restores_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            db=ERPDatabase(ROOT/"KİTAPS.xlsx",data_dir=directory)
            code=next(iter(db.katalog))
            local_order=local("Ayrı koli",book=code)
            order=db.yeni_siparis_olustur(local_order,local_order["kitaplar"])
            order["bulut_id"]=str(uuid.uuid4());order["bulut_version"]=1
            db.siparisleri_kaydet()
            db.cloud_api=object()
            db.queue_notice_ack(order,revision(order))
            batch=db.next_outbox_batch()
            self.assertEqual(batch["kind"],"notice_ack")
            db.quarantine_batch(batch,"revision mismatch")
            self.assertTrue(pending_notice(order))
            self.assertEqual(db.pending_count,0)
            self.assertEqual(order["bulut_version"],0)

    def test_optional_creation_and_semantic_diffs(self):
        before=local()
        self.assertIsNone(make_notice(None,before))
        after=local("Ayrı kolile",code="NEW",book="102")
        first=make_notice(before,after)
        self.assertEqual({x.get("code") for x in first["changes"].values()
                          if x["type"]=="book"},{"101","102"})
        self.assertTrue(any(i["label"]=="Kargo kodu / adres" for i in first["changes"].values()
                            if i["type"]=="field"))
        after["order_notice"]=first
        further=copy.deepcopy(after)
        further["order_note"]="Yeni not"
        second=make_notice(after,further)
        self.assertGreater(len(second["changes"]),len(first["changes"]))
        further["order_notice"]=second
        with self.assertRaises(ValueError):acknowledge(further,first["revision"])
        further["order_notice"]=acknowledge(further,second["revision"],"ci")
        self.assertFalse(pending_notice(further))
        progress=copy.deepcopy(further)
        progress["kitaplar"][0]["hazir"]=1
        progress["durum"]="aktif"
        self.assertIsNone(make_notice(further,progress))

    def test_cloud_exact_revision_guard_and_owner_note(self):
        station=FakeStation()
        row=local("Özel not")
        row["order_notice"]=make_notice(None,row)
        result=station.commit([{"local_id":"1","request_id":str(uuid.uuid4()),"order":row}])[0]
        oid=result["uuid"]
        remote=station.rows[oid]
        rev=revision(remote)
        self.assertEqual(rev,revision(row))
        event={"order_id":oid,"op_id":str(uuid.uuid4()),"from_status":"havuz",
               "to_status":"aktif","notice_revision":rev}
        with self.assertRaises(DeviceError):station.transition([event])
        with self.assertRaises(DeviceError):station.acknowledge_order_notice(oid,str(uuid.uuid4()))
        receipt=station.acknowledge_order_notice(oid,rev)
        self.assertEqual(receipt["notice"]["ack_revision"],rev)
        self.assertEqual(station.acknowledge_order_notice(oid,rev)["version"],receipt["version"])
        with self.assertRaises(DeviceError):station.transition([{**event,"notice_revision":""}])
        station.transition([event])
        station.role="staff"
        edited=local("Değişmiş not")
        edit={"local_id":"1","uuid":oid,"version":station.rows[oid]["version"],"order":edited}
        with self.assertRaises(DeviceError):station.commit([edit])
        station.role="owner"
        station.commit([edit])
        newest=revision(station.rows[oid])
        self.assertNotEqual(newest,rev)
        self.assertTrue(pending_notice(station.rows[oid]))
        progress={"order_id":oid,"op_id":str(uuid.uuid4()),"book_code":"101","print_type":"SB",
                  "delta_ready":2,"delta_boxed":2,"notice_revision":newest}
        with self.assertRaises(DeviceError):station.progress([progress])
        station.acknowledge_order_notice(oid,newest)
        with self.assertRaises(DeviceError):station.progress([{**progress,"notice_revision":rev}])
        station.progress([progress])
        station.transition([{"order_id":oid,"op_id":str(uuid.uuid4()),
                             "from_status":"aktif","to_status":"tamamlandi","notice_revision":newest}])
        self.assertEqual(station.rows[oid]["status"],"tamamlandi")

    def test_local_note_lock_and_durable_ack(self):
        with tempfile.TemporaryDirectory() as directory:
            db=ERPDatabase(ROOT/"KİTAPS.xlsx",data_dir=directory)
            code=next(iter(db.katalog))
            original=local("Koliye not",book=code)
            order=db.yeni_siparis_olustur(original, original["kitaplar"])
            self.assertTrue(pending_notice(order))
            with self.assertRaises(ValueError):db.siparis_durumunu_degistir(order,"aktif")
            rev=revision(order)
            db.apply_notice_ack(order,rev,acknowledge(order,rev))
            db.siparis_durumunu_degistir(order,"aktif")
            db.siparis_ilerleme_degistir(order,code,"SB",2,2)
            db.siparis_duzenle(order,{**original,"order_note":"Farklı not"},order["kitaplar"])
            self.assertTrue(pending_notice(order))
            with self.assertRaises(ValueError):db.siparis_durumunu_degistir(order,"tamamlandi")
            reopened=ERPDatabase(ROOT/"KİTAPS.xlsx",data_dir=directory)
            self.assertTrue(pending_notice(reopened.siparisler[0]))

    def test_note_only_queue_is_not_migrated_away(self):
        with tempfile.TemporaryDirectory() as directory:
            db=ERPDatabase(ROOT/"KİTAPS.xlsx",data_dir=directory)
            code=next(iter(db.katalog))
            oid=str(uuid.uuid4()); db.cloud_epoch="ci-notices"
            row={"id":oid,"order_number":1,"status":"aktif","platform":"Dolap",
                 "shipping_reference":"TEST","order_type":"Normal Sipariş","gross_amount":100,
                 "version":1,"created_at":"2026-11-14T00:00:00Z"}
            line={"id":str(uuid.uuid4()),"order_id":oid,"book_code":code,
                  "print_type":"SB","quantity":2,"prepared_count":0,"boxed_count":0}
            payload={"epoch":"ci-notices","orders":[row],"items":[line]}
            db.apply_cloud_snapshot(payload)
            db.cloud_api=object()
            order=db.siparisler[0]
            db.siparis_duzenle(order,{**order,"order_note":"Not eklendi"},order["kitaplar"])
            self.assertEqual(db.pending_count,1)
            db.recover_old_outbox(payload)
            self.assertEqual(db.next_outbox_batch()["kind"],"commit")
            self.assertTrue(pending_notice(order))

if __name__=="__main__":
    unittest.main()
