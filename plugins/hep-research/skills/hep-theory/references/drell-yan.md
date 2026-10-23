# Drell-Yan: cross sections, variables, frames and angular coefficients

Purpose: conventions, formulas and required fields for a Drell-Yan prediction, h_1 h_2 -> gamma*/Z -> l+ l- X (and
W -> l nu as rules), for proton, antiproton, pion and kaon beams on proton or nuclear targets, fixed target or
collider. Differences between beams are in the parton densities and the kinematic conventions only. The LO cross
section, the conversions between variables and frames, and the Lam-Tung combination are computed by
`drell_yan_lo.py`; higher orders and resummation are rules. Entry page: [hadron structure](hadron-structure-essentials.md);
PDF sets in [PDFs](pdfs-and-lhapdf.md); orders and envelopes in [higher orders](higher-order-predictions.md); Z and W
line shapes in [widths](amplitudes-and-widths.md).

Status: guidance and one tool (Th15), sources read in full text on 2026-10-23 (see "Sources read"). The script
implements photon exchange only; a request with Z exchange is refused until the gamma*/Z couplings and the
Breit-Wigner are added and tested.

## Contents

- Required fields
- LO cross section
- Variables: x_F, rapidity frames, Jacobians
- Angular distribution and frames
- Lam-Tung relation
- Beyond LO (rules)
- Script
- Sources read

## Required fields

Beam and target (with Z and A for a nucleus), `xF_definition`, `rapidity_frame` (hadronic centre-of-mass or lab, and
the +z direction), `exchanged_bosons`, `em_coupling`, `electroweak_scheme` when Z is included, the angular `frame`
(Collins-Soper, helicity, Gottfried-Jackson) and which lepton's angles are quoted, and the resonance mass windows
(J/psi, psi', Upsilon) excluded by the user. A missing field is a refusal.

## LO cross section

Photon exchange, N_c = 3, number densities, y the rapidity of the pair in the hadronic centre-of-mass frame:

```
d2sigma/dM dy = (8 pi alpha^2 / (9 M s)) sum_q e_q^2 [ q_1(x_1) qbar_2(x_2) + qbar_1(x_1) q_2(x_2) ],
x_{1,2} = (M / sqrt(s)) e^{+/- y},   tau = x_1 x_2 = M^2 / s
```

Derived here (`analytic-derivation`, LO): the partonic cross section sigma_hat(q qbar -> l+ l-) =
4 pi alpha^2 e_q^2 / (3 N_c M^2) follows from sigma(e+ e- -> f fbar) = N_c Q_f^2 4 pi alpha^2 / (3 s) (PDG 2026
"Cross-Section Formulae", Eq. 51.3) by the colour average; the hadronic cross section is the parton sum of Eq. (51.40)
with dx_1 dx_2 = dtau dy, and dsigma/dM = 2M dsigma/dM^2. LO scaling: M^3 d2sigma/dM dy depends only on tau and y (a
check, not a prediction). The ratio sigma(pd) / (2 sigma(pp)) at LO responds to dbar/ubar of the target at x_2; the pd
system is not symmetric, so "the asymmetry comes from ubar != dbar" is a statement about this ratio, not an identity.
For a pi- beam the dominant term is the valence ubar of the beam with u of the target.

## Variables: x_F, rapidity frames, Jacobians

At LO with q_T = 0, 2 p_L* / sqrt(s) = x_1 - x_2 exactly; p_L* / p_L,max with p_L,max = (s - M^2) / (2 sqrt(s))
equals (x_1 - x_2) / (1 - tau) (derived here). The first two coincide at LO; the third differs, and so does its
Jacobian:
dx_F/dy = x_1 + x_2 for the first two and (x_1 + x_2) / (1 - tau) for the third, so d2sigma/dM dx_F =
(d2sigma/dM dy) / (dx_F/dy). dx_1 dx_2 = dtau dy (unit Jacobian). In a fixed-target or asymmetric-beam lab frame,
y_lab = y_cm + y_shift with y_shift the rapidity of the beam system; the script converts only with `rapidity_frame`
declared and the beam four-momenta given. Beyond LO (q_T != 0) the definitions of x_F must be restated.

## Angular distribution and frames

In the dilepton rest frame (Peng et al., Eq. 1; Lam and Tung, as cited there):

```
dsigma/dOmega ~ 1 + lambda cos^2 theta + mu sin 2theta cos phi + (nu / 2) sin^2 theta cos 2phi
```

The LHC expansion (Aad et al., Eq. 1) is (1 + cos^2 theta) + (1/2) A_0 (1 - 3 cos^2 theta) + A_1 sin 2theta cos phi +
(1/2) A_2 sin^2 theta cos 2phi + A_3 sin theta cos phi + A_4 cos theta + A_5 sin^2 theta sin 2phi +
A_6 sin 2theta sin phi + A_7 sin theta sin phi, so lambda = (2 - 3 A_0)/(2 + A_0), mu = 2 A_1/(2 + A_0), nu = 2 A_2/(2 + A_0) (Peng et al., Eq. 7; rederived
here). The (lambda, mu, nu) form covers the parity-conserving terms of photon
exchange. With Z in `exchanged_bosons` the full A_0 to A_7 expansion is needed: A_3 and A_4 depend on products of
vector and axial couplings (A_FB comes from A_4), A_5 to A_7 are small and arise at O(alpha_s^2) (Aad et al., Sec. 1).
The angles are those of one lepton: Aad et al. and Peng et al. use l-, Faccioli et al. the positive fermion. Swapping the
lepton (theta -> pi - theta, phi -> phi + pi) leaves lambda, mu, nu, A_5 and A_6 unchanged and flips A_3, A_4 and A_7 (derived here); state the lepton.

Frames (Faccioli et al. 2010, Sec. 3 and Eq. 25): the helicity (HX) axis is the pair's direction in the hadronic
centre-of-mass frame, the Collins-Soper (CS) axis the bisector of beam 1 and the opposite of beam 2 in the pair rest
frame, the Gottfried-Jackson axis one beam. All lie in the production plane, so a change of frame is a rotation by an
angle d about the normal (y) axis, and (their Eq. 21, with lambda_phi = nu/2, lambda_thetaphi = mu)

```
lambda'          = (lambda - 3 L) / (1 + L),   lambda_phi' = (lambda_phi + L) / (1 + L)
lambda_thetaphi' = (lambda_thetaphi cos 2d - (lambda - lambda_phi) sin 2d / 2) / (1 + L)
L = (lambda - lambda_phi) sin^2 d / 2 - lambda_thetaphi sin 2d / 2
d_HX->CS = -d_CS->HX = arccos(m p_L / (m_T p))      (their Eq. 28; beam 1 along +z, y along P1' x P2')
```

The sign of d, and so of mu, depends on the axis conventions (their Sec. 5); with beam 1 always along +z and
symmetric beams (pp, p pbar), mu(-y) = -mu(y); for pA or pi p there is no such symmetry. Frame-invariant combinations, for rotations about the normal to the production plane:
lambda~ = (lambda + 3 lambda_phi) / (1 - lambda_phi) = (lambda + 3 nu/2) / (1 - nu/2) (their Eq. 31) and
F = (1 + lambda + 2 lambda_phi) / (3 + lambda) (Faccioli, Lourenco, Seixas, Eq. 8). Allowed domain: the bounds of Eq. 22, |lambda| <= 1, |nu/2| <= (1 + lambda)/2, |mu| <= (1 - nu/2)/2 (from
|lambda| <= 1 in every frame), and W >= 0 on the sphere, which holds exactly when I + M has no negative eigenvalue,
M = [[nu/2, 0, mu], [0, -nu/2, 0], [mu, 0, lambda]] (derived here). Neither condition implies the other; the script
checks both. At LO with q_T = 0 the distribution is 1 + cos^2 theta (lambda = 1, mu = nu = 0) and all frames share one axis
(for y < 0 the HX axis is antiparallel to the CS axis, d = pi: lambda, mu, nu are unchanged, cos theta and so A_3,
A_4 flip).

## Lam-Tung relation

1 - lambda - 2 nu = 0, equivalently A_0 = A_2 and lambda~ = 1. It holds at O(alpha_s) for both the q qbar -> gamma* g
and q g -> gamma* q channels (spin-1/2 quarks and spin-1 gluon) and can be violated at higher orders (Aad et al., Sec. 1);
status `perturbative-argument`, order stated. It is frame independent (Faccioli, Lourenco, Seixas). Peng et al. describe the q_T dependence of lambda and nu and the violation at colliders as non-coplanarity of the
quark axis and the hadron plane, and only propose extending this to fixed-target data; for the large violations in
pion-induced data they cite non-perturbative explanations, including Boer's TMD (Boer-Mulders) interpretation, which
belongs to the SIDIS/TMD module (planned). The O(alpha_s)
derivation of the relation is planned in a theory-domain profile (phase 4).

## Beyond LO (rules)

- NLO has q qbar and q g channels. Fixed-target K-factors are large; record the scale and PDFs a K-factor was obtained
  with; applying an inclusive K-factor to a differential distribution is an assumption.
- Central scales mu_R = mu_F = M with the 7-point envelope of [higher orders](higher-order-predictions.md).
- Large tau and large x_F: threshold logarithms grow; state whether threshold resummation is used (`log_accuracy`).
- q_T spectrum: fixed order is valid for q_T of order M; q_T -> 0 needs CSS/TMD resummation (SIDIS/TMD module,
  planned). Intrinsic-k_T models are alternative-model objects.
- Meson beams: pion and kaon PDFs are user inputs or special-purpose sets with fewer data and a different uncertainty
  structure; state them in the theory-spec.
- Nuclear targets: nuclear PDFs and effects are the nuclear-effects module (planned); a ratio sigma(pA)/sigma(pd) at
  forward x_F mainly probes target antiquarks at x_2.

## Script

`drell_yan_lo.py`: `xsec` (d2sigma/dM dy and d2sigma/dM dx_F in GeV^-3 and pb/GeV from beam and target parton values
at x_1 and x_2, which the parton file must carry; photon exchange), `convert` ((M, y), (M, x_F), (x_1, x_2), (tau, y)
with Jacobians; cm or lab rapidity), `frames` (CS <-> HX with the invariants), `lam-tung` (1 - lambda - 2 nu with a
linear uncertainty and the user's correlation), `coefficients` ((A_0, A_1, A_2) <-> (lambda, mu, nu)). Refuses (exit 1)
Z exchange, M inside a declared resonance window without `--allow-in-window`, and angular parameters outside the
positivity domain; rejects (exit 2) undeclared frames or x_F definitions, M^2 >= s, x outside (0, 1], a parton file
evaluated at another point. Tests: `tests/skills/hep_theory/test_drell_yan_lo.py` (hand value, Jacobians and x_F
against four-vectors, round trips, lab shift for a fixed target, y symmetry, LO scaling, a closed-form y integral,
pd/pp response to dbar/ubar) and `test_dy_angular_frames.py` (rotation angle against boosted axes, Eq. 21 against a
direct numerical rotation of the distribution, invariants, Lam-Tung frame independence). Software checks only.

## Sources read (full text, 2026-10-23)

- PDG, "51. Cross-Section Formulae for Specific Processes", in F. Takahashi et al. (Particle Data Group), Int. J. Mod.
  Phys. A 41, 2630011 (2026) (https://pdg.lbl.gov/2026/reviews/rpp2026-rev-cross-section-formulae.pdf): Eqs. (51.2),
  (51.3), (51.25), (51.40). The review has no explicit Drell-Yan formula; the LO form above is derived from these.
- J.-C. Peng, W.-C. Chang, R.E. McClellan, O. Teryaev, arXiv:1511.08932v3: Eqs. 1-7 (the A_i in terms of the quark
  axis and lambda, mu, nu in terms of A_0, A_1, A_2).
- G. Aad et al. (an LHC collaboration), arXiv:1606.00689v1 (JHEP 08 (2016) 159): Sec. 1, Eqs. 1-5, Fig. 1 (Collins-Soper frame, l-).
- P. Faccioli, C. Lourenco, J. Seixas, H.K. Woehri, arXiv:1006.2738v1 (Eur. Phys. J. C 69 (2010) 657): Secs. 3-6,
  Eqs. 18-22, 25-31.
- P. Faccioli, C. Lourenco, J. Seixas, arXiv:1005.2601v1 (Phys. Rev. Lett. 105 (2010) 061601): Eqs. 2-10.

Not verified and therefore not used: the original Collins-Soper (1977) and Lam-Tung (1978, 1980) papers (their
content is taken from the sources above, which state it); NLO K-factors and threshold-resummation formulas; the
gamma*/Z coupling formulas for A_3 and A_4 (Aad et al. App. A, not used by the script).
