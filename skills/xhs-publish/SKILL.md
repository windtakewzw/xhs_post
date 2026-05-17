---
name: xhs-publish
description: Use when publishing Xiaohongshu drafts via browser automation, checking account login status, or manually publishing a specific draft to a target account
---

# 小红书内容发布

通过 Patchright 浏览器自动化将草稿发布到小红书。扫描 `data/{项目}/drafts/index.md` 中状态为 `pending_publish` 的草稿。

## 核心架构：CDP 模式

**策略：不伪装，而是"本来就是真的"。**

```
真人 Chrome（带历史、书签、扩展）
    ↑ CDP 连接 (connect_over_cdp)
Patchright（协议层修补，不注入 JS）
    ↑
publisher.py
```

区别于旧方案（Playwright `launch()` 自启浏览器 → 注入 JS 改指纹 → 3-5 次操作后被风控），CDP 模式连接用户日常使用的 Chrome，天然具备真实浏览器指纹。

## 前置条件

**首次使用前，启动 CDP Chrome 并登录小红书：**

```bash
# 1. 启动 CDP Chrome
scripts/launch_chrome_cdp.bat

# 2. 在打开的 Chrome 窗口中访问 creator.xiaohongshu.com 并登录
# 3. 登录态持久化在 accounts/chrome-cdp-profile/ 中，后续无需重复登录
```

## 触发场景

1. **启动调度** — 用户说"开始发布"、"启动发布"、"publish {项目}"时启动发布循环
2. **手动发布** — 用户指定某篇草稿"发这篇"、"把 draft-xxx 发了"
3. **检查账号** — 用户说"检查账号"、"看下登录状态"

## 数据来源

- 草稿索引：`data/{项目}/drafts/index.md`（xhs-generate 生成）
- 账号配置：`rules/{项目}/accounts.yaml`

## 账号配置格式

```yaml
# rules/{项目}/accounts.yaml
accounts:
  - id: account-001
    persona: 老王
    persona_type: investment-advisor
    user_data_dir: accounts/account-001/
    login_status: active
    last_published_at: 2026-05-12T20:00:00
    daily_limit: 1
    preferred_window:
      start: "09:00"
      end: "21:00"
```

## 发布流程

### 自动调度

用户启动后，每 15 分钟执行一次：

1. Read `data/{项目}/drafts/index.md` → 找到状态为 `pending_publish` 的条目
2. Read `rules/{项目}/accounts.yaml` → 找到匹配人设的活跃账号
3. 检查时间窗口（是否在账号 preferred_window 内）
4. 检查冷却时间（距该账号上次发布 ≥ 24 小时，同项目其他账号 ≥ 3 小时）
5. 通过后，随机延迟（窗口内 0-30 分钟），然后执行发布
6. 调用 publisher.py 执行发布

### 手动单篇

```bash
source venv/Scripts/activate && python skills/xhs-publish/scripts/publisher.py \
  --draft-dir data/{项目}/drafts/{YYYYMMDD}_{seq}/ \
  --account-id {账号ID} \
  --accounts-config rules/{项目}/accounts.yaml
```

### 检查登录态

Read `rules/{项目}/accounts.yaml`，列出每个账号的 `login_status`。
也可以直接打开 CDP Chrome 窗口检查是否仍处于登录状态。

## 发布脚本 (publisher.py)

CDP 模式（默认）：

```bash
source venv/Scripts/activate && python skills/xhs-publish/scripts/publisher.py \
  --draft-dir data/{项目}/drafts/{YYYYMMDD}_{seq}/ \
  --account-id {account_id} \
  --accounts-config rules/{项目}/accounts.yaml \
  --cdp-endpoint 127.0.0.1:9222
```

Launch 降级模式（CDP 不可用时）：

```bash
source venv/Scripts/activate && python skills/xhs-publish/scripts/publisher.py \
  --draft-dir data/{项目}/drafts/{YYYYMMDD}_{seq}/ \
  --account-id {account_id} \
  --accounts-config rules/{项目}/accounts.yaml \
  --no-cdp
```

### 两种模式对比

| 维度 | CDP 模式（默认） | Launch 模式（降级） |
|------|------------------|---------------------|
| 浏览器 | 用户真实 Chrome | Patchright 自启 Chromium |
| 指纹 | 天然真实（历史、扩展、书签） | 全新实例，仅协议层修补 |
| `add_init_script()` | ❌ 不使用（破坏网络栈） | ✅ 注入反检测 JS |
| `new_context()` | ❌ 不使用（破坏 TLS） | ✅ 创建隔离 context |
| UA 覆盖 | ❌ 不碰 | ❌ 不碰 |
| 风控预期 | 长期稳定 | 3-5 次操作后触发 |

### 发布步骤

1. CDP 连接 Chrome → 用已有 context，注入 cookies
2. 打开创作者中心发布页 → 检查登录态
3. 随机浏览 2-5 个创作者中心菜单（反检测）
4. 上传图片
5. 填写标题（逐字输入，60-180ms 随机间隔）
6. 填写正文（分段粘贴）
7. 添加话题标签
8. 点击发布
9. 发布后随机浏览 → 保存 cookies 快照

### 成功时（退出码 0）：

- 更新 `accounts.yaml` 中 `last_published_at`
- 返回笔记 ID
- Claude 更新 `index.md`：该行状态改为 `published`，填入 `xhs_note_id`

### 登录失效时（退出码 2）：

- 更新 `accounts.yaml` 中 `login_status` 为 `expired`
- Claude 通知用户："账号 {persona} ({account_id}) 登录已失效，请在 CDP Chrome 窗口中重新登录"

### CDP 不可用时（退出码 3）：

- 提示用户运行 `scripts/launch_chrome_cdp.bat` 启动 CDP Chrome
- 或使用 `--no-cdp` 降级为 launch 模式

### 其他失败时（退出码 1）：

- 更新 `index.md`：该行状态改为 `failed`

## 反检测策略

- **CDP 模式**：连接真人 Chrome，天然指纹，不注入任何 JS
- Patchright 协议层修补：移除 `Runtime.enable`/`Console.enable` 泄露，禁用 `AutomationControlled`
- 逐字打字 + 随机间隔（60-180ms per char）
- 操作间随机暂停，有快有慢
- 发布前后随机浏览创作者中心菜单（模拟真人操作习惯）
- 不覆盖 User-Agent（Chrome 自己的 UA 是最好的 UA）

## Chrome CDP 管理

```bash
# 启动 CDP Chrome（首次或重启后）
scripts/launch_chrome_cdp.bat

# 检查 CDP 是否就绪
curl http://127.0.0.1:9222/json/version
```

Chrome Profile 位置：`accounts/chrome-cdp-profile/`
CDP 端口：`9222`

## 多账号

CDP 模式下一个 Chrome 实例 = 一个账号的登录态。多账号需要多个 Chrome 实例，各自使用独立的 Profile 目录和 CDP 端口。暂未实现多实例管理，需要时扩展。
