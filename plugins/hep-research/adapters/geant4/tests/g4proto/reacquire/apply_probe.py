#!/usr/bin/env python3
"""Make a re-acquisition copy of an old program (g4sim plan, Section 7.4): its sources and the shared headers in a separate
folder, plus ProbeV2 and one call line in the master's BeginOfRunAction. The program in the plugin is never modified.

Usage: apply_probe.py PROGRAM ASSETS_DIR DESTINATION   PROGRAM is layered_sim or element_sim. Prints JSON with a status key.
Exit 0 ok, 2 bad input or a source with no known call site.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CALL_SITES = {"layered_sim": "void RunAction::WriteProbe() const {\n",
              "element_sim": "    g4sim::ProbeResult res = g4sim::RunProbe(\"element_sim: master"}
INCLUDE_SITE = '#include "SimProbe.hh"\n'


def apply(program: str, assets: Path, destination: Path) -> Path:
    if program not in CALL_SITES:
        raise ValueError(f"{program!r} is not an old program")
    shutil.copytree(assets / program, destination / program)
    shutil.copytree(assets / "g4sim", destination / "g4sim", dirs_exist_ok=True)
    if (assets / "simroot").is_dir():  # element_sim's CMakeLists.txt also builds simroot from the next folder
        shutil.copytree(assets / "simroot", destination / "simroot", dirs_exist_ok=True)
    shutil.copy(HERE / "ProbeHook.hh", destination / "g4sim" / "ProbeHook.hh")
    actions = destination / program / "Actions.cc"
    text = actions.read_text(encoding="utf-8")
    site = CALL_SITES[program]
    if text.count(site) != 1 or text.count(INCLUDE_SITE) != 1:
        raise ValueError(f"{actions}: no single call site; this source version needs its own patch")
    call = f'g4proto::Record("{program}");\n'
    patched = site + "  " + call if program == "layered_sim" else "    " + call + site
    text = text.replace(site, patched).replace(INCLUDE_SITE, INCLUDE_SITE + '#include "ProbeHook.hh"\n')
    actions.write_text(text, encoding="utf-8")
    return destination / program


def main(argv) -> int:
    if len(argv) != 4:
        print(json.dumps({"status": "rejected", "message": __doc__.splitlines()[-2]}))
        return 2
    try:
        built = apply(argv[1], Path(argv[2]), Path(argv[3]))
    except (OSError, ValueError) as err:
        print(json.dumps({"status": "rejected", "message": str(err)}))
        return 2
    print(json.dumps({"status": "ok", "source": str(built)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
