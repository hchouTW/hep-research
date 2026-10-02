# Derivation record: tree-level e+e- -> mu+mu- (theory:qed-benchmark)

**Status: `analytic-derivation`.** The result is exact at tree level under the stated assumptions. The algebra was done by SymPy 1.14.0 from explicit Dirac matrices, and SymPy simplification is trusted as a tool. This is not a formal proof. Numerical agreement in `scripts/predict.py` corroborates the result on a finite set of checks and is not proof either.

**Reference read.** PDG review "Cross-Section Formulae for Specific Processes" (H. Baer, R.N. Cahn, revised August 2019), in F. Takahashi et al. (Particle Data Group), Int. J. Mod. Phys. A 41, 2630011 (2026), section 51.2 "Production of light particles", eqs. (51.2) and (51.3). It was read on 2026-10-02 at page level through a text-extraction fetch (`evidence/`, qedbench:S01, C01, C02). The derivation below was done independently and then compared with the reference.

## Steps (`scripts/derive.py`, output `derivations/derivation.json`)

1. **Kinematics** in the c.m. frame. E = sqrt(s)/2; p1 = (E, 0, 0, E) for e-; p2 = (E, 0, 0, -E) for e+; p3 = (E, p sin theta, 0, p cos theta) for mu-; p4 = -p3 in space for mu+; p = sqrt(E^2 - m^2), so beta = p/E = sqrt(1 - 4m^2/s).
2. **Amplitude.** M = (e^2/s) [vbar(p2) gamma^mu u(p1)] [ubar(p3) gamma_mu v(p4)]. Its square summed over spins is (e^4/s^2) Tr[p2-slash gamma^mu p1-slash gamma^nu] Tr[(p3-slash + m) gamma_mu (p4-slash - m) gamma_nu], with electrons massless. Both traces are evaluated with explicit 4x4 Dirac matrices; no trace theorem is assumed. Averaging over the 4 initial spin states gives (1/4) sum |M|^2 = 16 pi^2 alpha^2 [s(1 + c^2) + 4 m^2 (1 - c^2)] / s, where c = cos theta.
3. **Phase space.** d sigma / d Omega = beta / (64 pi^2 s) x (1/4) sum |M|^2 = (alpha^2 / 4s) beta [1 + c^2 + (1 - beta^2)(1 - c^2)]. **Identical to PDG eq. (51.2)** with N_c = 1 and Q_f^2 = 1 (SymPy difference simplifies to 0).
4. **Integration.** d sigma / d cos theta = 2 pi d sigma / d Omega. sigma = (4 pi alpha^2 / 3s) beta (3 - beta^2)/2, which tends to 4 pi alpha^2 / 3s as beta -> 1. **Identical to PDG eq. (51.3)** in its symbolic form.
5. **Massless shape.** (1/sigma) d sigma / d cos theta = (3/8)(1 + cos^2 theta). The forward-backward asymmetry is 0, and the distribution is even in cos theta.
6. **Threshold.** sigma / beta tends to (3/2)(4 pi alpha^2 / 3s) as beta -> 0, so the cross section vanishes linearly in beta.

## Numerical input

The prediction uses the reference's conversion 4 pi alpha^2 / 3 = 86.8 nb GeV^2 (eq. 51.3, three significant figures). It enters as a fully correlated relative uncertainty of 0.05/86.8 = 5.8e-4 from rounding. No value of alpha or (hbar c)^2 is used separately.

## Checks run

| Check | Result |
|---|---|
| Massless squared amplitude = e^4 (1 + c^2) | pass |
| d sigma / d Omega = PDG eq. 51.2 (any beta) | pass |
| sigma(beta -> 1) = PDG eq. 51.3; sigma(beta) = (4 pi alpha^2/3s) beta (3 - beta^2)/2 | pass |
| Normalized shape 3/8 (1 + c^2); A_FB = 0; even in c | pass |
| Threshold: linear in beta | pass |
| Units: sigma scales as 1/s; 86.8 nb GeV^2 / 100 GeV^2 = 868 pb at sqrt(s) = 10 GeV | pass (`predict.py`) |
| Bin integrals sum to sigma; full-range integral = sigma | pass |
| Trapezoid converges at order 2.00; Simpson exact (quadratic integrand); scipy quad agrees to < 1e-10 relative | pass |

## Checks not run

- An independent numerical value of 4 pi alpha^2 / 3 in nb GeV^2 from separately read values of alpha and (hbar c)^2. No physical-constants source was read in this session.
- A quantitative size of Z exchange and gamma-Z interference at the benchmark point, which needs m_Z, Gamma_Z and sin^2 theta_W from a read source.
- The size of QED radiative corrections and the running of alpha.
- A numerical estimate of the muon-mass correction. The symbolic factor beta(3 - beta^2)/2 is available, but no muon-mass value is cited here.
- A formal proof. SymPy's simplification steps are not independently verified.
