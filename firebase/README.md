# ALFA ERP — Firebase Realtime Database

Active application branch: \`firebase-rtdb-final\`
Firebase project: \`alfa-erp-8700c\`
RTDB region: \`europe-west1\`

The Windows desktop app uses **Firebase Authentication + Realtime Database**.
There is no server API key, admin key, or login password embedded in the EXE.

## Access model

- First launch creates a per-device Firebase anonymous Auth identity.
- Only a Firebase owner-authorized UID may manage devices, books, analytics PIN,
  and administrative settings.
- Staff UIDs require explicit owner approval. Unauthorized clients cannot read
  order records.
- Auth refresh tokens are stored in Windows DPAPI-encrypted, edition-separated
  local files. The updated encryption helper preserves existing sessions.
- The analytics PIN is a user-interface gate, not the database authorization
  boundary. Firebase Rules enforce actual permissions.

## Realtime and offline

Firebase SSE listeners notify running workstations of updates. A bounded
periodic revision poll recovers missed events and network interruptions.
The local JSON outbox survives restarts. Before replaying queued changes the
app validates the current workspace generation to avoid cross-project writes.

## Deploying reviewed rules

The source-controlled RTDB rules are in \`database.rules.json\`.
They are NOT automatically published by a GitHub source edit.

With the proper Firebase project account connected in a trusted terminal:

\`\`\`bash
cd firebase
firebase use alfa-erp-8700c
firebase deploy --only database --project alfa-erp-8700c
\`\`\`

Review Rules against a test workspace before deploying to live production.
Never paste service-account keys, password secrets or private exports into GitHub.
No migration or data-reset command is required for this code update.

## Windows deployment

Build the unified V1.1.2 setup from the Firebase branch. Do not overwrite
\`%LOCALAPPDATA%\AlfaERP\`; that folder holds encrypted device identities, cached
orders and queued actions. For two-device operations, validate real disconnect,
reconnection, concurrent updates and owner/staff roles before declaring production
acceptance.
