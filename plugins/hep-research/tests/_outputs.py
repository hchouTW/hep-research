"""Comparing a fresh run with committed output: the plugin version that wrote a file records provenance, not a result,
so a release does not regenerate outputs (docs/maintenance.md). Everything else stays compared."""


def without_plugin_version(doc):
    """doc without any versions.plugin and without a top-level plugin_version; the input is not changed."""
    def strip(node):
        if isinstance(node, dict):
            return {k: ({x: strip(y) for x, y in v.items() if x != "plugin"} if k == "versions" and isinstance(v, dict)
                        else strip(v)) for k, v in node.items()}
        return [strip(v) for v in node] if isinstance(node, list) else node
    out = strip(doc)
    if isinstance(out, dict):
        out.pop("plugin_version", None)
    return out
