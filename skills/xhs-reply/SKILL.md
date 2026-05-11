---
name: xhs-reply
description: Use when replying to comments on published Xiaohongshu posts, writing responses in persona voice, or processing the pending comment queue
---

# 小红书评论回复

读取待回复的评论，用人设语气撰写回复，通过 Playwright 发送。

## 触发场景

1. **处理待回复** — 用户说"回复评论"、"处理评论"、"reply"时处理 pending 队列
2. **回复指定评论** — 用户说"回复这条评论"时用指定人设风格回复

## 数据来源

- 待回复队列：`data/{项目}/comments/pending.json`（xhs-monitor 产出）
- 项目规则：`rules/{项目}/rules.md` → 获取人设语言风格和口径
- 账号配置：`rules/{项目}/accounts.yaml`

## 回复流程

1. Read `data/{项目}/comments/pending.json` → 获取待回复评论列表
2. Read `rules/{项目}/rules.md` → 获取对应人设的语言风格、口头禅、内容禁忌
3. 对每条评论，按**对应笔记发布者的人设**生成回复：

**回复原则：**
- 保持人设语气一致（投资顾问理性克制、生活顾问温暖亲切、家庭顾问贴心务实）
- 简短自然（1-3句话），像真人在对话，不是客服
- 价格相关 → 引导私信，不直接报具体价格
- 位置/户型 → 邀请到访（可提供营销中心地址）
- 正面评价 → 表达感谢，保持人设风格
- 负面/投诉 → 礼貌回应，不争论

4. 通过 Bash 调用 replier.py 发送回复：

```bash
source venv/Scripts/activate && python skills/xhs-reply/scripts/replier.py \
  --note-id {笔记ID} \
  --comment-id {评论ID} \
  --reply-text "{回复文本}" \
  --account-id {账号ID} \
  --accounts-config rules/{项目}/accounts.yaml
```

5. 发送成功后，从 `pending.json` 中移除该条，写入 `data/{项目}/comments/replied.json` 记录历史

## 回复模板（按分类）

| 类别 | 方向 |
|------|------|
| price_inquiry | "价格根据楼层和户型有所不同，方便的话可以来售楼处看看，我帮你详细算一下" |
| visit_intent | "我们在{地址}，每天{时间}都可以，你来之前跟我说一声" |
| interest | 保持人设风格的道谢（如老王："谢谢关注，用数据说话"） |
| general | 不回复 |
| complaint | 人工处理，不自动回复 |
| sensitive | 不回复，标记人工 |

模板仅作方向参考，具体回复需按人设重新表述。

## 回复记录

`data/{项目}/comments/replied.json`：

```json
[
  {
    "note_id": "xxx",
    "comment_id": "c123",
    "comment_content": "三房多少钱？",
    "reply_content": "价格根据楼层和户型有所不同，方便加微信发详细资料给你",
    "persona": "老王",
    "replied_at": "2026-05-13T10:05:00"
  }
]
```
