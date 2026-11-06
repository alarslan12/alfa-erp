"""ALFACOPYCENTER ERP 2.0.1 regression tests: offline, no Firebase writes."""
from __future__ import annotations

import copy
import unittest

from alfa_rtdb import Workstation, DeviceError
from bulut_canli import Sync
from PySide6.QtCore import QCoreApplication


def item(qty=1,ready=0,boxed=0):
    return {"book_code":"443","print_type":"SB","quantity":qty,
            "prepared_count":ready,"boxed_count":boxed,"version":1}


def order(qty=1,ready=0,boxed=0,status="aktif"):
    return {"id":"test","status":status,"version":7,
            "items":{"book":item(qty,ready,boxed)},
            "ops":{},"event_log":{}}


def op(identifier,ready_delta=0,boxed_delta=0,
       target_ready=0,target_boxed=0):
    return {"op_id":identifier,"order_id":"test","book_code":"443",
            "print_type":"SB","delta_ready":ready_delta,
            "delta_boxed":boxed_delta,"target_ready":target_ready,
            "target_boxed":target_boxed}


class FakeWorkstation(Workstation):
    paired=False

    def __init__(self,row):
        self.row=copy.deepcopy(row)
        self.writes=0
        self._identity={"uid":"test-device","refresh_token":"test"}

    def _atomic_order(self,order_id,mutate,allow_create=False):
        assert order_id=="test"
        updated,result=mutate(copy.deepcopy(self.row))
        if updated is not None:
            self.row=updated
            self.writes+=1
        return result


class CloudProgressTests(unittest.TestCase):
    def test_same_ready_target_not_double_counted_and_ack_persisted(self):
        client=FakeWorkstation(order(ready=1))
        event=op("other-device",ready_delta=1,target_ready=1)
        result=client.progress([event])
        self.assertEqual(client.row["items"]["book"]["prepared_count"],1)
        self.assertEqual(result[0]["op_id"],"other-device")
        self.assertIn("other-device",client.row["ops"])
        self.assertEqual(client.writes,1)
        # A future OTHER operation lowers count: replay of the acknowledged
        # op must NEVER put a physically unprepared book back.
        client.row["items"]["book"]["prepared_count"]=0
        client.progress([event])
        self.assertEqual(client.row["items"]["book"]["prepared_count"],0)
        self.assertEqual(client.writes,1)

    def test_same_boxed_target_not_double_counted(self):
        client=FakeWorkstation(order(ready=1,boxed=1))
        client.progress([op("same-box",boxed_delta=1,
                            target_ready=1,target_boxed=1)])
        self.assertEqual(client.row["items"]["book"]["boxed_count"],1)
        self.assertIn("same-box",client.row["ops"])

    def test_fast_consecutive_clicks_reach_intended_local_target(self):
        client=FakeWorkstation(order(qty=3))
        client.progress([op("one",ready_delta=1,target_ready=1),
                         op("two",ready_delta=1,target_ready=2)])
        self.assertEqual(client.row["items"]["book"]["prepared_count"],2)
        self.assertEqual(set(client.row["ops"]),{"one","two"})
        self.assertEqual(client.writes,1)

    def test_inactive_order_cannot_gain_new_progress(self):
        client=FakeWorkstation(order(status="tamamlandi"))
        with self.assertRaises(DeviceError) as outcome:
            client.progress([op("late",ready_delta=1,target_ready=1)])
        self.assertEqual(outcome.exception.status,409)
        self.assertEqual(client.writes,0)

    def test_new_click_prepared_then_boxed_preserves_invariant(self):
        client=FakeWorkstation(order(qty=2))
        client.progress([op("prepared",ready_delta=1,target_ready=1)])
        client.progress([op("boxed",boxed_delta=1,target_ready=1,
                            target_boxed=1)])
        book=client.row["items"]["book"]
        self.assertEqual((book["prepared_count"],book["boxed_count"]),(1,1))


class FakeDB:
    pending_count=0


class SyncLatencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QCoreApplication.instance() or QCoreApplication(["alfa-test-sync"])

    def setUp(self):
        class Client:
            paired=False
        self.sync=Sync(Client(),FakeDB())
        self.sync.last_pulse={"epoch":"e","orders_revision":10,
                              "catalog_revision":2,"inventory_revision":3}
        self.sync.force_pull=False
        self.sync._last_orders_verified=100.0
        self.sync._recent_until=0

    def tearDown(self):
        self.sync._event_pull_timer.stop()

    def test_idle_safety_refresh_after_three_minutes(self):
        self.assertEqual(self.sync._revision_request(now=150)[0]
                         ["orders_revision"],10)
        self.assertEqual(self.sync._revision_request(now=281)[0]
                         ["orders_revision"],-1)

    def test_active_refresh_after_two_minutes(self):
        self.sync._recent_until=1000.0
        self.assertEqual(self.sync._revision_request(now=221)[0]
                         ["orders_revision"],-1)

    def test_sse_refresh_is_queued_while_network_pull_busy(self):
        self.sync.request_authoritative_refresh()
        self.assertTrue(self.sync.force_pull)
        self.assertEqual(self.sync._event_serial,1)
        self.assertTrue(self.sync._event_pull_timer.isActive())
        self.sync._realtime_event()
        self.assertEqual(self.sync._event_serial,2)


if __name__=="__main__":
    unittest.main(verbosity=2)
