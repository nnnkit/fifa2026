#!/usr/bin/env bash
# Run one Codex research agent for a whole World Cup group.

set -euo pipefail

group="${1:?usage: $0 <group-letter>}"
root="$(cd "$(dirname "$0")/.." && pwd)"
codex_bin="${CODEX_BIN:-codex}"
codex_sandbox="${CODEX_SANDBOX:-workspace-write}"
group_timeout_seconds="${GROUP_TIMEOUT_SECONDS:-3600}"
python_bin="${PYTHON_BIN:-}"

if [[ -z "$python_bin" ]]; then
  if [[ -x "$root/.venv/bin/python" ]]; then
    python_bin="$root/.venv/bin/python"
  else
    python_bin="python"
  fi
fi

group="$(printf '%s' "$group" | tr '[:lower:]' '[:upper:]')"
teams_json="$(jq -e --arg g "$group" '[.[] | select(.group==$g)]' "$root/data/teams.json")"
team_count="$(jq 'length' <<<"$teams_json")"
if [[ "$team_count" -eq 0 ]]; then
  echo "no teams found for group: $group" >&2
  exit 2
fi

run_id="$(date +%Y%m%d-%H%M%S)"
run_dir="$root/research/group-dumps/_logs/run-$run_id"
dump_file="$root/research/group-dumps/group-$group.json"
prompt_file="$run_dir/group-$group.prompt.md"
log="$run_dir/group-$group.log"
mkdir -p "$run_dir" "$root/research/group-dumps"

TEAMS_JSON="$teams_json" "$python_bin" - "$root/scripts/codex_group_prompt.md" "$prompt_file" "$group" <<'PY'
import os
import sys
from pathlib import Path

template = Path(sys.argv[1]).read_text()
out = Path(sys.argv[2])
group = sys.argv[3]
teams_json = os.environ["TEAMS_JSON"]
out.write_text(template.replace("{GROUP}", group).replace("{TEAMS_JSON}", teams_json))
PY

if [[ -x "$root/.venv/bin/python" ]]; then
  export VIRTUAL_ENV="$root/.venv"
  export PATH="$root/.venv/bin:$PATH"
fi

echo "▶ codex group $group → prompt: $prompt_file → dump: $dump_file → log: $log"
cd "$root"
"$python_bin" -c '
import os
import signal
import subprocess
import sys

timeout_seconds = int(sys.argv[1])
cmd = sys.argv[2:]
prompt = sys.stdin.buffer.read()

try:
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, start_new_session=True)
    proc.communicate(input=prompt, timeout=timeout_seconds)
except subprocess.TimeoutExpired:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    print(f"ERROR: group run timed out after {timeout_seconds} seconds", file=sys.stderr)
    raise SystemExit(124)

raise SystemExit(proc.returncode)
' "$group_timeout_seconds" "$codex_bin" --ask-for-approval never --search exec --ignore-user-config --ignore-rules --sandbox "$codex_sandbox" --cd "$root" --ephemeral - < "$prompt_file" 2>&1 | tee "$log"

"$python_bin" -m scripts.validate_group_dump "$group"
