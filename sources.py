import calendar
import re
from datetime import datetime, timezone

import config


def _clean(s, n=300):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()[:n]


def fetch_feeds(feeds):
    import feedparser
    out = []
    now = datetime.now(timezone.utc).timestamp()
    for f in feeds:
        try:
            d = feedparser.parse(f["url"], agent="Mozilla/5.0")
        except Exception as e:
            print("feed error", f["name"], e)
            continue
        for e in d.entries[:25]:
            ts = e.get("published_parsed")
            age = int((now - calendar.timegm(ts)) / 60) if ts else 0
            out.append({
                "id": e.get("id") or e.get("link") or e.get("title"),
                "title": _clean(e.get("title"), 200),
                "summary": _clean(e.get("summary"), 250),
                "source": f["name"], "tier": f["tier"], "age_min": max(age, 0),
            })
    return out


def x_search(query, source, tier):
    """اختياري: يحتاج X_BEARER_TOKEN (API مدفوع). بدونه يرجع قائمة فارغة."""
    if not config.X_BEARER_TOKEN:
        return []
    import requests
    try:
        r = requests.get(
            "https://api.x.com/2/tweets/search/recent",
            headers={"Authorization": f"Bearer {config.X_BEARER_TOKEN}"},
            params={"query": query, "max_results": 20, "tweet.fields": "created_at"},
            timeout=20)
        r.raise_for_status()
    except Exception as e:
        print("X error", e)
        return []
    out, now = [], datetime.now(timezone.utc)
    for t in r.json().get("data", []):
        created = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
        out.append({"id": "x" + t["id"], "title": _clean(t["text"], 280), "summary": "",
                    "source": source, "tier": tier,
                    "age_min": max(int((now - created).total_seconds() / 60), 0)})
    return out


def get_candles():
    import pandas as pd
    import yfinance as yf
    df = yf.download(config.PRICE_SYMBOL, period="5d", interval="15m",
                     progress=False, auto_adjust=True)
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()


def minutes_since_last_candle(df):
    import pandas as pd
    idx = df.index[-1]
    if idx.tzinfo is None:
        idx = idx.tz_localize("UTC")
    return (pd.Timestamp.now(tz="UTC") - idx).total_seconds() / 60
