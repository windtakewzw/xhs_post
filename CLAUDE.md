# CLAUDE.md

本文档为 Claude Code 在此仓库中工作提供指导。

## 项目概述

xhs_post 是一个小红书内容发布系统，面向房地产项目。以 Claude Code Plugin 形式运行。

插件位置：`~/.claude/plugins/xhs/`（用户级），提供四个技能：`xhs:generate`、`xhs:publish`、`xhs:monitor`、`xhs:reply`。

## 模块架构

```
~/.claude/plugins/xhs/       # 插件（运行时）
├── skills/
│   ├── generate/SKILL.md    # 内容生成
│   ├── publish/SKILL.md     # 发布引擎
│   ├── monitor/SKILL.md     # 评论监控
│   └── reply/SKILL.md       # 评论回复
├── scripts/                 # Python 脚本
├── rules/                   # 跨项目共享规则
└── venv/                    # Python 虚拟环境

{项目目录}/                   # 项目专属（CWD）
├── rules/{项目}/            # 项目规则、账号配置
├── materials/{项目}/        # 项目素材（oss 同步）
├── data/{项目}/drafts/      # 草稿和发布索引
└── accounts/                # 浏览器登录态
```

上游设计参考在 `D:\project\yj_skills\skills\xiaohongshu\references\`。

## 常用命令

```bash
# 激活插件 venv
source ~/.claude/plugins/xhs/venv/Scripts/activate
```

## 依赖

- Python 3.12（虚拟环境在 `~/.claude/plugins/xhs/venv/`）
- patchright（浏览器自动化，发布引擎用）
- requests（Seedream API 图片生成）
- PyYAML（YAML 解析）
