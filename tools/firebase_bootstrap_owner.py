"""ALFA ERP: trusted Firebase owner membership bootstrap.

Does nothing by default. Only use on a trusted admin machine after verifying
the Google sign-in user, Firestore project and private source snapshot.
Never put Firebase Admin SDK keys or refresh tokens in this repository.
"""
import argparse
import json
from pathlib import Path
import re
import sys

PROJECT_ID = "alfa-erp-8700c"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="Private snapshot manifest.json")
    parser.add_argument("--uid", required=True, help="Existing Google-authenticated Firebase user UID")
    parser.add_argument("--project-id", default=PROJECT_ID)
    parser.add_argument("--apply", action="store_true", help="Write owner membership to Firestore")
    args = parser.parse_args()

    if args.project_id != PROJECT_ID:
        raise SystemExit("Refusing unexpected Firebase project ID.")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{8,128}", args.uid):
        raise SystemExit("Invalid Firebase Auth UID.")
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if manifest.get("workspace_slug") != "alfa-erp" or manifest.get("format") != 1:
        raise SystemExit("Unrecognized ALFA ERP snapshot manifest.")
    wsid = str(manifest.get("workspace_id") or "")
    if not re.fullmatch(r"[0-9a-f-]{36}", wsid):
        raise SystemExit("Invalid source workspace UUID.")
    print("Project:", args.project_id, "workspace:", wsid, "owner UID:", args.uid)
    if not args.apply:
        print("DRY RUN. No Firebase or database requests.")
        return

    try:
        import firebase_admin
        from firebase_admin import auth, credentials, firestore
    except ImportError:
        raise SystemExit("Install firebase-admin on a trusted admin computer.")

    app = firebase_admin.initialize_app(credentials.ApplicationDefault(),
                                        {"projectId": PROJECT_ID})
    user = auth.get_user(args.uid, app=app)
    providers = {p.provider_id for p in user.provider_data}
    if "google.com" not in providers:
        raise SystemExit("Owner UID must belong to a Google-authenticated Firebase user.")
    db = firestore.client(app=app)
    ref = db.collection("workspaces").document(wsid)
    if not ref.get().exists:
        raise SystemExit("Source workspace must be staged/promoted before owner bootstrap.")
    member = ref.collection("members").document(args.uid)
    if member.get().exists:
        raise SystemExit("Membership exists already; review roles manually.")
    member.create({"role": "admin", "active": True, "source": "trusted_owner_bootstrap"})
    print("Owner access created for this verified Google Firebase user.")


if __name__ == "__main__":
    main()
