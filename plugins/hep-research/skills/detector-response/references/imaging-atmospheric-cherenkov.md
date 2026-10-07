# Imaging Atmospheric Cherenkov Technique

Covers ground-based gamma-ray astronomy: how an array of Cherenkov telescopes images
an air shower's Cherenkov light pool to reconstruct a gamma-ray's energy and
direction and reject the overwhelming hadronic cosmic-ray background. Builds on
[extensive air showers](extensive-air-showers.md) (a gamma-initiated shower is a
pure electromagnetic cascade, described by the Greisen profile) and shares its
significance and background-estimation methodology with
[astroparticle statistics](../../hep-statistics/references/astroparticle-statistics.md). Not to be confused with
the ring-imaging Cherenkov (RICH) *particle-identification* detectors in
[particle-identification.md](particle-identification.md), which
image single-particle Cherenkov cones in a dense radiator rather than a whole air
shower's Cherenkov light pool in the atmosphere.

## The technique

A charged shower particle traveling faster than the local speed of light in air emits
Cherenkov light, which for a full electromagnetic cascade sums into a light pool
roughly 120-150 m in radius (~250 m across) on the ground, lasting a few nanoseconds, peaking in the
near-UV/blue. An **imaging atmospheric Cherenkov telescope** (IACT) - a large
segmented mirror focusing this light onto a fast, finely pixelated camera - within the
light pool's footprint records a two-dimensional image of the shower's angular
development as seen from that vantage point, elongated along the shower axis
projected onto the sky. Because the technique depends on the shower reaching well
above the ground before its Cherenkov emission is intercepted, it requires clear,
dark, moonless conditions, giving it a duty cycle comparable to fluorescence detection
(see [ground-based detection arrays](ground-based-detection-arrays.md)) - typically
around 10-15%, the dominant limitation on exposure for any IACT source measurement.

**Hillas parameters** are the classical image-shape description: the ellipse's
length and width, its orientation, and its distance from the assumed source position
in the camera plane. A gamma-ray-initiated shower produces a narrow, well-collimated
image pointing back toward the source, while a hadron-initiated shower - which
develops a broader, more irregular cascade because of its hadronic sub-showers and
higher-multiplicity muon content - produces a wider, less regular image with no
preferred pointing. Modern analyses supplement or replace simple Hillas cuts with
multivariate classifiers (Random Forest/BDT, or deep learning on the raw image) built
on the same underlying shape information plus timing across pixels; see
[machine learning](../../physics-ml/references/ml-analysis.md) for the general leakage and calibration
requirements that apply to training such a classifier on simulated gamma showers and
applying it to real hadronic-background-dominated data.

<!-- example: experiment-specific illustration -->
**Stereoscopic reconstruction**: an array of multiple telescopes viewing the same
shower from different ground positions intersects each telescope's image axis to
reconstruct the shower's true (not just camera-projected) arrival direction and
impact point, dramatically improving angular resolution and background rejection
relative to a single telescope - the reason all current-generation instruments
(H.E.S.S., MAGIC, VERITAS, and the planned CTA) are arrays rather than single
telescopes.
<!-- /example -->

## Energy reconstruction

<!-- example: experiment-specific illustration -->
Cherenkov light yield in the image scales with the primary energy (Cherenkov photon
number tracks the electromagnetic cascade's total track length, itself proportional
to energy for a fixed atmospheric depth of first interaction), so image intensity,
together with the reconstructed impact distance from the telescope (light density
falls off with distance in a way that must be corrected for), gives an energy
estimate calibrated against detailed shower simulation. Because this calibration is
simulation-based rather than tied to an independent calorimetric measurement (unlike
the hybrid fluorescence/surface-array calibration in
[ground-based detection arrays](ground-based-detection-arrays.md)), the absolute
energy scale for IACTs carries a larger systematic uncertainty (typically ~10-20%: MAGIC quotes <15%, H.E.S.S. sees ~10% residual atmospheric-transparency variation, and VERITAS quotes ~25% on the absolute flux of an index-2.5 source, which includes the energy-scale term; checked 2026-10-02, see [sources](../../research-communication/references/primary-sources-and-version-checks.md)),
dominated by the atmospheric-transparency model and the assumed telescope optical
throughput; report the assumed atmospheric model and its calibration/monitoring
alongside any absolute flux or spectral normalization.
<!-- /example -->

## Background rejection and significance

Above the Cherenkov-image gamma/hadron classifier, the dominant remaining background
is the isotropic hadronic cosmic-ray flux, which - because it has no preferred
celestial direction - is estimated **from the same dataset** rather than from a
separate control sample: background counts are taken from one or more OFF regions in
the same field of view (or the same tracking position observed at a different time),
selected to have the same acceptance as the ON (source) region, and it is standard to
require background estimation methods (reflected-region, ring-background, or
template) that avoid contaminating the OFF estimate with real source photons and that
correctly account for the camera's radially varying acceptance.

The standard significance formula for an ON/OFF counting measurement with unequal
exposure (encoded as the ratio `alpha` of ON to OFF exposure/normalization) is the
**Li & Ma (1983) likelihood-ratio significance**:

    S = sqrt(2) * sqrt(
          N_on * ln[ ((1+alpha)/alpha) * (N_on / (N_on + N_off)) ]
        + N_off * ln[ (1+alpha) * (N_off / (N_on + N_off)) ]
        )

with the sign of `S` taken as positive when `N_on > alpha * N_off` (an excess) and
negative otherwise. This is the field's standard test statistic for a claimed
detection and is implemented in `<plugin root>/skills/hep-statistics/scripts/li_ma_significance.py`; because it is
derived from a likelihood ratio under the Poisson ON/OFF model it is the appropriate
replacement for a naive `(N_on - alpha*N_off)/sqrt(N_on + alpha^2*N_off)` significance
at low counts, where the naive formula's Gaussian assumption breaks down. Its own
normal p-value is still asymptotic (`S = sqrt(-2 ln lambda)`, Wilks), so at a few counts
quote the script's `--toys` or `--exact-conditional` p-value as well. See
[astroparticle statistics](../../hep-statistics/references/astroparticle-statistics.md) for the trials-factor
correction required when this significance is evaluated at many trial positions in a
blind sky scan rather than at one predetermined source position.

## Spectral and morphological analysis

Once a signal is established, the observed count excess in each energy and/or spatial
bin must be **forward-folded** through the instrument response (effective area,
energy resolution/migration matrix, point-spread function) to compare a candidate
source spectrum or morphology model to data, rather than naively unfolding, because
IACT effective areas and energy resolution are steeply energy-dependent near the
technique's low-energy threshold (set by the night-sky-background noise floor and by
the reduced Cherenkov yield of low-energy showers) - the same steep-spectrum
forward-folding preference stated in
[cosmic-ray spectrum and composition](cosmic-ray-spectrum-and-composition.md) and
[measurements-and-unfolding.md](../../hep-analysis/references/measurements-and-unfolding.md).

## Worked walkthrough: an IACT ON/OFF measurement with a trials correction (verified 2026-09-24)

A pre-defined source position gives `N_on = 64` and `N_off = 180` with reflected OFF regions
(`alpha = 0.25`). Five energy thresholds were then tried before this one was chosen.

```bash
python3 <plugin root>/skills/hep-statistics/scripts/li_ma_significance.py --on 64 --off 180 --alpha 0.25
```

This gives excess = 19 and a local significance of 2.35 sigma (one-sided p = 9.4e-3). The five
thresholds are nested and correlated, so `N_eff <= 5`. As a bound,
`p_global = 1 - (1 - 9.4e-3)^5 = 0.046`, about 1.7 sigma. The result is "no significant
excess". Report the local and the post-trials values and state how many thresholds were
tried. For a flux upper limit, forward-fold an assumed spectrum through the effective area
and energy migration ([astroparticle statistics](../../hep-statistics/references/astroparticle-statistics.md)); do not divide the counts by
an energy-averaged effective area. Check that the OFF regions exclude every known source and
the ON region.

## Deliverables

- The classifier (Hillas cuts or a trained multivariate method) used for gamma/hadron
  separation, its training sample (simulated showers - state the interaction/EM
  shower model), and the working-point efficiency and hadron-rejection factor.
- The OFF-region background-estimation method (reflected-region, ring-background,
  template) and the exposure ratio `alpha` used in the significance calculation.
- The Li & Ma significance (or equivalent likelihood-based statistic) rather than a
  Gaussian approximation, with the trials factor stated if multiple positions,
  energy bins, or time windows were scanned.
- The absolute energy-scale systematic and the atmospheric model/monitoring it is
  tied to.
- Whether a spectral or morphological result was obtained by forward-folding through
  the instrument response or by unfolding, given the steep-spectrum migration bias.
- Observation live time, duty-cycle-driven exposure, and zenith-angle range (which
  affects both the low-energy threshold and the effective area) for the dataset used.
