"""Comparing a fresh run with committed output: the plugin and contracts versions that wrote a file record provenance, not a
result, so neither a release nor a contracts bump regenerates outputs (docs/maintenance.md). Everything else stays compared."""

WRITER_KEYS = ("plugin", "contracts")
TOP_LEVEL_KEYS = ("plugin_version", "contract_version")


def without_writer_versions(doc):
    """doc without the versions that wrote it, in versions and at the top level; the input is not changed."""
    def strip(node):
        if isinstance(node, dict):
            return {k: ({x: strip(y) for x, y in v.items() if x not in WRITER_KEYS} if k == "versions" and isinstance(v, dict)
                        else strip(v)) for k, v in node.items() if k not in TOP_LEVEL_KEYS}
        return [strip(v) for v in node] if isinstance(node, list) else node
    return strip(doc)


def written_by_a_supported_contract(version: str, current: str) -> bool:
    """A committed output may be older than the contracts, within the same major version, and never newer."""
    written, now = (tuple(int(part) for part in text.split(".")) for text in (version, current))
    return written[0] == now[0] and written <= now
