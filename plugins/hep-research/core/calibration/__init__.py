"""Simulator parameter calibration workflow (docs/dev/simulator-calibration/, Part B): the engine library behind the
calib_*.py scripts of skills/hep-statistics/scripts. Each check of Part B section 14 is implemented once, in the module
of the script that owns it (chain: calib_chain; contract: calib_contract check; deps: calib_deps; use: calib_use; data:
calib_data); other modules call it, never copy it. Standard library only (NumPy for the kernel check). Steward:
core/OWNERS.json."""
