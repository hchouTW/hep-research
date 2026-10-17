# Dark-matter phenomenology: conventions for rates, J factors and relic abundance

Conventions only, so that a dark-matter number can be reproduced: which halo, which form factor, which
self-conjugacy factor, which J. In v1: the arithmetic below, with every input from the user. Outside v1: deciding
which dark-matter model explains an excess (limited support; the comparison itself is hep-statistics), global fits,
and full relic-density Boltzmann solvers. Tool: `<plugin root>/skills/hep-theory/scripts/dm_direct_rate.py`
(`rate`, `jfactor`, `flux`). No halo, cross-section or yield value is built in.

## Direct detection: the spin-independent recoil rate

Per unit target mass (PDG Dark Matter review, Eqs. 27.10-27.12; Duda, Kemper and Gondolo 2007, Eqs. 2 and 5):

    dR/dE_R = rho0 sigma_N |F(q)|^2 eta(v_min) / (2 m_chi mu_N^2),   v_min = sqrt(m_N E_R / (2 mu_N^2)),
    q = sqrt(2 m_N E_R),   eta(v_min) = integral over v > v_min of f(v + v_E) / v d^3v.

- Cross section: for isospin-conserving couplings sigma_N = sigma_n A^2 (mu_N / mu_n)^2, with the per-nucleon
  cross section sigma_n quoted at zero momentum transfer. State the coupling assumption; spin-dependent and
  non-relativistic EFT operators have different nuclear responses (not implemented).
- Halo: the standard halo model is an isotropic Maxwellian in the galactic frame, f ~ exp(-|v|^2 / v0^2) truncated at
  the escape speed v_esc, seen from the Earth's velocity v_E. A commonly recommended parameter set (Baxter et al.
  2021, Table 1) is rho0 = 0.3 GeV/c^2/cm^3, v_esc = 544 km/s, local standard of rest (0, 238, 0) km/s, solar
  peculiar velocity (11.1, 12.2, 7.3) km/s and average Earth speed 29.8 km/s; the PDG review quotes other
  determinations (for example a local density of 0.55 +- 0.17 GeV/cm^3 with an anisotropic halo). These are
  conventions for comparing results, not measured truths: give the values used with every rate or limit.
- Form factor: the Helm form |F|^2 = (3 j1(q R1) / (q R1))^2 exp(-q^2 s^2) with the Lewin-Smith parameters
  R1^2 = c^2 + (7/3) pi^2 a^2 - 5 s^2, c = 1.23 A^(1/3) - 0.60 fm, a = 0.52 fm, s = 0.9 fm (Duda et al., Eqs. 9-12).
  Duda et al. show Helm parameter choices differ by up to tens of percent at high momentum transfer: state the choice.
- A published reference rate to check the tool against is to-verify: none of the sources read gives one for a
  stated configuration. The tool's checks are analytic (velocity-integral limits, normalization, Helm zeros).

## Indirect detection: source terms, J and D factors

Production rate of a final-state particle per volume (PDG Eqs. 27.18-27.21): annihilation
Gamma = c rho^2 <sigma v> N / m^2, with c = 1/2 for a self-conjugate particle and c = 1/4 for a particle-antiparticle
pair without asymmetry; decay Gamma = rho N / (m tau). The flux integrates Gamma / 4 pi along the line of sight over
the solid angle, which factors into the particle term and

    J = integral over dOmega of the line-of-sight integral of rho^2 dl,   D = the same with rho.

For a target of uniform density rho and radius r at distance d >> r, J ~ 4 pi r^3 rho^2 / (3 d^2) (PDG Eq. 27.22); the
tool reproduces this limit. `jfactor` integrates uniform, NFW, Einasto or Burkert profiles with user parameters and
a truncation radius over a cone around the halo centre. Charged products (positrons, antiprotons) do not travel in
straight lines: hand their source term to the propagation reference ([cosmic-ray propagation](cosmic-ray-propagation.md)
and the theory-domain profiles listed in `<plugin root>/profiles/registry.json`).

## Relic abundance: conventions only

The freeze-out abundance follows from dn/dt + 3 H n = -<sigma v>(n^2 - n_eq^2) (PDG Eq. 27.2). For a cold relic, to
leading order Omega h^2 ~ 0.1 (x_fo / 20)(10^-8 GeV^-2 / sigma) with x = m / T and x_fo between 10 and 50 (PDG
Eqs. 27.5-27.6); a hot relic gives Omega h^2 ~ m / 93 eV for the Standard-Model neutrino case (Eq. 27.4). These are
estimates: entropy injection, a non-radiation-dominated early universe, coannihilation or resonances change them. A
full Boltzmann solution is outside v1; say so and name the code a result came from.

## What to report

The halo model and every parameter, v_E and the date if the rate is time dependent; the form factor and its
parameters; the coupling assumption and how sigma_N is scaled from sigma_n; for indirect detection the profile, its
parameters and truncation, the region (J over which cone), c, and the yield source; for relic statements the
approximation used.

## Sources read (2026-10-17)

- PDG Review of Particle Physics 2026, "Dark Matter" (L. Baudis, S. Profumo, rev. August 2025): Secs. 27.3, 27.4.1,
  27.6.2 and the start of 27.7 (Eqs. 27.2-27.6, 27.10-27.12, 27.18-27.22), full text of those sections.
- D. Baxter et al., "Recommended conventions for reporting results from direct dark matter searches",
  arXiv:2105.00599v3; Sec. 3.1 and Tables 1-2.
- G. Duda, A. Kemper, P. Gondolo, "Model independent form factors for spin independent neutralino-nucleon scattering
  from elastic electron scattering data", arXiv:hep-ph/0608035; Secs. I-II (Eqs. 1-12).
