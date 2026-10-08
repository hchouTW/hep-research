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
Keep local profiles read-only to the agent (the host loads them as instructions), and put non-public content in one
only for use under a project `agent_policy` that allows it on a qualified host configuration (none is qualified yet).

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
listings) ships as its own plugin in a private repository, distributed from its own source rather than this
marketplace, instead of inside this plugin or the user's project. Where a marketplace lists both, that is distribution
only, not a dependency. Such a companion plugin has:

- a plugin root that holds `profile/` (a complete profile in the layout above; it is also a valid local profile for
  `local_profile_paths`) and one skill, `skills/profile/SKILL.md`, named `<plugin>:profile`;
- no host-native dependency on hep-research in either host manifest or in a marketplace entry (no
  `"dependencies"` edge, bare, `name@marketplace` or with a version range): such an edge makes every host update of
  hep-research wait for the companion. hep-research is installed separately; `tools/check_host_manifests.py` fails on
  such an edge in the catalogs this repository owns;
- its own compatibility check (its preflight): the companion declares which hep-research versions it supports, in its
  own repository, and checks the hep-research root it is given before its profile is used. hep-research never reads a
  companion's package manifest or computes its supported range;
- a `SKILL.md` whose description says it is a companion and never an entry point, whose body states the preflight to
  run, and which states the profile's location as "the `profile/` folder under the folder two levels above this
  `SKILL.md`" (the companion plugin's root); both hosts tell the model the real path of the loaded `SKILL.md`, so no
  install path is written anywhere.

When the preflight runs: only when the current task uses the companion's profile, including a project whose
`local_profile_paths` entry is known to be that companion's folder (such a path is still routed through the companion
skill, so its preflight is not bypassed). Installing the companion, or doing unrelated hep-research work in a project
that contains its files, never triggers it, and hep-research never scans for companions at startup. A failed preflight
makes that profile unavailable; it does not stop other hep-research work. An ordinary user-written local profile that
no companion manages is validated generically and needs no preflight.

Resolution: when a project binds a profile that is neither registered nor a plain local profile, the context stanza
of every skill loads the installed `<plugin>:profile` skill that names it, runs that skill's preflight, and treats the
folder it gives as a local profile, but only when the project's `agent_policy` allows its content on this host and
destination; otherwise, or if none is installed or the preflight fails, the skill says the profile is unavailable and
does not answer its topics from memory. The companion's checker finds hep-research from the root it is handed; it does
not invoke skill discovery again.

Package compatibility and profile validation are separate checks. The companion's preflight decides whether its
package supports this hep-research release. The existing validators check the profile itself and need no new
interface:

```bash
# No research project is being checked.
python3 "<hep-research root>/contracts/registry.py" --local "<companion root>/profile"
# An explicitly selected project and its pins as well.
python3 "<hep-research root>/contracts/project.py" "<project-dir>" --local "<companion root>/profile"
```

Both print JSON with `ok` and exit 0 when valid and 1 with findings; an unreadable input, or an option given without
its value, exits 2 with an `error` object. A caller must still treat a crash or output that is not JSON as a failure.
The registry validator checks the whole registry plus the given folders, and the project validator the whole project:
a finding unrelated to the companion (for example the project's `plugin_version` range) keeps its own path and code
and must be reported as itself, not as a companion version mismatch. The same folder given twice (through
`local_profile_paths` and `--local`, or through a symbolic link) is one profile; two folders with one profile ID are
a `registry.duplicate_id` error. A profile may `depends_on` a registered profile (for example `experiment:ams-02`) and
must satisfy the same schema and version checks. Running these validators by hand checks a profile; it does not
certify a companion package or run its preflight.

The companion profile's modules must not link into this plugin's files by relative path; name the public profile and
module in prose instead. The first companion plugin is `ams02-research` (`experiment:ams-02-private`).
