"""Reply to comments via creator center note detail panel (Patchright CDP mode)."""
import io, os, sys, time, random, json, argparse, http.client
from urllib.parse import urlparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from patchright.sync_api import sync_playwright

INIT_SCRIPT_LAUNCH = """\
Object.defineProperty(navigator, 'webdriver', {get: () => false});
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
"""

CDP_DEFAULT_PORT = 9222
NOTE_MANAGER_URL = "https://creator.xiaohongshu.com/new/note-manager"
EXIT_SUCCESS = 0
EXIT_LOGIN_EXPIRED = 2
EXIT_NO_CDP = 3


def log(msg): print(msg, flush=True)


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
    for _ in range(random.randint(1, 2)):
        page.mouse.wheel(0, random.randint(200, 500))
        pause(0.5, 1.5)
        if random.random() < 0.3:
            mouse_wander(page)
            page.mouse.wheel(0, random.randint(-200, -100))
            pause(0.3, 0.8)


def scroll_to_comments(page):
    mouse_wander(page)
    pause(0.3, 0.6)
    page.evaluate("""() => {
        for (const el of document.querySelectorAll('[class*="detail"], [class*="panel"], [class*="drawer"], [class*="content"]')) {
            if (el.scrollHeight > el.clientHeight + 50) {
                el.scrollTop = el.scrollHeight;
                return;
            }
        }
    }""")
    pause(0.5, 1.5)
    for _ in range(random.randint(3, 5)):
        mouse_wander(page)
        pause(0.2, 0.5)
        page.mouse.wheel(0, random.randint(400, 800))
        pause(0.5, 1.5)


# ---------------------------------------------------------------------------
# CDP helpers
# ---------------------------------------------------------------------------

def resolve_cdp_ws_url(endpoint: str) -> str:
    if endpoint.startswith("ws://") or endpoint.startswith("wss://"):
        return endpoint
    parsed = urlparse(endpoint)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or CDP_DEFAULT_PORT
    conn = http.client.HTTPConnection(host, port, timeout=5)
    conn.request("GET", "/json/version")
    resp = conn.getresponse()
    data = json.loads(resp.read())
    conn.close()
    return data.get("webSocketDebuggerUrl")


def check_cdp_ready(endpoint: str) -> bool:
    try:
        resolve_cdp_ws_url(endpoint)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Reply — CDP mode
# ---------------------------------------------------------------------------

def _reply_cdp(args, state_file):
    log("CDP 模式: 连接 Chrome...")

    if not check_cdp_ready(args.cdp_endpoint):
        log(f"ERROR: Chrome CDP 未在 {args.cdp_endpoint} 监听")
        log("请先运行: scripts/launch_chrome_cdp.bat")
        sys.exit(EXIT_NO_CDP)

    ws_url = resolve_cdp_ws_url(args.cdp_endpoint)

    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(ws_url)
        ctx = browser.contexts[0]

        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if saved.get("cookies"):
                ctx.add_cookies(saved["cookies"])

        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})

        # Open note manager
        log("Opening note-manager...")
        page.goto(NOTE_MANAGER_URL, wait_until="load")
        pause(3, 5)

        if page.locator('[placeholder*="手机号"]').first.count():
            print(json.dumps({"error": "creator_not_logged_in"}, ensure_ascii=False))
            sys.exit(EXIT_LOGIN_EXPIRED)
        log("Logged in OK")

        # Pre-browse
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
            page.goto(NOTE_MANAGER_URL, wait_until="load")
            pause(2, 4)

        # Open note detail
        mouse_wander(page)
        pause(0.5, 1.5)
        imgs = page.locator('img.content')
        log(f"Found {imgs.count()} notes")
        if imgs.count() == 0:
            print(json.dumps({"error": "no_notes"}, ensure_ascii=False))
            sys.exit(1)

        log("Opening note detail...")
        hover_click(page, imgs.first)
        pause(3, 5)

        # Scroll to comments
        log("Scrolling to comments...")
        scroll_to_comments(page)
        pause(1, 2)

        # Find and click reply
        log("Looking for comment reply...")
        reply_clicked = page.evaluate("""() => {
            for (const el of document.querySelectorAll('*')) {
                const text = (el.innerText || '').trim();
                if (text === '回复' && el.offsetParent && el.tagName !== 'BODY') {
                    el.click();
                    return 'reply_btn';
                }
            }
            for (const el of document.querySelectorAll('[placeholder*="评论"], [placeholder*="说点什么"], [contenteditable="true"]')) {
                if (el.offsetParent) {
                    el.click();
                    el.focus();
                    return 'comment_input';
                }
            }
            return 'not_found';
        }""")
        log(f"Reply target: {reply_clicked}")
        pause(0.5, 1)

        # Type reply
        reply_text = args.reply_text
        log(f"Typing reply: {reply_text[:40]}...")

        input_el = page.locator('[contenteditable="true"]').first
        if not input_el.count():
            input_el = page.locator('textarea').first
        if not input_el.count():
            input_el = page.locator('[placeholder*="评论"], [placeholder*="说点什么"]').first

        if input_el.count():
            input_el.click()
            pause(0.2, 0.5)
            for char in reply_text:
                page.keyboard.type(char, delay=random.randint(60, 150))
            pause(0.5, 1)

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
                log("REPLIED")
            else:
                log("WARN: submit button not found, trying Enter")
                page.keyboard.press("Enter")
                pause(0.5, 1)
                log("Sent via Enter")
        else:
            log("WARN: reply input not found")

        # Save cookies
        cookies = ctx.cookies()
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"cookies": cookies}, f, ensure_ascii=False, indent=2)
        log("Done")


# ---------------------------------------------------------------------------
# Reply — launch fallback
# ---------------------------------------------------------------------------

def _reply_launch(args, state_file):
    log("Launch 模式: Patchright 自启动 Chromium")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled",
                  "--disable-gpu", "--disable-dev-shm-usage"]
        )
        ctx_kwargs = {
            "viewport": {"width": 1280, "height": 900},
            "locale": "zh-CN", "timezone_id": "Asia/Shanghai",
        }
        if os.path.exists(state_file):
            ctx_kwargs["storage_state"] = state_file

        ctx = browser.new_context(**ctx_kwargs)
        ctx.add_init_script(INIT_SCRIPT_LAUNCH)
        page = ctx.new_page()

        log("Opening note-manager...")
        page.goto(NOTE_MANAGER_URL, wait_until="load")
        pause(3, 5)

        if page.locator('[placeholder*="手机号"]').first.count():
            print(json.dumps({"error": "creator_not_logged_in"}, ensure_ascii=False))
            sys.exit(EXIT_LOGIN_EXPIRED)
        log("Logged in OK")

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
            page.goto(NOTE_MANAGER_URL, wait_until="load")
            pause(2, 4)

        mouse_wander(page)
        pause(0.5, 1.5)
        imgs = page.locator('img.content')
        log(f"Found {imgs.count()} notes")
        if imgs.count() == 0:
            print(json.dumps({"error": "no_notes"}, ensure_ascii=False))
            sys.exit(1)

        log("Opening note detail...")
        hover_click(page, imgs.first)
        pause(3, 5)

        log("Scrolling to comments...")
        scroll_to_comments(page)
        pause(1, 2)

        log("Looking for comment reply...")
        reply_clicked = page.evaluate("""() => {
            for (const el of document.querySelectorAll('*')) {
                const text = (el.innerText || '').trim();
                if (text === '回复' && el.offsetParent && el.tagName !== 'BODY') {
                    el.click();
                    return 'reply_btn';
                }
            }
            for (const el of document.querySelectorAll('[placeholder*="评论"], [placeholder*="说点什么"], [contenteditable="true"]')) {
                if (el.offsetParent) {
                    el.click();
                    el.focus();
                    return 'comment_input';
                }
            }
            return 'not_found';
        }""")
        log(f"Reply target: {reply_clicked}")
        pause(0.5, 1)

        reply_text = args.reply_text
        log(f"Typing reply: {reply_text[:40]}...")

        input_el = page.locator('[contenteditable="true"]').first
        if not input_el.count():
            input_el = page.locator('textarea').first
        if not input_el.count():
            input_el = page.locator('[placeholder*="评论"], [placeholder*="说点什么"]').first

        if input_el.count():
            input_el.click()
            pause(0.2, 0.5)
            for char in reply_text:
                page.keyboard.type(char, delay=random.randint(60, 150))
            pause(0.5, 1)

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
                log("REPLIED")
            else:
                log("WARN: submit button not found, trying Enter")
                page.keyboard.press("Enter")
                pause(0.5, 1)
                log("Sent via Enter")
        else:
            log("WARN: reply input not found")

        ctx.storage_state(path=state_file)
        browser.close()
        log("Done")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def reply(args):
    state_dir = args.accounts_dir or f"accounts/{args.account_id}/"
    state_file = os.path.join(state_dir, "state.json")

    if args.no_cdp:
        _reply_launch(args, state_file)
    else:
        _reply_cdp(args, state_file)


def main():
    p = argparse.ArgumentParser(description="小红书评论回复")
    p.add_argument("--note-id", default="")
    p.add_argument("--comment-id", default="")
    p.add_argument("--reply-text", required=True)
    p.add_argument("--account-id", required=True)
    p.add_argument("--accounts-config", default="")
    p.add_argument("--accounts-dir", default="")
    p.add_argument("--headless", action="store_true", default=True)
    p.add_argument("--cdp-endpoint", default=f"127.0.0.1:{CDP_DEFAULT_PORT}")
    p.add_argument("--no-cdp", action="store_true")
    reply(p.parse_args())


if __name__ == "__main__":
    main()
