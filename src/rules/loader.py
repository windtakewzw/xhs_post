import re
import yaml

from src.rules.models import Persona, ProjectRules, RuleSet


def parse_frontmatter(markdown: str) -> dict:
    """Extract YAML frontmatter from markdown."""
    match = re.match(r'^---\n(.*?)\n---', markdown, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1))


def parse_project_rules(markdown: str) -> ProjectRules:
    meta = parse_frontmatter(markdown)
    personas = _parse_personas(markdown)
    feature_tags = _parse_section_list(markdown, "项目特性标签")
    taboos = _parse_section_list(markdown, "项目内容禁忌")
    content_sequence = _parse_content_sequence(markdown)
    publish_config = _parse_publish_config(markdown)

    return ProjectRules(
        project=meta.get("project", ""),
        city=meta.get("city", ""),
        project_type=meta.get("type", ""),
        features=meta.get("features", []),
        personas=personas,
        feature_tags=feature_tags,
        taboos=taboos,
        content_sequence=content_sequence,
        publish_window=publish_config.get("每日发布窗口", "10:00-21:00"),
        min_interval_hours=_parse_int_field(publish_config, "本账号最小间隔", 24),
        max_weekly=_parse_int_field(publish_config, "本账号最大周发", 3),
        preferred_hours=[h.strip() for h in publish_config.get("优选时段", "").split(",") if h.strip()],
        project_interval_hours=_parse_int_field(publish_config, "同项目多账号间隔", 3),
    )


def _parse_personas(markdown: str) -> list[Persona]:
    """Parse persona definitions from markdown."""
    personas = []
    blocks = re.split(r'### 人设\d+：', markdown)
    for block in blocks[1:]:
        p = _parse_single_persona(block)
        if p:
            personas.append(p)
    return personas


def _parse_single_persona(block: str) -> Persona | None:
    name_match = re.search(r'^- \*\*姓名\*\*：(.+)', block, re.MULTILINE)
    type_match = re.search(r'^- \*\*人设类型\*\*：(.+)', block, re.MULTILINE)
    account_match = re.search(r'^- \*\*账号\*\*：(.+)', block, re.MULTILINE)
    years_match = re.search(r'^- \*\*从业年限\*\*：(\d+)', block, re.MULTILINE)
    personality_match = re.search(r'^- \*\*性格标签\*\*：(.+)', block, re.MULTILINE)
    expertise_match = re.search(r'^- \*\*专业领域\*\*：(.+)', block, re.MULTILINE)
    style_match = re.search(r'^- \*\*语言风格\*\*：(.+)', block, re.MULTILINE)
    catchphrases_match = re.search(r'^- \*\*口头禅\*\*：(.+)', block, re.MULTILINE)
    freq_match = re.search(r'\*\*发布频次\*\*：(.+)', block)

    if not name_match:
        return None

    dos = _parse_list_section(block, "✅")
    donts = _parse_list_section(block, "❌")
    distribution = _parse_distribution_table(block)

    return Persona(
        name=name_match.group(1).strip(),
        persona_type=type_match.group(1).strip() if type_match else "",
        account_id=account_match.group(1).strip() if account_match else "",
        years=int(years_match.group(1)) if years_match else 0,
        personality=[t.strip() for t in personality_match.group(1).split("、")] if personality_match else [],
        expertise=[t.strip() for t in expertise_match.group(1).split("、")] if expertise_match else [],
        style=style_match.group(1).strip() if style_match else "",
        catchphrases=[t.strip() for t in catchphrases_match.group(1).split("、")] if catchphrases_match else [],
        dos=dos,
        donts=donts,
        content_distribution=distribution,
        frequency=freq_match.group(1).strip() if freq_match else "",
    )


def _parse_list_section(block: str, prefix: str) -> list[str]:
    """Parse lines matching '- ✅ "..."' or '- ❌ "..."' pattern."""
    items = []
    for line in block.split('\n'):
        stripped = line.strip()
        if stripped.startswith(f'- {prefix}'):
            item = stripped[len(f'- {prefix}'):].strip().strip('"')
            if item:
                items.append(item)
    return items


def _parse_distribution_table(block: str) -> dict[str, float]:
    """Parse content distribution table to {content_type: ratio}."""
    result = {}
    in_table = False
    for line in block.split('\n'):
        if '| 内容类型 | 占比 |' in line or '|---------|------|' in line:
            in_table = True
            continue
        if in_table and line.strip().startswith('|'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2 and parts[0] != '内容类型':
                try:
                    result[parts[0]] = float(parts[1].replace('%', '')) / 100
                except ValueError:
                    pass
        elif in_table and not line.strip().startswith('|'):
            in_table = False
    return result


def _parse_section_list(markdown: str, section_name: str) -> list[str]:
    """Parse bullet list items under a section header."""
    pattern = rf'## [{re.escape("一二三四五六七八九十")}\d]+、{re.escape(section_name)}\n(.*?)(?=\n## |\Z)'
    match = re.search(pattern, markdown, re.DOTALL)
    if not match:
        return []
    section = match.group(1)
    items = []
    for line in section.split('\n'):
        stripped = line.strip()
        if stripped.startswith('- '):
            item = stripped[2:].strip()
            if item:
                items.append(item)
    return items


def _parse_content_sequence(markdown: str) -> dict[str, list[str]]:
    """Parse content rotation sequence like '投资顾问老王：market-analysis → area-value → buying-guide → 循环'."""
    result = {}
    pattern = r'^(.+?)：\s*$'
    lines = markdown.split('\n')
    for i, line in enumerate(lines):
        match = re.match(pattern, line.strip())
        if match and i + 1 < len(lines):
            name = match.group(1).strip()
            seq_line = lines[i + 1].strip()
            parts = [s.strip() for s in seq_line.split('→')]
            # Filter out "循环" (rotation marker, not a content type)
            parts = [p for p in parts if p != '循环']
            if parts:
                result[name] = parts
    return result


def _parse_publish_config(markdown: str) -> dict[str, str]:
    """Parse publish config table."""
    section_match = re.search(r'## 五、发布配置\n(.*?)(?=\n## |\Z)', markdown, re.DOTALL)
    if not section_match:
        return {}
    section = section_match.group(1)
    result = {}
    for line in section.split('\n'):
        if line.strip().startswith('|') and '|' in line[1:]:
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2 and parts[0] not in ('参数', '------', ''):
                result[parts[0]] = parts[1]
    return result


def load_ruleset(rules_dir: str, project_name: str) -> RuleSet:
    import os

    copywriting_path = os.path.join(rules_dir, "copywriting-rules.md")
    image_path = os.path.join(rules_dir, "image-rules.md")
    hashtag_path = os.path.join(rules_dir, "hashtag-rules.md")
    project_path = os.path.join(rules_dir, project_name, "rules.md")

    copywriting_raw = _read_file(copywriting_path)
    image_raw = _read_file(image_path)
    hashtag_raw = _read_file(hashtag_path)
    project_raw = _read_file(project_path)

    project = parse_project_rules(project_raw)

    return RuleSet(
        copywriting_raw=copywriting_raw,
        image_raw=image_raw,
        hashtag_raw=hashtag_raw,
        project=project,
    )


def _parse_int_field(config: dict, key: str, default: int) -> int:
    """Parse an integer field from config, handling non-numeric values gracefully."""
    value = config.get(key, str(default))
    # Strip common suffixes
    for suffix in ["小时", "篇", "个"]:
        value = value.replace(suffix, "")
    try:
        return int(value.strip())
    except (ValueError, AttributeError):
        return default


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
