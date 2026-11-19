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


def activity_dates(db, events=(), now=None):
    """Actual activation, completion and recorded progress dates, newest first.

    Never infer a historical work day from an order's current ready/boxed
    counters. No extra cloud reads; uses only the local synced snapshot.
    """
    now=now or datetime.now().astimezone()
    today=now.date()
    days=set()
    for order in db.siparisler:
        if not isinstance(order,dict):
            continue
        activated=local_datetime(order.get("isleme_alinma_tarihi"))
        if activated and activated.date()<=today:
            days.add(activated.date().isoformat())
        if db.siparis_durumu(order)=="tamamlandi":
            done=local_datetime(order.get("tamamlanma_tarihi"))
            if done and done.date()<=today:
                days.add(done.date().isoformat())
    for item in events or []:
        stamped=local_datetime(item.get("at"))
        if stamped and stamped.date()<=today:
            days.add(stamped.date().isoformat())
    return sorted(days,reverse=True)


def _date(value):
    if isinstance(value,date) and not isinstance(value,datetime):
        return value
    return date.fromisoformat(str(value)[:10])


def daily_dashboard(db, events=(), days=14, now=None, selected_day=None,
                    start_date=None, end_date=None):
    """Read-only production view; optional exact calendar day/range filter.

    Old `days` callers keep their rolling-date semantics. Calendar ranges are
    inclusive and limited to 366 days to prevent heavy UI redraws.
    """
    now=now or datetime.now().astimezone()
    today=now.date()
    if start_date is not None:
        start=_date(start_date)
        end=_date(end_date) if end_date is not None else start
        start,end=sorted((start,end))
        if end>today:
            raise ValueError("Gelecek tarihler için üretim verisi mevcut değil.")
        days=(end-start).days+1
        if days>366:
            raise ValueError("Tek seferde en fazla 366 günlük dönem seçilebilir.")
    else:
        days=max(1,min(90,int(days)))
        start=today-timedelta(days=days-1)
        end=today
    selected_day=_date(selected_day) if selected_day is not None else end
    if not start<=selected_day<=end:
        selected_day=end
    points={}
    for i in range(days):
        d=start+timedelta(days=i)
        key=d.isoformat()
        points[key]={"date":key,"label":d.strftime("%d/%m"),
                     "orders":0,"started":0,"ready":0,"boxed":0,
                     "ready_orders":set(),"boxed_orders":set(),
                     "pages":0,"books":0,"sb":0,"rnk":0}
    open_orders=[]
    snapshot_starts=set()
    prior_completions={}
    baseline_start=selected_day-timedelta(days=30)
    for order in db.siparisler:
        status=db.siparis_durumu(order)
        if status in ("havuz","aktif") and not order.get("iade_tarihi"):
            open_orders.append(order)
        if status=="tamamlandi":
            finished=local_datetime(order.get("tamamlanma_tarihi"))
            if finished and baseline_start<=finished.date()<selected_day:
                key=finished.date().isoformat()
                prior_completions[key]=prior_completions.get(key,0)+1
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
            key=(activated.date().isoformat(),str(order.get("bulut_id") or order.get("id") or ""))
            snapshot_starts.add(key)
            points[activated.date().isoformat()]["started"]+=1

    # Real cloud events only; current ready/boxed counters cannot reveal
    # what hour work was performed. Undo operations are signed deltas.
    logged_days=set()
    hourly=[{"hour":hour,"started":0,"orders":0,"ready":0,"boxed":0,
             "ready_orders":set(),"boxed_orders":set()} for hour in range(24)]
    event_days=set()
    logged_starts=set()
    for entry in events or []:
        dt=local_datetime(entry.get("at"))
        if dt is None:continue
        day_key=dt.date().isoformat()
        if day_key not in points:continue
        event_days.add(day_key)
        delta_ready=int(entry.get("ready") or 0)
        delta_boxed=int(entry.get("boxed") or 0)
        if delta_ready or delta_boxed:logged_days.add(day_key)
        if str(entry.get("status"))=="aktif":
            identity=(day_key,str(entry.get("order_id") or ""))
            if identity not in snapshot_starts and identity not in logged_starts:
                logged_starts.add(identity)
                points[day_key]["started"]+=1
                if dt.date()==selected_day:
                    hourly[dt.hour]["started"]+=1
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
    selected_row=points[selected_day.isoformat()]
    today_row=points.get(today.isoformat())
    if today_row is None:
        today_row={"orders":0,"started":0,"ready":0,"boxed":0,
                   "ready_orders":0,"boxed_orders":0,"pages":0,"books":0}
    historical=[p for p in values if p["date"]<selected_day.isoformat()]
    workdays=[p for p in historical if p["orders"]>0]
    if not workdays and prior_completions:
        workdays=[{"orders":value} for value in prior_completions.values()]
    average_orders=sum(p["orders"] for p in workdays)/len(workdays) if workdays else 0.0
    selected_orders=selected_row["orders"]
    shift_start=now.replace(hour=7,minute=0,second=0,microsecond=0)
    elapsed=(max(0.0,min(SHIFT_MINUTES,(now-shift_start).total_seconds()/60))
             if selected_day==today else SHIFT_MINUTES)
    rate=selected_orders/(elapsed/60) if elapsed else 0
    baseline_rate=average_orders/(SHIFT_MINUTES/60)
    # Compare only after one elapsed shift hour. Past-day denominator is
    # scheduled shift time, not measured employee or machine working time.
    tempo_change=(100*(rate/baseline_rate-1)) if baseline_rate>0 and elapsed>=60 else None
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
    selected_activity_known=selected_day.isoformat() in logged_days
    return {
        "days":days,"start":start.isoformat(),"end":end.isoformat(),
        "overview_mode":start_date is None,
        "selected_day":selected_day.isoformat(),
        "points":values,"hourly":hourly,"today":today_row,
        "selected":selected_row,
        "period": {
            "orders":sum(p["orders"] for p in values),
            "started":sum(p["started"] for p in values),
            "books":sum(p["books"] for p in values),
            "pages":sum(p["pages"] for p in values),
            "ready":sum(p["ready"] for p in values if p["date"] in logged_days),
            "boxed":sum(p["boxed"] for p in values if p["date"] in logged_days),
        },
        "open_orders":len(open_orders),
        "active_orders":sum(1 for o in open_orders if db.siparis_durumu(o)=="aktif"),
        "open_work":open_work,
        "average_orders":average_orders,
        "today_orders":today_row["orders"],"today_rate":rate,
        "selected_rate":rate,"baseline_rate":baseline_rate,
        "tempo_change":tempo_change,"workload":workload,
        "forecast":{
            "fully_known":forecast["fully_known"],
            "missing_page_copies":forecast["missing_page_copies"],
            "shift_status":forecast["shift_status"],
            "bottleneck":forecast["bottleneck"],
            "shift_remaining_min":forecast["shift_remaining_min"],
            "optimistic_elapsed_min":forecast["optimistic_elapsed_min"],
        },
        "event_days":sorted(event_days), "logged_days":sorted(logged_days),
        "today_activity_known":today_activity_known,
        "selected_activity_known":selected_activity_known,
        "has_progress_history":bool(logged_days),
        "has_missing_pages":forecast["missing_page_copies"]>0,
    }


def operation_insight(report, now=None):
    """Daily, factual, actionable interpretation from known operational values.

    Historic dates may be inspected, but the backlog snapshot is explicitly
    marked as CURRENT; we never pretend it was the backlog on a past date.
    """
    now=now or datetime.now().astimezone()
    selected=_date(report["selected_day"])
    today=now.date()
    ranged=(report["start"]!=report["end"]
            and not report.get("overview_mode",False))
    values=report["period"] if ranged else report["selected"]
    day_text=(selected.strftime("%d.%m.%Y") if not ranged else
              _date(report["start"]).strftime("%d.%m.%Y")+" – "+
              _date(report["end"]).strftime("%d.%m.%Y"))
    headline=("DÖNEM DEĞERLENDİRMESİ" if ranged else "GÜNLÜK OPERASYON DEĞERLENDİRMESİ")
    headline+=" · "+day_text
    completed=int(values["orders"])
    if completed:
        period_text="Seçilen dönemde" if ranged else "Seçilen günde"
        observation=(f"{period_text} {completed} sipariş tamamlandı; "
                     f"{int(values['books'])} kitap ve {int(values['pages'])} sayfalık "
                     "üretim tamamlanmış sipariş kayıtlarında görünüyor.")
    else:
        observation=(("Seçilen dönemde" if ranged else "Seçilen günde")+
                     " tamamlanmış sipariş kaydı bulunmuyor; "
                     "bu, hiç çalışılmadığı anlamına gelmez.")
    known=bool(report["selected_activity_known"])
    logged=set(report.get("logged_days") or [])
    if ranged:
        selected_points=[p for p in report["points"] if p["date"] in logged]
        if selected_points:
            progress=(f"Kayıtlı hareketlerde net {int(values['ready'])} nüsha hazırlandı, "
                      f"{int(values['boxed'])} nüsha kolilendi. "
                      "İşlem günlüğü olmayan günler bu toplamda ölçülmedi.")
        else:
            progress="Bu dönemde hazırlama/kolileme işlem günlüğü bulunmuyor; değerler sıfır kabul edilmedi."
    elif known:
        progress=(f"İşlem kayıtlarında net {int(values['ready'])} nüsha hazırlandı "
                  f"ve {int(values['boxed'])} nüsha kolilendi.")
    else:
        progress=("Bu güne ait hazırlama/kolileme saat kaydı yok; "
                  "gerçek çalışma temposu bu hareketlerden çıkarılamaz.")
    if report["average_orders"]>0 and not ranged:
        difference=100*(completed/report["average_orders"]-1)
        mark="üzerinde" if difference>1 else "altında" if difference<(-1) else "yakınında"
        comparison=(
            f"Önceki üretim günleri ortalaması {report['average_orders']:.1f} "
            f"sipariş/gün. Seçili günün tamamlanma adedi bu ortalamanın "
            f"%{abs(difference):.0f} {mark}."
            if mark!="yakınında" else
            f"Seçili gün, önceki üretim günleri ortalaması olan "
            f"{report['average_orders']:.1f} sipariş/güne yakın.")
    elif report["average_orders"]>0:
        comparison=(f"Önceki üretim günleri ortalaması "
                    f"{report['average_orders']:.1f} sipariş/gün.")
    else:
        comparison="Karşılaştırma için yeterli önceki üretim günü bulunmuyor."
    work=report["open_work"]
    active=int(report["active_orders"])
    pool=int(report["open_orders"])-active
    waiting=int(work["print_waiting"])
    packing=int(work["pack_ready"])
    if packing and waiting:
        priority=(f"Öncelik: kolilemeye hazır {packing} nüshayı sevkiyata ilerletirken "
                  f"{waiting} nüshanın baskı/hazırlığını sürdürmek.")
    elif packing:
        priority=f"Öncelik: hazır bekleyen {packing} nüshanın kolilenmesi."
    elif waiting:
        priority=f"Öncelik: baskı/hazırlık bekleyen {waiting} nüshanın tamamlanması."
    else:
        priority="Açık siparişlerde kayıtlı baskı veya kolileme bekleyen nüsha yok."
    live=f"Şu an {active} aktif, {pool} havuzda sipariş var. "+priority
    forecast=report.get("forecast") or {}
    missing=int(forecast.get("missing_page_copies") or 0)
    if missing:
        assessment=(f"Risk: {missing} nüshanın sayfa sayısı eksik. "
                    "Mesaiye yetişme hesabına güvenilemez; önce sayfa bilgilerini tamamlayın.")
        severity="warning"
    elif selected!=today or (ranged and _date(report["end"])!=today):
        assessment=("Açık iş ve mesai durumu güncel anlık veridir; "
                    "seçilen geçmiş tarihin vardiya sonu stoku olarak yorumlanmamalı.")
        severity="neutral"
    elif now.hour>=17:
        assessment=("07.00–17.00 mesai aralığı sona erdi. Kalan işlerin "
                    "bir sonraki vardiya için planlanması gerekir.")
        severity="warning" if waiting or packing else "success"
    elif now.hour<7:
        assessment="07.00–17.00 vardiyası henüz başlamadı; açık işler vardiya başında yeniden değerlendirilmeli."
        severity="neutral"
    else:
        risk=forecast.get("shift_status","")
        if risk=="İdeal koşulda bile mesaiye sığmıyor":
            assessment=("Risk: teorik en iyi senaryo bile kalan mesaiye sığmıyor. "
                        "Önceliklendirme veya ek kapasite planı gerekli.")
            severity="warning"
        elif risk=="Mesaiye yetişme riski var":
            assessment=("Mesaiye yetişme riski var. "
                        "Teorik süreler kesin teslim saati değildir.")
            severity="warning"
        elif waiting or packing:
            assessment=("Mevcut varsayımlarla kalan işler mesaiye sığabilir; "
                        "mola, arıza ve yeniden baskılar hesaba katılmıyor.")
            severity="success"
        else:
            assessment="Şu anda kayıtlı açık üretim işi bulunmuyor."
            severity="success"
    return {"title":headline, "observation":observation, "progress":progress,
            "comparison":comparison, "live":live, "assessment":assessment,
            "severity":severity,
            "note":"Karar desteği; gerçek cihaz/çalışan süre ölçümü değildir."}

