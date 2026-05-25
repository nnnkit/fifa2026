"""Wikidata entity fetch + extraction for football players & teams.

Wikidata is the right primary source for structured player attributes
(date of birth, position, club, height, image filename, external IDs).
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests

ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
UA = "fifa2026squads-research/0.1 (contact: iankit17@gmail.com)"

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "wikidata"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_session = requests.Session()
_session.headers.update({"User-Agent": UA, "Accept": "application/json"})

_last_call = 0.0
_RATE_LIMIT_SECONDS = 0.4


def _throttle() -> None:
    global _last_call
    delta = time.time() - _last_call
    if delta < _RATE_LIMIT_SECONDS:
        time.sleep(_RATE_LIMIT_SECONDS - delta)
    _last_call = time.time()


def entity(qid: str) -> dict | None:
    if not qid or not qid.startswith("Q"):
        return None
    cache_file = CACHE_DIR / f"{qid}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    _throttle()
    last_exc: requests.RequestException | None = None
    for attempt in range(3):
        try:
            resp = _session.get(ENTITY_URL.format(qid=qid), timeout=45)
            break
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    else:
        if last_exc:
            raise last_exc
        return None
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    ent = data.get("entities", {}).get(qid)
    if ent is None:
        return None
    cache_file.write_text(json.dumps(ent))
    return ent


# ---- claim extraction helpers ----


def _claims(ent: dict, prop: str) -> list[dict]:
    return [c for c in ent.get("claims", {}).get(prop, []) if c.get("mainsnak", {}).get("snaktype") == "value"]


def _value(snak: dict) -> Any:
    return snak.get("mainsnak", {}).get("datavalue", {}).get("value")


def first_value(ent: dict, prop: str) -> Any:
    cs = _claims(ent, prop)
    return _value(cs[0]) if cs else None


def label(ent: dict, lang: str = "en") -> str | None:
    labels = ent.get("labels", {})
    return labels.get(lang, {}).get("value") if labels else None


def description(ent: dict, lang: str = "en") -> str | None:
    descs = ent.get("descriptions", {})
    return descs.get(lang, {}).get("value") if descs else None


def labels_for(qids: list[str]) -> dict[str, str]:
    """Bulk label lookup — fetch each entity (cached) and pull its English label."""
    out: dict[str, str] = {}
    for q in qids:
        e = entity(q)
        if e:
            lab = label(e)
            if lab:
                out[q] = lab
    return out


def _looks_like_national_team_label(label_text: str | None) -> bool:
    if not label_text:
        return False
    s = label_text.lower()
    return (
        " national " in s
        or s.endswith(" national football team")
        or s.endswith(" national association football team")
        or " national under-" in s
        or " olympic football team" in s
    )


def _club_candidate_sort_key(team: dict) -> str:
    return team.get("start") or team.get("end") or ""


def player_summary(ent: dict) -> dict:
    """Pull the football-relevant fields off a player entity."""
    out: dict[str, Any] = {
        "qid": ent.get("id"),
        "name": label(ent),
        "description": description(ent),
    }

    # date of birth (P569)
    dob = first_value(ent, "P569")
    if isinstance(dob, dict) and dob.get("time"):
        out["date_of_birth"] = dob["time"].lstrip("+").split("T")[0]

    # place of birth (P19)
    pob = first_value(ent, "P19")
    if isinstance(pob, dict) and pob.get("id"):
        out["place_of_birth_qid"] = pob["id"]

    # country of citizenship (P27) — list
    citi = [_value(c).get("id") for c in _claims(ent, "P27") if isinstance(_value(c), dict)]
    if citi:
        out["citizenship_qids"] = citi

    # height (P2048) — quantity with unit
    h = first_value(ent, "P2048")
    if isinstance(h, dict) and h.get("amount"):
        out["height_cm"] = float(str(h["amount"]).lstrip("+"))

    # mass (P2067)
    w = first_value(ent, "P2067")
    if isinstance(w, dict) and w.get("amount"):
        out["weight_kg"] = float(str(w["amount"]).lstrip("+"))

    # dominant hand/foot (P741)
    foot = first_value(ent, "P741")
    if isinstance(foot, dict) and foot.get("id"):
        out["foot_qid"] = foot["id"]

    # position(s) played (P413)
    pos = [_value(c).get("id") for c in _claims(ent, "P413") if isinstance(_value(c), dict)]
    if pos:
        out["position_qids"] = pos

    # member of sports team (P54) — multiple, with start/end qualifiers
    teams: list[dict] = []
    for c in _claims(ent, "P54"):
        val = _value(c)
        if not isinstance(val, dict):
            continue
        team_qid = val.get("id")
        quals = c.get("qualifiers", {})

        def _qtime(key: str) -> str | None:
            q = quals.get(key, [])
            if not q:
                return None
            dv = q[0].get("datavalue", {}).get("value")
            if isinstance(dv, dict) and dv.get("time"):
                return dv["time"].lstrip("+").split("T")[0]
            return None

        teams.append(
            {
                "team_qid": team_qid,
                "start": _qtime("P580"),
                "end": _qtime("P582"),
            }
        )
    if teams:
        out["teams"] = teams

    # Current club: P54 mixes clubs and national teams. Prefer active
    # non-national teams, otherwise fall back to the newest P54 row.
    labels: dict[str, str] = {}
    if teams:
        labels = labels_for([t["team_qid"] for t in teams if t.get("team_qid")])
    current = [
        t for t in teams
        if not t["end"] and not _looks_like_national_team_label(labels.get(t["team_qid"]))
    ]
    current.sort(key=_club_candidate_sort_key, reverse=True)
    if current:
        out["current_club_qid"] = current[0]["team_qid"]
    elif teams:
        # fallback: most recently ended
        club_like = [
            t for t in teams
            if not _looks_like_national_team_label(labels.get(t["team_qid"]))
        ]
        fallback_pool = club_like or teams
        teams_sorted = sorted(fallback_pool, key=_club_candidate_sort_key, reverse=True)
        out["current_club_qid"] = teams_sorted[0]["team_qid"]

    # image (P18) — Commons filename
    img = first_value(ent, "P18")
    if isinstance(img, str):
        out["image_filename"] = img

    # sitelink to en.wikipedia
    sl = ent.get("sitelinks", {}).get("enwiki")
    if sl:
        out["wikipedia_title"] = sl.get("title")
        out["wikipedia_url"] = sl.get("url") or (
            "https://en.wikipedia.org/wiki/" + (sl.get("title", "").replace(" ", "_"))
        )

    # external IDs that are useful
    for prop, key in [
        ("P2446", "transfermarkt_id"),
        ("P1469", "fifa_player_id"),
        ("P3565", "uefa_player_id"),
        ("P3477", "national_football_teams_id"),
        ("P1278", "legacy_fifa_id"),
        ("P4773", "soccerway_id"),
    ]:
        v = first_value(ent, prop)
        if isinstance(v, str):
            out[key] = v

    return out
