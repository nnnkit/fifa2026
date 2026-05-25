#!/usr/bin/env bash
# Run codex for ONE team. Fresh process = fresh context.
#
# Usage:   ./scripts/codex-team.sh <slug>
# Example: ./scripts/codex-team.sh argentina
#
# Loop a group:
#   for s in $(jq -r '.[] | select(.group=="A") | .slug' data/teams.json); do
#     ./scripts/codex-team.sh "$s"
#   done
#
# Loop all teams with context reset and failure summary:
#   ./scripts/codex-teams.sh

set -euo pipefail
slug="${1:?usage: $0 <slug>}"
root="$(cd "$(dirname "$0")/.." && pwd)"
codex_bin="${CODEX_BIN:-codex}"
codex_sandbox="${CODEX_SANDBOX:-workspace-write}"
team_timeout_seconds="${TEAM_TIMEOUT_SECONDS:-1200}"
skip_preflight="${SKIP_CODEX_PREFLIGHT:-0}"
python_bin="${PYTHON_BIN:-}"

if [[ -z "$python_bin" ]]; then
  if [[ -x "$root/.venv/bin/python" ]]; then
    python_bin="$root/.venv/bin/python"
  else
    python_bin="python"
  fi
fi

if [[ "$skip_preflight" != "1" ]]; then
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
    print("network/DNS preflight failed; not starting Codex because the scraper cannot fetch required Wikimedia data:", file=sys.stderr)
    for item in bad:
        print(f"  - {item}", file=sys.stderr)
    raise SystemExit(2)
PY
fi

# Look up team metadata from teams.json
team_json="$(jq -e --arg s "$slug" '.[] | select(.slug==$s)' "$root/data/teams.json")" \
  || { echo "no such slug: $slug (see data/teams.json)" >&2; exit 2; }

country=$(jq -r '.country'      <<<"$team_json")
group=$(jq -r '.group'          <<<"$team_json")
qid=$(jq -r '.wikidata_qid'     <<<"$team_json")

# Render the prompt with this team's values substituted
prompt_file="${CODEX_PROMPT_FILE:-}"

# Per-team log, in case we want to look later
mkdir -p "$root/data/_codex-logs"
log="${CODEX_LOG:-$root/data/_codex-logs/${slug}.log}"
mkdir -p "$(dirname "$log")"
if [[ -z "$prompt_file" ]]; then
  prompt_file="$(dirname "$log")/${slug}.prompt.md"
fi
mkdir -p "$(dirname "$prompt_file")"

sed \
  -e "s|{COUNTRY}|${country}|g" \
  -e "s|{SLUG}|${slug}|g" \
  -e "s|{GROUP}|${group}|g" \
  -e "s|{QID}|${qid}|g" \
  "$root/scripts/codex_prompt.md" > "$prompt_file"

if [[ -x "$root/.venv/bin/python" ]]; then
  export VIRTUAL_ENV="$root/.venv"
  export PATH="$root/.venv/bin:$PATH"
fi

echo "▶ codex $slug ($country, group $group)  → prompt: $prompt_file  → log: $log"
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
    print(f"ERROR: timed out after {timeout_seconds} seconds", file=sys.stderr)
    raise SystemExit(124)

raise SystemExit(proc.returncode)
' "$team_timeout_seconds" "$codex_bin" --ask-for-approval never exec --ignore-user-config --ignore-rules --sandbox "$codex_sandbox" --cd "$root" --ephemeral - < "$prompt_file" 2>&1 | tee "$log"

# Run verify after codex exits — agent doesn't mark its own homework
echo "─── verify ───"
"$python_bin" -m scripts.verify "$slug" --strict
