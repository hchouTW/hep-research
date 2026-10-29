# hep-research

Repository and marketplace (`hep-research-dev`) of the hep-research plugin for Claude Code and Codex: experimental and
theoretical high-energy and astroparticle physics research.

Not endorsed by AMS or any collaboration or institution. Licensed under Apache-2.0 (see [LICENSE](LICENSE)).

## Core capabilities

- **Nine skills**: `hep-measurement`, `hep-detector`, `hep-theory`, `hep-statistics`, `hep-computing`, `hep-ml`,
  `hep-citations`, `hep-authoring`, `hep-review`.
- **Optional profiles** for experiments and theory domains, and the reference profile of the sourced detector atlas.
- **Artifact contracts, a shared library and tool adapters** that let one skill continue from another skill's result.
- **Evaluation harnesses** outside the plugin: live routing, agent behaviour, communication answers.

Full description, skill table, profiles and constraints: [plugin README](plugins/hep-research/README.md).

## Triggering conditions

- Skills load by request or by name, namespaced as `hep-research:<skill>` (for example `hep-research:hep-statistics`).
- A skill is chosen by the deliverable (a measurement design, a fit, a derivation, a paper), not by the experiment named.
- Profiles load only when a request names one or the project root holds `hep-research.project.json`.

## Workspace directory architecture

```text
hep-research/
├── .claude-plugin/marketplace.json     # marketplace hep-research-dev for Claude Code
├── .agents/plugins/marketplace.json    # the same marketplace for Codex
├── plugins/hep-research/               # the plugin (skills, core, contracts, profiles, adapters, examples, docs, tests, tools)
├── evals/                              # evaluations outside the plugin (paid model calls where live)
│   ├── routing/                        # live routing evaluation
│   ├── behavior/                       # behavioural evaluation of an agent using the plugin
│   ├── research_communication/         # behavioural evaluation of hep-citations and hep-authoring
│   └── cross-artifact-value-gate/      # value gate of the retired cross-artifact check
├── .githooks/                          # path-allowlist hooks (pre-commit, pre-push)
├── .github/workflows/                  # tests, guard, statistics-validation
├── .gitleaks.toml                      # secret-scan configuration
└── LICENSE
```

| Path | Role |
|---|---|
| [`plugins/hep-research/`](plugins/hep-research/) | the plugin; install, usage and checks in its [README](plugins/hep-research/README.md) |
| [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) | Claude Code marketplace entry |
| [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json) | Codex marketplace entry |
| [`evals/routing/`](evals/routing/README.md) | live routing evaluation (paid model calls) |
| [`plugins/hep-research/CHANGELOG.md`](plugins/hep-research/CHANGELOG.md) | release notes |
| [`plugins/hep-research/VALIDATION.md`](plugins/hep-research/VALIDATION.md) | test evidence |

## Input and output specifications

- **Input**: requests in English or Traditional Chinese; optional project configuration
  (`hep-research.project.json`) and profiles.
- **Output**: answers, and JSON artifacts written to the project's `artifacts_dir` (default
  `./hep-research-artifacts/`), never inside the plugin.
- Details: [plugin README, Input and output specifications](plugins/hep-research/README.md#input-and-output-specifications).

## Setup requirements

```bash
# Claude Code
claude plugin marketplace add hchouTW/hep-research
claude plugin install hep-research@hep-research-dev

# Codex CLI
codex plugin marketplace add hchouTW/hep-research
codex plugin add hep-research@hep-research-dev
```

- Python 3.13 or newer with `plugins/hep-research/requirements-core.txt` (NumPy, SciPy, Matplotlib, SymPy) for most
  scripts and all examples; contract, registry and blinding checks need only the standard library.
- Other hosts (Claude apps, ChatGPT), optional tools and removal:
  [plugin README, Setup requirements](plugins/hep-research/README.md#setup-requirements).

## Operational constraints

- Public or synthetic data only: no host configuration is qualified for private or blinded data. Every check the agent
  runs is advisory, not enforcement or authorization.
- This marketplace lists hep-research only. Companion plugins, such as the access-restricted `ams02-research` for AMS
  Collaboration members, are not listed here; they come from their own sources and are installed and updated
  separately. hep-research does not depend on any of them (see
  [companion plugins](plugins/hep-research/docs/profile-authoring.md#companion-plugin)).
- A companion already installed from this marketplace stays installed but no longer receives updates through it (see
  [operational constraints](plugins/hep-research/README.md#operational-constraints)).
- The cross-artifact analysis check was retired in 0.48.0 and its entry points removed in 0.49.0; records:
  [`plugins/hep-research/docs/dev/cross-artifact-check/`](plugins/hep-research/docs/dev/cross-artifact-check/README.md).

## Validation

```bash
python3 plugins/hep-research/tools/run_all_checks.py       # plugin checks and unit tests
python3 plugins/hep-research/tools/check_relocation.py     # same from a temp copy under a path with spaces
```

- CI (`.github/workflows/tests.yml`) runs the plugin checks on pull requests, pushes to `main` and weekly.
- What is validated: [capability matrix](plugins/hep-research/docs/capability-matrix.md).

## Contributing

- Commits are checked by `.githooks/` (path allowlist) and by the `guard` workflow (path allowlist over the whole
  history plus a secret scan).
- After cloning, run once:

```bash
git config core.hooksPath .githooks
```

## License

Apache License 2.0; see [LICENSE](LICENSE).
