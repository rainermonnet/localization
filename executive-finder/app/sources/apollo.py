import os
import httpx
from typing import Optional

BASE_URL = "https://api.apollo.io/v1"

SENIORITY_LEVELS = ["c_suite", "vp", "director", "manager", "owner", "founder"]


async def raw_apollo_request(
    api_key: str,
    keywords: list[str],
    titles: Optional[list[str]] = None,
    location: Optional[str] = None,
    limit: int = 25,
) -> tuple[int, list[dict], str]:
    """Returns (http_status, results, error_message)."""
    payload: dict = {
        "api_key": api_key,
        "per_page": limit,
        "page": 1,
        "person_seniorities": SENIORITY_LEVELS,
        "q_keywords": " ".join(keywords),
    }
    if titles:
        payload["person_titles"] = titles
    if location:
        payload["person_locations"] = [location]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/mixed_people/search",
                json=payload,
                headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
                timeout=15.0,
            )
        if response.status_code != 200:
            body = response.text[:300]
            return response.status_code, [], f"Apollo HTTP {response.status_code}: {body}"

        data = response.json()
        results = _parse_people(data.get("people", []), keywords)
        return 200, results, ""

    except httpx.TimeoutException:
        return 504, [], "Apollo.io Timeout – bitte erneut versuchen"
    except Exception as e:
        return 500, [], f"Verbindungsfehler: {str(e)}"


async def search_executives(
    keywords: list[str],
    titles: Optional[list[str]] = None,
    location: Optional[str] = None,
    limit: int = 25,
) -> list[dict]:
    api_key = os.environ.get("APOLLO_API_KEY", "")
    if not api_key:
        return _mock_results(keywords, titles)
    _, results, _ = await raw_apollo_request(api_key, keywords, titles, location, limit)
    return results or _mock_results(keywords, titles)


def _parse_people(people: list, keywords: list[str]) -> list[dict]:
    results = []
    for person in people:
        org = person.get("organization", {}) or {}
        results.append({
            "name": person.get("name", ""),
            "title": person.get("title", ""),
            "company": org.get("name", ""),
            "description": _build_description(person, org),
            "linkedin_url": person.get("linkedin_url", ""),
            "location": ", ".join(filter(None, [person.get("city", ""), person.get("country", "")])),
            "email": person.get("email", ""),
            "source": "Apollo.io",
            "relevance_score": _score_relevance(person, keywords),
        })
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results


def _build_description(person: dict, org: dict) -> str:
    parts = []
    if org.get("industry"):
        parts.append(f"Branche: {org['industry']}")
    if org.get("estimated_num_employees"):
        parts.append(f"Mitarbeiter: ~{org['estimated_num_employees']}")
    if org.get("short_description"):
        parts.append(org["short_description"])
    return " | ".join(parts)


def _score_relevance(person: dict, keywords: list[str]) -> float:
    score = 0.0
    text = " ".join([
        person.get("title", ""),
        person.get("headline", ""),
        (person.get("organization") or {}).get("short_description", ""),
        (person.get("organization") or {}).get("industry", ""),
    ]).lower()
    for kw in keywords:
        if kw.lower() in text:
            score += 1.0
    seniority = person.get("seniority", "")
    if seniority == "c_suite":
        score += 2.0
    elif seniority in ("vp", "owner", "founder"):
        score += 1.5
    return score


def _mock_results(keywords: list[str], titles: Optional[list[str]]) -> list[dict]:
    """Demo data when no API key is configured."""
    return [
        {
            "name": "Thomas Bergmann",
            "title": "CEO & Co-Founder",
            "company": "FutureTech Solutions",
            "description": f"Branche: Technology | Mitarbeiter: ~150 | Fokus auf {', '.join(keywords[:2])}",
            "linkedin_url": "https://linkedin.com/in/demo-thomas-bergmann",
            "location": "Frankfurt, Deutschland",
            "email": "",
            "source": "Apollo.io (Demo)",
            "relevance_score": 4.0,
        },
        {
            "name": "Dr. Julia Hoffmann",
            "title": "Chief Strategy Officer",
            "company": "Growth Partners GmbH",
            "description": f"Branche: Consulting | Mitarbeiter: ~80 | Spezialisierung: {keywords[0] if keywords else 'Strategy'}",
            "linkedin_url": "https://linkedin.com/in/demo-julia-hoffmann",
            "location": "München, Deutschland",
            "email": "",
            "source": "Apollo.io (Demo)",
            "relevance_score": 3.5,
        },
        {
            "name": "Robert Schneider",
            "title": "Managing Director",
            "company": "Scale Ventures AG",
            "description": f"Branche: Investment | Mitarbeiter: ~45 | Netzwerk in {', '.join(keywords[:2])}",
            "linkedin_url": "https://linkedin.com/in/demo-robert-schneider",
            "location": "Zürich, Schweiz",
            "email": "",
            "source": "Apollo.io (Demo)",
            "relevance_score": 3.0,
        },
    ]
