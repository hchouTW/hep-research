# T03: task sheets for T07, T08, T09

Section 16.2 structure. Paths are relative to `plugins/hep-research/`. Nothing here is applied in P0 (R07). All three start after T06. `<freeze>` values are the user's. They are frozen at Freeze A, before any development run, except the items in t04-values-v4.md, section 2.2, frozen at Freeze B, before any evaluation sample (t04-prereg.md).

## Recipes named

| Recipe (proposed) | Workflow | Backend | Evidence ceiling for now |
| --- | --- | --- | --- |
| `reco.track.acts-ckf-planar/1` | T07 finding and fit | ACTS 48.2.0, smoke confirmed | Synthetic |
| `reco.track.acts-kf-refit/1` | T07 refit of a known hit set | ACTS 48.2.0 | Synthetic; counted apart from finding (BP03) |
| `reco.vertex.acts-amvf/1` | T07 vertexing | ACTS 48.2.0 | Synthetic |
| `reco.track.simreco-pr-a/1`, `-b/1` | T15b two-candidate domain | `simreco` pattern recognition, two configurations | Simulated `element_sim` events |
| `reco.calo.cell-cluster/1` | T08 | Development binding | Synthetic, then simulated-unvalidated |
| `reco.light.channel-likelihood/1` | T09 | Development binding | Synthetic |

## External inputs

`zdc-ecal-study` and `ams02-rich-replica` in the g4sim task package are the user's studies, bundled as external read-only inputs. They are read or run from outside the repository. No code from them enters the plugin tree. Their numbers come from other simulations and are never an independent reference.

## T07: tracking and vertexing (BP03, BP04)

- **Background / Objective:** the plugin has no general tracker; `simreco` handles simulated planes only. Integrate ACTS so that finding, ambiguity resolution, fitting and vertexing run on measurements through a native driver, with evidence per stage.
- **Scope:** planar telescope in a uniform field, F01-like silicon measurements, event-based data. **Non-goals:** barrel geometry, GSF, GPU, any calibration or alignment constant (R31), any tracking quality claim for a real detector.
- **Files, confirmed:** `<workdir>/env/acts48`; `docs/adapter-authoring.md`. **Proposed:** `adapters/acts-tracking/` with a C++ driver, fixture generator, thin Python wrapper and tool contract; `examples/reconstruction-tracking/`.
- **ACTS interfaces, read from the installed 48.2.0 headers:** `Geometry/Blueprint.hpp` or `Geometry/CuboidVolumeBuilder.hpp`; `MagneticField/ConstantBField.hpp`; `Propagator/EigenStepper.hpp`, `Navigator.hpp`, `Propagator.hpp`; `Seeding/EstimateTrackParamsFromSeed.hpp`; `TrackFinding/CombinatorialKalmanFilter.hpp` (`findTracks`), `MeasurementSelector.hpp`, `TrackSelector.hpp`; `TrackFitting/KalmanFitter.hpp` (`fit`), `GainMatrixUpdater.hpp`, `GainMatrixSmoother.hpp`; `AmbiguityResolution/GreedyAmbiguityResolution.hpp`; `Vertexing/AdaptiveMultiVertexFinder.hpp`, `FullBilloirVertexFitter.hpp`, `HelicalTrackLinearizer.hpp`; `EventData/VectorTrackContainer.hpp`, `VectorMultiTrajectory.hpp`, `TrackProxy.hpp`; `Surfaces/Surface.hpp` (`alignmentToBoundDerivative`, `alignmentToPathDerivative`). Headers are named, not signatures; these are templates and are read in full at implementation.
- **Input:** synthetic hits from known track parameters propagated through the same geometry, Gaussian smearing, injected noise hits. Truth goes to a separate file with role `truth`, and the data-side driver never opens it.
- **Output:** per-surface states with predicted, filtered and smoothed kept apart; candidates, selected branches, failure categories. This ACTS package has no persistence layer (one library, `libActsCore.so`), so the driver defines its own product format and that format needs its own round-trip test (Section 8.3).
- **Formed in plugin code (R33, R37):** unbiased residuals by removing the hit from the smoothed state, since no helper was found in the installed headers; residual covariances; alignment derivatives in the R32 parametrization.
- **Steps:** telescope geometry and a straight-line case first, then field, noise, CKF, ambiguity resolution, vertexing, residual and derivative outputs. Each with its failing check first.
- **Acceptance:**
  - Finding and refit counted separately; a truth-seeded fit is never reported as finding.
  - Negative cases: wrong hits, branch explosion, seed failure. Limits reached are marked as search-truncated.
  - Scenarios A01, A05, A07, A17, A39. A01 needs a second backend with the same semantics, so it stays open unless `simreco` qualifies on the shared domain.
  - `CAI-T07-1` rigid shift, `-2` derivatives against finite differences with the track state held fixed, `-3` refit, `-4` sagitta-like weak-mode fixture. Tolerances recorded before the run (R37). Residuals use `r = x_meas - x_pred`.
  - Quality: t04-values-v4.md and t04-prereg.md; pass or fail only after K09. Refit gated on the clean fixture, truth-assisted, counted apart.
- **Open items:** `CAI-T07-3` needs a way to apply a payload; the path is to be probed. A gap rests on a recorded probe of the interface, otherwise it is unimplemented work (R37). Material effects come after the first pass.
- **Stop:** an ACTS behaviour that contradicts the contract map goes back to K04. Tolerances and valid ranges do not move after results.

## T08: calorimetry (BP05)

- **Background / Objective:** no plugin tool does cell-to-cluster reconstruction: `simreco`'s calorimeter stage sums deposits, and `calorimeter_resolution` fits supplied points. Build cell estimate, clustering, splitting and named energy as a development binding.
- **Scope:** homogeneous crystal grid (F15), analog cells. **Non-goals:** HCAL, digital or dual readout (F17), particle flow, sampling ECAL (F16). Those stay gaps. A development binding is not a native backend; the native-integration gap stays open.
- **Files, confirmed:** `skills/hep-detector/references/event-reconstruction.md#clustering`, `calorimetry-ecal-hcal.md`. **Proposed:** `adapters/calo-cluster/`, `examples/reconstruction-calorimetry/`.
- **Input, first:** synthetic grid events, fixture t08-grid/1 (t04-values-v4.md, section 4.2), including overlapping showers, dead cells, thresholds and saturation.
- **Input, second:** cell deposits from `zdcsim` (`cell`, `zbin`, `edep`), built and run outside the repository in an approved job. Label `simulated-unvalidated`: that study's model passed 1 of 5 measurable gates. It exercises the format only and supports no performance number.
- **Interfaces:** cell ID, raw ADC, pedestal treatment, calibrated energy kept side by side; per-cell saturation flag from the readout; each chain step records its payload in order (R34); stable channel IDs; sharing fractions kept per cluster; energy kind named. Deposited energy is never reported as incident energy.
- **Steps:** cell chain with gain payload, seeds and neighbours, splitting, position, energy. Clustering is written from the reference, not adapted from `reco/cluster.py`. Clustering follows t04-values-v4.md, section 7.1, exactly. Configuration holds no constant derived from pulls or targets.
- **Acceptance:**
  - Single and overlapping showers, low thresholds, saturation, edges and dead cells; split and merge rates; thresholds use the same selection as the response. The efficiency reference uses the exact cell response, `q x Poisson` plus Gaussian noise (t04-values-v4.md, section 4.2).
  - Scenarios A15, A32, A38.
  - `CAI-T08-1`: with membership fixed and a multiplicative chain, cluster energy changes exactly by the plan's formula, for both gain roles. If splitting makes fractions depend on energy, the change is recorded without an exact assertion. `CAI-T08-2`: full re-reconstruction records changes and membership changes, no numeric assertion.
  - Quality: t04-values-v4.md and t04-prereg.md.
- **Open items:** none for fixture t08-grid/1, which has no Geant4 tuning. Any tuned sample is a tuning sample, not confirmation.
- **Stop:** double counting of a cell, or an unexplained change in fixed-membership energy.

## T09: photon likelihood (BP06)

- **Background / Objective:** no tool implements the all-channel likelihood of `photon-likelihood-reconstruction.md`. Build one as a development binding, with seeded multistart fits.
- **Scope:** F22-type detector, a toy sphere of photosensors in a uniform medium, charge and first-time readout. **Non-goals:** real optics, RICH rings, topology beyond the required two-hypothesis check. No native backend exists for this workflow, a recorded gap in required delivery.
- **Existing work checked:** `ams02-rich-replica` (`richlib/reco.py`) fits a hit-based ring likelihood. It has no unhit-channel term, so it does not meet BP06's all-channel requirement and is not used as this recipe. Its optical Geant4 program may later supply input, labelled `synthetic`.
- **Files, confirmed:** `skills/hep-detector/references/photon-likelihood-reconstruction.md`. **Proposed:** `adapters/photon-likelihood/`, `examples/reconstruction-photon-likelihood/`.
- **Input:** events from fixture t09-sphere/1 (t04-values-v4.md, section 4.3), a stated analytic light model, which makes this a shared-model closure: it tests the code, not the model, and is labelled so (Section 11.1).
- **Likelihood:** per the reference. All live channels enter. Dead or disabled channels are excluded, never treated as unhit. Hit and no-hit terms share one threshold model, so their probabilities sum to one per channel. Saturated channels are censored. Single-time readout uses the first-arrival density, with the noise rate included.
- **Interfaces:** live, dead and unhit states are three explicit states; per-channel `saturated` flag from the readout; charge and time from one sensor are modelled jointly or conditionally, not assumed independent (Section 8.2).
- **Steps:** charge-only likelihood, then time, then multistart seeds, then topology.
- **Acceptance:**
  - Controls: live-unhit against dead channels (200 channels); few photons (bin B1, `N_exp` below 120); saturation; mirrored vertices and reversed tracks; two simultaneous events.
  - Wrong-minimum rate reported beside resolution. A hypothesis with more parameters is not preferred for a higher raw likelihood alone.
  - No data-side truth (A09).
  - Quality: t04-values-v4.md and t04-prereg.md.
- **Open items:** Section 16.1 names no A-ID for T09, so BP06's panel is its acceptance. BP06 also asks P0 to check original method sources; that needs network approval or stays `source-unverified`.
- **Stop:** per-channel hit and no-hit probabilities that do not sum to one.

## Resources

None of these three needs a new install on current evidence. Each needs its own approved jobs. `run_workflow.py` wraps steps that produce numbers (R29).
