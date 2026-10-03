# Data Pipelines, ROOT, and Columnar Processing

## Select an appropriate interface

Follow the existing project. RDataFrame suits new ROOT-native pipelines; uproot/awkward suits Python jagged-array processing; TTreeReader may remain appropriate for existing manual loops. Do not rewrite a RooFit model merely to standardize style. Inspect installed versions and the actual schema rather than assuming another NanoAOD production's branch names.

## Audit inputs

For every file, check successful opening, required trees/objects, entries, branches, types, and jagged-array structure. Do not silently skip failed remote files and report a complete sample. Bound retries and record failed files in the manifest. Run a small schema smoke test before reading the full production, and request only required branches.

Use chunked reads such as `uproot.iterate(..., expressions=..., step_size="100 MB", library="ak")` where appropriate. Merge sumw, sumw2, and cutflows across chunks and verify that changing chunk size preserves results. See the [official uproot guide](https://uproot.readthedocs.io/en/latest/basic.html).

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

Avoid SetBranchAddress bindings to expired local storage. Snapshot branch selection, output tree names, and compression form part of the output contract. If event order changes, compare by stable event keys rather than row index.

## Performance and preservation

Measure I/O, decompression, selection, correction lookup, and histogramming separately before optimizing. Bound memory per worker and avoid oversubscription from Python workers multiplied by ROOT threads. Distributed merges must compare expected and processed files/counts and prevent duplicate outputs from retries.

Preserve input manifests, commits and uncommitted diffs, configuration checksums, software versions, calibration payload checksums, seed strategies, commands, and failed-file lists. Do not include authentication tokens or credentials in manifests.
