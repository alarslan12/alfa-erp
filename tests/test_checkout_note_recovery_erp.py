"""Checkout notes use the desktop notice protocol; never call live Firebase."""
import copy
import json
import unittest
import uuid
from pathlib import Path

from alfa_rtdb import Workstation, WORKSPACE_ID
from siparis_uyari import pending_notice, initial_note_notice, acknowledge, revision


class CheckoutStation:
    _adopt_checkout = Workstation._adopt_checkout
    _make_items = staticmethod(Workstation._make_items)
    uid = "ci-staff"

    def __init__(self, note=None):
        self.request_id = str(uuid.uuid4())
        self.request_uid = "ci-mobile"
        self.rows = {}
        self.counter = 0
        self._checkout_dirty = True
        self._checkout_last_checked = 0
        self._catalog_cache = None
        self.request = {
            "uid": self.request_uid,
            "request_id": self.request_id,
            "platform": "Dolap",
            "shipping_reference": "CI-100",
            "order_type": "normal",
            "gross_amount": 100,
            "items": {"0": {"code": "101", "quantity": 2, "print_type": "SB"}},
        }
        if note is not None:
            self.request["order_note"] = note

    def _get(self, path):
        if path == "checkout":
            return {self.request_uid: {self.request_id: self.request}}
        if path == "public_catalog":
            return {"101": {
                "code": "101", "name": "CI kitap", "page_count": 120,
                "supports_color": True,
            }}
        if path.startswith("orders/"):
            return copy.deepcopy(self.rows.get(path.removeprefix("orders/")))
        raise AssertionError("Unexpected GET " + path)

    def _reserve_order_number(self):
        self.counter += 1
        return self.counter

    def _atomic_order(self, order_id, mutate, allow_create=False):
        result, receipt = mutate(copy.deepcopy(self.rows.get(order_id)))
        if result is not None:
            self.rows[order_id] = result
        return receipt

    def adopt(self):
        self._checkout_dirty = True
        self._adopt_checkout()
        return self.rows

    def existing_order(self, note_missing=True):
        # Older Suite v2.0.52: checkout was adopted without order_note.
        self.adopt()
        order_id = next(iter(self.rows))
        order = self.rows[order_id]
        order.pop("order_note", None)
        order.pop("order_notice", None)
        order["status"] = "aktif"
        order["version"] = 8
        order["items"][next(iter(order["items"]))]["prepared_count"] = 1
        if not note_missing:
            order["order_note"] = "Masaüstünde düzenlenen not"
        return order_id


class MobileCheckoutNoteTests(unittest.TestCase):
    def test_initial_note_is_pending_and_acknowledgeable(self):
        station = CheckoutStation("  Ayrı kolilensin  ")
        rows = station.adopt()
        self.assertEqual(len(rows), 1)
        order = next(iter(rows.values()))
        self.assertEqual(order["order_note"], "Ayrı kolilensin")
        self.assertEqual(order["status"], "havuz")
        self.assertTrue(initial_note_notice(order))
        self.assertTrue(pending_notice(order))
        notice = order["order_notice"]
        self.assertEqual(notice["kind"], "initial_note")
        self.assertEqual(len(notice["changes"]), 1)
        change = next(iter(notice["changes"].values()))
        self.assertEqual(change["label"], "Yeni sipariş notu")
        self.assertEqual(change["new"], "Ayrı kolilensin")
        self.assertFalse(pending_notice({**order,
            "order_notice": acknowledge(order, revision(order), "ci-owner")}))
        first = copy.deepcopy(order)
        station.adopt()
        self.assertEqual(next(iter(station.rows.values())), first)
        self.assertEqual(station.counter, 1)

    def test_blank_and_missing_notes_do_not_create_warning(self):
        for note in (None, "", "   "):
            with self.subTest(note=note):
                station = CheckoutStation(note)
                order = next(iter(station.adopt().values()))
                self.assertNotIn("order_notice", order)
                self.assertNotIn("order_note", order)

    def test_exact_2000_characters_is_accepted(self):
        station = CheckoutStation("N" * 2000)
        order = next(iter(station.adopt().values()))
        self.assertEqual(len(order["order_note"]), 2000)
        self.assertTrue(pending_notice(order))

    def test_invalid_notes_do_not_create_orders(self):
        for value in ("X" * 2001, {"spoof": "note"}, 4, None):
            with self.subTest(value=type(value).__name__):
                station = CheckoutStation()
                station.request["order_note"] = value
                self.assertFalse(station.adopt())
                self.assertEqual(station.counter, 0)

    def test_historical_order_is_not_modified(self):
        station = CheckoutStation("Eski checkout notu")
        oid = station.existing_order()
        before = copy.deepcopy(station.rows[oid])
        station.adopt()
        self.assertEqual(station.rows[oid], before)
        self.assertEqual(station.counter, 1)

    def test_no_source_note_cannot_be_reconstructed(self):
        station = CheckoutStation()
        oid = station.existing_order()
        before = copy.deepcopy(station.rows[oid])
        station.adopt()
        self.assertEqual(station.rows[oid], before)

    def test_rules_allow_only_optional_string_note_up_to_2000(self):
        root = Path(__file__).resolve().parents[1]
        with (root / "firebase/database.rules.json").open(encoding="utf-8") as f:
            rules = json.load(f)["rules"]
        request = rules["alfa"]["$workspace"]["checkout"]["$uid"]["$requestId"]
        self.assertIn("!data.exists()", request[".write"])
        self.assertIn("auth.uid === $uid", request[".write"])
        self.assertEqual(request["$other"][".validate"], False)
        self.assertNotIn("order_note", request[".write"].split("hasChildren(")[1].split(")")[0])
        self.assertEqual(request["order_note"][".validate"],
                         "newData.isString() && newData.val().length <= 2000")


if __name__ == "__main__":
    unittest.main()
