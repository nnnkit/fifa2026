# Codex agent prompt — populate ONE team's squad data

You are running inside the `fifa-2026/` directory of a project that builds
fifa2026squads.com — a daily-refreshed reference site for the 2026 FIFA World
Cup squads. Your job is to **populate accurate, complete data for exactly one
team** and then exit.

## The team you are working on

- Country: **{COUNTRY}**
- Slug: **{SLUG}**
- Group: **{GROUP}**
- Wikidata QID: **{QID}**
- Source-of-truth article: <https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads>

Do not touch any other team. Do not edit unrelated files.

## Runtime contract

Use the project virtualenv for every Python command:

```bash
.venv/bin/python -m scripts.fetch_squad {SLUG} --force
.venv/bin/python -m scripts.verify {SLUG}
```

Do not use bare `python` or `python3`. The orchestrator puts `.venv/bin`
first in `PATH`, but explicit `.venv/bin/python` is required so missing
dependencies fail less often.

This is a bounded one-team run. Spend at most 2-3 repair iterations after
the deterministic fetch. If Wikimedia sources do not provide enough
photos, document that in the team JSON and exit; do not get stuck chasing
manual photo searches.

Hard stop rule: if `.venv/bin/python -m scripts.fetch_squad {SLUG} --force`
fails because Wikimedia/Wikidata/Commons cannot be reached, print
`BLOCKED {SLUG} fetch_failed` with the traceback summary and exit. Do not
reconstruct the squad manually from `.cache`, browser pages, web search,
or per-player lookups.

Do not use `agent-browser`, browser automation, live web search, or broad
cache greps. The deterministic scraper is the source path for live data.

## Success criteria — your run is "done" only when ALL pass

1. `data/teams/{SLUG}.json` exists and is valid JSON.
2. `.venv/bin/python -m scripts.verify {SLUG}` reports:
    - Wikidata QID coverage ≥ 95%
    - DOB coverage ≥ 95%
    - Current club coverage ≥ 80%
    - Photo coverage ≥ 80%
3. `data/players/<player-slug>.json` exists for every player in the squad.
4. Photos downloaded to `data/photos/<player-slug>.{jpg,png,webp}` for every
   player with a photo URL.

The orchestrator will re-run `verify {SLUG}` after you exit. If any threshold
fails, your run is considered failed.

## Workflow

### Step 1 — run the existing deterministic scraper

```bash
.venv/bin/python -m scripts.fetch_squad {SLUG} --force
```

This handles 80–95% of the work via the Wikipedia + Wikidata + Commons
pipeline. Read `SCRAPING.md` for the source rules — **do not bypass them**.
We use only Wikipedia, Wikidata, and Wikimedia Commons. Transfermarkt,
FotMob, and SofaScore are off-limits (their ToS prohibits scraping; a
takedown during the tournament would be catastrophic).

### Step 2 — check what's still missing

```bash
.venv/bin/python -m scripts.verify {SLUG}
```

Look at the per-field coverage bars. Common gaps and how to fix them:

- **Player rows missing from squad table** — the row parser sometimes
  drops players whose row has merged cells or unusual formatting.
  Fix: open the squad article, find the country's section, look at the
  HTML structure. If the parser needs fixing, edit `scripts/_squads.py`
  carefully (the change must not break already-working teams). Otherwise
  hand-edit `data/teams/{SLUG}.json` to add the missing player records
  with the same shape as existing rows.
- **Player has no `wikidata_qid`** — usually a red-link in the squad
  table. Search Wikipedia by name, find the player, re-run
  `scripts/fetch_squad.py {SLUG}` after confirming the link exists. If
  the player genuinely has no article, leave the row as-is — partial
  data is OK for stub players.
- **No photo** — Wikidata's P18 may be empty AND the Wikipedia page may
  have no infobox image. Confirm by visiting the article. If a photo
  exists on the page but isn't being picked up, check why — but **do
  not** scrape commercial sources to fill the gap. Leave it; the site
  will render an initials avatar.
- **No `current_club`** — usually means the player's Wikidata P54
  (member of sports team) claims all have end dates. Check Wikidata
  directly. If a current club is obvious from a recent news source,
  you may add it to the JSON directly, with `current_club_source:
  "manual-override"`.

### Step 3 — re-verify

```bash
.venv/bin/python -m scripts.verify {SLUG}
```

Iterate Steps 2–3 until you're either passing all thresholds or have
documented (in the team JSON's top-level `"notes"` field) why a specific
threshold can't be met (e.g. "12 players are uncapped youth call-ups
with no Wikipedia articles").

### Step 4 — exit

Print a one-line summary:

```
DONE {SLUG} squad={N} photos={N}/{TOTAL} club={N}/{TOTAL}
```

Then exit cleanly. **Do not** try to improve any other team. **Do not**
commit anything to git. **Do not** edit anything outside `data/`,
`scripts/_squads.py`, or `data/teams/{SLUG}.json` itself.

## Hard rules — violations kill the run

- No HTTP calls to Transfermarkt, FotMob, SofaScore, ESPN, or any
  commercial site for data scraping.
- No `git commit`, `git push`, or any git-mutating command.
- No `pip install` of new packages. Use what's in
  `scripts/requirements.txt`.
- No edits to files outside the allowlist above.
- No background processes or long-running daemons. This is a one-shot run.

## If things go wrong

If `fetch_squad.py` errors out: read the traceback, check
`SCRAPING.md` for the relevant section, fix the smallest thing that
unblocks the run, document the fix in the team JSON's `"notes"` field.

If you can't reach success criteria after 2–3 iterations: exit with a
short report on what's blocking. The orchestrator will log it and move
on — partial data is better than a stuck run.
