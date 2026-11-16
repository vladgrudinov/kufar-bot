import sys
import time
import logging
from pathlib import Path

# Fix Windows console UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import (
    POLL_INTERVAL_SECONDS,
    AUTO_NEGOTIATE,
    MIN_PROFIT_BYN,
    MIN_PROFIT_PERCENT,
    MIN_PRICE_BYN,
    MAX_PRICE_BYN
)
from db import init_db
from kufar_scanner import KufarScanner
from browser_negotiator import BrowserNegotiator
from telegram_app import TelegramNotifier, MAIN_MENU_KEYBOARD
from negotiation_strategy import generate_first_offer_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / "kufar_bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("main")

def main():
    logger.info("Starting Kufar PC Sniper & Negotiator Bot...")
    init_db()

    scanner = KufarScanner()
    negotiator = BrowserNegotiator(headless=True)
    telegram = TelegramNotifier()

    bot_state = {
        "paused": False,
        "auto_negotiate": AUTO_NEGOTIATE,
        "poll_interval": POLL_INTERVAL_SECONDS
    }

    startup_text = (
        "🤖 <b>Kufar PC Sniper & Negotiator успешно запущен 24/7!</b>\n\n"
        f"🔍 <b>Мониторинг:</b> Категория 'Системные блоки' (каждые {POLL_INTERVAL_SECONDS} сек)\n"
        f"💵 <b>Фильтр цен:</b> от {int(MIN_PRICE_BYN)} до {int(MAX_PRICE_BYN)} BYN\n"
        f"📈 <b>Мин. выгода:</b> от +{int(MIN_PROFIT_BYN)} BYN (или от +{int(MIN_PROFIT_PERCENT)}%)\n"
        f"🤖 <b>Режим торга:</b> {'ВКЛЮЧЕН (Full Auto)' if bot_state['auto_negotiate'] else 'ПОЛУАВТОМАТ (кнопка в 1 клик)'}\n\n"
        "<i>Используйте кнопки меню внизу для управления ботом прямо из чата!</i>"
    )
    telegram.send_message(startup_text, reply_markup=MAIN_MENU_KEYBOARD)
    
    print("\n" + "="*60)
    print(f"✅ БОТ РАБОТАЕТ В РЕЖИМЕ 24/7!")
    print(f"📱 Полное управление доступно прямо из Telegram.")
    print("="*60 + "\n")

    last_chat_check = 0

    try:
        while True:
            # 1. Process incoming Telegram messages & button clicks
            telegram.process_telegram_updates(negotiator, bot_state)

            # 2. If not paused, scan for deals
            if not bot_state.get("paused"):
                logger.info("Scanning Kufar for new listings...")
                profitable_deals = scanner.scan_for_deals()

                for deal in profitable_deals:
                    ad_id = str(deal["ad_id"])
                    
                    if bot_state.get("auto_negotiate"):
                        offer_price = float(deal.get("recommended_offer", 0))
                        offer_msg = generate_first_offer_message(deal, custom_offer_price=offer_price)
                        logger.info(f"Auto-negotiating for ad {ad_id} at {offer_price} BYN...")
                        
                        telegram.send_deal_alert(deal)
                        telegram.send_message(f"⏳ Отправляю автоматический оффер на {int(offer_price)} BYN...")
                        
                        res = negotiator.send_negotiation_message(ad_id, offer_msg, offer_price)
                        if res.get("success"):
                            telegram.send_message(f"✅ Оффер на <b>{int(offer_price)} BYN</b> успешно отправлен продавцу!")
                            if res.get("screenshot"):
                                telegram.send_photo(res["screenshot"])
                        else:
                            telegram.send_message(f"⚠️ Ошибка отправки оффера: {res.get('error')}")
                    else:
                        # Semi-automatic mode: send alert with Telegram inline buttons
                        telegram.send_deal_alert(deal)

            # 3. Check for seller replies in Kufar inbox every 3 minutes
            now = time.time()
            if now - last_chat_check > 180 and not bot_state.get("paused"):
                last_chat_check = now
                try:
                    inbox_status = negotiator.check_chat_inbox()
                    if inbox_status.get("has_unread"):
                        telegram.send_message(
                            f"📩 <b>Внимание!</b> Продавец ответил в чате Куфара!\n"
                            f"Новых непрочитанных сообщений: {inbox_status.get('unread_count')}\n"
                            f"<a href=\"https://www.kufar.by/chat\">Перейти в сообщения на Kufar</a>"
                        )
                except Exception as e:
                    logger.debug(f"Inbox check error: {e}")

            # Sleep interval while continuing to poll Telegram button clicks
            for _ in range(bot_state.get("poll_interval", 25)):
                telegram.process_telegram_updates(negotiator, bot_state)
                time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
        telegram.send_message("🛑 <b>Kufar PC Sniper остановлен.</b>")

if __name__ == "__main__":
    main()
