from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchParams:
    keywords: list[str]
    titles: list[str] = field(default_factory=list)
    location: Optional[str] = None
    min_relevance: float = 0.0
    sources: list[str] = field(default_factory=lambda: ["crunchbase", "apollo"])
    limit_per_source: int = 25


def parse_keywords(raw: str) -> list[str]:
    return [kw.strip() for kw in raw.replace(",", "\n").split("\n") if kw.strip()]


def merge_and_deduplicate(results_a: list[dict], results_b: list[dict]) -> list[dict]:
    seen: set[str] = set()
    merged = []
    for item in results_a + results_b:
        key = _dedup_key(item)
        if key not in seen:
            seen.add(key)
            merged.append(item)
    merged.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return merged


def _dedup_key(item: dict) -> str:
    name = item.get("name", "").lower().replace(" ", "")
    company = item.get("company", "").lower().replace(" ", "")
    return f"{name}::{company}"


OUTREACH_TEMPLATES = {
    "collaboration": (
        "Betreff: Möglichkeit zur Zusammenarbeit im Bereich {keyword}\n\n"
        "Sehr geehrte/r {name},\n\n"
        "ich bin auf Ihr Profil gestoßen und war beeindruckt von Ihrer Arbeit "
        "bei {company} im Bereich {keyword}.\n\n"
        "Als Experte/in auf diesem Gebiet sehe ich großes Potenzial für eine "
        "strategische Zusammenarbeit, die beiden Seiten erheblichen Mehrwert bieten könnte.\n\n"
        "Wären Sie offen für ein kurzes Gespräch (15-20 Min.), um auszuloten, "
        "ob es Synergien gibt?\n\n"
        "Mit freundlichen Grüßen"
    ),
    "insight_request": (
        "Betreff: Ihre Perspektive zu {keyword} – kurze Frage\n\n"
        "Sehr geehrte/r {name},\n\n"
        "Ihre Führungsarbeit bei {company} im Bereich {keyword} ist bemerkenswert. "
        "Ich beschäftige mich intensiv mit diesem Thema und würde Ihre Einschätzung "
        "zu aktuellen Entwicklungen sehr schätzen.\n\n"
        "Hätten Sie 10 Minuten für einen kurzen Austausch?\n\n"
        "Mit freundlichen Grüßen"
    ),
    "value_offer": (
        "Betreff: Konkreter Mehrwert für {company} im Bereich {keyword}\n\n"
        "Sehr geehrte/r {name},\n\n"
        "ich habe mir Ihre Strategie bei {company} genauer angesehen und "
        "glaube, dass ich Ihnen im Bereich {keyword} konkreten Mehrwert bieten kann.\n\n"
        "Mein Ansatz hat in vergleichbaren Unternehmen bereits [Ergebnis] erzielt. "
        "Gerne teile ich Details in einem kurzen Call.\n\n"
        "Mit freundlichen Grüßen"
    ),
}


def generate_outreach(person: dict, keyword: str, template_key: str = "collaboration") -> str:
    template = OUTREACH_TEMPLATES.get(template_key, OUTREACH_TEMPLATES["collaboration"])
    return template.format(
        name=person.get("name", ""),
        company=person.get("company", "Ihrem Unternehmen"),
        keyword=keyword,
    )
