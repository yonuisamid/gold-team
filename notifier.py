import config


def send(text):
    if not config.QUIET:
        print("\n" + text + "\n")
    if not (config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID):
        print("(تلكرام غير مفعّل: تأكد من ملف .env)")
        return
    import requests
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": config.TELEGRAM_CHAT_ID, "text": text}, timeout=15)
        if not r.ok:
            print("Telegram error:", r.status_code)
    except Exception as e:
        print("Telegram error:", type(e).__name__)
