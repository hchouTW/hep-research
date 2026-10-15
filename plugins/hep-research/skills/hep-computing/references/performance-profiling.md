# Performance profiling (ROOT, RDataFrame, uproot, Python)

Use when correct code is too slow or too large for its budget: an RDataFrame or TTree loop, an uproot/awkward
script, a PyROOT macro, a batch job that runs out of wall time or memory. Crashes and leaks are in
[crash and memory debugging](crash-and-memory-debugging.md); numerical accuracy is in
[numerical and computational methods](numerical-and-computational-methods.md).

Checked on 2026-10-13 with ROOT 6.38.04 (PyROOT, Python 3.14), uproot 5.7.6 and CPython 3.13 `cProfile`:
`GetNRuns`, `RunGraphs`, `TTreePerfStats`, the default auto-flush, and the `uproot.iterate` options named below.
`perf` and `py-spy` were not available there; their command lines follow their documentation (perf 6.x, py-spy 0.3).

## Decision rules

1. State the target before measuring, in the acceptance criteria: "1e7 events in under 10 minutes on 8 cores",
   "peak memory under 2 GB per job". Stop when it is met; a faster version past the target is not a deliverable.
2. Measure wall time and peak memory first, on a fixed input, three runs or more, and report the spread:
   `/usr/bin/time -v cmd` on Linux ("Maximum resident set size" in kB), `/usr/bin/time -l cmd` on macOS (bytes).
   In a batch job, the scheduler's accounting (`sacct --format=Elapsed,MaxRSS`, HTCondor `MemoryUsage`) is the
   number that matters.
3. Find where the time goes before changing code: CPU in your code, CPU in ROOT, decompression, I/O wait, or
   Python overhead. A profile, not a guess.
4. Change one thing at a time and keep the output identical: compare the outputs byte for byte (or within the
   tolerance stated for multithreaded sums) after each change.
5. Prefer the change with the largest measured effect and least code: reading fewer branches, one event loop
   instead of several, a larger uproot step; rewrites come last.

## Where the time goes

- Compiled code and ROOT itself (Linux): `perf record -g ./build/analysis input.root`, then `perf report`. Build with
  `-g` and keep optimization on (`RelWithDebInfo`): profiling a `-O0` build measures the wrong program.
- Python: `python3 -m cProfile -o run.prof script.py`, then
  `python3 -c "import pstats; pstats.Stats('run.prof').sort_stats('cumulative').print_stats(20)"`. cProfile does not
  see inside C++ calls (a PyROOT call or an awkward kernel is one line). `py-spy record -o profile.svg -- python3
  script.py` samples without instrumenting and, with `--native`, shows C++ frames too; `py-spy dump --pid PID` shows
  where a running job is stuck.
- Is the job CPU-bound? CPU time close to wall time times threads means yes; much lower means it waits for I/O
  (remote files, a slow disk) and more threads will not help.

## RDataFrame

- One event loop: book every result first, then read them. `df.GetNRuns()` counts the loops: two results booked
  together and read afterwards give 1; a result booked after the first was read starts a second loop (checked: 1,
  then 2). Several independent dataframes run in one parallel pass with `ROOT::RDF::RunGraphs({r1, r2})`.
- `ROOT::EnableImplicitMT(n)` before building the dataframe; give it the cores the job was allocated (`n` from
  `$SLURM_CPUS_PER_TASK` or the HTCondor request), never the node's total. Multithreading splits by cluster:
  a file with few clusters cannot use many threads. Results that sum floating-point numbers differ in the last
  digits between runs; `Range` is not available with IMT (see the
  [ROOT guidelines](root-balanced-design-guidelines.md#design-checklist)).
- Jitted strings (`Define("y", "x*x")`) are compiled at the start of the event loop: seconds per loop, which
  dominates short test runs; compiled lambdas avoid it. Measure on a realistic input size.
- `Snapshot` runs its own event loop unless `RSnapshotOptions::fLazy` is set.

## TTree I/O

- Read only the branches you use: RDataFrame and `TTreeReader` already do; with `SetBranchAddress` call
  `tree->SetBranchStatus("*", false)` then enable the needed ones.
- `TTreePerfStats ps("ioperf", tree);` before the loop, `ps.Print()` after it: number of read calls, bytes read and
  unzipped, real and CPU time. Many small reads point at the cache or at remote latency; unzip time close to the
  total points at compression.
- Writing: clusters of 30 MB compressed data by default (`GetAutoFlush()` returns -30000000, a negative value meaning
  bytes). Small clusters make many small reads; very large ones cost memory per thread. Basket sizes adapt at the
  first flush; `TTree::OptimizeBaskets` re-balances them. Change these only with a `TTreePerfStats` comparison.
- Compression (`TFile::SetCompressionSettings`, `ROOT::RCompressionSetting`) trades size for read speed: LZ4
  decompresses fastest, ZSTD and LZMA write smaller files. Decide with a measurement on your own files and record
  the setting with the output. RDataFrame `Snapshot` changed its default in ROOT 6.38 from 101 (ZLIB level 1, the
  `TTree` default) to 505 (ZSTD level 5), as ROOT 6.38.04 itself reports; outputs of the same code differ in size
  between releases.
- Remote files (XRootD): latency dominates; read a larger cache or copy the file once when it is read many times
  (see [Python coding](python-hep-coding-patterns.md#remote-files-xrootd)).

## uproot and awkward

- Name the branches: `uproot.iterate(files, expressions=[...])` or `filter_name="Muon_*"`; reading every branch
  of a NanoAOD-like file is the most common waste.
- `step_size="100 MB"` (or a number of entries) sets the chunk; too small and Python overhead per chunk dominates,
  too large and memory per worker grows. Measure two or three values.
- Stay columnar: no Python loop over events. A loop that is unavoidable belongs in numba (on NumPy arrays, or awkward
  arrays with numba's awkward extension) or in compiled code.
- `decompression_executor` and `interpretation_executor` (thread pools) help when decompression dominates.

## Batch-scale checks

- Profile one chunk, then size the job: time per event × events per chunk + start-up time (environment setup,
  jitting, opening files). Start-up that is a large share of a short chunk means larger chunks.
- Pilot first: run a few chunks with the real resources before the full campaign ([batch scheduling](batch-scheduling.md)).

## Record

Write the target, the before and after numbers with their spread, the input, the commands and the tool versions into
the run record (`computational-run`). A speed-up without an output comparison is not done.

## Handoffs

- Training throughput and GPU utilization: hep-ml.
- Whether a faster approximate method is accurate enough: [numerical and computational methods](numerical-and-computational-methods.md),
  hep-statistics for inference.
