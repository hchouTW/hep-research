# T11: sources read

26 sources, read 2026-11-06. Read levels are as recorded when reading: `full-text`, or `page` for named sections only. A cell may rest only on what was read. The literature record is `<private>/evidence/t11-artifacts/t11-literature-record.json`, which passes `contracts/validate.py`; the 35 searches behind it are logged with it, and they were title searches, not a systematic review. Tiers were assigned for T11, with no profile policy.

Six statements were checked against the papers' own text: F27 vertex, F28 sidelobes and ghosts, KATRIN stacking, HAYSTAC baseline, PICO acoustics, Project 8 sidebands. All held. The other cells were not checked this way. Figures were not viewed, only captions.

| ID | Families | Title | Authors | Year | Identifier | Read level |
| --- | --- | --- | --- | --- | --- | --- |
| t11:S01 | F21 | Superconducting nanowire single-photon detectors: physics and applications | Natarajan, Chandra M. et al. | 2012 | arXiv:1204.5560 | page |
| t11:S02 | F21 | High speed readout electronics development for frequency-multiplexed kinetic inductance de | Bourrion, O. et al. | 2013 | arXiv:1310.5891 | full-text |
| t11:S03 | F21 | Mitigation of Cosmic Ray Effect on Microwave Kinetic Inductance Detector Arrays | Karatsu, K. et al. | 2019 | arXiv:1901.02387 | full-text |
| t11:S04 | F24 | Dark Matter Search Results from the Complete Exposure of the PICO-60 C$_3$F$_8$ Bubble Cha | PICO Collaboration et al. | 2019 | arXiv:1902.04031 | full-text |
| t11:S05 | F24 | Response of Superheated Droplet Detectors of the PICASSO Dark Matter Search Experiment | PICASSO Collaboration et al. | 2005 | arXiv:physics/0508098 | page |
| t11:S06 | F26 | Detection and Imaging of the Crab Nebula with the Nuclear Compton Telescope | Bandstra, M.S. et al. | 2011 | arXiv:1106.0323 | full-text |
| t11:S07 | F26 | 3D Image Reconstruction from Compton camera data | Kuchment, Peter et al. | 2016 | arXiv:1604.03805 | page |
| t11:S08 | F27 | The Large Area Telescope on the Fermi Gamma-ray Space Telescope Mission | Fermi-LAT Collaboration et al. | 2009 | arXiv:0902.1089 | page |
| t11:S09 | F27 | Pass 8: Toward the Full Realization of the Fermi-LAT Scientific Potential | Fermi-LAT Collaboration et al. | 2013 | arXiv:1303.3514 | full-text |
| t11:S10 | F28 | Coded Aperture Imaging in High-Energy Astrophysics | Braga, João | 2019 | arXiv:1909.08595 | page |
| t11:S11 | F33 | Single-electron and single-photon sensitivity with a silicon Skipper CCD | SENSEI Collaboration et al. | 2017 | arXiv:1706.00028 | full-text |
| t11:S12 | F33 | SENSEI: Characterization of Single-Electron Events Using a Skipper-CCD | SENSEI Collaboration et al. | 2021 | arXiv:2106.08347 | full-text |
| t11:S13 | F34 | Tritium Beta Spectrum and Neutrino Mass Limit from Cyclotron Radiation Emission Spectrosco | Project 8 Collaboration et al. | 2022 | arXiv:2212.05048 | full-text |
| t11:S14 | F34 | Cyclotron Radiation Emission Spectroscopy of Electrons from Tritium Beta Decay and 83mKr I | Project 8 Collaboration et al. | 2023 | arXiv:2303.12055 | page |
| t11:S15 | F34 | Determining the neutrino mass with Cyclotron Radiation Emission Spectroscopy -- Project 8 | Project 8 Collaboration et al. | 2017 | arXiv:1703.02037 | page |
| t11:S16 | F35 | The HAYSTAC Axion Search Analysis Procedure | Brubaker, B.M. et al. | 2017 | arXiv:1706.08388 | page |
| t11:S17 | F35 | Axion search with a quantum-limited ferromagnetic haloscope | QUAX Collaboration et al. | 2020 | arXiv:2001.08940 | full-text |
| t11:S18 | F35 | Broadband solenoidal haloscope for terahertz axion detection | BREAD Collaboration et al. | 2021 | arXiv:2111.12103 | page |
| t11:S19 | F36 | Analysis methods for the first KATRIN neutrino-mass measurement | KATRIN Collaboration et al. | 2021 | arXiv:2101.05253 | page |
| t11:S20 | F36 | Time-Focusing Time-of-Flight, a new method to turn a MAC-E-filter into a quasi-differentia | Fulst, Alexander et al. | 2020 | arXiv:2007.01020 | page |
| t11:S21 | F37 | ixpeobssim: a Simulation and Analysis Framework for the Imaging X-ray Polarimetry Explorer | Baldini, L. et al. | 2022 | arXiv:2203.06384 | page |
| t11:S22 | F37 | A crosstalk and non-uniformity correction method for the space-borne Compton polarimeter P | Xiao, Hualin et al. | 2015 | arXiv:1507.04474 | page |
| t11:S23 | F38 | Madam - a map-making method for CMB experiments | Keihanen, E. et al. | 2004 | arXiv:astro-ph/0412517 | page |
| t11:S24 | F38 | Comparison of map-making algorithms for CMB experiments | Poutanen, Torsti et al. | 2005 | arXiv:astro-ph/0501504 | page |
| t11:S25 | F38 | Destriping CMB temperature and polarization maps | Kurki-Suonio, H. et al. | 2009 | arXiv:0904.3623 | page |
| t11:S26 | F38 | Iterative destriping and photometric calibration for Planck-HFI, polarized, multi-detector | Tristram, M. et al. | 2011 | arXiv:1103.2281 | page |

## Scope notes from reading

No plan statement was contradicted. Refinements for T11's later passes:

- F27: a majority of events above 1 GeV have no recognizable vertex (0902.1089), so single-track output is normal.
- F28: the fully coded field has no intrinsic sidelobes; ghosts come from partial coding (1909.08595).
- F36, W7: KATRIN sums like steps and averages `qU`, after stability checks and with a stacking uncertainty (2101.05253). This is legitimate under those conditions and does not loosen W7's rule.
- F34, BP13: Project 8 sidebands are too weak to detect (2212.05048).
- F38: all sources read are simulation studies; no modulation or filter-transfer source was found.
- F35 circuit and F37 modulated variants have no source; all their cells are `gap-method`.
- 1303.3514 (Pass 8) is a 2013 status report.
