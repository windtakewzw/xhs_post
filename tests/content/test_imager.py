import os
from src.content.imager import Imager


def test_imager_decision_matrix():
    assert Imager.decide_mode(has_photos=True, has_renders=False, is_cover=False) == ("img2img", 0.35, None)
    assert Imager.decide_mode(has_photos=False, has_renders=True, is_cover=False) == ("img2img", 0.45, "效果图仅供参考")
    assert Imager.decide_mode(has_photos=False, has_renders=False, is_cover=False) == ("text2img", None, "概念示意图，以实际为准")
    assert Imager.decide_mode(has_photos=True, has_renders=True, is_cover=True) == ("text2img", None, None)


def test_imager_get_image_config():
    config = Imager.get_image_config("market-analysis")
    assert config["image_count"] == 5
    assert config["content_type"] == "market-analysis"
    assert "cover" in config["sequence"]


def test_imager_visual_style():
    style = Imager.get_visual_style("investment-advisor")
    assert "cool tones" in style["colors"]
    assert "professional" in style["lighting"]

    style = Imager.get_visual_style("lifestyle-advisor")
    assert "warm tones" in style["colors"]


def test_imager_build_prompt():
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
