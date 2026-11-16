import os
import re
import json
import logging
import requests
import sys
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from db import get_ad, update_ad_status, get_connection
from negotiation_strategy import generate_first_offer_message
try:
    from browser_negotiator import BrowserNegotiator
except Exception:
    BrowserNegotiator = None

logger = logging.getLogger("telegram_app")

MAIN_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "📊 Статус бота"}, {"text": "🔑 Авторизоваться с телефона"}],
        [{"text": "🔄 Переключить режим торга"}, {"text": "⏸ Пауза / Пуск"}],
        [{"text": "💎 Последние выгодные ПК"}, {"text": "📸 Скриншот профиля Куфар"}]
    ],
    "resize_keyboard": True
}

class TelegramNotifier:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0

    def send_message(self, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """Sends HTML formatted message to the user."""
        if not self.token or not self.chat_id:
            logger.warning("Telegram token or chat_id not configured!")
            return None
            
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
            
        try:
            resp = requests.post(url, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("result", {}).get("message_id")
            else:
                logger.error(f"Telegram error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
        return None

    def send_photo(self, photo_path: str, caption: str = ""):
        """Sends photo or screenshot to the user."""
        if not os.path.exists(photo_path):
            return
            
        url = f"{self.base_url}/sendPhoto"
        try:
            with open(photo_path, "rb") as f:
                requests.post(
                    url,
                    data={"chat_id": self.chat_id, "caption": caption, "parse_mode": "HTML"},
                    files={"photo": f},
                    timeout=25
                )
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")

    def send_deal_alert(self, deal: Dict[str, Any]):
        """Formats and sends a high-profit tech alert with action buttons."""
        ad_id = str(deal["ad_id"])
        title = deal.get("title", "")
        category_title = deal.get("category_title", "🖥️ Топовая Техника")
        price_byn = deal.get("price_byn", 0)
        market_val = deal.get("market_value", 0)
        profit_byn = deal.get("profit_byn", 0)
        profit_pct = deal.get("profit_percent", 0)
        offer_price = int(deal.get("recommended_offer", 0))
        link = deal.get("ad_link", f"https://www.kufar.by/item/{ad_id}")
        
        cpu = deal.get("cpu", "-")
        gpu = deal.get("gpu", "-")
        ram = deal.get("ram", "-")
        storage = deal.get("storage", "-")
        warnings = deal.get("warnings", "Нет")
        
        offer_msg = generate_first_offer_message(deal, custom_offer_price=offer_price)

        # Build specs section if available
        specs_lines = []
        if cpu and cpu != "-":
            specs_lines.append(f" • Процессор: <code>{cpu}</code>")
        if gpu and gpu != "-":
            specs_lines.append(f" • Видеокарта: <code>{gpu}</code>")
        if ram and ram != "-":
            specs_lines.append(f" • Оперативка: <code>{ram}</code>")
        if storage and storage != "-":
            specs_lines.append(f" • Накопитель: <code>{storage}</code>")
        specs_block = "\n".join(specs_lines) if specs_lines else " • Модель распознана автоматически"

        text = (
            f"🔥 <b>ВЫГОДНОЕ ПРЕДЛОЖЕНИЕ: {category_title}!</b>\n\n"
            f"📦 <b><a href=\"{link}\">{title}</a></b>\n\n"
            f"💵 <b>Цена продавца:</b> <code>{price_byn:,.0f} BYN</code>\n"
            f"📊 <b>Оценочная стоимость:</b> <code>{market_val:,.0f} BYN</code>\n"
            f"💰 <b>Чистая выгода:</b> <b>+{profit_byn:,.0f} BYN (+{profit_pct:.1f}%)</b>\n"
            f"🎯 <b>Рекомендуемый торг:</b> <code>{offer_price:,.0f} BYN</code>\n\n"
            f"⚙️ <b>Характеристики:</b>\n{specs_block}\n\n"
            f"⚠️ <b>Анализ рисков / проверка:</b> {warnings}\n\n"
            f"💬 <b>Текст для торга:</b>\n<i>«{offer_msg}»</i>"
        )

        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": f"🚀 Торговаться за {offer_price} BYN",
                        "callback_data": f"offer:{ad_id}:{offer_price}"
                    }
                ],
                [
                    {
                        "text": f"📉 Торговаться за {int(offer_price * 0.9)} BYN",
                        "callback_data": f"offer:{ad_id}:{int(offer_price * 0.9)}"
                    },
                    {
                        "text": "❌ Пропустить",
                        "callback_data": f"skip:{ad_id}"
                    }
                ],
                [
                    {
                        "text": "🔗 Открыть на Kufar.by",
                        "url": link
                    }
                ]
            ]
        }

        self.send_message(text, reply_markup=reply_markup)

    def process_telegram_updates(self, negotiator: BrowserNegotiator, bot_state: Dict[str, Any]):
        """Polls and executes Telegram commands and interactive button clicks."""
        url = f"{self.base_url}/getUpdates"
        params = {"offset": self.last_update_id + 1, "timeout": 2}
        
        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code != 200:
                return
                
            data = resp.json()
            for update in data.get("result", []):
                self.last_update_id = update["update_id"]
                
                # 1. Handle Inline Button Clicks
                if "callback_query" in update:
                    cb = update["callback_query"]
                    cb_id = cb["id"]
                    cb_data = cb.get("data", "")
                    
                    requests.post(f"{self.base_url}/answerCallbackQuery", json={"callback_query_id": cb_id})
                    
                    if cb_data.startswith("skip:"):
                        ad_id = cb_data.split(":")[1]
                        update_ad_status(ad_id, "SKIPPED")
                        self.send_message(f"❌ Объявление #{ad_id} помечено как пропущенное.")
                        
                    elif cb_data.startswith("req_sms:"):
                        phone_to_req = cb_data.split(":", 1)[1]
                        self.send_message(f"⏳ Открываю Куфар и высылаю SMS на номер <b>{phone_to_req}</b>...")
                        res = negotiator.request_sms_code(phone_to_req)
                        if res.get("success"):
                            self.send_message(
                                f"📩 <b>SMS / Viber код отправлен на {phone_to_req}!</b>\n\n"
                                f"Просто <b>напишите 4 цифры сюда в чат</b> (например: <code>1234</code>):"
                            )
                        else:
                            self.send_message(f"❌ Ошибка запроса кода: {res.get('error')}")

                    elif cb_data.startswith("offer:"):
                        parts = cb_data.split(":")
                        ad_id = parts[1]
                        offer_price = float(parts[2])
                        
                        ad = get_ad(ad_id)
                        if not ad:
                            self.send_message(f"⚠️ Объявление #{ad_id} не найдено в базе данных.")
                            continue
                            
                        self.send_message(f"⏳ Отправляю сообщение продавцу по объявлению #{ad_id} с ценой <b>{int(offer_price)} BYN</b>...")
                        
                        offer_msg = generate_first_offer_message(ad, custom_offer_price=offer_price)
                        res = negotiator.send_negotiation_message(ad_id, offer_msg, offer_price)
                        
                        if res.get("success"):
                            self.send_message(
                                f"✅ <b>Сообщение успешно отправлено продавцу!</b>\n\n"
                                f"Текст: <i>«{offer_msg}»</i>\n\n"
                                f"Бот ожидает ответ продавца."
                            )
                            if res.get("screenshot"):
                                self.send_photo(res["screenshot"], caption=f"📸 Подтверждение отправки по #{ad_id}")
                        else:
                            err = res.get("error", "Неизвестная ошибка")
                            self.send_message(f"❌ Не удалось отправить сообщение: <b>{err}</b>")
                            if res.get("screenshot"):
                                self.send_photo(res["screenshot"], caption="Скриншот экрана ошибки")

                # 2. Handle Text Commands & Menu Buttons
                elif "message" in update:
                    msg = update["message"]
                    text = (msg.get("text") or "").strip().lower()
                    
                    # Handle document upload (portable session file)
                    if "document" in msg:
                        doc = msg["document"]
                        file_name = doc.get("file_name", "")
                        if "session" in file_name or "auth" in file_name or file_name.endswith(".json"):
                            file_id = doc.get("file_id")
                            f_info = requests.get(f"{self.base_url}/getFile?file_id={file_id}").json()
                            f_path = f_info.get("result", {}).get("file_path")
                            if f_path:
                                down_url = f"https://api.telegram.org/file/bot{self.token}/{f_path}"
                                f_content = requests.get(down_url).content
                                target_path = BASE_DIR / "auth_storage_state.json"
                                with open(target_path, "wb") as f:
                                    f.write(f_content)
                                self.send_message("✅ <b>Файл сессии успешно принят и сохранен на сервере!</b>")
                            continue

                    if not text:
                        continue

                    if text in ("/start", "/menu", "меню"):
                        menu_text = (
                            "👋 <b>Панель управления Kufar Sniper</b>\n\n"
                            "Используйте кнопки внизу или команды:\n"
                            "• <b>/status</b> — Состояние бота, статистика и сессия\n"
                            "• <b>/login</b> — Авторизоваться на Куфаре прямо с телефона\n"
                            "• <b>/mode</b> — Переключить автопилот / полуавтомат\n"
                            "• <b>/pause</b> / <b>/resume</b> — Приостановить или возобновить\n"
                            "• <b>/deals</b> — Показать последние выгодные находки\n"
                            "• <b>/screenshot</b> — Проверить экран браузера на сервере"
                        )
                        self.send_message(menu_text, reply_markup=MAIN_MENU_KEYBOARD)

                    elif text in ("/login", "🔑 авторизоваться с телефона", "🔑 войти на куфар"):
                        self.send_message(
                            "🔐 <b>АВТОРИЗАЦИЯ НА КУФАРЕ С ТЕЛЕФОНА:</b>\n\n"
                            "Нажмите кнопку ниже, чтобы Куфар выслал 4-значный код на ваш номер:\n"
                            "<code>+375 (33) 371-57-69</code>",
                            reply_markup={
                                "inline_keyboard": [
                                    [
                                        {
                                            "text": "📩 Получить SMS-код",
                                            "callback_data": "req_sms:+375333715769"
                                        }
                                    ]
                                ]
                            }
                        )

                    elif text.startswith("/sms "):
                        phone_val = text.split(" ", 1)[1].strip()
                        self.send_message(f"⏳ Открываю Куфар и запрашиваю SMS-код на номер <b>{phone_val}</b>...")
                        res = negotiator.request_sms_code(phone_val)
                        if res.get("success"):
                            self.send_message(
                                f"📩 <b>SMS-код запрошен!</b>\n"
                                f"Просто <b>напишите 4 цифры сюда в чат</b>:"
                            )
                        else:
                            self.send_message(f"❌ Не удалось запросить код: {res.get('error')}")

                    elif text.startswith("/code ") or (text.isdigit() and len(text) == 4) or re.search(r'\b\d{4}\b', text):
                        match = re.search(r'\b\d{4}\b', text)
                        code_val = match.group(0) if match else text.replace("/code", "").strip()
                        self.send_message(f"⏳ Ввожу 4-значный код <b>{code_val}</b> на Куфаре...")
                        res = negotiator.submit_sms_code(code_val)
                        if res.get("success"):
                            self.send_message("🎉 <b>УСПЕШНЫЙ ВХОД В АККАУНТ КУФАРА!</b>\n\nСессия сохранена. Теперь кнопки торга будут автоматически отправлять ваши сообщения продавцам!")
                            if res.get("screenshot"):
                                self.send_photo(res["screenshot"], caption="📸 Экран подтверждения входа")
                        else:
                            self.send_message(f"❌ <b>Ошибка входа:</b> {res.get('error')}")
                            if res.get("screenshot"):
                                self.send_photo(res["screenshot"], caption="📸 Экран ошибки входа")

                    elif text.startswith("/auth "):
                        parts = text.split(" ", 2)
                        if len(parts) < 3:
                            self.send_message("⚠️ Неверный формат. Используйте: <code>/auth логин пароль</code>")
                            continue
                        login_val = parts[1].strip()
                        pass_val = parts[2].strip()
                        self.send_message("⏳ Вхожу в ваш аккаунт на Kufar.by...")
                        res = negotiator.login_with_credentials(login_val, pass_val)
                        if res.get("success"):
                            self.send_message("✅ <b>Успешный вход в аккаунт Куфара!</b>\nСессия сохранена. Теперь торг в 1 клик работает прямо с телефона.")
                            if res.get("screenshot"):
                                self.send_photo(res["screenshot"], caption="📸 Подтверждение входа")
                        else:
                            err = res.get("error", "Ошибка входа")
                            self.send_message(f"❌ <b>Ошибка входа:</b> {err}")
                            if res.get("screenshot"):
                                self.send_photo(res["screenshot"], caption="Экран после попытки входа")

                    elif text in ("/status", "📊 статус бота"):
                        with get_connection() as conn:
                            total_ads = conn.execute("SELECT COUNT(*) FROM ads").fetchone()[0]
                            profitable_ads = conn.execute("SELECT COUNT(*) FROM ads WHERE status = 'PROFITABLE'").fetchone()[0]
                            offers_sent = conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]

                        mode_name = "🤖 Полный автопилот (сразу пишет продавцам)" if bot_state.get("auto_negotiate") else "✋ Полуавтомат (кнопки в Telegram)"
                        status_name = "⏸ На паузе" if bot_state.get("paused") else "🟢 Активно сканирует Kufar 24/7"

                        status_text = (
                            f"📊 <b>ТЕКУЩИЙ СТАТУС БОТА:</b>\n\n"
                            f"• Состояние: <b>{status_name}</b>\n"
                            f"• Режим торга: <b>{mode_name}</b>\n"
                            f"• Всего отсканировано объявлений: <code>{total_ads}</code>\n"
                            f"• Найдено выгодных предложений: <code>{profitable_ads}</code>\n"
                            f"• Отправлено предложений продавцам: <code>{offers_sent}</code>\n"
                            f"• Интервал сканирования: <code>{bot_state.get('poll_interval', 25)} сек</code>"
                        )
                        self.send_message(status_text)

                    elif text in ("/mode", "🔄 переключить режим торга"):
                        bot_state["auto_negotiate"] = not bot_state.get("auto_negotiate", False)
                        new_mode = "🤖 Полный автопилот" if bot_state["auto_negotiate"] else "✋ Полуавтомат (с кнопками в Telegram)"
                        self.send_message(f"🔄 <b>Режим торга изменен на:</b> <code>{new_mode}</code>")

                    elif text in ("/pause", "⏸ пауза"):
                        bot_state["paused"] = True
                        self.send_message("⏸ <b>Сканирование приостановлено.</b> Напишите /resume или нажмите 'Пауза / Пуск' для продолжения.")

                    elif text in ("/resume", "▶ возобновить"):
                        bot_state["paused"] = False
                        self.send_message("🟢 <b>Сканирование возобновлено!</b> Бот снова отслеживает объявления 24/7.")

                    elif text in ("⏸ пауза / пуск",):
                        bot_state["paused"] = not bot_state.get("paused", False)
                        st = "⏸ Сканирование приостановлено." if bot_state["paused"] else "🟢 Сканирование запущено!"
                        self.send_message(f"<b>{st}</b>")

                    elif text in ("/screenshot", "📸 скриншот профиля куфар"):
                        self.send_message("📸 Делаю скриншот профиля Куфара в браузере...")
                        shot = negotiator.capture_status_screenshot()
                        if shot and os.path.exists(shot):
                            self.send_photo(shot, caption="📸 Текущее состояние браузера на сервере")
                        else:
                            self.send_message("❌ Не удалось сделать скриншот.")

                    elif text in ("/deals", "💎 последние выгодные пк"):
                        with get_connection() as conn:
                            rows = conn.execute("""
                                SELECT ad_id, title, price_byn, market_value, profit_byn, profit_percent, ad_link 
                                FROM ads 
                                WHERE status IN ('PROFITABLE', 'OFFER_SENT') 
                                ORDER BY profit_byn DESC LIMIT 5
                            """).fetchall()

                        if not rows:
                            self.send_message("ℹ️ Пока нет сохраненных выгодных ПК в базе.")
                        else:
                            deals_text = "💎 <b>ТОП ПОСЛЕДНИХ ВЫГОДНЫХ ПК:</b>\n\n"
                            for r in rows:
                                deals_text += (
                                    f"• <b><a href=\"{r['ad_link']}\">{r['title'][:40]}</a></b>\n"
                                    f"  Цена: <code>{r['price_byn']:.0f} BYN</code> | "
                                    f"Выгода: <b>+{r['profit_byn']:.0f} BYN (+{r['profit_percent']:.0f}%)</b>\n\n"
                                )
                            self.send_message(deals_text)

        except Exception as e:
            logger.debug(f"Telegram updates exception: {e}")
