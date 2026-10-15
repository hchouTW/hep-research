# Derivation record: force-field solar modulation and power-law closed forms (theory:heliospheric-modulation)

**Status: `analytic-derivation`** under the force-field assumptions below. The algebra is checked by SymPy
(`scripts/derive.py`, output `derivations/derivation.json`, SymPy 1.14.0 with Python 3.13.2 in the E2 environment,
chosen by `skills/hep-computing/scripts/find_python.py`). Not a formal proof. The force field is itself an approximation to the heliospheric transport equation; this record derives its consequences, not
its accuracy.

**Machine-readable header:** `derivations/theory-spec.json` (artifact type `theory-spec`, `model.family`
`heliospheric-modulation`, `degenerate_directions` phi vs LIS shape), written by `scripts/make_artifacts.py`.

**References.** Gleeson and Axford, ApJ 154 (1968) 1011 [helmod:S01]; Ghelfi, Barao, Derome and Maurin, A&A 591 (2016)
A94, arXiv:1511.08650 [helmod:S02]; Cholis, Hooper and Linden, arXiv:1511.01507v3 [helmod:S03]. All three were read on
2026-10-13 for `skills/hep-theory/references/cosmic-ray-propagation.md`; the claims in `evidence/claims.json` restate
that record. They were not re-opened for this profile (no network approved). The final relation [helmod:C01, C04] is
taken from them; the intermediate steps are written in this profile's notation and checked by SymPy.

## Notation

c = 1, e = 1. p momentum (GeV), m rest mass of the nucleus (GeV), Z = |Z| the charge number, A_n the mass number,
E = sqrt(p^2 + m^2), T = E - m, beta = p / E, R = p / Z (GV). f(r, p) is the phase-space density; the flux per unit
kinetic energy is J_T = p^2 f. phi in GV, Z phi in GeV.

## Steps

1. **Force-field equation.** Zero radial streaming, spherical symmetry and a steady state give
   kappa(r, p) df/dr + (V p / 3) df/dp = 0. With kappa = kappa_1(r) beta R (separable, proportional to rigidity) and
   phi(r) = int_r^r_b V / (3 kappa_1) dr', f = F(T + Z phi(r)) solves it for any F (SymPy: the residual simplifies to
   zero; the opposite sign F(T - Z phi) leaves a nonzero residual, the negative test).
2. **Characteristic.** Along dp/dr = V p / (3 kappa), dT/dr = beta dp/dr = Z V / (3 kappa_1) = -Z dphi/dr, so
   T + Z phi is constant: a particle observed with T at 1 AU had T + Z phi at the boundary, where phi = 0 and f = f_LIS.
3. **Flux relation.** J_TOA(T) = p(T)^2 f_LIS(T + Z phi) = p(T)^2 / p(T')^2 J_LIS(T'), T' = T + Z phi, with
   p^2 = T (T + 2m) = E^2 - m^2. This is the Gleeson-Axford form J / (E^2 - E_0^2) = invariant [helmod:C01].
4. **Power-law closed forms.** For J_LIS = A x^-gamma in the variable x of each kind:
   - total kinetic energy: J = A T (T + 2m) / (T' (T' + 2m)) T'^-gamma;
   - per nucleon (t = T / A_n, m_n = m / A_n, t' = t + (Z / A_n) phi [helmod:C04]):
     J = A t (t + 2 m_n) / (t' (t' + 2 m_n)) t'^-gamma; SymPy checks it equals A_n times the total-energy relation
     with the LIS written in t;
   - rigidity (p = Z R, E' = E + Z phi, p' = sqrt(E'^2 - m^2), R' = p' / Z): J = A p^3 E' / (p'^3 E) R'^-gamma; SymPy
     checks it equals (beta / beta') (p^2 / p'^2) A R'^-gamma, the Jacobian dT/dR = Z beta at each point, and that
     the kinetic-energy shift between p and p' is Z phi.
5. **Limits.** phi -> 0 returns the LIS in all three kinds. At large T the ratio J_TOA / J_LIS(T) =
   1 - (gamma + 2) Z phi / T + O(T^-2). As T -> 0, J_TOA -> 2 m A T (Z phi)^-gamma / (Z phi (Z phi + 2m)), linear in T.

## Benchmark against the implementation

`scripts/predict.py --benchmark` runs `skills/hep-measurement/scripts/solar_modulation_force_field.py` (as a separate
process, its documented CLI) on 90 synthetic points: two species (masses near the proton and helium-4 masses, test
inputs), phi = 0, 0.5, 1.0 GV, the three energy kinds, five points each from 0.1 to 200 GeV (GeV/n) (or 0.5 to 300 GV).
Result (2026-10-15): largest relative difference to the closed form 2.4e-15 (tolerance 1e-10), phi = 0 returns the
LIS to 2.4e-15, the script's `--demodulate` of its own modulated flux returns the LIS to 1.7e-16, and every modulated
flux lies below the LIS. Status `demonstrated-on-synthetic-data` (`tests/test_benchmark.py`).

## Checks run

| Check | Result |
|---|---|
| F(T + Z phi) solves the force-field equation; F(T - Z phi) does not | pass (SymPy, exact) |
| T + Z phi constant along the characteristic | pass (SymPy, exact) |
| p^2 = T (T + 2m) = E^2 - m^2 | pass (SymPy, exact) |
| per-nucleon and rigidity forms equal the total-energy relation with their Jacobians | pass (SymPy, exact) |
| phi -> 0, large-T and small-T limits | pass (SymPy, exact) |
| script vs closed form, phi = 0, round trip | pass (relative 1e-10; achieved 2.4e-15) |
| units: phi in GV, Z phi in GeV (e = 1), flux ratio dimensionless | pass (by construction) |

## Checks not run

Formal proof; the derivation of the force-field equation from the full transport equation (assumed, [helmod:C01]);
comparison with a numerical transport or drift model; comparison with a published modulated spectrum or phi series;
comparison with any measurement. The low-energy breakdown [helmod:C03] is quoted, not re-derived.
