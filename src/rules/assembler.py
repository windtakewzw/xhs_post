from src.rules.models import RuleSet, Persona


def assemble_prompt_context(rs: RuleSet, persona_name: str, content_type: str) -> dict:
    persona = _find_persona(rs, persona_name)
    if not persona:
        raise ValueError(f"Persona not found: {persona_name}")

    return {
        "system_prompt": _build_system_prompt(rs),
        "persona_context": _build_persona_context(persona),
        "content_type": content_type,
        "hashtag_hint": _build_hashtag_hint(rs, content_type, persona),
        "image_config": _build_image_config(content_type),
        "taboos": _format_taboos(rs),
    }


def _find_persona(rs: RuleSet, name: str) -> Persona | None:
    for p in rs.project.personas:
        if p.name == name:
            return p
    return None


def _build_system_prompt(rs: RuleSet) -> str:
    """Extract the anti-AI writing rules for the system prompt."""
    lines = []
    in_section = False
    for line in rs.copywriting_raw.split('\n'):
        if '## 五、去AI味写作法则' in line:
            in_section = True
        if in_section and line.startswith('## ') and '去AI味写作法则' not in line:
            break
        if in_section:
            lines.append(line)

    anti_ai_section = '\n'.join(lines)

    return f"""你是一个小红书房产内容创作者。严格遵循以下规则：

{anti_ai_section}

重要：输出内容必须通过"修改后自查"清单的6条检查。
"""


def _build_persona_context(persona: Persona) -> str:
    parts = [
        f"人设：{persona.name}",
        f"类型：{persona.persona_type}",
        f"身份：项目置业顾问，从业{persona.years}年",
        f"性格：{'、'.join(persona.personality)}",
        f"专业：{'、'.join(persona.expertise)}",
        f"语言风格：{persona.style}",
        f"口头禅：{' / '.join(persona.catchphrases)}",
        "",
        "可以写的：",
    ]
    for d in persona.dos:
        parts.append(f"  {d}")
    parts.append("不可以写的：")
    for d in persona.donts:
        parts.append(f"  {d}")
    return '\n'.join(parts)


def _build_hashtag_hint(rs: RuleSet, content_type: str, persona: Persona) -> str:
    """Extract relevant hashtag rules for the project's city."""
    city = rs.project.city
    lines = []
    in_city = False
    for line in rs.hashtag_raw.split('\n'):
        if f'### {city}' in line:
            in_city = True
        elif in_city and line.startswith('### ') and city not in line:
            in_city = False
        elif in_city and line.strip().startswith('|'):
            lines.append(line)

    city_table = '\n'.join(lines)
    return f"建议标签层级（{city}）：\n{city_table}"


def _build_image_config(content_type: str) -> dict:
    configs = {
        "market-analysis": {"content_type": content_type, "image_count": 5,
            "sequence": ["cover", "chart", "project", "cta"]},
        "area-value": {"content_type": content_type, "image_count": 6,
            "sequence": ["cover", "planning", "amenity", "location", "info", "cta"]},
        "product-analysis": {"content_type": content_type, "image_count": 6,
            "sequence": ["cover", "living_room", "bedroom", "balcony", "floorplan", "cta"]},
        "buying-guide": {"content_type": content_type, "image_count": 5,
            "sequence": ["cover", "tip_card", "tip_card", "project", "cta"]},
        "community-life": {"content_type": content_type, "image_count": 7,
            "sequence": ["cover", "landscape", "pool", "detail", "detail", "detail", "cta"]},
        "home-aesthetics": {"content_type": content_type, "image_count": 7,
            "sequence": ["cover", "light", "material", "panorama", "inspo", "inspo", "cta"]},
        "family-living": {"content_type": content_type, "image_count": 7,
            "sequence": ["cover", "living", "kids_room", "kitchen", "education", "detail", "cta"]},
        "trend-jacking": {"content_type": content_type, "image_count": 5,
            "sequence": ["cover", "trend", "project", "project", "cta"]},
    }
    return configs.get(content_type, {"content_type": content_type, "image_count": 5,
        "sequence": ["cover", "content", "content", "cta"]})


def _format_taboos(rs: RuleSet) -> str:
    if not rs.project.taboos:
        return "无特殊禁忌"
    return "项目内容禁忌：\n" + '\n'.join(f"- {t}" for t in rs.project.taboos)
