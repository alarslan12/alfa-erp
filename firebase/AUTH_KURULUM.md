# ALFA ERP — Firebase Authentication (Spark-ready preparation)

**Project ID:** `alfa-erp-8700c`

The user reports that the Firestore database was created. The Firebase plugin
appears installed, but direct Firebase project management tools have not been
available in this chat. No change is claimed to have been applied to Console.

## Configure in Firebase Console

1. Open [Authentication](https://console.firebase.google.com/project/alfa-erp-8700c/authentication).
2. Choose **Get started** if shown, then **Sign-in method**.
3. Enable **Anonymous** to give staff devices and unregistered mobile shoppers
   session-scoped identities. Anonymous identity alone must never grant access
   to private orders or staff roles.
4. Enable **Google** for a single initial, explicit owner device activation.
   The owner session is to be persisted securely on that Windows user profile;
   the app should not ask for Google login on every launch.
5. Register **one Web app** under Project settings for the mobile catalog and
   REST client configuration. The public SDK configuration fields are not
   service credentials. Never share Admin SDK service account private keys.
6. **Do not enable test-mode Firestore rules** or rules allowing all signed-in
   users to write. Keep production deny-by-default rules until the Firebase
   rules and role membership flow have been verified.

## Secure device design (must implement before production cutover)

- Staff workstation signs in anonymously once; the refresh token is kept with
  Windows DPAPI (never plain text), and re-used across launches. The device
  receives no business access until an admin authorizes its Auth UID in the
  workspace member directory, using a trusted Admin SDK process.
- Owner device signs in once with Google and the Auth UID is separately
  approved as `admin` by a trusted bootstrap. The owner login does not
  automatically grant the role on Firestore. Do not expose a self-assign role
  rule in the app.
- Public mobile customer may read only active catalog books and create one
  strictly validated checkout request, never manipulate existing order status.
  Mobile checkout rules, anti-spam controls and idempotency are pending.
- Firestore realtime listeners must subscribe to changed order documents, not
  frequently reload the entire catalog. Concurrency updates must use atomic
  transactions and operation IDs.
- Legacy Supabase paired device keys and analytic PIN hashes are not migrated.
  Analitik requires a separately provisioned PIN and protected server-side
  verification logic; it must not be just a UI prompt.

## Local trusted bootstrap (future execution after Firebase access)

The `tools/firebase_bootstrap_owner.py` utility is intentionally dry-run by
 default. It requires a verified Firebase Google user UID, the read-only source
snapshot manifest for the source workspace UUID and Application Default
Credentials on a trusted administrator computer. It never asks the ChatGPT
user to paste a service account JSON into GitHub or chat.

Do not run live operation or disconnect Supabase until staging counts,
read-only tests, and a complete migration cutover have been verified.
