# Neutrino oscillations

Three-flavour oscillation probabilities in vacuum and in matter of constant density, with the conventions that must
travel with every number. Tool: `<plugin root>/skills/hep-theory/scripts/neutrino_oscillation.py`. Fits of oscillation
parameters to data are inference (hep-statistics); global fits of the parameters are outside v1.

## Conventions block (state it with every result)

| Item | State |
|---|---|
| Mixing matrix | PDG parametrization (below), angles in [0, 90] degrees, delta_CP in [0, 360) |
| Splittings | dm21 = m2^2 - m1^2 >= 0, dm31 = m3^2 - m1^2; the mass ordering is the sign of dm31 (normal > 0, inverted < 0) |
| Units | dm^2 in eV^2, L in km, E in GeV; the phase dm^2 L / 4E = 1.267 dm^2[eV^2] L[km] / E[GeV] |
| Particle | neutrino or antineutrino (U -> U*, V_e -> -V_e) |
| Matter | vacuum, or constant density rho with electron fraction Y_e; never an implied Earth profile |
| Parameter values | from the user, with their source and edition; the plugin has no built-in values |

## Mixing matrix

The PDG Review (2026 edition, "Neutrino Masses, Mixing, and Oscillations", Eqs. 14.33-14.34) writes the lepton mixing
matrix as U = R23 U13(delta_CP) R12, so that

- U_e1 = c12 c13, U_e2 = s12 c13, U_e3 = s13 e^{-i delta_CP};
- U_mu1 = -s12 c23 - c12 s13 s23 e^{i delta_CP}, U_mu2 = c12 c23 - s12 s13 s23 e^{i delta_CP}, U_mu3 = c13 s23;
- U_tau1 = s12 s23 - c12 s13 c23 e^{i delta_CP}, U_tau2 = -c12 s23 - s12 s13 c23 e^{i delta_CP}, U_tau3 = c13 c23,

with c_ij = cos theta_ij and s_ij = sin theta_ij. For Majorana neutrinos Eq. (14.33) multiplies on the right by
diag(e^{i eta1}, e^{i eta2}, 1); these phases cancel in oscillation probabilities. Other parametrizations (a different
rotation order, or the phase on another element) give the same physics with different numbers for the angles and the
phase: convert before comparing.

## Vacuum

P(nu_alpha -> nu_beta) = delta_ab - 4 sum_{i>j} Re[U*_ai U_bi U_aj U*_bj] sin^2 X_ij
+ 2 sum_{i>j} Im[U*_ai U_bi U_aj U*_bj] sin 2X_ij, with X_ij = dm^2_ij L / 4E (Eq. 14.39-14.40). The antineutrino
probability takes U -> U*: the last term changes sign, which is the CP-violating part. CPT gives
P(nu_a -> nu_b) = P(nubar_b -> nubar_a) in vacuum; matter breaks it, since the medium is not CP symmetric.

Two-flavour limit: P = sin^2 2theta sin^2(1.267 dm^2 L / E), the oracle for any implementation.

## Matter of constant density

Charged-current scattering on electrons adds the potential V_e = sqrt(2) G_F n_e to nu_e (minus for antineutrinos);
the neutral-current potential is the same for every active flavour and drops out (Eqs. 14.53-14.58). In the flavour
basis the evolution is i d nu / dx = H nu with

H = [U diag(0, dm21, dm31) U^dagger + diag(A, 0, 0)] / 2E, A = 2 E V_e.

For constant density the amplitude is exp(-i H L), which the tool evaluates by diagonalizing H; with n_e = 0 it equals
the vacuum formula. n_e = Y_e rho N_A, and V_e = 7.63e-14 eV for Y_e rho = 1 g/cm^3. In two flavours the effective
angle and splitting are sin 2theta_m = dm^2 sin 2theta / dm_m^2 and dm_m^2 = sqrt((dm^2 cos 2theta - A)^2 +
(dm^2 sin 2theta)^2): the MSW resonance at A = dm^2 cos 2theta, whose position depends on the sign of dm^2, which is
why long baselines are sensitive to the mass ordering.

A varying density (the Earth's layers, the Sun) needs a profile and a numerical evolution; the tool does not provide
one and says so. Adiabatic solar-neutrino conversion is in the same review (Section 14.5.1).

## Validity

- Ultra-relativistic neutrinos, plane waves: no decoherence or wave-packet separation, no averaging over the energy
  resolution unless the user averages the output.
- Three active flavours: sterile states, non-standard interactions, non-unitarity and decay are outside the tool.
- Constant density only; state the density used and why it represents the path.

<!-- example: baselines -->
Illustrative L/E regions (Table 14.1 of the review lists typical L and E per source): an accelerator beam with
L = 295 km and E near 0.6 GeV, or L = 1300 km with E of a few GeV, sits near the first atmospheric-splitting maximum;
reactor antineutrinos at a few MeV and L near 50 km reach the solar-splitting oscillation. These are examples of
baselines, not parameter values.
<!-- /example -->

## Source

Particle Data Group, Review of Particle Physics (2026 edition), "Neutrino Masses, Mixing, and Oscillations" (revised
March 2026), Sections 14.3-14.5, read in full on 2026-10-17 from pdg.lbl.gov (the review's PDF); equations cited by
number above.
