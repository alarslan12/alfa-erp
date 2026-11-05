# ALFA ERP / Firebase Realtime Database final migration runbook

- Google project: **alfa-erp-8700c**
- RTDB: **alfa-erp-8700c-default-rtdb.europe-west1.firebasedatabase.app**
- Source Supabase project: **gdfuljiyfvpjvokiarnx**
- Source workspace UUID: **e2fc57b1-ef52-47b2-a6c9-ecd2e3832756**
- Branch: **firebase-rtdb-final**. Keep the main branch and V6.2.2 installations unchanged until confirmed.

## Preparation

1. Open [Google Cloud Shell](https://shell.cloud.google.com/?project=alfa-erp-8700c).
2. Run:

   git clone --depth 1 --branch firebase-rtdb-final https://github.com/alarslan12/alfa-erp.git
   cd alfa-erp && bash tools/rtdb_cloudshell_full.sh

3. At the hidden prompt supply the **Session Pooler URI** from Supabase → Connect.
   **Never provide passwords, the URI, service accounts or tokens to ChatGPT, GitHub or the mobile catalog.**
4. The script imports a READ ONLY snapshot (one repeatable-read transaction), installs restrictive RTDB rules, writes private staging, reads it back, and, only after your second confirmation, promotes it if the live workspace is empty.
5. Check the final **FIREBASE COPY VERIFIED** output. This does **NOT** switch old Windows applications.

## Device activation (only after import)

Install the *new* Firebase-enabled version of the owner app (not V6.2.2).

1. Open the owner app → **Cihaz yetkisi** → **Cihazı kaydet**.
2. Copy the displayed anonymous Firebase UID. It is not a password.
3. In the **same authorized Cloud Shell** (with the repo and venv already active) run:

   python3 tools/rtdb_authorize.py --uid YOUR_UID --role owner --apply

4. In the owner app click **Yönetici onayını kontrol et**.
5. Staff installs the *new* staff app, presses **Cihaz yetkisi** to register,
   and then owner uses **Ayarlar → Bilgisayarlar → Personel cihazını onayla**.
6. After migration confirmation, point the mobile website at the new
   firebase-rtdb-final/mobil_panel/index.html and verify a real test order
   reaches the shared pool exactly once.

## Security and operating constraints

- The Firebase API key is public client configuration, not an Admin SDK key.
- Staff permissions are determined **only by RTDB Rules** and a trusted admin-approved UID.
- Public checkout can only *create* an immutable request under its own UID.
  A trusted staff/owner workstation converts valid requests to shared orders
  with deterministic IDs; it must be online for that conversion.
- Spark free tier: 100 simultaneous connections, 1 GB storage, roughly
  10 GB/month downloads; no promise of truly unlimited free use.
- Realtime SSE does not guarantee a fixed delivery latency. 30-second fallback
  polling and local outbox are retained.
- The analytics PIN in this fully free client-only architecture is a **UI gate**
  (scrypt verifier readable to approved devices), **not server-enforced**.
- Changes made on Supabase after the snapshot will not magically appear in
  Firebase. Coordinate the final cutover: stop old writers, create a fresh
  snapshot, verify pending outbox queues and prevent split-brain writes.
- Never destroy or overwrite the source Supabase database. Keep an encrypted
  backup before final cutover.
- The migration script does not run itself from GitHub; a project-owner Google
  authorization is required to deploy rules and perform privileged imports.
- The source and scripts in this branch have not undergone Windows or live
  Firebase integration tests yet. No Windows EXE should be advertised as ready.
