import os
import time
import logging
import sys
import re
from pathlib import Path
from typing import Dict, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright, BrowserContext, Page
from config import SESSION_DIR
from db import record_offer, update_ad_status

logger = logging.getLogger("browser_negotiator")
SCREENSHOTS_DIR = SESSION_DIR.parent / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

class BrowserNegotiator:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.session_dir = str(SESSION_DIR)
        self._login_pw = None
        self._login_ctx = None
        self._login_page = None

    def request_sms_code(self, phone_str: str) -> Dict[str, Any]:
        """Opens login modal on Kufar, enters phone, and requests 4-digit SMS/Viber code."""
        shot_path = SCREENSHOTS_DIR / "sms_requested.png"
        try:
            # Clean up any lingering login context
            if self._login_ctx:
                try: self._login_ctx.close()
                except Exception: pass
            if self._login_pw:
                try: self._login_pw.stop()
                except Exception: pass

            self._login_pw = sync_playwright().start()
            self._login_ctx = self._login_pw.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=True,
                viewport={"width": 1280, "height": 850},
                args=["--disable-blink-features=AutomationControlled"]
            )
            self._login_page = self._login_ctx.pages[0] if self._login_ctx.pages else self._login_ctx.new_page()
            
            logger.info("Opening Kufar to request SMS code...")
            self._login_page.goto("https://www.kufar.by/", timeout=35000)
            self._login_page.wait_for_timeout(2000)

            # Accept cookies
            try:
                cb = self._login_page.query_selector('button:has-text("Принять"), button:has-text("Согласен")')
                if cb and cb.is_visible():
                    cb.click()
                    self._login_page.wait_for_timeout(500)
            except Exception:
                pass

            # Click login button
            for b in self._login_page.query_selector_all('button, a'):
                if 'войти' in (b.inner_text() or '').strip().lower():
                    b.click()
                    break

            self._login_page.wait_for_timeout(2000)

            # Switch to "Вход по коду"
            switch_btn = self._login_page.query_selector('button:has-text("Вход по коду")')
            if switch_btn and switch_btn.is_visible():
                switch_btn.click()
                self._login_page.wait_for_timeout(1500)

            phone_inp = self._login_page.query_selector('input[name="phone"]')
            if not phone_inp:
                self._login_page.screenshot(path=str(shot_path))
                return {"success": False, "error": "Поле ввода номера телефона не найдено", "screenshot": str(shot_path)}

            # Clean phone to 9 digits (e.g. 333715769)
            clean_digits = re.sub(r'\D', '', phone_str)
            if clean_digits.startswith("375"):
                clean_digits = clean_digits[3:]
            elif clean_digits.startswith("80"):
                clean_digits = clean_digits[2:]

            formatted = f"+375 ({clean_digits[:2]}) {clean_digits[2:5]} {clean_digits[5:7]} {clean_digits[7:]}"

            # Set phone using native setter for React masked input
            self._login_page.evaluate('''(args) => {
                const [el, val] = args;
                function setNativeValue(element, value) {
                    const valueSetter = Object.getOwnPropertyDescriptor(element, 'value')?.set;
                    const prototype = Object.getPrototypeOf(element);
                    const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;
                    if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {
                        prototypeValueSetter.call(element, value);
                    } else if (valueSetter) {
                        valueSetter.call(element, value);
                    } else {
                        element.value = value;
                    }
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                }
                setNativeValue(el, val);
            }''', [phone_inp, formatted])

            self._login_page.wait_for_timeout(600)

            # Click "Получить код"
            get_btn = self._login_page.query_selector('button:has-text("Получить код")')
            if get_btn and not get_btn.is_disabled():
                get_btn.click()
                logger.info("Clicked 'Получить код'. Waiting for 4 code boxes...")
                self._login_page.wait_for_timeout(3500)
            else:
                self._login_page.screenshot(path=str(shot_path))
                return {"success": False, "error": "Кнопка 'Получить код' не активна (проверьте номер)", "screenshot": str(shot_path)}

            self._login_page.screenshot(path=str(shot_path))
            return {"success": True, "screenshot": str(shot_path)}

        except Exception as e:
            logger.error(f"Error requesting SMS code: {e}")
            return {"success": False, "error": str(e)}

    def submit_sms_code(self, code_str: str) -> Dict[str, Any]:
        """Enters the 4 digits into the active open code boxes and confirms login."""
        shot_path = SCREENSHOTS_DIR / "login_result.png"
        if not self._login_page:
            return {"success": False, "error": "Сначала нажмите кнопку 'Запросить SMS-код'"}

        try:
            clean_code = re.sub(r'\D', '', code_str)
            logger.info(f"Submitting 4-digit code: {clean_code}...")

            boxes = self._login_page.query_selector_all('input[type="tel"], input[maxlength="1"], input[inputmode="numeric"]')
            if len(boxes) >= 4 and len(clean_code) >= 4:
                for idx, digit in enumerate(clean_code[:4]):
                    boxes[idx].click()
                    boxes[idx].fill(digit)
                    self._login_page.wait_for_timeout(150)
            else:
                inp = (
                    self._login_page.query_selector('input[name="code"]') or
                    self._login_page.query_selector('input[placeholder*="код"]') or
                    self._login_page.query_selector('input[type="tel"]') or
                    self._login_page.query_selector('input[type="text"]')
                )
                if inp:
                    inp.fill(clean_code)

            self._login_page.wait_for_timeout(2000)

            # Check if there is a confirm button
            confirm_btn = (
                self._login_page.query_selector('button:has-text("Подтвердить")') or
                self._login_page.query_selector('button:has-text("Продолжить")') or
                self._login_page.query_selector('button:has-text("Войти")')
            )
            if confirm_btn and confirm_btn.is_visible() and not confirm_btn.is_disabled():
                confirm_btn.click()
                self._login_page.wait_for_timeout(3000)

            self._login_page.screenshot(path=str(shot_path))

            # Check for errors on the page
            err_el = self._login_page.query_selector('[class*="error"], [class*="Error"], div:has-text("Неверный код")')
            if err_el and err_el.is_visible():
                err_text = (err_el.inner_text() or '').strip()
                if "неверн" in err_text.lower() or "ошиб" in err_text.lower():
                    return {"success": False, "error": f"Ошибка Куфара: {err_text}", "screenshot": str(shot_path)}

            # Export storage state
            try:
                self._login_ctx.storage_state(path=str(BASE_DIR / "auth_storage_state.json"))
                logger.info("auth_storage_state.json exported successfully!")
            except Exception as e:
                logger.debug(f"Export error: {e}")

            # Close login context cleanly
            self._login_ctx.close()
            self._login_pw.stop()
            self._login_page = None
            self._login_ctx = None
            self._login_pw = None

            return {"success": True, "screenshot": str(shot_path)}

        except Exception as e:
            logger.error(f"Error submitting SMS code: {e}")
            return {"success": False, "error": str(e)}

    def launch_interactive_login(self):
        """
        Launches a visible Chromium browser with persistent session.
        Allows the user to log in manually via Phone/SMS, Google, or Email.
        Keeps running until the user completes login and closes the window.
        """
        print("\n=======================================================")
        print("🚀 ЗАПУСК БРАУЗЕРА ДЛЯ ВХОДА НА KUFAR.BY")
        print("1. В открывшемся окне войдите в свой аккаунт Куфара.")
        print("2. Убедитесь, что вы успешно авторизовались.")
        print("3. Закройте браузер или нажмите Ctrl+C здесь, когда закончите.")
        print("=======================================================\n")
        
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=False,
                channel="chromium",
                viewport={"width": 1280, "height": 850},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://www.kufar.by/", timeout=60000)
            
            try:
                # Wait until user closes the browser or 15 minutes pass
                while len(context.pages) > 0:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            finally:
                # Export portable storage state for cloud usage
                export_path = BASE_DIR / "auth_storage_state.json"
                try:
                    context.storage_state(path=str(export_path))
                    print(f"📦 Портативный файл сессии сохранен: {export_path}")
                except Exception as e:
                    logger.debug(f"Could not export storage state: {e}")
                context.close()
                print("\n✅ Сессия сохранена в папке browser_session и auth_storage_state.json!\n")

    def capture_status_screenshot(self) -> Optional[str]:
        """Captures screenshot of current profile/session for Telegram check."""
        screenshot_path = SCREENSHOTS_DIR / "current_status.png"
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=True,
                viewport={"width": 1280, "height": 850},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto("https://www.kufar.by/account/profile", timeout=25000)
                page.wait_for_timeout(2500)
                page.screenshot(path=str(screenshot_path))
                return str(screenshot_path)
            except Exception as e:
                logger.error(f"Failed to capture status screenshot: {e}")
                return None
            finally:
                context.close()

    def login_with_credentials(self, login_str: str, password_str: str) -> Dict[str, Any]:
        """Performs remote login with phone/email and password from Telegram."""
        shot_path = SCREENSHOTS_DIR / "login_result.png"
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=True,
                viewport={"width": 1280, "height": 850},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            try:
                logger.info("Attempting remote login to Kufar...")
                page.goto("https://www.kufar.by/", timeout=30000)
                page.wait_for_timeout(2000)

                # Close cookie banner
                try:
                    cookie_btn = page.query_selector('button:has-text("Принять"), button:has-text("Согласен")')
                    if cookie_btn and cookie_btn.is_visible():
                        cookie_btn.click()
                        page.wait_for_timeout(500)
                except Exception:
                    pass

                # Find and click login button
                for b in page.query_selector_all('button, a'):
                    txt = (b.inner_text() or '').strip().lower()
                    if 'войти' in txt:
                        b.click()
                        break

                page.wait_for_timeout(2500)

                # If there is a button to switch to Email/Password login
                email_mode_btn = page.query_selector('button:has-text("Вход через Email и пароль")')
                if email_mode_btn and email_mode_btn.is_visible():
                    email_mode_btn.click()
                    page.wait_for_timeout(1200)

                login_inp = page.query_selector('input[name="login"], input[name="email"], input[type="email"]')
                pass_inp = page.query_selector('input[name="password"], input[type="password"]')

                if not login_inp or not pass_inp:
                    page.screenshot(path=str(shot_path))
                    return {"success": False, "error": "Поля логина/пароля не найдены", "screenshot": str(shot_path)}

                login_inp.fill(login_str)
                page.wait_for_timeout(300)
                pass_inp.fill(password_str)
                page.wait_for_timeout(500)

                # Click submit
                submit_btn = page.query_selector('button:has-text("Войти")')
                if submit_btn:
                    submit_btn.click()
                else:
                    pass_inp.press("Enter")

                page.wait_for_timeout(4000)
                page.screenshot(path=str(shot_path))

                # Check if modal closed or profile opened
                has_pass_inp = page.query_selector('input[name="password"]') is not None
                if not has_pass_inp:
                    # Export session
                    try:
                        context.storage_state(path=str(BASE_DIR / "auth_storage_state.json"))
                    except Exception:
                        pass
                    return {"success": True, "screenshot": str(shot_path)}
                else:
                    return {
                        "success": False,
                        "error": "Не удалось войти (проверьте логин/пароль или наличие капчи)",
                        "screenshot": str(shot_path)
                    }
            except Exception as e:
                logger.error(f"Remote login error: {e}")
                return {"success": False, "error": str(e), "screenshot": str(shot_path) if shot_path.exists() else None}
            finally:
                context.close()

    def check_is_logged_in(self) -> bool:
        """Checks if current saved session is authenticated on Kufar."""
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto("https://www.kufar.by/account/profile", timeout=25000)
                page.wait_for_timeout(2000)
                # If redirected to login or button "Войти" is visible
                is_login_page = "login" in page.url or page.query_selector('a[href*="/login"], button:has-text("Войти")') is not None
                return not is_login_page
            except Exception as e:
                logger.error(f"Error checking login state: {e}")
                return False
            finally:
                context.close()

    def send_negotiation_message(self, ad_id: str, message_text: str, offer_price: float) -> Dict[str, Any]:
        """
        Opens the ad page, clicks 'Написать' (Chat), enters the bargaining message,
        sends it to the seller, and captures a confirmation screenshot.
        """
        item_url = f"https://www.kufar.by/item/{ad_id}"
        screenshot_path = SCREENSHOTS_DIR / f"offer_{ad_id}_{int(time.time())}.png"
        
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=self.headless,
                viewport={"width": 1280, "height": 850},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            
            try:
                logger.info(f"Navigating to ad {ad_id}: {item_url}")
                page.goto(item_url, timeout=30000)
                page.wait_for_timeout(2000)

                # Close cookie consent banner if present
                try:
                    cookie_btn = page.query_selector('button:has-text("Принять"), button:has-text("Согласен")')
                    if cookie_btn and cookie_btn.is_visible():
                        cookie_btn.click()
                        page.wait_for_timeout(500)
                except Exception:
                    pass

                # Find chat button: data-name="write_button" or text "Написать"
                chat_btn = page.query_selector('[data-name="write_button"]')
                if not chat_btn:
                    chat_btn = page.query_selector('button:has-text("Написать"), a:has-text("Написать")')

                if not chat_btn:
                    logger.warning(f"Chat button not found on ad {ad_id}. Seller may have disabled chat.")
                    page.screenshot(path=str(screenshot_path))
                    return {
                        "success": False,
                        "error": "Кнопка 'Написать' не найдена (чат отключен продавцом)",
                        "screenshot": str(screenshot_path)
                    }

                logger.info(f"Clicking chat button for ad {ad_id}...")
                chat_btn.click()
                page.wait_for_timeout(2500)

                # Find message input: textarea or contenteditable or input
                input_elem = (
                    page.query_selector('textarea[placeholder*="сообщение"]') or
                    page.query_selector('textarea') or
                    page.query_selector('div[contenteditable="true"]') or
                    page.query_selector('input[placeholder*="сообщение"]')
                )

                # Check if login modal opened
                is_auth_needed = (
                    page.query_selector('div:has-text("Войдите или зарегистрируйтесь")') is not None or
                    page.query_selector('div:has-text("Вход"), div:has-text("Регистрация")') is not None or
                    "login" in page.url
                )

                if is_auth_needed and not input_elem:
                    logger.warning("Authentication required on Kufar!")
                    page.screenshot(path=str(screenshot_path))
                    return {
                        "success": False,
                        "error": "⚠️ Вход не выполнен! Запустите 1_LOGIN_KUFAR.bat на компьютере и войдите в свой аккаунт на Куфаре (это делается 1 раз), чтобы бот мог писать продавцам.",
                        "screenshot": str(screenshot_path)
                    }

                if not input_elem:
                    page.screenshot(path=str(screenshot_path))
                    return {
                        "success": False,
                        "error": "Поле ввода сообщения не найдено (возможно, требуется авторизация через 1_LOGIN_KUFAR.bat)",
                        "screenshot": str(screenshot_path)
                    }

                # Type offer message
                logger.info(f"Typing offer message: {message_text}")
                input_elem.fill("")
                input_elem.type(message_text, delay=25)
                page.wait_for_timeout(800)

                # Send message: look for send button or press Enter
                send_btn = (
                    page.query_selector('button[type="submit"]') or
                    page.query_selector('[data-name="send_button"]') or
                    page.query_selector('button:has-text("Отправить")') or
                    page.query_selector('button svg')
                )

                if send_btn and send_btn.is_visible():
                    send_btn.click()
                else:
                    input_elem.press("Enter")

                page.wait_for_timeout(2500)
                page.screenshot(path=str(screenshot_path))

                # Record in database
                record_offer(ad_id, offer_price, message_text, status="OFFER_SENT")
                update_ad_status(ad_id, "OFFER_SENT")

                logger.info(f"Offer sent successfully for ad {ad_id}!")
                return {
                    "success": True,
                    "message": message_text,
                    "screenshot": str(screenshot_path)
                }

            except Exception as e:
                logger.error(f"Error during negotiation for ad {ad_id}: {e}")
                try:
                    page.screenshot(path=str(screenshot_path))
                except Exception:
                    pass
                return {
                    "success": False,
                    "error": str(e),
                    "screenshot": str(screenshot_path) if screenshot_path.exists() else None
                }
            finally:
                context.close()

    def check_chat_inbox(self) -> Dict[str, Any]:
        """Checks https://www.kufar.by/chat for new incoming replies."""
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto("https://www.kufar.by/chat", timeout=25000)
                page.wait_for_timeout(3000)
                
                # Check for unread message indicators
                unread_badges = page.query_selector_all('[data-name="unread_badge"], .unread, span:has-text("1"), span:has-text("2")')
                return {
                    "has_unread": len(unread_badges) > 0,
                    "unread_count": len(unread_badges)
                }
            except Exception as e:
                logger.error(f"Error checking chat inbox: {e}")
                return {"has_unread": False, "error": str(e)}
            finally:
                context.close()
