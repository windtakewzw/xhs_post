"""Comment fetcher for Xiaohongshu posts. Playwright-based scraping."""
import argparse
import json
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


def fetch(args):
    accounts = yaml.safe_load(open(args.accounts_config, encoding="utf-8"))
    account = next((a for a in accounts["accounts"] if a["id"] == args.account_id), None)
    if not account:
        print(json.dumps({"error": f"account {args.account_id} not found"}))
        sys.exit(1)

    state_file = os.path.join(account.get("user_data_dir", f"accounts/{args.account_id}/"), "state.json")
    comments = []

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
            time.sleep(random.uniform(3, 5))

            # Scroll to load comments
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 500)")
                time.sleep(1)

            # Try to find comment elements
            comment_els = page.locator('[class*="comment"] [class*="content"], .comment-item, [data-v-comment]').all()
            for el in comment_els:
                try:
                    text = el.inner_text().strip()
                    if text and len(text) > 1:
                        comments.append({
                            "note_id": args.note_id,
                            "content": text,
                            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        })
                except Exception:
                    pass

            context.storage_state(path=state_file)
            browser.close()

    except Exception as e:
        comments.append({"error": str(e)})

    print(json.dumps(comments, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--note-id", required=True)
    p.add_argument("--account-id", required=True)
    p.add_argument("--accounts-config", required=True)
    p.add_argument("--headless", action="store_true", default=True)
    fetch(p.parse_args())


if __name__ == "__main__":
    main()
