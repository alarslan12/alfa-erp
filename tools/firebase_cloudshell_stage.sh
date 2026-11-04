#!/usr/bin/env bash
# Run from a trusted Google Cloud Shell in the checked-out firebase-migration branch.
# No private data or credentials are ever committed to GitHub by this script.
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT_ID="alfa-erp-8700c"
command -v gcloud >/dev/null || { echo "This script requires Google Cloud Shell / gcloud."; exit 2; }
command -v python3 >/dev/null || { echo "Python 3 is required in Cloud Shell."; exit 2; }
echo "Firebase target: ${PROJECT_ID}"
echo "Only migration_staging will be written. Live Supabase and Firestore collections remain unchanged."
gcloud config set project "$PROJECT_ID"
if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
  gcloud auth application-default login
fi
python3 -m venv .firebase-migrate-venv
source .firebase-migrate-venv/bin/activate
python3 -m pip install --disable-pip-version-check -r firebase/requirements-migration.txt
printf '\nSupabase Connect panelinden Session Pooler / PostgreSQL URI bilgisini al.\n'
printf 'Bu adresi sohbete veya GitHub\x27a gönderme. Girerken ekranda görünmeyecek.\n'
read -r -s -p 'Supabase database URI: ' SUPABASE_DATABASE_URL
echo
if [[ -z "$SUPABASE_DATABASE_URL" ]]; then echo "DB URI missing."; exit 2; fi
export SUPABASE_DATABASE_URL
trap 'unset SUPABASE_DATABASE_URL' EXIT
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
EXPORT_DIR="firebase/migration_exports/alfa_erp_${STAMP}"
python3 tools/firebase_export_supabase.py --output "$EXPORT_DIR"
unset SUPABASE_DATABASE_URL
printf '\nSnapshot export finished. Source files are private and stay in this Cloud Shell account.\n'
python3 tools/firebase_stage_import.py --input "$EXPORT_DIR" --project-id "$PROJECT_ID"
echo
echo "Before continuing, check Firebase Console > Firestore Database > Rules."
echo "Clients MUST be denied access to migration_staging and private ERP data."
echo "Do NOT proceed with Firebase test-mode or allow read, write: if true."
read -r -p "Type PRIVATE_RULES_CHECKED after confirming restrictive rules: " RULES_CONFIRMED
if [[ "$RULES_CONFIRMED" != "PRIVATE_RULES_CHECKED" ]]; then
  echo "STOPPED safely. No Firebase writes. Source snapshot: $EXPORT_DIR"
  exit 0
fi
echo "Do you want to WRITE a private staging copy to Firestore?"
echo "This does not change the existing production collections."
read -r -p "Type FIREBASE_STAGING to proceed: " CONFIRM
if [[ "$CONFIRM" != "FIREBASE_STAGING" ]]; then
  echo "No Firebase writes were made. Snapshot path: $EXPORT_DIR"
  exit 0
fi
python3 tools/firebase_stage_import.py --input "$EXPORT_DIR" --project-id "$PROJECT_ID" --apply
python3 tools/firebase_verify_staging.py --input "$EXPORT_DIR" --project-id "$PROJECT_ID"
echo
echo "STAGING VERIFIED. Production cutover was NOT performed."
echo "Keep the private export safely backed up and do not publish it."
