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
    assert any("#海景房" in tag for tag in rules.feature_tags)
    assert "本项目未交房，不编造入住体验" in rules.taboos
    assert rules.publish_window == "10:00-21:00"
    assert rules.min_interval_hours == 24
    assert rules.max_weekly == 3
    assert rules.project_interval_hours == 3
    assert "12:00-13:00" in rules.preferred_hours


def test_parse_project_rules_content_sequence():
    rules = parse_project_rules(SAMPLE_PROJECT_RULES)
    assert "投资顾问老王" in rules.content_sequence
    assert rules.content_sequence["投资顾问老王"] == [
        "market-analysis", "area-value", "product-analysis", "buying-guide"
    ]
