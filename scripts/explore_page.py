"""Explore the Xiaohongshu creator center publish page to find correct selectors."""
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
user_data_dir = f"accounts/{account_id}/"
state_file = os.path.join(user_data_dir, "state.json")
output_file = os.path.join(user_data_dir, "page_structure.txt")

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(
        storage_state=state_file if os.path.exists(state_file) else None,
        viewport={"width": 1280, "height": 900},
        locale="zh-CN", timezone_id="Asia/Shanghai",
    )
    context.add_init_script(INIT_SCRIPT)
    page = context.new_page()

    # Login on main site
    page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
    time.sleep(2)

    # Click avatar
    el = page.locator('[class*="avatar"] img').first
    if el.count() and el.is_visible():
        el.click()
        time.sleep(2)

    # Click 创作中心
    link = page.locator('text=创作中心').first
    if link.count() and link.is_visible(timeout=5000):
        link.click()
        time.sleep(5)

    # Go to publish page
    page.goto("https://creator.xiaohongshu.com/publish/publish", wait_until="networkidle", timeout=30000)
    time.sleep(3)

    # Check if login needed
    if "login" in page.url.lower():
        print("ERROR: Creator center not accessible (login redirect)")
        browser.close()
        sys.exit(1)

    print(f"Current URL: {page.url}")
    print(f"Page title: {page.title()}")
    print()

    # Extract all input elements
    print("=== INPUT ELEMENTS ===")
    inputs = page.evaluate("""() => {
        const inputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
        return Array.from(inputs).map(el => ({
            tag: el.tagName,
            type: el.type || '',
            placeholder: el.placeholder || '',
            name: el.name || '',
            id: el.id || '',
            class: el.className || '',
            contenteditable: el.getAttribute('contenteditable') || '',
            visible: el.offsetParent !== null,
            rect: el.getBoundingClientRect()
        }));
    }""")
    for inp in inputs:
        if inp['visible']:
            print(f"  {inp['tag']}#{inp['id']} .{inp['class'][:80]}")
            print(f"    placeholder='{inp['placeholder']}' type='{inp['type']}' contenteditable='{inp['contenteditable']}'")

    print()
    print("=== BUTTONS ===")
    buttons = page.evaluate("""() => {
        const btns = document.querySelectorAll('button, [role="button"]');
        return Array.from(btns).map(el => ({
            text: el.innerText?.substring(0, 50) || '',
            class: el.className?.substring(0, 80) || '',
            visible: el.offsetParent !== null
        }));
    }""")
    for btn in buttons:
        if btn['visible'] and btn['text'].strip():
            print(f"  .{btn['class']}")
            print(f"    text='{btn['text'].strip()}'")

    print()
    print("=== FILE INPUTS ===")
    file_inputs = page.evaluate("""() => {
        const inputs = document.querySelectorAll('input[type="file"]');
        return Array.from(inputs).map(el => ({
            accept: el.accept || '',
            class: el.className?.substring(0, 80) || '',
            visible: el.offsetParent !== null
        }));
    }""")
    for fi in file_inputs:
        print(f"  accept='{fi['accept']}' class='{fi['class']}' visible={fi['visible']}")

    # Save full HTML
    page.screenshot(path=os.path.join(user_data_dir, "explore_screenshot.png"))
    print(f"\nScreenshot saved to {user_data_dir}/explore_screenshot.png")

    browser.close()
