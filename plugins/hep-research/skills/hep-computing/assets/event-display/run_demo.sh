#!/usr/bin/env bash
# End-to-end demo of the event-display templates on synthetic data, in a fresh work directory.
# Usage: bash run_demo.sh WORK_DIR [PYTHON]
#   PYTHON defaults to python3 and needs numpy, uproot, awkward (export) and playwright (browser test).
#   Node.js and npm are needed for the web build (npm ci uses web/package-lock.json).
# Every output is synthetic. Exit status is non-zero at the first failing step.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="${1:?usage: run_demo.sh WORK_DIR [PYTHON]}"
PY="${2:-python3}"
mkdir -p "$WORK"
cd "$WORK"

echo "== 1. synthetic inputs (stand-in for the project's data and analysis results)"
"$PY" -I "$HERE/make_demo_data.py" --out demo

echo "== 2. export events (Phoenix safe subset: Hits Point / Line)"
"$PY" -I "$HERE/export_events.py" demo/demo.root --mapping "$HERE/mapping.example.json" --out work/events --status synthetic

echo "== 3. export already-computed results (no re-analysis)"
"$PY" -I "$HERE/export_histogram.py" --root demo/demo.root --object h_pt --integration jsroot --out work/results
"$PY" -I "$HERE/export_histogram.py" --json demo/results/hits_per_run.json --integration echarts --out work/results
for f in demo/results/hit_r/*.json; do
  key="$(basename "$f" .json)"
  "$PY" -I "$HERE/export_histogram.py" --json "$f" --integration plotly --out "work/results/hit_r/$key" > /dev/null
done

echo "== 4. build the web page"
rm -rf web && cp -r "$HERE/web" web
(cd web && npm ci --no-audit --no-fund && npm run build)

echo "== 5. assemble and check the bundle"
cp "$HERE/bundle-spec.example.json" bundle-spec.json
"$PY" -I "$HERE/build_bundle.py" bundle-spec.json
"$PY" -I "$HERE/check_bundle.py" bundle --spec bundle-spec.json

echo "== 6. browser test (loopback, headless Chromium)"
"$PY" -I "$HERE/test_page.py" bundle

echo "== done: serve with  $PY -m http.server -d $(pwd)/bundle --bind 127.0.0.1 8000  and open http://127.0.0.1:8000/"
