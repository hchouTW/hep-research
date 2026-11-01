# detsim integration progress ledger

Spec version: 9.1

## Isolation record

| Item | Value |
|---|---|
| Main checkout | `~/hep-research` (branch `main`, HEAD `cf622dab`, clean) |
| Task worktree WT | `~/hep-research-detsim` |
| Work root WR | `~/hep-research-detsim-work` |
| Branch | detsim-integration |
| Base ref and commit | `origin/HEAD` (after `git fetch origin`) `25a8dbe6bfe426b9cac52733e5487625d213f056` (hep-research 0.53.0 release merge) |
| Parent folder PARENT | `~` |
| Installed plugin (never written) | `~/.claude/plugins/cache/hep-research-dev/hep-research/0.52.0` (the folder this session loaded skills from) |
| Git version; `core.hooksPath`; hooks present | git 2.54.0 (Apple Git-157); `~/hep-research/.githooks` (`check-paths.sh`, `pre-commit`, `pre-push`); no hooks in the common `hooks/` folder besides samples |
| Plugin root PR | `<WT>/plugins/hep-research` |
| `git status --porcelain` of MAIN at W0 | empty (0 lines) |
| Isolation guard at W0 | pass, 2026-11-01T11:59Z; fails from MAIN ("not running inside .../hep-research-detsim"); byte-identical to §2.4 (`diff` empty) |
| Interpreter and venv | `~/miniconda3/bin/python3` 3.13.2 (`find_python.py`); `WR/venv` with `--system-site-packages`; `requirements-core.txt` and `requirements-test.txt` installed (numpy 2.4.4, scipy 1.17.1, sympy 1.14.0); `import ROOT` works (Homebrew ROOT 6.40.04) |
| Baseline test run | `python3 tools/run_all_checks.py --no-cli --out "$WR/scratch/baseline"` from PR: 31 pass, 0 fail, 2 skip (host CLIs); units 6342 run, 6132 passed, 210 skipped, 0 failures, 0 errors; no pre-existing failure |

## W1 reuse table (§7, V-01) — base `25a8dbe6` (plugin 0.53.0, contracts 3.17.0, `CORE_VERSION` 1.5.0)

Evidence scripts and outputs: `WR/scratch/W1/` (`w1_probe.py` → `out/w1_probe.json`, `v04_probe.py` → `v04.json`,
`geant4-register.json`, `envman.json`, `wf/`). Every cited file exists at the base.

| Component | Classification | Evidence |
|---|---|---|
| computational-run (`contracts/schemas/ext_computational_run.json`) | reuse directly | required fields as §7; `parameter_digest` pattern `^[0-9a-f]{64}$`; no `additionalProperties` (extension open). A synthetic A-shaped and a G-shaped record with `plan_digest`, `run_id`, `replicate`, `sidecars` pass `contracts/validate.py` on an artifacts dir (exit 0); a sidecar named only as an `output_hashes` key gives `artifacts_dir.not_artifact` (exit 1) |
| `contracts/verify_run.py` | reuse directly | replaced output → `mismatch`, exit 1 |
| `contracts/schema.py` | reuse directly (with code checks) | `SUPPORTED_KEYWORDS` = $ref, additionalProperties, anyOf, const, enum, exclusiveMaximum, exclusiveMinimum, items, maxItems, maximum, minItems, minLength, minimum, not, oneOf, pattern, properties, required, type, x-vocab; other keywords ignored; `pattern` via `re.search` (anchor every pattern) |
| `contracts/dependencies.py` | reuse directly | present; used through `contracts/validate.py` for upstream artifacts |
| `canonical_sha256` (4 copies) | reuse directly + `check_hash_scope` in front | the four copies give identical digests on the probe vectors; `float("nan")` is hashed without error (allow_nan default) → the hash-scope checker is needed |
| `run_workflow.py` | optional host (D-W1-1) | `parameter_digest` {argv, replaces}, `timeout_s` (default 3600), `HEP_RUN_WORKFLOW_ATTEMPT`, stdout file exempt (lines 593–670); fixture `wf/`: the digest is recorded in the step record and the stdout answer is not in `output_hashes` |
| `core/partition/engine.py` | pattern only | `dir_lock` present; `_write_atomic` uses `os.replace` (overwrites); no `F_FULLFSYNC` |
| `core/provider/` (`cr-provider/1`) | pattern only (D-W1-5) | `--allow-outside-validated-range`, `out-of-domain`, label `outside-validated-range` (entrypoint.py:11-17, conformance.py:14-15) |
| `core/hostcaps.py` | reuse directly | on this host `process_groups()` true, `proc_fs()` false, `posix_ids()` true; `require`, `UnsupportedPlatform` present |
| `executor_capabilities.py`, `control_layer.py` | not applicable | — |
| `core/status.py` | reuse directly | `EXIT_CODES` (0,1,2,3); `_NO_ARTIFACT` = error, missing-dependency, not-run, refused, rejected; labels include `failed`, `unvalidated`, `outside-validated-range` |
| `adapters/geant4/` `geant4_build.py register` / `check` | reuse as subprocess | host Geant4 11.4.3 (`~/Workspace/geant4-work/build-b/install`): register refused while G4NDL4.7.1 is absent from the installation; with `--skip-dataset G4NDL` status ok, `check` ok (exit 0) |
| `adapters/environments/`, `environment_manifest.py` | reuse as subprocess | `record --packages numpy` → recorded; `check --manifest` → `same` |
| `frontend_response` | not applicable (cite in K) | — |
| `core/simulation/seeds.py` | pattern (Allpix seeds) | present |
| `core/simulation/summary.py` | not reused (D-W1-2) | accumulators per run, not a long table |
| profiles / protected data | reuse directly | `contracts/protected_use.py` `guard_report`, `core/protected/guard.py` `detect` |
| partition, batch schedulers | not applicable | — |

R-07 checks (V-01): (a) `core/status.py` codes 0–3 confirmed; (b) `docs/adapter-authoring.md` present, adapters optional; (c) `contracts/vocab/core.json` and `ARTIFACT_LABELS` present; (d) `contracts/schemas/` + contracts version 3.17.0; (e) CHANGELOG `## 0.53.0` / VALIDATION present; (f) `semantic-naming.md` present; (g) `docs/routing-contract.md`, `docs/capability-map.json` present; (h) `tools/check_layering.py` line 9: adapters may import only core and contracts; (i) `docs/capability-matrix.md` rows and `tests/adapters/test_adapter_{declarations,missing_dependency}.py` present; (j) `contracts/validate.py` `_referenced_paths` follows string values only (line 2962) — confirmed by the key-only probe; (k) layering experiment-name rule present; (l) `tools/reference_inventory.py`, `skills/hep-detector/references/detector-simulation.md` present; (m) `tools/skill_scripts.py`, `tools/insert_interpreter_guard.py`, `tests/tools/test_python_compat.py` present; (n) `.githooks/` active via `core.hooksPath` (W0 commit passed them); (o) `core/hostcaps.py`, `tests/_platform.py` present.

Environment availability (2a): Allpix Squared — not installed; obtainable under H0 #5 (source build into `WR/env`, started). Garfield++ — not installed; obtainable under H0 #5 (source build, started). Neither is blocked at W2 step 1 for lack of permission.

## Subagent worktrees

| Key | Item | Path | Branch | Base commit | Patch folder | State |
|---|---|---|---|---|---|---|
| WK | WK | `~/hep-research-detsim-sub-WK` | detsim-sub-WK | `e480371cbe36929a0c08e2979778ff367b943007` | `WR/patches/WK/` | applied (WK, WK-2) |
| W3a | W3a | `~/hep-research-detsim-sub-W3a` | detsim-sub-W3a | `e480371cbe36929a0c08e2979778ff367b943007` | `WR/patches/W3a/` | applied (3 patches) |

## Environment reconnaissance

Host: Darwin arm64 (macOS 27.2), 8 CPUs, Python 3.13.2, git 2.54.0, CMake 4.3.2, Apple clang 21.0.0; 406 GiB free on `~`. Variables present (names only): `ROOTSYS`.

| Backend | Found here | Obtainable with H0 permission | Notes |
|---|---|---|---|
| Allpix Squared | no (`allpix` not on PATH) | yes, source build (H0 #5) into WR: needs spdlog >= 1.9.2 and Boost >= 1.64 (random), both absent, built into `WR/env/deps`; Geant4 11.4.3 source install with datasets at `~/Workspace/geant4-work/build-b/install`; ROOT 6.40.04 (Homebrew); Eigen 3 (Homebrew) | no CVMFS (`/cvmfs` absent), no container runtime (docker, podman, apptainer, singularity absent) |
| Garfield++ | no | yes, source build (H0 #5) against Homebrew ROOT 6.40.04 and GSL | ROOT Python bindings present (`import ROOT`) |

## Authorization (H0)

| # | Question | Answer | Source | Time |
|---|---|---|---|---|
| 1 | Clone / fetch the hep-research repository | yes (fetch done; editable checkout exists, no clone) | default | 2026-11-01 |
| 2 | Shallow-clone upstreams for reading | yes, read-only (blob-less clones in `WR/upstream`) | default | 2026-11-01 |
| 3 | Container images | no | default | 2026-11-01 |
| 4 | Mounted CVMFS | yes, read-only (none mounted) | default | 2026-11-01 |
| 5 | Build backends from source, download sources and Geant4 data | **yes, both backends, default budget (2 h and 20 GB per environment)** | user | 2026-11-01 |
| 6 | pip into `WR/venv` | yes, only there | default | 2026-11-01 |
| 7 | G0 platforms | current host (macOS); Linux declared soft or unsupported until measured | default | 2026-11-01 |
| 8 | Guide language | English | default | 2026-11-01 |
| 9 | Budget | environment 2 h and 20 GB; one test run 10 min | default (confirmed by user) | 2026-11-01 |
| 10 | Loop bounds | as in §3.4; **review rounds per item raised to 3** (gate H5, 2026-11-01) | default; user for the review bound | 2026-11-01 |
| 11 | Push / PR when finished | **push, open a PR, merge and release when the task ends done and CI is green** | user | 2026-11-01 |
| 12 | Owners of §15.3 | the user, every role | default | 2026-11-01 |
| 13 | Example gas table `ar_80_co2_20_0T.gas` | yes, under the two conditions (local input only; pipeline validation only) | default (user decision 2026-10-30) | 2026-11-01 |

## Work status

| Work item | Status | Last updated | Cycles / review rounds used | Evidence (test IDs, commits, files) | Missing |
|---|---|---|---|---|---|
| W0 | done | 2026-11-01 | 0 / 0 | T-WT (this ledger, isolation record) | |
| W1 | done | 2026-11-01 | 0 / 0 | W1 reuse table; V-01..V-06; D-W1-1..5; WR/scratch/W1 | |
| WK | in-progress | 2026-11-01 | 0 / 2 | patches WK (d3ee1c15), WK-2 (8628dc11), round-2 fixes 8abe2652; T-DISCOVER (WR/scratch/WK/t-discover.txt, raw); question set run 2: 19/20, Q05 partial (dc8f1d42) | review round 3; question set rerun |
| W2-AP | in-progress | 2026-11-01 | 0 / 0 | V-07, V-14 read at df69a6a4; G4NDL 4.7.1 in WR/env/g4data (MD5 54f0ed39 matches) | environment (V-08): ROOT with a working interpreter, Allpix build |
| W2-GF | in-progress | 2026-11-01 | 0 / 0 | card-GF-QUERY.md (query points and tolerances fixed before any query); V-09..V-12 read at e2e58ea | environment (V-13): ROOT with a working interpreter |
| W3a | in-progress | 2026-11-01 | 0 / 2 | patches 5ca7dbd1, 3fd54f69, 510315a5; review fixes 2468b15e (round 1), ff6a077e (round 2); 62 + 2 tests | review round 3; VALIDATION entry |
| W3b | in-progress | 2026-11-01 | 1 / 0 | 5fda61cd, d6dc4c66: detsim_platform, detsim_runner, detsim_run, run/inspect/check --probe; tests/adapters/test_detsim_run.py 45 tests (1 skipped: Linux only) | T-CONV complete, review |
| W4A | not-started | | 0 / 0 | | |
| W4G | not-started | | 0 / 0 | | |
| W5 | not-started | | 0 / 0 | | |

## To-verify results

| V-ID | Conclusion | Evidence (repo, commit, file:line or URL + date) | Affected sections |
|---|---|---|---|
| V-01 | Confirmed on base `25a8dbe6`: every §7 file and R-07 item present with the stated boundary (table "W1 reuse table") | WR/scratch/W1/out/w1_probe.json; files cited in the table | §7, R-07 |
| V-02 | Mechanism present: `parameter_digest` {argv, replaces}, stdout exemption, `timeout_s` default 3600, attempt token. The incremental skip also needs a known plugin-release digest (INC-03, `skip_reason`, line ~510), so in a development checkout a detsim step always reruns; in a released install it can skip | run_workflow.py:19-46, 116, 488, 509-535, 593-670; fixture WR/scratch/W1/wf (2026-11-01) | §8.3 |
| V-03 | Add `detsim-observables/1` (D-W1-2) | core/simulation/summary.py (accumulators per run) | §9.5 |
| V-04 | Measured on macOS 27.2 arm64, APFS: `renamex_np(RENAME_EXCL)` via ctypes refuses an existing empty dir (EEXIST) and renames to a new name; plain `os.rename` replaces an empty dir; `fcntl.F_FULLFSYNC` available and succeeds; `statfs$INODE64` `f_fstypename` = `apfs` (`/dev` = `devfs`); no `prctl`. Linux mechanisms not measured (no Linux host) | WR/scratch/W1/v04.json | §6.2, §10.3 |
| V-05 | Layout fits: `adapters/<name>/` with flat assets; layering lets adapters import core and contracts only; no `core/` change needed | tools/check_layering.py:9,153-155; core/OWNERS.json admission rule | §8.6 |
| V-06 | Mapping recorded in D-W1-5 | core/provider/entrypoint.py:11-17; conformance.py:14-15 | §12.3 |

## Decision log

| Time | Work item | Decision (incl. D-W1-n) | Reason | How to revert |
|---|---|---|---|---|
| 2026-11-01 | WK | Entry points through the registered hubs `detector-simulation.md` (hep-detector §11 lists it; reachable from the SKILL.md row "Simulation (Geant4)") and `analysis-workflows.md`; no new row in `detector-principles-summary.md` §11 (its routing part is 4081 B of the 4096 B soft limit; nine other hep-detector references are also reached through hubs) | review round 1 F4, round 2 confirmed as a decision | add a §11 entry after trimming that page |
| 2026-11-01 | WK | `detsim` is named without a `.py` token in skill text until R-07 (m) is handled for it in W3b/W5 (skill_scripts list, interpreter guard) | review round 1 F15 | name the file and regenerate the skill-script list |
| 2026-11-01 | W3a | D-W3a-4 (canonical/1 rule): `$NAME` references are refused only for an upper-case NAME (plus `${…}` and `$(`), so `#/$defs` and lower-case words after `$` in free text pass; a task string starting with `/`, `~` or a drive letter is refused anywhere, including `objective` (free text starting with "~" must be reworded) | review round 1 F3, round 2 | widen or narrow the regular expression |
| 2026-11-01 | W3a | F7: the T-PLAN clauses "wrong --plan-digest → digest-mismatch" and "plan-stale → refused, exit 1" are tested at library level in W3a and through `main()` in W3b (test_detsim_run ExitTable) | review round 1 F7 | — |
| 2026-11-01 | W3a | F9: the shared-layer hash scope is the set of `detsim*.py` modules declared in `adapter.json` "assets"; an undeclared or a declared-but-missing module is error/internal | review rounds 1-2 | glob again |
| 2026-11-01 | W3a | F5: a record that is not a detsim-env/1 document is `rejected` (environment-record-unreadable); a well-formed record that contradicts itself (identity hash, host paths) is `refused` (environment-record-invalid) | review rounds 1-2 | — |
| 2026-11-01 | W2 | Homebrew ROOT 6.40.04's interpreter (cling) crashes on the macOS 27 SDK (even a trivial rootcling), which blocks the Garfield++ dictionary, the Allpix object dictionaries and PyROOT; gate H1 answered by the user: build ROOT 6.40.04 from source in WR. First attempt against MacOSX26.5.sdk failed (C++ modules mixed SDK headers); second attempt with the Xcode SDK and `runtime_cxxmodules=OFF` | WR/scratch/rootcling-test, WR/env/root/build*.log | use another ROOT |
| 2026-11-01 | W2 | Garfield++ build: `GARFIELD_WITH_EIGEN=OFF`, examples/tests/docs/CUDA off; Allpix build: `BUILD_GDMLOutputWriter=OFF` (the host Geant4 has no GDML; AP-BOOT does not use the module) | build logs in WR/env | turn the options back on |
| 2026-11-01 | W2-AP | Allpix requires `G4NEUTRONHPDATA` to name an existing folder (GeometryBuilderGeant4Module.cpp:106-117 at df69a6a4); G4NDL 4.7.1 downloaded into `WR/env/g4data` (official MD5 54f0ed39…), never written into the Geant4 installation | V-08 | — |
| 2026-11-01 | WK | Question set run 1 (20/20) superseded: it predated the review fixes; run 2 graded 19/20 (Q05 omits "unverified") | review round 2 B1 | — |
| 2026-11-01 | W0 | Base is `origin/HEAD` = `25a8dbe6` (0.53.0), not the spec's `bf5e453` (0.51.0 + unreleased) | §2.3 step 3 takes the current `origin/HEAD`; W1 re-checks every repository fact on this base | rebase onto another base |
| 2026-11-01 | W0 | Upstream clones are blob-less (`--filter=blob:none`) rather than `--depth 1` | keeps tags, so `git describe` (used by the Allpix version string) works; still read-only | reclone shallow |
| 2026-11-01 | W1 | D-W1-1: `detsim run` can be an opaque `run_workflow.py` step with `parameter_digest` from `detsim prepare --digest-only` and only its `stdout` answer as output; incremental skip works only where the plugin release digest is known (released installs) | V-02 fixture | run detsim directly |
| 2026-11-01 | W1 | D-W1-2: add `detsim-observables/1` (do not reuse `simulation-summary/1`) | the summary contract holds per-run accumulators; GF-QUERY and AP-BOOT need one row per value with unit, decimal string, query point or event, label and source hash | reuse summary contract (H3 not needed, schema only) |
| 2026-11-01 | W1 | D-W1-3: `macos-g0` (measured): controller death terminates backend **soft**; commit without overwriting **hard** (`renamex_np` RENAME_EXCL, fallback soft); durable commit **soft** (F_FULLFSYNC files, dir fsync best effort); local fs check **hard** (apfs, hfs allowlist via statfs); input hashes before/after hard; timeout kill of own process group hard; output-size abort soft; descendants killed soft; no_network unsupported. `linux-g0`: declared, every level **unsupported** until measured on a Linux host (H0 #7) | V-04 | declare levels differently after measuring |
| 2026-11-01 | W1 | D-W1-4: §8.6 layout as written (`adapters/detector-simulation/`, owner `hep-detector`, flat modules); no `core/` change | V-05 | — |
| 2026-11-01 | W1 | D-W1-5: GF-QUERY takes from `cr-provider/1` the refusal default (`out-of-domain` with the valid range), the option `--allow-outside-validated-range` (here also a task parameter in the hash scope), the label `outside-validated-range` and the one-process batch shape. Not taken: the cosmic-ray request shape, the provider registry and its cache (detsim's identity replaces it), the conformance suite (detsim has its own T-GF). No generalisation of the protocol | V-06 | — |
| 2026-11-01 | W1 | Host Geant4 lacks G4NDL; whether AP-BOOT needs it is settled in W2-AP (FTFP_BERT_LIV uses no neutron HP data); never modify the installation | W1 register probe | — |
| 2026-11-01 | W0 | Environment builds (H0 #5) started after the baseline finished, before W2 formally starts | builds take hours; starting them early only writes into `WR/env`; W2 records and pins what they produce | delete `WR/env/{allpix,garfield,deps}` |

## Gate queue

| Gate | Question | Blocked work | Suggested options | Status |
|---|---|---|---|---|
| H1 | ROOT with a working interpreter: Homebrew ROOT's cling fails on the macOS 27 SDK | W2-AP, W2-GF, W4A, W4G | build ROOT from source in WR; conda-forge ROOT; block | answered 2026-11-01: build from source in WR |
| H5 | Review-round bound reached for WK and W3a (2 rounds, findings fixed) | WK, W3a and their dependents | raise to 3 or 4; keep 2 | answered 2026-11-01: raised to 3 |

## Delivery reports

```text
Work item ID: W0
Status: done
Isolation guard: pass at end of W0 (from WT); fails from MAIN, as required
Files changed: docs/dev/detector-simulation/TASK.md (copy of the spec), docs/dev/detector-simulation/PROGRESS.md
Decisions made (with reasons): see decision log (base 25a8dbe6; blob-less clones; early builds)
Commands actually run and results: git inspection of MAIN (clean, branch main, hooksPath .githooks); git fetch origin;
  git worktree add -b detsim-integration WT 25a8dbe6; WR created with isolation.env and isolation-guard.sh (identical
  to §2.4); venv with --system-site-packages + requirements-core/test; guard pass; baseline run_all_checks --no-cli:
  31 pass / 0 fail / 2 skip, units 6342 (6132 passed, 210 skipped, 0 failures)
Tests not run and reasons: none
V-items concluded / still open: none for W0
Independent review: not applicable
Blockers and gates raised: none
Next step: W1
```

```text
Work item ID: W1
Status: done
Isolation guard: pass at start / pass before commit
Files changed: docs/dev/detector-simulation/PROGRESS.md
Decisions made (with reasons): D-W1-1..5 (decision log)
Commands actually run and results: w1_probe.py, v04_probe.py, geant4_build.py register/check, environment_manifest.py
  record/check, run_workflow.py fixture (WR/scratch/W1); results in the W1 reuse table and the To-verify table
Tests not run and reasons: Linux mechanisms of V-04 (no Linux host)
V-items concluded / still open: V-01..V-06 concluded
Independent review: not applicable
Blockers and gates raised: none
Next step: WK, W2-AP, W2-GF, W3a
```

## Final report

(E.3, written in Phase 3)
