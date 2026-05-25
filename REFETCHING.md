# Efficient refetching runbook

This is the matchday operating plan for keeping fifa2026squads.com current
without spending tokens on full-site rereads.

It answers three questions:

1. Who is in the official squad?
2. Who is playing in each match?
3. Who is injured, doubtful, suspended, or one booking from suspension?

The key rule: do not rescan all 1,436 player pages after every match. Drive the
work from the fixture schedule, only touch the two teams involved, and only send
small source snippets to an LLM when deterministic parsing cannot decide.

---

## Current state

Already implemented:

- `data/teams/*.json` and `data/players/*.json` contain all 48 teams.
- `data/status/*.json` contains a baseline `available` status for every unique
  player slug.
- `python -m scripts.verify --strict` checks squad/profile/photo coverage.
- `python -m scripts.verify_status` checks status overlay coverage.

Not implemented yet:

- A live lineup/event fetcher.
- An injury/news scanner.
- Match-scoped appearance files.

Do not claim live injury or lineup automation until those scanners exist.

---

## Source priority

Use the highest tier that exists for the fact being updated.

| Tier | Source | Use for | Notes |
|---|---|---|---|
| 0 | FIFA official squad and match pages | final squads, fixtures, official lineups, match reports, disciplinary records | Highest trust. FIFA says final 26-player lists are official on 2 June 2026; national-team announcements before then are provisional. |
| 1 | National association official site/social | squad announcements, injury replacements, team medical updates | Use when FIFA has not updated yet. Keep the URL and timestamp. |
| 2 | Licensed sports-data API | confirmed lineups, bench, substitutions, cards, injuries/sidelined players | Best automation path if budget allows. Sportmonks documents lineups, confirmed-lineup metadata, and sidelined players; Sportradar documents lineups plus missing players/injuries. |
| 3 | Editorial/RSS sources | injury doubts, coach quotes, post-match injury news | BBC Sport and ESPN provide football/soccer RSS feeds. Use headlines/snippets as candidate generation, not as the only proof for major status changes. |
| 4 | General search | last-resort corroboration | Only query exact player/team terms for already-flagged candidates. |

Avoid:

- Unofficial FotMob/SofaScore/Transfermarkt endpoints unless we have explicit
  licensed access.
- Fan accounts, forums, and unsourced social posts as single-source evidence.
- Full-page scraping through an LLM. Fetch, parse, diff, then classify only the
  small changed snippets.

Reference URLs:

- FIFA squad rules: https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/squad-lists-number-date
- FIFA squad tracker: https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/all-world-cup-squad-announcements
- FIFA fixtures: https://www.fifa.com/tournaments/mens/worldcup/canadamexicousa2026/scores-fixtures
- BBC Sport feed docs: https://support.bbc.co.uk/platform/feeds/SportFeeds.htm
- ESPN RSS feeds: https://www.espn.com/soccer/story/_/id/37380404/rss-feeds
- Sportmonks lineups/injuries docs: https://docs.sportmonks.com/football/tutorials-and-guides/tutorials/lineups-and-formations
- Sportradar soccer lineup docs: https://developer.sportradar.com/soccer/docs/soccer-ig-rosters-lineups-transfers

---

## Data model rule

Keep these separate:

### Player availability

File: `data/status/{player-slug}.json`

Use for:

- `available`
- `doubtful`
- `injured`
- `suspended`
- `yellow`

This answers: can the player be selected for the next match?

### Match participation

Recommended file:

`data/matches/{match-id}.json`

Use for:

- starter
- bench
- not in squad
- subbed on
- subbed off
- unused substitute
- goals/cards/minutes

This answers: what happened in this specific match?

Do not overwrite a player’s global availability just because they did not start
a match. A player can be available and still be benched.

---

## Refetch cadence

### Daily outside matchdays

Run once or twice per day.

Scope:

- Official squad page/tracker.
- RSS/news feeds.
- Only players with new candidate headlines.

Output:

- Update `data/status/*.json` only for changed availability.
- Leave unchanged `available` baselines alone.

### Matchday before kickoff

For each match, scope to the two teams only.

Suggested windows:

- T-24h: scan official team/news sources for injuries and suspensions.
- T-6h: refresh team availability candidates.
- T-90m to kickoff: poll official lineups / licensed API more aggressively.
- Stop lineup polling once a confirmed lineup is found.

Output:

- `data/matches/{match-id}.json` with starters/bench/not-in-squad.
- `data/status/*.json` only when the source explicitly says injured,
  doubtful, suspended, or yellow-risk.

### During the match

If using a licensed live API:

- Poll the fixture/event endpoint every 2-5 minutes.
- Update substitutions, cards, goals, and minutes in the match file.
- Do not run LLM classification during normal event polling.

If using only free sources:

- Do not attempt full live automation.
- Wait for official live match centre or match report updates.
- Update manually or semi-manually from the official page.

### After full time

Run three passes:

1. T+15m: final score, starters, bench, subs, cards.
2. T+2h: official report and disciplinary state.
3. T+12h: injury/news scan for post-match injuries or coach updates.

Only the two teams from that match are in scope.

---

## Low-token pipeline

### Step 1: candidate generation without LLM

Fetch structured feeds/pages and keep only changed records:

- HTTP `ETag` / `Last-Modified` if available.
- Content hash per URL.
- For RSS, compare item GUID/link/title/date.
- For APIs, compare fixture `updated_at`, lineup confirmation flag, event IDs,
  and injury/sideline IDs.

Store the previous source snapshot. If nothing changed, do nothing.

### Step 2: deterministic extraction first

No LLM needed for:

- confirmed lineup JSON
- substitutions
- cards
- goals
- final score
- source timestamps
- exact squad list rows

### Step 3: LLM only for ambiguous news

Send only this compact payload:

```json
{
  "player_slug": "lionel-messi",
  "player_name": "Lionel Messi",
  "team": "Argentina",
  "current_status": "available",
  "source": {
    "url": "https://example.com/story",
    "headline": "Messi trains separately before opener",
    "published_at": "2026-06-10T18:20:00Z",
    "snippet": "Coach says Messi will be assessed before tomorrow's match..."
  },
  "allowed_statuses": ["available", "doubtful", "injured", "suspended", "yellow"]
}
```

Expected classifier output:

```json
{
  "status": "doubtful",
  "confidence": "medium",
  "reason": "Coach said he will be assessed before the next match.",
  "source_url": "https://example.com/story",
  "needs_human_review": false
}
```

Never send whole team JSON, full articles, or all player records to the model.

---

## Update rules

Use conservative rules. Wrong injury data is worse than stale availability.

- `injured`: source says ruled out, unavailable, withdrawn, serious injury, or
  replaced because of injury/illness.
- `doubtful`: source says fitness test, trained separately, questionable,
  will be assessed, race to be fit.
- `suspended`: official disciplinary suspension or red/card accumulation ban
  for the next match.
- `yellow`: official tournament disciplinary state says one yellow from
  suspension.
- `available`: confirmed squad inclusion and no active stronger status.

Downgrades back to `available` require a stronger source than the original
status, such as official lineup inclusion, official training/medical update, or
the player appearing in a match.

---

## Suggested implementation phases

### Phase 1: source ledger and no-token diffs

Add a small cache/ledger:

- `data/source_snapshots/rss/*.json`
- `data/source_snapshots/fixtures/*.json`
- `data/source_snapshots/lineups/*.json`

Each record stores URL, fetched_at, etag/last_modified if present, content hash,
and extracted item IDs.

### Phase 2: match files

Add `data/matches/{match-id}.json` from the schedule:

```json
{
  "match_id": "group-a-001",
  "home_team": "mexico",
  "away_team": "south-africa",
  "status": "scheduled",
  "lineups_confirmed": false,
  "players": {
    "mexico": [],
    "south-africa": []
  },
  "sources": []
}
```

### Phase 3: licensed API integration

If we can pay for one provider, prefer the one with:

- World Cup coverage confirmed in writing.
- Confirmed lineup flag.
- Bench and substitutions.
- Missing/sidelined player feed.
- Clear redistribution terms for our website/API.

Use that for match participation. Keep FIFA/official association pages as the
trust source for final squad and official corrections.

### Phase 4: RSS/news injury scanner

Build a candidate scanner that:

1. Reads BBC/ESPN/official federation feeds.
2. Filters by current squad player names and team names.
3. Stores candidate snippets.
4. Classifies only candidates.
5. Writes changed `data/status/*.json`.
6. Runs `python -m scripts.verify_status`.

---

## Matchday checklist

For each match:

1. Identify the two team slugs from schedule.
2. Refresh only those team/player/status records.
3. Fetch official or licensed lineup source.
4. Write match participation data.
5. Process cards/suspensions after final whistle.
6. Scan injury news for only those two teams at T+2h and T+12h.
7. Run:

```bash
python -m scripts.verify_status
cd web && npm run build
```

8. Deploy only if verifiers pass.

