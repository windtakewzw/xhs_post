"""Open browser for manual Xiaohongshu login. Saves session state after login."""
import sys
import os
import time
from playwright.sync_api import sync_playwright

INIT_SCRIPT = """\
Object.defineProperty(navigator, 'webdriver', {get: () => false});
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
"""

account_id = sys.argv[1] if len(sys.argv) > 1 else "account-001"
user_data_dir = f"data/accounts/{account_id}/"
state_file = os.path.join(user_data_dir, "state.json")
os.makedirs(user_data_dir, exist_ok=True)

print(f"账号: {account_id}")
print(f"存储目录: {user_data_dir}")
print("正在打开浏览器...")

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context(
        storage_state=state_file if os.path.exists(state_file) else None,
        viewport={"width": 1280, "height": 900},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
    )
    context.add_init_script(INIT_SCRIPT)
    page = context.new_page()

    page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")
    print("\n浏览器已打开，请在浏览器中扫码登录小红书")
    print("120秒后自动保存登录态（你也可以直接关掉浏览器窗口结束）...")
    time.sleep(120)

    context.storage_state(path=state_file)
    browser.close()
    print(f"\n登录态已保存到 {state_file}")
    print("现在可以关闭浏览器，使用 xhs-publish 自动发布了")
