# Light (anti)nuclei by coalescence: B_A, p0 and the Wigner-function model

How a deuteron, helium-3 or their antinuclei yield is built from nucleon yields, and which convention a number
assumes. Tool: `<plugin root>/skills/hep-theory/scripts/coalescence.py` (`ba`, `yield`, `wigner`). No coalescence
momentum, deuteron size or source size is built in.

## The standard coalescence model

The invariant yield of a nucleus of mass number A is a power of the nucleon yield at the same momentum per nucleon
(Duperray et al. 2005, Eqs. 1-4):

    E_A d^3N_A / dp_A^3 = B_A (E_p d^3N_p / dp_p^3)^A,   p_A = A p_p,

with equal proton and neutron yields (otherwise the product of the proton and neutron yields). The coefficient
follows from requiring the nucleons to lie within a sphere of radius p0 in momentum space:

    B_A = A (4 pi p0^3 / (3 m_N))^(A-1)              (Kachelriess et al. 2019, Eq. 2)
    B_A = (4 pi p0^3 / 3)^(A-1) m_A / m_p^A          (Duperray et al. 2005, Eq. 5)

The two agree when m_A = A m_N; they differ by m_A / (A m_N), a few parts in 10^4 for the deuteron, which the tool
reports. B_A has units GeV^(2(A-1)) (c = 1). Spin and isospin factors are absorbed into p0 in this form.

The value of p0 is fitted and depends on the reaction and energy: Duperray et al. fit p0 = 79 MeV/c to p-A data and
note that other analyses used 58 MeV; event-generator approaches tune p0 per generator. A p0 taken from one reaction
does not transfer to another without saying so. For p-A systems Duperray et al. found the coefficients energy
independent; that is a statement about their data, not a general rule.

## Event-by-event and Wigner-function coalescence

The factorized form ignores momentum correlations between nucleons, which matter in small systems (e+e-, dark-matter
annihilation, pp). Event-by-event coalescence applies the p0 condition to nucleon pairs in generated events. The
Wigner-function model of Kachelriess, Ostapchenko and Tjemsland (2019, Eqs. 3-16) replaces the sharp cut by a weight
per pair: with a Gaussian deuteron wave function of size d and nucleons emitted with spatial spread sigma, a pair with
relative momentum q contributes 3 zeta exp(-q^2 d^2), with zeta = (d^2 / (d^2 + 4 sigma^2))^(3/2) <= 1. Here
3 = 8 S with the spin-isospin factor S = 3/8 for the deuteron (S = 1/12 for three-nucleon states, their Eq. 41).
Their d = 3.2 fm reproduces the deuteron rms charge radius 1.96 fm; sigma depends on the collision system and is
estimated or fitted (their Sec. 2.2). `coalescence.py wigner` returns zeta and the weights; applying them needs the
nucleon pairs of an event generator.

## Hand-offs

- Antideuteron and antihelium source terms in cosmic rays: take the antiproton (and antineutron) source term from the
  secondary-antiproton theory-domain profile (see `<plugin root>/profiles/registry.json`), state the coalescence
  convention and p0, then propagate with the [cosmic-ray propagation](cosmic-ray-propagation.md) reference.
- From dark-matter annihilation: the prompt antinucleon spectrum comes from an event generator (state it); the
  conventions for the source term are in [dark-matter phenomenology](dark-matter-phenomenology.md).
- Comparing a coalescence prediction with data is hep-statistics.

## What to report

The model (factorized B_A, event-by-event p0, or Wigner weights), p0 or (d, sigma) with where they were fitted, whether
B_A includes A and which mass convention, the nucleon spectrum and generator, and how isospin asymmetry is treated.

## Sources read (2026-10-17)

- R. Duperray, B. Baret, D. Maurin, G. Boudoul, A. Barrau, L. Derome, K. Protasov, M. Buenerd, "Flux of light
  antimatter nuclei near Earth, induced by cosmic rays in the Galaxy and in the atmosphere", arXiv:astro-ph/0503544
  (report LPSC/04-88); Sec. II (Eqs. 1-5) and the p0 fit.
- M. Kachelriess, S. Ostapchenko, J. Tjemsland, "Alternative coalescence model for deuteron, tritium, helium-3 and
  their antinuclei", arXiv:1905.01192 (an EPJ A manuscript); Secs. 1-2.1 (Eqs. 2-16) and Eq. 41.
