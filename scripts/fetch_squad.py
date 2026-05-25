"""Fetch one team's squad with deep per-player enrichment.

Output:
  data/teams/{slug}.json       — team-level record + ordered squad list
  data/players/{slug}.json     — one file per player (denormalised for player pages)
  data/photos/{player-slug}.jpg
  data/photos/attribution.json — per-photo license/attribution

Run:
    python -m scripts.fetch_squad argentina
    python -m scripts.fetch_squad argentina --force      # ignore cache, refetch
    python -m scripts.fetch_squad argentina --no-photos  # skip photo download
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts import _squads, _wiki, _wikidata

ROOT = Path(__file__).resolve().parent.parent
TEAMS_FILE = ROOT / "data" / "teams.json"
TEAM_DIR = ROOT / "data" / "teams"
PLAYER_DIR = ROOT / "data" / "players"
PHOTO_DIR = ROOT / "data" / "photos"
ATTRIB_FILE = PHOTO_DIR / "attribution.json"


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


def _load_teams() -> list[dict]:
    if not TEAMS_FILE.exists():
        print(
            f"data/teams.json not found. Run `python -m scripts.fetch_teams` first.",
            file=sys.stderr,
        )
        sys.exit(2)
    return json.loads(TEAMS_FILE.read_text())


def _find_team(teams: list[dict], slug: str) -> dict | None:
    for t in teams:
        if t["slug"] == slug:
            return t
    return None


def _save_attribution(player_slug: str, info: dict) -> None:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    if ATTRIB_FILE.exists():
        atts = json.loads(ATTRIB_FILE.read_text())
    else:
        atts = {}
    atts[player_slug] = {
        "filename": info.get("filename"),
        "source_url": info.get("url"),
        "license": info.get("license"),
        "license_url": info.get("license_url"),
        "artist": info.get("artist"),
        "credit": info.get("credit"),
    }
    ATTRIB_FILE.write_text(json.dumps(atts, indent=2))


def enrich_player(row: _squads.SquadRow, *, download_photos: bool) -> dict:
    rec: dict = {
        "slug": _slug(row.player_name),
        "display_name": row.player_name,
        "shirt_no": row.shirt_no,
        "position_code": row.position_code,
        "dob": row.dob,
        "age": row.age,
        "caps": row.caps,
        "goals": row.goals,
        "club_from_squad_table": row.club,
        "wikipedia_title": row.wikipedia_title,
    }
    if row.dob:
        rec["date_of_birth"] = row.dob
        rec["date_of_birth_source"] = "wikipedia-squad-table"
    if row.club:
        rec["current_club"] = row.club
        rec["current_club_source"] = "wikipedia-squad-table"

    if not row.wikipedia_title:
        return rec

    qid = _wiki.page_wikidata_id(row.wikipedia_title)
    rec["wikidata_qid"] = qid
    if not qid:
        return rec

    ent = _wikidata.entity(qid)
    if not ent:
        return rec

    summary = _wikidata.player_summary(ent)
    rec.update(summary)
    if row.dob:
        if rec.get("date_of_birth") and rec["date_of_birth"] != row.dob:
            rec["wikidata_date_of_birth"] = rec["date_of_birth"]
        rec["date_of_birth"] = row.dob
        rec["date_of_birth_source"] = "wikipedia-squad-table"

    # Resolve QIDs we collected into readable labels (one-shot, cached)
    qids_to_resolve = []
    if rec.get("current_club_qid"):
        qids_to_resolve.append(rec["current_club_qid"])
    qids_to_resolve += rec.get("position_qids", [])
    qids_to_resolve += rec.get("citizenship_qids", [])
    if rec.get("foot_qid"):
        qids_to_resolve.append(rec["foot_qid"])
    if rec.get("place_of_birth_qid"):
        qids_to_resolve.append(rec["place_of_birth_qid"])
    labels = _wikidata.labels_for(list(dict.fromkeys(qids_to_resolve)))
    if rec.get("current_club_qid"):
        rec["current_club"] = labels.get(rec["current_club_qid"])
        rec["current_club_source"] = "wikidata-p54-filtered"
    if rec.get("position_qids"):
        rec["positions"] = [labels[q] for q in rec["position_qids"] if q in labels]
    if rec.get("citizenship_qids"):
        rec["citizenship"] = [labels[q] for q in rec["citizenship_qids"] if q in labels]
    if rec.get("foot_qid"):
        rec["foot"] = labels.get(rec["foot_qid"])
    if rec.get("place_of_birth_qid"):
        rec["place_of_birth"] = labels.get(rec["place_of_birth_qid"])

    if row.club:
        if rec.get("current_club") and rec["current_club"] != row.club:
            rec["wikidata_current_club"] = rec["current_club"]
            rec["wikidata_current_club_qid"] = rec.get("current_club_qid")
        rec["current_club"] = row.club
        rec["current_club_source"] = "wikipedia-squad-table"

    # Photo — prefer Wikidata P18; fall back to Wikipedia page's lead image.
    image_filename = rec.get("image_filename")
    image_source = "wikidata-p18"
    if not image_filename and rec.get("wikipedia_title"):
        fallback = _wiki.page_lead_image_filename(rec["wikipedia_title"])
        if fallback:
            image_filename = fallback
            image_source = "wikipedia-pageimage"
            rec["image_filename"] = fallback

    if image_filename:
        info = _wiki.commons_image_info(image_filename)
        if info:
            # Prefer the 800px thumb for local storage — full originals can be 5+ MB
            # and we never display larger than ~400px on the site.
            download_url = info.get("thumb_url") or info.get("url")
            rec["photo"] = {
                "filename": info["filename"],
                "url": info["url"],
                "thumb_url": info.get("thumb_url"),
                "width": info.get("width"),
                "height": info.get("height"),
                "license": info.get("license"),
                "license_url": info.get("license_url"),
                "attribution": info.get("artist") or info.get("credit"),
                "source": image_source,
            }
            if download_photos and download_url:
                ext = Path(info["filename"]).suffix or ".jpg"
                dest = PHOTO_DIR / f"{rec['slug']}{ext}"
                try:
                    _wiki.download_file(download_url, dest)
                    rec["photo"]["local_path"] = str(dest.relative_to(ROOT))
                    _save_attribution(rec["slug"], info)
                except Exception as e:  # noqa: BLE001
                    rec["photo"]["download_error"] = str(e)

    return rec


def fetch_one(slug: str, *, force: bool = False, download_photos: bool = True) -> int:
    teams = _load_teams()
    team = _find_team(teams, slug)
    if not team:
        print(f"Unknown team slug: {slug}", file=sys.stderr)
        print(f"Known: {', '.join(t['slug'] for t in teams)}", file=sys.stderr)
        return 2

    TEAM_DIR.mkdir(parents=True, exist_ok=True)
    PLAYER_DIR.mkdir(parents=True, exist_ok=True)

    out_file = TEAM_DIR / f"{slug}.json"
    if out_file.exists() and not force:
        print(f"[skip] {slug} (already exists; pass --force to refetch)")
        return 0

    country = team["country"]
    print(f"[{slug}] fetching squad for {country} …")
    rows, source = _squads.fetch_squad(
        country,
        tournament_title=team.get("tournament_article"),
        national_team_title=team.get("national_team_article"),
    )

    if not rows or not source:
        print(f"[{slug}] no squad table found in any known article", file=sys.stderr)
        return 3

    print(f"[{slug}] found {len(rows)} players via {source.kind} ({source.title})")

    players: list[dict] = []
    for i, row in enumerate(rows, 1):
        print(f"  [{i:>2}/{len(rows)}] {row.player_name}")
        rec = enrich_player(row, download_photos=download_photos)
        players.append(rec)

    record = {
        "slug": slug,
        "country": country,
        "wikidata_qid": team.get("wikidata_qid"),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "kind": source.kind,
            "title": source.title,
            "url": source.url,
        },
        "squad_size": len(players),
        "players": players,
    }
    out_file.write_text(json.dumps(record, indent=2))
    print(f"[{slug}] wrote {out_file.relative_to(ROOT)}")

    # Denormalised per-player files
    for p in players:
        if not p.get("slug"):
            continue
        prec = dict(p)
        prec["team_slug"] = slug
        prec["team_country"] = country
        (PLAYER_DIR / f"{p['slug']}.json").write_text(json.dumps(prec, indent=2))

    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Fetch one team's squad + enrichment")
    ap.add_argument("slug", help="team slug, e.g. argentina (see data/teams.json)")
    ap.add_argument("--force", action="store_true", help="refetch even if cached output exists")
    ap.add_argument("--no-photos", action="store_true", help="skip photo downloads")
    args = ap.parse_args(argv)
    return fetch_one(args.slug, force=args.force, download_photos=not args.no_photos)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
