#!/usr/bin/env bash
# Run Codex once per team, sequentially.
#
# Each team is handled by scripts/codex-team.sh, which starts a fresh
# `codex exec` process. That process boundary is the context reset.

set -uo pipefail
trap 'echo; echo "interrupted"; exit 130' INT TERM

usage() {
  cat <<'EOF'
Usage:
  ./scripts/codex-teams.sh                 # all teams, sequential
  ./scripts/codex-teams.sh --group A       # one group
  ./scripts/codex-teams.sh --from argentina
  ./scripts/codex-teams.sh --missing-only
  ./scripts/codex-teams.sh argentina brazil

Options:
  --all             Run every team from data/teams.json (default)
  --group <group>   Run teams from one group only
  --from <slug>     Start at this slug within the selected list
  --missing-only    Skip teams that already have data/teams/<slug>.json
  --timeout <secs>  Per-team Codex timeout, default 1200
  --skip-preflight  Do not check Python deps / Wikimedia DNS before running
  --stop-on-fail    Stop after the first failed team
  --dry-run         Print the selected teams without running Codex
  -h, --help        Show this help
EOF
}

root="$(cd "$(dirname "$0")/.." && pwd)"
group=""
from_slug=""
stop_on_fail=0
dry_run=0
missing_only=0
skip_preflight="${SKIP_CODEX_PREFLIGHT:-0}"
team_timeout_seconds="${TEAM_TIMEOUT_SECONDS:-1200}"
slugs=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      shift
      ;;
    --group)
      group="${2:?missing group after --group}"
      shift 2
      ;;
    --from)
      from_slug="${2:?missing slug after --from}"
      shift 2
      ;;
    --timeout)
      team_timeout_seconds="${2:?missing seconds after --timeout}"
      shift 2
      ;;
    --missing-only)
      missing_only=1
      shift
      ;;
    --skip-preflight)
      skip_preflight=1
      shift
      ;;
    --stop-on-fail)
      stop_on_fail=1
      shift
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      slugs+=("$1")
      shift
      ;;
  esac
done

if [[ ${#slugs[@]} -eq 0 ]]; then
  if [[ -n "$group" ]]; then
    while IFS= read -r slug; do
      slugs+=("$slug")
    done < <(jq -r --arg g "$group" '.[] | select(.group==$g) | .slug' "$root/data/teams.json")
  else
    while IFS= read -r slug; do
      slugs+=("$slug")
    done < <(jq -r '.[].slug' "$root/data/teams.json")
  fi
fi

if [[ ${#slugs[@]} -eq 0 ]]; then
  echo "no teams selected" >&2
  exit 2
fi

if [[ -n "$from_slug" ]]; then
  filtered=()
  found=0
  for slug in "${slugs[@]}"; do
    if [[ "$slug" == "$from_slug" ]]; then
      found=1
    fi
    if [[ "$found" -eq 1 ]]; then
      filtered+=("$slug")
    fi
  done
  if [[ "$found" -eq 0 ]]; then
    echo "--from slug not found in selected teams: $from_slug" >&2
    exit 2
  fi
  slugs=("${filtered[@]}")
fi

if [[ "$missing_only" -eq 1 ]]; then
  missing=()
  for slug in "${slugs[@]}"; do
    if [[ ! -f "$root/data/teams/$slug.json" ]]; then
      missing+=("$slug")
    fi
  done
  slugs=("${missing[@]}")
fi

total=${#slugs[@]}
ok=0
failed=0

if [[ "$total" -eq 0 ]]; then
  echo "Selected 0 team(s). Nothing to do."
  exit 0
fi

echo "Selected $total team(s)."
if [[ "$dry_run" -eq 1 ]]; then
  printf '%s\n' "${slugs[@]}"
  exit 0
fi

if [[ "$skip_preflight" != "1" ]]; then
  python_bin="${PYTHON_BIN:-}"
  if [[ -z "$python_bin" ]]; then
    if [[ -x "$root/.venv/bin/python" ]]; then
      python_bin="$root/.venv/bin/python"
    else
      python_bin="python"
    fi
  fi
  "$python_bin" - <<'PY'
import importlib.util
import socket
import sys

missing = [name for name in ("bs4", "requests") if importlib.util.find_spec(name) is None]
if missing:
    print(f"missing Python dependencies in selected interpreter: {', '.join(missing)}", file=sys.stderr)
    raise SystemExit(2)

hosts = ("en.wikipedia.org", "www.wikidata.org", "commons.wikimedia.org", "upload.wikimedia.org")
bad = []
for host in hosts:
    try:
        socket.getaddrinfo(host, 443)
    except OSError as exc:
        bad.append(f"{host}: {exc}")

if bad:
    print("network/DNS preflight failed; not starting Codex batch:", file=sys.stderr)
    for item in bad:
        print(f"  - {item}", file=sys.stderr)
    raise SystemExit(2)
PY
fi

run_id="$(date +%Y%m%d-%H%M%S)"
run_dir="$root/data/_codex-logs/run-$run_id"
summary="$run_dir/summary.tsv"
mkdir -p "$run_dir"
printf "slug\tstatus\texit_code\tstarted_at\tfinished_at\tprompt\tlog\n" > "$summary"

echo "Logs: $run_dir"

i=0
for slug in "${slugs[@]}"; do
  i=$((i + 1))
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  prompt_file="$run_dir/$slug.prompt.md"
  log="$run_dir/$slug.log"

  echo
  echo "[$i/$total] starting $slug"
  CODEX_PROMPT_FILE="$prompt_file" CODEX_LOG="$log" TEAM_TIMEOUT_SECONDS="$team_timeout_seconds" SKIP_CODEX_PREFLIGHT=1 "$root/scripts/codex-team.sh" "$slug"
  code=$?
  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  if [[ "$code" -eq 130 || "$code" -eq 143 ]]; then
    echo "interrupted while running $slug"
    exit "$code"
  fi

  if [[ "$code" -eq 0 ]]; then
    ok=$((ok + 1))
    status="ok"
    echo "[$i/$total] ok $slug"
  else
    failed=$((failed + 1))
    status="failed"
    echo "[$i/$total] failed $slug (exit $code); continuing"
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$slug" "$status" "$code" "$started_at" "$finished_at" "$prompt_file" "$log" >> "$summary"

  if [[ "$code" -ne 0 && "$stop_on_fail" -eq 1 ]]; then
    echo "stopping after first failure because --stop-on-fail was set"
    break
  fi
done

echo
echo "Done. ok=$ok failed=$failed summary=$summary"

if [[ "$failed" -eq 0 ]]; then
  exit 0
fi
exit 1
