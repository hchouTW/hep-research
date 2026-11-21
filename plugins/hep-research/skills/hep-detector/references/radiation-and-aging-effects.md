# Radiation and Ageing Effects

Damage from dose, fluence and charge, for conditions and simulation. Environments: COL, FXT, SPC, UGD;
GND and NUC are gaps. Electronics damage (SEU, circuit TID):
[front-end electronics](front-end-electronics-and-signal-processing.md#radiation-and-the-electronics).

## Relations

Fluence `Phi_eq` is the non-ionizing energy loss (NIEL) normalised to the damage of 1 MeV neutrons, in
`n_eq/cm^2`; total ionizing dose (TID) is in Gy, independent of particle type (definitions; PDG RPP 2025,
sec. 35.8.5, p. 74). Give both, with the particle spectrum they came from: NIEL scaling
holds well for leakage current and is "moderately violated" for other effects (same page).

| Relation | Label, validity and source |
|---|---|
| `Delta I_L = alpha_80 Phi_eq V`, `alpha_80 ≈ 4e-17 A/cm` at 20 °C after 80 min at 60 °C (not the `alpha_I` below) | approximate (NIEL hypothesis); `V` depleted volume; gain in the device multiplies it. PDG sec. 35.8.5, p. 74 |
| `I_L(T) ∝ T^2 exp(-E_a/(2kT))`, `E_a ≈ 1.2 eV` | approximate; about 7-fold from room temperature to 0 °C (PDG; the relation gives 6.6 from 20 °C). PDG eq. (35.26), p. 74 |
| `N_id = N_id,0 exp(-c Phi_eq)` (initial dopant removal) | approximate; `c` depends on `N_id,0`, particle type and impurities (Fig. 35.32). PDG sec. 35.8.5, p. 76 |
| induced current times `exp(-t/tau_eff,e/h)`; `1/tau_eff ∝ Phi_eq` | approximate; linear up to about `1e15 n_eq/cm^2`, where `tau_eff` is of order 1 ns, then saturating. PDG p. 77 |
| bias limit from single-event effects at average fields near 12 V/um | approximate; sets the lifetime in highly energetic particle fields. PDG pp. 77-78 |
| `I_leak = sum_i V_i Phi_eq,i [alpha_I exp(-sum_{j>=i} t_j/tau(T_j)) + alpha_0* - beta ln(sum_{j>=i} Theta(T_j) t_j / t_0)]` | approximate (phenomenological annealing model); per interval `i` with fluence `Phi_eq,i` (collider: `(Phi/L_int) L_int,i`), duration, temperature and depleted volume `V_i`; `alpha_I` is the short-term amplitude; `t_0` = 1 min, natural log; 20 °C scaling with `E_eff = 1.12 eV`, not the 1.2 eV above; gives the current at full depletion (10% for the bias used); `beta` at 21 °C; valid at the 2015-2017 fluences (≤ `1e15 n_eq/cm^2`) and annealing times. arXiv:1905.03739, abstract, sec. 3.1, eqs. (1)-(2), pp. 5-6, notes 5-6 |
| `L/L_0 ≈ exp(-D/D_c)` for plastic scintillator | approximate; `D_c` of tens of kGy at dose rates from a few `1e-3` to 10 Gy/h, larger damage at lower rate. PDG sec. 35.3.2, p. 12 |
| `S(t)/S_0 = (R(t)/R_0)^alpha` (scintillation versus monitoring-light response) | approximate, for small transparency losses; `alpha` differs between crystal producers, measured in a beam test under irradiation; an in-situ tuned value is an effective exponent that also absorbs VPT loss, outside this validity. arXiv:1306.2016, sec. 4.1, eq. (3), pp. 10-11, and sec. 4.1.1, p. 12 |
| `s(t) = (p_0 - p_1) + p_1 exp(-(t - t_s)/tau)` (energy-scale drift) | approximate, empirical fit to a monitored peak over three years (Fig. 73), extrapolated beyond; `t_s` is eq. (53)'s `t_0`. arXiv:1206.1896, sec. 7.3.2, eq. (53), p. 137 |
| `R = -(1/G) dG/dQ` (% per C/cm) | definition of the gas ageing rate; **not** a predictor at high rate, where ageing is not a function of `Q` alone. arXiv:hep-ex/0204005, sec. I, p. 1 |
| `Q_A = r_pe T f_duty G e` (integrated anode charge per area) | exact bookkeeping for a constant photoelectron rate `r_pe` (DQE × incident rate) per area, run time `T`, duty factor, gain `G`; an unspecified photon rate taken as `r_pe` bounds the photon-induced charge only: state which |

## Damage and ageing by sensor

**Silicon (bulk and surface).** Bulk damage (displaced atoms) raises the leakage current, traps carriers and builds
space charge that changes the depletion voltage; surface damage (oxide charge, interface traps) scales with TID and
raises surface currents and changes inter-electrode isolation (PDG sec. 35.8.5, p. 74). Damage changes with time:
beneficial annealing first, then reverse annealing over months at room temperature and much longer when cold; n-type
bulk inverts, p-type with n+ readout does not, and is preferred because electrons are collected (pp. 75-76).
Temperature and warm-ups are therefore part of the damage history (p. 78). Related:
[tracking and vertexing](tracking-and-vertexing.md). In low Earth orbit a
design study took trapped protons only (SPC; arXiv:1503.07682, abstract; sec. 1, p. 3).

<!-- example: ATLAS pixel detector (COL) and LOFT silicon drift detectors (SPC design study) -->
ATLAS pixel (arXiv:1905.03739):
eq. (1): short-term amplitude `alpha_I = (1.23 ± 0.06)e-17
A/cm` with `alpha_0* = 7.07e-17 A/cm` and `beta = (3.29 ± 0.18)e-18 A/cm` (sec. 3.1, pp. 5-6): with its
`tau(T)` and `Theta(T)`, the bracket is about `4.1e-17 A/cm` after 80 min at 60 °C (central values, `3.2e-17` to `5.2e-17` over the quoted ranges, computed here), the `alpha_80` above. LOFT SDDs (arXiv:1503.07682): charge collection loss measured with protons against expected
in-orbit damage (abstract; sec. 1, p. 3).
<!-- /example -->

**LGAD.** The highly doped gain layer loses acceptors with fluence, so gain drops sharply (PDG p. 77); raising
the bias recovers part of it, until the single-event limit above. Deeper gain layers (stronger recovery with
bias) and carbon in the gain layer (fewer interstitials that remove boron) are the mitigations (arXiv:2004.05260,
secs. 1-2, pp. 1-2). This is a **single-environment** technique (COL): acceptor removal is measured at the
fluences of hadron-collider timing layers (example below), while the lifetime fluence a SiPM review gives for
most space detectors is below 1e12 particles/cm^2 as quoted, not NIEL-weighted (arXiv:1809.06361, sec. 1, p. 1).
Timing consequences: [timing detectors](timing-detectors.md).

<!-- example: LGAD prototypes for the HL-LHC timing layers (ATLAS HGTD, CMS ETL; COL) -->
arXiv:2004.05260: 50 um HPK and 55 um FBK LGADs (abstract; Table 1, p. 2), neutron-irradiated from `4e14` to `4e15 n_eq/cm^2`, measured at
-30 °C; the deep and the carbonated gain layers perform reasonably up to `3e15` (abstract); requirements up to a few `1e15 n_eq/cm^2` and a
few MGy (sec. 1, p. 1).
<!-- /example -->

**SiPM.** The dominant effect is the rise in dark count rate, which first destroys single-photoelectron resolution
(arXiv:1809.06361, abstract). Pixel occupancy from dark counts then lowers the effective photon detection
efficiency and gain (eq. (10), p. 11). The fluence at which single photoelectrons are lost depends on design and
temperature: test it per application; annealing (room temperature, or high temperature with forward
bias) recovers part of it (secs. 3.4 and 6, pp. 12 and 15). With a scintillator, the rising dark rate raises the
energy threshold (SPC; arXiv:2411.00607v2, abstract).

<!-- example: GRBAlpha and VZLUSAT-2 CubeSats, Hamamatsu S13360-3050PE MPPCs (SPC) -->
arXiv:2411.00607v2: GRBAlpha, 550 km sun-synchronous orbit, CsI(Tl) read by eight MPPCs behind 2-2.5 mm PbSb: the
low-energy threshold rose from about 20 to about 120 keV in 3 years 5 months, matching a simulated TID of 1.6
Gy and `2.1e9 n_eq/cm^2` from trapped protons (AP-8) (abstract; sec. 6, p. 14).
<!-- /example -->

**Crystal scintillators.** Ionizing dose forms colour centres; the induced absorption shortens the attenuation
length, lowers light output and distorts light-response uniformity; hadrons add
displacement and fission-fragment damage (PDG sec. 35.4, p. 18). Damage and spontaneous recovery compete, so the
loss depends on dose rate; injected monitoring light tracks it (COL; arXiv:1306.2016, sec. 3, p. 8).

<!-- example: CMS ECAL PbWO4 (COL) and the Fermi LAT CsI(Tl) calorimeter (SPC) -->
CMS ECAL (arXiv:1306.2016): by the end of 2011 the average laser response
dropped 2-3% in the barrel and 40% at 2.7 ≤ |eta| ≤ 3.0 in the endcap, there partly from VPT loss (sec.
3, p. 8); `alpha` of eq. (3) is 1.52 and 1.0 for the two crystal producers, BTCP and SIC, with a 10% spread, from a
beam test (sec. 4.1, pp. 10-11); an effective 1.16 for endcap BTCP, tuned on Z to ee events, absorbs the VPT loss
(sec. 4.1.1, p. 12). Fermi LAT (arXiv:1206.1896): light yield fell about 1% per year over its first three
years in orbit (sec. 2.1.2, p. 20); eq. (53) on the proton peak gives `tau` ≈ 2 years and a correctable
4.5% energy-scale shift after 10 years, extrapolated (sec. 7.3.2, p. 137).
<!-- /example -->

**Plastic scintillator and WLS fibres.** Radiation yellows the plastic and lowers its transparency, which partly recovers after irradiation, faster with oxygen (PDG sec.
35.3.2, p. 12). Plastics also age **without dose**: crazing under stress or solvents, and fogging from
humidity at elevated temperature (same page); for a measured long-term loss the cause can stay unknown, with
photochemical oxidation a further candidate (arXiv:2207.12982, sec. 1.2, pp. 7-8). Separate the causes with two
monitors: a light source that bypasses the scintillator sees the photosensor,
a radioactive source or physics signal sees both (COL; arXiv:1806.02129, sec. 4.5, p. 24).

<!-- example: ATLAS Tile Calorimeter (COL) and T2K near detectors (UGD) -->
TileCal (arXiv:1806.02129, sec. 4.5, pp. 23-24): the difference between minimum-bias (or Cs) and laser response is
read as scintillator irradiation; laser data alone show PMT gain loss under light and recovery
without collisions. T2K near detectors (arXiv:2207.12982): light yield fell 0.9-2.2% per year over ten years (abstract,
p. 5); most of the loss is in the scintillator, not the WLS fibres, whose long attenuation component degrades by
1-5% per year (sec. 7, p. 31).
<!-- /example -->

**MCP-PMT.** Ions fed back from residual gas damage the photocathode, so quantum efficiency falls with integrated
anode charge; atomic-layer-deposition (ALD) coatings of the channels raise the lifetime above 20 C/cm^2 of anode
charge (PDG sec. 35.2.1.2, pp. 5-6; arXiv:2311.16676, sec. 1, p. 1). Lifetime tests illuminate at a known rate,
log the anode charge and scan QE; a covered part of the photocathode separates charge-driven loss from loss with
time alone, such as vacuum micro-leaks (arXiv:2311.16676, sec. 2.1, p. 2). Lifetime source: FXT only.

<!-- example: PANDA Barrel and Endcap Disc DIRC MCP-PMTs (FXT) -->
arXiv:2311.16676: before ALD the QE dropped by a factor of 2 or more after a few hundred mC/cm^2; a photon rate of
about 200 kHz/cm^2 (incident or detected not stated), 10 years, 50% duty and gain `1e6` give an expected
charge of about 5 C/cm^2 for the Barrel DIRC (sec. 1, p. 1; the upper bound of the relation above gives 5.1
C/cm^2); a tube with two ALD layers reached more than 34 C/cm^2 of anode charge with no QE loss yet (sec. 2.1,
p. 2).
<!-- /example -->

**Gaseous detectors.** Avalanche plasma chemistry forms deposits on electrodes, from hydrocarbon quenchers and
outgassing insulators, glues and oils; strict materials and gas control allow several C/cm^2 without observable
ageing (PDG sec. 35.6.2.4, p. 33). An insulating cathode layer can ignite the self-sustained Malter discharge;
ageing depends on gas, materials, irradiated area, current density, gain, rate, particle type and energy, so
laboratory tests with X-ray sources may not transfer to a hadron environment (arXiv:hep-ex/0204005, secs. II.A
and V.D, pp. 2 and 8). Data: FXT and COL (same review, secs. IV.A and V.D, pp. 4 and 9). Drift chambers: [gaseous
tracking](gaseous-and-specialized-tracking-technologies.md#drift-chambers-and-drift-tubes).

<!-- example: HERA-B honeycomb drift tubes and muon chambers (FXT) -->
arXiv:hep-ex/0204005, sec. V.D, pp. 8-9: prototype honeycomb drift tubes aged severely after a few mC/cm in the hadron
environment of 920 GeV protons on a nuclear target, though X-ray tests to 5 C/cm showed nothing; in the muon
proportional chambers the ageing rate in Ar/CF4/CH4 was over 100 times higher in hadron beams than with radioactive sources.
<!-- /example -->

## Radiation fields by environment

- **COL.** Dose and hadron fluence depend on radius and pseudorapidity and scale with integrated luminosity;
  the fluence comes from an event generator plus transport (Pythia8, FLUKA) as `Phi/L_int`, checked per
  module group against leakage currents through the annealing model, FLUKA kept for the central value with a 15% uncertainty from that study, valid only at central `|z| ≈ 0` and excluding the hardness-factor uncertainty (significant, not quantified): the data show a stronger `z`-dependence,
  FLUKA about 1.5 sigma off at `z = 0` and more at larger `|z|`, where the `Phi/L_int` fitted per module group (Fig. 3) or an uncertainty covering the difference is needed (arXiv:1905.03739, secs. 2-3.1, pp. 3-8).
- **SPC (low Earth orbit).** The proton/electron balance depends on shielding and spectrum (example below), so
  model trapped electrons too; solar protons and Galactic cosmic rays add little TID for that orbit and shielding (arXiv:2411.00607v2, sec. 4.1,
  p. 10). Dose depends on altitude, shielding and solar cycle (same page), from trapped-particle models (AP-8 protons,
  AE-8 electrons), with a factor of two quoted on the AP-8 flux only (sec. 3.2, p. 7); its cited
  SPENVIS page gives the widely quoted factor of 2 for AP-8 and AE-8, larger for differential fluxes made from the integral maps (SPENVIS trapped-radiation help, sec. 5.1): assign at least that to both and state the factor used or vary it. In AP-8, trapped protons at low altitude are more numerous at
  solar minimum (arXiv:1503.07682, sec. 1, p. 3). Cutoff
  handling is in [space-based direct detection](space-based-direct-detection.md#geomagnetic-cutoff).
- **UGD.** No underground damage source is cited (gap; plastic ageing of unknown cause: above); context:
  [noble liquid and neutrino detectors](noble-liquid-neutrino-and-rare-event-detectors.md).

<!-- example: CMS ECAL (COL), LOFT, Fermi and GRBAlpha orbits (SPC) -->
CMS ECAL: expected dose up to 4 kGy in the barrel and 200 kGy at |eta| = 3 after 10 years (500 fb^-1); hadron
fluence from about `1e13` to `1e14 cm^-2`, as quoted (weighting and NIEL source not stated;
arXiv:1306.2016, sec. 2, p. 6). LOFT: AP8-MIN via SPENVIS, 600 km and 5° worst case, behind 3.3 mm Al equivalent;
AP8-MIN is about 7 times AP8-MAX at 1 MeV (arXiv:1503.07682, sec. 1, p. 3). Fermi: 565 km at 25.6°, about 15% of the
time in the SAA, with science data suspended there (arXiv:1206.1896, sec. 2.2, p. 25). GRBAlpha: behind 2-2.5 mm
PbSb, trapped protons dominate TID and TNID, electrons about 1-6% of TID (central values, 1.1-7.3% within the quoted uncertainties, computed here from `TID(p)/TID(e)`:
1.3% at ~550 km with the solar-minimum AP-8/AE-8 models, 74 ± 14; 5.8% at ~475 km with the solar-maximum models (altitude and model changed together), 16.1 ± 3.4, as `1/(1 + ratio)`; arXiv:2411.00607v2 (GRAS), sec. 4.1, p. 10).
<!-- /example -->

## Feeding damage into conditions and simulation

1. **Conditions.** Store the damage history, not a constant: per interval the [Tool hooks](#tool-hooks) inputs (fluence
   from `Phi/L_int` or orbit segments) and the monitored response. Derived constants (trapping,
   threshold, light-yield factor `S_i(t)`, energy-scale drift) are payloads with intervals of validity
   ([calibration and alignment](calibration-and-alignment.md#time-dependence-and-conditions-data)). The light
   monitor corrects each channel by the transfer relation (COL; arXiv:1306.2016, sec. 4.1, p. 10); in orbit a
   stable peak (non-interacting protons) tracks the scale, fitted in time (arXiv:1206.1896, sec. 7.3.2, p. 137).
2. **Digitization.** Digitize with device-model fields and trapping; state whether annealing enters. One collider
   pixel digitizer omits annealing with no correction or uncertainty: at the annealing state reached, its variation, checked at `1e14` and `2e14 n_eq/cm^2`,
   lies within the field-model and trapping-constant variations; omit it only after that check at your fluences and annealing state (COL; arXiv:1905.03739,
   secs. 2, 4.2.3, 4.2.4 and 4.5, Table 5, pp. 4-5, 20 and 24). General digitization:
   [detector simulation](detector-simulation.md#digitization).
3. **Dose prediction.** Pre-launch, Geant4-based MULASSIS gave TID only, without electrons,
   and in orbit AE-8 and AP-8 fluences per mission segment (IRENE) go into Geant4-based GRAS for TID and TNID (SPC;
   arXiv:2411.00607v2 (3 Apr 2025), secs. 2 and 3.2, pp. 3-4 and 7). A TID-only prediction misses displacement damage (TNID), and one without trapped electrons misses their dose: state TNID (protons dominate it in the example), and compute the electron dose or add its bounding share, with at least the factor of two above on both models (more for differential spectra), to the TID as a one-sided upward term, neglected only below the dose's own statistical and transport uncertainty (example above, at 1 sigma: 6.2% solar-minimum and 24% solar-maximum models, 41% with a factor of three, computed here).
4. **Extrapolation.** A measured ageing trend, extrapolated, says when simulation and reconstruction must model the
   reduced response (UGD; arXiv:2207.12982, sec. 7, p. 31).

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| silicon leakage current | fluence per interval, annealing model fitted to currents | temperature log, depleted volume | NIEL factors for the wrong spectrum; warm-ups not logged | COL |
| charge collection loss | bias scans per period; damaged-sensor digitization | device model of the field | one constant per run range hides annealing | COL; SPC (design study) |
| LGAD gain loss | gain-versus-bias curves per fluence step; raise bias | single-event limit known | bias raised past the burnout limit | COL |
| SiPM dark rate | dark rate and threshold versus time; annealing; cooling; shielding | temperature recorded | threshold drift read as signal loss | COL, SPC |
| crystal or plastic transparency | monitoring light plus a physics or source reference | transfer exponent measured per producer (crystals) | monitor and scintillation light take different paths | COL |
| photosensor versus scintillator | compare a light-bypass monitor with source or physics response | both monitors in the same period | PMT fatigue and recovery read as scintillator damage | COL |
| MCP-PMT lifetime | QE scans versus integrated anode charge, partly covered cathode | rate and gain logged | time-driven loss (leaks) read as charge-driven | FXT |
| gas ageing | irradiation at the real rate, particle type and area; gain and current monitoring | final gas and materials | X-ray tests read as a lifetime for hadron fields | FXT, COL |

## Distinctive but generalizable features

- **Topology**: a slow per-channel drift under the event response.
- **Inverse problem**: separate dose, annealing, temperature and photosensor drift from one monitored response.
- **Natural objects**: per-channel monitored time series.
- **Informative residual**: monitored response minus the history-based prediction.
- **Scaling**: leakage current linear in `Phi_eq`; MCP and gas loss
  per integrated charge; plastic loss exponential in dose.
- **Conventions**: units and inputs of [Tool hooks](#tool-hooks); annealing state from per-interval temperature.
- **Tails**: dead channels, Malter discharges, sudden breakdown at the bias limit.
- **Dependence**: dose rate, temperature, gas flow and materials, solar cycle (SPC), luminosity (COL).
- **Data sample**: currents, monitoring light, stable peaks (resonances, MIPs,
  protons).
- **Transfers**: history-based conditions and two-monitor separation; **does not transfer**: laboratory
  ageing rates to another particle field.

## Common misconceptions and failure modes

- **Damage as a static constant.** It anneals, reverses and depends on temperature history.
- **One fluence number for all effects.** NIEL scaling is approximate beyond leakage current;
  surface damage follows TID, not `Phi_eq`. State the spectrum.
- **X-ray ageing tests as a lifetime.** Hadron fields can age faster.
- **All light loss as radiation damage.** Plastics age from humidity, stress and oxidation; PMTs fatigue and recover.
- **Collider phrasing elsewhere.** "Per fill" and "per luminosity" become orbit segments and SAA passages in SPC.

## Deliverables

- The damage history per channel group (fluence uniform within its uncertainty over a group; and the channel-to-group map): the inputs [Tool hooks](#tool-hooks) marks required, per interval, and the monitored response per channel.
- The history-to-response model, with source, validity and residual to monitored data.
- Time-dependent constants with intervals of validity, and the end-of-life extrapolation.
- For simulation: damaged-sensor digitization or response scaling, and its periods.

## Tool hooks

A damage-history tool (none shipped) takes the inputs below and the monitored response (optional); it outputs per interval the predicted leakage
current, LGAD gain, SiPM dark rate, MCP-PMT QE or response factor. Units, all required per interval:
fluence in `n_eq/cm^2` (silicon sensors, LGADs, SiPMs, hadron fluence for crystals), dose in Gy (those and crystals, plastics and WLS), each stated
even when zero (absent is not zero), with particle species and spectrum (and NIEL source for fluence) when non-zero, depleted volume `V_i` in cm^3 (silicon sensors, LGADs, SiPMs),
bias in V and gain (LGADs, SiPMs: gain multiplies the current), charge in C/cm^2 per area (MCP-PMT, micro-pattern gas, and any PMT, VPT or SiPM reading a dosed scintillator) or C/cm per wire (wire chambers) with the
geometry stated, with gain and photoelectron rate (MCP-PMT) and, for gas, current density, irradiated area, particle type and energy, gain, rate, gas mixture and materials,
time in s, temperature in K. Required negative control: a
history whose required fluence, dose and charge are all zero returns no radiation-induced change (zero is inside every relation's range), and a history with a warm-up returns the
annealing step. Statuses, first match wins: `missing-history` (an interval or a required input, temperature included, is absent), `no-dose-ageing` (the response changes while the sensor's required fluence, dose and charge are all zero), `no-predictor` (non-zero exposure and no relation in [Relations](#relations) for the output: LGAD gain, SiPM dark rate, MCP-PMT QE versus charge, WLS fibres, crystals without a monitored response, the PMT, VPT or SiPM of a dosed scintillator, gas outside the conditions of a cited ageing test, all gas inputs above), `extrapolated` (an input or the monitored response outside a relation's
fitted range or stated validity, such as a crystal transparency loss beyond it), `residual` (the monitored response differs from the prediction beyond its uncertainty, for example from non-dose ageing or PMT fatigue: report it), `ok`.

## Environment coverage

Cells credit the target detector's environment and mark lab, irradiation or beam-test (FXT) data.

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| silicon bulk and surface | arxiv_1905.03739 | gap | arxiv_1503.07682 (design study; irradiation) | gap | gap | gap |
| LGAD gain layer | arxiv_2004.05260 (irradiation) | gap | n/a: lifetime fluence far below acceptor removal (arxiv_1809.06361) | gap | gap | gap |
| SiPM | arxiv_1809.06361 | gap | arxiv_2411.00607 | gap | gap | gap |
| crystal scintillators | arxiv_1306.2016 (exponent: beam test) | gap | arxiv_1206.1896 | gap | gap | gap |
| plastic scintillator and WLS | arxiv_1806.02129 | gap | gap | arxiv_2207.12982 | gap | gap |
| MCP-PMT | gap (related: pdg_2025_particle-detectors-at-accelerators, principle only) | arxiv_2311.16676 (lab tests) | gap | gap | gap | gap |
| gas ageing | arxiv_hep-ex_0204005 (in situ and tests) | arxiv_hep-ex_0204005 | gap | gap | gap | gap |
| radiation fields | arxiv_1306.2016; arxiv_1905.03739 | gap | arxiv_2411.00607; arxiv_1503.07682; arxiv_1206.1896 (exposure only) | gap (arxiv_2207.12982: no identified dose) | gap | gap |
| conditions and simulation | arxiv_1905.03739; arxiv_1306.2016 | gap | arxiv_1206.1896; arxiv_2411.00607 | arxiv_2207.12982 | gap | gap |

## Citations

PDG: [the bibliography](detector-principles-bibliography.md), "General and cross-cutting"; the rest:
`detector-principles-bibliography-radiation.md`, "Radiation damage and ageing". Read dates: in the bibliography fragment (2026-11-19 to 2026-11-21), PDG 2026-10-14;
locators count PDF pages (PDG: the printed pages).
