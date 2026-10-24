#!/usr/bin/env python3
"""Shared helpers of the adapters/geant4 scripts (hashing, ~ paths, record skeletons, dataset environment, units).

Imported by geant4_build.py's siblings (geant4_run.py, geant4_examples.py, geant4_verify.py) from this folder; it
imports only the standard library, core and contracts. Run directly it only prints this help.
Exit codes: 0 (--help). Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
PLUGIN = Path(__file__).resolve().parents[3]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts import trace  # noqa: E402

ASSETS = Path(__file__).resolve().parent
# dataset variables Geant4 11.4 reads (cmake/Modules/G4DatasetDefinitions.cmake) and the search root
DATA_VARS = ("G4NEUTRONHPDATA", "G4LEDATA", "G4LEVELGAMMADATA", "G4RADIOACTIVEDATA", "G4PARTICLEXSDATA", "G4PIIDATA",
             "G4REALSURFACEDATA", "G4SAIDXSDATA", "G4ABLADATA", "G4INCLDATA", "G4ENSDFSTATEDATA", "G4CHANNELINGDATA",
             "G4PARTICLEHPDATA", "G4NUDEXLIBDATA", "G4URRPTDATA", "GEANT4_DATA_DIR")

# G4BestUnit symbols -> factor to the base unit of each category (MeV, mm, Gy, ns, kg)
UNITS = {
    "energy": {"meV": 1e-9, "eV": 1e-6, "keV": 1e-3, "MeV": 1.0, "GeV": 1e3, "TeV": 1e6, "PeV": 1e9, "J": 6.241509074e12},
    "length": {"fm": 1e-12, "pm": 1e-9, "Ang": 1e-7, "nm": 1e-6, "um": 1e-3, "mm": 1.0, "cm": 10.0, "m": 1e3,
               "km": 1e6, "pc": 3.0856775814913673e19},
    "dose": {"picoGy": 1e-12, "nanoGy": 1e-9, "microGy": 1e-6, "milliGy": 1e-3, "Gy": 1.0},
    "mass": {"mg": 1e-6, "g": 1e-3, "kg": 1.0},
    "angle": {"urad": 1e-6, "mrad": 1e-3, "rad": 1.0, "deg": 0.017453292519943295},
}


class SpecError(ValueError):
    """A spec or argument a script refuses (exit 2)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def tilde(path) -> str:
    """A path for a record: inside the plugin as '<plugin root>/...', else with the home folder written as ~
    (records never carry a user's absolute home path)."""
    s, home, plugin = str(path), str(Path.home()), str(PLUGIN)
    if s == plugin or s.startswith(plugin + os.sep):
        return "<plugin root>" + s[len(plugin):]
    return "~" + s[len(home):] if s == home or s.startswith(home + os.sep) else s


def expand(path: str) -> Path:
    return Path(os.path.expanduser(path))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_json(doc) -> str:
    return hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest()


def plugin_version() -> str:
    return json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def record_skeleton(artifact_id: str, objective: str, created: str, status: list[str]) -> dict:
    """A computational-run envelope produced by hep-detector (the adapter's owner skill); extension left to fill."""
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": artifact_id, "artifact_type": "computational-run",
            "objective": objective, "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": plugin_version(), "contracts": CONTRACTS_VERSION, "profiles": {}},
            "provenance": {"producer_skill": "hep-detector", **trace.provenance(), "created": created, "evidence_ids": []},
            "inputs": [], "outputs": [], "unresolved_inputs": [], "status": list(dict.fromkeys(status)),
            "extension": {}}


def data_env(build_record: dict) -> dict[str, str]:
    """The run environment: every Geant4 dataset variable unset (so Geant4's automatic search in G4FindDataDir cannot
    silently pick another copy), then the variables of the datasets the build installed, at their recorded paths."""
    env = {k: v for k, v in os.environ.items() if k not in DATA_VARS and k != "G4FORCE_RUN_MANAGER_TYPE"}
    for d in build_record["extension"]["build"]["datasets"]:
        env[d["envvar"]] = str(expand(d["path"]))
    return env


def install_prefix(build_record: dict) -> Path:
    return expand(build_record["extension"]["build"]["install_prefix"])


def build_record_ok(build_record: dict) -> str | None:
    """None when the build record can be used for runs, else why not."""
    if build_record.get("artifact_type") != "computational-run" or "build" not in build_record.get("extension", {}):
        return "not a geant4_build.py record"
    if "failed" in build_record.get("status", []):
        return "the build record carries 'failed'"
    return None


def parse_quantity(text: str, category: str) -> float:
    """'6.353 keV' -> 0.006353 (MeV); the unit must be a G4BestUnit symbol of the category."""
    m = re.fullmatch(r"\s*([-+0-9.eE]+)\s*([A-Za-z]+)\s*", text)
    if not m or m.group(2) not in UNITS[category]:
        raise ValueError(f"cannot read {text!r} as a {category}")
    return float(m.group(1)) * UNITS[category][m.group(2)]


def run_settings(sim: dict) -> dict:
    """The settings block of a run summary's run (what hep-detector's study check compares with the study spec),
    from a run record's extension.simulation (layered_sim's gun, or element_sim's source from adapter 0.3.0)."""
    phys, gun = sim.get("physics") or {}, sim.get("gun") or sim.get("source") or {}
    return {"default_cut_mm": phys.get("default_cut_mm"), "step_limit_mm": phys.get("step_limit_mm", 0.0),
            "em_constructor": phys.get("em_constructor"), "reference_list": phys.get("reference_list"),
            "ui_commands": sim.get("ui_commands", []), "particle": gun.get("particle"),
            "energy_MeV": gun.get("energy_MeV")}


def write_json(path: Path, doc) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    JsonArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    sys.exit(0)
