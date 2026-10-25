# J15: a minimal spectrometer from F1 to F4

**SYNTHETIC.** J15 is an invented geometry. It represents no experiment, and its requirements are illustrative
numbers. It exists to show the design loop of `skills/hep-detector/references/system-design-workflow.md` end to
end. The loop starts with analytic estimates (F1) and a toy simulation (F2). It ends with Geant4 studies upgraded
through the F4 qualification path of `geant4-study-protocol.md`. Every verdict below is derived by
`contracts/design.py`; none is written by hand.

## The design

A 0.5 T uniform-field spectrometer (Geant4 program §B.4):

- Six 0.3 mm silicon planes over a 0.80 m lever arm, 10 µm point resolution.
- Two TOF stations, each with two 10 mm PVT layers and 100 ps per layer.
- A 50-layer Pb (2 mm) / PVT (5 mm) sampling calorimeter of 18.4 X₀.

The candidates differ only in their tracker planes, over the same 0.80 m:

| Candidate | Description |
|---|---|
| `cand-N6` | Nominal: six planes (§B.4.1) |
| `cand-N4` | Four planes |
| `cand-N8` | Eight planes |

The requirements are synthetic:

| Requirement | Figure of merit | Denominator | Target |
|---|---|---|---|
| `REQ-TRK-001` | momentum-resolution-core | protons, 1 GV | ≤ 0.03 |
| `REQ-TRK-002` | momentum-resolution-core | protons, 100 GV | ≤ 0.12 |
| `REQ-CC-001` | charge-confusion-rate | protons, 500 GV, curvature offset 0 ± 2e-5 /GV | ≤ 0.02 |
| `REQ-CAL-001` | shower-containment | electrons, 10 GeV | ≥ 0.95 |

There are also hard mass and soft channel-count constraints. The comparison basis is equal mass within 5 %: the
candidates differ only in 0.3 mm silicon planes (3 kg each, synthetic), 6 to 12 kg of about 1.94 t, so the basis
holds by construction (`design.py` checks it).

The geometry is generated from the candidate. `evaluate_design.py geometry` writes the geometry file, and
`geant4_run.py from-geometry` with `j15.realization.json` (mapping 1.1.0) derives the `element_sim` spec. For
`cand-N6` the derived spec equals §B.4.1 element by element.

The human gates H1 and H2 are prepared by an agent as decision records in `output/decisions/*.draft.json`. They are
marked as needing a human signature. The report lists them but shows the gates as missing, because only a record
whose actor is a human clears a gate (DEC-05; the actor is a declared field, which the check cannot verify). Here they are a demonstration. H3 (`architecture-selection`) is not drafted, so the
report flags H1, H2 and H3 as missing; H4 (`design-baseline`) comes only after those three.

### Deliberate simplifications (§B.4.1)

- A uniform field with sharp edges.
- No magnet material.
- Unsegmented TOF layers.
- No optical photons.
- No trigger, readout electronics or anticoincidence.

`simreco` has four switchable tail sources: `alignment`, `calibration-non-uniformity`, `noise-digitization` (strip
digitization, threshold, efficiency, noise hits) and `pattern-recognition`. Their models are synthetic and illustrative: alignment
leaves residuals of 5 µm (bending), 10 µm (non-bending) and 20 µrad (rotation); the calibration non-uniformity is a field-map gradient of 1 %; the strips are 47 µm and
116 µm with 8 µm charge sharing, which gives 10.3 µm and 30.1 µm, slightly coarser than the declared point resolution (10 µm
bending, 30 µm non-bending in the reconstruction spec); the noise is 0.1 hits per plane; the efficiency is 99 %; the
association window is 2 mm. They are illustrative, not a measured detector.

### Against real instruments (§B.4.3)

PAMELA (arXiv:0905.2551, section 2, read 2026-10-24) has:

- A 0.43 T permanent magnet.
- Six double-sided silicon planes with resolution better than 4 µm, and an MDR above 1 TV (both stated up to a
  zenith angle of 10°).
- Three TOF planes (S1–S3).
- A 16.3 X₀, 0.6 λ calorimeter.

J15 is of the same type. Its 10 µm silicon resolution is more conservative, and its TOF is unsegmented.

The AMS-02 TOF (astro-ph/0206021, sections 1 and 3, read 2026-10-24) has four planes of 8, 8, 10 and 8 counters, with
an expected resolution of about 140 ps for protons. J15's 100 ps per layer is optimistic, so the reconstruction is
repeated at 150 ps (below).

## What the loop gives

### F1 and F2

All values are reproduced by `run.py`; the numbers are in `output/results.json`.

| Quantity | Value | §B.4.2 reference |
|---|---|---|
| `cand-N6` resolution at 1 GV, F1 | 2.5 % | 1.8–2.6 % |
| `cand-N6` resolution at 1 GV, F2 toy | 2.2 % | 1.8–2.6 % |
| MDR (Gluckstern) | 1131 GV | about 1172 GV from exact least squares |
| `cand-N6` resolution at 100 GV, F1: exact least-squares measurement term 8.5 % ⊕ multiple scattering 1.9 % | 8.7 % | — |
| F2 in-field acceptance at 10 GV | equals the straight-line F1 acceptance within 10 % | — |

At 100 GV more planes resolve better. Shower containment has no tool below F4.

### The Geant4 studies (F4)

The studies were run live by `live.py` and recorded in `recorded/`. `run.py` replays them offline: it re-runs
`check_geant4_study.py label --upgrade` on the recorded inputs, then writes the F4 evaluation of each upgraded study
(`f4` refuses a study whose upgrade was refused) and the report.

| Study | Result | Upgrade | Verdict |
|---|---|---|---|
| N4, 1 GV | 1.48 % | validated-in-scope | `REQ-TRK-001` pass (row 16) |
| N6, 1 GV, all tail sources | 1.82 % | validated-in-scope | see below |
| N6, 1 GV, tail sources off | 1.82 % (`optimistic`) | validated-in-scope | — |
| N8, 1 GV | 2.08 % | validated-in-scope | `REQ-TRK-001` pass (row 16) |
| N4, N6, N8, 100 GV | 11.3 %, 10.5 %, 9.8 % | refused (reference control) | no F4 evaluation (`f4`: `upgrade-refused`); `REQ-TRK-002` stays at F1/F2 |
| N6, 500 GV charge confusion | 3.4 % | refused (D0-b) | no F4 evaluation; stays at F1 (`bound.direction`) |
| N6, 10 GeV shower containment | 96.8 % | refused (no reference) | no F4 evaluation; no evaluation used |

Notes on the table:

- **What the qualification checks.** Each 1 GV study passed the four conditions of the qualification path:
  - material definition (geantino scan and independent densities);
  - field propagation against the analytic helix;
  - reconstruction closure with charged geantinos at 1 TV;
  - the multiple-scattering reference.

  The multiple-scattering reference is an isolated 0.3 mm silicon slab against Lynch–Dahl F = 98 %. It is −1.8 % at
  1 GV; the ±13 % density controls shift the width by +7.3 % and −7.0 %, within 1.1 times the 8.1 % detection limit.
- **The uncertainty.** It is statistical ⊕ replica spread ⊕ the 1 GV reference's 4.0 % tolerance (D0-c). Its relative size is
  compared with the qualification-path floor of 0.02 in adequacy table 1.2.0. With a 4.0 % tolerance in the uncertainty
  the floor does not bind for J15 (it would below a tolerance of about 3.3 %). The floor is provisional until the
  table's physics review.
- **Why fewer planes are better at 1 GV.** Multiple scattering dominates there, so less material wins. At 100 GV the
  order reverses, in F1 and in the 100 GV Geant4 studies (refused, so `unvalidated`).
- **Why `cand-N6` is inconclusive on `REQ-TRK-001`.** The tail-source demonstration evaluates the same simulation
  twice, both at F4: once with every tail source off (`optimistic`) and once with all four on (`estimate`). The
  estimate alone would pass (row 16, `estimate.decides`). The optimistic value is inconclusive by row 14
  (`bound.direction`: an optimistic bound cannot approve a ≤ requirement), and AGG-04 compares only the evaluations
  at the highest fidelity present: one inconclusive evaluation there makes the requirement inconclusive. So the
  demonstration blocks the pass although both values agree (1.82 %); the same bound at a lower fidelity would be
  ignored. This is a property of the aggregation rule (a follow-up for `design.py`), not of the evidence. Deleting
  the demonstration would also make `cand-N6` pass like the other two; no check flags a missing evaluation, a gap
  in the shortcut guard of LIM-02 (verdicts guard against oversight and shortcuts, not deliberate forgery), so the
  evaluation set belongs in the plan before the runs (here `run.py`'s `STUDIES`) and J15 keeps it. At 1 GV the tail
  sources barely move the core, because multiple scattering dominates. In the refused 100 GV studies
  (`unvalidated`) they widen it from 8.6 % to 10.5 %.
- **Why the 100 GV studies are refused.** At 100 GV the multiple-scattering reference agrees with Lynch–Dahl to
  −0.6 %, and both controls are caught (their verdicts fail), but the −13 % control shifted the width by 8.1 %, beyond 1.1 times its
  claimed detection limit of 6.3 %: the controls had a fixed size instead of one sized from each rigidity's detection
  limit. The protocol records a single miss and never reruns it with another seed. Qualifying 100 GV needs a new
  reference study whose control size is declared before its runs (for example from this study's 6.3 % detection
  limit, which can miss again); no tool can tell such a study from a rerun, so the pre-declaration is a step a
  human checks, and this record and its miss stay listed. `cand-N6` at 100 GV also missed its
  convergence se target (incomplete, never topped up). These verdicts are conditional on the declared 10 µm point
  resolution, which no benchmark validates, and above about 20–30 GV it dominates.
- **Charge confusion.** It cannot be upgraded before a tail reference exists (D0-b). Compliance would also need
  `charge-confusion-data-validation` and `rigidity-scale-offset`, which J15 does not fabricate.
- **Shower containment.** It has no reference benchmark here; the PDG gamma profile is sanity only.

### Physics variations (B3.4)

The model envelope comes from the per-list results. Each end is judged separately; the envelope is not a σ.

| Rigidity | Multiple-scattering model variation | Hadronic variation |
|---|---|---|
| 1 GV | Single scattering (`FTFP_BERT__SS`) against WentzelVI (option 4, `FTFP_BERT_EMZ`) | `QGSP_BIC_EMZ` (binary cascade for nucleons) |
| 100 and 500 GV | Option 3 (`FTFP_BERT_EMY`: Urban multiple scattering for protons, other EM settings too) against option 4 | `QGSP_BIC_EMZ` (QGS string model instead of FTF) |

- **1 GV.** Protons get `G4CoulombScattering` in single scattering against WentzelVI multiple scattering
  (`G4EmBuilder.cc`, Geant4 11.4.3).
- **100 and 500 GV.** Single scattering of the electrons in a hadronic shower in lead is prohibitively slow. Option 3
  passes `isWVI=false`, so protons get the Urban model; option 3 also differs from option 4 in other settings
  (electron models, step limits), so this variation is wider than the proton multiple-scattering model alone.
- **Air.** Filling the world, field region and calorimeter mothers with air widens the `cand-N6` 1 GV core by 5 %.

### Other studies

- **TOF (B3.5).** At 1 GV σβ/β is 1.68 % at 100 ps per layer and 2.52 % at 150 ps. That is 2.3 % × β = 0.73
  (§B.4.2), scaled by σ_t. The two-layer residual is 142.6 ps and 213.9 ps, against √2 σ_t = 141.4 ps and 212.1 ps.
- **Verification ladder (B3.2).** The ladder is a separate record that is always `unvalidated`; see
  `output/artifacts/studies/ladder/`. These checks pass, and every negative control is caught:
  - overlaps: Si2 moved onto Si1 is refused by check-spec;
  - energy balance for e⁻ and e⁺ at 1 GeV, EM-only (controls: double-counted leakage and the omitted 2 mₑ);
  - material budget and material definition (control: Pb density × 1.05);
  - field propagation (control: B × (1 ± 1e-4));
  - field-propagation-muon at 1, 10 and 100 GV (control: B × 1.01);
  - reconstruction closure (control: reconstruction B × 1.05);
  - TOF beta and two-layer consistency (control: a 100 ps offset);
  - sampling fraction: 0.268 against 0.270 from the PDG muon tables (control: PVT density × 1.2).
- **Multiple-scattering reference record.** It is listed separately in `output/artifacts/studies/msref/`, at 1, 100
  and 500 GV.
- **Calorimeter cut convergence (B3.3).** 10 GeV electrons at production cuts of 0.1, 0.3, 0.7 and 1.0 mm. Both the
  containment and the rear-leakage fraction are converged.

## Files

| File | Content |
|---|---|
| `run.py` | Offline replay (default): design, F1, F2, the F4 studies from `recorded/`, report, criteria |
| `live.py` | The live campaign. It needs Geant4 with `element_sim`, `simroot` and `simreco` (`HEP_GEANT4_CONFIG`). It rewrites `recorded/` |
| `j15.realization.json` | The realization profile (mapping 1.1.0) |
| `recorded/` | Run records (gzip), specs, study inputs, benchmark results, convergence and variation tables, F4 results files. About 1.8 MB; no ROOT file |
| `output/` | Results, the design report, evaluations and re-labelled study records. The run records, specs and checks are unpacked from `recorded/` on each replay and are not committed |

Usage, from the plugin root:

- `python3 examples/design-minimal-spectrometer/run.py [--out DIR]`
- `HEP_GEANT4_CONFIG=cfg.json python3 examples/design-minimal-spectrometer/live.py --work DIR`

The test is `tests/examples/test_design_minimal_spectrometer.py`. Evidence: VALIDATION GEANT4-J15 (the campaign, the README review and the independent acceptance run).

## Still missing

- Human records for the gates (DEC-05): H1 and H2 (drafted here, unsigned), H3 (not drafted), then H4.
- A reviewer for the adequacy table.
- A new 100 GV multiple-scattering reference study, its control size declared before its runs (a human-checked step).
- A published multiple-scattering tail reference (D0-b).
- Data validation of charge confusion, and the rigidity-scale offset.
- A leakage reference for showers.
- Expected-precision evaluations, so that the report can rank and draw a Pareto front (it refuses both with the
  reasons).
- The full-text check of Lynch–Dahl's accuracy.
