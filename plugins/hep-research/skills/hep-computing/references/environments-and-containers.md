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
| Virtual environment plus lock file | Python packages only, on the host's Python and system libraries | local development and unit tests; not enough for a published result that depends on ROOT or compilers |

Mixing routes (a venv on top of an LCG view, `pip install --user` inside a container) is where environments silently
diverge: record both layers or avoid the mix.

## Record with every run

Run, inside the environment that produced the result:

```
python3 <plugin root>/skills/hep-computing/scripts/environment_manifest.py record --project . --out environment.json
```

It writes the `environment` object and the `tools` list of a `computational-run` artifact: Python version and
executable, platform, where the environment comes from (`lcg-view`, `container`, `conda`, `venv`, `system`), the
versions of the named packages (`--packages`, or `--all-packages`), a fixed list of environment variables
(`LCG_VERSION`, `BINARY_TAG`, `ROOTSYS`, `APPTAINER_CONTAINER`, ...) and the project's git commit and dirty state.
Other variables are never recorded: they can hold credentials. Add by hand what the script cannot see: the LCG
release and platform you sourced, the container image digest (`apptainer inspect`), compiler flags of compiled code.

## Check before reusing a result

```
python3 <plugin root>/skills/hep-computing/scripts/environment_manifest.py check --manifest environment.json
```

lists every difference in Python, platform, origin, package versions and recorded variables (exit 1 on drift). A drift
is not an error by itself; it means the earlier result is not yet reproduced here. Rerun the closure or regression
test that the result depends on and compare within its declared tolerance before reusing the number.

## Pitfalls

- `pip install` into an LCG view or a read-only container fails or lands in `~/.local`, which then shadows the pinned
  versions on every later run; use a venv with `--system-site-packages` and record it.
- A dirty git tree means the commit does not identify the code; commit or record the diff.
- Floating tags (`latest`, `LCG_dev3`, nightly views) are not pins.
- Thread counts and BLAS libraries change floating-point results at the last digits; compare with tolerances, not
  bytes, unless the run was built to be bit-reproducible.
