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
    date: str
    seq: str
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
    def load_or_create(cls, drafts_dir: str, project: str) -> "DraftIndex":
        index_path = os.path.join(drafts_dir, "index.md")
        if os.path.exists(index_path):
            return cls.load(index_path)
        return cls(project=project)

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
