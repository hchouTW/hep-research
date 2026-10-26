# ROOT usage patterns: histogram errors, efficiency objects, workspaces, installation

Object-level rules that decide whether a ROOT number and its error bar are what the code claims. Design, ownership
(`AddDirectory`, `SetOwnership`), dictionaries, RDataFrame, RNTuple, `Vary`, `Snapshot`, `AsNumpy`, schema evolution
and `hadd` are in [ROOT design](root-balanced-design-guidelines.md); the statistics of sum w and sum w^2 are in
hep-measurement's [histograms and efficiencies](../../hep-measurement/references/histograms-efficiencies.md).
Boundary: using the objects correctly is this skill's; which interval to quote is hep-statistics'; measuring an
efficiency (tag-and-probe, truth matching) is hep-detector's.

Sources read 2026-10-17 (generic User-Agent): the TH1, TEfficiency and RooWorkspace class references on root.cern
(master), the ROOT 6.38 release notes and the install page, and the PyPI record of the `root` package. Read level:
the sections quoted below.

## Histogram errors

- **Sumw2 before a weighted fill.** "If TH1::Sumw2 has been called before filling, the sum of squares of weights is
  also stored." Without it the error of a bin is sqrt(content), which is wrong for weights. `TH1::SetDefaultSumw2()`
  turns it on for every new histogram. Check: `check_histogram_errors.py` flags `sumw2-missing` (weighted fill,
  fTsumw2 != fTsumw, no Sumw2 array).
- **Poisson errors for counts.** `SetBinErrorOption(TH1::kPoisson)` (enum `EBinErrorOpt`: `kNormal`, `kPoisson`,
  `kPoisson2`) gives asymmetric errors through `GetBinErrorLow`/`GetBinErrorUp`; it is meant for unweighted counts.
  Whether a central interval suits the result is hep-statistics' call.
- **Divide.** `Divide(h1, h2, c1, c2)` assumes uncorrelated histograms. With option `"B"` binomial errors are
  computed and c1, c2 are ignored; when passed = total the binomial error is zero, so efficiencies near 1 need
  `TGraphAsymmErrors::BayesDivide` or a `TEfficiency` interval instead. Call `Sumw2()` before dividing if the errors
  are used later.
- **Scale.** `Scale(c)` multiplies contents and errors; the stored fill statistics (fEntries, fTsumw) describe the
  fill, not the scaled object. A unit-weight histogram scaled after filling has Sumw2 = c x content everywhere:
  `check_histogram_errors.py` reports it as `scaled` (a warning). Bin errors that no uniform scale explains
  (`SetBinError` on some bins, edited contents) are `sumw2-inconsistent`.
- **Flow bins.** Bin 0 is the underflow and bin nbins+1 the overflow; integrals and `GetEntries()` include or exclude
  them by option. State the flow policy; the check warns above `--max-flow-fraction` of |content|.
- **Negative bins** appear with negative event weights; fits, ratios and log plots need a declared treatment.

## TEfficiency objects

- Built from `passed` and `total` histograms that satisfy `TEfficiency::CheckConsistency` (same binning, passed <=
  total); otherwise construction fails. `check_histogram_errors.py` checks passed <= total per bin on saved objects.
- The intervals are statistic options (`kFCP` Clopper-Pearson, `kFNormal`, `kFWilson`, `kFAC` Agresti-Coull, and
  Bayesian ones); the choice belongs to hep-statistics.
- Counts are integers; "a filling with weights is not possible" in the plain mode: a global weight is set with
  `SetWeight`, and `SetUseWeightedEvents()` switches to weighted events. Say which mode produced a number.
- An object built from existing histograms is not attached to the current directory; write it explicitly.

## RooWorkspace problems (software, not statistics)

- **Name clashes on import.** If an object with the same name exists, the import of the whole tree is cancelled with
  an error. Options: `RenameConflictNodes(suffix)`, `RenameAllNodes`, `RenameAllVariables`,
  `RenameVariable(in, out)`, or `RecycleConflictNodes()` (connects to the existing nodes and changes the imported
  definition if they differ: use with care). A second dataset with the same variable names is the common case.
- **Ownership.** `import` stores copies; keep using the workspace's objects (`ws.pdf(...)`, `ws.var(...)`), not the
  originals.
- **Persistence.** Custom classes need their dictionaries to be read back; `importClassCode()` (or
  `autoImportClassCode(true)`) stores their source in the workspace for portability.
- **Crashes when reading large workspaces.** Deeply nested PDFs can exhaust the stack, which shows as crashes at
  random places or a silent exit; check `ulimit -s` and read again. Statistical results from a workspace (fits,
  limits) go to hep-statistics; `roofit_workspace_summary.py` lists what a workspace holds.

## Installation routes

| Route | Command | Python | Note |
|---|---|---|---|
| conda-forge | `conda config --set channel_priority strict`; `conda create -c conda-forge --name <env> root` | the environment's | Linux and macOS; strict channel priority avoids conflicts (install page) |
| LCG view on CVMFS | `source /cvmfs/sft.cern.ch/lcg/views/<LCG_n>/<platform>/setup.sh` | the view's | [environments](environments-and-containers.md) |
| Homebrew, Linux package managers | per the install page | the package's | PyROOT loads only under the Python it was built for |
| PyPI | `pip install root` | 3.10 to 3.14 (wheels cp310-cp314) | alpha series (0.1a8, 2025-10-14, to 0.1a12, 2026-05-20), Linux x86_64 wheels only (manylinux_2_28); which ROOT release a version ships is not stated on PyPI: to-verify |

ROOT 6.38 (release notes, 2025-11-27) requires Python 3.9 or newer; the plugin's floor is 3.13, so pick an
interpreter with `scripts/find_python.py` and record it with `environment_manifest.py`.

<a id="naming-n3"></a>
### Naming: objects inside ROOT files (N3)
- **Extractor:** `extract_names.py --surface N3` (hep-computing; inputs: every object in every folder of the ROOT files in scope, read with uproot or else PyROOT; without either, each file is listed as skipped and N3 is unsupported)
- **Entity kinds and level floors:** generated from `contracts/naming/surfaces.json`, not restated by hand:

<!-- naming-kinds:N3: generated from contracts/naming/surfaces.json by contracts/naming_registry.py sections; do not edit -->

| Kind | Level floor | Format | Rename policy |
|---|---|---|---|
| `object` | C2 | — | matrix |
| `shape_histogram` | C3 | `^[A-Za-z0-9_]+(Up\|Down)?$` | matrix |

<!-- /naming-kinds:N3 -->

- **The name must say:** the quantity, the selection or region and the sample; a shape variation is `<process>_<nuisance>Up`/`Down`, exactly as the datacard's shapes line builds it
- **Rename policy:** matrix; a shape histogram is C3: its name is part of the statistical model (rename it only with the nuisance, through one change set)
- **Rules:** see the registry for surface N3 (`naming.common.*`, `naming.n3.*`, `naming.cross.*`)
- **Good / bad:** `dimuon_mass_sr`, `ttbar_jesUp` / `h1`, `hist_new`, `ttbar_jes_up`

Procedure, levels and report: [semantic naming charter](semantic-naming.md).
