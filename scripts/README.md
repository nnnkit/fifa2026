# scripts/

Data-ingestion scripts for fifa2026squads.com.

Primary source: **Wikipedia + Wikidata + Wikimedia Commons**. All three are
free, well-licensed (CC-BY-SA / public domain photos), have public APIs, and
encourage reuse with attribution. We do **not** scrape Transfermarkt, FotMob,
or SofaScore — their ToS prohibits it.

## Setup

```bash
cd fifa-2026
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
```

All scripts must be run as modules from the `fifa-2026` directory so the
`scripts.*` imports resolve:

```bash
cd fifa-2026
python -m scripts.fetch_teams
```

## Order of operations

1. **`fetch_teams.py`** — discovers the 48 qualified teams from the Wikipedia
   category "Teams at the 2026 FIFA World Cup" and writes `data/teams.json`
   with `slug`, `country`, `wikidata_qid`, and the relevant article titles.

2. **`fetch_squad.py <slug>`** — for one team:
    - Locates the squad table, trying three articles in order:
      `2026 FIFA World Cup squads` → `{Country} at the 2026 FIFA World Cup`
      → `{Country} national football team` (current squad section).
    - Parses each player row (shirt #, position, name, DOB, caps, goals, club).
    - For every player with a Wikipedia link: resolves to Wikidata QID, pulls
      DOB / height / weight / dominant foot / position(s) / current club /
      citizenship / external IDs / photo filename.
    - Downloads the Commons photo into `data/photos/{player-slug}.jpg` and
      records license + attribution in `data/photos/attribution.json`.
    - Writes `data/teams/{slug}.json` (team-level + ordered squad) and
      `data/players/{slug}.json` (one denormalised file per player).

3. **`fetch_all.py`** — three modes:
    - `python -m scripts.fetch_all` — iterate every team, skip ones already done.
    - `python -m scripts.fetch_all --force` — refetch every team.
    - `python -m scripts.fetch_all next` — fetch exactly **one** un-fetched
      team and report how many remain. Designed for autonomous loop runners.
    - `python -m scripts.fetch_all status` — show progress.

4. **`seed_status.py` / `verify_status.py`** — status overlay baseline:
    - `python -m scripts.seed_status` creates one explicit `available`
      status file per player, sourced to the current squad source.
    - `python -m scripts.verify_status` validates that every player row has
      a status overlay file and that each file has a valid status, timestamp,
      reason, and source.
    - The news scanner can overwrite individual baseline files with sourced
      `injured`, `doubtful`, `suspended`, or `yellow` updates.

## Running autonomously

The `next` subcommand is loop-friendly. It picks the next un-fetched team,
runs it, exits **0 if more work remains** and **2 when everything is done**.
Wire it up however you like:

### Built-in `/loop`

```
/loop python -m scripts.fetch_all next
```

This re-runs every few seconds (self-paced) until exit code 2.

### `/goal` (if you have a custom goal-runner skill)

The script's "exit 0 → keep going, exit 2 → done" contract is a clean goal
loop. Point it at:

```bash
cd fifa-2026 && python -m scripts.fetch_all next
```

and let it iterate until it sees a non-zero "nothing to do" exit.

### Plain shell

```bash
while python -m scripts.fetch_all next; do :; done
```

### Cron (refresh nightly)

```cron
0 3 * * *  cd /path/to/fifa-2026 && /path/to/.venv/bin/python -m scripts.fetch_all --force
```

## Data layout

```
data/
├── teams.json                       # 48-team index
├── teams/
│   └── argentina.json               # squad + all enrichment, per team
├── players/
│   └── lionel-messi.json            # denormalised per player
├── status/
│   └── lionel-messi.json            # availability overlay per player
└── photos/
    ├── lionel-messi.jpg
    └── attribution.json             # required for CC-BY-SA compliance
```

## Caching

- MediaWiki responses cache to `.cache/wiki/`.
- Wikidata entities cache to `.cache/wikidata/`.
- Photos are downloaded once per filename (skipped if file exists & non-empty).
- `data/teams/{slug}.json` is treated as the per-team "done marker" — pass
  `--force` to overwrite.

Add `.cache/` to `.gitignore`. `data/` is committed (small, reviewable diffs
on each squad update).

## Rate-limit etiquette

Each helper throttles to ~2 requests/second per host. A full 48-team run
with photo downloads takes ~15-20 minutes depending on squad sizes. Both
APIs are happy at this rate as long as the `User-Agent` identifies you —
edit `UA` in `_wiki.py` / `_wikidata.py` if you fork.

## Attribution

Photos from Commons are mostly CC-BY-SA. You must display the credit
shown in `data/photos/attribution.json` next to each photo on the site
(name + license + license link). This is a hard requirement — bake it
into the player-card component, not as an afterthought.
