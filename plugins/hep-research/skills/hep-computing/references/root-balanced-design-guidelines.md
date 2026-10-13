# C++ and ROOT Design Guidelines

The reference for writing and reviewing C++ code that touches ROOT: the object model (`TObject`, dictionaries,
directory ownership), RDataFrame and TTree/RNTuple patterns, histograms and plots, and the conventions every
hep-computing reference shares. General C++ design (classes, structs, RAII, ownership, const, templates, tests) is the
checklist in [C++ guidelines](cpp-balanced-design-guidelines.md); Python is in
[Python guidelines](python-balanced-design-guidelines.md) and [Python HEP coding](python-hep-coding-patterns.md),
Bash in [Bash guidelines](bash-balanced-design-guidelines.md). Not the statistical treatment of pipelines: see
[Data pipelines](../../hep-analysis/references/data-pipelines.md). Follow established repository conventions when
they intentionally differ from this reference.

Conventions used in every example, decided once here (and in the C++ guidelines, which link back):

- **Naming:** `snake_case` variables and parameters, `PascalCase` types and functions, `kPascalCase` constants,
  `trailing_underscore_` data members, `ALL_CAPS` only for macros (the Google C++ Style Guide convention); see
  [Naming Guidance](#naming-guidance).
- **Language standard:** C++17, the standard ROOT 6.38 and 6.40 are built with. Take `-std` from
  `root-config --cflags` (or `ROOT_CXX_STANDARD` in CMake) and do not add a second one; mark C++20 features
  (`std::numbers`, `std::span`, ranges, designated initializers) as "C++20 only".
- **Errors:** exceptions are allowed (ROOT, the STL and Cling throw); translate a ROOT failure at the boundary into an
  exception or an explicit return value and keep one style per component; see [Error Handling](#error-handling).
- **Paths:** `std::filesystem` (C++17) for path handling; the Google guide's ban on `<filesystem>` is not adopted.
- **Non-owning members:** a pointer documented as non-owning and non-null, never a reference member; see
  [Ownership Guidelines](#ownership-guidelines).

## Read only what the task needs

| Task | Section |
|---|---|
| Writing or fixing an RDataFrame/TTreeReader event loop, RNTuple, histograms, plots | [Concrete ROOT/RDataFrame Coding Patterns](#concrete-rootrdataframe-coding-patterns) |
| Header comment block, naming, comments (all languages) | [Naming, Comments, and File Documentation](#naming-comments-and-file-documentation) |
| Segfaults/leaks around TFile, histograms, `SetDirectory` | [Ownership Guidelines](#ownership-guidelines) (and [crash and memory debugging](crash-and-memory-debugging.md)) |
| Custom classes in a TTree, `ClassDef`, LinkDef, "no dictionary" errors | [Class Dictionaries and I/O](#class-dictionaries-and-io) (and [root-debugging.md](root-debugging.md)) |
| `TObject` or a plain class, flat branch structs | [TObject or Plain C++](#tobject-or-plain-c) |
| Reviewing a C++/ROOT design or diff | [Design Checklist](#design-checklist), [Anti-Patterns to Avoid](#anti-patterns-to-avoid-recap) |

## Core Principle

Take on ROOT's object model (`TObject` inheritance, a dictionary, directory ownership) only for a type that needs
one of ROOT's services: persistence through `TObject` APIs or ROOT containers, `TTree`/RNTuple storage of a class,
ROOT's runtime type system (`TClass`, `IsA()`), or interactive introspection (`TBrowser`, `.ls`, the Cling prompt).
Everything else (helper types, algorithm parameters, intermediate results, configuration) stays plain C++ and
follows the [C++ guidelines](cpp-balanced-design-guidelines.md). Where ROOT's ownership or error model differs from
general C++ practice, make the departure explicit and contained: one owner, a `SetDirectory(nullptr)`, a checked
return value at the boundary.

## TObject or Plain C++

### When (Not) to Inherit from TObject

Writing to a file does not need `TObject`: any class with a dictionary can be written with
`file->WriteObject(&obj, "name")` and read back with `file->Get<MyType>("name")`, and a non-`TObject` class with a
dictionary can be a `TTree` branch. Inherit from `TObject` only when the type needs one of:

- A ROOT container of `TObject*` (`TList`, `TObjArray`, `TClonesArray`) or an API that takes `TObject*`
  (`TDirectory::Append`, `TCollection` algorithms, `TObject::Write` by its own name).
- Directory registration so `.ls`/`TBrowser` list it and the directory deletes it, or `TObject` services such as
  `Clone()`, `IsA()`, `Draw()` and `Print()` through the base class.

Do **not** inherit from `TObject` for:

- Analysis-internal helper classes (selection logic, a fit-result wrapper, a
  systematics bookkeeping object) that never get written to a file or handed to a
  ROOT container. A plain class following the guidance above is simpler, needs no
  dictionary, and gets real RAII and move semantics for free.
- Data that is naturally tabular and only ever consumed as `TTree` branches — model
  it as a flat struct of built-in types (or `std::vector<T>` of them), not a
  `TObject`-derived class with a dictionary.

```cpp
// Needs TFile persistence and TBrowser introspection: TObject is justified.
class CalibrationSet : public TObject {
 public:
  CalibrationSet() = default;
  CalibrationSet(int run, std::vector<double> constants)
      : run_(run), constants_(std::move(constants)) {}

  int run() const { return run_; }
  const std::vector<double>& constants() const { return constants_; }

 private:
  int run_ = 0;
  std::vector<double> constants_;

  ClassDef(CalibrationSet, 1)
};

// Analysis-internal, never persisted: plain class, no TObject, no dictionary.
class SelectionResult {
 public:
  SelectionResult(bool passed, std::string cut_name)
      : passed_(passed), cut_name_(std::move(cut_name)) {}

  bool passed() const { return passed_; }
  const std::string& cut_name() const { return cut_name_; }

 private:
  bool passed_;
  std::string cut_name_;
};
```

Each `TObject` subclass buys a dictionary to generate and maintain, a
directory-ownership contract to get right (see
[Directory-Based Ownership](#directory-based-ownership)), and a permanent I/O
compatibility surface — do not inherit from `TObject` "just in case" or because a
neighboring class in the codebase does.

### Struct-Like Data for Branches

A `TTree` branch of built-in types, or of a "flat" aggregate of built-in types and
fixed/variable-length arrays, does not need `TObject`, a dictionary, or member
functions at all — a plain struct (or even separate scalar/vector variables bound
directly to branches) is simpler and avoids the dictionary and I/O-versioning
overhead entirely:

```cpp
// No TObject, no ClassDef, no dictionary: this is a branch-buffer struct,
// not a persisted object in its own right.
struct MuonRecord {
  float pt = 0;
  float eta = 0;
  float phi = 0;
  int charge = 0;
};

tree->Branch("muon_pt", &record.pt);
tree->Branch("muon_eta", &record.eta);
```

This is a deliberate, narrower exception to the general struct criteria above:
public data members here are correct because the struct's only job is to be a
typed memory layout the `TTree`/`RDataFrame` machinery reads and writes directly,
not to protect an invariant. Reach for a real `TObject`-derived class with I/O
only when the data needs to be addressed and loaded as a single named object in
the file (nested collections of objects, versioned schema evolution, `TBrowser`
introspection) rather than as a flat set of branches.

#### Branch names and one list of fields

Name each flat branch `<block>_<member>` and give its leaf the same name. In a test of a flat ntuple against the
ROOT readers (2026-10-06) only that form worked in every reader: a branch `list.run` with leaf `run`
failed in `TTreeReader` and in RDataFrame (whose column is then `list.run.run`); a branch and leaf both named
`list.run` failed in jitted RDataFrame strings, because `list.run` is not a C++ identifier; `list_run` worked in
`TTreeFormula`/`TTree::Draw`, `TTreeReader`, typed and jitted RDataFrame. Dotted names are what split
`TObject` branches produce, so moving to plain structs is also the moment to fix the names.

Keep the persisted layout in one place: a member function that visits every data member with its name, used by the
branch registration and by every check, so that adding a member without registering it cannot go unnoticed.

```cpp
#define VISIT(member) visit(#member, member)   // the name is spelled by the preprocessor
struct Track {
  Float_t rigidity = 0;
  Short_t hits[9] = {};
  std::vector<Float_t> cluster_time;
  template <class Visitor> void ForEachField(Visitor&& visit) {
    VISIT(rigidity); VISIT(hits); VISIT(cluster_time);
  }
};
// RegisterBlock(tree, "trk", track): one branch "trk_<member>" per visited member; throw when
// TTree::Branch returns null; static_assert against std::vector<bool> (not a contiguous array).
```

Test that list, not only the code that uses it: the visited names must equal the member declarations in order, the
visited members must lie back to back in memory (`offsetof` plus `sizeof`, allowing alignment padding), and a written
file must hold one branch per member with the member's leaf type and length. Check the test itself on deliberately
broken copies (a member removed in the middle and at the end, one hidden in padding, two swapped); the producer above
had such a check fail on each of the four.

## Class Dictionaries and I/O

Any class ROOT streams, `TObject`-derived or not, needs a ROOT dictionary (generated by `rootcling`/
`ROOT_GENERATE_DICTIONARY`, see [Build setup](cmake-and-build.md)) before ROOT can
stream it. Design for the dictionary generator, not around it:

- Add `ClassDef(ClassName, version)` in the class body (`ClassDefOverride` is the same macro with `override` on the
  virtual functions it declares; use it when the class marks its other overrides). `ClassImp` is no longer needed in
  ROOT 6; drop it. A non-`TObject` class needs no `ClassDef` at all to be
  written, only a dictionary entry; `ClassDef` adds the version number and `IsA()`.
- Every persisted member must itself be streamable: a built-in type, a
  `TObject`-derived type, an STL container of either, or a type with its own
  dictionary entry in the project's `LinkDef.h`. A raw non-owning pointer to a
  non-persisted type will not round-trip correctly.
- Provide a default constructor. ROOT's I/O layer default-constructs an object
  before filling its members from the stream; a class that cannot be
  default-constructed cannot be read back.
- Bump the `ClassDef` version number when the persisted member layout changes. Old files stay readable through
  automatic schema evolution (added, removed or reordered members, changed numeric types); for a rename or a
  computed member write a `#pragma read` rule in `LinkDef.h` (`sourceClass`, `version`, `source`, `target`, `code`)
  rather than a hand-written `Streamer()`, which disables automatic evolution and must be kept in step by hand. Treat this the same as any other on-disk format migration: plan for
  readers of the old version before shipping the new one.
- Do not hand-edit the generated dictionary source (`*Dict.cxx`/`*Dict.h` or
  `G__*.cxx`) — it is build output, not a source file. If it looks wrong, the bug is
  in the `LinkDef.h` entry, the `ClassDef` declaration, or the CMake dictionary
  target, not the generated file itself; see [Debugging ROOT](root-debugging.md#dictionary-issues)
  for the "cannot find a class dictionary" failure mode.

```cpp
// CalibrationSet.h
class CalibrationSet : public TObject {
 public:
  CalibrationSet() = default;  // required for I/O
  ...
 private:
  int run_ = 0;
  std::vector<double> constants_;  // streamable: built-in + std::vector of built-in

  ClassDef(CalibrationSet, 1)  // bump this on layout changes
};
```

```text
# LinkDef.h
#pragma link C++ class CalibrationSet+;
// version 2 renamed constants_ to gains_: map the old member in files written with version 1
#pragma read sourceClass="CalibrationSet" version="[1]" source="std::vector<double> constants_" \
  target="gains_" code="{ gains_ = onfile.constants_; }"
```

## Ownership Guidelines

The general rules (RAII for every resource, `std::unique_ptr` by default, a documented non-owning pointer for
a kept dependency, never a reference member) are in the [C++ guidelines](cpp-balanced-design-guidelines.md#ownership-and-lifetime).
ROOT adds directory ownership:

### Directory-Based Ownership

ROOT's default ownership model is not RAII: a histogram (`TH1` and derived), a `TTree`, a `TEventList` or a
`TGraph2D` created while a `TDirectory`/`TFile` is the current directory (`gDirectory`) registers with it and is
owned by it. Closing the file deletes every object it owns, including ones your code still holds a raw pointer to.

```cpp
TH1D* h = nullptr;
{
  auto file = std::unique_ptr<TFile>(TFile::Open("out.root", "RECREATE"));
  h = new TH1D("h_pt", "p_{T};p_{T} [GeV];Events", 50, 0, 200);  // registered with *file
}  // the TFile destructor closes the file and deletes h
h->Fill(30.0);  // use-after-free
```

Not every object registers. `Get<T>` of a `TGraph`, `TF1`, `TCanvas`, `TVectorD`, a `TList` or a class of your own
returns an object the file does not track: the caller owns it and must delete it (or hold it in a
`std::unique_ptr`). Histograms and trees read with `Get<T>` do register with the file. To stop registration for
the whole program, call `TH1::AddDirectory(kFALSE)` once at start-up (histograms only: a `TTree` always attaches to
the current directory, so detach a tree with `SetDirectory(nullptr)` if it must outlive the file). `RResultPtr<TH1D>` from RDataFrame owns its histogram;
do not delete `&*result` or hand it to a file without `SetDirectory`.

Rules of thumb:

- If a histogram/tree should outlive the file it was created under (e.g., to merge
  or compare it after closing the input file), detach it explicitly:
  `h->SetDirectory(nullptr);` immediately after creation, before any file operation
  can delete it out from under you.
- If a histogram is read from a file and you want to keep using it after the file
  closes, either `SetDirectory(nullptr)` on it or `Clone()` it into a directory you
  control (including `nullptr`, meaning "no directory owns this").
- When you explicitly want the directory to own and eventually free an object, do
  not also delete it yourself and do not wrap it in an owning smart pointer — pick
  exactly one owner.
- `TObject::kCanDelete`/`kMustCleanup` bits and `gDirectory`'s cleanup list are the
  mechanism behind this; you rarely need to touch them directly, but recognize them
  in stack traces or `TObject` documentation as the same directory-ownership system.

```cpp
auto h = std::make_unique<TH1D>("h_pt", "p_{T};p_{T} [GeV];Events", 50, 0, 200);
h->SetDirectory(nullptr);  // detach: h now has no directory owner
h->Fill(30.0);
// h is safe to keep using after any TFile that happened to be open closes,
// and std::unique_ptr will delete it exactly once, as the sole owner.
```

### RAII vs. ROOT Ownership

Prefer RAII (`std::unique_ptr`, scope-bound `TFile`/`TDirectory` guards) for
anything ROOT does not itself claim ownership of — most notably `TFile*` itself,
which is not directory-owned by anything else:

```cpp
auto file = std::unique_ptr<TFile>(TFile::Open(path.c_str(), "READ"));
if (!file || file->IsZombie()) {
  throw std::runtime_error("Could not open file: " + path);
}
```

Do **not** let an owning smart pointer outlive the file that still owns the object. `~TH1` deregisters the
histogram from its directory, so deleting it while the file is open is safe; whether the pair crashes depends on
the order of destruction. The hazard is a smart pointer that outlives its file: the file deletes the histogram on
close, and the smart pointer deletes it again later:

```cpp
// Wrong when h outlives file: file->Close() deletes the histogram, then ~unique_ptr deletes it again.
std::unique_ptr<TH1D> h;
{
  auto file = std::unique_ptr<TFile>(TFile::Open("in.root", "READ"));
  h.reset(file->Get<TH1D>("h_pt"));
}

// Right: either use a raw, non-owning observer pointer and keep the file
// alive for as long as you use it...
auto* h_view = file->Get<TH1D>("h_pt");

// ...or explicitly take ownership by detaching/cloning before the file can
// delete it, then a smart pointer is correct again.
auto* h_raw = file->Get<TH1D>("h_pt");
h_raw->SetDirectory(nullptr);
auto h_owned = std::unique_ptr<TH1D>(h_raw);
```

The general ownership rule above still holds — a smart pointer's presence should
tell the reader who owns the object — but with ROOT, "who owns it" is a
`TDirectory`/`TFile` by default, and the smart pointer must not contradict that
until you have explicitly transferred ownership away from it.

## Inheritance in ROOT

- `TObject` already provides virtual `Clone()`, `IsA()`, and RTTI-equivalent type
  queries through `TClass`; do not reinvent a parallel type-tag or `Clone()`
  mechanism in a subclass hierarchy that already inherits from `TObject`.
- Every `TObject`-derived class needs a virtual destructor (inherited from
  `TObject`, so this is automatic) — but confirm any additional owned resources in
  a subclass are still released correctly through that virtual destructor when
  deleted through a `TObject*`.
- Keep `TObject`-derived hierarchies shallow. Deep inheritance chains compound the
  dictionary/`ClassDef` version-bump burden at every level and make schema
  evolution (see [Class Dictionaries and I/O](#class-dictionaries-and-io)) harder
  to reason about across versions. Prefer composition — a `TObject`-derived class
  holding non-`TObject` helper members — over adding another inheritance level,
  the same general preference as above, just with a higher cost per level here.
- If a class needs runtime polymorphism but never needs ROOT I/O or `TBrowser`
  introspection for the base/derived relationship itself, prefer an ordinary
  (non-`TObject`) abstract base class rather than routing purely-analysis-internal
  polymorphism through `TObject`.

## ROOT Global State and Testability

ROOT exposes significant global state — `gROOT`, `gDirectory`, `gFile`, `gStyle`,
`gRandom`, `gErrorIgnoreLevel` — that interactive ROOT sessions and macros rely on
implicitly. This makes naive unit testing of ROOT-touching code fragile: tests can
pass or fail depending on what some other test left in `gDirectory` or `gStyle`.

- Prefer passing a `TDirectory*`/`TFile*`/`TRandom*` explicitly into functions and
  constructors over reading the corresponding `g*` global inside them — the same
  explicit-dependency rule as in the [C++ guidelines](cpp-balanced-design-guidelines.md#design-rules),
  applied to ROOT's specific globals.
- Where a function must touch global state (`gROOT->SetBatch(kTRUE)` for batch-mode
  plotting, see [Plotting](#plotting)), isolate that touch at the entry point of a
  script/executable, not scattered through library code that a test might also
  call.
- Reset any global state a test changes (`gDirectory`, `gRandom`'s seed, batch
  mode) at the end of that test, so test order does not affect results.

## Error Handling

Use one error-handling strategy per component, consistent with the repository. Exceptions are allowed (see the
conventions at the top): throw for a failure the caller cannot handle locally (a missing input file, a broken
tree), and use a function returning `std::optional` or a status when failure is an expected outcome.

ROOT's own APIs generally do not throw C++ exceptions; failures are reported
through null returns (`TFile::Open` returning `nullptr` or a zombie object),
`Error()`/`Warning()`/`Fatal()` calls that print through ROOT's message system
(governed by `gErrorIgnoreLevel`), or sentinel return codes.

- Treat every ROOT API call that can fail as an external boundary: check its return
  value/zombie state immediately and translate the failure into your own code's
  chosen error-handling style (exceptions, factory-function-with-`std::optional`,
  or whatever the surrounding repository already uses) rather than letting a null
  `TFile*`/`TTree*` propagate silently. See
  [Input and object safety](#input-and-object-safety) below for the
  pattern used with files/trees/branches.
- Do not rely on `gErrorIgnoreLevel` suppression as an error-handling strategy —
  it silences ROOT's own diagnostic output, it does not make the underlying
  failure recoverable. Raise or return an explicit error from your own code at the
  point you detect the failure instead.
- Your own new `TObject`-derived and plain classes should still follow whatever
  error-handling convention the rest of the codebase uses for non-ROOT code — do
  not adopt ROOT's C-style reporting for code you control just because it is
  adjacent to ROOT calls.

## Const-Correctness in ROOT

Some older ROOT APIs (particularly pre-ROOT6 holdovers still present for backward
compatibility) are not fully const-correct — a getter that conceptually should be
`const` may not be marked so, because it lazily initializes internal caches. This
is a property of ROOT's own API surface, not license to relax const-correctness in
your own code:

- Keep your own classes and functions const-correct per the general guidance
  above, even when they wrap a ROOT type whose own API is not.
- Where a non-const ROOT call must be made from a logically-const member function
  of your own wrapper (a known lazy-init getter, not a mutation), isolate the
  workaround (e.g., a `mutable` cache member, or a documented `const_cast` at a
  single well-commented call site) rather than dropping `const` from your own
  interface to route around it.

## Templates and Dictionary Limits

ROOT dictionaries require concrete, explicitly named types — you cannot generate a
dictionary for an unbounded template. Two consequences for design:

- If a template class needs ROOT I/O, every instantiation that will be persisted
  must be explicitly named in `LinkDef.h` (e.g.
  `#pragma link C++ class MyContainer<double>+;`), not left implicit. Prefer a
  small, fixed set of instantiations (`<double>`, `<int>`) over an open-ended
  template parameter if persistence is required.
- If a template's use case is purely algorithmic/in-memory (never written to a
  file), it does not need a dictionary at all — write it as an ordinary C++
  template per the guidance above and keep it out of `LinkDef.h`.
- For expressions that vary per-analysis inside an `RDataFrame` pipeline (a
  `Define`/`Filter` string), prefer RDataFrame's JIT string-expression interface
  over hand-rolled C++ templates — it sidesteps the dictionary question entirely
  by compiling the expression at run time, at the cost of losing compile-time type
  checking on that one expression. Use a compiled template or free function
  instead when the logic is complex enough that JIT-string debugging becomes the
  bottleneck (see [RDataFrame patterns](#rdataframe-patterns)).

## Naming, Comments, and File Documentation

Match the repository's existing conventions first wherever this analysis code
lives. Use the following as a default when no repository convention exists.

### Naming Guidance

Nouns for types, verbs for functions; no vague names (`Process()`, `Manager`, `DoStuff()`). Short names only in
small scopes.

For this codebase specifically, C++/ROOT macros follow Google C++ style:
`snake_case` variables/params, `PascalCase` types/functions, `kPascalCase` static
constants, `trailing_underscore_` members, `ALL_CAPS` only for macros. Use
meaningful, descriptive physics names for histograms, canvases, and functions:
`event_weight`, `signal_yield`, `mass_window`, `fit_range`, `mass_hist`,
`fit_result`. Standard HEP abbreviations (`pt`, `eta`, `phi`, `met`, `pu`, `sf`,
`mc`) are fine. Python follows PEP 8 and Bash the Google Shell Style Guide; see the
[Python](python-balanced-design-guidelines.md) and [Bash](bash-balanced-design-guidelines.md) guidelines.

### Comments and Documentation

This is the one place for the comment rule in every language (C++, Python, Bash, CMake). Write comments to explain
why, not what. Avoid comments that repeat the code
(`// Increment i by 1.` above `++i;`). Prefer comments that explain intent,
constraints, or non-obvious decisions. Public APIs should document what the
function or type represents, ownership expectations, error behavior, and
important preconditions/postconditions. Avoid excessive comments around obvious
code.

For this analysis code specifically, reserve comments for non-obvious logic:
physics/statistical assumptions, weight/normalization choices, fit models and
ranges, ROOT object ownership/lifetime, and edge cases. Do not comment
`// open file` or `// loop over events` — the code already says that.

### File-level documentation requirement

When creating or modifying any code file (C++ source/headers, ROOT macros, PyROOT/
uproot scripts, CMake files, config loaders), include a short introductory comment
block at the top of the file (`//` or `/* */` for C++/ROOT macros, `#` for
Python/CMake, a module docstring `"""..."""` for Python scripts) covering:

- **Purpose** — why the file exists, e.g. "dimuon selection + mass histogram" or
  "JES systematics check".
- **What the code does** — the main behavior: selections, histograms produced, fit
  model, or inspection performed.
- **Usage notes, dependencies, or assumptions** — build/run command, expected input
  format and tree/branch names, units, weight conventions, ROOT version, and any
  preconditions.

For existing files, add the explanation if it is missing, or update it if it is
incomplete or outdated. Keep it proportional to the file and do not let it drift
from the code — this complements the inline-comment guidance above, it does not
replace it.

## Build Layout

### ROOT dictionary and build layout

Keep a `TObject`-derived class's declaration (`.h`, with `ClassDef`) and
definition (`.cxx`) split the same way as any other C++ class in
the codebase; add its `LinkDef.h` entry alongside it, not in a separate far-away
file, so the three stay in sync when the class changes. Treat generated
dictionary files as build artifacts: do not commit them unless the project's
existing convention already does (some projects commit generated dictionaries for
reproducible builds — match whatever this repository already does), and never
hand-edit them; see [Build setup](cmake-and-build.md) for the CMake
`ROOT_GENERATE_DICTIONARY` step that produces them.

### Build

Single-file program:

```bash
c++ -O2 -Wall -Wextra analysis.cpp $(root-config --cflags --libs) -o analysis  # -std comes from root-config
```

Compiled macro:

```bash
root -l -q 'analysis.C+("input.root")'
```

For CMake-based projects, see [Build setup](cmake-and-build.md).

## Concrete ROOT/RDataFrame Coding Patterns

### Choosing an event-loop API

- `ROOT::RDataFrame`: default for new columnar event processing. Declarative
  filters and defines, multithreading, snapshots, and cutflow reports.
- `TTreeReader`: use when manual event-loop control is required, branch structures
  are awkward for RDataFrame, the code integrates into existing manual-loop code,
  or step-by-step debugging of event iteration is needed.
- `SetBranchAddress`: legacy maintenance only. Validate addresses and object
  lifetimes carefully; a dangling or reused address is a common source of
  silently wrong values.

```cpp
TTreeReader reader(tree);
TTreeReaderValue<float> pt(reader, "pt");

while (reader.Next()) {
    if (*pt > 25.0f) {
        // fill objects
    }
}
```

### RDataFrame patterns

Basic filter and histogram:

```cpp
ROOT::RDataFrame df("Events", "input.root");

auto selected = df.Filter("pt > 25.0", "pt selection");
auto h = selected.Histo1D(
    {"h_pt", "p_{T};p_{T} [GeV];Events", 50, 0.0, 200.0},
    "pt"
);
```

Multiple input files:

```cpp
std::vector<std::string> files = {"a.root", "b.root"};
ROOT::RDataFrame df("Events", files);
```

Named cutflow, booked before materialization:

```cpp
auto df1 = df.Filter("nMuon >= 2", "at least two muons");
auto df2 = df1.Filter("Muon_pt[0] > 25.0", "leading muon pt");
auto report = df2.Report();  // book everything before .GetValue()/.Print()
report->Print();
```

Weighted histogram:

```cpp
auto dfw = df.Define("weight", "genWeight * pileupWeight");
auto h = dfw.Histo1D(
    {"h_mass", "Mass;m [GeV];Weighted events", 60, 60.0, 120.0},
    "mass",
    "weight"
);
```

Reusable helper functions operate on `ROOT::RDF::RNode`:

```cpp
ROOT::RDF::RNode add_columns(ROOT::RDF::RNode df) {
    return df.Define("abs_eta", "std::abs(eta)");
}
```

Lazy execution: book every action, then trigger by accessing results once, in one
place, to avoid duplicating the event scan:

```cpp
auto n = df.Count();
auto h = df.Histo1D({"h", "x;x;Events", 50, 0, 1}, "x");

std::cout << "Events: " << *n << "\n";
h->Write();
```

### RNTuple and current RDataFrame features

Checked by running them with ROOT 6.38.04 (PyROOT) and uproot 5.7.6 on 2026-10-13; release facts from the
[6.34](https://root.cern/doc/v634/release-notes.html) and [6.36](https://root.cern/doc/v636/release-notes.html)
release notes (accessed 2026-10-13).

- **RNTuple or TTree.** RNTuple is ROOT's columnar successor to `TTree`: its on-disk format 1.0 is final since ROOT
  6.34 (later releases read it; experimental files from earlier releases are not readable), and its main types moved
  from `ROOT::Experimental` to `ROOT` in 6.36 (`ROOT::RNTupleReader`, `ROOT::RNTupleModel`). Choose RNTuple for new
  outputs whose readers are all on ROOT 6.34+ or uproot 5 (uproot 5.7.6 read a ROOT 6.38 RNTuple with a jagged
  column); keep `TTree` when a reader is older, when an experiment framework writes or requires it, or when the
  data need `TObject`-based classes. RDataFrame reads both with the same code: `ROOT::RDataFrame("Events", file)`
  detects the format. To write one, set `RSnapshotOptions::fOutputFormat = ROOT::RDF::ESnapshotOutputFormat::kRNTuple`.
  The branch-naming advice in [Branch names](#branch-names-and-one-list-of-fields) is about `TTree` leaves;
  RNTuple fields are named by the model and have no leaf level.
- **`Vary`** books systematic variations of a column in the same event loop:
  `df.Vary("pt", "ROOT::RVecD{pt*0.98, pt*1.02}", {"down", "up"})`, then
  `ROOT::RDF::Experimental::VariationsFor(result)` gives `nominal`, `pt:down`, `pt:up`. Prefer it to one event loop
  per variation; every result downstream of the varied column is varied.
- **`DefinePerSample`** computes a value once per input sample (a cross section, a luminosity weight from
  `rdfsampleinfo_`), not once per event; **`ROOT::RDF::Experimental::FromSpec(spec.json)`** builds the dataframe from
  a JSON list of samples with metadata (`rdfsampleinfo_.GetD("xsec")`). Use the spec for multi-sample analyses
  instead of hand-written file loops.
- **`DefineSlot`** passes the slot (thread) number as the first argument of a compiled callable; with implicit
  multithreading use it for per-thread state such as one random generator per slot, seeded from a base seed and the
  slot. A jitted string sees the same number as `rdfslot_`. `GetNSlots()` gives the number of slots to allocate.
- **Distributed RDataFrame** runs the same graph on Dask or Spark: since 6.36 pass the cluster client with the
  `executor` keyword (`ROOT.RDataFrame("Events", files, executor=client)`); the old
  `ROOT.RDF.Experimental.Distributed` path warns in 6.36 and is removed in 6.38. Seeds, `Range` and actions that
  need the whole dataset in one process (`Take` of large columns, `Foreach` with side effects) need rethinking there.
- **NumPy bridges.** `df.AsNumpy(["x"])` returns NumPy arrays of the selected columns (materializes them: select
  columns and filter first); `ROOT.RDF.FromNumpy({"w": array})` makes a dataframe from NumPy arrays.

### Input and object safety

Validate every file, tree, and branch before building a large workflow, and fail
with a message naming the file/object that failed rather than producing silent
empty output:

```cpp
auto file = std::unique_ptr<TFile>(TFile::Open(path.c_str(), "READ"));
if (!file || file->IsZombie()) {
    throw std::runtime_error("Could not open file: " + path);
}
auto* tree = file->Get<TTree>(treeName.c_str());
if (!tree) {
    throw std::runtime_error("Missing tree: " + treeName);
}
if (!tree->GetBranch("pt")) {
    throw std::runtime_error("Missing branch pt");
}
```

### Histogram construction

```cpp
TH1D h("h_muon_pt", "Muon p_{T};p_{T} [GeV];Events", 50, 0.0, 200.0);
h.Sumw2();  // before filling manually with weights
```

Use explicit axis titles and units; check entries and integrals before scaling,
dividing, or fitting; state the underflow/overflow policy when reporting
integrals. See [Histograms and uncertainties](../../hep-analysis/references/histograms-efficiencies.md) for
the statistical treatment of sumw/sumw2 and covariance.

### Plotting

```cpp
gROOT->SetBatch(kTRUE);  // required for non-interactive/batch plotting jobs

TCanvas c("c", "c", 800, 600);
h.Draw("HIST");
c.SaveAs("plot.pdf");
```

Include luminosity, sqrt(s), and region/channel labels; use ratio panels for
data/MC; mask blinded data in both the main panel and any ratio (real inputs arrive already blinded; see
[Analysis design](../../hep-analysis/references/analysis-design.md) for blinding rules and
[Histograms and uncertainties](../../hep-analysis/references/histograms-efficiencies.md) for ratio/pull
statistics).

## Design Checklist

General class, function and inheritance questions are in the [C++ guidelines](cpp-balanced-design-guidelines.md#design-rules).
Before adding a ROOT type, ask whether it actually needs `TObject` or a dictionary (I/O through `TObject` APIs, a
ROOT container, `TBrowser`), or is purely analysis-internal.

If a type does need a ROOT dictionary: is there a default constructor, are all
persisted members themselves streamable, and does `LinkDef.h` name every
instantiation (including template instantiations) that will actually be
persisted?

Before writing or reviewing any ROOT-touching code, also check:

- Is directory ownership explicit — `SetDirectory(nullptr)`/`Clone()` used
  wherever an object must outlive the file/directory it was created or read
  under, and never double-owned by both a directory and a smart pointer?
- Does every ROOT API call that can fail (`TFile::Open`, `Get<T>`, a fit call) get
  its return value/zombie state checked before use?
- Does any global-state (`gDirectory`, `gRandom`, `gStyle`) dependency get passed
  in explicitly rather than read implicitly, at least in code that needs to be
  testable?
- Cuts, weights, binning, labels, and object definitions are preserved; data and
  simulation branches are handled separately where needed.
- Batch mode is enabled for non-interactive plotting jobs.
- A cutflow or equivalent event-count validation exists.
- All RDataFrame actions are booked before `.GetValue()`/`.Report()`/writing
  output.
- With `ROOT::EnableImplicitMT()`: no `gRandom` (or any shared generator) inside `Define`, it is not thread-safe;
  use `DefineSlot` with one generator per slot seeded from the slot number and a base seed. `Range` is not
  supported with implicit multithreading. Entry order and floating-point sums differ from run to run, so compare
  multithreaded outputs within a tolerance, not bit for bit (or run single-threaded for a byte comparison).
- `Snapshot` runs the event loop at once unless `RSnapshotOptions::fLazy` is set; book it last, or lazily, so it does
  not trigger a second pass over the data.
- Inputs/trees/branch names are validated and documented; units are explicit;
  selections are named and traceable; weights are applied exactly once.
- Histograms have names and axis labels; empty histograms are handled safely;
  fit status/covariance is checked; output files are closed cleanly.
- Build/run commands are documented; tests/validation are run, or their absence
  is stated with a reason.

## Anti-Patterns to Avoid (recap)

- Inheriting from `TObject` "just in case," for a type that never crosses an I/O
  or reflection boundary.
- An owning smart pointer to a directory-owned object (an un-detached histogram or tree) that outlives the file:
  the file deletes it on close and the smart pointer deletes it again.
- Leaking what `Get<T>` returns for types that do not register (`TGraph`, `TF1`, `TCanvas`, `TVectorD`): the
  caller owns those.
- Forgetting `SetDirectory(nullptr)` on a histogram/tree that must outlive the
  file it was created or read under, then hitting a use-after-free once that file
  closes.
- Hand-editing generated dictionary source instead of fixing the `LinkDef.h`/
  `ClassDef` declaration or CMake target that produced it.
- An open-ended template that needs ROOT I/O with no fixed, explicitly-linked set
  of instantiations.
- Silencing a ROOT failure via `gErrorIgnoreLevel` instead of checking the actual
  return value/zombie state and handling the failure explicitly.
- Reading or writing `gDirectory`/`gRandom`/other ROOT globals from deep inside
  library code that a test might also exercise, instead of passing them in
  explicitly.
