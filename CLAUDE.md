# CLAUDE.md

本文档为 Claude Code 在此仓库中工作提供指导。

## 项目概述

xhs_post 是一个小红书内容发布系统，面向房地产项目。生成房产主题的图文笔记（文案 + 图片），通过浏览器自动化发布到小红书。

当前阶段：规则体系 + 内容生成已完成（32 tests passing），下一步实现发布引擎。

## 模块规划

1. **规则体系** — 可维护的 Markdown 规则文件（人设、内容类型、文案、图片、标签）✅ 完成
2. **内容生成** — 选题 + Claude API 文案生成 + Seedream API 图片生成 ✅ 完成
3. **发布引擎** — Playwright 浏览器自动化 + 调度 + 多账号管理
4. **评论跟踪** — 监控和采集已发布笔记的评论
5. **评论回复** — AI 辅助或自动回复评论

设计文档见 `docs/superpowers/specs/`，实现计划见 `docs/superpowers/plans/`。

## 常用命令

```bash
# 激活虚拟环境
source venv/Scripts/activate

# 运行所有测试
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/rules/test_models.py -v

# 运行单个测试函数
python -m pytest tests/rules/test_models.py::test_persona_creation -v

# CLI 帮助
python -m src.cli --help
```

## 架构

**规则体系** (`src/rules/`)：`loader.py` 解析 Markdown 规则 → `models.py` 数据类 → `assembler.py` 组装 Prompt 上下文。全局规则在 `rules/*.md`，项目规则在 `rules/{项目}/rules.md`。

**内容生成** (`src/content/`)：`topic.py` 选题引擎读 `index.md` 决定发什么 → `copywriter.py` 调 Claude API 写文案 → `imager.py` 调 Seedream API 生图片 → 输出到 `data/{项目}/drafts/`。

草稿索引 `data/{项目}/drafts/index.md` 追踪所有生成和发布状态（Markdown 表格 + YAML frontmatter）。

Cli 入口：`src/cli.py`（click），命令：generate / batch / status / approve / reject。

上游设计参考在 `D:\project\yj_skills\skills\xiaohongshu\references\`（非运行时依赖）。

## 依赖

- Python 3.12（虚拟环境在 `venv/`）
- anthropic（Claude API）
- click（CLI）
- requests（Seedream API + 图片下载）
- PyYAML（frontmatter 解析）
- pytest（测试）
