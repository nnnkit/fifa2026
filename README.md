# fifa-2026

Research + product notes for **fifa2026squads.com** — a daily-updated squad reference site for the 2026 FIFA World Cup (USA / Canada / Mexico, June–July 2026).

Created: 2026-05-24 — kickoff is ~3 weeks out, squad submission deadline imminent.

## What this folder contains

```
fifa-2026/
├── README.md             ← this file (orientation + quick start)
├── PRODUCT.md            ← product spec — feed to designers/agents
├── SCRAPING.md           ← data sources, learnings, periodic-refresh plan
├── REFETCHING.md         ← matchday refetch plan for lineups/injuries/status
├── astro-evaluation.md   ← stack decision: Astro + React islands
├── research/             ← keyword research (DataForSEO output)
├── scripts/              ← Python data pipeline (Wikipedia + Wikidata + Commons)
├── data/                 ← scraper output: teams.json, teams/, players/, photos/
└── web/                  ← Astro site reading from ../data/
```

## Quick start — get everything running

```bash
# 1. data pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
python -m scripts.fetch_teams          # → data/teams.json (48 teams)
python -m scripts.fetch_all            # → data/teams/*.json + photos (~35 min)
python -m scripts.verify               # coverage report
python -m scripts.seed_status          # → data/status/*.json baseline statuses
python -m scripts.verify_status        # status overlay coverage report

# 2. site
cd web
npm install
ln -s ../../data/photos public/photos  # serve scraped photos at /photos/*
npm run dev
```

For deeper docs: **`SCRAPING.md`** is the data-ingestion handbook.
**`REFETCHING.md`** is the low-token matchday refetch plan for lineups,
injuries, suspensions, and post-match updates. **`PRODUCT.md`** is the product
spec. **`astro-evaluation.md`** is the stack-choice reasoning.

## Product scope (as of 2026-05-24)

**In scope:**
- 48 team pages — squad list, jersey numbers, club, age, position
- Daily-refreshed status per player: `available` / `injured` / `doubtful` / `suspended next match` / `one yellow from suspension`
- Group + schedule + fixtures pages
- Star-player pages (Messi, Ronaldo, Mbappé, Haaland, Bellingham, Yamal, …)
- Public read API + MCP server for AI agents (`/api/v1/squads/{team}`, `/api/v1/players/{id}`)

**Out of scope (decided):**
- Polymarket / prediction-market integration — dropped to keep scope tight
- Suspension/yellow-card landing pages — almost no SEO volume (~60/mo combined); keep as a product feature, not a page

## Why this can work in 3 weeks

The big informational terms (`world cup 2026 schedule` 87k/mo, `fifa rankings` 58k/mo, `world cup 2026 groups` 50k/mo) are owned by Wikipedia / ESPN / FIFA.com and unrankable for a new domain. **The wedge is the long tail of per-team squad pages** — 24 well-known nations × ~500–3000 searches/mo each, total ~32k combined monthly with low competition and a freshness angle nobody else exploits well.

Plus a second distribution surface: **MCP server for AI agents**. No clean "current World Cup squads + injuries" MCP exists; listing on MCP registries is a different funnel from Google SEO.

## Roadmap snapshot

1. Scrape Wikipedia squad pages on announcement → seed database
2. Build 4 page templates: `/` `/teams/{slug}` `/players/{slug}` `/api`
3. Daily cron: pull headlines for each player, classify with LLM → status
4. Ship MCP server + `/api` docs
5. SEO push on top-8 squad pages (brazil, england, france, spain, portugal, germany, argentina, netherlands) + 2 star pages (messi, ronaldo)

See `research/README.md` for the keyword data backing these picks.
