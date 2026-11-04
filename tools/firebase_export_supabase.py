"""Read-only private Supabase snapshot for an ALFA ERP Firestore migration.

NEVER commit exported data. This is a database migration utility, not part
of the Windows app. Requires a READ-ONLY Postgres connection in the environment.
"""
import argparse
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys

TABLES = (
    ("workspaces", "id"),
    ("books", "id"),
    ("orders", "id"),
    ("order_items", "id"),
    ("accounting_days", "id"),
    ("erp_inventory_products", "id"),
    ("erp_inventory_sales", "id"),
    ("audit_events", "id"),
    ("erp_device_activity", "id"),
    ("erp_progress_ops", "id"),
    ("erp_status_ops", "id"),
    ("erp_sync_state", "workspace_id"),
)
RESTRICTED = {"erp_device_keys", "erp_pairing_codes", "workspace_members",
              "erp_analytics_access", "auth.users", "auth.sessions"}


def encode(value):
    if isinstance(value, Decimal):
        return str(value)  # Preserve exact monetary values.
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Unsupported data type: {type(value).__name__}")


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), default=encode).encode("utf-8")


def run(dsn, output, slug):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise SystemExit("Install firebase/requirements-migration.txt") from exc
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    try:
        output.chmod(0o700)
    except OSError:
        pass
    manifest = {"format": 1, "source": "Supabase public schema",
                "workspace_slug": slug, "tables": {}, "restricted_excluded": sorted(RESTRICTED)}
    # Never connect with a service_role or write-capable database user.
    with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute("SELECT id FROM public.workspaces WHERE slug=%s", (slug,))
            ws = cur.fetchall()
            if len(ws) != 1:
                raise RuntimeError("Expected exactly one source workspace")
            workspace_id = ws[0]["id"]
            manifest["workspace_id"] = str(workspace_id)
            for table, primary_key in TABLES:
                if table == "workspaces":
                    cur.execute("SELECT * FROM public.workspaces WHERE id=%s", (workspace_id,))
                else:
                    # Identifiers are fixed, enumerated constants; never user input.
                    cur.execute(f"SELECT * FROM public.{table} WHERE workspace_id=%s "
                                f"ORDER BY {primary_key}", (workspace_id,))
                rows = [dict(row) for row in cur.fetchall()]
                # Serialize, hash, and write privately; no printed order details.
                blob = canonical(rows)
                target = output / f"{table}.json"
                target.write_bytes(blob)
                try:
                    target.chmod(0o600)
                except OSError:
                    pass
                manifest["tables"][table] = {"count": len(rows),
                    "sha256": hashlib.sha256(blob).hexdigest(),
                    "primary_key": primary_key}
    manifest_path = output / "manifest.json"
    manifest_path.write_bytes(canonical(manifest))
    try:
        manifest_path.chmod(0o600)
    except OSError:
        pass
    print("Read-only snapshot created. Counts only:")
    for table, info in manifest["tables"].items():
        print(f"  {table}: {info['count']}")
    print("Snapshot contains private business records; do not upload it to public GitHub.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--workspace-slug", default="alfa-erp")
    args = parser.parse_args()
    dsn = os.environ.get("SUPABASE_DATABASE_URL")
    if not dsn:
        sys.exit("SUPABASE_DATABASE_URL must be set to a read-only DB connection URL.")
    run(dsn, args.output, args.workspace_slug)
