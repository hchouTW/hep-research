# Analysis data pipelines: ROOT, columnar processing and analysis code

Code-level companion of the hep-measurement skill (moved here from `skills/hep-measurement/references/data-pipelines.md`
and the code sections of its guide). The physics rules these pipelines implement (stable event keys, duplicate
removal across streams, signed weights, the normalization denominator) are stated in
[hep-measurement analysis design](../../hep-measurement/references/analysis-design.md) and
[weights and normalization](../../hep-measurement/references/weights-normalization.md); this file covers interfaces,
I/O and code. Related: [Python coding](python-hep-coding-patterns.md),
[C++, ROOT, and balanced design guidelines](root-balanced-design-guidelines.md).

## API selection

| API | Use for |
|---|---|
| C++ `ROOT::RDataFrame` | new compiled event loops, multithreaded columnar processing, many histograms from one selection, snapshots |
| PyROOT `ROOT.RDataFrame` | ROOT-native workflow with Python orchestration, no compiled helpers needed |
| uproot + awkward-array | Python-native analysis, jagged arrays, fast inspection, no full interactive ROOT |
| `TTreeReader` | manual C++ loops, custom object handling, where RDataFrame would obscure a simple algorithm |
| `SetBranchAddress` | legacy maintenance only - validate addresses/lifetimes carefully |
| RooFit/RooStats, pyhf, Combine | likelihood models, constrained fits, workspaces, toys, limits, intervals |

Don't mix more APIs than needed in one script; if mixing, keep boundaries clear (e.g. uproot for inspection,
RDataFrame for production, ROOT files as interchange).

awkward leading objects: apply the object mask, order each event with
`jets = jets[ak.argsort(jets.pt, axis=1, ascending=False)]`, cut with `ak.num(jets, axis=1) >= 2` (on the jets and the
weights together), then index `jets[:, 0]` and `jets[:, 1]`. Never write `jets.pt[ak.argsort(jets.pt, axis=1)[:, 0]]`:
an integer array indexes *events*, so it returns whole events, not one jet per event. Fill histograms with
`np.histogram(x, bins, weights=w)` and the same call with `weights=w**2`, then print or plot them; write a ROOT output
file only if asked, because uproot's histogram writing costs many turns.

## Run the code you deliver

Run any analysis code before delivering it: on the user's sample if there is one, otherwise on a small synthetic
sample built with the stated branch names (a few hundred events, e.g. written with uproot), and compare a count or
yield with a hand-computed expectation. For a jagged-jet analysis, build that sample with
`python3 <plugin root>/skills/hep-computing/scripts/make_synthetic_nanoaod.py --out sample.root` instead of writing
your own ROOT-writing code (it prints the expected counts and weight sums to compare with). Show the cutflow it
printed; if it could not run, say so instead of implying it works. Keep this to a few runs: if the same failure
survives three fixes, stop, deliver the code with the failing output, and say it does not yet work. Distinguish
successful execution, numerical validation, physical plausibility, and demonstrated statistical coverage.

## Code file requirement

When creating or modifying any code file (C++ source/headers, ROOT macros, PyROOT/uproot scripts, CMake files, config
loaders), include a short introductory comment block: purpose, what it does, and usage notes/dependencies/assumptions
(build/run command, expected input format and tree/branch names, units, weight conventions, ROOT version,
preconditions). Full convention: [C++, ROOT, and balanced design guidelines](root-balanced-design-guidelines.md#naming-comments-and-file-documentation).

## Normalization denominator in RDataFrame (skimmed NanoAOD)

A skim removes events, so neither `Events` entries nor a `genWeight` sum over skimmed events is the denominator.
NanoAOD stores the pre-skim sums in the `Runs` tree (`genEventSumw`, `genEventSumw2`, `genEventCount`; check the
branch names with `Runs->Print()`). Sum the tree over every file of the sample, including skim outputs that kept zero
events. Verified with PyROOT on synthetic files (2026-09-25):

```python
import ROOT

files = ["skim_0.root", "skim_1.root"]  # every file of the sample, including skim outputs with 0 events kept
lumi_fb, xsec_pb = 59.8, 88.3

# Denominator: signed generator-weight sum of the full produced sample, from the Runs tree
# (filled before any skim). Not Events.GetEntries(), not a sum over post-skim events.
sumw = ROOT.RDataFrame("Runs", files).Sum("genEventSumw").GetValue()
norm = lumi_fb * 1000.0 * xsec_pb / sumw  # fb^-1 -> pb^-1

df = ROOT.RDataFrame("Events", files).Define("w", f"genWeight * {norm}").Define("w2", "w * w")
cuts = [("skim", "true"), ("1 muon", "nMuon >= 1"), ("4 jets", "nJet >= 4")]
results, node = [], df
for name, expr in cuts:
    node = node.Filter(expr, name)
    results.append((name, node.Count(), node.Sum("w"), node.Sum("w2")))  # booked lazily, one event loop
for name, n, sw, sw2 in results:
    print(f"{name:8s} N={n.GetValue():6d} sumw={sw.GetValue():10.1f} +- {sw2.GetValue() ** 0.5:.1f}")
```

## Select an appropriate interface

Follow the existing project. RDataFrame suits new ROOT-native pipelines; uproot/awkward suits Python jagged-array processing; TTreeReader may remain appropriate for existing manual loops. Do not rewrite a RooFit model merely to standardize style. Inspect installed versions and the actual schema rather than assuming another NanoAOD production's branch names.

## Audit inputs

For every file, check successful opening, required trees/objects, entries, branches, types, and jagged-array structure. Do not silently skip failed remote files and report a complete sample. Bound retries and record failed files in the manifest. Run a small schema smoke test before reading the full production, and request only required branches.

Use chunked reads such as `uproot.iterate(..., expressions=..., step_size="100 MB", library="ak")` where appropriate. Merge sumw, sumw2, and cutflows across chunks and verify that changing chunk size preserves results within a declared tolerance. Additive quantities merge exactly up to floating-point order; medians, quantiles or fits do not merge by addition. See the [official uproot guide](https://uproot.readthedocs.io/en/latest/basic.html).

Check multiplicities before indexing `[:, 0]`. Object masks and event masks act on different axes. Object-level histograms require deliberate broadcasting of event weights and treatment of correlations from multiple objects in one event. Define behavior for empty lists, missing values, NaNs, and insufficient multiplicity.

Order matters: object cuts first, then count, then the event mask, then index. A
multiplicity check on the *uncut* collection followed by object cuts can leave events
with fewer than two selected objects and then fail (or silently pick unselected objects)
at `[:, 1]`.

```python
# Adaptation pattern: requires awkward and vector; Jet_* in GeV, genWeight signed.
import awkward as ak
import vector
vector.register_awkward()

jets = ak.zip({"pt": arrays["Jet_pt"], "eta": arrays["Jet_eta"],
               "phi": arrays["Jet_phi"], "mass": arrays["Jet_mass"]}, with_name="Momentum4D")
jets = jets[(jets.pt > 30.0) & (abs(jets.eta) < 2.5)]        # 1. object mask
jets = jets[ak.argsort(jets.pt, axis=1, ascending=False)]    # 2. order the *selected* objects
has_two = ak.num(jets, axis=1) >= 2                           # 3. count after the cuts
jets, weights = jets[has_two], arrays["genWeight"][has_two]  # 4. event mask on objects AND weights
mjj = (jets[:, 0] + jets[:, 1]).mass                         # 5. only now index
# Fill with weights and keep sum(w^2) (e.g. hist ... .Weight()); keep weights signed.
```

Do not pick the leading object with `arr[ak.argsort(arr, axis=1)[:, 0]]`: an integer array indexes events, so it returns whole events (for `pt = [[50,40,30],[60,20],[90,80,70,10]]` it gives `[[50,40,30]]*3`, not `[50,60,90]`). Reorder the objects with the argsort as in step 2, then take `[:, 0]`, or, for the single leading object, `ak.firsts(pt[ak.argmax(pt, axis=1, keepdims=True)])`.

## RDataFrame and C++

Book related actions before triggering evaluation or writing results to reduce repeated event scans. Name filters. Count/Report are unweighted; compute sums of weight and weight squared at each selection node for a weighted cutflow. Filter empty collections or define an explicit alternative before accessing their first elements.

Manage ROOT ownership explicitly. Histograms that must outlive an input TFile need appropriate cloning/detachment and ownership. Check zombie files, null pointers, branch types, and dictionary warnings. Multithreaded helpers must not share mutable event state. Derive smearing seeds from stable event identifiers and source labels rather than scheduling order.

Avoid SetBranchAddress bindings to expired local storage. Snapshot branch selection, output tree names, and compression form part of the output contract. If event order changes, compare by stable event keys rather than row index. Results are invariant under event order only for order-independent algorithms: time-dependent state, online calibration and sequence models change with it.

## Performance and preservation

Measure I/O, decompression, selection, correction lookup, and histogramming separately before optimizing. Bound memory per worker and avoid oversubscription from Python workers multiplied by ROOT threads. Distributed merges must compare expected and processed files/counts and prevent duplicate outputs from retries.

Preserve input manifests, commits and uncommitted diffs, configuration checksums, software versions, calibration payload checksums, seed strategies, commands, and failed-file lists. Do not include authentication tokens or credentials in manifests.

## Time-sliced records and mergeable reductions

Per-period records (live time, counts, sums of weights per time slice) reach an analysis split over files and jobs,
and a slice can appear twice: at a file boundary, in a resubmitted job, or in two overlapping productions. A reduction
is mergeable only if it is made in two steps.

1. **Deduplicate by a stable key.** Key each record by what identifies the slice (a period id, or run and slice
   number), never by the file or the row index. Keep one copy of identical duplicates and report how many were
   removed; refuse a key whose copies differ, because one slice cannot have two live times.
2. **Then sum** the additive columns (counts, live times, sums of weights and their squares). Means, medians, rates
   and fractions are not additive: recompute them from the merged sums, or declare a merge rule for them
   (`local_partition.py merge --rule KEY=RULE`; an undeclared non-additive key is refused).

Partitioned, the same two steps go through `core/partition`: each chunk returns its records and sources unreduced, the
chunks are merged with `concat` rules, and the deduplication and sum happen once, on the merged records, in key order,
so the partitioned and the single-run results agree to the last bit. Record the merge inputs (chunks merged and
expected, the source file digests), so the merge can be shown complete later. A merge that is incomplete gives no
reduced number.

`<plugin root>/skills/hep-computing/assets/time_slice_reduction.py` implements this (`reduce`, `partial` as a
`local_partition.py` worker, `finalize`); its tests show a slice split across two files counted once and the
partitioned result equal to a single run.
