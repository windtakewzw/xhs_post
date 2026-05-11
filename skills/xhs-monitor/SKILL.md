---
name: xhs-monitor
description: Use when monitoring comments on published Xiaohongshu posts, checking for new interactions, or classifying comments that need replies
---

# 小红书评论监控

通过创作者中心笔记管理页，抓取已发布笔记的评论和互动数据。

## 触发场景

1. **检查评论** — "看看评论"、"有没有新评论"
2. **定时巡检** — `/loop 60m /xhs-monitor` 定时采集

## 数据来源

- 发布索引：`data/{项目}/drafts/index.md` → 查找 `status: published` 的笔记
- 账号配置：`rules/{项目}/accounts.yaml` → 获取活跃账号

## 监控流程

1. 对每个活跃账号执行 fetcher：

```bash
source venv/Scripts/activate && python skills/xhs-monitor/scripts/fetcher.py \
  --account-id {账号ID} \
  --accounts-dir accounts/{账号ID}/
```

2. fetcher 流程：note-manager → 点击封面展开详情 → 滚动面板 → 提取笔记数据和评论

3. fetcher 输出 JSON（标准输出），包含每篇笔记的 stats 和评论内容

4. Claude 分析每条评论：
   - **需要回复**：询问价格/户型/位置、表达意向、正面评价
   - **无需回复**：纯 emoji、无意义内容
   - **负面/敏感**：投诉、攻击标注人工处理

5. 汇总报告：每篇笔记的浏览量/点赞/评论/收藏/分享数 + 需要回复的评论列表

## 评论分类

| 类型 | 示例 | 处理 |
|------|------|------|
| price_inquiry | "多少钱"、"总价多少" | 引导私信 |
| visit_intent | "怎么去看"、"在哪" | 回复位置信息 |
| interest | "好喜欢"、"不错" | 礼貌回复 |
| general | emoji、打卡 | 不回复 |
| complaint | 负面情绪 | 通知人工 |

## 运行频率

`/loop 60m /xhs-monitor` 每 60 分钟自动检查一次。
