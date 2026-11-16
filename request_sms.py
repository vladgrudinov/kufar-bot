import os
import sys
import time
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
SESSION_DIR = BASE_DIR / "browser_session"
CODE_FILE = BASE_DIR / "sms_code.txt"
SCREENSHOTS = BASE_DIR / "screenshots"
SCREENSHOTS.mkdir(exist_ok=True)

if CODE_FILE.exists():
    CODE_FILE.unlink()

PHONE_DIGITS = "333715769"

print(f"Starting browser to request SMS for +375 {PHONE_DIGITS}...", flush=True)

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(SESSION_DIR),
        headless=True,
        viewport={"width": 1280, "height": 850},
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://www.kufar.by/", timeout=35000)
    page.wait_for_timeout(2000)

    # Cookie banner
    try:
        cb = page.query_selector('button:has-text("Принять"), button:has-text("Согласен")')
        if cb and cb.is_visible():
            cb.click()
            page.wait_for_timeout(500)
    except Exception:
        pass

    # Find and click login button
    for b in page.query_selector_all('button, a'):
        if 'войти' in (b.inner_text() or '').strip().lower():
            b.click()
            break

    page.wait_for_timeout(2500)

    # Check if we need to click "Вход по коду"
    switch_to_code_btn = (
        page.query_selector('button:has-text("Вход по коду")') or
        page.query_selector('a:has-text("Вход по коду")')
    )
    if switch_to_code_btn and switch_to_code_btn.is_visible():
        print("Clicking 'Вход по коду'...", flush=True)
        switch_to_code_btn.click()
        page.wait_for_timeout(1500)

    # Find phone input
    phone_inp = (
        page.query_selector('input[type="tel"]') or
        page.query_selector('input[placeholder*="375"]') or
        page.query_selector('input[name="phone"]') or
        page.query_selector('input[name="login"]') or
        page.query_selector('input')
    )

    if not phone_inp:
        print("Error: phone input not found", flush=True)
        page.screenshot(path=str(SCREENSHOTS / "phone_err.png"))
        context.close()
        sys.exit(1)

    print("Found phone input, typing digits...", flush=True)
    phone_inp.click()
    page.wait_for_timeout(300)
    phone_inp.type(PHONE_DIGITS, delay=80)
    page.wait_for_timeout(1000)

    # Click "Получить код"
    get_code_btn = (
        page.query_selector('button:has-text("Получить код")') or
        page.query_selector('button[type="submit"]')
    )

    if get_code_btn:
        print("Clicking 'Получить код'...", flush=True)
        get_code_btn.click()
    else:
        print("Error: button 'Получить код' not found", flush=True)
        page.screenshot(path=str(SCREENSHOTS / "phone_err.png"))
        context.close()
        sys.exit(1)

    page.wait_for_timeout(4000)
    page.screenshot(path=str(SCREENSHOTS / "sms_requested.png"))
    print(">>> SMS_CODE_REQUESTED_SUCCESSFULLY <<<", flush=True)

    # Now wait for user to write sms_code.txt
    print("Waiting for sms_code.txt...", flush=True)
    for _ in range(300):
        if CODE_FILE.exists():
            code = CODE_FILE.read_text().strip()
            if code:
                print(f"Got code: {code}, entering into page...", flush=True)
                clean = re.sub(r'\D', '', code)
                code_boxes = page.query_selector_all('input[type="tel"], input[maxlength="1"], input[inputmode="numeric"]')
                if len(code_boxes) >= 4:
                    for i, ch in enumerate(clean[:len(code_boxes)]):
                        code_boxes[i].fill(ch)
                        page.wait_for_timeout(100)
                else:
                    inp = (
                        page.query_selector('input[name="code"]') or
                        page.query_selector('input[placeholder*="код"]') or
                        page.query_selector('input[type="tel"]') or
                        page.query_selector('input[type="text"]')
                    )
                    if inp:
                        inp.fill(clean)

                page.wait_for_timeout(1500)
                conf_btn = page.query_selector('button:has-text("Подтвердить"), button:has-text("Войти"), button[type="submit"]')
                if conf_btn and conf_btn.is_visible():
                    conf_btn.click()
                else:
                    page.keyboard.press("Enter")

                page.wait_for_timeout(4000)
                page.screenshot(path=str(SCREENSHOTS / "login_done.png"))
                
                try:
                    context.storage_state(path=str(BASE_DIR / "auth_storage_state.json"))
                except Exception:
                    pass
                print(">>> LOGIN_COMPLETED_SUCCESSFULLY <<<", flush=True)
                break
        time.sleep(1)

    context.close()
    if CODE_FILE.exists():
        CODE_FILE.unlink()
