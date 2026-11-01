# Task card AP-BOOT — pinned rerun of the official Allpix Squared pixel example (pinned in W2-AP)

Specification: `TASK.md` §12.2. Every tolerance and criterion below was fixed on 2026-11-02, before any acceptance run;
only a native pilot run (allowed, §5.5 Do 5) was made to size the budget. Pipeline validation only: 10 events are not
physics statistics and check 3b is a plausibility band, not physics validation.

| Field | Pinned value |
|---|---|
| Capability | `allpix.pixel-charge`, version 1; state `proposed` until W4A |
| Backend | Allpix Squared `master` commit `df69a6a4c69219e035dadf1005e7509856b73b86` (2026-10-30, `git describe` `v3.2.0-689-gdf69a6a4`; `allpix --version` prints `v3.2.0-689-gdf69a6a4`), source `https://github.com/allpix-squared/allpix-squared`, licence MIT. No Docker or CVMFS release matches a master commit; built from source (H0 #5) |
| Environment | source build in `WR/env/allpix` (`WR/env/build_allpix.sh`): Release, `BUILD_GDMLOutputWriter=OFF` (the Geant4 below has no GDML; AP-BOOT does not use the module), `CMAKE_CXX_FLAGS=-include numbers` (upstream `src/tools/units.h` uses `std::numbers` without including `<numbers>`; the macOS 27 SDK's libc++ no longer provides it transitively); dependencies: spdlog 1.15.3 and Boost 1.89.0 (random) built into `WR/env/deps`, Eigen 3 (Homebrew), ROOT 6.40.04 (Homebrew, C++20), **Geant4 11.4.3 (commit `2ee379e6`) built with C++20** into `WR/env/geant4` (MT, no GDML, no Qt; the host's earlier install is C++17, which master Allpix cannot use) |
| Geant4 record | `geant4_build.py register --dataset-source env` → `WR/env/W2-AP/geant4-register.json`: status ok, 12 datasets content-hashed; `geant4_build.py check` ok. The dataset variables cover all 12 datasets of `geant4-config --datasets` (Allpix's GeometryBuilderGeant4 requires G4NEUTRONHPDATA among others, `GeometryBuilderGeant4Module.cpp:106-117`); G4NDL 4.7.1 from `WR/env/g4data` (official MD5 `54f0ed39…`), the other eleven from the existing installation's data folder, never modified |
| Environment root | view folder `WR/env/ap-view`: `allpix`, `geant4`, `root`, `deps` and `data/<dataset>` links; the plan names only `ENV_ROOT/...`; identity is content-based (commits, versions, library hashes, dataset hashes), never the path |
| Variables | `PATH = ENV_ROOT/allpix/bin`; `DYLD_LIBRARY_PATH = ENV_ROOT/allpix/lib:ENV_ROOT/geant4/lib:ENV_ROOT/root/lib/root:ENV_ROOT/deps/lib`; the 12 dataset variables `ENV_ROOT/data/<dataset folder>` |
| Object library (V-08) | `ENV_ROOT/allpix/lib/libAllpixObjects.dylib` loads in ROOT 6.40.04 (`gSystem.Load` → 0); the extractor reads data members through PyROOT under Homebrew Python 3.15 (PyROOT's interpreter); without it, collect reports `missing-dependency` |
| Source files (V-07) | `examples/example.conf` (SHA-256 `bc735e7a…2ce3`), `examples/example_detector.conf` (`296abda7…d5f182`), `examples/example_electric_field.init` (`9d4da3e4…4fd8`) at `df69a6a4`, copied unchanged into the project as inputs; content as §12.2 (modules GeometryBuilderGeant4, DepositionGeant4 `FTFP_BERT_LIV` 120 GeV π⁺ pencil beam, ElectricFieldReader mesh, GenericPropagation, PulseTransfer, DefaultDigitizer 600 e threshold, two DetectorHistogrammer, ROOTObjectWriter `exclude = DepositedCharge, PropagatedCharge`, `[Ignore]` visualisation); `number_of_events = 10000` and no `random_seed` / `multithreading` key in the file |
| Override method | `-o key=value` on the command line, the official file unchanged (`src/exec/allpix.cpp:154-155`: each `-o` adds a module option). Allowed keys only: `number_of_events=10`, `multithreading=false` (written explicitly; upstream default is true), `random_seed=<integer>`, `output_directory=<ATTEMPT_ROOT path>`; `random_seed_core` is not set (its derived value, upstream default `random_seed + 1`, is recorded) |
| Sensor thickness (V-14) | `models/cmsp1.conf` line 12 at `df69a6a4`: `sensor_thickness = 285um` |
| Check 1 — configuration fidelity | the three source files' hashes equal the values above at run time (input manifest) and the override list holds only the allowed keys |
| Check 2 — reproducibility | the same plan (same seed) under `--replicate 0` and `--replicate 1` in the same environment identity gives, per event and per detector, identical PixelCharge (pixel index and charge) and PixelHit (pixel index, signal) data members after deserialisation, and identical per-event seeds in the `Event` tree; compared on data members only (no object references, no stored configuration, never the ROOT file hash). A plan with another seed differs somewhere. The summary lists per-pixel values |
| Check 3 — output semantics | 10 events; every event has at least one PixelHit in detector1 and at least one in detector2 (else failed); the expected tree set is the module chain minus the ROOTObjectWriter exclude list: `MCParticle`, `MCTrack`, `PixelCharge`, `PixelHit` (+ `Event`); `DepositedCharge` and `PropagatedCharge` are excluded by configuration, never reported missing; never fill with zeros |
| Check 3b — plausibility band | per event, Σ over detector1 pixels of `PixelCharge::getAbsoluteCharge()`; its median over the 10 events lies in [0.5, 2] × (75 e/µm × 285 µm) = **[10687.5, 42750] e**; labelled plausibility, not physics validation |
| Native comparison (auxiliary) | the same configuration run natively once with `multithreading = false`; SHOULD match check 2's data members; not an acceptance criterion |
| Counterexamples (must be caught) | missing dependency (object library or program absent → missing-dependency); wrong version (environment identity differs → plan-stale); missing Geant4 dataset (refused before running, or the program's own refusal → failed); exit 0 with required content missing (failed); no hit in a detector in some event (failed); charge sign read wrongly (check 3b uses getAbsoluteCharge; a signed sum fails the band); replaced input (input-changed / plan-stale) |
| Budget | native pilot (allowed): 10 events in 2.77 s wall (74 ms/event); one acceptance run ≤ 120 s timeout; whole acceptance (three runs + native) ≤ 10 min |
| Required guarantees | G0 `macos-g0`: inputs not modified (hard), timeout (hard), output-size abort (soft) |
| Not claimed | 10 events are not statistics; check 3b is not an external numerical oracle; no efficiency, waveform or scan |

## Amendments (recorded after W4A review round 1, 2026-11-02; none relaxes a tolerance or criterion)

- Override method, as built: the command line is exactly `ENV_ROOT/allpix/bin/allpix -c INPUT_ROOT/<config>` followed by
  the three overrides `number_of_events=10`, `multithreading=false`, `random_seed=<n>`, each once (check 1 whitelists the
  whole argv); no `output_directory` override — the output goes to Allpix's default folder under ATTEMPT_ROOT (the
  runner binds a logical root only at the start of an argument). `DYLD_LIBRARY_PATH = ENV_ROOT/allpix/lib` only.
- Added check `charge-sign`: every PixelCharge charge is strictly negative (this example propagates electrons only);
  catches a sign read wrongly even where the plausibility band would pass.
- Stored class versions pinned: PixelCharge 9, PixelHit 7, Pixel 2 (as written at `df69a6a4`); another version fails the
  members check. The extractor reads data members through ROOT's stored class layouts, without the Allpix object
  library (cross-checked against the library's accessors: identical).
- Check 2 procedure: `compare_summary_files(A, B)` of `detsim_backend_allpix.py` on two committed runs'
  `extract/pixel_summary.json` (command in its docstring); its result lists per-pixel values from both runs.
- Environment identity: also the SHA-256 of every library the `allpix` program and its module libraries load
  (resolved in the loader's order: the plan's library path, LC_RPATH, install names; system libraries excluded), grouped
  by Allpix, Geant4, ROOT, dependencies and other; the rpaths are recorded in facts.
- Known limitation: collect reads ROOT files inside the detsim controller; a crash of ROOT there ends the controller
  without a JSON answer; the OS releases the lock, the record stays unfinished (inspect: stale) and the next run moves
  the attempt to orphans (TASK.md 10.4).
