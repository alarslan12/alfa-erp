"""Verify every source snapshot row against a Firestore staging upload.

Read-only Firestore operation. Counts plus canonical per-row content comparison.
No private customer/order data is printed on failure.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

def verify(source, project_id):
    if project_id != "alfa-erp-8700c":
        raise ValueError("Unexpected Firebase project. Refusing to verify.")
    from google.cloud import firestore
    source = Path(source)
    raw_manifest = (source / "manifest.json").read_bytes()
    manifest = json.loads(raw_manifest)
    if manifest.get("format") != 1 or manifest.get("workspace_slug") != "alfa-erp":
        raise ValueError("Invalid snapshot manifest.")
    workspace_id = str(manifest["workspace_id"])
    manifest_digest = hashlib.sha256(raw_manifest).hexdigest()
    migration_id = ("alfa_erp_" + workspace_id.replace("-", "")
                    + "_" + manifest_digest[:12])
    client = firestore.Client(project=project_id)
    root = client.collection("migration_staging").document(migration_id)
    meta = root.get()
    if not meta.exists:
        raise RuntimeError("Firebase staging root is missing")
    state = meta.to_dict()
    if state.get("state") != "staged" or state.get("manifest_sha256") != manifest_digest:
        raise RuntimeError("Staging not completed or manifest hash mismatch")
    total = 0
    for table, details in manifest["tables"].items():
        payload = (source / f"{table}.json").read_bytes()
        if hashlib.sha256(payload).hexdigest() != details["sha256"]:
            raise RuntimeError(f"{table}: source checksum mismatch")
        rows = json.loads(payload)
        if len(rows) != details["count"]:
            raise RuntimeError(f"{table}: source count mismatch")
        collection = root.collection("tables").document(table).collection("rows")
        # Stream once per table instead of ~one HTTP request per row.
        remote = {document.id: document.to_dict() for document in collection.stream()}
        seen = set()
        for source_row in rows:
            key = str(source_row[details["primary_key"]])
            if key in seen:
                raise RuntimeError(f"{table}: duplicate source key")
            seen.add(key)
            if key not in remote:
                raise RuntimeError(f"{table}: missing document")
            if remote[key] != source_row:
                raise RuntimeError(f"{table}: data mismatch")
        if set(remote) != seen:
            raise RuntimeError(f"{table}: unexpected documents in staging")
        total += len(rows)
        print(f"{table}: {len(rows)} verified")
    if total != state.get("staged_row_count") or total != state.get("row_count"):
        raise RuntimeError("Global total mismatch")
    print(f"VERIFIED: {total} records staged, all values match source snapshot.")
    print("This is NOT a production cutover. Supabase remains live.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--project-id", required=True)
    args = ap.parse_args()
    try:
        verify(args.input, args.project_id)
    except Exception as exc:
        sys.exit("VERIFY FAILED: " + str(exc))
