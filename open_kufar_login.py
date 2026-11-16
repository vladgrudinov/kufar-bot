import sys
import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
SESSION_DIR = BASE_DIR / "browser_session"

print("======================================================", flush=True)
print("  ОТКРЫТИЕ ОКНА ДЛЯ ВХОДА НА KUFAR.BY                 ", flush=True)
print("======================================================", flush=True)

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

print("[+] Открываем Kufar.by...", flush=True)
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

# Check if already logged in
login_btn = page.query_selector('header button:has-text("Войти"), header a:has-text("Войти")')
if not login_btn:
    print("[+++] ВЫ УЖЕ АВТОРИЗОВАНЫ НА КУФАРЕ!", flush=True)
    try:
        context.storage_state(path=str(BASE_DIR / "auth_storage_state.json"))
    except Exception:
        pass
    context.close()
    p.stop()
    subprocess.Popen([sys.executable, str(BASE_DIR / "main.py")])
    sys.exit(0)

# Click Войти
print("[+] Открываем окно входа...", flush=True)
for b in page.query_selector_all('button, a'):
    if 'войти' in (b.inner_text() or '').strip().lower():
        b.click()
        break
time.sleep(2)

# Click "Вход по коду"
switch_btn = page.query_selector('button:has-text("Вход по коду")')
if switch_btn and switch_btn.is_visible():
    print("[+] Переключаем на вход по коду...", flush=True)
    switch_btn.click()
    time.sleep(1.5)

# Fill phone number automatically
phone_inp = page.query_selector('input[name="phone"]')
if phone_inp:
    print("[+] Заполняем номер +375 (33) 371-57-69...", flush=True)
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

    get_btn = page.query_selector('button:has-text("Получить код")')
    if get_btn and not get_btn.is_disabled():
        print("[+] Запрашиваем код...", flush=True)
        get_btn.click()
        time.sleep(2)

print("\n" + "=" * 65, flush=True)
print(">>> ОКНО ОТКРЫТО! Введите 4 цифры из SMS/Viber в открывшемся окне.", flush=True)
print(">>> После ввода кода окно само закроется и запустит бота!", flush=True)
print("=" * 65 + "\n", flush=True)

# Wait up to 6 minutes for user to enter code or log in
logged_in = False
for _ in range(180):
    time.sleep(2)
    # If user closed browser
    if len(context.pages) == 0:
        print("[!] Окно закрыто пользователем.", flush=True)
        break
        
    has_boxes = page.query_selector('input[maxlength="1"], input[type="tel"]')
    login_btn = page.query_selector('header button:has-text("Войти"), header a:has-text("Войти")')
    
    # If modal is gone and login button is gone -> SUCCESS
    if not has_boxes and not login_btn:
        print("\n[+++] ВХОД УСПЕШНО ВЫПОЛНЕН! СЕССИЯ ПОЛНОСТЬЮ СОХРАНЕНА.", flush=True)
        logged_in = True
        time.sleep(2)
        break

try:
    context.storage_state(path=str(BASE_DIR / "auth_storage_state.json"))
except Exception:
    pass

context.close()
p.stop()

if logged_in:
    print("[+] Запуск боевого бота Kufar Sniper 24/7...", flush=True)
    subprocess.Popen([sys.executable, str(BASE_DIR / "main.py")])
    print("[+] БОТ УСПЕШНО ЗАПУЩЕН В ФОНЕ!", flush=True)
