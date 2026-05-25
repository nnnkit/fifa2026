# Codex group research prompt — dump one World Cup group

You are running inside the `fifa-2026/` directory.

Your job is to research **Group {GROUP}** and write one structured dump file:

```text
research/group-dumps/group-{GROUP}.json
```

This is a research dump, not the final verified site data. Do not write to
`data/teams/`, `data/players/`, or `data/photos/`. Do not edit code.

## Teams in this group

```json
{TEAMS_JSON}
```

## Allowed sources

Use only:

- `https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads`
- each team's tournament article from `data/teams.json`
- each team's national-team article from `data/teams.json`
- linked player Wikipedia pages
- Wikidata pages/API for linked players
- Wikimedia Commons for image metadata

Do not use Transfermarkt, FotMob, SofaScore, ESPN, social media, fan sites,
or commercial stats databases.

## Output contract

Write valid UTF-8 JSON to:

```text
research/group-dumps/group-{GROUP}.json
```

The top-level shape must be:

```json
{
  "group": "{GROUP}",
  "generated_at": "ISO-8601 timestamp",
  "source_policy": "wikipedia-wikidata-commons-only",
  "teams": [
    {
      "slug": "team-slug",
      "country": "Country",
      "wikidata_qid": "Q...",
      "source_urls": ["https://..."],
      "notes": [],
      "players": [
        {
          "display_name": "Player Name",
          "slug": "player-slug",
          "wikipedia_title": "Player article title or null",
          "wikipedia_url": "https://en.wikipedia.org/wiki/...",
          "wikidata_qid": "Q... or null",
          "position_code": "GK|DF|MF|FW|null",
          "date_of_birth": "YYYY-MM-DD or null",
          "current_club": "Club or null",
          "caps": 0,
          "goals": 0,
          "photo": {
            "filename": "Commons filename or null",
            "commons_url": "https://commons.wikimedia.org/wiki/File:...",
            "license": "license string or null"
          },
          "sources": ["https://..."],
          "confidence": "high|medium|low",
          "research_notes": []
        }
      ]
    }
  ],
  "blockers": []
}
```

## Research rules

- Prefer the central squads article table for the squad list.
- Use table DOB, caps, goals, position, and club when present.
- Use Wikidata only to attach QIDs, structured DOB, current club, and Commons
  image metadata where available.
- If a player has no article or QID, keep the row with nulls and a note. Do
  not invent identifiers.
- If photos are unavailable from Wikimedia/Commons, leave `photo` null or the
  missing subfields null. Do not spend more than a few minutes on photos.
- Cite source URLs per player. At minimum, include the team squad source and
  the player page/Wikidata page when used.
- Keep this bounded: research the four teams in this group, write the dump,
  print `DONE group-{GROUP} teams=4`, and exit.

## Validation

Before exiting, run:

```bash
.venv/bin/python -m scripts.validate_group_dump {GROUP}
```

If validation fails, fix the JSON shape and run it again. Do not try to
convert the dump into production `data/` files; that is the verifier/import
stage.
