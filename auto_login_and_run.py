import os
import sys
import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
SESSION_DIR = BASE_DIR / "browser_session"

print("======================================================")
print("  АВТОМАТИЧЕСКИЙ ВХОД НА KUFAR.BY                     ")
print("======================================================")

p = sync_playwright().start()
context = p.chromium.launch_persistent_context(
    str(SESSION_DIR),
    headless=False,
    args=[
        "--start-maximized",
        "--disable-blink-features=AutomationControlled"
    ]
)
page = context.pages[0] if context.pages else context.new_page()

print("[+] Открываем Kufar.by...")
page.goto('https://www.kufar.by/', wait_until='domcontentloaded', timeout=40000)
time.sleep(2)

# Cookie banner
try:
    cb = page.query_selector('button:has-text("Принять"), button:has-text("Согласен")')
    if cb and cb.is_visible():
        cb.click()
        time.sleep(0.5)
except Exception:
    pass

# Click Войти
print("[+] Нажимаем кнопку 'Войти'...")
for b in page.query_selector_all('button, a'):
    if 'войти' in (b.inner_text() or '').strip().lower():
        b.click()
        break
time.sleep(2)

# Click "Вход по коду"
switch_btn = page.query_selector('button:has-text("Вход по коду")')
if switch_btn and switch_btn.is_visible():
    print("[+] Переключаем на вход по коду...")
    switch_btn.click()
    time.sleep(1.5)

# Fill phone number automatically
phone_inp = page.query_selector('input[name="phone"]')
if phone_inp:
    print("[+] Вводим номер +375 (33) 371-57-69...")
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
    time.sleep(1)

    # Click "Получить код"
    get_btn = page.query_selector('button:has-text("Получить код")')
    if get_btn and not get_btn.is_disabled():
        print("[+] Нажимаем 'Получить код'...")
        get_btn.click()
        time.sleep(2)

print("\n" + "=" * 65)
print(">>> ОКНО KUFAR ОТКРЫТО ПРЯМО ПЕРЕД ВАМИ!")
print(">>> Код отправлен в Viber / SMS на ваш номер.")
print(">>> Просто введите 4 цифры прямо в окне браузера!")
print(">>> Как только вы войдете — бот САМ всё зафиксирует и запустит мониторинг 24/7!")
print("=" * 65 + "\n")

# Wait for successful login
logged_in = False
for _ in range(120): # 4 minutes
    time.sleep(2)
    # Check if login modal disappeared and user profile button or message icon appeared
    has_profile = (
        page.query_selector('a[href*="/chat"]') or
        page.query_selector('button:has-text("Подать объявление")') or
        page.query_selector('[data-name="user_profile"]')
    )
    modal_open = page.query_selector('input[type="tel"], input[maxlength="1"], input[name="phone"]')

    # When 4 boxes disappear and user is authenticated
    if not modal_open:
        # Check if button "Войти" is gone
        login_btn = page.query_selector('header button:has-text("Войти"), header a:has-text("Войти")')
        if not login_btn:
            print("\n[+++] ВХОД УСПЕШНО ВЫПОЛНЕН! СЕССИЯ ПОЛНОСТЬЮ СОХРАНЕНА.")
            logged_in = True
            time.sleep(2)
            break

# Export storage state
try:
    context.storage_state(path=str(BASE_DIR / "auth_storage_state.json"))
    print("[+] Файл auth_storage_state.json обновлен.")
except Exception:
    pass

context.close()
p.stop()

if logged_in:
    print("[+] Запускаем Kufar Sniper 24/7...")
    subprocess.Popen([sys.executable, str(BASE_DIR / "main.py")])
    print("[+] Бот успешно запущен в фоновом режиме 24/7!")
else:
    print("[-] Окно закрыто или время ожидания истекло.")
