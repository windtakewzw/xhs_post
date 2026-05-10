import os
import tempfile
from src.rules.loader import load_ruleset
from src.content.indexer import DraftIndex, DraftEntry, DraftStatus
from src.content.topic import TopicSelector
from src.content.copywriter import Copywriter


def test_full_generation_flow():
    """端到端：选题 -> 文案 -> 写入草稿"""
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
        draft_dir = os.path.join(tmpdir, "20260512_001")
        os.makedirs(os.path.join(draft_dir, "images"))

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

        with open(post_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "测试标题" in content
        assert "测试正文内容" in content
        assert "#测试" in content
