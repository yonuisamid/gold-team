import json
import re
from datetime import datetime

import config
from models import Vote

_client = None


def parse_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in model output")
    return json.loads(m.group(0))


def ask_json(system, user):
    global _client
    import anthropic
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = _client.messages.create(
        model=config.MODEL, max_tokens=700, system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return parse_json(text)


def to_vote(agent, data, now=None):
    d = str(data.get("direction", "NEUTRAL")).upper().strip()
    if d not in ("BUY", "SELL", "NEUTRAL"):
        d = "NEUTRAL"
    try:
        conf = int(max(0, min(100, float(data.get("confidence", 0)))))
    except (TypeError, ValueError):
        conf = 0
    try:
        mult = float(data.get("sl_atr_mult", config.ATR_MULT_DEFAULT))
    except (TypeError, ValueError):
        mult = config.ATR_MULT_DEFAULT
    mult = max(1.0, min(2.5, mult))
    return Vote(agent, d, conf, str(data.get("reason_ar", ""))[:300],
                now or datetime.now(), mult)
