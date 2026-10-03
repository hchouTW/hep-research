# hep-research

A Claude Code plugin for experimental and theoretical high-energy and astroparticle physics research. It has seven
core skills, a shared library (`core/`), artifact contracts (`contracts/`), optional experiment and theory-domain
profiles (`profiles/`) and tool adapters (`adapters/`).

Version 0.1.0. Not endorsed by AMS or any collaboration. Example data shipped with the plugin is synthetic and is
labeled synthetic in file names and metadata. What is and is not validated is listed in
[docs/capability-matrix.md](docs/capability-matrix.md); test evidence is in [VALIDATION.md](VALIDATION.md).

## Skills

| Skill | Use it when the deliverable is |
|---|---|
| `hep-analysis` | the design or review of a measurement: estimand, selection, backgrounds, corrections, systematics, blinding |
| `detector-response` | detector response: reconstruction, calibration, resolution, efficiency, unfolding, simulation |
| `hep-theory` | a theory or phenomenology result: model, conventions, derivation, predictions, recasting |
| `hep-statistics` | an inference: likelihoods, fits, intervals, limits, combinations, comparisons with data |
| `hep-computing` | working, reproducible software and its execution, including task files for coding agents |
| `physics-ml` | a machine-learning model or study for physics (PyTorch) |
| `research-communication` | papers, figures, diagrams, talks, literature and citation checks |

Skills are chosen by what you want produced, not by the experiment you name. Results that another skill continues
from are written as JSON artifacts in your project's `artifacts_dir` (default `./hep-research-artifacts/`).

## Install and remove (Claude Code)

From a clone of the repository that contains this plugin (the development marketplace is
`.claude-plugin/marketplace.json` at the repository root):

```bash
claude plugin marketplace add ./hep-research          # path to the repository clone
claude plugin install hep-research@hep-research-dev   # add --scope project or --scope local if preferred
```

Start a new Claude Code session. `/plugin` lists the plugin; skills are invoked by request or by name, for example
`/hep-research:hep-statistics`. To remove:

```bash
claude plugin uninstall hep-research@hep-research-dev
claude plugin marketplace remove hep-research-dev
```

The plugin does not touch skills you installed separately (for example the older standalone skills in
`~/.claude/skills/`); both can be installed at once, but then Claude may pick an older skill for some requests, so
name the plugin skill (`/hep-research:<skill>`) when it matters. With a local-directory marketplace, Claude Code loads
the plugin in place from that directory, so keep it at a stable path. Install, discovery, invocation, removal and
coexistence were tested with Claude Code 2.1.287 (VALIDATION.md, AC24/AC25/T22). Other hosts are not tested in v1.

## Quick start: example prompts

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
| Collaboration member (J11) | "Use our collaboration's private calibration constants from my local profile in the efficiency study." |
| Outside v1 (J12) | "Set up a lattice QCD global analysis of form factors." The skill says there is no validated profile and applies general methods. |

Requests in Traditional Chinese are routed the same way, and answers come in the language you write in.

## Project configuration and profiles

Profiles are used only when you name them or when your project root holds `hep-research.project.json`:

```json
{
 "schema_version": "1.0.0",
 "plugin_version": ">=0.1,<1.0",
 "experiments": [{"profile": "experiment:ams-02", "version": "1.0.0"}],
 "theory": [{"profile": "theory:qed-benchmark", "version": "1.0.0"}]
}
```

Shipped profiles: `experiment:ams-02` (public evidence ledger), `experiment:synthetic-collider` (an invented detector
for examples) and `theory:qed-benchmark` (tree-level QED). Private profiles stay in your project and are listed in
the config's `local_profile_paths`; check the config with
`python3 "${CLAUDE_PLUGIN_ROOT}/contracts/project.py" <project-dir>`. Nothing private is copied into the plugin.

## Environments

- **Core (needed by most scripts and all examples):** Python 3.11 or newer with the packages in
  [requirements-core.txt](requirements-core.txt) (NumPy, SciPy, Matplotlib, SymPy). Install them in a project
  virtual environment, for example `python3 -m venv .venv-hep && .venv-hep/bin/pip install -r requirements-core.txt`.
  Contract, registry and blinding checks need only the standard library.
- **Optional (skipped in the v1 handover run; each was installed and verified afterwards, see the `*-RUN` sections of
  `VALIDATION.md`, except the tectonic paper build):** PyTorch (`physics-ml` assets), ROOT/PyROOT, uproot and awkward (`hep-computing`
  ROOT tools, `adapters/root-uproot`), pyhf and CMS Combine (`adapters/pyhf-combine`, the end-to-end sample),
  Graphviz, Mermaid, PlantUML and tectonic (diagrams and papers). Slurm and HTCondor (`adapters/batch-schedulers`)
  have not been run for real: that adapter is `documented` and tested against fake schedulers only. Scripts that need them report the missing tool
  and stop with a `failed` status; tests that need them are skipped and counted as unverified.

## Offline behavior

Everything mandatory works offline: skills, references, profiles, contracts, core library, scripts and examples
read only files inside the plugin and your project. Literature searches (INSPIRE-HEP, ADS, arXiv) and package
installs need network access, which the host asks you to approve. Without it, citations are marked unverified
rather than guessed, and nothing is downloaded silently.

## Checks for maintainers

```bash
python3 tools/run_all_checks.py --out <dir>      # registry, layering, contracts, unit tests, profiles, routing, packaging, budgets
python3 tools/check_relocation.py --out <dir>    # copy to a temp path with spaces and rerun everything from another cwd
```

Software checks establish contract consistency only. They do not establish physical validity, proof, statistical
coverage, or authorization to unblind.
