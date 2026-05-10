"""Publish a Xiaohongshu draft via Playwright browser automation."""
import io, os, re, sys, time, random, json, yaml, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

INIT_SCRIPT = """\
Object.defineProperty(navigator, 'webdriver', {get: () => false});
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
"""

EXIT_SUCCESS = 0
EXIT_FAILED = 1
EXIT_LOGIN_EXPIRED = 2


def log(msg): print(f"[publisher] {msg}", flush=True)


def rand_delay(lo=0.5, hi=1.5):
    time.sleep(random.uniform(lo, hi))

# Creator center sidebar menus to randomly browse for anti-detection
SIDEBAR_MENUS = ["首页", "笔记管理", "数据看板", "活动中心", "笔记灵感", "创作学院", "创作百科"]

def random_browse(page, count=2):
    """Randomly click a few sidebar menus to simulate human browsing."""
    menus = random.sample(SIDEBAR_MENUS, min(count, len(SIDEBAR_MENUS)))
    for menu in menus:
        log(f"  浏览: {menu}")
        clicked = page.evaluate(f"""(m) => {{
            for (const el of document.querySelectorAll('*')) {{
                if (el.innerText && el.innerText.trim() === m && el.offsetParent) {{
                    el.click(); return true;
                }}
            }}
            return false;
        }}""", menu)
        if clicked:
            rand_delay(3, 8)  # Simulate reading time
        else:
            rand_delay(1, 2)


def human_type(page, text: str, per_char_delay=(60, 180)):
    """Type character by character with random delays."""
    for ch in text:
        page.keyboard.type(ch, delay=random.randint(*per_char_delay))


def human_click(page, locator):
    """Click with random offset, force=True for elements outside viewport."""
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


def publish(args):
    post_path = os.path.join(args.draft_dir, "post.md")
    images_dir = os.path.join(args.draft_dir, "images")
    if not os.path.exists(post_path):
        log(f"ERROR: {post_path} not found"); sys.exit(EXIT_FAILED)

    post = parse_post(post_path)
    accounts = yaml.safe_load(open(args.accounts_config, encoding="utf-8"))
    account = next((a for a in accounts["accounts"] if a["id"] == args.account_id), None)
    if not account:
        log(f"ERROR: account {args.account_id} not found"); sys.exit(EXIT_FAILED)

    state_file = os.path.join(account.get("user_data_dir", f"accounts/{args.account_id}/"), "state.json")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=args.headless,
            args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
        )
        context = browser.new_context(
            storage_state=state_file if os.path.exists(state_file) else None,
            viewport={"width": 1280, "height": 900},
            locale="zh-CN", timezone_id="Asia/Shanghai",
        )
        context.add_init_script(INIT_SCRIPT)
        page = context.new_page()

        # === Step 1: Open publish page ===
        log("Step 1: 打开发布页面...")
        page.goto("https://creator.xiaohongshu.com/publish/publish", wait_until="networkidle", timeout=30000)
        rand_delay(2, 4)

        # Check login
        if page.locator('[placeholder*="手机号"]').first.count():
            log("ERROR: 创作者中心未登录")
            context.storage_state(path=state_file)
            browser.close()
            sys.exit(EXIT_LOGIN_EXPIRED)
        log("已登录")

        # === Random browse before publishing ===
        log("反检测: 随机浏览创作者中心...")
        random_browse(page, count=random.randint(2, 4))
        page.goto("https://creator.xiaohongshu.com/publish/publish", wait_until="networkidle", timeout=30000)
        rand_delay(2, 3)

        # === Step 2: Click "上传图文" tab ===
        log("Step 2: 切换到上传图文...")
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
        if clicked:
            log("已切换到上传图文")
        else:
            log("WARN: 未找到上传图文")
        rand_delay(3, 5)

        # === Step 3: Upload images ===
        log("Step 3: 上传图片...")
        if os.path.isdir(images_dir):
            images = sorted([f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
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

        # === Step 4: Fill title ===
        log(f"Step 4: 填写标题...")
        rand_delay(1, 2)
        # Actual element: <INPUT class='d-text' placeholder='填写标题会有更多赞哦'>
        title_el = page.locator('input.d-text').first
        if not title_el.count():
            title_el = page.locator('[placeholder*="填写标题"]').first
        if title_el.count():
            human_click(page, title_el)
            title_el.fill("")  # Clear existing text
            human_type(page, post["title"][:20])
            log(f"标题已填写: {post['title'][:30]}")
        else:
            log("WARN: 未找到标题输入框")

        # === Step 5: Fill body ===
        log("Step 5: 填写正文...")
        rand_delay(1, 2)
        # Actual element: <DIV class='tiptap ProseMirror' contenteditable>
        body_el = page.locator('div.tiptap').first
        if not body_el.count():
            body_el = page.locator('div.ProseMirror').first
        if not body_el.count():
            body_el = page.locator('[contenteditable="true"]').first

        if body_el.count():
            human_click(page, body_el)
            body_text = post["body"]
            segments = [s.strip() for s in body_text.split('\n') if s.strip()]
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

        # === Step 6: Add tags ===
        if post.get("hashtags"):
            log(f"Step 6: 添加标签...")
            rand_delay(1, 2)
            # Click "话题" button first to open tag input
            tag_btn = page.locator('.topic-btn').first
            if not tag_btn.count():
                tag_btn = page.locator('button').filter(has_text="话题").first
            if tag_btn.count():
                human_click(page, tag_btn)
                rand_delay(1, 2)
            # Type tags in the input that appears
            for tag in post["hashtags"]:
                page.keyboard.insert_text(tag)
                rand_delay(0.5, 1)
                page.keyboard.press("Enter")
                rand_delay(0.3, 0.5)
            log("标签已添加")

        rand_delay(2, 3)

        # === Step 7: Publish ===
        log("Step 7: 点击发布...")
        publish_btn = page.locator('button.d-button').filter(has_text="发布").first
        if not publish_btn.count():
            publish_btn = page.locator('button').filter(has_text="发布").first
        if publish_btn.count():
            human_click(page, publish_btn)
            rand_delay(5, 8)
            log("已点击发布")
        else:
            log("WARN: 未找到发布按钮")

        # === Step 8: Collect note ID from profile page ===
        log("Step 8: 获取笔记ID...")
        note_id = ""
        # Try to get user profile URL from current page first
        user_link = page.evaluate("""() => {
            const links = document.querySelectorAll('a[href*="/user/profile/"]');
            for (const l of links) {
                const href = l.href || '';
                const m = href.match(/\\/user\\/profile\\/([a-f0-9]+)/);
                if (m) return m[1];
            }
            return '';
        }""")

        if user_link:
            page.goto(f"https://www.xiaohongshu.com/user/profile/{user_link}", wait_until="networkidle", timeout=30000)
        else:
            page.goto("https://www.xiaohongshu.com/explore", wait_until="networkidle", timeout=30000)
            rand_delay(2, 4)
            page.goto(f"https://www.xiaohongshu.com/user/profile/5f3a4b050000000001006d74", wait_until="networkidle", timeout=30000)

        rand_delay(3, 5)
        # Extract the most recent note link
        note_id = page.evaluate("""() => {
            const links = document.querySelectorAll('a[href*="/explore/"]');
            for (const link of links) {
                const href = link.href || '';
                // Skip non-note explore links (homefeed etc)
                if (href.includes('channel_id') || href.includes('channel_type')) continue;
                const m = href.match(/\\/explore\\/([a-f0-9]+)/);
                if (m && m[1].length > 10) return m[1];
            }
            return '';
        }""")
        if note_id:
            log(f"笔记ID: {note_id}")
        else:
            log("WARN: 无法自动提取笔记ID")

        # === Random browse after publishing ===
        log("反检测: 发布后随机浏览...")
        random_browse(page, count=random.randint(1, 2))

        # Save state
        context.storage_state(path=state_file)
        browser.close()

        result = {"success": True, "url": page.url, "title": post["title"]}
        print(f"RESULT: {json.dumps(result, ensure_ascii=False)}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--draft-dir", required=True)
    p.add_argument("--account-id", required=True)
    p.add_argument("--accounts-config", required=True)
    p.add_argument("--headless", action="store_true", default=True)
    publish(p.parse_args())


if __name__ == "__main__":
    main()
