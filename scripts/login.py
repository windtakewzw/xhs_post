"""Login to Xiaohongshu creator center."""
import io, os, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

INIT_SCRIPT = """\
Object.defineProperty(navigator, 'webdriver', {get: () => false});
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
"""

account_id = sys.argv[1] if len(sys.argv) > 1 else "account-001"
user_data_dir = os.path.abspath(f"accounts/{account_id}/")
state_file = os.path.join(user_data_dir, "state.json")
os.makedirs(user_data_dir, exist_ok=True)

print(f"账号: {account_id}")

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context(
        storage_state=state_file if os.path.exists(state_file) else None,
        viewport={"width": 1280, "height": 900},
        locale="zh-CN", timezone_id="Asia/Shanghai",
    )
    context.add_init_script(INIT_SCRIPT)
    page = context.new_page()

    # Go directly to creator center login
    page.goto("https://creator.xiaohongshu.com/", wait_until="networkidle", timeout=30000)
    time.sleep(3)

    print("浏览器已打开创作者中心登录页")
    print("可以切换到扫码登录（页面右上角有切换按钮）")
    print("请登录... (180秒)")
    time.sleep(180)

    # Verify login
    page.goto("https://creator.xiaohongshu.com/publish/publish", wait_until="networkidle", timeout=30000)
    time.sleep(3)

    phone_input = page.locator('[placeholder*="手机号"]').first
    if phone_input.count() and phone_input.is_visible(timeout=2000):
        print("警告: 登录未成功，请重试")
    else:
        print("登录成功!")

    context.storage_state(path=state_file)
    page.screenshot(path=os.path.join(user_data_dir, "login_final.png"))
    browser.close()
    print(f"登录态已保存")
