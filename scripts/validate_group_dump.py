"""Validate a group-level research dump before verification/import.

This intentionally checks shape and basic completeness only. It does not
trust the data as production-ready; the next stage should verify values
against Wikipedia/Wikidata and then write data/teams + data/players.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DUMP_DIR = ROOT / "research" / "group-dumps"
TEAMS_FILE = ROOT / "data" / "teams.json"

POSITION_CODES = {"GK", "DF", "MF", "FW", None}
CONFIDENCE = {"high", "medium", "low"}


def _load_expected(group: str) -> list[dict]:
    teams = json.loads(TEAMS_FILE.read_text())
    return [t for t in teams if t.get("group") == group]


def _err(errors: list[str], path: str, message: str) -> None:
    errors.append(f"{path}: {message}")


def validate(group: str) -> int:
    group = group.upper()
    path = DUMP_DIR / f"group-{group}.json"
    if not path.exists():
        print(f"missing dump: {path}", file=sys.stderr)
        return 2

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc}", file=sys.stderr)
        return 2

    expected = _load_expected(group)
    expected_slugs = {t["slug"] for t in expected}
    errors: list[str] = []

    if data.get("group") != group:
        _err(errors, "group", f"expected {group!r}")
    if data.get("source_policy") != "wikipedia-wikidata-commons-only":
        _err(errors, "source_policy", "must be wikipedia-wikidata-commons-only")

    teams = data.get("teams")
    if not isinstance(teams, list):
        _err(errors, "teams", "must be a list")
        teams = []

    got_slugs = {t.get("slug") for t in teams if isinstance(t, dict)}
    if got_slugs != expected_slugs:
        _err(errors, "teams", f"expected slugs {sorted(expected_slugs)}, got {sorted(got_slugs)}")

    for i, team in enumerate(teams):
        base = f"teams[{i}]"
        if not isinstance(team, dict):
            _err(errors, base, "must be an object")
            continue
        slug = team.get("slug")
        players = team.get("players")
        if not slug:
            _err(errors, f"{base}.slug", "required")
        if not isinstance(team.get("source_urls"), list) or not team["source_urls"]:
            _err(errors, f"{base}.source_urls", "must include at least one URL")
        if not isinstance(players, list):
            _err(errors, f"{base}.players", "must be a list")
            continue
        if len(players) < 23:
            _err(errors, f"{base}.players", f"expected at least 23 players, got {len(players)}")
        if len(players) > 60:
            _err(errors, f"{base}.players", f"expected at most 60 players, got {len(players)}")

        seen_names: set[str] = set()
        for j, player in enumerate(players):
            pbase = f"{base}.players[{j}]"
            if not isinstance(player, dict):
                _err(errors, pbase, "must be an object")
                continue
            name = player.get("display_name")
            if not name:
                _err(errors, f"{pbase}.display_name", "required")
            elif name in seen_names:
                _err(errors, f"{pbase}.display_name", f"duplicate {name!r}")
            else:
                seen_names.add(name)
            if player.get("position_code") not in POSITION_CODES:
                _err(errors, f"{pbase}.position_code", "must be GK, DF, MF, FW, or null")
            if player.get("confidence") not in CONFIDENCE:
                _err(errors, f"{pbase}.confidence", "must be high, medium, or low")
            sources = player.get("sources")
            if not isinstance(sources, list) or not sources:
                _err(errors, f"{pbase}.sources", "must include at least one URL")

    if errors:
        print(f"{path} failed validation with {len(errors)} issue(s):", file=sys.stderr)
        for error in errors[:80]:
            print(f"  - {error}", file=sys.stderr)
        if len(errors) > 80:
            print(f"  ... {len(errors) - 80} more", file=sys.stderr)
        return 1

    total_players = sum(len(t.get("players", [])) for t in teams if isinstance(t, dict))
    print(f"OK group-{group}: {len(teams)} teams, {total_players} players")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("group", help="group letter, e.g. A")
    args = ap.parse_args(argv)
    return validate(args.group)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
