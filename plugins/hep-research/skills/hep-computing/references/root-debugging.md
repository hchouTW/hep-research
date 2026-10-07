# Debugging ROOT, PyROOT, and C++ Builds

## Environment

```bash
root --version
root-config --version
root-config --cflags --libs
```

If compilation fails with missing ROOT headers, check that `root-config --cflags` is
included in the build command. If linking fails with unresolved ROOT symbols, check
that `root-config --libs` is included, and that `find_package(ROOT ...)` in CMake
requests the components the code actually links against (see
[Build setup](cmake-and-build.md)). `<plugin root>/skills/hep-computing/scripts/check_root_cpp_env.sh` automates this
first check.

## File inspection

```bash
rootls input.root
root -l input.root
```

Inside an interactive ROOT session:

```cpp
_file0->ls();
```

`<plugin root>/skills/hep-computing/scripts/inspect_root_file.py` and `<plugin root>/skills/hep-computing/scripts/inspect_root_file.C` list keys, trees,
branches, and histogram metadata from the command line without an interactive
session.

## Missing tree or object

Check top-level keys, then retrieve safely rather than dereferencing a null pointer:

```cpp
file->ls();

auto* tree = file->Get<TTree>("Events");
if (!tree) throw std::runtime_error("Missing tree Events");
```

## Missing branch

```cpp
tree->Print();
if (!tree->GetBranch("pt")) {
    throw std::runtime_error("Missing branch pt");
}
```

## Fit issues

Check, in order: histogram entries (empty histograms fit "successfully" to
meaningless parameters), fit range, initial parameter values, and fit status. See
[Models and fitting](../../hep-statistics/references/likelihood-fitting.md) for status/covariance-quality
diagnostics beyond this first pass.

## Dictionary issues

If ROOT reports that it cannot find a class dictionary, load the library defining that
class:

```cpp
gSystem->Load("libMyAnalysis.so");
```

The library must actually contain the ROOT dictionary for the class — a missing
dictionary generation step in the build is a common root cause, not a runtime
misconfiguration.

## Reading flat array branches and comparing files

- RDataFrame (seen on an older ROOT 6 release) presents a fixed-size array branch as a flattened `RVec<T>`: element `[2][0]`
  of a `[6][4]` array is index 8 in a jitted string. That release could not read a `Bool_t` array in a jitted
  expression (no `RVec<bool>` from the reader array); read it with `TTree::Draw` or `TTreeReaderArray<Bool_t>`, or
  store such flags as `Short_t`.
- Two files whose classes have different member names must be read in two processes: ROOT reuses the emulated class of
  the first file it opens, and the renamed members of the second then read back as defaults.
- `TLeaf::GetValue` on emulated classes returned only element 0 of each array and vector in one set of checks;
  evaluate leaves through a `TTreeFormula` (as `TTree::Draw` does) when every element matters.
- A macro compiled with ACLiC keeps its `*_C.so` beside the source. After a header it includes changed, a cached
  library built from the old header gave a stale answer (41 fields for a 40-member struct) until the macro was
  recompiled with `.C++`.

## Symptom table

For yield/refactor/multithreading/fit symptoms beyond ROOT-specific build and I/O
errors, see the broader symptom table in [Validation](../../hep-analysis/references/analysis-validation.md).
