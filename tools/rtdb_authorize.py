"""Approve a pending ALFA ERP Firebase UID with Google ADC (owner only).

This is a trusted one-time bootstrap: do not put IAM credentials in EXEs.
After owner activation, the Windows owner UI can approve staff devices.
"""
import argparse
import re
import sys
from rtdb_migrate import request, session

WORKSPACE_ID = "e2fc57b1-ef52-47b2-a6c9-ecd2e3832756"


def authorize(uid, role):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{8,128}", uid):
        raise ValueError("Invalid Firebase Auth UID")
    if role not in ("owner", "staff"):
        raise ValueError("Unsupported role")
    client = session()
    workspace, _, _ = request(client, "GET", "alfa/" + WORKSPACE_ID + "/meta")
    if not workspace or workspace.get("schema") != "rtdb-v1":
        raise RuntimeError("Verified RTDB workspace not promoted")
    pending, _, _ = request(client, "GET",
                            "alfa/" + WORKSPACE_ID + "/device_requests/" + uid)
    if not pending or not pending.get("name"):
        raise RuntimeError("UID has not registered an ALFA ERP device")
    member, _, _ = request(client, "GET",
                           "alfa/" + WORKSPACE_ID + "/members/" + uid)
    if member is not None:
        raise RuntimeError("Membership exists; refusing to overwrite")
    data = {"role": role, "active": True, "name": pending["name"]}
    _, _, status = request(client, "PUT", "alfa/" + WORKSPACE_ID +
                           "/members/" + uid, data, match="null_etag")
    if status != 200:
        raise RuntimeError("Membership changed concurrently; nothing overwritten")
    recorded, _, _ = request(client, "GET",
                             "alfa/" + WORKSPACE_ID + "/members/" + uid)
    if recorded != data:
        raise RuntimeError("Membership read-back mismatch")
    print("VERIFIED:", role, "device approved. UID:", uid)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--uid", required=True)
    parser.add_argument("--role", required=True, choices=("owner", "staff"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print("DRY RUN: project alfa-erp-8700c, role", args.role, "UID", args.uid)
        sys.exit(0)
    try:
        authorize(args.uid, args.role)
    except Exception as exc:
        sys.exit("Device authorization stopped: " + str(exc))
