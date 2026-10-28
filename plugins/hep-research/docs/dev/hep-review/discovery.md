# hep-review v9: T00 discovery note

Written 2026-10-29 in the worktree `~/hep-research/.claude/worktrees/hep-review-v9` (branch `hep-review-v9-impl`,
base `main` = `42f5bad16e87a66518e5ead2a738a1fe9a59e787`, the 0.43.0 release merge). Spec references are to
`hep-review-v9-en.md`; this file is the deliverable of spec §1.2 step 3.

## 1. Source and versions

| Item | Observed |
|---|---|
| Repo root | `~/hep-research` (Git; remote `origin` = github.com/hchouTW/hep-research). The plugin lives in `plugins/hep-research/`; every spec path (`contracts/`, `skills/`, `tests/`, `tools/`) is relative to that plugin root |
| Plugin version | 0.43.0 (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `pyproject.toml`) |
| Contracts version | 3.14.0 (`contracts/__init__.py` `CONTRACTS_VERSION`) |
| Skills | eight: hep-measurement, hep-detector, hep-theory, hep-statistics, hep-computing, hep-ml, hep-citations, hep-authoring (`contracts/skill_names.py` `SKILLS`, `contracts/schemas/skill_names.json`) |
| Installed cache | `~/.claude/plugins/cache/hep-research-dev/hep-research/0.43.0/`: same eight skills, no hep-review. Read only (listing); never modified |
| Instructions files | No AGENTS.md or CLAUDE.md in the repo. Rules come from `docs/maintenance.md`, `pyproject.toml`, the tools under `tools/` and the user's global instructions (hep-research skills; merge only with separate authorization) |
| Main checkout state before T00 | branch `main`, clean (0 porcelain lines); 4 linked worktrees (`.claude/worktrees/crprop-k`, `-k1`, `-k2`, `-k4`, other sessions' work, untouched); no submodules |

## 2. Existing hep-review code and the difference table (case N04)

No file in the source tree or the installed 0.43.0 cache is named hep-review or implements this specification
(`grep -rl hep-review` matches only the authoring review harness tests, where the string is part of
"independent review" prose, not this skill). The spec's §1.5 premise "the user has said a hep-review skill has been
added" does not hold for this base: there is nothing to integrate and nothing is overwritten.

Neighbouring existing code that the new work must not disturb or be confused with:

| Existing | What it is | Relation to hep-review v9 |
|---|---|---|
| `contracts/review.py`, `contracts/schemas/review_*.json` (`review_record`, `review_event`, `review_head`, `review_manifest`, ...), `skills/hep-authoring/scripts/review.py` + `review_lib/` | The authoring independent review of a draft (docs/dev/independent-review-spec.md): its own driver, event log with file locks, receipt and format | Kept as is. New names use the `hep_review` prefix (`contracts/hep_review.py`, `contracts/schemas/hep_review_*.json`) so they never collide. The new format is not fed into the old receipt; no compatibility is claimed (spec §1.5) |
| `review_lib/store.py` `default_private_root()` = `$XDG_STATE_HOME/hep-research/reviews` (default `~/.local/state`) | The repository's convention for private per-user state | Followed for the hep-review store location (§5 below) |

Difference table between the spec's §1.5 baseline (0.42.0, read-only inspection) and this base (0.43.0 source):

| Spec §1.5 row | Observed now | Consequence |
|---|---|---|
| pyproject: Python >= 3.13, not an installable package | Same (`requires-python = ">=3.13"`, `packages = []`) | Use the existing environment; no packaging |
| skill_names.py: eight names | Same eight names, contracts 3.14.0 | Adding `hep-review` touches: `SKILLS`, `schemas/skill_names.json`, `core/OWNERS.json` only if it stewards core (it will not), routing cases (`tests/routing/make_cases.py`), capability map, README counts, wiring (`tools/check_wiring.py`), SKILL.md budgets (`tools/measure_entrypoints.py`), skill lists in tests (T03 step 2, case N16) |
| schema.py: a subset incl. oneOf and maxItems; unknown keywords may be ignored | `SUPPORTED_KEYWORDS` = $ref, anyOf, oneOf, not, type, const, enum, minLength, pattern, minimum, exclusiveMinimum, maximum, exclusiveMaximum, x-vocab, required, properties, additionalProperties, minItems, maxItems, items. `tests/contracts/test_schema_keywords.py` fails any schema using a keyword outside these and the annotation set. `integer` excludes bool | New schemas use only these keywords (case N11); `uniqueItems`, `maxLength`, `propertyNames`, `dependentRequired` etc. are enforced in Python. `schema.load_schema` reads files, so the pure kernel takes schemas as already-loaded dicts or uses Python checks |
| check_layering.py | contracts -> contracts, core (+ stdlib); skills/<s>/scripts -> core, contracts, never another skill; text rules forbid experiment names and profile ids in core skill text outside example blocks | `contracts/hep_review.py` imports only stdlib (and possibly `contracts.schema`); the skill's scripts import `contracts.hep_review`; no experiment names in skill text |
| independent-review-spec.md | Present (authoring review) | Not reused (above) |
| VALIDATION.md | Historical records, 7,470 lines | Old results say nothing about hep-review |

## 3. Interfaces and conventions found

- **Script contract** (`core/status.py`, hep-computing SKILL.md): JSON on stdout with a `status` key; exit 0 ok, 1
  negative verdict (`refused`), 2 bad input (`rejected`), 3 missing dependency or incomplete. Scripts locate files
  from their own path and write only to given output paths. The hep-review CLI follows this.
- **Packaging** (`tools/check_packaging.py`, scans every tracked file under the plugin root, `docs/dev` included):
  no `/Users/...` or `/tmp/claude...` paths, no `*.jsonl`, no file name matching `rubric|answer[-_]?key|grading`,
  no archive, nothing over 2 MiB, README package size within 10%. Consequences: run documents use `~`-relative paths;
  spike answer keys are named `expected-*.json`; the README size line may need refreshing when files are added.
- **Tests**: unittest only (`python3 -m unittest <module>`); `tools/run_all_checks.py` runs each test module in its own
  process; fast and slow tiers (`HEP_SLOW_TESTS=1`). Test packages have empty `__init__.py`; naming a package alone
  runs 0 tests.
- **Lint**: CI runs ruff 0.16 and mypy 2.4 on `core/` and `contracts/` (pyproject `[tool.ruff]`, `[tool.mypy]`);
  `contracts/hep_review.py` must pass both.
- **Selective CI**: `contracts/rules/registry.json` impact groups; a new path not covered runs the full suite (safe).
- **Skill discovery**: Claude Code and Codex discover skills by folder (`.codex-plugin/plugin.json` `"skills":
  "./skills/"`); the plugin descriptions say "seven core skills" (stale but not ours to change in T00).

## 4. Platform probe (step 8) and the spec §1.5 premises on this machine

Probe script kept in the session scratch (not committed: it is a one-off measurement); its output:

| Item | Value |
|---|---|
| Python | 3.13.2 (conda-forge build) |
| SQLite | 3.51.1 |
| git | 2.50.1 (Apple Git-155) |
| Platform | darwin |
| `os.open in os.supports_dir_fd` | true |
| `O_NOFOLLOW`, `O_DIRECTORY`, `O_NONBLOCK` | all present |

| Spec §1.5 premise | Linux container (spec) | This Mac |
|---|---|---|
| `object_pairs_hook` sees decoded duplicate keys (`"id"`, `"id"`) | yes | yes |
| `json.loads(bytes)` accepts BOM / UTF-16 / UTF-32 / raw lone surrogate | accepts | accepts all four |
| `-0` | becomes 0 | becomes 0 |
| `"\ud800"` escape | parses, fails at encode | parses, fails at encode |
| `isinstance(True, int)` | True | True |
| 200,000 nesting levels | RecursionError | RecursionError |
| `BEGIN IMMEDIATE` after `connect(autocommit=False)` | fails | fails ("cannot start a transaction within a transaction") |
| `BEGIN IMMEDIATE` with `isolation_level=None` | works | works |
| `os.open("link/f", O_NOFOLLOW, dir_fd=root)` with symlinked parent | opens | opens |
| FIFO with `O_NONBLOCK` | no block, `S_ISREG` false | no block, `S_ISREG` false |
| `git rev-parse --git-dir --git-common-dir` in a subdirectory of a main checkout | one absolute, one `../.git` | same (absolute `.../repo/.git` and `../.git`); with `--path-format=absolute` both equal |

Every premise holds here, so the spec's stdlib-only strict ingestion, the `isolation_level=None` transaction mode and
the component-by-component opening (§9.2) apply unchanged. The rev-parse probe ran in a scratch repository in the
session temp folder, not in the user's main checkout (the host refuses git commands aimed at the main checkout from
this worktree session, which is itself a useful isolation property).

## 5. Store location (step 9; spec §11.1)

| Item | Value |
|---|---|
| Path | `~/.local/state/hep-research/hep-review` (`$XDG_STATE_HOME/hep-research/hep-review` when set; unset here) |
| Why not `~/Library/Application Support` | Spec §11.1 lets T00 fix the path per repository convention; the repo's existing private state uses XDG_STATE_HOME on every platform. Both are local, non-synced |
| Filesystem | APFS, local, journaled (`df` -> `/dev/disk3s5` on `/System/Volumes/Data`); no nfs/smb/fuse/9p/virtiofs mounts exist on this host (`mount`) |
| Sync folders | `~/Library/CloudStorage` holds one Google Drive mount; `~/Library/Mobile Documents` not used. The store path is under neither and contains no Dropbox/OneDrive/Google Drive component |
| Persistence | marker `hep-review-persistence-marker` written 2026-10-28T22:32:23Z; `store_persistence: pending-next-session` until a later session reads it back (T0S H5) |

## 6. Host capabilities known before T0S (spec §12.2)

Claude Code CLI on macOS with: the Agent tool (fresh-context subagents, background by default), file Read/Write/Edit
tools, a Bash tool, and worktree tools. Subagents share this machine's filesystem. Whether they can read each other's
drop files and transcripts, whether transcripts are writable by reviewers, real parallelism and hash capability are
measured in T0S (host-profile.md).

## 7. Isolation record (cases N01, N02, N40)

- N01 (worktree cannot be created): not triggered; the worktree was created and confirmed. Behaviour on failure is
  the hard stop of the task file §4.1; recorded as not-applicable-with-basis for this run.
- N02 (already in a linked worktree; main has dirty files or submodules): the session started in the main checkout
  (clean, no submodules), so detection had to decide "main checkout, create a new worktree". No reset, clean or
  stash was run anywhere; other sessions' worktrees were left alone.
- N40 (detection in a subdirectory of the main checkout): measured on a scratch repo: unnormalized output differs
  (`.../.git` vs `../.git`), `--path-format=absolute` output is equal, so it is identified as the main checkout and
  not reused. From inside the new worktree: `.git/worktrees/hep-review-v9` vs `.git` (different), no superproject.
