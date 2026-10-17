# Astroparticle essentials: an entry page

Routing first: the standard relations below, each with the tool or reference that carries it. Tool:
`<plugin root>/skills/hep-theory/scripts/secondary_gamma.py` (`pi0`, `flavour`, `threshold`). Every astrophysical
input (spectra, fields, sizes, photon energies, mixing parameters) comes from the user.

| Topic | Read or run |
|---|---|
| Transport, B/C, force-field modulation, electron losses | [cosmic-ray propagation](cosmic-ray-propagation.md); `lepton_energy_losses.py` |
| Gamma rays from pi0 decay | `secondary_gamma.py pi0` |
| Neutrino flavour ratios at Earth | `secondary_gamma.py flavour`; [neutrino oscillations](neutrino-oscillations.md) |
| gamma gamma and photopion thresholds | `secondary_gamma.py threshold`; `kinematics.py` |
| Light antinuclei | [coalescence](light-nuclei-coalescence.md) |
| Dark-matter source terms | [dark-matter phenomenology](dark-matter-phenomenology.md) |
| Shipped theory-domain profiles | `<plugin root>/profiles/registry.json` |

## Acceleration

- Diffusive shock acceleration (test particles, Blasi 2013, Eqs. 40-41): the phase-space spectrum is a power law in
  momentum, f0(p) ~ p^-alpha with alpha = 3r / (r - 1), r the shock compression ratio. A strong shock (r = 4) gives
  alpha = 4, i.e. N(E) ~ E^-2 for relativistic particles. The slope does not depend on the diffusion coefficient; the
  maximum energy does not come out of the test-particle theory.
- Hillas criterion (PDG Cosmic Rays review, Sec. 30.1): the gyroradius must be smaller than the source, so
  E_max ~ Z e c B R (no shock-velocity factor here). Numerically Z x 0.93 EeV for B = 1 microgauss and R = 1 kpc
  (from c B R; consistent with the review's statement that EeV protons are not confined by microgauss fields over
  kiloparsecs).

## Radiative processes

Synchrotron and inverse Compton losses (Thomson and Klein-Nishina) are in the propagation reference's "Electron and
positron energy losses". Hadronic gamma rays come mostly from pi0 -> gamma gamma: a pion of energy E_pi gives a flat
photon spectrum between (E_pi -+ p_pi)/2, so for any pion spectrum dN/dE_gamma = 2 integral (dN/dE_pi)/p_pi dE_pi from
E_pi,min = E_gamma + m_pi^2/(4 E_gamma) (exact kinematics; `secondary_gamma.py pi0`). The resulting spectrum is
symmetric in log E_gamma about m_pi/2 and carries two photons per pion. The pion spectrum itself (from pp or p-gamma
interactions) is an input: state its source.

## Neutrino flavour ratios

Pion decay chains give nu_e : nu_mu : nu_tau = 1 : 2 : 0 at the source; muon-damped sources 0 : 1 : 0 and neutron
decay 1 : 0 : 0 (PDG Cosmic Rays review, Sec. 30.4.1). Over cosmic distances the oscillation phases average out:
P(alpha -> beta) = sum_i |U_alpha i|^2 |U_beta i|^2. The review quotes 0.30 : 0.36 : 0.34 at Earth for a 1 : 2 : 0
source, with mixing parameters from its reference [301], not restated there; `secondary_gamma.py flavour` gives the
ratio for the parameters you supply (tribimaximal mixing gives exactly 1 : 1 : 1).

## Thresholds

For a particle of mass m meeting a photon of energy eps head on, s = m^2 + 2 eps (E + p); the threshold s = M^2 (sum of
final masses) gives E = (K^2 + m^2)/(2K) with K = (M^2 - m^2)/(2 eps). Pair production on a photon: E = m_e^2 / eps;
photopion production p gamma -> p pi0 on CMB photons sets the scale of the GZK suppression (PDG Sec. 30.1, which also
notes photodisintegration of nuclei). Other collision angles need more energy; a thermal photon field spreads the
threshold. `kinematics.py threshold` covers fixed targets; `secondary_gamma.py threshold` covers a photon target.

## Radioactive clocks

Unstable secondaries constrain the residence time and gas density (PDG Sec. 30.1). Two conventions to state: the lab
lifetime is gamma tau (time dilation at the stated energy per nucleon), and a nucleus that decays only by electron
capture needs a bound electron, so its effective lifetime in flight depends on electron attachment and stripping,
which a propagation model must include. No lifetime or attachment value is given here: take half-lives from
`physical_data.py` (NUBASE2020) and attachment rates from a source you read.

## Sources read (2026-10-17)

- PDG Review of Particle Physics 2026, "Cosmic Rays" (J. Alvarez-Muniz, Z. Cao, U.F. Katz, P. Mertsch, C. Spiering,
  rev. March 2026): Secs. 30.1 and 30.4.1.
- P. Blasi, "The origin of galactic cosmic rays", arXiv:1311.7346; the test-particle shock section
  (Eqs. 36-41).
- Neutrino mixing: the PDG 2026 neutrino review as read for `neutrino-oscillations.md` (Eq. 14.34).
