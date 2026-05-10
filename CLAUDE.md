# CLAUDE.md

本文档为 Claude Code 在此仓库中工作提供指导。

## 项目概述

xhs_post 是一个小红书内容发布系统，面向房地产项目。生成房产主题的图文笔记（文案 + 图片），通过浏览器自动化发布到小红书。

当前阶段：规则体系已完成（11 tests passing），下一步实现内容生成和发布引擎。

## 模块规划

1. **规则体系** — 可维护的 Markdown 规则文件（人设、内容类型、文案、图片、标签）
2. **内容生成** — 选题 + Claude API 文案生成 + Seedream API 图片生成
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
```

## 架构

规则以 Markdown 文件形式存储，不是代码。`src/rules/loader.py` 将 Markdown 解析为 Python 数据结构（`src/rules/models.py`），`src/rules/assembler.py` 从结构化规则组装 AI Prompt 上下文。

规则分两级：
- `rules/*.md` — 全局规则，跨项目共享（文案写法、图片生成、标签策略）
- `rules/{项目名}/rules.md` — 项目规则（人设定义、内容策略、禁忌）

上游设计参考在 `D:\project\yj_skills\skills\xiaohongshu\references\`（非运行时依赖）。

## 依赖

- Python 3.11+（虚拟环境在 `venv/`）
- PyYAML（frontmatter 解析）
- pytest（测试）
