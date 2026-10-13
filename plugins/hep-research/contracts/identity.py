"""Code identity of the installed plugin (AGENTIC-R5 T0.2/T0.3): the public import path. The implementation is
core/protected/identity.py (the protected-use guard in core needs it, and core never imports contracts); see its
docstring for the release bundle, the manifest format and plugin_release()."""
from core.protected.identity import (CACHE_DIRS, FORMAT, RECORDS, ROOT, UNKNOWN, RefusedFile, _git_files,  # noqa: F401
                                     _plugin_release, _walk_files, bundle_files, digest_of, entry, generate,
                                     plugin_release, verify)
