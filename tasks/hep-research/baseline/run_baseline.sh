#!/usr/bin/env bash
set -u
# Legacy skills live in a read-only checkout of agentic-ai-skills (see tasks/hep-research/LEGACY_SOURCE.md).
HERE="$(git rev-parse --show-toplevel)"
REPO="${LEGACY_REPO:-$HERE/.legacy/agentic-ai-skills}"
OUT="$HERE/tasks/hep-research/baseline"; mkdir -p "$OUT"
SUMMARY="$OUT/summary.csv"; echo "skill,step,result" > "$SUMMARY"
for skill in ams-analysis hep-analysis deep-learning academic-papers \
             academic-diagrams agile-development task-authoring; do
  if [[ -f "$REPO/$skill/scripts/validate_skill_bundle.py" ]]; then
    (cd "$REPO/$skill" && python3 scripts/validate_skill_bundle.py) \
      > "$OUT/$skill.bundle.log" 2>&1
    echo "$skill,bundle,$?" >> "$SUMMARY"
  else
    echo "$skill,bundle,MISSING" >> "$SUMMARY"
  fi
  if [[ -d "$REPO/$skill/tests" ]]; then
    (cd "$REPO/$skill" && python3 -m unittest discover -s tests -v) \
      > "$OUT/$skill.unittest.log" 2>&1
    echo "$skill,unittest,$?" >> "$SUMMARY"
  else
    echo "$skill,unittest,MISSING" >> "$SUMMARY"
  fi
done
cat "$SUMMARY"
