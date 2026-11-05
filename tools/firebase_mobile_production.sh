#!/usr/bin/env bash
# ALFA ERP production mobile Hosting deployment.
# EXPLICIT two-file allowlist for the Spark plan. Database and auth are untouched.
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT="alfa-erp-8700c"
if command -v gcloud >/dev/null 2>&1; then
  ACTIVE="$(gcloud config get-value project 2>/dev/null || true)"
  [[ "$ACTIVE" == "$PROJECT" ]] || {
    echo "Wrong Google Cloud project: $ACTIVE (expected $PROJECT)"; exit 2;
  }
fi
command -v firebase >/dev/null || { echo "Firebase CLI is required"; exit 2; }
[[ -s mobil_panel/index.html && -s mobil_panel/manifest.webmanifest ]] || {
  echo "Mobile catalog files missing"; exit 2;
}
TEMP="$(mktemp -d "$PWD/.alfa-live-hosting-XXXXXXXX")"
trap 'rm -rf -- "$TEMP"' EXIT
mkdir -p "$TEMP/public"
cp -- mobil_panel/index.html "$TEMP/public/index.html"
cp -- mobil_panel/manifest.webmanifest "$TEMP/public/manifest.webmanifest"
cat > "$TEMP/firebase.json" <<'JSON'
{
  "hosting": {
    "public": "public",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "headers": [
      {"source":"**", "headers":[
        {"key":"Cache-Control","value":"no-cache"},
        {"key":"Referrer-Policy","value":"no-referrer"},
        {"key":"X-Content-Type-Options","value":"nosniff"}
      ]}
    ]
  }
}
JSON
echo "PRODUCTION Hosting deploy: replaces current LIVE website of $PROJECT."
echo "Only index.html and manifest.webmanifest will be published."
echo "Do this ONLY after desktop verification, private backup and clean cutover."
echo "Does NOT touch Firebase Realtime Database or Security Rules."
read -r -p "Type ALFA-MOBIL-YAYINLA to deploy LIVE: " APPROVAL
[[ "$APPROVAL" == "ALFA-MOBIL-YAYINLA" ]] || { echo "Cancelled."; exit 0; }
firebase deploy --only hosting --project "$PROJECT" \
  --config "$TEMP/firebase.json" --non-interactive
echo "Production Hosting deployment completed. Check the printed Hosting URL."
