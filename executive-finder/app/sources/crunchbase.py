import os
import httpx
from typing import Optional

BASE_URL = "https://api.crunchbase.com/api/v4"

EXECUTIVE_TITLES = [
    "CEO", "Chief Executive Officer",
    "CTO", "Chief Technology Officer",
    "COO", "Chief Operating Officer",
    "CFO", "Chief Financial Officer",
    "CMO", "Chief Marketing Officer",
    "CPO", "Chief Product Officer",
    "Founder", "Co-Founder",
    "Managing Director", "General Manager",
    "Vice President", "VP",
    "President",
]


async def search_executives(
    keywords: list[str],
    titles: Optional[list[str]] = None,
    location: Optional[str] = None,
    limit: int = 25,
) -> list[dict]:
    api_key = os.environ.get("CRUNCHBASE_API_KEY", "")
    if not api_key:
        return _mock_results(keywords, titles)

    target_titles = titles or EXECUTIVE_TITLES

    query = {
        "field_ids": [
            "first_name", "last_name", "title", "primary_job_title",
            "primary_organization", "short_description", "profile_image_url",
            "linkedin", "location_identifiers",
        ],
        "query": [
            {
                "type": "predicate",
                "field_id": "facet_ids",
                "operator_id": "includes",
                "values": ["person"],
            },
            {
                "type": "predicate",
                "field_id": "primary_job_title",
                "operator_id": "contains",
                "values": target_titles[:5],
            },
        ],
        "limit": limit,
    }

    if keywords:
        query["query"].append({
            "type": "predicate",
            "field_id": "short_description",
            "operator_id": "contains",
            "values": keywords,
        })

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/searches/people",
            json=query,
            params={"user_key": api_key},
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()

    results = []
    for entity in data.get("entities", []):
        props = entity.get("properties", {})
        org = props.get("primary_organization", {})
        results.append({
            "name": f"{props.get('first_name', '')} {props.get('last_name', '')}".strip(),
            "title": props.get("primary_job_title", props.get("title", "")),
            "company": org.get("value", "") if isinstance(org, dict) else "",
            "description": props.get("short_description", ""),
            "linkedin_url": props.get("linkedin", {}).get("value", "") if isinstance(props.get("linkedin"), dict) else "",
            "location": _extract_location(props.get("location_identifiers", [])),
            "source": "Crunchbase",
            "relevance_score": _score_relevance(props, keywords),
        })

    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results


def _extract_location(location_identifiers: list) -> str:
    if not location_identifiers:
        return ""
    parts = [loc.get("value", "") for loc in location_identifiers if isinstance(loc, dict)]
    return ", ".join(filter(None, parts[:2]))


def _score_relevance(props: dict, keywords: list[str]) -> float:
    score = 0.0
    text = f"{props.get('short_description', '')} {props.get('primary_job_title', '')}".lower()
    for kw in keywords:
        if kw.lower() in text:
            score += 1.0
    return score


def _mock_results(keywords: list[str], titles: Optional[list[str]]) -> list[dict]:
    """Demo data when no API key is configured."""
    demo = [
        {
            "name": "Dr. Anna Müller",
            "title": "CEO",
            "company": "TechVentures GmbH",
            "description": f"Expertin für {', '.join(keywords[:2])} und digitale Transformation.",
            "linkedin_url": "",
            "location": "München, Deutschland",
            "source": "Crunchbase (Demo)",
            "relevance_score": 3.0,
        },
        {
            "name": "Marcus Weber",
            "title": "Managing Director",
            "company": "Innovation Labs AG",
            "description": f"Führungskraft mit Schwerpunkt {', '.join(keywords[:2])}.",
            "linkedin_url": "",
            "location": "Berlin, Deutschland",
            "source": "Crunchbase (Demo)",
            "relevance_score": 2.5,
        },
        {
            "name": "Sarah Klein",
            "title": "CTO",
            "company": "Digital Dynamics SE",
            "description": f"Technologieführerin im Bereich {keywords[0] if keywords else 'Innovation'}.",
            "linkedin_url": "",
            "location": "Hamburg, Deutschland",
            "source": "Crunchbase (Demo)",
            "relevance_score": 2.0,
        },
    ]
    return demo
