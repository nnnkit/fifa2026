"""Orchestrate squad fetches across all 48 teams.

Three modes:

    python -m scripts.fetch_all              # iterate every team, skip done
    python -m scripts.fetch_all --force      # refetch every team
    python -m scripts.fetch_all next         # fetch exactly ONE un-fetched team

The `next` subcommand is designed for autonomous loop runners (/loop, /goal,
cron, GitHub Actions). Exit codes:

    0  — work was done and more teams remain
    2  — nothing left to do (all teams fetched)
    >2 — error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts import fetch_squad

ROOT = Path(__file__).resolve().parent.parent
TEAMS_FILE = ROOT / "data" / "teams.json"
TEAM_DIR = ROOT / "data" / "teams"


def _load_teams() -> list[dict]:
    if not TEAMS_FILE.exists():
        print("data/teams.json not found. Run `python -m scripts.fetch_teams` first.", file=sys.stderr)
        sys.exit(2)
    return json.loads(TEAMS_FILE.read_text())


def _is_done(slug: str) -> bool:
    return (TEAM_DIR / f"{slug}.json").exists()


def _remaining(teams: list[dict]) -> list[dict]:
    return [t for t in teams if not _is_done(t["slug"])]


def cmd_all(force: bool, download_photos: bool) -> int:
    teams = _load_teams()
    failed: list[str] = []
    for t in teams:
        rc = fetch_squad.fetch_one(t["slug"], force=force, download_photos=download_photos)
        if rc not in (0,):
            failed.append(t["slug"])
    print(f"\nDone. {len(teams) - len(failed)} ok, {len(failed)} failed.")
    if failed:
        print("Failed:", ", ".join(failed))
        return 1
    return 0


def cmd_next(download_photos: bool) -> int:
    teams = _load_teams()
    rem = _remaining(teams)
    if not rem:
        print("All teams fetched — nothing to do.")
        return 2
    target = rem[0]
    print(f"Picking next un-fetched team: {target['slug']} ({len(rem)} remaining including this)")
    rc = fetch_squad.fetch_one(target["slug"], force=False, download_photos=download_photos)
    if rc != 0:
        print(f"Fetch failed for {target['slug']} (rc={rc})", file=sys.stderr)
        return rc + 10  # surface the upstream code shifted into the >2 error band
    still_remaining = len(_remaining(teams))
    print(f"OK. {still_remaining} team(s) still remaining.")
    return 0 if still_remaining > 0 else 2


def cmd_status() -> int:
    teams = _load_teams()
    done = [t for t in teams if _is_done(t["slug"])]
    rem = [t for t in teams if not _is_done(t["slug"])]
    print(f"{len(done)}/{len(teams)} teams fetched.")
    if rem:
        print("Remaining:", ", ".join(t["slug"] for t in rem))
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Run squad fetches across all teams")
    ap.add_argument("mode", nargs="?", default="all", choices=("all", "next", "status"))
    ap.add_argument("--force", action="store_true", help="(mode=all) refetch every team")
    ap.add_argument("--no-photos", action="store_true", help="skip photo downloads")
    args = ap.parse_args(argv)
    if args.mode == "all":
        return cmd_all(force=args.force, download_photos=not args.no_photos)
    if args.mode == "next":
        return cmd_next(download_photos=not args.no_photos)
    if args.mode == "status":
        return cmd_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
