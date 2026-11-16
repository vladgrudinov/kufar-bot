import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
SESSION_DIR = BASE_DIR / "browser_session"

def submit_code(code_str: str):
    clean = re.sub(r'\D', '', code_str)
    print(f"Submitting 4-digit code: {clean}...")
    
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=True,
            viewport={"width": 1280, "height": 850},
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = ctx.new_page()
        page.goto("https://www.kufar.by/", timeout=30000)
        page.wait_for_timeout(2000)
        
        # Cookie
        try:
            cb = page.query_selector('button:has-text("Принять")')
            if cb: cb.click()
        except Exception: pass

        # Click login
        for b in page.query_selector_all('button, a'):
            if 'войти' in (b.inner_text() or '').strip().lower():
                b.click()
                break
        page.wait_for_timeout(2000)

        # Switch to "Вход по коду" if on password screen
        switch_btn = page.query_selector('button:has-text("Вход по коду")')
        if switch_btn and switch_btn.is_visible():
            print("Switching to 'Вход по коду'...")
            switch_btn.click()
            page.wait_for_timeout(1500)

        # If phone input is shown, fill it
        phone_inp = page.query_selector('input[name="phone"]')
        if phone_inp and phone_inp.is_visible():
            print("Filling phone number...")
            page.evaluate('''(el) => {
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
                setNativeValue(el, '+375 (33) 371 57 69');
            }''', phone_inp)
            page.wait_for_timeout(500)
            get_btn = page.query_selector('button:has-text("Получить код")')
            if get_btn and not get_btn.is_disabled():
                print("Clicking 'Получить код' to reach code boxes...")
                get_btn.click()
                page.wait_for_timeout(2500)

        # Look for the 4 code boxes
        boxes = page.query_selector_all('input[type="tel"], input[maxlength="1"], input[inputmode="numeric"]')
        print(f"Found {len(boxes)} code boxes")
        
        if len(boxes) >= 4:
            for idx, digit in enumerate(clean[:4]):
                boxes[idx].click()
                page.wait_for_timeout(100)
                boxes[idx].fill(digit)
                page.wait_for_timeout(150)
            print("Filled all 4 digits!")
            page.wait_for_timeout(3500)
        else:
            print("Boxes not found, searching other inputs...")
            for inp in page.query_selector_all('input'):
                print("Input:", inp.get_attribute('name'), inp.get_attribute('type'))

        page.screenshot(path=str(BASE_DIR / "screenshots" / "login_success.png"))
        
        try:
            ctx.storage_state(path=str(BASE_DIR / "auth_storage_state.json"))
            print("Exported storage state successfully!")
        except Exception as e:
            print("Storage state export error:", e)
            
        ctx.close()

if __name__ == "__main__":
    submit_code(sys.argv[1] if len(sys.argv) > 1 else "7534")
