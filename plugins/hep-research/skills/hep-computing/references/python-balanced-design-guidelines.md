# Balanced Python Design Guidelines

A checklist for Python in HEP work: analysis scripts, uproot/awkward and PyROOT code, small tools and their
tests. Concrete PyROOT, uproot and awkward idioms are in [Python HEP coding patterns](python-hep-coding-patterns.md);
naming, comments and file headers are decided once in the
[ROOT guidelines](root-balanced-design-guidelines.md#naming-comments-and-file-documentation) (the Python form:
PEP 8 and the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), `snake_case`
functions and variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constants, a leading underscore for non-public
names, type hints on public functions). Python 3.10+ is assumed (`X | None`, `list[str]`). Follow established
repository conventions when they intentionally differ.

## Design rules

- **Functions first.** Selections, corrections, weights and kinematics are pure functions of arrays
  (`def select_dimuons(events: ak.Array) -> ak.Array`); a script is a `main()` that wires them together.
- **Dataclasses for configuration and results** (`@dataclass(frozen=True)` for a cut set, a binning, a fit result);
  a class only when it owns a resource or guards an invariant. No classes of static methods; no `utils.py` holding
  unrelated helpers.
- **Explicit inputs.** Paths, seeds, cut values and the random generator (`np.random.default_rng(seed)`) are
  parameters, never module globals or `np.random.seed` calls hidden inside functions.
- **Protocols or plain functions for interchangeable behaviour** (two fitters, two readers); inheritance only for a
  real is-a relation, kept shallow.

## Resources and errors

- `with` for every file and resource: `with open(...)`, `with uproot.open(path) as f`,
  `with ROOT.TFile.Open(path) as f` (ROOT 6.22+), `with uproot.recreate(path) as f`, `tempfile.TemporaryDirectory()`.
- Exceptions are the error mechanism. Raise a specific type with a message naming the file, object and value
  (`raise KeyError(f"tree 'Events' not found in {path}")`); catch only what you can handle, at the boundary
  (`main()` turns it into one line on stderr and an exit code). Never `except Exception: pass`.
- Validate inputs before the expensive part: files exist, trees and branches are present, units and binning match.
- CLI: `argparse`, `pathlib.Path`, documented exit codes, a JSON status for machine use (the skill's script
  contract, `SKILL.md` invariant 5).

## Correctness checks

- **Mutable defaults:** `def f(cuts=[])` shares one list between calls; use `None` and create inside.
- **Aliasing:** NumPy slicing returns views and awkward arrays share buffers: `w = weights; w *= 2` changes
  `weights`. Copy (`.copy()`, `ak.copy`) before modifying data you do not own.
- **Masks and alignment:** weights, event IDs and per-event quantities stay aligned with the same mask; apply a
  mask to every array of the event, not to one of them. Check multiplicities before `[:, 0]`.
- **Floating point:** accumulate in float64 (`np.sum(x, dtype=np.float64)` when `x` is float32); compare with
  `math.isclose`/`np.isclose` and a stated tolerance; never `==` on computed floats.
- **NaN and inf** propagate silently: check `np.isfinite` on inputs that come from files and on results before
  writing them.
- **Integer division and types:** `//` truncates toward minus infinity; `np.int32` overflows silently on large
  sums; booleans are integers (`True + True == 2`).
- **Iteration:** no Python loop over events for columnar data; vectorize with NumPy/awkward, or use numba for an
  unavoidable loop and check it against a small pure-Python version.
- **Determinism:** seeds recorded with the output; dictionaries and sets are not a stable order for anything that
  ends in a file (`sorted(...)`).

## Type hints and modules

- Type hints on public functions and dataclasses; `mypy` on library code that others import.
- One module per responsibility; no side effects at import time (no file reads, no `ROOT.gROOT.SetBatch` except in
  the script that runs); `if __name__ == "__main__": sys.exit(main())`.
- Import optional heavy packages (ROOT, torch, uproot) inside the function that needs them when a tool must also
  work without them, and explain the missing dependency in one line.

## Testing

- `pytest` or `unittest` for the pure functions with hand-computed values and edge cases (empty arrays, zero or
  negative weights, values on bin edges, NaN inputs).
- A small synthetic input with known answers (`scripts/make_synthetic_nanoaod.py`) for the event selection; compare
  the full output against a stored reference within a stated tolerance.
- Tests do not depend on the working directory, the network or the order they run in.

## Grep-able anti-patterns

| Pattern | Problem | Instead |
|---|---|---|
| `def .*=\[\]` or `=\{\}` in a signature | shared mutable default | `None`, create inside |
| `except:` / `except Exception: pass` | hides the failure | catch the specific error at the boundary |
| `np.random.seed(` inside a function | hidden global state | `rng = np.random.default_rng(seed)` passed in |
| `f = ROOT.TFile.Open(` without `with`, `f.Close()` on one path only | file left open on errors | `with ROOT.TFile.Open(...) as f` |
| `for i in range(len(events))` | Python loop over events | columnar operations |
| `== 0.1` on computed floats | rounding | `math.isclose(..., rel_tol=...)` |
| `[:, 0]` without `ak.num(...) >= 1` | index error or wrong event | mask on multiplicity first |
| `import ROOT` at module top in a tool that must run without ROOT | `--help` fails without ROOT | import inside the function |
| `class .*Utils` with only `@staticmethod` | no responsibility | module-level functions |
