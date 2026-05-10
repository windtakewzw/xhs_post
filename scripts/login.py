"""Open browser for manual Xiaohongshu login.
Step 1: QR login on main site (xiaohongshu.com)
Step 2: Phone login on creator center (creator.xiaohongshu.com) - separate auth system
"""
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
user_data_dir = f"accounts/{account_id}/"
state_file = os.path.join(user_data_dir, "state.json")
os.makedirs(user_data_dir, exist_ok=True)

print(f"账号: {account_id}")
print("=== 第一步：登录主站（扫码）===")
print("正在打开浏览器...")

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context(
        storage_state=state_file if os.path.exists(state_file) else None,
        viewport={"width": 1280, "height": 900},
        locale="zh-CN", timezone_id="Asia/Shanghai",
    )
    context.add_init_script(INIT_SCRIPT)
    page = context.new_page()

    # === Step 1: Main site QR login ===
    page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
    print("请在浏览器中扫码登录小红书... (120秒)")
    time.sleep(120)
    context.storage_state(path=state_file)
    print("主页登录态已保存")

    # === Step 2: Creator center login (phone + code) ===
    print("\n=== 第二步：登录创作者中心（手机号）===")
    page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
    time.sleep(2)

    # Click avatar -> 创作中心
    try:
        avatar = page.locator('[class*="avatar"] img').first
        if avatar.count():
            avatar.click()
            time.sleep(2)
    except Exception:
        pass

    link = page.locator('text=创作中心').first
    if link.count() and link.is_visible(timeout=5000):
        link.click()
        time.sleep(5)
    else:
        page.goto("https://creator.xiaohongshu.com/publish/publish", wait_until="networkidle", timeout=30000)
        time.sleep(3)

    print(f"当前页面: {page.url}")
    if "login" in page.url.lower():
        print("创者中心需要手机号登录")
        print("请在浏览器中输入手机号和验证码... (120秒)")
        time.sleep(120)
    else:
        # Check if a login form is shown even though URL doesn't say "login"
        phone_input = page.locator('[placeholder*="手机号"], input[type="tel"]').first
        if phone_input.count() and phone_input.is_visible(timeout=3000):
            print("检测到手机号登录表单")
            print("请在浏览器中输入手机号和验证码... (120秒)")
            time.sleep(120)
        else:
            print("创作者中心可访问 - 无需额外登录")

    # Save final state
    context.storage_state(path=state_file)
    browser.close()
    print(f"\n所有登录态已保存到 {state_file}")
