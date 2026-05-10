"""Playwright publishing script for Xiaohongshu."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import argparse
import json
import os
import re
import sys
import time
import random
import yaml
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


def log(msg: str):
    print(f"[publisher] {msg}", flush=True)


def parse_post_md(post_path: str) -> dict:
    with open(post_path, "r", encoding="utf-8") as f:
        content = f.read()
    meta = {}
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        meta.update(yaml.safe_load(fm_match.group(1)))
        body = content[fm_match.end():].strip()
    else:
        body = content

    title_match = re.match(r'^# (.+)', body)
    title = title_match.group(1).strip()[:20] if title_match else ""
    if title_match:
        body = body[title_match.end():].strip()

    text, tags = body, []
    tag_match = re.search(r'(#[\w一-鿿]+(?:\s*#[\w一-鿿]+)*)$', body.strip())
    if tag_match:
        tags = re.findall(r'#[\w一-鿿]+', tag_match.group(1))
        text = body[:tag_match.start()].strip()

    meta["title"] = title
    meta["body"] = text
    meta["hashtags"] = tags
    return meta


def is_logged_in(page) -> bool:
    """Check if user is logged in to main site."""
    current_url = page.url
    if "login" in current_url.lower():
        return False
    try:
        login_btns = page.locator('text=登录').all()
        if len(login_btns) > 0:
            return False
    except Exception:
        pass
    return True


def is_creator_accessible(page) -> bool:
    """Check if creator center is accessible (not showing phone login form)."""
    current_url = page.url
    if "login" in current_url.lower():
        return False
    # Check for phone login form which the creator center shows when auth is needed
    try:
        phone_input = page.locator('[placeholder*="手机号"]').first
        if phone_input.count() and phone_input.is_visible(timeout=2000):
            return False
    except Exception:
        pass
    try:
        code_input = page.locator('[placeholder*="验证码"]').first
        if code_input.count() and code_input.is_visible(timeout=2000):
            return False
    except Exception:
        pass
    return True


def publish(args):
    post_path = os.path.join(args.draft_dir, "post.md")
    if not os.path.exists(post_path):
        log(f"ERROR: post.md not found at {post_path}")
        sys.exit(EXIT_FAILED)

    post = parse_post_md(post_path)
    images_dir = os.path.join(args.draft_dir, "images")
    accounts = yaml.safe_load(open(args.accounts_config, encoding="utf-8"))
    account = next((a for a in accounts["accounts"] if a["id"] == args.account_id), None)
    if not account:
        log(f"ERROR: account {args.account_id} not found")
        sys.exit(EXIT_FAILED)

    user_data_dir = account.get("user_data_dir", f"accounts/{args.account_id}/")
    state_file = os.path.join(user_data_dir, "state.json")
    os.makedirs(user_data_dir, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        context = browser.new_context(
            storage_state=state_file if os.path.exists(state_file) else None,
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        context.add_init_script(INIT_SCRIPT)
        page = context.new_page()

        # === Step 1: Check login on main site ===
        log("Step 1: 访问小红书首页...")
        page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
        time.sleep(3)

        if not is_logged_in(page):
            log("ERROR: 未登录或登录已失效")
            context.storage_state(path=state_file)
            browser.close()
            sys.exit(EXIT_LOGIN_EXPIRED)

        log("Step 1: 已登录 ✓")

        # === Step 2: Navigate to creator center ===
        log("Step 2: 通过主页进入创作者中心...")
        # Must navigate through main site UI for SSO token transfer
        # Direct URL navigation to creator.xiaohongshu.com will fail (no cross-domain auth)

        # Try finding the "创作" entry in user dropdown
        page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
        time.sleep(2)

        # Take debug screenshot to see what the page looks like
        if args.debug:
            page.screenshot(path=os.path.join(user_data_dir, "debug_main_page.png"))

        creator_opened = False

        # Method 1: Click user avatar in top-right, then find creator center in dropdown
        avatar_selectors = [
            '[class*="user-avatar"]', '[class*="avatar-wrapper"]', '[class*="avatar"] img',
            '[class*="header"] [class*="avatar"]', '.side-bar [class*="avatar"]',
            'img[class*="avatar"]', '[data-testid="avatar"]',
        ]
        for sel in avatar_selectors:
            try:
                el = page.locator(sel).first
                if el.count() and el.is_visible(timeout=2000):
                    el.click()
                    time.sleep(2)
                    log(f"  点击头像: {sel}")
                    break
            except Exception:
                continue

        # After clicking avatar, look for creator center in dropdown
        dropdown_selectors = [
            'text=创作服务平台', 'text=创作者中心', 'text=创作中心',
            'a[href*="creator"]', '[class*="dropdown"] a[href*="creator"]',
            'a:has-text("创作")', 'text=发布笔记',
        ]
        for sel in dropdown_selectors:
            try:
                link = page.locator(sel).first
                if link.count() and link.is_visible(timeout=3000):
                    # Get the actual href for SSO tokens
                    href = link.get_attribute('href') or ''
                    log(f"  找到创作者中心入口: {sel} -> {href}")
                    link.click()
                    time.sleep(5)
                    creator_opened = True
                    break
            except Exception:
                continue

        if not creator_opened:
            # Method 2: Look for a "发布" button in the sidebar that leads to creator
            sidebar_selectors = [
                '[class*="side"] a[href*="creator"]', '[class*="nav"] a[href*="creator"]',
                'a[href*="creator.xiaohongshu"]',
            ]
            for sel in sidebar_selectors:
                try:
                    link = page.locator(sel).first
                    if link.count() and link.is_visible(timeout=2000):
                        link.click()
                        time.sleep(5)
                        creator_opened = True
                        log(f"  通过侧边栏进入: {sel}")
                        break
                except Exception:
                    continue

        if not creator_opened:
            # Method 3: Try with page.click at specific coordinates where avatar usually is
            log("  UI方式未找到入口，尝试坐标点击...")
            try:
                # Top-right area click (where avatar usually is)
                page.mouse.click(1200, 40)
                time.sleep(1)
                page.mouse.click(1200, 40)
                time.sleep(2)
                # Try finding creator link again
                link = page.locator('a[href*="creator"]').first
                if link.count() and link.is_visible(timeout=2000):
                    link.click()
                    time.sleep(5)
                    creator_opened = True
            except Exception:
                pass

        # Wait for navigation to settle
        time.sleep(3)
        current_url = page.url

        # Check if we reached the creator center (either main or publish page)
        if "creator.xiaohongshu.com" in current_url and "login" not in current_url.lower():
            if not is_creator_accessible(page):
                log("ERROR: 创作者中心需要手机号登录，请运行 scripts/login.py 重新登录")
                context.storage_state(path=state_file)
                browser.close()
                sys.exit(EXIT_LOGIN_EXPIRED)
            log(f"  创作者中心已进入: {current_url}")
            # Navigate to publish page if not already there
            if "/publish" not in current_url:
                page.goto("https://creator.xiaohongshu.com/publish/publish", wait_until="networkidle", timeout=30000)
                time.sleep(3)
        elif "login" in current_url.lower() or "401" in current_url:
            log(f"ERROR: 创作者中心需要登录，请重新运行 scripts/login.py (URL: {current_url})")
            context.storage_state(path=state_file)
            browser.close()
            sys.exit(EXIT_LOGIN_EXPIRED)

        log("Step 2: 创作者中心已进入 ✓")

        # === Step 3: Handle any popups ===
        log("Step 3: 处理弹窗...")
        for _ in range(3):
            try:
                # Various close button patterns
                close_selectors = [
                    '[class*="close"]',
                    'text=我知道了',
                    'text=跳过',
                    '[class*="dialog"] [class*="btn"]',
                    '.modal-close',
                ]
                for sel in close_selectors:
                    btn = page.locator(sel).first
                    if btn.count() and btn.is_visible(timeout=1000):
                        btn.click()
                        time.sleep(0.5)
            except Exception:
                pass

        # === Step 4: Wait for publish form to load ===
        log("Step 4: 等待发布表单加载...")
        time.sleep(3)
        # Take screenshot for debugging
        if args.debug:
            page.screenshot(path=os.path.join(user_data_dir, "debug_after_load.png"))
            log(f"Debug screenshot saved to {user_data_dir}/debug_after_load.png")

        # === Step 5: Upload images ===
        log("Step 5: 上传图片...")
        if os.path.isdir(images_dir):
            images = sorted([f for f in os.listdir(images_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
            if images:
                # Try multiple file input selectors
                for file_selector in ['input[type="file"]', '[class*="upload"] input', 'input[accept*="image"]']:
                    file_input = page.locator(file_selector).first
                    if file_input.count():
                        paths = [os.path.join(images_dir, img).replace('\\', '/') for img in images]
                        log(f"  上传 {len(paths)} 张图片...")
                        file_input.set_input_files(paths)
                        time.sleep(3 + len(images))
                        log(f"  图片上传完成")
                        break
                else:
                    log("  WARN: 未找到图片上传入口")
            else:
                log("  没有图片文件")
        else:
            log(f"  图片目录不存在: {images_dir}")

        time.sleep(random.uniform(2, 4))

        # === Step 6: Fill title ===
        log(f"Step 6: 填写标题: {post['title'][:30]}...")
        title_selectors = [
            'input[placeholder*="标题"]',
            '[class*="title"] input',
            '#title',
            '[data-placeholder*="标题"]',
        ]
        for sel in title_selectors:
            el = page.locator(sel).first
            if el.count() and el.is_visible(timeout=2000):
                el.click()
                el.fill("")  # Clear
                for char in post["title"][:20]:
                    page.keyboard.type(char, delay=random.randint(80, 200))
                log("  标题填写完成")
                break
        else:
            log("  WARN: 未找到标题输入框")

        time.sleep(random.uniform(2, 4))

        # === Step 7: Fill body ===
        log("Step 7: 填写正文...")
        body_selectors = [
            '[placeholder*="正文"]',
            '[contenteditable="true"]',
            '[class*="editor"]',
            'textarea',
            '#content',
        ]
        for sel in body_selectors:
            el = page.locator(sel).first
            if el.count() and el.is_visible(timeout=2000):
                el.click()
                body_text = post["body"]
                segments = [s for s in body_text.split('\n') if s.strip()]
                if not segments:
                    segments = [body_text]
                for seg in segments:
                    page.keyboard.type(seg.strip(), delay=random.randint(40, 100))
                    page.keyboard.press("Enter")
                    time.sleep(0.3)
                log("  正文填写完成")
                break
        else:
            log("  WARN: 未找到正文输入框")

        time.sleep(random.uniform(2, 4))

        # === Step 8: Add hashtags ===
        if post.get("hashtags"):
            log(f"Step 8: 添加标签: {post['hashtags']}")
            tag_selectors = [
                '[placeholder*="标签"]',
                '[class*="tag"] input',
                '[class*="hashtag"] input',
            ]
            tag_input = None
            for sel in tag_selectors:
                el = page.locator(sel).first
                if el.count() and el.is_visible(timeout=2000):
                    tag_input = el
                    break

            if tag_input:
                for tag in post["hashtags"]:
                    tag_input.click()
                    page.keyboard.type(tag, delay=random.randint(80, 150))
                    page.keyboard.press("Enter")
                    time.sleep(0.8)
                log("  标签添加完成")
            else:
                # Try typing in body area with # format
                log("  未找到独立标签输入，尝试在正文末尾添加...")
                body_el = page.locator('[contenteditable="true"], textarea').first
                if body_el.count():
                    body_el.click()
                    page.keyboard.press("End")
                    page.keyboard.press("Enter")
                    page.keyboard.press("Enter")
                    for tag in post["hashtags"]:
                        page.keyboard.type(f"{tag} ", delay=random.randint(80, 150))
                    time.sleep(1)

        time.sleep(random.uniform(2, 3))

        # Take pre-submit screenshot
        if args.debug:
            page.screenshot(path=os.path.join(user_data_dir, "debug_before_submit.png"))
            log(f"Debug: pre-submit screenshot saved")

        # === Step 9: Submit ===
        log("Step 9: 提交发布...")
        submit_selectors = [
            'button:has-text("发布")',
            '[class*="publish"] button',
            '[class*="submit"] button',
            'button:has-text("确定")',
            'button:has-text("提交")',
        ]
        submitted = False
        for sel in submit_selectors:
            btn = page.locator(sel).first
            if btn.count():
                try:
                    btn.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    btn.click(timeout=5000)
                    submitted = True
                    log(f"  点击发布按钮: {sel}")
                    break
                except Exception as e:
                    log(f"  尝试 {sel} 失败: {e}")

        if not submitted:
            log("  WARN: 未找到发布按钮，请检查页面截图")

        # Wait for success/redirect
        time.sleep(5)
        page.wait_for_timeout(3000)

        # === Step 10: Capture result ===
        current_url = page.url
        log(f"Step 10: 发布完成，当前URL: {current_url}")

        result = {
            "success": submitted,
            "url": current_url,
            "title": post["title"],
            "persona": account.get("persona", ""),
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        context.storage_state(path=state_file)
        browser.close()
        print(f"RESULT: {json.dumps(result, ensure_ascii=False)}")
        sys.exit(EXIT_SUCCESS if submitted else EXIT_FAILED)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--draft-dir", required=True)
    p.add_argument("--account-id", required=True)
    p.add_argument("--accounts-config", required=True)
    p.add_argument("--headless", action="store_true", default=True)
    p.add_argument("--debug", action="store_true", default=False)
    publish(p.parse_args())


if __name__ == "__main__":
    main()
