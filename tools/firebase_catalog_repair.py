"""Inspect and repair Firebase books using the CURRENT Excel, via Cloud Shell.

Dry-run by default. Firebase Admin Application Default Credentials required.
This never deletes orders, device identities, history or stored print files.

Usage:
  python tools/firebase_catalog_repair.py --excel "kitaplar_sablonu.xlsx"
  python tools/firebase_catalog_repair.py --excel "kitaplar_sablonu.xlsx" \
    --apply --confirm-project alfa-erp-8700c
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from firebase_admin_access import PROJECT_ID, reference


def remote_code_map():
    raw=reference("books").get() or {}
    if not isinstance(raw,dict):
        raise RuntimeError("Unexpected Firebase books type; no writes performed.")
    active={}
    for key,row in raw.items():
        if not isinstance(row,dict) or row.get("is_active") is not True:
            continue
        code=str(row.get("code") or "").strip()
        if code:
            active.setdefault(code,[]).append((key,row))
    return active


class AdminAdapter:
    """Use Firebase Admin ADC, not the Windows anonymous-device identity."""
    def _get(self,path):
        return reference(path).get()

    def _request(self,method,path,body=None,timeout=20,**_kwargs):
        ref=reference(path)
        if method=="PUT":ref.set(body)
        elif method=="PATCH":ref.update(body)
        else:raise ValueError("Unsupported Cloud Shell update method")
        return None,None,200

    def _bump(self,kind):
        if kind!="catalog":raise ValueError("Unsafe revision kind")
        return reference("meta/revisions/catalog").transaction(
            lambda prev:int(prev or 0)+1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--excel",required=True,help="Uploaded .xlsx workbook in Cloud Shell")
    parser.add_argument("--apply",action="store_true",help="Write after dry-run verification")
    parser.add_argument("--confirm-project",default="",help="Must exactly match Firebase project ID")
    args=parser.parse_args()

    source=Path(args.excel).expanduser().resolve()
    if not source.is_file():parser.error("Excel file not found: "+str(source))
    from katalog_excel_aktar import preview_excel_catalog
    from rtdb_owner_admin import _catalog
    books=preview_excel_catalog(source)
    if not books:raise RuntimeError("No named Excel rows; refusing update")
    before=remote_code_map()
    differing=[]
    for row in books:
        code=row["code"]
        previous=before.get(code,[])
        old=previous[0][1] if previous else {}
        if (not previous or len(previous)!=1 or
            str(old.get("name") or "")!=row["name"] or
            (row["page_count"]>0 and int(old.get("page_count") or 0)!=row["page_count"])):
            differing.append((code,str(old.get("name") or "—"),
                              row["name"],str(old.get("page_count") or 0),
                              str(row["page_count"])))
    print("Firebase project:",PROJECT_ID)
    print("Excel:",source.name,"rows:",len(books),"active cloud codes:",len(before))
    print("Different/new codes:",len(differing))
    for code,old,new,old_pages,new_pages in differing[:25]:
        print(f"  #{code}: {old} [{old_pages}] -> {new} [{new_pages}]")
    if len(differing)>25:print("  ...",len(differing)-25,"more")
    if not args.apply:
        print("DRY RUN ONLY; no Firebase changes. To apply add "+
              "--apply --confirm-project "+PROJECT_ID)
        return
    if args.confirm_project!=PROJECT_ID:
        parser.error("Wrong project confirmation; nothing written")
    answer=_catalog(AdminAdapter(),books)
    after=remote_code_map()
    for row in books:
        matches=after.get(row["code"],[])
        if len(matches)!=1 or str(matches[0][1].get("name"))!=row["name"]:
            raise RuntimeError("Cloud readback differs after apply: "+row["code"])
    print("Verified Firebase catalog:",answer["count"],
          "books, updated records:",answer["updated"])
    print("Recoverable PRE-IMPORT catalog backup:",answer["backup"])
    print("No order, employee or device records were deleted.")


if __name__=="__main__":
    main()
