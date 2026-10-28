"""اختبار المنطق بدون إنترنت ولا مفاتيح: python test_logic.py"""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

import config
import main
from consensus import agree, store_vote
from llm import parse_json, to_vote
from models import Vote
from risk import build_trade

NOW = datetime(2026, 10, 26, 14, 0, tzinfo=timezone.utc)


def V(agent, d, c, age=0):
    return Vote(agent, d, c, "x", NOW - timedelta(minutes=age))


# --- المخاطرة ---
config.ACCOUNT_BALANCE = 1000
config.FIXED_LOT = 0
t = build_trade("BUY", 2650.0, 5/1.5, 1.5, 1000)   # SL = 5.0
assert t["sl_dist"] == 5.0 and t["lot"] == 0.02 and t["sl"] == 2645.0, t
assert t["tp1"] == 2655.0 and t["tp2"] == 2660.0 and t["partial"], t
s = build_trade("SELL", 2650.0, 5/1.5, 1.5, 1000)
assert s["sl"] == 2655.0 and s["tp2"] == 2640.0, s
assert build_trade("BUY", 2650.0, 5/1.5, 1.5, 200) is None      # رصيد صغير
assert build_trade("BUY", 2650.0, 40, 2.5, 1000)["sl_dist"] == 15.0  # الحد الأعلى

config.FIXED_LOT = 0.01
f = build_trade("BUY", 2650.0, 5 / 1.5, 1.5, 100)
assert f["lot"] == 0.01 and f["risk_usd"] == 5.0 and f["risk_pct"] == 5.0 and not f["partial"], f
config.FIXED_LOT = 0

# --- الاتفاق ---
names = ("sniper", "detective", "professor")
ok = {"sniper": V("sniper", "BUY", 80), "detective": V("detective", "BUY", 70),
      "professor": V("professor", "BUY", 66)}
assert agree(ok, names, NOW, 30, 65) == "BUY"
assert agree({**ok, "professor": V("p", "SELL", 90)}, names, NOW, 30, 65) is None
assert agree({**ok, "professor": V("p", "NEUTRAL", 90)}, names, NOW, 30, 65) is None
assert agree({**ok, "professor": V("p", "BUY", 60)}, names, NOW, 30, 65) is None
assert agree({**ok, "sniper": V("s", "BUY", 90, age=45)}, names, NOW, 30, 65) is None
assert agree({"sniper": ok["sniper"]}, names, NOW, 30, 65) is None
vs = {"sniper": V("s", "BUY", 80)}
store_vote(vs, "sniper", V("s", "NEUTRAL", 10), NOW, 30)
assert vs["sniper"].direction == "BUY"                          # المحايد ما يلغي
store_vote(vs, "sniper", V("s", "SELL", 70), NOW, 30)
assert vs["sniper"].direction == "SELL"

# --- تحليل رد النموذج ---
d = parse_json('```json\n{"direction":"buy","confidence":"88","reason_ar":"تمام","sl_atr_mult":9}\n```')
v = to_vote("professor", d, NOW)
assert v.direction == "BUY" and v.confidence == 88 and v.sl_atr_mult == 2.5
assert to_vote("sniper", {"direction": "MOON", "confidence": 500}, NOW).direction == "NEUTRAL"

# --- محاكاة دورة كاملة بأصوات مزيفة ---
rng = np.random.default_rng(1)
idx = pd.date_range(end=NOW, periods=300, freq="15min")
close = 2650 + np.cumsum(rng.normal(0, 1.2, 300))
df = pd.DataFrame({"Close": close, "High": close + 1.5, "Low": close - 1.5}, index=idx)
sent = []
mk = lambda a, d, c: (lambda *x: Vote(a, d, c, "سبب تجريبي", NOW))
item = [{"id": "1", "title": "t", "summary": "", "source": "Fed", "tier": 1, "age_min": 5}]
S = type("S", (), dict(
    get_prices=lambda self=None: df, minutes_stale=lambda d: 5,
    sniper_items=lambda st: item, detective_items=lambda st: item,
    sniper_vote=mk("sniper", "BUY", 80), detective_vote=mk("detective", "BUY", 72),
    professor_vote=lambda ind, now: Vote("professor", "BUY", 70, "فني", now, 1.5),
    notify=sent.append))
st, votes = {"seen": [], "day": "", "count": 0, "last_signal": None, "last_prof": None}, {}
main.cycle(S, st, votes, NOW)
assert len(sent) == 1 and "شراء" in sent[0], sent
main.cycle(S, st, votes, NOW + timedelta(minutes=5))
assert len(sent) == 1                                          # فترة الانتظار
back = main.votes_from_json(main.votes_to_json({"sniper": V("sniper", "SELL", 77, 3)}))
assert back["sniper"].direction == "SELL" and back["sniper"].confidence == 77
assert abs((NOW - back["sniper"].ts).total_seconds() - 180) < 1
# --- سجل النتائج ---
import journal
def mkdf(rows):
    ix = pd.date_range(start=NOW + timedelta(minutes=15), periods=len(rows), freq="15min")
    return pd.DataFrame({"High": [r[0] for r in rows], "Low": [r[1] for r in rows],
                         "Close": [r[2] for r in rows]}, index=ix)
def run(direction, rows, entry=2650.0):
    tr = build_trade(direction, entry, 5 / 1.5, 1.5, 1000)      # lot 0.02, SL 5
    st2 = {}
    journal.register(st2, tr, NOW)
    return journal.update_signals(st2, mkdf(rows), NOW + timedelta(hours=2)), st2
c, st2 = run("BUY", [(2656, 2651, 2655), (2661, 2655, 2660)])
assert c[0][1] == "TP2" and c[0][2] == 15.0, c                  # 5 + 10
c, _ = run("BUY", [(2651, 2644, 2645)])
assert c[0][1] == "SL" and c[0][2] == -10.0, c
c, _ = run("BUY", [(2656, 2651, 2655), (2653, 2649, 2650)])
assert c[0][1] == "TP1+BE" and c[0][2] == 5.0, c
c, _ = run("SELL", [(2649, 2644, 2645), (2645, 2639, 2640)])
assert c[0][1] == "TP2" and c[0][2] == 15.0, c
c, st3 = run("BUY", [(2652, 2649, 2651)])
assert c == [] and len(st3["open"]) == 1                        # لسا مفتوحة
print(journal.format_result(*run("BUY", [(2651, 2644, 2645)])[0][0], run("BUY", [(2651, 2644, 2645)])[1]["stats"]))
print(sent[0])
print("\n✅ كل الاختبارات نجحت")
