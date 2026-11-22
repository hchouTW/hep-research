# Radiation and Ageing Effects

Damage from dose, fluence and charge, for conditions and simulation. Environments: COL, FXT, SPC, UGD;
GND and NUC are gaps. Electronics damage (SEU, circuit TID):
[front-end electronics](front-end-electronics-and-signal-processing.md#radiation-and-the-electronics).

## Relations

Fluence `Phi_eq` is the particle fluence weighted by the hardness factor `kappa` (non-ionizing energy loss, NIEL, relative to 1 MeV neutrons), in
`n_eq/cm^2`; total ionizing dose (TID) is in Gy, for any particle type (definitions; PDG RPP 2025,
sec. 35.8.5, p. 74). Give both, with the particle spectrum they came from: NIEL scaling
holds well for leakage current and is "moderately violated" for other effects (same page).

| Relation | Label, validity and source |
|---|---|
| `Delta I_L = alpha_80 Phi_eq V`, `alpha_80 ≈ 4e-17 A/cm` at 20 °C after 80 min at 60 °C (not the `alpha_I` below) | approximate (NIEL hypothesis); `V` depleted volume; gain in the device multiplies it. PDG sec. 35.8.5, p. 74 |
| `I_L(T) ∝ T^2 exp(-E_a/(2kT))`, `E_a ≈ 1.2 eV` | approximate; about 7-fold from room temperature to 0 °C (PDG; the relation gives 6.6 from 20 °C). PDG eq. (35.26), p. 74 |
| `N_id = N_id,0 exp(-c Phi_eq)` (initial dopant removal) | approximate; `c` depends on `N_id,0`, particle type and impurities (Fig. 35.32). PDG sec. 35.8.5, p. 76 |
| induced current times `exp(-t/tau_eff,e/h)`; `1/tau_eff ∝ Phi_eq` | approximate; linear up to about `1e15 n_eq/cm^2`, where `tau_eff` is of order 1 ns, then saturating. PDG p. 77 |
| bias limit from single-event effects at average fields near 12 V/um | approximate; sets the lifetime in highly energetic particle fields. PDG pp. 77-78 |
| `I_leak = sum_i V_i Phi_eq,i [alpha_I exp(-sum_{j>=i} t_j/tau(T_j)) + alpha_0* - beta ln(sum_{j>=i} Theta(T_j) t_j / t_0)]` | approximate (phenomenological); per interval `i` with fluence `Phi_eq,i` (collider: `(Phi/L_int) L_int,i`), duration, temperature and depleted volume `V_i`; `alpha_I` is the short-term amplitude; `1/tau = 1.2e13/s exp(-1.11 eV/kT)`, `Theta = exp(-(1.30 eV/k)(1/T - 1/T_ref))`, `T_ref` = 20 °C; `t_0` = 1 min; ln for the source's base-less `log` (it reproduces `alpha_80`); 20 °C scaling with `E_eff = 1.12 eV`, not the 1.2 eV above; gives the current at full depletion (10% on `Phi/L_int` for the bias used); `beta` at 21 °C; no stated range; fit to one window (Fig. 2): beyond its fluence or −15 to +20 °C (operation, sec. 4.2.1, p. 16), e.g. 60 °C below, `extrapolated`. arXiv:1905.03739, sec. 3.1, eqs. (1)-(2), pp. 5-6, notes 5-6 |
| `L/L_0 ≈ exp(-D/D_c)` for plastic scintillator | approximate; `D_c` of tens of kGy at dose rates from a few `1e-3` to 10 Gy/h, larger damage at lower rate. PDG sec. 35.3.2, p. 12 |
| `S(t)/S_0 = (R(t)/R_0)^alpha` (scintillation vs monitoring light) | approximate; `alpha` per crystal producer from an irradiated beam test, loss-independent only for small losses (no threshold given): a loss beyond the beam test's or an in-situ exponent outside its 10% spread (larger transparency and VPT loss) is `extrapolated`. arXiv:1306.2016, sec. 4.1, eq. (3), pp. 10-11, and sec. 4.1.1, pp. 12-13 |
| `s(t) = (p_0 - p_1) + p_1 exp(-(t - t_s)/tau)` (energy-scale drift) | approximate, empirical fit to a monitored peak over three years (Fig. 73), extrapolated beyond; `t_s` is eq. (53)'s `t_0`. arXiv:1206.1896, sec. 7.3.2, eq. (53), p. 137 |
| `R = -(1/G) dG/dQ` (% per C/cm per wire, or per C/cm^2 for micro-pattern gas) | definition of the gas ageing rate; **not** a predictor outside the tested conditions: ageing is not a function of `Q` alone; lower accumulation rates can age more. arXiv:hep-ex/0204005, secs. I and V.D, pp. 1 and 8 |
| `Q_A = r_pe T f_duty G e` (integrated anode charge per area) | exact bookkeeping for a constant photoelectron rate `r_pe` (DQE × incident rate) per area, run time `T`, duty factor, gain `G`; an unspecified photon rate taken as `r_pe` bounds the photon-induced charge only: state which |

## Damage and ageing by sensor

**Silicon (bulk and surface).** Bulk damage (displaced atoms) raises the leakage current, traps carriers and builds
space charge, changing the depletion voltage; surface damage (oxide charge, interface traps) scales with TID,
raising surface currents and changing inter-electrode isolation (PDG sec. 35.8.5, p. 74). It anneals:
beneficial first, then reverse over months at room temperature, much longer when cold; n-type
bulk inverts, p-type with n+ readout does not and is preferred (electrons are collected) (pp. 75-76).
Temperature and warm-ups belong to the damage history (p. 78). Related:
[tracking and vertexing](tracking-and-vertexing.md). In low Earth orbit a
design study took trapped protons only (SPC; arXiv:1503.07682, abstract; sec. 1, p. 3).

<!-- example: ATLAS pixel detector (COL) and LOFT silicon drift detectors (SPC design study) -->
ATLAS pixel (arXiv:1905.03739):
eq. (1): short-term amplitude `alpha_I = (1.23 ± 0.06)e-17
A/cm` with `alpha_0* = 7.07e-17 A/cm` and `beta = (3.29 ± 0.18)e-18 A/cm` (sec. 3.1, pp. 5-6): with
`tau`, `Theta` above, the bracket is about `4.1e-17 A/cm` after 80 min at 60 °C (central values, `3.9e-17` to `4.3e-17` over the `alpha_I`, `beta` ranges, computed here), the `alpha_80` above. LOFT SDDs (arXiv:1503.07682): charge collection loss measured with protons against expected
in-orbit damage (abstract; sec. 1, p. 3).
<!-- /example -->

**LGAD.** The highly doped gain layer loses acceptors with fluence, so gain drops sharply (PDG p. 77); raising
the bias recovers part of it, until the single-event limit above. Mitigations: deeper gain layers (stronger recovery with
bias) and carbon in the gain layer (fewer interstitials that remove boron) (arXiv:2004.05260,
secs. 1-2, pp. 1-2). This is a **single-environment** technique (COL): acceptor removal is measured at
hadron-collider timing-layer fluences (example below), while a SiPM review gives most space detectors a
lifetime fluence below 1e12 particles/cm^2, as quoted, not NIEL-weighted (arXiv:1809.06361, sec. 1, p. 1).
Timing consequences: [timing detectors](timing-detectors.md).

<!-- example: LGAD prototypes for the HL-LHC timing layers (ATLAS HGTD, CMS ETL; COL) -->
arXiv:2004.05260: 50 um HPK and 55 um FBK LGADs (abstract; Table 1, p. 2), neutron-irradiated from `4e14` to `4e15 n_eq/cm^2`, measured at
-30 °C; the deep and the carbonated gain layers perform reasonably up to `3e15` (abstract); requirements up to a few `1e15 n_eq/cm^2` and a
few MGy (sec. 1, p. 1).
<!-- /example -->

**SiPM.** The dominant effect, rising dark count rate, first destroys single-photoelectron resolution
(arXiv:1809.06361, abstract). Pixel occupancy from dark counts lowers the effective photon detection
efficiency and gain (eq. (10), p. 11). The fluence at which single photoelectrons are lost depends on design and
temperature: test per application; annealing (room temperature, or high temperature with forward
bias) recovers part of it (secs. 3.4 and 6, pp. 12 and 15). With a scintillator, the rising dark rate raises the
energy threshold (SPC; arXiv:2411.00607v2, abstract).

<!-- example: GRBAlpha and VZLUSAT-2 CubeSats, Hamamatsu S13360-3050PE MPPCs (SPC) -->
arXiv:2411.00607v2: GRBAlpha, 550 km sun-synchronous orbit, CsI(Tl) read by eight MPPCs behind 2-2.5 mm PbSb: the
low-energy threshold rose from about 20 to 120 keV in 3 years 5 months, matching a simulated TID of 1.6
Gy and `2.1e9 n_eq/cm^2` from trapped protons (AP-8) (abstract; sec. 6, p. 14).
<!-- /example -->

**Crystal scintillators.** Ionizing dose forms colour centres; the induced absorption shortens the attenuation
length, lowers light output and distorts its uniformity; hadrons add
displacement and fission-fragment damage (PDG sec. 35.4, p. 18). Damage and spontaneous recovery compete, so the
loss depends on dose rate; injected monitoring light tracks it (COL; arXiv:1306.2016, sec. 3, p. 8).

<!-- example: CMS ECAL PbWO4 (COL) and the Fermi LAT CsI(Tl) calorimeter (SPC) -->
CMS ECAL (arXiv:1306.2016): by the end of 2011 the average laser response
dropped 2-3% in the barrel and 40% at 2.7 ≤ |eta| ≤ 3.0 in the endcap, there partly from VPT loss (sec.
3, p. 8); `alpha` of eq. (3) is 1.52 and 1.0 for crystal producers BTCP and SIC, with a 10% spread, from a
beam test (sec. 4.1, pp. 10-11); an effective 1.16 for endcap BTCP, tuned on Z to ee events, absorbs larger transparency loss and VPT loss
(sec. 4.1.1, pp. 12-13). Fermi LAT (arXiv:1206.1896): light yield fell about 1%/year in its first three
years in orbit (sec. 2.1.2, p. 20); eq. (53) on the proton peak gives `tau` ≈ 2 years and a correctable
4.5% energy-scale shift after 10 years, extrapolated (sec. 7.3.2, p. 137).
<!-- /example -->

**Plastic scintillator and WLS fibres.** Radiation yellows plastic and lowers its transparency, partly recovering after irradiation, faster with oxygen (PDG sec.
35.3.2, p. 12). Plastics also age **without dose**: crazing under stress or solvents, and fogging from
humidity at elevated temperature (same page); a measured long-term loss can have an unknown cause,
photochemical oxidation a further candidate (arXiv:2207.12982, sec. 1.2, pp. 7-8). Two monitors separate the
causes: a light source that bypasses the scintillator sees the photosensor,
a radioactive source or physics signal sees both (COL; arXiv:1806.02129, sec. 4.5, p. 24).

<!-- example: ATLAS Tile Calorimeter (COL) and T2K near detectors (UGD) -->
TileCal (arXiv:1806.02129, sec. 4.5, pp. 23-24): the difference between minimum-bias (or Cs) and laser response is
read as scintillator irradiation; laser data alone show PMT gain loss under light and recovery
without collisions. T2K near detectors (arXiv:2207.12982): light yield fell 0.9-2.2%/year over ten years (abstract,
p. 5); most of the loss is in the scintillator, not the WLS fibres, whose long attenuation component degrades by
1-5%/year (sec. 7, p. 31).
<!-- /example -->

**MCP-PMT.** Ions fed back from residual gas damage the photocathode, so quantum efficiency falls with integrated
anode charge; atomic-layer-deposition (ALD) coatings of the channels raise the lifetime above 20 C/cm^2
(PDG sec. 35.2.1.2, pp. 5-6; arXiv:2311.16676, sec. 1, p. 1). Lifetime tests illuminate at a known rate,
log anode charge, scan QE; a covered part of the photocathode separates charge-driven loss from loss with
time alone (vacuum micro-leaks) (arXiv:2311.16676, sec. 2.1, p. 2). Lifetime source: FXT only.

<!-- example: PANDA Barrel and Endcap Disc DIRC MCP-PMTs (FXT) -->
arXiv:2311.16676: before ALD the QE dropped by a factor of 2 or more after a few hundred mC/cm^2; a photon rate of
about 200 kHz/cm^2 (incident or detected not stated), 10 years, 50% duty and gain `1e6` give an expected
charge of about 5 C/cm^2 for the Barrel DIRC (sec. 1, p. 1; the upper bound of the relation above gives 5.1
C/cm^2); a two-ALD-layer tube passed 34 C/cm^2 with no QE loss yet (sec. 2.1,
p. 2).
<!-- /example -->

**Gaseous detectors.** Avalanche plasma chemistry forms deposits on electrodes, from hydrocarbon quenchers and
outgassing insulators, glues and oils; strict materials and gas control allow several C/cm^2 without observable
ageing (PDG sec. 35.6.2.4, p. 33). An insulating cathode layer can ignite the self-sustained Malter discharge;
ageing depends on gas, gas flow, materials, irradiated area, current density, gain, rate, particle type and energy, so
laboratory tests with X-ray sources may not transfer to a hadron environment (arXiv:hep-ex/0204005, secs. II.A
and V.D, pp. 2 and 8). Data: FXT and COL (same review, secs. IV.A and V.D, pp. 4 and 9). Drift chambers: [gaseous
tracking](gaseous-and-specialized-tracking-technologies.md#drift-chambers-and-drift-tubes).

<!-- example: HERA-B honeycomb drift tubes and muon chambers (FXT) -->
arXiv:hep-ex/0204005, sec. V.D, pp. 8-9: honeycomb drift-tube prototypes aged badly after a few mC/cm among
secondaries of 920 GeV protons on a nuclear target, though X-ray tests to 5 C/cm showed nothing; in the muon
proportional chambers Ar/CF4/CH4 aged over 100 times faster in hadron beams than with radioactive sources.
<!-- /example -->

## Radiation fields by environment

- **COL.** Dose and hadron fluence depend on radius and pseudorapidity and scale with integrated luminosity;
  the fluence comes from a generator plus transport (Pythia8, FLUKA) as `Phi/L_int`, checked per
  module group against leakage currents (annealing model): in every branch include or cover the hardness-factor uncertainty, which enters both sides (prediction and `alpha`), so the check cannot test it, else mark incomplete, and keep the transport value and uncertainty only where
  checked and within 1 sigma of the current-derived `Phi/L_int`, sigma being that measurement's uncertainty alone and below the transport uncertainty (example below: 1.5 sigma), else the fitted `Phi/L_int` or a covering uncertainty.
- **SPC (low Earth orbit).** The proton/electron balance depends on shielding and spectrum (example below), so
  model trapped electrons too; solar-proton and Galactic cosmic-ray (GCR) TID is called negligible next to trapped protons (arXiv:2411.00607v2, sec. 4.1,
  p. 10, citing another study): bound it per mission. Dose depends on altitude, shielding and solar cycle (same page), from trapped-particle models (AP-8 protons,
  AE-8 electrons), with a factor of two quoted on AP-8 only (sec. 3.2, p. 7); its cited
  SPENVIS page gives 2 for both as a widely quoted estimate, larger errors where spatial or spectral gradients are steep or time variations poorly known, more for differential fluxes from the integral maps (SPENVIS trapped-radiation help, sec. 5.1): use 2 on both as a lower estimate, varied upward where gradients are steep, and 3 for differential fluxes, this page's convention (SPENVIS gives no value, so the 3-based numbers below follow from it), each propagated as a bound or variation (item 3). In AP-8, trapped protons at low altitude are more numerous in
  AP8-MIN (arXiv:1503.07682, sec. 1, p. 3, protons only): for electrons run AE8-MIN and AE8-MAX and carry the larger, unless each segment's phase is fixed (item 3). Cutoffs:
  [space-based direct detection](space-based-direct-detection.md#geomagnetic-cutoff).
- **UGD.** No underground damage source (gap; plastic ageing of unknown cause: above); context:
  [noble liquid and neutrino detectors](noble-liquid-neutrino-and-rare-event-detectors.md).

<!-- example: ATLAS pixel and CMS ECAL (COL), LOFT, Fermi and GRBAlpha orbits (SPC) -->
ATLAS pixel (arXiv:1905.03739): FLUKA central value, 15% uncertainty, valid at `|z| ≈ 0` only, hardness-factor
uncertainty (significant, not quantified) excluded; 1.5 sigma off at `z = 0`, more at larger `|z|` (Fig. 3 per
module group; secs. 2-3.1, pp. 3-8). Its digitizer omits annealing (uncorrected, no uncertainty): at the
state reached, its variation at `1e14` and `2e14 n_eq/cm^2` is within the field-model and trapping-constant variations (secs. 2, 4.2.3, 4.2.4, 4.5, Table 5, pp. 4-5, 20, 24).
CMS ECAL: expected dose up to 4 kGy in the barrel and 200 kGy at |eta| = 3 after 10 years (500 fb^-1); hadron
fluence from about `1e13` to `1e14 cm^-2`, as quoted (weighting and NIEL source not stated;
arXiv:1306.2016, sec. 2, p. 6). LOFT: AP8-MIN via SPENVIS, 600 km and 5° worst case, behind 3.3 mm Al equivalent;
AP8-MIN is about 7 times AP8-MAX at 1 MeV (arXiv:1503.07682, sec. 1, p. 3). Fermi: 565 km at 25.6°, about 15% of the
time in the SAA, science data suspended there (arXiv:1206.1896, sec. 2.2, p. 25). GRBAlpha (shielding above):
trapped protons dominate TID and TNID, electrons about 1-6% of TID (central values, 1.1-7.3% within quoted uncertainties, computed here as `1/(1 + TID(p)/TID(e))`:
1.3% from 74 ± 14 at ~550 km, solar-minimum AP-8/AE-8 models; 5.8% from 16.1 ± 3.4 at ~475 km, solar-maximum models (altitude and model changed together); arXiv:2411.00607v2 (GRAS), sec. 4.1, p. 10). Electron bound (1 sigma, factor 3 on both models (differential fluxes), computed here): 13% (solar minimum), 41% (maximum), or 6.2% and 24% with a factor of 2.
<!-- /example -->

## Feeding damage into conditions and simulation

1. **Conditions.** Store the damage history, not a constant: per interval the [Tool hooks](#tool-hooks) inputs (fluence
   from `Phi/L_int` or orbit segments) and the monitored response. Derived constants (trapping,
   threshold, per-channel `S(t)/S_0` of the transfer relation, energy-scale drift) are payloads with intervals of validity
   ([calibration and alignment](calibration-and-alignment.md#time-dependence-and-conditions-data)). The light
   monitor corrects each channel by the transfer relation (COL; arXiv:1306.2016, sec. 4.1, p. 10); in orbit a
   stable peak (non-interacting protons) tracks the scale, fitted in time (arXiv:1206.1896, sec. 7.3.2, p. 137).
2. **Digitization.** Digitize with device-model fields and trapping; state whether annealing enters; omit it
   only if its variation at your fluences and annealing state is within the field-model and trapping-constant
   variations at their published sizes (not enlarged for this test) propagated as uncertainties, re-checked past the tested fluence or annealing (COL; example above). General digitization:
   [detector simulation](detector-simulation.md#digitization).
3. **Dose prediction.** Pre-launch, MULASSIS gave TID only, without electrons,
   and in orbit AE-8 and AP-8 fluences per mission segment (IRENE) go into GRAS (both Geant4-based) for TID and TNID (SPC;
   arXiv:2411.00607v2 (3 Apr 2025), secs. 2 and 3.2, pp. 3-4 and 7). A TID-only prediction misses displacement damage (TNID), and one without trapped electrons their dose: state TNID (protons dominate it in the example), add the electron dose, bounded with the model factor on both models (2, or 3 for differential fluxes), for this mission to the TID as a one-sided upward term, neglected only when that bound is below the dose's transport-code uncertainty (Monte Carlo statistics and model factor excluded), and likewise state solar protons and GCR or show them negligible.
4. **Extrapolation.** A measured ageing trend, extrapolated, says when simulation and reconstruction must model the
   reduced response (UGD; arXiv:2207.12982, sec. 7, p. 31).

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| silicon leakage current | fluence per interval, annealing model fitted to currents | temperature log, depleted volume | wrong-spectrum NIEL factors; unlogged warm-ups | COL |
| charge collection loss | bias scans per period; damaged-sensor digitization | field device model | one constant per run range hides annealing | COL; SPC (design study) |
| LGAD gain loss | gain-versus-bias curves per fluence step; raise bias | single-event limit known | bias raised past the burnout limit | COL |
| SiPM dark rate | dark rate and threshold versus time; annealing, cooling, shielding | temperature recorded | threshold drift read as signal loss | COL, SPC |
| crystal or plastic transparency | monitoring light plus a physics or source reference | transfer exponent measured per producer (crystals) | monitor and scintillation light take different paths | COL |
| photosensor versus scintillator | light-bypass monitor versus source or physics response | both monitors in one period | PMT fatigue and recovery read as scintillator damage | COL |
| MCP-PMT lifetime | QE scans versus integrated anode charge, partly covered cathode | rate and gain logged | time-driven loss (leaks) read as charge-driven | FXT |
| gas ageing | irradiation at the real rate, particle type and area; gain and current monitoring | final gas and materials | X-ray tests read as a lifetime for hadron fields | FXT, COL |

## Distinctive but generalizable features

- **Topology**: a slow per-channel drift under the event response.
- **Inverse problem**: dose, annealing, temperature and photosensor drift from one monitored response.
- **Natural objects**: per-channel monitored time series.
- **Informative residual**: monitored response minus the history-based prediction.
- **Scaling**: leakage current linear in `Phi_eq` at a fixed annealing state; MCP loss per integrated charge once time-only loss is separated, gas loss
  too only at the fixed conditions of Gaseous detectors; plastic loss exponential in dose at a fixed dose rate.
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
- **All light loss as radiation damage.** Plastics age from humidity, stress and oxidation; PMTs fatigue and recover.
- **Collider phrasing elsewhere.** "Per fill" and "per luminosity" become orbit segments and SAA passages (SPC).

## Deliverables

- The damage history per channel group (fluence uniform within its uncertainty over a group) with the channel-to-group map: the required [Tool hooks](#tool-hooks) inputs per interval and the monitored response per channel.
- The history-to-response model, with source, validity and residual to monitored data.
- Time-dependent constants with intervals of validity, and the end-of-life extrapolation.
- For simulation: damaged-sensor digitization or response scaling, and its periods.

## Tool hooks

A damage-history tool (none shipped) takes the inputs below and optionally the monitored response; it outputs per interval the predicted leakage
current or response factor where a relation exists, else `no-predictor`. Units, all required per interval:
fluence in `n_eq/cm^2` (silicon, LGADs, SiPMs) and crystal hadron fluence in cm^-2, weighting stated (crystals: producer's beam-test `alpha`, spread, loss), dose in Gy (those, plastics, WLS), per species expected for the orbit (SPC: trapped protons
and electrons, solar protons and GCR, with the per-mission bound when shown negligible), each stated even when zero (absent is not zero), with spectrum and NIEL source when non-zero, depleted volume `V_i` in cm^3 (silicon, LGADs, SiPMs),
bias, full-depletion voltage in V and active thickness in um (all silicon), gain (LGADs, SiPMs: it multiplies the current), charge in C/cm^2
(MCP-PMT, micro-pattern gas, any PMT, VPT or SiPM reading a dosed scintillator) or C/cm per wire, geometry stated, with gain, duty factor and rate with its kind (photoelectron, or photon as an upper bound, `missing-history` if the kind is absent) (MCP-PMT) and, for gas,
current density, irradiated area, particle type and energy, gain, rate, mixture, flow rate and materials, time in s, temperature in K. Required negative control: a
history whose required fluence, dose and charge are all zero returns no radiation-induced change (zero is in every exposure-driven relation's range, and time-only fits such as `s(t)` apply only to the detector and exposure they were fitted to, so a zero-exposure history skips them), and a history with a warm-up returns the
leakage-current annealing step. Status, first match wins: `missing-history` (an interval or required input, temperature included, is absent), `no-dose-ageing` (the response changes while cumulative required fluence, dose and charge are zero), `no-predictor` (non-zero exposure and no relation in Relations for the output, always for LGAD gain, SiPM dark rate, MCP-PMT QE versus charge, WLS fibres, crystals without a monitored response, the PMT, VPT or SiPM of a dosed scintillator, gas ageing always (`R` is a definition, and a cited test's rate is only a reference at that test's conditions)), `extrapolated` (an input or the monitored response outside a relation's
fitted range or stated validity, such as a crystal loss beyond its beam test), `ok`, plus flags reported with any status: `bias-limit` (silicon bias/thickness at or above a stated margin below the single-event field of about 12 V/um in Relations) and `residual` (the monitored response off a prediction beyond its uncertainty, for example non-dose ageing or PMT fatigue).

## Environment coverage

Cells credit the target detector's environment and mark lab, irradiation or beam-test (FXT) data.

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| silicon bulk and surface | arxiv_1905.03739 (bulk only) | gap | arxiv_1503.07682 (bulk only; design study; irradiation) | gap | gap | gap |
| LGAD gain layer | arxiv_2004.05260 (irradiation) | gap | n/a below about 1e12 particles/cm^2 lifetime fluence (arxiv_1809.06361), else gap | gap | gap | gap |
| SiPM | arxiv_1809.06361 (irradiation) | gap | arxiv_2411.00607 | gap | gap | gap |
| crystal scintillators | arxiv_1306.2016 (exponent: beam test) | gap | arxiv_1206.1896 | gap | gap | gap |
| plastic scintillator and WLS | arxiv_1806.02129 | gap | gap | arxiv_2207.12982 | gap | gap |
| MCP-PMT | gap (related: PDG, principle only) | arxiv_2311.16676 (lab tests) | gap | gap | gap | gap |
| gas ageing | arxiv_hep-ex_0204005 (in situ and tests) | arxiv_hep-ex_0204005 | gap | gap | gap | gap |
| radiation fields | arxiv_1306.2016; arxiv_1905.03739 | gap | arxiv_2411.00607 (simulated); arxiv_1503.07682 (design study); related, exposure only, not coverage: arxiv_1206.1896 | gap (arxiv_2207.12982: no identified dose) | gap | gap |
| conditions and simulation | arxiv_1905.03739; arxiv_1306.2016 | gap | arxiv_1206.1896; arxiv_2411.00607 | arxiv_2207.12982 | gap | gap |

## Citations

PDG: [the bibliography](detector-principles-bibliography.md), "General and cross-cutting"; the rest:
`detector-principles-bibliography-radiation.md`, "Radiation damage and ageing". Read dates: in the bibliography fragment (2026-11-19 to 2026-11-21), PDG 2025 edition kept as the one read (2026-11-19/20, copy cached 2026-11-16, main bibliography: 2026-10-14), 2026 edition listed on pdg.lbl.gov 2026-11-22, not read;
locators count PDF pages (PDG: the printed pages).
