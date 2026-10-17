# Particle-physics essentials

An entry page for the conventions a particle-physics calculation states before its numbers. Mostly routing: each
topic links to the file or tool that owns it. Global fits of mixing parameters (CKM, PMNS) are outside v1.

## Where to go

| Need | Read or run |
|---|---|
| Masses, widths, mean lives, constants with their edition (PDG 2026 subset, CODATA 2022) | `<plugin root>/skills/hep-theory/scripts/physical_data.py` |
| Width, lifetime and c tau (tau = hbar / Gamma, c tau = c tau) | `<plugin root>/skills/hep-theory/scripts/kinematics.py lifetime` |
| Two-body momenta, boosts, Mandelstam variables, thresholds, Dalitz limits, rapidity | `<plugin root>/skills/hep-theory/scripts/kinematics.py` |
| Breit-Wigner forms, when the narrow-width approximation holds, phase space | [amplitudes and widths](amplitudes-and-widths.md) |
| Whether a process or diagram is allowed | [selection rules](selection-rules.md) |
| Running masses, schemes, regularization | [schemes](regularization-and-schemes.md) |
| NLO/NNLO predictions, scale variations | [higher orders](higher-order-predictions.md) |
| PDFs and their uncertainties | [PDFs](pdfs-and-lhapdf.md) |
| SMEFT conventions | [SMEFT](smeft-and-eft.md) |
| Neutrino oscillations, PMNS | [oscillations](neutrino-oscillations.md) |
| alpha_s at another scale | `<plugin root>/skills/hep-theory/scripts/running_coupling.py` (below) |

## Running strong coupling

State the scheme (MS-bar), the order of the running (1-4 loops), the input (alpha_s(m_Z) with its source and edition),
the quark masses used for the thresholds, their scheme (MS-bar m_h(m_h) or pole) and the matching scale. The beta
function is mu^2 d alpha_s / d mu^2 = -(b0 alpha_s^2 + b1 alpha_s^3 + ...) with b0 = (33 - 2 nf)/(12 pi),
b1 = (153 - 19 nf)/(24 pi^2) and b2 = (2857 - 5033 nf/9 + 325 nf^2/27)/(128 pi^3) (PDG Review, QCD, Eq. 9.3); b2 and
higher are scheme dependent. The four-loop coefficient is that of van Ritbergen, Vermaseren and Larin (1997), cited by
the review. At a heavy-quark threshold the coupling is discontinuous: Eq. 9.4 relates nf and nf + 1 flavours, with
c10 = 0 so the one-loop matching vanishes at mu = m_h. `running_coupling.py` integrates the equation numerically
(no Lambda parameter), matches at the thresholds and stops where alpha_s > 0.5, below which perturbative QCD is not
used. A value of Lambda only means something together with the approximation that defines it (Eq. 9.5 is one of
several); quote alpha_s at a scale instead.

## Mixing-matrix conventions (conventions only)

- **CKM.** The standard parametrization (PDG Review, "CKM Quark-Mixing Matrix", Eq. 12.3) is V = R23 U13(delta) R12
  with V_ud = c12 c13, V_us = s12 c13, V_ub = s13 e^{-i delta}, angles in the first quadrant and delta the CP-violating
  phase. The Wolfenstein parameters lambda, A, rho-bar, eta-bar are defined exactly by Eq. 12.4 (s12 = lambda,
  s23 = A lambda^2, s13 e^{i delta} = V_ub*), which keeps V unitary to all orders in lambda; rho-bar + i eta-bar is
  phase-convention independent. Say which parametrization and which set of fitted values (with its edition) a
  prediction uses; fitting them is a global fit, outside v1.
- **PMNS.** The same structure for leptons, plus two Majorana phases that do not enter oscillations: see
  [neutrino oscillations](neutrino-oscillations.md).

## Particle identifiers

The PDG Monte Carlo particle numbering scheme (Review, "Monte Carlo Particle Numbering Scheme") gives particles
positive and antiparticles negative numbers; quarks are numbered from 1 and leptons from 11; mesons and baryons use a
7-digit form whose last digit is 2J + 1; nuclei use the 10-digit form +-10LZZZAAAI (for example 1000922350 for
235U). Generators and analysis files exchange particles by these codes; the bundled PDG subset in `<plugin root>/core/constants` records
the code (`mcid`) of each particle.

## Sources

Particle Data Group, Review of Particle Physics (2026 edition): "Quantum Chromodynamics" (Section 9.1.1, read in full),
"CKM Quark-Mixing Matrix" (the introduction with Eqs. 12.2-12.4, read in full), "Monte Carlo Particle Numbering Scheme"
(rules 1-3 and 16 read); T. van Ritbergen, J.A.M. Vermaseren and S.A. Larin, Phys. Lett. B 400 (1997) 379,
arXiv:hep-ph/9701390 (Eqs. 4, 11 and 12 read). All read on 2026-10-17 from pdg.lbl.gov and arxiv.org.
