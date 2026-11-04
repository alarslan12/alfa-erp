# ALFA ERP / Firebase read-only web pilot

Project: `alfa-erp-8700c`  
Source workspace: `e2fc57b1-ef52-47b2-a6c9-ecd2e3832756`

The user-supplied public Firebase Web configuration is in `config.js`.
Its `databaseURL` is for **Realtime Database**; this pilot deliberately
uses **Cloud Firestore** with `getFirestore()`.

Files:
- `config.js`: client-side Firebase identifiers, NO service-account secrets.
- `catalog_pilot.html`: lightweight, isolated preview (NOT live mobile site).
- `catalog_pilot.js`: one `onSnapshot` listener with `is_active == true`;
  pagehide unsubscribes. No polling and no database writes.

## Before using it

1. Confirm Firestore is configured, `(default)` database, intended region.
2. Deploy carefully reviewed `../firestore.rules` from a trusted admin
   environment. The current rules are read-only for business collections.
3. The preview reads only
   `workspaces/{source_workspace_uuid}/books`, and that collection is
   empty until data is **explicitly promoted** from verified staging.
4. Serve this folder using any HTTP(S) static server. Do not launch via
   `file://` because browsers restrict ES modules on local file URLs.
5. Do not put the private SQL export, Admin SDK JSON, owner tokens, or
   customer addresses in a public web folder or GitHub repository.

The pilot is expected to show 0 records until verified source migration.
A non-zero book count proves only Firestore read access, **not** completed
migration, secure order writes, or Windows realtime integration.

**No checkout in the pilot.** Public checkout must be implemented with
idempotent request IDs, immutable/validated fields, transaction-safe
number allocation, authorization and abuse controls before cutover.
Never allow Anonymous Auth accounts to write internal `orders` documents
or staff `members` documents.
