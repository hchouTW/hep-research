#!/usr/bin/env python3
"""DRAGON2 translation of a transport block with its source items handled explicitly (escalation 12, work package K3).

dragon2_run.spec_from_transport (the D1 translator) writes the run spec; it reads only the slopes of
sources.injection and neither translates nor records sources.abundances or the variable of the injection spectrum
(VALIDATION CRPROP-D3, open issues 1 and 2). spec_from_transport here checks those two items first, translates them or
refuses them with a reason (SpecError), then calls the D1 translator and records the translation in the spec's
"substitutes". Nothing in the run directory changes: DRAGON2 cd588707 reads its source abundances and injection slopes
from source.param, and dragon2_run.prepare still writes BaseModel_DRAGONxsec.source.param with every slope set to the
one gamma. The provider (dragon2_provider.py) and the D3 study translate through this module.

sources.injection[].spectrum_variable (stated in harmonized-v1, tests/adapters/fixtures/cr_propagation/specs/): the
variable the source spectrum is a density in, dQ/dX = q beta^eta R^-gamma with X one of SPECTRUM_VARIABLES.
DRAGON2 injects a rigidity power law per unit momentum (per nucleon momentum, so per rigidity at fixed A/|Z|): D3
found DRAGON2's C and O spectra 1.75 times USINE's (per E_k/n) at 0.2 GeV/n relative to 10 GeV/n, about 1/beta, and
equal within 0.6% over 0.05-1000 GeV/n once USINE has eta_s = -1. So 'rigidity' with eta 0 is translated; the
per-energy variables need a factor beta^1 that source.param cannot carry, and an eta other than 0 a factor
beta^eta: both refused (on B/C up to 3% at 2-3 GV, D3's injection-convention step 1.000-1.031). Not stated: rigidity,
recorded as a default.

sources.abundances: DRAGON2 takes the source abundances of BaseModel_DRAGONxsec.source.param (its examples folder,
next to HEP_DRAGON2_DATA). DRAGON2_OWN_ABUNDANCES names them and is translated (kept, recorded). Any other text is
refused, among them harmonized-v1's 'fixed by the parent list of theory:cr-secondary-ratio' (propagated O/C 0.9 at
10 GeV/n): source.param fixes source abundances, and the propagated ratio is known only after a run (BaseModel gives
O/C 1.19-1.21 at 10 GeV/n, x1.10 on B/C; VALIDATION CRPROP-D3). Not given: DRAGON2's own abundances, recorded as a
default.

with_dragon2_sources(transport) writes DRAGON2's own source choices (rigidity, eta 0, its own abundances) into a
copy of a transport. The D1 item runs and the D3 DRAGON2 runs were
made with exactly these sources (their recorded XML and source.param are unchanged); their specs state them since K3.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import dragon2_run  # noqa: E402

SpecError = dragon2_run.SpecError

SPECTRUM_VARIABLES = ("rigidity", "kinetic_energy_per_nucleon", "total_energy")
DRAGON2_SPECTRUM_VARIABLE = "rigidity"
DRAGON2_OWN_ABUNDANCES = "dragon2:BaseModel_DRAGONxsec.source.param"
INJECTION_KEYS = {"species_group", "gamma", "eta", "breaks", "spectrum_variable"}


def source_notes(transport: dict) -> list[str]:
    """The substitutes notes of sources.injection's variable and sources.abundances, or SpecError (refused)."""
    src = transport.get("sources") or {}
    if not isinstance(src, dict):
        raise SpecError("transport.sources must be an object")
    inj = src.get("injection") or []
    if not isinstance(inj, list) or any(not isinstance(i, dict) or set(i) - INJECTION_KEYS for i in inj):
        raise SpecError(f"sources.injection: a list of objects with keys among {sorted(INJECTION_KEYS)}")
    notes = []
    variables = {i.get("spectrum_variable") for i in inj}
    if len(variables) > 1:
        raise SpecError(f"sources.injection: one spectrum_variable for every item, got {sorted(map(str, variables))}")
    variable = variables.pop() if variables else None
    if variable is not None and variable not in SPECTRUM_VARIABLES:
        raise SpecError(f"sources.injection spectrum_variable {variable!r}: one of {list(SPECTRUM_VARIABLES)}")
    if variable not in (None, DRAGON2_SPECTRUM_VARIABLE):
        raise SpecError(f"sources.injection spectrum_variable {variable!r}: DRAGON2 cd588707 injects a rigidity power "
                        "law per unit momentum (source.param slopes); a spectrum per "
                        f"{variable.replace('_', ' ')} needs a factor beta that it cannot carry (up to 3% on B/C at "
                        "2-3 GV, VALIDATION CRPROP-D3); state 'rigidity' to run DRAGON2's own injection")
    etas = {float(i["eta"]) for i in inj if "eta" in i}
    if etas - {0.0}:
        raise SpecError(f"sources.injection eta {sorted(etas)}: DRAGON2's source spectrum has no beta factor; only "
                        "eta 0 is translated")
    if inj:
        gammas = sorted({float(i["gamma"]) for i in inj if "gamma" in i})
        slope = ", ".join(f"{g:g}" for g in gammas) or "none"
        if variable is None:
            notes.append(f"sources.injection spectrum_variable not stated: rigidity (DRAGON2 cd588707 injects R^-gamma "
                         f"per unit momentum, gamma {slope}, eta 0)")
        else:
            notes.append(f"sources.injection spectrum_variable 'rigidity': DRAGON2's own measure (R^-gamma per unit "
                         f"momentum, gamma {slope}, eta 0), translated exactly")
    abund = src.get("abundances")
    if abund is None:
        notes.append(f"sources.abundances not given: {DRAGON2_OWN_ABUNDANCES} (DRAGON2's source abundances, kept)")
    elif str(abund).strip() == DRAGON2_OWN_ABUNDANCES:
        notes.append(f"sources.abundances {DRAGON2_OWN_ABUNDANCES!r}: the source abundances of DRAGON2's "
                     "BaseModel_DRAGONxsec.source.param, kept (propagated O/C 1.19-1.21 at 10 GeV/n, VALIDATION "
                     "CRPROP-D3)")
    else:
        raise SpecError(f"sources.abundances {abund!r}: not translated. DRAGON2 reads source abundances from "
                        "source.param, while a propagated ratio (e.g. the parent list's O/C 0.9 at 10 GeV/n) is known "
                        "only after a run; DRAGON2's BaseModel gives O/C 1.19-1.21 there (x1.10 on B/C, VALIDATION "
                        f"CRPROP-D3). State {DRAGON2_OWN_ABUNDANCES!r} to run DRAGON2's own abundances")
    return notes


def with_dragon2_sources(transport: dict) -> dict:
    """A copy of transport with DRAGON2's own source choices stated: every injection item's spectrum_variable
    'rigidity' (eta removed when 0) and sources.abundances DRAGON2_OWN_ABUNDANCES."""
    out = copy.deepcopy(transport)
    src = out.setdefault("sources", {})
    items = []
    for item in src.get("injection") or []:
        item = dict(item, spectrum_variable=DRAGON2_SPECTRUM_VARIABLE)
        if float(item.get("eta", 0.0)) == 0.0:
            item.pop("eta", None)
        items.append(item)
    src["injection"] = items
    src["abundances"] = DRAGON2_OWN_ABUNDANCES
    return out


def spec_from_transport(transport: dict, name: str, channels_mb: dict, **options) -> dict:
    """dragon2_run.spec_from_transport with the source items checked first and recorded (keyword options as there)."""
    if not isinstance(transport, dict):
        raise SpecError("transport must be an object")
    notes = source_notes(transport)
    spec = dragon2_run.spec_from_transport(transport, name, channels_mb, **options)
    spec["substitutes"] = spec["substitutes"] + notes
    return spec


if __name__ == "__main__":
    import argparse
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    sys.exit(0)
