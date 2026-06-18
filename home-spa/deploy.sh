#!/usr/bin/env bash
# Build the Home SPA, commit+push, and force HA's /config checkout to the head.
# Usage: home-spa/deploy.sh "commit message"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/home-spa" && npm run build >/dev/null
cd "$ROOT"
# Stage only SPA build output + source — never `git add -A` (sweeps in stray
# screenshots / scratch files from the repo root).
git add www/home-spa home-spa/src home-spa/*.ts home-spa/*.js home-spa/*.json home-spa/*.md 2>/dev/null || true
git commit -q -m "${1:-wip(home-spa): iterate design}" || echo "(nothing to commit)"
git push -q
HEAD=$(git rev-parse --short HEAD)
# HA side: clear the stale remote-tracking ref that causes "cannot lock ref",
# then fetch+reset to the just-pushed head.
ssh -o BatchMode=yes root@homeassistant.local \
  'cd /config && rm -f .git/refs/remotes/origin/feat/home-spa-pilot .git/refs/remotes/origin/feat/home-spa-pilot.lock 2>/dev/null; git fetch -q origin feat/home-spa-pilot && git reset --hard -q FETCH_HEAD && git rev-parse --short HEAD'
echo "local=$HEAD"
