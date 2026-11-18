"""Operational FlexFlow metrics sourced from recorded order and cloud events.

Never invents hourly ready/boxed timestamps, employee hours or a 0-100
"efficiency score". Comparisons are completed orders per scheduled shift hour.
Cloud event history is read-only, deduplicated, bounded and contains no PII.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from math import isfinite

from flexflow import estimate, SHIFT_MINUTES
from siparis_uretim_ozeti import production_summary


def local_datetime(raw):
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt.astimezone() if dt.tzinfo else dt
    except (ValueError, TypeError, OverflowError):
        return None


def extract_history(rows, days=90, now=None, maximum=12000):
    """Extract compact progress/transition events from the already-fetched RTDB order rows.

    Event-log records have server-side timestamps. No extra Firebase fetch.
    Do not reconstruct old missing events from current ready/boxed counters.
    """
    now=now or datetime.now().astimezone()
    cutoff=now.date()-timedelta(days=days-1)
    seen=set()
    events=[]
    for order in rows or []:
        if not isinstance(order,dict):continue
        order_id=str(order.get("id") or "")
        logs=order.get("event_log") or {}
        if not isinstance(logs,dict):continue
        for event_id,entry in logs.items():
            if not isinstance(entry,dict):continue
            action=str(entry.get("action") or "")
            if action not in ("transition","progress","progress_bulk"):
                continue
            event_key=order_id+":"+str(entry.get("id") or event_id)
            if event_key in seen:continue
            dt=local_datetime(entry.get("created_at"))
            if dt is None or dt.date()<cutoff or dt.date()>now.date():continue
            details=entry.get("details") or {}
            if not isinstance(details,dict):continue
            records=details.get("events") or []
            if not isinstance(records,list):continue
            ready=boxed=0
            status=""
            valid=True
            for detail in records:
                if not isinstance(detail,dict):continue
                try:
                    ready+=int(detail.get("delta_ready") or 0)
                    boxed+=int(detail.get("delta_boxed") or 0)
                except (ValueError,TypeError,OverflowError):
                    valid=False
                    break
                status=str(detail.get("to_status") or status)
            if not valid:continue
            if ready==boxed==0 and status not in ("aktif","tamamlandi"):continue
            seen.add(event_key)
            events.append({"id":event_key, "order_id":order_id,
                           "at":dt.isoformat(), "ready":ready,
                           "boxed":boxed, "status":status})
    events.sort(key=lambda e:e["at"],reverse=True)
    return events[:max(100,int(maximum))]


def daily_dashboard(db, events=(), days=14, now=None, selected_day=None):
    """Business-ready production indicators, separated by provenance."""
    now=now or datetime.now().astimezone()
    days=max(1,min(90,int(days)))
    today=now.date()
    selected_day=selected_day or today
    if isinstance(selected_day,str):
        selected_day=date.fromisoformat(selected_day)
    start=today-timedelta(days=days-1)
    points={}
    for i in range(days):
        d=start+timedelta(days=i)
        key=d.isoformat()
        points[key]={"date":key,"label":d.strftime("%d/%m"),
                     "orders":0,"started":0,"ready":0,"boxed":0,
                     "ready_orders":set(),"boxed_orders":set(),
                     "pages":0,"books":0,"sb":0,"rnk":0}
    open_orders=[]
    for order in db.siparisler:
        status=db.siparis_durumu(order)
        if status in ("havuz","aktif") and not order.get("iade_tarihi"):
            open_orders.append(order)
        if status=="tamamlandi":
            finished=local_datetime(order.get("tamamlanma_tarihi"))
            if finished and finished.date().isoformat() in points:
                row=points[finished.date().isoformat()]
                row["orders"]+=1
                for item in order.get("kitaplar",[]) or []:
                    try:qty=max(0,int(item.get("adet") or 0))
                    except (ValueError,TypeError):qty=0
                    kind="rnk" if str(item.get("tur","SB")).upper() in ("RNK","RENK","RENKLİ","RENKLI") else "sb"
                    row[kind]+=qty
                    row["books"]+=qty
                    try:pages=max(0,int(db._book_page_count(item) or 0))
                    except (ValueError,TypeError):pages=0
                    row["pages"]+=pages*qty
        activated=local_datetime(order.get("isleme_alinma_tarihi"))
        if activated and activated.date().isoformat() in points:
            points[activated.date().isoformat()]["started"]+=1

    # Real cloud events only; current ready/boxed counters cannot reveal
    # what hour work was performed. Undo operations are signed deltas.
    logged_days=set()
    hourly=[{"hour":hour,"started":0,"orders":0,"ready":0,"boxed":0,
             "ready_orders":set(),"boxed_orders":set()} for hour in range(24)]
    event_days=set()
    for entry in events or []:
        dt=local_datetime(entry.get("at"))
        if dt is None:continue
        day_key=dt.date().isoformat()
        if day_key not in points:continue
        event_days.add(day_key)
        delta_ready=int(entry.get("ready") or 0)
        delta_boxed=int(entry.get("boxed") or 0)
        if delta_ready or delta_boxed:logged_days.add(day_key)
        row=points[day_key]
        row["ready"]+=delta_ready
        row["boxed"]+=delta_boxed
        if delta_ready:row["ready_orders"].add(entry.get("order_id"))
        if delta_boxed:row["boxed_orders"].add(entry.get("order_id"))
        if dt.date()==selected_day:
            hour=hourly[dt.hour]
            hour["ready"]+=delta_ready
            hour["boxed"]+=delta_boxed
            if delta_ready:hour["ready_orders"].add(entry.get("order_id"))
            if delta_boxed:hour["boxed_orders"].add(entry.get("order_id"))

    # For hour/day "activated" and "completed" use timestamps saved on
    # each order, not event count (avoids duplicates and old redo events).
    for order in db.siparisler:
        start_at=local_datetime(order.get("isleme_alinma_tarihi"))
        done_at=local_datetime(order.get("tamamlanma_tarihi")) if db.siparis_durumu(order)=="tamamlandi" else None
        if start_at and start_at.date()==selected_day:
            hourly[start_at.hour]["started"]+=1
        if done_at and done_at.date()==selected_day:
            hourly[done_at.hour]["orders"]+=1

    values=list(points.values())
    for row in values:
        row["ready_orders"]=len(row["ready_orders"])
        row["boxed_orders"]=len(row["boxed_orders"])
    for row in hourly:
        row["ready_orders"]=len(row["ready_orders"])
        row["boxed_orders"]=len(row["boxed_orders"])

    open_work=production_summary(open_orders,db._book_page_count)
    historical=values[:-1]
    workdays=[p for p in historical if p["orders"]>0]
    average_orders=sum(p["orders"] for p in workdays)/len(workdays) if workdays else 0.0
    today_orders=values[-1]["orders"]
    shift_start=now.replace(hour=7,minute=0,second=0,microsecond=0)
    elapsed=max(0.0,min(SHIFT_MINUTES,(now-shift_start).total_seconds()/60))
    rate=today_orders/(elapsed/60) if elapsed else 0
    baseline_rate=average_orders/(SHIFT_MINUTES/60)
    tempo_change=(100*(rate/baseline_rate-1)) if baseline_rate>0 else None
    pending=[o for o in open_orders if db.siparis_durumu(o) in ("aktif","havuz")]
    forecast=estimate(pending,db._book_page_count,now=now)
    if forecast["shift_status"]=="İki senaryoda da mesaiye sığıyor":
        workload="Mesaiye yetişmesi bekleniyor"
    elif forecast["shift_status"]=="İdeal koşulda bile mesaiye sığmıyor":
        workload="Mesai kapasitesi yetersiz"
    elif not forecast["fully_known"]:
        workload="Eksik sayfa verisi · tahmin belirsiz"
    else:
        workload="Mesaiye yetişme riski var"
    today_activity_known=today.isoformat() in logged_days
    return {
        "days":days,"start":start.isoformat(),"end":today.isoformat(),
        "selected_day":selected_day.isoformat(),
        "points":values,"hourly":hourly,"today":values[-1],
        "open_orders":len(open_orders),
        "active_orders":sum(1 for o in open_orders if db.siparis_durumu(o)=="aktif"),
        "open_work":open_work,
        "average_orders":average_orders,
        "today_orders":today_orders,"today_rate":rate,"baseline_rate":baseline_rate,
        "tempo_change":tempo_change,"workload":workload,
        "event_days":sorted(event_days), "logged_days":sorted(logged_days),
        "today_activity_known":today_activity_known,
        "has_progress_history":bool(logged_days),
        "has_missing_pages":forecast["missing_page_copies"]>0,
    }
