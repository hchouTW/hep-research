# Detector domain card (owner: hep-detector): simulator calibration

Questions for a simulator-calibration contract and result (Part B of the simulator calibration workflow, §13
"Review"): does the stage graph fit the detector type; is every parameter bound where the simulator can change it;
are references placed and converted as declared; are external inputs sourced; are the model discrepancy and the
alternative hypotheses declared from physics rather than from the outcome? The gates, intervals and validation
statistics are statistics obligations (the [statistics card](statistics.md)); the detector-type pages are in
hep-detector `references/simulation-calibration/` and are advisory.

| Field | Content |
|---|---|
| Typical required material | the locked contract and plan; the outputs of `hep-statistics/scripts/calib_contract.py check` (with `--model-documents` for g4sim), `hep-statistics/scripts/calib_chain.py check`, `p4` and `candidates`; the detector-type page; sources of every φ and of the control samples |
| Methods | assumption and convention check; reproduction (rerun the checker and the chain derivation on the locked files); counterexample (a parameter or reference the graph cannot carry) |
| Evidence | the element named (node, edge, parameter, binding pointer, reference id), the script output with its contract hash |
| Do not confuse | a checker that accepts with a physically right graph; an advisory table of the detector-type page with a declared value; P4 (necessary) with identifiability (P3, G5) |
| decision_required | usually true for the stage graph and the parameter binding |

## Calibration review obligation template

Each row fills one obligation of a review plan (`question`, `criterion`, `required_methods`,
`evidence_requirements`; `targets` are the contract and plan; `required` true unless marked).

| Id | Question | Criterion | Required evidence |
|---|---|---|---|
| cal-graph | Does the stage graph match the type's stage mapping, split at every injection point? | each node's kernel nature declared; every reference on an edge; departures from the type page justified | contract `stage_graph`, `hep-statistics/scripts/calib_chain.py check` output |
| cal-binding | Is every θ and φ bound to a field the simulator reads? | each binding in a row of §11.4 Table 2; candidates derived, not chosen by hand | `hep-statistics/scripts/calib_chain.py candidates` output |
| cal-references | Can each θ be reached, and does each injection state its conversion? | P4 passed; conversion parameters are φ with a source | `hep-statistics/scripts/calib_chain.py p4`, the references |
| cal-control | Are the control samples independent of the measurement with provenance? | no tuning toward the expected signal; samples traced to raw units | data-release lineage, sample definitions |
| cal-external | Is each φ sourced and each ψ negligible? | a source per φ; ψ passes the D37 bound | the φ sources, the `--design` check |
| cal-discrepancy | Are f, C, ℓ declared from physics? | declared before opening the validation data; never revised after a G6 outcome; a literature value carries a verified citation | contract versions, citations (hep-citations) |
| cal-alternatives | Are the alternative hypotheses simulation settings with an observable? | at least one when validation is not `none`; no parameter shift | `validation.alternatives` |
| cal-approximations | Are the simulator's declared approximations handled? | the §5.4 table (spot checks at the k_B and r extremes, multi-component scintillation, map versus optical tracking) applied | P0/P6 spot-check records |
| cal-identity | Were the model identity items recomputed from the documents? (optional when `deferred` is recorded) | no `IDENTITY_UNVERIFIED` left at lock | `hep-statistics/scripts/calib_contract.py check --model-documents` output |

## Positive case (supported)

The ECAL example of hep-detector (`assets/simulation-calibration/ecal.binding.example.json`, completed by an
instance) is accepted by the checker, P4 passes, every parameter has a candidate, and the instance's f, C, ℓ are
declared with a physics basis before opening. Expected: `cal-graph`, `cal-binding`, `cal-references` `supported`.

## Negative case (violated)

Version 2 of a contract raises the correlation length ℓ of the location group after version 1 failed G6, with no
new physics basis; the checker accepts both versions. Expected: `cal-discrepancy` `violated`, the finding naming
the two contract hashes and the changed field (§5.4: correlation lengths are never chosen to make G6 pass).

## Missing input

A φ (dead-material thickness) has `source` "survey" with no record. Expected: `cal-external` `undetermined`, the
missing record named.
