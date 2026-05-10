# xhs_post 规则体系 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 xhs_post 的可维护规则体系——3个全局规则文件 + 项目规则文件 + Markdown/前端解析加载器

**Architecture:** Markdown 文件作为规则源（人类可读可改），Python loader 解析章节和表格为结构化对象。规则分两级：全局规则（怎么写/图片/标签）和项目规则（人设/策略/禁忌）

**Tech Stack:** Python 3.11+, PyYAML (frontmatter), pytest

---

### Task 1: 项目骨架

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/rules/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/rules/__init__.py`

- [ ] **Step 1: 创建 requirements.txt**

```bash
cat > D:/project/xhs_post/requirements.txt << 'EOF'
pyyaml>=6.0
pytest>=8.0
EOF
```

- [ ] **Step 2: 创建目录和 __init__.py**

```bash
mkdir -p D:/project/xhs_post/src/rules D:/project/xhs_post/tests/rules
touch D:/project/xhs_post/src/__init__.py
touch D:/project/xhs_post/src/rules/__init__.py
touch D:/project/xhs_post/tests/__init__.py
touch D:/project/xhs_post/tests/rules/__init__.py
```

- [ ] **Step 3: 安装依赖并验证**

```bash
cd D:/project/xhs_post && pip install -r requirements.txt
python -c "import yaml; print(yaml.__version__)"
```

- [ ] **Step 4: 初始化 git**

```bash
cd D:/project/xhs_post && git init && git add -A && git commit -m "chore: project scaffold"
```

---

### Task 2: 规则数据模型

**Files:**
- Create: `src/rules/models.py`
- Test: `tests/rules/test_models.py`

- [ ] **Step 1: 写测试**

```python
# tests/rules/test_models.py
from src.rules.models import Persona, ContentTypeConfig, ProjectRules, RuleSet

def test_persona_creation():
    p = Persona(
        name="老王",
        persona_type="investment-advisor",
        account_id="account-001",
        years=10,
        personality=["理性", "数据控"],
        expertise=["房产投资分析", "区域价值研判"],
        style="理性自信、多用数据对比",
        catchphrases=["用数据说话", "算笔账你就明白了"],
        dos=["用数据说话..."],
        donts=["过于技术化", "堆砌术语"],
        content_distribution={"market-analysis": 0.30, "area-value": 0.25},
        frequency="每周 2-3 篇",
    )
    assert p.name == "老王"
    assert p.persona_type == "investment-advisor"
    assert p.content_distribution["market-analysis"] == 0.30


def test_project_rules_creation():
    p = Persona(
        name="老王",
        persona_type="investment-advisor",
        account_id="account-001",
        years=10,
        personality=["理性"],
        expertise=["房产投资"],
        style="理性自信",
        catchphrases=["用数据说话"],
        dos=["用数据说话..."],
        donts=["过于技术化"],
        content_distribution={"market-analysis": 1.0},
        frequency="每周 2 篇",
    )
    pr = ProjectRules(
        project="中央半岛",
        city="海口",
        project_type="高端改善盘",
        features=["海景", "园林大盘"],
        personas=[p],
        feature_tags=["#海景房", "#品质楼盘"],
        taboos=["未交房，不编造入住体验"],
        content_sequence={"老王": ["market-analysis", "area-value"]},
        publish_window="10:00-21:00",
        min_interval_hours=24,
        max_weekly=3,
        preferred_hours=["12:00-13:00", "18:00-20:00"],
        project_interval_hours=3,
    )
    assert pr.project == "中央半岛"
    assert pr.city == "海口"
    assert len(pr.personas) == 1


def test_ruleset_holds_all_rules():
    p = Persona(
        name="老王",
        persona_type="investment-advisor",
        account_id="account-001",
        years=10,
        personality=["理性"],
        expertise=["房产投资"],
        style="理性自信",
        catchphrases=["用数据说话"],
        dos=[],
        donts=[],
        content_distribution={"market-analysis": 1.0},
        frequency="每周 2 篇",
    )
    project = ProjectRules(
        project="测试盘",
        city="海口",
        project_type="高端改善盘",
        features=[],
        personas=[p],
        feature_tags=[],
        taboos=[],
        content_sequence={},
        publish_window="10:00-21:00",
        min_interval_hours=24,
        max_weekly=3,
        preferred_hours=[],
        project_interval_hours=3,
    )
    rs = RuleSet(
        copywriting_raw="文案规则全文",
        image_raw="图片规则全文",
        hashtag_raw="标签规则全文",
        project=project,
    )
    assert rs.copywriting_raw == "文案规则全文"
    assert rs.project.project == "测试盘"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd D:/project/xhs_post && python -m pytest tests/rules/test_models.py -v
```
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现数据模型**

```python
# src/rules/models.py
from dataclasses import dataclass, field


@dataclass
class Persona:
    name: str
    persona_type: str  # investment-advisor | lifestyle-advisor | family-advisor
    account_id: str
    years: int
    personality: list[str]
    expertise: list[str]
    style: str
    catchphrases: list[str]
    dos: list[str]
    donts: list[str]
    content_distribution: dict[str, float]
    frequency: str


@dataclass
class ContentTypeConfig:
    id: str
    suitable_personas: list[str]
    frequency: str  # high | medium | low | instant
    priority: int
    image_count: str  # "4-5", "5-7" etc.
    image_sequence: list[dict]


@dataclass
class ProjectRules:
    project: str
    city: str
    project_type: str
    features: list[str]
    personas: list[Persona]
    feature_tags: list[str]
    taboos: list[str]
    content_sequence: dict[str, list[str]]  # persona_name -> [content_type_id]
    publish_window: str
    min_interval_hours: int
    max_weekly: int
    preferred_hours: list[str]
    project_interval_hours: int


@dataclass
class RuleSet:
    copywriting_raw: str
    image_raw: str
    hashtag_raw: str
    project: ProjectRules
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd D:/project/xhs_post && python -m pytest tests/rules/test_models.py -v
```
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add rule data models"
```

---

### Task 3: 全局规则文件

**Files:**
- Create: `rules/copywriting-rules.md`
- Create: `rules/image-rules.md`
- Create: `rules/hashtag-rules.md`

这些是数据文件（非代码），直接写入。

- [ ] **Step 1: 创建 rules/ 目录**

```bash
mkdir -p D:/project/xhs_post/rules
```

- [ ] **Step 2: 写入 rules/copywriting-rules.md**

文件内容按设计 spec `docs/superpowers/specs/2026-05-10-rules-system-design.md` 中「rules/copywriting-rules.md」章节的完整 Markdown 写入。六大章节：
- 一、平台特性（小红书 vs 朋友圈对比表 + 4条核心原则）
- 二、标题公式（6种公式模板 + 示例）
- 三、正文结构模板（模板A干货清单型 / 模板B叙事体验型 / 模板C热点借势型）
- 四、Emoji 使用规范（功能性emoji对照表 + 用量限制）
- 五、去AI味写作法则（七条铁律 + 八个AI标志词 + 修改后自查清单）
- 六、合规红线（广告法禁用词 + 房地产合规要求）

- [ ] **Step 3: 写入 rules/image-rules.md**

文件内容按设计 spec 中「rules/image-rules.md」章节的完整 Markdown 写入。六大章节：
- 一、生成模式决策（决策流程图 + 决策表）
- 二、多图排版（标准6图结构 + 按内容类型的图片配置表）
- 三、Seedream API 参数（端点、模型、尺寸等公共参数）
- 四、提示词规范（text2img封面提示词模板 + img2img场景提示词模板 + 负面提示词）
- 五、按人设的视觉风格（3种人设的色调/光线/氛围映射表）
- 六、图片命名与存储（命名规则 + 输出路径）

- [ ] **Step 4: 写入 rules/hashtag-rules.md**

文件内容按设计 spec 中「rules/hashtag-rules.md」章节的完整 Markdown 写入。六大章节：
- 一、标签分层策略（三层：大流量/精准/长尾）
- 二、按城市的标签库（海口/三亚/北京/上海/广州/深圳/成都/杭州）
- 三、按人设的基础标签（每人设的基础包 + 按内容类型追加）
- 四、按项目特性的补充标签（海景/改善/刚需/别墅/TOD）
- 五、热点标签规则（来源 + 使用限制 + 负面热点禁用）
- 六、标签生成检查清单（8项检查）

- [ ] **Step 5: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add global rule files"
```

---

### Task 4: 项目规则文件（模板）

**Files:**
- Create: `rules/中央半岛/rules.md`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p D:/project/xhs_post/rules/中央半岛
```

- [ ] **Step 2: 写入 rules/中央半岛/rules.md**

文件内容按设计 spec `docs/superpowers/specs/2026-05-10-rules-system-design.md` 中「rules/{项目}/rules.md」章节的完整 Markdown 写入。包含：
- YAML frontmatter（project/city/type/features）
- 一、本项目人设（3个人设的完整定义：投资顾问老王、生活顾问小陈、家庭顾问阿芳）
- 二、项目特性标签
- 三、项目内容禁忌
- 四、内容选题序列（每人设的轮换顺序）
- 五、发布配置（窗口/间隔/频次）

- [ ] **Step 3: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add project rule template (中央半岛)"
```

---

### Task 5: 规则加载器 — 项目规则解析

**Files:**
- Create: `src/rules/loader.py`
- Test: `tests/rules/test_loader.py`

- [ ] **Step 1: 写测试 — 解析 YAML frontmatter**

```python
# tests/rules/test_loader.py
from src.rules.loader import parse_frontmatter, parse_project_rules

SAMPLE_PROJECT_RULES = """---
project: 测试盘
city: 海口
type: 高端改善盘
features: [海景, 园林]
created: 2026-05-10
---

# 测试盘 - 内容规则

## 一、本项目人设

### 人设1：投资顾问

- **姓名**：老王
- **人设类型**：investment-advisor
- **账号**：account-001
- **从业年限**：10年
- **性格标签**：理性、数据控
- **专业领域**：房产投资分析
- **语言风格**：理性自信
- **口头禅**：用数据说话

**写作用语习惯**：
- ✅ "用数据说话..."
- ❌ 过于技术化

**内容占比**：
| 内容类型 | 占比 |
|---------|------|
| market-analysis | 30% |
| area-value | 25% |

**发布频次**：每周 2-3 篇

---

## 二、项目特性标签

- 项目名：#测试盘
- 项目特性：#海景房

---

## 三、项目内容禁忌

- 本项目未交房，不编造入住体验
- 不承诺升值幅度

---

## 四、内容选题序列

投资顾问老王：
market-analysis → area-value → product-analysis → buying-guide → 循环

---

## 五、发布配置

| 参数 | 值 |
|------|-----|
| 每日发布窗口 | 10:00-21:00 |
| 本账号最小间隔 | 24小时 |
| 本账号最大周发 | 3篇 |
| 同项目多账号间隔 | 3小时 |
| 优选时段 | 12:00-13:00, 18:00-20:00 |
"""


def test_parse_frontmatter():
    meta = parse_frontmatter(SAMPLE_PROJECT_RULES)
    assert meta["project"] == "测试盘"
    assert meta["city"] == "海口"
    assert meta["type"] == "高端改善盘"
    assert meta["features"] == ["海景", "园林"]


def test_parse_project_rules_personas():
    rules = parse_project_rules(SAMPLE_PROJECT_RULES)
    assert len(rules.personas) == 1
    p = rules.personas[0]
    assert p.name == "老王"
    assert p.persona_type == "investment-advisor"
    assert p.account_id == "account-001"
    assert p.years == 10
    assert "理性" in p.personality
    assert "房产投资分析" in p.expertise
    assert p.style == "理性自信"
    assert "用数据说话" in p.catchphrases
    assert "用数据说话..." in p.dos
    assert "过于技术化" in p.donts
    assert p.content_distribution["market-analysis"] == 0.30
    assert p.content_distribution["area-value"] == 0.25
    assert p.frequency == "每周 2-3 篇"


def test_parse_project_rules_meta():
    rules = parse_project_rules(SAMPLE_PROJECT_RULES)
    assert rules.project == "测试盘"
    assert rules.city == "海口"
    assert rules.project_type == "高端改善盘"
    assert "海景" in rules.features
    assert "#海景房" in rules.feature_tags
    assert "本项目未交房，不编造入住体验" in rules.taboos
    assert rules.publish_window == "10:00-21:00"
    assert rules.min_interval_hours == 24
    assert rules.max_weekly == 3
    assert rules.project_interval_hours == 3
    assert "12:00-13:00" in rules.preferred_hours


def test_parse_project_rules_content_sequence():
    rules = parse_project_rules(SAMPLE_PROJECT_RULES)
    assert "老王" in rules.content_sequence
    assert rules.content_sequence["老王"] == [
        "market-analysis", "area-value", "product-analysis", "buying-guide"
    ]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd D:/project/xhs_post && python -m pytest tests/rules/test_loader.py -v
```
Expected: ModuleNotFoundError (loader.py 不存在)

- [ ] **Step 3: 实现 parse_frontmatter**

```python
# src/rules/loader.py
import re
import yaml


def parse_frontmatter(markdown: str) -> dict:
    """Extract YAML frontmatter from markdown."""
    match = re.match(r'^---\n(.*?)\n---', markdown, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1))
```

- [ ] **Step 4: 运行测试 — parse_frontmatter 应通过**

```bash
cd D:/project/xhs_post && python -m pytest tests/rules/test_loader.py::test_parse_frontmatter -v
```

- [ ] **Step 5: 实现 parse_project_rules**

```python
# 追加到 src/rules/loader.py

from src.rules.models import Persona, ProjectRules


def parse_project_rules(markdown: str) -> ProjectRules:
    meta = parse_frontmatter(markdown)
    personas = _parse_personas(markdown)
    feature_tags = _parse_section_list(markdown, "项目特性标签")
    taboos = _parse_section_list(markdown, "项目内容禁忌")
    content_sequence = _parse_content_sequence(markdown)
    publish_config = _parse_publish_config(markdown)

    return ProjectRules(
        project=meta.get("project", ""),
        city=meta.get("city", ""),
        project_type=meta.get("type", ""),
        features=meta.get("features", []),
        personas=personas,
        feature_tags=feature_tags,
        taboos=taboos,
        content_sequence=content_sequence,
        publish_window=publish_config.get("每日发布窗口", "10:00-21:00"),
        min_interval_hours=int(publish_config.get("本账号最小间隔", "24").replace("小时", "")),
        max_weekly=int(publish_config.get("本账号最大周发", "3").replace("篇", "")),
        preferred_hours=[h.strip() for h in publish_config.get("优选时段", "").split(",") if h.strip()],
        project_interval_hours=int(publish_config.get("同项目多账号间隔", "3").replace("小时", "")),
    )


def _parse_personas(markdown: str) -> list[Persona]:
    """Parse persona definitions from markdown."""
    personas = []
    # Split by persona headers: ### 人设N：xxx
    blocks = re.split(r'### 人设\d+：', markdown)
    for block in blocks[1:]:  # skip content before first persona
        p = _parse_single_persona(block)
        if p:
            personas.append(p)
    return personas


def _parse_single_persona(block: str) -> Persona | None:
    name_match = re.search(r'^- \*\*姓名\*\*：(.+)', block, re.MULTILINE)
    type_match = re.search(r'^- \*\*人设类型\*\*：(.+)', block, re.MULTILINE)
    account_match = re.search(r'^- \*\*账号\*\*：(.+)', block, re.MULTILINE)
    years_match = re.search(r'^- \*\*从业年限\*\*：(\d+)', block, re.MULTILINE)
    personality_match = re.search(r'^- \*\*性格标签\*\*：(.+)', block, re.MULTILINE)
    expertise_match = re.search(r'^- \*\*专业领域\*\*：(.+)', block, re.MULTILINE)
    style_match = re.search(r'^- \*\*语言风格\*\*：(.+)', block, re.MULTILINE)
    catchphrases_match = re.search(r'^- \*\*口头禅\*\*：(.+)', block, re.MULTILINE)
    freq_match = re.search(r'\*\*发布频次\*\*：(.+)', block)

    if not name_match:
        return None

    dos = _parse_list_section(block, "✅")
    donts = _parse_list_section(block, "❌")
    distribution = _parse_distribution_table(block)

    return Persona(
        name=name_match.group(1).strip(),
        persona_type=type_match.group(1).strip() if type_match else "",
        account_id=account_match.group(1).strip() if account_match else "",
        years=int(years_match.group(1)) if years_match else 0,
        personality=[t.strip() for t in personality_match.group(1).split("、")] if personality_match else [],
        expertise=[t.strip() for t in expertise_match.group(1).split("、")] if expertise_match else [],
        style=style_match.group(1).strip() if style_match else "",
        catchphrases=[t.strip() for t in catchphrases_match.group(1).split("、")] if catchphrases_match else [],
        dos=dos,
        donts=donts,
        content_distribution=distribution,
        frequency=freq_match.group(1).strip() if freq_match else "",
    )


def _parse_list_section(block: str, prefix: str) -> list[str]:
    """Parse lines matching '- ✅ "..."' or '- ❌ "..."' pattern."""
    items = []
    for line in block.split('\n'):
        stripped = line.strip()
        if stripped.startswith(f'- {prefix}'):
            item = stripped[len(f'- {prefix}'):].strip().strip('"')
            if item:
                items.append(item)
    return items


def _parse_distribution_table(block: str) -> dict[str, float]:
    """Parse content distribution table to {content_type: ratio}."""
    result = {}
    in_table = False
    for line in block.split('\n'):
        if '| 内容类型 | 占比 |' in line or '|---------|------|' in line:
            in_table = True
            continue
        if in_table and line.strip().startswith('|'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2 and parts[0] != '内容类型':
                try:
                    result[parts[0]] = float(parts[1].replace('%', '')) / 100
                except ValueError:
                    pass
        elif in_table and not line.strip().startswith('|'):
            in_table = False
    return result


def _parse_section_list(markdown: str, section_name: str) -> list[str]:
    """Parse bullet list items under a section header."""
    # Find the section
    pattern = rf'## \d+、{re.escape(section_name)}\n(.*?)(?=\n## |\Z)'
    match = re.search(pattern, markdown, re.DOTALL)
    if not match:
        return []
    section = match.group(1)
    items = []
    for line in section.split('\n'):
        stripped = line.strip()
        if stripped.startswith('- '):
            item = stripped[2:].strip()
            if item:
                items.append(item)
    return items


def _parse_content_sequence(markdown: str) -> dict[str, list[str]]:
    """Parse content rotation sequence like '老王：market-analysis → area-value → buying-guide'."""
    result = {}
    pattern = r'(.+?)：\n?([\w-]+(?:\s*→\s*[\w-]+)+)'
    for match in re.finditer(pattern, markdown):
        name = match.group(1).strip()
        sequence = [s.strip() for s in re.split(r'→', match.group(2))]
        result[name] = sequence
    return result


def _parse_publish_config(markdown: str) -> dict[str, str]:
    """Parse publish config table."""
    # Find the table under 发布配置 section
    section_match = re.search(r'## 五、发布配置\n(.*?)(?=\n## |\Z)', markdown, re.DOTALL)
    if not section_match:
        return {}
    section = section_match.group(1)
    result = {}
    for line in section.split('\n'):
        if line.strip().startswith('|') and '|' in line[1:]:
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2 and parts[0] not in ('参数', '------', ''):
                result[parts[0]] = parts[1]
    return result
```

- [ ] **Step 6: 运行项目规则测试**

```bash
cd D:/project/xhs_post && python -m pytest tests/rules/test_loader.py -v
```
Expected: 4 passed

- [ ] **Step 7: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add project rules loader with frontmatter parsing"
```

---

### Task 6: 规则加载器 — 全局规则加载

**Files:**
- Modify: `src/rules/loader.py`

- [ ] **Step 1: 写测试 — 加载完整 RuleSet**

```python
# 追加到 tests/rules/test_loader.py
import os
from src.rules.loader import load_ruleset


def test_load_ruleset_from_files():
    """Integration test: load actual rule files from rules/ directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    rules_dir = os.path.join(base_dir, "rules")

    rs = load_ruleset(rules_dir, "中央半岛")

    assert rs.project.project == "中央半岛"
    assert rs.project.city == "海口"
    assert len(rs.project.personas) == 3
    assert len(rs.copywriting_raw) > 100
    assert "去AI味写作法则" in rs.copywriting_raw
    assert len(rs.image_raw) > 100
    assert "Seedream API" in rs.image_raw
    assert len(rs.hashtag_raw) > 100
    assert "标签分层策略" in rs.hashtag_raw


def test_load_ruleset_persona_types():
    """Verify persona types match expected values."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    rules_dir = os.path.join(base_dir, "rules")

    rs = load_ruleset(rules_dir, "中央半岛")

    types = [p.persona_type for p in rs.project.personas]
    assert "investment-advisor" in types
    assert "lifestyle-advisor" in types
    assert "family-advisor" in types
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd D:/project/xhs_post && python -m pytest tests/rules/test_loader.py::test_load_ruleset_from_files -v
```
Expected: AttributeError (load_ruleset 未定义)

- [ ] **Step 3: 实现 load_ruleset**

```python
# 追加到 src/rules/loader.py
import os


def load_ruleset(rules_dir: str, project_name: str) -> "RuleSet":
    from src.rules.models import RuleSet

    copywriting_path = os.path.join(rules_dir, "copywriting-rules.md")
    image_path = os.path.join(rules_dir, "image-rules.md")
    hashtag_path = os.path.join(rules_dir, "hashtag-rules.md")
    project_path = os.path.join(rules_dir, project_name, "rules.md")

    copywriting_raw = _read_file(copywriting_path)
    image_raw = _read_file(image_path)
    hashtag_raw = _read_file(hashtag_path)
    project_raw = _read_file(project_path)

    project = parse_project_rules(project_raw)

    return RuleSet(
        copywriting_raw=copywriting_raw,
        image_raw=image_raw,
        hashtag_raw=hashtag_raw,
        project=project,
    )


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
```

- [ ] **Step 4: 运行集成测试**

```bash
cd D:/project/xhs_post && python -m pytest tests/rules/test_loader.py -v
```
Expected: 6 passed

- [ ] **Step 5: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add RuleSet loader with global + project rules"
```

---

### Task 7: 内容组装器（桥接到内容生成）

**Files:**
- Create: `src/rules/assembler.py`
- Test: `tests/rules/test_assembler.py`

- [ ] **Step 1: 写测试**

```python
# tests/rules/test_assembler.py
import os
from src.rules.loader import load_ruleset
from src.rules.assembler import assemble_prompt_context


def test_assemble_prompt_context():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    rules_dir = os.path.join(base_dir, "rules")
    rs = load_ruleset(rules_dir, "中央半岛")

    ctx = assemble_prompt_context(rs, persona_name="老王", content_type="market-analysis")

    # 系统指令应包含文案规则中的关键约束
    assert "去AI味写作法则" in ctx["system_prompt"]
    assert "广告法禁用词" in ctx["system_prompt"]
    # 人设上下文应包含具体人设信息
    assert "老王" in ctx["persona_context"]
    assert "investment-advisor" in ctx["persona_context"]
    assert "10年" in ctx["persona_context"]
    # 应有标签提示
    assert "#海口买房" in ctx["hashtag_hint"] or "#海口" in ctx["hashtag_hint"]
    # 应有图片配置
    assert ctx["image_config"]["content_type"] == "market-analysis"
    assert isinstance(ctx["image_config"]["image_count"], int) or "image_count" in ctx["image_config"]
    # 应有内容禁忌
    assert "未交房" in ctx["taboos"]


def test_assemble_different_persona():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    rules_dir = os.path.join(base_dir, "rules")
    rs = load_ruleset(rules_dir, "中央半岛")

    ctx = assemble_prompt_context(rs, persona_name="小陈", content_type="community-life")

    assert "小陈" in ctx["persona_context"]
    assert "lifestyle-advisor" in ctx["persona_context"]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd D:/project/xhs_post && python -m pytest tests/rules/test_assembler.py -v
```
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现 assemble_prompt_context**

```python
# src/rules/assembler.py
from src.rules.models import RuleSet, Persona


def assemble_prompt_context(rs: RuleSet, persona_name: str, content_type: str) -> dict:
    persona = _find_persona(rs, persona_name)
    if not persona:
        raise ValueError(f"Persona not found: {persona_name}")

    return {
        "system_prompt": _build_system_prompt(rs),
        "persona_context": _build_persona_context(persona),
        "content_type": content_type,
        "hashtag_hint": _build_hashtag_hint(rs, content_type, persona),
        "image_config": _build_image_config(content_type),
        "taboos": _format_taboos(rs),
    }


def _find_persona(rs: RuleSet, name: str) -> Persona | None:
    for p in rs.project.personas:
        if p.name == name:
            return p
    return None


def _build_system_prompt(rs: RuleSet) -> str:
    """Extract key writing rules for the system prompt."""
    # Extract the anti-AI rules section
    lines = []
    in_section = False
    for line in rs.copywriting_raw.split('\n'):
        if '## 五、去AI味写作法则' in line:
            in_section = True
        elif in_section and line.startswith('## '):
            break
        elif in_section:
            lines.append(line)

    anti_ai_section = '\n'.join(lines)

    return f"""你是一个小红书房产内容创作者。严格遵循以下规则：

{anti_ai_section}

重要：输出内容必须通过"修改后自查"清单的6条检查。
"""


def _build_persona_context(persona: Persona) -> str:
    parts = [
        f"人设：{persona.name}",
        f"类型：{persona.persona_type}",
        f"身份：项目置业顾问，从业{persona.years}年",
        f"性格：{'、'.join(persona.personality)}",
        f"专业：{'、'.join(persona.expertise)}",
        f"语言风格：{persona.style}",
        f"口头禅：{' / '.join(persona.catchphrases)}",
        "",
        "可以写的：",
    ]
    for d in persona.dos:
        parts.append(f"  {d}")
    parts.append("不可以写的：")
    for d in persona.donts:
        parts.append(f"  {d}")
    return '\n'.join(parts)


def _build_hashtag_hint(rs: RuleSet, content_type: str, persona: Persona) -> str:
    """Extract relevant hashtag rules."""
    city = rs.project.city
    lines = []
    in_city = False
    for line in rs.hashtag_raw.split('\n'):
        if f'### {city}' in line:
            in_city = True
        elif in_city and line.startswith('### ') and city not in line:
            in_city = False
        elif in_city and line.strip().startswith('|'):
            lines.append(line)
    return f"建议标签层级（{city}）：\n" + '\n'.join(lines)


def _build_image_config(content_type: str) -> dict:
    # Map content type to image count and types based on image-rules.md
    configs = {
        "market-analysis": {"image_count": 5, "sequence": ["cover", "chart", "project", "cta"]},
        "area-value": {"image_count": 6, "sequence": ["cover", "planning", "amenity", "location", "info", "cta"]},
        "product-analysis": {"image_count": 6, "sequence": ["cover", "living_room", "bedroom", "balcony", "floorplan", "cta"]},
        "buying-guide": {"image_count": 5, "sequence": ["cover", "tip_card", "tip_card", "project", "cta"]},
        "community-life": {"image_count": 7, "sequence": ["cover", "landscape", "pool", "detail", "detail", "detail", "cta"]},
        "home-aesthetics": {"image_count": 7, "sequence": ["cover", "light", "material", "panorama", "inspo", "inspo", "cta"]},
        "family-living": {"image_count": 7, "sequence": ["cover", "living", "kids_room", "kitchen", "education", "detail", "cta"]},
        "trend-jacking": {"image_count": 5, "sequence": ["cover", "trend", "project", "project", "cta"]},
    }
    return configs.get(content_type, {"image_count": 5, "sequence": ["cover", "content", "content", "cta"]})


def _format_taboos(rs: RuleSet) -> str:
    if not rs.project.taboos:
        return "无特殊禁忌"
    return "项目内容禁忌：\n" + '\n'.join(f"- {t}" for t in rs.project.taboos)
```

- [ ] **Step 4: 运行测试**

```bash
cd D:/project/xhs_post && python -m pytest tests/rules/test_assembler.py -v
```
Expected: 2 passed

- [ ] **Step 5: 运行全部测试**

```bash
cd D:/project/xhs_post && python -m pytest tests/rules/ -v
```
Expected: 11 passed

- [ ] **Step 6: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add prompt context assembler"
```
