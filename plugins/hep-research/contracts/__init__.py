"""Versioned research contracts of the hep-research plugin (single canonical location)."""
CONTRACTS_VERSION = "2.2.0"
# Capabilities this reader implements; an artifact whose required_capabilities lists any other is rejected (F08).
# stats:result-semantics (2.2.0): the artifact relies on the statistical-result semantic rules (contracts.validate,
# _stat_semantics); a 2.1 reader does not implement them and must refuse it rather than read it under weaker rules.
KNOWN_CAPABILITIES = frozenset({"core:plugin-release-identity", "core:data-exposure", "stats:result-semantics"})
