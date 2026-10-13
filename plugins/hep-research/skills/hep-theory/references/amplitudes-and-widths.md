# Amplitudes, phase space and decay widths

Purpose: state an amplitude, a decay width or a cross section so that its normalization and its sign conventions
travel with it, and say when the narrow-width approximation and a Breit-Wigner form may be used. Formulas below are
quoted from sources opened on 2026-10-13 (list at the end); a line without a source is marked `unverified`. Nothing
here is a validated domain profile: a derivation built from this file carries its own derivation status.

## Conventions that must travel

- **Feynman-rule signs.** The literature differs in the signs of the gauge couplings and fields. Romao and Silva
  parametrize them by signs eta = +-1 (eta_s in the covariant derivative D_mu = d_mu + i eta_s g_s G^a_mu T^a,
  Eqs. (1), (3); eta, eta', eta_Y, eta_Z, eta_theta, eta_e, Eqs. (7)-(18); a ghost sign eta_G, Sec. 2.7) and find
  that only eta_s, eta, eta_e and eta_Z appear in Feynman diagrams (Sec. 3, p. 8; arXiv:1209.6213v2, read 2026-10-13).
  Their tables assume the metric (+, -, -, -) and Bjorken-Drell propagators with an explicit i (p. 2). State the
  metric, the sign of each coupling in D_mu, the factor of i convention of vertices and propagators, and a source
  that uses the same choice.
- **Averaging and summing.** Average over initial spins and colours, sum over final ones; the PDG three-body formula
  below is written "if the decaying particle is a scalar, or we average over its spin states" (PDG 2026 Kinematics,
  Sec. 49.4.3, Eq. (49.22), read 2026-10-13). Identical final-state particles reduce the phase space by combinatoric
  factors (same review, text after Eq. (49.12)). State the averaging factors and the symmetry factor explicitly.
- **Normalization of states and phase space.** The formulas below use the PDG normalization of |M|^2 and of
  d^3p / ((2 pi)^3 2E); a source with another state normalization changes the prefactors. Name it.

## Phase space and widths (PDG 2026, "49. Kinematics", reviewed August 2021, read 2026-10-13)

- Decay rate of a particle of mass M into n bodies in its rest frame: dGamma = (2 pi)^4 / (2M) |M|^2
  dPhi_n(P; p_1, ..., p_n) (Eq. (49.11), Sec. 49.4, read 2026-10-13).
- n-body phase space: dPhi_n = delta^4(P - sum_i p_i) prod_i d^3p_i / ((2 pi)^3 2E_i) (Eq. (49.12), read 2026-10-13);
  recursive form Eq. (49.13).
- Two-body decay: dGamma = |M|^2 |p_1| dOmega / (32 pi^2 M^2) (Eq. (49.18), Sec. 49.4.2, read 2026-10-13), with
  |p_1| = lambda^(1/2)(M^2, m_1^2, m_2^2) / (2M), lambda the Kallen function (Eq. (49.17), read 2026-10-13).
- Three-body decay (scalar or spin-averaged parent): dGamma = |M|^2 dm_12^2 dm_23^2 / ((2 pi)^3 32 M^3), the Dalitz
  form (Eq. (49.22), Sec. 49.4.3, read 2026-10-13); boundaries of the Dalitz plot Eqs. (49.23a,b).
- Cross section for 2 -> n: dsigma = (2 pi)^4 |M|^2 / (4 sqrt((p_1.p_2)^2 - m_1^2 m_2^2)) dPhi_n (Eq. (49.27),
  Sec. 49.5, read 2026-10-13); the flux factor in the lab and c.m. frames is Eq. (49.28a,b).
- The total width is the sum of partial widths over all open channels; a branching ratio is a partial width over the
  total (`unverified` here: standard, but no opened source was cited for the sentence).

## Narrow width and Breit-Wigner forms

- **Narrow-width approximation (NWA).** It replaces |1/(q^2 - M^2 + i M Gamma)|^2 by its integral pi / (M Gamma)
  times delta(q^2 - M^2) (Berdine, Kauer, Rainwater, arXiv:hep-ph/0703058v2, Eq. (1), read 2026-10-13). Its use "is
  justified only if five critical conditions are met: (i) Gamma << M; (ii) daughter particles are much less massive
  than the parent, m << M; (iii) sqrt(s) >> M; (iv) there is no significant interference with non-resonant
  processes; and (v) the resonant propagator is separable from the matrix element" (p. 1, read 2026-10-13). The
  parametric error is O(Gamma/M), but near-degenerate parent and daughter masses enhance it (inverse velocity
  squared, Eq. (2); beta^-4 for a gluino example, Eq. (3)); one SPS1a decay receives "almost a 25% correction, an
  order of magnitude larger than the Gamma/M estimate" (p. 3, read 2026-10-13). Check all five conditions and quote
  the off-shell result where one fails.
- **Breit-Wigner.** BW(s) = 1 / (m_BW^2 - s - i m_BW Gamma(s)) with Gamma_BW = Gamma(m_BW^2) (PDG 2026 "50.
  Resonances", revised August 2025, Eq. (50.31), Sec. 50.3.1, read 2026-10-13); an energy-dependent width
  Gamma(s) = sum_b Gamma_b(s) with Blatt-Weisskopf factors (Eqs. (50.32)-(50.34), read 2026-10-13). A constant width
  is the special case Gamma(s) = Gamma_BW; the review gives no separate numbered fixed-width form. The Breit-Wigner
  parameters differ from the pole parameters sqrt(s_R) = M_R - i Gamma_R / 2 (Eq. (50.20), Sec. 50.2, read
  2026-10-13), and "it is generally inappropriate to employ a sum of Breit-Wigner functions", which breaks unitarity
  (p. 14, read 2026-10-13). State fixed or running width, and BW or pole parameters.
- **Complex-mass scheme.** The W and Z masses are taken complex, mu_W^2 = M_W^2 - i M_W Gamma_W and likewise for the Z
  (Eq. (4.2)), "everywhere in the Feynman rules, in particular in the definition of the weak mixing angle"
  c_w^2 = mu_W^2 / mu_Z^2 (Eq. (4.1)); Ward identities then remain valid "because the gauge-boson masses are modified
  only by an analytic continuation" (Denner, Dittmaier, Roth, Wieders, arXiv:hep-ph/0505042v3, Sec. 4, pp. 24-25,
  read 2026-10-13). In the fixed-width scheme the width enters only the propagators (same paper, Sec. 5). The
  original tree-level scheme (Nucl. Phys. B 560 (1999) 33) was not opened.

## Checks to run and list

- Units and dimensions of |M|^2 for the multiplicity n (`unverified`: dimension counting, no opened source cited).
- Lorentz invariance (the amplitude depends on invariants only), crossing between channels, and known limits (a
  massless limit, threshold behaviour from the lambda^(1/2) factor of Eq. (49.17)).
- Gauge invariance: the Ward identity (replace a photon polarization by its momentum; the amplitude vanishes) and
  independence of the gauge parameter (`unverified`: standard checks, no opened source cited for their statement).
- Phase-space integration analytic vs numerical with a stated tolerance; Dalitz-boundary checks for three bodies.
- A width computed in a finite-width scheme compared with the NWA where the five conditions hold.

## What this file cannot claim

It gives no amplitude for a specific process and no numerical width; it does not validate a generator's width
treatment; polarized or interfering resonances beyond the cited forms are not covered. A width or cross section
derived with it carries `analytic-derivation` only when every step and check is recorded, otherwise a lower status.

## Deliverables

The amplitude with its sign conventions and source, the averaging and symmetry factors, the phase-space measure, the
width or cross section with units, the resonance treatment (NWA with the five conditions checked, fixed or running
BW, pole or complex-mass scheme), the checks run and not run, and the derivation status.

## Sources read (all on 2026-10-13)

- PDG, "49. Kinematics", reviewed August 2021 by D. Miller and D.R. Tovey, in F. Takahashi et al. (Particle Data
  Group), Int. J. Mod. Phys. A 41, 2630011 (2026), https://pdg.lbl.gov/2026/reviews/rpp2026-rev-kinematics.pdf;
  Secs. 49.4-49.5, Eqs. (49.11)-(49.13), (49.17)-(49.23), (49.27)-(49.28). Same equation numbers in the 2024 edition.
- PDG, "50. Resonances", revised August 2025 by D.M. Asner, C. Hanhart and M. Mikhasenko (2026 edition),
  https://pdg.lbl.gov/2026/reviews/rpp2026-rev-resonances.pdf; Secs. 50.2, 50.3.1, Eqs. (50.20), (50.31)-(50.35), pp. 13-14.
- J.C. Romao and J.P. Silva, "A resource for signs and Feynman diagrams of the Standard Model", Int. J. Mod. Phys. A
  27 (2012) 1230025, arXiv:1209.6213v2; abstract, Secs. 1-3, Table 2.
- A. Denner, S. Dittmaier, M. Roth, L.H. Wieders, "Electroweak corrections to charged-current e+e- -> 4 fermion
  processes: technical details and further results", Nucl. Phys. B724 (2005) 247, arXiv:hep-ph/0505042v3; Secs. 4-5.
- D. Berdine, N. Kauer, D. Rainwater, "Breakdown of the narrow width approximation for new physics", Phys. Rev.
  Lett. 99 (2007) 111601, arXiv:hep-ph/0703058v2; pp. 1-3, Eqs. (1)-(3).
