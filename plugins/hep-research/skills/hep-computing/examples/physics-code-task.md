# Prove the RDataFrame Cutflow Reproduces a TTreeReader Event Loop Bin for Bin

<!-- example: experiment-specific illustration -->
> Verified against the repository (`plugins/hep-research/`) on 2026-10-13. Paths are relative to the plugin root. The physics is a synthetic dimuon selection; the shape of the task is the usual one when an event loop is ported to RDataFrame: same selection, same weights, same histogram, and a comparison that would catch one event or one bin of difference.

## Background

`adapters/root-uproot/assets/rdf_cutflow_analysis.cpp` is an RDataFrame cutflow: at least two muons, leading-muon
pt above 25 GeV, leading-muon |eta| below 2.4, and a 50-bin histogram of the leading-muon pt from 0 to 200 GeV
weighted by `event_weight`. It enables implicit multithreading. Its test,
`tests/adapters/test_root_cpp_assets.py`, checks that the C++ cutflow counts equal those of the PyROOT asset
`adapters/root-uproot/assets/pyroot_rdf_cutflow_analysis.py`, but both are RDataFrame programs: nothing compares
them with a plain event loop, and nothing compares the histogram itself. Requesters porting their own
`TTreeReader` loops copy this asset as the model, so a port that is subtly wrong here (an off-by-one in the cut, a
weight applied twice, events lost to threading) would be copied too.

The requester wants a reference `TTreeReader` implementation of the same selection and a check that the port
reproduces it: identical cutflow counts and identical histogram bin contents and errors.

## Objective

After this task, a new C++ program applies the selection with a `TTreeReader` loop, and a test runs both programs
on the synthetic fixture and passes only if every cutflow count is equal and every bin content and bin error of
`h_leading_muon_pt` is equal to the last bit, single-threaded and with implicit multithreading.

## Scope

### In Scope

- A new `TTreeReader` program next to the RDataFrame one, with the same command-line options and the same output
  histogram name and binning.
- A comparison test in `tests/adapters/test_root_cpp_assets.py` using
  `skills/hep-computing/scripts/compare_root_histograms.py` with zero tolerance.
- Listing the new asset in `adapters/root-uproot/adapter.json`.

### Out of Scope

- Changing the selection, the binning or the weights.
- Byte equality of the two ROOT files: a ROOT file stores creation times and a UUID, so two files with identical
  histograms are not byte-identical. The comparison is on the histogram's bin contents, errors and edges.
- Performance of either program.

## Repository Context

Verified by inspection and by running the tests on 2026-10-13 (Homebrew ROOT 6.38.04):

- `adapters/root-uproot/assets/rdf_cutflow_analysis.cpp` lines 81-90: the three `Filter` calls, the two `Define`
  calls for `Muon_pt[0]` and `Muon_eta[0]`, and `Histo1D` with `event_weight`; `ROOT::EnableImplicitMT()` at line
  73.
- `tests/skills/hep_computing/make_root_fixtures.py` writes `events.root` (5000 events, `nMuon`, jagged
  `Muon_pt`/`Muon_eta`, `event_weight` of +1 or -1, about 5 % negative) with a fixed seed.
- `tests/adapters/test_root_cpp_assets.py` builds the C++ assets with `root-config --cxx --cflags --libs` and skips
  without ROOT; `test_cpp_cutflow_equals_pyroot_cutflow` compares cutflow text only.
- `skills/hep-computing/scripts/compare_root_histograms.py` compares edges and bin contents (with `--sigma-tol`,
  differences in units of the combined bin errors) and exits 1 on any difference beyond `--abs-tol`/`--rel-tol`;
  it does not compare the bin errors themselves.

## Technical Approach

1. Run `tests/adapters/test_root_cpp_assets.py` before any change (with `HEP_ROOT_PYTHON` set where PyROOT needs a
   specific interpreter) and record the cutflow counts the RDataFrame program prints.
2. Write the `TTreeReader` program: `TTreeReaderValue<Int_t>` for `nMuon`, `TTreeReaderArray<Float_t>` for
   `Muon_pt` and `Muon_eta`, `TTreeReaderValue<Float_t>` for `event_weight`; apply the three cuts in the same
   order with the same comparison operators (`>=`, `>`, `<` on `std::abs`); count each stage; fill a `TH1D` with
   the same name, title and binning, `Sumw2()` before filling, and `SetDirectory(nullptr)` before the input file
   closes.
3. Check the multiplicity before reading element 0, as the RDataFrame version does through its first `Filter`.
4. Compare: run both programs on `events.root`, then
   `compare_root_histograms.py --reference loop.root --candidate rdf.root --hist h_leading_muon_pt --abs-tol 0 --rel-tol 0 --include-flow`,
   compare the three cutflow counts, and compare the bin errors (`GetBinError` for every bin, or uproot
   `errors(flow=True)`) separately, since the script does not.
5. Repeat the comparison with the RDataFrame program run single-threaded. With the fixture's integer weights the
   multithreaded sums are exact; with general floating-point weights they are not, and the test must say which case
   it checks.
6. Break the port on purpose (`>=` instead of `>` in the pt cut; the weight applied twice) and confirm the
   comparison fails each time; revert.

## Deliverables

- New `adapters/root-uproot/assets/ttreereader_cutflow.cpp` (proposed name).
- A new test in `tests/adapters/test_root_cpp_assets.py` comparing cutflow counts and the histogram with zero
  tolerance, single-threaded and multithreaded.
- `adapters/root-uproot/adapter.json` listing the new asset.

## Acceptance Criteria

- On `events.root`, both programs print the same three cutflow counts, and the first equals 5000.
- `compare_root_histograms.py` with `--abs-tol 0 --rel-tol 0 --include-flow` exits 0 for the pair, and every bin
  error is equal, with and without implicit multithreading in the RDataFrame program.
- Each of the two deliberate mutations in step 6 makes the comparison exit 1; the mutation run is described in the
  change description.
- The test skips, and says why, when ROOT is not available; it never passes without running.
- `python3 -m unittest tests.adapters.test_root_cpp_assets` passes with ROOT available.

## Validation

- `python3 -m unittest tests.adapters.test_root_cpp_assets -v` before the change (green), with the new test before
  the program exists (red), and after (green).
- `python3 skills/hep-computing/scripts/compare_root_histograms.py --reference loop.root --candidate rdf.root --hist h_leading_muon_pt --abs-tol 0 --rel-tol 0`
  run by hand once, expecting exit 0 and `"status": "pass"`.
- `python3 skills/hep-computing/scripts/lint_task.py` on this task with `--repo` set to the plugin root.

## Open Questions

- Should the reference program stay in `adapters/root-uproot/assets/` as a worked example for requesters, or live
  under `tests/` as test-only code? **Requires Confirmation**; the deliverables assume the assets folder.
- With a fixture that had non-integer weights, would the requester accept a relative tolerance of 1e-12 for the
  multithreaded comparison instead of exact equality? **Open Question**; the current fixture does not need it.
- Is a `TTreeReader` reference enough, or does the requester also want the PyROOT asset compared histogram for
  histogram? **TBD.**

## References

- `adapters/root-uproot/assets/rdf_cutflow_analysis.cpp`, `adapters/root-uproot/assets/pyroot_rdf_cutflow_analysis.py`:
  the two RDataFrame implementations.
- `tests/adapters/test_root_cpp_assets.py`, `tests/skills/hep_computing/make_root_fixtures.py`: the test and the
  fixture.
- `skills/hep-computing/scripts/compare_root_histograms.py`: the comparison.
- `skills/hep-computing/references/root-balanced-design-guidelines.md`, "Concrete ROOT/RDataFrame Coding Patterns" and
  "Ownership Guidelines".
<!-- /example -->
