# SIDIS, TMD factorization and Drell-Yan q_T

Purpose: kinematics, azimuthal conventions, structure-function decomposition and the rules of TMD factorization for
semi-inclusive DIS (SIDIS) and the transverse-momentum spectrum of Drell-Yan pairs; collinear SIDIS at LO; the Gaussian
ansatz as a worked model. Entry page: [hadron structure](hadron-structure-essentials.md); fragmentation functions in
[fragmentation functions](fragmentation-functions.md); fixed-order Drell-Yan in [Drell-Yan](drell-yan.md).

Status: guidance and two tools (Th18), sources read in full text on 2026-10-23 (see "Sources read"). The executable
pieces are `sidis_kinematics.py` (invariants, Trento angles, leading-power q_T, region classification) and
`tmd_gaussian.py` (Gaussian-ansatz SIDIS and Drell-Yan shapes, Sivers sign bookkeeping). TMD evolution, matching and
nonperturbative prescriptions are rules only.

## Contents

- Required fields
- Kinematics and the Trento conventions
- Cross section and structure functions
- Collinear SIDIS at LO
- TMD factorization (rules)
- Gaussian ansatz
- Sivers and Boer-Mulders: process dependence
- Drell-Yan q_T
- Scripts
- Sources read

## Required fields

`azimuth_convention` (Trento or another named convention), the polarization state (UU, UL, UT, LU, LL, LT), `frame`
(target rest frame or hadron frame), the hadron species and whether charges are summed, hadron-mass corrections
(neglected or the form used), `log_accuracy` with its fixed-order matching (both parts, e.g. "NNLL matched to
O(alpha_s)"), and in `parameters` the nonperturbative prescription (b*, g_K and width models). A missing field is a
refusal.

## Kinematics and the Trento conventions

For l(l) + N(P) -> l(l') + h(P_h) + X with q = l - l', Q^2 = -q^2 (Bacchetta et al., Eq. 2.2):

```
x = Q^2 / (2 P.q),   y = P.q / P.l,   z = P.P_h / P.q,   gamma = 2 M x / Q
epsilon = (1 - y - gamma^2 y^2/4) / (1 - y + y^2/2 + gamma^2 y^2/4)       (their Eq. 2.8)
```

The azimuth phi_h of the hadron around q, measured from the lepton plane, in the target rest frame (Trento conventions,
Eq. 16):

```
cos phi_h = (q^ x l).(q^ x P_h) / (|q^ x l| |q^ x P_h|),   sin phi_h = (l x P_h).q^ / (|q^ x l| |q^ x P_h|)
```

phi_S likewise with the target spin; the definitions hold in any frame reached from the target rest frame by a boost
along q (Trento, Eqs. 16-18). Two conventions for drawing angles in figures are in use (Trento, Sec. II, A and B):
state which. P_h_perp is the hadron momentum transverse to q in that frame. At leading power, in the frame where the target and hadron carry no transverse momentum, q_T = -P_h_perp / z
(the scripts report |q_T| = P_h_perp / z) (Bacchetta et al., Eqs. 3.9 and 4.1 with the frame
of their Sec. 3.2): a leading-power relation between frames, not an exact four-vector identity.

## Cross section and structure functions

The SIDIS cross section in one-photon exchange, lepton mass neglected, is a sum of 18 structure functions, each with its
phi_h, phi_S modulation and its depolarization factor in epsilon (Bacchetta et al., Eq. 2.7); integrated over P_h_perp
it reduces to the collinear ones (their Eqs. 2.14-2.22), and sum_h int dz z F_UU,T = 2x F_1 (Eq. 2.18; a
momentum sum over all hadrons). Their TMD results are
written with the convolution

```
C[w f D] = x sum_a e_a^2 int d^2p_T d^2k_T delta^(2)(p_T - k_T - P_h_perp/z) w(p_T, k_T) f^a(x, p_T^2) D^a(z, k_T^2)
```

(their Eq. 4.1; the sum runs over quarks and antiquarks), with F_UU,T = C[f_1 D_1] and F_UU,L = 0 at leading twist
(Eqs. 4.2-4.3) and the other structure functions in Eqs. 4.4-4.19. The quark correlator has eight twist-2 TMD PDFs
(f_1, g_1L, g_1T, h_1, h_1L^perp, h_1T^perp, h_1^perp (Boer-Mulders), f_1T^perp (Sivers); their Sec. 3.3, Eq. 3.15,
with h_1 = h_1T + (p_T^2/2M^2) h_1T^perp from Eq. 3.29);
the fragmentation side has eight leading-twist TMD FFs (PDG "Fragmentation Functions", Sec. 19.9).

## Collinear SIDIS at LO

Integrating over P_h_perp, F_UU,T = x sum_a e_a^2 f_1^a(x) D_1^a(z) (Bacchetta et al., Eq. 4.21), the sum over quarks
and antiquarks with D_qbar^h for antiquarks. In the limit gamma -> 0 (hadron- and target-mass terms dropped: Eq. 2.14 carries 1 + gamma^2/2x and
F_L = (1 + gamma^2) F_2 - 2x F_1 is not zero at LO when gamma != 0) the multiplicity is the ratio (derived here from
Eqs. 2.14, 2.17 and 4.21 at LO)

```
M^h(x, z, Q^2) = sum_a e_a^2 f_1^a(x, Q^2) D_1^a(z, Q^2) / sum_a e_a^2 f_1^a(x, Q^2)
```

## TMD factorization (rules)

- Regions: the TMD region q_T << Q, the collinear region q_T ~ Q, and their matching (W + Y). `sidis_kinematics.py`
  classifies a point against thresholds on q_T/Q that the user supplies; no default is shipped.
- Evolution: two scales (mu and zeta), the Collins-Soper kernel, a b-space prescription (b*), and nonperturbative
  functions (g_K and the TMD widths). These choices are alternative-model objects; state each in `parameters`.
- Accuracy: `log_accuracy` names the logarithmic order together with the fixed-order matching; one without the other is
  incomplete.
- No TMD evolution formula is given here: none was read for this page. The Gaussian ansatz below has no evolution.

## Gaussian ansatz

With factorized Gaussian transverse dependences and flavour-independent widths (Anselmino et al., Eqs. 34-35)

```
f_q(x, k_perp) = f_q(x) exp(-k_perp^2/<k_perp^2>) / (pi <k_perp^2>)
D_q^h(z, p_perp) = D_q^h(z) exp(-p_perp^2/<p_perp^2>) / (pi <p_perp^2>)     (p_perp: hadron relative to the quark)
F_UU,T(x, z, P_hT) = x sum_q e_q^2 f_q(x) D_q^h(z) exp(-P_hT^2/<P_T^2>) / (pi <P_T^2>),   <P_T^2> = <p_perp^2> + z^2 <k_perp^2>
```

(their Eq. 39 for the width; the d^2 P_hT integral of F_UU,T is the collinear x sum e_q^2 f_q D_q, Bacchetta et al.
Eq. 2.15, which the tests check). Normalizations of the FF transverse momentum differ between groups (p_perp of the
hadron relative to the quark versus k_T of the quark relative to the hadron, k_T = -P_hT/z in Trento's Eq. 8 notation):
convert before combining widths. Status `heuristic-argument`: a model for examples and analytic checks, not a fit. A theory-domain profile for
Gaussian-ansatz TMDs (listed in `<plugin root>/profiles/registry.json`) derives these forms, the Cahn term and the
Sivers asymmetry in SymPy.

## Sivers and Boer-Mulders: process dependence

Time reversal with the Wilson lines selected by each process gives f_1T^perp,SIDIS = -f_1T^perp,DY, while f_1 is the
same (Trento conventions, Eq. 14; Collins, abstract and Secs. 3-4). More generally the Drell-Yan Wilson lines reverse the sign of all T-odd distributions, which include the
Boer-Mulders function h_1^perp (Bacchetta et al., Sec. 3.3).
Status `analytic-derivation` (cited); its experimental status is recorded separately. Notation: f_1T^perp or
Delta^N f_{q/p^up} = -(2|k_T|/M) f_1T^perp (Trento, Eqs. 2-4); Boer-Mulders Delta^N f_{q^up/p} = -(|k_T|/M) h_1^perp
(Eq. 7). State which notation a number uses.

## Drell-Yan q_T

Fixed order is valid for q_T ~ M ([Drell-Yan](drell-yan.md)); q_T -> 0 needs resummation (CSS/TMD), with the same
Collins-Soper kernel as SIDIS. In the Gaussian ansatz the Drell-Yan q_T distribution is the convolution of two TMD
distributions, so its width is <q_T^2> = <k_1perp^2> + <k_2perp^2> with no z factor (derived here). TMD contributions
to the angular coefficients (for example nu from Boer-Mulders functions) belong here.

## Scripts

- `sidis_kinematics.py`: `vectors` (four-vectors in any frame -> x, y, Q^2, z, gamma, epsilon, P_h_perp, phi_h, phi_S,
  q_T at leading power, W^2, region if thresholds are given), `classify` (region from Q^2, z, P_hT and the user's
  thresholds). Rejects an undeclared azimuth convention, z outside (0, 1], P_hT < 0, a hadron along q.
- `tmd_gaussian.py`: `sidis` (F_UU,T(P_hT) and its collinear integral), `dy` (normalized q_T shape), `sivers` (the
  Drell-Yan value -V of a SIDIS Sivers value, notation recorded).
- Tests: `tests/skills/hep_theory/test_sidis_kinematics.py` (invariants and phi_h against constructed four-vectors,
  invariance under a boost along the beam, mirror reflection and spin flip, classification) and `test_tmd_gaussian.py`
  (integral over d^2 P_hT, width addition, Sivers sign). Software checks only.

## Sources read (full text, 2026-10-23)

- A. Bacchetta, U. D'Alesio, M. Diehl, C.A. Miller, "Single-spin asymmetries: the Trento conventions",
  arXiv:hep-ph/0410050v2 (Phys. Rev. D 70 (2004) 117504): Secs. I-II, Eqs. 2-18.
- A. Bacchetta, M. Diehl, K. Goeke, A. Metz, P.J. Mulders, M. Schlegel, arXiv:hep-ph/0611265v2 (JHEP 02 (2007) 093):
  Secs. 2-4, Eqs. 2.2-2.22, 3.9, 3.15, 4.1-4.21.
- M. Anselmino, M. Boglione, U. D'Alesio, A. Kotzinian, F. Murgia, A. Prokudin, arXiv:hep-ph/0501196v2 (Phys. Rev. D 71
  (2005) 074006): Sec. II, Eqs. 34-39.
- J.C. Collins, arXiv:hep-ph/0204004v3 (Phys. Lett. B 536 (2002) 43): abstract, Secs. 1-4.
- PDG 2026 "Fragmentation Functions" (see [fragmentation functions](fragmentation-functions.md)): Sec. 19.9.

Not verified and therefore not used: Collins' book on QCD factorization and any TMD evolution formula; CSS
resummation formulas; the Sivers positivity bound (no source read); fits of TMD widths.
