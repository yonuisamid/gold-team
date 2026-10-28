"""سجل الإشارات: يتابع كل إشارة على الشموع ويحسب نتيجتها (هدف/وقف) والإحصائيات."""
import csv
from datetime import datetime

import pandas as pd

import config

TIMEOUT_H = 24
CSV_FILE = "signals.csv"


def new_stats():
    return {"n": 0, "wins": 0, "losses": 0, "be": 0, "pnl": 0.0}


def register(st, trade, now):
    st.setdefault("open", []).append({**trade, "ts": now.isoformat(),
                                      "tp1_hit": False, "sl_cur": trade["sl"], "banked": 0.0})


def _utc(df):
    idx = df.index
    return idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")


def evaluate(sig, df, now):
    """يرجع (outcome, pnl) إذا انتهت الإشارة، وإلا None. يحدّث sig (TP1/الوقف المتحرك)."""
    ts = pd.Timestamp(sig["ts"])
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts
    buy = sig["direction"] == "BUY"
    s = 1 if buy else -1
    unit, d, lot = config.CONTRACT_SIZE, sig["sl_dist"], sig["lot"]
    rem = round(lot - sig["lot_tp1"], 2) if sig["partial"] else lot

    for t, hi, lo in zip(_utc(df), df["High"], df["Low"]):
        if t <= ts:
            continue
        hi, lo = float(hi), float(lo)
        if (lo <= sig["sl_cur"]) if buy else (hi >= sig["sl_cur"]):      # الوقف أولاً (تحفظ)
            if sig["tp1_hit"]:
                return "TP1+BE", round(sig["banked"], 2)
            return "SL", round(-lot * unit * d, 2)
        if sig["partial"] and not sig["tp1_hit"]:
            if (hi >= sig["tp1"]) if buy else (lo <= sig["tp1"]):
                sig["tp1_hit"] = True
                sig["banked"] = sig["lot_tp1"] * unit * d
                sig["sl_cur"] = sig["entry"]
                continue                                                  # الوقف المتحرك يُفحص بالشمعة التالية
        if sig["tp1_hit"] or not sig["partial"]:
            if (hi >= sig["tp2"]) if buy else (lo <= sig["tp2"]):
                return "TP2", round(sig["banked"] + rem * unit * d * config.RR, 2)

    if (now - datetime.fromisoformat(sig["ts"])).total_seconds() > TIMEOUT_H * 3600:
        last = float(df["Close"].iloc[-1])
        floating = rem * unit * (last - sig["entry"]) * s
        return "TIMEOUT", round(sig["banked"] + floating, 2)
    return None


def update_signals(st, df, now):
    closed, still = [], []
    stats = st.setdefault("stats", new_stats())
    for sig in st.get("open", []):
        res = evaluate(sig, df, now)
        if res is None:
            still.append(sig)
            continue
        outcome, pnl = res
        stats["n"] += 1
        stats["pnl"] = round(stats["pnl"] + pnl, 2)
        stats["wins" if pnl > 0 else "losses" if pnl < 0 else "be"] += 1
        closed.append((sig, outcome, pnl))
        try:
            with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([sig["ts"], sig["direction"], sig["entry"], sig["sl"],
                                        sig["tp2"], sig["lot"], outcome, pnl])
        except OSError:
            pass
    st["open"] = still
    return closed


def format_result(sig, outcome, pnl, stats):
    names = {"SL": "ضرب الوقف ❌", "TP2": "حقق الهدف الثاني ✅",
             "TP1+BE": "الهدف الأول ثم رجع للدخول ➖", "TIMEOUT": "أُغلقت بعد 24 ساعة ⏱"}
    wr = round(100 * stats["wins"] / stats["n"]) if stats["n"] else 0
    return (f"📊 نتيجة إشارة {sig['direction']} عند {sig['entry']}: {names.get(outcome, outcome)}\n"
            f"الربح/الخسارة: {pnl:+.2f}$\n"
            f"الإجمالي: {stats['n']} صفقة | رابحة {stats['wins']} | خاسرة {stats['losses']} | "
            f"نسبة النجاح {wr}% | صافي {stats['pnl']:+.2f}$")
