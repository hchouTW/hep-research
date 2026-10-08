"""Versioned research contracts of the hep-research plugin (single canonical location)."""
CONTRACTS_VERSION = "2.1.0"
# Capabilities this reader implements; an artifact whose required_capabilities lists any other is rejected (F08).
KNOWN_CAPABILITIES = frozenset({"core:plugin-release-identity", "core:data-exposure"})
