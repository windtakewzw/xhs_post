# 发布引擎 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Playwright 浏览器自动化发布引擎——账号管理、10步发布流水线、反检测、定时调度，将 pending_publish 草稿发布到小红书

**Architecture:** accounts.py 管理多账号 BrowserContext（userDataDir 持久化）→ engine.py 执行10步发布流水线（上传图片、填标题/正文/标签、提交）→ scheduler.py 定时扫描 index.md 待发队列 + 时间窗口随机延迟 → anti_detect.py 提供反检测脚本和拟人化操作

**Tech Stack:** Python 3.12, playwright, 已有 PyYAML + pytest

---

### Task 1: 模块骨架 + Playwright 依赖

**Files:**
- Create: `src/publisher/__init__.py`
- Create: `tests/publisher/__init__.py`
- Modify: `requirements.txt`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p D:/project/xhs_post/src/publisher D:/project/xhs_post/tests/publisher
touch D:/project/xhs_post/src/publisher/__init__.py
touch D:/project/xhs_post/tests/publisher/__init__.py
```

- [ ] **Step 2: 追加 playwright 依赖**

```bash
echo 'playwright>=1.50.0' >> D:/project/xhs_post/requirements.txt
cd D:/project/xhs_post && source venv/Scripts/activate && pip install playwright && python -m playwright install chromium
```

- [ ] **Step 3: 验证安装**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -c "from playwright.sync_api import sync_playwright; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "chore: add publisher module scaffold and playwright"
```

---

### Task 2: 反检测模块

**Files:**
- Create: `src/publisher/anti_detect.py`
- Test: `tests/publisher/test_anti_detect.py`

- [ ] **Step 1: 写测试**

```python
# tests/publisher/test_anti_detect.py
from src.publisher.anti_detect import AntiDetect


def test_init_script_contains_key_patterns():
    script = AntiDetect.get_init_script()
    assert 'webdriver' in script
    assert 'window.chrome' in script
    assert 'navigator.plugins' in script
    assert 'navigator.languages' in script


def test_init_script_is_valid_javascript():
    script = AntiDetect.get_init_script()
    # Each line should be a valid JS statement ending with ;
    lines = [l.strip() for l in script.split('\n') if l.strip()]
    for line in lines:
        assert line.endswith(';'), f"Line missing semicolon: {line}"


def test_typing_interval_range():
    import random
    random.seed(42)
    delays = [AntiDetect.random_typing_delay() for _ in range(100)]
    for d in delays:
        assert 80 <= d <= 200, f"Delay out of range: {d}"


def test_action_interval_range():
    import random
    random.seed(42)
    delays = [AntiDetect.random_action_delay() for _ in range(100)]
    for d in delays:
        assert 2000 <= d <= 5000, f"Delay out of range: {d}"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/publisher/test_anti_detect.py -v
```
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现 anti_detect.py**

```python
# src/publisher/anti_detect.py
import random


class AntiDetect:
    TYPING_MIN = 80   # ms
    TYPING_MAX = 200  # ms
    ACTION_MIN = 2000  # ms
    ACTION_MAX = 5000  # ms

    @staticmethod
    def get_init_script() -> str:
        return """\
Object.defineProperty(navigator, 'webdriver', {get: () => false});
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
"""

    @staticmethod
    def random_typing_delay() -> int:
        return random.randint(AntiDetect.TYPING_MIN, AntiDetect.TYPING_MAX)

    @staticmethod
    def random_action_delay() -> int:
        return random.randint(AntiDetect.ACTION_MIN, AntiDetect.ACTION_MAX)

    @staticmethod
    async def human_type(page, selector: str, text: str):
        """逐字输入，模拟打字速度"""
        await page.click(selector)
        for char in text:
            delay = AntiDetect.random_typing_delay()
            await page.keyboard.type(char, delay=delay)

    @staticmethod
    async def human_scroll(page):
        """随机滚动"""
        scroll_distance = random.randint(100, 500)
        await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
        await page.wait_for_timeout(random.randint(500, 1500))

    @staticmethod
    async def human_click(page, selector: str):
        """点击前在目标附近轻微偏移"""
        box = await page.locator(selector).bounding_box()
        if box:
            x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
            await page.mouse.move(x, y)
            await page.wait_for_timeout(random.randint(100, 300))
        await page.click(selector)
```

- [ ] **Step 4: 运行测试**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/publisher/test_anti_detect.py -v
```
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add anti-detect module"
```

---

### Task 3: 账号管理模块

**Files:**
- Create: `src/publisher/accounts.py`
- Create: `data/中央半岛/accounts.yaml`
- Test: `tests/publisher/test_accounts.py`

- [ ] **Step 1: 创建账号配置文件**

```yaml
# data/中央半岛/accounts.yaml
accounts:
  - id: account-001
    persona: 老王
    persona_type: investment-advisor
    user_data_dir: data/accounts/account-001/
    login_status: active
    last_published_at:
    daily_limit: 1
    preferred_window:
      start: "09:00"
      end: "21:00"

  - id: account-002
    persona: 小陈
    persona_type: lifestyle-advisor
    user_data_dir: data/accounts/account-002/
    login_status: active
    last_published_at:
    daily_limit: 1
    preferred_window:
      start: "09:00"
      end: "21:00"

  - id: account-003
    persona: 阿芳
    persona_type: family-advisor
    user_data_dir: data/accounts/account-003/
    login_status: active
    last_published_at:
    daily_limit: 1
    preferred_window:
      start: "09:00"
      end: "21:00"
```

- [ ] **Step 2: 写测试**

```python
# tests/publisher/test_accounts.py
import os
import tempfile
from src.publisher.accounts import AccountManager

SAMPLE_ACCOUNTS_YAML = """
accounts:
  - id: account-001
    persona: 老王
    persona_type: investment-advisor
    user_data_dir: data/accounts/account-001/
    login_status: active
    last_published_at: 2026-05-12T20:00:00
    daily_limit: 1
    preferred_window:
      start: "09:00"
      end: "21:00"
  - id: account-002
    persona: 小陈
    persona_type: lifestyle-advisor
    user_data_dir: data/accounts/account-002/
    login_status: expired
    last_published_at:
    daily_limit: 1
    preferred_window:
      start: "10:00"
      end: "20:00"
"""


def test_load_accounts():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "accounts.yaml")
        with open(path, "w") as f:
            f.write(SAMPLE_ACCOUNTS_YAML)

        mgr = AccountManager(path)
        accounts = mgr.list_active()
        assert len(accounts) == 1  # only account-001 is active
        assert accounts[0]["id"] == "account-001"
        assert accounts[0]["persona"] == "老王"


def test_find_by_persona():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "accounts.yaml")
        with open(path, "w") as f:
            f.write(SAMPLE_ACCOUNTS_YAML)

        mgr = AccountManager(path)
        acc = mgr.find_by_persona("小陈")
        assert acc is not None
        assert acc["login_status"] == "expired"


def test_find_available_account():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "accounts.yaml")
        with open(path, "w") as f:
            f.write(SAMPLE_ACCOUNTS_YAML)

        mgr = AccountManager(path)
        acc = mgr.find_available(persona_type="investment-advisor")
        assert acc is not None
        assert acc["id"] == "account-001"


def test_mark_expired():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "accounts.yaml")
        with open(path, "w") as f:
            f.write(SAMPLE_ACCOUNTS_YAML)

        mgr = AccountManager(path)
        mgr.mark_expired("account-001")
        acc = mgr.find_by_id("account-001")
        assert acc["login_status"] == "expired"


def test_update_last_published():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "accounts.yaml")
        with open(path, "w") as f:
            f.write(SAMPLE_ACCOUNTS_YAML)

        mgr = AccountManager(path)
        mgr.update_last_published("account-001", "2026-05-13T10:00:00")
        acc = mgr.find_by_id("account-001")
        assert acc["last_published_at"] == "2026-05-13T10:00:00"
```

- [ ] **Step 3: 运行测试确认失败**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/publisher/test_accounts.py -v
```
Expected: ModuleNotFoundError

- [ ] **Step 4: 实现 accounts.py**

```python
# src/publisher/accounts.py
import yaml
import os
from datetime import datetime


class AccountManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.data = self._load()

    def _load(self) -> dict:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self.data, f, allow_unicode=True, default_flow_style=False)

    def list_all(self) -> list[dict]:
        return self.data.get("accounts", [])

    def list_active(self) -> list[dict]:
        return [a for a in self.list_all() if a.get("login_status") == "active"]

    def find_by_id(self, account_id: str) -> dict | None:
        for a in self.list_all():
            if a["id"] == account_id:
                return a
        return None

    def find_by_persona(self, persona: str) -> dict | None:
        for a in self.list_all():
            if a["persona"] == persona:
                return a
        return None

    def find_available(self, persona_type: str = None) -> dict | None:
        """找一个可用的活跃账号，优先匹配类型"""
        active = self.list_active()
        if not active:
            return None
        if persona_type:
            for a in active:
                if a["persona_type"] == persona_type:
                    return a
        return active[0]

    def mark_expired(self, account_id: str):
        acc = self.find_by_id(account_id)
        if acc:
            acc["login_status"] = "expired"
            self._save()

    def update_last_published(self, account_id: str, timestamp: str = None):
        acc = self.find_by_id(account_id)
        if acc:
            acc["last_published_at"] = timestamp or datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            self._save()
```

- [ ] **Step 5: 运行测试**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/publisher/test_accounts.py -v
```
Expected: 5 passed

- [ ] **Step 6: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add account management module"
```

---

### Task 4: 发布引擎核心

**Files:**
- Create: `src/publisher/engine.py`
- Test: `tests/publisher/test_engine.py`

- [ ] **Step 1: 写测试**

```python
# tests/publisher/test_engine.py
import os
import tempfile
from unittest.mock import patch, MagicMock
from src.publisher.engine import Publisher, PublishResult


def test_publisher_parse_post_md():
    post_md = """---
id: draft-20260512-001
project: 中央半岛
persona: 老王
persona_type: investment-advisor
content_type: market-analysis
status: pending_publish
---

# LPR又降了！算笔账

央行刚刚公布了最新LPR...
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        post_path = os.path.join(tmpdir, "post.md")
        with open(post_path, "w", encoding="utf-8") as f:
            f.write(post_md)

        data = Publisher.parse_post_md(post_path)
        assert data["id"] == "draft-20260512-001"
        assert data["title"] == "LPR又降了！算笔账"
        assert "央行刚刚公布" in data["body"]


def test_publisher_split_tags():
    body = "正文内容\n\n#LPR下调 #房贷利率 #海口买房"
    text, tags = Publisher.split_tags(body)
    assert "LPR下调" not in text
    assert "#LPR下调" in tags[0]
    assert len(tags) == 3


def test_publisher_split_tags_no_tags():
    body = "正文内容，没有任何标签"
    text, tags = Publisher.split_tags(body)
    assert text == body
    assert tags == []


@patch('src.publisher.engine.sync_playwright')
def test_publish_flow_outline(mock_pw):
    """验证发布流程不会在 mock 模式下崩溃"""
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()
    mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    publisher = Publisher()
    # 测试构建步骤序列
    steps = publisher.build_steps()
    assert len(steps) == 10
    assert steps[0] == "load_context"
    assert steps[9] == "collect_note_id"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/publisher/test_engine.py -v
```
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现 engine.py**

```python
# src/publisher/engine.py
import os
import re
import random
import time
import yaml
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, BrowserContext
from src.publisher.anti_detect import AntiDetect
from src.publisher.accounts import AccountManager


@dataclass
class PublishResult:
    success: bool
    note_id: str = ""
    error: str = ""


class Publisher:
    def __init__(self):
        self.anti = AntiDetect()

    def build_steps(self) -> list[str]:
        return [
            "load_context", "check_login", "close_popups",
            "enter_creator_center", "upload_images", "fill_title",
            "fill_body", "add_hashtags", "submit", "collect_note_id",
        ]

    @staticmethod
    def parse_post_md(path: str) -> dict:
        """解析 post.md，返回 {id, title, body, hashtags, persona, content_type, ...}"""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse frontmatter
        meta = {}
        fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if fm_match:
            meta = yaml.safe_load(fm_match.group(1))
            body = content[fm_match.end():].strip()
        else:
            body = content

        # Extract title (# heading)
        title_match = re.match(r'^# (.+)', body)
        title = title_match.group(1).strip() if title_match else ""
        if title_match:
            body = body[title_match.end():].strip()

        meta["title"] = title
        meta["body"] = body
        return meta

    @staticmethod
    def split_tags(body: str) -> tuple[str, list[str]]:
        """Split hashtags from end of body text."""
        tag_pattern = r'(#[\w一-鿿]+(?:\s*#[\w一-鿿]+)*)$'
        match = re.search(tag_pattern, body.strip())
        if match:
            tags_str = match.group(1)
            tags = re.findall(r'#[\w一-鿿]+', tags_str)
            text = body[:match.start()].strip()
            return text, tags
        return body, []

    def publish(self, account: dict, draft_dir: str) -> PublishResult:
        """执行单篇发布的完整流程"""
        post_path = os.path.join(draft_dir, "post.md")
        images_dir = os.path.join(draft_dir, "images")
        post_data = self.parse_post_md(post_path)

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=False)
                context = browser.new_context(
                    storage_state=os.path.join(account["user_data_dir"], "state.json")
                    if os.path.exists(os.path.join(account["user_data_dir"], "state.json"))
                    else None,
                    viewport={"width": 1280, "height": 900},
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                )
                context.add_init_script(AntiDetect.get_init_script())
                page = context.new_page()

                # Step 1-2: Login check
                page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")
                time.sleep(AntiDetect.random_action_delay() / 1000)

                if "login" in page.url.lower() or page.locator('text=登录').count() > 0:
                    context.storage_state(path=os.path.join(account["user_data_dir"], "state.json"))
                    return PublishResult(success=False, error="login_expired")

                # Step 3-10: Navigate and publish
                self._navigate_to_creator(page)
                self._upload_images(page, images_dir)
                self._fill_content(page, post_data)
                self._submit(page)
                note_id = self._collect_note_id(page)

                context.storage_state(path=os.path.join(account["user_data_dir"], "state.json"))
                browser.close()
                return PublishResult(success=True, note_id=note_id)

        except Exception as e:
            return PublishResult(success=False, error=str(e))

    def _navigate_to_creator(self, page):
        """Steps 3-4: Close popups, navigate to creator center"""
        time.sleep(AntiDetect.random_action_delay() / 1000)
        # Close any popups
        try:
            close_btn = page.locator('[class*="close"]').first
            if close_btn.is_visible():
                close_btn.click()
        except Exception:
            pass
        # Click publish entry
        page.goto("https://creator.xiaohongshu.com/publish/publish", wait_until="domcontentloaded")
        time.sleep(AntiDetect.random_action_delay() / 1000)

    def _upload_images(self, page, images_dir: str):
        """Step 5: Upload images via file chooser"""
        if not os.path.isdir(images_dir):
            return
        images = sorted([f for f in os.listdir(images_dir) if f.endswith('.jpg') or f.endswith('.png')])
        if not images:
            return
        paths = [os.path.join(images_dir, img) for img in images]
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(paths)
        time.sleep(3)  # Wait for upload

    def _fill_content(self, page, post_data: dict):
        """Steps 6-8: Fill title, body, hashtags"""
        # Title
        title_input = page.locator('[placeholder*="标题"]')
        if title_input.is_visible():
            for char in post_data["title"][:20]:  # Max 20 chars
                page.keyboard.type(char, delay=self.anti.random_typing_delay())

        time.sleep(AntiDetect.random_action_delay() / 1000)

        # Body
        body_input = page.locator('[placeholder*="正文"]')
        if body_input.is_visible():
            body_text, hashtags = self.split_tags(post_data["body"])
            body_input.click()
            # Paste body in segments
            segments = body_text.split('\n')
            for seg in segments:
                if seg.strip():
                    page.keyboard.type(seg, delay=self.anti.random_typing_delay() // 2)
                page.keyboard.press("Enter")
                time.sleep(0.3)

        time.sleep(AntiDetect.random_action_delay() / 1000)

        # Hashtags
        hashtag_input = page.locator('[placeholder*="标签"]')
        if hashtag_input.is_visible() and post_data.get("hashtags"):
            for tag in post_data["hashtags"]:
                page.keyboard.type(tag, delay=self.anti.random_typing_delay())
                page.keyboard.press("Enter")
                time.sleep(0.5)

    def _submit(self, page):
        """Step 9: Click publish button"""
        submit_btn = page.locator('button:has-text("发布")')
        if submit_btn.is_visible():
            submit_btn.click()
            time.sleep(5)  # Wait for success

    def _collect_note_id(self, page) -> str:
        """Step 10: Extract note ID from URL or success page"""
        page.wait_for_timeout(3000)
        return page.url.split('/')[-1] if '/' in page.url else ""
```

- [ ] **Step 4: 运行 engine 测试**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/publisher/test_engine.py -v
```
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add publishing engine core"
```

---

### Task 5: 调度器 + CLI 集成

**Files:**
- Create: `src/publisher/scheduler.py`
- Modify: `src/cli.py`
- Test: `tests/publisher/test_scheduler.py`

- [ ] **Step 1: 写测试**

```python
# tests/publisher/test_scheduler.py
from src.publisher.scheduler import Scheduler


def test_scheduler_window_check():
    """测试时间窗口判断"""
    # 12:00 is within 10:00-21:00
    assert Scheduler.is_in_window("12:00", "10:00", "21:00") is True
    # 08:00 is before window
    assert Scheduler.is_in_window("08:00", "10:00", "21:00") is False
    # 22:00 is after window
    assert Scheduler.is_in_window("22:00", "10:00", "21:00") is False
    # Boundary: exactly at start
    assert Scheduler.is_in_window("10:00", "10:00", "21:00") is True


def test_scheduler_cooldown_check():
    """测试冷却时间判断"""
    from datetime import datetime, timedelta
    now = datetime.now()
    recent = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
    old = (now - timedelta(hours=25)).strftime("%Y-%m-%dT%H:%M:%S")

    assert Scheduler.is_cooled_down(recent, hours=24) is False
    assert Scheduler.is_cooled_down(old, hours=24) is True
    assert Scheduler.is_cooled_down("", hours=24) is True  # never published


def test_scheduler_random_delay():
    """测试随机延迟在范围内"""
    import random
    random.seed(42)
    for _ in range(50):
        delay = Scheduler.random_delay(30)
        assert 0 <= delay <= 30 * 60  # in seconds
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/publisher/test_scheduler.py -v
```
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现 scheduler.py**

```python
# src/publisher/scheduler.py
import os
import time
import random
import logging
from datetime import datetime, timedelta
from src.content.indexer import DraftIndex, DraftStatus
from src.publisher.accounts import AccountManager
from src.publisher.engine import Publisher

log = logging.getLogger(__name__)


class Scheduler:
    SCAN_INTERVAL = 15 * 60  # 15 minutes in seconds
    PROJECT_COOLDOWN = 3 * 60 * 60  # 3 hours between different accounts on same project
    ACCOUNT_COOLDOWN = 24 * 60 * 60  # 24 hours for same account

    def __init__(self, project: str, data_dir: str = "data", rules_dir: str = "rules"):
        self.project = project
        self.data_dir = os.path.join(data_dir, project)
        self.drafts_dir = os.path.join(self.data_dir, "drafts")
        self.accounts_path = os.path.join(self.data_dir, "accounts.yaml")
        self.running = False

    @staticmethod
    def is_in_window(current_time: str, window_start: str, window_end: str) -> bool:
        t = datetime.strptime(current_time, "%H:%M").time()
        s = datetime.strptime(window_start, "%H:%M").time()
        e = datetime.strptime(window_end, "%H:%M").time()
        return s <= t <= e

    @staticmethod
    def is_cooled_down(last_published: str, hours: int = 24) -> bool:
        if not last_published:
            return True
        last = datetime.strptime(last_published, "%Y-%m-%dT%H:%M:%S")
        return (datetime.now() - last).total_seconds() >= hours * 3600

    @staticmethod
    def random_delay(minutes: int = 30) -> int:
        return random.randint(0, minutes * 60)

    def start(self):
        """主循环：扫描 → 决策 → 发布"""
        self.running = True
        log.info(f"[scheduler] 启动 {self.project}")

        try:
            while self.running:
                self._scan_and_publish()
                log.info(f"[scheduler] 等待 {self.SCAN_INTERVAL // 60} 分钟")
                time.sleep(self.SCAN_INTERVAL)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.running = False
        log.info("[scheduler] 停止")

    def _scan_and_publish(self):
        index_path = os.path.join(self.drafts_dir, "index.md")
        if not os.path.exists(index_path):
            return

        index = DraftIndex.load(index_path)
        accounts = AccountManager(self.accounts_path)

        # Find pending_publish entries
        for entry in index.entries:
            if entry.status != DraftStatus.PENDING_PUBLISH:
                continue

            account = accounts.find_by_persona(entry.persona)
            if not account or account.get("login_status") != "active":
                continue

            # Check window
            now = datetime.now().strftime("%H:%M")
            window_start = account.get("preferred_window", {}).get("start", "09:00")
            window_end = account.get("preferred_window", {}).get("end", "21:00")

            if not self.is_in_window(now, window_start, window_end):
                continue

            # Check cooldown
            if not self.is_cooled_down(account.get("last_published_at", ""), hours=24):
                continue

            # Check project cooldown (other accounts)
            if not self._check_project_cooldown(index, accounts, entry.persona):
                continue

            # Random delay then publish
            delay = self.random_delay(30)
            log.info(f"[scheduler] 找到待发草稿 {entry.date}_{entry.seq}，随机延迟 {delay}s")
            time.sleep(delay)

            draft_dir = os.path.join(self.drafts_dir, f"{entry.date}_{entry.seq}")
            self.publish_one(draft_dir, account, index, entry)

    def _check_project_cooldown(self, index: DraftIndex, accounts: AccountManager,
                                current_persona: str) -> bool:
        """同项目其他账号3小时内没发过"""
        cutoff = datetime.now() - timedelta(hours=3)
        for entry in index.entries:
            if entry.persona == current_persona:
                continue
            if entry.status == DraftStatus.PUBLISHED:
                try:
                    pub_date = datetime.strptime(entry.date, "%Y-%m-%d")
                    if pub_date >= cutoff:
                        return False
                except ValueError:
                    pass
        return True

    def publish_one(self, draft_dir: str, account: dict, index: DraftIndex, entry=None):
        """执行单篇发布"""
        publisher = Publisher()
        result = publisher.publish(account, draft_dir)

        if result.success:
            if entry:
                index.update_status(entry.date, entry.seq, DraftStatus.PUBLISHED)
            accounts = AccountManager(self.accounts_path)
            accounts.update_last_published(account["id"])
            index.save(os.path.join(self.drafts_dir, "index.md"))
            log.info(f"[scheduler] 发布成功: {result.note_id}")
        else:
            if entry and result.error == "login_expired":
                accounts = AccountManager(self.accounts_path)
                accounts.mark_expired(account["id"])
                log.warning(f"[scheduler] 登录失效: {account['id']}，请人工登录")
            elif entry:
                index.update_status(entry.date, entry.seq, DraftStatus.FAILED)
                index.save(os.path.join(self.drafts_dir, "index.md"))
            log.error(f"[scheduler] 发布失败: {result.error}")
```

- [ ] **Step 4: 运行 scheduler 测试**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/publisher/test_scheduler.py -v
```
Expected: 3 passed

- [ ] **Step 5: 追加 CLI 命令到 src/cli.py**

在现有 `cli.py` 的 `main()` 函数后追加：

```python
@main.command()
@click.option("--project", required=True)
def publish(project):
    """启动发布调度器"""
    from src.publisher.scheduler import Scheduler
    s = Scheduler(project)
    s.start()


@main.command()
@click.option("--project", required=True)
@click.option("--id", "draft_id", default=None)
@click.option("--account", default=None)
def publish_one(project, draft_id, account):
    """手动发布单篇"""
    from src.publisher.accounts import AccountManager
    from src.publisher.engine import Publisher
    from src.content.indexer import DraftIndex

    data_dir = os.path.join("data", project)
    acc_mgr = AccountManager(os.path.join(data_dir, "accounts.yaml"))

    if account:
        acc = acc_mgr.find_by_id(account)
    else:
        acc = acc_mgr.find_available()

    if not acc:
        click.echo("没有可用账号")
        return

    drafts_dir = os.path.join(data_dir, "drafts")
    index = DraftIndex.load(os.path.join(drafts_dir, "index.md"))

    if draft_id:
        date, seq = draft_id.split("_")
        draft_dir = os.path.join(drafts_dir, f"{date}_{seq}")
    else:
        # Find first pending_publish
        for entry in index.entries:
            if entry.status.value == "pending_publish":
                draft_dir = os.path.join(drafts_dir, f"{entry.date}_{entry.seq}")
                draft_id = f"{entry.date}_{entry.seq}"
                break
        else:
            click.echo("没有待发草稿")
            return

    publisher = Publisher()
    result = publisher.publish(acc, draft_dir)

    if result.success:
        click.echo(f"发布成功: {result.note_id}")
        # Update index
        for entry in index.entries:
            if f"{entry.date}_{entry.seq}" == draft_id:
                entry.status = DraftStatus.PUBLISHED
                break
        index.save(os.path.join(drafts_dir, "index.md"))
    else:
        click.echo(f"发布失败: {result.error}")


@main.command()
@click.option("--project", required=True)
def accounts(project):
    """查看账号状态"""
    from src.publisher.accounts import AccountManager
    data_dir = os.path.join("data", project)
    mgr = AccountManager(os.path.join(data_dir, "accounts.yaml"))

    for acc in mgr.list_all():
        status_icon = "✅" if acc["login_status"] == "active" else "❌"
        last = acc.get("last_published_at") or "从未发布"
        click.echo(f"{status_icon} {acc['id']} | {acc['persona']} | {acc['login_status']} | 上次: {last}")
```

- [ ] **Step 6: 运行全量测试**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/ -v
```

- [ ] **Step 7: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add scheduler and CLI publish commands"
```
