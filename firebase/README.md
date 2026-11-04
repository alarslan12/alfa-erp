# ALFA ERP / Firebase transition staging

**Status: PREPARATION ONLY. Do not switch production clients yet.**

The live system is currently on Supabase. This folder is a reversible,
data-preserving migration scaffold. Firebase project `alfa-erp-8700c` has been
created by the user; a Firestore database was also reported as created.
This tool session has not confirmed Firebase account-level access, published
Firestore rules or migrated live data.

## Architecture / free-tier safety

- Firestore Standard edition, Firebase Authentication, Windows PySide6 clients
  and the existing mobile catalog.
- Staff may open the app without a recurring login dialog, but each device
  must be authenticated and explicitly approved; no API secrets in an EXE.
- Browser customers must not be permitted to modify internal order statuses.
- Real-time listeners on narrowly scoped order changes, not 2-second full
  polling. Reconnect with exponential backoff. Count document reads.
- All writes must use validated atomic transactions, idempotent operation IDs,
  role-aware rules, and conflict handling before any production cutover.
- Keep the existing local order outbox and GUI unchanged.
- Firebase Cloud Functions are not a guaranteed no-billing/Spark-plan option.
  A fully free client-only implementation must be safe under Firestore Rules
  and Firebase Auth, or use an explicitly approved backend.

## Data layout (staging)

Original UUIDs are preserved as document IDs. Private SQL export from Supabase
is never committed to GitHub. Imports go to:
`migration_staging/{migration_id}/tables/{table}/rows/{source_id}`.

Production candidate after verification:
`workspaces/{workspace_uuid}/{table}/{source_id}`, with documents
`workspaces/{workspace_uuid}/members/{firebase_auth_uid}` for roles.
Nested subcollections must be designed and security rules verified before
migration promotion. No one has authorized production promotion yet.

Tables included: workspaces, books, orders, order_items, accounting_days,
erp_inventory_products, erp_inventory_sales, audit_events,
erp_device_activity, erp_progress_ops, erp_status_ops, erp_sync_state.
**NOT** exported: old DPAPI device tokens, pairing codes, Supabase members,
Supabase authentication sessions or analytics PIN hashes. The new identity
provider requires new device authorization and a new analytics PIN.

## Private staging steps (deployment machine, not staff PCs)

1. Export with a read-only Supabase database connection:
   `python tools/firebase_export_supabase.py --output firebase/migration_exports/snapshot_001`
   and a `SUPABASE_DATABASE_URL` environment variable. Use a read-only
   database user. Never share or commit the DSN or export.
2. Examine the JSON manifest, source counts and order totals. Preserve a
   separate encrypted backup.
3. Firebase project `alfa-erp-8700c` and Firestore are user-created.
   Review `AUTH_KURULUM.md` and enable providers for approved roles.
4. Configure short-lived Google Application Default Credentials or a secure
   local service account key (never commit it). Set project ID explicitly.
5. Dry-run the import:
   `python tools/firebase_stage_import.py --input firebase/migration_exports/snapshot_001 --project-id alfa-erp-8700c`
6. After reviewing preview, stage privately with `--apply`. This **does
   not** affect live collections or existing Supabase orders.
7. Reconcile counts and sample identities. Only then separately implement
   native Firestore clients, tested security rules, and a planned cutover.

## Before live go-live

- No legacy sessions, keys, or local outbox operations may be silently lost.
- Must pass mobile order create, concurrent counter update, prepared/boxed,
  status transitions, deletion, inventory, reconciliation, role and analytics
  PIN security checks.
- No switch while an old Supabase client still writes orders.
- Prepare rollback and prevent split-brain dual writes.
