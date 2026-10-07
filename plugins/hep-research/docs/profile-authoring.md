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

## Companion plugin

A profile whose content only some people may read (for example access-controlled experiment software or data
listings) ships as its own plugin in a private repository, listed in the same marketplace, instead of inside this
plugin or the user's project. Such a companion plugin has:

- a plugin root that holds `profile/` (a complete profile in the layout above; it is also a valid local profile for
  `local_profile_paths`) and one skill, `skills/profile/SKILL.md`, named `<plugin>:profile`;
- a Claude Code manifest with `"dependencies": [{"name": "hep-research", "version": "^0.3"}]`, and a Codex manifest
  without dependencies (Codex installs both plugins separately);
- a `SKILL.md` whose description says it is a companion and never an entry point, and whose body states the profile's
  location as "the `profile/` folder under the folder two levels above this `SKILL.md`" (the companion plugin's root); both
  hosts tell the model the real path of the loaded `SKILL.md`, so no install path is written anywhere.

Resolution: when a project binds a profile that is neither registered nor in `local_profile_paths`, the context stanza
of every skill loads the installed `<plugin>:profile` skill that names it and treats the folder it gives as a local
profile; if none is installed the skill says the profile is unavailable and does not answer its topics from memory.
Validate the setup with `python3 contracts/project.py <project-dir> --local <companion plugin root>/profile`; the profile may
`depends_on` a registered profile (for example `experiment:ams-02`) and must satisfy the same schema and version checks.
The companion profile's modules must not link into this plugin's files by relative path; name the public profile and
module in prose instead. The first companion plugin is `ams02-research` (`experiment:ams-02-private`).
