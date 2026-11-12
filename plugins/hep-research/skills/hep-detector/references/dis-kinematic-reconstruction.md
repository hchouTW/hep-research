# DIS Kinematic Reconstruction

Owner: hep-detector. This page covers which estimator reconstructs x, y and Q^2 of a deep-inelastic event from
measured quantities, and what each estimator is sensitive to. The invariants themselves, their identities and the
frames are defined in hep-theory ([DIS kinematics](../../hep-theory/references/dis-kinematics.md)). Facility
settings (beam species, energies, crossing angle) come from an experiment profile or the user. Binning and
selections belong to hep-measurement, unfolding to hep-statistics, and the radiative-correction calculation to
hep-theory. Estimator families and per-event errors in general:
[measurement framework](detector-measurement-framework.md#choosing-the-estimator). The reconstruction chain:
[event reconstruction](event-reconstruction.md).

## Measured quantities and conventions

The formulas below assume collinear, head-on beams along z. The +z axis is the incoming hadron direction, as at
HERA and in the Yellow Report (section 8.1.1; full citation under Sources read). Masses are neglected.

- `E_e`: lepton beam energy. `E_p`: hadron beam energy, per nucleon for an ion. `s = 4 E_e E_p`.
- `E` and `theta`: energy and polar angle of the scattered lepton, with theta measured from +z. A small scattering
  angle is a theta near 180 degrees.
- `Sigma = sum_h (E_h - p_z,h)` and `T = sqrt((sum_h p_x,h)^2 + (sum_h p_y,h)^2)`. Both sums run over the hadronic
  final state. The inclusive hadronic angle is `gamma`, with `tan(gamma/2) = Sigma / T`.
- `Sigma_e = E (1 - cos theta)`. Longitudinal momentum conservation gives `Sigma + Sigma_e = 2 E_e` for an event
  with no undetected radiation. A forward particle lost in the beam pipe contributes little to Sigma, because
  `E - p_z` is small for it.

A measured event over-determines (x, y, Q^2): four quantities (E, theta, Sigma, gamma) for two independent
variables. Each method picks a subset, and its errors and biases follow from that choice.

## The methods

All formulas are from Bassler and Bernardi (1995): the appendix table and eqs. (6), (8), (10)-(12). In every
method `x = Q^2 / (s y)`.

| Method | y | Q^2 | Uses |
|---|---|---|---|
| Electron (e) | `1 - (E/E_e) sin^2(theta/2)` | `4 E_e E cos^2(theta/2)` | E, theta |
| Hadron, Jacquet-Blondel (h, JB) | `Sigma / (2 E_e)` | `T^2 / (1 - y_h)` | Sigma, T |
| Mixed (m) | `y_h` | `Q^2_e` | E, theta, Sigma |
| Double angle (DA) | `tan(gamma/2) / (tan(gamma/2) + tan(theta/2))` | `4 E_e^2 cot(theta/2) / (tan(gamma/2) + tan(theta/2))` | theta, gamma |
| Sigma | `Sigma / (Sigma + E (1 - cos theta))` | `E^2 sin^2(theta) / (1 - y_Sigma)` | E, theta, Sigma |
| e-Sigma | `2 E_e Sigma / (Sigma + E (1 - cos theta))^2` | `Q^2_e` (and `x = x_Sigma`) | E, theta, Sigma |

The Yellow Report gives the same electron and JB definitions (eqs. 8.1 and 8.2). The formulas were checked here on
exact massless four-vectors: with no radiation, every method returns the generated x, y and Q^2 to rounding.

What each method is sensitive to, as the sources state it:

- **Electron.** Precise at high y. The error grows as y falls, because `delta y / y = ((1 - y)/y) (delta E/E (+)
  delta theta / tan(theta/2))` (Bassler and Bernardi 1995, eq. 5). Resolutions on x and y diverge as y -> 0, and
  poor low-y resolution moves some high-x events to very low x; a lower y cut removes that offset (Yellow Report
  section 8.1.4). As y -> 1, the scattered-lepton energy falls and the reconstruction degrades again.
- **Hadron (JB).** Better than the electron method at low y; poor in Q^2 because hadrons are lost in the beam pipe.
  It is the only method for charged-current events, where no lepton is measured (Bassler and Bernardi 1995,
  section 2; Yellow Report section 8.1.1). Its accuracy depends on the fraction of the hadronic final state inside
  the acceptance (Yellow Report section 8.1.5).
- **Double angle.** Uses angles only, so it is independent of the absolute energy scale, provided the energy
  response is uniform over the solid angle. It is precise at high Q^2 and poor at low x and low Q^2 (Bassler and
  Bernardi 1995, section 2; 1999, section 3). In a Yellow Report SIDIS study, DA and the mixed method improved on JB
  at high x and moderate Q^2, and a hadronic calorimeter did not improve them significantly (section 8.2.3).
- **Sigma.** Has no low-y divergence, and at high y its errors partly cancel. In the 1995 study it was the one x
  estimator with small bias and good resolution over the whole y range examined. Q^2_Sigma degrades with
  increasing y (section 4).
- **e-Sigma.** Takes Q^2 from the electron and x from Sigma. It optimizes the reconstruction over most of the plane,
  but at high y it becomes correlated with the electron method (Bassler and Bernardi 1995, section 5.1). Bassler
  and Bernardi (1999) add rescaled and averaged variants and compare them.

## QED radiation

- **Initial-state radiation (ISR)** lowers the lepton energy at the hard vertex. The photon usually escapes down the
  beam pipe (Arratia et al. 2022, section 2). The Sigma method replaces `2 E_e` by the measured `Sigma + Sigma_e`,
  so y_Sigma and Q^2_Sigma are those of the hard vertex for a collinear ISR photon (Bassler and Bernardi 1995,
  section 3). The electron and JB methods are biased. A window on `Sigma + Sigma_e` around `2 E_e` rejects events
  with hard ISR. The check above, with a collinear ISR photon, reproduces this: y_Sigma and Q^2_Sigma are those of
  the hard vertex, y_DA is unchanged, and the other estimates shift.
- **Final-state radiation** shares the lepton's energy with a photon. Whether the photon is merged with the lepton
  cluster changes E and theta. In Arratia et al. (2022), real QED radiation is the reason the classical methods
  disagree and show resolution tails.
- **Radiative corrections.** The Yellow Report (section 7.6.2) states that DIS radiative corrections can be very
  large, in particular at small x and large y. Their size depends on acceptance and cuts, and size and uncertainty
  are not tied: a cut on the accepted energy deficit can make the correction small and its uncertainty large.
  HERA practice, recommended there, is Monte Carlo with radiative generators (for example DJANGOH) rather than
  post-hoc correction factors. The correction is computed in hep-theory; what this page owns is that the
  reconstruction method, the `Sigma + Sigma_e` window and the lepton-photon merging all change it, so all three
  are stated together with the correction.

## Calibration sensitivity

The electron method depends on the lepton energy scale and angle, and JB on the hadronic energy scale and on
losses near the beam pipe. DA depends on the uniformity of the hadronic response, not on its absolute scale. Sigma
depends little on forward losses. Bassler and Bernardi (1999, sections 3 and 5) give the error propagation of each
method in terms of `delta Sigma / Sigma` and the angle errors. Before choosing a method, propagate the detector's
own scale and angle uncertainties through each candidate method; they come from the calibration
([calibration and alignment](calibration-and-alignment.md)) or the experiment profile, never from these papers.

## Crossing angle and beam effects

The formulas assume head-on beams. With a crossing angle, transform every measured four-vector to the frame where
the two beams are collinear and head-on, then apply the formulas there. The transformation follows from the two
beam four-momenta: one boost and one rotation. Then state the beam axis and sign convention, as hep-theory
requires for frames. The invariants x, y and Q^2 are frame-independent, but E, theta, Sigma and gamma are not.
Computing them in the laboratory frame with head-on formulas gives a biased estimate. s itself comes from the
crossing angle and the two energies (`<plugin root>/skills/hep-theory/scripts/dis_kinematics.py`).

The Yellow Report treats the crossing angle as well defined and correctable event by event. The beam momentum
spread and angular divergence are not correctable event by event (section 8.4.6, p. 346). Generators mostly assume
zero crossing angle, so the report generated head-on events and then applied the beam effects (section 8.4.6, p. 344). The
crab-cavity rotation acts as an effective vertex smearing for the Roman pots (section 11.6.2, p. 549).
The crossing angle of a given configuration is a facility value from the experiment profile.

## Choosing and combining

- Two strategies were used at HERA: different methods in different regions of the (x, Q^2) plane, or one precise
  method over the whole plane (Bassler and Bernardi 1999, section 3). Bin-by-bin switching needs the migration and
  the radiative correction computed with the same per-bin method.
- Judge the choice by **purity** and **stability**. Purity is the fraction of events reconstructed in a bin that
  were generated in it. Stability is the fraction of events generated in a bin that are reconstructed in it. The
  Yellow Report (section 8.1.4, p. 272) quotes 30% for both as the typical lower limit in HERA analyses. The
  binning, migration and response follow
  [response and forward folding](response-and-forward-folding.md) and
  [reconstruction performance and truth matching](reconstruction-performance-and-truth-matching.md).
- **SIDIS and Breit-frame variables** need the full vector q, not only x and Q^2. The Yellow Report (section 8.2.3)
  takes the transverse part of q from the hadronic final state and solves eqs. (8.3)-(8.4) for the rest. That
  quadratic has two solutions, and the report found the smaller one usually correct, a choice it says needs
  further study.
- **Learned reconstruction.** Arratia et al. (2022) regress ln Q^2, ln y and ln x with a deep neural network whose
  inputs include QED-radiation indicators. On simulation they report better resolution and smaller bias than the
  classical methods. Validate a learned estimator as in
  [event reconstruction](event-reconstruction.md#validating-a-learned-reconstruction), including radiative events
  and generator dependence. Training belongs to hep-ml.

## Sources read

<!-- example: source citations (experiments named as the source of a general method) -->
Each source was read on 2026-11-12. Every DOI was matched against its Crossref record (authors, title, venue,
volume, pages, year).

- U. Bassler and G. Bernardi, "On the kinematic reconstruction of deep inelastic scattering at HERA", Nucl.
  Instrum. Methods A361 (1995) 197-208, DOI 10.1016/0168-9002(95)00173-5 (arXiv:hep-ex/9412004). Full text, arXiv
  PDF v1: eqs. (5), (6), (8), (10)-(12), the appendix table (p. 18), sections 2-5.
- U. Bassler and G. Bernardi, "Structure function measurements and kinematic reconstruction at HERA", Nucl.
  Instrum. Methods A426 (1999) 583-598, DOI 10.1016/S0168-9002(99)00044-3 (arXiv:hep-ex/9801017). Sections 1-5 of
  the arXiv version (partial read). Used for method comparisons and error propagation only.
- R. Abdul Khalek et al., "Science Requirements and Detector Concepts for the Electron-Ion Collider: EIC Yellow
  Report", Nucl. Phys. A 1026 (2022) 122447, DOI 10.1016/j.nuclphysa.2022.122447. Report version v1.1 (Zenodo
  record 6423305). Pages read: sections 7.6.2 (pp. 252-255), 8.1.1 (pp. 261-262), 8.1.4-8.1.5 (pp. 271-275),
  8.2.3 (pp. 287-289), 8.4.6 beam effects (pp. 344-346) and 11.6.2 (p. 549).
- M. Arratia, D. Britzger, O. Long and B. Nachman, "Reconstructing the kinematics of deep inelastic scattering with
  deep learning", Nucl. Instrum. Methods A1025 (2022) 166164, DOI 10.1016/j.nima.2021.166164 (arXiv:2110.05505).
  Full text, arXiv v2.

Not read; cited through Bassler and Bernardi (1995) only: F. Jacquet and A. Blondel, DESY 79/48 (1979) 391
(hadron method); S. Bentvelsen et al. and C. Hoeger, Proc. Workshop Physics at HERA, vol. 1 (1992) 23 and 43
(double angle). Performance numbers for a specific detector are not given here: take them from that experiment's
profile or publications.
<!-- /example -->
