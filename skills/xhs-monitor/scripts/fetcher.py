"""Fetch comments from notes via creator center with anti-detection."""
import io, os, sys, time, random, json, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

INIT_SCRIPT = """\
Object.defineProperty(navigator, 'webdriver', {get: () => false});
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
"""


def pause(lo=0.5, hi=2.0):
    time.sleep(random.uniform(lo, hi))


def mouse_wander(page):
    """Move mouse to a random spot with natural curved path."""
    w, h = page.viewport_size['width'], page.viewport_size['height']
    x, y = random.randint(80, w - 80), random.randint(80, h - 80)
    if random.random() < 0.7:
        page.mouse.move(x, y, steps=random.randint(3, 10))
    else:
        page.mouse.move(x, y)
    pause(0.15, 0.5)


def hover_then_click(page, locator):
    """Hover near element, pause, then click with slight offset."""
    try:
        box = locator.bounding_box()
        if box:
            mx = box['x'] + box['width'] * random.uniform(0.25, 0.75)
            my = box['y'] + box['height'] * random.uniform(0.25, 0.75)
            page.mouse.move(mx - random.randint(5, 20), my - random.randint(5, 20), steps=random.randint(2, 4))
            pause(0.2, 0.5)
            page.mouse.move(mx, my, steps=random.randint(1, 3))
            pause(0.1, 0.3)
    except Exception:
        pass
    locator.click(force=True, timeout=5000)


def idle_scroll(page):
    """Random scrolling behavior like someone reading."""
    for _ in range(random.randint(1, 3)):
        page.mouse.wheel(0, random.randint(200, 700))
        pause(0.5, 2.0)
        if random.random() < 0.3:
            mouse_wander(page)
            pause(0.5, 1.5)
            page.mouse.wheel(0, random.randint(-300, -100))  # scroll back a bit
            pause(0.3, 1.0)


def idle_browse(page, label=""):
    """Simulate a human clicking around and reading - quick version."""
    menus = random.sample(["首页", "笔记管理", "数据看板", "活动中心", "笔记灵感", "创作学院", "创作百科"],
                          random.randint(1, 2))
    for menu in menus:
        mouse_wander(page)
        pause(0.3, 1.0)
        page.evaluate(f"""(m) => {{
            for (const el of document.querySelectorAll('*')) {{
                if (el.innerText && el.innerText.trim() === m && el.offsetParent) {{ el.click(); return; }}
            }}
        }}""", menu)
        pause(1, 3)  # reading time
        if random.random() < 0.5:
            idle_scroll(page)


def scroll_in_detail_panel(page):
    """Scroll within the note detail panel (not outer frame)."""
    pause(1, 2)
    mouse_wander(page)
    pause(0.3, 0.8)

    # First try to scroll the detail panel container
    page.evaluate("""() => {
        for (const el of document.querySelectorAll('[class*="detail"], [class*="panel"], [class*="drawer"], [class*="content"]')) {
            if (el.scrollHeight > el.clientHeight + 50) {
                for (let i = 0; i < 8; i++) {
                    el.scrollTop += 350 + Math.random() * 400;
                }
                return;
            }
        }
    }""")

    # Also do some mouse wheel scrolling for realism
    for _ in range(random.randint(3, 6)):
        mouse_wander(page)
        pause(0.3, 0.8)
        page.mouse.wheel(0, random.randint(300, 800))
        pause(0.8, 2.5)
        if random.random() < 0.4:
            page.mouse.wheel(0, random.randint(-400, -100))
            pause(0.5, 1.5)


def extract_page_data(page) -> dict:
    """Extract note titles, stats, and comments from the page."""
    text = page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in text.split('\n') if l.strip() and 'ICP' not in l and '营业执照' not in l and '行吟' not in l]

    result = {"notes": [], "comments": [], "raw_lines": len(lines)}

    # Look for note entries with stats
    i = 0
    while i < len(lines):
        line = lines[i]
        if '发布于' in line and i > 0:
            title = lines[i - 1] if i > 0 else ""
            date = line
            # Next few lines might be stats: views, likes, comments, etc
            stats = []
            for j in range(i + 1, min(i + 6, len(lines))):
                if lines[j].isdigit():
                    stats.append(int(lines[j]))
                else:
                    break
            if title and '笔记管理' not in title and '全部笔记' not in title:
                result["notes"].append({"title": title, "date": date, "stats": stats})
        # Look for comment-like content
        if any(k in line for k in ['评论区', '说点什么', '写下评论']):
            result["has_comment_input"] = True
        i += 1

    return result


def fetch(args):
    state_file = os.path.join(args.accounts_dir or f"accounts/{args.account_id}/", "state.json")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=args.headless,
            args=["--disable-gpu", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            storage_state=state_file if os.path.exists(state_file) else None,
            viewport={"width": 1280, "height": 900},
            locale="zh-CN", timezone_id="Asia/Shanghai",
        )
        context.add_init_script(INIT_SCRIPT)
        page = context.new_page()

        # === Go to note manager ===
        page.goto("https://creator.xiaohongshu.com/new/note-manager", wait_until="load")
        pause(5, 9)  # Full page load wait

        if page.locator('[placeholder*="手机号"]').first.count():
            print(json.dumps({"error": "creator_not_logged_in"}, ensure_ascii=False))
            sys.exit(2)

        # === Pre-browse anti-detection ===
        idle_browse(page, "pre")
        page.goto("https://creator.xiaohongshu.com/new/note-manager", wait_until="load")
        pause(4, 7)

        # === Open first note detail ===
        mouse_wander(page)
        pause(1, 2)
        imgs = page.locator('img.content')
        if imgs.count() == 0:
            print(json.dumps({"error": "no_notes"}, ensure_ascii=False))
            sys.exit(1)

        hover_then_click(page, imgs.first)
        pause(4, 7)

        # === Scroll for comments ===
        scroll_in_detail_panel(page)
        pause(2, 4)

        # === Extract data ===
        data = extract_page_data(page)
        pause(1, 2)

        # === Post-browse anti-detection ===
        idle_browse(page, "post")

        # Close detail by clicking sidebar area
        mouse_wander(page)
        pause(0.5, 1.5)
        page.mouse.click(random.randint(50, 250), random.randint(80, 300))
        pause(1, 2)

        context.storage_state(path=state_file)
        browser.close()

    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--note-id", default="")
    p.add_argument("--account-id", required=True)
    p.add_argument("--accounts-config", default="")
    p.add_argument("--accounts-dir", default="")
    p.add_argument("--headless", action="store_true", default=True)
    fetch(p.parse_args())


if __name__ == "__main__":
    main()
