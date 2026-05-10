"""Comment reply script for Xiaohongshu. Playwright-based."""
import argparse
import os
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


def reply(args):
    accounts = yaml.safe_load(open(args.accounts_config, encoding="utf-8"))
    account = next((a for a in accounts["accounts"] if a["id"] == args.account_id), None)
    if not account:
        print(f"ERROR: account {args.account_id} not found")
        sys.exit(1)

    state_file = os.path.join(account.get("user_data_dir", f"accounts/{args.account_id}/"), "state.json")

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=getattr(args, 'headless', True))
            context = browser.new_context(
                storage_state=state_file if os.path.exists(state_file) else None,
                viewport={"width": 1280, "height": 900},
                locale="zh-CN", timezone_id="Asia/Shanghai",
            )
            context.add_init_script(INIT_SCRIPT)
            page = context.new_page()

            note_url = f"https://www.xiaohongshu.com/explore/{args.note_id}"
            page.goto(note_url, wait_until="domcontentloaded")
            time.sleep(random.uniform(2, 4))

            # Scroll to comments section
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 600)")
                time.sleep(1)

            # Find and click reply button near the target comment
            reply_btns = page.locator('[class*="reply"], text=回复').all()
            clicked = False
            for btn in reply_btns:
                if btn.is_visible():
                    btn.click()
                    clicked = True
                    time.sleep(1)
                    break

            if clicked:
                # Type reply text
                input_el = page.locator('textarea, [contenteditable="true"], [class*="input"]').first
                if input_el.count():
                    input_el.click()
                    # Type character by character
                    for char in args.reply_text:
                        page.keyboard.type(char, delay=random.randint(80, 150))
                    time.sleep(0.5)
                    # Submit
                    submit_btn = page.locator('button:has-text("发送"), button:has-text("回复")').first
                    if submit_btn.count():
                        submit_btn.click()
                        time.sleep(2)
                        print("REPLIED")
                    else:
                        print("WARN: submit button not found, text typed but not sent")
                else:
                    print("WARN: reply input not found")
            else:
                print("WARN: reply button not found, comment page structure may have changed")

            context.storage_state(path=state_file)
            browser.close()

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--note-id", required=True)
    p.add_argument("--comment-id", default="")
    p.add_argument("--reply-text", required=True)
    p.add_argument("--account-id", required=True)
    p.add_argument("--accounts-config", required=True)
    p.add_argument("--headless", action="store_true", default=True)
    reply(p.parse_args())


if __name__ == "__main__":
    main()
