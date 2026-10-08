# Maintenance

Run everything from the plugin root. The aggregate check is the gate for any change:

```bash
python3 tools/run_all_checks.py --out <dir>      # layering, stanzas, registry, ledger, AMS-optional, routing (static),
                                                 # packaging, budgets, host validator, unit and profile tests
python3 tools/check_relocation.py --out <dir>    # the same from a copy at a path with spaces and another cwd
```

For a subset of the unit tests name the modules (`python3 -m unittest tests.tools.test_check_packaging_size`) or
use `python3 -m unittest discover -s tests/tools -t .`; naming only the package (`python3 -m unittest tests.tools`)
runs 0 tests, because the test packages have empty `__init__.py` files.

Tests come in two tiers. The fast tier is the default. `HEP_SLOW_TESTS=1` adds the slow tier (for example the full
Feldman-Cousins tables, the 10,000-mutation contract fuzz and the full theory-comparison example). `run_all_checks.py`
runs each test module in its own process with a time limit (`--module-timeout`, default 600 s) and records every
module's duration; a fast-tier module listed under `slow_modules` (over 60 s) belongs in the slow tier. Every
subprocess call in the tests and tools has a timeout (`tests/tools/test_subprocess_timeouts.py`).

Software checks show contract consistency only, not physical validity. Report pass, fail, skip and unverified
separately; a skipped test (missing tool) is unverified, never passing.

## SKILL.md size budget

Every `SKILL.md` must stay at or under 8,192 bytes (`tools/measure_entrypoints.py`, run by `run_all_checks.py`).
Two are close: `detector-response` (8,185 B) and `hep-statistics` (8,138 B). Plan to cut each by at least 10%
(to about 7,360 and 7,320 B) before adding anything to them. Byte counts below were measured on 2026-10-08:

- `detector-response`: move the seven astroparticle reference links (461 B) and the four lookup references
  (glossary, bibliography, comparison tables, case studies) into an index in `detector-principles-summary.md`,
  keeping one link to it (saves about 600 B); tighten the Invariants and Workflow wording (about 250 B).
- `hep-statistics`: the script paragraph under Resources is 1,419 B; keep the script names and move what each one does
  to `references/core-stats-guide.md`, which already documents `core/stats` (saves about 770 B); tighten the reference
  list (about 100 B).

Both cuts change what the model reads before it acts, so they need the routing checks (`check_routing_static.py`,
`check_ownership.py`) and a rerun of the answer evaluations that measured these skills before they are merged.

## Porting a fix

1. Reproduce the defect with a failing test first.
2. Fix in the owning location: the general method in its owner skill or `core/` module (`core/OWNERS.json`);
   experiment or domain specifics in the profile. Never fix the same method in two places.
3. Commit scientific corrections separately with the `sci-fix:` prefix and the regression test; pure moves use
   `move:`. Never silently clip negative bins, repair covariance or response matrices, invent correlations, or change
   cuts, weights, binning, bounds or constants.

## Rerunning comparisons and examples

Each example writes byte-reproducible output with its seed and tolerances; run `python3 examples/<name>/run.py`
from the plugin root (each takes `--help`; the seeds are in each `output/report.md`). The researcher journey each one exercises:

| Example | Journey |
|---|---|
| `examples/ams-flux-ratio/` | J1 |
| `examples/detector-resolution/` | J2 |
| `examples/collider-angular/` | J3 |
| `examples/qed-prediction/` | J4 |
| `examples/theory-comparison/` (run after B and C) | J5 |
| `examples/published-comparison/` | J6 |
| `examples/recasting/` | J7 |
| `examples/local-partition/` | - |
| `examples/batch-partition/` (fake Slurm and HTCondor schedulers) | - |
| `examples/end-to-end-sample/` | - |
| `examples/unfolding-coverage/` | J3 |

`tests/examples/` compares a fresh run with the
committed output. When a change alters a committed number, explain why in the commit, regenerate the output, and
record the old and new values; a change beyond the declared tolerance is a breaking change.

## Evidence ledgers

Update sources and claims through the ledger files, keep ids stable (renaming an id is breaking), set the
verification date to the day the source was read, then run `core/evidence/ledger.py` and regenerate the index with
`core/evidence/render_index.py`.

## Schema migration

Contracts carry `CONTRACTS_VERSION` (`contracts/__init__.py`) and each artifact records the plugin, contract and
profile versions it was written with. Adding an optional field or vocabulary term is a minor change. Removing or
renaming a field, changing a default convention, or tightening a rule so old artifacts fail is a major change and
needs: a converter that rewrites old artifacts with explicit refusal codes for what it cannot convert, valid and invalid
fixtures in `contracts/fixtures/`, and an entry in the changelog of the release.

Readers apply a version policy (`contracts/validate.py`, since 2.1.0): a newer major is an error; a newer minor is a
warning, or an error with `--protected`; `versions.contracts` must equal `contract_version`; an unknown entry in
`required_capabilities` is an error (add new capabilities to `contracts.KNOWN_CAPABILITIES` when a reader implements
them). `contracts/dependencies.py` validates every source the same way. Artifacts record the code identity in
`versions.plugin_release` through `contracts/identity.py`; older artifacts lack it and their identity is unknown.

## Versioning

SemVer for the plugin (`.claude-plugin/plugin.json`), contracts, core (`core/__init__.py`), each profile and each
ledger. A profile states the core and contract ranges it supports (`compatible`); the registry check rejects an
incompatible pair. Projects pin a plugin range in `hep-research.project.json`.

## Adapter changes

Follow `docs/adapter-authoring.md`: bump the adapter version, rerun its tests in the declared environment, update
`adapter.json`, `VALIDATION.md` and the capability matrix.

## Routing

`tests/routing/cases.json` is generated by `tests/routing/make_cases.py`; `tools/check_routing_static.py` checks it
against the descriptions. A change to a skill description should be followed by a live routing run (paid model
calls, run only with approval); the G5 record in the source repository shows how it was done.
