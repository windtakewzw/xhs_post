"""Reply to comments via creator center note detail panel."""
import io, os, sys, time, random, json, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

INIT_SCRIPT = """\
Object.defineProperty(navigator, 'webdriver', {get: () => false});
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
"""


def pause(lo=0.3, hi=1.0):
    time.sleep(random.uniform(lo, hi))


def mouse_wander(page):
    w, h = page.viewport_size['width'], page.viewport_size['height']
    x, y = random.randint(80, w - 80), random.randint(80, h - 80)
    if random.random() < 0.7:
        page.mouse.move(x, y, steps=random.randint(3, 10))
    else:
        page.mouse.move(x, y)
    pause(0.1, 0.4)


def hover_click(page, locator):
    """Hover near element, pause, then click with slight offset."""
    try:
        box = locator.bounding_box()
        if box:
            mx = box['x'] + box['width'] * random.uniform(0.25, 0.75)
            my = box['y'] + box['height'] * random.uniform(0.25, 0.75)
            page.mouse.move(mx - random.randint(5, 20), my - random.randint(5, 20), steps=random.randint(2, 4))
            pause(0.2, 0.5)
            page.mouse.move(mx, my, steps=random.randint(1, 3))
            pause(0.1, 0.3)
    except Exception:
        pass
    locator.click(force=True, timeout=5000)


def idle_scroll(page):
    """Random scrolling like someone reading."""
    for _ in range(random.randint(1, 2)):
        page.mouse.wheel(0, random.randint(200, 500))
        pause(0.5, 1.5)
        if random.random() < 0.3:
            mouse_wander(page)
            page.mouse.wheel(0, random.randint(-200, -100))
            pause(0.3, 0.8)


def scroll_to_comments(page):
    """Scroll inside note detail panel to reach comments section."""
    mouse_wander(page)
    pause(0.3, 0.6)

    # Scroll the detail panel to bottom where comments are
    page.evaluate("""() => {
        for (const el of document.querySelectorAll('[class*="detail"], [class*="panel"], [class*="drawer"], [class*="content"]')) {
            if (el.scrollHeight > el.clientHeight + 50) {
                el.scrollTop = el.scrollHeight;
                return;
            }
        }
    }""")
    pause(0.5, 1.5)

    # Mouse wheel to bottom
    for _ in range(random.randint(3, 5)):
        mouse_wander(page)
        pause(0.2, 0.5)
        page.mouse.wheel(0, random.randint(400, 800))
        pause(0.5, 1.5)


def reply(args):
    state_file = os.path.join(args.accounts_dir or f"accounts/{args.account_id}/", "state.json")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=args.headless,
            args=["--disable-gpu", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            storage_state=state_file if os.path.exists(state_file) else None,
            viewport={"width": 1280, "height": 900},
            locale="zh-CN", timezone_id="Asia/Shanghai",
        )
        context.add_init_script(INIT_SCRIPT)
        page = context.new_page()

        # === Open note manager ===
        print("Opening note-manager...", flush=True)
        page.goto("https://creator.xiaohongshu.com/new/note-manager", wait_until="load")
        pause(3, 5)

        if page.locator('[placeholder*="手机号"]').first.count():
            print(json.dumps({"error": "creator_not_logged_in"}, ensure_ascii=False))
            sys.exit(2)
        print("Logged in OK", flush=True)

        # === Pre-browse (1 random menu) ===
        if random.random() < 0.6:
            menus = random.sample(["首页", "数据看板", "笔记灵感"], 1)
            mouse_wander(page)
            pause(0.3, 1)
            page.evaluate(f"""(m) => {{
                for (const el of document.querySelectorAll('*')) {{
                    if (el.innerText && el.innerText.trim() === m && el.offsetParent) {{ el.click(); return; }}
                }}
            }}""", menus[0])
            pause(1, 3)
            page.goto("https://creator.xiaohongshu.com/new/note-manager", wait_until="load")
            pause(2, 4)

        # === Open note detail ===
        mouse_wander(page)
        pause(0.5, 1.5)
        imgs = page.locator('img.content')
        print(f"Found {imgs.count()} notes", flush=True)
        if imgs.count() == 0:
            print(json.dumps({"error": "no_notes"}, ensure_ascii=False))
            sys.exit(1)

        print("Opening note detail...", flush=True)
        hover_click(page, imgs.first)
        pause(3, 5)

        # === Scroll to comments ===
        print("Scrolling to comments...", flush=True)
        scroll_to_comments(page)
        pause(1, 2)

        # === Find and click reply ===
        print("Looking for comment reply...", flush=True)
        # Try to find a comment to reply to, or the general comment input
        reply_clicked = page.evaluate("""() => {
            // Look for reply buttons near comments
            for (const el of document.querySelectorAll('*')) {
                const text = (el.innerText || '').trim();
                if (text === '回复' && el.offsetParent && el.tagName !== 'BODY') {
                    el.click();
                    return 'reply_btn';
                }
            }
            // Look for comment input area
            for (const el of document.querySelectorAll('[placeholder*="评论"], [placeholder*="说点什么"], [contenteditable="true"]')) {
                if (el.offsetParent) {
                    el.click();
                    el.focus();
                    return 'comment_input';
                }
            }
            return 'not_found';
        }""")
        print(f"Reply target: {reply_clicked}", flush=True)

        pause(0.5, 1)

        # === Type reply ===
        reply_text = args.reply_text
        print(f"Typing reply: {reply_text[:40]}...", flush=True)

        # Find the active input element
        input_el = page.locator('[contenteditable="true"]').first
        if not input_el.count():
            input_el = page.locator('textarea').first
        if not input_el.count():
            input_el = page.locator('[placeholder*="评论"], [placeholder*="说点什么"]').first

        if input_el.count():
            input_el.click()
            pause(0.2, 0.5)
            # Type character by character for human feel
            for char in reply_text:
                page.keyboard.type(char, delay=random.randint(60, 150))
            pause(0.5, 1)

            # Submit reply
            submit_btn = page.locator('button').filter(has_text="发送").first
            if not submit_btn.count():
                submit_btn = page.locator('button').filter(has_text="回复").first
            if not submit_btn.count():
                submit_btn = page.locator('button').filter(has_text="发布").first

            if submit_btn.count():
                mouse_wander(page)
                pause(0.2, 0.5)
                submit_btn.click(force=True, timeout=3000)
                pause(1, 2)
                print("REPLIED", flush=True)
            else:
                print("WARN: submit button not found", flush=True)
                # Try Enter key
                page.keyboard.press("Enter")
                pause(0.5, 1)
                print("Sent via Enter", flush=True)
        else:
            print("WARN: reply input not found", flush=True)

        # Save state
        context.storage_state(path=state_file)
        browser.close()
        print("Done", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--note-id", default="")
    p.add_argument("--comment-id", default="")
    p.add_argument("--reply-text", required=True)
    p.add_argument("--account-id", required=True)
    p.add_argument("--accounts-config", default="")
    p.add_argument("--accounts-dir", default="")
    p.add_argument("--headless", action="store_true", default=True)
    reply(p.parse_args())


if __name__ == "__main__":
    main()
