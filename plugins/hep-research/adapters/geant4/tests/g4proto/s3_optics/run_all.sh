#!/usr/bin/env bash
# Runs for GB15, GB16 and GB17. Usage: run_all.sh trial|scope PROGRAM FOLDER  |  run_all.sh judged PROGRAM FOLDER NUMBERS.json
# trial: the runs derive_registration.py register reads; never the test sample. scope: the GB16 runs. judged: only after the S3 card holds NUMBERS.json.
# PARALLEL (default 4) processes at a time; ONLY, a pattern, keeps the runs whose name matches. A run's exit code lands in NAME.exit: a Geant4 crash is a recorded fact for GB16, so it does not stop the others.
set -eu
stage=$1; program=$(readlink -f "$2"); folder=$3
here=$(dirname "$(readlink -f "$0")")
python=${PYTHON:-python3}
mkdir -p "$folder/gb15" "$folder/gb16" "$folder/gb17"
case "$stage" in
  trial) listing=$("$python" "$here/derive_registration.py" commands trial) ;;
  scope) listing=$("$python" "$here/derive_registration.py" gb16-commands) ;;
  judged) listing=$("$python" "$here/derive_registration.py" commands judged "$4") ;;
  *) echo '{"status": "rejected", "message": "stage must be trial, scope or judged"}'; exit 2 ;;
esac
if [ -n "${ONLY:-}" ]; then listing=$(printf '%s\n' "$listing" | grep -E "^${ONLY}"); fi
cd "$folder"
ulimit -c 0
one_run() {
  IFS=$'\t' read -r name mode options <<< "$1"
  target=$name.json; [ "$mode" = gb15 ] && target=$name
  set +e
  # shellcheck disable=SC2086
  "$program" "$mode" "$target" $options > "$name.log" 2>&1
  echo $? > "$name.exit"
}
export -f one_run; export program
printf '%s\n' "$listing" | xargs -d '\n' -P "${PARALLEL:-4}" -I{} bash -c 'one_run "$1"' _ {}
echo '{"status": "ok"}'
