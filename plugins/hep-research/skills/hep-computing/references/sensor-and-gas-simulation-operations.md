# Sensor and gas simulation operations: Allpix Squared and Garfield++

Operations guide for running Allpix Squared and Garfield++ through the optional `detector-simulation` adapter:
where an environment comes from, what a build needs, how to record the environment, the `detsim` command, execution
and troubleshooting. Which tool to use, what its result means and the physics of the two task cards are in the
hep-detector [sensor and gas transport tools](../../hep-detector/references/sensor-and-gas-transport-tools.md) guide;
read it first.

**Status (2026-11-02):** the `detsim` command and both backends ran their task cards' acceptance checks on one macOS
arm64 environment (Allpix Squared `df69a6a4`, Garfield++ `e2e58ea`, ROOT 6.40.04); any other version, platform or
configuration is **unverified**, and the command is described as specified (task specification 9.1 §9-§11, source
H-01). No output below is a result to reuse. Source IDs in brackets refer to
`docs/dev/detector-simulation/SOURCES.md` (plugin root). Replace "unverified" by the tested versions only after the
backend's acceptance tests pass in a recorded environment.

## 1. Problem, scope, preconditions

Problem: obtain a reproducible backend environment, pin a task to a plan, run it once per identity, and find out what
went wrong when it fails, without editing results by hand.

In scope: environment sources, build preconditions, environment records, the `detsim` verbs, run layout, exit
statuses, troubleshooting. Out of scope: physics choices (hep-detector), statistical use of the observables
(hep-statistics), gas-table generation, user Allpix Squared configurations, batch campaigns (later task cards).

Preconditions before any run:

- A project folder (`--workspace`) on a local file system: APFS or HFS on macOS; ext2/3/4, xfs, btrfs or tmpfs on
  Linux. NFS, CIFS, FUSE and unknown types are refused (`unsupported-fs`) [H-01 §6.2, §10.2].
- One backend environment obtained by a route of section 3 and recorded (section 5).
- The task card's pinned commit and inputs, and the hep-detector guide's version basis.
- Platform: the adapter's guarantees are measured on macOS only. On Linux (for example an EL9 node) the environment
  routes below exist, but the adapter's Linux guarantees are declared unsupported until measured on a Linux host, so
  a capability that requires one of them is refused there (`guarantee-insufficient`) [H-02].

## 2. Inputs

| Input | Form | Where it comes from |
|---|---|---|
| Task | `task.json` (`detector-task/1`): capability id, objective, environment reference, inputs, parameters, budget; unknown fields are rejected | written by the user for a capability (AP-BOOT, GF-QUERY) |
| Workspace | `--workspace <project>`; inputs resolve relative to it, never to the current directory | the research project |
| Native inputs | Allpix Squared: main configuration, detector setup, models, field map; Garfield++: one 1D gas table | files in the project, each hashed into the plan's input manifest; never committed to the plugin |
| Environment | the validation record `.env/<env_identity>.json` | `detsim check --probe` (section 6) |
| Plan | `plan.json` (`detector-plan/1`) and its `plan_digest` | `detsim prepare` |
| Replicate | `--replicate N`, default 0 | only for reproducibility tests; not part of the task or plan |

## 3. Environment sources

Building from source is the last resort: it is the largest cost of the first batch [H-01 §14.2]. Obtain and identify
each backend separately; the two need not share an LCG release.

| Backend | Route | Identity recorded | Notes (versions as read) |
|---|---|---|---|
| Allpix Squared | Docker image `gitlab-registry.cern.ch/allpix-squared/allpix-squared:<tag>`; host folder mounted at `/data` [AP-18, AW-06] | image digest | The tag must be the release that the pinned commit is; a development (master) commit such as `df69a6a4` has no release image; nightly `latest` images track master and are overwritten, so pin a release tag, build that commit from source, or use an image digest whose `allpix --version` (from `git describe --tags`, [AP-26]) names the pinned commit [AP-25]; Geant4 data sets complete; image architecture on Apple Silicon unverified |
| Allpix Squared | CVMFS: `source /cvmfs/clicdp.cern.ch/software/allpix-squared/<version>/<system-specifier>/setup.sh` [AP-19, AW-07] | version + platform + SHA-256 of `setup.sh` | Binaries only for CentOS 7 (GCC) and EL9 (GCC, LLVM), published per release; nightly `latest` builds track master and are overwritten, so a specific master commit is reproducible only from a source build or an image digest whose `allpix --version` matches the pin [AP-25]; not in LCG releases; CVMFS must already be mounted (never mount it yourself); **unverified**: no hep-research run has used this route |
| Allpix Squared | Source build | manifest digest | Linux and macOS stated by upstream [AP-17]; the only route for a development commit; needs explicit authorization to download and build |
| Garfield++ | LCG views | view name + platform + Garfield++ commit | The LCG package index lists releases 110a, 110, 109a, 109, 108a, 108, dev and SWAN variants; versions are commit abbreviations, not tags [GW-05, retrieved 2026-11-01] |
| Garfield++ | Source build (`gitlab.cern.ch/garfield/garfieldpp`) | manifest digest | Master `e2e58ea7` = tag `2026.10` + 4 commits [GF-01] |
| Both | `adapters/environments/` templates: LCG view setup and Apptainer definition (state `documented`) [H-04]; the [environments](environments-and-containers.md) page | manifest digest | Estimate build time and disk first |

An installed Garfield++ ships its headers (`Include/Garfield/*.hh`): they give signatures and defaults, not the
interpolation stencil. GF-QUERY pins the interpolation order and extrapolation methods of the table's own footer (order 2,
constant low, linear high for the example table), read from the implementation source at the pinned commit [GF-02].

## 4. Build preconditions (from the upstream sources; unverified on this plugin's hosts)

**Allpix Squared** at master `df69a6a4` [AP-16, AP-17, AP-20]:

- C++20 compiler (GCC 11+, LLVM/Clang 10+, AppleClang 13+).
- ROOT 6 built with C++20 (`-DCMAKE_CXX_STANDARD=20`), with the `GenVector` component (CMake asks for Geom, Core,
  GenVector, Hist, RIO).
- Boost.Random >= 1.64.0 (portable random distributions; older `normal_distribution` implementations differ).
- spdlog >= 1.9.2: required by master's build script (`CMakeLists.txt` line 326) although the master prerequisites
  page does not list it; **not** required by release `v3.3.0` [AP-16, AP-20, AP-21]. Take the dependency list from
  the build script of the version you build, not only from the manual.
- Geant4 built with C++20, with **all** data sets installed, and multithreading enabled if MT runs are wanted.
  Upstream's suggested flags include `-DGEANT4_INSTALL_DATA=ON`, `-DGEANT4_USE_GDML=ON`,
  `-DGEANT4_BUILD_MULTITHREADED=ON`, `-DCMAKE_CXX_STANDARD=20`.
- Eigen3 (Runge-Kutta in propagation modules).

**Garfield++** at master `e2e58ea7` [GF-09, GF-10, GF-11]:

- ROOT 6 (`find_package(ROOT 6.0 REQUIRED …)`, `CMakeLists.txt` line 94; line 97 only branches on ROOT < 6.20 for
  compatibility), CMake >= 3.12, a C++ compiler with the same C++ standard as ROOT, a Fortran
  compiler; GSL only with `GARFIELD_WITH_GSL`; OpenMP optional.
- After `make install`, source `<install>/share/Garfield/setupGarfield.sh`: it sets `HEED_DATABASE` and
  `CMAKE_PREFIX_PATH`.
- Python use goes through PyROOT: `import ROOT` then `import Garfield` after sourcing the setup script (the GF-QUERY
  query script prefers this; a compiled driver is the fallback).

Record build flags, compiler, ROOT and Geant4 versions with the manifest; a rebuilt library is a new environment.

## 5. Record the environment

- `detsim --backend <name> check --workspace <project> --probe --env-root <environment root>` validates and records an
  environment: it hashes the backend's programs, libraries and data, runs `environment_manifest.py record` itself
  for the path-bearing part, and writes the record; you do not run those scripts yourself.
- The **environment root** is one folder (typically a folder of symbolic links, a "view") with a fixed layout, because
  plans name only paths under it:
  - Allpix Squared: `allpix/` (the install: `allpix/bin/allpix`, `allpix/lib/`), `geant4/`, `root/`, `deps/` and
    `data/<data set folder>` for every data set of `geant4-config --datasets` (Allpix Squared requires all of them,
    including G4NDL [AP-16]).
  - Garfield++: `bin/python3` (a Python with ROOT's bindings), `root/` (the ROOT prefix), `garfield/` (the install),
    and a build record `detsim-garfield-build.json` at the root, written by whoever built Garfield++:
    `{"format": "detsim-garfield-build/1", "garfield_commit": "<40-hex commit of the built source>",
    "library_sha256": "<SHA-256 of garfield/lib/libGarfield…dylib>"}` (plus the build options if known). The probe
    refuses `environment-unpinned` without it; the commit is the builder's statement and is recorded as such.
- `describe` prints the layout and variables a backend expects.
- Environment variables are recorded by name, never by value.
- The validation record lives at `artifacts_root/detector-simulation/.env/<env_identity>.json`; the identity is
  content-based, so reaching the same installation through another path does not change it [H-01 §9.1].

## 6. The `detsim` command

`detsim` below stands for running the adapter's entry file `adapters/detector-simulation/assets/detsim` (a Python
file, suffix `.py`) with a Python 3.13 or newer; there is no console script. The interpreter matters for one backend:
**Allpix Squared's results are read with ROOT's Python bindings inside `detsim`**, so its verbs must run under a
Python that has them (for example a Homebrew Python matching the ROOT build, with `PYTHONPATH` set to ROOT's library
folder); without them `check --probe` answers `missing-dependency`. Garfield++ runs its own Python from the
environment root, so any Python 3.13+ runs `detsim` for it. Clear any ROOT setup inherited from a login shell
(`ROOT_INCLUDE_PATH`, `ROOTSYS`, `LD_LIBRARY_PATH`, a ROOT `PYTHONPATH`) before running ROOT or `detsim`:
`ROOT_INCLUDE_PATH` pointing at another SDK's C++ headers breaks ROOT's interpreter. Backends themselves always run with
exactly the plan's variables, so the login environment never reaches them. `--backend allpix-squared` or
`--backend garfieldpp` selects the backend; parameters come from the capability schema, never from free argv or
shell [H-01 §11.1].

| Verb | Does | Writes |
|---|---|---|
| `describe` | capability, version, limitations, `required_guarantees` | nothing |
| `check` | static and semantic checks of the task and workspace; `--probe` also probes the backend and records the environment | `.env/<env_identity>.json` with `--probe` |
| `prepare` | prints the pinned plan and `plan_digest`; `--digest-only [--replicate N]` prints only the run digest as `parameter_digest` | nothing (stateless) |
| `run` | rebuilds and compares the plan, takes the run lock, snapshots inputs, executes, collects, commits | `runs/<run_id>/` or `failed/…` |
| `inspect` | `--view state` (committed, in progress, stale, failures, orphans), `--view summary` (results and observables), `--attempt <id>` (a failure's completeness evidence) | nothing, and it never signals a process |

Usage, as specified:

```bash
detsim --backend allpix-squared check   --workspace <project> --probe --env-root <environment root>
detsim --backend allpix-squared check   --workspace <project> --task task.json
detsim --backend allpix-squared prepare --workspace <project> --task task.json > plan.json
detsim --backend allpix-squared run     --workspace <project> --plan plan.json [--plan-digest <sha256>] [--replicate N]
detsim --backend allpix-squared inspect --workspace <project> --run <run_id> --view state|summary [--attempt <id>]
```

For GF-QUERY, `--allow-outside-validated-range` on `check` / `prepare` sets the task parameter
`allow_outside_validated_range` (it is part of the plan's identity). Output is always one JSON object with `status`,
a stable `error_code`, the location of the problem and diagnostics; large outputs are never printed.

**Identity.** The same plan and replicate always give the same `run_id` (first 32 hex characters of the run digest).
A new seed is a new plan; running the same plan again is a retry; `--replicate N` (default 0) is only for
reproducibility tests [H-01 §9.3].

**Where results land.** `artifacts_root` is the project's artifacts folder: `artifacts_dir` of
`hep-research.project.json` if the project has one, else `<workspace>/hep-research-artifacts/`. `prepare > plan.json`
saves the answer (`status`, `plan_digest`, `plan`); `run` accepts that file or the bare plan.

**Layout** under `artifacts_root/detector-simulation/` [H-01 §9.6]: `runs/<run_id>/` (exists only after a successful
commit: `run.computational-run.json`, `plan.canonical.json`, `completeness.json` — **the card's check results** —
`observables.csv`, `manifests/`, `input/`, `logs/`, plus the backend's own output: `output/` and `extract/` for Allpix
Squared, `query/` and `raw/` for Garfield++), `failed/<run_id>-<UTC ms>-<nonce>/` (same inner layout, kept), and the hidden `.pending/` (lock
records, attempt folders, `orphans/`) and `.env/`. Read results only from `runs/` or through `inspect`; never from
`.pending/`.

The development record of the adapter ships with the plugin under `docs/dev/detector-simulation/`: `TASK.md` (the
specification the command's help and `describe` cite by section), the pinned task cards `card-AP-BOOT.md` and
`card-GF-QUERY.md`, the source index `SOURCES.md` and the support matrix `SUPPORT-MATRIX.md`.

## 7. Execution

1. `check --probe --env-root <root>` once per environment; its answer gives the `env_identity` for the task.
2. Write the task (examples below) and `check` it; then `prepare > plan.json`; keep the plan with the task.
3. `run --plan plan.json --plan-digest <digest>`. A second `run` of the same plan returns the committed result
   (`reused: true`) without launching. The `run_id` is the first 32 hex characters of
   `prepare --digest-only [--replicate N]`'s `parameter_digest`, so it is known before running.
4. The card's checks are in `runs/<run_id>/completeness.json` (`state: complete` when every check passed); the
   observables are `runs/<run_id>/observables.csv` (also `inspect --view summary`, which prints all rows).
5. Check the files against the record with the contracts layer's run verifier (`verify_run` in the plugin's
   `contracts/` folder, given the record `runs/<run_id>/run.computational-run.json`); the contracts validator
   (`validate` there, given the artifacts folder) validates the records (it warns about non-JSON outputs, which are named in
   the record's `output_hashes`).

**Task file (`detector-task/1`).** One JSON object; unknown fields are rejected; physical quantities are
`{"value": "<decimal string>", "unit": "<unit>"}`, never binary floats:

```json
{"schema": "detector-task/1", "capability_id": "allpix.pixel-charge",
 "objective": "AP-BOOT: pinned rerun of the official Allpix Squared example (pipeline validation only)",
 "environment_ref": "<env_identity from check --probe>",
 "inputs": [{"role": "config", "path": "inputs/example.conf"}, {"role": "detector", "path": "inputs/example_detector.conf"},
            {"role": "field", "path": "inputs/example_electric_field.init"}],
 "parameters": {"random_seed": 1, "number_of_events": 10, "multithreading": false},
 "budget": {"timeout_s": 120, "max_output_bytes": 67108864}}
```

For GF-QUERY the capability is `garfield.gas-table-query`, the input role is the one `describe` names for the table,
and the parameters hold the query fields (`{"value", "unit": "V/cm"}`), B = 0, the table's temperature and pressure,
the interpolation settings of the table's footer and, optionally, `allow_outside_validated_range`; `describe
--backend garfieldpp` lists the exact names. When the example table is used, the objective must contain "example
table, pipeline validation only". Node fields are the table's E/p values times its pressure in Torr, computed in double
precision (for the example table 100.000002 and 80000.0016 V/cm, not 100 and 80000); the query must include the
first node, the last node and an interior node, so an out-of-range task is the in-range task plus the outside points.

**Comparing replicates (AP-BOOT check 2).** Run the same plan with `--replicate 0` and `--replicate 1`; compare the two
runs' `extract/pixel_summary.json` with the backend's `compare_summary_files` (its docstring gives the one-line
command); it lists per-pixel values from both runs. A different seed is a new task and plan; its comparison must
differ.

In a workflow, `detsim run` can be an opaque [workflow](analysis-workflows.md) step whose `parameter_digest` command is
`detsim prepare --digest-only` and whose only output is its `stdout` answer (a design decision of the task [H-02]). The step
timeout (default 3600 s) bounds it; the incremental skip works only where the plugin release digest is known, so in a
development checkout the step always reruns.

**Agent time limits.** If the plan's budget timeout plus 60 s fits under the host's foreground tool limit, run in the
foreground with an explicit tool timeout; otherwise run in the background and poll `inspect --view state` no more
often than every 30 s (`inspect` needs `--run <run_id>`). A background command stopped by the host is a controller
death, not a result [H-01 §10.5]. The first-batch runs take seconds (about 4 s for AP-BOOT, 2 s for GF-QUERY on the
tested host), so they run in the foreground.

**Platform guarantees.** On macOS the controller's death does not kill the backend (`soft`); commit without
overwriting is `hard` with `renamex_np`; durable commit is `soft`; Linux guarantees are declared `unsupported` until
measured on a Linux host [H-02]. The run record states the achieved level of each guarantee; cite
those fields, never a word such as "isolated".

## 8. Statuses and troubleshooting

Exit codes are only 0-3; `status` and `error_code` tell cases apart [H-01 §11.3, H-03]. An exit without parseable
JSON on stdout means `detsim` itself crashed or was killed from outside. `failed` and `refused` share exit 1; only
`failed` writes a run record (under `failed/`); `refused`, `rejected` and `missing-dependency` write none [H-01 §11.3].

| `status` / `error_code` (exit) | Meaning | What to do |
|---|---|---|
| `ok` (0), maybe `reused: true` | completed and complete, or the committed result returned | read `runs/<run_id>/`; look at `orphans_reported` if present |
| `rejected` (2) | malformed task, unknown field, unreadable plan, `unsupported-fs`, usage error | fix the input or move the workspace to a local file system |
| `refused` / `plan-stale` (1) | code, environment record, profile or an input changed since `prepare` | run `prepare` again; the mismatched fields are listed |
| `refused` / `digest-mismatch` (1) | `--plan-digest` does not match the plan | use the digest `prepare` printed |
| `refused` / `guarantee-insufficient` (1) | the capability needs a guarantee this platform's profile does not give | run on a platform whose profile has it; never downgrade the requirement |
| `refused` / `input-changed` (1) | an input's hash differs from the plan's manifest at snapshot | restore the input or `prepare` a new plan |
| `refused` / `run-id-collision` (1) | `runs/<run_id>/` holds a different plan | investigate; nothing was overwritten |
| `refused` / `out-of-domain` (1) | a GF-QUERY point outside the table's E range; the valid range is reported | drop the point, or set `allow_outside_validated_range` knowingly (rows get `outside-validated-range`) |
| `refused` / `condition-mismatch` (1) | GF-QUERY temperature or pressure differs from the table's | use the table's conditions or a table made for yours |
| `refused` / `interpolation-mismatch` (1) | GF-QUERY interpolation order or extrapolation methods differ from the table footer | use the footer's values |
| `refused` / `extrapolation-undefined` (1) | exponential extrapolation requested on a side whose end velocities are not both positive | use another table |
| `rejected` / `node-coverage` (2) | the query points lack the first node, the last node or an interior node of the table | add those points |
| `rejected` / `table-format` (2) | the gas table cannot be parsed in the pinned storage form | use an intact 1D table |
| `rejected` / `note-missing` (2) | the pinned example table is used without "example table, pipeline validation only" in the objective | add the note |
| `refused` (3) | the protected-use guard refused before anything ran | follow the project's protected-data policy |
| `missing-dependency` (3) | backend program, ROOT bindings, library or Geant4 data set missing, found before the lock | fix the environment (sections 3-5); nothing ran |
| `failed` / `missing-dependency` (1) | a library failed to load after the lock | a run record exists with the `failed` label; fix and rerun the same plan |
| `incomplete` / `in-progress` (3) | another controller holds the run lock | wait; poll `inspect --view state` |
| `failed` (1), e.g. `cancelled`, `commit-conflict`, timeout, partial | the run did not produce a complete result | read `failed/…` with `inspect --attempt <id>`; rerunning the same plan is a retry |
| `failed` (1) with native exit 0 | required outputs missing although the program succeeded | treat as a failure; never as a result |
| `error` / `internal` (2) | an exception inside `detsim` | report it with the JSON diagnostics |

`inspect --view state` shows `stale` when the lock is free but the last record is not finished (the controller died).
Leftover backend processes are shown with pid and start time and are **never** signalled by `detsim`; stop them
yourself after checking that the pid still names that process. `failed/` and `.pending/orphans/` may be cleaned by
retention policy; `runs/` never [H-01 §15.3].

Common environment problems (from the upstream prerequisites; unverified here): ROOT built with another C++
standard than the backend; a Geant4 without all data sets or with another C++ standard (Allpix Squared); a missing
`HEED_DATABASE` because `setupGarfield.sh` was not sourced (Garfield++); `import Garfield` failing because the
library directory is not on the loader path.

## 9. Outputs, checks and limitations

- Outputs per run: the computational-run record (with `plan_digest`, `run_id`, replicate, achieved guarantees and its
  sidecars), the canonical plan, the completeness result and a long observables table. Their schemas are added by
  the shared-layer work items.
- Checks that the plumbing worked: the record validates with `contracts/validate.py`; output hashes match
  the recorded ones (the contracts layer's run verifier); the card's own checks (hep-detector guide, section 7) pass. Passing checks show software
  consistency, not physical validity.
- Limitations: unverified throughout; macOS host only; no batch execution, cross-session recovery or cancel command
  (deferred to later work); no container isolation, so no claim of "no network".

## 10. Citations

`docs/dev/detector-simulation/SOURCES.md`: Allpix Squared prerequisites, supported systems, Docker and CVMFS pages and
build script [AP-16 … AP-21, AW-06, AW-07]; Garfield++ installation, readme and build script [GF-09 … GF-11]; LCG package
index [GW-05]; task specification 9.1 [H-01]; the task ledger's design decisions [H-02]; repository status codes
[H-03]; environment templates [H-04].
