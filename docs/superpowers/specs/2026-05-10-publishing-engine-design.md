# xhs_post 发布引擎设计

## 概述

发布引擎是 xhs_post 的执行层，位于内容生成模块下游。读取待发草稿，通过 Playwright 浏览器自动化将内容发布到小红书。

- **上游依赖**：内容生成模块输出的 `data/{项目}/drafts/index.md`（status=pending_publish）
- **下游输出**：更新 index.md（status=published + xhs_note_id）
- **外部依赖**：Playwright（浏览器自动化）

## 模块架构

```
src/publisher/
├── engine.py         # Playwright 发布流水线（单篇10步）
├── scheduler.py      # 定时扫描 + 时间窗口随机延迟
├── anti_detect.py    # 反检测（桌面UA/webdriver隐藏/打字/滚动）
└── accounts.py       # 账号管理（BrowserContext工厂 + 登录态检测）
```

## 账号管理 (accounts.py)

### 账号配置

每个项目一个 `data/{项目}/accounts.yaml`：

```yaml
accounts:
  - id: account-001
    persona: 老王
    persona_type: investment-advisor
    user_data_dir: data/accounts/account-001/
    login_status: active        # active | expired | blocked
    last_published_at: 2026-05-12T20:00:00
    daily_limit: 1
    preferred_window:
      start: "09:00"
      end: "21:00"
```

### 接口

```python
class AccountManager:
    def list_accounts(project: str) -> list[dict]
    def get_context(account_id: str) -> BrowserContext
    def check_login(context: BrowserContext) -> bool
    def mark_expired(account_id: str)
```

### 登录态管理

- 每个账号独立 `userDataDir`（`data/accounts/{account_id}/`）
- 持久化 Cookie/storage，首次需人工登录一次
- `check_login()` 访问小红书首页，检测是否存在「登录」按钮
- 登录失效 → `login_status: expired` → 通知人工介入
- context 配置：桌面端 Chrome UA、zh-CN、Asia/Shanghai

## 发布流水线 (engine.py)

### 单篇发布10步

1. 加载 BrowserContext（account userDataDir）
2. 验证登录态 → 失效则标记 expired，中断
3. 关弹窗（新手引导/活动弹窗）
4. 点击发布按钮 → 进入创作者中心
5. 上传图片（文件选择器，最多18张，房产建议4-9张）
6. 填写标题（逐字输入，随机间隔80-200ms，最多20字）
7. 填写正文（分段粘贴，带emoji和换行）
8. 添加话题标签（逐个输入，利用平台推荐）
9. 提交发布（点击发布按钮，等待成功回调）
10. 回收笔记ID → 更新 index.md

### 关键参数

- 每步之间间隔：`random.uniform(2, 5)` 秒
- 打字间隔：`random.uniform(80, 200)` 毫秒
- 任何一步失败 → 重试1次 → 仍失败标记 `failed`
- 等待策略：`wait_for_selector` + `wait_for_load_state("networkidle")`

### 接口

```python
class Publisher:
    def publish(draft_id: str, account_id: str, draft_dir: str) -> str  # 返回 xhs_note_id
```

## 反检测策略 (anti_detect.py)

采用桌面端中等强度策略（不用移动端UA，因为小红书主要用App）：

### 策略清单

| 策略 | 实现 |
|------|------|
| 桌面端 Chrome UA | 真实 Windows Chrome UA |
| 隐藏 webdriver | `Object.defineProperty(navigator, 'webdriver', {get: () => false})` |
| 注入 chrome 对象 | `window.chrome = { runtime: {} }` |
| 随机打字速度 | 每字80-200ms随机间隔 |
| 随机滚动 | 随机滚动距离和停留时间 |
| 随机鼠标移动 | 点击前在目标附近轻微偏移 |

### init_script

```javascript
Object.defineProperty(navigator, 'webdriver', {get: () => false});
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
```

### 接口

```python
class AntiDetect:
    @staticmethod
    def get_init_script() -> str
    @staticmethod
    async def human_type(page, selector, text: str)
    @staticmethod
    async def human_scroll(page)
    @staticmethod
    async def human_click(page, selector)
```

## 调度器 (scheduler.py)

### 调度参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 扫描间隔 | 15分钟 | 定期检查待发队列 |
| 发布窗口 | 10:00-21:00 | 每个账号可单独配置 |
| 随机延迟范围 | ±30分钟 | 窗口内随机N分钟后执行 |
| 同账号最小间隔 | 24小时 | 单账号不连续发 |
| 同项目多账号间隔 | 3小时 | 同项目账号错开 |
| 全局并发 | 1个Browser | 一次只处理一篇 |

### 决策流程

```
定时扫描 → 找到 pending_publish 草稿
  ├── 当前时间在账号发布窗口内？
  ├── 距上次发布 ≥ 24小时？
  ├── 同项目其他账号3小时内没发过？
  └── 全部通过 → 随机延迟N分钟 → 执行发布
```

### CLI

```bash
xhs publish --project 中央半岛                  # 启动调度器
xhs publish --project 中央半岛 --id 20260512_001 --account account-001  # 手动单篇
xhs accounts --project 中央半岛                  # 查看登录态
```

### 接口

```python
class Scheduler:
    def __init__(project: str, config: dict)
    async def start()     # 启动定时循环
    async def stop()      # 停止
    async def publish_one(draft_id: str, account_id: str)  # 手动单篇
```

## 文件清单

| 文件 | 职责 |
|------|------|
| `src/publisher/__init__.py` | 模块入口 |
| `src/publisher/accounts.py` | 账号配置加载 + BrowserContext工厂 + 登录检测 |
| `src/publisher/engine.py` | Playwright 发布流水线（10步） |
| `src/publisher/scheduler.py` | 定时扫描 + 时间窗口随机调度 |
| `src/publisher/anti_detect.py` | 反检测脚本 + 拟人化操作 |
| `data/{项目}/accounts.yaml` | 账号配置文件 |

## 依赖

- playwright（浏览器自动化）
- 内容生成模块（`src/content/indexer.py` DraftIndex 读写）
- PyYAML（已有，账号配置解析）
- 规则体系（读取发布配置）
