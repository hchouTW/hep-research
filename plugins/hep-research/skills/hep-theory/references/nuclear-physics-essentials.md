# Nuclear-physics essentials

An entry page for the nuclear bookkeeping a calculation states before its numbers: masses, decay energies, decay
chains, radii and low-energy reaction rates. Nuclear-structure calculations (shell model, density functionals,
ab initio) are outside v1: say so and give the general discipline.

## Where to go

| Need | Read or run |
|---|---|
| Atomic masses, mass excesses, half-lives (AME2020, NUBASE2020), with edition | `<plugin root>/skills/hep-theory/scripts/physical_data.py nuclide` |
| Decay energy Q of alpha, beta-, beta+ or EC decay | `<plugin root>/skills/hep-theory/scripts/physical_data.py qvalue` |
| Amounts and activities of a decay chain, equilibrium | `<plugin root>/skills/hep-theory/scripts/decay_chain.py` |
| Bare-nucleus masses and kinematics of nuclei (rigidity, energy per nucleon) | `physical_data.py nuclide`; `<plugin root>/core/kinematics/relativistic.py` |
| Selection rules of a decay | [selection rules](selection-rules.md) |

## Atomic and nuclear masses

Mass tables (AME) give **atomic** masses: the neutral atom, with Z electrons and their binding energy. A bare-nucleus
mass is M_nuc = M_atom - Z m_e + B_e/c^2, where the electron binding energy B_e is below 1 keV for light nuclei and
grows with Z; say whether it was neglected. Mass excess Delta = (M_atom - A u) c^2.

Decay energies from atomic masses (ground state to ground state; the electron bookkeeping is already inside the atomic
masses except where noted):

- alpha: Q = [M(Z, A) - M(Z-2, A-4) - M(4He)] c^2;
- beta-: Q = [M(Z, A) - M(Z+1, A)] c^2;
- electron capture: Q = [M(Z, A) - M(Z-1, A)] c^2 (minus the binding energy of the captured electron, if stated);
- beta+: Q = [M(Z, A) - M(Z-1, A) - 2 m_e] c^2: the two electron masses appear because the daughter atom has one
  electron too many and a positron is created. beta+ needs Q_EC > 2 m_e c^2.

With mass excesses the same formulas hold with Delta in place of M c^2. `physical_data.py qvalue` adds the
mass-excess uncertainties in quadrature (correlations between AME values ignored, and said).

## Binding energy

B(Z, A) = [Z M(1H) + (A - Z) m_n - M(Z, A)] c^2 from atomic masses. The semi-empirical (liquid-drop) formula
(volume, surface, Coulomb, asymmetry and pairing terms) explains the trend of B/A; use it for explanation only, never
in place of a tabulated mass, and state its coefficient set if a number is quoted.

## Decay laws and units

- Activity A = lambda N, lambda = ln 2 / T_1/2; the SI unit is the becquerel (1 Bq = one decay per second). A legacy
  unit must be converted with its stated definition.
- Half-lives with year units: NUBASE2020 uses 1 y = 365.2422 d (the tropical year); `core/constants` converts with
  it. Another year (Julian, 365.25 d) differs by 2e-5 relatively: state which.
- Chains: the Bateman solution for linear chains; a branch, a production term or two nearly equal decay constants
  need the matrix form (`decay_chain.py` chooses).
- Equilibrium: **secular** when the parent lives much longer than the daughter (activity ratio -> 1 after several
  daughter half-lives); **transient** when the parent lives longer but not much longer (ratio ->
  T_p / (T_p - T_d)); **none** when the parent is shorter-lived.

## Radii

R = r0 A^{1/3} is a convention, not a measurement: r0 differs between charge, matter and potential radii, and
between authors. State the r0 used and its source, or use a tabulated charge radius.

## Low-energy reactions (astrophysical S factor)

For charged particles below the Coulomb barrier the cross section is written sigma(E) = S(E) e^{-2 pi eta} / E with
the Sommerfeld parameter eta = Z1 Z2 alpha sqrt(mu c^2 / 2E) (mu the reduced mass, E the centre-of-mass energy). The
S factor varies slowly and is what is tabulated and extrapolated. In a thermal plasma the product of the
Maxwell-Boltzmann factor and the tunnelling factor peaks at the Gamow energy E0 = (b kT / 2)^{2/3}, with
b = sqrt(2 mu c^2) pi alpha Z1 Z2 (from eta = b / (2 pi sqrt(E))); the rate integral is dominated by a window around
E0. State the unit system (keV, MeV b), whether E is in the centre-of-mass frame, and the electron-screening
treatment, which changes S at the lowest energies.

## Sources

AME2020 (Huang et al., Wang et al., Chinese Phys. C 45 (2021) 030002 and 030003) and NUBASE2020 (Kondev et al., Chinese
Phys. C 45 (2021) 030001; Section 2.3 and the explanation of Table I read on 2026-10-17 for the year definition) through
`core/constants`; the formulas above follow from these definitions and need no further numbers.
