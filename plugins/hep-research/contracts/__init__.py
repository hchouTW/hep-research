"""Versioned research contracts of the hep-research plugin (single canonical location)."""
CONTRACTS_VERSION = "2.11.0"
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
# 2.7.0 adds three capabilities for the agentic-architecture sidecars (task P3.4) and the validator warning
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
# minor, response hardening (hep-detector audit) and communication result types (hep-communication audit).
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
KNOWN_CAPABILITIES = frozenset({"core:plugin-release-identity", "core:data-exposure", "stats:result-semantics",
                                "communication:traceability-v1", "core:revocation-log", "core:exposure-record",
                                "core:decision-lineage", "measurement:correction-keys-v1"})
