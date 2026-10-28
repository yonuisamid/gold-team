import pandas as pd


def summarize(df):
    """ملخص فني من شموع 15 دقيقة (أعمدة Close/High/Low)."""
    c, h, l = df["Close"].astype(float), df["High"].astype(float), df["Low"].astype(float)
    ema20 = c.ewm(span=20, adjust=False).mean()
    ema50 = c.ewm(span=50, adjust=False).mean()

    delta = c.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + up / down.replace(0, 1e-9))

    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()

    last = float(c.iloc[-1])

    def chg(n):
        return round((last / float(c.iloc[-1 - n]) - 1) * 100, 3) if len(c) > n else None

    day = df.tail(96)
    return {
        "price": round(last, 2),
        "ema20": round(float(ema20.iloc[-1]), 2),
        "ema50": round(float(ema50.iloc[-1]), 2),
        "rsi14": round(float(rsi.iloc[-1]), 1),
        "atr14_usd": round(float(atr.iloc[-1]), 2),
        "change_1h_pct": chg(4),
        "change_4h_pct": chg(16),
        "high_24h": round(float(day["High"].max()), 2),
        "low_24h": round(float(day["Low"].min()), 2),
        "trend": "up" if ema20.iloc[-1] > ema50.iloc[-1] else "down",
    }
