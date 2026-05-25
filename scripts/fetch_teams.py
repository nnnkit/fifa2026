"""Build data/teams.json — the 48 qualified FIFA 2026 teams.

Source of truth: the Wikipedia article "2026 FIFA World Cup squads" — its
section structure is 12 H2 group headers (Group A..L) each followed by 4 H3
country headers. That gives us the country name AND the group assignment in
one cheap call (the sections list endpoint is tiny).

Each team's Wikidata QID is then resolved from "{Country} national football team".

Run:
    python -m scripts.fetch_teams
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from scripts import _wiki

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "teams.json"
SQUADS_ARTICLE = "2026 FIFA World Cup squads"

# A small map for cases where "{Country} national football team" needs a
# different form (Wikipedia article naming quirks). Add to this as discovered.
NAT_TEAM_OVERRIDES = {
    "Australia": "Australia men's national soccer team",
    "Canada": "Canada men's national soccer team",
    "United States": "United States men's national soccer team",
    "South Korea": "South Korea national football team",
    "Turkey": "Turkey national football team",
    "Ivory Coast": "Ivory Coast national football team",
    "DR Congo": "DR Congo national football team",
}


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


def _sections() -> list[dict]:
    data = _wiki.get(
        action="parse",
        page=SQUADS_ARTICLE,
        prop="sections",
        redirects=1,
    )
    return data.get("parse", {}).get("sections", [])


def main() -> int:
    print(f"Reading sections of '{SQUADS_ARTICLE}' …")
    sections = _sections()
    if not sections:
        print("No sections returned — the article may have changed.", file=sys.stderr)
        return 1

    current_group: str | None = None
    teams: list[dict] = []
    for s in sections:
        line = s.get("line", "").strip()
        level = s.get("level")
        if level in ("2", 2):
            if line.lower().startswith("group "):
                current_group = line.split(" ", 1)[1].strip()
            else:
                current_group = None  # leaving the groups area (Statistics, Notes, etc.)
            continue
        if level in ("3", 3) and current_group:
            country = line
            nat_article = NAT_TEAM_OVERRIDES.get(country, f"{country} national football team")
            teams.append(
                {
                    "slug": _slug(country),
                    "country": country,
                    "group": current_group,
                    "national_team_article": nat_article,
                    "tournament_article": f"{country} at the 2026 FIFA World Cup",
                }
            )

    if not teams:
        print("Parsed no teams. The article structure may have changed.", file=sys.stderr)
        return 1

    print(f"Parsed {len(teams)} teams across {len({t['group'] for t in teams})} groups.")
    print("Resolving Wikidata QIDs (one lookup per national-team article)…")
    for t in teams:
        qid = _wiki.page_wikidata_id(t["national_team_article"])
        t["wikidata_qid"] = qid
        marker = qid or "(no QID)"
        print(f"  Group {t['group']:>1}  {t['country']:<25}  {marker}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(teams, indent=2))
    print(f"\nWrote {len(teams)} teams → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
