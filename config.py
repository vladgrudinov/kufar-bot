import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

# Telegram Settings (Kufar Sniper Bot)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9030767347:AAHy75DhjE17Ecy7ZsYhd0cOQmRj0wsXfUU")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "617898045")

# Polling Interval
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "25"))

# Monitored Categories on Kufar:
# 1. PC: Desktop computers (Системные блоки)
# 2. LAPTOPS: Gaming Laptops & MacBooks
# 3. CONSOLES: PS5, PS4, Xbox Series X/S, Steam Deck, Switch, ROG Ally
# 4. VIDEOCARDS: Standalone discrete GPUs (RTX 30/40/50, RX 6000/7000)
# 5. PHONES: Apple iPhone (11 - 16 Pro Max)
# 6. TABLETS: Apple iPad (Air, Pro, Mini)
# 7. MONITORS: Gaming high-hz monitors (144Hz–240Hz+)
CATEGORIES = [
    {
        "type": "PC",
        "name": "Игровые ПК",
        "url_params": {"cat": "16020", "size": "15", "sort": "lst.d"}
    },
    {
        "type": "LAPTOPS",
        "name": "Игровые Ноутбуки и MacBook",
        "url_params": {"cat": "16040", "celg": "1", "size": "15", "sort": "lst.d"}
    },
    {
        "type": "CONSOLES",
        "name": "Консоли (PS5 / Xbox / Steam Deck)",
        "url_params": {"cat": "5040", "cte": "1", "size": "15", "sort": "lst.d"}
    },
    {
        "type": "VIDEOCARDS",
        "name": "Топовые Видеокарты",
        "url_params": {"cat": "16010", "cct": "11", "size": "15", "sort": "lst.d"}
    },
    {
        "type": "PHONES",
        "name": "Смартфоны Apple iPhone",
        "url_params": {"cat": "17010", "phbr": "1", "size": "15", "sort": "lst.d"}
    },
    {
        "type": "TABLETS",
        "name": "Планшеты Apple iPad",
        "url_params": {"cat": "17050", "query": "iPad", "size": "15", "sort": "lst.d"}
    },
    {
        "type": "MONITORS",
        "name": "Игровые Мониторы 144Hz+",
        "url_params": {"cat": "16030", "cedg": "1", "size": "15", "sort": "lst.d"}
    }
]

MIN_PRICE_BYN = float(os.getenv("MIN_PRICE_BYN", "200.0"))
MAX_PRICE_BYN = float(os.getenv("MAX_PRICE_BYN", "6000.0"))
EXCLUDE_COMPANIES = os.getenv("EXCLUDE_COMPANIES", "true").lower() in ("true", "1", "yes")

# Profit & Thresholds (BYN)
MIN_PROFIT_BYN = float(os.getenv("MIN_PROFIT_BYN", "120.0"))
MIN_PROFIT_PERCENT = float(os.getenv("MIN_PROFIT_PERCENT", "15.0"))

# Negotiation Mode
AUTO_NEGOTIATE = os.getenv("AUTO_NEGOTIATE", "false").lower() in ("true", "1", "yes")
DEFAULT_DISCOUNT_PERCENT = float(os.getenv("DEFAULT_DISCOUNT_PERCENT", "16.0"))

# Storage paths
DB_PATH = BASE_DIR / "kufar_bot.db"
SESSION_DIR = BASE_DIR / "browser_session"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
