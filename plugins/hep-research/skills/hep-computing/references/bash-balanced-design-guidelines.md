# Balanced Bash Design Guidelines

A checklist for Bash in HEP work: job scripts, environment setup, wrappers around ROOT or Python, small pipelines.
Follow established repository conventions when they intentionally differ. Naming, comments and file headers are
decided once in the [ROOT guidelines](root-balanced-design-guidelines.md#naming-comments-and-file-documentation);
the Bash form is `lower_snake_case` functions and variables, `UPPER_SNAKE_CASE` constants and exported variables
([Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)), with `#!/usr/bin/env bash` as
the shebang so a newer Bash on `PATH` is used.

Bash versions: stock macOS ships Bash 3.2 as `/bin/bash`; `declare -A` and `mapfile` need 4.0, `local -n` 4.3,
`inherit_errexit` and safe empty-array expansion 4.4. Target a version explicitly when a script uses them. When a
script grows past a few hundred lines, needs data structures or arithmetic on floats, write it in Python.

## Start every unattended script like this

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
```

- `-e` stops on an unchecked failure, `-u` on an unset variable, `pipefail` on a failure inside a pipeline, `-E`
  makes an `ERR` trap fire inside functions and subshells too.
- `set -e` has gaps. A function called as a condition (`if f`, `f && ...`, `f || ...`, `! f`) runs with errexit off
  for everything inside it and returns the status of its last command: check each step explicitly
  (`cmd || return 1`) in such functions. `local out=$(cmd)` loses `cmd`'s status (`local` succeeds): declare first,
  then assign. `$(...)` does not inherit `-e` without `shopt -s inherit_errexit` (Bash 4.4+).
- `((count++))` returns status 1 when `count` was 0 and ends the script under `set -e` on Bash 4.1+; write
  `count=$((count + 1))`.

## set -u and environment setup (HEP job scripts)

- Setup scripts are not written for `set -u`: sourcing ROOT's `thisroot.sh`, an LCG view's `setup.sh`, an
  experiment setup script or running `module load` reads unset variables (`$LD_LIBRARY_PATH`, `$PYTHONPATH`,
  `$MANPATH` on a clean node) and stops the job. Relax `-u` only around the source:

  ```bash
  set +u
  source /cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-opt/setup.sh
  set -u
  ```
- `"${arr[@]}"` on an empty array is an "unbound variable" error under `set -u` before Bash 4.4 (checked on
  macOS `/bin/bash` 3.2.57). Use `${arr[@]+"${arr[@]}"}` where the array may be empty and the script must run on
  old Bash, or require 4.4+ (`(( BASH_VERSINFO[0] * 100 + BASH_VERSINFO[1] >= 404 ))`).
- Record what the setup gave you (`root-config --version`, `python3 --version`, the LCG release) in the job's log or
  run record; see [environments and containers](environments-and-containers.md).

## Quoting and input validation

- Quote every expansion: `"${var}"`, `"$(cmd)"`, `"${arr[@]}"`. Unquoted, a path with a space or a `*` splits or
  globs. `rm -rf -- "${dir}"` with the `--`; never `rm -rf ${dir}/` where `dir` may be empty.
- `[[ ]]` instead of `[ ]`; `$(...)` instead of backticks; `readonly` for constants.
- Validate external values with `[[ "${n}" =~ ^[0-9]{1,9}$ ]]` before they reach `(( ))`, `$(( ))` or `let`:
  arithmetic treats a non-number as a variable name (`abc` becomes 0), expands `$(...)` in array subscripts (runs
  commands from input) and wraps on 64-bit overflow (`18446744073709551621` becomes 5).
- Build command lines as arrays (`args=(--input "${f}" --out "${o}"); prog "${args[@]}"`), never by concatenating a
  string and `eval`.

## Temporary files, cleanup and locks

- Temporary folders with `mktemp -d "${TMPDIR:-/tmp}/name.XXXXXX"`, never a fixed name or `$$` (predictable,
  collides between parallel jobs); do not reassign `TMPDIR` itself.
- One `EXIT` trap with one cleanup function: Bash does not stack traps, a second `trap ... EXIT` replaces the
  first.

  ```bash
  work_dir="$(mktemp -d "${TMPDIR:-/tmp}/job.XXXXXX")"
  cleanup() { rm -rf -- "${work_dir}"; }
  trap cleanup EXIT
  ```
- Locks: `flock` (util-linux; not on stock macOS) on a file in local scratch the user owns:
  `exec 9>"${TMPDIR:-/tmp}/myscript.${USER}.lock"; flock -n 9 || { echo "already running" >&2; exit 1; }`. Not
  `/var/lock` (root-owned, node-local). `flock` on NFS, EOS, AFS, Lustre or CVMFS is unreliable or a no-op and may
  succeed on two nodes at once: serialize across nodes with the scheduler (dependencies, one job per resource), not
  with `flock` on shared storage.

## Signals and preemption

The `EXIT` trap runs when the script exits after `SIGINT` or `SIGTERM`, but it does not stop the script's children,
and while a foreground child runs the trap waits for it. A batch system that preempts a job sends `SIGTERM`, then
`SIGKILL` after a grace period: run the long step in the background, forward the signal and `wait`, so the child can
close its output inside the grace period, and exit 143 so the scheduler sees a terminated job (checked on Bash
3.2.57: the child's TERM handler ran, then the EXIT trap, exit 143):

```bash
child_pid=""
on_term() {
  [[ -n "${child_pid}" ]] && kill -TERM "${child_pid}" 2>/dev/null
  wait "${child_pid}" 2>/dev/null
  exit 143
}
trap on_term TERM INT

./run_analysis --out "${work_dir}/out.root" &
child_pid=$!
wait "${child_pid}"
```

## Structure

- Functions for every step with a name; `local` for every variable inside them; `main "$@"` at the bottom.
- Functions return non-zero for expected failures; only the top level calls `exit`, so a sourced library stays
  usable. Messages go to stderr (`echo "error: ..." >&2`); stdout is for data.
- A dispatch `case "${cmd}" in ... esac` instead of an `if/elif` chain; no simulated objects (prefixed globals,
  nameref "methods").
- Document the exit codes in the header and keep one convention (0 success, 1 a negative result, 2 bad usage).
- Prefer built-ins over a fork per line in loops (`${var#prefix}`, `${var%suffix}`, `[[ =~ ]]`); for real text
  processing use `awk` once, not `grep | sed | cut` per line.
- Never parse `ls`; loop over globs (`for f in "${dir}"/*.root; do [[ -e "${f}" ]] || continue; ...`).

## Testing

- `bash -n script.sh` (syntax) and [ShellCheck](https://www.shellcheck.net) on every change.
- Run the script once with a missing input and once with an unwritable output: it must exit non-zero with one
  message, not continue with empty variables.
- For job scripts: run one chunk locally with the same environment setup before submitting; see
  [batch scheduling](batch-scheduling.md).

## Grep-able anti-patterns

| Pattern | Problem | Instead |
|---|---|---|
| `rm -rf $dir` or `rm -rf ${dir}/` | empty or split variable deletes the wrong tree | `rm -rf -- "${dir}"` after `[[ -n "${dir}" ]]` |
| `/tmp/name.$$`, `TMPDIR=` | predictable, collides, changes every child's temp | `mktemp -d` |
| `local x=$(cmd)` | `cmd`'s failure is lost | `local x; x=$(cmd)` |
| `((i++))` under `set -e` | exits when `i` was 0 | `i=$((i + 1))` |
| `source .../setup.sh` under `set -u` | setup script stops the job | `set +u; source ...; set -u` |
| `/var/lock`, `flock` on shared storage | not writable, or no mutual exclusion across nodes | lock in local scratch; scheduler for cross-node |
| `eval "$cmd"` | runs input as code | argument arrays |
| `for f in $(ls ...)` | breaks on spaces, misses errors | globs |
| a second `trap ... EXIT` | replaces the first | one cleanup function |
| long job in the foreground with only an `EXIT` trap | children killed without flushing on preemption | background child, forward `TERM`, `wait` |
