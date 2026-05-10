import os
from unittest.mock import patch, MagicMock
from src.rules.loader import load_ruleset
from src.content.copywriter import Copywriter


def test_copywriter_builds_prompt():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    rules_dir = os.path.join(base_dir, "rules")
    rs = load_ruleset(rules_dir, "中央半岛")

    cw = Copywriter(rs)
    system_prompt, user_prompt = cw.build_prompts("老王", "market-analysis", topic="LPR降息")

    assert "七条铁律" in system_prompt
    assert "老王" in user_prompt
    assert "market-analysis" in user_prompt
    assert "LPR降息" in user_prompt


@patch('src.content.copywriter.Anthropic')
def test_copywriter_generate(mock_anthropic):
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


def test_copywriter_anti_ai_check():
    cw = Copywriter(MagicMock())

    ai_text = "综上所述，该楼盘是一个非常值得购买的优质项目"
    assert not cw.passes_anti_ai_check(ai_text)

    human_text = "说实话，看了这么多盘，这个户型确实让人心动"
    assert cw.passes_anti_ai_check(human_text)


def test_copywriter_anti_ai_flag_words():
    cw = Copywriter(MagicMock())
    for word in ["综上所述", "总而言之", "值得注意的是", "极致", "非凡", "卓越"]:
        assert not cw.passes_anti_ai_check(f"这是一段{word}的测试文本"), f"Should reject: {word}"
