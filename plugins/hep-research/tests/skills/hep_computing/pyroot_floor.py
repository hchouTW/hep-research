"""The Python floor for PyROOT test interpreters: ROOT tests use an external interpreter ($HEP_ROOT_PYTHON, the Python
next to root-config, ...), and a run under one older than the plugin's floor is not supported evidence."""
import subprocess

FLOOR = (3, 13)  # pyproject.toml requires-python


def meets_floor(python: str) -> bool:
    """True when `python` runs and reports a version at or above FLOOR."""
    try:
        proc = subprocess.run([python, "-c", "import sys; print(*sys.version_info[:2])"], capture_output=True,
                              text=True, timeout=60)
        major, minor = (int(x) for x in proc.stdout.split()[:2])
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False
    return proc.returncode == 0 and (major, minor) >= FLOOR
