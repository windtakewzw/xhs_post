# CLAUDE.md

本文档为 Claude Code 在此仓库中工作提供指导。

## 项目概述

xhs_post 是一个小红书内容发布系统，面向房地产项目。以 Claude Code Skill 的形式运行（非独立 CLI）。

## 模块架构

```
skills/
├── xhs-generate/     # 内容生成（读规则 → 写文案 → 生图）
├── xhs-publish/      # 发布引擎（Playwright 浏览器自动化） [待建]
├── xhs-monitor/      # 评论监控 [待建]
└── xhs-reply/        # 评论回复 [待建]

rules/                # Markdown 规则文件（Claude 直接读写）
data/                 # 运行时数据（草稿、账号配置）
```

上游设计参考在 `D:\project\yj_skills\skills\xiaohongshu\references\`。

## 常用命令

```bash
source venv/Scripts/activate
```

## 依赖

- Python 3.12（虚拟环境在 `venv/`）
- playwright（浏览器自动化，发布引擎用）
- requests（Seedream API 图片生成）
- PyYAML（YAML 解析）
