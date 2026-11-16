import os
import sys
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# UTF-8 encoding support
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
from db import init_db, get_connection
from kufar_scanner import KufarScanner
from telegram_app import TelegramNotifier, MAIN_MENU_KEYBOARD
from negotiation_strategy import generate_first_offer_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("cloud_bot")

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(b'{"status": "ok", "service": "kufar_pc_sniper_bot", "mode": "24/7_cloud"}')

    def log_message(self, format, *args):
        # Silence standard HTTP access logs
        return

def run_health_server(port: int):
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logger.info(f"Health check web server running on port {port}...")
    httpd.serve_forever()

def bot_worker():
    logger.info("Initializing Cloud Kufar Sniper...")
    init_db()
    scanner = KufarScanner()
    telegram = TelegramNotifier()

    bot_state = {
        "paused": False,
        "auto_negotiate": AUTO_NEGOTIATE,
        "poll_interval": POLL_INTERVAL_SECONDS
    }

    startup_msg = (
        "☁️ <b>Kufar Sniper Bot успешно запущен в ОБЛАКЕ 24/7!</b>\n\n"
        "⚡ Ваш компьютер теперь может спать или быть выключен — бот работает на удаленном сервере непрерывно!\n\n"
        f"🔍 Сканирование: каждые {POLL_INTERVAL_SECONDS} сек.\n"
        "📱 Все находки приходят прямо сюда с быстрыми ссылками."
    )
    telegram.send_message(startup_msg, reply_markup=MAIN_MENU_KEYBOARD)

    cf_warned = False
    while True:
        try:
            # 1. Check Telegram commands (basic status/pause/resume/deals)
            process_simple_updates(telegram, bot_state)

            # 2. Scan if not paused
            if not bot_state.get("paused"):
                # Test connectivity to Kufar
                test_ads = scanner.fetch_category_ads(CATEGORIES[0])
                if test_ads is None or (len(test_ads) == 0 and not cf_warned):
                    # Check if blocked by Cloudflare
                    try:
                        r = scanner.session.get(scanner.search_url, params={"cat": "16020", "lang": "ru"}, timeout=10)
                        if r.status_code == 403 and not cf_warned:
                            cf_warned = True
                            telegram.send_message("⚠️ <b>Внимание:</b> Облачный сервер Render (Германия) заблокирован защитой Cloudflare Куфара (HTTP 403 Forbidden). Запросы с иностранных дата-центров блокируются.")
                    except Exception:
                        pass

                deals = scanner.scan_for_deals()
                for deal in deals:
                    telegram.send_deal_alert(deal)

        except Exception as e:
            logger.error(f"Error in cloud bot loop: {e}")

        # Sleep interval while checking updates
        for _ in range(bot_state.get("poll_interval", 25)):
            try:
                process_simple_updates(telegram, bot_state)
            except Exception:
                pass
            time.sleep(1)

def process_simple_updates(telegram: TelegramNotifier, bot_state: dict):
    url = f"{telegram.base_url}/getUpdates"
    params = {"offset": telegram.last_update_id + 1, "timeout": 1}
    try:
        import requests
        resp = requests.get(url, params=params, timeout=4)
        if resp.status_code != 200:
            return
        data = resp.json()
        for update in data.get("result", []):
            telegram.last_update_id = update["update_id"]
            if "message" in update:
                msg = update["message"]
                text = (msg.get("text") or "").strip().lower()
                if text in ("/start", "/menu", "меню"):
                    telegram.send_message("👋 Бот активен в облаке 24/7. Отправьте /status для проверки.", reply_markup=MAIN_MENU_KEYBOARD)
                elif text in ("/status", "📊 статус бота"):
                    with get_connection() as conn:
                        total = conn.execute("SELECT COUNT(*) FROM ads").fetchone()[0]
                        prof = conn.execute("SELECT COUNT(*) FROM ads WHERE status = 'PROFITABLE'").fetchone()[0]
                    telegram.send_message(
                        f"☁️ <b>СТАТУС ОБЛАЧНОГО БОТА:</b>\n\n"
                        f"• Сервер: <b>В сети 24/7</b>\n"
                        f"• Состояние: <b>{'⏸ Пауза' if bot_state['paused'] else '🟢 Активно ищет'}</b>\n"
                        f"• Всего лотов: <code>{total}</code>\n"
                        f"• Выгодных находок: <code>{prof}</code>"
                    )
                elif text in ("/pause", "⏸ пауза", "⏸ пауза / пуск"):
                    bot_state["paused"] = not bot_state.get("paused", False)
                    telegram.send_message(f"<b>{'⏸ Бот поставлен на паузу' if bot_state['paused'] else '🟢 Бот возобновил поиск'}</b>")
                elif text in ("/deals", "💎 последние выгодные пк"):
                    with get_connection() as conn:
                        rows = conn.execute("SELECT title, price_byn, profit_byn, ad_link FROM ads WHERE status='PROFITABLE' ORDER BY profit_byn DESC LIMIT 5").fetchall()
                    if rows:
                        t = "💎 <b>ПОСЛЕДНИЕ НАХОДКИ:</b>\n\n"
                        for r in rows:
                            t += f"• <a href=\"{r['ad_link']}\">{r['title'][:40]}</a>\n  Цена: {r['price_byn']} BYN | Выгода: +{r['profit_byn']} BYN\n\n"
                        telegram.send_message(t)
    except Exception as e:
        logger.debug(f"Update error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # Start bot in background thread
    t = threading.Thread(target=bot_worker, daemon=True)
    t.start()
    # Keep web server on main thread for cloud platform keep-alive
    run_health_server(port)
