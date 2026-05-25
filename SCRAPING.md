# Scraping — sources, learnings, how to run periodically

This is the operational handbook for the data side of fifa2026squads.com.
Read this **first** before touching anything in `scripts/` or making changes
to the periodic refresh. Update it whenever you learn something the next
person (or agent) needs to know.

For matchday lineups, injuries, suspensions, and post-match low-token
refreshing, read `REFETCHING.md` next.

---

## How to run — the everything command

From `fifa-2026/`:

```bash
# one-time setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt

# 1. resolve the 48 qualified teams
python -m scripts.fetch_teams

# 2. fetch all 48 squads + enrich every player + download photos
python -m scripts.fetch_all

# 3. audit what we got
python -m scripts.verify

# refresh later (e.g. after FIFA's squad-submission deadline)
python -m scripts.fetch_all --force
```

Per-team workflow (smoke tests, debugging, a single fresh team):

```bash
python -m scripts.fetch_squad argentina
python -m scripts.fetch_squad argentina --force      # ignore cache, refetch
python -m scripts.fetch_squad argentina --no-photos  # skip downloads
python -m scripts.verify argentina
```

Queue-mode for autonomous loops (Codex, /loop, cron, GitHub Actions):

```bash
python -m scripts.fetch_all next      # exactly one un-fetched team
# exit 0 → keep looping; exit 2 → all 48 done; exit >2 → error
```

Plain shell:

```bash
while python -m scripts.fetch_all next; do :; done
```

Status at any time:

```bash
python -m scripts.fetch_all status
```

---

## Source ranking — what we use and why

The whole pipeline is built on **legal, free, well-licensed sources** with
public APIs that explicitly permit reuse. No commercial scrapers, no
ToS-violating endpoints. The cost of a takedown notice or IP ban during the
tournament window would be catastrophic.

### Primary (use these)

| Source | What we get from it | Why we trust it | API/access |
|---|---|---|---|
| **Wikipedia** (`en.wikipedia.org/w/api.php`) | Squad list (the central `2026 FIFA World Cup squads` article is *the* canonical aggregator), per-player articles, page lead images, section structure | Volunteer-edited but heavily watched; sourced; CC-BY-SA licensed; structured templates make parsing reliable | MediaWiki Action API — free, no key |
| **Wikidata** (`www.wikidata.org/wiki/Special:EntityData/Q…json`) | Per-player structured data: DOB, height, weight, nationality, current club, career history, image filename, external IDs (Transfermarkt, FIFA, UEFA) | Structured, typed, machine-readable; same edits that update Wikipedia flow here | EntityData JSON dumps — free, no key |
| **Wikimedia Commons** (`commons.wikimedia.org/w/api.php`) | Player photos with explicit license + attribution | Same license-checking infra as the rest of Wikimedia; safe for commercial reuse with attribution | MediaWiki Action API — free, no key |

### Secondary (don't use unless we explicitly negotiate access)

| Source | Why not | What it would give us |
|---|---|---|
| Transfermarkt | ToS prohibits scraping; aggressive anti-bot | Better market values, more current club info, deeper market histories |
| FotMob / SofaScore | ToS prohibits non-app access to their unofficial APIs | Live match data, injury feeds, in-game stats |
| FIFA.com | Has rate limits + JS-rendered pages; no public squad API | The official-source bonus |
| ESPN / BBC | Editorial pages, no API | News summaries already covered by RSS |

**The injury/news scanner (Phase 2) MUST use only RSS / public news APIs** —
BBC Sport RSS, ESPN RSS, official club RSS feeds, plus an aggregator like
NewsAPI on a paid tier. Do not scrape ESPN article pages directly.

---

## What the API returns — coverage we have learned to expect

Run on Argentina's preliminary 55-man squad, 2026-05-24:

| Field | Coverage | Where it comes from | Failure mode |
|---|---:|---|---|
| Wikidata QID | 100% | Wikipedia `pageprops` lookup | Player has no Wikipedia article (very rare for WC squads) |
| Date of birth | 100% | Wikidata P569 | Stub entity with missing claims |
| Transfermarkt ID | 100% | Wikidata P2446 | Same as above |
| Height (cm) | 96% | Wikidata P2048 | Younger players sometimes missing |
| Position(s) | 89% | Wikidata P413 | Resolved from QID labels |
| Photo (Wikidata P18) | 85% | Wikidata + Commons lookup | **Young players with stub articles often have NO photo anywhere** |
| Current club | 80% | Wikidata P54, latest with no end-date | Stale data when transfer hasn't been edited yet |
| Weight (kg) | ~50% | Wikidata P2067 | Less commonly populated than height |
| Dominant foot | 0% | (Wikidata P741 is wrong — actual property is P5328 for football; **see TODO**) | Property mismatch — open bug |

Expect these numbers to **rise** as we get closer to the tournament — Wikipedia
editor activity spikes when squads are announced. Treat current numbers as a
floor, not a ceiling.

---

## What we have learned (keep adding to this)

### Wikipedia article shapes for 2026

- `2026 FIFA World Cup squads` is the canonical squad article. It groups by
  H2 (Group A..L) and H3 (each country). Already populated as of 2026-05-24
  with preliminary lists (often 25–55 players per team). Final 26-man lists
  land after FIFA's submission deadline (~10 days pre-tournament, so ~June 1
  2026).
- `{Country} at the 2026 FIFA World Cup` articles **do not all exist yet** —
  Argentina's is missing as of 2026-05-24. Useful as a fallback, not a primary.
- `{Country} national football team` is the safest final fallback — every
  qualified country has one.
- Country names in the central article use specific forms: `Turkey` (not
  Türkiye), `United States` (not USA), `DR Congo` (not Democratic Republic
  of Congo), `South Korea`. The `NAT_TEAM_OVERRIDES` map in
  `scripts/fetch_teams.py` handles known divergences from the
  `{country} national football team` pattern — add to it as needed.
- The "Statistics" section in the central article also uses H3 headers
  (`Age`, `Coaches`, `Coach representation by country`) — the parser only
  picks up H3s that follow a `Group X` H2, so these are correctly skipped.

### Wikipedia squad tables

- The squad template `{{nat fs g player}}` renders to a `<table
  class="wikitable">` with column order: No., Pos. (GK/DF/MF/FW), Player,
  DOB/age, Caps, Goals, Club.
- The Player column contains a `<a href="/wiki/Foo">` for every player who
  has an article. Red-links (no article) currently fail to enrich — we get
  the name but no Wikidata QID, no photo, no club. Real but rare for WC squads.
- The DOB cell embeds the ISO date inside parentheses `(YYYY-MM-DD)`.
  Currently our row-level parser misses this for some players (returns
  null) but Wikidata catches it — net DOB coverage is still 100%.

### Wikidata extraction gotchas

- **P54 (member of sports team)** is a list with start (P580) / end (P582)
  date qualifiers. We pick the row with no end-date and latest start as
  "current club". Most accurate available — beats the squad-table club
  column which is often empty.
- **Image (P18)** stores just the filename ("Lionel Messi 2018.jpg"). To get
  URL + license, query Commons `imageinfo` separately.
- **Citizenship (P27)** can be multi-valued (e.g. Messi has AR/ES/IT). We
  store all, the site picks the relevant one.
- **Dominant foot is P5328**, not P741 (which is dominant *hand* used in
  tennis). Open TODO — fix in `_wikidata.py`.

### Photo strategy

- We download the **800px thumb** (via Commons `iiurlwidth=800`), not the
  full original. Saves ~10× disk + bandwidth, plenty for cards & profile pages.
- Stored as `data/photos/{player-slug}.{ext}` where extension comes from
  the original filename (jpg / png / webp).
- License + attribution captured in `data/photos/attribution.json`. **This
  must appear on every photo on the site** — CC-BY-SA requirement.
- Fallback path when Wikidata P18 is empty: try Wikipedia's `pageimages` API.
- **When both fail (8/55 in Argentina): render an initials avatar** on the
  site. Don't keep retrying — these players genuinely have no Wikipedia
  photo. Either they're too young/obscure, or their article is a stub.

### Caching contract

- Wikipedia responses cached at `.cache/wiki/` keyed by SHA256(endpoint+params).
- Wikidata entities cached at `.cache/wikidata/{QID}.json`.
- Photos: never re-downloaded if file exists and is non-empty.
- Team JSON files at `data/teams/{slug}.json` act as the "done marker" —
  presence = skip in queue mode; pass `--force` to overwrite.
- **Delete `.cache/` before any periodic refresh that should pull fresh
  Wikipedia data.** Otherwise we'll just re-use yesterday's cached responses.

### Rate-limiting

- ~2 req/sec to en.wikipedia.org, ~2.5 req/sec to wikidata.org. Both APIs
  document soft limits; the `User-Agent` header (set to
  `fifa2026squads-research/0.1`) identifies us so they can throttle/contact
  us if we misbehave.
- Full 48-team cold run: ~1500 player records × ~3 API calls each ≈ 4500
  requests ≈ **35–45 minutes** end-to-end with photos.
- Warm run (everything cached except deltas): ~5 minutes.

### Schema contract with the site (web/)

- `web/src/lib/data.ts` reads from `../../data/` directly via `fs`.
- The TypeScript interfaces in that file (`TeamMeta`, `TeamRecord`,
  `PlayerRecord`, `PlayerPhoto`) are the contract. **Any change to scraper
  output must be reflected there**, or the site breaks silently.
- Photo serving: the site expects to read photos at `/photos/{filename}`.
  In dev, symlink `web/public/photos -> ../../data/photos`. In CI/build,
  copy the directory.

---

## Periodic-refresh plan

Three different cadences, three different commands.

### Daily — status overlays only (Phase 2, not built yet)

```cron
0 0 * * *  cd /path/to/fifa-2026 && /path/to/.venv/bin/python -m scripts.scan_news_and_classify
```

Reads each player's name, pulls last-24h news from RSS sources, LLM-classifies
into `available | doubtful | injured | suspended | yellow-warning`, writes
to `data/status/{player-slug}.json`. Site rebuilds affected pages via
on-demand revalidation.

### Weekly — squad + Wikidata refresh

```cron
0 3 * * 1  cd /path/to/fifa-2026 && rm -rf .cache && /path/to/.venv/bin/python -m scripts.fetch_all --force
```

Pulls latest Wikipedia squad edits + Wikidata claim updates. Catches new
caps/goals, transfers, photos becoming available. Deleting `.cache/` is
intentional — we want fresh data, not cached.

### Event-driven — squad announcement deadline (~June 1, 2026)

Manual trigger when FIFA confirms the final 26-man squads:

```bash
cd fifa-2026
rm -rf .cache data/teams data/players
python -m scripts.fetch_all --force
python -m scripts.verify --strict
```

Expect squad sizes to drop from 26–55 to exactly 26 per team. If they don't,
Wikipedia hasn't caught up yet — wait 12 hours, retry.

---

## Known issues / TODO

In priority order:

- [ ] **Foot (P741) is wrong** — should be P5328 for football. 0% coverage
  currently. One-line fix in `_wikidata.py`.
- [ ] **Caps/goals from squad table are null** for ~5/55 players because
  the row parser misses comma-separated numbers. Wikidata has caps_for_country
  (P1350) — could fall back.
- [ ] **Initials-avatar component** for the site, for the players with no
  photo anywhere. Should match the photo dimensions so layout doesn't shift.
- [ ] **`{Country} at the 2026 FIFA World Cup` articles**: most don't exist
  yet. Re-test the fallback chain after squad-submission deadline; per-team
  articles tend to appear right around then.
- [ ] **Coach data**: the central article has coach info per team.
  `scripts/fetch_squad.py` doesn't extract it yet. Worth adding before
  building the team-page coach card.
- [ ] **OG image generation**: build-time generate a 1200×630 PNG per team
  and per player (photo + name + country). Add to `web/src/lib/og.ts`.
- [ ] **Players-by-country deduplication**: a player with dual nationality
  (e.g. Messi: AR/ES/IT) currently only attaches to the team that fetched
  them. Not a problem for the squad pages — the team they actually represent
  is the one that called them up.

---

## Hand-off note to whoever runs this next (human or agent)

If `python -m scripts.fetch_teams` returns 0 teams, the
`2026 FIFA World Cup squads` article probably changed structure. Look at its
section list (Wikipedia API: `action=parse&page=...&prop=sections`), confirm
the group H2 / country H3 pattern still holds, and update
`scripts/fetch_teams.py` accordingly.

If `python -m scripts.fetch_squad <team>` fails with "no squad table found",
all three fallback articles are failing. Open the central article and the
per-team article in a browser — Wikipedia almost certainly has the data, but
the `<table class="wikitable">` selector might be wrong, or a country header
uses a different name than our `teams.json` (e.g. `Turkey` vs `Türkiye`,
which is how this exact bug manifested first time).

If verification suddenly drops below thresholds on a previously-good team,
**don't refetch blindly** — first check if Wikipedia removed/edited the
squad section. Pulling junk data and overwriting good data is worse than
serving slightly stale data.
