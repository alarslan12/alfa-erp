#!/usr/bin/env python3
"""Plan and carefully perform ALFA ERP's one-time production reset.

This does NOT reset Firebase Auth or delete the working catalog.
Run in trusted Google Cloud Shell on project alfa-erp-8700c after closing
all staff/owner apps and pausing public mobile order submission.

Default: read-only PREVIEW (creates a private, full backup).
--apply: requires an explicit interactive confirmation and an ETag-matched
atomic PUT of the complete workspace, never blind multi-node deletion.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone
from uuid import uuid4

from rtdb_migrate import PROJECT_ID, DATABASE_URL, request, session

WORKSPACE_ID = "e2fc57b1-ef52-47b2-a6c9-ecd2e3832756"
ROOT = "alfa/" + WORKSPACE_ID
CONFIRM = "ALFA-URETIM-VERISINI-SIFIRLA"
REMOVE = (
    "orders", "checkout", "audit", "archive", "accounting",
    "inventory", "device_requests", "analytics_pin",
)


def private_backup(data, epoch):
    destination = Path.home() / "alfa_erp_private_backups"
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(destination, 0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = destination / f"firebase_before_production_{stamp}_{epoch[:8]}.json.gz"
    if path.exists():
        raise RuntimeError("Backup filename collision. Retry once UTC second changes.")
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as sink:
        with gzip.GzipFile(fileobj=sink, mode="wb", filename="") as zipped:
            zipped.write(raw)
    with gzip.open(path, "rb") as source:
        if hashlib.sha256(source.read()).hexdigest() != digest:
            raise RuntimeError("Backup checksum mismatch; reset ABORTED")
    digest_path = Path(str(path) + ".sha256")
    digest_path.write_text(digest + "  " + path.name + "\n", encoding="ascii")
    os.chmod(digest_path, 0o600)
    return path, digest


def main():
    parser = argparse.ArgumentParser(description="ALFA ERP clean production cutover")
    parser.add_argument("--apply", action="store_true",
                        help="Reset only after private backup and interactive confirmation")
    args = parser.parse_args()
    if PROJECT_ID != "alfa-erp-8700c" or "alfa-erp-8700c" not in DATABASE_URL:
        raise RuntimeError("Incorrect Firebase target")
    client = session()
    before, etag, status = request(client, "GET", ROOT, etag=True)
    if status != 200 or not isinstance(before, dict) or not etag:
        raise RuntimeError("Workspace is missing or ETag unavailable. Aborting.")
    meta = before.get("meta") or {}
    epoch = str(meta.get("epoch") or "")
    revisions = meta.get("revisions") or {}
    books = before.get("books") or {}
    public = before.get("public_catalog") or {}
    members = before.get("members") or {}
    if not epoch or not isinstance(revisions, dict):
        raise RuntimeError("Existing production epoch/revisions not recognized")
    if not isinstance(books, dict) or len(books) < 1 or not public:
        raise RuntimeError("Book catalog missing; refusing reset")
    if not isinstance(members, dict) or not any(
        isinstance(x, dict) and x.get("active") and x.get("role") == "owner"
        for x in members.values()
    ):
        raise RuntimeError("Approved owner not found. Refusing reset.")
    orders = before.get("orders") or {}
    checkout = before.get("checkout") or {}
    requests = sum(len(v) for v in checkout.values() if isinstance(v, dict)) if isinstance(checkout,dict) else -1
    print("Firebase project:", PROJECT_ID)
    print("Workspace:", WORKSPACE_ID)
    print("Catalog books (PRESERVED):", len(books))
    print("Approved device memberships (PRESERVED):", len(members))
    print("Orders to remove:", len(orders))
    print("Mobile checkout requests to remove:", requests)
    print("Other experimental nodes to remove:", ", ".join(REMOVE[2:]))
    backup, digest = private_backup(before, epoch)
    print("\nPRIVATE BACKUP VERIFIED:", backup)
    print("SHA256:", digest)
    print("Keep this file OFF GITHUB and copy it off Cloud Shell before final cutover.")
    if not args.apply:
        print("\nREAD-ONLY preflight finished. Firebase data was NOT modified.")
        print("For the actual reset: close both desktop apps, stop mobile orders,")
        print("check all desktop pending queues are zero, then rerun with --apply.")
        return 0
    if not sys.stdin.isatty():
        raise RuntimeError("Interactive terminal required for destructive reset")
    print("\nWARNING: This removes test orders, checkout, inventory, legacy audit,")
    print("accounting, and the UI Analytics PIN. Books and approved members stay.")
    print("Old desktop local test records are backed up when epoch changes.")
    confirm = input("Type " + CONFIRM + " to authorize reset: ").strip()
    if confirm != CONFIRM:
        print("Cancelled. Firebase remains unchanged.")
        return 2
    # Perform one conditional write of the entire workspace to prevent a
    # competing mobile order or owner edit being silently discarded.
    future = dict(before)
    for key in REMOVE:
        future.pop(key, None)
    changed_meta = dict(meta)
    changed_meta["epoch"] = str(uuid4())
    changed_meta["order_counter"] = 0
    changed_meta["revisions"] = {
        name: max(1, int(revisions.get(name) or 0) + 1)
        for name in ("orders", "catalog", "inventory")
    }
    changed_meta["production_cutover_at"] = datetime.now(timezone.utc).isoformat()
    future["meta"] = changed_meta
    result, _, put_status = request(client, "PUT", ROOT, future, match=etag)
    if put_status == 412:
        raise RuntimeError(
            "Another device wrote during the reset. CONDITIONAL WRITE REJECTED; "
            "no reset. Inspect activity and retry with a new backup."
        )
    if put_status not in (200, 204):
        raise RuntimeError(f"Unexpected Firebase response {put_status}; inspect manually")
    current_meta, _, _ = request(client, "GET", ROOT + "/meta")
    current_orders, _, _ = request(client, "GET", ROOT + "/orders")
    if current_meta.get("epoch") != changed_meta["epoch"] or current_orders:
        raise RuntimeError("Post-cutover verification failed; RESTORE FROM BACKUP")
    print("\nPRODUCTION RESET VERIFIED. New epoch:", changed_meta["epoch"])
    print("Catalog and owner memberships were preserved. Do not repeat reset.")
    print("Restart desktop apps and reconfigure the Analytics PIN.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("ABORTED:", str(error), file=sys.stderr)
        raise SystemExit(1)
