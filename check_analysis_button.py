from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:3000/analysis'
TEXT = 'This is a sample passage for testing the analysis page. It contains more than twenty words so the analysis button should become enabled after the content is entered into the editor successfully.'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1400})
    page.goto(URL)
    page.wait_for_load_state('networkidle')

    print('TITLE:', page.title())

    buttons_before = [b.inner_text().strip() for b in page.locator('button').all()]
    print('BUTTONS_BEFORE:', buttons_before)

    btn = page.get_by_role('button', name='开始白盒分析')
    print('BUTTON_COUNT_BEFORE:', btn.count())
    if btn.count() > 0:
        print('BUTTON_VISIBLE_BEFORE:', btn.first.is_visible())
        print('BUTTON_ENABLED_BEFORE:', btn.first.is_enabled())

    contenteditable = page.locator('[contenteditable="true"]').first
    print('EDITOR_COUNT:', page.locator('[contenteditable="true"]').count())
    contenteditable.click()
    contenteditable.fill(TEXT)
    page.wait_for_timeout(500)

    page.screenshot(path='C:/Users/ht/Documents/outeye3.0/outeye-edu/analysis-check.png', full_page=True)

    buttons_after = [b.inner_text().strip() for b in page.locator('button').all()]
    print('BUTTONS_AFTER:', buttons_after)
    print('BUTTON_COUNT_AFTER:', btn.count())
    if btn.count() > 0:
        print('BUTTON_VISIBLE_AFTER:', btn.first.is_visible())
        print('BUTTON_ENABLED_AFTER:', btn.first.is_enabled())
        try:
            btn.first.scroll_into_view_if_needed(timeout=2000)
            print('BUTTON_BOUNDING_BOX:', btn.first.bounding_box())
        except Exception as e:
            print('BUTTON_SCROLL_ERROR:', str(e))

    word_label = page.locator('text=/\\(\\d+ 词\\)/').all_inner_texts()
    print('WORD_LABELS:', word_label)

    browser.close()
