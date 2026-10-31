# Environments and containers

A result is reproducible only if its software environment can be named and rebuilt. This page says how to pin one,
what to record with every run, and how to notice that the environment moved. Status: the manifest script is tested;
the LCG-view and Apptainer templates in `<plugin root>/adapters/environments/assets/` are `documented` (written
without CVMFS or Apptainer at hand; raise the status only after building or sourcing them on a real cluster).

## Choose one way to pin the stack

| Route | Pins | Use when |
|---|---|---|
| LCG view on CVMFS (`lcg_view_setup.sh`) | ROOT, Python, compilers and the scientific stack as one release (`LCG_<n>`) for one platform tag (`x86_64-el9-gcc13-opt`) | on lxplus, a WLCG site or any node with `/cvmfs/sft.cern.ch` |
| Container (`hep-research.def`, Apptainer) | the operating system, ROOT from the base image, Python packages from `requirements-ci.lock` | batch nodes without CVMFS, or when the OS itself must be fixed; record the image digest |
| Experiment release (profile software modules) | the experiment's framework and its externals | analysis code that links against the framework; follow the bound profile, not this page |
| Virtual environment plus lock file | Python packages only, on the host's Python and system libraries | local development and unit tests; not enough for a published result that depends on ROOT or compilers. An interpreter that anything outside the agent sandbox runs (hooks, batch jobs) lives outside agent-writable paths |

Mixing routes (a venv on top of an LCG view, `pip install --user` inside a container) is where environments silently
diverge: record both layers or avoid the mix.

## Interpreter for skill scripts

Skill scripts start with `python3 <script>`, so `requires-python` does not stop an old interpreter. Each one runs a
guard block first (`<plugin root>/core/interpreter_guard.py`; the list is `<plugin root>/tools/skill_scripts.json`):

- Python 3.13 or newer: the script runs.
- Older (macOS ships 3.9 as `/usr/bin/python3`): one stderr line `hep-research: Python 3.13 or newer is required ...`
  and exit 2, before any work; nothing on stdout.
- Older with `HEP_RESEARCH_PYTHON` set to an absolute path of an existing executable whose file and folder the account
  cannot write, not as root and without `--protected`: the script is re-run once with that interpreter (the path is
  kept as given, so a virtual environment keeps its packages). If that one is old too, exit 2 with "did not provide
  one"; never a second switch.
- Windows: UTF-8 mode is required (`PYTHONUTF8=1`), otherwise exit 2 with that instruction.

`find_python.py --json` (`<plugin root>/skills/hep-computing/scripts/`) runs on an old `python3` and finds a 3.13+
interpreter with the packages; it carries no guard. Batch jobs never see `HEP_RESEARCH_PYTHON`: the executor and bundle
freezing refuse it, and the command names its interpreter by absolute path.

## Record with every run

Run, inside the environment that produced the result:

```
python3 <plugin root>/skills/hep-computing/scripts/environment_manifest.py record --project . --inputs data/*.json --out environment.json
```

It writes the `environment` object, the `tools` list and (with `--inputs`) the `input_manifest` (path, SHA-256, size)
of a `computational-run` artifact: Python version and executable, the system (OS family, architecture, libc, and the
kernel release for information), where the environment comes from (`lcg-view`, `container`, `conda`, `venv`,
`system`), the versions of the named packages (`--packages`, or `--all-packages`), a fixed list of environment
variables (`LCG_VERSION`, `BINARY_TAG`, `ROOTSYS`, `APPTAINER_CONTAINER`, ...) and the project's git commit and dirty
state.
Other variables are never recorded: they can hold credentials. Add by hand what the script cannot see: the LCG
release and platform you sourced, the container image digest (`apptainer inspect`), compiler flags of compiled code.

## Check before reusing a result

```
python3 <plugin root>/skills/hep-computing/scripts/environment_manifest.py check --manifest environment.json --project .
```

lists every difference in Python, executable, OS family, architecture, libc, origin, package versions, recorded
variables and input checksums, and with `--project` a changed commit or a dirty checkout (exit 1 on drift). A
different kernel release alone is a note: on a batch farm the kernel changes from node to node. A drift
is not an error by itself; it means the earlier result is not yet reproduced here. Rerun the closure or regression
test that the result depends on and compare within its declared tolerance before reusing the number.

## Pitfalls

- `pip install` into an LCG view or a read-only container fails or lands in `~/.local`, which then shadows the pinned
  versions on every later run; use a venv with `--system-site-packages` and record it.
- A dirty git tree means the commit does not identify the code; commit or record the diff.
- Floating tags (`latest`, `LCG_dev3`, nightly views) are not pins.
- Thread counts and BLAS libraries change floating-point results at the last digits; compare with tolerances, not
  bytes, unless the run was built to be bit-reproducible.


<a id="naming-n5"></a>
### Naming: configuration keys, environment variables, CLI flags (N5)
- **Extractor:** `extract_names.py --surface N5` (inputs: argparse flags and environment variables read by Python code; keys of JSON, TOML, INI and, with PyYAML, YAML configuration files)
- **Entity kinds and level floors:** generated from `contracts/naming/surfaces.json`, not restated by hand:

<!-- naming-kinds:N5: generated from contracts/naming/surfaces.json by contracts/naming_registry.py sections; do not edit -->

| Kind | Level floor | Format | Rename policy |
|---|---|---|---|
| `project_config_key` | C2 | `^[a-z][a-z0-9]*(?:[_-][a-z0-9]+)*$` | matrix |
| `project_cli_flag` | C2 | `^--?[a-z0-9][a-z0-9]*(?:-[a-z0-9]+)*$` | matrix |
| `plugin_cli_flag` | C3 | `^--?[a-z0-9][a-z0-9]*(?:-[a-z0-9]+)*$` | deprecate |
| `env_var` | C2 | `^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$` | matrix |

<!-- /naming-kinds:N5 -->

- **The name must say:** the setting it controls and its unit; flags in lower-case kebab, environment variables in upper-case snake
- **Rename policy:** matrix; `deprecate` for the plugin's own flags
- **Rules:** see the registry for surface N5 (`naming.common.*`, `naming.n5.*`, `naming.cross.*`)
- **Good / bad:** `--livetime-s`, `HEP_RESEARCH_PYTHON` / `--x`, `--doIt`

Procedure, levels and report: [semantic naming charter](semantic-naming.md).
