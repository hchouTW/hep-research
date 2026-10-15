# Secondary antiproton source term: model, assumptions, validity

All shipped cross sections, gas densities and primary fluxes are ILLUSTRATIVE. Claims with an ID are in
`evidence/claims.json`; conventions in `conventions.json`.

## Definition

q(T) = sum_ij q_ij(T), q_ij(T) = 4 pi n_j int_{T_th}^oo dT_i phi_i(T_i) dsigma_ij/dT(T_i, T) [crpb:C01]:

- i = projectile (p, He), with flux phi_i per kinetic energy per nucleon T_i (cm^-2 s^-1 sr^-1 (GeV/n)^-1);
- j = target (H, He), n_He / n_H = 0.1 [crpb:C02]; heavier species neglected [crpb:C03];
- channels named projectile first: pp, pHe, Hep, HeHe;
- T = antiproton kinetic energy (GeV); q in cm^-3 s^-1 GeV^-1.

## Cross sections (TOY)

- Prompt pp: dsigma/dT = (sigma0 / T_i) (1 - T/T_i)^n for T_i >= T_th and T < T_i, zero otherwise. T_th = 6 m_p per
  nucleon follows from the pp threshold E_p >= 7 m_p [crpb:C02]. The toy form ignores the true dependence of the
  threshold on T and every measured feature of the spectrum; it exists so that the source integral has a closed form.
- Nuclear channels: dsigma_ij/dT = f_ij dsigma_pp/dT at the same energy per nucleon, constant f_ij. The literature
  uses fitted rescaling functions [crpb:C03]; constants are placeholders.
- Antineutrons and hyperons: total = prompt x (2 + Delta_IS + 2 Delta_Lambda), Delta_Lambda = c_Lambda (Lambda-bar /
  pbar) with c_Lambda = 0.81 [crpb:C04]. The code books (1 + Delta_Lambda) for antiprotons and (1 + Delta_IS +
  Delta_Lambda) for antineutrons (this split is the profile's bookkeeping); `antineutrons` and `hyperons` in the config
  switch each part (`included` / `excluded`), and the artifacts state the choice. Delta_IS and Lambda-bar/pbar are
  ILLUSTRATIVE constants (energy dependent in the literature).

## Model alternatives

A choice among cross-section parametrizations is a `model-alternative` uncertainty object, never an independent
Gaussian per bin [crpb:C05]. The prediction carries two: toy set B against toy set A (all parameters differ), and the
antineutron treatment without isospin enhancement (Delta_IS = 0, the traditional factor 2). Their spread says nothing
about the size of real parametrization differences.

## What it can and cannot do

- Can: evaluate q per channel and in total for any primary flux given as (broken) power laws, with any cross-section
  set in the toy form; check the numerical integration against the closed form; produce artifacts that validate.
- Cannot: give a physical antiproton source term (toy cross sections), propagate the source term, or constrain
  propagation parameters.
- External benchmark (B2): `../scripts/published_benchmark.py` evaluates the pp channel with the published closed
  forms of di Mauro et al. 2014 (`xs-dimauro2014-pp.json`, claims crpb:C07-C09) and compares with that paper's
  Table VI; this path is not used by the prediction artifact. `model.family` is
  `cosmic-ray-secondary-source-term`, so no degenerate directions are declared or required.

## Validity

0 < T, with the benchmark grid 1-500 GeV on both sides of T_th = 5.63 GeV. Source integral to T_i = e^80 T_low
(the power-law tail beyond is below double precision for gamma > 1).
