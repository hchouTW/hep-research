---
role: Lead Auditor for detector simulation
skill: hep-detector
archetype: adversarial-audit
candidate_artifact: a Geant4 note on a silicon sensor with a neutron converter that calls its results validated
---

Illustrative example: the note, its numbers and its sensor are invented and name no experiment. Each flaw is mapped to
the rule, gate or benchmark that catches it in [the Geant4 study protocol](../references/geant4-study-protocol.md).

## 1. Initial Candidate Artifact

A two-page note, "Geant4 simulation of a silicon sensor with a converter layer: validated", reports:

- thermal-to-1 MeV neutron capture rates in a boron-loaded converter in front of 300 um of silicon, simulated with
  `FTFP_BERT`;
- the energy deposit of 100 MeV protons in the silicon, "agreeing with Bethe to 0.6 %";
- a production cut of 0.7 mm, "chosen because it gives the best agreement of the deposit with the expectation";
- reference densities and mean excitation energies "taken from the Geant4 material printout of the run";
- mean deposits read from the run's histogram summary (range 0 to 200 keV);
- one run per configuration, no scan of cuts or step limits;
- references written from memory, no literature record.

It asks for the label `validated-in-scope`.

## 2. Attack Vectors & Stress-Tests

Attack Vector 1: low-energy neutron physics. Below 20 MeV the data-driven neutron models and G4NDL are only in the
`_HP` lists; `FTFP_BERT` uses cross-section tables and a cascade model there. Caught by rule `G4R-HP-NEUTRON`
(`check_geant4_study.py spec`, severity error).

Attack Vector 2: the cut was tuned on the analysis observable. A cut chosen for agreement hides a cut dependence
instead of showing convergence. Caught by the convergence gate (`check_geant4_study.py run`) and rule
`G4R-THIN-CUT-SCAN`, which require a declared cut scan whose two finest settings agree within tolerance.

Attack Vector 3: deposit compared with Bethe. Bethe is the mean energy loss; delta rays leave a thin layer, so the
deposit is lower (in the official 20 um silicon example the mean deposit corresponds to 1.363 MeV cm2/g against a full
dE/dx of 2.028). The `stopping-power` benchmark of `geant4_benchmarks.py` uses E_in - E_exit of transmitted primaries.

Attack Vector 4: reference inputs from the Geant4 material dump. An error in the material definition then enters the
reference too and cancels. `geant4_benchmarks.py` refuses a material with `reference_origin` `geant4-material-dump`,
and `check_geant4_study.py label` lists it as a gap.

Attack Vector 5: a histogram range that truncates the mean. Histogram means count in-range entries only; the delta-ray
tail above 200 keV is dropped. The benchmarks read per-event CSV values, never histogram summaries (protocol,
section 5).

Attack Vector 6: no convergence scan. With one run per configuration the convergence gate reports `not-run` and fails;
the study record lists the gap.

Attack Vector 7: citations not in a literature record. hep-authoring's `check_citations.py` reports each citation
without a record as `not-verified` (exit 3).

## 3. Concrete Counter-Example / Exploit Proof

The 0.6 % agreement is an artefact of attack vectors 2, 3 and 4 acting together: the deposit lies below the mean loss,
and the coarse cut was chosen to bring it back up to a Bethe value computed from the same material table. Rerun with
the protocol settings (cut scan 0.1, 0.03, 0.01 mm; energy loss instead of deposit; PDG inputs), the deposit over the
mean loss of transmitted primaries is below one while the energy loss itself agrees with Bethe, which is what the
benchmark tests. The J14 replay (run inside `examples/geant4-thin-silicon`; output abridged) shows the separation on real Geant4 11.4.3 runs (100 MeV protons, 300 um silicon,
cut 0.01 mm):

```console
$ python3 ../../skills/hep-detector/scripts/geant4_benchmarks.py run --config output/benchmarks-sp.config.json
  "benchmark": "stopping-power",
  "geant4": 13.6056,                      # MeV/cm, mean (E_in - E_exit) / thickness of transmitted primaries
  "reference_value": 13.6309,             # Bethe at the mean energy, PDG inputs
  "relative_difference": -0.00185,
  "mean_deposit_over_mean_loss": 0.98857  # the deposit is 1.1 % below the energy loss
```

The highest usable label of the note is `unvalidated`, and the request for `validated-in-scope` is
refused: `check_geant4_study.py label --upgrade` re-issues a study only with a passed reference benchmark whose
negative control was caught, a passed convergence gate, its scope inside the benchmark scope and no gap left, and the
contract rule (`geant4.upgrade_*`, contracts 3.1.0) refuses a hand-made relabel.

## 4. Hardened Architectural Patch

```diff
- "physics": {"layered_sim_spec": "specs/note.json"}          # FTFP_BERT, cut 0.7 mm tuned on the observable
+ "physics": {"layered_sim_spec": "specs/neutrons-hp.json",    # QGSP_BIC_HP for the converter study
+             "justification": [{"choice": "QGSP_BIC_HP", "reason": "neutrons below 20 MeV",
+                                "source": "geant4:source/physics_lists/constructors/hadron_inelastic/src/G4HadronPhysicsQGSP_BIC_HP.cc"}]}
+ "convergence_plan": {"parameters": [{"name": "physics.default_cut_mm", "values": [0.1, 0.03, 0.01]}],
+                      "observables": ["mean_deposit_MeV", "tail_fraction"],
+                      "tolerance_relative": {"mean_deposit_MeV": 0.01, "tail_fraction": 0.1}}
- "materials": [{"name": "Si", "density_g_cm3": 2.33, "reference_source": "Geant4 material printout"}]
+ "materials": [{"name": "Si_study", "density_g_cm3": 2.329, "z_over_a": 0.498478, "mean_excitation_eV": 173.0,
+                "sternheimer": {"a": 0.1492, "k": 3.2546, "x0": 0.2015, "x1": 2.8716, "Cbar": 4.4355, "delta0": 0.14},
+                "reference_source": "PDG Atomic and Nuclear Properties, silicon, 2024 edition",
+                "reference_origin": "independent"}]
+ "validation_plan": {"benchmarks": [{"name": "stopping-power", "grade": "reference"}], "scope": {"particle": "proton",
+                     "energy_MeV": [100.0, 100.0], "material": "Si_study", "thickness_mm": [0.3, 0.3],
+                     "observable": "mean stopping power", "beta_gamma": 0.4719}}
```

The per-event CSV replaces the histogram summary, and the references come from a hep-citations literature record.

## 5. Proof of Robustness Post-Fix

- `check_geant4_study.py spec` on the patched spec: no error rule fires; `G4R-HP-NEUTRON` is satisfied by the `_HP`
  list.
- `check_geant4_study.py run`: the gate compares the two finest cuts and passes only if the change is within
  tolerance and resolved.
- `geant4_benchmarks.py run`: `stopping-power` uses the energy loss, its negative control (density raised by the
  claimed detection limit on the Geant4 side) fails as it must.
- `check_geant4_study.py label --write`: the study record carries `unvalidated`, embeds benchmarks, convergence and
  scope, and lists any remaining gap; it passes `validate.py --strict` and `dependencies.py`.
- `check_citations.py` on the revised note: every citation is found in the literature record.
