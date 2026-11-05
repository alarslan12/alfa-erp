#!/usr/bin/env bash
# Resume only the private staging phase after rules compilation errors.
# No Supabase connection, no source mutation, no production promotion.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f ".firebase-migrate-venv/bin/activate" ]]; then
  echo "Önceki Cloud Shell Python ortamı bulunamadı. İşlem durduruldu."
  exit 2
fi
source .firebase-migrate-venv/bin/activate
SNAPSHOT="$(find firebase/migration_exports -maxdepth 1 -type d -name 'rtdb_*' -print | sort | tail -n 1)"
if [[ -z "$SNAPSHOT" || ! -f "$SNAPSHOT/manifest.json" ]]; then
  echo "Doğrulanabilir özel kaynak yedeği bulunamadı. İşlem durduruldu."
  exit 2
fi
echo "Kaynak yedeği bulundu: $SNAPSHOT"
python3 tools/rtdb_migrate.py --input "$SNAPSHOT"
echo
echo "Bu işlem mevcut RTDB kurallarının özel yedeğini alacak, ardından"
echo "güvenlik kurallarını yayımlayıp yalnızca migration_staging alanına yazacak."
echo "Canlı sipariş havuzuna yazma veya RTDB_PROMOTE işlemi YOK."
read -r -p "Onaylamak için RTDB_RULES yaz: " OK
if [[ "$OK" != "RTDB_RULES" ]]; then
  echo "İşlem güvenle iptal edildi."; exit 0
fi
python3 tools/rtdb_migrate.py --input "$SNAPSHOT" --deploy-rules --apply
echo "STAGING VERIFIED — Üretime geçiş yapılmadı."
