"""Dump publish editor elements AFTER clicking upload 图文."""
import io, os, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

INIT_SCRIPT = """\
Object.defineProperty(navigator, 'webdriver', {get: () => false});
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
"""

account_id = sys.argv[1] if len(sys.argv) > 1 else "account-001"
state_file = f"accounts/{account_id}/state.json"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context(
        storage_state=state_file, viewport={"width": 1280, "height": 900},
        locale="zh-CN", timezone_id="Asia/Shanghai",
    )
    context.add_init_script(INIT_SCRIPT)
    page = context.new_page()

    page.goto("https://creator.xiaohongshu.com/publish/publish", wait_until="networkidle", timeout=30000)
    time.sleep(3)

    # Click 上传图文 via JS (avoids CSS encoding issues)
    clicked = page.evaluate("""() => {
        const all = document.querySelectorAll('span, div, button, a');
        for (const el of all) {
            if (el.innerText && el.innerText.trim() === '上传图文' && el.offsetParent) {
                el.click();
                return true;
            }
        }
        return false;
    }""")
    print(f"已点击 上传图文: {clicked}")
    time.sleep(3)

    page.screenshot(path=f"accounts/{account_id}/editor_form.png")
    print(f"URL: {page.url}")

    # Dump ALL inputs now
    print("\n=== INPUTS (after clicking 上传图文) ===")
    inputs = page.evaluate("""() => {
        const all = document.querySelectorAll('input, textarea, [contenteditable="true"]');
        return Array.from(all).filter(el => el.offsetParent !== null).map(el => ({
            tag: el.tagName, type: el.type || '', placeholder: el.placeholder || '',
            name: el.name || '', id: el.id || '',
            class: (typeof el.className === 'string' ? el.className : '').substring(0, 80),
            contenteditable: el.getAttribute('contenteditable') || '',
            value: (el.value || '').substring(0, 30)
        }));
    }""")
    for el in inputs:
        markers = []
        if el['placeholder']: markers.append(f"placeholder='{el['placeholder']}'")
        if el['contenteditable']: markers.append('contenteditable')
        if el['value']: markers.append(f"value='{el['value']}'")
        print(f"  <{el['tag']}> class='{el['class'][:60]}' {' | '.join(markers)}")

    # All visible buttons
    print("\n=== BUTTONS ===")
    btns = page.evaluate("""() => {
        const all = document.querySelectorAll('button, [role="button"], span[class*="btn"]');
        return Array.from(all).filter(el => el.offsetParent !== null).map(el => ({
            text: (el.innerText || '').trim().substring(0, 60),
            class: (typeof el.className === 'string' ? el.className : '').substring(0, 60)
        }));
    }""")
    for b in btns:
        if b['text']:
            print(f"  '{b['text']}' class='{b['class'][:50]}'")

    # Full page text (first 40 lines)
    print("\n=== PAGE TEXT ===")
    text = page.evaluate("() => document.body.innerText")
    for i, line in enumerate(text.split('\n')[:40]):
        if line.strip():
            print(f"  {line.strip()[:120]}")

    context.storage_state(path=state_file)
    browser.close()
