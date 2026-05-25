"""Validate per-player status overlay coverage."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAM_DIR = ROOT / "data" / "teams"
PLAYER_DIR = ROOT / "data" / "players"
STATUS_DIR = ROOT / "data" / "status"

VALID_STATUSES = {"available", "yellow", "doubtful", "injured", "suspended"}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _valid_iso(value: str | None) -> bool:
    if not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def main() -> int:
    failures: list[str] = []
    team_player_slugs: set[str] = set()

    for team_file in sorted(TEAM_DIR.glob("*.json")):
        team = _read_json(team_file)
        for player in team.get("players", []):
            slug = player.get("slug")
            if not slug:
                failures.append(f"{team_file.name}: player row without slug")
                continue
            team_player_slugs.add(slug)
            if not (PLAYER_DIR / f"{slug}.json").exists():
                failures.append(f"{team.get('slug')}: missing player file for {slug}")
            if not (STATUS_DIR / f"{slug}.json").exists():
                failures.append(f"{team.get('slug')}: missing status file for {slug}")

    status_files = sorted(STATUS_DIR.glob("*.json")) if STATUS_DIR.exists() else []
    for status_file in status_files:
        slug = status_file.stem
        data = _read_json(status_file)
        status = data.get("status")
        if slug not in team_player_slugs:
            failures.append(f"{slug}: status file not referenced by any team row")
        if status not in VALID_STATUSES:
            failures.append(f"{slug}: invalid status {status!r}")
        if not data.get("reason"):
            failures.append(f"{slug}: missing reason")
        if not _valid_iso(data.get("last_updated")):
            failures.append(f"{slug}: missing/invalid last_updated")
        source = data.get("source") or {}
        if not source.get("url") or not source.get("headline"):
            failures.append(f"{slug}: missing source.url/source.headline")

    print(f"team_player_slugs={len(team_player_slugs)} status_files={len(status_files)}")
    if failures:
        print(f"❌ {len(failures)} status failure(s):")
        for item in failures[:80]:
            print(f"  - {item}")
        if len(failures) > 80:
            print(f"  ... {len(failures) - 80} more")
        return 1
    print("Status overlay coverage OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
