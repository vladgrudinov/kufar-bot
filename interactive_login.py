import sys
import time
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
session_dir = BASE_DIR / "browser_session"
export_path = BASE_DIR / "auth_storage_state.json"

print("=======================================================")
print("🚀 Запуск окна входа на Kufar.by...")
print("=======================================================")

with sync_playwright() as p:
    # Try channel chrome first, fallback to default chromium
    try:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(session_dir),
            headless=False,
            channel="chrome",
            viewport={"width": 1280, "height": 850},
            args=["--disable-blink-features=AutomationControlled"]
        )
    except Exception:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(session_dir),
            headless=False,
            viewport={"width": 1280, "height": 850},
            args=["--disable-blink-features=AutomationControlled"]
        )

    page = context.pages[0] if context.pages else context.new_page()

    print("Открываю главную страницу Kufar...")
    page.goto("https://www.kufar.by/", timeout=45000)
    page.wait_for_timeout(2000)

    # Automatically accept cookies
    try:
        cb = page.query_selector('button:has-text("Принять"), button:has-text("Согласен")')
        if cb and cb.is_visible():
            cb.click()
            page.wait_for_timeout(500)
    except Exception:
        pass

    # Automatically click "Войти" to open the login modal
    try:
        for b in page.query_selector_all('button, a'):
            txt = (b.inner_text() or '').strip().lower()
            if 'войти' in txt and ('подать' not in txt):
                b.click()
                print("Модальное окно входа открыто.")
                break
    except Exception:
        pass

    print("\n👉 Пожалуйста, нажмите в окне браузера 'Google', 'Яндекс' или введите Email и пароль.")
    print("⏳ Ожидание успешного входа...")

    # Wait until logged in or window closed
    logged_in = False
    start_wait = time.time()
    while time.time() - start_wait < 300:  # 5 min max
        if len(context.pages) == 0:
            print("Окно было закрыто.")
            break

        try:
            # Check for profile button or avatar or url change
            profile = (
                page.query_selector('a[href*="/account/profile"]') or
                page.query_selector('button:has-text("Профиль")') or
                page.query_selector('[data-testid="header-user-avatar"]') or
                page.query_selector('img[alt*="аватар"]')
            )
            if profile and profile.is_visible():
                logged_in = True
                print("\n🎉 ВХОД УСПЕШНО ВЫПОЛНЕН!")
                page.wait_for_timeout(2000)
                break
        except Exception:
            pass

        time.sleep(1)

    # Save state
    try:
        context.storage_state(path=str(export_path))
        print(f"✅ Файл сессии сохранен: {export_path}")
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

    context.close()
    if logged_in:
        print("Готово! Браузер закрыт.")
        sys.exit(0)
    else:
        print("Вход не был завершен.")
        sys.exit(1)
