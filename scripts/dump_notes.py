"""Dump note manager page to find note ID selectors."""
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
    ctx = browser.new_context(storage_state=state, viewport={"width":1280,"height":900}, locale="zh-CN", timezone_id="Asia/Shanghai")
    ctx.add_init_script(INIT_SCRIPT)
    page = ctx.new_page()

    page.goto("https://creator.xiaohongshu.com/note-manager", wait_until="networkidle", timeout=30000)
    time.sleep(5)
    # Try waiting longer for AJAX
    page.wait_for_timeout(5000)
    page.screenshot(path="accounts/account-001/notes_page.png")
    print("PAGE TEXT:")
    text = page.evaluate("() => document.body.innerText")
    for line in text.split('\n')[:30]:
        if line.strip(): print(f"  {line.strip()[:120]}")
    print()

    # Also try the main site version - note might be at xiaohongshu.com
    page.goto("https://www.xiaohongshu.com/user/profile/5f3a4b050000000001006d74", wait_until="networkidle", timeout=30000)
    time.sleep(5)
    page.wait_for_timeout(3000)
    print("PROFILE TEXT:")
    text2 = page.evaluate("() => document.body.innerText")
    for line in text2.split('\n')[:30]:
        if line.strip(): print(f"  {line.strip()[:120]}")

    # Extract all links
    links = page.evaluate("""() => {
        const all = document.querySelectorAll('a[href*="explore"], a[href*="note"], a[href*="detail"]');
        return Array.from(all).map(el => ({
            href: el.href||'', text: (el.innerText||'').substring(0,60),
            class: (typeof el.className==='string'?el.className:'').substring(0,60)
        }));
    }""")
    for l in links[:20]:
        if l['href']:
            print(f"LINK: {l['href'][:120]}")

    # All note cards / items with data attributes
    cards = page.evaluate("""() => {
        const cards = [];
        for (const el of document.querySelectorAll('[class*="note"], [class*="card"], [class*="item"]')) {
            const dataId = el.getAttribute('data-id') || el.getAttribute('data-note-id') || '';
            const text = (el.innerText||'').substring(0,80).replace(/\\n/g, ' ');
            const cls = (typeof el.className==='string'?el.className:'').substring(0,80);
            if (dataId || text.length > 10) {
                cards.push({dataId, text, class: cls});
            }
        }
        return cards;
    }""")
    print(f"\nFound {len(cards)} cards")
    for c in cards[:10]:
        print(f"  dataId='{c['dataId']}' class='{c['class'][:60]}' text='{c['text'][:80]}'")

    # Also dump page URL
    print(f"\nCurrent URL: {page.url}")

    ctx.storage_state(path=state)
    browser.close()
