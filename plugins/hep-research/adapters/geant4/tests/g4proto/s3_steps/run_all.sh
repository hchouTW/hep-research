#!/usr/bin/env bash
# All the runs judge.py needs, in FOLDER, from the built PROGRAM, three at a time. Usage: run_all.sh PROGRAM FOLDER
set -eu
program=$(readlink -f "$1"); mkdir -p "$2"; cd "$2"
geantino_events=4000; physics_events=400; hook_events=600; kill_events=6000
{
  for seed in 11 12; do echo "gb19-idle-$seed.json gb19 idle $seed $hook_events"; echo "gb19-none-$seed.json gb19 none $seed $hook_events"; done
  echo "gb19-none-11-again.json gb19 none 11 $hook_events"
  for hook in consuming triggering region_only process_only inert_process; do echo "gb19-$hook-11.json gb19 $hook 11 $hook_events"; done
  for pair in linear_exact:ordinary,replica,parameterised,assembly,assembly_raw,ordinary_nudged \
              linear_decimal:ordinary,replica,parameterised,assembly,assembly_raw,ordinary_nudged \
              gapped:ordinary,parameterised,assembly grid6:ordinary,parameterised,assembly grid8:ordinary,parameterised,assembly \
              ring:ordinary,parameterised,assembly module:ordinary,assembly,ordinary_module; do
    layout=${pair%%:*}
    for impl in $(echo "${pair#*:}" | tr , ' '); do
      echo "gb20-$layout-$impl-geantino.json gb20 $layout $impl geantino 21 $geantino_events"
      echo "gb20-$layout-$impl-physics.json gb20 $layout $impl physics 21 $physics_events"
    done
  done
  echo "gb20-linear_exact-ordinary-physics-again.json gb20 linear_exact ordinary physics 21 $physics_events"
  echo "gb20-linear_exact-ordinary-physics-seed22.json gb20 linear_exact ordinary physics 22 $physics_events"
  for variant in plain emit pixe booked_as_deposit pre_step_energy; do echo "gb21-$variant.json gb21 $variant 31 $kill_events"; done
} | xargs -P 3 -L 1 bash -c 'name=$1; shift; mode=$1; shift; "$0" "$mode" "$name" "$@" > "${name%.json}.log" 2>&1' "$program"
# A replica cannot express a gapped stack: the program must refuse it, exit 2, and that is the record of why it is not compared.
set +e; "$program" gb20 gb20-gapped-replica.json gapped replica physics 21 1 > gb20-gapped-replica.log 2>&1; echo "$?" > gb20-gapped-replica.exit; set -e
echo '{"status": "ok"}'
