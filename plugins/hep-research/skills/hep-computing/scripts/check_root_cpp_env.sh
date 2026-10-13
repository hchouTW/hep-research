#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $(basename "$0") [--json]"
  echo "Check that the CERN ROOT C++ toolchain (root, root-config) is on PATH, print its versions and flags, and"
  echo "compile and run a one-entry RDataFrame program."
  echo "--json: print one JSON object with \"status\" (ok, failed, missing-dependency) instead of text."
  echo "Exit codes: 0 toolchain works, 1 the test program does not compile or run, 2 bad usage,"
  echo "3 root or root-config not on PATH."
}

JSON=0
case "${1:-}" in
  -h|--help) usage; exit 0 ;;
  --json) JSON=1 ;;
  "") ;;
  *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
esac

json_str() {  # a JSON string literal: escape backslashes, quotes and control characters
  printf '"%s"' "$(printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr '\n\t\r' '   ')"
}

finish() {  # finish STATUS CODE MESSAGE
  if [ "$JSON" -eq 1 ]; then
    printf '{"status": %s, "message": %s' "$(json_str "$1")" "$(json_str "$3")"
    if [ -n "${ROOT_VERSION:-}" ]; then
      printf ', "root": %s, "root_version": %s, "root_config_version": %s, "cflags": %s, "libs": %s' \
        "$(json_str "$ROOT_BIN")" "$(json_str "$ROOT_VERSION")" "$(json_str "$CONFIG_VERSION")" \
        "$(json_str "$CFLAGS")" "$(json_str "$LIBS")"
    fi
    printf '}\n'
  elif [ "$2" -eq 0 ]; then
    echo "$3"
  else
    echo "ERROR: $3" >&2
  fi
  exit "$2"
}

say() { [ "$JSON" -eq 1 ] || echo "$@"; }

say 'Checking CERN ROOT C++ environment...'

command -v root >/dev/null 2>&1 || finish missing-dependency 3 'root command not found.'
command -v root-config >/dev/null 2>&1 || finish missing-dependency 3 'root-config command not found.'

ROOT_BIN=$(command -v root)
CFLAGS=$(root-config --cflags)
LIBS=$(root-config --libs)
CONFIG_VERSION=$(root-config --version)
ROOT_VERSION=$(root --version 2>&1 | head -n 1)

say "root: $ROOT_BIN"
say "root version: $ROOT_VERSION"
say "root-config: $(command -v root-config)"
say "root-config version: $CONFIG_VERSION"
say "cflags: $CFLAGS"
say "libs: $LIBS"

TMPDIR="${TMPDIR:-/tmp}/root_cpp_check.$$"
mkdir -p "$TMPDIR"
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/check.cpp" <<'CPP'
#include <ROOT/RDataFrame.hxx>
#include <iostream>

int main() {
    ROOT::RDataFrame df(1);
    auto n = df.Count();
    std::cout << "RDataFrame count: " << *n << "\n";
    return *n == 1 ? 0 : 1;
}
CPP

# shellcheck disable=SC2086  # root-config flags are word lists
if ! c++ -std=c++17 "$TMPDIR/check.cpp" $CFLAGS $LIBS -o "$TMPDIR/check" >"$TMPDIR/build.log" 2>&1; then
  [ "$JSON" -eq 1 ] || cat "$TMPDIR/build.log" >&2
  finish failed 1 'the RDataFrame test program does not compile against this ROOT.'
fi
if ! RUN_OUT=$("$TMPDIR/check" 2>&1); then
  finish failed 1 "the RDataFrame test program failed: $RUN_OUT"
fi
say "$RUN_OUT"

finish ok 0 'C++ ROOT environment: OK'
