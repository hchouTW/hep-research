# Multisample PID and Reference PDFs

How a detector that samples one particle many times (tracker, silicon or TRD layers, calorimeter samplings, time
slices) turns the samples into one identification or charge estimate, and how its per-layer reference PDFs are made
from control samples: sources per environment, binning, layer correlations, and the input format of
`<plugin root>/skills/hep-detector/scripts/multisample_pid.py`. This page owns the topic;
[particle identification](particle-identification.md#combining-many-samples) keeps a summary and a link, and owns
the detector technologies and [Combining measurements](particle-identification.md#combining-measurements).

Environments: `COL` collider, `FXT` fixed target and test beam, `SPC` space and high-altitude balloon (sourced);
`UGD`, `GND`, `NUC` are gaps or n/a (table at the end).

Owned elsewhere: generic tag-and-probe and closure,
[Control samples and data-driven methods](data-mc-validation-and-detector-systematics.md#control-samples-and-data-driven-methods);
the "product of likelihoods only if independent" rule for whole subsystems,
[Detector combination and global reconstruction](data-mc-validation-and-detector-systematics.md#detector-combination-and-global-reconstruction);
test-beam versus in-situ constants, [calibration and alignment](calibration-and-alignment.md#test-beam-versus-in-situ-calibration);
background subtraction with sWeights, hep-statistics
[likelihood fitting](../../hep-statistics/references/likelihood-fitting.md#weighted-unbinned-fits-and-sweights);
applying a PID efficiency or scale factor to a signal sample, hep-measurement
[correction chain](../../hep-measurement/references/correction-chain.md#factorized-efficiency); neural-network
estimators and the calibration of model outputs, hep-ml
[multivariate analysis](../../hep-ml/references/multivariate-analysis-bdt-nn.md).

## Relations

- **Per-layer log-likelihood ratio** (exact for known PDFs and independent layers; Neyman-Pearson optimum for two
  simple hypotheses, arXiv:astro-ph/0608641 sec. 5.2; the track likelihood as the product of single-layer
  likelihoods, arXiv:1709.02743 sec. 11.2):

      LLR = sum_l ln[ p_s,l(x_l | theta) / p_b,l(x_l | theta) ]

  `x_l` is the signal in layer `l`, `p_s,l` and `p_b,l` the reference PDFs of the two species in that layer, and
  `theta` the conditions the PDFs depend on (below). With correlated layers the sum is not the likelihood ratio and
  overstates the separation.
- **Geometric-mean normalisation** (a definition, exact; arXiv:astro-ph/0608641 sec. 5.2; arXiv:1706.10182 sec. 3,
  eqs. 5-6):

      Pbar_k = ( prod_{i=1..n} P_k(x_i) )^(1/n),   Lambda_i/j = -ln[ Pbar_i / (Pbar_i + Pbar_j) ]

  with `n` the number of layers that contributed on this track. `ln Pbar_i - ln Pbar_j = LLR / n`, so at fixed `n`
  the estimator orders tracks exactly as the LLR does; across different `n` it puts tracks on one scale, but it is no
  longer the Neyman-Pearson statistic, and performance must be quoted versus `n` (arXiv:1709.02743 sec. 11.2).
- **Conditions of the PDF** (approximate: the list is what the response is known to depend on, not a closed set;
  arXiv:1803.00824 sec. 4, printed p. 7; arXiv:1706.10182 sec. 3, eq. 6): `p_k(x | p or R, eta, layer, occupancy,
  gas pressure, path length, run conditions)`.
- **Binning criterion** (approximate; arXiv:1803.00824 sec. 4, printed p. 7): partition in the parameterising
  variables finely enough that the PDF does not vary significantly within a bin, assuming these variables fully
  parameterise the response; check by splitting bins and by the binning variation below. Between momentum bins,
  interpolate between adjacent references (arXiv:1709.02743 sec. 11.2).
- **Independence check** (a test; arXiv:physics/0402131 sec. 4): predict the `n`-layer performance from the measured
  single-layer distributions and compare with the measured `n`-layer performance. A significant difference in either
  direction indicates layer correlations or mis-modelled single-layer PDFs; agreement shows independence only to the
  stated precision of the comparison. Use a sample not used to build the PDFs, or quote the bias of reusing it
  (reusing the reference sample shapes the performance, arXiv:1709.02743 sec. 11.2, p. 52).

## Control samples by environment

A reference PDF is measured on a sample whose species is known **without** the variable being calibrated, in the
trigger and pre-selection as well as in the offline selection (arXiv:1803.00824 secs. 2 and 4; arXiv:1706.10182
sec. 3). The likelihood rests on detailed knowledge of the response to each species (PDG RPP 2025 *Particle
detectors at accelerators*, sec. 35.6.5); PDFs derived in data improve on simulated ones (arXiv:1908.00005 sec. 6.2).

- **Decay and conversion topology (`COL`; fixed-target `FXT` not sourced).** Pions from `K0S -> pi+ pi-`, protons
  from `Lambda -> p pi-`, electrons from photon conversions in material, selected topologically and with other PID
  detectors (arXiv:1709.02743 sec. 11; arXiv:1803.00824 sec. 4). It needs abundant neutral decays reconstructed inside
  a tracking volume. Control-sample kinematics differ from the signal's (softer `K0S` pions): extend the coverage
  with further decay modes (arXiv:1803.00824 sec. 4, Table 2) and weight the control sample to the signal kinematics
  in the binning variables (eqs. 1-2, printed p. 7); a bin with no control-sample entries cannot be calibrated.
- **Tag-and-probe on resonances (`COL` only).** One leg passes a tight identification, the opposite-charge probe is
  selected with no PID requirement (arXiv:1803.00824 sec. 4); signal PDFs from `Z -> ee` and `J/psi -> ee`
  (arXiv:1908.00005 sec. 6.2); a purity cut on the probe distorts the PDF (below).
- **Charge- and velocity-selected cosmic-ray data (`SPC`; also ground-level data).** An instrument in an untagged
  cosmic-ray flux cuts its control samples out of flight data with its other subdetectors (arXiv:1706.10182 sec. 3):
  the rigidity sign (negative-rigidity muons as the `beta ~ 1` reference, in sea-level data of a balloon instrument,
  arXiv:hep-ex/9805001 sec. 3.1), a velocity cut from TOF (same) or a Cherenkov detector (arXiv:0808.1718 sec. 4.2),
  and a velocity-dependent charge cut in an independent detector (arXiv:1407.1657 sec. 3.3). A velocity cut removes
  a species only in the rigidity range where the velocity bands are still separated, with velocity from a detector
  other than the one calibrated; state the residual contamination (arXiv:hep-ex/9805001 secs. 3 and 3.1).
- **Tagged beams (`FXT`), and transfer to the final instrument (`COL`).** Beam species tagged by threshold
  Cherenkov counters and a lead-glass calorimeter (arXiv:astro-ph/0608641 sec. 4.1;
  arXiv:physics/0402131 sec. 2). Tagged beams are not pure: an inefficient veto can leave pions in a proton beam
  (arXiv:astro-ph/0608641 sec. 5.3.2). Test-beam references serve the final detector once shown to describe its own
  data over the momentum range used (arXiv:1709.02743 sec. 11, Fig. 36); a conversion-electron sample then
  cross-checks the references and sets their systematic (sec. 11.2).

<!-- example: control samples (sources as cited) -->
- ALICE TRD, p-Pb at 5.02 TeV (arXiv:1709.02743v2, sec. 11, p. 46): electrons from conversions and pions from
  `K0S`, selected topologically and with TPC and TOF PID; electron impurity below 1 %. Test-beam distributions for
  1-10 GeV/c electrons and pions (CERN PS, 2004) describe the p-Pb data at 1.9-2.1 GeV/c after one common gain
  factor (Fig. 36, p. 47), and so can serve as references.
- LHCb Run 2 calibration samples (arXiv:1803.00824v1, sec. 4, printed pp. 4-5): `Lambda -> p pi-` and
  `Lambda_c+ -> p K- pi+` protons, `K0S` pions, `J/psi -> mu+ mu-` tag-and-probe; the trigger uses no PID or applies
  it to a particle other than the probe.
- ATLAS electron likelihood, Run 2 (arXiv:1908.00005v2, sec. 6.2, pp. 26-27): signal PDFs from `Z -> ee`
  (`ET > 15 GeV`) and `J/psi -> ee` (`ET < 15 GeV`) tag-and-probe in 36.9 fb^-1 of 2015-2016 data; the loose probe
  requirement rejects about 95 % of the background at 97 % signal efficiency, "causing only a mild distortion".
- AMS-02 TRD on the ISS (arXiv:1706.10182v1, sec. 3, p. 4): species selected with the other subdetectors;
  per-layer lookups built from flight data in a dedicated calibration analysis.
- BESS aerogel counter, sea-level cosmic rays (arXiv:hep-ex/9805001v1, secs. 3-3.1, pp. 8-10): p and mu bands
  separated in `1/beta` (TOF) up to 2.5 GV/c; muons at -10 to -2 GV/c as the `beta ~ 1` reference; below-threshold
  protons at 1.5-2.5 GV/c with `1/beta > 1.1` against muon contamination.
- CREAM-I TRD, balloon (arXiv:0808.1718v1, sec. 4.2, p. 11): oxygen selected close to minimum ionizing with the
  Cherenkov detector, more than six TRD tubes with a usable signal.
- AMS-02 TRD 20-layer prototype, CERN SPS X7 (arXiv:astro-ph/0608641v1, sec. 4.1, p. 3): He and N2 threshold
  Cherenkov counters veto the lighter particles when recording protons or pions.
<!-- /example -->

## Binning, parameterisation and statistics

- **Bin in what the response depends on**: momentum or rigidity, `eta`, layer, occupancy or multiplicity, gas
  pressure, path length; split by run conditions where they change the response (arXiv:1803.00824 sec. 4,
  printed p. 7; arXiv:1706.10182 sec. 3). One PDF averaged over all layers is a stated simplification
  (arXiv:astro-ph/0608641 sec. 5.2), wrong where the response changes with depth (below).
- **Smooth or parameterise** sparse histograms: an adaptive kernel density estimate (arXiv:1908.00005 sec. 6.2), an
  unbinned multi-dimensional KDE in the PID variable, `pT`, `eta` and multiplicity (arXiv:1803.00824 sec. 4,
  printed p. 8), or a fitted shape: (Exponential x Landau) * Gaussian describes measured charge distributions and
  gives their most probable value (arXiv:1709.02743 sec. 11); using such a fit as the reference PDF is a choice to
  check against the high-amplitude tail.
- **Statistics limit the dimension**: each binning variable divides the control sample (arXiv:1709.02743
  sec. 11.2). The binning is a systematic (arXiv:1803.00824 sec. 4, printed p. 9, without a variation scheme): vary
  the bin edges and counts, or the KDE bandwidth and fitted shape, over a stated range and quote the change.
- **Make the PDFs after the gain and time-dependence calibration**, and remake them when it changes
  (arXiv:1709.02743 sec. 11.2).

<!-- example: binning (sources as cited) -->
- ATLAS electron likelihood (arXiv:1908.00005v2, sec. 6.2, p. 26): KDE-smoothed PDFs of typically 13 variables in
  9 bins of `|eta|` and 7 of `ET`.
- ALICE TRD, p-Pb and Pb-Pb (arXiv:1709.02743v2, sec. 11.2, pp. 51-52): references in momentum bins from the p-Pb
  clean samples, interpolated between adjacent bins; above 2 GeV/c the reference statistics limit the gain of the
  multi-dimensional methods (p-Pb, Fig. 43); in Pb-Pb the mean charge deposit changes by about 15 % between central
  and peripheral collisions, so centrality-dependent references were introduced.
- AMS-02 TRD (arXiv:1706.10182v1, sec. 3, eq. 6): `p_k(R, layer, P_Xe, dE, dx)` per species, rigidity, layer, xenon
  partial pressure and path length.
<!-- /example -->

## Layer correlations

The product of per-layer PDFs assumes independent layers. Thick-module detectors respond nearly independently (PDG
RPP 2025 *Particle detectors at accelerators*, sec. 35.6.5); layers differ or correlate through:

- **Signal build-up with depth.** In a fine-grained TRD, TR photons pass several layers before absorption, so the
  electron response rises with depth while the hadron response stays flat (PDG RPP 2025 sec. 35.6.5;
  arXiv:1706.10182 sec. 3); per-layer performance improves with depth (arXiv:physics/0402131 sec. 4). Layers are then
  not identical and may not be independent: use per-layer PDFs, and test independence with the `n`-layer test above
  (the same prototype study found no sign of correlation over its four layers).
- **Correlated samples of one layer.** Amplitudes in successive time slices of one chamber are highly correlated and
  cannot enter a likelihood as independent terms (arXiv:physics/0402131 sec. 4); combine them into a few charge sums
  and build a joint (multi-dimensional) PDF of the sums (arXiv:1709.02743 sec. 11.2).
- **Shared track quantities**: momentum, path length, common-mode calibration.
- **Variables generated independently lose their correlations**: resampling each PID variable of a track separately
  from its PDF reproduces no correlation between them, so only one such variable per track can be used
  (arXiv:1803.00824 sec. 4, printed p. 8).

<!-- example: layer dependence (sources as cited) -->
- AMS-02 TRD (arXiv:1706.10182v1, sec. 3, p. 4): proton and helium mean deposits roughly constant across layers,
  electron deposits rising with depth; layers 5 and 17 have less radiator; the two bottom layers are raised by
  backsplash.
- ALICE TRD prototypes (arXiv:physics/0402131v1, sec. 4 and Fig. 4, pp. 3-4): pion efficiency predicted from single
  layers agrees with the measured one for up to the four prototype layers; the six-layer value is extrapolated;
  per-layer pion rejection improves substantially from layer 1 to layer 4.
- ALICE TRD (arXiv:1709.02743v2, sec. 11.2, p. 51): LQ2D combines the first four and the last three of seven time
  slices into two charge bins; LQ7D and the neural network use all seven, and each charge bin must hold a deposit,
  which for LQ7D loses about 40 % of electrons.
<!-- /example -->

## Contamination and selection bias of the control sample

- Measure the purity and state it (arXiv:1709.02743 sec. 11); subtract the residual background statistically with
  sWeights from a fit to a discriminating variable, which must be uncorrelated with the PID variables
  (arXiv:1803.00824 sec. 4, printed pp. 6-7; method in hep-statistics, linked above).
- A purity cut on the PID variable itself, or on a correlated one, biases the PDF. If one is needed, it is an
  exception to the selection rule above: quantify it (background rejection and signal efficiency of the cut) and
  measure the distortion it causes, for example by varying the cut (arXiv:1908.00005 sec. 6.2).
- Cross-check with an independently selected sample: apply the same selection to a sample chosen by different
  detectors and compare (arXiv:1407.1657 sec. 3.2).

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Hadron and electron references at a collider | `V0` and conversion samples | topological selection; the calibrated variable (or a correlated one) unused on the probe in trigger, pre-selection and offline; other PID detectors only if uncorrelated with it | kinematics unlike the signal; impurity | COL |
| Electron or muon references at a collider | tag-and-probe on a resonance | tight tag, probe without PID, mass fit | probe purity cut distorts the PDF | COL |
| Untagged cosmic-ray flux | charge- and velocity-selected cosmic-ray data | independent charge and velocity detectors; separated velocity bands | the selecting detector shares the variable; heavier-species contamination | SPC |
| Before data exist, or for a new design | tagged test beam | beam counters; same gas, electronics and geometry | veto inefficiency, beam contamination; response differs in the final detector: validate on its data before use | FXT, COL |
| Sparse control sample | KDE or fitted shape; fewer bins | smoothing preserves the tails | over-smoothing erases the tails | COL, FXT |
| Tracks with different numbers of layers | geometric mean, or LLR quoted per `n` | per-layer PDFs | one threshold across `n` mixes efficiencies | SPC, FXT, COL |
| Correlated samples within a layer | sums into a few bins, joint PDF | statistics for the joint PDF | treating slices as independent overstates rejection | FXT, COL |
| Response changing with depth (build-up) | per-layer PDFs; `n`-layer versus single-layer test | per-layer control samples | one PDF misstates each layer; product overstates rejection if layers correlate | COL, SPC, FXT |

## Distinctive but generalizable features (multisample PID)

- **Topology**: one particle, `N` samples along its path, already assigned to the track (example below).
- **Inverse problem**: species (or charge) from `N` noisy samples; the product of per-layer PDFs is optimal only for
  independent layers.
- **Natural objects**: per-layer PDF per species and condition bin; per-track LLR or normalised estimator.
- **Informative residual/closure**: measured `n`-layer performance against the single-layer prediction.
- **Scaling**: separation grows with `N`, less for correlated layers; it falls as layers drop out.
- **Conventions**: LLR sign and log base; normalisation by `n` or not; rejection = 1/(background species'
  mis-identification efficiency) at a stated signal efficiency.
- **Tails**: the separating information sits in the high-amplitude tails, where the control samples are thinnest.
- **Dependence**: momentum, `eta`, layer, occupancy, gas pressure, path length, run conditions.
- **Data sample**: control samples selected without the variable; simulation validates, it does not replace them.
- **Transfers**: test-beam references to the instrument, or PDFs across run periods, only after a check on the
  target data.

## Common misconceptions and failure modes

- **Templates from simulation alone**, or from a sample selected with the variable being calibrated.
- **One PDF for all layers** where the response changes with depth; **correlated slices or layers summed** as
  independent.
- **One LLR threshold across tracks with different numbers of layers**, unstated.
- **PDF edges that cut the high-amplitude tail**, where a TRD signal shows up: `multisample_pid.py likelihood` skips
  such values with status `ok` and only a warning, so the most signal-like tracks lose their strongest terms. Close
  the top with an overflow bin over the full signal range and treat a non-zero out-of-edge count as a failure.
- **Binning or smoothing never varied** (bin edges and counts, KDE bandwidth or fitted shape, over a stated range).
- **PDFs kept after a gain recalibration** that changed the response.

## Deliverables

- Per species and environment: the control sample, its selection (not using the variable), purity, background
  subtraction.
- PDF binning variables and edges, smoothing, statistics per bin, binning systematic.
- Whether PDFs are per layer, and the evidence for or against layer independence (the `n`-layer test).
- The estimator (LLR, normalised geometric mean, joint PDF), its convention, and performance versus the number of
  contributing layers, at a stated signal efficiency.
- The calibration and conditions version behind the PDFs.

## Tool hooks

`multisample_pid.py` (standard library only) does both standard combinations with every choice stated.

**Input format.** Events CSV: one row per particle, one column per layer (`--layers a,b,c`); `#` lines are skipped;
every named cell must be finite (empty or `nan` is rejected). No missing-layer marker: run each layer set
separately. `charge` takes `--response` JSON `{"z2": [...], "signal": [...]}`, strictly increasing in both (a flat
plateau is rejected), `--path-column` of `cos(theta)` (or `--no-path-correction`) and optionally `--true-z-column`.
`likelihood` takes `--pdfs` JSON, `{"edges", "signal", "background"}` for all layers or
`{"layers": {"<column>": {...}}}` (a missing layer falls back to the top-level keys): strictly increasing edges,
non-negative bin contents (counts are fine) with a positive sum, normalised by the tool to densities.
`--label-column` (1 signal, 0 background) adds the efficiency - mis-identification curve.

**What it does** (the script's docstring is the full statement).

- **Charge from many dE/dx samples** (`charge`): path-length correction (signal x cos(theta); skipping it must be
  said), inversion through the measured response curve Z^2 -> signal, which may flatten but must stay strictly
  increasing (never a pure Z^2 law) and gives the most probable signal, the Moyal location, not the larger mean (PDG
  RPP 2025 secs. 34.2.3 and 35.6.4). Combination by truncated mean, weighted mean (1/sigma^2, or generalized least
  squares with a declared common correlation) or likelihood (Moyal densities; a maximum at the scan edge is counted,
  at_z_range_edge, not returned); out-of-table events are counted (out_of_range). With `--true-z-column`: peak,
  sigma68, tail fraction and the **leakage matrix** P(reco | true) with Clopper-Pearson intervals, a
  species-migration block for hep-measurement and hep-statistics that travels with its selection. `--toys` predicts
  the core width; the response table must cover the per-layer tail (toys_requested, toys_used).
- **Log-likelihood ratio from per-layer PDFs** (`likelihood`): the plain LLR sum above, with the efficiency -
  mis-identification curve and Clopper-Pearson intervals. A value outside the PDF edges contributes no term
  (skipped, counted in a warning, status still `ok`); an empty bin gets a floor of 1e-12 of the largest density.
- **Correlations.** Only `charge --method weighted-mean` takes one (`--correlation`); every other mode says
  "independence assumed".

**Limits of the current tool**: PDFs are one-dimensional per layer, so binned PDFs need one run per bin; the LLR is
not normalised by the number of layers; `likelihood` models no layer correlation, so run the `n`-layer test yourself.

**Negative control.** `likelihood` with identical signal and background PDFs must give LLR = 0 for every event and
efficiency equal to mis-identification at every threshold. It passes whatever the lookup does, so add a positive
control (PDFs with known per-bin log ratios give the known per-event LLR) and a swap control (exchanging signal
and background flips the sign of every LLR).

**Statuses.** JSON `status` (`ok`, or `rejected` with exit code 2 for invalid input), `status_label` (`--status`,
default `unvalidated`), `label: "[General method]"`, `defaults_used`, and `warnings` (out-of-edge values, floored
bins, dropped events), which must be read.

<!-- example: source citation -->
Assigning samples to the track. In the ALICE TRD (arXiv:1709.02743v2, secs. 8-8.2), a TPC seed track is propagated
to each chamber, the clusters near the intersection form a tracklet (a straight-line fit), and the Kalman filter
updates the track with it; imperfect ion-tail cancellation biases tracklet positions differently by charge sign.
<!-- /example -->

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Per-layer PDFs from control samples | arxiv_1709.02743, arxiv_1803.00824 | arxiv_astro-ph_0608641 | arxiv_1706.10182 | gap | n/a: no per-layer samples of one particle; see [ground-based detection arrays](ground-based-detection-arrays.md) | gap |
| `V0` and conversion samples | arxiv_1709.02743, arxiv_1803.00824 | gap: fixed-target `V0` samples not sourced; test beams use tagged beams | n/a: no reconstructable `V0` source; charge and velocity selection instead | gap | n/a: as above | gap |
| Tag-and-probe on resonances | arxiv_1803.00824, arxiv_1908.00005 | n/a: tagged beams instead | n/a: no reconstructed resonances in the flux | gap | n/a: as above | gap |
| Charge- and velocity-selected cosmic-ray data | arxiv_1709.02743 (cosmic-ray muons selected by flight direction) | n/a: beam is tagged | arxiv_1706.10182, arxiv_hep-ex_9805001 (sea-level data of a balloon instrument), arxiv_1407.1657, arxiv_0808.1718 | gap | n/a: as above | n/a: beams are tagged |
| Tagged beams and transfer to the instrument | arxiv_1709.02743 | arxiv_astro-ph_0608641, arxiv_physics_0402131 | gap | gap | n/a: as above | gap |
| Binning and parameterisation | arxiv_1803.00824, arxiv_1908.00005, arxiv_1709.02743 | arxiv_astro-ph_0608641 | arxiv_1706.10182 | gap | n/a: as above | gap |
| Layer correlations | arxiv_1709.02743, arxiv_1803.00824, pdg_2025_particle-detectors-at-accelerators | arxiv_physics_0402131 | arxiv_1706.10182 | gap | n/a: as above | gap |
| Variable number of layers | arxiv_1709.02743 | arxiv_astro-ph_0608641 | arxiv_1706.10182 | gap | n/a: as above | gap |
| Control-sample contamination | arxiv_1709.02743, arxiv_1803.00824, arxiv_1908.00005 | arxiv_astro-ph_0608641 | arxiv_1407.1657, arxiv_hep-ex_9805001 | gap | n/a: as above | gap |
| `multisample_pid.py` input format | n/a: plugin format, documented from the script | n/a | n/a | n/a | n/a | n/a |

`V0` and conversion samples and tag-and-probe are sourced only at colliders; charge- and velocity-selected
cosmic-ray data mainly in space and balloon flight, also at sea level (arXiv:hep-ex/9805001 sec. 3) and with
cosmic-ray muons at a collider (arXiv:1709.02743 sec. 11); the other rows hold their analogues. Dense-detector
stopping-track identification (`UGD`) is in [noble-liquid, neutrino and rare-event detectors](noble-liquid-neutrino-and-rare-event-detectors.md);
its control samples are a gap here.

## Citations

Full titles and annotations are in the bibliography.

<!-- example: citations -->
- ALICE Collaboration, NIM A 881 (2018) 88 (arXiv:1709.02743).
- R. Aaij et al. (LHCb), EPJ Tech. Instrum. 6 (2019) 1 (arXiv:1803.00824).
- ATLAS Collaboration, JINST 14 (2019) P12006 (arXiv:1908.00005).
- T. Raiha et al. (AMS-02 TRD), NIM A 868 (2017) 10 (arXiv:1706.10182).
- P. v. Doetinchem et al. (AMS-02 TRD), NIM A 558 (2006) 526 (arXiv:astro-ph/0608641).
- A. Andronic et al. (ALICE TRD), NIM A 522 (2004) 40 (arXiv:physics/0402131).
- Y. Asaoka et al. (BESS), NIM A 416 (1998) 236 (arXiv:hep-ex/9805001).
- O. Adriani et al. (PAMELA), ApJ 791 (2014) 93 (arXiv:1407.1657).
- H. S. Ahn et al. (CREAM), Astropart. Phys. 30 (2008) 133 (arXiv:0808.1718).
- PDG RPP 2025, *Particle detectors at accelerators* (general section of the bibliography).
<!-- /example -->
