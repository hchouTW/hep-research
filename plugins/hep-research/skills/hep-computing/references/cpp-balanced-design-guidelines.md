# Balanced C++ Design Guidelines

A checklist for general C++ in HEP code: analysis executables, reconstruction and calibration libraries, tools
around ROOT. ROOT's object model (TObject, dictionaries, directory ownership, RDataFrame) is in the
[ROOT guidelines](root-balanced-design-guidelines.md), which also fix the conventions every hep-computing reference
uses: naming, C++17 as the one baseline (`-std` from `root-config --cflags` or `ROOT_CXX_STANDARD`; C++20 features
marked "C++20 only"), exceptions allowed with one error style per component, `std::filesystem` for paths, and a
documented non-owning pointer instead of a reference member. Follow established repository conventions when they
intentionally differ.

## Design rules

- **Classes protect something.** Use a `class` when it owns a resource, guards an invariant (a calibration that
  must be loaded before use, a histogram set with matching binning) or needs runtime polymorphism. Plain data is a
  `struct` with public members and aggregate initialization; algorithms are free functions in a namespace. A class
  of only static functions (`Utils`, `Helper`, `Manager`) is a namespace with a vague name.
- **Free functions for physics.** Kinematics, selections, corrections and weights as free functions of their
  inputs (`double InvariantMass(const Lorentz& a, const Lorentz& b)`): testable without files, threads or globals.
- **Inheritance only for interchangeable behaviour** behind a stable interface (a detector-geometry provider, a
  pluggable fitter). Keep hierarchies shallow; consider `std::variant`, templates or a `std::function` first.
- **Explicit dependencies.** Pass conditions, configuration and random generators in; do not read globals (`gRandom`,
  a singleton database) inside library code. This is what makes multithreading and tests possible.

## Ownership and lifetime

- RAII for every resource: files, sockets, locks, temporary state. No naked `new`/`delete` outside a factory that
  immediately hands the object to an owner. `std::make_unique` by default; `std::shared_ptr` only for real shared
  ownership; values when the object is small or the container owns it.
- A non-owning dependency an object keeps is a pointer documented as non-owning, non-null and outliving the object;
  never a reference member (it binds to a temporary that then dangles, and blocks assignment). Reference parameters
  are for what a function only reads during the call.
- Do not return references or `std::string_view`/`std::span` (C++20 only) to locals or temporaries; do not keep
  iterators or pointers into a `std::vector` across a `push_back`.
- Objects that ROOT owns follow the [ROOT ownership rules](root-balanced-design-guidelines.md#ownership-guidelines):
  exactly one owner, and no smart pointer that outlives the file owning the object.

## Correctness checks

- `const` everything that does not change: parameters by `const&` for large objects, by value for small ones;
  `const` member functions; `const` locals.
- Numeric types: `double` for accumulations (sums of weights, integrals); `float` storage is fine but convert
  before summing many entries. Compare floats with a tolerance stated next to the comparison. Use `std::size_t` or
  `std::ptrdiff_t` for indices and check signed/unsigned comparisons (`-Wall -Wextra -Wsign-compare`).
- Initialize every member (`int n_ = 0;`) and every local at declaration. Uninitialized branch buffers produce
  plausible garbage, not crashes.
- Bounds: `.at()` in code that is not hot, or an explicit check before indexing; jagged collections (`nMuon`
  entries) are checked for size before `[0]`.
- Thread safety: code called from RDataFrame with implicit multithreading must not write shared state; give each
  slot its own state (`DefineSlot`).
- Errors: throw (or return `std::optional`/a status) at the point of detection with a message naming the input,
  the object and the value; never print and continue. Check every library call that can fail (file open, tree
  lookup, fit status).
- Templates for algorithms that really work across types; in C++17 constrain them with a `static_assert` on the
  value type (concepts are C++20 only). Prefer concrete code until the repetition is clear.

## Standard library first

`std::vector`, `std::array`, `std::string`, `std::string_view`, `std::optional`, `std::variant`, `std::unique_ptr`,
`std::filesystem`, `std::chrono`, and the algorithms (`std::sort`, `std::accumulate`, `std::any_of`) before a
hand-written container or loop when they make the intent clearer. `std::string` over `TString` unless a ROOT API
needs it.

## Files and builds

- One main abstraction per header/source pair; implementation details in an unnamed namespace; no catch-all
  `utils.cc`. Every file starts with the header comment block described in the
  [ROOT guidelines](root-balanced-design-guidelines.md#file-level-documentation-requirement).
- CMake with imported `ROOT::` targets ([CMake](cmake-and-build.md)); warnings on (`-Wall -Wextra`); a debug or
  sanitizer build for testing ([crash and memory debugging](crash-and-memory-debugging.md)).

## Testing

- Unit tests for the free functions (kinematics, selections, corrections) with hand-computed values, including
  edge cases: empty collections, zero weights, values on bin edges.
- A small synthetic input (`scripts/make_synthetic_nanoaod.py` writes one with known answers) for the event loop;
  compare outputs byte for byte, or within a stated tolerance for multithreaded sums.
- Run tests under AddressSanitizer at least once per change that touches memory handling.

## Grep-able anti-patterns

| Pattern | Problem | Instead |
|---|---|---|
| `new ` without an owner, `delete ` | leak or double delete | `std::make_unique`, values |
| `const T& member_;` | dangles when bound to a temporary | `const T* member_;`, documented non-owning |
| `class .*Utils`, `class .*Helper`, only `static` members | no responsibility | namespace with free functions |
| `gRandom`, `static` mutable locals in library code | not thread-safe, hidden dependency | pass a generator; per-slot state |
| `float sum` over many entries | precision loss | `double` accumulator |
| `-std=c++` next to `root-config --cflags` | second, conflicting standard | the flag from `root-config` only |
| `catch (...) {}` or print-and-continue | failure hidden | rethrow or return an error with context |
| `using namespace std;` in a header | name clashes for every includer | qualified names |
| `[0]` on a jagged collection without a size check | out of bounds on empty events | check the size first |
