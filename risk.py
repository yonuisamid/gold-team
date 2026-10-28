import math
import config


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def build_trade(direction, price, atr, sl_mult=None, balance=None):
    """يحسب وقف الخسارة والأهداف وحجم اللوت. يرجع None إذا الرصيد صغير جداً."""
    balance = config.ACCOUNT_BALANCE if balance is None else balance
    sl_mult = sl_mult or config.ATR_MULT_DEFAULT
    sl_dist = clamp(atr * sl_mult, config.SL_MIN_USD, config.SL_MAX_USD)

    risk_target = balance * config.RISK_PCT / 100
    if config.FIXED_LOT > 0:
        lot = round(config.FIXED_LOT, 2)
        actual_risk = lot * sl_dist * config.CONTRACT_SIZE
    else:
        raw = risk_target / (sl_dist * config.CONTRACT_SIZE)
        lot = math.floor(raw / config.LOT_STEP + 1e-9) * config.LOT_STEP
        lot = round(max(lot, config.MIN_LOT), 2)
        actual_risk = lot * sl_dist * config.CONTRACT_SIZE
        if actual_risk > risk_target * config.MAX_RISK_OVERSHOOT:
            return None

    s = 1 if direction == "BUY" else -1
    partial = lot >= 2 * config.LOT_STEP
    lot_tp1 = round(math.floor(lot / 2 / config.LOT_STEP + 1e-9) * config.LOT_STEP, 2) if partial else 0.0
    return {
        "direction": direction,
        "entry": round(price, 2),
        "sl": round(price - s * sl_dist, 2),
        "sl_dist": round(sl_dist, 2),
        "tp1": round(price + s * sl_dist, 2),
        "tp2": round(price + s * sl_dist * config.RR, 2),
        "lot": lot,
        "lot_tp1": lot_tp1,
        "partial": partial,
        "risk_usd": round(actual_risk, 2),
        "risk_pct": round(actual_risk / balance * 100, 2),
    }
