"""Login to both xiaohongshu.com AND creator.xiaohongshu.com."""
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

    # === Step 1: Main site login ===
    print("=" * 50)
    print("第1步：登录主站 (xiaohongshu.com)")
    print("=" * 50)
    page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
    print("请扫码登录主站... (60秒)")
    time.sleep(60)

    # Verify main site login
    if page.locator('text=登录').count() > 0:
        print("主站未登录，再等60秒...")
        time.sleep(60)
    context.storage_state(path=state_file)
    print("主站登录态已保存\n")

    # === Step 2: Creator center login ===
    print("=" * 50)
    print("第2步：登录创作者中心 (creator.xiaohongshu.com)")
    print("需要手机号登录或切换扫码登录")
    print("=" * 50)
    page.goto("https://creator.xiaohongshu.com/", wait_until="networkidle", timeout=30000)
    time.sleep(3)

    # Check if phone login form is visible
    phone_input = page.locator('[placeholder*="手机号"]').first
    if phone_input.count() and phone_input.is_visible(timeout=2000):
        print("请登录创作者中心（手机号或右上角切换扫码）... (120秒)")
        time.sleep(120)
    else:
        print("创作者中心已登录（无需额外操作）")

    # === Step 3: Verify both domains work ===
    print("\n验证双域登录状态...")

    # Test main site
    page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
    time.sleep(2)
    main_ok = page.locator('text=登录').count() == 0
    print(f"  主站 (xiaohongshu.com): {'OK' if main_ok else '未登录!'}")

    # Test creator center
    page.goto("https://creator.xiaohongshu.com/new/note-manager", wait_until="networkidle", timeout=30000)
    time.sleep(3)
    creator_ok = page.locator('[placeholder*="手机号"]').first.count() == 0
    print(f"  创作者中心 (creator.xiaohongshu.com): {'OK' if creator_ok else '未登录!'}")

    # Final save with both domains' cookies
    context.storage_state(path=state_file)
    browser.close()
    print(f"\n登录态已保存: {state_file}")
