# T15b: the K16 `element_sim` sample spec

**State: DRAFT for the user's freeze by hash.** Freeze A leaves this spec out and says it is frozen by hash before T15b (`freeze-a.md`,
"Not in this freeze"; `t04-values-v4.md` section 13). The user's word of 2026-11-13, "Draft spec, digitization off (Recommended)", asked for
this draft (to be recorded verbatim in `decisions.md` before the freeze is asked). It is not frozen, and no T15b result exists. It is a
new spec outside `t04-values-v4.md` section 3.2, not an amendment of Freeze A. Once frozen, a change to this text is a section 2.3
amendment. Fix round 1 (`jobs/gate-d/T15B-REVIEW.md`, 6 Important, 10 Minor, all adopted) is applied.

Each value below names its source. "Choice" means no source fixes the value. It is proposed here and becomes binding only through the
user's freeze. Numbers marked "derived" are computed from the sources named, with the computation given.

## 1. What the sample is for

| Item | Value | Source |
| --- | --- | --- |
| Use | K16's paired comparison of two `simreco` pattern-recognition configurations, with A50, A51 and A53, on the T03 two-candidate domain | Plan R19; `t03-selection.md`, "Two-candidate domain"; `t04-values-v4.md` section 13 |
| Population | One shared sample; every candidate and the comparator read the same events | Section 13, "Event sample", "Comparison: paired events, one population and denominator" |
| Development results | None enter. The block-1 pilot (`jobs/gate-d/t15b-pilot.sh`) is a cost and pipeline reading. It sets no value here | Section 13, "No development results enter" |
| Claim | None beyond the declared baseline and the tested domain (simulated `element_sim` events on an invented geometry). Without confirmation data, no post-selection quality claim (K18 default). With digitization off, a pass of the fake gate carries no evidence about robustness to noise hits, and the two windows will rarely see different hits, so the comparison rests mostly on CPU (section 6) | `decisions.md` K16, K18; `t03-selection.md` row 2; review M3 |

## 2. Geometry, physics and field

| Item | Value | Source |
| --- | --- | --- |
| Geometry | J15 `cand-N6`, the element spec `examples/design-minimal-spectrometer/recorded/artifacts/specs/N6-TRK100-nominal.spec.json` with its `world`, `elements`, `field`, `physics`, `output` and `provenance` unchanged; this spec sets `source`, `run` and `note`. That is six 0.3 mm silicon planes over 0.80 m in 0.5 T, two TOF stations (TOF1's two 10 mm PVT layers at x = -805 and -785 mm, before Si1 at -500 mm), and a 50-layer Pb/PVT calorimeter | Choice. J15 is one of the `element_sim` geometries with recorded `simreco` studies (J16's `examples/design-search-j16` is another); it has a validated-in-scope 1 GV point and `cand-N6` is its nominal candidate (`examples/design-minimal-spectrometer/README.md`). The file at this branch: SHA-256 `30ec3251c84b8464f39dac7f42765bd6430d26e5970023a71f472ab3fe0c038f` |
| Physics | `FTFP_BERT_EMZ`, default cut 0.7 mm, as that spec | The same file |
| Label | SYNTHETIC: an invented geometry that represents no experiment | `examples/design-minimal-spectrometer/README.md`, first line |

## 3. Source: species, charges and rigidity

| Item | Value | Source |
| --- | --- | --- |
| Species | `proton` (positive) and `anti_proton` (negative): one run per charge, same mass, opposite charge | Choice. J15's tracking requirements use protons (README, `REQ-TRK-001`, `-002`). The antiparticle gives the second charge at equal kinematics. `simreco`'s particle table carries both (`simreco_spec.py`, `particle_table`: antiparticles at `-pdg`) |
| Gun | J15's: position (-1000, 0, 0) mm, direction (1, 0, 0) | The spec file of section 2 |
| Rigidity range | 1 to 50 GV | Choice, bounded by section 13's condition (section 5 below). 1 GV is J15's validated-in-scope point (README, F4 table: N6 at 1 GV `validated-in-scope`) |
| Rigidity values | `source.cycle` of 1,000 entries. Entry `k` (0 to 999) has rigidity `R_k = 1 GV x 50^((k + 0.5)/1000)`, a deterministic log-uniform grid. Kinetic energy `sqrt(R_k^2 + m_p^2) - m_p` (charge 1, GeV), with `m_p` 0.93827208943 GeV from `core/constants`. Direction (1, 0, 0). Event `i` uses entry `i mod 1000` | Choice of grid. The mechanism is `element_sim`'s only multi-energy gun: `source.cycle`, at most 1,000 entries, entry `i mod n` (`element_sim/spec.schema.json`, `source.cycle`; `element_sim/Actions.cc` line 399). The schema has no continuous spectrum: `gps` and `event-file` are interface only, exit 2 |
| Derived | First entry 1.00196 GV (434.4 MeV). Last 49.902 GV (48,972.8 MeV). Mean kinetic energy 11.69 GeV | Computed from the grid |

## 4. Bins and size

| Item | Value | Source |
| --- | --- | --- |
| Bins | 4 true-rigidity bins at the generator's equal-population quartiles. Bin `j` (0 to 3) holds entries `250 j` to `250 j + 249`. Edges 1, 2.6591, 7.0711, 18.803 and 50 GV (`50^(j/4)`), each strictly between two grid values | Section 13, "4 true rigidity bins at the generator's equal-population quartiles, a function of truth". The edges are derived from the grid |
| Bin of an event | **By the cycle entry only**: entry `event mod 1000` (with `first_event` 0 and consecutive events), bin `entry div 250`. The entry is the generated (true) rigidity, so this is "a function of truth" | Section 13 ("a function of truth"); `element_sim/Actions.cc` line 399 |
| `rig_true_GV` is not the bin variable | `simreco` writes `rig_true_GV` as `1/mean(1/p_i)` over the primary's entries into the tracker planes (`simreco.cc` lines 371-384), after TOF1's 2 x 10 mm PVT. It sits below the generated value: about 0.8 % at 1 GV. A primary that interacts before Si1 has `n_true_planes` 0 and `rig_true_GV` 0. Pilot job 7627120 (block 1, 2,000 events per species) showed it: entries 0-4 read -0.82 % (proton) and -0.85 % (anti_proton) on average; 49 (proton) and 58 (anti_proton) events have no true plane; 4 more per species fall in another bin by `rig_true_GV`. These counts are reported as a reading, never used to bin | `simreco.cc` at this branch; review I1; job 7627120's results (development reading) |
| Size | 12,000 events per bin per charge. Per charge one run of 48,000 events (entries 0 to 999, 48 times each), so each bin gets exactly 12,000. In total 96,000 events | Section 13, "12,000 events per bin per charge"; derived |
| Test budget | 4 bins x 12 tests x 2 candidates = 96 tests, `alpha` 1.04e-4, `z1` 3.71 | Section 13, "Budget" |

## 5. The top-edge condition

Section 13: "The spec must keep `rho_sigma/|rho|` at most 0.1 at the top bin's upper edge, from truth, or that bin is ungated with the
obligation open."

| Item | Value | Source |
| --- | --- | --- |
| Closed form at 50 GV | 0.047. Derived: J15's F1 terms for `cand-N6` at 100 GV are an exact least-squares measurement term of 8.5 % and multiple scattering of 1.9 % (README, F1 table). The measurement term scales with rigidity and the scattering term is constant at beta near 1: `sqrt((0.085 x 50/100)^2 + 0.019^2)` = 0.0466 | J15 README, rows "MDR" and "`cand-N6` resolution at 100 GV, F1"; derived |
| Geant4 reading in this configuration | With every tail source off, as here, the refused (`unvalidated`) 100 GV Geant4 study reads 8.6 % for `cand-N6`, against F1's 8.7 %. Scaled the same way, about 0.043 at 50 GV. (The 10.5 % of the README's F4 table is the all-tails-on value, which this sample does not use.) | README, "In the refused 100 GV studies (`unvalidated`) they widen it from 8.6 % to 10.5 %"; derived. A reading, not a validation |
| Why 50 GV, not 100 GV | At 100 GV both values (0.086 Geant4, 0.087 F1) sit under 0.1 with less than 15 % margin, on a study that was refused; and the result there rests on the declared 10 um point resolution, "which no benchmark validates, and above about 20-30 GV it dominates". At 50 GV the margin is more than a factor 2. 50 GV stays a Choice | README, F4 discussion; Choice |
| Check in the sample | Reported: the median of `rho_sigma x 50 GV` (the fit's predicted relative width, scaled to the edge since the measurement term is linear in R) over selected comparator tracks of entries 975-999 (45.5 to 49.9 GV). If it exceeds 0.1, bin 3 is ungated with the obligation open, as section 13 says. Pilot 7627120 read 0.045 for both species (development reading) | Section 13; `simreco` columns `rho_sigma`; Choice of subset and statistic |

## 6. Tail sources: noise-digitization off, and why

| Item | Value | Source |
| --- | --- | --- |
| `noise-digitization` | **Off** | The user, 2026-11-13: "Draft spec, digitization off (Recommended)" |
| Why | This branch's `simreco.cc` (SHA-256 `e5ea011e...`, base 0.58.0) computes a digitized hit's error with `StripSigma`. Upstream e0a10d44 (plugin 0.61.0) found it 5 % to 72 % too small, about 14 % on J15's bending strips (chi2/ndof 1.197 against 1.001) and replaced it with `StripClusterSigma`. With digitization on, section 13's `rho_pull` width gates would test known-wrong errors. With it off, a hit carries the reco spec's nominal Gaussian errors (`simreco.cc` lines 428-432: `h.y = yt + s.sigma_y_mm * rng.Next(); h.sigma_y = s.sigma_y_mm`), and `StripSigma` (lines 259-262, the formula e0a10d44 replaced, used only in the digitized branch, lines 426-427) does not enter | `t15b-assessment.md`; upstream commit e0a10d44's message (0.61.0, not an ancestor of this branch's base); `simreco.cc` at this branch |
| Consequence | No noise hits, threshold or efficiency loss. Fakes come only from other charged tracks' hits (delta rays, back-splash), which pattern recognition still sees ("hits of every charged track", `simreco.cc` header). A fake rate near 0 is expected (pilot 7627120: 0 to 1 per 500-event bin). The fake gate stays and its result is reported as it falls, but a pass carries no evidence about noise hits. With 10 um hits and multiple-scattering residuals of about 0.1-0.2 mm at 1 GV, the 1.0 and 0.5 mm windows will rarely select different hits (pilot: identical selections in every bin), so the tie rule is likely to keep `simreco-pr-a` as the "qualified default choice" | `simreco.cc` header comment; section 13 fake gate and tie rule; review M3 |
| `alignment`, `calibration-non-uniformity` | Off | Choice. Section 13 names only pattern recognition. Both are random per replica and need at least 20 replicas (`simreco_spec.py`, `MIN_REPLICAS`), which would multiply the paired cost and change the denominator |
| `pattern-recognition` | On for the candidates, off for the comparator | Section 13, "Candidates", "Comparator" |
| Replicas | 1 | Follows from the two tails off (`simreco_spec.py`, `REPLICA_TAILS`) |

## 7. The candidates and the comparator

All three use one reco spec, identical outside `tail_sources.pattern-recognition`: J15's
`examples/design-minimal-spectrometer/recorded/artifacts/specs/N6-TRK1-nominal-off.reco.json` (point resolution 10 um bending, 30 um
non-bending; `G4_Si` radiation length 93.7 mm; TOF 100 ps), which has no `tail_sources` (all off) and one replica; SHA-256 `b49ea75da6efe582c3a3efe585af65ba17c2db59e74119112759f44aa88517be`. Choice: it was written for J15's 1 GV studies, while the geometry file is the 100 GV one; their elements are identical, and only the observables' binning differs. Its `output` (J15's observables, 16 blocks of 800 events) is dropped, since K16 reads the per-event CSV and the blocks would mislabel a 48,000-event run. `replicas` 1 is set, and `tail_sources.pattern-recognition` is added for the candidates.

| Name | `pattern-recognition` | Source |
| --- | --- | --- |
| `simreco-pr-a` | on, `window_mm` 1.0, `chi2_per_ndof_cut` 50, `min_hits` 4 (the code defaults) | Section 13; `simreco.cc` line 80 (`pr_window_mm = 1.0, pr_chi2_cut = 50, pr_min_hits = 4`) |
| `simreco-pr-b` | on, `window_mm` 0.5, otherwise as `-pr-a` | Section 13 |
| Comparator | off: the primary's own plane entries | Section 13, "Comparator"; `simreco.cc` header |

## 8. Pairing

| Item | Value | Source |
| --- | --- | --- |
| Events | One `element_sim` run per charge, at `crossings` level. Every candidate and the comparator reconstruct the same event file through `geant4_run.py reco` | Section 13; `geant4_run.py` `cmd_reco` |
| Random numbers in `simreco` | The same logical-run seed `S` in every reco, so event `i`'s stream `H(S, i, "digi")` starts the same. The two candidates see identical hits. The comparator shares the draws exactly only in events whose tracker crossings are all the primary's: with pattern recognition off, non-primary crossings are skipped before the Gaussian draw (`simreco.cc` line 389), so a secondary on an earlier plane shifts the stream for the primary's later hits. Validity is unaffected (same events, same denominator); only the comparator pairing's variance reduction is lower | `simreco.cc` header and line 389; review M1 |
| Unit | The event, paired by `event` number. Denominator: particles with at least 4 true planes (`n_true_planes` at least 4) | Section 13, "Efficiency" and "Comparison" |
| CPU: mechanism | Section 13's rule, by event-range reconstruction from one dump: per charge, `simroot dump events.root --ntuple crossings` once; the crossings and `events.csv` are split by event into chunks of 100 (chunk `c` holds events `100 c` to `100 c + 99`; 480 chunks per charge); per chunk, `simreco` runs once per configuration from the whole-run reco's effective spec with only its file paths changed. In even chunks `simreco-pr-a` goes first, in odd chunks `simreco-pr-b`, and the comparator runs last. Each process's user plus system time is recorded. Chunk 0 is the cold chunk, reported apart. Per-event timing is not available, so the chunk is the unit, as section 13 allows. The merged chunk results must equal the whole-run results row for row, or the measurement is void | Section 13, "CPU measurement"; `simroot.cc` (`dump`), `geant4_run.py` `cmd_reco`; the step is `jobs/gate-d/t15b_pilot_tools.py chunks` |
| CPU: layout and boundary | Files: one `events.root` and `events.csv` per charge (the sample); per chunk a crossings file, an events file, one results CSV per configuration (temporary, hashed by the job); the merged results per configuration. "I/O included": each process's own reading of its chunk files and writing of its results is inside its time. The dump is common to all three and is reported apart, not charged to a candidate (Choice). A failed event costs what its process spent on it | Choice; section 13, "Objective" |

## 9. Seeds and block

| Item | Value | Source |
| --- | --- | --- |
| `fixture_id` | 1601 | Choice. v4 section 3.2's table has T07 7001-7004, T08 8001-8004 and T09 9001-9004. 1601 (K16, first fixture) is unused |
| Seed form | `element_sim` seeds per event only: logical-run seed `S` and event `i`'s pair `(H(S, i, 0), H(S, i, 1))`, with `run.seeds` the job seeds of `S` at `first_event` (`core/simulation/seeds.py`; `element_spec.py` line 215). The proposal is `S = H("t15b-k16-1601", "block-<b>", "<species>")` with `H` from `core/simulation/seeds.py` | Section 3.2 asks for `(fixture_id, block, stratum, event_index)`. `element_sim` cannot take that form. Fixture, block and species enter `S`, and the event index enters per event. The stratum is a function of the event index (`event mod 1000`), so `(fixture, block, stratum, event)` is covered. A departure from v4 3.2's wording, proposed for `deviations.md` and asked as its own question (section 11) |
| Blocks | v4 section 3.2 assigns no block to T15b. Choices outside section 3.2, not an amendment of it: **21** the frozen sample (attempt 1); **22** an attempt 2; **23** reserved for K18's confirmation sample (plan 14.5, "Data roles"), drawn only on the user's word. Blocks 2-6, 11 and 12 are avoided because T07-T09 use them; T15b's events would not share a stream with theirs anyway (a different hash on different inputs), but a separate number keeps the records unambiguous | Choice; v4 3.2; review I3 |
| Pilot | Block 1, the tuning role ("any size within approved jobs"), with this spec's own seed form, so no T07-T09 stream is drawn | Section 3.2 (role by analogy) |
| Attempts | At most 2: attempt 1 on block 21, attempt 2 on block 22 only after a recorded method change and the user's word. A failure stands. An inconclusive attempt counts | Choice, after v4 3.4 |
| Repeats | A reconstruction that crashes for infrastructure reasons may be repeated on the same event file: it draws nothing. A lost event file is regenerated from the same `S`. Per-event seeding gives the same events bit for bit, independent of the thread count, and the content hash against the run record is checked before any reconstruction. That is not a new draw. Any other repeat is the user's | `VALIDATION.md` per-event invariance row (J15: serial, MT 2 and 4, jobs of 10 events, identical `content_sha256`); `geant4_run.py` `cmd_reco` content check; Choice |
| Generator check | None (Choice), unlike T07-T09's block-6 checks. The run record's `content_sha256`, `spec_sha256` and seeds (`geant4_run.py run`) identify the sample, and `reco` refuses an event file whose content hash differs | Choice; `geant4_run.py` `cmd_reco` |

## 10. Programs

| Item | Value | Source |
| --- | --- | --- |
| `simreco` | Built from this branch's `adapters/geant4/assets/simreco/` (C++17, no Geant4) by `geant4_run.py build-sim --program simreco`. The binary's SHA-256 is recorded and frozen with the sample | `simreco/CMakeLists.txt`; `t15b-assessment.md` |
| `element_sim`, `simroot` | Built from this branch by `build-sim --program element_sim --configure-with geant4-config` against the registered Geant4 11.4.3 (conda-forge), the route GEANT4-REGISTER recorded on this host class | `VALIDATION.md` GEANT4-REGISTER |
| Threads | 4, MT (Choice; `per-event` seeding makes the events independent of the thread count) | `VALIDATION.md` per-event invariance row (J15, serial, MT 2 and 4) |

## 11. Open for the user at the freeze

1. This spec as a whole, by hash: the geometry and reco file hashes, species, range, grid, `fixture_id`, blocks 21, 22 and 23, attempts, the
   CPU mechanism and its boundary (section 8).
2. The seed form of section 9, a departure from v4 3.2's `SeedSequence` wording, as its own answer.
3. Whether to accept that, with digitization off, this sample cannot test pattern recognition against noise hits, and that the comparison
   will rest mostly on CPU (sections 1 and 6).
4. The K16 reading: that the user's acceptance of section 16 (2026-11-06), with section 13 inside Freeze A, gives K16's hard gates and
   quality objective (R02), leaving this spec as the only open K16 item (`t15b-assessment.md`).
5. The full run's resources (K10, K17). Development readings from pilot job 7627120 (block 1; initialisation included, so upper bounds):
   Geant4 43.5 CPU-ms per event for protons and 61.1 for antiprotons, which gives about 0.58 and 0.81 CPU-hours for 48,000 events each;
   whole-run reconstruction 0.73 to 0.80 CPU-ms per event per configuration (about 0.06 CPU-hours per pass of the three configurations
   over 96,000 events); event files 3.4 kB per event (about 0.33 GB). In all about 1.6 CPU-hours with two whole-run passes and the
   chunked measurement. The rerun of the pilot (the job of record) replaces these.
