# Detector atlas: evidence index and claim-to-source map

Profile-qualified ids (`detector-atlas:S01`, `detector-atlas:C001`). The two tables are **generated** from
`sources.json` and `claims.json`: edit those files, then from the plugin root run
`python3 core/evidence/ledger.py --sources S --claims C --namespace detector-atlas` and
`python3 core/evidence/render_index.py --sources S --claims C --index I --write`, then
`python3 skills/hep-detector/scripts/detector_atlas.py validate`. Each source row carries its own verification date.

## Verification level

`full-text`: the full text was obtained (publisher or arXiv PDF) and the overview chapter or section and every cited
passage were read on the verification date; the long detector papers were not read cover to cover. A claim's strength
never exceeds its source's level.

## Source table

<!-- BEGIN GENERATED: source-table (edit sources.json, then run core/evidence/render_index.py --write) -->
| ID | Title | Authors | Year | DOI / URL | Tier | Level |
|---|---|---|---|---|---|---|
| detector-atlas:S01 | The ATLAS Experiment at the CERN Large Hadron Collider | ATLAS Collaboration (G. Aad et al.) |  | https://iopscience.iop.org/article/10.1088/1748-0221/3/08/S08003/pdf | 1: the collaboration's detector paper | full-text (full text obtained from the publisher or arXiv PDF and converted to text; the overview chapter or section and every cited passage read at its location; the document was not read cover to cover) |
| detector-atlas:S02 | The CMS experiment at the CERN LHC | CMS Collaboration (S. Chatrchyan et al.) |  | https://iopscience.iop.org/article/10.1088/1748-0221/3/08/S08004/pdf | 1: the collaboration's detector paper | full-text (full text obtained from the publisher or arXiv PDF and converted to text; the overview chapter or section and every cited passage read at its location; the document was not read cover to cover) |
| detector-atlas:S03 | The LHCb Upgrade I | LHCb Collaboration (R. Aaij et al.) |  | https://arxiv.org/abs/2305.10515 | 1: the collaboration's detector paper for the upgraded detector | full-text (full text obtained from the publisher or arXiv PDF and converted to text; the overview chapter or section and every cited passage read at its location; the document was not read cover to cover) |
| detector-atlas:S04 | The IceCube Neutrino Observatory: Instrumentation and Online Systems | IceCube Collaboration (M. G. Aartsen et al.) |  | https://arxiv.org/abs/1612.05093 | 1: the collaboration's instrumentation paper | full-text (full text obtained from the publisher or arXiv PDF and converted to text; the overview chapter or section and every cited passage read at its location; the document was not read cover to cover) |
| detector-atlas:S05 | Calibration of the Super-Kamiokande Detector | K. Abe et al. (Super-Kamiokande) |  | https://arxiv.org/abs/1307.0162 | 1: the collaboration's calibration paper with the detector description | full-text (full text obtained from the publisher or arXiv PDF and converted to text; the overview chapter or section and every cited passage read at its location; the document was not read cover to cover) |
| detector-atlas:S06 | The Large Area Telescope on the Fermi Gamma-ray Space Telescope Mission | W. B. Atwood et al. (Fermi LAT) |  | https://arxiv.org/abs/0902.1089 | 1: the instrument paper | full-text (full text obtained from the publisher or arXiv PDF and converted to text; the overview chapter or section and every cited passage read at its location; the document was not read cover to cover) |
<!-- END GENERATED: source-table -->

## Claim ledger

<!-- BEGIN GENERATED: claim-ledger (edit claims.json, then run core/evidence/render_index.py --write) -->
| claim_id | claim (paraphrased) | type | source | location | supported scope | limitation |
|---|---|---|---|---|---|---|
| detector-atlas:C001 | The inner detector is immersed in a 2 T solenoidal field. | performance_number | detector-atlas:S01 | section 1.1 | ATLAS: detector as described in 2008 (design) | |
| detector-atlas:C002 | Tracking: required resolution sigma_pT/pT = 0.05% pT (+) 1%, eta coverage +-2.5 (pT in GeV). | performance_number | detector-atlas:S01 | table 1.1 | ATLAS: detector as described in 2008 (design) | |
| detector-atlas:C003 | EM calorimetry: required resolution sigma_E/E = 10%/sqrt(E) (+) 0.7% (E in GeV). | performance_number | detector-atlas:S01 | table 1.1 | ATLAS: detector as described in 2008 (design) | |
| detector-atlas:C004 | Hadronic calorimetry (jets), barrel and end-cap: required resolution sigma_E/E = 50%/sqrt(E) (+) 3%. | performance_number | detector-atlas:S01 | table 1.1 | ATLAS: detector as described in 2008 (design) | |
| detector-atlas:C005 | Muon spectrometer: required resolution sigma_pT/pT = 10% at pT = 1 TeV. | performance_number | detector-atlas:S01 | table 1.1 | ATLAS: detector as described in 2008 (design) | |
| detector-atlas:C006 | The pixel intrinsic accuracies in the barrel are 10 um (R-phi) and 115 um (z). | performance_number | detector-atlas:S01 | section 1.2 | ATLAS: detector as described in 2008 (design) | |
| detector-atlas:C007 | The SCT intrinsic accuracies per module in the barrel are 17 um (R-phi) and 580 um (z). | performance_number | detector-atlas:S01 | section 1.2 | ATLAS: detector as described in 2008 (design) | |
| detector-atlas:C008 | The TRT provides typically 36 hits per track and has an intrinsic accuracy of 130 um per straw (R-phi only). | performance_number | detector-atlas:S01 | section 1.2 | ATLAS: detector as described in 2008 (design) | |
| detector-atlas:C009 | The pixel detector has approximately 80.4 million readout channels. | detector_fact | detector-atlas:S01 | section 1.2 | ATLAS: detector as described in 2008 (design) | |
| detector-atlas:C010 | The dimensions of the detector are 25 m in height and 44 m in length; the overall weight is approximately 7000 tonnes. | detector_fact | detector-atlas:S01 | figure 1.1 caption | ATLAS: detector as described in 2008 (design) | |
| detector-atlas:C011 | The Level-1 trigger reduces the data rate to approximately 75 kHz (limited by the readout bandwidth, upgradeable to 100 kHz). | performance_number | detector-atlas:S01 | section 1.1 | ATLAS: detector as described in 2008 (design) | |
| detector-atlas:C012 | At the heart of CMS sits a 13-m-long, 6-m-inner-diameter, 4-T superconducting solenoid providing a large bending power (12 Tm). | performance_number | detector-atlas:S02 | section 1.1 | CMS: detector as described in 2008 (design; before the 2017 pixel upgrade) | |
| detector-atlas:C013 | The tracking volume is given by a cylinder of 5.8-m length and 2.6-m diameter. | detector_fact | detector-atlas:S02 | section 1.1 | CMS: detector as described in 2008 (design; before the 2017 pixel upgrade) | |
| detector-atlas:C014 | CMS employs 10 layers of silicon microstrip detectors, and 3 layers of silicon pixel detectors close to the interaction region. | detector_fact | detector-atlas:S02 | section 1.1 | CMS: detector as described in 2008 (design; before the 2017 pixel upgrade) | |
| detector-atlas:C015 | The electromagnetic calorimeter uses lead tungstate (PbWO4) crystals with coverage in pseudorapidity up to \|eta\| < 3.0. | detector_fact | detector-atlas:S02 | section 1.1 | CMS: detector as described in 2008 (design; before the 2017 pixel upgrade) | |
| detector-atlas:C016 | The ECAL energy resolution for incident electrons measured in a beam test has stochastic, noise and constant terms S = 2.8% GeV^1/2, N = 0.12 GeV, C = 0.3%. | performance_number | detector-atlas:S02 | section 1.1, figure 1.3 | CMS: ECAL beam test reported in 2008 | |
| detector-atlas:C017 | The ECAL thickness is larger than 25 X0; the HCAL thickness varies in the range 7-11 lambda_I (10-15 lambda_I with the HO included), depending on eta. | detector_fact | detector-atlas:S02 | section 1.1 | CMS: detector as described in 2008 (design; before the 2017 pixel upgrade) | |
| detector-atlas:C018 | Coverage up to a pseudorapidity of 5.0 is provided by an iron/quartz-fibre calorimeter. | detector_fact | detector-atlas:S02 | section 1.1 | CMS: detector as described in 2008 (design; before the 2017 pixel upgrade) | |
| detector-atlas:C019 | The CMS detector is 21.6-m long and has a diameter of 14.6 m; it has a total weight of 12 500 t. | detector_fact | detector-atlas:S02 | section 1.1 | CMS: detector as described in 2008 (design; before the 2017 pixel upgrade) | |
| detector-atlas:C020 | The return field allows 4 muon stations to be integrated; each consists of drift tubes in the barrel and cathode strip chambers in the endcap, complemented by resistive plate chambers. | detector_fact | detector-atlas:S02 | section 1.1 | CMS: detector as described in 2008 (design; before the 2017 pixel upgrade) | |
| detector-atlas:C021 | LHCb is a single-arm forward spectrometer covering the pseudorapidity range 2 < eta < 5. | detector_fact | detector-atlas:S03 | section 2.1 | LHCb: upgraded detector (Upgrade I, from 2022) | |
| detector-atlas:C022 | The dipole magnet, unchanged with respect to Run 1-2, provides a vertical magnetic field with a bending power of about 4 Tm. | performance_number | detector-atlas:S03 | section 2.2 | LHCb: original and upgraded detector | |
| detector-atlas:C023 | LHCb was originally designed to take data at a maximum instantaneous luminosity of 2 x 10^32 cm^-2 s^-1. | performance_number | detector-atlas:S03 | section 1 | LHCb: original detector (2009-2018) | |
| detector-atlas:C024 | LHCb was operated for most of Run 1 and Run 2 at about 4 x 10^32 cm^-2 s^-1. | performance_number | detector-atlas:S03 | section 1 | LHCb: Run 1 and Run 2 (2010-2018) | |
| detector-atlas:C025 | The upgrade is designed to run at a nominal instantaneous luminosity of 2 x 10^33 cm^-2 s^-1 and to collect events at the LHC crossing rate of 40 MHz. | performance_number | detector-atlas:S03 | section 1 | LHCb: upgraded detector (Upgrade I, from 2022) | |
| detector-atlas:C026 | Inner radius of the active silicon detector of the VELO: 8.2 mm (2009-2018). | performance_number | detector-atlas:S03 | section 3.1, table 1 | LHCb: original detector (2009-2018) | |
| detector-atlas:C027 | Inner radius of the active silicon detector of the VELO: 5.1 mm (2022). | performance_number | detector-atlas:S03 | section 3.1, table 1 | LHCb: upgraded detector (Upgrade I, from 2022) | |
| detector-atlas:C028 | VELO pitch: 37-97 um r-phi strips (2009-2018); 55 um square pixels (2022). | performance_number | detector-atlas:S03 | section 3.1, table 1 | LHCb: original (2009-2018) and upgraded (2022) VELO | |
| detector-atlas:C029 | VELO total number of channels: 172 thousand (2009-2018); 41 million (2022). | detector_fact | detector-atlas:S03 | section 3.1, table 1 | LHCb: original (2009-2018) and upgraded (2022) VELO | |
| detector-atlas:C030 | LHCb collected a total of 9 fb^-1 of proton-proton data during Run 1 and Run 2. | performance_number | detector-atlas:S03 | section 1 | LHCb: Run 1 and Run 2 (2010-2018) | |
| detector-atlas:C031 | 5160 DOMs are deployed between 1450 m and 2450 m below the surface of the ice on 86 vertical strings; each string consists of 60 DOMs. | detector_fact | detector-atlas:S04 | section 1.1.1 | IceCube: full detector after completion of construction (2011), as described in the 2017 paper | |
| detector-atlas:C032 | The primary in-ice array consists of 78 strings with a vertical DOM separation of 17 m on a triangular grid with 125 m horizontal spacing, instrumenting one cubic kilometer of ice. | detector_fact | detector-atlas:S04 | section 1.1.1 | IceCube: full detector after completion of construction (2011), as described in the 2017 paper | |
| detector-atlas:C033 | The angular resolution for muon tracks is typically 0.6 degrees, confirmed by the shadows of the Moon and Sun in cosmic rays. | performance_number | detector-atlas:S04 | section 1.1.1 | IceCube: full detector after completion of construction (2011), as described in the 2017 paper | |
| detector-atlas:C034 | The eight specialized DeepCore strings have a DOM-to-DOM spacing of 7 m for the bottom 50 DOMs, deployed at depths of 2100 m to 2450 m. | detector_fact | detector-atlas:S04 | section 1.1.2 | IceCube: full detector after completion of construction (2011), as described in the 2017 paper | |
| detector-atlas:C035 | DeepCore's denser geometry and increased efficiency result in an energy threshold of about 10 GeV, compared to about 100 GeV for most IceCube analyses. | performance_number | detector-atlas:S04 | section 1.1.2 | IceCube: full detector after completion of construction (2011), as described in the 2017 paper | |
| detector-atlas:C036 | IceTop, at 2835 m above sea level, consists of 162 ice-filled tanks arranged in 81 stations. | detector_fact | detector-atlas:S04 | section 1.1.3 | IceCube: full detector after completion of construction (2011), as described in the 2017 paper | |
| detector-atlas:C037 | The measured photon arrival-time accuracy is 1.2 ns (from flasher data with 7 m DOM spacing). | performance_number | detector-atlas:S04 | time-calibration section, figure 18 | IceCube: full detector after completion of construction (2011), as described in the 2017 paper | |
| detector-atlas:C038 | As of 2016, 5397 of the 5484 deployed DOMs (98.4%) are operating in data-taking mode. | performance_number | detector-atlas:S04 | DOM reliability section | IceCube: status in 2016 | |
| detector-atlas:C039 | IceCube routinely achieves a detector uptime of 99%. | performance_number | detector-atlas:S04 | abstract | IceCube: operations after construction (as of 2016) | |
| detector-atlas:C040 | Construction of IceCube was completed in 2011. | detector_fact | detector-atlas:S04 | abstract | IceCube: full detector after completion of construction (2011), as described in the 2017 paper | |
| detector-atlas:C041 | The SK detector is a cylindrical tank (39.3 m diameter and 41.4 m height) filled with 50 kilotons of ultra-pure water. | detector_fact | detector-atlas:S05 | section 2.1 | Super-K: all phases | |
| detector-atlas:C042 | The detector is located 1000 m underground (2,700 m water equivalent) in the Kamioka mine. | detector_fact | detector-atlas:S05 | section 2.1 | Super-K: all phases | |
| detector-atlas:C043 | SK-I (1996 Apr. - 2001 Jul.) had 11146 inner-detector PMTs (40% photo-coverage). | detector_fact | detector-atlas:S05 | table 1 | Super-K: SK-I (April 1996 - July 2001) | |
| detector-atlas:C044 | SK-II (2002 Oct. - 2005 Oct.) had 5182 inner-detector PMTs (19% photo-coverage). | detector_fact | detector-atlas:S05 | table 1 | Super-K: SK-II (October 2002 - October 2005) | |
| detector-atlas:C045 | SK-III (2006 Jul. - 2008 Sep.) and SK-IV (from 2008 Sep.) had 11129 inner-detector PMTs (40% photo-coverage). | detector_fact | detector-atlas:S05 | table 1 | Super-K: SK-III and SK-IV (from July 2006) | |
| detector-atlas:C046 | The outer detector has 1885 PMTs. | detector_fact | detector-atlas:S05 | table 1 | Super-K: SK-I to SK-IV (as tabulated) | |
| detector-atlas:C047 | The electronics were upgraded in September 2008; SK-IV uses the QBEE front-end electronics. | detector_fact | detector-atlas:S05 | section 2.1, table 1 | Super-K: SK-IV (from September 2008) | |
| detector-atlas:C048 | The timing resolution was 2.1 ns at the one-photoelectron charge level and 0.5 ns at the 100-photoelectron charge level. | performance_number | detector-atlas:S05 | abstract | Super-K: SK-IV calibration (paper of 2013) | |
| detector-atlas:C049 | Charge determination was at the level of 1%. | performance_number | detector-atlas:S05 | abstract | Super-K: SK-IV calibration (paper of 2013) | |
| detector-atlas:C050 | Anti-implosion containers were added from SK-II on; OD segmentation from SK-III on. | detector_fact | detector-atlas:S05 | table 1 | Super-K: detector configuration per phase (SK-I to SK-IV) | |
| detector-atlas:C051 | The tracker and calorimeter each consist of a 4 x 4 array of 16 modules. | detector_fact | detector-atlas:S06 | abstract | Fermi-LAT: pre-flight expected performance (2009 paper) | |
| detector-atlas:C052 | Each tracker module has a vertical stack of 18 x, y tracking planes, with tungsten converter material. | detector_fact | detector-atlas:S06 | abstract | Fermi-LAT: pre-flight expected performance (2009 paper) | |
| detector-atlas:C053 | Every calorimeter module has 96 CsI(Tl) crystals in 8 layers, with a total depth of 8.6 radiation lengths (10.1 for the whole instrument). | detector_fact | detector-atlas:S06 | abstract; section 2.2 | Fermi-LAT: pre-flight expected performance (2009 paper) | |
| detector-atlas:C054 | Field of view: 2.4 sr. | performance_number | detector-atlas:S06 | table 1 | Fermi-LAT: pre-flight expected performance (2009 paper) | |
| detector-atlas:C055 | Energy range: 20 MeV - 300 GeV. | performance_number | detector-atlas:S06 | table 1 | Fermi-LAT: pre-flight expected performance (2009 paper) | |
| detector-atlas:C056 | Effective area at normal incidence: 9,500 cm^2 (maximum as a function of energy). | performance_number | detector-atlas:S06 | table 1 | Fermi-LAT: pre-flight expected performance (2009 paper) | |
| detector-atlas:C057 | Energy resolution (equivalent Gaussian 1 sigma), 1 GeV - 10 GeV on axis: 8%-9%. | performance_number | detector-atlas:S06 | table 1 | Fermi-LAT: pre-flight expected performance (2009 paper) | |
| detector-atlas:C058 | Single-photon angular resolution, on-axis 68% containment radius: <= 0.15 deg above 10 GeV, 0.6 deg at 1 GeV, 3.5 deg at 100 MeV. | performance_number | detector-atlas:S06 | table 1 | Fermi-LAT: pre-flight expected performance (2009 paper) | |
| detector-atlas:C059 | Event readout time (dead time): 26.5 us. | performance_number | detector-atlas:S06 | table 1 | Fermi-LAT: pre-flight expected performance (2009 paper) | |
| detector-atlas:C060 | Timing accuracy: < 10 us. | performance_number | detector-atlas:S06 | table 1 | Fermi-LAT: pre-flight expected performance (2009 paper) | |
<!-- END GENERATED: claim-ledger -->
