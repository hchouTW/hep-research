# Radiation and Ageing Effects

How sensors change with dose, fluence and accumulated charge, and how that change enters conditions data and
simulation. Per sensor: silicon (bulk and surface damage), LGAD gain layers, SiPMs, crystal scintillators, plastic
scintillator and WLS fibres, MCP-PMTs, and gaseous detectors. Then radiation fields per environment.
Environment codes: COL collider; FXT fixed-target and test beam;
SPC space and balloon; UGD underground, neutrino and rare-event; GND ground-based arrays; NUC nuclear and
low-energy. Sourced here: COL, FXT, SPC, UGD (UGD only for scintillator ageing of
unknown cause); GND and NUC are gaps (coverage table). Damage of the front-end electronics (single-event upsets, total
ionizing dose in circuits) is in
[front-end electronics](front-end-electronics-and-signal-processing.md#radiation-and-the-electronics).

## Relations

Fluence `Phi_eq` is the non-ionizing energy loss (NIEL) normalised to the damage of 1 MeV neutrons, in
`n_eq/cm^2`; total ionizing dose (TID) is in Gy, independent of particle type (definitions; PDG RPP 2025,
sec. 35.8.5, p. 74). Give both, with the particle spectrum they came from: NIEL scaling
holds well for leakage current and is "moderately violated" for other effects (same page).

| Relation | Label, validity and source |
|---|---|
| `Delta I_L = alpha_I Phi_eq V`, `alpha_I ≈ 4e-17 A/cm` at 20 °C after 80 min at 60 °C | approximate (NIEL hypothesis); `V` depleted volume; gain in the device multiplies it. PDG sec. 35.8.5, p. 74 |
| `I_L(T) ∝ T^2 exp(-E_a/(2kT))`, `E_a ≈ 1.2 eV` | approximate; PDG quotes about 7-fold from room temperature to 0 °C; for `E_a = 1.2 eV` the relation gives 6.6 from 20 °C and about 10 from 25 °C. PDG eq. (35.26), p. 74 |
| `N_id = N_id,0 exp(-c Phi_eq)` (initial dopant removal) | approximate; `c` depends on `N_id,0`, particle type and impurities (Fig. 35.32). PDG sec. 35.8.5, p. 76 |
| induced current times `exp(-t/tau_eff,e/h)`; `1/tau_eff ∝ Phi_eq` | approximate; linear up to about `1e15 n_eq/cm^2`, where `tau_eff` is of order 1 ns, then saturating. PDG p. 77 |
| bias limit from single-event effects at average fields near 12 V/um | approximate; sets the sensor lifetime. PDG pp. 77-78 |
| `I_leak = (Phi/L_int) sum_i V_i L_int,i [alpha_I exp(-sum_{j>=i} t_j/tau(T_j)) + alpha_0* - beta ln(sum_{j>=i} Theta(T_j) t_j / t_0)]` | approximate (phenomenological annealing model); per time interval `i` with luminosity, duration and temperature. arXiv:1905.03739, sec. 3.1, eq. (1), p. 5 |
| `L/L_0 ≈ exp(-D/D_c)` for plastic scintillator | approximate; `D_c` of tens of kGy at dose rates from a few `1e-3` to 10 Gy/h, larger damage at lower rate. PDG sec. 35.3.2, p. 12 |
| `S(t)/S_0 = (R(t)/R_0)^alpha` (scintillation versus monitoring-light response) | approximate, for small transparency losses, where `alpha` does not depend on the loss; `alpha` differs between producers of the same crystal (set by the initial transparency), with a channel-to-channel spread, measured in a beam test under irradiation. A value tuned in situ on collision data is an effective exponent for large losses that also absorbs photodetector loss, outside this validity. arXiv:1306.2016, sec. 4.1, eq. (3), pp. 10-11, and sec. 4.1.1, p. 12 |
| `s(t) = (p_0 - p_1) + p_1 exp(-(t - t_0)/tau)` (energy-scale drift) | approximate, empirical fit to a monitored peak. arXiv:1206.1896, sec. 7.3.2, eq. (53), p. 137 |
| `R = -(1/G) dG/dQ` (% per C/cm) | definition of the gas ageing rate; **not** a predictor at high rate, where ageing is not a function of `Q` alone. arXiv:hep-ex/0204005, sec. I, p. 1 |
| `Q_A = r_pe T f_duty G e` (integrated anode charge per area) | exact bookkeeping for a constant photoelectron rate `r_pe` per area, run time `T`, duty factor, gain `G`; the "photon rate" of arXiv:2311.16676 (sec. 1, p. 1), used for its charge budget, is not stated as incident or detected; take a quoted rate as `r_pe` unless known to be incident |

## Damage and ageing by sensor

**Silicon (bulk and surface).** Bulk damage (displaced atoms) raises the leakage current, traps carriers and builds
space charge that changes the depletion voltage; surface damage (oxide charge, interface traps) scales with TID and
raises surface currents and changes inter-electrode isolation (PDG sec. 35.8.5, p. 74). Damage changes with time:
beneficial annealing first, then reverse annealing over months at room temperature and much longer when cold; n-type
bulk inverts, p-type with n+ readout does not, and is preferred because electrons are collected (pp. 75-76).
Operating temperature and warm-up periods are therefore part of the damage history (p. 78). The full-depletion
relation and the Lorentz angle are in [tracking and vertexing](tracking-and-vertexing.md); leakage-current noise in
[front-end electronics](front-end-electronics-and-signal-processing.md). The same mechanisms apply in orbit, where
the fluence comes from trapped protons (SPC; arXiv:1503.07682, abstract).

<!-- example: ATLAS pixel detector (COL) and LOFT silicon drift detectors (SPC design study) -->
ATLAS pixel (arXiv:1905.03739): the current detector will receive more than `1e15` 1 MeV `n_eq/cm^2`, the HL-LHC
detector an order of magnitude more (abstract); the annealing model of eq. (1) uses `alpha_I = (1.23 ± 0.06)e-17
A/cm` (sec. 3.1, p. 5). LOFT SDDs (arXiv:1503.07682): displacement damage from protons trapped in the
magnetosphere reduces the charge collection efficiency, measured with protons and compared with the expected
in-orbit damage (abstract; sec. 1, p. 3).
<!-- /example -->

**LGAD.** The highly doped gain layer loses acceptors with fluence, so gain drops sharply (PDG p. 77); raising
the bias recovers part of it, until the single-event limit above. Deeper gain layers (stronger recovery with
bias) and carbon in the gain layer (fewer interstitials that remove boron) are the mitigations (arXiv:2004.05260,
secs. 1-2, pp. 1-2). This is a **single-environment** technique (COL): acceptor removal is measured at the
fluences of hadron-collider timing layers (example below), while the lifetime fluence a SiPM review gives for
space detectors is below `1e12 /cm^2` (arXiv:1809.06361, sec. 1, p. 1).
Timing consequences: [timing detectors](timing-detectors.md).

<!-- example: LGAD prototypes for the HL-LHC timing layers (ATLAS HGTD, CMS ETL; COL) -->
arXiv:2004.05260: 50 um HPK and 55 um FBK LGADs, neutron-irradiated from `4e14` to `4e15 n_eq/cm^2`, measured at
-30 °C; the deep gain layer and the carbonated gain layer perform reasonably up to `3e15`; time resolution versus
gain does not depend on fluence for the same thickness (abstract); requirements up to a few `1e15 n_eq/cm^2` and a
few MGy (sec. 1, p. 1).
<!-- /example -->

**SiPM.** The dominant effect is the rise in dark count rate, which first destroys single-photoelectron resolution
(arXiv:1809.06361, abstract). Pixel occupancy from dark counts then lowers the effective photon detection
efficiency and gain (eq. (10), p. 11). The fluence at which single photoelectrons are lost depends on design and
temperature and must be tested for each application; annealing (room temperature, or high temperature with forward
bias) recovers part of it (secs. 3.4 and 6, pp. 12 and 15). With a scintillator, the rising dark rate raises the
energy threshold (SPC; arXiv:2411.00607, abstract).

<!-- example: GRBAlpha and VZLUSAT-2 CubeSats, Hamamatsu S13360-3050PE MPPCs (SPC) -->
arXiv:2411.00607: GRBAlpha, 550 km sun-synchronous orbit, CsI(Tl) read by eight MPPCs behind 2-2.5 mm PbSb: the
low-energy threshold rose from about 20 keV to about 120 keV in 3 years 5 months, matching a simulated TID of 1.6
Gy (160 rad) and `2.1e9 n_eq/cm^2` from trapped protons (AP-8) (sec. 6, p. 14).
<!-- /example -->

**Crystal scintillators.** Ionizing dose forms colour centres; the induced absorption shortens the attenuation
length, lowers light output and distorts light-response uniformity, which degrades resolution; hadrons add
displacement and fission-fragment damage (PDG sec. 35.4, p. 18). Damage and spontaneous recovery compete, so the
loss depends on dose rate; injected monitoring light tracks it (COL; arXiv:1306.2016, sec. 3, p. 8).

<!-- example: CMS ECAL PbWO4 (COL) and the Fermi LAT CsI(Tl) calorimeter (SPC) -->
CMS ECAL (arXiv:1306.2016): laser at 440 nm into each crystal; by the end of 2011 the response to laser light
dropped 2-3% in the barrel and up to 40% at 2.7 ≤ |eta| ≤ 3.0, with partial recovery in low-luminosity running (sec.
3, p. 8); `alpha` of eq. (3) is 1.52 and 1.0 for the two crystal producers, BTCP and SIC, with a 10% spread, from a
beam test (sec. 4.1, pp. 10-11); an effective 1.16 is used for the endcap BTCP crystals, tuned on Z to ee events
(sec. 4.1.1, p. 12). Fermi LAT (arXiv:1206.1896): a slow (about 1% per year over its first three years of
operation) decrease of the light yield in low Earth orbit (sec. 2.1.2, p. 20).
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
between fills. T2K near detectors (arXiv:2207.12982): light yield fell 0.9-2.2% per year over ten years (abstract,
p. 5); most of the loss is in the scintillator, not the WLS fibres, whose long attenuation component degrades by
1-5% per year (sec. 7, p. 31).
<!-- /example -->

**MCP-PMT.** Ions fed back from residual gas damage the photocathode, so quantum efficiency falls with integrated
anode charge; atomic-layer-deposition (ALD) coatings of the channels raise the lifetime above 20 C/cm^2 of anode
charge (PDG sec. 35.2.1.2, pp. 5-6; arXiv:2311.16676, sec. 1, p. 1). Lifetime tests illuminate at a known rate,
log the anode charge and scan QE; a covered part of the photocathode separates charge-driven loss from loss with
time alone, such as vacuum micro-leaks (arXiv:2311.16676, sec. 2.1, p. 2). Lifetime source: FXT only; the rest
are gaps.

<!-- example: PANDA Barrel and Endcap Disc DIRC MCP-PMTs (FXT) -->
arXiv:2311.16676: before ALD the QE dropped by a factor of 2 or more after a few hundred mC/cm^2; a photon rate of
about 200 kHz/cm^2 (incident or detected is not stated), 10 years, 50% duty and gain `1e6` give an expected
charge of about 5 C/cm^2 for the Barrel DIRC (sec. 1, p. 1; the relation above, with that rate as `r_pe`, gives 5.1
C/cm^2); a tube with two ALD layers reached more than 34 C/cm^2 of anode charge with no QE loss yet (sec. 2.1,
p. 2).
<!-- /example -->

**Gaseous detectors.** Avalanche plasma chemistry forms deposits on electrodes, from hydrocarbon quenchers and from
outgassing insulators, glues and oils; strict materials and gas control allow several C/cm^2 without observable
ageing (PDG sec. 35.6.2.4, p. 33). An insulating cathode layer can ignite the self-sustained Malter discharge;
ageing depends on gas, materials, irradiated area, current density, gain, rate, particle type and energy, so
laboratory tests with X-ray sources may not transfer to a hadron environment (arXiv:hep-ex/0204005, secs. II.A
and V.D, pp. 2 and 8). Drift-chamber operation and calibration: [gaseous and specialized tracking
technologies](gaseous-and-specialized-tracking-technologies.md#drift-chambers-and-drift-tubes).

<!-- example: HERA-B honeycomb drift tubes and muon chambers (FXT) -->
arXiv:hep-ex/0204005, sec. V.D, pp. 8-9: prototype honeycomb drift tubes aged severely after a few mC/cm in the hadron
environment of 920 GeV protons on a nuclear target, though X-ray tests to 5 C/cm showed nothing; the ageing rate
in Ar/CF4/CH4 was more than two orders of magnitude higher in hadron beams than with radioactive sources.
<!-- /example -->

## Radiation fields by environment

- **COL.** Dose and hadron fluence depend on position (radius, pseudorapidity) and scale with integrated luminosity;
  the fluence comes from an event generator plus particle transport, as a factor `Phi/L_int`, checked against the
  measured leakage current through the annealing model (arXiv:1905.03739, secs. 2-3.1, pp. 4-5).
- **SPC (low Earth orbit).** The proton/electron balance depends on shielding and spectrum: behind the 2-2.5 mm PbSb
  (about 2.2-2.8 g/cm^2) of the cited CubeSat detector trapped protons dominate TID and NIEL; for lighter
  shielding (in g/cm^2) model trapped electrons too;
  solar protons and Galactic cosmic rays add little TID (arXiv:2411.00607, sec. 4.1, p. 10). Dose
  depends on altitude, shielding and solar cycle (same page), from trapped-particle models (AP-8 protons, AE-8
  electrons), with a quoted factor-of-two uncertainty on the AP-8 proton flux (sec. 3.2, p. 7); none is
  quoted for AE-8, which does not make it exact. In AP-8, trapped protons at low altitude are more numerous at
  solar minimum (AP8-MIN above AP8-MAX; arXiv:1503.07682, sec. 1, p. 3; and arXiv:2411.00607, sec. 4.1, p. 10). For
  the low-inclination orbit of the cited drift-detector study, protons dominate, especially those trapped in the
  South Atlantic Anomaly (arXiv:1503.07682, sec. 1, citing its Ref. [11], p. 3; no fraction given). Cutoff
  handling is in [space-based direct detection](space-based-direct-detection.md#geomagnetic-cutoff).
- **UGD.** The measured ageing of neutrino-detector scintillator has no identified cause (candidates under
  plastic scintillator above; arXiv:2207.12982, sec. 1.2, pp. 7-8).
  No radiation-field or radiation-damage source for underground sensors is
  cited here (coverage gap). Detector context:
  [noble liquid, neutrino and rare-event detectors](noble-liquid-neutrino-and-rare-event-detectors.md).

<!-- example: CMS ECAL (COL), LOFT and Fermi orbits (SPC) -->
CMS ECAL: expected dose up to 4 kGy in the barrel and 200 kGy at |eta| = 3 after 10 years (500 fb^-1); expected
hadron fluence from about `1e13` to `1e14 cm^-2`, as quoted (weighting and NIEL source not stated;
arXiv:1306.2016, sec. 2, p. 6). LOFT: AP8-MIN via SPENVIS, 600 km and 5° worst case, behind 3.3 mm Al equivalent;
AP8-MIN is about 7 times AP8-MAX at 1 MeV (arXiv:1503.07682, sec. 1, p. 3). Fermi: 565 km at 25.6°, about 15% of the
time in the SAA, with science data suspended there (arXiv:1206.1896, sec. 2.2, p. 25).
<!-- /example -->

## Feeding damage into conditions and simulation

1. **Conditions.** Store the damage history, not a constant: per interval its duration, fluence (from
   `Phi/L_int` or orbit segments, with NIEL source), TID, anode charge (MCP-PMT, gas), temperature, bias, and the
   monitored response. Derived constants (depletion voltage, trapping,
   threshold, light-yield factor `S_i(t)`, energy-scale drift) are payloads with intervals of validity
   ([calibration and alignment](calibration-and-alignment.md#time-dependence-and-conditions-data)). The light
   monitor corrects per channel through the transfer relation above (arXiv:1306.2016, sec. 4.1, p. 10); in orbit a
   stable peak (non-interacting protons) tracks the scale, fitted in time (arXiv:1206.1896, sec. 7.3.2, p. 137);
   annealing: item 2.
2. **Digitization.** The digitizer simulates the damage with device-model fields and trapping but no annealing,
   then the induced signal (arXiv:1905.03739, sec. 4, pp. 12-30; sec. 2, PDF p. 5). The annealing model only
   validates the conditions (fluence, depletion voltage; sec. 3) and does not enter the simulated response. No
   annealing correction or uncertainty is applied (sec. 2, PDF p. 5; sec. 4.2.4, pp. 18-20): its variation lies within
   the field-model variations (secs. 4.2.3-4.2.4, p. 20) and the trapping-constant range (sec. 4.5 and Table 5,
   p. 24), at the current annealing level only. Keep the annealing history in
   the conditions (item 1). General digitization:
   [detector simulation](detector-simulation.md#digitization) and
   [readout, digitization and overlay](readout-digitization-and-overlay.md).
3. **Dose prediction.** Pre-launch shielding and in-orbit TID/NIEL come from Geant4-based transport (MULASSIS,
   GRAS) of trapped-particle spectra per orbit segment (SPC; arXiv:2411.00607, secs. 2 and 3.2, pp. 3 and 7).
4. **Extrapolation.** A measured ageing trend, extrapolated, says when simulation and reconstruction must model the
   reduced response (UGD; arXiv:2207.12982, sec. 7, p. 31).

<!-- example: Fermi LAT calorimeter energy scale (SPC) -->
arXiv:1206.1896, sec. 7.3.2, p. 137: eq. (53) fitted to the proton-peak position gives `tau` of about 2 years and a
correctable energy-scale shift of about 4.5% after 10 years, consistent with pre-launch light-yield estimates.
<!-- /example -->

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| silicon leakage current versus time | fluence per luminosity or orbit segment through the annealing model, fitted to measured currents | temperature log, depleted volume | NIEL factors for the wrong spectrum; warm-ups not logged | COL, SPC |
| charge collection loss | bias scans per period; damaged-sensor digitization | device model of the field | one constant per run range hides annealing | COL, SPC |
| LGAD gain loss | gain-versus-bias curves per fluence step; raise bias | single-event limit known | bias raised past the burnout limit | COL |
| SiPM dark rate | dark rate and threshold versus time; annealing; cooling; shielding | temperature recorded | threshold drift read as signal loss | COL, SPC |
| crystal or plastic transparency | monitoring light plus a physics or source reference | transfer exponent measured | monitor and scintillation light take different paths | COL, SPC, UGD |
| photosensor versus scintillator | compare a light-bypass monitor with source or physics response | both monitors in the same period | PMT fatigue and recovery read as scintillator damage | COL, UGD |
| MCP-PMT lifetime | QE scans versus integrated anode charge, partly covered cathode | rate and gain logged | time-driven loss (leaks) read as charge-driven | FXT |
| gas ageing | irradiation at the real rate, particle type and area; gain and current monitoring | final gas and materials | X-ray tests read as a lifetime for hadron fields | COL, FXT |

## Distinctive but generalizable features

- **Topology**: a slow drift per channel on top of the fast event-level response.
- **Inverse problem**: separate dose, annealing, temperature and photosensor drift from one monitored response.
- **Natural objects**: per-channel time series of leakage current, gain, dark rate and monitoring response.
- **Informative residual**: monitored response minus the model prediction from the logged history.
- **Scaling**: leakage current linear in `Phi_eq`; trapping rate linear to about `1e15 n_eq/cm^2`; MCP and gas loss
  per integrated charge; plastic loss exponential in dose.
- **Conventions**: state `n_eq/cm^2` with its NIEL source, Gy, C/cm^2 per area or C/cm per wire, and the
  annealing state.
- **Tails**: dead channels, Malter discharges, sudden breakdown at the bias limit.
- **Dependence**: dose rate, temperature, gas flow and materials, solar cycle (SPC), luminosity (COL).
- **Data sample**: leakage currents, monitoring light, stable physics peaks (resonances, MIPs, non-interacting
  protons).
- **Transfers**: the history-based conditions and the two-monitor separation to every sensor; **does not
  transfer**: laboratory ageing rates to a different particle field.

## Common misconceptions and failure modes

- **Damage as a static constant.** It anneals, reverses and depends on temperature history.
- **One fluence number for all effects.** NIEL scaling holds well for leakage current and only approximately for
  other bulk effects (trapping, dopant removal); surface damage follows TID, not `Phi_eq`. State the spectrum.
- **X-ray ageing tests as a lifetime.** Hadron fields can age faster.
- **All light loss as radiation damage.** Plastics age from humidity, stress and oxidation; PMTs fatigue and recover.
- **Collider phrasing elsewhere.** "Per fill" and "per luminosity" become orbit segments and SAA passages in SPC.
- **Ignoring the dose-rate effect.** A fast laboratory irradiation underestimates slow damage in plastics.

## Deliverables

- The damage history per channel group: fluence, TID or anode charge per interval, temperature and bias.
- The model linking history to response, with its source and validity, and the residual to monitored data.
- Time-dependent constants with intervals of validity, and the extrapolation to end of life.
- For simulation: damaged-sensor digitization or response scaling, and the periods it represents.

## Tool hooks

A damage-history tool (none is shipped) would take per-interval duration, temperature, fluence and dose (silicon,
LGADs and SiPMs included) or anode charge (MCP-PMT, gas), and bias; output per interval the predicted leakage
current, depletion voltage or response factor. Units:
fluence in `n_eq/cm^2` with its NIEL source and particle spectrum as required inputs, dose in Gy (required with
fluence for silicon sensors, as surface damage follows TID), charge in C/cm^2 per area (MCP-PMT, micro-pattern gas) or
C/cm per wire (wire chambers) with the geometry stated, time in s, temperature in K. Required negative control: a
history with zero fluence, dose and charge returns no radiation-induced change (ageing without an identified dose,
such as plastic crazing or MCP-PMT leaks, is reported separately), and a history with a warm-up returns the
annealing step. Statuses: `ok`, `extrapolated` (outside the fitted range of any input or the relation's stated
validity), `unsupported-sensor`, `missing-history`.

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| silicon bulk and surface | pdg_2025_particle-detectors-at-accelerators; arxiv_1905.03739 | gap | arxiv_1503.07682 | gap | gap | gap |
| LGAD gain layer | pdg_2025_particle-detectors-at-accelerators; arxiv_2004.05260 | gap | n/a: lifetime fluence far below acceptor removal (arxiv_1809.06361) | gap | gap | gap |
| SiPM | arxiv_1809.06361 | gap | arxiv_2411.00607 | gap | gap | gap |
| crystal scintillators | pdg_2025_particle-detectors-at-accelerators; arxiv_1306.2016 | gap | arxiv_1206.1896 | gap | gap | gap |
| plastic scintillator and WLS | pdg_2025_particle-detectors-at-accelerators; arxiv_1806.02129 | gap | gap | arxiv_2207.12982 | gap | gap |
| MCP-PMT | gap (generic principle only: pdg_2025_particle-detectors-at-accelerators) | arxiv_2311.16676 | gap | gap | gap | gap |
| gas ageing | pdg_2025_particle-detectors-at-accelerators; arxiv_hep-ex_0204005 | arxiv_hep-ex_0204005 | gap | gap | gap | gap |
| radiation fields | arxiv_1306.2016; arxiv_1905.03739 | gap | arxiv_2411.00607; arxiv_1503.07682; arxiv_1206.1896 (orbit and SAA exposure only) | gap: ageing without an identified dose only (arxiv_2207.12982) | gap | gap |
| conditions and simulation | arxiv_1905.03739; arxiv_1306.2016 | gap | arxiv_1206.1896; arxiv_2411.00607 | arxiv_2207.12982 | gap | gap |

## Citations

The PDG reviews are in [the bibliography](detector-principles-bibliography.md) under "General and cross-cutting";
the other entries are in its split file `detector-principles-bibliography-radiation.md`, section "Radiation damage
and ageing". Read 2026-11-19/20; page locators count PDF pages (for PDG, equal to
the printed pages):
PDG RPP 2025, Particle detectors at accelerators (secs. 35.2.1.2, 35.3.2, 35.4, 35.6.2.4, 35.8.5);
arXiv:1905.03739; arXiv:1503.07682; arXiv:2004.05260; arXiv:1809.06361; arXiv:2411.00607; arXiv:1306.2016;
arXiv:1206.1896; arXiv:1806.02129; arXiv:2207.12982; arXiv:2311.16676; arXiv:hep-ex/0204005.
