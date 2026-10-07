#!/bin/sh
# LCG view on CVMFS: STARTING TEMPLATE (status: documented, not run here: no CVMFS on the machine it was written on).
# Source it, do not execute it:  . lcg_view_setup.sh
# An LCG view gives a consistent ROOT, Python and scientific stack from /cvmfs/sft.cern.ch. Choose the release and the
# platform your site supports (ls /cvmfs/sft.cern.ch/lcg/views/), record both with every run, and pin them here.
LCG_VERSION="<LCG_RELEASE>"          # for example LCG_106
LCG_PLATFORM="<PLATFORM_TAG>"        # for example x86_64-el9-gcc13-opt
VIEW="/cvmfs/sft.cern.ch/lcg/views/${LCG_VERSION}/${LCG_PLATFORM}/setup.sh"
if [ ! -r "$VIEW" ]; then
  echo "lcg_view_setup.sh: $VIEW not found (is CVMFS mounted, and do the release and platform exist?)" >&2
  return 1 2>/dev/null || exit 1
fi
. "$VIEW"
export LCG_VERSION
# Record what you got, next to the run's outputs:
#   python3 <plugin root>/skills/hep-computing/scripts/environment_manifest.py record --out environment.json
