# Derivation record: B/C in the weighted-slab and 1D thin-disc models (theory:cr-secondary-ratio)

**Status: `analytic-derivation`** under the model assumptions below. The algebra is checked by SymPy
(`scripts/derive.py`, output `derivations/derivation.json`) and the closed forms are checked numerically against the
profile's own solvers (`scripts/predict.py --benchmark`). Not a formal proof; no propagation code was run.

**Machine-readable header:** `derivations/theory-spec.json` (artifact type `theory-spec`, `model.family`
`cosmic-ray-propagation`, `degenerate_directions: ["D0/L"]`), written by `scripts/make_artifacts.py`.

**References.** None was opened in this session (no network was approved for this work package): the sources in
`evidence/sources.json` are cited from background knowledge at `verification_level: not-opened`, and the claims
built on them (`crsr:C01`-`C04`) are context, not inputs. Every formula below is derived here and checked by the
code; no number is taken from a paper. The relation of this derivation to the literature:

- The diffusion-halo picture (thin gas disc, halo of half-height L, free escape) and the statement that stable
  secondary-to-primary ratios fix only the ratio of the diffusion coefficient to the halo height, with the halo
  height needing radioactive clocks, are standard; see the review of Strong, Moskalenko and Ptuskin, Annu. Rev.
  Nucl. Part. Sci. 57 (2007) 285, arXiv:astro-ph/0701517 [crsr:C01].
- Maurin, Donato, Taillet and Salati, ApJ 555 (2001) 585, arXiv:astro-ph/0101231, fit B/C with a two-zone diffusion
  model and find the normalization K0 and L strongly correlated; Génolini et al., PRD 99 (2019) 123028,
  arXiv:1904.08917, use a 1D model and discuss the same K0/L degeneracy [crsr:C02].
- Jones, Lukasiak, Ptuskin and Webber, ApJ 547 (2001) 264, arXiv:astro-ph/0007293, relate the weighted-slab technique
  to diffusion models [crsr:C03]; Génolini, Putze, Salati and Serpico, A&A 580 (2015) A9, arXiv:1504.03134, compare
  leaky-box and 1D descriptions as a source of theoretical uncertainty for B/C, with the 1D grammage proportional to
  the gas surface density times v L / K [crsr:C04].

These attributions are unverified (source not opened; locations not checked). The result below does not depend on
them: it is re-derived and checked.

## Model and notation

Species: parents j (C, O; pure primaries, observed ratios r_j = N_j / N_C given as input) and one effective stable
secondary s (B). Fragmentation conserves kinetic energy per nucleon E/n (straight-ahead), so all species are compared
at the same E/n and, with masses A u, the same velocity v = beta c. Cross sections on hydrogen: production
sigma_js (effective, cumulative) and inelastic sigma_i; 1/lambda_i = sigma_i / m_H, with m_H the target mass.

## Steps

1. **Weighted slab.** Along the path length x (g/cm^2): dN_j/dx = -N_j/lambda_j, dN_s/dx = sum_j N_j/lambda_js -
   N_s/lambda_s, N_s(0) = 0. With N_j(0) = N_j0 one gets N_s(x) = sum_j N_j0 (exp(-x/lambda_j) - exp(-x/lambda_s)) /
   (lambda_js (1/lambda_s - 1/lambda_j)). The observed density is the average over the path-length distribution
   G(x) = exp(-x/lambda_esc)/lambda_esc: <N_j> = N_j0 (1/lambda_esc) / (1/lambda_esc + 1/lambda_j) and
   <N_s> = sum_j N_j0 (1/lambda_js)(1/lambda_esc) / ((1/lambda_esc + 1/lambda_j)(1/lambda_esc + 1/lambda_s)). Hence

   N_s / N_C = sum_j (sigma_js / m_H) r_j / (1/lambda_esc + sigma_s / m_H),

   identical to the steady-state leaky box with escape length lambda_esc.
2. **1D thin disc.** -D_i d^2N_i/dz^2 + 2h delta(z) n_H v sigma_i N_i = 2h delta(z) S_i in |z| < L, N_i(+-L) = 0, with
   S_j the primary source and S_s = sum_j n_H v sigma_js N_j(0). Away from z = 0 the equation is N'' = 0, so
   N_i = N_i(0)(1 - |z|/L). Integrating across z = 0: 2 D_i N_i(0)/L + 2h n_H v sigma_i N_i(0) = 2h S_i, so

   N_s(0) / N_C(0) = sum_j sigma_js r_j / (sigma_s + D_s / (h n_H v L)),

   with D_s = D(R_s) at the secondary's rigidity R_s = (A_s/Z_s) p/n.
3. **Equivalence and degeneracy.** Step 2 equals step 1 exactly when

   lambda_esc = n_H m_H h v L / D(R_s)   (g/cm^2).

   With D(R) = D0 beta (R/R0)^delta and v = beta c, lambda_esc = n_H m_H h c L / D0 (R/R0)^(-delta): beta cancels, and
   D0 and L enter only as D0/L (with h n_H, the gas column, as a fixed input). So in this model **B/C at any energy
   constrains D0/L and not D0 and L separately**: `degenerate_directions: ["D0/L"]`. In fuller models (convection,
   reacceleration, decay, losses) the degeneracy is approximate and holds best at high energy, where those terms
   matter least [crsr:C01, C02; unverified attribution]; this profile does not model them. The gas column h n_H and a
   common rescaling of all production cross sections are also degenerate with D0/L; they are inputs here, not fit
   parameters.
4. **Finite disc (benchmark only).** Gas and sources uniform in |z| < h. Inside, D_i N_i'' = Gamma_i N_i - S_i(z)
   with Gamma_i = n_H v sigma_i; outside, N_i = B_i (L - z). For a parent, N_j = a_j + A_j cosh(k_j z) with
   a_j = q_j/Gamma_j, k_j^2 = Gamma_j/D_j, A_j = -a_j/Delta_j, Delta_i = cosh(k_i h) + (L - h) k_i sinh(k_i h)
   (continuity of N and N' at z = h). For the secondary, N_s = c + sum_j E_j cosh(k_j z) + F cosh(k_s z) with
   c = sum_j Gamma_js a_j/Gamma_s, E_j = Gamma_js A_j/(Gamma_s - D_s k_j^2) and F = -(c + sum_j E_j Delta_j)/Delta_s.
   As h -> 0 at fixed column h n_H this tends to step 2 (checked numerically: the difference falls linearly with h).

## Checks run

| Check | How | Result |
|---|---|---|
| Slab average equals the closed form | SymPy `dsolve` + exact integral | pass |
| Thin-disc jump solution, linear halo profile, N(L) = 0 | SymPy | pass |
| Thin disc = slab with lambda_esc = n_H m_H h v L / D | SymPy, exact | pass |
| Ratio invariant under (D, L) -> (c D, c L); changes under D alone | SymPy, exact | pass |
| Finite-disc closed form solves both regions, continuous N and N' at h, symmetric at 0 | SymPy, rational identity in cosh/sinh | pass |
| Slab ODEs integrated (DOP853) and averaged over G(x) by quadrature vs closed form | `predict.py --benchmark` | max relative deviation ~1e-11 (tolerance 1e-7) |
| Finite-volume solution (6,000 cells, node at z = h) vs finite-disc closed form | `predict.py --benchmark` | ~3e-8 (tolerance 1e-6) |
| Finite disc tends to thin disc as h -> 0 at fixed column | h = 400, 100, 25, 6.25, 1.56 pc | 6.0e-2, 1.5e-2, 3.7e-3, 9.3e-4, 2.3e-4 (monotonic, linear in h) |
| Units: grammage in g/cm^2, ratio dimensionless | by construction in the code and SymPy forms | pass |
| A wrong grammage mapping (factor 2) breaks the equivalence check | `tests/test_derivation.py` | pass (negative test) |

## Checks not run

Formal proof; comparison with a published numerical B/C benchmark (open question B1: the search of 2026-10-15 found
no B/C or grammage printed in a table for inputs this profile can reproduce; record in
`benchmarks/external-benchmark-search.json`, claim `crsr:C06`); comparison with any
propagation code; comparison with measured data; energy-dependent cross sections; any model term excluded in
`profile.json`.
