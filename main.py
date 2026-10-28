"""فريق الذهب: القناص + المحقق + البروفيسور. نسخة تجريبية: إشعار تلكرام بدون تنفيذ."""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import config
from consensus import agree, is_active, store_vote
import journal
from indicators import summarize
from models import Vote
from risk import build_trade

STATE_FILE = "state.json"
AR_DIR = {"BUY": "شراء 🟢", "SELL": "بيع 🔴"}


def log(*a):
    print(datetime.now().strftime("%H:%M:%S"), *a, flush=True)


# ---------- الحالة ----------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            return json.load(open(STATE_FILE, encoding="utf-8"))
        except Exception:
            pass
    return {"seen": [], "day": "", "count": 0, "last_signal": None, "last_prof": None}


def save_state(st):
    st["seen"] = st["seen"][-2000:]
    json.dump(st, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False)


def votes_to_json(votes):
    return {k: {"agent": v.agent, "direction": v.direction, "confidence": v.confidence,
                "reason": v.reason, "ts": v.ts.isoformat(), "sl": v.sl_atr_mult}
            for k, v in votes.items()}


def votes_from_json(d):
    out = {}
    for k, v in (d or {}).items():
        try:
            out[k] = Vote(v["agent"], v["direction"], int(v["confidence"]), v["reason"],
                          datetime.fromisoformat(v["ts"]), float(v.get("sl", 1.5)))
        except Exception:
            pass
    return out


def new_items(items, st):
    seen = set(st["seen"])
    fresh = []
    for it in sorted(items, key=lambda x: (x["tier"], x["age_min"])):
        if it["id"] in seen or it["age_min"] > config.MAX_ITEM_AGE_MIN:
            continue
        seen.add(it["id"])
        st["seen"].append(it["id"])
        fresh.append(it)
    return fresh[:config.MAX_ITEMS_PER_AGENT]


def _ago_min(iso, now):
    return (now - datetime.fromisoformat(iso)).total_seconds() / 60 if iso else 1e9


def in_blackout(now):
    w = timedelta(minutes=config.BLACKOUT_WINDOW_MIN)
    for s in config.BLACKOUT_UTC:
        t = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        if abs(now - t) <= w:
            return True
    return False


# ---------- نص الإشعار ----------
def format_signal(t, votes, ind):
    icons = {"sniper": "🎯 القناص", "detective": "🕵️ المحقق", "professor": "🎓 البروفيسور"}
    lines = [
        "🔔 إشارة ذهب (تجريبية، بدون تنفيذ)",
        f"الاتجاه: {AR_DIR[t['direction']]}",
        f"الدخول التقريبي: {t['entry']}",
        f"وقف الخسارة: {t['sl']} (مسافة {t['sl_dist']}$)",
        f"الهدف 1: {t['tp1']} | الهدف 2: {t['tp2']}",
        f"الحجم المقترح: {t['lot']} لوت (مخاطرة ≈ {t['risk_usd']}$ = {t['risk_pct']}%)",
    ]
    if t["partial"]:
        lines.append(f"عند الهدف 1: اغلق {t['lot_tp1']} لوت وانقل الوقف لنقطة الدخول")
    else:
        lines.append("الحجم صغير: بدون إغلاق جزئي، هدف واحد (الهدف 2)")
    lines.append(f"RSI {ind['rsi14']} | ATR {ind['atr14_usd']}$ | اتجاه {ind['trend']}")
    lines.append("— الأصوات —")
    for k in ("sniper", "detective", "professor"):
        v = votes[k]
        lines.append(f"{icons[k]} ({v.confidence}): {v.reason}")
    return "\n".join(lines)


# ---------- دورة واحدة ----------
def cycle(S, st, votes, now=None):
    now = now or datetime.now(timezone.utc)
    ttl, minc = config.VOTE_TTL_MIN, config.MIN_CONFIDENCE

    df = S.get_prices()
    if df is None or S.minutes_stale(df) > config.STALE_MIN:
        log("السوق مغلق أو لا توجد بيانات سعر")
        return
    ind = summarize(df)

    for sig, outcome, pnl in journal.update_signals(st, df, now):
        S.notify(journal.format_result(sig, outcome, pnl, st["stats"]))

    items = S.sniper_items(st)
    if items:
        log(f"القناص: {len(items)} خبر جديد")
        store_vote(votes, "sniper", S.sniper_vote(items, ind, now), now, ttl)
    items = S.detective_items(st)
    if items:
        log(f"المحقق: {len(items)} خبر جديد")
        store_vote(votes, "detective", S.detective_vote(items, ind, now), now, ttl)

    for k in ("sniper", "detective"):
        v = votes.get(k)
        if v:
            log(f"  {k}: {v.direction} ({v.confidence})")

    if not agree(votes, ("sniper", "detective"), now, ttl, minc):
        return

    # القناص والمحقق متفقان: البروفيسور يعطي القرار النهائي
    if _ago_min(st.get("last_prof"), now) >= config.PROFESSOR_RECHECK_MIN:
        st["last_prof"] = now.isoformat()
        store_vote(votes, "professor", S.professor_vote(ind, now), now, ttl)
        v = votes.get("professor")
        log(f"  professor: {v.direction} ({v.confidence})" if v else "  professor: فشل")

    d = agree(votes, ("sniper", "detective", "professor"), now, ttl, minc)
    if not d:
        return

    # ---- بوابات الأمان ----
    today = now.strftime("%Y-%m-%d")
    if st.get("day") != today:
        st["day"], st["count"] = today, 0
    if st["count"] >= config.MAX_SIGNALS_PER_DAY:
        log("وصلنا الحد اليومي للإشارات")
        return
    if _ago_min(st.get("last_signal"), now) < config.COOLDOWN_MIN:
        log("فترة انتظار بعد آخر إشارة")
        return
    if in_blackout(now):
        log("قريب من خبر عالي التأثير: لا إشارة")
        return

    t = build_trade(d, ind["price"], ind["atr14_usd"], votes["professor"].sl_atr_mult)
    if t is None:
        log("الرصيد صغير جداً لهذا الوقف: لا صفقة")
        return

    S.notify(format_signal(t, votes, ind))
    journal.register(st, t, now)
    st["count"] += 1
    st["last_signal"] = now.isoformat()
    votes.clear()


# ---------- التشغيل الحقيقي ----------
def real_services():
    import agents
    import notifier
    import sources as src

    def sniper_items(st):
        raw = src.fetch_feeds(config.SNIPER_FEEDS) + src.x_search(config.X_SNIPER_QUERY, "X-Official", 1)
        return new_items(raw, st)

    def detective_items(st):
        raw = src.fetch_feeds(config.DETECTIVE_FEEDS) + src.x_search(config.X_DETECTIVE_QUERY, "X-Community", 2)
        return new_items(raw, st)

    return SimpleNamespace(
        get_prices=src.get_candles, minutes_stale=src.minutes_since_last_candle,
        sniper_items=sniper_items, detective_items=detective_items,
        sniper_vote=agents.sniper_vote, detective_vote=agents.detective_vote,
        professor_vote=agents.professor_vote, notify=notifier.send)


def run_once():
    """دورة واحدة (لـ GitHub Actions): يحمّل الحالة والأصوات، ينفذ، ثم يحفظ."""
    S, st = real_services(), load_state()
    votes = votes_from_json(st.get("votes"))
    try:
        cycle(S, st, votes)
    finally:
        st["votes"] = votes_to_json(votes)
        save_state(st)


def main():
    if not config.ANTHROPIC_API_KEY:
        print("ضع ANTHROPIC_API_KEY في ملف .env")
        return
    if "--once" in sys.argv:
        run_once()
        return
    S, st, votes = real_services(), load_state(), {}
    S.notify("✅ فريق الذهب اشتغل (وضع تجريبي: إشعارات فقط)")
    log("بدأ التشغيل. اضغط Ctrl+C للإيقاف.")
    while True:
        try:
            cycle(S, st, votes)
        except Exception as e:
            log("خطأ في الدورة:", type(e).__name__, str(e)[:200])
        save_state(st)
        time.sleep(config.LOOP_SECONDS)


if __name__ == "__main__":
    main()
