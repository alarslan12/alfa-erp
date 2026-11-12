"""Authorize a Firebase RTDB device from trusted Google Cloud Shell.

Uses Google Application Default Credentials, not any legacy transport.
Requires: python3 -m pip install firebase-admin
Run with --apply only after checking the UID and the Firebase project.
"""
import argparse, re, sys
from firebase_admin_access import PROJECT_ID, read, reference

def authorize(uid,role):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{8,128}",uid):
        raise ValueError("Invalid Firebase UID")
    if role not in ("owner","staff"):
        raise ValueError("Unsupported role")
    meta=read("meta")
    if not isinstance(meta,dict) or meta.get("schema")!="rtdb-v1":
        raise RuntimeError("Firebase RTDB workspace is not initialized")
    pending=read("device_requests/"+uid)
    if not isinstance(pending,dict) or not pending.get("name"):
        raise RuntimeError("Device has no registration request")
    member_ref=reference("members/"+uid)
    if member_ref.get() is not None:
        raise RuntimeError("Membership exists; refusing overwrite")
    data={"role":role,"active":True,"name":str(pending["name"])[:120]}
    def create_only(current):
        if current is not None:
            raise RuntimeError("Concurrent membership detected; no overwrite")
        return data
    member_ref.transaction(create_only)
    if member_ref.get()!=data:
        raise RuntimeError("Firebase readback did not match; inspect rules and state")
    print("Verified:",role,"device approval for UID",uid)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--uid",required=True)
    parser.add_argument("--role",required=True,choices=("owner","staff"))
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    if not args.apply:
        print("DRY RUN: Firebase project",PROJECT_ID,"role",args.role,"UID",args.uid)
        sys.exit(0)
    try:
        authorize(args.uid,args.role)
    except Exception as exc:
        sys.exit("Device authorization stopped: "+str(exc))
