from dataclasses import dataclass, field


@dataclass
class Persona:
    name: str
    persona_type: str  # investment-advisor | lifestyle-advisor | family-advisor
    account_id: str
    years: int
    personality: list[str]
    expertise: list[str]
    style: str
    catchphrases: list[str]
    dos: list[str]
    donts: list[str]
    content_distribution: dict[str, float]
    frequency: str


@dataclass
class ContentTypeConfig:
    id: str
    suitable_personas: list[str]
    frequency: str  # high | medium | low | instant
    priority: int
    image_count: str  # "4-5", "5-7" etc.
    image_sequence: list[dict]


@dataclass
class ProjectRules:
    project: str
    city: str
    project_type: str
    features: list[str]
    personas: list[Persona]
    feature_tags: list[str]
    taboos: list[str]
    content_sequence: dict[str, list[str]]  # persona_name -> [content_type_id]
    publish_window: str
    min_interval_hours: int
    max_weekly: int
    preferred_hours: list[str]
    project_interval_hours: int


@dataclass
class RuleSet:
    copywriting_raw: str
    image_raw: str
    hashtag_raw: str
    project: ProjectRules
