# Python Coding Patterns: PyROOT, uproot, and awkward

Use this reference for concrete Python code and CLI conventions. See
[Data pipelines](../../hep-analysis/references/data-pipelines.md) for the design-level treatment of chunked
reads, schema audits, and ownership; this file covers the code-level idioms.

## Naming

Google/PEP 8 style: `snake_case` functions/vars, `PascalCase` classes,
`UPPER_SNAKE_CASE` constants, `_leading_underscore` for private helpers. For C++/ROOT
naming and general/ROOT-specific C++ design guidance, see
[C++, ROOT, and Balanced Design Guidelines](root-balanced-design-guidelines.md).

## CLI structure

- Use `argparse` and a `main()` function.
- Use `pathlib.Path` for file paths.
- Validate inputs before opening many files.
- Keep selection and weight helper functions pure when practical.
- Use logging for production scripts; short one-off scripts may print a final summary
  instead.

## PyROOT

- Call `ROOT.gROOT.SetBatch(True)` for any script that creates plots.
- Validate files with `TFile.Open` and `IsZombie()`.
- Validate trees and histograms before dereferencing.
- Close output files explicitly.
- Be careful with object ownership when returning ROOT objects from helper functions —
  a Python-side reference does not always keep the underlying C++ object alive.

## uproot and awkward

- Read only the branches required for the event processing at hand.
- Use awkward masks for jagged collections; check multiplicities before indexing
  `[:, 0]`. With object cuts, count *after* the cuts (see the ordered pattern in
  [data pipelines](../../hep-analysis/references/data-pipelines.md)).
- Convert to NumPy only at plotting or histogram-filling boundaries.
- Preserve event weights as arrays aligned with the final selected event mask.
- Document whether a systematic affects weights, object kinematics, or both.

```python
import awkward as ak
import uproot

for arrays in uproot.iterate(files, expressions=["Muon_pt", "Muon_eta", "event_weight"],
                              library="ak", step_size="100 MB"):
    mask = ak.num(arrays["Muon_pt"]) >= 2  # check multiplicity before indexing
    values = arrays["Muon_pt"][mask, 0]
    weights = arrays["event_weight"][mask]
```

## Plotting

- Use `mplhep` for experiment-style Python plots with matplotlib used explicitly (no
  notebook-only state).
- Save plots with explicit paths and `bbox_inches="tight"`.
- Include luminosity, energy, channel, and region labels when known.
- Use ratio panels for data/MC comparisons; see
  [Histograms and uncertainties](../../hep-analysis/references/histograms-efficiencies.md) for what the ratio and
  its uncertainty should represent.

## Tests

Lightweight checks, in increasing order of cost:

```bash
python -m py_compile analysis.py
python analysis.py --help
python -m pytest
```

For regression validation, compare selected event counts, cutflow counts, histogram
integrals, maximum absolute/relative bin differences, and fit parameters/uncertainties
against a reference — see [Validation](../../hep-analysis/references/analysis-validation.md) for the full regression
checklist.
