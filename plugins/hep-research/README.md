# hep-research

Claude Code and Codex plugin for experimental and theoretical high-energy and astroparticle physics research.

Version 0.51.0, licensed under Apache-2.0 (see [LICENSE](LICENSE)). Not endorsed by AMS or any collaboration. Example data is synthetic and labeled synthetic in file names and metadata.
Validation status: [docs/capability-matrix.md](docs/capability-matrix.md). Test evidence: [VALIDATION.md](VALIDATION.md).

## Core capabilities

- **Nine skills** under `skills/`, chosen by the deliverable, not by the experiment named in the request.
- **Shared library** (`core/`): blinding, constants, evidence, kinematics, naming, partitioning, protected-mode checks,
  providers, simulation, statistics, terminology, trace.
- **Artifact contracts** (`contracts/`): JSON schemas, vocabularies and validators for the results skills hand to each
  other, project configuration, profile registry, custody, permits, release manifests.
- **Profiles** (`profiles/`): optional experiment and theory-domain profiles, and the reference profile of the sourced
  detector atlas.
- **Tool adapters** (`adapters/`): batch schedulers, cosmic-ray propagation, CRDB, environments, Geant4, geomagnetic
  backtracing, HEPData, literature lookup, pyhf/Combine, recasting, ROOT/uproot, unbinned fit, unfolding.
- **Worked examples** (`examples/`): 26 examples on synthetic data, most with a `run.py` and committed outputs.
- **Bilingual routing**: requests in Traditional Chinese are routed the same way; answers come in the language of the
  request.

## Triggering conditions

Skills load by request or by name (`hep-research:<skill>`). Each `SKILL.md` front matter carries the description the
host routes on.

| Skill | Use it when the deliverable is |
|---|---|
| `hep-measurement` | the design or review of a measurement: estimand, selection, backgrounds, corrections, systematics, blinding |
| `hep-detector` | detector response: reconstruction, calibration, resolution, efficiency, response matrices and forward folding, simulation |
| `hep-theory` | a theory or phenomenology result: model, conventions, derivation, predictions, recasting |
| `hep-statistics` | an inference: likelihoods, fits, intervals, limits, unfolding, combinations, comparisons with data |
| `hep-computing` | working, reproducible software and its execution, including task files for coding agents |
| `hep-ml` | a machine-learning model or study for physics (PyTorch) |
| `hep-citations` | answers from cited sources: what a paper or experiment published, the latest result, citation verification, literature records and matrices |
| `hep-authoring` | papers, figures, diagrams, talks, referee reports, claims traced to results and sources; every citation from a literature record |
| `hep-review` | a recorded review of an analysis, derivation, fit or physics code: review obligations, assurance tiers R0-R3, checkpoints, a report that never claims more than its tier (evaluated on multi-step statistics reviews) |

- Profiles load only when the request names one or the project root holds `hep-research.project.json`.
- A companion plugin's `<plugin>:profile` skill loads only when a task needs a profile that is neither registered here
  nor a plain local profile; hep-research never scans for companions.
- If a host picks another installed skill for a request, name the plugin skill. Skills installed separately are not
  touched.

## Workspace directory architecture

```text
hep-research/
├── .claude-plugin/plugin.json    # Claude Code manifest
├── .codex-plugin/plugin.json     # Codex manifest
├── skills/                       # nine skills; each: SKILL.md, README.md, references/, scripts/, assets/
├── core/                         # shared Python library
├── contracts/                    # schemas, vocabularies, validators, project and profile tooling
├── profiles/
│   ├── experiments/              # ams-02, eic, synthetic-collider
│   ├── theory/                   # nine theory-domain profiles
│   ├── reference/                # detector-atlas
│   └── registry.json
├── adapters/                     # tool adapters with declared status
├── examples/                     # worked examples on synthetic data
├── docs/                         # architecture, capability matrix, routing contract, authoring guides, dev records
├── tests/                        # unittest suites (adapters, contracts, core, examples, routing, skills, tools)
├── tools/                        # maintainer checks
├── release-manifests/            # per-release file manifests and digests
├── requirements-core.txt         # NumPy, SciPy, Matplotlib, SymPy
├── pyproject.toml
├── CHANGELOG.md
└── VALIDATION.md
```

| Path | Role |
|---|---|
| `skills/<skill>/SKILL.md` | entry point the host loads |
| `skills/<skill>/README.md` | folder guide for people: capabilities, layout, inputs and outputs, setup, constraints |
| `<project>/hep-research.project.json` | project configuration (profiles, pins, `agent_policy`) |
| `<project>/hep-research-artifacts/` | default `artifacts_dir`: JSON artifacts other skills continue from |

Skill text names plugin files as `<plugin root>/...`, so it works without any host-specific variable. `<plugin root>`
is the folder that holds this README (in an install, the host's copy of the plugin).

## Input and output specifications

**Inputs**
- The request, in English or Traditional Chinese.
- Optional project configuration in the project root:

```json
{
 "schema_version": "1.0.0",
 "plugin_version": ">=0.3,<1.0",
 "experiments": [{"profile": "experiment:ams-02", "version": "2.0.0"}],
 "theory": [{"profile": "theory:qed-benchmark", "version": "1.0.0"}]
}
```

- Shipped profiles:

| Profile | Content |
|---|---|
| `experiment:ams-02` | public evidence ledger and public-domain methods; no internal data or software |
| `experiment:eic` | EIC facility context and the ePIC experiment; public documents only, no performance numbers |
| `experiment:synthetic-collider` | an invented detector for examples |
| `theory:qed-benchmark` | tree-level QED |
| `theory:qcd-r-ratio` | the R ratio with QCD corrections |
| `theory:higgs-bb-width` | H -> b bbar with the MS-bar running mass |
| `theory:cr-secondary-ratio` | B/C in weighted-slab and 1D thin-disc diffusion models; illustrative cross sections |
| `theory:cr-secondary-antiprotons` | the antiproton source term; illustrative toy cross sections |
| `theory:heliospheric-modulation` | force-field solar modulation: validity, limits, a power-law benchmark |
| `theory:dis-parton-model` | LO parton-model F_2 and the O(alpha_s) longitudinal structure function F_L; synthetic only |
| `theory:drell-yan-lo` | LO Drell-Yan cross section and lepton angular coefficients at O(alpha_s) |
| `theory:tmd-gaussian-lo` | Gaussian-ansatz TMD distributions and fragmentation functions at LO, without evolution |
| `reference:detector-atlas` | sourced evidence ledger of detector facts for twelve experiments |

- Private profiles stay in the project, listed in the config's `local_profile_paths`. Nothing private is copied into
  the plugin.
- Schema 1.1.0 adds `agent_policy`: which content may reach the model (`public`, `synthetic`,
  `collaboration-internal`, `blinded-derivative:approved-manifest`), protected paths, data release manifests with their
  SHA-256, and `"unblinding": "outside-agent-session"`; a project with it must declare its `blinding` block.

**Outputs**
- JSON artifacts in the project's `artifacts_dir` (default `./hep-research-artifacts/`), validated against
  `contracts/`; never written inside the plugin.
- Script reports as JSON or labelled tables; each skill README states its scripts' exit codes.
- In protected mode, entry points refuse with exit 3 and `"status": "refused"` (see Operational constraints).

**Project and profile commands**

```bash
python3 "<plugin root>/contracts/project.py" <project-dir>                     # check the project config
python3 "<plugin root>/contracts/protected_use.py" status <project-dir>        # protected-mode state
python3 "<plugin root>/contracts/custody.py" <project-dir> [--local DIR ...]  # where each profile comes from, custody status
python3 "<plugin root>/contracts/registry.py" --local <companion plugin root>/profile
python3 "<plugin root>/contracts/project.py" <project-dir> --local <companion plugin root>/profile
```

A missing custody value is never read as public.

## Setup requirements

**Python**
- Python 3.13 or newer (tested on 3.13; a newer series is installable but not tested), with the packages in
  [requirements-core.txt](requirements-core.txt) (NumPy, SciPy, Matplotlib, SymPy) for most scripts and all examples.
  Contract, registry and blinding checks need only the standard library.

```bash
python3 -m venv ~/.venvs/hep && ~/.venvs/hep/bin/pip install -r requirements-core.txt
```

- An interpreter used by anything that runs outside the agent sandbox must live outside agent-writable paths.
- Interpreter choice: before SymPy work the skills run `skills/hep-computing/scripts/find_python.py`, which picks the
  first interpreter at 3.13 or newer that has the packages, from `--python`, `HEP_RESEARCH_PYTHON`, the calling
  interpreter, then `python3` on PATH. Nothing else is searched and nothing is installed; with no qualifying candidate
  it reports `failed`. A lower `--min-python` is refused. Scripts run directly (`python3 script.py`), so
  `requires-python` in `pyproject.toml` does not stop an older interpreter.

```bash
export HEP_RESEARCH_PYTHON=~/miniconda3/envs/sympy-py313/bin/python
```

- Interpreter guard: every script a skill runs starts with a guard block (`core/interpreter_guard.py`). Under a
  Python older than 3.13 it stops before any work with one stderr line starting `hep-research:` and exit 2, or, when
  `HEP_RESEARCH_PYTHON` names a safe interpreter, re-runs the script once with it. Safe means an absolute path to an
  existing executable file (no PATH lookup), neither the file nor its folder writable by the running account, not
  running as root, and no `--protected` argument. The batch executor and bundle freezing refuse both guard variables
  (`HEP_RESEARCH_PYTHON`, `HEP_RESEARCH_GUARD_REEXEC`): a job runs the interpreter its bundle names.

**macOS.** `/usr/bin/python3` is the Xcode command-line tools' Python 3.9, which the guard stops. Install Python 3.13
from Homebrew (`brew install python@3.13`), conda (`conda create -n hep python=3.13`) or uv
(`uv python install 3.13`), create the virtual environment with it and install
[requirements-core.txt](requirements-core.txt). Point the guard at an interpreter whose file and folder you cannot
write (Homebrew's `/opt/homebrew/bin` is user-writable, so the guard does not switch to it; use a copy or an
environment owned by another account, or start scripts with the 3.13 interpreter directly):

```bash
export HEP_RESEARCH_PYTHON=/absolute/path/to/python3.13
```

PyTorch and xgboost publish arm64 wheels for Apple Silicon (`pip install torch xgboost`; no CUDA, the MPS device is
used where the code asks for it). ROOT is easiest from conda-forge (`conda install -c conda-forge root`), in the same
environment as the Python that runs the scripts.

**Optional tools** (each installed and verified after the v1 handover, see the `*-RUN` sections of `VALIDATION.md`,
except the tectonic paper build). Scripts that need a missing tool report it and stop with a `failed` status; tests
that need it are skipped and counted as unverified.
- PyTorch (`hep-ml` assets).
- ROOT/PyROOT, uproot and awkward (`hep-computing` ROOT tools, `adapters/root-uproot`).
- pyhf and CMS Combine (`adapters/pyhf-combine`, the end-to-end sample).
- Graphviz, Mermaid, PlantUML and tectonic (diagrams and papers).
- Slurm and HTCondor (`adapters/batch-schedulers`, `demonstrated-on-synthetic-data`): synthetic campaigns on one site
  each (Slurm 24.05.1 at NSTCCore, HTCondor 24.12.16 at CERN).
- DRAGON2 (`adapters/cr-propagation`, status `proposed`, required by no skill), run from a JSON run spec in a recorded
  environment; GALPROP and USINE are only proposed.

**Install: Claude Code**

The repository root carries one marketplace, `hep-research-dev`, in two formats: `.claude-plugin/marketplace.json`
(Claude Code) and `.agents/plugins/marketplace.json` (Codex). Both point at this folder. Skills are namespaced, for
example `hep-research:hep-statistics`.

```bash
claude plugin marketplace add ./hep-research          # path to the repository clone, or hchouTW/hep-research
claude plugin install hep-research@hep-research-dev   # user scope; --scope project/local only for development
# remove
claude plugin uninstall hep-research@hep-research-dev
claude plugin marketplace remove hep-research-dev
```

- Start a new session; `/plugin` lists the plugin; invoke by request or by name, for example
  `/hep-research:hep-statistics`.
- A local-directory marketplace loads the plugin in place, so keep it at a stable path. In-place loading is for
  development only: the agent can edit a checkout in its working tree and the host would load the edited code. For
  other use, install from the GitHub marketplace (cloned and cached) or keep the plugin outside every agent-writable
  path and deny writes there.
- `claude plugin update` only picks up a new version number.

**Install: Codex CLI**

```bash
codex plugin marketplace add ./hep-research           # path to the repository clone, or hchouTW/hep-research
codex plugin add hep-research@hep-research-dev
# remove
codex plugin remove hep-research@hep-research-dev
codex plugin marketplace remove hep-research-dev
```

- Start a new session and ask for a skill by name, for example "Use the hep-research:hep-statistics skill to ...".
- Codex copies the plugin into `$CODEX_HOME/plugins/cache/`, so the clone can move afterwards.
- For full use with OpenAI models, the Codex CLI install is the tested path.

**Install: Claude apps, Chat and Cowork (not tested)**

Taken from Anthropic's documentation, read on 2026-10-04 ([Plugins](https://claude.com/docs/plugins/overview),
[Install plugins in Cowork](https://claude.com/docs/cowork/guide/plugins)); not run with this plugin. Needs a paid plan
(Pro, Max, Team or Enterprise).

1. In claude.ai or the Claude desktop app, open **Customize > Plugins** (for Cowork, open the **Cowork** tab first).
2. **Add > Add marketplace**: `hchouTW/hep-research` (or `https://github.com/hchouTW/hep-research`). The app should read
   the same `.claude-plugin/marketplace.json`. On Team and Enterprise plans an Owner may have turned off adding your own
   marketplaces.
3. Find `hep-research` under **Discover** and select **Add** (or **Install**).
4. Or **Add > Upload plugin** with a `.zip` holding exactly one `.claude-plugin/plugin.json`, built from a clean
   checkout so it carries no caches:
   `git archive --format=zip -o hep-research.zip HEAD:plugins/hep-research`. The plugin (about 4400 files, 71.3 MB uncompressed) is inside the documented limits (5,000 files, 200 MB). An uploaded plugin does not update from GitHub.

- The plugin is saved to the account: available in Chat, Cowork, and Claude Code sessions signed in to the same account
  (synced plugin; run `/reload-plugins`). Pick a skill with `/` and `hep-research:`, or describe the task.
- Update: **Check for updates** on the marketplace, or **Sync automatically**. Remove: **Remove** from the plugin's
  menu, or **Disable plugin**.
- **Chat** has no access to your computer: no project `hep-research.project.json`, private profiles or data; scripts
  run only in Anthropic's code-execution sandbox (turn on code execution in **Settings**) with its network limits.
  Whether `core/`, `contracts/`, `profiles/` and `adapters/` are reachable there is not verified; skills that need them
  may stop and say so. Upload only public or synthetic files, and download the artifacts produced.
- **Cowork** works on a folder you choose, so project configuration, local profiles and `artifacts_dir` should work as
  in Claude Code, for public and synthetic projects only (no enforcement of data boundaries has been checked). Python
  and `requirements-core.txt` must be available where Cowork runs the scripts.
- Plugins added in the apps are separate from `claude plugin install`; with both, Claude Code may load two copies; keep
  one.

**Install: ChatGPT (not tested)**

Taken from OpenAI's documentation, read on 2026-10-04 ([Plugins](https://learn.chatgpt.com/docs/plugins),
[Build skills](https://learn.chatgpt.com/docs/build-skills),
[Skills in ChatGPT](https://help.openai.com/en/articles/20001066-skills-in-chatgpt)); not run with this plugin.

- **As a plugin**: ChatGPT and Codex share one public plugin directory, and hep-research is not listed there. An
  individual user cannot add a GitHub marketplace in ChatGPT. On Business and Enterprise workspaces an admin can import
  and sync a GitHub marketplace; whether that reads `.agents/plugins/marketplace.json` is not verified. If it works,
  invoke a skill with `@`.
- **As separate skills (fallback)**: **Skills > Create > Upload from your computer**, one `.zip` per skill folder:

```bash
git archive --format=zip --prefix=hep-statistics/ -o hep-statistics.zip HEAD:plugins/hep-research/skills/hep-statistics
```

  ChatGPT scans each upload; some come back as **Needs Review**; availability depends on plan and workspace. The skills
  lose the `hep-research:*` names and the shared folders (`core/`, `contracts/`, `profiles/`, `adapters/`), so steps
  that read `<plugin root>/...` fail and scripts that import `core` do not run. Use it for the methods and checklists
  in `SKILL.md` and `references/` only.

**Tested hosts**: macOS (E2), Claude Code 2.1.288 and Codex CLI 0.160.0 from a local-directory marketplace, for install,
discovery, invocation, profile access and removal (VALIDATION.md, MULTIHOST); Claude Code on Linux (E1, CLI 2.1.287).
Codex also installs from the GitHub marketplace (`hchouTW/hep-research`). Codex on Linux and other hosts are not
tested. "Tested" means install, discovery and invocation only.

## Operational constraints

**Data boundaries**
- **No host configuration is qualified for private or blinded data**: use the plugin with public or synthetic data
  only.
- Unblinding is never done in an agent session. Every check the agent runs (contracts, dependencies, blinding scans) is
  advisory, not enforcement or authorization.
- The `agent_policy` copy in the project is agent-writable, so `contracts/project.py` only checks it (advisory);
  enforcement needs a host configuration that compares it with an authoritative copy, and none is qualified yet.
- **Protected mode** (a project with `agent_policy`, or any entry point given `--protected`): before anything else,
  every formal-use entry point checks the revocation log, its head and the qualification record that the authoritative
  copy of the policy names (schema 1.2.0, `protected_inputs`), and refuses with exit 3 and `"status": "refused"` when
  they are missing, stale, altered or writable by the session's account, or when an input is revoked. These checks run
  in the agent's own process, so they are advisory too and authorize nothing. Formal use (publication) also needs a
  formal-use permit issued by the custodian (`--permit`, `contracts/permit.py`), bound to the analysis-level bundle and
  to an attestation whose review covers the use.
- Private collaboration content needs a qualified host configuration (none yet) and the collaboration's approval to
  send it to a model service.

**Network**
- Everything mandatory works offline: skills, references, profiles, contracts, core library, scripts and examples read
  only files inside the plugin and the project.
- Literature searches (INSPIRE-HEP, ADS, arXiv) and package installs need network access, which the host asks you to
  approve. In a protected session only destinations its egress policy allows may be reached, uncovered calls are
  denied, and queries never carry unpublished numbers or internal names.
- Without network access, citations are marked unverified rather than guessed; nothing is downloaded silently.

**Companion plugins**
- A profile can be shipped by a separate plugin that only authorized people can install. It provides one skill,
  `<plugin>:profile`, whose text names its profile folder and the preflight to run. The skills load it only when a task
  needs that profile (or the `local_profile_paths` entry is known to be the companion's folder), run its preflight, and
  use the folder it names as a local profile. If no companion is installed or its preflight fails, they say the profile
  is unavailable, do not answer its topics from memory, and go on with other work.
- hep-research installs, updates and runs without any companion. A companion must not declare a host dependency on
  this plugin; it owns its compatibility check. hep-research's own install, update and checks never read a companion's
  package manifest or need access to a private repository.
- The first companion, `ams02-research` (access-restricted; not listed in this marketplace, installed separately),
  provides `experiment:ams-02-private` for AMS Collaboration members. Load a companion profile only on a host
  configuration qualified for its content and with the collaboration's approval to send that content to the model
  service (none is qualified yet), and install it where the agent cannot write. Writing one:
  [docs/profile-authoring.md](docs/profile-authoring.md).
- A copy of `ams02-research` installed from this marketplace earlier stays installed but receives no updates through
  it; reinstall it from its own source or uninstall it. Releases 1.1.0 and earlier declare `hep-research ^0.4.0` and
  hold hep-research at 0.4.x while installed; update or remove that copy before updating hep-research.
- Before `claude plugin prune`, follow the companion's own update notes so hep-research is not removed as an
  auto-installed dependency. Do not edit the plugin cache by hand. Behaviour on a live host is checked separately (see
  the changelog).

**Retired: cross-artifact analysis check**
- The opt-in cross-artifact analysis check (`contracts/analysis_check.py`, the `counting-chain` and `ratio-subset`
  suites, `permit.py check-report` and `review_measurement_spec.py --check-bundle`) was retired in 0.48.0: its value
  gate found no error it caught that closure tests and contract checks missed. Its entry points were removed in 0.49.0;
  reproduce old bundles and reports with 0.47.x.
- Its review questions are in the measurement review
  ([review and artifacts](skills/hep-measurement/references/review-and-artifacts.md)) and, for ratios, in
  [combinations](skills/hep-statistics/references/combinations.md); a recorded, tiered review uses them through
  hep-review. Records: [docs/dev/cross-artifact-check/](docs/dev/cross-artifact-check/README.md).

**Scope of software checks**
- Software checks establish contract consistency only. They do not establish physical validity, proof, statistical
  coverage, or authorization to unblind.

## Validation and maintainer checks

```bash
python3 tools/run_all_checks.py --out <dir>      # registry, layering, contracts, unit tests, profiles, routing, packaging, budgets
python3 tools/check_relocation.py --out <dir>    # copy to a temp path with spaces and rerun everything from another cwd
```

- What is and is not validated: [docs/capability-matrix.md](docs/capability-matrix.md).
- Evidence per change: [VALIDATION.md](VALIDATION.md). Release notes: [CHANGELOG.md](CHANGELOG.md).

## Example requests

| Who you are | Try |
|---|---|
| AMS-02 analyst (J1) | "Plan the time-dependent helium flux and He/p ratio measurement for AMS-02 across two periods." |
| Detector physicist (J2) | "Study how the RICH velocity resolution depends on charge." |
| Collider experimentalist (J3) | "Measure the corrected angular distribution at my e+e- collider with its own luminosity and response." |
| Analytic theorist (J4) | "Compute the tree-level e+e- -> mu+mu- cross section with all conventions stated and check it numerically." |
| Phenomenologist (J5) | "Fold my prediction through the detector response and fit a normalization scale." |
| Comparing with published data (J6) | "Compare my model with this published spectrum and its covariance; no detector details." |
| Recasting (J7) | "Recast the published search with its efficiency maps to constrain my model." |
| Computational theorist (J8) | "Run a convergence study of this integral and cross-check the symbolic result numerically." |
| Physics-ML researcher (J9) | "Train a classifier and declare the valid domain of its surrogate before using it in inference." |
| Writing up (J10) | "Draft the paper section and figures with claim-to-result links and honest status." |
| Collaboration member (J11) | "Set up a local profile for my experiment from its public detector paper and use it in the efficiency study." Private content needs a qualified host configuration (none yet) and your collaboration's approval to send it to a model service. |
| Outside v1 (J12) | "Set up a lattice QCD global analysis of form factors." The skill says there is no validated profile and applies general methods. |

## License

Apache License 2.0; see [LICENSE](LICENSE). Example data is synthetic. The plugin is not endorsed by AMS or any
collaboration or institution, and nothing in it is an AMS Collaboration rule or result.
