#!/bin/sh
# check-paths.sh: reads paths on stdin; refuses any path outside this repository's allowlist.
ALLOWED='^(\.claude-plugin|\.agents|\.github|\.githooks|plugins|evals)/|^(\.gitignore|\.gitleaks\.toml|LICENSE|README\.md)$'
bad=$(grep -Ev "$ALLOWED" | sort -u)
if [ -n "$bad" ]; then
  echo "Refused: paths outside the allowlist of this repository:" >&2
  echo "$bad" >&2
  exit 1
fi
