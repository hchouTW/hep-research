#!/usr/bin/env bash
# GB1 and GB22 (g4sim plan, Section 23) on one machine, from the plugin root. Writes under WORK only; prints each judge's result.
# Usage: run_gb1_gb22.sh WORK [GEANT4_CONFIG]  GEANT4_CONFIG: build through geant4-config (an installation with no usable
# CMake package); otherwise find_package(Geant4) with the environment's CMAKE_PREFIX_PATH.
set -u
WORK=$(mkdir -p "$1" && cd "$1" && pwd)
CONFIG=${2:-}
HERE=adapters/geant4/tests/g4proto/reacquire
PY=${PYTHON:-python3}
rm -rf "$WORK/src" "$WORK/build"
for program in layered_sim element_sim; do
  "$PY" "$HERE/apply_probe.py" "$program" adapters/geant4/assets "$WORK/src" || exit 2
  option=()
  [ -n "$CONFIG" ] && option=("-DG4SIM_GEANT4_CONFIG=$CONFIG")
  cmake -S "$WORK/src/$program" -B "$WORK/build/$program" -DCMAKE_BUILD_TYPE=Release -DLAYERED_SIM_TEST_HOOKS=ON "${option[@]}" \
    > "$WORK/build-$program.log" 2>&1 && cmake --build "$WORK/build/$program" -j8 >> "$WORK/build-$program.log" 2>&1
  echo "build $program exit=$?"
done
"$PY" - "$WORK" <<'PYTHON'
import json, os, sys
work = sys.argv[1]
def write(name, source, edit):
    folder = f"{work}/run-{name}"
    os.makedirs(folder, exist_ok=True)
    spec = json.load(open(source))
    spec["run"]["events"] = 20
    spec["output"].update({key: f"{folder}/{key}.out" for key in ("materials", "datapaths")})
    spec["output"]["csv"] = f"{folder}/events.csv"
    edit(spec)
    json.dump(spec, open(f"{folder}/spec.json", "w"), indent=1)
write("layered", "examples/geant4-thin-silicon/recorded/specs/mpv-control.json",
      lambda s: s.__setitem__("ui_commands", s.get("ui_commands", []) + ["/layered_sim/test/probeAfterInitialize"]))
write("element", "examples/design-minimal-spectrometer/recorded/artifacts/specs/N4-TRK1-nominal.spec.json",
      lambda s: s["run"].__setitem__("threads", 2))
PYTHON
(cd "$WORK/run-layered" && G4PROTO_OUT=$PWD "$WORK/build/layered_sim/layered_sim" spec.json > log.txt 2>&1; echo "layered_sim exit=$?")
(cd "$WORK/run-element" && G4PROTO_OUT=$PWD G4PROTO_DECLARED=FieldRegion "$WORK/build/element_sim/element_sim" spec.json > log.txt 2>&1; echo "element_sim exit=$?")
"$PY" "$HERE/judge.py" "$WORK/run-layered" --uninitialized "$WORK/run-layered/probe.test.json"; echo "judge layered exit=$?"
"$PY" "$HERE/judge.py" "$WORK/run-element" --mt; echo "judge element exit=$?"
if [ -n "$CONFIG" ]; then
  g++ -O2 -std=c++17 $("$CONFIG" --cflags) -I adapters/geant4/assets/g4sim "$HERE/beamon_zero/main.cc" -o "$WORK/beamon_zero" \
    $("$CONFIG" --libs) -Wl,-rpath,"$("$CONFIG" --prefix)/lib" -Wl,-rpath-link,"$("$CONFIG" --prefix)/lib"
else
  cmake -S "$HERE/beamon_zero" -B "$WORK/build/beamon_zero" -DCMAKE_BUILD_TYPE=Release > "$WORK/build-beamon.log" 2>&1 \
    && cmake --build "$WORK/build/beamon_zero" >> "$WORK/build-beamon.log" 2>&1 && cp "$WORK/build/beamon_zero/beamon_zero" "$WORK/beamon_zero"
fi
"$WORK/beamon_zero" 2>&1 | grep BEAMON_ZERO
