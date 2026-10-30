# References (Annotated, by Detector Family and Topic)

Annotated sources for the hep-detector references. Citation format used throughout:
author(s), title, venue volume (year) pages, then a persistent identifier: a DOI
(resolve at `https://doi.org/<DOI>`) or, where none exists, a stable URL.

**Verification status (2026-09-20).** Every journal article and book below was matched
against the Crossref registry by title, first-author surname, venue, volume, pages, and year,
and its DOI is given as returned by Crossref. Every URL was checked to return HTTP 200.
One first-author initial (Grupen) was corrected on 2026-10-13 after review.
Not verified: that each work supports the specific use noted in its annotation (this
was written from knowledge of the works, not by re-reading them), and DOI/URL
availability can change over time. The document makes no detector-specific performance
claim, so none of these is cited for a number; if a performance value is quoted
downstream, cite the apparatus's own technical design report or official performance
paper (name, configuration, phase space, conditions), which are deliberately not listed
here because they are experiment-specific. Prefer primary sources for technical claims;
the textbooks are for principles.

## General and cross-cutting

- **Particle Data Group reviews**: S. Navas et al. (Particle Data Group), Phys. Rev. D 110 (2024) 030001, and
  later web updates (the 2025 URLs below; check <https://pdg.lbl.gov/> for a newer edition before citing). The
  2024 *Passage of particles through matter* (revised March 2025) and *Particle detectors at accelerators* were
  read 2026-10-14 for the hep-detector audit corrections:
  *Passage of particles through matter* (<https://pdg.lbl.gov/2025/reviews/rpp2025-rev-passage-particles-matter.pdf>),
  *Particle detectors at accelerators* (<https://pdg.lbl.gov/2025/reviews/rpp2025-rev-particle-detectors-accel.pdf>),
  *Particle detectors for non-accelerator physics* (<https://pdg.lbl.gov/2025/reviews/rpp2025-rev-particle-detectors-non-accel.pdf>),
  *Statistics* (<https://pdg.lbl.gov/2025/reviews/rpp2025-rev-statistics.pdf>). Standard
  reference for Bethe-Bloch, Highland, radiation and interaction lengths, Cherenkov and
  transition radiation, detector resolution parameterizations, and statistical
  terminology ([core detector equations](core-detector-equations.md), [signal formation and readout](signal-formation-and-readout.md), [tracking and vertexing](tracking-and-vertexing.md), [particle identification](particle-identification.md), [cherenkov imaging variants and photosensors](cherenkov-imaging-variants-and-photosensors.md), [calorimetry ecal hcal](calorimetry-ecal-hcal.md), [performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md)). Particle masses and properties for PID
  calculations come from the PDG listings.
- W. R. Leo, *Techniques for Nuclear and Particle Physics Experiments*, 2nd ed.
  (Springer, 1994), DOI 10.1007/978-3-642-57920-2. Textbook: interaction with matter, signal formation, electronics.
- C. Grupen and B. Shwartz, *Particle Detectors*, 2nd ed. (Cambridge University Press,
  2008), DOI 10.1017/CBO9780511534966. Textbook covering nearly all detector families in this study.
- F. Sauli, *Gaseous Radiation Detectors: Fundamentals and Applications* (Cambridge
  University Press, 2014), DOI 10.1017/CBO9781107337701. Gas detectors, drift, diffusion, gain, micro-pattern devices.

## Signal formation, energy loss, fluctuations ([signal formation and readout](signal-formation-and-readout.md))

- H. Bichsel, "Straggling in thin silicon detectors", Rev. Mod. Phys. 60 (1988) 663-699, DOI 10.1103/RevModPhys.60.663.
  Landau/Vavilov-type fluctuations in thin layers.
- V. L. Highland, "Some practical remarks on multiple scattering", Nucl. Instrum.
  Methods 129 (1975) 497-499, DOI 10.1016/0029-554X(75)90743-0; G. R. Lynch and O. I. Dahl, "Approximations to multiple
  Coulomb scattering", Nucl. Instrum. Methods B58 (1991) 6-10, DOI 10.1016/0168-583X(91)95671-Y. Origin of the Highland
  approximation; the PDG review gives the current form.

## Tracking, vertexing, alignment ([calibration and alignment](calibration-and-alignment.md), [tracking and vertexing](tracking-and-vertexing.md), [gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md), [muon systems](muon-systems.md))

- R. Fruhwirth, "Application of Kalman filtering to track and vertex fitting", Nucl.
  Instrum. Methods A262 (1987) 444-450, DOI 10.1016/0168-9002(87)90887-4. The Kalman track/vertex fit.
- V. Blobel, "Software alignment for tracking detectors", Nucl. Instrum. Methods A566
  (2006) 5-13, DOI 10.1016/j.nima.2006.05.157. Track-based alignment, global/local parameters, weak modes.
- W. Blum, W. Riegler and L. Rolandi, *Particle Detection with Drift Chambers*, 2nd
  ed. (Springer, 2008), DOI 10.1007/978-3-540-76684-1. Drift chambers, time-to-distance relation, diffusion, resolution.
- F. Sauli, "GEM: a new concept for electron amplification in gas detectors", Nucl.
  Instrum. Methods A386 (1997) 531-534, DOI 10.1016/S0168-9002(96)01172-2. GEM.
- Y. Giomataris, P. Rebourgeard, J. P. Robert and G. Charpak, "MICROMEGAS: a
  high-granularity position-sensitive gaseous detector for high particle-flux
  environments", Nucl. Instrum. Methods A376 (1996) 29-35, DOI 10.1016/0168-9002(96)00175-1. Micromegas.
- R. Santonico and R. Cardarelli, "Development of resistive plate counters", Nucl.
  Instrum. Methods 187 (1981) 377-380, DOI 10.1016/0029-554X(81)90363-3. RPC. The multi-gap
  variant: E. Cerron Zeballos et al., "A new type of resistive plate chamber: the
  multigap RPC", Nucl. Instrum. Methods A374 (1996) 132-135,
  DOI 10.1016/0168-9002(96)00158-1.

## Front-end electronics and signal processing ([front-end electronics and signal processing](front-end-electronics-and-signal-processing.md))

Entries in this section were matched against Crossref on 2026-10-13, with the same
criteria as above.

- W. Shockley, "Currents to conductors induced by a moving point charge", J. Appl. Phys.
  9 (1938) 635-636, DOI 10.1063/1.1710367. Induced current on electrodes (with Ramo).
- S. Ramo, "Currents induced by electron motion", Proc. IRE 27 (1939) 584-585,
  DOI 10.1109/JRPROC.1939.228757. Weighting-field form of signal induction.
- V. Radeka, "Low-noise techniques in detectors", Annu. Rev. Nucl. Part. Sci. 38 (1988)
  217-277, DOI 10.1146/annurev.ns.38.120188.001245. Series, parallel and `1/f` noise,
  shaping and the noise optimum.
- H. Spieler, *Semiconductor Detector Systems* (Oxford University Press, 2005),
  DOI 10.1093/acprof:oso/9780198527848.001.0001. Textbook: signal formation, front-end
  electronics, noise, shaping, timing, and system design.
- W. E. Cleland and E. G. Stern, "Signal processing considerations for liquid ionization
  calorimeters in a high rate environment", Nucl. Instrum. Methods A338 (1994) 467-497,
  DOI 10.1016/0168-9002(94)91332-3. Optimal filtering of sampled pulses with pileup noise.
- S. O. Rice, "Mathematical analysis of random noise", Bell Syst. Tech. J. 23 (1944)
  282-332, DOI 10.1002/j.1538-7305.1944.tb00874.x. Level-crossing rate of Gaussian noise
  (noise-hit rate above a threshold).
- S. Vinogradov, "Analytical models of probability distribution and excess noise factor of
  solid state photomultiplier signals with crosstalk", Nucl. Instrum. Methods A695 (2012)
  247-251, DOI 10.1016/j.nima.2011.11.086. Borel branching model of SiPM optical crosstalk.
- C. Adams et al. (MicroBooNE), "Ionization electron signal processing in single phase
  LArTPCs. Part I. Algorithm description and quantitative evaluation with MicroBooNE
  simulation", JINST 13 (2018) P07006, DOI 10.1088/1748-0221/13/07/P07006. Deconvolution
  of induction and collection signals in a LAr TPC.
- M. Moll, "Displacement damage in silicon detectors for high energy physics", IEEE Trans.
  Nucl. Sci. 65 (2018) 1561-1582, DOI 10.1109/TNS.2018.2819506. Leakage current, depletion
  voltage and trapping after irradiation.
- V. T. Jordanov and G. F. Knoll, "Digital synthesis of pulse shapes in real time for high
  resolution radiation spectroscopy", Nucl. Instrum. Methods A345 (1994) 337-345 (title,
  volume and pages read from the article's first page, University of Michigan Deep Blue
  copy, 2026-10-25; DOI not checked). Recursive trapezoidal and triangular digital shaping;
  flat tops against ballistic deficit and trapping.
<!-- example: source citations (experiments named as the source of a general method) -->
- M. Aharrouche et al., "Response uniformity of the ATLAS liquid argon electromagnetic
  calorimeter", arXiv:0709.1094 (read 2026-10-25; journal reference not checked). Optimal
  filtering coefficients from the pulse shape, its derivative and the pedestal-run noise
  autocorrelation by Lagrange multipliers.
- N. Nikiforou for the ATLAS Collaboration, "Performance of the ATLAS liquid argon
  calorimeter after three years of LHC operation and plans for a future upgrade",
  arXiv:1306.6756v2 (full text read 2026-10-25). Cell energy from samples with the ramp, the DAC
  calibration and the physics-to-calibration pulse ratio `M_phys/M_cali` (sec. II-C).
- G. Aad et al., "Readiness of the ATLAS liquid argon calorimeter for LHC collisions",
  arXiv:0912.2642v4 (sec. 3.1.2, pp. 16-17, read in the full text 2026-10-25; journal
  reference not checked). Cell energy reconstruction (eq. 5); `M_phys/M_cali` as the ratio of the
  responses to calibration and ionization pulses of the same input current.
<!-- /example -->
- J. Apostolakis et al., "HEP Software Foundation Community White Paper Working Group -
  Detector Simulation", arXiv:1803.04165 (read 2026-10-25). Zero-bias overlay against
  premixing; non-zero-suppressed samples and nonlinear signal addition as the overlay's
  difficulties.
- J. P. Nolan, "Numerical calculation of stable densities and distribution functions",
  Commun. Statist. Stochastic Models 13 (1997) 759-774, DOI 10.1080/15326349708807450
  (matched against Crossref, 2026-10-25). The integral representation used for the Landau
  density and distribution function in `frontend_response.py` (Landau = stable law
  `alpha = 1`, `beta = 1`, scale `pi/2`).

## Timing detectors ([timing detectors](timing-detectors.md))

- G. Pellegrini et al., "Technology developments and first measurements of Low Gain
  Avalanche Detectors (LGAD) for high energy physics applications", Nucl. Instrum.
  Methods A765 (2014) 12-16, DOI 10.1016/j.nima.2014.06.008. LGAD.
- H. F.-W. Sadrozinski, A. Seiden and N. Cartiglia, "4D tracking with ultra-fast
  silicon detectors", Rep. Prog. Phys. 81 (2018) 026101 (published online 2017), DOI 10.1088/1361-6633/aa94d3.
  Ultra-fast silicon and timing
  in trackers, including radiation effects.

## Cherenkov, RICH, DIRC/TOP, TRD, ionization PID, photosensors ([particle identification](particle-identification.md), [cherenkov imaging variants and photosensors](cherenkov-imaging-variants-and-photosensors.md))

- T. Ypsilantis and J. Seguinot, "Theory of ring imaging Cherenkov counters", Nucl.
  Instrum. Methods A343 (1994) 30-51, DOI 10.1016/0168-9002(94)90532-0. RICH principles, resolution terms.
<!-- example: experiment-specific illustration -->
- I. Adam et al. (BaBar DIRC), "The DIRC particle identification system for the BaBar
  experiment", Nucl. Instrum. Methods A538 (2005) 281-357, DOI 10.1016/j.nima.2004.08.129. DIRC principle and a worked
  implementation; TOP is the time-of-propagation extension of the same idea.
<!-- /example -->
- B. Dolgoshein, "Transition radiation detectors", Nucl. Instrum. Methods A326 (1993)
  434-469, DOI 10.1016/0168-9002(93)90846-A. TRD principles and electron/hadron separation.
- Hamamatsu Photonics, *Photomultiplier Tubes: Basics and Applications* (manufacturer
  handbook, 4th ed.; no DOI; PDF at
  <https://www.hamamatsu.com/content/dam/hamamatsu-photonics/sites/documents/99_SALES_LIBRARY/etd/PMT_handbook_v4E.pdf>;
  PMT gain, timing, noise). F. Acerbi and S. Gundacker, "Understanding and
  simulating SiPMs", Nucl. Instrum. Methods A926 (2019) 16-35, DOI 10.1016/j.nima.2018.11.118. SiPM dark counts, crosstalk,
  afterpulsing.

## Calorimetry ([calorimetry ecal hcal](calorimetry-ecal-hcal.md))

- C. W. Fabjan and F. Gianotti, "Calorimetry for particle physics", Rev. Mod. Phys. 75
  (2003) 1243-1286, DOI 10.1103/RevModPhys.75.1243. Sampling and homogeneous calorimeters, resolution terms, hadronic
  response, compensation.
- R. Wigmans, *Calorimetry: Energy Measurement in Particle Physics*, 2nd ed. (Oxford
  University Press, 2017), DOI 10.1093/oso/9780198786351.001.0001. Non-compensation, dual readout, hadronic shower physics.
- M. A. Thomson, "Particle flow calorimetry and the PandoraPFA algorithm", Nucl.
  Instrum. Methods A611 (2009) 25-40, DOI 10.1016/j.nima.2009.09.009. Particle flow, confusion term.

## Noble-liquid, neutrino, rare-event detectors ([noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md))

- E. Aprile and T. Doke, "Liquid xenon detectors for particle physics and
  astrophysics", Rev. Mod. Phys. 82 (2010) 2053-2097, DOI 10.1103/RevModPhys.82.2053. Scintillation, ionization,
  recombination, anticorrelation, noble-liquid detectors.
- The PDG non-accelerator detector review above covers neutrino, dark-matter, and
  cryogenic detectors at the level used here.

## Astroparticle systems ([extensive air showers](extensive-air-showers.md), [ground based detection arrays](ground-based-detection-arrays.md), [imaging atmospheric cherenkov](imaging-atmospheric-cherenkov.md), [neutrino astronomy](neutrino-astronomy.md), [space based direct detection](space-based-direct-detection.md))

- T. K. Gaisser, R. Engel and E. Resconi, *Cosmic Rays and Particle Physics*, 2nd ed.
  (Cambridge University Press, 2016), DOI 10.1017/CBO9781139192194. Air showers, atmospheric and detection techniques.
- M. S. Longair, *High Energy Astrophysics*, 3rd ed. (Cambridge University Press,
  2011), DOI 10.1017/CBO9780511778346. Astrophysical context.
- T.-P. Li and Y.-Q. Ma, "Analysis methods for results in gamma-ray astronomy",
  Astrophys. J. 272 (1983) 317-324, DOI 10.1086/161295. ON/OFF significance.

<!-- example: source citation (experiment named as the source of a general method or number) -->
- **Read 2026-10-14 for the hep-detector audit** (astroparticle corrections): Verzi for the Pierre Auger
  Collaboration, PoS(ICRC2019)231 (energy-scale budget); Gesualdi et al., PoS(ICRC2021)473 (WHISP muon-scale
  summary); LHAASO, arXiv:2505.14447 (proton knee); ANTARES, IceCube, LIGO and Virgo, arXiv:1703.06298 (+-500 s
  window); DAMPE, Sci. Adv. 5 (2019) eaax3793, arXiv:1909.12860 (calorimetric unfolding); R. Nolty, Caltech thesis,
  arXiv:hep-ex/0201015 (Störmer cutoff and the east-west effect); ECSS-E-ST-10-04C annex B.8 via SPENVIS; SIDC and
  the Royal Observatory of Belgium (solar cycle 25 minimum and maximum).
<!-- /example -->

## Simulation and reconstruction ([event reconstruction](event-reconstruction.md), [detector simulation](detector-simulation.md))

- S. Agostinelli et al. (GEANT4), "GEANT4: a simulation toolkit", Nucl. Instrum.
  Methods A506 (2003) 250-303, DOI 10.1016/S0168-9002(03)01368-8. Documentation: <https://geant4.web.cern.ch/support/user_documentation>
  (Physics Reference Manual for physics lists, production cuts, model validity ranges).

**Reconstruction methods** (cited in [tracking and vertexing](tracking-and-vertexing.md), [calorimetry](calorimetry-ecal-hcal.md),
[noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md),
[photon likelihood reconstruction](photon-likelihood-reconstruction.md),
[gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md) and
[ground based detection arrays](ground-based-detection-arrays.md)). Each entry below was matched against the Crossref
record of its DOI (authors, title, venue, volume, pages, year) on 2026-10-30; as above, the annotation is the use made
here, not a re-reading of the work, and no performance number is taken from them.

<!-- example: source citations (experiments named as the source of a general method) -->
- W. Adam, R. Frühwirth, A. Strandlie and T. Todorov, "Reconstruction of electrons with the Gaussian-sum filter in the
  CMS tracker at the LHC", J. Phys. G 31 (2005) N9-N20, DOI 10.1088/0954-3899/31/9/N01. Gaussian-sum filter.
- W. Waltenberger, R. Frühwirth and P. Vanlaer, "Adaptive vertex fitting", J. Phys. G 34 (2007) N343-N356,
  DOI 10.1088/0954-3899/34/12/N01. Adaptive (annealed) vertex fit.
- C. Kleinwort, "General broken lines as advanced track fitting method", Nucl. Instrum. Methods A673 (2012) 107-110,
  DOI 10.1016/j.nima.2012.01.024. Broken-lines global fit.
- X. Ai et al., "A Common Tracking Software Project", Comput. Softw. Big Sci. 6 (2022) 8,
  DOI 10.1007/s41781-021-00078-8. Combinatorial Kalman filter track finding in a shared implementation.
- T. C. Awes, F. E. Obenshain, F. Plasil, S. Saini et al., "A simple method of shower localization and identification
  in laterally segmented calorimeters", Nucl. Instrum. Methods A311 (1992) 130-138,
  DOI 10.1016/0168-9002(92)90858-2. Logarithmic position weighting.
- R. Acciarri et al. (MicroBooNE), "The Pandora multi-algorithm approach to automated pattern recognition of
  cosmic-ray muon and neutrino events in the MicroBooNE detector", Eur. Phys. J. C 78 (2018) 82,
  DOI 10.1140/epjc/s10052-017-5481-6. LArTPC view matching.
- X. Qian, C. Zhang, B. Viren and M. Diwan, "Three-dimensional imaging for large LArTPCs", J. Instrum. 13 (2018)
  P05032, DOI 10.1088/1748-0221/13/05/P05032. Tomographic LArTPC imaging.
- P. Abratenko et al. (MicroBooNE), "Determination of muon momentum in the MicroBooNE LArTPC using an improved model
  of multiple Coulomb scattering", J. Instrum. 12 (2017) P10010, DOI 10.1088/1748-0221/12/10/P10010. Momentum from
  multiple scattering.
- M. Jiang et al. (Super-Kamiokande), "Atmospheric neutrino oscillation analysis with improved event reconstruction
  in Super-Kamiokande IV", Prog. Theor. Exp. Phys. 2019 (2019) 053F01, DOI 10.1093/ptep/ptz015. Joint charge-time
  likelihood with multi-ring hypotheses.
- J. Ahrens et al. (AMANDA), "Muon track reconstruction and data selection techniques in AMANDA", Nucl. Instrum.
  Methods A524 (2004) 169-194, DOI 10.1016/j.nima.2004.01.065. First-guess line fit, photon arrival-time likelihood.
- M. G. Aartsen et al. (IceCube), "Energy reconstruction methods in the IceCube neutrino telescope", J. Instrum. 9
  (2014) P03009, DOI 10.1088/1748-0221/9/03/P03009. Tabulated light model, energy from the light along a track.
- R. D. Parsons and J. A. Hinton, "A Monte Carlo template based analysis for air-Cherenkov arrays", Astropart. Phys.
  56 (2014) 26-34, DOI 10.1016/j.astropartphys.2014.03.002. Pixel-likelihood image templates.
- The Pierre Auger Collaboration, "The Pierre Auger Cosmic Ray Observatory", Nucl. Instrum. Methods A798 (2015)
  172-213, DOI 10.1016/j.nima.2015.06.058. Surface and fluorescence reconstruction in a hybrid observatory.
- T. Huege, "Radio detection of cosmic ray air showers in the digital era", Phys. Rep. 620 (2016) 1-52,
  DOI 10.1016/j.physrep.2016.02.001. Radio emission and reconstruction (review).
- C. Glaser, M. Erdmann, J. R. Hörandel, T. Huege and J. Schulz, "Simulation of radiation energy release in air
  showers", J. Cosmol. Astropart. Phys. 09 (2016) 024, DOI 10.1088/1475-7516/2016/09/024. Radiation energy and its
  geomagnetic-angle and air-density corrections.
- S. Buitink et al., "Method for high precision reconstruction of air shower X_max using two-dimensional radio
  intensity profiles", Phys. Rev. D 90 (2014) 082003, DOI 10.1103/PhysRevD.90.082003. `X_max` from simulated radio
  footprints.
- S. Aiola et al., "Hybrid seeding: A standalone track reconstruction algorithm for scintillating fibre tracker at
  LHCb", Comput. Phys. Commun. 260 (2021) 107713, DOI 10.1016/j.cpc.2020.107713. Fibre-tracker track finding.
- L. Arrabito et al., "Track reconstruction in the emulsion-lead target of the OPERA experiment using the ESS
  microscope", J. Instrum. 2 (2007) P05004, DOI 10.1088/1748-0221/2/05/P05004. Emulsion base-track linking and film
  alignment.
- M. De Serio et al., "Momentum measurement by the angular method in the Emulsion Cloud Chamber", Nucl. Instrum.
  Methods A512 (2003) 539-545, DOI 10.1016/S0168-9002(03)02016-3. Momentum from multiple scattering in emulsion.
- D. M. Chernyak et al., "Rejection of randomly coinciding events in ZnMoO4 scintillating bolometers", Eur. Phys.
  J. C 74 (2014) 2913, DOI 10.1140/epjc/s10052-014-2913-4. Pileup rejection in bolometers.
- A. Broniatowski, B. Censier, A. Juillard and L. Bergé, "Cryogenic germanium detectors for dark matter search:
  Surface events rejection by charge measurements", Nucl. Instrum. Methods A559 (2006) 378-380,
  DOI 10.1016/j.nima.2005.12.015. Surface-event rejection with interleaved electrodes.
- D. Budjáš, M. Barnabé Heider, O. Chkvorets, N. Khanbekov and S. Schönert, "Pulse shape discrimination studies with a
  Broad-Energy Germanium detector for signal identification and background suppression in the GERDA double beta
  decay experiment", J. Instrum. 4 (2009) P10007, DOI 10.1088/1748-0221/4/10/P10007. Germanium current-pulse
  discrimination.
<!-- /example -->

## Statistics, performance measurement, and uncertainties ([reconstruction performance and truth matching](reconstruction-performance-and-truth-matching.md), [performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md), [data mc validation and detector systematics](data-mc-validation-and-detector-systematics.md))

- G. Cowan, K. Cranmer, E. Gross and O. Vitells, "Asymptotic formulae for
  likelihood-based tests of new physics", Eur. Phys. J. C71 (2011) 1554, DOI 10.1140/epjc/s10052-011-1554-0,
  <https://arxiv.org/abs/1007.1727>. Profile likelihood, Asimov data.
- C. J. Clopper and E. S. Pearson, "The use of confidence or fiducial limits illustrated
  in the case of the binomial", Biometrika 26 (1934) 404-413, DOI 10.1093/biomet/26.4.404; L. D. Brown, T. T. Cai and
  A. DasGupta, "Interval estimation for a binomial proportion", Statist. Sci. 16 (2001)
  101-133, DOI 10.1214/ss/1009213286. Exact and alternative binomial intervals for efficiencies.

## Not listed here

Specific technical design reports, performance papers, and calibration notes of named
experiments are omitted on purpose: any detector-specific number in downstream work must
be sourced from the relevant apparatus's own documentation. Nuclear emulsions, forward
proton detectors, neutron detectors, beam and luminosity monitors, polarimeters, and
cryogenic bolometers are treated at the principle level in this study and are covered by
the general textbooks and PDG reviews above; add primary sources when a downstream
analysis relies on a specific device.
