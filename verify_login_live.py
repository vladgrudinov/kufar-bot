from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        'C:/Users/grudinov.vi/Downloads/kufar_pc_bot/browser_session',
        headless=True,
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = ctx.new_page()
    page.goto('https://www.kufar.by/item/1094030262', timeout=30000)
    page.wait_for_timeout(2000)
    
    chat_btn = page.query_selector('[data-name="write_button"]') or page.query_selector('button:has-text("Написать")')
    if chat_btn:
        chat_btn.click()
        page.wait_for_timeout(3000)
        has_chat = page.query_selector('textarea') is not None
        has_modal = page.query_selector('div:has-text("Войдите или зарегистрируйтесь")') is not None
        print(f"RESULTS -> Has chat textarea: {has_chat} | Has login modal: {has_modal}")
        page.screenshot(path='C:/Users/grudinov.vi/Downloads/kufar_pc_bot/screenshots/actual_chat_test.png')
    ctx.close()
