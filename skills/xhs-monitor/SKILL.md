---
name: xhs-monitor
description: Use when monitoring comments on published Xiaohongshu posts, checking for new interactions, or classifying comments that need replies
---

# 小红书评论监控

拉取已发布笔记的评论，分类整理，标记需要回复的评论。

## 触发场景

1. **检查评论** — 用户说"看看评论"、"有没有新评论"、"评论监控"
2. **定期巡检** — /loop 定时触发，自动采集新评论

## 数据来源

- 发布索引：`data/{项目}/drafts/index.md` → 查找所有 `status: published` 的笔记及其 `xhs_note_id`
- 账号配置：`rules/{项目}/accounts.yaml` → 获取可用的活跃账号

## 监控流程

1. Read `data/{项目}/drafts/index.md` → 找到所有已发布的笔记
2. 对每篇笔记，用 fetcher.py 拉取最新评论：

```bash
source venv/Scripts/activate && python skills/xhs-monitor/scripts/fetcher.py \
  --note-id {xhs_note_id} \
  --account-id {账号ID} \
  --accounts-config rules/{项目}/accounts.yaml \
  --project {项目名}
```

3. fetcher.py 输出 JSON 格式的评论列表到 stdout

4. Claude 分析每条评论：
   - **需要回复**：询问价格/户型/位置、表达意向、正面评价
   - **无需回复**：纯 emoji、路过留言、无意义内容
   - **负面/敏感**：投诉、攻击、需人工处理

5. 将需要回复的评论写入 `data/{项目}/comments/pending.json`：

```json
[
  {
    "note_id": "xxx",
    "note_title": "LPR又降了",
    "comment_id": "c123",
    "author": "用户A",
    "content": "三房多少钱？",
    "category": "price_inquiry",
    "fetched_at": "2026-05-13T10:00:00"
  }
]
```

6. 汇总报告给用户：每个账号的新评论数、需要回复的数量、是否有异常评论

## 评论分类规则

| 类型 | 示例 | 处理 |
|------|------|------|
| price_inquiry | "多少钱"、"总价多少" | xhs-reply 自动回复（引导私信） |
| visit_intent | "怎么去看"、"在哪" | xhs-reply 自动回复 |
| interest | "好喜欢"、"不错" | xhs-reply 礼貌回复 |
| general | emoji、打卡 | 不回复 |
| complaint | 负面情绪 | 通知人工处理 |
| sensitive | 违规内容 | 通知人工处理 |

## 运行频率

首次手动触发（`/xhs-monitor`），后续建议 `/loop 30m /xhs-monitor` 每30分钟自动检查。
