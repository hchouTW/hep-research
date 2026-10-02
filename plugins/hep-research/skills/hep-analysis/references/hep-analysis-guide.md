# High-Energy Physics and Astroparticle Physics Experimental Analysis and Statistics (guide)

## When to read this file

This file is the migrated routing and rules of the legacy `hep-analysis` skill (agentic-ai-skills@3e995a4): its check-first corrections, working procedure, API selection, analysis invariants, reference routing table, and list of executable resources. The references, scripts, and templates it points to now live in several skills of this plugin; the links below are relative to this file.

Produce physically traceable, statistically sound, reproducible analyses. Support design, implementation, debugging, review, and explanation. Follow the user's language and established project tools; do not assume an experiment, collision energy, era, or input format. Maintained in English. Preserve existing physics behavior (cuts, weights, binning, fit models) unless the user explicitly asks for a physics change.

## Check first: proposals to correct before answering

If the user proposes one of these, open with the correction, even when they only ask "is that right?". Each row restates an invariant below.

| User proposes | Answer |
|---|---|
| MC normalization by entry count, post-skim count, or sum of abs(weights) | No: `lumi * xsec / sum(signed genWeight)` over the full produced sample before any skim (e.g. the NanoAOD `Runs` tree `genEventSumw`); keep negative weights. Units: lumi in fb^-1 times xsec in pb needs a factor 1000 (`lumi_fb * 1000 * xsec_pb / sumw`). Show RDataFrame code that reads `genEventSumw` from `Runs` |
| `sqrt(N)` error on a few-count flux/rate bin | No: run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/cosmic_ray_flux.py --counts N --exposure E --bin-width W --level 0.6827` (W in the exposure's units, e.g. 0.6 for a 1.2-1.8 TV bin) with Bash before you answer, and quote the `flux`, `flux_lower` and `flux_upper` it prints, with units and asymmetric errors. Never write a flux value you did not read from that output; if you cannot run it, give the formula and the count interval from the table only. The table below is the check on the count interval. In a high-rigidity/energy bin also spillover and background |
| A plot or ratio covering a blinded region | Say first that SR data stay hidden: set observed values in the region to NaN/drop them before plotting; shading is not masking; offer MC/Asimov/CR checks |
| Scaling the final histogram for a kinematic systematic (JES, energy scale) | No: a flat bin scaling is only a normalization change. Vary the object (and propagate to MET and jet ordering), rerun selection and migration, then check the templates by comparing yields per cut, nominal against varied: identical yields mean the variation did not propagate |
| Widening a prior or retuning to improve agreement or a limit | If the reason is the fit, the agreement or the limit: decline in your first sentence, before looking for or asking for any file (a missing datacard changes nothing), and do not offer to make the change later; offer pulls/impacts, GoF, a CR constraint. If the user gives an independent measurement made before looking at the fit, that is not tuning: make the change and cite the measurement |
| Quadrature errors on a ratio with shared systematics | No: use the covariance; shared terms cancel |
| Hottest spot of a scan as a detection | Apply the trials correction `1-(1-p)^N` (fewer effective trials if correlated) |
| Tau/iterations chosen by agreement with a model | No: objective criterion fixed in advance, closure on alternative truths |

Exact 68.27% (Garwood) interval on the count N; divide by exposure times bin width for the flux:

| N | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lower | 0 | 0.17 | 0.71 | 1.37 | 2.09 | 2.84 | 3.62 | 4.42 | 5.23 | 6.06 | 6.89 |
| upper | 1.84 | 3.30 | 4.64 | 5.92 | 7.16 | 8.38 | 9.58 | 10.77 | 11.95 | 13.11 | 14.27 |

## Working procedure

1. Classify the task (inspection, production, inference, refactor, review). Inspect project instructions, configs, entry points, build system, and a small sample before changing the analysis.
2. Establish physics objective, data/MC distinction, units, observables, selections, normalization, signal/control/validation regions, POI, and blinding state. Keep inspecting when information is missing and state assumptions. Never invent luminosities, cross sections, calibration values, or correlations for a reported result.
3. Choose the simplest matching API (see API selection below) and read only the relevant references. Complete a minimal verifiable analysis before scaling to the full dataset. Record software, config, sample, and calibration versions.
4. Run any code you deliver before delivering it: on the user's sample if there is one, otherwise on a small synthetic sample you build with the stated branch names (a few hundred events, e.g. written with uproot), and compare a count or yield with a hand-computed expectation. For a jagged-jet analysis, build that sample with `python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/make_synthetic_nanoaod.py --out sample.root` instead of writing your own ROOT-writing code (it prints the expected counts and weight sums to compare with). Show the cutflow it printed; if you could not run it, say so instead of implying it works. When a bundled script computes the number you are asked for (flux and Poisson interval, Li & Ma significance, cutoff, resolution), run it and quote its output instead of computing by hand. Keep this to a few runs: if the same failure survives three fixes, stop, deliver the code with the failing output, and say it does not yet work. Distinguish successful execution, numerical validation, physical plausibility, and demonstrated statistical coverage. State which checks were not run and why.
5. Deliver relevant code/config, build+run and reproduction commands, cutflow, statistical model and diagnostics, assumptions (units, tree/branch names, weights), validation evidence, and limitations. Scale deliverables to the task, not a full report for every small question.

## API selection

| API | Use for |
|---|---|
| C++ `ROOT::RDataFrame` | new compiled event loops, multithreaded columnar processing, many histograms from one selection, snapshots |
| PyROOT `ROOT.RDataFrame` | ROOT-native workflow with Python orchestration, no compiled helpers needed |
| uproot + awkward-array | Python-native analysis, jagged arrays, fast inspection, no full interactive ROOT |
| `TTreeReader` | manual C++ loops, custom object handling, where RDataFrame would obscure a simple algorithm |
| `SetBranchAddress` | legacy maintenance only - validate addresses/lifetimes carefully |
| RooFit/RooStats, pyhf, Combine | likelihood models, constrained fits, workspaces, toys, limits, intervals |

Don't mix more APIs than needed in one script; if mixing, keep boundaries clear (e.g. uproot for inspection, RDataFrame for production, ROOT files as interchange).

awkward leading objects: apply the object mask, order each event with `jets = jets[ak.argsort(jets.pt, axis=1, ascending=False)]`, cut with `ak.num(jets, axis=1) >= 2` (on the jets and the weights together), then index `jets[:, 0]` and `jets[:, 1]`. Never write `jets.pt[ak.argsort(jets.pt, axis=1)[:, 0]]`: an integer array indexes *events*, so it returns whole events, not one jet per event. Fill histograms with `np.histogram(x, bins, weights=w)` and the same call with `weights=w**2`, then print or plot them; write a ROOT output file only if asked, because uproot's histogram writing costs many turns. Full pattern: [data pipelines](02-data-pipelines.md).

## Analysis invariants

### General

- Do not silently change cuts, object ordering, binning, weights, corrections, models, parameter bounds, or nuisance correlations during a refactor. If a change risks altering physics output, say so and propose a comparison method (event count per cut, histogram integrals, max absolute/relative bin difference, fit parameters/uncertainties).
- Preserve signed generator weights. Normalize with the signed sum of generator weights for the corresponding full production (before any skim), not the selected entry count and not the sum of absolute weights. Store both sumw and sumw2.
- Do not count the same events, MC statistical information, or auxiliary measurement twice as independent likelihood information. Remove region overlaps or model them jointly.
- Label observed counts, weighted yields, Asimov expectations, and toy data separately. Arbitrary weighted or background-subtracted data are not ordinary Poisson observations.
- Poisson expectations must be nonnegative. Do not silently clip negative bins; investigate signed weights, sample statistics, binning, or model suitability.
- Propagate shape variations through object corrections, ordering, selections, missing transverse momentum, and category migration where affected. Changing only the final histogram weight is insufficient for a kinematic variation.
- Preserve existing blinding rules and define masks for new analyses. Without authorized unblinding, do not expose masked observations through plots, ratios, logs, temporary tables, or optimization. A mask removes the observed values (drop them or set them to NaN before any plotting or arithmetic, or never read them). Shading or overlaying the region is not a mask. A pre-unblinding "check" of a blinded region uses MC, Asimov data, or control/validation regions.
- Do not tune a model to obtain a desired significance, exclusion, or goodness-of-fit value. This includes widening or narrowing a nuisance prior/constraint, changing parameter bounds, or dropping a nuisance after seeing the fit or the limit. Do not write such a change into a datacard or workspace on request, and decline before searching for or asking for the file when the reason is the fit or the limit. Say it biases the result, ask for the independent measurement that justifies it, and offer pulls/impacts, a goodness-of-fit test, or a control-region constraint instead.
- Do not tune simulation, calibration, or alignment parameters to remove a disagreement in the observable being measured. Tune only on independent control observables, with a stated physical justification, and carry the remaining freedom as a systematic.
- Detector-level quantities are inferred, not observed. Rigidity is `p/q`, not momentum; efficiency is not acceptance; a matched object is matched under a stated criterion. State the definition whenever one of these is quoted.
- Distinguish frequentist confidence intervals from Bayesian credible intervals. Report the statistic, tail convention, nuisance treatment, and validity conditions.
### Astroparticle and cosmic-ray

- In an ON/OFF or blind sky-scan search, the OFF/background region must not overlap the ON region, and a reported significance must account for the number of independent trials (positions, energy bins, time windows, source catalogs) actually tested, not just the one presented.
- Distinguish a flux measured at the top of the atmosphere or at an instrument from one corrected to the local interstellar spectrum; state the solar-modulation epoch/potential and the geomagnetic cutoff applied whenever a low-rigidity cosmic-ray flux is reported. Select events above a safety factor (typically 1.2) times the cutoff backtraced through a realistic field model (per second or per event); a Stormer formula is only a planning estimate. Take the epoch's solar phase from the sunspot record: cycle 24 had its minimum in Dec 2008 and a double maximum (Nov 2011 and 2012-mid 2013, smoothed peak Apr 2014), so 2011-2013 is solar maximum, not a declining phase ([35](../../detector-response/references/35-space-based-direct-detection.md)).
- Do not draw a composition conclusion from a single shower observable (X_max or muon content alone) without stating the hadronic interaction model assumed (quote more than one) and checking consistency against the other observable, given the current muon-content/X_max modeling discrepancy. Use the X_max distribution width (sigma(X_max)), not only the mean: protons fluctuate most, and a nucleus of mass A averages fluctuations down (~1/sqrt(A)), so heavier means narrower.
- A flux or rate reported from raw counts must use an exact Poisson interval, not a Gaussian sqrt(N) approximation, whenever counts are low enough for the two to disagree (routine in a steeply falling spectrum's high-energy tail); state the exposure (effective area/geometric factor times live time times solid angle) and bin width used, separately from the raw count. If asked whether `sqrt(N)` is right for a few-count bin, answer no (not "approximately right"), run `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/cosmic_ray_flux.py` for the interval, and for a high-rigidity/energy bin also address resolution spillover and background ([35, low-count bins](../../detector-response/references/35-space-based-direct-detection.md#low-count-high-rigidity-bins)).
- A ratio or fraction of two yields (e.g. a positron fraction or an antiproton/proton ratio) must use the yields' actual covariance, not an independence assumption, whenever they share a systematic (the same acceptance, exposure, or background-template shape) - state which systematics are shared and whether they were treated as correlated. Species-specific effects (e.g. charge confusion, which feeds protons into the antiproton sample) belong to one yield only and do not cancel.

## Reference routing

| Task | Read |
|---|---|
| Analysis design, quality masks, triggers, blinding | [Analysis contract](01-analysis-design.md) |
| ROOT/columnar I/O, event loops, performance, ownership | [Data pipelines](02-data-pipelines.md) |
| Luminosity, cross sections, signed weights, cutflows | [Normalization](03-weights-normalization.md) |
| Histograms, efficiencies, covariance, plotting (statistics) | [Histograms and uncertainties](04-histograms-efficiencies.md) |
| Control regions, ABCD, fake rates, sidebands, transfer factors | [Background estimation](05-backgrounds.md) |
| Detector/theory uncertainties, MC statistics, correlations, variation implementation | [Systematics](06-systematics.md) |
| Binned/unbinned likelihoods, RooFit, nuisance parameters, workspace inspection | [Models and fitting](../../hep-statistics/references/07-likelihood-fitting.md) |
| Intervals, significance, CLs, toys, Bayesian inference | [Statistical inference](../../hep-statistics/references/08-inference.md) |
| pyhf, HistFactory, Combine workspaces/datacards | [Statistical tools](../../hep-statistics/references/09-statistical-tools.md) |
| Cross sections, response matrices, unfolding, combinations | [Measurements and unfolding](10-measurements-unfolding.md) |
| Classifiers, leakage, mass sculpting | [Machine learning](../../physics-ml/references/11-ml-analysis.md) |
| Debugging, verification, preservation, review | [Validation](12-validation.md) |
| Versions and methodological sources | [Primary sources](../../research-communication/references/13-sources.md) |
| Drawing an analysis-pipeline, Monte Carlo chain, region/likelihood workflow, detector schematic, or decay-tree figure (structural diagram, not a data plot) | the `academic-diagrams` skill, when installed |
| C++/ROOT/RDataFrame code patterns, TTreeReader, naming/comments/file-documentation, general C++ class/struct/RAII/ownership/inheritance design, TObject inheritance, class dictionaries, directory-based ownership, branch-buffer structs, build commands | [C++, ROOT, and balanced design guidelines](../../hep-computing/references/14-root-balanced-design-guidelines.md) - long; use its "Read only what the task needs" table and read one section |
| CMake and root-config builds, project scaffolding | [Build setup](../../hep-computing/references/15-cmake-and-build.md) |
| Debugging ROOT/PyROOT/C++ (missing symbols, dictionaries, fits) | [Debugging ROOT](../../hep-computing/references/16-debugging-root.md) |
| Python CLI structure, naming, PyROOT/uproot/awkward code conventions | [Python coding](../../hep-computing/references/17-python-hep-coding.md) |
| Jet clustering, JES/JER, b-tagging, MET, pileup jets, overlap removal | [Physics objects](../../detector-response/references/18-physics-objects-jets-btagging-met.md) |
| Tag-and-probe, trigger turn-ons/prescales, luminosity, pileup reweighting | [Triggers, luminosity, pileup](../../detector-response/references/19-triggers-luminosity-pileup.md) |
| BDT/NN classifier choice, training, feature engineering, calibration, regression targets (energy/mass regression) | [Multivariate classifiers and regression](../../physics-ml/references/20-multivariate-analysis-bdt-nn.md) |
| Subsystem layout, rigidity vs. momentum, material budget, acceptance, resolution vocabulary | [Detector systems overview](../../detector-response/references/21-detector-systems-overview.md) |
| Silicon/gas tracking, pattern recognition, Kalman fit, charge confusion, vertexing | [Tracking and vertexing](../../detector-response/references/22-tracking-and-vertexing.md) |
| EM/hadronic showers, sampling vs. homogeneous, stochastic/noise/constant terms, e/h non-compensation, leakage | [Calorimetry](../../detector-response/references/23-calorimetry-ecal-hcal.md) |
| TRD, TOF, RICH/Cherenkov, dE/dx, muon systems, combined PID likelihoods, isotope separation | [Particle identification](../../detector-response/references/24-particle-identification.md) |
| Hits to clusters to tracks to objects, particle flow, ambiguity resolution, reconstruction under pileup | [Event reconstruction](../../detector-response/references/25-event-reconstruction.md) |
| Truth matching, reconstruction efficiency/fake rate/purity, resolution and bias, scale factors | [Reconstruction performance](../../detector-response/references/26-reconstruction-performance-and-truth-matching.md) |
| Generators, LHE/HepMC, matching/merging, negative weights, PDF and scale variations | [Event generation](../../hep-theory/references/27-event-generation.md) |
| Geant4 geometry/physics lists/production cuts, digitization, fast simulation, simulation validation | [Detector simulation](../../detector-response/references/28-detector-simulation.md) |
| Test-beam and in-situ calibration, alignment weak modes, conditions time dependence | [Calibration and alignment](../../detector-response/references/29-calibration-and-alignment.md) |
| Cosmic-ray spectrum features (knee/ankle/GZK), composition, acceleration, propagation, solar modulation | [Cosmic-ray spectrum and composition](../../detector-response/references/30-cosmic-ray-spectrum-and-composition.md) |
| Extensive air showers, Heitler-Matthews model, Gaisser-Hillas/Greisen profiles, X_max, muon puzzle | [Extensive air showers](../../detector-response/references/31-extensive-air-showers.md) |
| Surface detector arrays, fluorescence detectors, hybrid reconstruction, atmospheric monitoring | [Ground-based detection arrays](../../detector-response/references/32-ground-based-detection-arrays.md) |
| IACT gamma-ray astronomy, Hillas parameters, gamma/hadron separation, ON/OFF significance | [Imaging atmospheric Cherenkov](../../detector-response/references/33-imaging-atmospheric-cherenkov.md) |
| Neutrino telescopes, track/cascade/double-bang topologies, atmospheric background rejection | [Neutrino astronomy](../../detector-response/references/34-neutrino-astronomy.md) |
| Balloon/satellite direct detection, geomagnetic cutoff, solar modulation, antiparticle excesses, periodicity/time-structure search (epoch-folding, Lomb-Scargle, charge-sign drift diagnostic) | [Space-based direct detection](../../detector-response/references/35-space-based-direct-detection.md) |
| Multi-messenger coincidence analysis, alert follow-up, trials/timing/pointing systematics | [Multi-messenger analysis](../../detector-response/references/36-multimessenger-analysis.md) |
| Li & Ma significance, sky-scan/catalog trials factor, exposure/forward-folding for steep spectra | [Astroparticle statistics](../../hep-statistics/references/37-astroparticle-statistics.md) |
| AMS-02 overview only: how tracker/TRD/TOF/RICH/ACC/ECAL combine, orbital/solar-cycle systematics, rare-species ratio pattern. For AMS-specific design, review, published results or "latest" checks use the `ams-analysis` skill if installed | [AMS-02 case study](../../../profiles/experiments/ams-02/modules/subsystems/instrument-overview.md); `ams-analysis` (sibling skill) |
| Forward model/inverse problem, identifiability, bias vs resolution vs efficiency, thresholds, conditional-probability language, 14-question template for any detector | [Detector measurement framework](../../detector-response/references/39-detector-measurement-framework.md) |
| Bethe-Bloch/Landau/Highland, scintillation/Cherenkov/TR, drift/diffusion/gain/attachment, shaping, noise, saturation, dead time, trigger bias | [Signal formation and readout](../../detector-response/references/40-signal-formation-and-readout.md) |
| Drift chambers/tubes, TPC, MWPC/straw/RPC, GEM/Micromegas, fibers, emulsion, MAPS/CCD/diamond, left-right ambiguity, space charge | [Gaseous and specialized tracking](../../detector-response/references/41-gaseous-and-specialized-tracking-technologies.md) |
| Time-walk/CFD, single-hit vs per-track vs event-time resolution budget, LGAD/MCP/MRPC, bunch assignment, clock offsets | [Timing detectors](../../detector-response/references/42-timing-detectors.md) |
| Segments, standalone/combined/tagged muons, sagitta weak modes, charge misID, punch-through, decay in flight, tag-and-probe | [Muon systems](../../detector-response/references/43-muon-systems.md) |
| LAr/LXe/dual-phase TPCs, recombination, lifetime, water/scintillator, near/far, bolometers, thresholds, fiducialization | [Noble-liquid, neutrino, rare-event](../../detector-response/references/44-noble-liquid-neutrino-and-rare-event-detectors.md) |
| Threshold/differential counters, DIRC/TOP, PMT/SiPM/APD/MCP, WLS, fibers, light guides, SPE calibration | [Cherenkov variants and photosensors](../../detector-response/references/45-cherenkov-imaging-variants-and-photosensors.md) |
| Acceptance/efficiency/purity/fake/mis-ID/resolution definitions, worked numerical example, residual/pull/covariance/coverage | [Performance metrics and residuals](../../detector-response/references/46-performance-metrics-and-residual-diagnostics.md) |
| Data/MC chain, tag-and-probe, scale factors, reweighting risks, J V J^T propagation, detector combination | [Validation, systematics, combination](47-validation-systematics-and-combination.md) |
| Eight defect-to-physics-bias cases, unfamiliar-detector/plot-reading/data-MC/calibration checklists, one-page synthesis | [Case studies and checklists](../../detector-response/references/48-detector-case-studies-and-checklists.md) |
| Master, tracking, timing, PID, ECAL/HCAL, chain-distinction, detector-specific, systematics, auxiliary-detector tables | [Comparison tables](../../detector-response/references/49-detector-comparison-tables.md) |
| Symbols, acronyms, adopted conventions | [Detector glossary](../../detector-response/references/50-detector-glossary.md) |
| Authoring a canonical worked example (Contrast, Execution Trajectory, Gated Pipeline, Decision-Tree, Interactive Elicitation, Adversarial Audit, Test-First, or Postmortem archetype) for `examples/` | `task-authoring`'s [example-authoring reference](../../hep-computing/references/example-authoring.md) (requires `task-authoring` installed alongside this skill) |

Overlapping rows: for tag-and-probe read 19 for the method and 47 for scale factors, and 43 only for muon specifics. For efficiency read 04 for the statistics (intervals, weighted efficiencies), 26 for reconstruction efficiency against truth, and 46 for the definitions. Read one of them, not all three.

Worked, verified walkthroughs sit at the end of: [07](../../hep-statistics/references/07-likelihood-fitting.md#worked-walkthrough-a-roofit-signal--background-fit-verified-2026-09-24) (RooFit fit), [09](../../hep-statistics/references/09-statistical-tools.md#worked-walkthrough-a-pyhf-workflow-end-to-end-verified-2026-09-24) (pyhf end to end), [20](../../physics-ml/references/20-multivariate-analysis-bdt-nn.md#worked-walkthrough-training-a-bdt-without-leakage-verified-2026-09-24) (BDT without leakage), [28](../../detector-response/references/28-detector-simulation.md#worked-walkthrough-setting-up-a-geant4-simulation-for-a-calorimeter-test-beam-comparison) (Geant4 setup, not executed), [33](../../detector-response/references/33-imaging-atmospheric-cherenkov.md#worked-walkthrough-an-iact-onoff-measurement-with-a-trials-correction-verified-2026-09-24) (IACT ON/OFF with trials), [35](../../detector-response/references/35-space-based-direct-detection.md#worked-walkthrough-a-proton-flux-point-from-counts-verified-2026-09-24) (cosmic-ray flux from counts).

## Code file requirement

When creating or modifying any code file (C++ source/headers, ROOT macros, PyROOT/uproot scripts, CMake files, config loaders), include a short introductory comment block: purpose, what it does, and usage notes/dependencies/assumptions (build/run command, expected input format and tree/branch names, units, weight conventions, ROOT version, preconditions). Add or update it if missing/outdated. Full convention: [C++, ROOT, and balanced design guidelines](../../hep-computing/references/14-root-balanced-design-guidelines.md#naming-comments-and-file-documentation).

## Executable resources

- `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/audit_histograms.py`: audit the JSON histogram bundle defined by this guide. Detect malformed arrays, nonfinite values, negative variances, negative Poisson rates, missing variations, and identical templates. It does not read ROOT, prove physical correctness, or infer whether Up/Down labels are reversed.
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/counting_reference.py`: exact Poisson tails and flat-signal-prior Bayesian bounds for a single bin with known background. This is a small-model cross-check, **not a general CLs or nuisance-parameter calculator**.
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/inspect_root_file.py` / `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/inspect_root_file.C`: list keys, trees, branches, and histogram metadata in a real ROOT file (requires PyROOT/ROOT).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/check_root_cpp_env.sh`: verify ROOT/root-config/compiler availability and print resolved versions.
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/new_root_cpp_project.sh`: scaffold a CMake-based ROOT C++ project.
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/check_systematic_variations.py`: verify Up/Down variation histograms in a real ROOT file exist, aren't swapped, aren't byte-identical to nominal, and share nominal binning (requires PyROOT; complements `audit_histograms.py`, which works on the JSON bundle format instead).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/compare_root_histograms.py`: diff two histograms across ROOT files (integral, bin-by-bin, max abs/relative difference) for regression checks (requires PyROOT).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/make_yield_table.py`: render a yield CSV (region/sample/yield[/uncertainty]) as Markdown tables (standard library only).
- `${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/tag_and_probe_efficiency.py`: exact Clopper-Pearson binomial confidence interval for a pass/total efficiency measurement (standard library only; not a Gaussian/Wald approximation).
- `${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/pileup_reweight.py`: per-bin data/MC pileup reweighting factors from two profile histograms, with a closure-check mean and explicit flagging (not silent inf/0) of data-populated bins where MC has zero probability (standard library only).
- `${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/multiple_scattering.py`: PDG Highland scattering angle, accumulated material budget, and the scattering/intrinsic terms of a magnetic spectrometer's rigidity resolution, with the crossover rigidity and maximum detectable rigidity (standard library only; a design-level estimate, **not** a substitute for a track fit).
- `${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/calorimeter_resolution.py`: fit and evaluate the three-term calorimeter resolution `(sigma_E/E)^2 = a^2/E + b^2/E^2 + c^2`. The model is linear in `(a^2, b^2, c^2)`, so the fit is an exact linear least squares with no minimizer; a coefficient that fits negative is reported as a failed separation rather than square-rooted into a NaN (standard library only).
- `${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/pid_separation_power.py`: species separation in sigma for time-of-flight, Bethe-Bloch ionization, and directly-supplied velocity resolution, with the mass resolution's `gamma^2` degradation and the momentum ceiling where separation is lost. The dE/dx evaluation **omits the density-effect correction** and flags when it is in the relativistic rise (standard library only).
- `${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/cherenkov_angle.py`: RICH threshold momenta, Cherenkov angle and its saturation, photon yield, per-track angular resolution, and the resulting velocity/mass resolution and species separation (standard library only; a design estimate, not a ring-reconstruction simulation).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/summarize_histogram_statistics.py`: entries, integral, sum of weights, bin edges, negative bins for a histogram in a ROOT file (requires PyROOT).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/roofit_workspace_summary.py`: summarize a `RooWorkspace` (variables, PDFs, datasets, functions, snapshots) (requires PyROOT).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/scripts/li_ma_significance.py`: exact Li & Ma (1983) likelihood-ratio significance for an ON/OFF counting measurement, including the N_on=0/N_off=0 boundary terms (standard library only; no trials/look-elsewhere correction - see reference 37).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/geomagnetic_cutoff.py`: analytic vertical Stormer dipole geomagnetic cutoff rigidity at a given geomagnetic latitude/altitude, with an optional conversion to minimum kinetic energy per nucleon for a given (Z, A) (standard library only; an idealized-dipole first-order estimate, **not** a substitute for particle backtracing through a full field model).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/cr_spectrum_powerlaw_fit.py`: exact (weighted) linear least-squares power-law fit to a flux-vs-energy spectrum in log-log space, single or two-segment (given a break energy), reporting the index(es) and their uncertainty (standard library only).
- `${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/xmax_gaisser_hillas.py`: evaluate the Gaisser-Hillas air-shower longitudinal profile, shower age, and half-maximum depths for a given or externally fitted parameter set (standard library only; an evaluator, not a nonlinear curve fitter).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/orbit_averaged_geomagnetic_cutoff.py`: minimum, maximum, and time-weighted average vertical Stormer cutoff over an inclined low-Earth orbit (e.g. the ISS), by direct numerical quadrature over the orbit's latitude range (standard library only; a planning-level estimate, not a substitute for ephemeris-based backtracing).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/solar_modulation_force_field.py`: force-field approximation converting between the local interstellar spectrum and the flux measured at 1 AU, in both directions - modulate a LIS model to a predicted top-of-atmosphere flux, or demodulate one measured flux point back to its equivalent LIS value (standard library only).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/particle_ratio_with_uncertainty.py`: ratio or fraction of two independent yields (e.g. a positron-fraction- or antiproton/proton-ratio-style measurement) with exact delta-method error propagation, including an optional correlation term (standard library only; first-order/Gaussian approximation).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/cosmic_ray_flux.py`: differential flux from an observed count, exposure, and bin width, with an exact Poisson confidence interval (not a Gaussian sqrt(N) approximation) and optional background subtraction (standard library only; exact interval limited to counts where the underlying Poisson-tail tool's 0-500 rate range suffices - reports a clear error otherwise rather than a silently truncated interval).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/make_synthetic_nanoaod.py`: write a synthetic NanoAOD-like ROOT file (TTree `Events` with jagged `Jet_*` and signed `genWeight`, TTree `Runs` with the full-sample `genEventSumw`) and print the expected count, signed weight sums and leading-pair mass for a jet selection, computed independently of any analysis code, so code under test has a known answer (requires numpy, awkward, uproot; all values are synthetic and never results).
- legacy hep-analysis/scripts/validate_skill_bundle.py at agentic-ai-skills@3e995a4: check that this package's own files (SKILL.md, README.md, references, scripts, assets, tests) are all present and non-empty, and that SKILL.md/README.md have their expected structure (standard library only).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/histograms.example.json`: synthetic audit input for `audit_histograms.py`; see the [schema](12-validation.md).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/pileup_profiles.example.json`: synthetic data/MC pileup profile pair for `pileup_reweight.py`.
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/detector_stack.example.json`: synthetic layered detector stack (material budget per layer, field, lever arm, point resolution) for `multiple_scattering.py`. Illustrative geometry, not any real experiment.
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/calorimeter_response.example.json`: synthetic `(E, sigma_E/E)` points generated exactly from stated `a`, `b`, `c` values, so a correct fit recovers them; input for `calorimeter_resolution.py`.
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/cosmic_ray_spectrum.example.json`: synthetic broken-power-law flux points generated exactly from stated indices and a break energy, so a segmented fit recovers them; input for `cr_spectrum_powerlaw_fit.py`.
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/analysis-contract.yaml`, `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/systematics.csv`, `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/report-template.md`: reusable analysis, correlation, and reporting templates.
- `${CLAUDE_PLUGIN_ROOT}/adapters/pyhf-combine/assets/pyhf-counting.json`: a synthetic single-bin workspace. Never present its values as experimental results.
- `${CLAUDE_PLUGIN_ROOT}/adapters/root-uproot/assets/uproot_awkward_analysis.py`, `${CLAUDE_PLUGIN_ROOT}/adapters/root-uproot/assets/pyroot_rdataframe_analysis.py`, `${CLAUDE_PLUGIN_ROOT}/adapters/root-uproot/assets/cpp_rdataframe_analysis.cpp`, `${CLAUDE_PLUGIN_ROOT}/adapters/root-uproot/assets/rdf_analysis.cpp`: starting templates (copy and adapt) for uproot+awkward and RDataFrame (Python/C++) selection-and-histogram skeletons.
- legacy hep-analysis/assets/end_to_end_sample_analysis.py at agentic-ai-skills@3e995a4: runnable end-to-end template and smoke test (synthetic signed-weight ntuple -> sumw/sumw2 cutflow -> orthogonal SR/CR histograms -> pyhf fit and CLs limit on labelled pseudo-data -> yield table). Needs numpy + pyhf; legacy hep-analysis/tests/test_end_to_end.py at agentic-ai-skills@3e995a4 skips without them (`HEP_PYHF_PYTHON` selects an interpreter).
- `${CLAUDE_PLUGIN_ROOT}/adapters/root-uproot/assets/pyroot_roofit_signal_background.py`, `${CLAUDE_PLUGIN_ROOT}/adapters/root-uproot/assets/fit_histogram.cpp`, `${CLAUDE_PLUGIN_ROOT}/adapters/root-uproot/assets/plot_branch.C`: RooFit signal+background fit and fitting/plotting macro templates.
- `${CLAUDE_PLUGIN_ROOT}/adapters/root-uproot/assets/CMakeLists.txt`, `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/analysis_config.yaml`, `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/systematics_config.yaml`, `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/statistical_histogram_config.yaml`, `${CLAUDE_PLUGIN_ROOT}/adapters/pyhf-combine/assets/combine_datacard_template.txt`: build and config templates (copy and adapt).
- `${CLAUDE_PLUGIN_ROOT}/tests/skills/detector_response/test_hep_analysis_helpers.py`: standard-library tests for `audit_histograms.py`/`counting_reference.py`/`tag_and_probe_efficiency.py`/`pileup_reweight.py`. Run `python3 -m unittest discover -s tests -v`.
- `${CLAUDE_PLUGIN_ROOT}/tests/skills/hep_computing/test_hep_analysis_synthetic_nanoaod.py`: checks the synthetic sample generator against an independent awkward recomputation (skips without numpy, awkward and uproot).
- `${CLAUDE_PLUGIN_ROOT}/tests/skills/hep_analysis/test_hep_analysis_astroparticle.py`, `${CLAUDE_PLUGIN_ROOT}/tests/skills/hep_analysis/test_hep_analysis_ams02.py`, `${CLAUDE_PLUGIN_ROOT}/tests/skills/hep_analysis/test_hep_analysis_yield_table.py`: standard-library tests for the astroparticle/space-detection helpers and `make_yield_table.py` (including error paths).
- legacy hep-analysis/tests/prompts_eval.py at agentic-ai-skills@3e995a4, legacy hep-analysis/tests/routing_eval.py at agentic-ai-skills@3e995a4: model-behavior harnesses (they call `claude -p` and cost money): graded prompts from legacy hep-analysis/tests/prompts.md at agentic-ai-skills@3e995a4 and trigger/routing evals on the legacy hep-analysis/tests/trigger_queries*.json at agentic-ai-skills@3e995a4 sets.
- `${CLAUDE_PLUGIN_ROOT}/tests/skills/detector_response/test_hep_analysis_reference_values.py`: cross-checks the physics helpers against independent references (scipy quantiles, a numerical profile likelihood, PDG table values, Smart & Shea); scipy tests skip if scipy is missing.
- `${CLAUDE_PLUGIN_ROOT}/tests/skills/hep_computing/test_hep_analysis_root_integration.py` + `${CLAUDE_PLUGIN_ROOT}/tests/skills/hep_computing/hep_analysis_make_root_fixtures.py`: run the PyROOT scripts and assets end to end on synthetic ROOT fixtures; skipped unless PyROOT imports (set `HEP_ROOT_PYTHON`, e.g. Homebrew's `python3.14`, when conda Python cannot load Homebrew ROOT).

Resolve relative paths from the skill directory. Read a script's `--help` before use. Write outputs to the appropriate user-project location. Use the project's existing ROOT/PyROOT/uproot/pyhf environment; loading this skill needs no software install, but PyROOT-dependent scripts above need PyROOT. When a script's output (branch/key listings, bin-by-bin diffs, workspace contents) is large, summarize it: report counts and the top ~20 offending/differing entries rather than the full dump.

## Example requests

- "Review this NanoAOD selection and explain the yield difference for the negative-weight sample."
- "Design a simultaneous likelihood for three control regions and identify shared nuisances."
- "Review my CLs limit, including low-statistics and parameter-boundary effects."
- "Build a reproducible differential cross-section analysis with response uncertainties and covariance."
- "Inspect this NanoAOD file and list the muon-related branches."
- "Write an RDataFrame selection for >=2 muons with pT>25 GeV and make a pT histogram with a cutflow."
- "My uproot script gives different yields after a refactor - help me find why."
- "Check that my JES Up/Down systematic histograms aren't swapped or empty."
- "Build a CMake project for this ROOT C++ analysis."
- "Why does my spectrometer's rigidity resolution get worse both below 5 GV and above 200 GV?"
- "Up to what momentum can this TOF separate pions from kaons, and would a RICH do better?"
- "Generate a canonical `examples/` entry for this skill contrasting a weak vs. expert
  JES systematic on a cutflow-based cross-section measurement."
- "My data and simulation disagree in tracking efficiency at low momentum but agree at high - where should I look?"
- "Review how this analysis defines truth matching and reconstruction efficiency."
- "What should I check before trusting fast simulation for this measurement?"
- "Is a 4.8-sigma excess in my ON/OFF gamma-ray source search significant after accounting for the sky scan?"
- "Why does my composition analysis using X_max disagree with the one using muon content?"
- "Review my IceCube-style point-source likelihood - is the background estimation and trials factor right?"
- "Fit the spectral break in this cosmic-ray flux and check whether it's consistent with a knee-like feature."
- "What geomagnetic cutoff range does an AMS-02-like instrument on the ISS orbit see, and how should that shape my low-rigidity selection?"
- "Convert this local-interstellar proton spectrum to what we'd expect at 1 AU during solar minimum vs. solar maximum."
- "Propagate the uncertainty on a positron fraction from independent positron and electron template-fit yields."
- "Compute the differential flux and its statistical uncertainty from these raw counts, exposure, and bin width."

See legacy hep-analysis/README.md at agentic-ai-skills@3e995a4 for installation and cross-agent use. Pair with a general software-engineering skill for the broader workflow (scoping, tests, review discipline) if one is available.
