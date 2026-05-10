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
    lao_wang_topics = [t for p, t in result if p == "老王"]
    assert "area-value" in lao_wang_topics


def test_auto_skips_recent_duplicates():
    """自动选题跳过3天内已发的类型"""
    index = make_index()
    index.entries.append(
        DraftEntry("2026-05-12", "002", "老王", "area-value", "重复", DraftStatus.PUBLISHED)
    )
    result = TopicSelector.select(index, make_sequence(), persona="老王")
    assert result[0] == ("老王", "product-analysis")


def test_batch_all_personas():
    """批量为所有人设选题"""
    result = TopicSelector.select_all(make_index(), make_sequence())
    personas = {p for p, t in result}
    assert "老王" in personas
    assert "小陈" in personas
    assert len(result) >= 2
