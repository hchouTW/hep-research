# Writing a profile

A profile adds knowledge about one experiment or one theory domain without changing any skill, `core/` or
`contracts/` code. Two small shipped profiles are the templates: `profiles/experiments/synthetic-collider/`
(experiment) and `profiles/theory/qed-benchmark/` (theory domain). `experiment:ams-02` shows a large one.

## Layout

```
profiles/<experiments|theory>/<name>/
  profile.json        # metadata, validated by contracts/schemas/profile.json
  index.md            # short routing map: request -> file to read (budget 4 KiB)
  conventions.json    # units, frames, level and normalization definitions, namespaced keys
  modules/ ...        # topic files read only when a request needs them
  evidence/sources.json, evidence/claims.json   # ledger with <namespace>:S01 / :C01 ids
  datasets/, benchmarks/, scripts/, tests/      # as needed
```

Private profiles use the same layout but live in the researcher's project and are named in
`hep-research.project.json` under `local_profile_paths`. Never copy one into the plugin; `contracts/project.py` rejects that.

## profile.json

Required fields: `id` (`experiment:<name>` or `theory:<name>`), `kind`, `version` (SemVer), `scope`, `exclusions`,
`compatible` (core and contracts ranges), `related_skills`, `resources` (at least `index` and `conventions`),
`vocabulary_extensions`, `adapters` (`required`, `optional`; ids `adapter:<name>`), `depends_on`, `evidence_namespace`,
`maintainer`, `capabilities`. Mark invented content with `"illustrative": true` and say so in `scope`.

## Vocabulary extensions

Core vocabularies (`contracts/vocab/core.json`) cover levels, normalization kinds, conventions and statuses. A profile
adds terms only in its own namespace, for example `synthcol:fiducial_definition`, listed in `vocabulary_extensions`
and `vocabulary_namespaces`. A term outside the profile's namespace is rejected (`profile.vocab_namespace`). The
comparison gate treats a namespaced convention key on one side only as "not comparable" until a mapping with a
justification is declared.

## Evidence

Every factual statement in modules cites a ledger claim (`<ns>:C07`), and every claim cites a source (`<ns>:S03`)
read at a stated level. Keep three dates apart: the current date, the publication or data-taking date, and the
verification date. A source newer than the verification date is unverified, not nonexistent. Never invent values:
a dataset record without published numbers is metadata only. Check a ledger with
`python3 core/evidence/ledger.py --sources evidence/sources.json --claims evidence/claims.json --namespace <ns>` and
render its index with `core/evidence/render_index.py`.

## Capability states

Each capability names one state from `contracts/vocab/core.json`:

| State | Meaning | Needs |
|---|---|---|
| `proposed` | design only | nothing runnable |
| `documented` | guidance text exists | the text |
| `demonstrated-on-synthetic-data` | runs on synthetic inputs | tests listed in `tests` that exist |
| `tested-in-declared-environment` | runs in a named environment | tests and the environment recorded in VALIDATION |
| `unavailable` | needs something missing (tool, licence, data) | the reason in `scope` |

`contracts/registry.py` rejects a demonstrated or tested capability without existing tests (`profile.unbacked_capability`).

## Tests and registration

1. Put tests in `<profile>/tests/`; `tools/run_all_checks.py` runs every registered profile's suite.
2. Add one line to `profiles/registry.json` (`id`, `kind`, `version`, `scope`, `path`; the registry stays under 2 KiB).
3. Run `python3 contracts/registry.py` (duplicate ids, versions, missing resources, escaping paths, cycles, budgets)
   and `python3 tools/check_layering.py` (no skill, core or contract file may name the profile).
4. Run `python3 tools/run_all_checks.py --out <dir>` and add the capability to `docs/capability-matrix.md`.

Adding a profile must not need a change outside `profiles/`, `examples/` and `tests/examples/`; if it does, the
change belongs in a reviewed core or contract release first (AC10 records the check for the synthetic collider).
