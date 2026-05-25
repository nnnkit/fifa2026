"""Audit the fetched data for completeness and quality.

Reports per-team and overall:
  - Squad size (expected: 23–55, depending on prelim vs final list)
  - % players with DOB, current_club, position, photo, photo-on-disk
  - Players that are total blanks (no Wikidata QID) — these need manual review
  - Photo files on disk vs declared in JSON (orphans + missing)

Run:
    python -m scripts.verify              # report on every fetched team
    python -m scripts.verify argentina    # just one team
    python -m scripts.verify --strict     # exit non-zero if any team falls below thresholds
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAM_DIR = ROOT / "data" / "teams"
PLAYER_DIR = ROOT / "data" / "players"
PHOTO_DIR = ROOT / "data" / "photos"

THRESHOLDS = {
    "dob_pct": 0.95,
    "current_club_pct": 0.80,
    "photo_pct": 0.80,
}


def _pct(n: int, total: int) -> float:
    return (n / total) if total else 0.0


def _audit_one(team_path: Path) -> dict:
    d = json.loads(team_path.read_text())
    players = d.get("players", [])
    total = len(players)
    metrics = {
        "slug": d["slug"],
        "country": d["country"],
        "fetched_at": d.get("fetched_at"),
        "source": d.get("source", {}).get("kind"),
        "total": total,
        "with_qid": sum(1 for p in players if p.get("wikidata_qid")),
        "with_dob": sum(1 for p in players if p.get("date_of_birth")),
        "with_club": sum(1 for p in players if p.get("current_club")),
        "with_position": sum(1 for p in players if p.get("positions")),
        "with_height": sum(1 for p in players if p.get("height_cm")),
        "with_photo_meta": sum(1 for p in players if p.get("photo")),
        "with_photo_local": sum(
            1 for p in players if p.get("photo", {}).get("local_path")
            and (ROOT / p["photo"]["local_path"]).exists()
        ),
        "with_transfermarkt": sum(1 for p in players if p.get("transfermarkt_id")),
    }
    metrics["blank_players"] = [
        p["display_name"] for p in players if not p.get("wikidata_qid")
    ]
    metrics["missing_photo"] = [
        p["display_name"] for p in players if not p.get("photo")
    ]
    return metrics


def _print_team(m: dict) -> None:
    total = m["total"]
    print(f"\n{m['country']} ({m['slug']})  — {total} players  via {m['source']}  fetched {m['fetched_at']}")
    rows = [
        ("Wikidata QID",   m["with_qid"]),
        ("DOB",            m["with_dob"]),
        ("Current club",   m["with_club"]),
        ("Position",       m["with_position"]),
        ("Height (cm)",    m["with_height"]),
        ("Photo metadata", m["with_photo_meta"]),
        ("Photo on disk",  m["with_photo_local"]),
        ("Transfermarkt",  m["with_transfermarkt"]),
    ]
    for label, n in rows:
        pct = _pct(n, total) * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  {label:<16} {n:>3}/{total:<3}  {bar} {pct:5.1f}%")
    if m["blank_players"]:
        print(f"  ⚠ blank players (no QID): {', '.join(m['blank_players'])}")
    if m["missing_photo"]:
        print(f"  ⚠ no photo: {', '.join(m['missing_photo'])}")


def _check_orphan_files() -> tuple[int, int]:
    if not PHOTO_DIR.exists():
        return (0, 0)
    declared: set[Path] = set()
    for team_file in TEAM_DIR.glob("*.json"):
        d = json.loads(team_file.read_text())
        for p in d.get("players", []):
            lp = p.get("photo", {}).get("local_path") if isinstance(p.get("photo"), dict) else None
            if lp:
                declared.add(ROOT / lp)
    on_disk = {p for p in PHOTO_DIR.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}}
    orphans = on_disk - declared
    missing = declared - on_disk
    return len(orphans), len(missing)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?", help="team slug; omit for all")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any team below threshold")
    args = ap.parse_args(argv)

    if not TEAM_DIR.exists():
        print("No data/teams/ directory — nothing fetched yet.", file=sys.stderr)
        return 2

    files = sorted(TEAM_DIR.glob("*.json"))
    if args.slug:
        files = [f for f in files if f.stem == args.slug]
        if not files:
            print(f"No data for team slug: {args.slug}", file=sys.stderr)
            return 2

    failures: list[str] = []
    grand = {"total": 0, "qid": 0, "dob": 0, "club": 0, "photo": 0, "photo_disk": 0}
    for f in files:
        m = _audit_one(f)
        _print_team(m)
        grand["total"] += m["total"]
        grand["qid"] += m["with_qid"]
        grand["dob"] += m["with_dob"]
        grand["club"] += m["with_club"]
        grand["photo"] += m["with_photo_meta"]
        grand["photo_disk"] += m["with_photo_local"]
        if args.strict:
            if _pct(m["with_dob"], m["total"]) < THRESHOLDS["dob_pct"]:
                failures.append(f"{m['slug']}: dob {m['with_dob']}/{m['total']}")
            if _pct(m["with_club"], m["total"]) < THRESHOLDS["current_club_pct"]:
                failures.append(f"{m['slug']}: club {m['with_club']}/{m['total']}")
            if _pct(m["with_photo_meta"], m["total"]) < THRESHOLDS["photo_pct"]:
                failures.append(f"{m['slug']}: photo {m['with_photo_meta']}/{m['total']}")

    print("\n" + "=" * 70)
    t = grand["total"] or 1
    print(f"GRAND TOTAL — {len(files)} team(s), {grand['total']} players")
    print(f"  Wikidata QID    {grand['qid']:>4}/{grand['total']}  ({grand['qid']/t*100:.1f}%)")
    print(f"  DOB             {grand['dob']:>4}/{grand['total']}  ({grand['dob']/t*100:.1f}%)")
    print(f"  Current club    {grand['club']:>4}/{grand['total']}  ({grand['club']/t*100:.1f}%)")
    print(f"  Photo metadata  {grand['photo']:>4}/{grand['total']}  ({grand['photo']/t*100:.1f}%)")
    print(f"  Photo on disk   {grand['photo_disk']:>4}/{grand['total']}  ({grand['photo_disk']/t*100:.1f}%)")

    orphans, missing = _check_orphan_files()
    print(f"\nPhoto files: {orphans} orphan(s) on disk, {missing} declared-but-missing")

    if failures:
        print(f"\n❌ {len(failures)} threshold failure(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
