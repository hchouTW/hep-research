#!/usr/bin/env bash
set -euo pipefail

printf 'Checking CERN ROOT C++ environment...\n'

if ! command -v root >/dev/null 2>&1; then
  echo 'ERROR: root command not found.' >&2
  exit 1
fi

if ! command -v root-config >/dev/null 2>&1; then
  echo 'ERROR: root-config command not found.' >&2
  exit 1
fi

echo "root: $(command -v root)"
echo "root version: $(root --version | head -n 1)"
echo "root-config: $(command -v root-config)"
echo "root-config version: $(root-config --version)"
echo "cflags: $(root-config --cflags)"
echo "libs: $(root-config --libs)"

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

c++ -std=c++17 "$TMPDIR/check.cpp" $(root-config --cflags --libs) -o "$TMPDIR/check"
"$TMPDIR/check"

echo 'C++ ROOT environment: OK'
