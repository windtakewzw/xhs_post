"""Fetch comments from notes via creator center (Patchright CDP mode)."""
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


def pause(lo=0.5, hi=2.0):
    time.sleep(random.uniform(lo, hi))


def mouse_wander(page):
    w, h = page.viewport_size['width'], page.viewport_size['height']
    x, y = random.randint(80, w - 80), random.randint(80, h - 80)
    if random.random() < 0.7:
        page.mouse.move(x, y, steps=random.randint(3, 10))
    else:
        page.mouse.move(x, y)
    pause(0.15, 0.5)


def hover_then_click(page, locator):
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
    for _ in range(random.randint(1, 3)):
        page.mouse.wheel(0, random.randint(200, 700))
        pause(0.5, 2.0)
        if random.random() < 0.3:
            mouse_wander(page)
            pause(0.5, 1.5)
            page.mouse.wheel(0, random.randint(-300, -100))
            pause(0.3, 1.0)


def idle_browse(page, label=""):
    menus = random.sample(["首页", "笔记管理", "数据看板", "活动中心", "笔记灵感", "创作学院", "创作百科"],
                          random.randint(1, 1) if random.random() < 0.6 else 0)
    for menu in menus:
        mouse_wander(page)
        pause(0.3, 1.0)
        page.evaluate(f"""(m) => {{
            for (const el of document.querySelectorAll('*')) {{
                if (el.innerText && el.innerText.trim() === m && el.offsetParent) {{ el.click(); return; }}
            }}
        }}""", menu)
        pause(1, 3)
        if random.random() < 0.5:
            idle_scroll(page)


def scroll_in_detail_panel(page):
    pause(1, 2)
    mouse_wander(page)
    pause(0.3, 0.8)
    page.evaluate("""() => {
        for (const el of document.querySelectorAll('[class*="detail"], [class*="panel"], [class*="drawer"], [class*="content"]')) {
            if (el.scrollHeight > el.clientHeight + 50) {
                for (let i = 0; i < 5; i++) {
                    el.scrollTop += 400 + Math.random() * 300;
                }
                return;
            }
        }
    }""")
    for _ in range(random.randint(2, 3)):
        mouse_wander(page)
        pause(0.2, 0.5)
        page.mouse.wheel(0, random.randint(300, 700))
        pause(0.5, 1.5)
        if random.random() < 0.3:
            page.mouse.wheel(0, random.randint(-300, -100))
            pause(0.3, 0.8)


def extract_page_data(page) -> dict:
    text = page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in text.split('\n') if l.strip() and 'ICP' not in l and '营业执照' not in l and '行吟' not in l]

    result = {"notes": [], "comments": [], "raw_lines": len(lines)}

    i = 0
    while i < len(lines):
        line = lines[i]
        if '发布于' in line and i > 0:
            title = lines[i - 1] if i > 0 else ""
            date = line
            stats = []
            for j in range(i + 1, min(i + 6, len(lines))):
                if lines[j].isdigit():
                    stats.append(int(lines[j]))
                else:
                    break
            if title and '笔记管理' not in title and '全部笔记' not in title:
                result["notes"].append({"title": title, "date": date, "stats": stats})
        if any(k in line for k in ['评论区', '说点什么', '写下评论']):
            result["has_comment_input"] = True
        i += 1

    return result


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
# Fetch — CDP mode
# ---------------------------------------------------------------------------

def _fetch_cdp(args, state_file):
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

        # Go to note manager
        page.goto(NOTE_MANAGER_URL, wait_until="load")
        pause(3, 5)

        if page.locator('[placeholder*="手机号"]').first.count():
            print(json.dumps({"error": "creator_not_logged_in"}, ensure_ascii=False))
            sys.exit(EXIT_LOGIN_EXPIRED)

        # Pre-browse
        idle_browse(page, "pre")
        page.goto(NOTE_MANAGER_URL, wait_until="load")
        pause(2, 4)

        # Open first note detail
        mouse_wander(page)
        pause(0.5, 1.5)
        imgs = page.locator('img.content')
        if imgs.count() == 0:
            print(json.dumps({"error": "no_notes"}, ensure_ascii=False))
            sys.exit(1)

        hover_then_click(page, imgs.first)
        pause(2, 4)

        # Scroll for comments
        scroll_in_detail_panel(page)
        pause(1, 2)

        # Extract
        data = extract_page_data(page)
        pause(0.5, 1)

        # Close detail
        mouse_wander(page)
        pause(0.3, 0.8)
        page.mouse.click(random.randint(50, 250), random.randint(80, 300))
        pause(0.5, 1.5)

        # Save cookies
        cookies = ctx.cookies()
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"cookies": cookies}, f, ensure_ascii=False, indent=2)

    print(json.dumps(data, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Fetch — launch fallback
# ---------------------------------------------------------------------------

def _fetch_launch(args, state_file):
    log("Launch 模式: Patchright 自启动 Chromium")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled",
                  "--disable-gpu", "--disable-dev-shm-usage", "--disable-software-rasterizer",
                  "--disable-features=VizDisplayCompositor"]
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

        page.goto(NOTE_MANAGER_URL, wait_until="load")
        pause(3, 5)

        if page.locator('[placeholder*="手机号"]').first.count():
            print(json.dumps({"error": "creator_not_logged_in"}, ensure_ascii=False))
            sys.exit(EXIT_LOGIN_EXPIRED)

        idle_browse(page, "pre")
        page.goto(NOTE_MANAGER_URL, wait_until="load")
        pause(2, 4)

        mouse_wander(page)
        pause(0.5, 1.5)
        imgs = page.locator('img.content')
        if imgs.count() == 0:
            print(json.dumps({"error": "no_notes"}, ensure_ascii=False))
            sys.exit(1)

        hover_then_click(page, imgs.first)
        pause(2, 4)

        scroll_in_detail_panel(page)
        pause(1, 2)

        data = extract_page_data(page)
        pause(0.5, 1)

        mouse_wander(page)
        pause(0.3, 0.8)
        page.mouse.click(random.randint(50, 250), random.randint(80, 300))
        pause(0.5, 1.5)

        ctx.storage_state(path=state_file)
        browser.close()

    print(json.dumps(data, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def fetch(args):
    state_dir = args.accounts_dir or f"accounts/{args.account_id}/"
    state_file = os.path.join(state_dir, "state.json")

    if args.no_cdp:
        _fetch_launch(args, state_file)
    else:
        _fetch_cdp(args, state_file)


def main():
    p = argparse.ArgumentParser(description="小红书评论抓取")
    p.add_argument("--note-id", default="")
    p.add_argument("--account-id", required=True)
    p.add_argument("--accounts-config", default="")
    p.add_argument("--accounts-dir", default="")
    p.add_argument("--headless", action="store_true", default=True)
    p.add_argument("--cdp-endpoint", default=f"127.0.0.1:{CDP_DEFAULT_PORT}")
    p.add_argument("--no-cdp", action="store_true")
    fetch(p.parse_args())


if __name__ == "__main__":
    main()
