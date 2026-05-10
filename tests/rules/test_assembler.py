import os
from src.rules.loader import load_ruleset
from src.rules.assembler import assemble_prompt_context


def test_assemble_prompt_context():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    rules_dir = os.path.join(base_dir, "rules")
    rs = load_ruleset(rules_dir, "中央半岛")

    ctx = assemble_prompt_context(rs, persona_name="老王", content_type="market-analysis")

    assert "七条铁律" in ctx["system_prompt"]
    assert "老王" in ctx["persona_context"]
    assert "investment-advisor" in ctx["persona_context"]
    assert "10年" in ctx["persona_context"]
    assert ctx["content_type"] == "market-analysis"
    assert ctx["image_config"]["content_type"] == "market-analysis"
    assert isinstance(ctx["image_config"]["image_count"], int)
    assert any("海口" in tag for tag in [ctx["hashtag_hint"]])
    assert "未交房" in ctx["taboos"]


def test_assemble_different_persona():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    rules_dir = os.path.join(base_dir, "rules")
    rs = load_ruleset(rules_dir, "中央半岛")

    ctx = assemble_prompt_context(rs, persona_name="小陈", content_type="community-life")

    assert "小陈" in ctx["persona_context"]
    assert "lifestyle-advisor" in ctx["persona_context"]
