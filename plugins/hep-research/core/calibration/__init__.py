"""Deprecated alias of `core.simcal` (simcal rename, hep-research 0.70.0; removed in 0.72.0).

The simulator parameter calibration workflow (simcal) moved from `core.calibration` to `core.simcal`. Importing this
package warns once (DeprecationWarning) and makes every `core.calibration.<m>` the same module object as
`core.simcal.<m>`, so old imports and `isinstance` checks keep working. See docs/dev/simcal-naming-map.md.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
import warnings

import core.simcal as _simcal
from core.simcal import *  # noqa: F401,F403  (the package's public names, if any)

_ALIAS_PACKAGE, _SIMCAL_PACKAGE = __name__, "core.simcal"

warnings.warn("core.calibration is deprecated: use core.simcal (removed in hep-research 0.72.0)", DeprecationWarning,
              stacklevel=2)


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, target: str):
        self.target = target

    def create_module(self, spec):
        module = importlib.import_module(self.target)
        self.alias, self.spec = spec.name, module.__spec__     # importlib sets module.__spec__ to the alias spec next
        return module

    def exec_module(self, module):
        module.__spec__ = self.spec                     # keep the core.simcal module's own spec
        sys.modules[self.alias] = module                # the alias name points at the core.simcal module object


class _AliasFinder(importlib.abc.MetaPathFinder):
    """Finds core.calibration.<m> as the module object of core.simcal.<m>."""

    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith(_ALIAS_PACKAGE + "."):
            return None
        simcal_name = _SIMCAL_PACKAGE + fullname[len(_ALIAS_PACKAGE):]
        if importlib.util.find_spec(simcal_name) is None:
            return None
        return importlib.util.spec_from_loader(fullname, _AliasLoader(simcal_name))


if not any(isinstance(f, _AliasFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _AliasFinder())

__path__ = list(_simcal.__path__)       # submodule lookups go through the finder above first
