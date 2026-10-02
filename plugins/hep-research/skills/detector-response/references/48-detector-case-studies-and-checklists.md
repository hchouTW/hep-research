# Detector-to-Physics-Bias Case Studies, Checklists, and Synthesis

Eight end-to-end cases across distinct detector families, then the practical checklists
and a one-page synthesis. All cases are generic *mechanism* studies: they name no
experiment and quote no performance number; any real instance needs the apparatus,
configuration, and source ([13](../../research-communication/references/13-sources.md)). Each follows the same eight steps:
(1) defect, (2) low-level effect, (3) reconstruction effect, (4) performance-plot
signature, (5) how data/MC or controls reveal it, (6) correction/model update,
(7) assigned systematic, (8) possible final physics bias. Framework:
[39](39-detector-measurement-framework.md); propagation:
[47](../../hep-analysis/references/47-validation-systematics-and-combination.md).

## Case 1: Tracker weak mode (alignment) - charge-dependent momentum bias

1. **Defect**: a global deformation (e.g. a sagitta/"curl" mode) that leaves track
   `chi^2` nearly unchanged ([22](22-tracking-and-vertexing.md), [29](29-calibration-and-alignment.md)).
2. **Low level**: hit residuals show a small coherent trend versus `phi`/`z`, invisible
   per hit. 3. **Reconstruction**: `q/p` shifts by an amount proportional to `q * p`
   (charge-dependent), mostly at high `p`. 4. **Signature**: dimuon mass versus `q*eta`
   and `phi` shows opposite-sign shifts for `mu+` and `mu-`; cosmic-track split
   (upper/lower half) disagrees. 5. **Reveal**: resonance mass in `(q, eta, phi)` bins,
   split-track `Delta pT/pT`, `E/p` for electrons of each charge. 6. **Correction**:
   include the resonance mass and cosmic/track-split constraint in the alignment;
   external survey constraints. 7. **Systematic**: residual `q/p` curvature bias,
   correlated across `eta` with charge sign. 8. **Physics**: charge asymmetries and
   high-`pT` spectrum slopes (`W` charge asymmetry, high-mass `Z'` search) biased.

## Case 2: TPC space-charge distortion

1. **Defect**: positive-ion buildup (ion backflow, ionization at high rate) distorts `E`.
2. **Low level**: cluster positions displaced radially, dependent on `r`, `z`, and
   luminosity/rate. 3. **Reconstruction**: curved residual trends; momentum and `dE/dx`
   path errors; matching to outer detectors degrades. 4. **Signature**: cluster-to-track
   residuals versus `(r, z)` and versus instantaneous rate; track-matching residual to
   an external precision layer. 5. **Reveal**: matching map to a reference detector, laser
   or cosmic calibration, rate-dependent comparison. 6. **Correction**: time-dependent
   distortion map, rate-parameterized. 7. **Systematic**: map uncertainty
   (correlated over the rate/time range). 8. **Physics**: momentum scale/resolution and
   PID efficiency drift with beam intensity.

## Case 3: Drift-chamber `t0`/`r(t)` offset

1. **Defect**: a `t0` shift (e.g. clock/cable offset) or a wrong drift velocity.
2. **Low level**: measured drift times shifted by a constant/`E`-dependent amount.
3. **Reconstruction**: apparent radius error; left and right hits pull to opposite sides
   (a `t0` offset produces the same structure as a misalignment); segment `chi^2`
   rises. 4. **Signature**: residual versus drift distance with a left/right offset
   and slope. 5. **Reveal**: residual versus drift distance, per-run `t0` fit, per-layer
   comparison. 6. **Correction**: refit `t0`/`r(t)` per period, decouple from alignment
   by using their different dependence on the drift distance. 7. **Systematic**:
   `t0`/`v_d` residual (time-correlated). 8. **Physics**: coherent `pT` and impact
   parameter bias, muon efficiency loss.

## Case 4: ECAL dead material and nonlinearity

1. **Defect**: unmodeled upstream material and a nonlinear response (saturation or
   channel intercalibration error) ([23](23-calorimetry-ecal-hcal.md)).
2. **Low level**: energy lost before the calorimeter, shower starting earlier;
   channel gain errors. 3. **Reconstruction**: cluster energy scale wrong versus `eta`
   and energy; enhanced converted-photon and electron-bremsstrahlung tails. 4. **Signature**:
   `E/p` (electrons) and `pi^0`/`Z -> ee` mass versus `eta`, energy, and shower start.
5. **Reveal**: `Z -> ee` mass scale, `E/p`, `pi^0 -> gamma gamma`, comparison to
   simulation with varied material. 6. **Correction**: material-model update, layer
   weights, energy-dependent scale. 7. **Systematic**: scale with `eta`- and energy-dependent
   correlation; material variation. 8. **Physics**: shift of a resonance mass
   (e.g. `H -> gamma gamma`) and category migration.

## Case 5: HCAL non-compensation and jet-response bias

1. **Defect**: `e/h != 1`, invisible energy fluctuations, leakage ([23](23-calorimetry-ecal-hcal.md)).
2. **Low level**: single-hadron response depends on the electromagnetic fraction and
   energy. 3. **Reconstruction**: jet response depends on fragmentation (`pi^0` content)
   and flavor; non-Gaussian low tail. 4. **Signature**: response versus `pT`, `eta`,
   and flavor/constituent composition; low-side tail in `pT_reco/pT_true`. 5. **Reveal**:
   `gamma`+jet or dijet balance, single-hadron `E/p` in data, quark/gluon differences.
6. **Correction**: local hadronic calibration, software compensation, jet energy scale
   from data ([18](18-physics-objects-jets-btagging-met.md)). 7. **Systematic**: flavor
   and composition JES components; single-particle calibration does not equal jet
   calibration. 8. **Physics**: jet-based mass and cross-section slopes; `MET` tails.

## Case 6: RICH refractive-index drift

1. **Defect**: index `n` changes with temperature/pressure/aerogel aging.
2. **Low level**: Cherenkov angle of a given `beta` shifts, photon yield changes.
3. **Reconstruction**: likelihood peaks displaced; species separation degrades; kaon-pion
   swaps in a momentum-dependent way. 4. **Signature**: photon-angle residual mean
   versus run/time, versus momentum; PID efficiency versus run. 5. **Reveal**:
   kinematically identified `K`/`pi`/`p` from `D^*`, `K_s`, `Lambda` versus run.
6. **Correction**: monitored `n(T, P)` per run; refit refractive index; re-derive PID
   calibration. 7. **Systematic**: PID efficiency/mis-ID by period, correlated in time.
8. **Physics**: particle-yield ratios (e.g. `K/pi`), heavy-flavor branching fractions.

## Case 7: TOF clock offset

1. **Defect**: a channel/fill-dependent clock offset or a start-time misassignment
   ([42](42-timing-detectors.md)). 2. **Low level**: times shifted for a subset of
   channels or a run. 3. **Reconstruction**: `beta`/`m^2` shifts; species bands move.
4. **Signature**: time residual for identified muons versus channel/run/`phi`; band
   center versus run. 5. **Reveal**: per-run residual, cross-check with a second start-time
   estimator. 6. **Correction**: per-run/per-channel `t0` and clock-transfer calibration.
7. **Systematic**: residual offset (time-correlated, partially channel-correlated).
8. **Physics**: mis-identified proton/kaon yields, isotope/anti-particle ratios.

## Case 8: Noble-liquid electron-lifetime drift

1. **Defect**: purity degradation (attachment), `tau_e` falls
   ([44](44-noble-liquid-neutrino-and-rare-event-detectors.md)). 2. **Low level**:
   charge signal `S2` (or wire charge) decays with drift time, more at large depth.
3. **Reconstruction**: `z`-dependent energy scale, worse resolution at large depth;
   discrimination leakage changes. 4. **Signature**: charge versus drift time (a
   decaying exponential) and the position dependence of a calibration line versus
   time. 5. **Reveal**: through-going/stopping tracks, calibration line versus
   depth per time bin. 6. **Correction**: time-dependent `tau_e` map applied per event,
   with position-dependent uniformity correction. 7. **Systematic**: `tau_e` uncertainty
   (time-correlated) and its propagation to the energy scale and discrimination.
8. **Physics**: energy scale, threshold efficiency, and hence a rare-event rate limit or
   an oscillation energy spectrum.

**Other cases (same template)**: optical attenuation drift in a light-based detector
(position-dependent light yield); timing-layer radiation damage (LGAD gain loss and
time-resolution degradation); atmospheric uncertainty in air-shower reconstruction
(energy scale and `X_max` bias from aerosol/molecular profile, [32](32-ground-based-detection-arrays.md));
muon-station misalignment (Case 1's structure with a long lever arm, [43](43-muon-systems.md)).

## Reusable checklist for any unfamiliar detector

1. Fill the fourteen questions ([39](39-detector-measurement-framework.md)).
2. Name `x`, `y`, `theta`, `epsilon`; list irreducible fluctuations and correctable
   response variations.
3. Identify the direct observable and the latent inferred quantity; write the identifiability
   and the degeneracy.
4. Identify the natural local object, the global object, and the natural residual.
5. State the topology (sparse points, image, waveform, ring, shower, segment, time series,
   distributed array) and pick the matching reconstruction family.
6. List efficiency, fake, duplicate, mis-ID, migration, and tail mechanisms.
7. State scaling with energy, momentum, angle, occupancy, pileup, dose, rate, time.
8. Name the data-driven calibration/performance samples and the simulation-truth-only quantities.
9. Fill the chain (response -> calibration -> alignment/conditions -> reconstruction ->
   performance -> validation -> systematics) and trace a defect to a physics observable.

## Checklist for reading a performance plot

- Which quantity, and which estimator, center, width, tail definition, and selection?
- Binned in truth or reco? What phase space? Denominator? Matching rule?
- Statistical uncertainty (binomial for efficiencies)? Weighted events?
- Simulation only or data? What proxy and its bias?
- Is there a plateau (insensitive) or a turn-on (sensitive)? Are tails plotted on a log scale?
- Are the two curves compared under equivalent definitions and conditions?
- What is missing: correlations, time dependence, pileup dependence?

## Diagnostic sequence for a data/MC discrepancy

1. Confirm the comparison is like-for-like (selection, weights, pileup, normalization).
2. Check the conditions and period: run/fill dependence, dead channels, conditions tags.
3. Localize it in the chain: raw quantity -> local object -> object -> physics quantity.
4. Look at conditional and joint distributions and tails, not just marginals.
5. Test candidate causes with independent controls (alignment vs timing vs gain vs material).
6. Fix the *cause* (calibration/model), not the symptom (reweighting), and validate on an
   independent sample. 7. Assign a systematic for the remaining freedom.

## Calibration and alignment validation checklist

- Closure on an independent sample; no circularity (do not tune on the measured observable).
- Relative vs absolute, local vs global, in-situ vs external explicitly stated.
- Interval of validity and time dependence monitored; conditions versions recorded.
- Weak modes tested with an independent constraint (resonance mass, cosmics, `E/p`).
- Calibration-alignment coupling checked (timing error vs spatial shift, gain vs energy).
- The stored calibration applied in both data and simulation consistently.

## One-page synthesis: common principles and family exceptions

**Common to all.** Measurements are inverse problems with hidden parameters; response
is not calibration; spread has a floor (stochastic, irreducible) and a systematic part
(correlated, correctable); every performance number is a conditional probability with
a named population; thresholds turn shifts into efficiency; truth is simulation-only;
pulls test uncertainties, not just widths; and systematics are propagated by rerunning
the reconstruction and selection.

**Family exceptions.** Silicon: charge sharing, ghosts, dose. Drift/TPC: ambiguities
(left-right, `t_0`), `r(t)`, distortions. Timing: correlated clock terms do not average.
Cherenkov/DIRC: photon-path and index terms. TRD/`dE/dx`: Landau tails, saturation.
Calorimeters: `e/h`, sampling, leakage, confusion in particle flow. Muons: charge-sign
failure at high `p`, weak modes. Noble liquid: recombination and lifetime.
Rare events: threshold and fiducial mass dominate. Astroparticle: atmosphere/medium
optics as the largest nuisance, exposure replaces acceptance. Emulsion: no timing.

## Self-audit (before submitting a detector analysis)

Can the framework be applied to an uncovered detector? Is every efficiency denominator
unambiguous? Is every resolution tied to estimator, reference, center, width, selection,
tail? Does every pull use the right covariance? Does every data/MC correction state
derivation, applicability, correlation, extrapolation? Can each detector systematic be
traced to a physics observable? Are comparisons made under equivalent definitions?
Are approximations labeled? Are tails and catastrophic failures shown? Are rare-event,
neutrino, astroparticle, timing, and auxiliary systems integrated?

## Common misconceptions and failure modes

- **Fixing the symptom.** Reweighting to hide a calibration/alignment cause.
- **Case-study generalization.** The mechanism transfers; the numbers do not.
- **Skipping the independent control.** Agreement on the tuned observable is not validation.

## Deliverables

- For a real defect: the eight-step trace with the data-driven evidence for each step.
- The filled checklists relevant to the task, with unchecked items marked and justified.
