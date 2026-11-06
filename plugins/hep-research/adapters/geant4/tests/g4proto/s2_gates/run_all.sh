#!/usr/bin/env bash
# All the runs judge.py needs, in FOLDER, from the built PROGRAM. Usage: run_all.sh PROGRAM FOLDER
set -eu
program=$(readlink -f "$1"); mkdir -p "$2"; cd "$2"
"$program" gb9 gb9.json > gb9.log 2>&1
"$program" gb7 gb7.json > gb7.log 2>&1
limit=$(python3 -c "import json; print(float.fromhex(json.load(open('gb7.json'))['median_electron_step_mm']) / 10)")
python3 -c "import json; json.dump({'limit_mm': float('$limit').hex()}, open('gb7-limit.json', 'w'))"
"$program" gb7 gb7-limited.json "$limit" > gb7-limited.log 2>&1
"$program" gb8 gb8.json > gb8.log 2>&1
"$program" gb8em gb8em.json > gb8em.log 2>&1
"$program" gb5 gb5.json > gb5.log 2>&1
for order in forward reverse mother_only none_manager no_manager; do "$program" gb3 "gb3-$order.json" "$order" > "gb3-$order.log" 2>&1; done
echo '{"status": "ok"}'
