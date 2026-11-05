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
CURRENT_HEADERS = HERE.parents[2] / "assets" / "g4sim"
# The call goes in the master's run start. Newer sources have a probe call to stand next to; older ones have neither the probe
# nor the g4sim/ headers, so the call opens BeginOfRunAction, guarded by the master thread (Section 7.4).
PROBE_SITES = {"layered_sim": "void RunAction::WriteProbe() const {\n",
               "element_sim": "    g4sim::ProbeResult res = g4sim::RunProbe(\"element_sim: master"}
RUN_START = "void RunAction::BeginOfRunAction(const G4Run*) {\n"
FIRST_INCLUDE = '#include "Actions.hh"\n'
INCLUDE_LINE = "target_include_directories({program} PRIVATE ${{CMAKE_CURRENT_SOURCE_DIR}}/../g4sim)\n"


def _call(text: str, program: str, path: Path) -> str:
    site, call = PROBE_SITES[program], f'g4proto::Record("{program}");\n'
    if text.count(site) == 1:
        return text.replace(site, site + "  " + call if program == "layered_sim" else "    " + call + site)
    if text.count(RUN_START) == 1:
        return text.replace(RUN_START, RUN_START + f"  if (G4Threading::IsMasterThread()) {call}")
    raise ValueError(f"{path}: no single call site; this source version needs its own patch")


def apply(program: str, assets: Path, destination: Path) -> Path:
    """assets is the program's folder as recorded: the plugin's, or one extracted with git archive at the run's commit."""
    if program not in PROBE_SITES:
        raise ValueError(f"{program!r} is not an old program")
    shutil.copytree(assets / program, destination / program)
    headers = destination / "g4sim"
    if (assets / "g4sim").is_dir():
        shutil.copytree(assets / "g4sim", headers, dirs_exist_ok=True)
    else:
        headers.mkdir(parents=True, exist_ok=True)
    if (assets / "simroot").is_dir():  # element_sim's CMakeLists.txt also builds simroot from the next folder
        shutil.copytree(assets / "simroot", destination / "simroot", dirs_exist_ok=True)
    for header in CURRENT_HEADERS.glob("*.hh"):  # a source's own older headers stay; only what it lacks comes from the plugin
        if not (headers / header.name).exists():
            shutil.copy(header, headers / header.name)
    shutil.copy(HERE / "ProbeHook.hh", headers / "ProbeHook.hh")
    actions = destination / program / "Actions.cc"
    text = actions.read_text(encoding="utf-8")
    if text.count(FIRST_INCLUDE) != 1:
        raise ValueError(f"{actions}: no single first include")
    text = _call(text, program, actions).replace(FIRST_INCLUDE, FIRST_INCLUDE + '#include "ProbeHook.hh"\n')
    actions.write_text(text, encoding="utf-8")
    cmake = destination / program / "CMakeLists.txt"
    build = cmake.read_text(encoding="utf-8")
    if "../g4sim" not in build:
        cmake.write_text(build + INCLUDE_LINE.format(program=program), encoding="utf-8")
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
