"""ALFA ERP Supabase -> Firebase RTDB, reversible private staging.

Uses a read-only source snapshot. Never commits customer data, and never
overwrites an existing live workspace. Requires Google ADC with RTDB IAM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ID = "alfa-erp-8700c"
DATABASE_URL = "https://alfa-erp-8700c-default-rtdb.europe-west1.firebasedatabase.app"
SCOPES = [
    "https://www.googleapis.com/auth/firebase.database",
    "https://www.googleapis.com/auth/userinfo.email",
]
PRIMARY_KEYS = {
    "workspaces": "id", "books": "id", "orders": "id",
    "order_items": "id", "accounting_days": "id",
    "erp_inventory_products": "id", "erp_inventory_sales": "id",
    "audit_events": "id", "erp_device_activity": "id",
    "erp_progress_ops": "id", "erp_status_ops": "id",
    "erp_sync_state": "workspace_id",
}


def packed(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def prune_empty(value):
    # Firebase RTDB stores empty objects as absent nodes, unlike SQL/JSON.
    # Canonicalize both the staged input and readback for exact verification.
    if isinstance(value, dict):
        kept = {k: v for k, raw in value.items()
                if (v := prune_empty(raw)) is not None}
        return kept or None
    if isinstance(value, list):
        return [prune_empty(x) for x in value]
    return value


def load_snapshot(folder):
    folder = Path(folder)
    raw_manifest = (folder / "manifest.json").read_bytes()
    manifest = json.loads(raw_manifest)
    if manifest.get("format") != 1 or manifest.get("workspace_slug") != "alfa-erp":
        raise ValueError("Invalid ALFA ERP snapshot")
    workspace_id = str(manifest.get("workspace_id") or "")
    if not re.fullmatch(r"[0-9a-f-]{36}", workspace_id):
        raise ValueError("Invalid source workspace UUID")
    if set(manifest["tables"]) != set(PRIMARY_KEYS):
        raise ValueError("Snapshot is incomplete or has unexpected tables")
    data = {}
    for table, pk in PRIMARY_KEYS.items():
        info = manifest["tables"][table]
        if info["primary_key"] != pk:
            raise ValueError(f"{table}: unexpected primary key")
        blob = (folder / f"{table}.json").read_bytes()
        if hashlib.sha256(blob).hexdigest() != info["sha256"]:
            raise ValueError(f"{table}: checksum mismatch")
        rows = json.loads(blob)
        if len(rows) != info["count"]:
            raise ValueError(f"{table}: row count mismatch")
        keys = [str(row[pk]) for row in rows]
        if len(set(keys)) != len(keys):
            raise ValueError(f"{table}: duplicate primary keys")
        if table != "workspaces" and any(str(row["workspace_id"]) != workspace_id for row in rows):
            raise ValueError(f"{table}: cross-workspace row")
        data[table] = {str(row[pk]): row for row in rows}
    if len(data["workspaces"]) != 1 or workspace_id not in data["workspaces"]:
        raise ValueError("Source workspace mismatch")
    return manifest, data, hashlib.sha256(raw_manifest).hexdigest()


def candidate_from_rows(manifest, rows):
    wsid = manifest["workspace_id"]
    sync = rows["erp_sync_state"].get(wsid)
    if not sync or not sync.get("epoch"):
        raise ValueError("Cloud sync state missing; refusing a new epoch")
    books = rows["books"]
    orders = {}
    items_by_order = defaultdict(dict)
    for item_id, item in rows["order_items"].items():
        oid = str(item["order_id"])
        if oid not in rows["orders"]:
            raise ValueError(f"Orphan order item {item_id}")
        items_by_order[oid][item_id] = item
    for oid, order in rows["orders"].items():
        orders[oid] = {**order, "items": items_by_order.get(oid, {})}
    public_catalog = {}
    for book in books.values():
        code = str(book.get("code") or "")
        if code in public_catalog:
            raise ValueError("Duplicate catalog code")
        if book.get("is_active") is True:
            public_catalog[code] = {
                "code": code, "name": book.get("name") or "",
                "group_name": book.get("group_name") or "",
                "page_count": book.get("page_count") or 0,
                "supports_color": bool(book.get("supports_color")),
            }
    counts = {table: len(values) for table, values in rows.items()}
    latest = max([0] + [int(o.get("order_number") or 0) for o in orders.values()])
    inventory = {
        "products": rows["erp_inventory_products"],
        "sales": rows["erp_inventory_sales"],
    }
    result = {
        "meta": {
            "epoch": sync["epoch"],
            "revisions": {
                "catalog": max(1, int(sync.get("catalog_revision") or 1)),
                "orders": max(1, int(sync.get("orders_revision") or 1)),
                "inventory": max(1, int(sync.get("inventory_revision") or 1)),
            },
            "order_counter": latest,
            "schema": "rtdb-v1",
        },
        "books": books,
        "orders": orders,
        "inventory": inventory,
        "accounting": rows["accounting_days"],
        "audit": rows["audit_events"],
        "archive": {
            "erp_device_activity": rows["erp_device_activity"],
            "erp_progress_ops": rows["erp_progress_ops"],
            "erp_status_ops": rows["erp_status_ops"],
        },
        "public_catalog": public_catalog,
        "checkout": {},
        "members": {},
        "device_requests": {},
    }
    if len(result["orders"]) != len(rows["orders"]) or sum(len(o["items"]) for o in orders.values()) != len(rows["order_items"]):
        raise ValueError("Order/line mismatch in candidate")
    return result, counts


def session():
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
    except ImportError as exc:
        raise SystemExit("Install google-auth and requests on the trusted migration machine") from exc
    credentials, project_id = google.auth.default(scopes=SCOPES)
    if project_id and project_id != PROJECT_ID:
        raise RuntimeError(f"Wrong active Google project {project_id}; expected {PROJECT_ID}")
    return AuthorizedSession(credentials)


def request(client, method, path, payload=None, etag=False, match=None):
    headers = {"Accept": "application/json"}
    if etag:
        headers["X-Firebase-ETag"] = "true"
    if match is not None:
        headers["if-match"] = match
    url = DATABASE_URL + "/" + path.strip("/") + ".json"
    result = client.request(method, url, json=payload if method in ("PUT", "PATCH") else None,
                            headers=headers, timeout=40)
    if result.status_code in (401, 403):
        raise RuntimeError("Firebase IAM permission denied; verify the signed-in project owner")
    if result.status_code >= 400 and result.status_code != 412:
        if path == ".settings/rules":
            # Rules compilation errors contain source positions; no database
            # rows or credentials are printed with this diagnostic.
            try:
                detail = result.json()
                detail = detail.get("error", detail) if isinstance(detail, dict) else detail
                detail = str(detail)[:1100]
            except (ValueError, TypeError):
                detail = "No structured compiler diagnostic returned"
            raise RuntimeError(f"Firebase Rules HTTP {result.status_code}: {detail}")
        raise RuntimeError(f"Firebase HTTP {result.status_code}, {path}")
    return (result.json() if result.content else None), result.headers.get("ETag"), result.status_code


def migrate(folder, apply=False, promote=False, deploy_rules=False, rules_file=None):
    manifest, data, digest = load_snapshot(folder)
    candidate, counts = candidate_from_rows(manifest, data)
    wsid = manifest["workspace_id"]
    stage_id = "alfa_erp_" + wsid.replace("-", "") + "_" + digest[:12]
    payload = prune_empty({
        "manifest_sha256": digest,
        "workspace_id": wsid,
        "source_count": counts,
        "candidate": candidate,
        "state": "staged",
    })
    print("Source:", sum(counts.values()), "rows; orders:", counts["orders"],
          "items:", counts["order_items"], "books:", counts["books"])
    print("RTDB staging path: migration_staging/" + stage_id)
    if not apply and not promote and not deploy_rules:
        print("DRY RUN: No Firebase network access, no writes.")
        return
    client = session()
    if deploy_rules:
        if not rules_file:
            raise RuntimeError("Rules path required")
        parsed_rules = json.loads(Path(rules_file).read_text(encoding="utf-8"))
        if parsed_rules.get("rules", {}).get(".read") is not False:
            raise RuntimeError("Root read must be false")
        if parsed_rules.get("rules", {}).get(".write") is not False:
            raise RuntimeError("Root write must be false")
        # Back up exact existing rules before replacing them.
        # The backup remains private beside the source snapshot.
        current_rules, _, _ = request(client, "GET", ".settings/rules")
        backup = Path(folder) / "rtdb_rules_before_import.json"
        if not backup.exists():
            backup.write_bytes(packed(current_rules))
            backup.chmod(0o600)
        result, _, code = request(client, "PUT", ".settings/rules", parsed_rules)
        confirmed, _, _ = request(client, "GET", ".settings/rules")
        if confirmed != parsed_rules:
            raise RuntimeError("Published RTDB rules do not match local rules file")
        print("Rules deployment verified:", code)
    if apply:
        existing, etag, _ = request(client, "GET", "migration_staging/" + stage_id, etag=True)
        if existing is not None and existing.get("manifest_sha256") != digest:
            raise RuntimeError("Staging ID belongs to a different snapshot")
        if existing is None:
            _, _, code = request(client, "PUT", "migration_staging/" + stage_id,
                                 payload, match="null_etag")
            if code != 200:
                raise RuntimeError("Concurrent staging write; no overwrite")
        echoed, _, _ = request(client, "GET", "migration_staging/" + stage_id)
        if prune_empty(echoed) != payload:
            raise RuntimeError("Staging validation mismatch; live data untouched")
        print("STAGING VERIFIED", sum(counts.values()), "source rows")
    if promote:
        staged, _, _ = request(client, "GET", "migration_staging/" + stage_id)
        if not staged or staged.get("manifest_sha256") != digest:
            raise RuntimeError("Verified private staging is required before promotion")
        if prune_empty(staged.get("candidate")) != prune_empty(candidate):
            raise RuntimeError("Staging does not match local snapshot")
        _, _, code = request(client, "PUT", "alfa/" + wsid,
                             candidate, match="null_etag")
        if code == 412:
            raise RuntimeError("Live RTDB workspace already exists. Refusing overwrite.")
        final, _, _ = request(client, "GET", "alfa/" + wsid)
        if prune_empty(final) != prune_empty(candidate):
            raise RuntimeError("Promotion readback mismatch; investigate immediately")
        print("LIVE RTDB COPY VERIFIED. Supabase was NOT changed.")
        print("Clients must remain on legacy backend until explicit coordinated cutover.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--apply", action="store_true", help="Create and verify private staging")
    parser.add_argument("--promote", action="store_true", help="Promote only if live workspace is empty")
    parser.add_argument("--deploy-rules", action="store_true")
    parser.add_argument("--rules-file", default="firebase/database.rules.json")
    args = parser.parse_args()
    try:
        migrate(args.input, apply=args.apply, promote=args.promote,
                deploy_rules=args.deploy_rules, rules_file=args.rules_file)
    except Exception as exc:
        sys.exit("RTDB migration stopped: " + str(exc))
