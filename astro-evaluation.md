# Is Astro the right stack for fifa2026squads.com?

**TL;DR — Yes, decisively. Astro + React islands is the closest thing to a
purpose-built stack for this product.**

The site is ~1,300 mostly-static SEO pages (48 teams × ~27 players + a few
hubs) with small interactive surfaces (squad filter, search, status legend),
needing fast time-to-first-byte, perfect crawlability, and the ability to
re-render specific pages when daily status overlays change. That's the
exact problem Astro is built for.

---

## What this product actually needs from a framework

| Requirement | Why it matters here |
|---|---|
| Zero-JS by default | Most pages need no client JS at all. Don't pay hydration tax on every Argentina visitor. |
| Per-page rebuild | Status overlay for one player changes → rebuild that team page, not 1,300. |
| SSG with optional ISR | Static for crawlers + CDN, on-demand revalidation when scanner pushes. |
| Built-in image optimisation | 1,300 Commons photos resized to 80px squares + responsive variants. |
| Content-collections / type-safe data layer | JSON files in `data/teams/` need to feed pages with type safety. |
| Per-page metadata (title, OG, JSON-LD) | SEO is the entire distribution thesis. |
| React (or similar) interop for islands | Search modal + filter want React; nothing else does. |
| Fast cold builds | 1,300 pages × frequent rebuilds. Build time directly affects update latency. |

## Astro score: 8 / 8

Astro literally lists each of these as a feature page. The notable ones:

- **Content collections** — `data/teams/*.json` becomes a typed collection
  with one config block; `getCollection('teams')` returns typed records.
  This is exactly the shape our scraper outputs.
- **Static + SSR per route** — most routes static, `/api/*` server-only.
  No need to bolt a separate API onto a SPA.
- **`<Image>` component** — automatic resizing, AVIF/WebP, lazy loading,
  CLS-safe. Saves writing this ourselves for player photos.
- **Islands architecture** — `<SquadFilter client:visible />` ships JS for
  the filter, nothing else. The default zero-JS posture is the right one
  for SEO and for mobile India audience.
- **`@astrojs/sitemap`, `@astrojs/rss`** — out-of-the-box. We need both.
- **MDX support** — for the `/about`, `/methodology`, `/api` doc pages.

## Alternatives, briefly

| Framework | Verdict | Reason |
|---|---|---|
| **Next.js (App Router)** | Workable but heavier than needed | All pages bundle React runtime even when not used. Better than Astro only if we needed a lot of server-rendered interactivity, which we don't. |
| **SvelteKit** | Good performance, smaller community | Loses the React island option for the MCP/admin pieces that benefit from React ecosystem. |
| **11ty / Hugo** | Fastest builds | Zero island story — building the squad filter / search means going SPA-shaped on top, which defeats the simplicity. |
| **Plain React SPA** | No | Catastrophic for SEO on a content-driven site with 1,300 unique pages. |
| **Remix** | Overkill | We have almost no mutations; remix's strength (forms + data loaders) doesn't earn its complexity here. |

## Concrete Astro structure (committed)

```
web/
├── astro.config.mjs              # site, integrations (react, tailwind, sitemap, mdx)
├── src/
│   ├── content/
│   │   ├── config.ts             # zod schemas for teams/, players/
│   │   └── (symlinked from ../../data, or imported via getCollection)
│   ├── components/
│   │   ├── PlayerCard.astro
│   │   ├── SquadTable.astro
│   │   ├── StatusBadge.astro
│   │   ├── GroupCard.astro
│   │   └── islands/
│   │       ├── SquadFilter.tsx          # React, client:visible
│   │       └── SearchModal.tsx          # React, client:idle
│   ├── layouts/
│   │   └── BaseLayout.astro       # head, fonts, OG defaults
│   ├── pages/
│   │   ├── index.astro
│   │   ├── teams/
│   │   │   ├── index.astro
│   │   │   └── [slug].astro       # 48 static routes via getStaticPaths
│   │   ├── players/
│   │   │   └── [slug].astro       # ~1300 static routes
│   │   ├── groups.astro
│   │   ├── schedule.astro
│   │   ├── rankings.astro
│   │   ├── api/
│   │   │   ├── index.astro        # docs
│   │   │   └── v1/
│   │   │       ├── teams.ts             # SSR
│   │   │       ├── teams/[slug].ts
│   │   │       └── players/[slug].ts
│   │   └── mcp.astro
│   └── lib/
│       ├── status.ts              # overlay merge logic
│       └── seo.ts                 # JSON-LD generators
├── public/
│   ├── favicon.svg
│   └── photos/                    # symlinked to ../../data/photos
└── package.json
```

## Hosting

**Vercel** — the Astro adapter is first-class, includes:
- Static for `/teams/*`, `/players/*`, etc.
- Serverless functions for `/api/v1/*`.
- ISR-style on-demand revalidation: scanner calls a revalidate webhook
  with a list of paths, only those rebuild. Keeps build cost flat.
- Edge cache + automatic image CDN for the photo set.

Cloudflare Pages is a viable secondary; pick Vercel because the existing
toolchain in this repo (per the project's broader setup) is already
Vercel-leaning.

## Performance budget targets

These are honest, achievable on Astro with a small island count:

| Metric | Target | Why achievable |
|---|---|---|
| LCP (squad page, mobile 4G) | <1.5s | Static HTML + AVIF photo + critical CSS inlined |
| CLS | <0.05 | Astro `<Image>` sets dimensions; no late-loading photo blocks |
| JS shipped (squad page) | <15 KB gz | Only the filter island; no router, no global state lib |
| Lighthouse SEO | 100 | Default Astro output is already there |
| TTFB (cached) | <100ms | Vercel edge cache |

## Risk

The single Astro-specific risk: **build time at scale.** ~1,300 pages,
each pulling JSON + generating OG image, can push a cold build to 60-90s.
Mitigations:
- Use Astro's incremental build (Astro 4.5+, on by default).
- ISR-style on-demand revalidation for status-only changes — don't rebuild
  everything, rebuild the affected slugs.
- Defer OG image generation to a runtime endpoint cached at the edge,
  rather than build-time.

Verdict: tractable. None of this is a blocker.

## Recommendation

Commit to Astro now. Set up the `web/` directory next, wire it to read
from `data/teams/*.json` via content collections, ship the team page
template first (it's 80% of the SEO value), then build outward to player
pages and the homepage.
