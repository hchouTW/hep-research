# Support matrix — detector-simulation adapter (TASK.md 15.2)

One row per tested combination; anything not listed is untested. Kept in step with `adapter.json`
`tools[].tested_versions` and the `docs/capability-matrix.md` row.

| Capability | Backend (commit, environment source, identity) | Adapter | Platform | Validation |
|---|---|---|---|---|
| `allpix.pixel-charge` 1.0.0 (card AP-BOOT) | Allpix Squared `df69a6a4c69219e035dadf1005e7509856b73b86` (v3.2.0-689), source build in the work root against a C++20 Geant4 11.4.3 (12 registered datasets) and Homebrew ROOT 6.40.04; view folder; env identity `04b91a73…` (97 libraries hashed) | 0.4.0, tool `allpix-squared`, `tested-in-declared-environment` | macOS 27.2 arm64, APFS, runner profile `macos-g0` (commit_noreplace hard, durable_commit soft, timeout_kill hard, output_size_abort soft, descendants_killed soft, backend_dies_with_controller soft, no_network unsupported) | T-ENV, T-AP, T-OUTPUT, T-CONV (2026-11-02): checks 1, 2, 3, 3b, charge-sign and class versions pass; VALIDATION DETSIM-W4A, DETSIM-W5. Limitations: 10 events, plausibility band only, no physical validity |
| `garfield.gas-table-query` 1.0.0 (card GF-QUERY) | Garfield++ `e2e58ea74ec8b20d347d78b7a769f40e3b156072`, source build (GSL on, Eigen off) with Homebrew ROOT 6.40.04 and Python 3.15.2 PyROOT; view folder; env identity `96827976…` | 0.4.0, tool `garfieldpp`, `tested-in-declared-environment` | same host and profile | T-ENV, T-GF, T-OUTPUT, T-CONV (2026-11-02): checks 1-4 pass on the example table `ar_80_co2_20_0T.gas` (pipeline validation only); VALIDATION DETSIM-W4G, DETSIM-W5. Limitations: 1D tables, B = 0, the table's T and p only, no physical validity |
| shared layer (detsim run/inspect/probe) | — | 0.4.0, `demonstrated-on-synthetic-data` | `macos-g0` measured; `linux-g0` every guarantee unsupported (not measured) | T-IDEM … T-OUTPUT with the synthetic backend; VALIDATION DETSIM-W3A, DETSIM-W3B |

Untested: Linux (any distribution), other Allpix Squared or Garfield++ versions, release tags, Docker images, CVMFS,
LCG views, other gas tables, user Allpix configurations.
