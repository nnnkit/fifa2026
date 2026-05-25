#!/usr/bin/env bash
# Run one fresh Codex research agent per World Cup group, sequentially.

set -uo pipefail
trap 'echo; echo "interrupted"; exit 130' INT TERM

usage() {
  cat <<'EOF'
Usage:
  ./scripts/codex-groups.sh              # all groups A-L
  ./scripts/codex-groups.sh A B C        # selected groups
  ./scripts/codex-groups.sh --from D     # D through L

Options:
  --from <group>      Start at this group in the selected list
  --missing-only      Skip groups with research/group-dumps/group-<G>.json
  --timeout <secs>    Per-group Codex timeout, default 3600
  --stop-on-fail      Stop after the first failed group
  --dry-run           Print selected groups without running Codex
  -h, --help          Show this help
EOF
}

root="$(cd "$(dirname "$0")/.." && pwd)"
from_group=""
missing_only=0
stop_on_fail=0
dry_run=0
group_timeout_seconds="${GROUP_TIMEOUT_SECONDS:-3600}"
groups=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from)
      from_group="$(printf '%s' "${2:?missing group after --from}" | tr '[:lower:]' '[:upper:]')"
      shift 2
      ;;
    --missing-only)
      missing_only=1
      shift
      ;;
    --timeout)
      group_timeout_seconds="${2:?missing seconds after --timeout}"
      shift 2
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
      groups+=("$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')")
      shift
      ;;
  esac
done

if [[ ${#groups[@]} -eq 0 ]]; then
  while IFS= read -r group; do
    groups+=("$group")
  done < <(jq -r '[.[].group] | unique | .[]' "$root/data/teams.json")
fi

if [[ -n "$from_group" ]]; then
  filtered=()
  found=0
  for group in "${groups[@]}"; do
    if [[ "$group" == "$from_group" ]]; then
      found=1
    fi
    if [[ "$found" -eq 1 ]]; then
      filtered+=("$group")
    fi
  done
  if [[ "$found" -eq 0 ]]; then
    echo "--from group not found in selected groups: $from_group" >&2
    exit 2
  fi
  groups=("${filtered[@]}")
fi

if [[ "$missing_only" -eq 1 ]]; then
  missing=()
  for group in "${groups[@]}"; do
    if [[ ! -f "$root/research/group-dumps/group-$group.json" ]]; then
      missing+=("$group")
    fi
  done
  groups=("${missing[@]}")
fi

total=${#groups[@]}
if [[ "$total" -eq 0 ]]; then
  echo "Selected 0 group(s). Nothing to do."
  exit 0
fi

echo "Selected $total group(s)."
if [[ "$dry_run" -eq 1 ]]; then
  printf '%s\n' "${groups[@]}"
  exit 0
fi

run_id="$(date +%Y%m%d-%H%M%S)"
run_dir="$root/research/group-dumps/_logs/batch-$run_id"
summary="$run_dir/summary.tsv"
mkdir -p "$run_dir"
printf "group\tstatus\texit_code\tstarted_at\tfinished_at\tdump\n" > "$summary"

ok=0
failed=0
i=0
for group in "${groups[@]}"; do
  i=$((i + 1))
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  dump="$root/research/group-dumps/group-$group.json"

  echo
  echo "[$i/$total] starting group $group"
  GROUP_TIMEOUT_SECONDS="$group_timeout_seconds" "$root/scripts/codex-group.sh" "$group"
  code=$?
  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  if [[ "$code" -eq 130 || "$code" -eq 143 ]]; then
    echo "interrupted while running group $group"
    exit "$code"
  fi

  if [[ "$code" -eq 0 ]]; then
    ok=$((ok + 1))
    status="ok"
    echo "[$i/$total] ok group $group"
  else
    failed=$((failed + 1))
    status="failed"
    echo "[$i/$total] failed group $group (exit $code); continuing"
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\n" "$group" "$status" "$code" "$started_at" "$finished_at" "$dump" >> "$summary"

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
