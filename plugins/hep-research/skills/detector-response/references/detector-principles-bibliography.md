# References (Annotated, by Detector Family and Topic)

Companion to `high_energy_detector_principles.md`. Citation format used throughout:
author(s), title, venue volume (year) pages, then a persistent identifier: a DOI
(resolve at `https://doi.org/<DOI>`) or, where none exists, a stable URL.

**Verification status (2026-09-20).** Every journal article and book below was matched
against the Crossref registry by title, first author, venue, volume, pages, and year,
and its DOI is given as returned by Crossref. Every URL was checked to return HTTP 200.
Not verified: that each work supports the specific use noted in its annotation (this
was written from knowledge of the works, not by re-reading them), and DOI/URL
availability can change over time. The document makes no detector-specific performance
claim, so none of these is cited for a number; if a performance value is quoted
downstream, cite the apparatus's own technical design report or official performance
paper (name, configuration, phase space, conditions), which are deliberately not listed
here because they are experiment-specific. Prefer primary sources for technical claims;
the textbooks are for principles.

## General and cross-cutting

- **Particle Data Group reviews** (current edition, <https://pdg.lbl.gov/>):
  *Passage of particles through matter* (<https://pdg.lbl.gov/2025/reviews/rpp2025-rev-passage-particles-matter.pdf>),
  *Particle detectors at accelerators* (<https://pdg.lbl.gov/2025/reviews/rpp2025-rev-particle-detectors-accel.pdf>),
  *Particle detectors for non-accelerator physics* (<https://pdg.lbl.gov/2025/reviews/rpp2025-rev-particle-detectors-non-accel.pdf>),
  *Statistics* (<https://pdg.lbl.gov/2025/reviews/rpp2025-rev-statistics.pdf>). Standard
  reference for Bethe-Bloch, Highland, radiation and interaction lengths, Cherenkov and
  transition radiation, detector resolution parameterizations, and statistical
  terminology (Chapters 2-3, 6, 9-11, 17). Particle masses and properties for PID
  calculations come from the PDG listings.
- W. R. Leo, *Techniques for Nuclear and Particle Physics Experiments*, 2nd ed.
  (Springer, 1994), DOI 10.1007/978-3-642-57920-2. Textbook: interaction with matter, signal formation, electronics.
- D. Grupen and B. Shwartz, *Particle Detectors*, 2nd ed. (Cambridge University Press,
  2008), DOI 10.1017/CBO9780511534966. Textbook covering nearly all detector families in this study.
- F. Sauli, *Gaseous Radiation Detectors: Fundamentals and Applications* (Cambridge
  University Press, 2014), DOI 10.1017/CBO9781107337701. Gas detectors, drift, diffusion, gain, micro-pattern devices.

## Signal formation, energy loss, fluctuations (Chapter 3)

- H. Bichsel, "Straggling in thin silicon detectors", Rev. Mod. Phys. 60 (1988) 663-699, DOI 10.1103/RevModPhys.60.663.
  Landau/Vavilov-type fluctuations in thin layers.
- V. L. Highland, "Some practical remarks on multiple scattering", Nucl. Instrum.
  Methods 129 (1975) 497-499, DOI 10.1016/0029-554X(75)90743-0; G. R. Lynch and O. I. Dahl, "Approximations to multiple
  Coulomb scattering", Nucl. Instrum. Methods B58 (1991) 6-10, DOI 10.1016/0168-583X(91)95671-Y. Origin of the Highland
  approximation; the PDG review gives the current form.

## Tracking, vertexing, alignment (Chapters 5-7, 12)

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

## Timing detectors (Chapter 8)

- G. Pellegrini et al., "Technology developments and first measurements of Low Gain
  Avalanche Detectors (LGAD) for high energy physics applications", Nucl. Instrum.
  Methods A765 (2014) 12-16, DOI 10.1016/j.nima.2014.06.008. LGAD.
- H. F.-W. Sadrozinski, A. Seiden and N. Cartiglia, "4D tracking with ultra-fast
  silicon detectors", Rep. Prog. Phys. 81 (2018) 026101 (published online 2017), DOI 10.1088/1361-6633/aa94d3.
  Ultra-fast silicon and timing
  in trackers, including radiation effects.

## Cherenkov, RICH, DIRC/TOP, TRD, ionization PID, photosensors (Chapters 9-10)

- T. Ypsilantis and J. Seguinot, "Theory of ring imaging Cherenkov counters", Nucl.
  Instrum. Methods A343 (1994) 30-51, DOI 10.1016/0168-9002(94)90532-0. RICH principles, resolution terms.
- I. Adam et al. (BaBar DIRC), "The DIRC particle identification system for the BaBar
  experiment", Nucl. Instrum. Methods A538 (2005) 281-357, DOI 10.1016/j.nima.2004.08.129. DIRC principle and a worked
  implementation; TOP is the time-of-propagation extension of the same idea.
- B. Dolgoshein, "Transition radiation detectors", Nucl. Instrum. Methods A326 (1993)
  434-469, DOI 10.1016/0168-9002(93)90846-A. TRD principles and electron/hadron separation.
- Hamamatsu Photonics, *Photomultiplier Tubes: Basics and Applications* (manufacturer
  handbook, 4th ed.; no DOI; PDF at
  <https://www.hamamatsu.com/content/dam/hamamatsu-photonics/sites/documents/99_SALES_LIBRARY/etd/PMT_handbook_v4E.pdf>;
  PMT gain, timing, noise). F. Acerbi and S. Gundacker, "Understanding and
  simulating SiPMs", Nucl. Instrum. Methods A926 (2019) 16-35, DOI 10.1016/j.nima.2018.11.118. SiPM dark counts, crosstalk,
  afterpulsing.

## Calorimetry (Chapter 11)

- C. W. Fabjan and F. Gianotti, "Calorimetry for particle physics", Rev. Mod. Phys. 75
  (2003) 1243-1286, DOI 10.1103/RevModPhys.75.1243. Sampling and homogeneous calorimeters, resolution terms, hadronic
  response, compensation.
- R. Wigmans, *Calorimetry: Energy Measurement in Particle Physics*, 2nd ed. (Oxford
  University Press, 2017), DOI 10.1093/oso/9780198786351.001.0001. Non-compensation, dual readout, hadronic shower physics.
- M. A. Thomson, "Particle flow calorimetry and the PandoraPFA algorithm", Nucl.
  Instrum. Methods A611 (2009) 25-40, DOI 10.1016/j.nima.2009.09.009. Particle flow, confusion term.

## Noble-liquid, neutrino, rare-event detectors (Chapter 13)

- E. Aprile and T. Doke, "Liquid xenon detectors for particle physics and
  astrophysics", Rev. Mod. Phys. 82 (2010) 2053-2097, DOI 10.1103/RevModPhys.82.2053. Scintillation, ionization,
  recombination, anticorrelation, noble-liquid detectors.
- The PDG non-accelerator detector review above covers neutrino, dark-matter, and
  cryogenic detectors at the level used here.

## Astroparticle systems (Chapter 13)

- T. K. Gaisser, R. Engel and E. Resconi, *Cosmic Rays and Particle Physics*, 2nd ed.
  (Cambridge University Press, 2016), DOI 10.1017/CBO9781139192194. Air showers, atmospheric and detection techniques.
- M. S. Longair, *High Energy Astrophysics*, 3rd ed. (Cambridge University Press,
  2011), DOI 10.1017/CBO9780511778346. Astrophysical context.
- T.-P. Li and Y.-Q. Ma, "Analysis methods for results in gamma-ray astronomy",
  Astrophys. J. 272 (1983) 317-324, DOI 10.1086/161295. ON/OFF significance.

## Simulation and reconstruction (Chapters 14-15)

- S. Agostinelli et al. (GEANT4), "GEANT4: a simulation toolkit", Nucl. Instrum.
  Methods A506 (2003) 250-303, DOI 10.1016/S0168-9002(03)01368-8. Documentation: <https://geant4.web.cern.ch/support/user_documentation>
  (Physics Reference Manual for physics lists, production cuts, model validity ranges).

## Statistics, performance measurement, and uncertainties (Chapters 16-18)

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
