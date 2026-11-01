# Source index: Allpix Squared and Garfield++ knowledge guides

Source records for the knowledge deliverable K (task specification §13.2) and the two guides it produced:
`skills/hep-detector/references/sensor-and-gas-transport-tools.md` (tool selection, model and signal boundaries, the
two task cards) and `skills/hep-computing/references/sensor-and-gas-simulation-operations.md` (environment, build,
`detsim` command, troubleshooting). Every version-sensitive statement in those guides cites an ID from this file.

Built 2026-11-01 by work item WK. Rules:

- **Priority**: official documentation and source of the same version, then release notes and examples, then forums
  (leads only, never cited for a fact).
- **Content hash**: SHA-256 of exactly what was retrieved. For a repository file, the hash of the blob at the stated
  commit (`git show <commit>:<path> | shasum -a 256`); for a whole tree or a directory listing, the hash of
  `git ls-tree -r <commit>` or `git ls-tree <commit> <dir>/` output; for a web page, the hash of the bytes the server returned at
  the retrieval time (pages are dynamic, so a later retrieval may differ without the content changing). Empty when
  retrieval failed or the source was not retrieved.
- **Retrieval**: repository files were read from the read-only clones in the task's work root (`WR/upstream/`, blob-less
  clones made in W0); web pages were downloaded with `curl` and a generic User-Agent on 2026-11-01 at about 12:06 UTC.
- **Review status** (exactly one of these values):
  - `read`: WK read the cited part itself and the guides' statements match it;
  - `read-partial`: WK read only what the Section column names (a title page, a listing, a version line);
  - `retrieved-not-used`: retrieved and hashed, no guide statement rests on it;
  - `lead-only`: a forum or copy of unknown version; never cited for a fact;
  - `retrieval-failed`: retrieval was attempted and failed (content hash empty).
- **Licence**: as stated by the source. Allpix Squared code is MIT and its manual pages CC-BY-4.0 (`LICENSE.md`,
  SPDX headers). The Garfield++ repository has no licence file at its root, so the terms of its files, including
  the example gas tables, are not stated (recorded as "not stated").

## Pinned upstream states

| Upstream | Commit | `git describe` | Date (commit) | Note |
|---|---|---|---|---|
| Allpix Squared, master | `df69a6a4c69219e035dadf1005e7509856b73b86` | `v3.2.0-689-gdf69a6a4` | 2026-10-30 | Development branch. The latest release tag `v3.3.0` (`8d570fdde8f76ca46cbf50af82bd01173559bd13`, 2026-09-30) is **not an ancestor** of this master (separate release branch); 473 files differ between them |
| Garfield++, master | `e2e58ea74ec8b20d347d78b7a769f40e3b156072` | `2026.10-4-ge2e58ea` | 2026-10-28 | Four commits after tag `2026.10` (`419bd464`); CMake project version 0.3 |

Neither backend has been built or run by WK; the task cards pin their own commits in W2-AP and W2-GF, and any
statement below must be re-read at that pinned commit before it is relied on for a run.

## Allpix Squared — repository files (commit `df69a6a4` unless stated)

| ID | Repository | Type | Version or commit | Section / symbol / lines | Retrieved | Content hash (SHA-256) | Licence | Review status |
|---|---|---|---|---|---|---|---|---|
| AP-01 | `https://github.com/allpix-squared/allpix-squared.git` (mirror of the CERN GitLab project) | source repository | `df69a6a4` (master) | whole tree, tags `v3.2.0`, `v3.3.0` | 2026-11-01 | `aa3d7d6f0babcbf75c47c78d3e8c0792b4f1142b1b84a3fc5996319ca61a54a9` (`ls-tree -r`) | MIT (`LICENSE.md`) | read-partial |
| AP-02 | AP-01 | example configuration | `df69a6a4` | `examples/example.conf`: modules, `number_of_events = 10000`, no `random_seed`, no `multithreading` key, `[Ignore]` visualisation, `ROOTObjectWriter exclude = DepositedCharge, PropagatedCharge`, `DefaultDigitizer threshold = 600e`, `physics_list = FTFP_BERT_LIV`, 120 GeV `Pi+` beam | 2026-11-01 | `bc735e7ae12414b7f1cb42fb8a6f8ecc2a59a6616f8c8c6d4410c49bb3312ce3` | MIT | read |
| AP-03 | AP-01 | example detector setup | `df69a6a4` | `examples/example_detector.conf`: two `cmsp1` detectors, detector2 at (10 µm, 80 µm, 4 mm), rotated −45° | 2026-11-01 | `296abda7e360dcdec9d99a1c2b6737e2567070747cc940e15666f902b8d5f182` | MIT | read |
| AP-04 | AP-01 | example field map | `df69a6a4` | `examples/example_electric_field.init` (external input of AP-02) | 2026-11-01 | `9d4da3e4b965fd5d55580e020c34c13f355ae8c4e9562c3952ca7b68849d4fd8` | MIT | read-partial |
| AP-05 | AP-01 | detector model | `df69a6a4` | `models/cmsp1.conf` line 12 `sensor_thickness = 285um`; lines 9-10: 52 × 80 pixels of 150 µm × 100 µm. At `v3.3.0` the file lacks the `name = "cmsp1"` line, otherwise the same | 2026-11-01 | `13ae919d95229d4322b1a4340f46702e805a66deead4eb5d0760e0d5a855e0c0` | MIT | read |
| AP-06 | AP-01 | executable source | `df69a6a4` | `src/exec/allpix.cpp` line 154 (`-o` parsing), line 182 (help text "-o <option> extra module configuration option(s) to pass") | 2026-11-01 | `5dfae0d8399f83a613eb0967f46ed2e4e624f36186641b0ce7669127fd107683` | MIT | read |
| AP-07 | AP-01 | manual page (source) | `df69a6a4` | `doc/usermanual/03_getting_started/05_allpix_executable.md`: `-o` adds or overwrites main-configuration keys (`-o output_directory=...`), module keys as `Module.key`, per-detector as `Module:detector.key`; only the single argument after `-o` is read | 2026-11-01 | `453483ad2f5d709a6cdba6d6233f9055fe9fdf0f27b543e9875ebe937eac24cb` | CC-BY-4.0 | read |
| AP-08 | AP-01 | manual page (source) | `df69a6a4` | `doc/usermanual/03_getting_started/04_framework_parameters.md`: `number_of_events` (default 1), `random_seed` (`mt19937_64` seed generator; random if unset), `random_seed_core` (default `random_seed + 1`), `multithreading` (default `true`), `workers`, `output_directory`, `root_file` (default `modules.root`), `log_level` values. `v3.3.0` differs only in the `log_level` value list (adds `FATAL`) | 2026-11-01 | `4115e98d5109a44a92b80880cf68474ab02d1a3e06d2d9fbcedb3450306ae09e` | CC-BY-4.0 | read |
| AP-09 | AP-01 | manual page (source) | `df69a6a4` | `doc/usermanual/04_framework/10_multithreading.md`, "Seed Distribution": per-event seeds from a central generator in event order, reproducible for a different number of workers | 2026-11-01 | `e4969ea46651defbb9aefb526baa46f5b76aa1a74a12cb51c60ada45c7e5c5f8` | CC-BY-4.0 | read |
| AP-10 | AP-01 | module documentation | `df69a6a4` | `src/modules/ROOTObjectWriter/README.md` lines 13-25: tree created when the first object of a type arrives; empty vector stored for events without objects; `Event` tree holds event number and seed; `include` / `exclude` mutually exclusive | 2026-11-01 | `9e58f1d90fdad8fefa771b946ebb987d615012f20899ab1c0d0f80fc90eb615c` | MIT | read |
| AP-11 | AP-01 | module documentation | `df69a6a4` | `src/modules/GenericPropagation/README.md` lines 55-69: `temperature` default 293.15 K, `mobility_model` default `jacoboni`, `propagate_electrons` default true, `propagate_holes` default false | 2026-11-01 | `6be3d01f9383326ae5ed8117ec25c3712154cd84b8513dd378254250e115eef2` | MIT | read |
| AP-12 | AP-01 | module documentation | `df69a6a4` | `src/modules/DefaultDigitizer/README.md` lines 69-86: `threshold` required; `threshold_smearing` default 30 e; `electronics_noise` default 110 e; `qdc_resolution` and `tdc_resolution` default 0 (charge in electrons, time in ns) | 2026-11-01 | `601181688dc4201d216260a83c1a326314c4ad68082fae1901cf49b7d95459bb` | MIT | read |
| AP-13 | AP-01 | object source | `df69a6a4` | `src/objects/PixelCharge.cpp` line 72 `getCharge()` returns the signed `long` charge; line 74 `getAbsoluteCharge()` returns its absolute value | 2026-11-01 | `6b83dff40ff99458ec60c21da5dc0eb8fd51bbfd87f835a34ffacd70396867d7` | MIT | read |
| AP-14 | AP-01 | module documentation | `df69a6a4` | `src/modules/PulseTransfer/README.md` lines 20-40: without pulse information from propagation, a pulse is built from carrier arrival times (`timestep`, `max_depth_distance` default 5 µm, `collect_from_implant`) and "does not represent a time-resolved simulation of the signal formation" | 2026-11-01 | `37da1b78d59188916f18bdb220d3155a43c1800ffb38ead425d41269b1a25b38` | MIT | read |
| AP-15 | AP-01 | module documentation | `df69a6a4` | `src/modules/TransientPropagation/README.md` lines 5, 27: induced charge per step via the Shockley-Ramo theorem from a weighting potential | 2026-11-01 | `02f3cbe3b7d8aeefd6b7bd931bb13635321e6383c056cf7e315676335fcc07d1` | MIT | read |
| AP-16 | AP-01 | manual page (source) | `df69a6a4` | `doc/usermanual/02_installation/02_prerequisites.md`: ROOT 6 built with C++20 (GenVector), Boost.Random >= 1.64.0, Geant4 built with C++20 and **all data sets**, multithreading enabled in Geant4 for MT runs, Eigen3 | 2026-11-01 | `f2d7744ba7d9b18715e02cd98e10991ec3d544ddf746df814a7056cfa515b4b9` | CC-BY-4.0 | read |
| AP-17 | AP-01 | manual page (source) | `df69a6a4` | `doc/usermanual/02_installation/01_supported_systems.md`: recent Linux or macOS; CI on CentOS 7, AlmaLinux 9 / RHEL 9, Ubuntu 22.04 (Docker), macOS 10.15; C++20 compiler (GCC 11+, Clang 10+, AppleClang 13+) | 2026-11-01 | `51839add9b93754497862e0f781d4066975ad6be7f5e2acf26c2cc9d92e1b3a7` | CC-BY-4.0 | read |
| AP-18 | AP-01 | manual page (source) | `df69a6a4` | `doc/usermanual/02_installation/07_docker_images.md`: image `gitlab-registry.cern.ch/allpix-squared/allpix-squared[:<tag>]`, host folder mounted at `/data` | 2026-11-01 | `571293e62765d11cf1cd21c3de60e5991d1ddfbb1eaeca6dc6b339d7973b8154` | CC-BY-4.0 | read |
| AP-19 | AP-01 | manual page (source) | `df69a6a4` | `doc/usermanual/02_installation/08_cvmfs.md`: `/cvmfs/clicdp.cern.ch/software/allpix-squared/<version>/<system-specifier>/setup.sh`; binaries for CentOS 7 (GCC) and EL9 (GCC, LLVM) | 2026-11-01 | `7b73a6685e5c3ac0bbec7e5317d7026d38fb7b984de744f6540d01c8ff02f3a9` | CC-BY-4.0 | read |
| AP-20 | AP-01 | build script | `df69a6a4` | `CMakeLists.txt` line 187 `FIND_PACKAGE(ROOT REQUIRED COMPONENTS Geom Core GenVector Hist RIO ...)`, line 326 `FIND_PACKAGE(spdlog 1.9.2 REQUIRED)`, line 329 `FIND_PACKAGE(Boost 1.64.0 REQUIRED COMPONENTS random)` | 2026-11-01 | `acc913de958569901568655cfad57905cbc2c66b9ba74b7a134e9c459326ae1e` | MIT | read |
| AP-21 | AP-01 | build script | tag `v3.3.0` (`8d570fdd`) | `CMakeLists.txt`: no `spdlog` requirement; line 321 `FIND_PACKAGE(Boost 1.64.0 REQUIRED COMPONENTS random)` | 2026-11-01 | `ae92581c0e508d964d5abe7724f6618cc1008d78c0d0f12bbb7c68bce5726c8b` | MIT | read |
| AP-22 | AP-01 | licence | `df69a6a4` | `LICENSE.md` (MIT) and `LICENSES/` (BSD-3-Clause, BSL-1.0, CC-BY-4.0, CC0-1.0, MIT) | 2026-11-01 | `9898a1a7c613c178c8ab875a12ab59093d888e944cf47408a3aab3198200cdc1` | MIT | read |
| AP-23 | AP-01 | tools | `df69a6a4` | `tools/mesh_converter/` (TCAD mesh to field-map conversion), `tools/weightingpotential_generator/` (directory listing only) | 2026-11-01 | `9a180be45e63be9f1c429f7628abd10866387db61d6960e838de7f5d6b3e03ac` (`ls-tree tools/`) | MIT | read-partial |
| AP-24 | AP-01 | module documentation | `df69a6a4` | `src/modules/ElectricFieldReader/README.md` lines 17-81: `model` = `linear`, `constant`, `parabolic`, `custom` (analytic) or `mesh` (map read from file) | 2026-11-01 | `f5d99b2556b5dd72fb5a6099c63de6a9294120fc8e21d3a39b9d10eedd081c2c` | MIT | read |
| AP-25 | AP-01 | CI configuration and developer manual | `df69a6a4` | `.gitlab-ci.yml` lines 581-596 (`deploy:cvmfs`, schedules: `BUILD_PATH='latest'`) and 614-620 (`deploy:docker-latest`); `doc/usermanual/11_devtools/05_building_docker_images.md` lines 8-11 (nightly `latest` image from master); hash of the two files concatenated | 2026-11-01 | `fd59c2967bece026f712b6709bf7bc6f5c74ba1dc8cf019a4fcb8e205123627b` | MIT | read |

## Allpix Squared — official web documentation

| ID | URL | Type | Version | Section | Retrieved (UTC) | Content hash (SHA-256 of bytes returned) | Licence | Review status |
|---|---|---|---|---|---|---|---|---|
| AW-01 | `https://project-allpix-squared.web.cern.ch/usermanual/allpix-manual.pdf` | user manual (PDF, 2,531,385 bytes) | title page: "Version v3.3.0", 2026-10-01 | title page only | 2026-11-01T12:06Z | `a340caaf1b167d1967343e6e795bd4c926e3a615bb8617987bbf3b5ceda1a385` | CC-BY-4.0 (manual) | read-partial |
| AW-02 | `https://allpix-squared.docs.cern.ch/docs/03_getting_started/04_framework_parameters/` | web manual | live site (version not stated on the page) | Framework Parameters | 2026-11-01T12:06Z | `0c7693bf0cc8c41557485093642a205f86b8f38c06a179790dbcfc0165009ea4` | CC-BY-4.0 | retrieved-not-used |
| AW-03 | `https://allpix-squared.docs.cern.ch/docs/04_framework/10_multithreading/` | web manual | live site | Multithreading, Seed Distribution | 2026-11-01T12:06Z | `7f51cfd15ffec476618f3139c0734523e54b669212aa13974e603477029848fd` | CC-BY-4.0 | retrieved-not-used |
| AW-04 | `https://allpix-squared.docs.cern.ch/docs/08_modules/rootobjectwriter/` | web manual | live site | ROOTObjectWriter | 2026-11-01T12:06Z | `71729752bb6d7ab06ed1167d7426fdf6cdfdfe83eb23d4a2b5fec83f7bbbb435` | CC-BY-4.0 | retrieved-not-used |
| AW-05 | `https://allpix-squared.docs.cern.ch/docs/01_introduction/04_quick_start/` | web manual | live site | Quick start | 2026-11-01T12:06Z | `10466165201cee33b7a2321ada9d0380d9eaed176e5728cec590c3e3211afae9` | CC-BY-4.0 | retrieved-not-used |
| AW-06 | `https://allpix-squared.docs.cern.ch/docs/02_installation/07_docker_images/` | web manual | live site | Docker images | 2026-11-01T12:06Z | `9c34ce871fd2c710a93a7111953ac0cc9a9fb0dddb50b4148b9cbdb7b696ede1` | CC-BY-4.0 | read |
| AW-07 | `https://allpix-squared.docs.cern.ch/docs/02_installation/08_cvmfs/` | web manual | live site | Releases on CVMFS | 2026-11-01T12:06Z | `ff5cc97a165722a7f3b31cb4fe15689ef4dd92a58c2aea78f0ea778ff6777e80` | CC-BY-4.0 | read |

## Garfield++ — repository files (commit `e2e58ea7` unless stated)

| ID | Repository | Type | Version or commit | Section / symbol / lines | Retrieved | Content hash (SHA-256) | Licence | Review status |
|---|---|---|---|---|---|---|---|---|
| GF-01 | `https://gitlab.cern.ch/garfield/garfieldpp.git` | source repository | `e2e58ea7` (master, `2026.10-4`) | whole tree | 2026-11-01 | `6b316b702c724d371f47d235604d9b1322c2166775131ec5c50fd9cb33376590` (`ls-tree -r`) | not stated (no licence file at the root) | read-partial |
| GF-02 | GF-01 | source | `e2e58ea7` | `Source/MediumGas.cc`: `UpdateScaling` 150-163 (density ratio `(p_table/T_table)·(T/p)`, line 156); `LoadGasFile`: lines 555-556 set pressure and temperature from the file; line 560 E/p × p (Torr); 563-577 diffusion ÷ √p, Townsend and attachment logs + ln p; 590-612 interpolation and extrapolation settings taken from the file (velocity: 592, 604); line 671 `Dimension` header; lines 477-483 record dispatch (`ReadRecord3D` when the table has B/angle grids, else `ReadRecord1D`); `ReadRecord1D` 837-850 reads each quantity followed by a discarded column (`ve, waste, vb, waste, vx, waste`, …) and converts velocities cm/µs × 1e-3 at 848-850; `ReadRecord3D` 786ff, velocity conversion at line 796 | 2026-11-01 | `87d791b371fb780c5aa83b06cc7ec50896d8a05529724b639331a6c60cbee309` | not stated | read |
| GF-03 | GF-01 | source | `e2e58ea7` | `Source/Medium.cc`: `Velocity` 205-238 (scaled field `e0`, B < `Small` branch 232-238: `v = (q·v_E/|E|)·E`); `ElectronVelocity` 490-495 (`q = −1`); `SetExtrapolationMethodVelocity` 1291; `SetExtrapolationMethod` 1321-1339 and `GetExtrapolationIndex` 1341-1356: the setters take strings `CONST`/`CONSTANT`, `LIN`/`LINEAR`, `EXP`/`EXPONENTIAL` (case-insensitive), mapped to 0/1/2; an unknown string prints an error and leaves that side unchanged; `SetInterpolationMethodVelocity` 1381 (ignores 0); `Interpolate` 1419-1437 (`Boxin3` for 3D tables, `Interpolate1D` otherwise); `Interpolate1D` 1439-1542 | 2026-11-01 | `ca8c2c0161ae5f75b234c6bdb366f0a5ffce1c2892fcf855b92b7c2e33b611b2` | not stated | read |
| GF-04 | GF-01 | source | `e2e58ea7` | `Source/Numerics.cc`: `Divdif` 1658-1754 (CERNLIB E105 port; effective order `min(order, 10, n−1)`; node order ix, ix+1, ix−1, ix+2; averaging of the two highest differences for even order when `m+2` nodes are inside the table; end-node return within 1e-6 of the end spacing); `LinearInterpolation` 1756 | 2026-11-01 | `69ebdb4f9b781e83c802b1f7ac094bc37546f0180e78a160aac5ac774b93fd44` | not stated | read |
| GF-05 | GF-01 | header | `e2e58ea7` | `Include/Garfield/Medium.hh`: compiled defaults line 770 `m_extrVel = {0, 1}` (constant low, linear high), line 779 `m_intpVel{2}`; line 621 base `ScaleElectricField` returns `e` | 2026-11-01 | `e64e9aa9e4eae0783c17d5491a767dcff38ccd275787e8abc782a51cd8fc06b0` | not stated | read |
| GF-06 | GF-01 | header | `e2e58ea7` | `Include/Garfield/MediumGas.hh` lines 150-152: `ScaleElectricField(e)` returns `e * m_densityRatio` | 2026-11-01 | `1e7197d159a122a2420234391f7efb628e5ea0a5caead09520dab5b8ccf708f6` | not stated | read |
| GF-07 | GF-01 | example gas table | `e2e58ea7` | `Examples/GasFile/ar_80_co2_20_0T.gas`: created 30/11/12, `Version : 12`, `Identifier: CO2 20%, Ar 80%, T=300 K, p=1 atm`, `Dimension : F 30 1 1 ...` (1D, 30 E points, first E/p 0.13157895 V/(cm·Torr)), `H Extr: 1 ...`, `L Extr: 0 ...`, `Interp: 2 ...`, `PGAS = 760`, `TGAS = 300` | 2026-11-01 | `ba4357348c211812b40f982b979df34bf02738855ee6a1ba58555c35d196b732` | not stated | read |
| GF-08 | GF-01 | user guide (LaTeX source) | `e2e58ea7` | `Doc/UserGuide/Media.tex` lines 186-220: Newton-polynomial interpolation, order 1 to `min(10, n−1)`, orders above 2 not recommended; extrapolation `"constant"`, `"linear"`, `"exponential"` per side, for 1D tables only (3D: polynomial of the interpolation order); default quadratic interpolation, constant low, linear high; lines 555-560 `LoadGasFile`, format compatible with Garfield 9 | 2026-11-01 | `be8ed70f9e9147e5d176303a76f3e3ffc9e6f95ae8a9409bd2b85808b2fe98c9` | not stated | read |
| GF-09 | GF-01 | user guide (LaTeX source) | `e2e58ea7` | `Doc/UserGuide/Installation.tex`: prerequisites ROOT 6, CMake >= 3.12, C++ compiler with ROOT's standard, Fortran compiler, optional GSL and OpenMP; `setupGarfield.sh` in `share/Garfield` sets `HEED_DATABASE` and `CMAKE_PREFIX_PATH`; Python through PyROOT (`import ROOT`, `import Garfield`) | 2026-11-01 | `9d7bbaca2c4b49d21fe6502d1d23db40eb7a636f9ab1a6ffa5ffc7a8abdffcf2` | not stated | read |
| GF-10 | GF-01 | readme | `e2e58ea7` | `README.md`: CMake build options, `setupGarfield.sh`, Python examples with `python3 -i` | 2026-11-01 | `254495ac1476cea096abde9241d0468e539fa533e90851aaf17317e7df8b17e0` | not stated | read |
| GF-11 | GF-01 | build script | `e2e58ea7` | `CMakeLists.txt` line 5 `project(Garfield VERSION 0.3`; line 94 `find_package(ROOT 6.0 REQUIRED COMPONENTS Geom Gdml MathCore)`; line 97 a compatibility branch for ROOT < 6.20 only | 2026-11-01 | `f4bc8a91c8061996f44ee296a40502f307285f5729cbb99e206101265a751f05` | not stated | read |
| GF-12 | GF-01 | headers (listing) | `e2e58ea7` | `Include/Garfield/`: `ComponentTcad2d/3d`, `ComponentComsol`, `ComponentElmer`, `ComponentAnsys121/123`, `ComponentAnalyticField`, `ComponentNeBem2d/3d`, `AvalancheMC`, `AvalancheMicroscopic`, `TrackHeed`, `Sensor` (existence only) | 2026-11-01 | `8a88dd00f70609f0c16fac2b738b2e40a89d5e391c90a70d617d9feefbb31ffa` (`ls-tree Include/Garfield/`) | not stated | read-partial |

## Garfield++ — official web documentation and other pages

| ID | URL | Type | Version | Section | Retrieved (UTC) | Content hash (SHA-256 of bytes returned) | Licence | Review status |
|---|---|---|---|---|---|---|---|---|
| GW-01 | `https://garfieldpp.web.cern.ch/doxygen/UserGuide.pdf` | user guide (PDF, 804,810 bytes) | "Version 2026.1, July 2026" (title page) | 3.1.1 Transport parameter tables: Newton polynomials; default quadratic, constant low, linear high | 2026-11-01T12:06Z | `7b62d761831d91c7fde611c6dbc3dc5e13b2d587fc7a4190ddb99f97050db1c0` | not stated | read-partial |
| GW-02 | `https://garfieldpp.docs.cern.ch/tutorials/gasfiles/` | tutorial | live site | Gas files: `LoadGasFile` sets composition, pressure and temperature; changing the pressure afterwards scales by "very approximate" laws, not recommended | 2026-11-01T12:06Z | `100b9435faa0216e6b4ec2efa9b291a45eec8166f181db766ef48f14fd67ca15` | not stated | read |
| GW-03 | `https://garfieldpp.docs.cern.ch/doxygen/classGarfield_1_1Medium.html` | API reference | live site (doxygen of the current master) | class `Medium` | 2026-11-01T12:06Z | `77bf72c9908372349f3cf8be183e616430d9520300f9598b7e0d14fe19b152fb` | not stated | retrieved-not-used |
| GW-04 | `https://garfieldpp.docs.cern.ch/doxygen/MediumGas_8hh_source.html` | API reference | live site | `MediumGas.hh` | 2026-11-01T12:06Z | `e8cc55b0e1320d621251366fa615731f55ecb8cc76b1e288d638fb9c1dbc141a` | not stated | retrieved-not-used |
| GW-05 | `https://lcginfo.cern.ch/pkg/Garfield++/` | LCG package index | live site | releases list (newest named LCG releases 110a, 110, 109a, 109, 108a, 108, plus dev, SWAN and experiment-specific variants); versions listed as commit abbreviations, none mapped to a Garfield++ tag on that page | 2026-11-01T12:06Z | `6d7036eaccf9d7da6039e78de7dd06eaf28389542887e527d78356a036e8a13c` | not stated | read |
| GW-06 | `https://drd1.web.cern.ch/garfield/` | collaboration page | live site | Garfield page | 2026-11-01T12:06Z | `d4f241d0677a24e7d8bde31bcfa2d8cc54c0b55405adba5ecd5fb4a8914547fc` | not stated | retrieved-not-used |
| GW-07 | `https://root-forum.cern.ch/t/garfield-simulation-taking-a-lot-longer-to-finish-after-update/63508` | forum thread | unknown version | copies of `Medium.cc` / `Medium.hh` | 2026-11-01T12:32Z | `391f473b4b04e723f830b006e91513538c1e1096ae5ac53fc75443719179b10d` | forum terms | lead-only |

## hep-research (the task's own specification and repository)

| ID | Path (plugin root) | Type | Version | Section | Retrieved | Content hash (SHA-256) | Licence | Review status |
|---|---|---|---|---|---|---|---|---|
| H-01 | `docs/dev/detector-simulation/TASK.md` | task specification | 9.1 (2026-11-01), base `e480371c` | §1.4, §6, §10-§12, §14.2, §15.1, §16.2, Appendix A | 2026-11-01 | `a178647965af3ad7871099c01f1bd4a9d5f329307c98451e0af0723bfc635953` | repository | read |
| H-02 | `docs/dev/detector-simulation/PROGRESS.md` | ledger | base `e480371c` | W1 decisions D-W1-1 … D-W1-5, environment availability | 2026-11-01 | `7a9d06a2d1bc38f9cfc3d4c6d5e75178d2270e400cc757e02773b3000aae5351` | repository | read |
| H-03 | `core/status.py` | code | base `e480371c` (plugin 0.53.0) | exit codes 0-3, `_NO_ARTIFACT` | 2026-11-01 | `a4609ec692ef083df49898e401d0651cd94446928c110747396a60746fc79246` | repository | read-partial |
| H-04 | `adapters/environments/` | adapter | base `e480371c` | `lcg_view_setup.sh`, `hep-research.def`, state `documented` | 2026-11-01 | `d5dae5844daa140a83d7be6ee57688902bad3fbe8d99bd79d8c05ea8f2139af1` (`adapter.json`) | repository | read |
