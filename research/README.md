# Keyword research — fifa2026squads.com

Run date: **2026-05-24** · Source: DataForSEO Google Ads search-volume API · Cost: **$0.15** (2 batched calls × $0.075).

## Method

- 189 candidate keywords compiled from intuition (no Labs discovery call).
- Single batched `keywords_data/google_ads/search_volume/live` call per locale.
- Two locales: US (`location_code: 2840`) as global-English proxy, India (`2356`) as secondary market — Indian football audience is meaningful for this project's focus.
- Language: `en` for both.
- Raw JSON in `raw/`. Re-running should read from cache, not re-call the API.

## Volume by intent bucket (combined US + IN per month)

| Bucket | # kw | Combined mo. volume | SEO winnable? | Action |
|---|---:|---:|---|---|
| schedule_venue | 6 | 95,380 | No — Wikipedia/FIFA own these | Cover lightly, internal-link only |
| rankings | 5 | 78,420 | Maybe long-term, no in 3 weeks | Single `/rankings` page, dynamic |
| groups | 2 | 55,700 | No — same SERP giants | Single `/groups` page, dynamic |
| **team_squad** | **120** | **31,720** | **Yes — programmatic, low DA needed** | **Primary play: 24 team pages** |
| head_squad | 34 | 18,530 | Partial — homepage targets | Homepage H1 + meta |
| star_player | 10 | 2,760 | Yes — long tail | Build top-10 star pages |
| news | 2 | 1,530 | No — news sites dominate | Skip |
| api | 3 | 900 | Yes for niche dev audience | `/api` landing + MCP listing |
| discipline | 4 | 60 | No volume | Product feature only |
| injury | 3 | 40 | No volume | Product feature only |

## Top 30 keywords by combined volume

| Keyword | US | IN | Combined | CPC |
|---|---:|---:|---:|---:|
| world cup 2026 schedule | 60,500 | 27,100 | 87,600 | $1.12 |
| fifa rankings | 40,500 | 18,100 | 58,600 | $8.32 |
| world cup 2026 groups | 40,500 | 9,900 | 50,400 | $5.76 |
| fifa world ranking | 14,800 | 2,400 | 17,200 | — |
| world cup squad 2026 | 70 | 6,600 | 6,670 | — |
| brazil world cup squad | 2,900 | 2,900 | 5,800 | $5.22 |
| fifa 2026 groups | 2,900 | 2,400 | 5,300 | $6.72 |
| world cup 2026 teams | 3,600 | 1,000 | 4,600 | $1.17 |
| england world cup squad | 2,900 | 1,300 | 4,200 | $2.06 |
| world cup 2026 fixtures | 590 | 2,900 | 3,490 | $4.66 |
| france world cup squad | 2,400 | 880 | 3,280 | $7.06 |
| world cup squads | 260 | 2,900 | 3,160 | — |
| world cup 2026 venues | 2,400 | 720 | 3,120 | $0.54 |
| portugal world cup squad | 1,600 | 880 | 2,480 | $2.77 |
| spain world cup squad | 1,900 | 480 | 2,380 | — |
| fifa team rankings | 1,000 | 1,300 | 2,300 | — |
| messi world cup 2026 | 1,600 | 320 | 1,920 | $1.70 |
| germany world cup squad | 1,300 | 320 | 1,620 | $4.01 |
| argentina world cup squad | 880 | 590 | 1,470 | $0.54 |
| australia world cup squad | 90 | 1,000 | 1,090 | — |
| netherlands world cup squad | 880 | 110 | 990 | $4.83 |
| world cup 2026 team list | 390 | 590 | 980 | $2.74 |
| world cup 2026 news | 720 | 110 | 830 | — |
| 2026 world cup squad | 20 | 720 | 740 | — |
| fifa world cup 2026 news | 590 | 110 | 700 | $0.86 |
| brazil world cup 2026 squad | 170 | 480 | 650 | — |
| mexico world cup squad | 590 | 30 | 620 | $2.59 |
| world cup 2026 squad | 10 | 590 | 600 | — |
| fifa 2026 teams | 320 | 260 | 580 | $10.56 |
| brazil squad 2026 | 210 | 320 | 530 | — |

Full ranked list in `keyword-digest.json` / `keywords.csv`.

## Decisions

1. **Per-team squad pages are the primary SEO play.** 24 templated pages, 30k+ combined monthly volume, low competition, programmatic.
2. **Top-8 priority pages** (build first, polish most): brazil, england, france, spain, portugal, germany, argentina, netherlands.
3. **Star pages** (10 of them, near-zero marginal effort): messi, cristiano-ronaldo, mbappe, haaland, bellingham, vinicius-jr, harry-kane, lamine-yamal, musiala, bukayo-saka.
4. **India matters** — typically 20–50% additional volume on top of US numbers. Already aligned with the broader project focus.
5. **Drop disciplinary SEO pages** — yellow card / suspension terms total <100/mo. Keep as a product feature on each team page (the `one yellow from suspension` badge).
6. **API/MCP angle is small for SEO** (~900/mo combined) but valuable for a different distribution channel: AI-agent registries, dev blogs, HN. Treat as side surface, not SEO target.

## Cache notes

- Volume data is stable month-to-month; do not re-call DataForSEO unless materially expanding the keyword set or the seasonality shifts (e.g., post-tournament).
- If expanding: add 24 missing teams (Ghana, Senegal, Tunisia, Iran, Saudi Arabia, Qatar, …) — same 4 patterns per team, fits in one more batched call (~$0.075).
