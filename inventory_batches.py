"""Shared read-only inventory lot projections (no database access).

Each acquisition batch keeps its own purchase timestamp, cost, initial quantity
and remaining quantity. Legacy one-price stock remains visible as a virtual
batch, and is migrated into the product on its first atomic inventory write.
"""


def stock_batches(product):
    raw=product.get("stock_batches")
    if isinstance(raw,dict) and raw:
        return {str(key):dict(row) for key,row in raw.items()
                if isinstance(row,dict)}
    quantity=max(0,int(product.get("quantity") or 0))
    if not quantity:
        return {}
    batch_id="legacy-"+str(product.get("id") or "unknown")
    return {batch_id:{
        "id":batch_id,"quantity":quantity,"remaining":quantity,
        "unit_cost":round(float(product.get("cost_price") or 0),2),
        "received_at":"",  # Old master creation time is NOT the acquisition date.
        "legacy":True}}


def sorted_batches(product,include_empty=False,newest_first=True):
    result=[dict(row) for row in stock_batches(product).values()]
    if not include_empty:
        result=[row for row in result if int(row.get("remaining") or 0)>0]
    result.sort(key=lambda row:(str(row.get("received_at") or ""),
                                str(row.get("id") or "")),reverse=newest_first)
    return result


def batch_stock_quantity(product):
    return sum(int(row.get("remaining") or 0)
               for row in stock_batches(product).values())


def batch_stock_value(product):
    return round(sum(int(row.get("remaining") or 0)*
                     float(row.get("unit_cost") or 0)
                     for row in stock_batches(product).values()),2)
