"""Click into note detail from manager, dump comment structure."""
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

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    ctx = browser.new_context(storage_state=state, viewport={"width":1280,"height":900},
                              locale="zh-CN", timezone_id="Asia/Shanghai")
    ctx.add_init_script(INIT_SCRIPT)
    page = ctx.new_page()

    # Navigate to note manager
    page.goto("https://creator.xiaohongshu.com/new/note-manager", wait_until="networkidle", timeout=30000)
    time.sleep(5)

    # Click the note card - try the whole row area, not just the image
    # The clickable area might be a parent div, not just the img
    note_clicked = page.evaluate("""() => {
        // Find element containing the note title text and click its parent card
        const all = document.querySelectorAll('[class*="row"], [class*="item"], [class*="card"], [class*="list"]');
        for (const el of all) {
            if (el.innerText && el.innerText.includes('带客户在小区园林') && el.offsetParent) {
                // Click the first image inside this card
                const img = el.querySelector('img.content, img[class*="cover"]');
                if (img) { img.click(); return 'img'; }
                el.click(); return 'card';
            }
        }
        // Fallback - just click the cover image
        const imgs = document.querySelectorAll('img.content');
        if (imgs.length > 0) { imgs[0].click(); return 'img_direct'; }
        return 'not_found';
    }""")
    print(f"Clicked: {note_clicked}")
    time.sleep(3)
    page.wait_for_timeout(2000)

    # Wait for lazy-loaded comments
    for _ in range(5):
        page.evaluate("window.scrollBy(0, 600)")
        time.sleep(2)

    page.screenshot(path="accounts/account-001/note_comments.png")

    # Dump comment elements
    print("\n=== COMMENT ELEMENTS ===")
    comments = page.evaluate("""() => {
        const results = [];
        // Common comment selectors
        const selectors = [
            '[class*="comment"]', '[class*="reply"]', '[class*="message"]',
            '[class*="interaction"] [class*="item"]', '[class*="feedback"]'
        ];
        for (const sel of selectors) {
            for (const el of document.querySelectorAll(sel)) {
                const text = (el.innerText || '').trim().replace(/\\n/g, ' | ');
                const cls = (typeof el.className === 'string' ? el.className : '').substring(0, 80);
                if (text.length > 2 && text.length < 300) {
                    results.push({selector: sel, class: cls, text: text});
                }
            }
        }
        return results;
    }""")
    for c in comments[:30]:
        print(f"  [{c['selector']}] class='{c['class'][:60]}'")
        print(f"    '{c['text'][:150]}'")

    # All visible text in the detail page
    print("\n=== DETAIL PAGE TEXT ===")
    text = page.evaluate("() => document.body.innerText")
    for line in text.split('\n')[:40]:
        if line.strip():
            print(f"  {line.strip()[:120]}")

    ctx.storage_state(path=state)
    browser.close()
