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
        index = DraftIndex(project="测试盘")
        index.entries = [
            DraftEntry("2026-05-13", "001", "老王", "market-analysis", "测试标题", DraftStatus.DRAFT),
        ]
        index.save(index_path)

        loaded = DraftIndex.load(index_path)
        assert loaded.project == "测试盘"
        assert len(loaded.entries) == 1
        assert loaded.entries[0].title == "测试标题"
