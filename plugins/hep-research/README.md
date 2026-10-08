# hep-research

A Claude Code plugin for experimental and theoretical high-energy and astroparticle physics research. It has seven
core skills, a shared library (`core/`), artifact contracts (`contracts/`), optional experiment and theory-domain
profiles (`profiles/`) and tool adapters (`adapters/`).

Version 0.5.0, licensed under Apache-2.0 (see [LICENSE](LICENSE)). Not endorsed by AMS or any collaboration. Example data shipped with the plugin is synthetic and is
labeled synthetic in file names and metadata. What is and is not validated is listed in
[docs/capability-matrix.md](docs/capability-matrix.md); test evidence is in [VALIDATION.md](VALIDATION.md).

## Skills

| Skill | Use it when the deliverable is |
|---|---|
| `hep-analysis` | the design or review of a measurement: estimand, selection, backgrounds, corrections, systematics, blinding |
| `detector-response` | detector response: reconstruction, calibration, resolution, efficiency, response matrices and forward folding, simulation |
| `hep-theory` | a theory or phenomenology result: model, conventions, derivation, predictions, recasting |
| `hep-statistics` | an inference: likelihoods, fits, intervals, limits, unfolding, combinations, comparisons with data |
| `hep-computing` | working, reproducible software and its execution, including task files for coding agents |
| `physics-ml` | a machine-learning model or study for physics (PyTorch) |
| `research-communication` | papers, figures, diagrams, talks, literature and citation checks |

Skills are chosen by what you want produced, not by the experiment you name. Results that another skill continues
from are written as JSON artifacts in your project's `artifacts_dir` (default `./hep-research-artifacts/`).

## Install and remove

The repository root carries one marketplace, `hep-research-dev`, in two formats: `.claude-plugin/marketplace.json`
for Claude Code and `.agents/plugins/marketplace.json` for Codex. Both point at this folder. Skills are namespaced in
both hosts, for example `hep-research:hep-statistics`.

### Claude Code

```bash
claude plugin marketplace add ./hep-research          # path to the repository clone, or hchouTW/hep-research
claude plugin install hep-research@hep-research-dev   # user scope; --scope project/local only for development
```

Start a new Claude Code session. `/plugin` lists the plugin; skills are invoked by request or by name, for example
`/hep-research:hep-statistics`. To remove:

```bash
claude plugin uninstall hep-research@hep-research-dev
claude plugin marketplace remove hep-research-dev
```

With a local-directory marketplace, Claude Code loads the plugin in place from that directory, so keep it at a
stable path. That in-place loading is for development only: the agent can edit a checkout in its working tree, and the
host would then load the edited code. For other use, install from the GitHub marketplace (cloned and cached) or keep the
plugin outside every agent-writable path and deny writes there. `claude plugin update` only picks up a new version number.

### Codex CLI

```bash
codex plugin marketplace add ./hep-research           # path to the repository clone, or hchouTW/hep-research
codex plugin add hep-research@hep-research-dev
```

Start a new Codex session. Ask for a skill by name, for example "Use the hep-research:hep-statistics skill to ...".
Codex copies the plugin into `$CODEX_HOME/plugins/cache/`, so the clone can move afterwards. To remove:

```bash
codex plugin remove hep-research@hep-research-dev
codex plugin marketplace remove hep-research-dev
```

### Claude apps: Chat and Cowork (not tested)

These steps are taken from Anthropic's documentation, read on 2026-10-04
([Plugins](https://claude.com/docs/plugins/overview), [Install plugins in Cowork](https://claude.com/docs/cowork/guide/plugins)).
They have not been run with this plugin. Plugins need a paid plan (Pro, Max, Team or Enterprise).

1. In claude.ai or the Claude desktop app, open **Customize > Plugins**. For Cowork, open the **Cowork** tab first.
2. Select **Add > Add marketplace** and enter `hchouTW/hep-research` (or `https://github.com/hchouTW/hep-research`).
   The app should read the same `.claude-plugin/marketplace.json` as Claude Code. On Team and Enterprise plans an Owner
   may have turned off adding your own marketplaces.
3. Find `hep-research` under **Discover** and select **Add** (or **Install**).
4. Alternatively, **Add > Upload plugin** accepts a `.zip` of this folder; the archive must hold exactly one
   `.claude-plugin/plugin.json`. Build it from a clean checkout so it carries no caches:
   `git archive --format=zip -o hep-research.zip HEAD:plugins/hep-research`. The plugin (about 1030 files, 6.8 MB
   uncompressed) is inside the documented limits (5,000 files, 200 MB). An uploaded plugin does not update from GitHub.

The plugin is saved to your account, so it is then available in Chat, in Cowork, and in Claude Code sessions signed
in to the same account (Claude Code downloads it as a synced plugin; run `/reload-plugins`). Pick a skill by typing
`/` and `hep-research:` in the message box, or describe the task. To update, select **Check for updates** on the
marketplace, or turn on **Sync automatically**. To remove, open the plugin and select **Remove** from its menu, or
turn it off with **Disable plugin**.

What to expect, read from the documentation and the plugin's design (untested):

- **Chat** loads the skills. Chat has no access to your computer: it cannot read your project's
  `hep-research.project.json`, private profiles or data, and scripts run only in Anthropic's code-execution sandbox
  (turn on code execution in **Settings**), with that sandbox's network limits. Whether the files outside `skills/`
  (`core/`, `contracts/`, `profiles/`, `adapters/`) are reachable there is not verified; skills that need them may
  stop and say so. Upload only public or synthetic files a request needs, and download the artifacts it produces.
- **Cowork** works on a folder you choose on your computer, so project configuration, local profiles and the
  `artifacts_dir` should work as in Claude Code, for public and synthetic projects only: Cowork has not been checked for
  any enforcement of data boundaries. Python and the packages in `requirements-core.txt` must be
  available where Cowork runs the scripts.
- Plugins added in the apps are separate from plugins installed with `claude plugin install`, which stay on that
  machine. If you have both, Claude Code may load two copies; keep one of them.

### ChatGPT (not tested)

Taken from OpenAI's documentation, read on 2026-10-04 ([Plugins](https://learn.chatgpt.com/docs/plugins),
[Build skills](https://learn.chatgpt.com/docs/build-skills), [Skills in ChatGPT](https://help.openai.com/en/articles/20001066-skills-in-chatgpt)).
None of this has been run with this plugin.

- **As a plugin.** ChatGPT and Codex share one public plugin directory (**Plugins** tab, then the plus button), and
  hep-research is not listed there. An individual user cannot add a GitHub marketplace in ChatGPT. On Business and
  Enterprise workspaces an admin can import and sync a GitHub marketplace for the team; whether that import reads
  this repository's `.agents/plugins/marketplace.json` (the Codex marketplace) is not verified. If it works, the
  plugin is available in Chat and Work in ChatGPT and in Codex; invoke a skill with `@`.
- **As separate skills (fallback).** Open **Skills**, select **Create > Upload from your computer**, and upload one
  `.zip` per skill folder, for example
  `git archive --format=zip --prefix=hep-statistics/ -o hep-statistics.zip HEAD:plugins/hep-research/skills/hep-statistics`
  (the skill folder sits at the top of the archive). ChatGPT scans each upload; some come back as **Needs Review**.
  Skills availability depends on the plan and workspace (check the help page for yours). This loses a lot: the skills are no longer `hep-research:*` (name them as uploaded),
  and the shared plugin folders (`core/`, `contracts/`, `profiles/`, `adapters/`) are missing, so steps that read
  `<plugin root>/...` fail and scripts that import `core` do not run. Use it for the methods and checklists in
  `SKILL.md` and `references/`, not for the scripts or profiles.

For full use with OpenAI models, the Codex CLI install above is the tested path.

### All hosts

Skill text names plugin files as `<plugin root>/...` (see "Project configuration and profiles"), so it works without
any host-specific variable. Skills you installed separately are not touched; if a host picks another skill for a
request, name the plugin skill.

Tested on macOS (E2): Claude Code 2.1.288 and Codex CLI 0.160.0, from a local-directory marketplace, for install,
discovery, invocation, profile access and removal (VALIDATION.md, MULTIHOST). Claude Code was also tested on Linux
(E1, CLI 2.1.287). Codex also installs from the GitHub marketplace (`hchouTW/hep-research`). Codex on Linux and
other hosts are not tested.

"Tested" means install, discovery and invocation only. **No host configuration is qualified for private or blinded
data**: use the plugin with public or synthetic data only. Unblinding is never done in an agent session, and every check
the agent runs (contracts, dependencies, blinding scans) is advisory, not enforcement or authorization.

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
| Collaboration member (J11) | "Set up a local profile for my experiment from its public detector paper and use it in the efficiency study." Private content needs a qualified host configuration (none yet) and your collaboration's approval to send it to a model service. |
| Outside v1 (J12) | "Set up a lattice QCD global analysis of form factors." The skill says there is no validated profile and applies general methods. |

Requests in Traditional Chinese are routed the same way, and answers come in the language you write in.

## Project configuration and profiles

Profiles are used only when you name them or when your project root holds `hep-research.project.json`:

```json
{
 "schema_version": "1.0.0",
 "plugin_version": ">=0.3,<1.0",
 "experiments": [{"profile": "experiment:ams-02", "version": "2.0.0"}],
 "theory": [{"profile": "theory:qed-benchmark", "version": "1.0.0"}]
}
```

Shipped profiles: `experiment:ams-02` (public evidence ledger and public-domain methods; no internal data or
software), `experiment:eic` (EIC facility context and the ePIC experiment, public documents only, no performance
numbers), `experiment:synthetic-collider` (an invented detector for examples), `theory:qed-benchmark` (tree-level
QED) and `theory:qcd-r-ratio` (R ratio with QCD corrections). Private profiles stay in your project and are listed in
the config's `local_profile_paths`; check the config with
`python3 "<plugin root>/contracts/project.py" <project-dir>`, where `<plugin root>` is the folder that holds this README
(in an install, the host's copy of the plugin). Nothing private is copied into the plugin.

Schema 1.1.0 adds `agent_policy`: which content may reach the model (`public`, `synthetic`, `collaboration-internal`,
`blinded-derivative:approved-manifest`), protected paths, data release manifests with their SHA-256, and
`"unblinding": "outside-agent-session"`; a project with it must declare its `blinding` block. The copy in the project
is agent-writable, so `contracts/project.py` only checks it (advisory); enforcement needs a host configuration that
compares it with an authoritative copy, and none is qualified yet.

### Companion plugins

A profile can also be shipped by a separate plugin that only authorized people can install. Such a plugin provides one
skill, `<plugin>:profile`, whose text states where its profile folder is and which preflight to run. When a task needs
a profile that is neither registered here nor a plain local profile (or whose `local_profile_paths` entry is known to be
the companion's folder), the skills load that companion skill, run its preflight, and use the folder it names as a
local profile; if no companion plugin is installed or its preflight fails, they say the profile is unavailable, do not
answer its topics from memory, and go on with other work. Nothing else triggers it: hep-research never scans for
companions. Validate the profile itself with
`python3 "<plugin root>/contracts/registry.py" --local <companion plugin root>/profile`, or a project and its pins with
`python3 "<plugin root>/contracts/project.py" <project-dir> --local <companion plugin root>/profile`.

hep-research installs, updates and runs without any companion. A companion must not declare a host dependency on
this plugin; it owns its compatibility check, so installing or updating hep-research does not wait for it. The first companion plugin
is `ams02-research` (access-restricted; listed in the same marketplace and installed separately), which provides
`experiment:ams-02-private` for AMS Collaboration members. Load a companion profile only on
a host configuration qualified for its content and with the collaboration's approval to send that content to the model
service (no configuration is qualified yet), and install it where the agent cannot write. See
[docs/profile-authoring.md](docs/profile-authoring.md) for writing one.

Migration from `ams02-research` 1.1.0 and earlier: those releases declare `hep-research ^0.4.0` in their Claude Code
manifest, and an installed copy keeps holding hep-research inside that range (Claude Code skips newer hep-research
updates) until `ams02-research` is updated to a release without the declaration, or uninstalled, through the host's own
plugin commands. This marketplace pins `ams02-research` 1.2.1 (commit `32d538a`), which has no such declaration, so
update the companion first and hep-research second:

```bash
claude plugin marketplace update hep-research-dev
claude plugin update ams02-research@hep-research-dev
claude plugin update hep-research@hep-research-dev
```

Before running `claude plugin prune`, follow the companion's own update notes so hep-research is not removed as an
auto-installed dependency. Do not edit the plugin cache by hand. A marketplace refresh can still read every catalog entry,
including the companion's; what hep-research guarantees is that its own install, update and checks never read a
companion's package manifest or need access to a private repository. Behaviour on a live host is checked separately
(see the changelog).

## Environments

- **Core (needed by most scripts and all examples):** Python 3.11 or newer with the packages in
  [requirements-core.txt](requirements-core.txt) (NumPy, SciPy, Matplotlib, SymPy). Install them in a virtual
  environment, for example `python3 -m venv ~/.venvs/hep && ~/.venvs/hep/bin/pip install -r requirements-core.txt`;
  an interpreter used by anything that runs outside the agent sandbox must live outside agent-writable paths.
  Contract, registry and blinding checks need only the standard library.
- **Which interpreter:** before SymPy work the skills run `skills/hep-computing/scripts/find_python.py`, which picks
  the first Python >= 3.11 that has the packages from `--python`, the `HEP_RESEARCH_PYTHON` environment variable, the
  calling interpreter, then `python3` on PATH. To use a dedicated environment, set the variable, for example
  `export HEP_RESEARCH_PYTHON=~/miniconda3/envs/sympy-py313/bin/python`. Nothing else is searched, and nothing is
  installed: if no candidate qualifies, the script reports a `failed` status.
- **Optional (skipped in the v1 handover run; each was installed and verified afterwards, see the `*-RUN` sections of
  `VALIDATION.md`, except the tectonic paper build):** PyTorch (`physics-ml` assets), ROOT/PyROOT, uproot and awkward (`hep-computing`
  ROOT tools, `adapters/root-uproot`), pyhf and CMS Combine (`adapters/pyhf-combine`, the end-to-end sample),
  Graphviz, Mermaid, PlantUML and tectonic (diagrams and papers). Slurm and HTCondor (`adapters/batch-schedulers`)
  have not been run for real: that adapter is `documented` and tested against fake schedulers only. Scripts that need them report the missing tool
  and stop with a `failed` status; tests that need them are skipped and counted as unverified.

## Offline behavior

Everything mandatory works offline: skills, references, profiles, contracts, core library, scripts and examples
read only files inside the plugin and your project. Literature searches (INSPIRE-HEP, ADS, arXiv) and package
installs need network access, which the host asks you to approve; in a protected session only the destinations its
egress policy allows may be reached, uncovered calls are denied, and queries never carry unpublished numbers or
internal names. Without network access, citations are marked unverified rather than guessed, and nothing is downloaded
silently.

## Checks for maintainers

```bash
python3 tools/run_all_checks.py --out <dir>      # registry, layering, contracts, unit tests, profiles, routing, packaging, budgets
python3 tools/check_relocation.py --out <dir>    # copy to a temp path with spaces and rerun everything from another cwd
```

Software checks establish contract consistency only. They do not establish physical validity, proof, statistical
coverage, or authorization to unblind.

## License

Apache License 2.0; see [LICENSE](LICENSE). Example data is synthetic. The plugin is not endorsed by AMS or any
collaboration or institution, and nothing in it is an AMS Collaboration rule or result.
