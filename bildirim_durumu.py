"""Pure notification de-duplication, independent from Qt/Firebase.

Only monotonically increasing server order numbers in the same Firebase
workspace epoch count as a NEW order. The first baseline suppresses the
historical backlog, while the first ever new order (number 1) does alert.
"""


def classify_new_orders(previous,rows,epoch,legacy_seen=None):
    if not isinstance(rows,list):
        raise ValueError("Invalid order data")
    if not isinstance(previous,dict):
        previous={}
    last=max(0,int(previous.get("last_order_number") or 0))
    old_epoch=str(previous.get("epoch") or "")
    initialized=bool(previous.get("initialized",False))
    reset=bool(old_epoch and epoch and old_epoch!=epoch)
    if not epoch:
        raise ValueError("Missing workspace epoch")
    valid=[]
    for item in rows:
        if not isinstance(item,dict):
            continue
        try:
            number=int(item.get("order_number") or 0)
        except (ValueError,TypeError):
            continue
        if number>0:
            valid.append((number,item))
    if reset or not initialized and legacy_seen is None:
        fresh=[]
    elif legacy_seen is not None and not initialized:
        fresh=[item for _,item in valid if str(item.get("id")) not in legacy_seen]
    else:
        fresh=[item for number,item in valid if number>last]
    # Malformed duplicate rows must never produce duplicate notifications.
    unique={}
    for item in fresh:
        key=str(item.get("id") or item.get("order_number"))
        unique[key]=item
    return list(unique.values()),{
        "initialized":True,
        "last_order_number":max([0 if reset else last]+[n for n,_ in valid]),
        "epoch":epoch
    }
