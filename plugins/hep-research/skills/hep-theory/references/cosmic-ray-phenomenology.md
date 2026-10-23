# Cosmic-ray propagation and astroparticle phenomenology: codes, cross sections, modulation, global fits, new physics

Purpose: the second propagation page and the entry to two more. [Cosmic-ray propagation](cosmic-ray-propagation.md)
holds the model families, kinematics, the force-field derivation, the antiproton source term and the plugin's tool
status. This page adds how the public codes parametrize transport, which production cross sections dominate the error
and how they are carried, and the nuisance structure of a global fit. Modulation beyond the force field and its
alignment with time-resolved data are in [solar modulation models](solar-modulation-models.md); dark-matter and pulsar
interpretations, and how to state them without overclaiming, in [cosmic-ray new physics](cosmic-ray-new-physics.md).
Conventions of nuclear cross sections are in [nuclear cross sections](nuclear-cross-sections.md); halo, J factor and
annihilation conventions in [dark matter](dark-matter-phenomenology.md).

Status: guidance (Th13), sources not yet verified (see "Sources read"); the only executable piece is
`bartels_rotation.py`. Running a propagation code in
a global fit stays outside v1; choosing which model explains an excess stays limited-support. Unless a line says
otherwise a source was read at abstract level; see "Sources read". Experiment facts (bins, periods, published numbers)
come from the bound experiment profile or a dataset record, never from this page.

## Contents

- Propagation codes and transport parameters
- Secondary production cross sections
- Solar modulation beyond the force field
- Global propagation fits: what hep-theory supplies
- What to report
- Sources read

## Propagation codes and transport parameters

**The codes.** Each is a model choice with its own numerics and defaults; name the code, version and configuration.

- *GALPROP.* Numerical solution on a grid in (R, z, p), cylindrically symmetric in the original version, with free
  escape at the halo boundary and a Crank-Nicholson scheme with operator splitting (Strong and Moskalenko 1998, Sec. 2
  and App. B). Release v57 solves about 90 coupled transport equations in 3D or 4D and ships updated cross-section and
  gas data (Porter et al. 2022, abstract and Sec. 2).
- *DRAGON2.* Numerical solver whose diffusion may depend on position, momentum and direction (a diffusion tensor along
  and across the regular field), with advection, reacceleration and losses, checked against analytic solutions (Evoli
  et al. 2017, abstract, Eqs. 2.1-2.2). One build runs in the plugin through the optional adapter; see the tool status
  in the first propagation page.
- *USINE.* Semi-analytic leaky-box and two-zone 1D and 2D diffusion models for nuclei, antiprotons and antideuterons,
  fast enough for statistical scans, with nuisance parameters for modulation, cross sections and data systematics
  built in (Maurin 2020, abstract).

**Diffusion-coefficient conventions differ; convert before comparing.**

| Source | Form | Normalization |
|---|---|---|
| GALPROP v57 (Tables 1-2) | D proportional to beta rho^delta | D0 at rho0 = 4 GV, in 10^28 cm^2/s |
| USINE analyses (Weinrich et al. 2020a, Eq. 1) | K = beta^eta K0 (R/R0)^delta, with smooth low (R_l) and high (R_h) breaks | K0 at R0 = 1 GV, in kpc^2/Myr; K10 = K0 10^delta |
| DRAGON2 examples (Evoli et al. 2017, Sec. 5) | D proportional to (p/p0)^delta | D0 at 1 GV (or p0 = 1 GeV) in cm^2/s |

1 kpc^2/Myr = 3.017e29 cm^2/s (Julian Myr, IAU parsec; unit arithmetic). A D0 quoted at 4 GV and one quoted at 1 GV
differ by 4^delta before any physics; the beta^eta factor, the break shape and the halo height L change the meaning
of D0 further. A comparison of transport parameters across papers states all of them or compares predictions instead.

**Parameters and what pins them.** Normalization D0 (or K0) and slope delta; eta; low- and high-rigidity breaks;
Alfven speed V_A (reacceleration); convective speed V_c and its gradient; halo height L; injection indices and their
breaks; the modulation parameters of the data periods.

- **Reacceleration ties momentum diffusion to spatial diffusion:** D_pp D_xx = 4 p^2 V_A^2 / (3 delta (4 - delta^2)
  (4 - delta) w), w the ratio of wave to magnetic energy density, set to 1 so that only V_A^2 / w matters (Strong and
  Moskalenko 1998, Sec. 2, Eq. 1, after Seo and Ptuskin 1994). GALPROP v57 cites the same relation without writing it
  (Porter et al. 2022, Sec. 2); the DRAGON2 prefactor was not read. A V_A from one code is comparable with another's
  only when both use this relation and the same w.

- Above about 5 GV convection and reacceleration are degenerate and poorly constrained one by one (Korsmeier and
  Cuoco 2016, abstract, from p, He and antiprotons).
- With cross-section uncertainties as nuisances, both "low-rigidity diffusion break, no reacceleration" and
  "reacceleration, no break" fit Li-O data (Korsmeier and Cuoco 2021, abstract); a Li/Be/B fit keeps two regions,
  reacceleration plus convection or pure diffusion (Weinrich et al. 2020a, abstract). So the low-rigidity transport
  model is not decided by secondary ratios alone; report the families that survive.
- Benchmark families make the choice explicit: BIG (all terms) and its two limits SLIM (diffusion only) and QUAINT
  (convection plus reacceleration) (Genolini et al. 2019, abstract). Above about 10 GV the abstract gives delta in
  0.43-0.53 and K10 in 0.26-0.36 kpc^2/Myr at 1 sigma, and a high-rigidity break of typical size 0.2.
- **Halo height L** comes from radioactive clocks and Be/B; it is limited by production cross sections. Quoted values:
  4 to 12 kpc from 10Be/9Be in reacceleration models (Strong and Moskalenko 1998, Sec. 3); L = 5 (+3/-2) kpc at 68% CL
  from precision space-borne Be/B (Weinrich et al. 2020b, abstract); about 5 kpc or more with nominal cross
  sections, weakened when their uncertainties are allowed (Evoli et al. 2020, abstract); L at least about 3 kpc from
  Be (Korsmeier and Cuoco 2021, abstract). Quote L with the data, model family and cross-section treatment it came
  from; do not average them. Percent-level 10Be/9Be below 10 GV, and Al/Mg and Cl/Ar (other radioactive clocks), are
  named as the next handles (Weinrich et al. 2020b, abstract). A preprint using 7Be with data-driven cross sections
  gives 5.67 +- 0.76 kpc (Zhao et al., arXiv:2402.04659, abstract).

**Comparing codes or papers.** Same species network and cross-section set, same gas and helium fraction, same geometry
(radial boundary, source distribution), same modulation and the same rigidity range; otherwise the difference is a
model alternative, not a numerical error. The first propagation page shows a case (DRAGON2 against a closed form)
where the radial boundary and gas structure alone break the D0/L degeneracy at large L.

## Secondary production cross sections

**B/C and Li, Be.** Production goes through many channels, measured sparsely in energy; parametrizations are
semi-empirical sets renormalized to the available nuclear data (conventions and ghost nuclei in
[nuclear cross sections](nuclear-cross-sections.md)).

- **The sets and how they differ.** Each code ships its own production network; name it.

  | Set | How it is built | Notes |
  |---|---|---|
  | Webber family (WKS93, WKS98, S01, W03; WNEW code) | semi-empirical formulas fitted to data | W03 has no Li production (Maurin et al. 2022, Sec. 2.3) |
  | Silberberg-Tsao (YIELDX, TS00) | semi-empirical systematics | DRAGON2 takes Li from it (Evoli et al. 2018, Sec. 5) |
  | GALPROP opt12 / opt22 | fits to data on top of WNEW 1998 / YIELDX 2000 | opt12 has no Fe to LiBeB, opt22 includes it (Maurin et al. 2022, Sec. 2.3); opt12 (kopt = 12) is GALPROP's default (Korsmeier and Cuoco 2021, Sec. IV) |
  | DRAGON2 | Webber tables; missing channels from WNEWTR renormalized to data at 0.1-100 GeV/n | three generations of intermediate-lived parents, GALPROP five (Evoli et al. 2018, Sec. 5) |
  | OPT12, OPT22, OPT12up22 | GALPROP sets renormalized to data (smoothed data/model spline, threshold fit, constant above 1.5 GeV/n) | Maurin et al. 2022, Sec. 3 |

  Size of the differences at 10 GV with progenitors up to Fe: opt12 against the others moves the ratios by 3% or less,
  S01 and W03 raise Be/B by about 5%, opt22 raises Li/C by about 15%, Be/C 10%, B/C 5%; among the renormalized sets
  the spread is about 6% for Be and 10-20% for Li, and B/C moves by 4% or less (Maurin et al. 2022, Secs. 2.3, 3.3).
  Most of the Li spread comes from Fe and from reactions never measured. Inelastic sets (Tripathi99, CROSEC) agree
  above about 2 GeV/n and differ by up to about 20% below (Evoli et al. 2018, Sec. 3). Helium-target cross sections
  are scaled from hydrogen ones (Ferrando et al. 1988 scaling in both papers).
- **What matters most.** Cross-section uncertainties are often 20-50% or more against 1-3% data precision; 12C + H and
  16O + H give about half of LiBeB production and about ten more reactions bring it to 80%; ghost nuclei give up to
  about 25% for some isotopes (Genolini et al. 2018, abstract and Secs. IV, VII). Starting the network at Mg captures
  about 90% of the LiBeB source at 10 GeV/n, and intermediate-lived nuclei give about 35% of the B source (Evoli et
  al. 2018, Sec. 5).
- Calculation uncertainties from cross sections exceed the quoted errors of current precision ratio data (Evoli,
  Aloisio and Blasi 2019, abstract, which also gives a new parametrization with branching-ratio uncertainties).
- Renormalizing several parametrizations to nuclear data gave three equally plausible sets; against the initial sets,
  Li production rose by about 20-50%, Be by about 5-15%, B was mostly unchanged; Fe fragmentation gives up to 10% of Li
  and Be, and Ne, Mg, Si and Fe reactions about 20% of Li and B with almost no nuclear data (Maurin et al. 2022,
  abstract). A "primary Li" or a transport anomaly inferred from Li must first survive this.
- **Nuisance scheme ("normalization, slope, shape").** Inelastic reactions get a normalization and an energy-scale
  nuisance; production reactions a normalization and a low-energy slope below a threshold; priors centred at 1 with
  widths of about 5% (inelastic) and 10% (production); a proxy reaction standing for a fraction x of a species'
  production enters as N_eff = 1 + x (N_proxy - 1) (Weinrich et al. 2020a, App. B and Sec. 5.2, Eq. 11;
  scheme from Derome et al. 2019). Post-fit shifts were about 5-15%.
- **Other schemes in use.** One normalization A and one slope delta per product element below 5 GeV/n,
  sigma = sigma_default A (T/A)^delta, ten parameters for Li-N with flat priors (A in [0.1, 10] for Li, Be, B; delta
  in [-0.3, 0.3]); a fitted A sat at its prior edge (Korsmeier and Cuoco 2021, Sec. IV Eq. 10, Table II, Sec. VII).
  Or the sets themselves as model alternatives (Maurin et al. 2022). Report the scheme, the priors and any parameter
  at a prior edge; never fix the cross sections and quote the transport errors as complete.
- Data-driven production cross sections are appearing at preprint status (Zhao et al., arXiv:2402.04659 and
  arXiv:2502.05514, abstracts); label them so.
- Wrong cross sections, or a wrong correlation length in the data systematics, bias the fit and can make an acceptable
  model look excluded (Derome et al. 2019, abstract).

**Antiprotons.** The source-term conventions (channels, antineutrons, hyperons, rescaling to nuclei) are in the first
propagation page. Uncertainty objects in use:

- an analytic parametrization fitted to new fixed-target pp and pHe data, about +-20% on the source term, dominated
  by pp (Korsmeier, Donato and Di Mauro 2018, abstract);
- a Monte Carlo alternative, AAfrag: QGSJET-II-04m tabulated for pp, pA, Ap and AA with hadronization retuned to
  recent accelerator data (Kachelriess, Moskalenko and Ostapchenko 2019, abstract);
- newer work at preliminary or preprint status only: a 2025 proceedings quotes about 10-15% current uncertainty
  (D'Angelo, Masi and Oliva, PoS ICRC2025 234, abstract page), and an NLO collinear-QCD preprint finds an antineutron
  excess of a few percent (Boglione et al., arXiv:2605.04150, abstract). Label them so; no newer peer-reviewed source
  determination was found on 2026-10-20.
- Parametrization choice is a `model-alternative`; a fitted set's own error enters with its covariance. When the data
  are corrected with nuclear cross sections in the detector, that correction can dominate the antiproton systematics
  near 10-20 GV (Heisig, Korsmeier and Winkler 2020, abstract). It is correlated with the interpretation only when
  both use cross sections from the same family or data; then declare one shared nuisance
  ([nuclear cross sections](nuclear-cross-sections.md), "Uncertainty and correlations"), otherwise keep them apart.

**Secondary positrons and electrons.** Analytic pi and K production cross sections fitted to collider data, with
hyperon channels and heavier nuclei from p + C data, give the total e+- production cross section with about 5-7%
uncertainty over the energy range of current space-borne data (Orusa et al. 2022, abstract). Against the older Kamae
et al. 2006 parametrization the positron source term differs by about 20% above 5 GeV (Kamae smaller) and is larger
in Kamae below 1 GeV; AAfrag agrees within about 10% for positrons at 1-100 GeV but is 30-40% higher for electrons
and is valid only for proton energies of at least 3.1 GeV (Orusa et al. 2022, Secs. VI-VII). Lepton losses: first
propagation page.

## Solar modulation beyond the force field

Moved to its own page: [solar modulation models](solar-modulation-models.md) (model hierarchy, LIS dependence of phi,
heliospheric inputs and lag, charge sign, and alignment with monthly or Bartels-rotation data through
`bartels_rotation.py`).

## Global propagation fits: what hep-theory supplies

hep-theory writes the model and its nuisance structure; hep-statistics owns the likelihood, priors as statistical
objects, samplers, profiling and goodness of fit. A theory spec for a global fit lists these blocks, each with its
source and its correlation across species, periods and charge signs:

| Block | Content | Typical prior source |
|---|---|---|
| Transport | D0 (with reference rigidity), delta, eta, breaks, V_A, V_c, L | free; L also from clocks |
| Sources | injection indices and breaks per species group, abundances | free |
| Production cross sections | normalization, slope, scale per reaction or proxy (scheme above), or a set of parametrizations | nuclear data |
| Antiparticle source term | pp normalization and shape, nuclear rescaling, antineutron factor | fitted parametrization covariance |
| Modulation | one parameter set per period and sign or polarity era; LIS shared | heliospheric inputs, lag |
| Gas | normalization degenerate with transport normalization | tracer uncertainties |
| New physics (if any) | mass, channel, cross section; halo profile | none; see below |

- Data covariance (correlated systematics across rigidity) is a measurement input; without it a fit to a percent-level
  ratio is not credible (Derome et al. 2019; Cuoco et al. 2019 found the dark-matter significance moved from about
  3 sigma to above 5 sigma between correlation models, abstract).
- **How the blocks travel.** The theory spec lists every block's parameters in `parameters` with their reference
  conventions, and the transport degeneracies in `degenerate_directions` (first propagation page, "What to report").
  In each `prediction`, a cross-section nuisance is an uncertainty component of kind `parametric` with `correlation`
  `covariance` and a `covariance_ref`, or a separate prediction per set with kind `model-alternative`; modulation and
  LIS choices are `model-alternative` unless fitted. Never fold a set choice into a Gaussian without a stated
  prescription. The same nuisance shared by several species or periods keeps one name in all of them.
- Scans use emulators in practice (for example a neural-network emulator of the antiproton flux with propagation
  nuisances marginalized; Balan et al. 2023, abstract). An emulator is a surrogate with a validity domain: hep-ml, and
  its use inside a likelihood is hep-statistics.
- In v1, a fit to tabulated predictions on a grid is supported (`covariance_fit.py`, model `tabulated-grid`, in
  hep-statistics; DRAGON2 grid nodes through the optional propagation adapter; synthetic data only); a fit that runs a
  propagation code across many species gets the outside-v1 notice.

## What to report

Code and version; geometry, terms kept and the diffusion form with its reference rigidity; cross-section set and the
nuisance scheme; LIS and modulation model per period and sign, inputs, averaging window and lag; data and covariance;
degenerate directions. For new physics, the list in [cosmic-ray new physics](cosmic-ray-new-physics.md).

## Sources read (2026-10-20; through a summarizing fetch, not verified)

Every page below, abstract or named sections, was read through a fetch tool that returns a model-written summary of the
page. Under hep-citations' rule (`skills/hep-citations/references/citation-verification.md`, step 2) such a summary
counts as a search snippet, not as having checked the source: each attribution, section, equation and number on this
page and on [solar modulation models](solar-modulation-models.md) and
[cosmic-ray new physics](cosmic-ray-new-physics.md) is unverified until re-read in the primary source, and is not to be
quoted into a paper before that. The location named after each entry is where the summary placed the content.

- A.W. Strong, I.V. Moskalenko, arXiv:astro-ph/9807150v2 (DOI 10.1086/306470); abstract, Secs. 2-3 (Eq. 1),
  App. A-B.
- T.A. Porter, G. Johannesson, I.V. Moskalenko, arXiv:2112.12745v2 (ApJS, DOI 10.3847/1538-4365/ac80f6); abstract,
  Secs. 2, 4, Tables 1-2.
- C. Evoli et al., arXiv:1607.07886v2 (JCAP 02 (2017) 015); abstract, Secs. 2, 5.
- D. Maurin, arXiv:1807.02968v2 (Comput. Phys. Commun., DOI 10.1016/j.cpc.2019.106942).
- Y. Genolini et al., arXiv:1904.08917v2 (PRD 99 (2019) 123028).
- N. Weinrich et al. 2020a, arXiv:2002.11406v1 (A&A, DOI 10.1051/0004-6361/202037875); abstract, Secs. 2, 5.2, App. B.
- N. Weinrich et al. 2020b, arXiv:2004.00441v2 (A&A, DOI 10.1051/0004-6361/202038064).
- C. Evoli, G. Morlino, P. Blasi, R. Aloisio, arXiv:1910.04113v2 (PRD 101 (2020) 023013).
- C. Evoli, R. Aloisio, P. Blasi, arXiv:1904.10220v2 (PRD 99 (2019) 103023).
- M. Korsmeier, A. Cuoco, arXiv:1607.06093v3 (PRD 94 (2016) 123019); arXiv:2103.09824v2 (PRD 103 (2021) 103016),
  Secs. II, IV (Eq. 10), V (Table II), VII.
- D. Maurin et al., arXiv:2203.00522v2 (A&A, DOI 10.1051/0004-6361/202243446); abstract, Secs. 2.3, 3, 5.
- C. Evoli, D. Gaggero, A. Vittino, M. Di Mauro, D. Grasso, M.N. Mazziotta, arXiv:1711.09616v2 (JCAP, DOI
  10.1088/1475-7516/2018/07/006); Secs. 3, 5.
- Y. Genolini, D. Maurin, I.V. Moskalenko, M. Unger, arXiv:1803.04686v1 (PRC 98 (2018) 034611); abstract, Secs. II,
  IV-VII, App. A.
- Q. Zhao et al., arXiv:2402.04659v1 and arXiv:2502.05514v1 (preprints).
- L. Derome et al., arXiv:1904.08210v3 (A&A, DOI 10.1051/0004-6361/201935717).
- M. Korsmeier, F. Donato, M. Di Mauro, arXiv:1802.03030 (PRD 97 (2018) 103019).
- M. Kachelriess, I.V. Moskalenko, S. Ostapchenko, arXiv:1904.05129v2 (Comput. Phys. Commun., DOI
  10.1016/j.cpc.2019.08.001).
- F. D'Angelo, N. Masi, A. Oliva, PoS(ICRC2025)234 (proceedings page); M. Boglione et al., arXiv:2605.04150v1
  (preprint).
- L. Orusa, M. Di Mauro, F. Donato, M. Korsmeier, arXiv:2203.13143v2 (PRD 105 (2022) 123021); abstract, Secs. I,
  VI-VII.
- I. Cholis, D. Hooper, T. Linden, arXiv:1511.01507 (PRD 93 (2016) 043016); Secs. I, II, IV, Eqs. 1, 2, 12.
- C. Corti et al., arXiv:1511.08790 (ApJ 829 (2016) 8); abstract, Sec. 3, Eq. 7.
- J. Gieseler, B. Heber, K. Herbst, arXiv:1710.10834 (JGR, DOI 10.1002/2017JA024763).
- M. Kuhlen, P. Mertsch, arXiv:1909.01154v2 (PRL 123 (2019) 251104); abstract and model section.
- M.S. Potgieter, arXiv:1306.4421 (Living Rev. Solar Phys., DOI 10.12942/lrsp-2013-3); abstract, Secs. 2.2.1,
  4.1-4.4.
- M.J. Boschini, S. Della Torre et al., HelMod: arXiv:1612.08445, arXiv:1903.07501, arXiv:1704.06337.
- N. Tomassetti et al., arXiv:1707.06916 (ApJL 849 (2017) L32); abstract, Secs. 1-3.
- I.G. Usoskin et al., JGR 110 (2005) A12108, DOI 10.1029/2005JA011250; Sec. 2, App. A; and arXiv:1705.07197 (DOI
  10.1002/2016JA023819), abstract, Secs. 2, 6.3.
- Bartels rotations: WDC Kp/Ap format description, https://ftp.space.dtu.dk/WDC/indices/kp-ap/wdc/wdc_fmt.txt;
  Caltech ACE Science Center table, https://izw1.caltech.edu/ACE/ASC/DATA/bartels/Bartels2008-2027.pdf.
- M. Boudaud et al., arXiv:1906.07119 (PRR 2 (2020) 023022); J. Heisig, M. Korsmeier, M.W. Winkler, arXiv:2005.04237v2
  (PRR 2 (2020) 043017); A. Cuoco, J. Heisig, L. Klamt, M. Korsmeier, M. Kramer, arXiv:1903.01472v2 (PRD 99 (2019)
  103014).
- A. Cuoco, M. Kramer, M. Korsmeier, arXiv:1610.03071 (PRL 118 (2017) 191102); M.-Y. Cui et al., arXiv:1610.03840v2
  (PRL 118 (2017) 191101); F. Calore et al., arXiv:2202.03076 (SciPost Phys. 12 (2022) 163), Secs. 3, 5.1-5.4.
- M. Cirelli et al., arXiv:1012.4515v4 (JCAP 03 (2011) 051); S. Balan et al., arXiv:2303.07362v1.
- D. Hooper, P. Blasi, P.D. Serpico, arXiv:0810.1527 (JCAP 01 (2009) 025); HAWC Collaboration, arXiv:1711.06223
  (Science, DOI 10.1126/science.aan4880); D. Hooper, I. Cholis, T. Linden, K. Fang, arXiv:1702.08436 (PRD 96 (2017)
  103013); S. Profumo et al., arXiv:1803.09731 (PRD 97 (2018) 123008).
- M. Di Mauro, S. Manconi, F. Donato, arXiv:1903.05647 (PRD 100 (2019) 123015); S. Manconi, M. Di Mauro, F. Donato,
  arXiv:2001.09985 (PRD 102 (2020) 023015); L. Orusa et al., arXiv:2107.06300 (JCAP, DOI
  10.1088/1475-7516/2021/12/014).
- "Searching for Dark Matter Annihilation from Milky Way Dwarf Spheroidal Galaxies with Six Years of [satellite]
  Data" (collaboration paper), arXiv:1503.02641 (PRL 115 (2015) 231301); M. Di Mauro, F. Donato, N. Fornengo,
  A. Vittino, arXiv:1507.07001 (JCAP 05 (2016) 031); Y.-Z. Ding et al., arXiv:2104.14881 (JCAP, DOI
  10.1088/1475-7516/2021/09/005).

Not verified and therefore not used: the DRAGON2 general beta^eta form of D and its D_pp prefactor (Appendix C not
read), the Planck 2018 annihilation limit, a numerical diffusion coefficient from the HAWC abstract, and what the
Wilcox "L" and "R" tilt models assume (only their names and use were read).
