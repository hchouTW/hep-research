# C++, ROOT, and Balanced Design Guidelines

The single reference for writing and reviewing C++/ROOT/RDataFrame analysis code:
concrete event-loop and histogram code patterns, naming/comments/file-documentation
conventions, general C++ class/struct/RAII/ownership/inheritance design, and
ROOT-specific object-model design (TObject inheritance, dictionaries, directory-based
ownership). Not the statistical treatment of pipelines — see
[Data pipelines](../../hep-analysis/references/data-pipelines.md) for I/O, ownership, and performance concerns
at the design level — and not Python/PyROOT/uproot coding, see
[Python coding](python-hep-coding-patterns.md) for that.

When modifying or writing C++/ROOT code, prefer a balanced style between
object-oriented and procedural programming, and prefer standard C++ idioms (RAII,
`std::unique_ptr`, exceptions or explicit return values) except where ROOT's own
object model forces a deliberate, contained departure from them. Follow established
repository conventions when they intentionally differ from this reference.

The design-principle examples follow the
[Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html):
two-space indentation, `PascalCase` function names, `snake_case` variables, trailing
underscores for data members, and documented namespace endings. The HEP-code
examples instead follow this package's own naming convention — `snake_case`
variables/params, `PascalCase` types/functions, `kPascalCase` static constants,
`trailing_underscore_` members — which is documented in full under
[Naming, Comments, and File Documentation](#naming-comments-and-file-documentation)
below.

## Read only what the task needs

This file is long (~1,300 lines); do not read it end to end. Jump to the section for the task:

| Task | Section |
|---|---|
| Writing or fixing an RDataFrame/TTreeReader event loop, histograms, plots | [Concrete ROOT/RDataFrame Coding Patterns](#concrete-rootrdataframe-coding-patterns) |
| Header comment block, naming | [Naming, Comments, and File Documentation](#naming-comments-and-file-documentation) |
| Segfaults/leaks around TFile, histograms, `SetDirectory` | [RAII, Resource Management, and Ownership](#raii-resource-management-and-ownership) |
| Custom classes in a TTree, `ClassDef`, LinkDef, "no dictionary" errors | [Class Dictionaries and I/O](#class-dictionaries-and-io) (and [root-debugging.md](root-debugging.md)) |
| Class vs struct vs free function, TObject inheritance, polymorphism | [Choosing Classes, Structs, and Free Functions](#choosing-classes-structs-and-free-functions), [Inheritance and Polymorphism](#inheritance-and-polymorphism) |
| Reviewing a C++ design or diff | [Design Checklist](#design-checklist), [Anti-Patterns to Avoid](#anti-patterns-to-avoid-recap) |

## Contents

- [Core Principle](#core-principle)
- [Choosing Classes, Structs, and Free Functions](#choosing-classes-structs-and-free-functions)
- [Class Dictionaries and I/O](#class-dictionaries-and-io)
- [RAII, Resource Management, and Ownership](#raii-resource-management-and-ownership)
- [Inheritance and Polymorphism](#inheritance-and-polymorphism)
- [Member Functions vs Free Functions](#member-functions-vs-free-functions)
- [Encapsulation Guidelines](#encapsulation-guidelines)
- [State Management and Global State](#state-management-and-global-state)
- [Error Handling](#error-handling)
- [Const-Correctness](#const-correctness)
- [Templates and Generic Code](#templates-and-generic-code)
- [Naming, Comments, and File Documentation](#naming-comments-and-file-documentation)
- [File and Build Organization](#file-and-build-organization)
- [Testing Guidance](#testing-guidance)
- [Standard Library Preference](#standard-library-preference)
- [Concrete ROOT/RDataFrame Coding Patterns](#concrete-rootrdataframe-coding-patterns)
- [Design Checklist](#design-checklist)
- [Anti-Patterns to Avoid (recap)](#anti-patterns-to-avoid-recap)
- [Summary Rule](#summary-rule)

## Core Principle

Use classes to protect state, lifetime, ownership, resources, and invariants. Use
free functions to express algorithms, transformations, calculations, and procedural
workflows. Do not force everything into classes, and do not write purely
global-state procedural code either.

On top of that general C++ principle, only take on ROOT's object model —
`TObject` inheritance, a dictionary, directory ownership — for a type that actually
needs one of ROOT's services: persistence in a `TFile`, `TTree` branch storage,
ROOT's runtime type system (`TClass`, `IsA()`), or interactive introspection
(`TBrowser`, `.ls`, CINT/Cling command line). Everything else — helper types,
algorithm parameters, intermediate results, config structs, anything that never
crosses a ROOT I/O or reflection boundary — should stay a plain C++ type and follow
the general guidance in this reference without the ROOT-specific additions.

The preferred style is simple, idiomatic, testable C++, with ROOT's own
conventions contained to the code that actually touches ROOT's I/O and object
model.

---

## Choosing Classes, Structs, and Free Functions

### When to Use a Class

Use a `class` when the code needs one or more of the following:

- Encapsulated state
- A clear lifetime
- Ownership of a resource
- Invariants that must be protected
- RAII behavior
- Runtime polymorphism through a stable interface

Good examples:

```cpp
class File;
class Socket;
class BankAccount;
class Parser;
class Renderer;
class Order;
```

A class should represent a real concept in the domain or architecture, not merely
act as a folder for related functions. Prefer a `class` when there is something
meaningful to hide, validate, protect, or manage.

```cpp
class BankAccount {
 public:
  static std::optional<BankAccount> Create(int initial_balance) {
    if (initial_balance < 0) {
      return std::nullopt;
    }
    return BankAccount(initial_balance);
  }

  bool Deposit(int amount) {
    if (amount <= 0) {
      return false;
    }

    balance_ += amount;
    return true;
  }

  bool Withdraw(int amount) {
    if (amount <= 0 || amount > balance_) {
      return false;
    }

    balance_ -= amount;
    return true;
  }

  int balance() const { return balance_; }

 private:
  explicit BankAccount(int initial_balance) : balance_(initial_balance) {}

  int balance_;
};
```

In this example, the class is justified because it protects the invariant that
the balance must not become negative.

### When (Not) to Inherit from TObject

Inherit from `TObject` when the type needs to be:

- Written to a `TFile` or read back by name (`file->Get<MyType>("name")`).
- Stored as a `TTree` branch's object (as opposed to a branch of fundamental types
  or a "flat" struct — see [Struct-Like Data for Branches](#struct-like-data-for-branches)).
- Owned by a `TDirectory`/`TFile` so ROOT manages its lifetime and `.ls`/`TBrowser`
  can see it.
- Used somewhere that specifically requires `TObject*` (a ROOT container like
  `TObjArray`/`TList`, an API that takes `TObject*`).

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

### When to Use a Struct

Use a `struct` for simple passive data where public fields are clear, safe, and
intentional.

Prefer this:

```cpp
struct Point {
  double x;
  double y;
};
```

Avoid unnecessary getters and setters when there is no invariant to protect. Avoid
this unless validation or encapsulation is actually needed:

```cpp
class Point {
 public:
  double x() const { return x_; }
  void set_x(double x) { x_ = x; }
  double y() const { return y_; }
  void set_y(double y) { y_ = y; }

 private:
  double x_;
  double y_;
};
```

A `struct` is not inferior to a `class`. In C++, it is often the clearest choice
for simple data types. Use `struct` when:

- The type is mainly a data carrier
- The fields are safe to expose
- There are no important invariants
- The type has no complex ownership responsibility
- The type benefits from aggregate initialization

If later the data needs validation or lifecycle management, it can be refactored
into a class.

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

### When to Use Free Functions

Use free functions for algorithms, calculations, conversions, and operations that
do not need private access to an object.

Prefer this:

```cpp
struct Point {
  double x;
  double y;
};

double Distance(Point a, Point b) {
  const auto dx = a.x - b.x;
  const auto dy = a.y - b.y;
  return std::sqrt(dx * dx + dy * dy);
}
```

Do not put a function inside a class only because it is related to a type. A
function should usually remain a free function when:

- It does not need private access
- It does not modify object invariants
- It represents an algorithm rather than object behavior
- It can be tested independently
- It can operate on multiple compatible types

### Avoid Artificial Utility Classes

Do not create classes that only wrap stateless helper functions.

Avoid this:

```cpp
class MathHelper {
 public:
  static int Add(int a, int b) { return a + b; }
};
```

Prefer this:

```cpp
int Add(int a, int b) { return a + b; }
```

If grouping is needed, use a namespace:

```cpp
namespace math {

int Add(int a, int b) { return a + b; }

}  // namespace math
```

Avoid names like `Utils`, `Helper`, `Manager`, `Processor`, `Handler` unless there
is a strong reason — they often indicate unclear responsibility. Prefer precise
names that describe what the code owns, does, or represents:
`HttpClient`, `FileReader`, `OrderBook`, `ImageDecoder`, `CommandParser`.

---

## Class Dictionaries and I/O

A `TObject` subclass needs a ROOT dictionary (generated by `rootcling`/
`ROOT_GENERATE_DICTIONARY`, see [Build setup](cmake-and-build.md)) before ROOT can
stream it. Design for the dictionary generator, not around it:

- Add `ClassDef(ClassName, version)` in the class body and `ClassImp(ClassName)` in
  the `.cxx` (or rely on `ClassDefOverride`/dictionary-only builds in newer ROOT —
  match whatever the surrounding codebase already does).
- Every persisted member must itself be streamable: a built-in type, a
  `TObject`-derived type, an STL container of either, or a type with its own
  dictionary entry in the project's `LinkDef.h`. A raw non-owning pointer to a
  non-persisted type will not round-trip correctly.
- Provide a default constructor. ROOT's I/O layer default-constructs an object
  before filling its members from the stream; a class that cannot be
  default-constructed cannot be read back.
- Bump the `ClassDef` version number when the persisted member layout changes, and
  add a custom `Streamer()` (or a schema-evolution rule) if old files must remain
  readable. Treat this the same as any other on-disk format migration: plan for
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
```

---

## RAII, Resource Management, and Ownership

### RAII and Resource Management

Use RAII for resources such as memory, files, sockets, locks, handles,
transactions, temporary state that must be restored, and any resource that must
be released reliably. Resource acquisition and release should be tied to object
lifetime. Prefer standard library RAII types where possible:
`std::unique_ptr<T>`, `std::shared_ptr<T>`, `std::lock_guard<std::mutex>`,
`std::unique_lock<std::mutex>`, `std::fstream`, `std::vector<T>`, `std::string`.

Avoid manual `new` and `delete` in normal application code. Prefer this:

```cpp
auto widget = std::make_unique<Widget>();
```

Avoid this:

```cpp
Widget* widget = new Widget();
// ...
delete widget;
```

Use custom RAII classes when the standard library does not already provide an
appropriate abstraction. RAII classes should clearly express ownership (move-only,
with the acquire/release symmetric in the constructor/destructor).

### Ownership Guidelines

Make ownership explicit. Use values when ownership is simple
(`std::vector<Item> items;`). Use `std::unique_ptr` for exclusive dynamic
ownership. Use `std::shared_ptr` only when ownership is genuinely shared. Use raw
pointers for non-owning nullable references when the repository has no clearer
observer type, and references for non-owning required dependencies. Do not infer
ownership from a raw pointer — document non-obvious lifetime constraints and
prefer values, references, or standard smart pointers when they express the
contract more clearly:

```cpp
// Clear: a required, non-owning dependency expressed as a reference.
class Renderer {
 public:
  explicit Renderer(const TextureCache& texture_cache)
      : texture_cache_(texture_cache) {}

 private:
  const TextureCache& texture_cache_;
};
```

```cpp
// Unclear: does Renderer own texture_cache or just observe it?
class Renderer {
 public:
  explicit Renderer(TextureCache* texture_cache)
      : texture_cache_(texture_cache) {}

 private:
  TextureCache* texture_cache_;
};
```

### Directory-Based Ownership

ROOT's default ownership model is not RAII: a histogram, tree, or other
`TObject`-derived object created while a `TDirectory`/`TFile` is open is, by
default, registered with and owned by that directory. Closing the file (or letting
it go out of scope) deletes every object it owns — including ones your code still
holds a raw pointer to.

```cpp
{
  auto file = std::unique_ptr<TFile>(TFile::Open("out.root", "RECREATE"));
  auto* h = new TH1D("h_pt", "p_{T};p_{T} [GeV];Events", 50, 0, 200);
  // h is now owned by file's TDirectory, NOT by the `new` caller.
}  // file destructor closes the file and deletes h.

h->Fill(30.0);  // use-after-free: h was deleted when file closed.
```

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

Do **not** wrap a directory-owned object (a histogram/tree fetched via
`file->Get<T>(name)` without detaching it, or one you created while the file was
open and did not detach) in an owning smart pointer — the file will delete it too,
and you get a double-free:

```cpp
// Wrong: h is directory-owned; wrapping it in unique_ptr double-deletes it
// when the file closes.
auto file = std::unique_ptr<TFile>(TFile::Open("in.root", "READ"));
auto h = std::unique_ptr<TH1D>(file->Get<TH1D>("h_pt"));

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

---

## Inheritance and Polymorphism

Do not introduce inheritance just to organize code. Use runtime polymorphism only
when the code truly needs interchangeable behavior behind a common interface.

Acceptable example:

```cpp
class Shape {
 public:
  virtual ~Shape() = default;

  virtual double Area() const = 0;
};

class Circle final : public Shape {
 public:
  explicit Circle(double radius) : radius_(radius) {}

  double Area() const override { return std::numbers::pi * radius_ * radius_; }

 private:
  double radius_;
};
```

Use this style when callers need to work with different concrete implementations
through the same interface: `std::vector<std::unique_ptr<Shape>> shapes;`.

Avoid deep inheritance hierarchies unless there is a clear architectural reason.
Before adding inheritance, consider these alternatives: free functions,
templates, `std::variant`, composition, strategy objects, function objects,
lambdas, plain data plus algorithms. Prefer composition over inheritance when
behavior can be assembled from smaller parts.

Avoid this style unless there is a strong reason:

```cpp
class Animal {
 public:
  virtual ~Animal() = default;
  virtual void Speak() = 0;
};

class Dog : public Animal {};
class Cat : public Animal {};
class Bird : public Animal {};
```

A small number of cases may be better represented with `std::variant`:

```cpp
struct Circle {
  double radius;
};

struct Rectangle {
  double width;
  double height;
};

using Shape = std::variant<Circle, Rectangle>;
```

### Inheritance and Polymorphism in ROOT

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

---

## Member Functions vs Free Functions

Prefer member functions for operations that are part of the object's essential
behavior. Good member functions usually preserve invariants, mutate internal
state intentionally, depend on private representation, or represent core
behavior of the abstraction.

Prefer free functions for operations that are external algorithms. Good free
functions usually do not need private access, are broadly reusable, are easy to
test independently, keep the type smaller, and express a clear computation or
transformation.

```cpp
class Polygon {
 public:
  static std::optional<Polygon> Create(std::vector<Point> points) {
    if (points.size() < 3) {
      return std::nullopt;
    }
    return Polygon(std::move(points));
  }

  const std::vector<Point>& points() const { return points_; }

 private:
  explicit Polygon(std::vector<Point> points) : points_(std::move(points)) {}

  std::vector<Point> points_;
};

double Perimeter(const Polygon& polygon) {
  const auto& points = polygon.points();

  double result = 0.0;
  for (size_t i = 0; i < points.size(); ++i) {
    const auto& current = points[i];
    const auto& next = points[(i + 1) % points.size()];
    result += Distance(current, next);
  }

  return result;
}
```

In this example, `Polygon` protects the invariant that it has at least three
points. `Perimeter` is a free function because it is an algorithm over the public
interface.

---

## Encapsulation Guidelines

Encapsulation should protect meaningful invariants, not create unnecessary
boilerplate. Use private data when the data must stay valid according to rules,
changes must go through validation, representation may change later, ownership
must be controlled, or thread-safety/synchronization is involved. Public data is
acceptable when the type is simple passive data, there are no invariants, the
fields are naturally part of the type's meaning, or the type is used as a value
object/data transfer object.

Avoid writing trivial getters and setters just to imitate other languages. Prefer
direct public fields for simple data:

```cpp
struct Color {
  int red;
  int green;
  int blue;
};
```

Prefer validation when the values must be constrained:

```cpp
class Color {
 public:
  static std::optional<Color> Create(int red, int green, int blue) {
    if (!IsChannelValid(red) || !IsChannelValid(green) ||
        !IsChannelValid(blue)) {
      return std::nullopt;
    }
    return Color(red, green, blue);
  }

  int red() const { return red_; }
  int green() const { return green_; }
  int blue() const { return blue_; }

 private:
  Color(int red, int green, int blue) : red_(red), green_(green), blue_(blue) {}

  static bool IsChannelValid(int value) { return value >= 0 && value <= 255; }

  int red_;
  int green_;
  int blue_;
};
```

---

## State Management and Global State

### State Management

Minimize mutable shared state. Prefer local variables, function parameters,
return values, immutable values, clear ownership, and explicit dependencies.
Avoid hidden global variables, singleton abuse, mutable global state, static
state that makes testing difficult, and functions that secretly depend on
external state.

Avoid this:

```cpp
std::string g_current_user;

bool CanAccessDocument(const Document& document) {
  return document.owner() == g_current_user;
}
```

Prefer this:

```cpp
bool CanAccessDocument(const Document& document, const User& user) {
  return document.owner() == user.id();
}
```

Pass dependencies explicitly unless there is a strong reason not to.

### Global State and Testability

ROOT exposes significant global state — `gROOT`, `gDirectory`, `gFile`, `gStyle`,
`gRandom`, `gErrorIgnoreLevel` — that interactive ROOT sessions and macros rely on
implicitly. This makes naive unit testing of ROOT-touching code fragile: tests can
pass or fail depending on what some other test left in `gDirectory` or `gStyle`.

- Prefer passing a `TDirectory*`/`TFile*`/`TRandom*` explicitly into functions and
  constructors over reading the corresponding `g*` global inside them — the same
  dependency-injection reasoning as [Testing Guidance](#testing-guidance) below,
  applied to ROOT's specific globals.
- Where a function must touch global state (`gROOT->SetBatch(kTRUE)` for batch-mode
  plotting, see [Plotting](#plotting)), isolate that touch at the entry point of a
  script/executable, not scattered through library code that a test might also
  call.
- Reset any global state a test changes (`gDirectory`, `gRandom`'s seed, batch
  mode) at the end of that test, so test order does not affect results.

---

## Error Handling

Use a clear error-handling strategy that is consistent with the surrounding
component and repository conventions. Google-style code does not use C++
exceptions; use a factory function when construction can fail and return a value
that makes failure explicit:

```cpp
class Config {
 public:
  static std::optional<Config> Load(std::filesystem::path path) {
    if (!std::filesystem::exists(path)) {
      return std::nullopt;
    }
    return Config(std::move(path));
  }

 private:
  explicit Config(std::filesystem::path path) : path_(std::move(path)) {}

  std::filesystem::path path_;
};
```

Use return values for expected failure paths (`std::optional<User> FindUserById(UserId id);`).
Use `bool` when callers only need success/failure and no diagnostic value would be
lost (`bool ContainsUser(UserId id);`). For failures that need diagnostics, prefer
the repository's established status or result type. Avoid mixing multiple
error-handling styles in the same component without a clear reason.

### Error Handling at the ROOT Boundary

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

---

## Const-Correctness

Use `const` to communicate intent: `int size() const { return size_; }`. Pass
large objects by const reference when they do not need to be copied
(`void Render(const Scene& scene);`); pass small value types by value
(`double Distance(Point a, Point b);`); use `const` local variables when the value
should not change (`const auto count = items.size();`). Const-correctness improves
readability, correctness, and API design.

### Const-Correctness Caveats

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

---

## Templates and Generic Code

Use templates when the algorithm naturally works across multiple types:

```cpp
template <typename Range>
typename Range::value_type Sum(const Range& values) {
  typename Range::value_type result{};

  for (const auto& value : values) {
    result += value;
  }

  return result;
}
```

Do not use templates only to avoid writing clear types, and do not over-generalize
too early. Prefer simple concrete code first; introduce templates when repeated
patterns are clear and the generic version remains readable.

### Templates and Dictionary Limits

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

---

## Naming, Comments, and File Documentation

Match the repository's existing conventions first wherever this analysis code
lives. Use the following as a default when no repository convention exists.

### Naming Guidance

Use names that describe the responsibility clearly. Prefer nouns for types
(`class HttpClient;`, `struct Point;`) and verbs or verb phrases for functions
(`ParseConfig();`, `LoadImage();`, `CalculateTotal();`). Avoid vague names
(`DoStuff();`, `HandleData();`, `Process();`, `Run();`, `Manage();`). Short names
are acceptable for small scopes (`for (const auto& x : values) { ... }`); use more
descriptive names for wider scopes.

For this codebase specifically, C++/ROOT macros follow Google C++ style:
`snake_case` variables/params, `PascalCase` types/functions, `kPascalCase` static
constants, `trailing_underscore_` members, `ALL_CAPS` only for macros. Use
meaningful, descriptive physics names for histograms, canvases, and functions:
`event_weight`, `signal_yield`, `mass_window`, `fit_range`, `mass_hist`,
`fit_result`. Standard HEP abbreviations (`pt`, `eta`, `phi`, `met`, `pu`, `sf`,
`mc`) are fine. Python naming follows Google/PEP 8 conventions instead — see
[Python coding](python-hep-coding-patterns.md).

### Comments and Documentation

Write comments to explain why, not what. Avoid comments that repeat the code
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

---

## File and Build Organization

### File Organization

Keep files focused. A file should usually contain one primary class or
abstraction, closely related simple structs, closely related free functions, and
implementation details hidden in an unnamed namespace when appropriate. Use
namespaces to group related functionality:

```cpp
namespace geometry {

struct Point {
  double x;
  double y;
};

double Distance(Point a, Point b);

class Polygon;

}  // namespace geometry
```

Avoid large files that mix unrelated responsibilities, and avoid catch-all files
such as `utils.cc`, `helpers.cc`, `misc.cc`, `common.cc` — acceptable only for
very small, clearly scoped collections.

### ROOT dictionary and build layout

Keep a `TObject`-derived class's declaration (`.h`, with `ClassDef`) and
definition (`.cxx`, with `ClassImp`) split the same way as any other C++ class in
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
c++ -std=c++17 -O2 -Wall -Wextra analysis.cpp $(root-config --cflags --libs) -o analysis
```

Compiled macro:

```bash
root -l -q 'analysis.C+("input.root")'
```

For CMake-based projects, see [Build setup](cmake-and-build.md).

---

## Testing Guidance

Prefer designs that are easy to test. Free functions should be deterministic when
possible. Classes should expose behavior, not internal implementation details.
Avoid hidden dependencies that make tests fragile; prefer dependency injection
over hard-coded global dependencies:

```cpp
class ReportGenerator {
 public:
  explicit ReportGenerator(const Clock& clock) : clock_(clock) {}

 private:
  const Clock& clock_;
};
```

Avoid this:

```cpp
class ReportGenerator {
 public:
  Report Generate() {
    const auto now = SystemClock::Now();
    // ...
  }
};
```

Code should be designed so that core logic can be tested without file systems,
networks, timers, or global state when possible — for ROOT's own globals
specifically, see [Global State and Testability](#global-state-and-testability)
above.

---

## Standard Library Preference

Prefer the C++ standard library over custom implementations: `std::vector`,
`std::array`, `std::string`, `std::string_view`, `std::optional`, `std::variant`,
`std::unique_ptr`, `std::shared_ptr`, `std::filesystem`, `std::chrono`,
`std::span`, `std::ranges`. Do not write custom containers, smart pointers, string
classes, or date/time utilities unless there is a strong project-specific reason.

Prefer algorithms from the standard library when they improve clarity
(`std::find`, `std::sort`, `std::transform`, `std::accumulate`, `std::any_of`,
`std::all_of`, `std::none_of`). Use standard algorithms when they make intent
clearer; use loops when they are more readable.

Default to C++17 for this codebase's ROOT-facing code. Prefer RAII and
standard-library containers; prefer `std::string` over `TString` unless a ROOT
API specifically requires ROOT string behavior.

---

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
data/MC; mask blinded data in both the main panel and any ratio (see
[Analysis design](../../hep-analysis/references/analysis-design.md) for blinding rules and
[Histograms and uncertainties](../../hep-analysis/references/histograms-efficiencies.md) for ratio/pull
statistics).

---

## Design Checklist

Before adding a new class, ask:

1. Does it own state, protect an invariant, or manage a resource?
2. Does it represent a real concept?
3. Does it need polymorphic behavior?
4. Would a simple `struct` plus free functions be clearer?
5. Does it actually need `TObject`/a dictionary (I/O, `TTree` branch object,
   `TBrowser`, a ROOT container), or is it purely analysis-internal?

Before adding a new member function, ask whether it needs access to private
state, preserves or modifies an invariant, is essential behavior of the object,
or whether a free function would be more flexible and testable.

Before adding a free function, ask whether it is mostly an algorithm or
calculation, avoids unnecessary access to private state, can be tested
independently, and makes the type simpler.

Before adding inheritance, ask whether runtime polymorphism is required, whether
callers will use different implementations through a common interface, whether
composition or `std::variant` would be clearer, and whether the hierarchy is
likely to remain shallow and stable.

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
- Inputs/trees/branch names are validated and documented; units are explicit;
  selections are named and traceable; weights are applied exactly once.
- Histograms have names and axis labels; empty histograms are handled safely;
  fit status/covariance is checked; output files are closed cleanly.
- Build/run commands are documented; tests/validation are run, or their absence
  is stated with a reason.

---

## Anti-Patterns to Avoid (recap)

- Excessive OOP (see [When to Use Free Functions](#when-to-use-free-functions)).
- Stateless utility classes (see [Avoid Artificial Utility Classes](#avoid-artificial-utility-classes)).
- Unnecessary inheritance (see [Inheritance and Polymorphism](#inheritance-and-polymorphism)).
- Global mutable state (see [State Management](#state-management)).
- Classes with unclear responsibility (see [Naming Guidance](#naming-guidance)).
- Inheriting from `TObject` "just in case," for a type that never crosses an I/O
  or reflection boundary.
- Wrapping a directory-owned object (an un-detached histogram/tree) in an owning
  smart pointer, or deleting it manually — either double-frees it or fights the
  directory for ownership.
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

## Summary Rule

As a default: use `class` for state, ownership, lifetime, invariants, resources,
RAII, and true runtime polymorphism; use `struct` for simple passive data
(including flat `TTree` branch buffers); use free functions for algorithms,
calculations, conversions, and procedural workflows. Avoid unnecessary
inheritance, fake OOP such as stateless utility classes, and hidden global
mutable state. Prefer explicit ownership, explicit dependencies, and standard
library facilities over custom infrastructure.

On top of that, take on `TObject`, a dictionary, and directory ownership only for
types that actually need ROOT's I/O, branch-storage, or reflection services;
write everything else as plain, RAII-friendly C++. Where ROOT's ownership or
error-reporting model genuinely differs from general C++ practice, make the
departure explicit and contained — an owner, a `SetDirectory(nullptr)`, or a
checked return value at the boundary — rather than letting ROOT's conventions
bleed into code that has no reason to follow them.

When uncertain, choose the simpler design first. Add abstraction only when the
code clearly benefits from it.
