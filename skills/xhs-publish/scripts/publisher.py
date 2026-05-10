"""Playwright publishing script for Xiaohongshu."""
import argparse
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


def parse_post_md(post_path: str) -> dict:
    with open(post_path, "r", encoding="utf-8") as f:
        content = f.read()
    meta = {}
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        meta = yaml.safe_load(fm_match.group(1))
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


def human_type(page, selector: str, text: str):
    el = page.locator(selector)
    if el.count():
        el.click()
        for char in text:
            page.keyboard.type(char, delay=random.randint(80, 200))


def publish(args):
    post = parse_post_md(os.path.join(args.draft_dir, "post.md"))
    images_dir = os.path.join(args.draft_dir, "images")
    accounts = yaml.safe_load(open(args.accounts_config, encoding="utf-8"))
    account = next((a for a in accounts["accounts"] if a["id"] == args.account_id), None)
    if not account:
        print(f"Error: account {args.account_id} not found")
        sys.exit(EXIT_FAILED)

    user_data_dir = account.get("user_data_dir", f"data/accounts/{args.account_id}/")
    state_file = os.path.join(user_data_dir, "state.json")
    os.makedirs(user_data_dir, exist_ok=True)

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=args.headless)
            context = browser.new_context(
                storage_state=state_file if os.path.exists(state_file) else None,
                viewport={"width": 1280, "height": 900},
                locale="zh-CN", timezone_id="Asia/Shanghai",
            )
            context.add_init_script(INIT_SCRIPT)
            page = context.new_page()

            # Step 1-2: Check login
            page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")
            time.sleep(random.uniform(2, 4))

            if page.locator('text=登录').count() > 0 or "login" in page.url.lower():
                context.storage_state(path=state_file)
                browser.close()
                print("LOGIN_EXPIRED")
                sys.exit(EXIT_LOGIN_EXPIRED)

            # Step 3: Close popups
            try:
                close_btn = page.locator('[class*="close"]').first
                if close_btn.is_visible(timeout=3000):
                    close_btn.click()
                    time.sleep(1)
            except Exception:
                pass

            # Step 4: Enter creator center
            page.goto("https://creator.xiaohongshu.com/publish/publish", wait_until="domcontentloaded")
            time.sleep(random.uniform(2, 4))

            # Step 5: Upload images
            if os.path.isdir(images_dir):
                images = sorted([f for f in os.listdir(images_dir) if f.endswith(('.jpg', '.png'))])
                if images:
                    paths = [os.path.join(images_dir, img) for img in images]
                    file_input = page.locator('input[type="file"]')
                    if file_input.count():
                        file_input.set_input_files(paths)
                        time.sleep(3)

            time.sleep(random.uniform(2, 4))

            # Step 6: Fill title
            human_type(page, '[placeholder*="标题"]', post["title"][:20])

            time.sleep(random.uniform(2, 4))

            # Step 7: Fill body
            body_el = page.locator('[placeholder*="正文"]')
            if body_el.count() and post["body"]:
                body_el.click()
                for seg in post["body"].split('\n'):
                    if seg.strip():
                        page.keyboard.type(seg.strip(), delay=random.randint(40, 100))
                    page.keyboard.press("Enter")
                    time.sleep(0.3)

            time.sleep(random.uniform(2, 4))

            # Step 8: Add hashtags
            tag_input = page.locator('[placeholder*="标签"]')
            if tag_input.count() and post.get("hashtags"):
                for tag in post["hashtags"]:
                    page.keyboard.type(tag, delay=random.randint(80, 150))
                    page.keyboard.press("Enter")
                    time.sleep(0.5)

            time.sleep(random.uniform(1, 2))

            # Step 9: Submit
            submit_btn = page.locator('button:has-text("发布")')
            if submit_btn.count():
                submit_btn.click()
                time.sleep(5)

            # Step 10: Collect note ID
            page.wait_for_timeout(3000)
            note_id = page.url.split('/')[-1] if '/' in page.url else "unknown"

            context.storage_state(path=state_file)
            browser.close()
            print(f"PUBLISHED {note_id}")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(EXIT_FAILED)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--draft-dir", required=True)
    p.add_argument("--account-id", required=True)
    p.add_argument("--accounts-config", required=True)
    p.add_argument("--headless", action="store_true", default=True)
    publish(p.parse_args())


if __name__ == "__main__":
    main()
