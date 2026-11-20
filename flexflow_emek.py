"""Read-only two-shift allocation of completed-order production workload.

'Orders completed' remains the authoritative event-date count. This module
builds a SECOND, assumption-based standard workload index with transparent
provenance. It never changes order timestamps, progress events or Firebase.

A standard workload minute is a conservative modeled effort proxy:
  prepared = max(SB printer minutes, color printer minutes, punching minutes,
                 punching+minimum binding labor / 2 staff)
  packed   = minimum packing minutes / 2 staff
Per-order prepared and packed stages can overlap in real production; summing
their proxy minutes is an index, NOT measured employee hours or machine uptime.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from math import isfinite
from statistics import median

from flexflow import (
    BLACK_PPM, COLOR_PPM, PUNCH_PAGES_PER_BOOK, PUNCH_MIN_PER_300,
    BIND_MIN_PER_COPY, PACK_MIN_PER_ORDER, WORKERS, SHIFT_START,
    SHIFT_END, SHIFT_MINUTES, estimate,
)


def _dt(value):
    if isinstance(value, datetime):
        return value.astimezone() if value.tzinfo else value
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone() if result.tzinfo else result
    except (ValueError, TypeError, OverflowError):
        return None


def _num(value):
    try:
        number = int(value)
        return max(0, number)
    except (ValueError, TypeError, OverflowError):
        return 0


def _work(order, page_count):
    """Full-order minimum modeled preparation and packing effort (minutes)."""
    sb = color = pages = punch = binding = copies = 0.0
    unknown = 0
    for item in order.get("kitaplar", []) or []:
        qty = _num(item.get("adet"))
        if not qty:
            continue
        copies += qty
        try:
            per_copy = _num(page_count(item))
        except (TypeError, ValueError, KeyError):
            per_copy = 0
        if not per_copy:
            unknown += qty
            continue
        total_pages = per_copy * qty
        pages += total_pages
        kind = str(item.get("tur") or "SB").upper()
        if kind in ("RNK", "RENK", "RENKLİ", "RENKLI"):
            color += total_pages
        else:
            sb += total_pages
        punch += total_pages / PUNCH_PAGES_PER_BOOK * PUNCH_MIN_PER_300[0]
        binding += qty * BIND_MIN_PER_COPY[0]
    if unknown or not copies:
        return None
    prepared = max(sb / BLACK_PPM, color / COLOR_PPM, punch,
                   (punch + binding) / WORKERS)
    packed = PACK_MIN_PER_ORDER[0] / WORKERS
    return {"prep": prepared, "pack": packed, "copies": copies,
            "total": prepared + packed}


def _shift_minutes(day, begin, end):
    """Overlap of a time interval with the date's scheduled 07–17 shift."""
    low = datetime.combine(day, SHIFT_START, tzinfo=begin.tzinfo)
    high = datetime.combine(day, SHIFT_END, tzinfo=begin.tzinfo)
    a, b = max(begin, low), min(end, high)
    return max(0.0, (b-a).total_seconds() / 60.0)


def build_workload(db, events, start, end, now=None):
    """Return day-indexed modeled work plus confidence/feasibility metadata.

    Known events get their recorded date. Unlogged preparation is split only
    if a persisted activation timestamp places the order on the immediately
    preceding shift; otherwise unknown work remains on completion day.

    Exact-day filters include next-day completed orders so yesterday's work is
    not hidden merely because the order was boxed tomorrow. No future or
    ongoing order is counted as completed production.
    """
    now = now or datetime.now().astimezone()
    first = date.fromisoformat(str(start)[:10])
    last = date.fromisoformat(str(end)[:10])
    entries = defaultdict(lambda: {
        "minutes": 0.0, "logged_minutes": 0.0, "inferred_minutes": 0.0,
        "incomplete_orders": 0, "modeled_orders": 0,
        "carry_in_min": 0.0, "carry_out_min": 0.0,
    })
    for d in (first + timedelta(days=i) for i in range((last-first).days+1)):
        _ = entries[d.isoformat()]

    grouped_events = defaultdict(list)
    for item in events or ():
        if isinstance(item, dict):
            grouped_events[str(item.get("order_id") or "")].append(item)

    finished = []
    baselines = []
    missing = 0
    max_end = min(now.date(), last + timedelta(days=1))
    for order in db.siparisler:
        if not isinstance(order, dict) or db.siparis_durumu(order) != "tamamlandi":
            continue
        done = _dt(order.get("tamamlanma_tarihi"))
        if done is None or done.date() > now.date():
            continue
        work = _work(order, db._book_page_count)
        if work and (now.date() - done.date()).days <= 365:
            baselines.append(work["total"])
        if not first <= done.date() <= max_end:
            continue
        if not work:
            if first <= done.date() <= last:
                entries[done.date().isoformat()]["incomplete_orders"] += 1
                missing += 1
            continue
        finished.append((order, done, work))
    reference = median(baselines) if baselines else None

    # On a heavy completion morning, compare the entire completion-day batch
    # with the *ideal* machine/labor parallel lower bound, not a per-order sum.
    capacity = {}
    by_day = defaultdict(list)
    for order, done, stage in finished:
        by_day[done.date()].append((order, done, stage))
    for day, orders in by_day.items():
        group = [item[0] for item in orders]
        ideal = estimate(group, db._book_page_count, completed=True,
                         now=orders[-1][1])["optimistic_elapsed_min"]
        last_done = max(item[1] for item in orders)
        elapsed = _shift_minutes(day, last_done.replace(hour=0, minute=0,
                                                        second=0, microsecond=0),
                                 last_done)
        if day == now.date():
            elapsed = min(elapsed, _shift_minutes(day, now.replace(
                hour=0, minute=0, second=0, microsecond=0), now))
        capacity[day.isoformat()] = {
            "ideal_min": ideal, "elapsed_min": elapsed,
            "over_capacity": ideal > elapsed + 1e-6,
            "excess_min": max(0.0, ideal - elapsed),
        }

    shifted_orders = set()
    uncertain_orders = 0
    for order, done, stage in finished:
        day = done.date()
        prev = day - timedelta(days=1)
        key = str(order.get("bulut_id") or order.get("id") or "")
        events_for_order = grouped_events.get(key, [])
        qty = stage["copies"]
        prev_ready = today_ready = prev_box = today_box = 0
        for event in events_for_order:
            stamped = _dt(event.get("at"))
            if stamped is None or stamped > done:
                continue
            if stamped.date() not in (prev, day):
                continue
            if stamped.date() == prev:
                prev_ready += int(event.get("ready") or 0)
                prev_box += int(event.get("boxed") or 0)
            else:
                today_ready += int(event.get("ready") or 0)
                today_box += int(event.get("boxed") or 0)
        prev_ready = min(qty, max(0, prev_ready))
        today_ready = min(qty-prev_ready, max(0, today_ready))
        prev_box = min(qty, max(0, prev_box))
        today_box = min(qty-prev_box, max(0, today_box))
        prep_logged_prev = stage["prep"] * prev_ready / qty
        prep_logged_today = stage["prep"] * today_ready / qty
        pack_logged_prev = stage["pack"] * prev_box / qty
        pack_logged_today = stage["pack"] * today_box / qty

        undated_prep = max(0.0, stage["prep"] - prep_logged_prev -
                           prep_logged_today)
        undated_pack = max(0.0, stage["pack"] - pack_logged_prev -
                           pack_logged_today)
        started = _dt(order.get("isleme_alinma_tarihi"))
        # Never invent a yesterday shift without an actual activation date.
        preceding = (started is not None and started.date() == prev and
                     started < done)
        prev_window = _shift_minutes(prev, started, done) if preceding else 0.0
        curr_start = datetime.combine(day, SHIFT_START, tzinfo=done.tzinfo)
        curr_window = _shift_minutes(day, curr_start, done)
        frac = (prev_window / (prev_window+curr_window)
                if prev_window + curr_window else 0.0)
        predicted_prev = undated_prep * frac
        # If today's *ideal parallel* machine+staff lower bound exceeds the
        # hours elapsed before the last completed order, the two-day split
        # should not casually put almost every unlogged stage on today.
        # This is a capacity-based HEURISTIC, not proof of which copy was made
        # yesterday. Apply only when the saved activation was yesterday.
        day_capacity = capacity.get(day.isoformat(), {})
        lower = float(day_capacity.get("ideal_min") or 0)
        elapsed = float(day_capacity.get("elapsed_min") or 0)
        minimum_previous_fraction = (
            max(0.0, 1.0 - elapsed / lower) if lower > 0 else 0.0
        )
        if preceding and minimum_previous_fraction > 0:
            goal = max(0.0, stage["prep"] * minimum_previous_fraction
                       - prep_logged_prev)
            predicted_prev = min(undated_prep, max(predicted_prev, goal))
        # Packing stays on completion day unless an actual earlier packing
        # event says otherwise. A prior-day activation is not packing evidence.
        prev_total = prep_logged_prev + pack_logged_prev + predicted_prev
        today_total = (prep_logged_today + pack_logged_today +
                       undated_prep - predicted_prev + undated_pack)

        if prev_total > 1e-8:
            shifted_orders.add(key)
        unknown = undated_prep + undated_pack
        if unknown > 1e-8:
            uncertain_orders += 1

        # Keep unassigned earlier work out of artificial zero-activity days:
        # modeled output is only displayed for dates in the selected window.
        if first <= prev <= last and prev_total > 0:
            row = entries[prev.isoformat()]
            row["minutes"] += prev_total
            row["logged_minutes"] += prep_logged_prev + pack_logged_prev
            row["inferred_minutes"] += predicted_prev
            row["carry_out_min"] += prev_total
            row["modeled_orders"] += 1
        if first <= day <= last:
            row = entries[day.isoformat()]
            row["minutes"] += today_total
            row["logged_minutes"] += prep_logged_today + pack_logged_today
            row["inferred_minutes"] += (undated_prep-predicted_prev) + undated_pack
            row["carry_in_min"] += prev_total
            row["modeled_orders"] += 1

    for item in entries.values():
        item["equiv"] = (
            round(item["minutes"] / reference, 3) if reference else None)
        item["minutes"] = round(item["minutes"], 3)
        item["logged_minutes"] = round(item["logged_minutes"], 3)
        item["inferred_minutes"] = round(item["inferred_minutes"], 3)
        item["carry_in_min"] = round(item["carry_in_min"], 3)
        item["carry_out_min"] = round(item["carry_out_min"], 3)
    return {
        "days": dict(entries),
        "reference_min": round(reference, 3) if reference else None,
        "reference_samples": len(baselines),
        "shifted_orders": len(shifted_orders),
        "uncertain_orders": uncertain_orders,
        "incomplete_orders": missing,
        "capacity": capacity,
        "method": (
            "Gerçek tamamlanmalar değişmez. Önceki güne kayıtlı hazırlama/"
            "kolileme hareketleri gününe yazılır. Kayıtsız hazırlama emeği "
            "yalnız bir önceki güne ait aktivasyon varsa iki vardiyanın "
            "müsait saatleri ve ideal üretim kapasitesi oranında tahmini "
            "edilir; kolileme tamamlanma gününde kalır. Standart eşdeğer, tamamlanan siparişlerin "
            "medyan tahmini minimum iş yüküne göre hesaplanır. "
            "Gerçek çalışma saati veya fiziksel çıktı ölçümü değildir."
        ),
    }
