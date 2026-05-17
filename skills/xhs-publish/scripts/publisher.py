"""Publish a Xiaohongshu draft via Patchright browser automation.

CDP mode (recommended): connects to a real Chrome instance started with
  launch_chrome_cdp.bat. No automation fingerprint — Chrome IS the browser.

Fallback mode (--no-cdp): Patchright launches its own Chromium. Still better
  than Playwright (CDP-level patches), but will trigger risk control sooner.
"""
import io, os, re, sys, time, random, json, yaml, argparse, http.client
from urllib.parse import urlparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from patchright.sync_api import sync_playwright

EXIT_SUCCESS = 0
EXIT_FAILED = 1
EXIT_LOGIN_EXPIRED = 2
EXIT_NO_CDP = 3

# Launch-mode only: inject minimal anti-detection when using Patchright's own Chromium.
# NOT used in CDP mode — real Chrome doesn't have --enable-automation, and
# add_init_script() via CDP Page.addScriptToEvaluateOnNewDocument can corrupt
# the network stack (silent ERR_CONNECTION_CLOSED).
INIT_SCRIPT_LAUNCH = """\
Object.defineProperty(navigator, 'webdriver', {get: () => false});
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
"""

CREATOR_PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish"
CREATOR_HOME_URL = "https://creator.xiaohongshu.com"
SIDEBAR_MENUS = ["首页", "笔记管理", "数据看板", "活动中心", "笔记灵感", "创作学院", "创作百科"]
CDP_DEFAULT_PORT = 9222


def log(msg): print(f"[publisher] {msg}", flush=True)


def rand_delay(lo=0.5, hi=1.5):
    time.sleep(random.uniform(lo, hi))


def random_browse(page, name=""):
    """Simulate human browsing: click random sidebar menus, scroll, pause."""
    count = random.randint(2, 5)
    menus = random.sample(SIDEBAR_MENUS, min(count, len(SIDEBAR_MENUS)))
    log(f"  {name}: 浏览 {len(menus)} 个菜单")
    for i, menu in enumerate(menus):
        log(f"    [{i+1}] {menu}")
        clicked = page.evaluate(f"""(m) => {{
            for (const el of document.querySelectorAll('*')) {{
                if (el.innerText && el.innerText.trim() === m && el.offsetParent) {{
                    el.click(); return true;
                }}
            }}
            return false;
        }}""", menu)
        rand_delay(3, 8) if clicked else rand_delay(1, 2)
        for _ in range(random.randint(0, 3)):
            page.evaluate(f"window.scrollBy(0, {random.randint(100, 600)})")
            rand_delay(0.5, 1.5)
        if i < len(menus) - 1 and random.random() > 0.5:
            rand_delay(2, 5)


def human_type(page, text: str, per_char_delay=(60, 180)):
    """Type character by character with random delays."""
    for ch in text:
        page.keyboard.type(ch, delay=random.randint(*per_char_delay))


def human_click(page, locator):
    """Click with random offset inside the element bounding box."""
    try:
        box = locator.bounding_box()
        if box:
            x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
            page.mouse.move(x, y)
            rand_delay(0.1, 0.3)
            page.mouse.click(x, y)
            return
    except Exception:
        pass
    locator.click(force=True, timeout=5000)


def parse_post(post_path: str) -> dict:
    with open(post_path, "r", encoding="utf-8") as f:
        content = f.read()
    meta = {}
    fm = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if fm:
        meta.update(yaml.safe_load(fm.group(1)))
        body = content[fm.end():].strip()
    else:
        body = content
    title = re.match(r'^# (.+)', body)
    meta["title"] = title.group(1).strip()[:20] if title else ""
    if title:
        body = body[title.end():].strip()
    text, tags = body, []
    tag_match = re.search(r'(#[\w一-鿿]+(?:\s*#[\w一-鿿]+)*)$', body.strip())
    if tag_match:
        tags = re.findall(r'#[\w一-鿿]+', tag_match.group(1))
        text = body[:tag_match.start()].strip()
    meta["body"] = text
    meta["hashtags"] = tags
    return meta


# ---------------------------------------------------------------------------
# CDP helpers
# ---------------------------------------------------------------------------

def resolve_cdp_ws_url(endpoint: str) -> str:
    """Resolve a CDP endpoint to its WebSocket URL.

    Handles both raw ws:// URLs and host:port strings. Uses raw http.client
    (not urllib) to avoid system-proxy interference on localhost.
    """
    if endpoint.startswith("ws://") or endpoint.startswith("wss://"):
        return endpoint

    parsed = urlparse(endpoint)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or CDP_DEFAULT_PORT

    conn = http.client.HTTPConnection(host, port, timeout=5)
    conn.request("GET", "/json/version")  # no trailing slash — Chrome 144+ rejects
    resp = conn.getresponse()
    data = json.loads(resp.read())
    conn.close()

    ws_url = data.get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError(f"CDP endpoint {endpoint} returned no webSocketDebuggerUrl")
    return ws_url


def check_cdp_ready(endpoint: str) -> bool:
    """Return True if a Chrome CDP endpoint is listening."""
    try:
        resolve_cdp_ws_url(endpoint)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Publish — CDP mode
# ---------------------------------------------------------------------------

def _fill_content(page, post):
    """Fill title, body, and tags on the publish page (shared by both modes)."""

    # --- Title ---
    log(f"填写标题: {post['title'][:30]}")
    rand_delay(1, 2)
    title_el = page.locator('input.d-text').first
    if not title_el.count():
        title_el = page.locator('[placeholder*="填写标题"]').first
    if title_el.count():
        human_click(page, title_el)
        title_el.fill("")
        human_type(page, post["title"][:20])
    else:
        log("WARN: 未找到标题输入框")

    # --- Body ---
    log("填写正文...")
    rand_delay(1, 2)
    body_el = page.locator('div.tiptap').first
    if not body_el.count():
        body_el = page.locator('div.ProseMirror').first
    if not body_el.count():
        body_el = page.locator('[contenteditable="true"]').first

    if body_el.count():
        human_click(page, body_el)
        segments = [s.strip() for s in post["body"].split('\n') if s.strip()]
        if segments:
            first = segments[0]
            human_type(page, first[:10], per_char_delay=(40, 100))
            page.keyboard.insert_text(first[10:])
            page.keyboard.press("Enter")
            rand_delay(0.3, 0.6)
            for seg in segments[1:]:
                page.keyboard.insert_text(seg)
                page.keyboard.press("Enter")
                rand_delay(0.2, 0.4)
        log("正文已填写")
    else:
        log("WARN: 未找到正文编辑器")

    # --- Tags ---
    if post.get("hashtags"):
        log(f"添加标签: {post['hashtags']}")
        rand_delay(1, 2)
        tag_btn = page.locator('.topic-btn').first
        if not tag_btn.count():
            tag_btn = page.locator('button').filter(has_text="话题").first
        if tag_btn.count():
            human_click(page, tag_btn)
            rand_delay(1, 2)
        for tag in post["hashtags"]:
            page.keyboard.insert_text(tag)
            rand_delay(0.5, 1)
            page.keyboard.press("Enter")
            rand_delay(0.3, 0.5)


def _check_login(page, state_file=None, ctx=None) -> bool:
    """Return True if logged in to creator center."""
    if page.locator('[placeholder*="手机号"]').first.count():
        return False
    return True


def _publish_cdp(args, post, account, state_file):
    """CDP mode: connect to the user's real Chrome via --remote-debugging-port.

    No add_init_script() (breaks network stack in CDP mode).
    No new_context() (isolated context breaks TLS in CDP mode).
    No User-Agent override (Chrome's own UA is the best UA).
    """
    log(f"CDP 模式: 连接 {args.cdp_endpoint}")

    if not check_cdp_ready(args.cdp_endpoint):
        log(f"ERROR: Chrome CDP 未在 {args.cdp_endpoint} 监听")
        log("请先运行: scripts/launch_chrome_cdp.bat")
        sys.exit(EXIT_NO_CDP)

    ws_url = resolve_cdp_ws_url(args.cdp_endpoint)
    log(f"WebSocket: {ws_url}")

    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(ws_url)
        ctx = browser.contexts[0]  # Chrome's real default context

        # Inject cookies from stored state (if available) so the CDP Chrome
        # picks up any session that was saved outside the profile.
        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            cookies = saved.get("cookies", [])
            if cookies:
                ctx.add_cookies(cookies)
                log(f"已注入 {len(cookies)} 个 cookie")

        # Use existing page or create one
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})

        # --- Step 1: Open publish page ---
        log("Step 1: 打开发布页面...")
        page.goto(CREATOR_PUBLISH_URL, wait_until="networkidle", timeout=30000)
        rand_delay(2, 4)

        if not _check_login(page):
            log("ERROR: 创作者中心未登录 — 请在 Chrome 窗口中人工登录后重试")
            sys.exit(EXIT_LOGIN_EXPIRED)
        log("已登录 ✓")

        # --- Random browse before publishing ---
        log("反检测: 随机浏览创作者中心...")
        random_browse(page, name="发布前")
        page.goto(CREATOR_PUBLISH_URL, wait_until="networkidle", timeout=30000)
        rand_delay(2, 3)

        # --- Step 2: Upload images ---
        log("Step 2: 上传图片...")
        images_dir = os.path.join(args.draft_dir, "images")
        if os.path.isdir(images_dir):
            images = sorted(
                [f for f in os.listdir(images_dir)
                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
            if images:
                file_input = page.locator('input.upload-input').first
                if file_input.count():
                    paths = [os.path.join(images_dir, img).replace('\\', '/') for img in images]
                    file_input.set_input_files(paths)
                    log(f"已选择 {len(paths)} 张图片, 等待上传...")
                    rand_delay(4, 6)
                else:
                    log("WARN: 未找到图片上传input")
            else:
                log("无图片文件")
        else:
            log("无图片目录")

        # --- Steps 3-5: Fill content ---
        _fill_content(page, post)

        # --- Step 6: Publish ---
        log("Step 6: 点击发布...")
        rand_delay(2, 3)
        publish_btn = page.locator('button.d-button').filter(has_text="发布").first
        if not publish_btn.count():
            publish_btn = page.locator('button').filter(has_text="发布").first
        if publish_btn.count():
            human_click(page, publish_btn)
            rand_delay(5, 8)
            log("已点击发布")
        else:
            log("WARN: 未找到发布按钮")

        log("笔记已提交审核（5-10分钟后可在笔记管理查看）")

        # --- Random browse after publishing ---
        log("反检测: 发布后随机浏览...")
        random_browse(page, name="发布后")

        # Save cookies snapshot for portability
        cookies = ctx.cookies()
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"cookies": cookies}, f, ensure_ascii=False, indent=2)

        result = {"success": True, "url": page.url, "title": post["title"]}
        print(f"RESULT: {json.dumps(result, ensure_ascii=False)}")
        log("Done ✓")


# ---------------------------------------------------------------------------
# Publish — fallback launch mode (Patchright's own Chromium)
# ---------------------------------------------------------------------------

def _publish_launch(args, post, account, state_file):
    """Fallback: Patchright launches its own Chromium.

    Still better than vanilla Playwright (CDP-level patches for Runtime.enable,
    Console.enable, navigator.webdriver), but the fresh browser fingerprint is
    more detectable than a real Chrome with history.
    """
    log("Launch 模式: Patchright 自启动 Chromium")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled",
                  "--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
        )
        ctx_kwargs = {
            "viewport": {"width": 1280, "height": 900},
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
        }
        if os.path.exists(state_file):
            ctx_kwargs["storage_state"] = state_file

        ctx = browser.new_context(**ctx_kwargs)
        ctx.add_init_script(INIT_SCRIPT_LAUNCH)
        page = ctx.new_page()

        # --- Step 1: Open publish page ---
        log("Step 1: 打开发布页面...")
        page.goto(CREATOR_PUBLISH_URL, wait_until="networkidle", timeout=30000)
        rand_delay(2, 4)

        if not _check_login(page):
            log("ERROR: 创作者中心未登录")
            ctx.storage_state(path=state_file)
            browser.close()
            sys.exit(EXIT_LOGIN_EXPIRED)
        log("已登录 ✓")

        # --- Random browse before publishing ---
        log("反检测: 随机浏览创作者中心...")
        random_browse(page, name="发布前")
        page.goto(CREATOR_PUBLISH_URL, wait_until="networkidle", timeout=30000)
        rand_delay(2, 3)

        # --- Step 2: Upload images ---
        log("Step 2: 上传图片...")
        images_dir = os.path.join(args.draft_dir, "images")
        if os.path.isdir(images_dir):
            images = sorted(
                [f for f in os.listdir(images_dir)
                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
            if images:
                file_input = page.locator('input.upload-input').first
                if file_input.count():
                    paths = [os.path.join(images_dir, img).replace('\\', '/') for img in images]
                    file_input.set_input_files(paths)
                    log(f"已选择 {len(paths)} 张图片, 等待上传...")
                    rand_delay(4, 6)
                else:
                    log("WARN: 未找到图片上传input")
            else:
                log("无图片文件")
        else:
            log("无图片目录")

        # --- Steps 3-5: Fill content ---
        _fill_content(page, post)

        # --- Step 6: Publish ---
        log("Step 6: 点击发布...")
        rand_delay(2, 3)
        publish_btn = page.locator('button.d-button').filter(has_text="发布").first
        if not publish_btn.count():
            publish_btn = page.locator('button').filter(has_text="发布").first
        if publish_btn.count():
            human_click(page, publish_btn)
            rand_delay(5, 8)
            log("已点击发布")
        else:
            log("WARN: 未找到发布按钮")

        log("笔记已提交审核（5-10分钟后可在笔记管理查看）")

        # --- Random browse after publishing ---
        log("反检测: 发布后随机浏览...")
        random_browse(page, name="发布后")

        ctx.storage_state(path=state_file)
        browser.close()

        result = {"success": True, "url": page.url, "title": post["title"]}
        print(f"RESULT: {json.dumps(result, ensure_ascii=False)}")
        log("Done ✓")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def publish(args):
    post_path = os.path.join(args.draft_dir, "post.md")
    if not os.path.exists(post_path):
        log(f"ERROR: {post_path} not found")
        sys.exit(EXIT_FAILED)

    post = parse_post(post_path)
    accounts = yaml.safe_load(open(args.accounts_config, encoding="utf-8"))
    account = next((a for a in accounts["accounts"] if a["id"] == args.account_id), None)
    if not account:
        log(f"ERROR: account {args.account_id} not found")
        sys.exit(EXIT_FAILED)

    state_dir = account.get("user_data_dir", f"accounts/{args.account_id}/")
    state_file = os.path.join(state_dir, "state.json")

    if args.no_cdp:
        _publish_launch(args, post, account, state_file)
    else:
        _publish_cdp(args, post, account, state_file)


def main():
    p = argparse.ArgumentParser(description="小红书笔记发布")
    p.add_argument("--draft-dir", required=True, help="草稿目录路径")
    p.add_argument("--account-id", required=True, help="发布账号ID")
    p.add_argument("--accounts-config", required=True, help="accounts.yaml 路径")
    p.add_argument("--headless", action="store_true", default=True,
                   help="无头模式 (仅 launch 模式生效)")
    p.add_argument("--cdp-endpoint", default=f"127.0.0.1:{CDP_DEFAULT_PORT}",
                   help=f"CDP 调试地址 (默认 127.0.0.1:{CDP_DEFAULT_PORT})")
    p.add_argument("--no-cdp", action="store_true",
                   help="使用 launch 模式而非 CDP 模式")
    publish(p.parse_args())


if __name__ == "__main__":
    main()
