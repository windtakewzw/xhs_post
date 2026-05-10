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

        for i in range(len(seq)):
            candidate = seq[(start_idx + i) % len(seq)]
            if candidate not in recent:
                return candidate

        return seq[start_idx]
