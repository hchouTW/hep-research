#!/usr/bin/env bash
# The one Mac job of S2 (g4sim-execution-plan.md): builds g4sim_run, scans the new C++ for G5, and judges gate 4 against the recorded references.
# Usage: run_s2_mac.sh [build|scan|start|status]   from the plugin root of the g4sim/S2 worktree. Everything is written below ~/g4sim-s2-mac.
# start is detached and resumable: run it again after a stop and finished runs are kept. It writes no tracked file.
set -u
OUT=~/g4sim-s2-mac
G4=~/Workspace/geant4-work/build-a/install
source ~/.venvs/hep-research-e2/bin/activate
source "$G4/bin/geant4.sh"
export CMAKE_PREFIX_PATH="$G4" PYTHONDONTWRITEBYTECODE=1
mkdir -p "$OUT"
case "${1:-status}" in
  build)
    cmake -S adapters/geant4/assets/g4sim_run -B "$OUT/build" -DCMAKE_BUILD_TYPE=Release > "$OUT/cmake.log" 2>&1 || { tail -20 "$OUT/cmake.log"; exit 1; }
    cmake --build "$OUT/build" -j8 >> "$OUT/cmake.log" 2>&1 || { tail -20 "$OUT/cmake.log"; exit 1; }
    mkdir -p "$OUT/records"
    tar xzf ~/g4sim-s1-records.tar.gz -C "$OUT/records" 2> /dev/null
    echo "build ok; records: $(ls "$OUT/records/runs" | wc -l | tr -d ' ') runs"
    ;;
  scan)
    A=adapters/geant4
    FILES="$A/assets/g4sim/Accounting.hh $A/assets/g4sim_run/IrTree.hh $A/assets/g4sim_run/WriteBack.hh $A/assets/g4sim_run/GeometryCheck.cc $A/assets/g4sim_run/g4sim_run.cc $A/assets/g4sim_run/legacy_element/Detector.cc $A/assets/g4sim_run/legacy_layered/Detector.cc $A/tests/g4proto/s2_gates/main.cc"
    for k in 3 4; do python3 $A/tests/g4proto/g5_scan.py --examples ~/Workspace/geant4-work/build-a/src/examples --length $k $FILES > "$OUT/g5_k$k.json"; echo "k=$k exit=$?"; done
    ;;
  start)
    bash adapters/geant4/tests/g4proto/run_job.sh "$OUT/job" python3 adapters/geant4/tests/g4proto/reacquire/regress.py \
      --facts adapters/geant4/tests/g4proto/reacquire/recorded_runs.json --baselines "$OUT/records" --program "$OUT/build/g4sim_run" \
      --work "$OUT/gate4" --recorded-root ~/Workspace/geant4-work --cores 8
    ;;
  status)
    python3 - "$OUT" <<'PY'
import json, os, sys
out = sys.argv[1]
path = os.path.join(out, "gate4", "regression.json")
done = json.load(open(path)) if os.path.exists(path) else {}
bad = {k: (v["exit"], [n for n, s in v["same"].items() if not s], v["tree_differences"]) for k, v in done.items() if not v["identical"]}
print(len(done), "of 112 done;", len(done) - len(bad), "identical; different:", list(bad.items())[:5])
PY
    [ -f "$OUT/job/job.pid" ] && { kill -0 "$(cat "$OUT/job/job.pid")" 2> /dev/null && echo RUNNING || echo STOPPED; }
    ;;
esac
