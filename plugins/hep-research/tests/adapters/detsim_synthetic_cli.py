"""detsim.py with the simulator-free synthetic backend, as a separate controller process (tests only).

The lock, orphan and interruption tests need detsim controllers that are processes of their own: this file runs
detsim.main(argv, backends={"synthetic": detsim_backend_synthetic}) and exits with its code.
"""
import os
import signal
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
for entry in (str(PLUGIN), str(PLUGIN / "adapters" / "detector-simulation" / "assets"), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)
sys.dont_write_bytecode = True

import detsim  # noqa: E402
import detsim_backend_synthetic  # noqa: E402

CRASH = os.environ.get("DETSIM_TEST_CRASH")  # crash injection: before_commit or after_rename -> SIGKILL itself
if CRASH:
    import detsim_run  # noqa: E402
    detsim_run.HOOKS[CRASH] = lambda *paths: os.kill(os.getpid(), signal.SIGKILL)

if __name__ == "__main__":
    sys.exit(detsim.main(sys.argv[1:], backends={"synthetic": detsim_backend_synthetic}))
