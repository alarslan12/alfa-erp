"""FlexFlow: read-only, assumption-based ALFA production capacity estimates.

Never mutates orders, contacts printers or sends data to Firebase.
A hazir copy is assumed to have completed printing, punching and binding;
a koli copy has also been packed. No device telemetry is inferred from
manual checkboxes. Durations are estimates, not actual work logs.
"""
from __future__ import annotations
from datetime import datetime, time
from math import isfinite

SHIFT_START = time(7, 0)
SHIFT_END = time(17, 0)
SHIFT_MINUTES = 600.0
WORKERS = 2
BLACK_PRINTERS = 3
BLACK_PPM_EACH = 45.0
COLOR_PRINTERS = 2
COLOR_PPM_EACH = 15.0
SLOW_COLOR_PRINTERS = 1
SLOW_COLOR_PPM_EACH = 7.5
BLACK_PPM = BLACK_PRINTERS * BLACK_PPM_EACH
COLOR_PPM = COLOR_PRINTERS * COLOR_PPM_EACH + SLOW_COLOR_PRINTERS * SLOW_COLOR_PPM_EACH
PUNCH_PAGES_PER_BOOK = 300.0
PUNCH_MIN_PER_300 = (1.0, 2.0)
BIND_MIN_PER_COPY = (5.0 / 60.0, 45.0 / 60.0)
PACK_MIN_PER_ORDER = (1.0, 5.0)


def _number(value):
    try:
        n = float(value)
        return n if isfinite(n) and n > 0 else 0.0
    except (TypeError, ValueError, OverflowError):
        return 0.0


def _copies(value):
    return max(0, int(_number(value)))


def _minutes_left(now):
    """Remaining minutes of today's 07:00-17:00 shift."""
    start = now.replace(hour=7, minute=0, second=0, microsecond=0)
    end = now.replace(hour=17, minute=0, second=0, microsecond=0)
    return max(0.0, (end - max(now, start)).total_seconds() / 60.0)


def _phase_bounds(pages_sb, pages_color, copies_finishing, finishing_pages, orders_to_pack):
    print_sb = pages_sb / BLACK_PPM
    print_color = pages_color / COLOR_PPM
    printing = max(print_sb, print_color)
    punch_lo = finishing_pages / PUNCH_PAGES_PER_BOOK * PUNCH_MIN_PER_300[0]
    punch_hi = finishing_pages / PUNCH_PAGES_PER_BOOK * PUNCH_MIN_PER_300[1]
    bind_lo = copies_finishing * BIND_MIN_PER_COPY[0]
    bind_hi = copies_finishing * BIND_MIN_PER_COPY[1]
    pack_lo = orders_to_pack * PACK_MIN_PER_ORDER[0]
    pack_hi = orders_to_pack * PACK_MIN_PER_ORDER[1]
    labor_lo = punch_lo + bind_lo + pack_lo
    labor_hi = punch_hi + bind_hi + pack_hi

    # Hard lower bound with parallel printers, one puncher, two workers.
    optimistic = max(printing, punch_lo, labor_lo / WORKERS)
    # Sequential scenario with one worker and no pipeline overlap; NOT a SLA.
    sequential = printing + labor_hi
    components = {
        "print_sb_min": print_sb, "print_color_min": print_color,
        "print_min": printing, "punch_min": (punch_lo, punch_hi),
        "bind_min": (bind_lo, bind_hi), "pack_min": (pack_lo, pack_hi),
        "labor_min": (labor_lo, labor_hi),
        "optimistic_elapsed_min": optimistic,
        "sequential_elapsed_min": sequential,
    }
    if printing >= max(punch_lo, labor_lo / WORKERS):
        components["bottleneck"] = "Siyah-beyaz baskı" if print_sb >= print_color else "Renkli baskı"
    elif punch_lo >= labor_lo / WORKERS:
        components["bottleneck"] = "Tek delme makinesi"
    else:
        components["bottleneck"] = "İki kişilik manuel iş gücü"
    return components


def estimate(orders, page_count, *, completed=False, now=None):
    """Estimate work from selected ERP orders and canonical page lookup.

    With completed=False, quantity minus ready needs printing and finishing;
    every order with an unboxed copy needs packing. With completed=True,
    value entire completed orders as standard workload, including returns.
    Missing page counts remain visible: the forecast is then incomplete.
    """
    now = now or datetime.now().astimezone()
    result = {
        "orders": 0, "unfinished_orders": 0, "print_copies": 0,
        "copies_sb": 0, "copies_color": 0, "copies_finishing": 0,
        "pages_sb": 0, "pages_color": 0, "finishing_pages": 0,
        "missing_page_copies": 0, "missing_page_codes": set(),
        "pack_orders": 0, "workers": WORKERS, "shift_minutes": SHIFT_MINUTES,
        "shift_remaining_min": _minutes_left(now), "now": now,
    }
    for order in orders:
        result["orders"] += 1
        order_unboxed = False
        for item in order.get("kitaplar", []) or []:
            qty = _copies(item.get("adet"))
            ready = min(qty, _copies(item.get("hazir")))
            boxed = min(ready, _copies(item.get("koli")))
            print_qty = qty if completed else qty - ready
            if not completed and qty > boxed:
                order_unboxed = True
            kind = "color" if str(item.get("tur", "SB")).upper() in ("RNK", "RENK", "RENKLİ", "RENKLI") else "sb"
            result["copies_" + kind] += print_qty
            result["print_copies"] += print_qty
            result["copies_finishing"] += print_qty
            try:
                pages = _copies(page_count(item))
            except (TypeError, ValueError, KeyError):
                pages = 0
            if pages == 0 and print_qty:
                result["missing_page_copies"] += print_qty
                result["missing_page_codes"].add(str(item.get("kod") or "?"))
            result["pages_" + kind] += pages * print_qty
            result["finishing_pages"] += pages * print_qty
        if completed:
            result["pack_orders"] += 1
        elif order_unboxed:
            result["unfinished_orders"] += 1
            result["pack_orders"] += 1

    result.update(_phase_bounds(
        result["pages_sb"], result["pages_color"],
        result["copies_finishing"], result["finishing_pages"],
        result["pack_orders"],
    ))
    result["print_pages"] = result["pages_sb"] + result["pages_color"]
    result["missing_page_codes"] = sorted(result["missing_page_codes"])
    result["fully_known"] = result["missing_page_copies"] == 0
    remaining = result["shift_remaining_min"]
    lo = result["optimistic_elapsed_min"]
    hi = result["sequential_elapsed_min"]
    if not result["fully_known"]:
        result["shift_status"] = "Belirsiz (sayfa bilgisi eksik)"
    elif lo > remaining:
        result["shift_status"] = "İdeal koşulda bile mesaiye sığmıyor"
    elif hi <= remaining:
        result["shift_status"] = "İki senaryoda da mesaiye sığıyor"
    else:
        result["shift_status"] = "Mesaiye yetişme riski var"
    result["minimum_overtime_min"] = max(0.0, lo - remaining) if result["fully_known"] else None
    result["scenario_overtime_min"] = max(0.0, hi - remaining) if result["fully_known"] else None
    result["black_shift_page_capacity"] = BLACK_PPM * SHIFT_MINUTES
    result["color_shift_page_capacity"] = COLOR_PPM * SHIFT_MINUTES
    return result
