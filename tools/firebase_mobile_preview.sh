#!/usr/bin/env bash
# Deploy mobile catalog to an expiring Firebase Hosting PREVIEW channel.
# Never publishes to the live channel and never deploys database rules.
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT="alfa-erp-8700c"
CHANNEL="alfa-mobile-test"
test -s firebase.json && test -s mobil_panel/index.html || {
  echo "Mobil katalog veya Firebase Hosting ayarlari bulunamadi."; exit 2;
}
if ! command -v firebase >/dev/null 2>&1; then
  echo "Firebase CLI bulunamadi. Firebase Console uzerinden Cloud Shell'i acin."
  exit 2
fi
if command -v gcloud >/dev/null 2>&1; then
  ACTIVE="$(gcloud config get-value project 2>/dev/null || true)"
  if [[ "$ACTIVE" != "$PROJECT" ]]; then
    echo "Yanlis Cloud Shell projesi: $ACTIVE (beklenen: $PROJECT)"
    exit 2
  fi
fi
printf '\nALFA ERP mobil katalog ONIZLEME dagitimi\n'
printf 'Proje: %s | Kanal: %s | SURE: 1 gun\n' "$PROJECT" "$CHANNEL"
printf 'Bu islem canli web sitesini, veri tabani kurallarini ve siparisleri DEGISTIRMEZ.\n'
read -r -p "Test linki olusturmak icin MOBILE_TEST yaz: " APPROVE
if [[ "$APPROVE" != "MOBILE_TEST" ]]; then echo "Iptal edildi."; exit 0; fi
firebase hosting:channel:deploy "$CHANNEL" --project "$PROJECT" --expires 1d --non-interactive
printf '\nOlusan Firebase Hosting onizleme URL adresini acin.\n'
printf 'Yonetici Windows uygulamasi acik ve Bulut bagli durumunda olmali.\n'
printf 'Tek bir deneme siparisi olusturun, kargo/adres alanina TEST-MOBIL yazin.\n'
printf 'Veriler dogrulanana kadar TEST siparisini silmeyin.\n'
