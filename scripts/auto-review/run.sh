#!/usr/bin/env bash
# Autonomous HA review: run a headless Claude over a period of HA data, then open a PR.
#
#   run.sh daily|weekly|monthly      (DRY_RUN=1 skips push + PR)
#
# Guarantees:
#  - Never touches the HA box (no ssh, no checkout there). HA is read through ha_ro.py only.
#  - Agent works in a throwaway git worktree off origin/main, never on main or your checkout.
#  - Agent cannot push or open PRs; this script does it from the agent's commits.
set -euo pipefail

PERIOD="${1:?usage: run.sh daily|weekly|monthly}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
STATE="$HOME/.cache/ha-auto-review"
LOGDIR="$HOME/Library/Logs/ha-auto-review"
STAMP="$(date +%Y%m%d-%H%M)"
BRANCH="auto/${PERIOD}-$(date +%Y%m%d)"
WT="$STATE/wt/${PERIOD}-${STAMP}"
OUT="$STATE/out/${PERIOD}-${STAMP}"
LOCK="$STATE/lock"
mkdir -p "$STATE/wt" "$OUT" "$LOGDIR"

case "$PERIOD" in
  daily)   WINDOW="24 hours"; MODEL="${AUTO_REVIEW_MODEL:-sonnet}"; BUDGET=5  ;;
  weekly)  WINDOW="7 days";   MODEL="${AUTO_REVIEW_MODEL:-opus}";   BUDGET=12 ;;
  monthly) WINDOW="30 days";  MODEL="${AUTO_REVIEW_MODEL:-opus}";   BUDGET=20 ;;
  *) echo "bad period: $PERIOD" >&2; exit 2 ;;
esac

log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*"; }
notify() { osascript -e "display notification \"$2\" with title \"$1\"" 2>/dev/null || true; }
exec >>"$LOGDIR/${PERIOD}.log" 2>&1
log "=== start $PERIOD (window $WINDOW, model $MODEL) ==="

# Env (HA_URL, API_ACCESS_TOKEN, ...) from the main checkout; launchd has no direnv.
cd "$REPO"
if [ -f .env ]; then set -a; . ./.env; set +a; fi
export PATH="/opt/homebrew/bin:$HOME/.local/bin:/usr/local/bin:$PATH"

# Preflight: HA and GitHub must both be reachable, else the run is wasted (11-02..11-04 silently
# produced nothing). Poll up to ~3h (Mac may have just woken / be off the LAN), then alert loudly.
preflight_ok() {
  curl -fsS -m 10 -o /dev/null -H "Authorization: Bearer ${API_ACCESS_TOKEN:-}" \
    "${HA_URL:-http://homeassistant.local:8123}/api/" && git ls-remote -q --exit-code origin HEAD >/dev/null
}
for i in $(seq 36); do
  preflight_ok && break
  [ "$i" = 1 ] && log "preflight failed (HA or GitHub unreachable); retrying every 5 min"
  sleep 300
done
if ! preflight_ok; then
  log "preflight still failing after ~3h; giving up"
  notify "HA auto-$PERIOD review FAILED" "HA or GitHub unreachable for 3h. Check network / Local Network permission."
  exit 1
fi

# One run at a time (weekly/monthly can coincide with daily); wait up to 2h.
for _ in $(seq 120); do mkdir "$LOCK" 2>/dev/null && break || sleep 60; done
[ -d "$LOCK" ] || { log "lock wait timed out"; exit 1; }

cleanup() {
  rc=$?
  [ "$rc" -ne 0 ] && { log "run failed (exit $rc)"; notify "HA auto-$PERIOD review FAILED" "exit $rc, see $LOGDIR/${PERIOD}.log"; }
  cd "$REPO"
  git worktree remove --force "$WT" 2>/dev/null || true
  [ "${PUSHED:-0}" = "1" ] || git branch -D "$BRANCH" 2>/dev/null || true
  rmdir "$LOCK" 2>/dev/null || true
}
trap cleanup EXIT

git fetch -q origin
# Keep open auto PRs mergeable: rebase onto fresh main. A PR that no longer rebases cleanly is closed
# with label auto-conflict (NOT a rejection; the agent may re-propose it on current main).
gh label create auto-conflict --color d93f0b --description "Closed: conflicted with main, safe to re-propose" 2>/dev/null || true
gh pr list --label auto-review --state open --json number,headRefName \
  --jq '.[] | select(.headRefName | startswith("auto/")) | "\(.number) \(.headRefName)"' 2>/dev/null |
while read -r PRN HEADREF; do
  git fetch -q origin "$HEADREF" || continue
  git merge-base --is-ancestor origin/main "origin/$HEADREF" && continue  # already up to date
  RB="$STATE/wt/rebase-$PRN"
  git worktree add -q --detach "$RB" "origin/$HEADREF"
  OLD="$(git -C "$RB" rev-parse HEAD)"
  if git -C "$RB" rebase -q origin/main >/dev/null 2>&1; then
    git -C "$RB" push -q --force-with-lease="$HEADREF:$OLD" origin "HEAD:refs/heads/$HEADREF" &&
      { log "rebased #$PRN ($HEADREF) onto main"; gh pr comment "$PRN" --body "Auto-rebased onto current main by the review wrapper." >/dev/null || true; }
  else
    git -C "$RB" rebase --abort 2>/dev/null || true
    log "#$PRN ($HEADREF) conflicts with main; closing"
    gh pr edit "$PRN" --add-label auto-conflict >/dev/null || true
    gh pr close "$PRN" --delete-branch \
      --comment "Conflicts with main and cannot be rebased automatically. Closing; a later auto-review may re-propose it on current main." >/dev/null || true
    notify "HA auto-review" "#$PRN closed: conflicts with main"
  fi
  git worktree remove --force "$RB" 2>/dev/null || true
done

if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  log "branch $BRANCH already on origin; nothing to do"; exit 0
fi
git branch -D "$BRANCH" 2>/dev/null || true  # stale local leftover; remote has none
git worktree add -q -b "$BRANCH" "$WT" origin/main

# What earlier auto-reviews proposed, so the agent does not repeat rejected ideas.
gh pr list --label auto-review --state all --limit 60 \
  --json number,title,state,labels \
  --jq '.[] | "#\(.number) [\(.state)\(if any(.labels[]; .name=="auto-conflict") then "/auto-conflict" else "" end)] \(.title)"' \
  >"$OUT/prior_prs.txt" 2>/dev/null || true
# Files touched by still-open auto PRs: the agent must not edit these (would conflict on merge).
gh pr list --label auto-review --state open --json number,files \
  --jq '.[] | .number as $n | .files[].path | "\(.)\t#\($n)"' >"$OUT/open_pr_files.txt" 2>/dev/null || true

PROMPT="$(
  sed -e "s|@@HA_RO@@|$HERE/ha_ro.py|g" \
      -e "s|@@WINDOW@@|$WINDOW|g" \
      -e "s|@@PERIOD@@|$PERIOD|g" \
      -e "s|@@OUT@@|$OUT|g" \
      -e "s|@@OPEN_FILES@@|$OUT/open_pr_files.txt|g" \
      "$HERE/prompts/common.md" "$HERE/prompts/$PERIOD.md"
)"

cd "$WT"
log "running claude in $WT"
claude -p "$PROMPT" \
  --model "$MODEL" \
  --max-budget-usd "$BUDGET" \
  --permission-mode dontAsk \
  ${CLAUDE_EXTRA:-} \
  --add-dir "$OUT" \
  --allowedTools \
    "Read" "Glob" "Grep" "Edit" "Write" \
    "Bash(uv run $HERE/ha_ro.py:*)" \
    "Bash(uv run yamllint:*)" "Bash(uv run pre-commit:*)" \
    "Bash(git add:*)" "Bash(git commit:*)" "Bash(git diff:*)" "Bash(git status:*)" "Bash(git log:*)" \
    "Bash(ls:*)" "Bash(cat:*)" "Bash(wc:*)" "Bash(head:*)" "Bash(tail:*)" "Bash(sort:*)" "Bash(uniq:*)" \
    "Bash(jq:*)" "Bash(grep:*)" "Bash(find:*)" "Bash(mkdir:*)" \
  --disallowedTools \
    "Bash(ssh:*)" "Bash(scp:*)" "Bash(curl:*)" "Bash(wget:*)" "Bash(websocat:*)" "Bash(hass-cli:*)" \
    "Bash(git push:*)" "Bash(git checkout:*)" "Bash(git switch:*)" "Bash(git reset:*)" "Bash(git remote:*)" \
    "Bash(gh:*)" "Bash(uv run python:*)" "Bash(python3:*)" "Bash(source:*)" "Bash(env:*)" "Bash(printenv:*)" \
    "WebFetch" "WebSearch" \
    "mcp__HomeAssistant" "mcp__playwright" "mcp__unifi-network-mcp" "mcp__memory" \
  </dev/null | tee "$OUT/claude_output.txt" || log "claude exited non-zero"

# Publish: script (not the agent) pushes and opens the PR.
cd "$WT"
AHEAD="$(git rev-list --count origin/main..HEAD)"
if [ "$AHEAD" -eq 0 ]; then
  log "no commits; findings (if any) in $OUT/report.md"
  [ -f "$OUT/report.md" ] && cp "$OUT/report.md" "$LOGDIR/${PERIOD}-${STAMP}-report.md"
  exit 0
fi

BODY="$OUT/pr_body.md"
[ -f "$BODY" ] || printf '%s\n' "Automated $PERIOD review (agent wrote no body; see commits)." >"$BODY"
{
  printf '\n---\n'
  printf '**Autonomous %s review** (window: last %s). Untested on the HA box by design: ' "$PERIOD" "$WINDOW"
  printf 'point the box at this branch and verify before merging.\n'
} >>"$BODY"

if [ "${DRY_RUN:-0}" = "1" ]; then
  log "DRY_RUN: $AHEAD commit(s) on $BRANCH, body at $BODY; not pushing"
  cp -R "$OUT" "$LOGDIR/${PERIOD}-${STAMP}-dryrun"
  git log --oneline origin/main..HEAD
  exit 0
fi

git push -q -u origin "$BRANCH"
PUSHED=1
gh label create auto-review --color 5319e7 --description "Autonomous review agent" 2>/dev/null || true
TITLE="$(git log -1 --format=%s origin/main..HEAD 2>/dev/null || true)"
[ "$AHEAD" -gt 1 ] && TITLE="chore(auto-$PERIOD): $AHEAD improvements from $(date +%F) review"
URL="$(gh pr create --base main --head "$BRANCH" --label auto-review \
  --title "[auto-$PERIOD] $TITLE" --body-file "$BODY")"
log "opened $URL"
osascript -e "display notification \"$URL\" with title \"HA auto-$PERIOD review: PR ready\"" || true
