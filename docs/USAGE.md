# 使用文档

## 部署

在新环境部署时，按顺序向 Claude 说：

| 步骤 | 文档 | 对话 |
|------|------|------|
| 1 | 01-install.md | "按 docs/install/01-install.md 安装" |
| 2 | 02-materials.md | "按 docs/install/02-materials.md 配置素材" |
| 3 | 03-init-project.md | "按 docs/install/03-init-project.md 初始化项目" |

Claude 会按文档中的步骤逐项执行，遇到异常会自动检测并提示。

### 部署后验证

```bash
# Skill 已安装
ls ~/.claude/skills/xhs-*/

# 发布脚本可用
source venv/Scripts/activate
python skills/xhs-publish/scripts/publisher.py --help

# 监控脚本可用
python skills/xhs-monitor/scripts/fetcher.py --account-id account-001

# 项目规则完整
grep -c "{{" rules/{项目}/rules.md && echo "! 占位符未替换" || echo "OK"

# 素材可访问
ls materials/{项目}/docs/
```

## 模块运行方式

| 模块 | 触发 | 说明 |
|------|------|------|
| xhs-generate | Claude 对话 | 读规则 → 选题 → 写文案 → 存草稿 |
| xhs-publish | 定时任务 / 手动 | 扫描 `pending_publish` 草稿发布 |
| xhs-monitor | 定时任务 / 手动 | 采集评论数据 |
| xhs-reply | Claude 对话 | 读评论 → 人设回复 → 发送 |

## 日常操作

### 生成内容

| 操作 | 对话 |
|------|------|
| 生成一篇 | "帮老王生成一篇市场分析" |
| 指定主题 | "帮小陈写一篇园林生活，主题是傍晚散步" |
| 批量生成 | "为中央半岛所有人设各生成一篇本周内容" |

生成后草稿在 `data/{项目}/drafts/{日期}_{序号}/post.md`。

### 审核草稿

在对话中说"审核通过 20260510_001"，Claude 把 index.md 中该草稿状态改为 `pending_publish`。

### 发布

定时任务自动执行。手动发布：

```bash
source venv/Scripts/activate
python skills/xhs-publish/scripts/publisher.py \
  --draft-dir data/中央半岛/drafts/20260510_001/ \
  --account-id account-001 \
  --accounts-config rules/中央半岛/accounts.yaml \
  --headless
```

### 查看评论

```bash
source venv/Scripts/activate
python skills/xhs-monitor/scripts/fetcher.py \
  --account-id account-001 \
  --accounts-dir accounts/account-001/
```

### 回复评论

在对话中说"看看有没有需要回复的评论"，Claude 会采集评论并按人设生成回复。

## 规则维护

所有规则以 Markdown 存储，直接对话修改：

| 操作 | 对话 |
|------|------|
| 调整内容占比 | "把老王的市场分析占比调到 40%" |
| 修改人设风格 | "小陈的语言风格改成更年轻化一些" |
| 新增城市标签 | "把成都的标签库加上" |
| 调整发布频次 | "阿芳改成每周发 1 篇" |

Claude 直接 Edit 对应文件，下次生成自动生效。

## 账号管理

### 查看状态

```bash
grep "login_status" rules/中央半岛/accounts.yaml
```

### 登录 / 重新登录

```bash
source venv/Scripts/activate
python scripts/login.py account-001
```

### 新增账号

在 `rules/{项目}/accounts.yaml` 追加，然后登录。

## 常见问题

| 问题 | 处理 |
|------|------|
| 发布提示 login_expired | 重新 `python scripts/login.py {账号}` |
| 草稿找不到 | 检查 index.md 状态是否为 `pending_publish` |
| 定时任务没跑 | 检查 Windows 任务计划程序 |
| 生成内容没变化 | 检查 materials 挂载是否正常 |
