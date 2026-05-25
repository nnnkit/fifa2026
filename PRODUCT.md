# fifa2026squads.com — Product spec

**One-line:** A single-purpose, daily-refreshed reference site for every player in
every squad at the 2026 FIFA World Cup, with live availability status (injured /
doubtful / suspended / one-yellow-from-suspension) — plus a free read-only API
and MCP server so AI agents and other developers can consume the same data.

Use this document as the canonical "what we're building" brief. Feed it to design
tools, planning agents, contractors, or anyone needing context. Update it when
scope changes, not after.

---

## Why this exists

The big informational searches (`world cup 2026 schedule`, `fifa rankings`,
`world cup 2026 groups`) are owned by Wikipedia, ESPN, and FIFA.com and cannot
be won by a new domain in 3 weeks. The keyword research (see `research/`) shows
**~32k combined monthly volume across 24 mainstream nations' "{country} world
cup squad" queries**, low competition, with a wedge none of the giants exploit:
**freshness**. ESPN updates squad pages weekly; Wikipedia depends on
volunteers; FotMob/SofaScore have the data but bury injury context. Nobody
runs a tight "updated 08:00 IST today, here's exactly who can play" page
per team.

Add a free developer API + MCP server and the same dataset becomes valuable
to AI agents (no clean "current World Cup squads" MCP exists today), which
generates a second distribution surface (dev blogs, registries, HN) that
pure squad sites don't get.

## Audience

Three distinct user types — design for all three from a shared data layer:

1. **Casual fans** — Googled "{country} world cup squad", want a fast,
   correct, scannable squad with photos and live status. Mobile, low patience,
   maybe one click deeper.
2. **Serious followers / fantasy / betting context** — return daily during
   the tournament for "who's available for {country}'s next match". Care
   about cards, injuries, lineup hints. Will bookmark and share.
3. **Developers / AI agents** — want JSON, want it cached, want it documented.
   Will install the MCP server into Claude/Cursor/ChatGPT.

## Non-goals

- Live in-match scoring / minute-by-minute updates (ESPN, BBC own it; we
  cannot match infrastructure cost or speed).
- Long-form journalism, opinion, tactics breakdowns.
- Prediction-market betting / Polymarket integration (dropped; reintroduces
  legal/geo complexity for marginal value).
- Comprehensive history. We're a *tournament* site. Post-tournament the
  domain redirects to a generic /tournaments/2026 archive and we pivot to
  Euro 2028 / Copa América.

---

## Sitemap

```
/                                         # homepage — 12 groups, fixtures, top-8 teams
/groups                                   # 12 groups + qualified teams matrix
/schedule                                 # full fixture list, filterable
/rankings                                 # FIFA world ranking snapshot
/teams                                    # index of all 48 teams
/teams/{slug}                             # ← PRIMARY SEO PAGE × 48
/players/{slug}                           # player profile × ~1300
/api                                      # developer docs (free, no auth needed for reads)
/api/v1/teams                             # JSON
/api/v1/teams/{slug}
/api/v1/players/{slug}
/mcp                                      # how to install the MCP server
/about                                    # who runs this, methodology, source attribution
/sources                                  # Wikipedia/Wikidata/Commons attribution page (required for CC-BY-SA)
```

## Page-by-page spec

### `/teams/{slug}` — the engine

This is 80% of the SEO value. Build it first, polish it most.

**Above the fold (mobile-first):**
- Country name + flag emoji
- Group letter + group standings mini-table (3 other teams + their next fixture)
- "Updated <X> ago" timestamp — anchor of the entire freshness pitch
- Next fixture card: opponent, kickoff time in viewer's TZ, venue

**Squad table (the meat):**
- Default sort: position groups (GK → DF → MF → FW), then by shirt number
- Columns: photo (40px), shirt no., name, age, club, **status badge**, caps/goals
- Status badge — the one feature no competitor surfaces clearly:
    - 🟢 `available` (default)
    - 🟡 `one yellow from suspension`
    - 🟠 `doubtful` — recent injury/fitness concern, source linked
    - 🔴 `injured — out of next match`
    - ⛔ `suspended — next match`
- Each badge is a tooltip / popover that shows: status reason (1 sentence),
  source link, last-updated timestamp. Trust = sourced + dated.

**Below the squad:**
- Recent news strip (last 5 headlines that triggered status changes, dated)
- Coach card (name, age, tenure, photo)
- Group fixture list for this team's group

### `/players/{slug}` — long-tail SEO

Templated profile page; only top 10 stars need polish. Above the fold:
- Photo, full name, jersey number, position, current club, age, height
- Country + group + link back to team page
- Current status badge (same component as on team page)

Body sections:
- Career club history (timeline from Wikidata teams[] array)
- International caps + goals
- "Latest about {Player}" — last 5 headlines (same scanner output as team)
- External profile links (Wikipedia, Transfermarkt, FIFA)

### `/` — homepage

Not an SEO play (we can't win `world cup 2026`), but the obvious internal-link
hub. Layout:
- Hero: countdown to next match
- 12 group cards in a grid (each card → /groups#group-a)
- "Most-watched teams" — link grid to the top-8 team pages
- "Latest squad updates" — feed of recent status changes across all teams
- Footer: API + MCP CTAs

### `/api` + `/mcp`

Public, no auth for reads up to 100 req/day per IP. Above that, email for an
API key (this is the developer-list capture).

Endpoints (all GET, all JSON):
- `/api/v1/teams` — list of 48 teams
- `/api/v1/teams/{slug}` — team + squad + per-player status
- `/api/v1/players/{slug}` — single player record
- `/api/v1/updates` — recent status changes (for webhooks/RSS later)

MCP server: a thin wrapper exposing the same endpoints as MCP tools. One
install command for Claude/Cursor/ChatGPT users, listed on official MCP
registries.

---

## Data model

Two layers — what we ingest, and what we serve.

### Ingested (see `scripts/`)

Per team (`data/teams/{slug}.json`):
- country, slug, group, wikidata_qid, source, fetched_at, squad_size
- players[]: shirt_no, position_code, display_name, dob, age, caps, goals,
  current_club, height_cm, weight_kg, foot, positions[], citizenship[],
  place_of_birth, wikidata_qid, transfermarkt_id, fifa_player_id, photo{}

### Derived daily (the scanner — to be built)

Per player overlay (`data/status/{player-slug}.json`):
- status: enum
- reason: 1-sentence summary
- sources: [{url, headline, fetched_at}]
- last_updated, last_match_yellow_card: bool

The site reads team JSON + overlays status. Static regeneration runs nightly
plus any time the scanner pushes an update (webhook → trigger rebuild).

---

## Visual + interaction principles

Tight constraint set, no over-design:
- **One typeface** — Inter for everything, two weights (regular + semibold).
- **High contrast, no chrome** — white background, near-black text. Status
  badges are the *only* coloured surfaces above the fold. Reserve colour
  for signal.
- **Photos are 1:1 squares, 40–80px**, never larger than the player name.
- **No carousels, no modals, no full-page transitions.** Pages load fast
  and link to each other.
- **Timestamp everywhere** — "Updated 8 min ago" beside any non-static fact.
  This is the entire trust contract.
- **Mobile-first** — most traffic on phones during match days. Squad table
  collapses to cards <600px.
- **Dark mode** — system-preference only, no toggle UI.
- **Animations: none, except a 150ms fade on status badge changes** during
  live match days (subtle "this just updated" signal).

## SEO strategy

- Each `/teams/{slug}` page targets one head term: `{country} world cup
  squad`. Title: `{Country} World Cup 2026 Squad — fifa2026squads.com`.
  H1 same.
- Each `/players/{slug}` targets `{player name} world cup 2026`.
- One LD-JSON structured-data block per team page (`SportsTeam` + nested
  `Person` items for squad) and per player page (`Person` + `MemberOf`).
- Sitemap with priority weighting (teams 1.0, players 0.7, others 0.5).
- No JS required to render content above the fold (Astro static output).
- Open Graph image per team and per player (generate from photo + name at
  build time).
- Internal linking: every player card links team page, every team page
  links group page, every news strip item links source.

## Operational contract

The product *only works* if these run reliably:

- **Daily scanner** — every morning 06:00 IST: pull news for each player,
  classify, update status overlays, trigger rebuild. Must alert on failure
  within 30 min, not at end-of-day.
- **Weekly squad refresh** — every Monday 06:00 IST: re-run `fetch_all
  --force` to absorb Wikipedia updates (new caps/goals, transfers, etc.).
- **Status latency budget** — major injury news → reflected on site within
  2 hours of breaking. This is the differentiator vs Wikipedia's
  volunteer-paced updates.

If either of those slips, the "updated 8 min ago" claim becomes a lie and
the entire trust pitch collapses. Build monitoring on day 1.

---

## Implementation stack — committed

See `astro-evaluation.md` for the reasoning.

- **Astro** for the site (static-first, content-collections for teams/players,
  React islands for interactive bits like search + status filter).
- **React** for islands only — squad filter, search modal, status legend
  popover. No SPA, no router.
- **Tailwind** for styling.
- **TypeScript** end to end.
- **Vercel** for hosting (works seamlessly with Astro, edge cache + ISR
  via on-demand rebuilds for status updates).
- **Python** for the data pipeline (`scripts/` — already built).
- **MCP server in TypeScript** (`@modelcontextprotocol/sdk`).

## Open questions

- Final 26-man squad cutoff date (FIFA confirms ~10 days before kickoff) —
  set a calendar alert for re-fetch.
- Domain — `.com` available? Fallback `.app` / `.football`?
- Hosting tier — free Vercel hobby is fine for read traffic; API rate
  limits decide upgrade.
- Coach data — Wikipedia central article also has coach info; same
  pipeline can extract it. Worth a separate `/coaches/{slug}` page?
