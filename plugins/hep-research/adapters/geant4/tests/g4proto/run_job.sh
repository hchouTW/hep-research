#!/usr/bin/env bash
# Start a long job detached (g4sim-execution-plan.md, Section 5): closing the session cannot end it, and on macOS the machine stays
# awake until it finishes. Writes job.log and job.pid in FOLDER, and refuses to start twice.
# Usage: run_job.sh FOLDER COMMAND [ARGUMENT...]    Check it with: kill -0 "$(cat FOLDER/job.pid)" && echo RUNNING || echo STOPPED
set -u
if [ $# -lt 2 ]; then
  echo '{"status": "rejected", "message": "usage: run_job.sh FOLDER COMMAND [ARGUMENT...]"}'
  exit 2
fi
FOLDER=$1
shift
mkdir -p "$FOLDER" || exit 2
if [ -f "$FOLDER/job.pid" ] && kill -0 "$(cat "$FOLDER/job.pid")" 2>/dev/null; then
  echo "{\"status\": \"rejected\", \"message\": \"a job is already running in $FOLDER\"}"
  exit 1
fi
if command -v caffeinate > /dev/null; then
  nohup caffeinate -i "$@" > "$FOLDER/job.log" 2>&1 &
else
  nohup "$@" > "$FOLDER/job.log" 2>&1 &
fi
echo $! > "$FOLDER/job.pid"
echo "{\"status\": \"ok\", \"pid\": $!, \"log\": \"$FOLDER/job.log\"}"
