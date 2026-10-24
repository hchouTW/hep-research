"""Versioned research contracts of the hep-research plugin (single canonical location)."""
CONTRACTS_VERSION = "3.13.0"
# Capabilities this reader implements; an artifact whose required_capabilities lists any other is rejected (F08).
# stats:result-semantics (2.2.0): the artifact relies on the statistical-result semantic rules (contracts.validate,
# _stat_semantics); a 2.1 reader does not implement them and must refuse it rather than read it under weaker rules.
# communication:traceability-v1 (2.3.0): the communication extension carries claims with evidence edges, document occurrences
# and support assessments (contracts/schemas/ext_communication_traceability.json, contracts.communication); a reader
# without it would read the record under the legacy rules and miss the claim-scoped provenance.
# 2.4.0 adds response semantics (contracts.validate, _response_semantics) and optional response fields; no capability:
# the new rules only refuse inconsistent declarations, and a 2.3 reader of a 2.4 response misreads no field.
# 2.5.0 adds ml-artifact semantics (contracts.validate, _ml_semantics) and optional ml-artifact fields (split-overlap
# result, structured weights, domain_shift, environment, output_semantics); no capability: the new rules only refuse
# incomplete or inconsistent declarations, and a 2.4 reader rejects a structured 'weights' object (its schema expects
# a string) instead of misreading it.
# 2.6.0 adds theory-spec and prediction semantics (contracts.validate, _theory_semantics, THEORY_SEMANTICS_FROM) and
# optional fields (theory-spec limit, neglected, computational_run_ref, degenerate_directions, model.family,
# checks_run[].tolerance, references_read[].date_read; prediction derivation_status; uncertainty prescription, method,
# bounds); no capability: the new rules only refuse incomplete or inconsistent declarations, and a 2.5 reader of a
# 2.6 theory-spec rejects the new top-level fields (additionalProperties) instead of misreading them.
# 2.6.0 also adds measurement-spec semantics (contracts.validate, _measurement_semantics, MEASUREMENT_SEMANTICS_FROM) and
# optional measurement-spec fields (estimand, background control_region/constraint/closure, blinding mask,
# no_backgrounds_reason, correction exact_zero); no capability: the new rules only refuse incomplete or inconsistent
# declarations, and a 2.5 reader of a 2.6 measurement-spec misreads no field.
# 2.6.0 also adds statistical-result hardening rules (contracts.validate, _stat_hardening and _bayesian_hardening, constant
# STAT_HARDENING_FROM; hep-statistics hardening STH-T1) and optional statistical-result fields (extension.seeds,
# coverage.seed, goodness_of_fit.p_value_bound, significance.convention; ext_statistical_result_v2_6.json); no
# capability: the rules only refuse inconsistent or incomplete results, and a 2.5 reader accepts the new optional
# keys without misreading any field (it simply does not apply the new rules). Other rule families joining 2.6.0 add
# their own *_SEMANTICS_FROM constant and helper.
# 2.7.0 adds three capabilities for the protected-data sidecars (task P3.4) and the validator warning
# exposure.capability_not_declared; no other rule changes, so a 2.6 artifact keeps its outcome under a 2.7 reader, and
# a 2.6 reader refuses a 2.7 artifact that requires one of the new capabilities (and warns on, or in protected use
# refuses, the newer minor). core:revocation-log: the artifact's status
# depends on the hash-chained revocation log and head (contracts.revocation); core:exposure-record: its data_exposure is
# derived from an exposure record (contracts.lineage.derive_exposure, record_ref); core:decision-lineage: it is bound to
# decision records (contracts.lineage.check_decision).
# Not added (decision of 2026-10-14, task P3.4): core:formal-use-permit and core:analysis-bundle. Permits and bundles
# are sidecars read as protected inputs and verified by contracts.permit and contracts.analysis_bundle; no artifact
# declares a dependency on them. Add an ID when an artifact type starts to require one.
# 2.8.0 adds rule families that only refuse false or incomplete declarations, each with its own *_FROM constant and
# helper in contracts.validate: ml-artifact semantics v2 (ML_SEMANTICS_V2_FROM; hep-ml audit) and, joining the same
# minor, response hardening (hep-detector audit) and communication result types (audit of the communication skill, now hep-authoring).
# New fields are optional and no capability is added: a 2.7 reader misreads no new field, it only does not apply the
# new rules. Older artifacts get the new rules under --strict and at the gate.
# Response hardening (contracts.validate, _response_hardening, RESPONSE_HARDENING_FROM; hep-detector audit DR-WP2)
# adds the overlay ext_response_v2_8.json (underflow_overflow enum, underflow/overflow vectors, correction_space, mc_stat,
# systematic_variations, periods) and rules R1-R10; contracts.response_adapter treats a missing underflow_overflow of a
# 2.8.0 artifact as an error. A 2.7 response that passed keeps its default outcome.
# 2.9.0 (hep-research 0.11.0) renames four skills: provenance.producer_skill and profile related_skills take the names
# of contracts/schemas/skill_names.json, which also keeps the four old names as deprecated aliases (contracts.skill_names).
# An old name is a warning (skill.deprecated_name, profile.deprecated_skill_name), an error under the version and name
# policy (--strict-versions, protected use); contracts/migrate_skill_names.py rewrites producer_skill and
# handoff.to_skill. No capability and no other rule change: a 2.8 artifact keeps its outcome apart from that warning,
# and a 2.8 reader rejects a new skill name in producer_skill (schema enum) instead of misreading it.
# 2.10.0 (v6.3 analysis-check programme) adds the capability measurement:correction-keys-v1 (D05a): a measurement-spec
# correction may carry the R4 correction keys (target_scope, calibration_digest, variation_id, stage) and
# application_id; contracts.validate knows and checks them only under this capability, so a spec without it keeps its
# findings and a reader without it refuses the spec instead of reading the keys as unknown. It also adds sidecar
# formats read only by contracts.analysis_check and its readers (analysis bundle /2, check context, semantic lock,
# check report, validation record, effect catalog, operator coverage, rule registry); no artifact type changes, and a
# 2.9 artifact keeps its outcome under a 2.10 reader. The checks are advisory and in shadow mode.
# 2.11.0 (v6.3 M2b model part, D12b, M2c) adds sidecar formats only: the analysis bundle mode "model" with model-card
# items and the model context fields (models, evaluations, model_roots, the observes binding), the pairing contract
# contracts/semantics/model_pairings.json, the result binding (contracts/schemas/result_binding.json) and the
# post-execution report fields. No artifact type changes and no capability is added; a 2.10 artifact keeps its outcome,
# and a 2.10 reader refuses the new bundle mode and context fields (schema enum, additionalProperties).
# 2.12.0 (upgrade plan v1.3, batches 0a-D) adds vocabulary and optional fields only: the levels top-of-instrument and
# top-of-atmosphere; the artifact statuses projection and outside-validated-range (the publication gate refuses both,
# the second unless a validation record is attached); the effects cutoff_transmission, survival and
# fragmentation_feeddown and the composition exposure_acceptance_livetime_transmission, with coverage entries; the
# optional measurement-spec fields systematics[].scaling, systematics[].era_correlation, eras[] and
# coupled_backgrounds; the profile kind reference. No capability is added; a 2.11 artifact keeps its outcome, and a
# 2.11 reader refuses the new labels, fields and profile kind (schema enums, additionalProperties).
# 2.13.0 (split of the communication skill into hep-citations and hep-authoring) adds the artifact type
# literature-record (contracts/schemas/ext_literature_record.json; rules in contracts.validate, _literature_semantics):
# the record manage_literature.py wrote before, unchanged in content, now inside the envelope so a literature handoff to
# hep-authoring validates instead of failing as artifacts_dir.not_artifact. It also adds the skill names hep-citations
# and hep-authoring; the communication skill's name becomes a deprecated alias of hep-authoring, and so does its 0.11.0
# predecessor (contracts.skill_names). No capability is added; a 2.12 artifact keeps its outcome apart from the alias
# warning, and a 2.12 reader refuses the new type and the new skill names (schema enums) instead of misreading them.
# 3.0.0 (hep-research 0.17.0) retires the deprecated skill names (the four of 2.9.0 and the one of 2.13.0):
# the schema enum lists only the eight current names, and contracts.skill_names reports a retired name in an artifact
# or a profile, and any unknown handoff.to_skill, as skill.unknown_name (an error, with or without --strict-versions).
# contracts/migrate_skill_names.py is removed; old files are migrated with hep-research 0.16.x. Major, because removing
# enum values turns artifacts that validated under 2.x into errors (docs/architecture.md section 5). No other rule
# changes: a 2.x artifact with current names keeps its outcome, and older contract versions are still read.
# 3.0.1 (hep-research 0.18.0, patch) fixes how ml.calibration_on_fit_sample compares sample names: '.' segments
# anywhere and repeated or trailing separators are dropped (was a leading './' only), so a calibration evaluated on its
# fit sample written as 'work/./x.csv' is the error it always should have been (sci-fix SAMPLE-NAME-DOT-SEGMENTS). No
# field, enum or capability changes.
# 3.1.0 (hep-research 0.20.0, Geant4 phase 2) adds the optional computational-run field extension.evidence_records
# (run records referenced by path and hash without inheriting their labels; resolved and checked by
# contracts/dependencies.py: hash, exit_status 0, no 'failed', output hashes) and the capability core:evidence-records
# that an artifact using it must require; and the rule family _study_upgrade (GEANT4_UPGRADE_FROM): a computational-run
# with Geant4 study material (extension.study, extension.simulation or evidence_records) that carries
# validated-in-scope needs a study block with a passed reference benchmark whose negative control was caught, a passed
# convergence gate, a declared scope inside that benchmark's scope, and evidence records. Other computational-runs are
# unaffected (none in the plugin carries validated-in-scope). A 3.0 reader refuses an upgraded record through the
# capability instead of reading it as validated without checking its evidence.
# 3.2.0 (Geant4 follow-up) adds the dataset status 'simulated' (vocab dataset_statuses) and the rule family
# dataset.simulated_* (contracts.validate._simulated_dataset): a simulated dataset-record needs its run or study records
# as inputs, is never 'observed', keeps 'unvalidated' unless an input carries 'validated-in-scope', and is at level
# detector or particle-fiducial; contracts/dependencies.py requires those inputs to be computational-runs with
# extension.simulation or extension.study (dataset.simulated_source) and warns when a communication uses a simulated
# table (communication.simulated_source). Additive: no capability, and a 3.1 reader refuses the new status as an
# unknown vocabulary term instead of misreading it.
# 3.3.0 (independent review, P1; docs/dev/independent-review-spec.md) adds the seven review schemas
# (contracts/schemas/review_config, review_units, review_manifest, review_record, review_event, review_head,
# review_observation) and contracts/review.py (their Python rules, the shared state table, decide and check). They
# are sidecar formats under <project>/reviews/, read only by contracts/review.py and the hep-authoring driver; no
# artifact type, vocabulary term or envelope field changes. No capability: no envelope artifact declares or embeds a
# review record and review files never live in an artifacts_dir, so no reader can misread one as an artifact; a 3.2
# reader keeps every artifact outcome and has no review reader at all. (The spec's "3.2.0" predates 0.21.0, which used
# 3.2.0 for simulated dataset-records.)
# 3.4.0 (independent review tuning; docs/dev/independent-review-spec.md sections 5.1, 5.5, 6.9, 7.5 and A2) adds the
# sidecar format review_filter_record 1.0.0 (contracts/schemas/review_filter_record.json, the filter_record.json of
# the optional filtering pass, with contracts.review.filter_record_rules and filter_receipt_codes), the event
# filter_needed, and two optional review_config fields: lens_models (the model of a lens's lens slot) and filter (the
# filtering pass's model). A configuration, log or record without them reads exactly as in 3.3.0. No capability: like
# every review file they live under <project>/reviews/, never in an artifacts_dir, and no artifact type, vocabulary
# term or envelope field changes; a 3.3 driver refuses a configuration with either field as config_out_of_range
# instead of ignoring it.
# 3.5.0 (sci-fix improvement plan A1, maintainer decision 2026-10-22) adds two optional envelope fields,
# provenance.code_paths (the plugin .py files loaded when the envelope was written) and provenance.code_tags (tags set
# by advisory-named shared functions), written by contracts/trace.py, so a sci-fix advisory can tell whether the
# affected code was loaded for an artifact. No capability: provenance has no additionalProperties limit, so a 3.4
# reader accepts and ignores both, and an artifact without them reads exactly as in 3.4.0.
# 3.6.0 (independent review; docs/dev/independent-review-spec.md sections 5.1, 5.3, 6.10, 7.6 and A8) adds the
# optional expert slot of round 1: the review_config field expert ({"model": M}), the review_record role expert (a
# record with claims, verdicts and findings but no skim, carry_forward or resolves, checked by contracts.review
# record_rules and receipt_codes with the reason code finding_without_verdict), and the optional round_started data
# key expert {slot_id, model}. A configuration, log or record without them reads exactly as in 3.5.0. No capability:
# like every review file they live under <project>/reviews/, never in an artifacts_dir, and no artifact type,
# vocabulary term or envelope field changes; a 3.5 driver refuses a configuration with expert as config_out_of_range
# and a record with role expert as schema_invalid instead of misreading either.
# 3.7.0 (cross-artifact check architecture Phase 0, release R1; docs/dev/cross-artifact-check/decision-phase0.md)
# moves the rule registry to registry_version 1.1.0: each new or changed rule records source_sha256, the
# function-level source digest of its implementation, and contracts/rule_registry.py fails when the code changes
# without a new rule version; V-case parts gain the slices P0-P2 and work packages P<phase>.<nn> and WP-R. The
# analysis check dispatches rules by (rule_id, version) and names its plugin_release in the report's assessment. No
# artifact type, vocabulary term, envelope field or capability changes: the registry, the check report and the
# bundle live outside an artifacts_dir, and a 3.6 reader refuses a 1.1.0 registry (schema enum) instead of misreading it.
# 3.8.0 (cross-artifact check Phase 2, releases R2 and R3 shipped together; docs/dev/cross-artifact-check/m2a-design.md)
# adds check-context 1.1.0 (no 'required'; paired with 1.1.0 suites), result binding 1.1.0 (campaigns[].inputs), the
# rule registry 1.2.0 (keyed by rule_id and version, retired versions kept), SemVer pre-release suite versions, the
# effect catalog 1.1.0 (description_required) and the stable 1.1.0 suites, now the default. The measurement
# vocabulary response_corrections gains cutoff_transmission, survival and fragmentation_feeddown (catalog effects it
# lacked). No artifact type, envelope field or capability changes. A 3.7 reader refuses a 1.1.0 check context, a 1.1.0
# result binding and a 1.2.0 registry as invalid input instead of misreading them (refusal-matrix.md).
# 3.9.0 (cross-artifact check value gate Shrink, architecture section 13.4; docs/dev/cross-artifact-check/
# decision-value-gate.md and refusal-matrix.md) removes sidecar formats: the result binding
# (contracts/schemas/result_binding.json), the model-card pairing contract (contracts/semantics/model_pairings.json and
# its schema), model-only analysis bundles (mode "model") and the model-card and run-lineage suites. Readers refuse
# them with the reason (bundle.removed, definition.suite_removed, permit.report_post_execution_removed). No artifact
# type, vocabulary term, envelope field or capability changes; check reports are pre-execution only.
# 3.10.0 (hadron structure, hep-theory Th14) adds 13 core convention keys (target_normalization, exchanged_bosons,
# electroweak_scheme, em_coupling, structure_function_signs, heavy_quark_scheme, factorization_scheme,
# target_mass_treatment, polarization_convention, xF_definition, rapidity_frame, azimuth_convention, log_accuracy) and
# the core vocabulary conditional_convention_keys listing them: the theory-spec completeness warning
# (theory.conventions_incomplete) skips them; the module that names a key requires it. Additive: a 3.9 reader warns on
# the new keys and its comparison gate treats them as not comparable. No artifact type, envelope field or capability
# changes.
# 3.11.0 (detector system design spec, M0; docs/architecture.md section 4) adds the artifact types design-spec,
# design-candidate and design-evaluation (contracts/schemas/ext_design_*.json; verdicts derived only by
# contracts/design.py with the adequacy table contracts/rules/design_adequacy.json), the core vocabulary subsystem_roles,
# the optional computational-run fields argv and script_sha256, tool contract 1.1.0 (positional arguments, config-file
# fields and the per-operation design block; contract_version 1.0.0 or 1.1.0) and decision record 1.1.0 (the six design
# categories, the seen marker 'not-applicable' and dispositions[], design categories only; record_version 1.0.0 or
# 1.1.0; contracts/lineage.py). No capability is added (the 2.13.0 literature-record precedent): a 3.10 reader refuses
# the new types, roles, run fields, sidecar versions and categories through the schema enums and additionalProperties
# instead of misreading them, and every 3.10 artifact, 1.0.0 tool contract and 1.0.0 decision record keeps its outcome.
# Detector design M1 extends the unreleased 3.11.0 (OQ-03): the tool contract 1.1.0 design block also has an
# uncertainty location and the expressions budget, object, zip, config (a generated config file) and span; no
# artifact field changes.
# Detector design M2 extends it again (OQ-03): the envelope inputs[].binding ("parameters", TRC-06), the
# computational-run parameter_digest (INC-02), the evaluation model_envelope (FID-05), the design-block keys
# upstream_directions and the expression input_artifact, and the geometry mapping table
# (contracts/rules/design_geometry.json, contracts/schemas/design_geometry.json). A 3.10 reader refuses the binding
# value (schema enum) instead of reading a parameter-bound input as a stale hash.
# Detector design M3 extends it again (OQ-03): the dataset-record optional design_measurement (F5), decision record
# 1.1.0 artifacts[] binding "parameters" with parameter_digest (measurement-acceptance only, DEC-06), and the
# expression parameters_all (CHN-14).
# Detector design M4 extends it once more (OQ-03): the computational-run optional scan_summary (OQ-18, AGG-08) and the
# design-spec comparison_basis.pareto_axes (CHN-06, RPT-07).
# 3.12.0 (minor; detector design follow-ups of the M3 reviews): design-spec requirements[].covered_by (a derived
# requirement names the driving one whose H4 disposition covers it, MAT-04 d) and constraints[].subsystems (the scope a
# hard constraint covers; a candidate lacking one cannot pass it); adequacy table 1.1.0 upstream_value_checks (the
# measured curvature offset must cover the offset a charge-confusion requirement assumes, ADQ-02).
# 3.13.0 (minor; CV-C1 of the Geant4 program, automated candidate generation): the computational-run optional
# search_summary of evaluate_design.py search (declared in ext_computational_run.json with hep-computing's agreement;
# field rules contracts/schemas/design_search_summary.json, applied from validate.SEARCH_SUMMARY_FROM or strict); the
# search spec schema design_search_spec.json (not an artifact); contracts/design.py exempts a search run from the
# orphan-run rule and refuses an evaluation that names one as its run (design.search_point_not_expanded). No
# capability: a 3.12 reader sees an unknown optional object and misreads no field. The number is the stage's
# placeholder (CV-C1); it is fixed at release in merge order with the other CV-* changes.
KNOWN_CAPABILITIES = frozenset({"core:evidence-records", "core:plugin-release-identity", "core:data-exposure", "stats:result-semantics",
                                "communication:traceability-v1", "core:revocation-log", "core:exposure-record",
                                "core:decision-lineage", "measurement:correction-keys-v1"})
