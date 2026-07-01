#!/usr/bin/env bash
#
# run-audit.sh — LLM-driven, read-only security audits.
#
# Each audit "module" is a prompt file in ../audits/<name>.md; it's prepended
# with audits/_preamble.md and run through the Claude CLI in headless (-p) mode
# with a read-only tool allowlist. Reports land in audits/reports/<name>.md.
#
# Usage:
#   scripts/run-audit.sh                 # run every module
#   scripts/run-audit.sh auth llm        # run specific modules
#   scripts/run-audit.sh --list          # list module names
#
# Env knobs:
#   AUDIT_MODEL=opus     model (default: sonnet — override with opus for depth)
#   AUDIT_PARALLEL=1     run modules concurrently (default: sequential)
#   AUDIT_MAX_BUDGET=5   per-module USD cap passed to the CLI (default: none)
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT_DIR="$REPO_ROOT/audits"
REPORT_DIR="$AUDIT_DIR/reports"
PREAMBLE="$AUDIT_DIR/_preamble.md"

MODEL="${AUDIT_MODEL:-sonnet}"
PARALLEL="${AUDIT_PARALLEL:-0}"
BUDGET="${AUDIT_MAX_BUDGET:-}"

# Read-only tool allowlist (comma-separated; tolerates the space in "git diff").
ALLOWED='Read,Grep,Glob,Bash(grep:*),Bash(rg:*),Bash(find:*),Bash(ls:*),Bash(cat:*),Bash(sed:*),Bash(head:*),Bash(tail:*),Bash(wc:*),Bash(git diff:*),Bash(git log:*),Bash(git show:*),Bash(git status:*),Bash(bun audit:*),Bash(pip-audit:*),Bash(poetry run pip-audit:*)'
DISALLOWED='Edit,Write,NotebookEdit,MultiEdit'

list_modules() {
  find "$AUDIT_DIR" -maxdepth 1 -name '*.md' ! -name '_*.md' ! -name 'README.md' \
    -exec basename {} .md \; | sort
}

case "${1:-}" in
  -l | --list)
    list_modules
    exit 0
    ;;
  -h | --help)
    sed -n '3,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
esac

command -v claude >/dev/null 2>&1 || {
  echo "error: the 'claude' CLI is not on PATH — install Claude Code to run audits." >&2
  exit 127
}

if [[ $# -gt 0 ]]; then
  MODULES=("$@")
else
  mapfile -t MODULES < <(list_modules)
fi

mkdir -p "$REPORT_DIR"

run_one() {
  local m="$1"
  local prompt_file="$AUDIT_DIR/$m.md"
  if [[ ! -f "$prompt_file" ]]; then
    echo "error: unknown audit module '$m' (try: scripts/run-audit.sh --list)" >&2
    return 2
  fi
  local report="$REPORT_DIR/$m.md"
  local errfile="$REPORT_DIR/$m.err"
  local tmp="$report.tmp"

  local args=(-p --model "$MODEL" --output-format text --no-session-persistence
    --permission-mode default --allowedTools "$ALLOWED" --disallowedTools "$DISALLOWED")
  [[ -n "$BUDGET" ]] && args+=(--max-budget-usd "$BUDGET")

  # `env -u CLAUDECODE` lets the headless one-shot run even when this script is
  # launched from inside a Claude Code session (the nested-session guard); -p +
  # --no-session-persistence keeps it isolated from any outer session.
  echo "▶ audit: $m (model=$MODEL)"
  if cat "$PREAMBLE" "$prompt_file" \
    | (cd "$REPO_ROOT" && env -u CLAUDECODE claude "${args[@]}") >"$tmp" 2>"$errfile"; then
    {
      echo "# Security audit: $m — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
      echo
      cat "$tmp"
    } >"$report"
    rm -f "$tmp" "$errfile"
    echo "  ✓ $m → audits/reports/$m.md"
    grep -m1 -i '^VERDICT' "$report" | sed 's/^/    /' || true
    return 0
  fi
  rm -f "$tmp"
  echo "  ✗ $m failed — see audits/reports/$m.err" >&2
  return 1
}

fail=0
if [[ "$PARALLEL" == "1" ]]; then
  pids=()
  for m in "${MODULES[@]}"; do
    run_one "$m" &
    pids+=("$!")
  done
  for pid in "${pids[@]}"; do wait "$pid" || fail=1; done
else
  for m in "${MODULES[@]}"; do run_one "$m" || fail=1; done
fi

echo
echo "── audit summary ──"
for m in "${MODULES[@]}"; do
  r="$REPORT_DIR/$m.md"
  if [[ -f "$r" ]]; then
    printf '  %-11s %s\n' "$m" "$(grep -m1 -i '^VERDICT' "$r" 2>/dev/null || echo '(report written)')"
  else
    printf '  %-11s %s\n' "$m" "FAILED"
  fi
done

exit "$fail"
