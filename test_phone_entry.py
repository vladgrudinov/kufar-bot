from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir='C:/Users/grudinov.vi/Downloads/kufar_pc_bot/browser_session',
        headless=True,
        viewport={"width": 1280, "height": 850},
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = ctx.new_page()
    page.goto('https://www.kufar.by/', timeout=30000)
    page.wait_for_timeout(2000)
    
    # Cookie
    try:
        cb = page.query_selector('button:has-text("Принять")')
        if cb: cb.click()
    except Exception: pass
    
    for b in page.query_selector_all('button, a'):
        if 'войти' in (b.inner_text() or '').strip().lower():
            b.click()
            break
            
    page.wait_for_timeout(2000)
    sb = page.query_selector('button:has-text("Вход по коду")')
    if sb and sb.is_visible():
        sb.click()
        page.wait_for_timeout(1000)
        
    phone_inp = page.query_selector('input[name="phone"]')
    print('Found phone input:', phone_inp is not None)
    if phone_inp:
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
            setNativeValue(el, '+375 (33) 371-57-69');
        }''', phone_inp)
        page.wait_for_timeout(800)
        print('Val after setNativeValue:', repr(phone_inp.input_value()))
        btn = page.query_selector('button:has-text("Получить код")')
        print('Btn disabled:', btn.is_disabled() if btn else None)
        if btn and not btn.is_disabled():
            btn.click()
            print('CLICKED ПОЛУЧИТЬ КОД!')
            page.wait_for_timeout(4000)
            page.screenshot(path='C:/Users/grudinov.vi/Downloads/kufar_pc_bot/screenshots/sms_sent_real.png')
    ctx.close()
