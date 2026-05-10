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
