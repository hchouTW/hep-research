# F05 adapters and tool-dependent tests (E2, dd9b940)

From the verbose unit run (`HEP_ROOT_PYTHON=/opt/homebrew/bin/python3.14`, venv `~/.venvs/hep-research-e2`).

| Adapter / tool | `adapter.json` (E1) | E2 status | Evidence (tests ok / skip / fail) |
|---|---|---|---|
| pyhf-combine: pyhf | demonstrated, 0.7.6 | **tested here, 0.7.6** | `test_pyhf_counting` 2, `test_pyhf_shape` 4, `test_pyhf_nuisance_diagnostics` 8, `test_pyhf_publication` 4, `test_nuisance_interpolation` 3 ok |
| pyhf-combine: CMS Combine | demonstrated, 11.1.0 | **unverified** (no `combine`, no Docker, no `HEP_COMBINE_WRAPPER`) | `test_combine_datacard_template` 2 ok (template only), 1 skip (`test_limit_matches_pyhf`) |
| root-uproot: ROOT | demonstrated, 6.40.04 | **tested here, 6.38.04** (Homebrew, PyROOT via python3.14; older than the declared tested version) | `test_root_cpp_assets` 5, `test_root_integration` 7, `test_root_cpp_scripts` 4 ok |
| root-uproot: uproot / awkward | demonstrated, 5.7.6 / 2.14.0 | **tested here, 5.7.6 / 2.14.0** | `test_uproot_awkward_asset` 3 ok |
| batch-schedulers: Slurm | documented, none | fake scheduler only; real **unverified** (no `sbatch`) | `test_batch_slurm` 9 ok, 1 skip (real Slurm) |
| batch-schedulers: HTCondor | documented, none | fake scheduler only; real **unverified** (no `condor_submit`) | `test_batch_htcondor` 9 ok, 1 skip (real pool) |
| physics-ml: PyTorch / torchvision | (no adapter) | **tested here, 2.14.1 / 0.29.1 (CPU)**, except DDP | `test_physics_ml_skill` 119 ok, 2 skip (only meaningful without torch); `test_assets_smoke` 8 ok, **1 error**: `test_ddp_skeleton_two_gloo_processes` timed out (300 s) |
| diagrams: Graphviz `dot` 16.1.0, PlantUML 1.2026.8 | (no adapter) | **tested here** | `test_diagrams` DOT and PlantUML blocks pass |
| diagrams: Mermaid `mmdc` 12.0.0 | (no adapter) | **tested here after completing the install** | `test_shipped_diagram_sources_pass` **failed** in F02: Homebrew `mermaid-cli` ships without the headless Chrome (`chrome-headless-shell` 154.0.8037.57). After `npx @puppeteer/browsers install chrome-headless-shell@154.0.8037.57 --path ~/.cache/puppeteer`: all 22 diagram tests pass |

## DDP timeout: cause

`torchrun --nproc_per_node=2` (gloo) hangs in c10d rendezvous: the host name `Mac.hitronhub.home` does not resolve
(`socket.getaddrinfo(socket.gethostname())` → Errno 8; log: "The IPv6 network addresses of (Mac.hitronhub.home, …)
cannot be retrieved"). It passed twice standalone earlier in the session, when the router's DNS answered, and then
hung in four later runs, including with `--master_addr=127.0.0.1` and `GLOO_SOCKET_IFNAME=lo0`. Network-dependent,
not a plugin defect as such; the test and asset depend on host-name resolution.

Adapter declarations (`test_adapter_declarations`): 2 ok.
