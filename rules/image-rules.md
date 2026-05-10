# 图片生成规则

定义小红书笔记配图的生成策略、决策矩阵和提示词规范。跨项目共享。

---

## 一、生成模式决策

### 决策流程

```
检查项目素材库
├── 有实景照片？
│   └── 是 → img2img（strength=0.3-0.4，无需合规标注）
├── 仅有效果图？
│   └── 是 → img2img（strength=0.4-0.5，标注"效果图仅供参考"）
├── 无任何素材？
│   └── 是 → text2img（标注"概念示意图，以实际为准"）
├── 图片类型为"标题封面/信息卡片"？
│   └── 始终 text2img
└── 意图为"修改/重新诠释现有图片"？
    └── img2img（strength=0.5，标注"效果图仅供参考"）
```

### 决策表

| 场景 | 模式 | strength | 标注 |
|------|------|----------|------|
| 有实景照片 | img2img | 0.3-0.4 | 无需 |
| 仅有效果图 | img2img | 0.4-0.5 | 效果图仅供参考 |
| 无任何素材 | text2img | — | 概念示意图，以实际为准 |
| 标题/封面卡片 | text2img | — | 无需 |
| 信息/数据卡片 | text2img | — | 无需 |
| 修改现有图片 | img2img | 0.5 | 按需 |

---

## 二、多图排版

### 标准6图结构

```
图1：标题封面（text2img）
  吸引点击，大字标题 + 项目元素 + 人设色调
  尺寸：2304×4096（9:16竖屏）

图2-4：核心内容图（img2img优先）
  项目实景/户型/配套

图5：信息/数据卡片（text2img）
  关键数据/配套清单，简洁图表风格

图6：CTA结尾图（text2img）
  项目Logo + 引导咨询/关注
```

### 按内容类型的图片配置

| 内容类型 | 图数 | 图1 | 图2 | 图3 | 图4 | 图5 | 图6 |
|---------|------|-----|-----|-----|-----|-----|-----|
| market-analysis | 4-5 | 数据封面 | 图表卡片 | 项目关联 | CTA | — | — |
| area-value | 5-6 | 区域封面 | 规划图 | 配套实拍 | 项目区位 | 信息卡 | CTA |
| product-analysis | 5-6 | 户型封面 | 客厅 | 主卧 | 阳台景观 | 户型标注 | CTA |
| buying-guide | 4-5 | 攻略封面 | 要点卡片 | 要点卡片 | 项目实景 | CTA | — |
| community-life | 5-7 | 社区封面 | 园林 | 泳池/会所 | 细节特写 | 细节特写 | CTA |
| home-aesthetics | 5-7 | 美学封面 | 光线特写 | 材质细节 | 空间全景 | 软装灵感 | CTA |
| family-living | 5-7 | 家庭封面 | 客厅家庭版 | 儿童房 | 餐厅 | 教育配套 | CTA |
| trend-jacking | 4-5 | 热点融合封面 | 热点关联 | 项目实景 | 项目实景 | CTA | — |

---

## 三、Seedream API 参数

公共参数：
- 端点：`https://ark.cn-beijing.volces.com/api/v3/images/generations`
- 认证：`Authorization: Bearer {SEEDREAM_API_KEY}`
- 模型：`{SEEDREAM_MODEL_NAME}`（默认 seedream-5.0-lite）
- 尺寸：`2304x4096`（9:16竖屏）
- scale：7.5
- ddim_steps：30

---

## 四、提示词规范

### text2img 封面图提示词结构

```
[主视觉] A real estate social media cover image for Xiaohongshu.
[内容] The cover features {核心视觉}, with {辅助元素}.
[排版] Large Chinese title text "{标题}" at {位置}, {字体风格}.
[色调] Color palette: {主色调}, {辅助色调}.
[质感] {光线条件}, {材质描述}, {气氛}.
[约束] Clean modern design, vertical 9:16 format,
  no QR code, no phone numbers, no watermarks,
  professional real estate photography style.
```

### img2img 场景图提示词结构

```
[基础] Real estate property photo, {场景类型}.
[保留] Keep the original {保留的关键特征}.
[增强] Enhance {增强的方面}, add {新增元素}.
[色调] Color tone: {色调描述}, {光线}.
[约束] Maintain architectural accuracy, realistic style,
  no distortion, professional real estate photography, vertical 9:16.
```

### 全局负面提示词

```
text overlay, watermarks, QR codes, phone numbers, logos,
distorted architecture, unrealistic proportions, blurry, low quality,
cartoon, illustration, 3D render style, overly saturated,
cluttered composition, messy, dark shadows, harsh lighting
```

---

## 五、按人设的视觉风格

| 人设 | 色调 | 光线 | 氛围 |
|------|------|------|------|
| investment-advisor | cool tones, navy, silver, white, blue-gray | bright, clean, professional | confident, authoritative |
| lifestyle-advisor | warm tones, beige, wood, gold, sage green | soft natural light, golden hour | warm, inviting, serene |
| family-advisor | neutral tones, warm gray, light blue, soft green | diffused natural light | cozy, safe, practical |

---

## 六、图片命名与存储

### 文件命名
`{YYYYMMDD}_{序号}_{人设类型}_{图片类型}.jpg`
例：`20260510_001_investment_cover.jpg`

### 输出路径
`data/{项目名}/xiaohongshu/drafts/{YYYYMMDD}_{序号}/images/`
