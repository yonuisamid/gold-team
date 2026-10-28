from dataclasses import dataclass
from datetime import datetime


@dataclass
class Vote:
    agent: str
    direction: str        # BUY / SELL / NEUTRAL
    confidence: int       # 0-100
    reason: str
    ts: datetime
    sl_atr_mult: float = 1.5
