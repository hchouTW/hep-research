# Cherenkov Ring Reconstruction

From photon hits on a pixelated plane and a track (or none) to a Cherenkov angle, a velocity, a likelihood per
mass hypothesis and a charge. Radiators, photosensors, threshold and differential counters:
[Cherenkov imaging variants](cherenkov-imaging-variants-and-photosensors.md); emission and yield:
[signal formation](signal-formation-and-readout.md); threshold, saturation, resolution budget and isotope mass
(separation power only in performance metrics, below): [particle identification](particle-identification.md#ring-imaging-cherenkov-detectors-rich);
DIRC and time-of-propagation counters: [DIRC and TOP reconstruction](dirc-and-time-of-propagation-reconstruction.md);
large-volume water, ice and air-Cherenkov likelihoods (a sibling, not re-derived here):
[photon-counting likelihood](photon-likelihood-reconstruction.md); mirror alignment and refractive index from data:
[in-situ calibration](in-situ-calibration-methods.md#ring-imaging-cherenkov-detectors); separation power and ROC:
[performance metrics](performance-metrics-and-residual-diagnostics.md); core-plus-tail shapes:
[resolution shape models](resolution-shape-models.md); combining the RICH likelihood with other detectors:
[particle identification](particle-identification.md#combining-measurements). Simcal of RICH optics is
hep-statistics' ([RICH simcal](simulation-calibration/rich.md)); learned PID combination is hep-ml's.

Environments: COL collider; FXT fixed target, test beam; SPC space, balloon; UGD underground; GND ground arrays;
NUC nuclear. Refractive index `n(lambda)` per radiator tile, radiator thickness, expansion gap, mirror geometry,
pixel size, track multiplicity, background rate and start-time source are parameters. Source IDs: `arxiv_<id>` is
arXiv:<id> (`/` as `_`); `pdg_2025_<review>` a PDG 2025 review. Pages are PDF pages.

## Relations (with source locators)

- **Cherenkov angle** (exact; pdg_2025_particle-detectors-at-accelerators sec. 35.5, eq. 35.5):
  `cos theta_c = 1 / (n(E) beta)`.
- **Yield** (exact for the stated efficiency `eps(E)`; sec. 35.5, eqs. 35.6-35.8, p. 19):
  `N_pe = L (alpha^2 z^2 / (r_e m_e c^2)) integral eps(E) sin^2 theta_c dE`, with
  `alpha^2/(r_e m_e c^2) = 370 cm^-1 eV^-1`; `N_pe ≈ L N_0 <sin^2 theta_c>` for `z = 1`. In a ring model `eps`
  factorizes into radiator transmission, the visible fraction of the ring, light-guide and photodetection
  efficiencies, all but the last depending on the track (arXiv:hep-ex/0210044 sec. 3, eq. 5, p. 4); the expected
  count `N_h` adds expected background hits (arXiv:2008.06251 sec. 3, p. 7).
- **Charge from the yield** (approximate: event-by-event efficiency, normalisation from a calibration sample;
  arXiv:0709.2154 eq. 3, p. 3; arXiv:hep-ex/0210044 eqs. 4-6, pp. 4-5):
  `Z^2 = N_pe / N_0 ∝ N_pe / (eps_tot DeltaL sin^2 theta_c)`, `N_0` here the expected count for `Z = 1` (not the
  quality factor above), `eps_tot` integrated over radiator depth, visible
  azimuth and reflected and direct branches; the geometric part is `Delta phi / 2 pi` of the ring.
- **Per-pixel Poisson likelihood** (exact for independent Poisson pixels; arXiv:2008.06251 sec. 3, eqs. 2-5,
  pp. 6-7; arXiv:2603.13000 sec. 2.1, eqs. 1-2, p. 2): `L_h = prod_i P(m_i | n_h,i)` over all live pixels,
  `n_h,i` the hypothesis PDF integrated over pixel `i` plus background. With binary pixels
  `P(no hit) = exp(-n)`, so `ln L_h = -N_h + sum_hit [n_h,i + ln(1 - exp(-n_h,i))]`, `N_h = sum_all n_h,i`: only
  hit pixels need evaluating. The review prints the hit sum without the `n_h,i` term (eq. 3, as extracted); with
  `N_h` over all pixels that drops a hypothesis-dependent term, so derive the form, do not copy it.
- **Likelihood ratio** (a definition; arXiv:2008.06251 eqs. 6-7, p. 7): `R_K/pi = L_K / (L_K + L_pi)`.
- **Velocity likelihood** (approximate: Gaussian residuals, flat background; arXiv:hep-ex/0210044 sec. 2,
  eqs. 2-3, pp. 2-3; arXiv:0709.2154 pp. 2-3): per hit, `p(r) = (1 - b) G(r; sigma) + b/D` with `r` the distance
  from the hit to the pattern predicted for `theta_c`, `b` the background fraction and `D` an effective
  length; `L(theta_c) = prod_i p_i[r_i(theta_c)]^(n_i)` (`n_i` photoelectrons per hit), maximized over `theta_c`
  (a velocity, not a discrete hypothesis). A second, wider Gaussian takes forward-scattered photons. Mass from
  `beta` and momentum: `Delta m/m = (Delta p/p) (+) gamma^2 (Delta beta/beta)` (arXiv:0709.2154 p. 2).
- **Average-angle likelihood** (approximate: Gaussian average-angle distribution, resolution independent of
  species; arXiv:physics/0104033 sec. 4.3, eqs. 10-11, p. 16): in a window `theta_th +- 4 sigma_theta`,
  `L(<theta>) = exp(-(theta_th - <theta>)^2 / (2 sigma_<theta>^2))`, `sigma_<theta> = sigma_theta / sqrt(N)`,
  defined for `N > 0` and with no count term, while an empty window (`N = 0`) and a hypothesis below threshold (no
  `theta_th`) need an explicit rule, and a count term `P(N | expected yield plus background)`, if used, multiplies
  every hypothesis's term for every `N`, so that `N = 0` is its limit (not in the source);
  radiator likelihoods are multiplied.
- **Per-track resolution** (approximate; pdg_2025_particle-detectors-at-accelerators sec. 35.5, eqs. 35.11-35.12,
  p. 21): `sigma(theta_c) = <sigma(theta_i)>/sqrt(N_pe) (+) C`, `C` collecting tracking, alignment, scattering, hit
  ambiguities, random background and other tracks; `delta beta = sigma(beta)/beta = tan theta_c sigma(theta_c)`, the
  source's fractional error. The `1/sqrt(N)`
  scaling holds only without correlated errors (arXiv:hep-ex/0010068 eq. 1, p. 3). A momentum-dependent width
  `sigma_PDF(p) = sqrt((A/p)^2 + B^2)`, added in quadrature to a constant pad term (arXiv:2008.06251 sec. 3.2.2,
  eq. 8, p. 9; motivated by multiple scattering).
- **Spherical-mirror inverse ray tracing** (exact for one spherical mirror and a known emission point;
  arXiv:physics/0104033 sec. 4.2, eqs. 3-9, pp. 14-15): with mirror centre `C`, radius `R`, emission point `E`
  (`|CE| = a`), detection point `D` (`|CD| = d`, angle `alpha` to `CE`), the reflection point at angle `beta_S`
  satisfies `a d sin(alpha - 2 beta_S) + R (a sin beta_S - d sin(alpha - beta_S)) = 0`, solved by Newton-Raphson
  from `alpha/2` (about three iterations); `theta_c` is the angle between the track and `ES`. The same reflection
  condition is solved as a quartic equation for the full mirror system, with the emission point at the middle of
  the track in the radiator (arXiv:1611.00296, section "RICH optical layout and reconstruction", p. 1).
- **Hough ring parameters** (exact for circles; arXiv:2603.13000 sec. 2.3, eq. 4, pp. 3-4):
  `(x_i - x_0)^2 + (y_i - y_0)^2 - r^2 = 0` per hit, accumulated in `(x_0, y_0, r)`; generalizes to ellipses.

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Track known, discrete species | Per-pixel Poisson (binary) likelihood per hypothesis; ratios or `Delta ln L` | Track at the radiator, `n(lambda)`, PDF tuned on control samples of known species | Unhit pixels dropped; PDF width from another momentum; dead pixels counted as unhit | COL (arXiv:2008.06251 sec. 3; arXiv:2603.13000 sec. 2.1); FXT: none read for a RICH; a DIRC's per-photon angle likelihood (arXiv:2002.07990 sec. 3, pp. 5-6) is on the [DIRC page](dirc-and-time-of-propagation-reconstruction.md) |
| Continuous velocity (nuclei, isotopes) | Per-hit residual PDF, `L(theta_c)` maximized; or per-hit `beta`, then the most probable hit cluster, mean weighted by signal amplitude | Track direction gives the mean emission point; reflected branches modelled | Background fraction varies event to event (arXiv:hep-ex/0210044 abstract); mirror branches missed | SPC only in the sources read (arXiv:hep-ex/0210044 sec. 2; arXiv:0709.2154 p. 2) |
| Sparse rings, yields varying over the acceptance | Average angle in a window per hypothesis, Gaussian likelihood | Single-photon resolution per radiator | Window width a free parameter (arXiv:physics/0104033 sec. 4.3) | FXT only in the sources read (arXiv:physics/0104033 sec. 4.3) |
| Proximity focusing | Back-trace each hit from the mean emission point; thin radiator, expansion gap; a focusing multi-layer radiator (index rising downstream) to overlap the layers' rings | Thickness and gap known; flat detection plane | Emission-point term dominates for a thick radiator | COL (arXiv:2008.06251 sec. 2.2.1; arXiv:0805.0737 abstract); SPC (arXiv:hep-ex/0210044 sec. 1) |
| Mirror focusing | Per-hit inverse ray tracing (iterative or quartic), not a circle fit: images on a flat plane are distorted ellipses | Mirror geometry and alignment ([in-situ calibration](in-situ-calibration-methods.md#ring-imaging-cherenkov-detectors)) | Circle fit (arXiv:physics/0104033 sec. 4.1); misaligned segments | COL (arXiv:1611.00296 p. 1); FXT (arXiv:physics/0104033 sec. 4.2) |
| Several radiators | Each hit reconstructed under each radiator's emission point; per-radiator spectra; likelihoods multiplied. Tiled radiators side by side: the track position picks one | Index and geometry per radiator and tile | Wrong radiator hypothesis where indices are close (inferred: with very different indices it is rarely a problem, arXiv:physics/0104033 sec. 4.2); refraction at boundaries | COL (arXiv:1211.6759 sec. 2.1); FXT (arXiv:physics/0104033 secs. 4.2-4.3); SPC (arXiv:0709.2154 p. 2) |
| Many overlapping rings | Global event likelihood: start from the most abundant species, change the one track hypothesis that most raises `ln L`, repeat; background per photodetector from the excess over expectation; iterate both | High multiplicity, ring overlap | Cost grows exponentially with the number of tracks without search shortcuts | COL only in the sources read (arXiv:1211.6759 sec. 5.1; arXiv:2603.13000 sec. 2.2): a condition (overlap), not a rule |
| Few tracks, noise-dominated background | Local (track-by-track) likelihood with a background term | Background model | Overlaps misassigned if multiplicity grows | No named instance: a hedged general remark (arXiv:2603.13000 sec. 2.2). Not FXT: few tracks there, but small noise and no background term in the likelihood (arXiv:physics/0104033 secs. 4.3, 6.2, pp. 16, 19) |
| Ring finding with a track | Track-seeded window, or a Hough transform of pad coordinates into Cherenkov-angle space | Track extrapolated to the radiator | Elliptical images at incidence; offsets of the mirror the track points to | COL (arXiv:nucl-ex/0211028 pp. 5-6); FXT, track-seeded ring fit (arXiv:1809.04026 sec. 3.1, p. 6) |
| Ring finding without a track | Standalone ring fit or Hough accumulator, then likelihood or local fit | Hits only; global offsets subtracted | Ghost rings from background; no species | FXT (arXiv:1809.04026 sec. 3.1, p. 6); COL (arXiv:2603.13000 sec. 2.3) |
| Background | Track-correlated: window light, delta rays; scattered and reflected photons either a broad signal component scaled with the hypothesis yield (arXiv:2008.06251 sec. 3.1) or background (arXiv:physics/0104033 sec. 6.2; arXiv:hep-ex/0210044 sec. 2): state which. Random (noise, dark counts, other tracks): uniform, its level from off-time hits; per photodetector from the excess over the expected signal, iterated with the hypotheses (arXiv:1211.6759 sec. 5.1); or a flat fraction `b` in hit residual (arXiv:hep-ex/0210044 sec. 2) | Readout window wider than the signal; or the expected signal per photodetector; or residuals beyond the signal width | One flat level for all pixels when rates vary (assumed because random hits are small, arXiv:2008.06251 sec. 3.2.3, p. 9); a fraction varying event to event (arXiv:hep-ex/0210044 abstract); in-time light of other tracks is absent from off-time bins (inferred; at overlap use the global likelihood); sparse rings swamped (arXiv:physics/0104033 p. 13) | COL (arXiv:2008.06251 secs. 3.1, 3.2.3, pp. 7-9; arXiv:1211.6759 sec. 5.1); SPC (arXiv:hep-ex/0210044 sec. 2); FXT: gap for a level model, sources only listed (arXiv:physics/0104033 sec. 6.2, p. 19) |
| Charge | `Z^2` from photoelectrons near the pattern, corrected by the event's efficiency | Velocity first; visible-ring fraction above a cut | Efficiency from the average, not the event | SPC only in the sources read (arXiv:hep-ex/0210044 sec. 3; arXiv:0709.2154 p. 3); COL uses `N_h` in the likelihood, not for charge (arXiv:2008.06251 sec. 3) |

Sources of the per-pixel efficiency: photosensor magnetic-field and immersion effects
([photosensors](cherenkov-imaging-variants-and-photosensors.md#photosensors-and-light-transport), paragraph
"Magnetic fields and immersion"). Night-sky light
reaches only sky-viewing cameras (GND): a background-rate parameter here
([imaging atmospheric Cherenkov](imaging-atmospheric-cherenkov.md)). Coherent radio (Askaryan) emission is not imaged
as rings ([signal formation](signal-formation-and-readout.md#light-scintillation-wavelength-shifting-attenuation),
its Askaryan paragraph, air-shower radio in
[ground-based arrays](ground-based-detection-arrays.md#radio-reconstruction)).

<!-- example: named apparatus and their numbers -->
- Belle II ARICH (COL): dual-layer aerogel, `n = 1.045` and `1.055` (difference kept at 0.010 +- 0.002), HAPDs
  in 1.5 T; six hypotheses; PDF a narrow and a broad (about 5%) Gaussian, window-photon and delta-ray background
  plus uniform random hits, 1.4e-4 per pixel and event from off-time bins; pad term 6.4 mrad; 11.4 detected photons
  for high-momentum muons (arXiv:2008.06251 secs. 2.2, 3-3.2.3, Fig. 5, pp. 4-9).
- AMS-02 RICH (SPC): proximity focusing, 25 mm aerogel (`n = 1.05`) and 5 mm NaF (`n = 1.334`) tiles, NaF crossed
  by about 11% of events; signal widths 0.37 and 1.35 cm (fractions about 3/4, 1/4), hits beyond 2.1 cm
  background (`b` 77%, `D` 134 cm); `sigma(beta)` floor about 2e-4 from pixelization (arXiv:0709.2154 pp. 1-3).
  Earlier design study (3 cm, `n = 1.03`): `sigma = 0.5 cm`, single-hit 5 mrad, `Delta beta/beta` near 0.1% for
  protons (arXiv:hep-ex/0210044 secs. 2-3, pp. 2-3).
- HERMES dual-radiator RICH (FXT): aerogel and gas, mirror-focused onto a flat PMT plane; about 10 hits on an
  aerogel ring, 12 of 23 touched PMTs firing on a gas ring (arXiv:physics/0104033 sec. 4.1, p. 13).
- LHCb RICH 1 and 2 (COL): C4F10 with a 50 mm aerogel wall (`n = 1.03`), CF4; global event likelihood starting
  from all pions, two iterations with the background (arXiv:1211.6759 secs. 2.1, 5.1; arXiv:1611.00296 p. 1);
  about 50 tracks per event, about 5000 steps (arXiv:2603.13000 sec. 2.2).
- ALICE HMPID (COL): proximity focusing, liquid C6F14, CsI-coated MWPCs (arXiv:0805.0737 abstract).
- STAR-RICH (COL): track-seeded Hough in Cherenkov-angle space, pad occupancy below 5% (arXiv:nucl-ex/0211028 p. 5).
- NA62 RICH (FXT): standalone ring fit after global mirror offsets, track-seeded fit with the pointed mirror's
  offset (arXiv:1809.04026 sec. 3.1, p. 6).
<!-- /example -->

## Distinctive but generalizable features (ring reconstruction)

- **Topology**: a partial, often distorted ring of few photons per track and radiator, on a plane shared by
  other tracks' rings and background.
- **Inverse problem**: `beta` (or species, given momentum) and, from the yield, `Z`; degeneracies: emission point
  versus chromatic spread, radiator hypothesis, ring overlap, mirror branch.
- **Natural objects**: hit, per-hit angle under a radiator hypothesis, ring candidate, track `theta_c`,
  `ln L` per hypothesis (discrete species) or `L(beta)` per track (continuous velocity, `theta_c` per radiator from
  `cos theta_c = 1/(n beta)`), `Z^2` from the yield. **Informative residual**: per-photon `theta_i - theta_h` (peak, width, background
  pedestal), versus azimuth around the track (alignment) and momentum; observed versus expected photon count.
- **Scaling**: Relations, each within its domain.
- **Conventions**: `Delta ln L` against a stated reference hypothesis; angles in rad; whether `N_h` includes
  background.
- **Tails**: wrong ring or radiator, scattered photons, decays and interactions before the radiator, low-yield
  tracks near threshold.
- **Dependence**: `n(lambda, T, P)`, aerogel transmission, mirror alignment, pixel efficiency, occupancy.
- **Data sample**: kinematically identified decays and dimuons (COL); tagged beams or exclusive reactions (FXT);
  flight nuclei selected by other detectors (SPC; [multisample PID](multisample-pid-and-reference-pdfs.md)).
- **Transfers**: the binary-pixel likelihood, inverse ray tracing, the background split. **Does not transfer**:
  a PDF tuned at one momentum, multiplicity or occupancy; the global search's start hypothesis.

## Common misconceptions and failure modes

- **Fitting circles to mirror images.** Flat planes off the focal surface give distorted ellipses.
- **`sigma_photon/sqrt(N)` alone.** Correlated terms set a floor; quote the measured per-track width.
- **Global likelihood as the rule.** It pays where rings overlap; where noise or uncorrelated background dominates,
  a local one with an appropriate background description may provide comparable performance at much lower cost
  (arXiv:2603.13000 sec. 2.2, hedged there); check it at the
  multiplicity at hand.
- **One average efficiency for charge.** The visible ring fraction changes from event to event.
- **Discrete hypotheses for nuclei.** Unknown `Z` and isotopes need the velocity form.

## Deliverables

- Radiator and optics model (index per tile with monitoring, emission-point and mirror treatment).
- The likelihood form, its PDF components, the background model and how its level is set.
- Per-photon and per-track widths versus momentum, from control samples, and the expected-to-observed yield map.
- Ring-finding and association efficiency and misassociation rate, versus multiplicity.
- PID efficiency and misidentification at the stated cut, or `beta` and `Z` resolution.

## Tool hooks

- **Inputs**: tracks at the radiator (position, direction, momentum, covariance); hypotheses (masses, `Z`);
  radiators (`n(lambda)` per tile with its temperature, pressure or monitoring dependence, thickness, transmission
  per tile as absorption and scattering lengths, emission-point model); optics (mirror centres, radii, alignment,
  planes); pixel map (position, size, live flag, efficiency); hits (pixel, photoelectrons, time and window);
  background model or rate per pixel.
- **Outputs**: per track and radiator: `ln L` per hypothesis, `Delta ln L`, `theta_c` and `sigma`, expected and
  observed counts, background estimate, `Z^2` with `eps_tot`; per hit: angle per radiator hypothesis.
- **Conventions**: rad; natural log; `Delta ln L = ln L_h - ln L_ref`.
- **Closure and negative control** (required, for each output path), on identified tracks disjoint from the
  samples that tuned the PDF and normalised `N_0`: kinematically identified decays (discrete path) or nuclei
  selected by other detectors (velocity and charge path). Discrete hypotheses: each delivered species is the true
  species on its own sample, over the hypothesis set used downstream, fixed in advance, and in each momentum bin
  where the separation expected from the measured per-track width (not from the PDF under test) exceeds a value
  fixed in advance, the median `Delta ln L(true - h)` must exceed a margin fixed in advance for every other
  hypothesis `h`, the worst pair deciding, and the fraction of tracks below the working-point cut must not exceed
  the rate expected from the measured width by more than a margin fixed in advance. The negative control reruns
  the bin once per `h` with each momentum scaled by `m_h/m_true` (same `beta` under `h`), and each rerun must
  fail: its median `Delta ln L(true - h)` at or below zero. Velocity
  and charge: per bin, on nuclei of one identified `Z` and isotope (or with `beta` from an independent detector),
  the mean and width of the `beta` pulls against `beta` from momentum and that mass, and the `Z^2` peak positions,
  must lie within margins fixed in advance; the velocity control scales each momentum by a factor fixed in
  advance, only in bins where that moves the expected `beta` by more than a stated number of `sigma(beta)` (other
  bins are listed, not failed), and the charge control scales `N_0` by a factor fixed in advance, each of which
  must fail. A bin below a count fixed in advance is `inconclusive` first;
  otherwise `failed` if the check fails or the control for any `h` or perturbed input passes, else `passed`.
  The check takes the worst bin (failed, then inconclusive, then passed), and is `inconclusive` if no bin
  qualifies or the qualifying bins miss the momentum range in use. Count, margins and threshold are recorded before
  the check runs; `inconclusive` is not a pass.
- **Statuses**: per track `ok`, `below-threshold` (no hypothesis radiates), `no-ring`, `overlap`,
  `out-of-acceptance`; per check `passed`, `failed`, `inconclusive`.

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Per-pixel or per-hit likelihood | arxiv_2008.06251, arxiv_2603.13000 | gap for a RICH per hit: arxiv_physics_0104033 is per track (average angle), arxiv_2002.07990 a DIRC | arxiv_hep-ex_0210044, arxiv_0709.2154 | [photon-counting likelihood](photon-likelihood-reconstruction.md) | [photon-counting likelihood](photon-likelihood-reconstruction.md) | gap |
| Proximity focusing | arxiv_2008.06251, arxiv_0805.0737 | gap | arxiv_hep-ex_0210044, arxiv_0709.2154 | n/a: imaged by correlated tracking (pdg_2025_particle-detectors-at-accelerators p. 21), [photon-counting likelihood](photon-likelihood-reconstruction.md) | n/a: telescope optics, [imaging atmospheric Cherenkov](imaging-atmospheric-cherenkov.md) | gap |
| Mirror inverse ray tracing | arxiv_1611.00296 | arxiv_physics_0104033 | arxiv_0709.2154 p. 2, arxiv_hep-ex_0210044 Fig. 4 (reflected branches per hit off a conical reflector, not a focusing mirror) | n/a: no mirror | gap: mirrors focus the light, but images are parametrized (moments, templates), not ring-traced; muon rings calibrate the optics ([imaging atmospheric Cherenkov](imaging-atmospheric-cherenkov.md)) | gap |
| Several radiators | arxiv_1211.6759 | arxiv_physics_0104033 | arxiv_0709.2154 (tiled only: the track picks one radiator) | gap | gap | gap |
| Ring finding and association | arxiv_nucl-ex_0211028, arxiv_2603.13000 | arxiv_1809.04026, arxiv_physics_0104033 | arxiv_0709.2154 | [photon-counting likelihood](photon-likelihood-reconstruction.md#topologies-and-hypothesis-comparison) (water rings, ring counting) | gap: images cleaned and parametrized, not ring-found; muon rings for optical calibration ([imaging atmospheric Cherenkov](imaging-atmospheric-cherenkov.md)) | gap |
| Global event likelihood | arxiv_1211.6759, arxiv_2603.13000 | gap (low multiplicity simplified association in arxiv_physics_0104033) | gap | gap | gap | gap |
| Background model | arxiv_2008.06251, arxiv_1211.6759 | gap (sources listed, no level model: arxiv_physics_0104033) | arxiv_hep-ex_0210044 | gap | pdg_2025_particle-detectors-for-non-accelerator-physics (night sky) | gap |
| Yield and charge from yield | arxiv_2008.06251 (yield only) | gap | arxiv_hep-ex_0210044, arxiv_0709.2154 | gap | gap | gap |
| Resolution budget | arxiv_hep-ex_0010068, arxiv_2008.06251, pdg_2025_particle-detectors-at-accelerators | gap | arxiv_0709.2154 | gap | gap | gap |
| DIRC and TOP | [DIRC and TOP](dirc-and-time-of-propagation-reconstruction.md) | [DIRC and TOP](dirc-and-time-of-propagation-reconstruction.md) | gap | gap | gap | gap |

`gap`: none in the sources read (COL, FXT, SPC) or not surveyed (UGD, GND, NUC). `n/a`: the device has no such
part; the reason is in the cell.

## Citations

Read in arXiv e-prints (PDG: 2025 review PDF, 1 December 2025 update), 2026-11-17 to 22. Full entries are in the
split file [particle identification bibliography](detector-principles-bibliography-particle-identification.md),
section "Cherenkov ring and DIRC reconstruction"; arXiv:1211.6759 and arXiv:1809.04026 in the
[calibration bibliography](detector-principles-bibliography-calibration.md); arXiv:physics/0104033 in the
[calorimetry bibliography](detector-principles-bibliography-calorimetry.md) (its existing entry in section "Calorimeter cluster reconstruction", first cited there for lepton identification, kept
there as a duplicate key is a merge conflict; not duplicated); PDG RPP 2025 in the main
[bibliography](detector-principles-bibliography.md).
