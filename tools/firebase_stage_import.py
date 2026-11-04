"""Verify a private ALFA ERP export and stage it in Firestore.

Defaults to NO NETWORK / DRY RUN. --apply requires explicit project ID.
Only writes to migration_staging, not live production collections.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

def run(source, project_id, apply):
    source = Path(source)
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != 1 or manifest.get("workspace_slug") != "alfa-erp":
        raise ValueError("Unrecognized migration manifest")
    wsid = str(manifest["workspace_id"])
    if not re.fullmatch(r"[0-9a-f-]{36}", wsid):
        raise ValueError("Invalid source workspace ID")
    data = {}
    count = 0
    for table, info in manifest["tables"].items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", table):
            raise ValueError("Unexpected table")
        blob = (source / f"{table}.json").read_bytes()
        if hashlib.sha256(blob).hexdigest() != info["sha256"]:
            raise ValueError(f"{table}: snapshot checksum mismatch")
        rows = json.loads(blob)
        if len(rows) != info["count"]:
            raise ValueError(f"{table}: snapshot count mismatch")
        id_key = info["primary_key"]
        ids = [str(row[id_key]) for row in rows]
        if len(set(ids)) != len(ids):
            raise ValueError(f"{table}: duplicate primary keys")
        if table != "workspaces" and any(str(row.get("workspace_id")) != wsid for row in rows):
            raise ValueError(f"{table}: foreign workspace record")
        data[table] = rows
        count += len(rows)
    print(f"Validated snapshot {wsid}: {len(data)} tables, {count} rows.")
    for table, rows in data.items():
        print(f"  {table}: {len(rows)}")
    if not apply:
        print("DRY RUN — no Firebase connection, no writes.")
        return
    if not project_id or not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project_id):
        raise ValueError("--project-id must be explicit and valid")
    try:
        from google.cloud import firestore
    except ImportError as exc:
        raise SystemExit("Install firebase/requirements-migration.txt") from exc
    client = firestore.Client(project=project_id)
    # Stable per snapshot, but different exports cannot overwrite one another.
    snapshot_fingerprint = hashlib.sha256((source / "manifest.json").read_bytes()).hexdigest()[:12]
    migration_id = "alfa_erp_" + wsid.replace("-", "") + "_" + snapshot_fingerprint
    root = client.collection("migration_staging").document(migration_id)
    if root.get().exists:
        raise RuntimeError("Staging ID already exists. Refusing to overwrite or resume silently.")
    root.set({"state": "uploading", "source_workspace_id": wsid,
              "source_manifest": manifest, "row_count": count})
    batch = client.batch()
    pending = 0
    for table, rows in data.items():
        id_key = manifest["tables"][table]["primary_key"]
        for row in rows:
            doc_id = str(row[id_key])
            # Explicit staging namespace; never touch live business collections.
            ref = root.collection("tables").document(table).collection("rows").document(doc_id)
            batch.set(ref, row)
            pending += 1
            if pending == 300:
                batch.commit()
                batch, pending = client.batch(), 0
    if pending:
        batch.commit()
    # This marks upload complete, NOT production-ready.
    root.update({"state": "staged", "staged_row_count": count,
                 "manifest_sha256": hashlib.sha256((source / "manifest.json").read_bytes()).hexdigest()})
    print(f"Staged {count} documents in Firebase project {project_id}.")
    print("No live collections or Supabase data were changed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--project-id")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        run(args.input, args.project_id, args.apply)
    except Exception as exc:
        sys.exit(f"Migration staging stopped: {exc}")
