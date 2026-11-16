"""Simulator parameter calibration workflow (docs/dev/simulator-calibration/, Part B): the engine library behind the
simcal_*.py scripts of skills/hep-statistics/scripts. Each check of Part B section 14 is implemented once, in the module
of the script that owns it (chain: simcal_chain; contract: simcal_contract check; deps: simcal_deps; use: simcal_use; data:
simcal_data); other modules call it, never copy it. Standard library only (NumPy for the kernel check). Steward:
core/OWNERS.json."""
