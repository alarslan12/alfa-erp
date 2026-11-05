#!/usr/bin/env bash
# Verify the existing private copy. No deployment, no Supabase access,
# no Firebase writes, no production promotion.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f ".firebase-migrate-venv/bin/activate" ]]; then
  echo "Önceki Cloud Shell Python ortamı bulunamadı. İşlem durduruldu."
  exit 2
fi
source .firebase-migrate-venv/bin/activate
SNAPSHOT="$(find firebase/migration_exports -maxdepth 1 -type d -name 'rtdb_*' -print | sort | tail -n 1)"
if [[ -z "$SNAPSHOT" || ! -f "$SNAPSHOT/manifest.json" ]]; then
  echo "Mevcut özel kaynak yedeği bulunamadı. İşlem durduruldu."
  exit 2
fi
echo "837 kayıtlık mevcut yedeğin doğrulanması (yalnızca okuma): $SNAPSHOT"
python3 tools/rtdb_migrate.py --input "$SNAPSHOT" --verify-only
echo "Bu yalnızca hazırlık kopyasıdır. Canlıya geçiş YAPILMADI."
