#!/usr/bin/env bash
# Read-only checkout of the legacy skills at the pinned baseline commit.
set -euo pipefail
HERE="$(git rev-parse --show-toplevel)"
DEST="${LEGACY_REPO:-$HERE/.legacy/agentic-ai-skills}"
PIN=3e995a49a89fad8e0e9d52130ee1fd93a3a0f4f9
if [[ ! -d "$DEST/.git" ]]; then
  git clone --quiet https://github.com/hchouTW/agentic-ai-skills "$DEST"
fi
git -C "$DEST" -c advice.detachedHead=false checkout --quiet "$PIN"
test "$(git -C "$DEST" rev-parse HEAD)" = "$PIN"
chmod -R a-w "$DEST" 2>/dev/null || true
echo "legacy source ready at $DEST ($PIN)"
