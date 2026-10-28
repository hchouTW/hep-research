# Derivation record: 1D thin disc with convection and radioactive decay (theory:cr-secondary-ratio, B2)

**Status: `analytic-derivation`** under the model assumptions below. The algebra is checked by SymPy
(`scripts/derive_convection_decay.py`, output `derivations/convection-decay-derivation.json`, 39 checks) and the
closed forms are checked numerically against an independent `scipy.integrate.solve_bvp` solution of the same
boundary-value problem (`scripts/convection_decay.py --benchmark`). Not a formal proof; no propagation code was run.
Pure-diffusion parent result: `derivations/derivation-record.md` (step 2).

**References.** None was opened for this work package (no literature access in its consent list). The closed forms
below are derived here from the transport equation and checked by the code; no formula or number is taken from a
paper. For context only (unverified attribution, source not opened, location not checked): one-dimensional
thin-disc solutions with a constant wind and decay of the form N(0) = 2 h q / (V_c + D S coth(S L/2) + 2 h Gamma_inel)
are used in the USINE-based analyses of Maurin, Putze and Derome (e.g. Putze, Derome and Maurin, A&A 516 (2010)
A66, arXiv:1001.0551) and in the review of Strong, Moskalenko and Ptuskin [crsr:C01].

## Model and notation

Same as the pure-diffusion record (species at equal E/n, cross sections on hydrogen, parents C and O with given
mid-plane ratios r_j), plus:

- constant convective speed V_c(z) = V_c sign(z) in the whole halo, written in conservative form d/dz(V_c(z) N);
  the derivative of sign(z) gives a sweeping term 2 V_c delta(z) N at the disc. The adiabatic energy change that
  accompanies div V, reacceleration and all other energy changes are neglected;
- radioactive decay of an unstable secondary at rate Gamma = 1/(gamma tau_0) in the whole halo (Lorentz time
  dilation; gamma at the species' E/n with mass A u), tau_0 = t_1/2 / ln 2 with t_1/2 from
  `core.constants.physical.half_life_seconds` (NUBASE2020; 10Be: 1.387 +- 0.012 My); decay inside the thin disc is
  neglected (measure zero);
- the decay daughter keeps its gain term (10Be -> 10B at the same E/n): halo source Gamma N_R(z);
- fully stripped 7Be cannot decay by electron capture and is propagated as stable; the config records this as its
  `stable_assumption`, and the code refuses any species with a finite NUBASE half-life that has neither a decay entry
  nor a recorded stable assumption.

Equation for species i in |z| < L, N_i(+-L) = 0, steady state:

    -D_i N_i'' + d/dz (V_c sign(z) N_i) + Gamma_i N_i + 2 h delta(z) n v sigma_i N_i = 2 h delta(z) q_i + G_i(z)

with q_i = n v sum_j sigma_ji N_j(0) and G_i the halo gain of a daughter.

## Steps

1. **Stable species with convection.** For z > 0: -D N'' + V_c N' = 0, so N = N(0)(e^{V_c L/D} - e^{V_c z/D}) /
   (e^{V_c L/D} - 1). Integrating across the disc: -2 D N'(0+) + 2 V_c N(0) + 2 h n v sigma N(0) = 2 h q, hence
   N(0) = 2 h q / (K + 2 h n v sigma), K = V_c (1 + coth(V_c L / 2D)).
2. **Radioactive species.** For z > 0: -D N'' + V_c N' + Gamma N = 0, N = N(0) e^{V_c z/2D} sinh(S(L - z)/2) /
   sinh(S L/2), S = sqrt(V_c^2/D^2 + 4 Gamma/D). The jump gives the same form with K = V_c + D S coth(S L/2); step 1
   is Gamma = 0 (S = V_c/D). The secondary-to-parent ratio is sigma_Ps r / (sigma_s + K / (2 h n v)).
3. **Limits (B2-1).** K -> 2 D/L for V_c -> 0 then Gamma -> 0 and in the other order (`sp.limit`), confirmed by
   Taylor series independent of `sp.limit`: K = 2D/L + V_c + V_c^2 L/(6D) + O(V_c^3) at Gamma = 0, and
   K = 2D/L + (2/3) Gamma L + O(Gamma^2) at V_c = 0. So the ratio tends to the pure-diffusion closed form
   sigma_Ps r / (sigma_s + D_s / (h n v L)) of `derivation-record.md` step 2.
4. **Daughter of a radioactive species.** With k_+- = V_c/(2 D_R) +- S_R/2, the parent profile is
   a_- e^{k_- z} + a_+ e^{k_+ z}, a_- = N_R(0)/(1 - e^{-S_R L}), a_+ = -N_R(0) e^{-S_R L}/(1 - e^{-S_R L}). The
   daughter's halo equation -D_d N'' + V_c N' = Gamma N_R has the particular solution sum c_+- e^{k_+- z},
   c = Gamma a / (V_c k - D_d k^2), plus alpha + beta g(z), g = (e^{V_c z/D_d} - 1) D_d / V_c (g = z at V_c = 0);
   N(L) = 0 and the disc jump fix alpha and beta (closed form in `convection_decay.decay_gain_mid_plane`). The gain
   adds to the daughter's direct disc term, which is step 1 unchanged. In the code k_- = -2 Gamma / (V_c + D_R S_R),
   so Gamma / k_- = -(V_c + D_R S_R)/2 has no cancellation as Gamma -> 0.

## Checks run

| Check | How | Result |
|---|---|---|
| Steps 1, 2: halo equation, N(0), N(L) = 0, disc jump gives the closed form | SymPy, exact (exponentials replaced by independent symbols, `sp.cancel`) | pass |
| Step 2 with S as a symbol equals the sqrt form | SymPy | pass |
| Limits V_c -> 0, Gamma -> 0 in both orders, ratio limit = pure diffusion | `sp.limit` | pass |
| Taylor coefficients: constant 2D/L, first order V_c and (2/3) Gamma L | `sp.series` | pass |
| Daughter: parent profile identities, particular and homogeneous parts solve the halo equation, N(L) = 0, jump | SymPy, exact | pass |
| Daughter: direct part equals step 1 | SymPy, exact | pass |
| Daughter: gain vanishes as Gamma -> 0 (D_d != D_R), gain / Gamma converges | 50-digit evaluation at a rational point, Gamma ~ 1e-20..1e-22 | pass (numerical evidence) |
| Decay conserves number: equal D and sigma, N_R(0) + N_d(0) = stable solution, any Gamma | SymPy, exact | pass |
| Dimensions (B2-2), 13 checks: [S^2] = length^-2; [S L] = [V_c L/D] = [Gamma t] = 1; [V_c] = [D S] = [2D/L] = [2 h n v sigma] = velocity; K/(2 h n v) an area; ratio dimensionless; [g(L)] = length; [k] = length^-1; c has the dimension of a density | SymPy, every symbol mapped to its dimension in length and time; a sum of terms of different dimension raises | pass |
| Units in the code (B2-2): V_c km/s -> cm/s (1e5); t_1/2 from NUBASE2020 in s, tau_0 ln 2 = t_1/2; gamma sqrt(1 - beta^2) = 1; Gamma gamma tau_0 = 1; kpc -> cm and cross sections mb -> cm^2 as in `predict.py` | `convection_decay.py --benchmark` | pass |
| Closed forms vs `solve_bvp` (2001 nodes, tol 1e-10), all five secondaries incl. the coupled 10Be/10B system, 0.1-1000 GeV/n | `--benchmark` | max relative deviation 9.8e-15 (tolerance 1e-6) |
| V_c = 0 and no decay vs `predict.thin_disc_ratio` (B/C benchmark, set A), 1-1000 GeV/n | `--benchmark` | 2.2e-16 (tolerance 1e-12) |
| Approach: V_c = 1 ... 1e-4 km/s with Gamma scaled by 1 ... 1e-8, 10 GeV/n | `--benchmark` | 0.26, 4.1e-3, 7.2e-5, 4.0e-6, 4.0e-7 (monotonic; < 1e-4) |
| Number conservation, Gamma scaled by 0, 0.3, 1, 3, 30 | `--benchmark` | spread < 1e-15 (tolerance 1e-10) |
| Discriminating: the advective disc condition (no 2 V_c N(0) term) fails the SymPy zero test and differs from `solve_bvp` by > 1e-3; a sum of terms of different dimension is refused | `tests/test_convection_decay.py` | pass (negative tests) |

## Checks not run

Formal proof; comparison with a published closed-form or code benchmark (no source opened); comparison with USINE,
DRAGON2 or GALPROP (work packages B3 and D1); comparison with data; energy-dependent cross sections; reacceleration
(no closed form; excluded), energy losses and the adiabatic term of the wind, a convective gradient
(`dVc_dz_kms_per_kpc`), a finite-thickness disc with convection or decay, decay inside the disc, electron-capture
nuclei and the other clocks (14C, 26Al, 36Cl, 54Mn), secondary-to-secondary feeding other than the 10Be -> 10B gain.
