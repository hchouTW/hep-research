"""Versioned research contracts of the hep-research plugin (single canonical location)."""
CONTRACTS_VERSION = "2.6.0"
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
KNOWN_CAPABILITIES = frozenset({"core:plugin-release-identity", "core:data-exposure", "stats:result-semantics",
                                "communication:traceability-v1"})
