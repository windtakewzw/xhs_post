---
name: xhs-generate
description: Use when generating or batch-producing Xiaohongshu (小红书) real estate content, or when maintaining content rules including personas, content types, copywriting guidelines, and hashtag strategies
---

# 小红书内容生成

读取 `rules/` 中的 Markdown 规则文件，为房地产项目生成小红书图文笔记。

## 触发场景

1. **内容生成** — 用户说"生成"、"批量"、"写一篇"、"产出"时执行生成流程
2. **规则维护** — 用户说"修改规则"、"调整占比"、"新增人设"、"改标签"时编辑 rules/ 文件

## 规则文件

```
rules/
├── copywriting-rules.md   # 怎么写（标题公式/正文模板/去AI味/合规）
├── image-rules.md         # 图片策略（决策矩阵/提示词/视觉风格）
├── hashtag-rules.md       # 标签策略（分层/城市库/人设库）
└── {项目名}/
    └── rules.md           # 项目规则（人设/内容策略/禁忌/发布配置）
```

生成内容前必须 Read 对应的 `rules/{项目}/rules.md`（获取人设和策略）和 `rules/copywriting-rules.md`（获取写作规范）。如需要图片生成信息，Read `rules/image-rules.md`。

## 生成流程

### 单篇生成

用户指定项目和人设时：

1. Read `rules/{项目}/rules.md` → 获取该人设的完整定义（姓名/性格/语言风格/口头禅/内容禁忌）
2. Read `rules/copywriting-rules.md` → 获取去AI味写作法则和合规红线
3. 选题：按人设的 `content_sequence` 轮换序列取下一个类型。查 `data/{项目}/drafts/index.md` 获取发布历史，跳过3天内已发过的内容类型
4. 加载项目素材：Read `materials/{项目}/docs/` 下的 Markdown 文件作为事实依据
5. 生成文案：按人设风格 + 去AI味法则 + 合规要求生成标题、正文、标签，输出格式：

```markdown
---
id: draft-{YYYYMMDD}-{seq}
project: {项目名}
persona: {人设名}
persona_type: {人设类型}
content_type: {内容类型}
generated_at: {时间}
status: draft
review_required: {true/false}
---

# {标题}

{正文}

#标签1 #标签2 #标签3
```

6. 保存到 `data/{项目}/drafts/{YYYYMMDD}_{seq}/post.md`
7. 更新 `data/{项目}/drafts/index.md`（追加一行记录）
8. 询问用户是否需要生成图片（如有 Seedream API Key）

### 批量生成

用户说"批量生成 {项目} 一周内容"时：

1. Read 项目规则 → 获取所有人设及其发布频次
2. 为每个人设按轮换序列选题 → 生成一週需要的篇数
3. 逐篇生成（同单篇流程 1-7），确保同项目多人设内容不撞主题
4. 逐篇输出到对应 drafts/ 目录

### 图片生成

用户确认后，Bash 调用 `python skills/xhs-generate/scripts/imager.py`：

```bash
source venv/Scripts/activate && python skills/xhs-generate/scripts/imager.py \
  --content-type {类型} --persona-type {人设类型} \
  --project-dir materials/{项目} --title "{标题}" \
  --output-dir data/{项目}/drafts/{id}/images/
```

Script 根据 `rules/image-rules.md` 的决策矩阵决定每张图片用 text2img 还是 img2img，调用 Seedream API 生图，自动追加合规标注。

## 规则维护

用户修改规则时，直接 Edit 对应的 rules/ 文件：

- **调整内容占比**：Edit `rules/{项目}/rules.md` 中对应人设的**内容占比**表格
- **修改人设风格**：Edit 人设定义中的语言风格/口头禅/写作用语
- **新增项目**：复制 `rules/{项目}/rules.md` 作为模板，修改人设和策略
- **新增城市标签**：Edit `rules/hashtag-rules.md` 追加城市标签库
- **调整频次**：Edit 人设定义中的**发布频次**

## 发布索引

`data/{项目}/drafts/index.md` 追踪所有草稿和发布状态：

```markdown
---
project: {项目名}
updated: {时间}
---

| 日期 | 序号 | 人设 | 内容类型 | 标题 | 状态 |
|------|------|------|---------|------|------|
```

状态：`draft` → `pending_review`（待审） / `pending_publish`（待发） → `published` → 由 xhs-publish skill 回写

## 去AI味检查清单

每篇生成后自查：

- [ ] 有超过3个四字成语或书面词吗？
- [ ] 能想象出"一个人这样说话"吗？
- [ ] 句长有变化吗（有短有长）？
- [ ] 暴露至少一个真实小缺点了吗？
- [ ] 写了一个具体时刻吗（"下午三点"）？
- [ ] 用了"首先/其次/综上所述"等AI标志词吗？
- [ ] 符合 `rules/{项目}/rules.md` 中的人设语言风格和口头禅吗？
- [ ] 触犯项目内容禁忌了吗？
