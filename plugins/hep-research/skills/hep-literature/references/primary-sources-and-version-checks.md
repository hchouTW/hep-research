# Primary Sources and Version Checks

This package is original operational guidance, not a complete summary of the manuals below. Apply formulas with their stated assumptions. Experiment-specific prescriptions must follow the formal sources supplied by the user. Links were consulted during preparation on 2026-09-05, with the astroparticle-physics entries added 2026-09-09; rolling/development pages do not pin an API version.

| Topic | Primary source | Purpose |
|---|---|---|
| HEP statistics | [PDG Statistics review](https://pdg.lbl.gov/2026/reviews/rpp2026-rev-statistics.pdf) | Check interval, likelihood, and inference terminology |
| Profile likelihood and Asimov data | [Cowan et al., arXiv:1007.1727](https://arxiv.org/abs/1007.1727) | Check statistics and asymptotic assumptions |
| RooStats | [ROOT AsymptoticCalculator, version 6.26](https://root.cern.ch/doc/v626/classRooStats_1_1AsymptoticCalculator.html) | Historical API reference; use installed-version documentation for implementation |
| pyhf models | [Likelihood specification](https://scikit-hep.org/pyhf/likelihood.html) | Schema, modifiers, and auxiliary data; may be a development page |
| pyhf preservation | [pyhf paper](https://arxiv.org/abs/2211.15838) | Background on HistFactory serialization |
| uproot | [Official getting-started guide](https://uproot.readthedocs.io/en/latest/basic.html) | Chunked I/O and array APIs |
| Passage of particles through matter | [PDG review](https://pdg.lbl.gov/2026/reviews/rpp2026-rev-passage-particles-matter.pdf) | Bethe-Bloch, Highland multiple scattering, radiation length, Cherenkov and transition radiation |
| Particle detectors at accelerators | [PDG review](https://pdg.lbl.gov/2026/reviews/rpp2026-rev-particle-detectors-accel.pdf) | Detector technologies, resolution parameterizations, calorimeter terms |
| Particle detectors for non-accelerator physics | [PDG review](https://pdg.lbl.gov/2026/reviews/rpp2026-rev-particle-detectors-non-accel.pdf) | Spectrometer, TOF, and Cherenkov practice outside collider geometries |
| Particle masses and properties | [PDG Particle Listings](https://pdg.lbl.gov/) | Masses used by `pid_separation_power.py` and `cherenkov_angle.py` |
| Geant4 physics | [Physics Reference Manual](https://geant4.web.cern.ch/support/user_documentation) | Physics lists, production cuts, hadronic model validity ranges |
| Cosmic rays and particle physics (textbook) | Gaisser, Engel & Resconi, *Cosmic Rays and Particle Physics*, 2nd ed. (Cambridge University Press, 2016) | Acceleration, propagation, air-shower, and detection-technique background for the astroparticle references in hep-detector ([air showers](../../hep-detector/references/extensive-air-showers.md) to [space-based detection](../../hep-detector/references/space-based-direct-detection.md)) and the cosmic-ray experiment profiles |
| Combine | [Official documentation](https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest/) | Match methods/options to the installed release |
| Cosmic-ray astrophysics (textbook) | Longair, *High Energy Astrophysics*, 3rd ed. (Cambridge University Press, 2011) | Acceleration mechanisms, multi-messenger astrophysics context |
| ON/OFF significance | Li & Ma, *Astrophysical Journal* 272, 317 (1983) | Derivation of the likelihood-ratio significance in `<plugin root>/skills/hep-statistics/scripts/li_ma_significance.py` |
| Cosmic-ray and astroparticle physics reviews | [PDG](https://pdg.lbl.gov/) | Cosmic-ray, astrophysical-constants, and related review chapters; check the current edition's table of contents for the exact chapter |
| Detector textbooks | Leo, *Techniques for Nuclear and Particle Physics Experiments*, 2nd ed. (Springer, 1994), [DOI 10.1007/978-3-642-57920-2](https://doi.org/10.1007/978-3-642-57920-2); Grupen & Shwartz, *Particle Detectors*, 2nd ed. (Cambridge University Press, 2008), [DOI 10.1017/CBO9780511534966](https://doi.org/10.1017/CBO9780511534966); Wigmans, *Calorimetry*, 2nd ed. (Oxford University Press, 2017), [DOI 10.1093/oso/9780198786351.001.0001](https://doi.org/10.1093/oso/9780198786351.001.0001); Blum, Riegler & Rolandi, *Particle Detection with Drift Chambers*, 2nd ed. (Springer, 2008), [DOI 10.1007/978-3-540-76684-1](https://doi.org/10.1007/978-3-540-76684-1) | Signal formation, drift/diffusion, calorimetry, gas detectors for the hep-detector technique references ([measurement framework](../../hep-detector/references/detector-measurement-framework.md) to [Cherenkov and photosensors](../../hep-detector/references/cherenkov-imaging-variants-and-photosensors.md)) |
| Track fitting | Fruhwirth, "Application of Kalman filtering to track and vertex fitting", Nucl. Instrum. Methods A262 (1987) 444, [DOI 10.1016/0168-9002(87)90887-4](https://doi.org/10.1016/0168-9002(87)90887-4) | Kalman track/vertex fit behind the [tracking](../../hep-detector/references/tracking-and-vertexing.md), [gaseous tracking](../../hep-detector/references/gaseous-and-specialized-tracking-technologies.md) and [muon systems](../../hep-detector/references/muon-systems.md) references |
| Multiple scattering | Highland, Nucl. Instrum. Methods 129 (1975) 497, [DOI 10.1016/0029-554X(75)90743-0](https://doi.org/10.1016/0029-554X(75)90743-0); Lynch & Dahl, Nucl. Instrum. Methods B58 (1991) 6, [DOI 10.1016/0168-583X(91)95671-Y](https://doi.org/10.1016/0168-583X(91)95671-Y) | Highland approximation used in [signal formation and readout](../../hep-detector/references/signal-formation-and-readout.md) (PDG review above gives the current form) |
| Geomagnetic cutoff | Smart & Shea, "A review of geomagnetic cutoff rigidities for earth-orbiting spacecraft", Adv. Space Res. 36 (2005) 2012 | Stormer form and the vertical `14.9 cos^4(lambda)/r^2` GV cutoff in `<plugin root>/skills/hep-measurement/scripts/geomagnetic_cutoff.py` (added 2026-09-24) |
| Solar modulation | Gleeson & Axford, Astrophys. J. 154 (1968) 1011 | Force-field approximation in `<plugin root>/skills/hep-measurement/scripts/solar_modulation_force_field.py`; shift `|Z| phi` in total kinetic energy, `(|Z|/A) phi` per nucleon |
| Solar cycle 24 and Voyager heliopause dates | [SILSO: 2014, maximum year for cycle 24](https://www.sidc.be/SILSO/news004); [NASA Voyager interstellar mission](https://science.nasa.gov/mission/voyager/interstellar-mission/); Stone et al., Science 341 (2013) 150 (Voyager 1); [Voyager 2 enters interstellar space, arXiv:1912.02476](https://arxiv.org/abs/1912.02476) | Cycle 24 minimum Dec 2008, maximum Apr 2014 with a Nov 2011 first peak; Voyager 1 heliopause 25 Aug 2012, Voyager 2 5 Nov 2018 ([space-based direct detection](../../hep-detector/references/space-based-direct-detection.md); checked by web search 2026-09-25) |
| Exact binomial/Poisson intervals | Clopper & Pearson, Biometrika 26 (1934) 404; Garwood, Biometrika 28 (1936) 437 | `tag_and_probe_efficiency.py` and `cosmic_ray_flux.py`; cross-checked against `scipy.stats` beta/chi2 quantiles in `<plugin root>/tests/skills/hep_detector/test_reference_values.py` |
| Longitudinal shower profile | Gaisser & Hillas, Proc. 15th ICRC (Plovdiv) 8 (1977) 353 | Functional form in `<plugin root>/skills/hep-detector/scripts/xmax_gaisser_hillas.py` |
| Detector-performance definitions | Experiment technical design reports and official performance papers for the apparatus in question (cite by name, configuration, and phase space; none is pinned here) | Any numeric performance claim in the hep-detector references must come from one of these, not from this package |
| Claude Code skills | [Official documentation](https://code.claude.com/docs/en/skills) | Skill directories and invocation |

Experiment- and collaboration-specific sources (illustrations; facts about an experiment live in its profile):

<!-- example: experiment-specific illustration -->
| Topic | Primary source | Purpose |
|---|---|---|
| Pierre Auger Observatory | [Official site](https://www.auger.org/) | Hybrid surface-array/fluorescence UHECR methodology and publications |
| IceCube Neutrino Observatory | [Official site](https://icecube.wisc.edu/) | In-ice Cherenkov neutrino-telescope methodology and publications |
| CTA Observatory | [Official site](https://www.cta-observatory.org/) | Imaging atmospheric Cherenkov technique and next-generation IACT array design |
| Alpha Magnetic Spectrometer (AMS-02) | Aguilar et al., "The Alpha Magnetic Spectrometer (AMS) on the International Space Station: Part II - Results from the First Seven Years," Phys. Rept. 894 (2021) 1-116 | Primary cross-check for instrument parameters and results; mission status, servicing and upgrade facts live in the `experiment:ams-02` profile's evidence ledger with their verification dates, not here. |
<!-- /example -->

Do not claim that an API is supported by the latest version without checking. Read local version/help output and lock files, then consult matching release documentation. Mark unverified points when network access is unavailable. Example luminosities, cross sections, and model parameters in documentation are not experimental inputs. The detector geometries, material budgets, and resolution values in this package's assets and examples are synthetic and illustrative; they are not measurements of any real apparatus.

## Latest-results policy

Measured values move: spectral-break positions, flux normalizations, limits, detector
performance and mission status are superseded by later publications. Rules:

- Any "latest", "current", "best", or "world-leading" statement, and any experimental
  number quoted as a result, must name its source and the date it was checked
  (`checked YYYY-MM-DD`). Without both, present it as an illustrative order of magnitude.
- Before quoting such a number to a user, re-check it if the check date is older than
  12 months, or state that it was not re-checked.
- Standard physics constants and textbook formulas (PDG constants, Bethe-Bloch, Highland,
  Stormer, force field) are stable and exempt, but still cite the edition they came from.
<!-- example: experiment-specific illustration -->
- Items to re-verify on each pass. Live checks done 2026-09-25 and re-run 2026-10-02 (the
  2026-09-24 pass was from knowledge only):
  - PDG edition: the 2026 edition is current; the links above now point to it (all four
    PDFs resolve). Checked 2026-09-25; pdg.lbl.gov still shows 2026 as current, 2026-10-02.
  - Knee/ankle/GZK energies and indices ([cosmic-ray spectrum](../../hep-detector/references/cosmic-ray-spectrum-and-composition.md)): checked 2026-09-25, text re-read
    2026-10-02 (unchanged, still "Revised March 2026"), against the
    [PDG 2026 cosmic-ray review](https://pdg.lbl.gov/2026/reviews/rpp2026-rev-cosmic-rays.pdf)
    (revised March 2026). Reference 30 corrected to match: knee at a few PeV, `gamma`
    ~2.7 -> ~3; second knee ~100 PeV, -> ~3.3; ankle ~5 EeV, -> ~2.5; instep from ~10 EeV;
    suppression from ~50 EeV. Note: PDG 2026 (section 30.6) words the instep as "a further
    flattening beginning at 10 EeV", but the Auger fit it cites (PRL 125 (2020) 121106)
    has `gamma` rising from ~2.5 to ~3.0 near 13 EeV, i.e. a steepening. Reference 30
    follows Auger.
  - IACT energy-scale systematic ([IACTs](../../hep-detector/references/imaging-atmospheric-cherenkov.md)): checked 2026-09-25, re-read in full text
    2026-10-02. MAGIC: energy-scale systematic <15% (abstract of arXiv:1508.04575). CTA
    (arXiv:1508.07225): the **requirement** is <10% on the energy scale, and the baseline
    calibration methods are expected to reach ~15% (a target "<10%" and an expected "~15%",
    not a "~15% target" as the 2026-09-25 note said). H.E.S.S. (arXiv:2403.12608, sect. 5): no
    single energy-scale percentage; about 10% variation in atmospheric transparency remains
    after run selection. VERITAS (arXiv:2111.04676, sect. 6): ~25% total on the absolute flux
    for an index-2.5 source (+5-10% in quadrature above ~10 TeV) and +-0.2 on the index; it
    gives no separate energy-scale percentage, so the earlier "up to ~20% for VERITAS" is
    **not confirmed** and the IACT reference now quotes the flux figure instead.
  - Experiment status and instrument parameters (mission status, upgrade schedules,
    detector numbers) are not kept here: they belong in the bound experiment profile's
    evidence ledger, each with a claim id, its source and a verification date (see the
    context-resolution steps in the skill's SKILL.md). Removed from this file 2026-10-14.
<!-- /example -->

**Done when:** every source used for a formula or API names its version or date, and anything not checked is marked unverified.
