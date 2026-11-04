# Firebase migration: Cloud Shell procedure

Target Firebase project: `alfa-erp-8700c`. The Supabase project
`gdfuljiyfvpjvokiarnx` remains live and is not deleted by these scripts.

**Current stage:** exported data can be copied to a *private Firestore staging*
namespace and compared record-by-record. This is not the app's production
migration. Client rollout requires secured role rules, authenticated desktop
clients and mobile checkout.

## Single-command setup in Cloud Shell

1. Open [Google Cloud Shell](https://shell.cloud.google.com/?project=alfa-erp-8700c).
2. Copy the two commands below:

```bash
git clone --depth 1 --branch firebase-migration https://github.com/alarslan12/alfa-erp.git
cd alfa-erp && bash tools/firebase_cloudshell_stage.sh
```

3. If requested, approve Google Cloud application-default authentication.
   Enter the Supabase Postgres connection URL (e.g. **Session Pooler** from
   Supabase → Connect) at the hidden prompt. **Do not paste the password or
   connection URI into ChatGPT or GitHub.** The script sets a read-only
   transaction for exporting.
4. Before uploading private orders, confirm **Firestore Database → Rules** do NOT
   permit public reads/writes to `migration_staging` or private orders. If
   Firestore was created in Test mode, stop and deploy restrictive rules first.
   Type `PRIVATE_RULES_CHECKED` only after actually reviewing the rules.
5. Verify table counts. Type `FIREBASE_STAGING` only if you want to stage the
   private copy. The importer verifies checksums and duplicate keys before
   writing and never updates production collections.
6. Every row is compared back against the original private snapshot.
   "VERIFIED" means staging succeeded, **not** live cutover.

## Security / limitations

- Customer shipping references and other business data belong in private
  Cloud Shell files, **not the public GitHub repository**.
- An offline/source snapshot should be protected. Cloud Shell storage can
  expire; export an encrypted backup before relying on it for recovery.
- No private Firebase Admin SDK key has to be pasted into this chat. Cloud
  Shell uses your authenticated Google Cloud identity and IAM permissions.
- Some Supabase Postgres direct URLs require IPv6. Use a supplied **Session
  Pooler** URI if the direct URL times out. The correct source database
  credentials are required; the Firebase API key cannot replace them.
- Spark/Firestore quotas count staging writes and verification reads.
- Take a fresh snapshot at cutover after pausing legacy writers, because
  operational data may change while staging is being verified.
- Never permit staff anonymous identities to self-approve or grant themselves
  roles. Firebase Rules currently contain a read-only baseline and have
  **not been deployed by these scripts**.
