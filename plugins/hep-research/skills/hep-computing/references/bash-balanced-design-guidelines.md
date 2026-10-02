# Balanced Bash Design Guidelines

When modifying or writing Bash scripts, prefer a balanced style between
disciplined procedural structure and lightweight data grouping. Follow
established repository conventions when they intentionally differ from this
reference.

Some examples use Bash 4+ features (`declare -A` and `mapfile` need 4.0, `declare -g` 4.2,
`local -n` 4.3). Stock macOS ships Bash 3.2 at `/bin/bash`, where they fail; target a
newer Bash explicitly or avoid them if the script must run there.

The examples follow the
[Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html):
two-space indentation, `lower_snake_case` for function and variable names,
`UPPER_SNAKE_CASE` for constants and exported environment variables, `[[ ]]`
over `[ ]`, `$(...)` over backticks, and `local` for every function-scoped
variable. One deliberate exception: the shebang is `#!/usr/bin/env bash`, not
Google's `#!/bin/bash`, so that a newer Bash on `PATH` runs the Bash 4+ examples
(`/bin/bash` on macOS is 3.2). Bash has no classes, RAII, or exceptions, so this guide reframes
those C++/Python concepts around what Bash actually offers: functions,
variables, arrays, subshells, traps, and exit status. See the
[C++](cpp-balanced-design-guidelines.md) and
[Python](python-balanced-design-guidelines.md) guides for the object-oriented
side of this family of references.

## Contents

- [Core Principle](#core-principle)
- [Choosing Functions, Variables, and Arrays](#when-to-use-a-function)
- [Avoid Simulated Object-Orientation](#avoid-simulated-object-orientation)
- [Resource Management](#resource-management)
- [Composition and Dispatch](#composition-and-dispatch)
- [Scoping and State](#scoping-and-state)
- [Error Handling](#error-handling)
- [Quoting and Const-Correctness](#quoting-and-const-correctness)
- [Ownership and Isolation](#ownership-and-isolation)
- [Naming and File Organization](#naming-guidance)
- [Testing and Portable Code](#testing-guidance)
- [External Tools and Documentation](#external-tool-preference)
- [Design Checklist](#design-checklist)
- [Anti-Patterns Recap](#anti-patterns-to-avoid-recap)
- [Summary Rule](#summary-rule)

## Core Principle

Use functions to name and encapsulate a step, a side effect, or a unit of
control flow.

Use plain variables and arrays to hold data — a value, a list, or a small
group of related fields.

Do not simulate classes, inheritance, or objects in Bash. Do not write a
script as one long unstructured sequence of top-level commands either.

The preferred style is simple, idiomatic, testable, procedural Bash.

---

## When to Use a Function

Use a function when the code needs one or more of the following:

- A named, reusable step
- A single-responsibility unit that can be tested or reasoned about alone
- A boundary around commands that must run together (e.g. acquire-then-use)
- A stable "interface" that callers depend on, even if the implementation
  changes later

Good examples:

```bash
parse_args() {
  ...
}

fetch_release_notes() {
  ...
}

validate_config_file() {
  ...
}

render_report() {
  ...
}
```

A function should represent one real step in the script's workflow, not
merely wrap a single command for no reason.

Example:

```bash
backup_database() {
  local db_name="$1"
  local dest_dir="$2"

  if [[ ! -d "${dest_dir}" ]]; then
    echo "backup_database: destination not found: ${dest_dir}" >&2
    return 1
  fi

  pg_dump "${db_name}" > "${dest_dir}/${db_name}.sql"
}
```

In this example, the function is justified because it validates a
precondition and names a step that the rest of the script can call by
intent ("back up the database") rather than by mechanism.

---

## When to Use Plain Variables and Arrays

Use plain scalar variables for single values, and indexed or associative
arrays for simple grouped data — Bash's nearest equivalent to a C++ `struct`
or a Python `@dataclass`.

Prefer this:

```bash
declare -A point=(
  [x]=3
  [y]=4
)

echo "${point[x]},${point[y]}"
```

Avoid writing a "constructor" function plus "getter" functions for data with
no invariants to protect:

```bash
# Unnecessary ceremony for plain data.
declare -A point=()

set_point() {
  point[x]="$1"
  point[y]="$2"
}

point_x() { echo "${point[x]}"; }
point_y() { echo "${point[y]}"; }
```

An associative array is not inferior to a "real" data type. In Bash, it is
often the clearest way to pass a handful of related fields to or from a
function.

Use an associative array (or a `declare -A` returned via a nameref) when:

- The data is mainly a value carrier
- The fields are safe to read directly
- There is no validation step that must run on every access
- Positional parameters would otherwise make a function call unreadable

Example:

```bash
declare -A opts=(
  [verbose]=0
  [output]="/tmp/report.txt"
)
```

If the data later needs validation on every write, promote the access
pattern to a function (see the color-validation example under Quoting and
Const-Correctness) rather than reading and writing the array directly
everywhere.

---

## When to Use Free-Standing Commands

Use a short, direct pipeline or command sequence — not a function — for a
one-off step that is used exactly once and needs no name to be understood in
context.

Prefer this for a single, self-explanatory step:

```bash
mapfile -t files < <(find . -name '*.log' -mtime +7)
```

(When file names may contain newlines, use `find ... -print0` with
`mapfile -d ''` on Bash 4.4+, or a `while IFS= read -r -d ''` loop.)

Do not wrap a single command in a function only because "everything should be
a function":

```bash
# Unnecessary indirection.
find_old_logs() {
  find . -name '*.log' -mtime +7
}

mapfile -t files < <(find_old_logs)
```

Reach for a function when the step is reused, when it needs its own error
handling, or when naming it clarifies intent that the raw command does not
already convey.

---

## Avoid Simulated Object-Orientation

Do not build class-like frameworks out of associative arrays, namerefs
(`local -n`), and prefixed global variables. Bash's indirection features can
imitate objects, but the result is usually harder to read than the
procedural code it replaces.

Avoid this:

```bash
# "Object" simulation via nameref indirection and prefixed globals.
Counter_new() {
  declare -g "$1_value=0"
}

Counter_increment() {
  local -n value="$1_value"
  value=$((value + 1))
}

Counter_get() {
  local -n value="$1_value"
  echo "${value}"
}

Counter_new my_counter
Counter_increment my_counter
echo "$(Counter_get my_counter)"
```

Prefer a plain variable, passed to functions as an argument and returned on
stdout, or an associative array passed by name when several related pieces of
state must travel together:

```bash
counter=0
counter=$((counter + 1))
echo "${counter}"
```

Avoid module names like these unless there is a strong reason — they signal
the same unclear-responsibility smell in Bash that they do in C++ or Python:

```bash
utils.sh
helpers.sh
manager.sh
```

Prefer precise, verb-first function names, and library file names that name
the one responsibility they hold:

```bash
lib/parse_args.sh
lib/render_report.sh
lib/validate_config.sh
```

---

## Resource Management

Use `trap` to guarantee cleanup, the same role RAII plays in C++ and context
managers play in Python.

Tie acquisition and release together at the point of acquisition, not at the
bottom of the script where a later `exit` might skip it.

Prefer this:

```bash
work_dir="$(mktemp -d)"
readonly work_dir
trap 'rm -rf -- "${work_dir}"' EXIT

# ... use "${work_dir}" ...
```

Avoid this:

```bash
work_dir="$(mktemp -d)"

# ... use "${work_dir}" ...

rm -rf -- "${work_dir}"  # skipped if an earlier command exits/returns first
```

Use `flock` for resources that must not be accessed concurrently:

```bash
# `flock` is part of util-linux; it is not installed on stock macOS.
exec 9>"/var/lock/myscript.lock"
flock -n 9 || { echo "already running" >&2; exit 1; }
```

The lock needs no unlock trap: it is held by file descriptor 9 and released
when the script exits and the descriptor closes.

Combine multiple cleanup actions in one function — Bash does not stack `EXIT`
traps, so a second `trap ... EXIT` silently replaces the first. Bash also runs
the `EXIT` trap when the script is killed by `SIGINT` or `SIGTERM`, so one
`EXIT` trap covers those cases:

```bash
cleanup() {
  rm -rf -- "${work_dir}"
  rm -f -- "${pid_file}"
}
trap cleanup EXIT
```

---

## Composition and Dispatch

Do not write a long `if`/`elif` chain to select behavior when a dispatch
table would be clearer — this is Bash's nearest equivalent to runtime
polymorphism.

A `case` statement is the default. It works on every Bash version and keeps
each branch visible:

```bash
case "${action}" in
  start) cmd_start "$@" ;;
  stop) cmd_stop "$@" ;;
  status) cmd_status "$@" ;;
  *)
    echo "unknown action: ${action}" >&2
    return 1
    ;;
esac
```

Use a dispatch table when the set of cases is data that something else also
reads, such as a generated help text or a list of valid subcommands:

```bash
declare -A handlers=(
  [start]=cmd_start
  [stop]=cmd_stop
  [status]=cmd_status
)

main() {
  local action="${1:-}"
  shift || true

  # Test for an empty key first: `${handlers[]}` is a "bad array subscript"
  # error that ends the whole script, even when the caller checks main's status.
  if [[ -z "${action}" || -z "${handlers[${action}]:-}" ]]; then
    echo "unknown action: ${action}" >&2
    return 1
  fi

  "${handlers[${action}]}" "$@"
}
```

Prefer composing small functions over building a deep chain of scripts that
`source` each other for indirection alone. Before adding another layer of
indirection, consider:

- A `case` statement
- A dispatch table (as above)
- A single function with clear early returns
- Splitting into a genuinely separate script only when it is also useful
  standalone

---

## Scoping and State

Minimize mutable shared state.

Prefer:

- `local` variables inside every function
- Explicit function parameters (`"$1"`, `"$2"`, ...)
- Explicit return values via `printf '%s\n'` captured with `$(...)`, or via
  an explicit exit status (prefer `printf` to `echo` for data: `echo`
  mangles values such as `-n` or strings with backslashes)
- A subshell `( ... )` to scope a `cd` or environment change

Avoid:

- Undeclared variables that become global by default
- Functions that read and write global variables instead of taking
  parameters
- `cd` inside a function without a subshell or a `popd`/`trap` to restore
  the caller's working directory
- Exported variables used as hidden inter-function channels

Avoid this:

```bash
current_user=""

set_current_user() {
  current_user="$1"
}

can_access_document() {
  local owner="$1"
  [[ "${owner}" == "${current_user}" ]]
}
```

Prefer this:

```bash
can_access_document() {
  local owner="$1"
  local user="$2"
  [[ "${owner}" == "${user}" ]]
}
```

Scope a directory change to a subshell so it cannot leak into the caller:

```bash
build_in() {
  local dir="$1"
  ( cd "${dir}" && make )
}
```

Always declare function-local variables with `local` (or `local -a`/
`local -A` for arrays) on their own line, since `local x=$(cmd)` masks
`cmd`'s exit status — see Error Handling.

---

## Error Handling

Use a clear error-handling strategy that is consistent with the surrounding
script and repository conventions.

Bash has no exceptions. Use exit status and `set -euo pipefail` as the
default safety net, and check status explicitly wherever `set -e`'s
well-known gaps apply (inside `&&`/`||` chains, command substitutions used
as a condition, and pipeline elements other than the last, unless
`pipefail` is set).

Start scripts meant to run unattended with:

```bash
#!/usr/bin/env bash
set -euo pipefail
```

Prefer explicit checks for expected, recoverable failures:

```bash
if ! output="$(curl -fsS "${url}")"; then
  echo "fetch failed: ${url}" >&2
  return 1
fi
```

Avoid silently discarding a command's failure:

```bash
# The exit status of `curl` is lost; `local` always succeeds.
local output=$(curl -fsS "${url}")
```

Prefer this instead, splitting declaration from assignment:

```bash
local output
if ! output="$(curl -fsS "${url}")"; then
  echo "fetch failed: ${url}" >&2
  return 1
fi
```

Use `trap ... ERR` when a script needs one centralized diagnostic on any
unexpected failure, in addition to (not instead of) specific checks on
expected failure paths:

```bash
on_error() {
  echo "error on line ${BASH_LINENO[0]}" >&2
}
trap on_error ERR
```

Add `set -E` (errtrace) next to `set -euo pipefail`: without it, the ERR trap is not
inherited by functions, command substitutions or subshells, and a failure inside a
function exits silently with no diagnostic.

The largest `set -e` gap: when a function is called as a condition
(`if my_func`, `my_func && ...`, `my_func || ...`, `! my_func`), errexit is
switched off for everything inside it, however deep. A failing command in the
middle of the function no longer stops it, and the function returns the status
of its last command:

```bash
set -euo pipefail

deploy() {
  false            # fails, but does not stop deploy() below
  echo "deployed"  # still runs; deploy() returns 0
}

if deploy; then
  echo "reported success"
fi
```

So a function whose result callers test must check its own steps explicitly
(`cmd || return 1`) rather than rely on `set -e`.

Two smaller traps. `((count++))` returns status 1 when `count` was 0, so under
`set -e` it ends the script on Bash 4.1+ (3.2 lets it pass); write `count=$((count + 1))`. And a command
substitution does not inherit `set -e` unless you also set
`shopt -s inherit_errexit` (Bash 4.4+), so a failing step inside `$(...)` does not
stop the steps after it.

Return non-zero from a function for expected failure; reserve `exit` for the
top-level script, so library functions stay usable when sourced.

For failures that need rich diagnostics, print to stderr and use a
consistent, documented exit-code convention across the script rather than
mixing ad hoc codes without a legend.

---

## Quoting and Const-Correctness

Quote every variable and command substitution unless word-splitting or
globbing is explicitly wanted, the same role `const` plays in C++ and type
hints play in Python: it communicates intent and prevents an entire class of
bugs.

Prefer:

```bash
rm -rf -- "${target_dir}"
```

Avoid:

```bash
rm -rf -- ${target_dir}
```

Use `readonly` or `declare -r` for values that must not change after being
set:

```bash
readonly MAX_RETRIES=3
```

Use `[[ ]]` instead of `[ ]` for conditionals — it does not word-split or
glob its operands and supports `&&`/`||`/pattern matching directly:

```bash
if [[ -n "${name}" && "${name}" =~ ^[a-z]+$ ]]; then
  ...
fi
```

Validate constrained values the same way the C++/Python guides validate a
`Color`'s channels — through a single checked entry point, not by trusting
every call site:

```bash
set_channel() {
  local -n channel_ref="$1"
  local value="$2"

  # Check the format before any arithmetic: `(( ))` treats a non-number as a
  # variable name (so "abc" becomes 0 and passes) and expands `$(...)` inside
  # array subscripts, which runs commands from untrusted input.
  if [[ ! "${value}" =~ ^[0-9]{1,3}$ ]] || (( 10#${value} > 255 )); then
    echo "channel out of range: ${value}" >&2
    return 1
  fi

  channel_ref="$((10#${value}))"
}
```

Validate the format of any external value with `[[ =~ ]]` before it reaches
`(( ))`, `$(( ))` or `let`, and limit its length: Bash arithmetic wraps on 64-bit
overflow, so a long digit string can pass a range check (`18446744073709551621`
becomes 5).

Quoting and `readonly` discipline together are what make a Bash script's
data flow legible without a type checker.

---

## Ownership and Isolation

Bash has no ownership model — every variable is a shared, mutable slot in
whatever scope holds it. Make sharing explicit instead.

Pass data into functions as parameters, not through ambient globals:

```bash
render_report(){
  local title="$1"
  local -n rows_ref="$2"
  ...
}
```

Use a subshell to isolate side effects (working directory, exported
variables, `set` options) that must not escape to the caller:

```bash
(
  cd "${build_dir}"
  export CFLAGS="-O2"
  make
)
```

Use a nameref (`local -n`) only when a function genuinely needs to modify a
caller's array or associative array in place, and document that it does —
callers should not have to read the function body to discover that their
variable will be mutated.

Avoid relying on `$?`, `$_`, or other transient state across more than the
next line; capture what you need immediately.

---

## Naming Guidance

Use names that describe the responsibility clearly.

Prefer verbs or verb phrases for functions:

```bash
parse_args() {
  ...
}

load_config() {
  ...
}

render_report() {
  ...
}

validate_input() {
  ...
}
```

Prefer nouns for variables and arrays:

```bash
local config_path
local -a input_files
local -A user_by_id
```

Avoid vague names:

```bash
do_stuff() {
  ...
}

handle() {
  ...
}

process() {
  ...
}

run() {
  ...
}
```

Use `UPPER_SNAKE_CASE` for constants and variables meant to be exported:

```bash
readonly MAX_RETRIES=3
export LOG_LEVEL="info"
```

Short names (`i`, `f`) are acceptable inside a small loop; use descriptive
names for anything with wider scope.

---

## File Organization

Keep scripts and sourced libraries focused.

A sourced library file should usually contain:

- One cohesive group of related functions
- No top-level side effects (so it is safe to `source` for its functions
  alone, e.g. in tests)
- A `source`-guard if it may be sourced more than once in the same shell

Example:

```bash
# lib/validate_config.sh
if [[ -n "${_VALIDATE_CONFIG_SH_INCLUDED:-}" ]]; then
  return 0
fi
readonly _VALIDATE_CONFIG_SH_INCLUDED=1

validate_config() {
  ...
}
```

Keep an executable entry-point script separate from the libraries it
sources, so the libraries stay testable in isolation:

```text
bin/deploy.sh       # thin entry point: parse args, call library functions
lib/deploy_steps.sh # the actual logic, sourced by bin/deploy.sh and by tests
```

Avoid catch-all files such as:

```text
utils.sh
helpers.sh
common.sh
```

These are acceptable only for a very small, clearly scoped set of
genuinely shared primitives (e.g. a single `log()` function).

---

## Testing Guidance

Prefer designs that are easy to test.

Keep functions that compute or transform data separate from functions that
perform I/O (network calls, file writes, `curl`, `psql`), so the former can
be tested without a live environment.

Avoid hidden dependencies that make tests fragile — the most common
offenders in Bash are reading directly from `$RANDOM`, `date`, environment
variables, or global state instead of taking them as parameters.

Prefer this:

```bash
is_expired() {
  local expiry_epoch="$1"
  local now_epoch="$2"
  (( now_epoch > expiry_epoch ))
}
```

Avoid this:

```bash
is_expired() {
  local expiry_epoch="$1"
  (( $(date +%s) > expiry_epoch ))
}
```

Use [Bats](https://github.com/bats-core/bats-core) (or an equivalent
Bash-testing framework already in the repository) for behavioral tests, and
run [ShellCheck](https://www.shellcheck.net/) on every script and sourced
library as a baseline lint before tests.

---

## External Tool Preference

Prefer well-established external tools over reimplementing their job in
pure Bash string manipulation — this is Bash's equivalent of preferring the
standard library over custom infrastructure.

Use:

```text
jq       # structured JSON, instead of grep/sed on JSON text
awk      # column/field processing, instead of nested string ops
sed      # stream text substitution
find     # file traversal, instead of hand-rolled recursive loops
xargs    # batching arguments into commands
mktemp   # safe temporary files/directories
getopts  # builtin option parsing (short options only), instead of a hand-rolled loop
```

Do not hand-parse JSON, YAML, or CSV with `grep`/`sed`/`cut` when a proper
parser (`jq`, `yq`, a real CSV tool) is available and already used
elsewhere in the repository.

Prefer builtins over external processes in a hot loop, since forking a
process per line is often the actual performance problem:

```bash
# Builtin substring, no fork per line.
while IFS= read -r line; do
  printf '%s\n' "${line#prefix-}"
done < "${file}"
```

Reach for Python, or another general-purpose language already used in the
repository, once a script's logic outgrows what Bash's string/array
handling can express clearly — forcing complex data structures or numeric
work into Bash is a sign the wrong tool was picked, not a Bash design
problem to solve with cleverer quoting.

---

## Comments and Documentation

Write comments to explain why, not what.

Avoid comments that repeat the code:

```bash
# Increment i by 1.
((i++))
```

Prefer comments that explain intent, constraints, or non-obvious decisions:

```bash
# Retry budget matches the upstream API's rate-limit reset window.
readonly MAX_RETRIES=3
```

Every script and every sourced library file should start with a header
comment explaining:

- What it does
- How to invoke it (arguments, expected environment variables)
- Any non-obvious preconditions (must run as root, must be sourced not
  executed, expects a specific working directory)

Example:

```bash
#!/usr/bin/env bash
# deploy.sh — build and push the release image, then trigger the rollout.
#
# Usage: deploy.sh <environment> [--dry-run]
# Requires: DOCKER_REGISTRY, DEPLOY_TOKEN environment variables.
set -euo pipefail
```

Avoid excessive comments around obvious code.

---

## Design Checklist

Before adding a new function, ask:

1. Does it name a real step in the workflow?
2. Is it reused, or does it need independent error handling?
3. Can it be tested without a live environment?
4. Would inlining it actually be clearer here?

Before adding an associative array or nameref, ask:

1. Is this genuinely grouped data, not a simulated object?
2. Would positional parameters be clearer for this many fields?
3. Does any field need validation on every write? If so, route writes
   through one function instead of touching the array everywhere.

Before adding another layer of sourced scripts, ask:

1. Is this genuinely reusable, or reused exactly once?
2. Would a `case` statement or a single function with early returns be
   simpler than another sourced file?
3. Is the dependency direction between scripts clear and one-way?

Before reaching for `set -e`/`trap` tricks, ask:

1. Is the failure expected (check explicitly) or truly exceptional (let
   `set -e`/`trap ERR` catch it)?
2. Does every acquired resource have a matching `trap`-based release?
3. Would splitting `local x=$(cmd)` into declaration and assignment change
   which failures are caught?

---

## Anti-Patterns to Avoid (recap)

Each is illustrated with a good/bad pair in its own section above — this is a
scan list, not new content: simulated object-orientation via namerefs and
prefixed globals (see Avoid Simulated Object-Orientation), catch-all
`utils.sh` files (see File Organization), unquoted variable expansion (see
Quoting and Const-Correctness), hidden global mutable state (see Scoping and
State), swallowed command failures via `local x=$(cmd)` (see Error
Handling), and reimplementing a structured-data parser in `grep`/`sed` (see
External Tool Preference).

---

## Summary Rule

As a default:

- Use functions for steps, side effects, and reusable or independently
  testable units.
- Use plain variables for single values and associative arrays for small
  groups of related fields.
- Do not simulate classes, inheritance, or objects with namerefs and
  prefixed globals.
- Use `trap` for guaranteed cleanup, the way RAII and context managers work
  elsewhere.
- Use a dispatch table or `case` statement instead of a long `if`/`elif`
  chain when the branches are genuinely data-driven.
- Quote everything; use `readonly` for values that must not change.
- Check expected failures explicitly; use `set -euo pipefail` and
  `trap ... ERR` as the safety net underneath, not the only mechanism —
  errexit is off inside any function called as a condition.
- Validate external values with `[[ =~ ]]` before arithmetic.
- Prefer established external tools (`jq`, `awk`, `sed`, `find`) over
  reimplementing structured-data handling in pure Bash.
- Prefer simple, readable, testable, idiomatic Bash — and reach for a
  different language once the logic outgrows what Bash expresses clearly.

When uncertain, choose the simpler design first. Add structure only when the
script clearly benefits from it.
