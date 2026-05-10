import click
import os
from datetime import datetime

from src.rules.loader import load_ruleset
from src.content.indexer import DraftIndex, DraftEntry, DraftStatus
from src.content.topic import TopicSelector


@click.group()
def main():
    """xhs_post - 小红书内容发布系统"""
    pass


@main.command()
@click.option("--project", required=True, help="项目名")
@click.option("--persona", default=None, help="人设名")
@click.option("--type", "content_type", default=None, help="内容类型")
@click.option("--topic", default=None, help="选题方向")
def generate(project, persona, content_type, topic):
    """生成单篇内容"""
    click.echo(f"[generate] {project} persona={persona} type={content_type}")
    rules_dir = "rules"
    data_dir = os.path.join("data", project)
    drafts_dir = os.path.join(data_dir, "drafts")

    rs = load_ruleset(rules_dir, project)
    index = DraftIndex.load_or_create(drafts_dir, project)

    topics = TopicSelector.select(
        index, rs.project.content_sequence,
        persona=persona, content_type=content_type,
    )

    for p_name, ct in topics:
        today = datetime.now().strftime("%Y%m%d")
        seq = _next_seq(index, today)
        click.echo(f"  生成: {p_name} x {ct} -> {today}_{seq}")


@main.command()
@click.option("--project", required=True, help="项目名")
@click.option("--persona", default=None, help="人设名")
@click.option("--days", default=7, help="生成天数")
@click.option("--count", default=None, type=int, help="生成篇数")
def batch(project, persona, days, count):
    """批量生成内容"""
    click.echo(f"[batch] {project} days={days} count={count}")


@main.command()
@click.option("--project", required=True, help="项目名")
@click.option("--persona", default=None, help="人设名")
def status(project, persona):
    """查看草稿/发布状态"""
    data_dir = os.path.join("data", project)
    drafts_dir = os.path.join(data_dir, "drafts")
    try:
        index = DraftIndex.load(os.path.join(drafts_dir, "index.md"))
        counts = {}
        for entry in index.entries:
            counts[entry.status.value] = counts.get(entry.status.value, 0) + 1
        click.echo(f"项目: {project}")
        for s, c in counts.items():
            click.echo(f"  {s}: {c}篇")
    except FileNotFoundError:
        click.echo(f"项目 {project} 还没有草稿")


@main.command()
@click.option("--project", required=True)
@click.option("--id", "draft_id", required=True)
def approve(project, draft_id):
    """审核通过草稿"""
    data_dir = os.path.join("data", project)
    drafts_dir = os.path.join(data_dir, "drafts")
    index = DraftIndex.load(os.path.join(drafts_dir, "index.md"))
    date, seq = draft_id.split("_")
    index.update_status(date, seq, DraftStatus.PENDING_PUBLISH)
    index.save(os.path.join(drafts_dir, "index.md"))
    click.echo(f"已通过: {draft_id} -> pending_publish")


@main.command()
@click.option("--project", required=True)
@click.option("--id", "draft_id", required=True)
def reject(project, draft_id):
    """驳回草稿"""
    data_dir = os.path.join("data", project)
    drafts_dir = os.path.join(data_dir, "drafts")
    index = DraftIndex.load(os.path.join(drafts_dir, "index.md"))
    date, seq = draft_id.split("_")
    index.update_status(date, seq, DraftStatus.FAILED)
    index.save(os.path.join(drafts_dir, "index.md"))
    click.echo(f"已驳回: {draft_id}")


def _next_seq(index: DraftIndex, date: str) -> str:
    count = sum(1 for e in index.entries if e.date == date)
    return f"{count + 1:03d}"


if __name__ == "__main__":
    main()
