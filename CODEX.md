# Running squads through Codex (YOLO)

One thin wrapper, then plain `codex`. No Python orchestrator.

## Setup

```bash
npm install -g @openai/codex
export OPENAI_API_KEY=sk-...
codex --help                              # confirm `exec` + `--sandbox`
brew install jq                           # used by the wrapper
```

Make sure `data/teams.json` exists:

```bash
cd fifa-2026 && source .venv/bin/activate
python -m scripts.fetch_teams             # 48 teams
```

## Run it

## Group research dump workflow

This is now the safer path when the direct per-team Codex flow gets too
slow. One agent researches a whole group and writes a raw dump. A later
verifier/import stage can turn that dump into production data.

**One group dump:**

```bash
./scripts/codex-group.sh A
```

**All groups, one after another:**

```bash
./scripts/codex-groups.sh
```

**Resume from a group or skip completed dumps:**

```bash
./scripts/codex-groups.sh --from D
./scripts/codex-groups.sh --missing-only
```

Outputs:

```text
research/group-dumps/group-A.json
research/group-dumps/_logs/run-*/group-A.prompt.md
research/group-dumps/_logs/run-*/group-A.log
```

Validate a dump without running Codex:

```bash
.venv/bin/python -m scripts.validate_group_dump A
```

Recommended sequence:

```bash
./scripts/codex-group.sh A
.venv/bin/python -m scripts.validate_group_dump A
# later: run a separate verifier/importer over research/group-dumps/group-A.json
```

The group dump step must not edit `data/teams`, `data/players`, or
`data/photos`. It only creates research JSON.

## Per-team Codex workflow

**One team** (smoke test first):

```bash
./scripts/codex-team.sh argentina
```

**One group of four:**

```bash
for s in $(jq -r '.[] | select(.group=="A") | .slug' data/teams.json); do
  ./scripts/codex-team.sh "$s"
done
```

**All 48, sequential:**

```bash
./scripts/codex-teams.sh
```

This is the preferred full-run command. It runs one team, lets that
`codex exec` process exit, then starts a new `codex exec` process for the
next team. That fresh subprocess is the context reset.

It writes one log per team under `data/_codex-logs/run-*/` plus a
`summary.tsv`. If a team fails, the runner records the failure and keeps
going unless you pass `--stop-on-fail`.

**Group-by-group with a pause:**

```bash
for g in A B C D E F G H I J K L; do
  ./scripts/codex-teams.sh --group "$g"
  echo "── finished group $g ──"
done
```

**Resume from a team:**

```bash
./scripts/codex-teams.sh --from argentina
```

**Only run teams without generated data:**

```bash
./scripts/codex-teams.sh --missing-only
```

**Preview without spending tokens:**

```bash
./scripts/codex-teams.sh --group A --dry-run
```

**Set a per-team timeout:**

```bash
./scripts/codex-teams.sh --timeout 1800
```

The default timeout is 1200 seconds. A timeout is recorded as a failed
team, and the batch runner moves to the next team.

Each `codex` invocation is its own subprocess — fresh context per team by
construction. No state leaks between teams.

## What the wrapper does

`scripts/codex-team.sh` is the one-team worker:

1. Reads the team's country / group / Wikidata QID from `data/teams.json`.
2. Substitutes them into `scripts/codex_prompt.md` and writes the
   rendered Markdown to `data/_codex-logs/run-*/{slug}.prompt.md`.
3. Runs `codex --ask-for-approval never exec --sandbox workspace-write -`,
   reading that Markdown from stdin and tee'ing the
   transcript to `data/_codex-logs/{slug}.log`.
4. Puts `.venv/bin` first in `PATH`, so agent shell commands use the
   repo dependencies.
5. Runs a preflight for Python dependencies and Wikimedia DNS before
   spending Codex tokens.
6. After codex exits, runs `.venv/bin/python -m scripts.verify {slug} --strict`
   itself — the agent doesn't get to mark its own homework. Non-zero
   exit from verify will short-circuit any outer loop (`set -euo
   pipefail`), so you'll notice immediately.

`scripts/codex-teams.sh` is the batch runner:

1. Selects teams from `data/teams.json` (`--all`, `--group A`, explicit
   slugs, or `--from slug`).
2. Calls `scripts/codex-team.sh` once per team.
3. Uses a new `codex exec` process per team, which clears context by
   construction.
4. Continues after failures and exits non-zero at the end if any team
   failed.

## The prompt

`scripts/codex_prompt.md` tells the agent:

- Which team it's working on.
- That `scripts/fetch_squad.py` already does 80–95% of the work — run
  that first, then patch the gaps.
- Hard source rules: Wikipedia / Wikidata / Commons only. No
  Transfermarkt / FotMob / SofaScore (ToS).
- Allowlisted edit paths: `data/teams/{slug}.json`,
  `data/players/*.json`, `data/photos/`, and `scripts/_squads.py` if
  parser fix is needed.
- Success criteria measured by `scripts.verify --strict`.

## Recommended pattern

Don't lead with Codex. The free deterministic pipeline gets ~80% of
teams across all thresholds:

```bash
python -m scripts.fetch_all                # free, ~35 min
python -m scripts.verify --strict 2>&1 | tee /tmp/verify.log
# Then use codex only on the teams that fell short:
./scripts/codex-team.sh england
./scripts/codex-team.sh south-korea
```

Keeps the agent budget proportional to actual marginal work, not a flat
tax on every team.

## If something looks wrong

- **`codex exec` not recognized** — older versions use just `codex
  "prompt"` without the `exec` subcommand. Edit the wrapper.
- **`--sandbox workspace-write` rejected** — your Codex CLI is older.
  Check `codex exec --help` and update the wrapper to match your local
  CLI.
- **Wrong model** — append `--model gpt-5-codex` (or whatever you have
  access to) inside the wrapper.
- **Agent edits files it shouldn't** — the prompt's allowlist is
  advisory, not enforced. For hard guarantees, run inside Docker or
  Vercel Sandbox.

## Files

```
scripts/
├── codex-team.sh        ← the ~25-line wrapper
├── codex-teams.sh       ← sequential all/group/resume runner
├── codex-group.sh       ← one research agent per World Cup group
├── codex-groups.sh      ← sequential all-group research runner
├── codex_group_prompt.md
└── codex_prompt.md      ← per-team prompt template
data/_codex-logs/        ← one transcript per team (gitignored)
research/group-dumps/    ← raw group research dumps
```
