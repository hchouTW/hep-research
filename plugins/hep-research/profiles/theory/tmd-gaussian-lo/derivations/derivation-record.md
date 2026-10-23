# Derivation record: Gaussian TMDs at LO (theory:tmd-gaussian-lo)

**Status.**
- Every step below is an `analytic-derivation` within the stated model: the Gaussian ansatz with constant widths and
  the O(k_perp/Q) kinematics.
- The physics status of the results is `heuristic-argument`, because the model itself is an ansatz.
- The Sivers sign change between SIDIS and Drell-Yan is cited (time reversal, Trento Eq. 14), not derived.
- Order: leading order in alpha_s, leading power in k_perp/Q (the Cahn term at O(k_perp/Q)), no TMD evolution.

SymPy did the algebra with exact arithmetic (`scripts/derive.py`, output `derivations/derivation.json`); SymPy is
trusted as a tool. This is not a formal proof.

**Environment.** Interpreter from `skills/hep-computing/scripts/find_python.py` (status `found`): Python 3.13.2,
SymPy 1.14.0. SciPy 1.17.1 and NumPy 2.4.4 were used for the quadrature. `derivation.json` records the versions of the
run that wrote it. The derivation takes about 50 s.

**References read (2026-10-23).**
- Anselmino et al., arXiv:hep-ph/0501196v2 (tmdg:S01): Eqs. 29 and 32-39 (pp. 6-7), Eq. 47 (p. 9), Eqs. 48-58
  (pp. 10-12), Eqs. 63-68 and Table I (pp. 12-14). Eqs. 38 and 63-67 were checked on the rendered pages.
- Bacchetta et al., arXiv:hep-ph/0611265v2 (tmdg:S02), PDF pages: Eqs. 2.3, 2.7-2.15 (pp. 4-6), Eq. 3.41 (p. 14),
  Eqs. 4.1, 4.2 and 4.11 (pp. 18-19), Eq. 4.20 (p. 20), Eq. 4.21 (p. 21).
- Trento conventions, arXiv:hep-ph/0410050v2 (tmdg:S03): Eqs. 2-4 (pp. 1-2) and Eq. 14 (p. 3).

## Steps

1. **Normalizations.** The 2D Gaussians integrate to 1 (Anselmino Eqs. 36-37). The Bacchetta form
   D_1(z, k_T^2) = (D_1(z)/z^2) exp(-k_T^2/<k_T^2>)/(pi <k_T^2>) satisfies z^2 int d^2k_T D_1(z, k_T^2) = D_1(z)
   (Eq. 3.41).
2. **SIDIS, Anselmino form.** x int d^2k f(x, k) D(z, P - z k) equals x f D exp(-P^2/<P_T^2>)/(pi <P_T^2>), with
   <P_T^2> = <p^2> + z^2 <k^2> (Eq. 39). Its d^2P integral is x f D (Bacchetta Eq. 4.21).
3. **SIDIS, Bacchetta form.** delta(p_T - k_T - P/z) fixes k_T = p_T - P/z in Eq. 4.1. With the z^2-normalized D_1
   above and <k_T^2> = <p_perp^2>/z^2, C[f_1 D_1] equals step 2 identically. The hadron moves relative to the quark
   by -z k_T, so P_hT = z p_T + (-z k_T), the same relation as Anselmino Eq. 29.
4. **Cahn term.** Insert Eq. 33 into Eq. 32, with the lepton plane along x so that k cos(phi) = k_x. The k_x moment
   of the Gaussian product is z <k^2> P_x/<P_T^2>, which reproduces the cos(phi_h) term of Eq. 38. From Bacchetta
   Eq. 4.20 (F^cos = -(2/Q) C[h.p_T f D]) with Eqs. 2.9 and 2.11 at gamma = 0, y^2/(2(1-eps)) = (1 + (1-y)^2)/2 and
   y^2/(2(1-eps)) sqrt(2 eps(1+eps)) = (2-y) sqrt(1-y). The same bracket follows.
5. **Sivers.**
   - The phi_S integral of sin(phi - phi_S) sin(phi_h - phi_S) is pi cos(phi - phi_h).
   - With h'(k) = sqrt(2e)(k/M') exp(-k^2/M'^2), the d^2k integral of Eq. 58 combines exp(-k^2/M'^2) with the
     k_perp Gaussian into <k^2>hat of Eq. 67. The ratio of Eq. 58 then reproduces Eqs. 64-67, including the 2 pi of
     Eq. 66.
   - Bacchetta Eq. 4.11 with f_1T^perp = -(M/(2|k_T|)) Delta^N f (Trento Eq. 4) gives the same F_UT/F_UU. M cancels,
     and the signs agree.
   - The angles of the two papers coincide. Anselmino et al. (p. 2) say they follow the Trento conventions, with q
     along +z, P = P0(1, 0, 0, -1) and l = E(1, sin theta, 0, cos theta), so l_x > 0. They write
     P_T = P_T(cos phi_h, sin phi_h, 0) (p. 6) and S_T = |S_T|(cos phi_S, sin phi_S, 0) (p. 11). In Trento Eq. 16
     (p. 3), q-hat x l = sin theta y-hat, so cos phi_h(Trento) = cos phi_h, and (l x P_h) . q-hat =
     E sin theta P_T sin phi_h. The same holds for phi_S. Their gamma* p c.m. frame is reached from the target rest
     frame by a boost along q-hat, which Trento allows.
6. **Drell-Yan.** The integral int d^2k1 d^2k2 delta(k1 + k2 - q_T) G(k1) G(k2) = G(q_T; <k1^2> + <k2^2>) is
   normalized to 1. It is derived here; no source read gives this line.
7. **Sivers sign change.** With f_1T^perp,DY = -f_1T^perp,SIDIS, the Gaussian Sivers function, its Delta^N form
   (Trento Eq. 4 round trip) and every quantity linear in it change sign.

## Checks run

| Check | Result |
|---|---|
| Normalizations (Eqs. 36-37, 3.41) (SymPy) | pass |
| Anselmino and Bacchetta forms of F_UU,T agree; collinear integral (SymPy) | pass |
| Cahn term from Eq. 32-33 and from Bacchetta Eq. 4.20 with Eqs. 2.9 and 2.11 (SymPy) | pass |
| Sivers: Eq. 58 gives Eqs. 64-67; Bacchetta 4.11 + Trento 4 gives the same (SymPy) | pass |
| Drell-Yan width sum and normalization (SymPy, quadrature) | pass |
| Sivers sign change and Trento Eq. 4 round trip (SymPy, numerical) | pass |
| Published closed forms (Eqs. 38-39, 64-67) vs 2D adaptive quadrature of the profile's transcription of the same paper's integrands, 4 points, relative 1e-7 (observed below 1e-15): same route as the paper, so it checks algebra and transcription, not physics | pass |
| Consistency check against `skills/hep-theory/scripts/tmd_gaussian.py` (sidis, dy, sivers; same author, not independent) | pass (`tests/test_prediction.py`) |
| Negative tests: a wrong width combination or a missing z^2 in D_1 fails | pass (`tests/test_derivation.py`) |

## Checks not run

- TMD evolution and the soft factor.
- An independent derivation of the Sivers sign change.
- A Drell-Yan Sivers asymmetry (no source formula was read).
- Comparison with data.
