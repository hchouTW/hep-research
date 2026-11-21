# Radiation and Ageing Effects

How sensors change with dose, fluence and accumulated charge, and how that enters conditions data and
simulation. Per sensor: silicon, LGADs, SiPMs, crystals, plastics and WLS, MCP-PMTs, gas;
then radiation fields.
Environments: COL collider, FXT fixed target and test beam, SPC space and balloon, UGD underground, neutrino
and rare event; GND (ground arrays) and NUC (nuclear) are gaps. Electronics damage (single-event upsets, circuit TID) is in
[front-end electronics](front-end-electronics-and-signal-processing.md#radiation-and-the-electronics).

## Relations

Fluence `Phi_eq` is the non-ionizing energy loss (NIEL) normalised to the damage of 1 MeV neutrons, in
`n_eq/cm^2`; total ionizing dose (TID) is in Gy, independent of particle type (definitions; PDG RPP 2025,
sec. 35.8.5, p. 74). Give both, with the particle spectrum they came from: NIEL scaling
holds well for leakage current and is "moderately violated" for other effects (same page).

| Relation | Label, validity and source |
|---|---|
| `Delta I_L = alpha_80 Phi_eq V`, `alpha_80 ≈ 4e-17 A/cm` at 20 °C after 80 min at 60 °C (not the `alpha_I` below) | approximate (NIEL hypothesis); `V` depleted volume; gain in the device multiplies it. PDG sec. 35.8.5, p. 74 |
| `I_L(T) ∝ T^2 exp(-E_a/(2kT))`, `E_a ≈ 1.2 eV` | approximate; PDG quotes about 7-fold from room temperature to 0 °C; for `E_a = 1.2 eV` the relation gives 6.6 from 20 °C and about 10 from 25 °C. PDG eq. (35.26), p. 74 |
| `N_id = N_id,0 exp(-c Phi_eq)` (initial dopant removal) | approximate; `c` depends on `N_id,0`, particle type and impurities (Fig. 35.32). PDG sec. 35.8.5, p. 76 |
| induced current times `exp(-t/tau_eff,e/h)`; `1/tau_eff ∝ Phi_eq` | approximate; linear up to about `1e15 n_eq/cm^2`, where `tau_eff` is of order 1 ns, then saturating. PDG p. 77 |
| bias limit from single-event effects at average fields near 12 V/um | approximate; sets the lifetime in highly energetic particle fields. PDG pp. 77-78 |
| `I_leak = (Phi/L_int) sum_i V_i L_int,i [alpha_I exp(-sum_{j>=i} t_j/tau(T_j)) + alpha_0* - beta ln(sum_{j>=i} Theta(T_j) t_j / t_0)]` | approximate (phenomenological annealing model); per interval `i` with luminosity, duration, temperature and depleted volume `V_i`; `alpha_I` is the short-term amplitude; currents scaled to 20 °C with `E_eff = 1.12 eV`, not the 1.2 eV above. arXiv:1905.03739, sec. 3.1, eqs. (1)-(2), pp. 5-6 |
| `L/L_0 ≈ exp(-D/D_c)` for plastic scintillator | approximate; `D_c` of tens of kGy at dose rates from a few `1e-3` to 10 Gy/h, larger damage at lower rate. PDG sec. 35.3.2, p. 12 |
| `S(t)/S_0 = (R(t)/R_0)^alpha` (scintillation versus monitoring-light response) | approximate, for small transparency losses; `alpha` differs between crystal producers (initial transparency), with a channel spread, measured in a beam test under irradiation; a value tuned in situ is an effective exponent for large losses that also absorbs photosensor (VPT) loss, outside this validity. arXiv:1306.2016, sec. 4.1, eq. (3), pp. 10-11, and sec. 4.1.1, p. 12 |
| `s(t) = (p_0 - p_1) + p_1 exp(-(t - t_0)/tau)` (energy-scale drift) | approximate, empirical fit to a monitored peak. arXiv:1206.1896, sec. 7.3.2, eq. (53), p. 137 |
| `R = -(1/G) dG/dQ` (% per C/cm) | definition of the gas ageing rate; **not** a predictor at high rate, where ageing is not a function of `Q` alone. arXiv:hep-ex/0204005, sec. I, p. 1 |
| `Q_A = r_pe T f_duty G e` (integrated anode charge per area) | exact bookkeeping for a constant photoelectron rate `r_pe` per area, run time `T`, duty factor, gain `G`; a photon rate not stated as incident or detected, taken as `r_pe`, gives an upper bound (`r_pe` = DQE × incident rate): state which |

## Damage and ageing by sensor

**Silicon (bulk and surface).** Bulk damage (displaced atoms) raises the leakage current, traps carriers and builds
space charge that changes the depletion voltage; surface damage (oxide charge, interface traps) scales with TID and
raises surface currents and changes inter-electrode isolation (PDG sec. 35.8.5, p. 74). Damage changes with time:
beneficial annealing first, then reverse annealing over months at room temperature and much longer when cold; n-type
bulk inverts, p-type with n+ readout does not, and is preferred because electrons are collected (pp. 75-76).
Operating temperature and warm-ups are therefore part of the damage history (p. 78). Related:
[tracking and vertexing](tracking-and-vertexing.md). The same holds in low Earth orbit, where a
design study took trapped protons only (SPC; arXiv:1503.07682, abstract; sec. 1, p. 3).

<!-- example: ATLAS pixel detector (COL) and LOFT silicon drift detectors (SPC design study) -->
ATLAS pixel (arXiv:1905.03739): the current detector will receive more than `1e15` 1 MeV `n_eq/cm^2`, the HL-LHC
detector an order of magnitude more (abstract); eq. (1) has the short-term amplitude `alpha_I = (1.23 ± 0.06)e-17
A/cm` (not `alpha_80`) with `alpha_0* = 7.07e-17 A/cm` and `beta = (3.29 ± 0.18)e-18 A/cm` (sec. 3.1, pp. 5-6): with its
`tau(T)` and `Theta(T)`, the bracket is about `4.1e-17 A/cm` after 80 min at 60 °C (central values, `T_ref` = 20 °C, natural log, `3.2e-17` to `5.2e-17` over the quoted ranges, computed here), the `alpha_80` above. LOFT SDDs (arXiv:1503.07682): displacement damage from trapped protons
reduces the charge collection efficiency, measured with protons against the expected
in-orbit damage (abstract; sec. 1, p. 3).
<!-- /example -->

**LGAD.** The highly doped gain layer loses acceptors with fluence, so gain drops sharply (PDG p. 77); raising
the bias recovers part of it, until the single-event limit above. Deeper gain layers (stronger recovery with
bias) and carbon in the gain layer (fewer interstitials that remove boron) are the mitigations (arXiv:2004.05260,
secs. 1-2, pp. 1-2). This is a **single-environment** technique (COL): acceptor removal is measured at the
fluences of hadron-collider timing layers (example below), while the lifetime fluence a SiPM review gives for
space detectors is below 1e12 particles/cm^2 as quoted, not NIEL-weighted (arXiv:1809.06361, sec. 1, p. 1).
Timing consequences: [timing detectors](timing-detectors.md).

<!-- example: LGAD prototypes for the HL-LHC timing layers (ATLAS HGTD, CMS ETL; COL) -->
arXiv:2004.05260: 50 um HPK and 55 um FBK LGADs (abstract; Table 1, p. 2), neutron-irradiated from `4e14` to `4e15 n_eq/cm^2`, measured at
-30 °C; the deep and the carbonated gain layers perform reasonably up to `3e15`; time resolution versus
gain does not depend on fluence for the same thickness (abstract); requirements up to a few `1e15 n_eq/cm^2` and a
few MGy (sec. 1, p. 1).
<!-- /example -->

**SiPM.** The dominant effect is the rise in dark count rate, which first destroys single-photoelectron resolution
(arXiv:1809.06361, abstract). Pixel occupancy from dark counts then lowers the effective photon detection
efficiency and gain (eq. (10), p. 11). The fluence at which single photoelectrons are lost depends on design and
temperature: test it per application; annealing (room temperature, or high temperature with forward
bias) recovers part of it (secs. 3.4 and 6, pp. 12 and 15). With a scintillator, the rising dark rate raises the
energy threshold (SPC; arXiv:2411.00607, abstract).

<!-- example: GRBAlpha and VZLUSAT-2 CubeSats, Hamamatsu S13360-3050PE MPPCs (SPC) -->
arXiv:2411.00607: GRBAlpha, 550 km sun-synchronous orbit, CsI(Tl) read by eight MPPCs behind 2-2.5 mm PbSb: the
low-energy threshold rose from about 20 keV to about 120 keV in 3 years 5 months, matching a simulated TID of 1.6
Gy (160 rad) and `2.1e9 n_eq/cm^2` from trapped protons (AP-8) (abstract; sec. 6, p. 14).
<!-- /example -->

**Crystal scintillators.** Ionizing dose forms colour centres; the induced absorption shortens the attenuation
length, lowers light output and distorts light-response uniformity, which degrades resolution; hadrons add
displacement and fission-fragment damage (PDG sec. 35.4, p. 18). Damage and spontaneous recovery compete, so the
loss depends on dose rate; injected monitoring light tracks it (COL; arXiv:1306.2016, sec. 3, p. 8).

<!-- example: CMS ECAL PbWO4 (COL) and the Fermi LAT CsI(Tl) calorimeter (SPC) -->
CMS ECAL (arXiv:1306.2016): laser light into each crystal; by the end of 2011 the average laser response
dropped 2-3% in the barrel and 40% at 2.7 ≤ |eta| ≤ 3.0 in the endcap, there partly from VPT loss (sec.
3, p. 8); `alpha` of eq. (3) is 1.52 and 1.0 for the two crystal producers, BTCP and SIC, with a 10% spread, from a
beam test (sec. 4.1, pp. 10-11); an effective 1.16 is used for the endcap BTCP crystals, tuned on Z to ee events, absorbing the VPT loss
(sec. 4.1.1, p. 12). Fermi LAT (arXiv:1206.1896): light yield fell about 1% per year over its first three
years in orbit (sec. 2.1.2, p. 20).
<!-- /example -->

**Plastic scintillator and WLS fibres.** Radiation yellows the plastic and lowers its transparency; damage per dose
is larger at low dose rate, and the transparency partly recovers after irradiation, faster with oxygen (PDG sec.
35.3.2, p. 12). Plastics also age **without dose**: crazing under mechanical stress or solvents, and fogging from
humidity at elevated temperature (same page); for a measured long-term loss the cause can stay unknown, with
photochemical oxidation a further candidate (arXiv:2207.12982, sec. 1.2, pp. 7-8). Separate the causes with two
monitors that see different parts of the chain: a light source that bypasses the scintillator sees the photosensor,
a radioactive source or physics signal sees both (COL; arXiv:1806.02129, sec. 4.5, p. 24).

<!-- example: ATLAS Tile Calorimeter (COL) and T2K near detectors (UGD) -->
TileCal (arXiv:1806.02129, sec. 4.5, pp. 23-24): the difference between minimum-bias (or Cs) and laser response is
read as scintillator irradiation, while laser data alone show PMT gain loss with light exposure and recovery
when there are no collisions. T2K near detectors (arXiv:2207.12982): light yield fell 0.9-2.2% per year over ten years (abstract,
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
about 200 kHz/cm^2 (incident or detected is not stated), 10 years, 50% duty and gain `1e6` give an expected
charge of about 5 C/cm^2 for the Barrel DIRC (sec. 1, p. 1; the upper bound of the relation above gives 5.1
C/cm^2); a tube with two ALD layers reached more than 34 C/cm^2 of anode charge with no QE loss yet (sec. 2.1,
p. 2).
<!-- /example -->

**Gaseous detectors.** Avalanche plasma chemistry forms deposits on electrodes, from hydrocarbon quenchers and from
outgassing insulators, glues and oils; strict materials and gas control allow several C/cm^2 without observable
ageing (PDG sec. 35.6.2.4, p. 33). An insulating cathode layer can ignite the self-sustained Malter discharge;
ageing depends on gas, materials, irradiated area, current density, gain, rate, particle type and energy, so
laboratory tests with X-ray sources may not transfer to a hadron environment (arXiv:hep-ex/0204005, secs. II.A
and V.D, pp. 2 and 8). Drift chambers: [gaseous and specialized tracking
technologies](gaseous-and-specialized-tracking-technologies.md#drift-chambers-and-drift-tubes).

<!-- example: HERA-B honeycomb drift tubes and muon chambers (FXT) -->
arXiv:hep-ex/0204005, sec. V.D, pp. 8-9: prototype honeycomb drift tubes aged severely after a few mC/cm in the hadron
environment of 920 GeV protons on a nuclear target, though X-ray tests to 5 C/cm showed nothing; in the muon
proportional chambers the ageing rate in Ar/CF4/CH4 was more than two orders of magnitude higher in hadron beams than with radioactive sources.
<!-- /example -->

## Radiation fields by environment

- **COL.** Dose and hadron fluence depend on position (radius, pseudorapidity) and scale with integrated luminosity;
  the fluence comes from an event generator plus particle transport (Pythia8, FLUKA) as a factor `Phi/L_int`, validated per
  module group against the measured leakage current through the annealing model, FLUKA kept for the central value with a 15% uncertainty: the data show a stronger `z`-dependence,
  FLUKA about 1.5 sigma off at `z = 0` and more at larger `|z|` (arXiv:1905.03739, secs. 2-3.1, pp. 3-7).
- **SPC (low Earth orbit).** The proton/electron balance depends on shielding and spectrum (example below), so
  model trapped electrons too; solar protons and Galactic cosmic rays add little TID (arXiv:2411.00607, sec. 4.1,
  p. 10). Dose depends on altitude, shielding and solar cycle (same page), from trapped-particle models (AP-8 protons,
  AE-8 electrons), with a quoted factor-of-two uncertainty on the AP-8 proton flux (sec. 3.2, p. 7); the paper quotes
  none for AE-8, so assign one. In AP-8, trapped protons at low altitude are more numerous at
  solar minimum (arXiv:1503.07682, sec. 1, p. 3; and arXiv:2411.00607, sec. 4.1, p. 10). Cutoff
  handling is in [space-based direct detection](space-based-direct-detection.md#geomagnetic-cutoff).
- **UGD.** The measured ageing of one accelerator-neutrino near detector's plastic scintillator has no identified cause (arXiv:2207.12982, sec. 1.2, pp. 7-8).
  No underground radiation-damage source is cited (gap). Detector context:
  [noble liquid, neutrino and rare-event detectors](noble-liquid-neutrino-and-rare-event-detectors.md).

<!-- example: CMS ECAL (COL), LOFT, Fermi and GRBAlpha orbits (SPC) -->
CMS ECAL: expected dose up to 4 kGy in the barrel and 200 kGy at |eta| = 3 after 10 years (500 fb^-1); expected
hadron fluence from about `1e13` to `1e14 cm^-2`, as quoted (weighting and NIEL source not stated;
arXiv:1306.2016, sec. 2, p. 6). LOFT: AP8-MIN via SPENVIS, 600 km and 5° worst case, behind 3.3 mm Al equivalent;
AP8-MIN is about 7 times AP8-MAX at 1 MeV (arXiv:1503.07682, sec. 1, p. 3). Fermi: 565 km at 25.6°, about 15% of the
time in the SAA, with science data suspended there (arXiv:1206.1896, sec. 2.2, p. 25). GRBAlpha: behind 2-2.5 mm
PbSb, trapped protons dominate TID and TNID, electrons 1-6% of TID (computed here from `TID(p)/TID(e)`:
1.3% at ~550 km, solar minimum, 74 ± 14; 5.8% at ~475 km, solar maximum, 16.1 ± 3.4; arXiv:2411.00607, sec. 4.1, p. 10).
<!-- /example -->

## Feeding damage into conditions and simulation

1. **Conditions.** Store the damage history, not a constant: per interval its duration, fluence (from
   `Phi/L_int` or orbit segments, with NIEL source), TID, anode charge (MCP-PMT, gas), temperature, bias, depleted volume (silicon), and the
   monitored response. Derived constants (depletion voltage, trapping,
   threshold, light-yield factor `S_i(t)`, energy-scale drift) are payloads with intervals of validity
   ([calibration and alignment](calibration-and-alignment.md#time-dependence-and-conditions-data)). The light
   monitor corrects each channel by the transfer relation (COL; arXiv:1306.2016, sec. 4.1, p. 10); in orbit a
   stable peak (non-interacting protons) tracks the scale, fitted in time (arXiv:1206.1896, sec. 7.3.2, p. 137).
2. **Digitization.** Digitize with device-model fields and trapping; state whether annealing enters. One collider
   pixel digitizer omits annealing (COL; arXiv:1905.03739, sec. 4, pp. 12-30; sec. 2, pp. 4-5). The annealing model only
   validates the conditions (fluence, depletion voltage; sec. 3) and does not enter the simulated response. No
   annealing correction or uncertainty is applied (sec. 2, p. 5; sec. 4.2.4, p. 20, checked at `1e14` and `2e14 n_eq/cm^2`,
   to be revisited after significant annealing): its variation lies within the field-model variations of sec. 4.2.3
   and the trapping-constant range (sec. 4.5 and Table 5,
   p. 24), so it holds at those fluences only. General digitization:
   [detector simulation](detector-simulation.md#digitization).
3. **Dose prediction.** Pre-launch shielding was studied with Geant4-based MULASSIS on two 500 km orbits, TID
   only and without electrons (protons, and cosmic-ray 2H, 3He, 4He), thickness set by CubeSat mass and volume,
   and in orbit AE-8 electron and AP-8 proton fluences per mission segment (IRENE) go into Geant4-based GRAS for TID and TNID (SPC;
   arXiv:2411.00607, secs. 2 and 3.2, pp. 3-4 and 7). A protons-only TID prediction misses electrons and displacement damage.
4. **Extrapolation.** A measured ageing trend, extrapolated, says when simulation and reconstruction must model the
   reduced response (UGD; arXiv:2207.12982, sec. 7, p. 31).

<!-- example: Fermi LAT calorimeter energy scale (SPC) -->
arXiv:1206.1896, sec. 7.3.2, p. 137: eq. (53) fitted to the proton-peak position gives `tau` of about 2 years and a
correctable energy-scale shift of about 4.5% after 10 years.
<!-- /example -->

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| silicon leakage current versus time | fluence per luminosity through the annealing model, fitted to measured currents | temperature log, depleted volume | NIEL factors for the wrong spectrum; warm-ups not logged | COL |
| charge collection loss | bias scans per period; damaged-sensor digitization | device model of the field | one constant per run range hides annealing | COL; SPC (design study: ground tests) |
| LGAD gain loss | gain-versus-bias curves per fluence step; raise bias | single-event limit known | bias raised past the burnout limit | COL |
| SiPM dark rate | dark rate and threshold versus time; annealing; cooling; shielding | temperature recorded | threshold drift read as signal loss | COL, SPC |
| crystal or plastic transparency | monitoring light plus a physics or source reference | transfer exponent measured per producer (crystals) | monitor and scintillation light take different paths | COL |
| photosensor versus scintillator | compare a light-bypass monitor with source or physics response | both monitors in the same period | PMT fatigue and recovery read as scintillator damage | COL |
| MCP-PMT lifetime | QE scans versus integrated anode charge, partly covered cathode | rate and gain logged | time-driven loss (leaks) read as charge-driven | FXT |
| gas ageing | irradiation at the real rate, particle type and area; gain and current monitoring | final gas and materials | X-ray tests read as a lifetime for hadron fields | COL, FXT |

## Distinctive but generalizable features

- **Topology**: a slow per-channel drift under the fast event response.
- **Inverse problem**: separate dose, annealing, temperature and photosensor drift from one monitored response.
- **Natural objects**: per-channel time series of leakage current, gain, dark rate and monitoring response.
- **Informative residual**: monitored response minus the history-based prediction.
- **Scaling**: leakage current linear in `Phi_eq`; trapping rate linear to about `1e15 n_eq/cm^2`; MCP and gas loss
  per integrated charge; plastic loss exponential in dose.
- **Conventions**: `n_eq/cm^2`, Gy, C/cm^2 per area or C/cm per wire, each with the inputs [Tool hooks](#tool-hooks) marks required, and the
  annealing state.
- **Tails**: dead channels, Malter discharges, sudden breakdown at the bias limit.
- **Dependence**: dose rate, temperature, gas flow and materials, solar cycle (SPC), luminosity (COL).
- **Data sample**: currents, monitoring light, stable physics peaks (resonances, MIPs, non-interacting
  protons).
- **Transfers**: the history-based conditions and the two-monitor separation to every sensor; **does not
  transfer**: laboratory ageing rates to a different particle field.

## Common misconceptions and failure modes

- **Damage as a static constant.** It anneals, reverses and depends on temperature history.
- **One fluence number for all effects.** NIEL scaling is approximate beyond leakage current;
  surface damage follows TID, not `Phi_eq`. State the spectrum.
- **X-ray ageing tests as a lifetime.** Hadron fields can age faster.
- **All light loss as radiation damage.** Plastics age from humidity, stress and oxidation; PMTs fatigue and recover.
- **Collider phrasing elsewhere.** "Per fill" and "per luminosity" become orbit segments and SAA passages in SPC.

## Deliverables

- The damage history: exposure per channel group, monitored response per channel (feeding item 1).
- The history-to-response model, with source, validity and residual to monitored data.
- Time-dependent constants with intervals of validity, and the end-of-life extrapolation.
- For simulation: damaged-sensor digitization or response scaling, and the periods it covers.

## Tool hooks

A damage-history tool (none shipped) would take per-interval duration, temperature, fluence and dose or anode charge (MCP-PMT, gas), bias, and the monitored response (optional); output per interval the predicted leakage
current, depletion voltage or response factor. Units:
fluence in `n_eq/cm^2` (NIEL source and particle spectrum required when non-zero), dose in Gy (required with
fluence for silicon sensors, LGADs and SiPMs included), depleted volume `V_i` in cm^3 (required for leakage current), bias in V,
charge in C/cm^2 per area (MCP-PMT, micro-pattern gas) or C/cm per wire (wire chambers) with the
geometry stated and, for gas, required current density, irradiated area, particle type and energy, gain, rate, gas mixture and materials,
time in s, temperature in K (required per interval). Required negative control: a
history with zero fluence, dose and charge returns no radiation-induced change (ageing without dose is `no-dose-ageing`), and a history with a warm-up returns the
annealing step. Statuses: `ok`, `extrapolated` (an input outside a valid relation's
fitted range), `missing-history` (an interval or any input marked required above, such as its temperature, is absent), `no-predictor` (no validated relation, preceding `extrapolated`: gas outside the current density, area and particle field of a cited ageing test, as no high-rate threshold is given), `no-dose-ageing` (the monitored response changes while fluence, dose and charge are zero).

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| silicon bulk and surface | pdg_2025_particle-detectors-at-accelerators; arxiv_1905.03739 | gap | arxiv_1503.07682 (design study: ground proton tests) | gap | gap | gap |
| LGAD gain layer | pdg_2025_particle-detectors-at-accelerators; arxiv_2004.05260 | gap | n/a: lifetime fluence far below acceptor removal (arxiv_1809.06361) | gap | gap | gap |
| SiPM | arxiv_1809.06361 | gap | arxiv_2411.00607 | gap | gap | gap |
| crystal scintillators | pdg_2025_particle-detectors-at-accelerators; arxiv_1306.2016 | gap | arxiv_1206.1896 | gap | gap | gap |
| plastic scintillator and WLS | pdg_2025_particle-detectors-at-accelerators; arxiv_1806.02129 | gap | gap | arxiv_2207.12982 | gap | gap |
| MCP-PMT | gap: generic principle only (pdg_2025_particle-detectors-at-accelerators) | arxiv_2311.16676 (laboratory illumination tests for a planned experiment) | gap | gap | gap | gap |
| gas ageing | pdg_2025_particle-detectors-at-accelerators; arxiv_hep-ex_0204005 | arxiv_hep-ex_0204005 | gap | gap | gap | gap |
| radiation fields | arxiv_1306.2016; arxiv_1905.03739 | gap | arxiv_2411.00607; arxiv_1503.07682; arxiv_1206.1896 (orbit and SAA exposure only) | gap: ageing without an identified dose only (arxiv_2207.12982) | gap | gap |
| conditions and simulation | arxiv_1905.03739; arxiv_1306.2016 | gap | arxiv_1206.1896; arxiv_2411.00607 | arxiv_2207.12982 | gap | gap |

## Citations

PDG: [the bibliography](detector-principles-bibliography.md), "General and cross-cutting"; the rest:
`detector-principles-bibliography-radiation.md`, "Radiation damage and ageing". Read 2026-11-19;
locators count PDF pages (PDG: the printed pages).
