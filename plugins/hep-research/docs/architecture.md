# hep-research Architecture

Status: M1, 2026-10-02. Responsibilities here are fixed; file names may still move before G1 approval.

## 1. Components (v1)

| Component | v1 | Why |
|---|---|---|
| Skills | Seven core skills under `skills/` | Description-routed entry points; plugin namespace `hep-research:<skill>` `[Confirmed]` (host fact 3) |
| Shared resources | `core/`, `contracts/`, `profiles/`, `adapters/` read on demand via `${CLAUDE_PLUGIN_ROOT}/...` | The whole plugin root is installed as one cached directory `[Confirmed]` (host fact 4), so no per-skill copies are needed |
| Commands | None | Skills supersede commands `[Confirmed]` (host fact 8); D10 |
| Hooks, MCP servers, background processes, required subagents | None | No implicit activity; handoffs are files |

## 2. Ownership

Core skill ownership and contested-topic resolution are restated per skill in each `SKILL.md` ("Owns", "Never", handoff table). Implementation stewards for shared code are in `core/OWNERS.json`:

| core module | Steward | Status |
|---|---|---|
| kinematics | hep-theory | implemented |
| stats | hep-statistics | implemented |
| blinding | hep-computing | implemented |
| evidence | research-communication | implemented |

Admission rule: code enters `core/` only when more than one top-level component uses it; experiment and theory-domain specifics never do.

## 3. Layers and directions

```text
core/                 -> core (+ stdlib, numpy, scipy, matplotlib, sympy)
contracts/            -> contracts, core (+ same environment)
skills/<s>/scripts    -> core, contracts           (never another skill)
profiles/<p>          -> core, contracts, declared depends_on profiles
adapters/<a>          -> core, contracts
examples/ tests/ tools/ -> anything
```

`[Proposal]` refinement: `contracts/` may import `core/` (the registry checks `core.CORE_VERSION`), while `core/` never imports `contracts/`, so `core/` stays the lowest layer.
Enforced by `tools/check_layering.py` (AST imports + text scan + schema scan + steward check); negative fixtures in `tests/tools/test_check_layering.py` (T23). Experiment and theory selection are independent axes (0/1/many each) in the project config; there is no global experiment or model field.

## 4. Contracts (single canonical location: `contracts/`)

| Piece | File | Notes |
|---|---|---|
| Vocabularies | `contracts/vocab/core.json`, `contracts/vocab.py` | levels, normalization kinds (no collider-only default), quantity types, bin semantics, statuses, derivation statuses, uncertainty kinds, missing markers (`unknown` / `not-applicable` / `not-provided`), convention keys, evidence statuses, verification levels, capability statuses. Profiles extend only with namespaced terms. |
| Observable spec, binned data, conventions block | `contracts/schemas/common.json` | Shared by measurements, predictions and dataset records |
| Envelope | `contracts/schemas/envelope.json` | Versions, bindings, provenance, status labels, inputs (with their statuses), handoff, unresolved inputs |
| Typed extensions | `contracts/schemas/ext_*.json` | measurement-spec, response, theory-spec, prediction, dataset-record, comparison-spec, statistical-result, ml-artifact, computational-run, communication |
| Validator | `contracts/validate.py` | Schema subset engine (`contracts/schema.py`) + semantic rules (status propagation, double-counted corrections, auto-Gaussianized envelopes, paradigm completeness, synthetic labelling, theory independence) |
| Registry and profiles | `contracts/registry.py`, `schemas/registry.json`, `schemas/profile.json` | Two-tier registry, templates, compatibility, escape and cycle checks |
| Project config | `contracts/project.py`, `schemas/project_config.json` | Resolution order, local profiles, pins, overrides with provenance |
| Evidence | `contracts/evidence.py`, `schemas/evidence_*.json` | Profile-qualified IDs; verification date distinct from publication and current dates |
| Comparison gate | `contracts/comparison/` | `gate.py` (observable, level, unit, convention and transformation checks), `conventions.py`, `composition.py`, `combination.py`, `model_set.py` |
| Context stanza | `contracts/stanzas/context-resolution.md` | Inserted into each SKILL.md by `tools/build_stanzas.py`; drift fails the checks |

Serialization (D6): JSON, stdlib-parseable. The strict-YAML subset reader is used only by the AMS-02 profile (`profiles/experiments/ams-02/scripts/yaml_subset.py`).

## 5. Versioning

SemVer for plugin (`0.1.0`), contracts (`1.1.0`, `contracts.CONTRACTS_VERSION`), core (`1.0.0`, `core.CORE_VERSION`), each profile, and each evidence ledger. Breaking (major): removing or renaming fields, changing a convention default, changing numerical results beyond declared tolerance, renaming evidence IDs. Every artifact envelope records plugin, contract and profile versions.

## 6. Runtime mechanics

- Skills reference shared files as `${CLAUDE_PLUGIN_ROOT}/...` (resolved inline in skill content, host fact 4).
- Scripts locate the plugin root from `__file__` (`Path(__file__).resolve().parents[N]`), never from cwd; outputs go to an explicit directory outside the plugin.
- Project state lives in the researcher's project (`hep-research.project.json`, `artifacts_dir`); `contracts/project.py` rejects local profiles or artifacts inside the plugin.

## 7. Loading budget (measured)

`tools/measure_entrypoints.py` on 2026-10-02: seven SKILL.md files 4.4–6.0 KiB each (budget 8 KiB), descriptions 773–919 characters (working budget 1,024), registry 47 B, host estimate **~2,005 always-on tokens** for all seven descriptions (`claude --plugin-dir ... plugin details hep-research`). SKILL.md line counts (47–60) are below the 100–180 guide because paragraphs are unwrapped; bytes are the binding budget. Drafts will grow in M2 when references are routed.

## 8. Risk register

| ID | Risk | Mitigation and check | M1 state |
|---|---|---|---|
| R1 | Misrouting by description | Deliverable-first descriptions with exclusions; routing cases M5 | Descriptions written; static check M5 |
| R2 | AMS profile becomes a monolith | Template + 4 KiB index budget + load traces | Template enforced by validator |
| R3 | `core/` dumping ground | Admission rule; stewards; layering check | Steward check active |
| R4 | Vocabulary too rigid | Namespaced extensions; "not comparable" default | T25 tests pass |
| R5 | Standalone skills with similar names and the plugin both trigger | Namespacing confirmed in docs; G5 live test | Partly mitigated |
| R6 | Host format drift | Verified facts dated; `claude plugin validate --strict` in checks | Active |
| R7 | Theory capability perceived broader than v1 | Capability statuses; limited-support stanza | Active |
| R8 | Collider/AMS terms leak into core | Vocabulary + schema-term scan + experiment-name scan | Active, found and fixed 2 leaks in M1 |
| R9 | Private data leaks into the package | Local profiles rejected inside plugin; packaging scan M5 | Partly |
| R10 | Always-on cost grows | Host estimate recorded each run | ~2,005 tok |
| R11 (new) | A profile adds vocabulary under a namespace shared by several profiles (e.g. a cosmic-ray namespace) | `vocabulary_namespaces` must be declared; validator rejects undeclared namespaces | Active |
| R12 (new) | Fixtures inside the package look like real profiles or private data | Fixture IDs prefixed `fixture-`, objectives marked SYNTHETIC; project fixtures are copied to a temp dir before loading | Active |
| R13 (new) | Headless traces may not expose skill loads (host fact 7) | Fall back to tool-use events in stream-json at M5 | Open |

## Verified Claude Code plugin facts (task Section 5.1)

Source for "verified locally": Claude Code CLI **2.1.287**, `claude plugin --help` and subcommand help, plus
`claude plugin validate --json` run on a throwaway probe plugin in a scratch directory, 2026-10-02.
Network documentation was read after G0 approval (sources below the table).

| # | Question | Status | Finding and source |
|---|---|---|---|
| 1 | Manifest location / required fields | `[Confirmed]` CLI | `.claude-plugin/plugin.json`. Only `name` is required (missing `name` = error; missing `version`, `description`, `author` = warnings); kebab-case. `--strict` turns warnings into errors, so we include `author`. |
| 2 | Skill discovery, description limit, always-loaded cost | `[Confirmed]` layout and cost model; limit not documented | One `skills/<name>/SKILL.md` per skill (docs: plugins/manifest-reference; CLI validator scans it). Always-on cost = each component's name + `description` + `when_to_use` (docs: skills, "The always-on figure counts each component's name plus its `description` and `when_to_use` frontmatter"). No maximum description length is documented, and a 1,100-character description raised no validator warning. **Budget decision:** measure with `claude plugin details` and keep each description under 1,024 characters `[Proposal]` (the common Agent Skills limit; not a verified Claude Code limit). |
| 3 | Namespacing | `[Confirmed]` docs | "Command name: `/<plugin>:<directory>`, so `skills/review/SKILL.md` in `my-plugin` is `/my-plugin:review`" (plugins/components). Plugin skills therefore appear as `hep-research:hep-analysis`, distinct from a personal `hep-analysis` skill. Live coexistence is still tested at G5. |
| 4 | Install cache, plugin root, base directory | `[Confirmed]` cache + variable; base directory not documented | Installed marketplace plugins live in `cache/<marketplace>/<plugin>/<version>/` and `${CLAUDE_PLUGIN_ROOT}` points there (plugins/loading). `${CLAUDE_PLUGIN_ROOT}` resolves inline in skill/command/agent content (plugins/manifest-reference, environment variables table). Whether the model is told a skill's base directory is not documented. **Consequence:** the whole plugin root is copied, so skills can read shared `core/`, `contracts/`, `profiles/` via `${CLAUDE_PLUGIN_ROOT}/...` paths in SKILL.md; the per-skill-copy fallback is not needed. Nothing outside the plugin root may be referenced. Scripts still resolve the root from `__file__` (works with or without the variable). |
| 5 | Local marketplace + install/remove | `[Confirmed]` CLI + docs | `.claude-plugin/marketplace.json` at the marketplace root; relative `source` resolves from the root, not from `.claude-plugin/` (plugins/marketplace-reference). Commands: `claude plugin marketplace add <path>`, `claude plugin install <plugin>@<marketplace> [-s user|project|local]`, `claude plugin uninstall <plugin> [--scope]`. Executed only at G5. |
| 6 | Non-interactive validator | `[Confirmed]` CLI | `claude plugin validate <path> [--json] [--strict]` on a plugin dir, marketplace root, or skills dir; exit 0/1. |
| 7 | Headless traces | `[Unresolved]` | `claude -p --output-format stream-json` exists; the docs do not say whether loaded skills are reported. Must be observed in a live run (paid; needs approval at M5). If skills are not visible, load traces come from tool-use events (Read of plugin files) in the stream. |
| 8 | Commands vs skills | `[Confirmed]` docs | "Commands are the older format, and skills supersede them for new work" (plugins/components). Frontmatter `disable-model-invocation: true` / `user-invocable: false` control invocation (skills). **Decision:** no `commands/` in v1 (D10). |

Docs read 2026-10-02 (network approved at G0): code.claude.com/docs/en/plugins/{manifest-reference,components,loading,marketplace-reference,cli-reference,plugin-evals}, code.claude.com/docs/en/skills. Quotes are from those pages as fetched that day.

## Additional host facts found

- `claude --plugin-dir <path>` loads a plugin from a directory or .zip for one session, without installing. `[Confirmed]` from help. This gives a low-risk first step for G5 (no change to the user's installed plugins).
- `claude plugin eval [target]` runs `evals/**/prompt.md + graders/*.md` cases against a plugin with a no-plugin baseline arm. `[Confirmed]` from help. This matches the existing `hep-analysis/evals/` layout and is a candidate mechanism for the M5 live routing check (paid; needs approval).
- `claude plugin tag` creates `{name}--v{version}` git tags after checking plugin.json and marketplace agree. Relevant to versioning (7.13), not used in v1.
