"""Parse squad tables out of rendered Wikipedia HTML.

Wikipedia squad tables follow a consistent template across national-team articles
(`{{nat fs g player}}` etc). After rendering, they become a `<table class="wikitable">`
with columns: No., Pos., Player, DOB/age, Caps, Goals, Club.

We try three article shapes in order:
  1. The central "2026 FIFA World Cup squads" article, grouped by team header
  2. The per-team tournament article: "{Country} at the 2026 FIFA World Cup"
  3. The team's main article: "{Country} national football team" (current squad section)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from . import _wiki  # type: ignore  # noqa


@dataclass
class SquadRow:
    shirt_no: int | None
    position_code: str | None  # "GK" / "DF" / "MF" / "FW"
    player_name: str
    wikipedia_title: str | None
    dob: str | None
    age: int | None
    caps: int | None
    goals: int | None
    club: str | None


@dataclass
class SquadSource:
    title: str  # Wikipedia article title we pulled from
    url: str
    kind: str  # "tournament-central" | "tournament-team" | "national-team"


_ASOFRX = re.compile(r"\((\d{4}-\d{2}-\d{2})\)")
_AGERX = re.compile(r"\baged?\s+(\d+)\b")


def _parse_player_cell(cell: Tag) -> tuple[str, str | None]:
    """Return (player_name, wikipedia_title or None)."""
    link = cell.find("a")
    if link and link.get("href", "").startswith("/wiki/") and "redlink" not in link.get("href", ""):
        title = link["href"][len("/wiki/") :].split("#")[0].replace("_", " ")
        from urllib.parse import unquote

        return link.get_text(strip=True), unquote(title)
    return cell.get_text(strip=True), None


def _parse_dob_age(cell: Tag) -> tuple[str | None, int | None]:
    text = cell.get_text(" ", strip=True)
    dob = None
    age = None
    bday = cell.find(class_="bday")
    if bday:
        dob = bday.get_text(strip=True)
    m = _ASOFRX.search(text)
    if m and not dob:
        dob = m.group(1)
    m2 = _AGERX.search(text)
    if m2:
        try:
            age = int(m2.group(1))
        except ValueError:
            pass
    return dob, age


def _parse_int(cell: Tag) -> int | None:
    txt = cell.get_text(strip=True).replace(",", "")
    try:
        return int(txt)
    except ValueError:
        return None


def _parse_row(tr: Tag) -> SquadRow | None:
    tds = tr.find_all(["td", "th"])
    if len(tds) < 5:
        return None
    # Heuristic: first td is shirt no., second is position (GK/DF/MF/FW)
    pos_text = tds[1].get_text(strip=True)
    if pos_text not in ("GK", "DF", "MF", "FW", "1GK", "2DF", "3MF", "4FW"):
        return None
    pos_code = pos_text[-2:]
    shirt = _parse_int(tds[0])
    name, wp_title = _parse_player_cell(tds[2])
    dob, age = _parse_dob_age(tds[3]) if len(tds) > 3 else (None, None)
    caps = _parse_int(tds[4]) if len(tds) > 4 else None
    goals = _parse_int(tds[5]) if len(tds) > 5 else None
    club_cell = tds[6] if len(tds) > 6 else None
    club = None
    if club_cell is not None:
        club_links = [
            a for a in club_cell.find_all("a")
            if a.get_text(strip=True) and a.get("href", "").startswith("/wiki/")
        ]
        club_link = club_links[-1] if club_links else None
        club = (club_link.get_text(strip=True) if club_link else club_cell.get_text(strip=True))
    return SquadRow(
        shirt_no=shirt,
        position_code=pos_code,
        player_name=name,
        wikipedia_title=wp_title,
        dob=dob,
        age=age,
        caps=caps,
        goals=goals,
        club=club,
    )


def _parse_squad_table(table: Tag) -> list[SquadRow]:
    rows: list[SquadRow] = []
    for tr in table.find_all("tr"):
        row = _parse_row(tr)
        if row:
            rows.append(row)
    return rows


def squad_from_html(html: str) -> list[SquadRow]:
    """Pick the first plausible squad wikitable from a rendered Wikipedia page."""
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table", class_="wikitable"):
        rows = _parse_squad_table(table)
        if len(rows) >= 11:  # need at least a starting XI to count as a squad
            return rows
    return []


def squad_from_central_article(html: str, country: str) -> list[SquadRow]:
    """The central squads article groups by H2/H3 country header."""
    soup = BeautifulSoup(html, "html.parser")
    # Find the heading whose anchor matches the country
    target = None
    for h in soup.find_all(["h2", "h3"]):
        span = h.find("span", class_="mw-headline")
        text = (span.get_text(strip=True) if span else h.get_text(strip=True))
        if text and text.lower() == country.lower():
            target = h
            break
    if target is None:
        return []
    # Walk siblings until next heading of same/higher level
    for sib in target.find_all_next():
        if sib.name in ("h2", "h3") and sib is not target:
            break
        if sib.name == "table" and "wikitable" in (sib.get("class") or []):
            rows = _parse_squad_table(sib)
            if len(rows) >= 11:
                return rows
    return []


CENTRAL_ARTICLE = "2026 FIFA World Cup squads"


def fetch_squad(
    country: str,
    *,
    tournament_title: str | None = None,
    national_team_title: str | None = None,
) -> tuple[list[SquadRow], SquadSource | None]:
    """Try three sources in order; return rows + which source we used."""
    # 1. Central tournament squads article
    html = _wiki.parse_html(CENTRAL_ARTICLE)
    if html:
        rows = squad_from_central_article(html, country)
        if rows:
            return rows, SquadSource(
                title=CENTRAL_ARTICLE,
                url="https://en.wikipedia.org/wiki/" + CENTRAL_ARTICLE.replace(" ", "_"),
                kind="tournament-central",
            )

    # 2. Per-team tournament article
    per_team_title = tournament_title or f"{country} at the 2026 FIFA World Cup"
    html = _wiki.parse_html(per_team_title)
    if html:
        rows = squad_from_html(html)
        if rows:
            return rows, SquadSource(
                title=per_team_title,
                url="https://en.wikipedia.org/wiki/" + per_team_title.replace(" ", "_"),
                kind="tournament-team",
            )

    # 3. National team article (current squad)
    nat_title = national_team_title or f"{country} national football team"
    html = _wiki.parse_html(nat_title)
    if html:
        rows = squad_from_html(html)
        if rows:
            return rows, SquadSource(
                title=nat_title,
                url="https://en.wikipedia.org/wiki/" + nat_title.replace(" ", "_"),
                kind="national-team",
            )

    return [], None
