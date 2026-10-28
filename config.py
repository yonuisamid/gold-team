"""كل الإعدادات هنا. عدّل الأرقام حسب رغبتك."""
import os
from urllib.parse import quote

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _f(name, default):
    return float(os.getenv(name) or default)


# ---------- المفاتيح (من ملف .env) ----------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")  # اختياري (API مدفوع)
QUIET = os.getenv("QUIET", "") == "1"  # لا تطبع نص الإشارة بالسجل (للمستودع العام)

# ---------- بيانات السعر ----------
PRICE_SYMBOL = "GC=F"      # عقود الذهب الآجلة (قريبة من XAUUSD)
STALE_MIN = 60             # إذا آخر شمعة أقدم من هذا = السوق مغلق

# ---------- الدورة ----------
LOOP_SECONDS = 300         # كل 5 دقائق
MAX_ITEM_AGE_MIN = 180     # تجاهل أخبار أقدم من 3 ساعات
MAX_ITEMS_PER_AGENT = 15

# ---------- الاتفاق ----------
MIN_CONFIDENCE = 65        # أقل ثقة لكل وكيل
VOTE_TTL_MIN = 30          # مدة صلاحية الصوت
PROFESSOR_RECHECK_MIN = 10 # أقل فاصل بين فحصين للبروفيسور
COOLDOWN_MIN = 60          # فاصل بعد كل إشارة
MAX_SIGNALS_PER_DAY = 3
# أوقات أخبار عالية التأثير (UTC) تدخلها يدوياً: FOMC, CPI, NFP ...
BLACKOUT_UTC = []          # مثال: ["2026-11-05T19:00", "2026-12-04T13:30"]
BLACKOUT_WINDOW_MIN = 30

# ---------- المخاطرة ----------
ACCOUNT_BALANCE = _f("ACCOUNT_BALANCE", "100")
RISK_PCT = 1.0             # % من الرصيد لكل صفقة (يُهمل إذا FIXED_LOT > 0)
FIXED_LOT = _f("FIXED_LOT", "0.01")  # لوت ثابت؛ ضعه 0 ليُحسب اللوت من المخاطرة
ATR_MULT_DEFAULT = 1.5     # وقف الخسارة = ATR × هذا الرقم
SL_MIN_USD = 3.0
SL_MAX_USD = 15.0
RR = 2.0                   # الهدف الثاني = 2 × المخاطرة
CONTRACT_SIZE = 100        # أونصة لكل 1 لوت (تأكد من وسيطك)
MIN_LOT = 0.01
LOT_STEP = 0.01
MAX_RISK_OVERSHOOT = 2.0   # إذا أصغر لوت يخاطر أكثر من ضعف الهدف = لا صفقة


# ---------- مصادر الأخبار ----------
def gnews(q):
    return ("https://news.google.com/rss/search?q=" + quote(q)
            + "&hl=en-US&gl=US&ceid=US:en")


# tier 1 = تأثير مباشر، tier 2 = ثانوي
SNIPER_FEEDS = [
    {"name": "Fed", "tier": 1, "url": "https://www.federalreserve.gov/feeds/press_all.xml"},
    {"name": "Trump", "tier": 1, "url": gnews("Trump (tariffs OR Fed OR dollar OR Iran OR sanctions) when:1d")},
    {"name": "Treasury", "tier": 1, "url": gnews("Treasury Secretary OR \"US Treasury\" when:1d")},
    {"name": "WhiteHouse", "tier": 2, "url": gnews("\"White House\" (executive order OR sanctions OR tariffs) when:1d")},
    {"name": "CentralBanks", "tier": 2, "url": gnews("(ECB OR PBoC OR \"Bank of Japan\" OR \"Bank of England\") gold OR rates when:1d")},
]
DETECTIVE_FEEDS = [
    {"name": "GoldNews", "tier": 1, "url": gnews("gold price when:1d")},
    {"name": "XAUUSD", "tier": 1, "url": gnews("XAUUSD when:1d")},
    {"name": "SafeHaven", "tier": 2, "url": gnews("gold safe haven demand when:1d")},
    {"name": "CBGold", "tier": 2, "url": gnews("central bank gold buying when:1d")},
]

# X (اختياري، يحتاج X_BEARER_TOKEN)
X_SNIPER_QUERY = "(from:federalreserve OR from:realDonaldTrump OR from:USTreasury OR from:WhiteHouse) -is:retweet"
X_DETECTIVE_QUERY = "(gold OR XAUUSD) lang:en -is:retweet"
