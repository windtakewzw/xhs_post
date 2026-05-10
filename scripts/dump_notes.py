"""Dump the note-manager page structure."""
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
    page.wait_for_timeout(5000)

    page.screenshot(path="accounts/account-001/note_manager.png")
    print(f"URL: {page.url}")
    print(f"Title: {page.title()}")
    print()

    # Dump all note items with their data
    print("=== NOTE CARDS ===")
    cards = page.evaluate("""() => {
        const results = [];
        // Try various selectors for note cards
        const selectors = [
            '[class*="noteItem"]', '[class*="note-item"]', '[class*="noteCard"]',
            '[class*="card"]', '[class*="table"] [class*="row"]', '[class*="list"] [class*="item"]',
            'a[href*="note"]', 'a[href*="detail"]'
        ];
        for (const sel of selectors) {
            for (const el of document.querySelectorAll(sel)) {
                const text = (el.innerText || '').trim().replace(/\\n/g, ' | ');
                const href = el.href || '';
                const cls = (typeof el.className === 'string' ? el.className : '').substring(0, 80);
                const dataId = el.getAttribute('data-id') || el.getAttribute('data-note-id') || '';
                if (text.length > 5 || href) {
                    results.push({selector: sel, class: cls, href: href.substring(0, 100), dataId, text: text.substring(0, 100)});
                }
            }
        }
        return results;
    }""")

    seen = set()
    for c in cards[:30]:
        key = (c['text'][:50], c['href'][:50])
        if key not in seen:
            seen.add(key)
            print(f"  [{c['selector']}] class='{c['class'][:60]}' dataId='{c['dataId']}' href='{c['href'][:80]}'")
            print(f"    text='{c['text'][:120]}'")

    # All links
    print("\n=== LINKS ===")
    links = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('a')).filter(el => el.offsetParent && el.href).map(el => ({
            href: el.href.substring(0, 150),
            text: (el.innerText || '').trim().substring(0, 60),
            class: (typeof el.className === 'string' ? el.className : '').substring(0, 60)
        }));
    }""")
    for l in links[:30]:
        if l['href']:
            print(f"  class='{l['class'][:50]}' text='{l['text'][:60]}' href='{l['href'][:100]}'")

    # All images
    print("\n=== IMAGES ===")
    imgs = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('img')).filter(el => el.offsetParent).map(el => ({
            src: (el.src || '').substring(0, 120),
            alt: (el.alt || '').substring(0, 60),
            class: (typeof el.className === 'string' ? el.className : '').substring(0, 60),
            width: el.width, height: el.height
        }));
    }""")
    for img in imgs[:20]:
        print(f"  class='{img['class'][:50]}' {img['width']}x{img['height']} alt='{img['alt'][:40]}' src='{img['src'][:100]}'")

    # Page text
    print("\n=== PAGE TEXT (first 25 lines) ===")
    text = page.evaluate("() => document.body.innerText")
    for line in text.split('\n')[:25]:
        if line.strip():
            print(f"  {line.strip()[:120]}")

    # Stop message
    print(f"\nBrowser will remain open - check manually if needed")
    input()
    ctx.storage_state(path=state)
    browser.close()
