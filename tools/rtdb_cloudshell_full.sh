#!/usr/bin/env bash
# ALFA ERP: one guided, data-preserving setup from Supabase to Firebase RTDB.
# Run only in YOUR Google Cloud Shell after reading the security notice.
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT="alfa-erp-8700c"
echo "=================================="
echo " ALFA ERP / Firebase Realtime DB  "
echo "=================================="
echo "Target: $PROJECT"
echo "Only encrypted/trusted Google Cloud Shell session; DO NOT paste DB passwords into ChatGPT."
echo "Supabase will NOT be deleted, altered or paused."
command -v gcloud >/dev/null
command -v python3 >/dev/null
gcloud config set project "$PROJECT"
echo "Authorize your project-owner Google account for Realtime Database IAM."
if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
  gcloud auth application-default login \
   --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/firebase.database,https://www.googleapis.com/auth/userinfo.email
fi
python3 -m venv .firebase-migrate-venv
source .firebase-migrate-venv/bin/activate
python3 -m pip install --disable-pip-version-check \
  -r firebase/requirements-migration.txt google-auth requests
printf '\nPaste Supabase Connect > Session Pooler PostgreSQL URL at the hidden prompt.\n'
printf 'Only put it in YOUR Cloud Shell; never into ChatGPT or GitHub.\n'
read -r -s -p 'PostgreSQL URI: ' SUPABASE_DATABASE_URL
echo
if [[ -z "$SUPABASE_DATABASE_URL" ]]; then
 echo "No database URI entered. No data moved."; exit 2
fi
export SUPABASE_DATABASE_URL
trap 'unset SUPABASE_DATABASE_URL' EXIT
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EXPORT_DIR="firebase/migration_exports/rtdb_$STAMP"
# Keep TLS enabled. On newer OpenSSL builds, hybrid post-quantum
# ClientHello can exceed the Supavisor pooler's 1024-byte startup guard.
# Limit only the PostgreSQL import connection to classical, still secure
# X25519/P-256 ECDHE groups (do not disable encryption).
PGGSSENCMODE=disable PGSSLMODE=require OPENSSL_CONF="$PWD/firebase/openssl-pooler.cnf" \
  python3 tools/firebase_export_supabase.py --output "$EXPORT_DIR"
unset SUPABASE_DATABASE_URL
python3 tools/rtdb_migrate.py --input "$EXPORT_DIR"
echo
echo "PRIVATE DATA WARNING: The snapshot contains orders and customer addresses."
echo "Do not upload the snapshot to GitHub or share it in chat."
echo "Rules will deny all access by default, except public catalogue and"
echo "strict one-time customer checkout writes. Device access uses approved UIDs."
read -r -p "Type RTDB_RULES to deploy reviewed rules and stage a private copy: " ACCEPT
if [[ "$ACCEPT" != "RTDB_RULES" ]]; then
 echo "Stopped after offline snapshot; no Firebase writes."; exit 0
fi
python3 tools/rtdb_migrate.py --input "$EXPORT_DIR" --deploy-rules --apply
echo
echo "Your private staging copy was read back and verified."
echo "Promotion copies it to a LIVE Firebase RTDB namespace, but Windows apps"
echo "must NOT switch until you have approved their device identities."
echo "Supabase remains unchanged."
read -r -p "Type RTDB_PROMOTE to copy verified data to empty live Firebase workspace: " GO
if [[ "$GO" == "RTDB_PROMOTE" ]]; then
 python3 tools/rtdb_migrate.py --input "$EXPORT_DIR" --promote
 echo "FIREBASE COPY VERIFIED. Existing Supabase remains intact."
else
 echo "Staging complete; no production Firebase namespace created."
fi
echo "Snapshot path: $EXPORT_DIR"
echo "Keep a private backup. Do not close your original Supabase project."
