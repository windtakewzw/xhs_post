---
name: xhs-reply
description: Use when replying to comments on Xiaohongshu posts using persona voice, or when reviewing comments that need replies
---

# 小红书评论回复

用人设语气自动回复评论。通常在 `/xhs-monitor` 发现需要回复的评论后触发。

## 触发场景

1. **手动回复** — "看看有没有需要回复的评论"、"帮老王回复一下"
2. **定时联动** — `/xhs-monitor` 发现需回复评论后自动触发 `/xhs-reply`

## 数据来源

- 发布索引：`data/{项目}/drafts/index.md` → 获取笔记对应的人设
- 项目规则：`rules/{项目}/rules.md` → 获取人设语言风格和口径
- 账号配置：`rules/{项目}/accounts.yaml` → 获取账号信息

## 回复流程

1. Claude 根据监控结果，选择需要回复的评论
2. Read `rules/{项目}/rules.md` → 获取对应人设的口头禅、语言风格、内容禁忌
3. Claude 用该人设的语气生成回复文案
4. 通过 Bash 发送回复：

```bash
source venv/Scripts/activate && python skills/xhs-reply/scripts/replier.py \
  --reply-text "{回复文案}" \
  --account-id {账号ID} \
  --accounts-dir accounts/{账号ID}/
```

replier 流程：note-manager → 点封面进详情 → 滚动到评论区 → 填写回复 → 发送。

## 回复风格

严格遵循 `rules/{项目}/rules.md` 中的人设定义：
- 语言风格（如"理性自信、多用数据对比"）
- 口头禅（如"用数据说话"、"说实话"）
- 写作用语习惯（✅ 和 ❌ 列表）
- 内容禁忌（如不承诺升值幅度、不制造焦虑）

## 注意事项

- 同一评论不重复回复
- 每次回复前检查账号登录态，过期则提示重新登录
- 负面/敏感评论不自动回复，通知人工处理
