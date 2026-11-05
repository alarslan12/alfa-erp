#!/usr/bin/env bash
# Promote only the existing, verified private ALFA ERP snapshot.
# Does not connect to Supabase, rotate credentials, delete data or
# overwrite an existing Firebase workspace.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f .firebase-migrate-venv/bin/activate ]]; then
  echo "Önceki geçiş ortamı bulunamadı; işlem durduruldu."
  exit 2
fi
source .firebase-migrate-venv/bin/activate
SNAPSHOT="$(find firebase/migration_exports -mindepth 1 -maxdepth 1 -type d -name 'rtdb_*' -print | sort | tail -n 1)"
if [[ -z "$SNAPSHOT" || ! -f "$SNAPSHOT/manifest.json" ]]; then
  echo "Kaynak yedek bulunamadı; hiçbir işlem yapılmadı."
  exit 2
fi
echo "ALFA ERP / Firebase RTDB"
echo "Yedek: $SNAPSHOT"
echo "Önce Firebase hazırlık kopyası yeniden doğrulanacak..."
python3 tools/rtdb_migrate.py --input "$SNAPSHOT" --verify-only
echo
echo "UYARI: Kaynak Supabase'de bu yedekten sonra değişen siparişler bu"
echo "kopyada bulunmaz. Eski V6.2.2 kurulumlarını henüz kaldırmayın."
echo "Hedef RTDB alanı doluysa mevcut kayıtların üzerine YAZILMAYACAK."
echo "Bu adım Windows uygulamalarını Firebase'e otomatik geçirmez."
read -r -p "Doğrulanmış yedeği BOŞ canlı RTDB alanına kopyalamak için RTDB_PROMOTE yaz: " ACCEPT
if [[ "$ACCEPT" != "RTDB_PROMOTE" ]]; then
  echo "İşlem iptal edildi. Canlı veriler değiştirilmedi."
  exit 0
fi
python3 tools/rtdb_migrate.py --input "$SNAPSHOT" --promote
echo
echo "KOPYA TAMAMLANDI. Supabase yerinde duruyor."
echo "Bir sonraki adım: Yönetici cihazını yetkilendirme ve sipariş testi."
