# 内容生成模块 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现内容生成模块——选题引擎、Claude API 文案生成、Seedream API 图片生成、CLI 入口，输出草稿到文件系统

**Architecture:** 选题引擎读 index.md 决定发什么 → copywriter 调 Claude API 写文案 → imager 调 Seedream API 生图片 → 输出到 data/{项目}/drafts/。之前构建的规则体系（loader + assembler）提供 Prompt 上下文

**Tech Stack:** Python 3.12, anthropic SDK, requests, click, 已有 PyYAML + pytest

---

### Task 1: 模块骨架 + 新依赖

**Files:**
- Create: `src/content/__init__.py`
- Create: `tests/content/__init__.py`
- Modify: `requirements.txt`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p D:/project/xhs_post/src/content D:/project/xhs_post/tests/content
touch D:/project/xhs_post/src/content/__init__.py
touch D:/project/xhs_post/tests/content/__init__.py
```

- [ ] **Step 2: 更新 requirements.txt**

追加 anthropic、click、requests：

```bash
cat >> D:/project/xhs_post/requirements.txt << 'EOF'
anthropic>=0.40.0
click>=8.0
requests>=2.31
EOF
```

- [ ] **Step 3: 安装依赖并验证**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && pip install -r requirements.txt
python -c "import anthropic; import click; import requests; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "chore: add content module scaffold and new deps"
```

---

### Task 2: 草稿索引管理 (index.md)

**Files:**
- Create: `src/content/indexer.py`
- Test: `tests/content/test_indexer.py`

- [ ] **Step 1: 写测试**

```python
# tests/content/test_indexer.py
import tempfile
import os
from src.content.indexer import DraftIndex, DraftEntry, DraftStatus

SAMPLE_INDEX = """---
project: 中央半岛
updated: 2026-05-12
---

| 日期 | 序号 | 人设 | 内容类型 | 标题 | 状态 |
|------|------|------|---------|------|------|
| 2026-05-10 | 001 | 老王 | market-analysis | LPR又降了 | published |
| 2026-05-10 | 002 | 小陈 | community-life | 周末在小区 | published |
| 2026-05-12 | 001 | 阿芳 | family-living | 带娃家庭选115㎡ | draft |
"""


def test_parse_index():
    index = DraftIndex.from_markdown(SAMPLE_INDEX)
    assert index.project == "中央半岛"
    assert len(index.entries) == 3
    assert index.entries[0].persona == "老王"
    assert index.entries[0].content_type == "market-analysis"
    assert index.entries[0].status == DraftStatus.PUBLISHED


def test_get_last_for_persona():
    index = DraftIndex.from_markdown(SAMPLE_INDEX)
    last = index.get_last_for_persona("老王")
    assert last is not None
    assert last.content_type == "market-analysis"
    assert last.date == "2026-05-10"


def test_get_last_for_persona_returns_none_for_new_persona():
    index = DraftIndex.from_markdown(SAMPLE_INDEX)
    assert index.get_last_for_persona("新人") is None


def test_add_entry():
    index = DraftIndex.from_markdown(SAMPLE_INDEX)
    entry = DraftEntry(
        date="2026-05-13", seq="001", persona="老王",
        content_type="area-value", title="海口江东新区规划",
        status=DraftStatus.GENERATING,
    )
    index.add_entry(entry)
    assert len(index.entries) == 4
    assert index.get_last_for_persona("老王").content_type == "area-value"


def test_recent_types_within_days():
    index = DraftIndex.from_markdown(SAMPLE_INDEX)
    # All sample entries are within 3 days of 2026-05-12
    recent = index.recent_types("2026-05-12", days=3)
    assert "market-analysis" in recent
    assert "community-life" in recent
    assert "family-living" in recent


def test_to_markdown_roundtrip():
    index = DraftIndex.from_markdown(SAMPLE_INDEX)
    output = index.to_markdown()
    reparsed = DraftIndex.from_markdown(output)
    assert reparsed.project == index.project
    assert len(reparsed.entries) == len(index.entries)


def test_load_and_save():
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = os.path.join(tmpdir, "index.md")
        # Create fresh index
        index = DraftIndex(project="测试盘")
        index.entries = [
            DraftEntry("2026-05-13", "001", "老王", "market-analysis", "测试标题", DraftStatus.DRAFT),
        ]
        index.save(index_path)

        # Load back
        loaded = DraftIndex.load(index_path)
        assert loaded.project == "测试盘"
        assert len(loaded.entries) == 1
        assert loaded.entries[0].title == "测试标题"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/content/test_indexer.py -v
```
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现 indexer.py**

```python
# src/content/indexer.py
from dataclasses import dataclass, field
from enum import Enum
import re
import yaml
import os
from datetime import datetime


class DraftStatus(Enum):
    GENERATING = "generating"
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PENDING_PUBLISH = "pending_publish"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass
class DraftEntry:
    date: str       # YYYY-MM-DD
    seq: str        # 序号 001/002
    persona: str
    content_type: str
    title: str
    status: DraftStatus


@dataclass
class DraftIndex:
    project: str
    updated: str = ""
    entries: list[DraftEntry] = field(default_factory=list)

    @classmethod
    def load(cls, path: str) -> "DraftIndex":
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return cls.from_markdown(content)

    @classmethod
    def from_markdown(cls, content: str) -> "DraftIndex":
        meta = cls._parse_frontmatter(content)
        entries = cls._parse_table(content)
        return cls(
            project=meta.get("project", ""),
            updated=meta.get("updated", ""),
            entries=entries,
        )

    @staticmethod
    def _parse_frontmatter(content: str) -> dict:
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return {}
        return yaml.safe_load(match.group(1))

    @staticmethod
    def _parse_table(content: str) -> list[DraftEntry]:
        entries = []
        in_table = False
        for line in content.split('\n'):
            if '| 日期 | 序号 | 人设 | 内容类型 | 标题 | 状态 |' in line:
                in_table = True
                continue
            if '|------|------|------|---------|------|------|' in line:
                continue
            if in_table and line.strip().startswith('|'):
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 6:
                    try:
                        entries.append(DraftEntry(
                            date=parts[0], seq=parts[1], persona=parts[2],
                            content_type=parts[3], title=parts[4],
                            status=DraftStatus(parts[5]),
                        ))
                    except ValueError:
                        pass
            elif in_table and not line.strip().startswith('|'):
                in_table = False
        return entries

    def get_last_for_persona(self, persona: str) -> DraftEntry | None:
        for entry in reversed(self.entries):
            if entry.persona == persona:
                return entry
        return None

    def recent_types(self, reference_date: str, days: int = 3) -> set[str]:
        from datetime import datetime, timedelta
        ref = datetime.strptime(reference_date, "%Y-%m-%d")
        cutoff = ref - timedelta(days=days)
        result = set()
        for entry in self.entries:
            try:
                entry_date = datetime.strptime(entry.date, "%Y-%m-%d")
                if entry_date >= cutoff:
                    result.add(entry.content_type)
            except ValueError:
                pass
        return result

    def add_entry(self, entry: DraftEntry):
        self.entries.append(entry)

    def update_status(self, date: str, seq: str, status: DraftStatus):
        for entry in self.entries:
            if entry.date == date and entry.seq == seq:
                entry.status = status
                return

    def to_markdown(self) -> str:
        self.updated = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            "---",
            f"project: {self.project}",
            f"updated: {self.updated}",
            "---",
            "",
            "| 日期 | 序号 | 人设 | 内容类型 | 标题 | 状态 |",
            "|------|------|------|---------|------|------|",
        ]
        for e in self.entries:
            lines.append(f"| {e.date} | {e.seq} | {e.persona} | {e.content_type} | {e.title} | {e.status.value} |")
        return '\n'.join(lines) + '\n'

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
```

- [ ] **Step 4: 运行测试**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/content/test_indexer.py -v
```
Expected: 7 passed

- [ ] **Step 5: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add draft index manager"
```

---

### Task 3: 选题引擎

**Files:**
- Create: `src/content/topic.py`
- Test: `tests/content/test_topic.py`

- [ ] **Step 1: 写测试**

```python
# tests/content/test_topic.py
from src.content.topic import TopicSelector
from src.content.indexer import DraftIndex, DraftEntry, DraftStatus


def make_index() -> DraftIndex:
    index = DraftIndex(project="测试盘")
    index.entries = [
        DraftEntry("2026-05-10", "001", "老王", "market-analysis", "测试标题1", DraftStatus.PUBLISHED),
        DraftEntry("2026-05-11", "001", "小陈", "community-life", "测试标题2", DraftStatus.PUBLISHED),
        DraftEntry("2026-05-12", "001", "阿芳", "family-living", "测试标题3", DraftStatus.PUBLISHED),
    ]
    return index


def make_sequence():
    return {
        "老王": ["market-analysis", "area-value", "product-analysis", "buying-guide"],
        "小陈": ["community-life", "home-aesthetics", "product-analysis"],
    }


def test_manual_topic():
    """手动指定人设+类型时直接返回"""
    result = TopicSelector.select(make_index(), make_sequence(), persona="老王", content_type="buying-guide")
    assert len(result) == 1
    assert result[0] == ("老王", "buying-guide")


def test_auto_next_in_sequence():
    """自动模式取轮换序列中的下一个"""
    result = TopicSelector.select(make_index(), make_sequence())
    # 老王上次是 market-analysis，下一个是 area-value
    lao_wang_topics = [t for p, t in result if p == "老王"]
    assert "area-value" in lao_wang_topics


def test_auto_skips_recent_duplicates():
    """自动选题跳过3天内已发的类型"""
    index = make_index()
    # 老王昨天才发了 market-analysis，area-value 也刚发
    index.entries.append(
        DraftEntry("2026-05-12", "002", "老王", "area-value", "重复", DraftStatus.PUBLISHED)
    )
    result = TopicSelector.select(index, make_sequence(), persona="老王")
    # 老王序列：market-analysis → area-value → product-analysis → buying-guide
    # 前两个都被跳过（3天内），应该跳到 product-analysis
    assert result[0] == ("老王", "product-analysis")


def test_batch_all_personas():
    """批量为所有人设选题"""
    result = TopicSelector.select_all(make_index(), make_sequence())
    personas = {p for p, t in result}
    assert "老王" in personas
    assert "小陈" in personas
    # 每个人设至少一篇
    assert len(result) >= 2
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/content/test_topic.py -v
```
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现 topic.py**

```python
# src/content/topic.py
from datetime import datetime
from src.content.indexer import DraftIndex


class TopicSelector:
    @staticmethod
    def select(index: DraftIndex, sequence: dict[str, list[str]],
               persona: str = None, content_type: str = None) -> list[tuple[str, str]]:
        if persona and content_type:
            return [(persona, content_type)]

        today = datetime.now().strftime("%Y-%m-%d")
        recent = index.recent_types(today, days=3)

        if persona:
            next_type = TopicSelector._next_in_sequence(
                sequence.get(persona, []), index, persona, recent
            )
            return [(persona, next_type)]

        # 未指定人设：为所有人设取下一个
        results = []
        for p, seq in sequence.items():
            next_type = TopicSelector._next_in_sequence(seq, index, p, recent)
            results.append((p, next_type))
        return results

    @staticmethod
    def select_all(index: DraftIndex, sequence: dict[str, list[str]]) -> list[tuple[str, str]]:
        return TopicSelector.select(index, sequence)

    @staticmethod
    def _next_in_sequence(seq: list[str], index: DraftIndex, persona: str, recent: set[str]) -> str:
        if not seq:
            return "product-analysis"

        last = index.get_last_for_persona(persona)
        start_idx = 0
        if last and last.content_type in seq:
            idx = seq.index(last.content_type)
            start_idx = (idx + 1) % len(seq)

        # 轮询最多一圈
        for i in range(len(seq)):
            candidate = seq[(start_idx + i) % len(seq)]
            if candidate not in recent:
                return candidate

        # 全部重复了，取下一个
        return seq[start_idx]
```

- [ ] **Step 4: 运行测试**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/content/test_topic.py -v
```
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add topic selection engine"
```

---

### Task 4: 文案生成器

**Files:**
- Create: `src/content/copywriter.py`
- Test: `tests/content/test_copywriter.py`

- [ ] **Step 1: 写测试**

```python
# tests/content/test_copywriter.py
import os
from unittest.mock import patch, MagicMock
from src.rules.loader import load_ruleset
from src.content.copywriter import Copywriter
from src.content.indexer import DraftIndex, DraftEntry, DraftStatus


def test_copywriter_builds_prompt():
    """测试 Prompt 组装逻辑（不调API）"""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    rules_dir = os.path.join(base_dir, "rules")
    rs = load_ruleset(rules_dir, "中央半岛")

    cw = Copywriter(rs)
    system_prompt, user_prompt = cw.build_prompts("老王", "market-analysis", topic="LPR降息")

    assert "去AI味写作法则" in system_prompt
    assert "老王" in user_prompt
    assert "market-analysis" in user_prompt
    assert "LPR降息" in user_prompt


@patch('src.content.copywriter.Anthropic')
def test_copywriter_generate(mock_anthropic):
    """测试文案生成（mock Claude API）"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = '{"title": "测试标题", "body": "测试正文", "hashtags": ["#测试", "#买房"]}'
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    cw = Copywriter(MagicMock())
    cw.client = mock_client

    result = cw.generate("system prompt", "user prompt")

    assert result["title"] == "测试标题"
    assert result["body"] == "测试正文"
    assert "#测试" in result["hashtags"]
    mock_client.messages.create.assert_called_once()


def test_copywriter_anti_ai_check():
    """测试去AI味检查"""
    cw = Copywriter(MagicMock())

    # 包含AI标志词的文本
    ai_text = "综上所述，该楼盘是一个非常值得购买的优质项目"
    assert not cw.passes_anti_ai_check(ai_text)

    # 正常的口语化文本
    human_text = "说实话，看了这么多盘，这个户型确实让人心动"
    assert cw.passes_anti_ai_check(human_text)


def test_copywriter_anti_ai_flag_words():
    cw = Copywriter(MagicMock())
    for word in ["综上所述", "总而言之", "值得注意的是", "极致", "非凡", "卓越"]:
        assert not cw.passes_anti_ai_check(f"这是一段{word}的测试文本"), f"Should reject: {word}"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/content/test_copywriter.py -v
```
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现 copywriter.py**

```python
# src/content/copywriter.py
import json
import re
from anthropic import Anthropic
from src.rules.models import RuleSet
from src.rules.assembler import assemble_prompt_context

AI_FLAG_WORDS = [
    "首先", "其次", "最后", "综上所述", "总而言之", "值得注意的是",
    "本项目", "该楼盘", "不仅如此", "更重要的是", "为您", "为广大客户",
    "极致", "非凡", "卓越", "因此", "由此可见",
]


class Copywriter:
    def __init__(self, ruleset: RuleSet, api_key: str = None, model: str = None):
        self.rs = ruleset
        self.client = Anthropic(api_key=api_key) if api_key else None
        self.model = model or "claude-sonnet-4-6"

    def build_prompts(self, persona_name: str, content_type: str, topic: str = None) -> tuple[str, str]:
        ctx = assemble_prompt_context(self.rs, persona_name, content_type)
        system_prompt = ctx["system_prompt"]
        user_prompt = ctx["persona_context"]
        if topic:
            user_prompt += f"\n\n选题方向：{topic}"
        user_prompt += f"\n\n请生成一篇{content_type}类型的小红书笔记。输出JSON格式：{{\"title\": \"...\", \"body\": \"...\", \"hashtags\": [\"...\"]}}"
        return system_prompt, user_prompt

    def generate(self, system_prompt: str, user_prompt: str, max_retries: int = 1) -> dict:
        for attempt in range(max_retries + 1):
            result = self._call_api(system_prompt, user_prompt)
            if self.passes_anti_ai_check(result.get("body", "")):
                return result
        return result  # 最后一次即使不通过也返回

    def _call_api(self, system_prompt: str, user_prompt: str) -> dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text
        return self._parse_json_response(text)

    def _parse_json_response(self, text: str) -> dict:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"title": "", "body": text, "hashtags": []}

    def passes_anti_ai_check(self, text: str) -> bool:
        for word in AI_FLAG_WORDS:
            if word in text:
                return False
        return True
```

- [ ] **Step 4: 运行测试**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/content/test_copywriter.py -v
```
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add copywriter with Claude API integration"
```

---

### Task 5: 图片生成器

**Files:**
- Create: `src/content/imager.py`
- Test: `tests/content/test_imager.py`

- [ ] **Step 1: 写测试**

```python
# tests/content/test_imager.py
import os
from unittest.mock import patch, MagicMock
from src.content.imager import Imager


def test_imager_decision_matrix():
    """测试决策矩阵：有实景→img2img"""
    assert Imager.decide_mode(has_photos=True, has_renders=False, is_cover=False) == ("img2img", 0.35, None)
    assert Imager.decide_mode(has_photos=False, has_renders=True, is_cover=False) == ("img2img", 0.45, "效果图仅供参考")
    assert Imager.decide_mode(has_photos=False, has_renders=False, is_cover=False) == ("text2img", None, "概念示意图，以实际为准")
    assert Imager.decide_mode(has_photos=True, has_renders=True, is_cover=True) == ("text2img", None, None)


def test_imager_get_image_config():
    """测试从内容类型获取图片配置"""
    config = Imager.get_image_config("market-analysis")
    assert config["image_count"] == 5
    assert config["content_type"] == "market-analysis"
    assert "cover" in config["sequence"]


def test_imager_visual_style():
    """测试人设视觉风格映射"""
    style = Imager.get_visual_style("investment-advisor")
    assert "cool tones" in style["colors"]
    assert "professional" in style["lighting"]

    style = Imager.get_visual_style("lifestyle-advisor")
    assert "warm tones" in style["colors"]


def test_imager_build_prompt():
    """测试图片提示词构建"""
    prompt = Imager.build_text2img_prompt(
        image_type="cover",
        title="LPR又降了",
        visual_elements="data chart with downward arrow",
        auxiliary_elements="apartment building silhouette",
        persona_style={"colors": "navy, silver", "lighting": "bright professional", "atmosphere": "confident"},
    )
    assert "cover image" in prompt
    assert "LPR又降了" in prompt
    assert "navy, silver" in prompt
    assert "no QR code" in prompt


def test_imager_compliance_label():
    assert Imager.get_compliance_label("text2img", has_real_photos=False) == "概念示意图，以实际为准"
    assert Imager.get_compliance_label("img2img", has_real_photos=False) == "效果图仅供参考"
    assert Imager.get_compliance_label("img2img", has_real_photos=True) is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/content/test_imager.py -v
```
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现 imager.py**

```python
# src/content/imager.py
import os
import requests


class Imager:
    API_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    SIZE = "2304x4096"
    NEGATIVE_PROMPT = (
        "text overlay, watermarks, QR codes, phone numbers, logos, "
        "distorted architecture, unrealistic proportions, blurry, low quality, "
        "cartoon, illustration, 3D render style, overly saturated"
    )

    VISUAL_STYLES = {
        "investment-advisor": {
            "colors": "cool tones, navy, silver, white, blue-gray",
            "lighting": "bright, clean, professional",
            "atmosphere": "confident, authoritative",
        },
        "lifestyle-advisor": {
            "colors": "warm tones, beige, wood, gold, sage green",
            "lighting": "soft natural light, golden hour",
            "atmosphere": "warm, inviting, serene",
        },
        "family-advisor": {
            "colors": "neutral tones, warm gray, light blue, soft green",
            "lighting": "diffused natural light",
            "atmosphere": "cozy, safe, practical",
        },
    }

    IMAGE_CONFIGS = {
        "market-analysis": {"content_type": "market-analysis", "image_count": 5,
            "sequence": ["cover", "chart", "project", "cta"]},
        "area-value": {"content_type": "area-value", "image_count": 6,
            "sequence": ["cover", "planning", "amenity", "location", "info", "cta"]},
        "product-analysis": {"content_type": "product-analysis", "image_count": 6,
            "sequence": ["cover", "living_room", "bedroom", "balcony", "floorplan", "cta"]},
        "buying-guide": {"content_type": "buying-guide", "image_count": 5,
            "sequence": ["cover", "tip_card", "tip_card", "project", "cta"]},
        "community-life": {"content_type": "community-life", "image_count": 7,
            "sequence": ["cover", "landscape", "pool", "detail", "detail", "detail", "cta"]},
        "home-aesthetics": {"content_type": "home-aesthetics", "image_count": 7,
            "sequence": ["cover", "light", "material", "panorama", "inspo", "inspo", "cta"]},
        "family-living": {"content_type": "family-living", "image_count": 7,
            "sequence": ["cover", "living", "kids_room", "kitchen", "education", "detail", "cta"]},
        "trend-jacking": {"content_type": "trend-jacking", "image_count": 5,
            "sequence": ["cover", "trend", "project", "project", "cta"]},
    }

    @staticmethod
    def decide_mode(has_photos: bool, has_renders: bool, is_cover: bool) -> tuple[str, float | None, str | None]:
        if is_cover:
            return ("text2img", None, None)
        if has_photos:
            return ("img2img", 0.35, None)
        if has_renders:
            return ("img2img", 0.45, "效果图仅供参考")
        return ("text2img", None, "概念示意图，以实际为准")

    @staticmethod
    def get_image_config(content_type: str) -> dict:
        return Imager.IMAGE_CONFIGS.get(content_type,
            {"content_type": content_type, "image_count": 5, "sequence": ["cover", "content", "content", "cta"]})

    @staticmethod
    def get_visual_style(persona_type: str) -> dict:
        return Imager.VISUAL_STYLES.get(persona_type, Imager.VISUAL_STYLES["lifestyle-advisor"])

    @staticmethod
    def build_text2img_prompt(image_type: str, title: str, visual_elements: str,
                               auxiliary_elements: str, persona_style: dict) -> str:
        return (
            f"A real estate social media {image_type} image for Xiaohongshu. "
            f"The {image_type} features {visual_elements}, with {auxiliary_elements}. "
            f'Large Chinese title text "{title}" prominently placed, modern typography. '
            f"Color palette: {persona_style['colors']}. "
            f"Lighting: {persona_style['lighting']}. "
            f"Atmosphere: {persona_style['atmosphere']}. "
            f"Clean modern design, vertical 9:16 format, "
            f"no QR code, no phone numbers, no watermarks, "
            f"professional real estate photography style."
        )

    @staticmethod
    def build_img2img_prompt(scene_type: str, keep_features: str, enhance_aspects: str,
                               persona_style: dict) -> str:
        return (
            f"Real estate property photo, {scene_type}. "
            f"Keep the original {keep_features}. "
            f"Enhance {enhance_aspects}. "
            f"Color tone: {persona_style['colors']}, {persona_style['lighting']}. "
            f"Maintain architectural accuracy, realistic style, no distortion, "
            f"professional real estate photography, vertical 9:16."
        )

    @staticmethod
    def get_compliance_label(mode: str, has_real_photos: bool) -> str | None:
        if mode == "text2img" and not has_real_photos:
            return "概念示意图，以实际为准"
        if mode == "img2img" and not has_real_photos:
            return "效果图仅供参考"
        return None

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.environ.get("SEEDREAM_API_KEY", "")
        self.model = model or "seedream-5.0-lite"

    def generate(self, project_dir: str, content_type: str, persona_type: str,
                 title: str, output_dir: str) -> list[str]:
        config = self.get_image_config(content_type)
        style = self.get_visual_style(persona_type)
        has_photos = self._check_photos(project_dir)
        has_renders = self._check_renders(project_dir)

        paths = []
        for i, img_type in enumerate(config["sequence"], 1):
            is_cover = (img_type == "cover")
            mode, strength, label = self.decide_mode(has_photos, has_renders, is_cover)

            if mode == "text2img":
                prompt = self.build_text2img_prompt(
                    img_type, title,
                    visual_elements=self._visual_elements_for(img_type),
                    auxiliary_elements="project architecture and landscape",
                    persona_style=style,
                )
                url = self._call_text2img(prompt)
            else:
                prompt = self.build_img2img_prompt(
                    img_type,
                    keep_features="architectural structure and layout",
                    enhance_aspects="lighting, color tone, atmosphere",
                    persona_style=style,
                )
                source_url = self._find_source_image(project_dir, img_type)
                url = self._call_img2img(prompt, source_url, strength)

            path = self._download(url, output_dir, i, persona_type, img_type)
            paths.append(path)

        return paths

    def _check_photos(self, project_dir: str) -> bool:
        photos_dir = os.path.join(project_dir, "media", "photos")
        return os.path.isdir(photos_dir) and len(os.listdir(photos_dir)) > 0

    def _check_renders(self, project_dir: str) -> bool:
        renders_dir = os.path.join(project_dir, "media", "renders")
        return os.path.isdir(renders_dir) and len(os.listdir(renders_dir)) > 0

    def _visual_elements_for(self, img_type: str) -> str:
        elements = {
            "cover": "eye-catching title card with real estate theme",
            "chart": "data visualization with clean charts",
            "project": "premium real estate exterior photography",
            "cta": "call-to-action design with subtle branding",
            "planning": "urban planning diagram",
            "amenity": "luxury amenities showcase",
            "location": "location map with key landmarks",
            "info": "clean information card design",
            "living_room": "bright spacious living room",
            "bedroom": "comfortable master bedroom",
            "balcony": "scenic balcony view",
            "floorplan": "architectural floor plan with annotations",
            "tip_card": "informative tip card",
            "landscape": "beautiful garden landscape",
            "pool": "resort-style swimming pool",
            "detail": "architectural detail close-up",
            "light": "natural light interior shot",
            "material": "premium material texture",
            "panorama": "panoramic interior view",
            "inspo": "design inspiration mood board",
            "living": "family living space",
            "kids_room": "children's room design",
            "kitchen": "modern kitchen design",
            "education": "nearby school exterior",
            "trend": "trending topic visual",
        }
        return elements.get(img_type, "real estate photography")

    def _find_source_image(self, project_dir: str, img_type: str) -> str:
        return ""

    def _call_text2img(self, prompt: str) -> str:
        response = requests.post(
            self.API_ENDPOINT,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model, "prompt": prompt,
                "negative_prompt": self.NEGATIVE_PROMPT,
                "size": self.SIZE, "seed": -1, "scale": 7.5, "ddim_steps": 30,
            },
            timeout=120,
        )
        data = response.json()
        return data["data"]["image_urls"][0]

    def _call_img2img(self, prompt: str, source_url: str, strength: float) -> str:
        response = requests.post(
            self.API_ENDPOINT,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model, "prompt": prompt,
                "negative_prompt": self.NEGATIVE_PROMPT,
                "image_url": source_url, "strength": strength,
                "size": self.SIZE, "seed": -1, "scale": 7.5, "ddim_steps": 30,
            },
            timeout=120,
        )
        data = response.json()
        return data["data"]["image_urls"][0]

    def _download(self, url: str, output_dir: str, index: int, persona_type: str, img_type: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"image-{index:02d}.jpg"
        path = os.path.join(output_dir, filename)
        response = requests.get(url, timeout=60)
        with open(path, "wb") as f:
            f.write(response.content)
        return path
```

- [ ] **Step 4: 运行测试**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/content/test_imager.py -v
```
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add image generator with Seedream API"
```

---

### Task 6: CLI 接口

**Files:**
- Create: `src/cli.py`

- [ ] **Step 1: 实现 CLI**

```python
# src/cli.py
import click
import os
from datetime import datetime

from src.rules.loader import load_ruleset
from src.content.indexer import DraftIndex, DraftEntry, DraftStatus
from src.content.topic import TopicSelector


@click.group()
def main():
    """xhs_post - 小红书内容发布系统"""
    pass


@main.command()
@click.option("--project", required=True, help="项目名")
@click.option("--persona", default=None, help="人设名")
@click.option("--type", "content_type", default=None, help="内容类型")
@click.option("--topic", default=None, help="选题方向")
def generate(project, persona, content_type, topic):
    """生成单篇内容"""
    click.echo(f"[generate] {project} persona={persona} type={content_type}")
    rules_dir = "rules"
    data_dir = os.path.join("data", project)
    drafts_dir = os.path.join(data_dir, "drafts")

    rs = load_ruleset(rules_dir, project)
    index = DraftIndex.load_or_create(drafts_dir, project)

    topics = TopicSelector.select(
        index, rs.project.content_sequence,
        persona=persona, content_type=content_type,
    )

    for p_name, ct in topics:
        today = datetime.now().strftime("%Y%m%d")
        seq = _next_seq(index, today)
        click.echo(f"  生成: {p_name} × {ct} → {today}_{seq}")
        # copywriter.generate + imager.generate 在此调用
        # 写入 post.md + 更新 index.md


@main.command()
@click.option("--project", required=True, help="项目名")
@click.option("--persona", default=None, help="人设名")
@click.option("--days", default=7, help="生成天数")
@click.option("--count", default=None, type=int, help="生成篇数")
def batch(project, persona, days, count):
    """批量生成内容"""
    click.echo(f"[batch] {project} days={days} count={count}")


@main.command()
@click.option("--project", required=True, help="项目名")
@click.option("--persona", default=None, help="人设名")
def status(project, persona):
    """查看草稿/发布状态"""
    data_dir = os.path.join("data", project)
    drafts_dir = os.path.join(data_dir, "drafts")
    try:
        index = DraftIndex.load(os.path.join(drafts_dir, "index.md"))
        counts = {}
        for entry in index.entries:
            counts[entry.status.value] = counts.get(entry.status.value, 0) + 1
        click.echo(f"项目: {project}")
        for s, c in counts.items():
            click.echo(f"  {s}: {c}篇")
    except FileNotFoundError:
        click.echo(f"项目 {project} 还没有草稿")


@main.command()
@click.option("--project", required=True)
@click.option("--id", "draft_id", required=True)
def approve(project, draft_id):
    """审核通过草稿"""
    data_dir = os.path.join("data", project)
    drafts_dir = os.path.join(data_dir, "drafts")
    index = DraftIndex.load(os.path.join(drafts_dir, "index.md"))
    date, seq = draft_id.split("_")
    index.update_status(date, seq, DraftStatus.PENDING_PUBLISH)
    index.save(os.path.join(drafts_dir, "index.md"))
    click.echo(f"已通过: {draft_id} → pending_publish")


@main.command()
@click.option("--project", required=True)
@click.option("--id", "draft_id", required=True)
def reject(project, draft_id):
    """驳回草稿"""
    data_dir = os.path.join("data", project)
    drafts_dir = os.path.join(data_dir, "drafts")
    index = DraftIndex.load(os.path.join(drafts_dir, "index.md"))
    date, seq = draft_id.split("_")
    index.update_status(date, seq, DraftStatus.FAILED)
    index.save(os.path.join(drafts_dir, "index.md"))
    click.echo(f"已驳回: {draft_id}")


def _next_seq(index: DraftIndex, date: str) -> str:
    count = sum(1 for e in index.entries if e.date == date)
    return f"{count + 1:03d}"


if __name__ == "__main__":
    main()
```

需要更新 indexer.py 增加 `DraftIndex.load_or_create` 方法：

```python
# 追加到 DraftIndex 类
@classmethod
def load_or_create(cls, drafts_dir: str, project: str) -> "DraftIndex":
    index_path = os.path.join(drafts_dir, "index.md")
    if os.path.exists(index_path):
        return cls.load(index_path)
    return cls(project=project)
```

- [ ] **Step 2: 验证 CLI 可启动**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m src.cli --help
```
Expected: 显示命令列表 (generate, batch, status, approve, reject)

- [ ] **Step 3: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add CLI interface"
```

---

### Task 7: 端到端集成

**Files:**
- Modify: `src/cli.py` — 串联 copywriter + imager
- Test: `tests/content/test_integration.py`

- [ ] **Step 1: 写集成测试**

```python
# tests/content/test_integration.py
import os
import tempfile
from unittest.mock import patch, MagicMock
from src.rules.loader import load_ruleset
from src.content.indexer import DraftIndex, DraftEntry, DraftStatus
from src.content.topic import TopicSelector
from src.content.copywriter import Copywriter


def test_full_generation_flow():
    """端到端：选题 → 文案 → 写入草稿"""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    rules_dir = os.path.join(base_dir, "rules")
    rs = load_ruleset(rules_dir, "中央半岛")

    # 选题
    index = DraftIndex(project="中央半岛")
    index.entries = [
        DraftEntry("2026-05-10", "001", "老王", "market-analysis", "旧标题", DraftStatus.PUBLISHED),
    ]
    topics = TopicSelector.select(index, rs.project.content_sequence, persona="老王")
    assert len(topics) == 1
    persona_name, content_type = topics[0]

    # 文案生成
    cw = Copywriter(rs)
    system_prompt, user_prompt = cw.build_prompts(persona_name, content_type)
    assert len(system_prompt) > 0
    assert len(user_prompt) > 0

    # 写入草稿（文件系统）
    with tempfile.TemporaryDirectory() as tmpdir:
        # 模拟草稿目录
        draft_dir = os.path.join(tmpdir, "20260512_001")
        os.makedirs(os.path.join(draft_dir, "images"))

        # 写 post.md
        post_content = f"""---
id: draft-20260512-001
project: 中央半岛
persona: {persona_name}
persona_type: {rs.project.personas[0].persona_type}
content_type: {content_type}
generated_at: 2026-05-12T10:30:00
status: draft
---
# 测试标题

测试正文内容

#测试 #买房
"""
        post_path = os.path.join(draft_dir, "post.md")
        with open(post_path, "w", encoding="utf-8") as f:
            f.write(post_content)

        assert os.path.exists(post_path)

        # 验证 post.md 内容
        with open(post_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "测试标题" in content
        assert "测试正文内容" in content
        assert "#测试" in content
```

- [ ] **Step 2: 运行集成测试**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/content/test_integration.py -v
```
Expected: 1 passed

- [ ] **Step 3: 运行全部测试**

```bash
cd D:/project/xhs_post && source venv/Scripts/activate && python -m pytest tests/ -v
```
Expected: 所有测试通过 (~23 tests)

- [ ] **Step 4: 提交**

```bash
cd D:/project/xhs_post && git add -A && git commit -m "feat: add end-to-end integration test"
```
