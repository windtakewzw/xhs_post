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
        # The title is usually a contenteditable or input at the top of the editor
        title_selectors = [
            '[placeholder*="标题"]',
            '.title-input',
            '[class*="title"] [contenteditable]',
            '[contenteditable="true"]',
        ]
        title_el = None
        for sel in title_selectors:
            el = page.locator(sel).first
            if el.count() and el.is_visible(timeout=2000):
                title_el = el
                break

        if title_el:
            human_click(page, title_el)
            human_type(page, post["title"][:20])
            log(f"标题已填写: {post['title'][:30]}")
        else:
            log("WARN: 未找到标题输入框，尝试键盘输入...")
            page.keyboard.press("Tab")
            rand_delay(0.3, 0.5)
            human_type(page, post["title"][:20])

        # === Step 5: Fill body ===
        log("Step 5: 填写正文...")
        rand_delay(1, 2)
        body_selectors = [
            '[placeholder*="正文"]',
            '[contenteditable="true"]',
            '[class*="editor"] [contenteditable]',
            '[class*="body"] [contenteditable]',
            'textarea',
        ]
        body_el = None
        for sel in body_selectors:
            el = page.locator(sel).first
            if el.count() and el.is_visible(timeout=2000):
                body_el = el
                break

        if body_el:
            human_click(page, body_el)
            body_text = post["body"]
            segments = [s.strip() for s in body_text.split('\n') if s.strip()]
            if segments:
                first = segments[0]
                if len(first) > 15:
                    human_type(page, first[:12], per_char_delay=(40, 100))
                    page.keyboard.insert_text(first[12:])
                else:
                    human_type(page, first, per_char_delay=(40, 100))
                page.keyboard.press("Enter")
                rand_delay(0.3, 0.6)
                for seg in segments[1:]:
                    page.keyboard.insert_text(seg)
                    page.keyboard.press("Enter")
                    rand_delay(0.3, 0.6)
            log("正文已填写")
        else:
            log("WARN: 未找到正文输入框，尝试insert...")
            page.keyboard.insert_text(post["body"])

        # === Step 6: Add tags ===
        if post.get("hashtags"):
            log(f"Step 6: 添加标签...")
            rand_delay(1, 2)
            # Look for tag input or type #tags in body
            tag_el = page.locator('[placeholder*="标签"], [placeholder*="话题"]').first
            if tag_el.count() and tag_el.is_visible(timeout=2000):
                human_click(page, tag_el)
                for tag in post["hashtags"]:
                    human_type(page, tag + " ")
                    rand_delay(0.3, 0.8)
                    page.keyboard.press("Enter")
            elif body_el:
                human_click(page, body_el)
                page.keyboard.press("End")
                page.keyboard.press("Enter")
                page.keyboard.press("Enter")
                for tag in post["hashtags"]:
                    human_type(page, tag + " ")
            log("标签已添加")

        rand_delay(2, 3)

        # === Step 7: Publish ===
        log("Step 7: 点击发布...")
        # Find publish button - avoid Chinese in CSS pseudo-selectors
        publish_btn = page.locator('button').filter(has_text="发布").first
        if not publish_btn.count():
            publish_btn = page.locator('[class*="publish"]').first
        if not publish_btn.count():
            publish_btn = page.locator('text=发布').first
        if publish_btn.count():
            human_click(page, publish_btn)
            rand_delay(3, 5)
            log("已点击发布")
        else:
            log("WARN: 未找到发布按钮")

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
