# xhs_post 内容生成模块设计

## 概述

内容生成模块是 xhs_post 的核心生产单元，位于规则体系和发布引擎之间。

- **上游依赖**：规则体系（rules/ 目录 + src/rules/loader.py + assembler.py）
- **下游输出**：`data/{项目}/drafts/{日期}_{序号}/` 草稿目录，供发布引擎消费
- **外部服务**：Claude API（文案生成）+ Seedream API（图片生成）

## 选题引擎 (src/content/topic.py)

### 决策流程

```
输入：项目名 + 可选(人设, 内容类型)
  ├── CLI 手动指定了人设+类型？
  │   └── 是 → 直接用
  └── 否 → 自动选题：
        ├── 读 index.md → 获取每个人设的最近发布类型和日期
        ├── 读项目 rules.md → 人设轮换序列
        ├── 取轮换序列中下一个类型（跳过3天内已发过的主题）
        └── 返回 (人设, 内容类型)
```

### 去重规则

- 同一项目内 3 天内不重复内容类型
- 同一人设不连续两篇同类型
- 去重通过 index.md 表格查询，不扫文件系统

## 发布索引 (data/{项目}/drafts/index.md)

一个 Markdown 文件记录该项目所有生成和发布历史。选题去重、状态追踪、发布引擎回写都通过此文件。

```markdown
---
project: 中央半岛
updated: 2026-05-12
---

| 日期 | 序号 | 人设 | 内容类型 | 标题 | 状态 |
|------|------|------|---------|------|------|
| 2026-05-10 | 001 | 老王 | market-analysis | LPR又降了 | published |
| 2026-05-10 | 002 | 小陈 | community-life | 周末在小区待了一天 | published |
| 2026-05-12 | 001 | 阿芳 | family-living | 带娃家庭选115㎡ | draft |
```

状态流转：`generating` → `draft` / `pending_review` → `pending_publish` → `published`

### 选题接口

```python
def select_topic(project: str, persona: str = None, content_type: str = None) -> list[tuple[str, str]]:
    """返回 [(人设名, 内容类型), ...] 单篇1个，批量N个"""
```

## 文案生成器 (src/content/copywriter.py)

### 流程

1. 接收：项目名 + 人设名 + 内容类型 + 可选主题
2. 通过 loader.load_ruleset() 加载 RuleSet
3. 调用 assembler.assemble_prompt_context() 组装 System Prompt + Persona Context
4. 加载项目素材（`data/{项目}/楼盘简介/`、`销售说辞/`、`户型清单/` 等）注入 User Prompt
5. 调用 Claude API，请求 JSON 输出 `{title, body, hashtags}`
6. 去 AI 味检查（自查清单 6 条），不合格重试一次
7. 写入 post.md + 更新 index.md
8. 返回草稿路径

### Claude API 调用

- 模型：配置项，默认 claude-sonnet-4-6
- System Prompt = 去AI味法则 + 合规红线 + 项目内容禁忌
- User Prompt = 人设上下文 + 内容类型要求 + 项目素材
- 输出格式：`{"title": "...", "body": "...", "hashtags": ["...", ...]}`
- 利用 assembler.py 组装上下文，不在 copywriter.py 中重复拼 Prompt

### 接口

```python
def generate_copy(rs: RuleSet, persona_name: str, content_type: str, project_dir: str, topic: str = None) -> dict:
    """返回 {title, body, hashtags}"""
```

## 图片生成器 (src/content/imager.py)

### 流程

1. 接收：内容类型 + 人设类型 + 项目名 + 标题文本
2. 从 image-rules.md 获取该内容类型的图片配置（张数、每张类型）
3. 扫描 `data/{项目}/media/` 判断素材可用性
4. 按决策表决定每张图片的生成模式（text2img / img2img）
5. 按人设视觉风格注入色调/光线/氛围关键词
6. 逐张调用 Seedream API
7. 下载图片到 `drafts/{date}_{seq}/images/`
8. 自动追加合规标注（概念图/效果图）

### 决策表（来自 image-rules.md）

| 场景 | 模式 | strength | 标注 |
|------|------|----------|------|
| 有实景照片 | img2img | 0.3-0.4 | 无需 |
| 仅有效果图 | img2img | 0.4-0.5 | 效果图仅供参考 |
| 无任何素材 | text2img | — | 概念示意图 |
| 标题封面/信息卡片 | text2img | — | 无需 |

### Seedream API

- 端点、参数见 image-rules.md 配置
- API Key 从环境变量 `SEEDREAM_API_KEY` 读取
- 尺寸固定 2304×4096（9:16 竖屏）

### 接口

```python
def generate_images(content_type: str, persona_type: str, project_dir: str, title: str, output_dir: str) -> list[str]:
    """返回图片文件路径列表"""
```

## CLI 接口 (src/cli.py)

```bash
xhs generate --project 中央半岛 --persona 老王
xhs generate --project 中央半岛 --persona 老王 --type market-analysis
xhs batch --project 中央半岛 --days 7
xhs batch --project 中央半岛 --persona 老王 --count 3
xhs status --project 中央半岛
xhs approve --project 中央半岛 --id 20260512_001
xhs reject --project 中央半岛 --id 20260512_001
```

## 项目规则扩展

在项目 `rules.md` 的 frontmatter 中增加 `review_required` 字段：

```yaml
---
project: 中央半岛
city: 海口
type: 高端改善盘
features: [海景, 园林大盘]
review_required: true   # 生成后需人工审核
---
```

- `review_required: false` → 生成后状态直接为 `pending_publish`
- `review_required: true` → 生成后状态为 `pending_review`，需 `xhs approve` 后变为 `pending_publish`

## 文件清单

| 文件 | 职责 |
|------|------|
| `src/content/__init__.py` | 模块入口 |
| `src/content/topic.py` | 选题引擎，读写 index.md |
| `src/content/copywriter.py` | Claude API 文案生成 |
| `src/content/imager.py` | Seedream API 图片生成 |
| `src/cli.py` | CLI 入口 |
| `data/{项目}/drafts/index.md` | 发布索引（运行时生成） |
| `data/{项目}/drafts/{日期}_{序号}/post.md` | 单篇草稿 |

## 依赖

- 规则体系（`src/rules/loader.py`, `src/rules/assembler.py`, `src/rules/models.py`）
- anthropic SDK（Claude API）
- requests / httpx（Seedream API 调用 + 图片下载）
- click 或 argparse（CLI）
- PyYAML（已有）
