"""Create explicit baseline status files for every player.

The live news scanner can overwrite individual files with sourced injury,
suspension, doubtful, or yellow-card updates. Until then, every player gets an
explicit baseline status instead of relying on the web layer's fallback.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAM_DIR = ROOT / "data" / "teams"
STATUS_DIR = ROOT / "data" / "status"

VALID_NON_BASELINE = {"yellow", "doubtful", "injured", "suspended"}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing available baseline files; never overwrites non-available files",
    )
    parser.add_argument(
        "--timestamp",
        default=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        help="ISO timestamp to store in generated status files",
    )
    args = parser.parse_args(argv)

    created = 0
    updated = 0
    skipped = 0

    if not TEAM_DIR.exists():
        raise SystemExit("data/teams does not exist; run scripts.fetch_all first")

    for team_file in sorted(TEAM_DIR.glob("*.json")):
        team = _read_json(team_file)
        source = team.get("source") or {}
        for player in team.get("players", []):
            slug = player.get("slug")
            if not slug:
                continue
            out = STATUS_DIR / f"{slug}.json"
            existed = out.exists()
            if existed:
                existing = _read_json(out)
                if existing.get("status") in VALID_NON_BASELINE:
                    skipped += 1
                    continue
                if not args.force:
                    skipped += 1
                    continue
            status = {
                "status": "available",
                "reason": (
                    "Baseline status from current squad inclusion; no separate sourced "
                    "injury, suspension, or yellow-card update is recorded yet."
                ),
                "last_updated": args.timestamp,
                "source": {
                    "url": source.get("url") or "",
                    "headline": f"{team.get('country', 'Team')} current squad source",
                },
            }
            _write_json(out, status)
            if existed:
                updated += 1
            else:
                created += 1

    print(f"status baseline created={created} updated={updated} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
