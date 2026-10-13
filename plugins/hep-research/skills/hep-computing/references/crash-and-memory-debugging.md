# Crash and memory debugging (ROOT, PyROOT, C++)

Use when a ROOT macro, a compiled analysis or a PyROOT script crashes (segmentation violation, abort, `bad_alloc`)
or its memory grows until the job is killed. Build and link errors are in [ROOT debugging](root-debugging.md) and
[CMake](cmake-and-build.md); slow but correct code is in [performance profiling](performance-profiling.md).

Checked on 2026-10-13 with ROOT 6.38.04 (Homebrew, macOS arm64) and lldb 2100: ROOT's stack trace setting, the
valgrind suppression files, `gSystem->GetProcInfo` and the directory "leak" below. gdb, valgrind and the Linux
LeakSanitizer are not available there; their command lines follow their documentation (gdb 14, valgrind 3.22).

## Decision rules

1. Reproduce before you fix. A crash you cannot reproduce on demand is not fixed by a change that makes it go away
   once.
2. Shrink the reproducer: one input file, the fewest events that still crash (`Range(0, n)` in RDataFrame, a
   `TTree::GetEntry` loop with a bound), one thread (`ROOT::DisableImplicitMT()`, no `EnableImplicitMT`), batch mode
   (`root -l -b -q`). If it stops crashing single-threaded, it is a thread-safety bug: look for shared state in
   `Define`/`Filter` (globals, `gRandom`, a non-const member captured by reference).
3. Read the first frame in your own code, not the top frame. ROOT frames above it are where the bad pointer was
   used, rarely where it was made.
4. Debug a compiled build with symbols (`-g`, `CMAKE_BUILD_TYPE=RelWithDebInfo` or `Debug`, ACLiC `+g`). An
   optimized build without symbols gives frames that do not match the source.
5. A tool's silence is not proof. A clean valgrind or sanitizer run covers only the code paths and inputs it ran.
6. Stop when the reproducer passes, the regression test that failed before passes, and the full input runs; record
   the tool, version and command in the run record.

## Read ROOT's own stack trace

ROOT installs a signal handler (`Root.Stacktrace: yes` in `$(root-config --etcdir)/system.rootrc`) that prints
`*** Break *** segmentation violation` and a stack trace when a debugger is available, followed by "The lines below
might hint at the cause of the crash". Use those lines first. When ROOT's handler gets in the way of a debugger, set
`Root.Stacktrace: no` in a local `.rootrc` (the working directory's file overrides the system one).

`gDebug` raises ROOT's internal verbosity: `gDebug = 1` (or `root -l -b -q -e 'gDebug=1' macro.C`) shows streamer
and dictionary activity, useful when a crash follows reading a custom class. Reset it to 0 afterwards; at 2 and more
the output is very large.

## Run under a debugger

```bash
gdb --args root.exe -l -b -q 'macro.C+g("input.root")'      # Linux: then run, bt, frame N, print var
lldb -- root.exe -l -b -q 'macro.C+g("input.root")'         # macOS: then run, bt, frame select N
gdb --args ./build/analysis input.root                      # a compiled program
gdb --args python3 script.py                                # PyROOT: C++ frames appear below the Python ones
```

Use `root.exe`, not `root`: on several installations `root` is a wrapper script and the debugger then attaches to the
shell. In a batch job, enable core files (`ulimit -c unlimited`) and analyse the core afterwards
(`gdb root.exe core.12345`) rather than running a debugger on the node.

## Memory errors: valgrind and sanitizers

- valgrind memcheck (Linux), with ROOT's suppressions so known ROOT and Cling noise is hidden:

  ```bash
  valgrind --suppressions=$(root-config --etcdir)/valgrind-root.supp --num-callers=30 \
           --leak-check=full root.exe -l -b -q 'macro.C+g'
  ```

  `valgrind-root-python.supp` in the same folder is for PyROOT under `python3`. Expect 20 to 50 times slower runs:
  use the shrunk reproducer. Read "Invalid read/write" first; "definitely lost" leaks next; "possibly lost" and
  "still reachable" at exit are usually ROOT's own caches.
- AddressSanitizer and UndefinedBehaviorSanitizer on your compiled code (fast, about 2 times slower):

  ```bash
  cmake -S . -B build-asan -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer" \
        -DCMAKE_EXE_LINKER_FLAGS="-fsanitize=address,undefined"
  cmake --build build-asan -j && ./build-asan/analysis input.root
  ```

  ROOT's libraries are not instrumented, so ASan sees errors in your code and at its calls into ROOT, not inside
  ROOT. Run sanitizers on compiled executables, not inside an interactive `root.exe` session or ACLiC macros, where
  Cling's JIT and the uninstrumented interpreter produce false reports. Leak detection
  (`ASAN_OPTIONS=detect_leaks=1`) works on Linux; Apple clang on macOS arm64 does not support it.
- ACLiC: `.L macro.C+g` compiles with debug symbols, `+` recompiles when the source changed, `++` always. A cached
  `macro_C.so` built against an older version of a header it includes gives stale results or crashes: force a
  rebuild with `++` after changing any included header (see [ROOT debugging](root-debugging.md#reading-flat-array-branches-and-comparing-files)).

## Common crash causes and their checks

| Symptom | Likely cause | Check |
|---|---|---|
| Crash after `TFile::Close` or at the end of a function | object owned by the file used after the file closed, or deleted twice | [ownership rules](root-balanced-design-guidelines.md#directory-based-ownership): `SetDirectory(nullptr)`, one owner |
| Wrong values, then crash in `GetEntry` | `SetBranchAddress` with the wrong type or a pointer to a variable that went out of scope | ROOT's "The pointer type given ... does not correspond" message; use `TTreeReader` |
| Crash only with `EnableImplicitMT` | shared mutable state in `Define`/`Filter`, `gRandom` | rule 2 above; `DefineSlot` with one generator per slot |
| Empty plot or crash in PyROOT after a helper returns | Python deleted an object C++ still uses | [PyROOT ownership](python-hep-coding-patterns.md#pyroot): keep a reference, `ROOT.SetOwnership` |
| `std::bad_alloc` or the batch system's memory kill | a real leak, or everything kept in memory on purpose | the leak triage below |
| Stack overflow in a macro | large local arrays (`double a[1000000]`) | `std::vector` on the heap |

## Leak triage

1. Measure resident memory against progress, not once. In C++ and PyROOT:
   `ProcInfo_t info; gSystem->GetProcInfo(&info); info.fMemResident` (kB). In Python without ROOT:
   `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` (peak; kB on Linux, bytes on macOS). Print it every N events
   and at each new input file.
2. Read the shape. Linear growth with events: something allocated per event and never freed (a `new` without an
   owner, a histogram booked per event). Steps at each file: objects per file kept alive (trees, histograms read and
   not deleted, file handles). Growth that levels off: a cache (baskets, Cling, the OS), not a leak.
3. Count ROOT objects: with `Root.ObjectStat: 1` in `.rootrc` (or `TObject::SetObjectStat(kTRUE)` before the objects
   are made), `gObjectTable->Print()` lists live `TObject`s by class; print it twice and compare.
4. The leak that is the directory: histograms created inside a loop while a `TFile` is the current directory are
   owned by that file and stay in memory until it closes. In a check on ROOT 6.38.04, 20000 `TH1D` with 100 bins
   created that way left 20000 objects in the file's list and about 50 MB more resident memory until `Close()`.
   Book histograms once outside the loop, or call `TH1::AddDirectory(kFALSE)` and own them.
5. Jitted RDataFrame strings: every new `Define`/`Filter` expression string is compiled by Cling and its code stays
   loaded. Building many RDataFrames with distinct strings in a loop grows memory without bound: use compiled
   callables, or build all graphs first and run them together with `ROOT::RDF::RunGraphs`.
6. Prove the fix the same way: the same measurement over the same input, flat (or levelling off) after the change.

## Handoffs

- Wrong numbers without a crash: [validation and done](validation-and-done.md) and hep-analysis.
- Slow but correct: [performance profiling](performance-profiling.md).
- A model's training memory: physics-ml.
