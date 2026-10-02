"""Locate the plugin root from this file, independent of cwd and of ${CLAUDE_PLUGIN_ROOT}.

Scripts elsewhere in the plugin use the same idiom inline (they cannot import this module
before the root is on sys.path):

    ROOT = next(p for p in Path(__file__).resolve().parents
                if (p / ".claude-plugin" / "plugin.json").is_file())
    sys.path.insert(0, str(ROOT))
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MANIFEST = Path(".claude-plugin") / "plugin.json"


def plugin_root(start: str | Path | None = None) -> Path:
    """Return the nearest ancestor of `start` (default: this file) holding the plugin manifest."""
    here = Path(start or __file__).resolve()
    for p in [here, *here.parents]:
        if (p / MANIFEST).is_file():
            return p
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env and (Path(env) / MANIFEST).is_file():
        return Path(env)
    raise RuntimeError(f"hep-research plugin root not found above {here}")


def ensure_on_path(start: str | Path | None = None) -> Path:
    root = plugin_root(start)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root
