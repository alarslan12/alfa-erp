"""Offline contract checks for ALFA Print Surveillance on Windows CI.

These tests use fake spool snapshots and an isolated SQLite journal.
They never access a real printer, touch production data, request elevated
permissions or submit/erase any print job.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from alfa_print_monitor import PrintJournal
from alfa_print_plan import PrintPlanRepository, PrintPlanError
from alfa_print_ipp import _request_body, _parse_ipp, IppTelemetryError
from alfa_print_snmp import _snmp_packet, SnmpTelemetryError
from alfa_print_runtime import PrintAgentLease, PrintCollectorLease


def fake_job(pages=0, state="yazdırılıyor"):
    return {
        "key":"fixture-printer-42", "printer":"DEMO_PRINTER",
        "native_id":42, "document":"Sample Book.pdf",
        "submitted":"2026-11-06T12:00:00+00:00", "owner":"qa",
        "position":1, "pages":pages, "total":300,
        "bytes":320000, "state":state, "detail":"",
        "color":"Siyah-beyaz (sürücü)"
    }


class PrintContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="alfa_print_contract_")
        self.root=Path(self.temp.name)
        self.journal=PrintJournal(self.root)
        self.repo=PrintPlanRepository(self.root)

    def tearDown(self):
        self.repo.close()
        self.journal.close()
        self.temp.cleanup()

    def test_interrupted_resume_requires_manual_last_good_pdf_page(self):
        original=self.root/"book.pdf"
        original.write_bytes(b"%PDF-1.4\nlocal fixture\n")
        task=self.repo.create(
            printer="DEMO_PRINTER",book="Sample Book",mode="SB",
            copies=1,page_start=1,page_end=300,pdf_path=str(original))
        self.journal.change([{"name":"DEMO_PRINTER",
                              "jobs":[fake_job(142)],"error":""}])
        self.repo.link_job(task,fake_job()["key"])
        self.assertEqual(self.repo.reconcile(),[])
        first=self.repo.list()[0]
        self.assertEqual(first["last_reported_pages"],142)
        # A remote status failure never marks printed or disappeared.
        self.journal.change([{"name":"DEMO_PRINTER",
                              "jobs":[],"error":"network offline"}])
        self.assertEqual(self.repo.reconcile(),[])
        self.assertEqual(self.repo._task(task)["state"],"queued")
        # When Windows *successfully* shows an empty queue, physical output
        # is UNKNOWN, no automatic resend or printed status is allowed.
        self.journal.change([{"name":"DEMO_PRINTER","jobs":[],"error":""}])
        interrupted=self.repo.reconcile()
        self.assertEqual(len(interrupted),1)
        self.assertEqual(interrupted[0]["windows_counter"],142)
        self.assertEqual(self.repo._task(task)["state"],"verify")
        new=self.repo.create_resume(task,140,"Pages 1-140 checked on paper")
        self.assertEqual(new["resume_from"],141)
        self.assertEqual(self.repo._task(task)["state"],"resumed")
        self.assertEqual(self.repo._task(new["task_id"])["page_start"],141)
        with self.assertRaises(PrintPlanError):
            self.repo.create_resume(task,140,"Don't duplicate job")

    def test_multi_copy_resume_is_not_guessed(self):
        original=self.root/"multi.pdf"
        original.write_bytes(b"%PDF-1.4\ntest\n")
        task=self.repo.create(
            printer="DEMO_PRINTER",book="Two copies",mode="RENK",
            copies=2,page_end=40,pdf_path=str(original))
        self.journal.change([{"name":"DEMO_PRINTER",
                              "jobs":[fake_job(12)],"error":""}])
        self.repo.link_job(task,fake_job()["key"])
        self.journal.change([{"name":"DEMO_PRINTER","jobs":[],"error":""}])
        self.repo.reconcile()
        with self.assertRaises(PrintPlanError):
            self.repo.create_resume(task,11,"Two copies differ")

    def test_local_print_agent_mutex_is_singleton(self):
        first=PrintAgentLease(self.root)
        try:
            self.assertTrue(first.acquired)
            second=PrintAgentLease(self.root)
            try:self.assertFalse(second.acquired)
            finally:second.close()
        finally:
            first.close()
        check=PrintCollectorLease(self.root)
        self.assertTrue(check.acquired)
        check.close()

    def test_only_read_only_protocol_operations(self):
        ipp=_request_body(0x000B,"ipp://127.0.0.1/ipp/print",(
            "printer-state","queued-job-count"))
        self.assertEqual(ipp[2:4],b"\x00\x0b")
        with self.assertRaises(IppTelemetryError):
            _request_body(0x0002,"ipp://127.0.0.1/ipp/print",())
        get=_snmp_packet("public",(1,3,6,1,2,1,1,1,0),0xA0,11)
        self.assertIn(b"\xa0",get)
        with self.assertRaises(SnmpTelemetryError):
            _snmp_packet("public",(1,3,6,1,2,1,1,1,0),0xA3,11)


if __name__=="__main__":
    unittest.main(verbosity=2)
