#!/usr/bin/env python3
"""Physical constants, particle data, nuclide data, unit conversions and decay Q values, with their sources (Th9).

Purpose: one place for the numbers a calculation takes from outside (see <plugin root>/core/constants/physical.py):
every value comes with its uncertainty, unit, source and edition, so a result can say which CODATA, PDG or AME edition
it used. Bundled: CODATA 2022 (exact SI 2019 constants marked exact; hbar, hbar c and (hbar c)^2 derived from the exact
h, c and e), a PDG 2026 subset of 32 particles (PDG data CC BY 4.0; cite the Review of Particle Physics 2026) and
AME2020/NUBASE2020 data for 40 nuclides. Full tables: --ame/--nubase read the AMDC files mass.mas20 and
nubase_4.mas20 that the user supplies; `particle --backend pdg` reads the optional `pdg` package (pip install pdg).

Subcommands:
  get NAME [--unit U]                     a CODATA constant (see `list`), or hbar, hbar_c, hbar_c_squared
  particle NAME [--property mass|width|lifetime] [--unit U] [--backend bundled|pdg]
  nuclide NAME [--ame FILE] [--nubase FILE]   atomic mass, mass excess, half-life, bare-nucleus mass (e.g. 4He, He-4)
  convert VALUE FROM TO                   units of one dimension, or across them with hbar = c = 1 (GeV^-2 -> mb)
  qvalue PARENT --mode alpha|beta-|beta+|ec [--ame FILE]   ground-state decay energy from AME2020 mass excesses
  edition                                 the bundled editions, sources, read levels and licenses
  list                                    the bundled names
Assumptions and validity: particle masses and widths are energies (c = 1); year-unit half-lives convert with the
NUBASE2020 year, 1 y = 365.2422 d; Q values are ground state to ground state, with
mass-excess uncertainties added in quadrature (correlations ignored).
Output JSON: "status" (run status, core/status.py), "status_label" (--status, default unvalidated), "inputs",
"defaults_used" and the result with its "source" and "edition".
Exit codes: 0 ok; 2 bad input (unknown name or unit, unreadable table); 3 the optional pdg package is missing.
Run: python3 <plugin root>/skills/hep-theory/scripts/physical_data.py get proton_mass_energy --unit GeV
     python3 <plugin root>/skills/hep-theory/scripts/physical_data.py convert 1 GeV^-2 mb
     python3 <plugin root>/skills/hep-theory/scripts/physical_data.py qvalue 238U --mode alpha
Standard library only (the pdg backend excepted).
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core import constants as K  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

DERIVED = {"hbar": K.hbar, "hbar_c": K.hbar_c, "hbar_c_squared": K.hbar_c_squared}
PDG_HINT = "pip install pdg  (the optional extra 'pdg' in pyproject.toml); the bundled subset needs nothing"


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input. Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _get(args) -> dict:
    if args.name in DERIVED:
        q = DERIVED[args.name](args.unit) if args.unit else DERIVED[args.name]()
    else:
        q = K.constant(args.name, unit=args.unit)
    return {"quantity": q.to_dict()}


def _pdg_backend(args) -> tuple[str, dict]:
    try:
        import warnings
        warnings.filterwarnings("ignore")
        import pdg  # optional; never imported by core
    except ImportError:
        return "missing-dependency", {"error": "the optional pdg package is not installed", "install": PDG_HINT}
    api = pdg.connect()
    bundled = None
    try:
        rec = K.particle_record(args.name)
        pdg_name, bundled = rec["pdg_name"], rec.get(args.property)
    except K.ConstantsError:
        pdg_name = args.name
    try:
        p = api.get_particle_by_name(pdg_name)
    except Exception as exc:  # the package raises its own error types for unknown or ambiguous names
        raise K.ConstantsError(f"pdg package: {exc}") from exc
    items = {"mass": p.masses, "width": p.widths, "lifetime": p.lifetimes}[args.property]()
    items = [m for m in items if not bundled or m.units == bundled["unit"]] or list(items)
    if not items:
        raise K.ConstantsError(f"pdg package: {pdg_name} has no {args.property} entry")
    best = items[0].best_summary()
    out = {"backend": "pdg", "package_edition": str(p.edition), "pdg_name": pdg_name,
           "value_text": best.value_text, "unit": best.units, "value": best.value,
           "uncertainty_plus": best.error_positive, "uncertainty_minus": best.error_negative,
           "source": "Particle Data Group, Review of Particle Physics, via the pdg package (https://pdg.lbl.gov)"}
    if bundled:
        out["bundled_value_text"] = bundled["pdg_value_text"]
        out["agrees_with_bundled"] = best.value_text == bundled["pdg_value_text"]
    return "ok", {"pdg": out}


def _particle(args) -> tuple[str, dict]:
    if args.backend == "pdg":
        return _pdg_backend(args)
    return "ok", {"quantity": K.particle(args.name, args.property, unit=args.unit).to_dict()}


def _tables(args) -> dict | None:
    table: dict = {}
    if getattr(args, "ame", None):
        table.update(K.load_ame(args.ame))
    if getattr(args, "nubase", None):
        for key, rec in K.load_nubase(args.nubase).items():
            if key in table:
                table[key] = dict(table[key], **rec)
    return table or None


def _nuclide(args) -> dict:
    table = _tables(args)
    rec = K.nuclide(args.name, table)
    out = {"nuclide": rec, "atomic_mass": K.atomic_mass(args.name, table).to_dict(),
           "nuclear_mass_gev": K.nuclear_mass_gev(rec["Z"], rec["A"], table),
           "nuclear_mass_rule": "atomic mass x m_u c^2 - Z m_e c^2 (CODATA 2022), electron binding energy neglected"}
    if rec.get("half_life"):
        out["half_life_seconds"] = K.half_life_seconds(args.name, table)
    return out


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("get", help="a CODATA 2022 constant or hbar, hbar_c, hbar_c_squared")
    p.add_argument("name")
    p.add_argument("--unit")
    p = sub.add_parser("particle", help="a PDG 2026 mass, width or mean life")
    p.add_argument("name")
    p.add_argument("--property", choices=("mass", "width", "lifetime"), default="mass")
    p.add_argument("--unit")
    p.add_argument("--backend", choices=("bundled", "pdg"), default="bundled")
    p = sub.add_parser("nuclide", help="AME2020 / NUBASE2020 data of a nuclide")
    p.add_argument("name")
    p.add_argument("--ame", help="a full AME2020 mass.mas20 file (user-supplied)")
    p.add_argument("--nubase", help="a full NUBASE2020 nubase_4.mas20 file (user-supplied; needs --ame)")
    p = sub.add_parser("convert", help="convert a value between units")
    p.add_argument("value", type=float)
    p.add_argument("from_unit")
    p.add_argument("to_unit")
    p = sub.add_parser("qvalue", help="ground-state decay energy from AME2020")
    p.add_argument("parent")
    p.add_argument("--mode", required=True, choices=("alpha", "beta-", "beta+", "ec"))
    p.add_argument("--ame", help="a full AME2020 mass.mas20 file (user-supplied)")
    sub.add_parser("edition", help="bundled editions and sources")
    sub.add_parser("list", help="bundled names")
    for sp in sub.choices.values():
        add_status_argument(sp)
    args = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(args).items() if k not in ("status",)}
    given = {tok.split("=")[0] for tok in (sys.argv[1:] if argv is None else argv) if tok.startswith("--")}
    defaults = [k for k in ("property", "backend", "unit", "status") if k in vars(args) and f"--{k}" not in given]
    status, out = "ok", {}
    try:
        if args.command == "get":
            out = _get(args)
        elif args.command == "particle":
            status, out = _particle(args)
        elif args.command == "nuclide":
            out = _nuclide(args)
        elif args.command == "convert":
            out = {"value": K.convert(args.value, args.from_unit, args.to_unit), "unit": args.to_unit,
                   "rule": "decimal scaling within a dimension; hbar and c (exact, CODATA 2022) across dimensions"}
        elif args.command == "qvalue":
            out = {"qvalue": K.qvalue(args.parent, args.mode, _tables(args))}
            if out["qvalue"].get("missing"):
                out["warning"] = f"not in the table: {out['qvalue']['missing']}; supply the full AME2020 file with --ame"
        elif args.command == "edition":
            out = {"editions": K.editions(), "pdg_backend": PDG_HINT}
        else:
            out = {"constants": K.constant_names() + sorted(DERIVED), "particles": K.particle_names(),
                   "nuclides": K.nuclide_names()}
    except (K.ConstantsError, OSError) as exc:
        status, out = "rejected", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults, **out},
                     indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
