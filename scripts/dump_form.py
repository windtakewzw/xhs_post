"""Upload image then dump ALL form elements."""
import io, os, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

INIT_SCRIPT = """\
Object.defineProperty(navigator, 'webdriver', {get: () => false});
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
"""

state = "accounts/account-001/state.json"
img = os.path.abspath("data/中央半岛/drafts/20260510_003/images/image-01.jpg").replace("\\", "/")

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    ctx = browser.new_context(storage_state=state, viewport={"width":1280,"height":900}, locale="zh-CN", timezone_id="Asia/Shanghai")
    ctx.add_init_script(INIT_SCRIPT)
    page = ctx.new_page()

    # Go to publish page
    page.goto("https://creator.xiaohongshu.com/publish/publish", wait_until="networkidle", timeout=30000)
    time.sleep(3)

    # Click upload photo tab via JS
    page.evaluate("""() => {
        for (const el of document.querySelectorAll('*')) {
            if (el.innerText && el.innerText.trim() === '上传图文' && el.offsetParent) {
                el.click(); return;
            }
        }
    }""")
    time.sleep(3)

    # Upload image
    file_input = page.locator('input.upload-input').first
    if file_input.count():
        file_input.set_input_files(img)
        print("Image uploaded")
    time.sleep(5)

    # Screenshot
    page.screenshot(path="accounts/account-001/form_after_upload.png")
    print(f"URL: {page.url}")

    # Dump ALL visible inputs
    result = page.evaluate("""() => {
        const inputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
        return Array.from(inputs).filter(el => el.offsetParent !== null).map(el => ({
            tag: el.tagName, type: el.type||'', placeholder: el.placeholder||'',
            id: el.id||'', name: el.name||'', maxlength: el.maxLength||'',
            class: (typeof el.className==='string'?el.className:'').substring(0,100),
            contenteditable: el.getAttribute('contenteditable')||'',
            text: (el.innerText||'').substring(0,50)
        }));
    }""")
    for el in result:
        parts = []
        if el['placeholder']: parts.append(f"placeholder='{el['placeholder']}'")
        if el['contenteditable']: parts.append('contenteditable')
        if el['maxlength']: parts.append(f"maxlength={el['maxlength']}")
        if el['text']: parts.append(f"text='{el['text']}'")
        print(f"<{el['tag']}> class='{el['class'][:80]}' {' | '.join(parts)}")

    # All visible buttons with text
    btns = page.evaluate("""() => {
        const all = document.querySelectorAll('button, [role="button"]');
        return Array.from(all).filter(el => el.offsetParent !== null && el.innerText.trim()).map(el => ({
            text: el.innerText.trim().substring(0,30),
            class: (typeof el.className==='string'?el.className:'').substring(0,60)
        }));
    }""")
    for b in btns:
        print(f"BTN: '{b['text']}' class='{b['class'][:50]}'")

    # Page text first 30 lines
    text = page.evaluate("() => document.body.innerText")
    print("\n--- PAGE TEXT ---")
    for line in text.split('\n')[:30]:
        if line.strip(): print(f"  {line.strip()[:120]}")

    ctx.storage_state(path=state)
    browser.close()
