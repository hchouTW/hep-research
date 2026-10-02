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
[Build setup](15-cmake-and-build.md)). `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/check_root_cpp_env.sh` automates this
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

`${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/inspect_root_file.py` and `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/inspect_root_file.C` list keys, trees,
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
[Models and fitting](../../hep-statistics/references/07-likelihood-fitting.md) for status/covariance-quality
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

## Symptom table

For yield/refactor/multithreading/fit symptoms beyond ROOT-specific build and I/O
errors, see the broader symptom table in [Validation](../../hep-analysis/references/12-validation.md).
