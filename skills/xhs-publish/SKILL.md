---
name: xhs-publish
description: Use when publishing Xiaohongshu drafts via browser automation, checking account login status, or manually publishing a specific draft to a target account
---

# 小红书内容发布

通过 Playwright 浏览器自动化将草稿发布到小红书。扫描 `data/{项目}/drafts/index.md` 中状态为 `pending_publish` 的草稿。

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
6. 调用 publisher.py 执行 Playwright 发布

### 手动单篇

```bash
source venv/Scripts/activate && python skills/xhs-publish/scripts/publisher.py \
  --draft-dir data/{项目}/drafts/{YYYYMMDD}_{seq}/ \
  --account-id {账号ID} \
  --accounts-config rules/{项目}/accounts.yaml
```

### 检查登录态

Read `rules/{项目}/accounts.yaml`，列出每个账号的 `login_status`。

## 发布脚本 (publisher.py)

Bash 调用：

```bash
source venv/Scripts/activate && python skills/xhs-publish/scripts/publisher.py \
  --draft-dir data/{项目}/drafts/{YYYYMMDD}_{seq}/ \
  --account-id {account_id} \
  --accounts-config rules/{项目}/accounts.yaml
```

脚本执行 Playwright 发布10步：

1. 加载 BrowserContext（账号 userDataDir）
2. 验证登录态 → 失效则退出码 2
3. 关弹窗
4. 进入创作者中心
5. 上传图片
6. 填写标题（逐字输入，80-200ms 随机间隔）
7. 填写正文（分段粘贴）
8. 添加话题标签
9. 点击发布
10. 回收笔记 ID

### 成功时（退出码 0）：

- 更新 `accounts.yaml` 中 `last_published_at`
- 返回笔记 ID
- Claude 更新 `index.md`：该行状态改为 `published`，填入 `xhs_note_id`

### 登录失效时（退出码 2）：

- 更新 `accounts.yaml` 中 `login_status` 为 `expired`
- Claude 通知用户："账号 {persona} ({account_id}) 登录已失效，请人工登录"

### 其他失败时（退出码 1）：

- 更新 `index.md`：该行状态改为 `failed`
- 记录错误信息

## 反检测策略

- 桌面端 Chrome UA（不模拟移动端）
- 隐藏 navigator.webdriver
- 注入 window.chrome 对象
- 逐字打字 + 随机间隔
- 操作间随机暂停 2-5 秒

## 首次使用

每个账号首次使用时需人工登录一次：

1. Playwright 启动浏览器窗口（headless=false）
2. 用户手动扫码/密码登录
3. 登录态持久化到 userDataDir
4. 后续自动复用

账号配置中 `login_status` 设为 `active`。
