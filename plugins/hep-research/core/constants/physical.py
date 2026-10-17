#!/usr/bin/env python3
"""Physical constants, particle data and nuclide data, each with value, uncertainty, unit, source and edition (Th9).

Bundled data (core/constants/data/, read 2026-10-17; each file records its source, read level and license):
- CODATA 2022 (NIST): the exact SI 2019 constants are marked exact; hbar, hbar c and (hbar c)^2 are derived here from
  the exact h, c and e, not stored;
- PDG 2026: a subset of 32 common particles (masses, widths, mean lives; PDG data CC BY 4.0, cite the Review of
  Particle Physics 2026). Full tables: the optional `pdg` package, used only by skills/hep-theory/scripts/
  physical_data.py, never imported here;
- AME2020 atomic masses and NUBASE2020 ground-state half-lives for 40 nuclides analyses use. Full tables are
  user-supplied files read by load_ame and load_nubase.

Conventions: particle masses and widths are energies (c = 1) in the unit PDG quotes; convert() bridges natural units
(GeV^-1 <-> fm or s, GeV^-2 <-> mb, MeV/c2 <-> kg) through the exact hbar and c. Unit changes within one dimension are
done in decimal arithmetic, so 938.27208943 MeV is exactly the float 0.93827208943 GeV. Year-unit half-lives convert
with the NUBASE2020 year, 1 y = 365.2422 d (the tropical year; Kondev et al. 2021, Sec. 2.3, read 2026-10-17).

Usage (from the plugin root; the CLI is skills/hep-theory/scripts/physical_data.py):
  from core import constants as K
  K.constant("proton_mass_energy", unit="GeV").value; K.hbar_c().value; K.convert(1.0, "GeV^-2", "mb")
  K.particle("pi+", "mass", unit="GeV"); K.nuclear_mass_gev(2, 4); K.qvalue("238U", "alpha")
Standard library only.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from decimal import Decimal, localcontext
from functools import cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
FILES = {"codata": "codata-2022.json", "pdg": "pdg-2026.json", "nuclides": "ame2020-nubase2020.json"}
LABEL = "[General method]"
PI = Decimal("3.14159265358979323846264338327950288419716939937510")
YEAR_NOTE = "NUBASE2020 year: 1 y = 365.2422 d (tropical year), Kondev et al., Chinese Phys. C 45 (2021) 030001, Sec. 2.3"

ELEMENTS = ("n H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb "
            "Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf "
            "Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh "
            "Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og").split()


class ConstantsError(ValueError):
    """An unknown name or unit, an incompatible conversion, or an unreadable table."""


@dataclass(frozen=True)
class Quantity:
    name: str
    value: float
    uncertainty: float | None
    unit: str
    source: str
    edition: str
    exact: bool = False
    uncertainty_plus: float | None = None
    uncertainty_minus: float | None = None
    note: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None or k == "uncertainty"}


@cache
def _load(kind: str) -> dict:
    return json.loads((DATA / FILES[kind]).read_text(encoding="utf-8"))


def editions() -> list[dict]:
    """Edition, source, read level and license of each bundled data file."""
    return [{k: _load(kind)[k] for k in ("edition", "source", "read", "license")} for kind in FILES]


# ---------------------------------------------------------------- units

def _D(x) -> Decimal:
    return Decimal(repr(float(x))) if not isinstance(x, Decimal) else x


def _exact(name: str) -> Decimal:
    return Decimal(repr(_load("codata")["constants"][name]["value"]))


_SI_PREFIX = {"y": "1e-24", "z": "1e-21", "a": "1e-18", "f": "1e-15", "p": "1e-12", "n": "1e-9", "u": "1e-6",
              "m": "1e-3", "": "1", "k": "1e3", "M": "1e6", "G": "1e9", "T": "1e12", "P": "1e15", "E": "1e18"}


@cache
def _units() -> dict[str, tuple[str, int, Decimal]]:
    """unit -> (dimension, power of energy in natural units, factor to the dimension's base unit)."""
    e, c = _exact("elementary_charge"), _exact("speed_of_light")
    u: dict[str, tuple[str, int, Decimal]] = {}
    for p, f in _SI_PREFIX.items():
        if p in "yzafpnumkMGTPE" or p == "":
            u[f"{p}eV"] = ("energy", 1, Decimal(f))  # base eV
            u[f"{p}eV/c2"] = u[f"{p}eV/c^2"] = ("mass", 1, Decimal(f) * e / (c * c))  # base kg
        if p in ("y", "z", "a", "f", "p", "n", "u", "m", ""):
            u[f"{p}s"] = ("time", -1, Decimal(f))  # base s
        if p in ("a", "f", "p", "n", "u", "m", ""):
            u[f"{p}b"] = ("area", -2, Decimal(f) * Decimal("1e-28"))  # base m^2
    u["barn"] = u["b"]
    u["J"] = ("energy", 1, 1 / e)
    for name, f in (("fm", "1e-15"), ("pm", "1e-12"), ("nm", "1e-9"), ("um", "1e-6"), ("mm", "1e-3"), ("cm", "1e-2"),
                    ("m", "1"), ("km", "1e3")):
        u[name] = ("length", -1, Decimal(f))
        u[f"{name}2"] = u[f"{name}^2"] = ("area", -2, Decimal(f) ** 2)
    u["kg"], u["g"] = ("mass", 1, Decimal(1)), ("mass", 1, Decimal("1e-3"))
    u["u"] = ("mass", 1, _exact("atomic_mass_constant"))
    u["min"], u["h"], u["d"] = ("time", -1, Decimal(60)), ("time", -1, Decimal(3600)), ("time", -1, Decimal(86400))
    for p in ("k", "M", "G", "T"):
        for n in (1, 2):
            u[f"{p}eV^-{n}"] = u[f"{p}eV-{n}"] = (f"inverse_energy{n}", -n, Decimal(_SI_PREFIX[p]) ** -n)
    return u


def _to_natural(dim: str) -> Decimal:
    """Factor from the dimension's base unit to eV^power (natural units, hbar = c = 1)."""
    with localcontext() as ctx:
        ctx.prec = 50
        h, c, e = _exact("planck_constant"), _exact("speed_of_light"), _exact("elementary_charge")
        hbar_ev_s = h / (2 * PI) / e
        hbar_c_ev_m = hbar_ev_s * c
        return {"energy": Decimal(1), "mass": c * c / e, "time": 1 / hbar_ev_s, "length": 1 / hbar_c_ev_m,
                "area": 1 / (hbar_c_ev_m * hbar_c_ev_m), "inverse_energy1": Decimal(1),
                "inverse_energy2": Decimal(1)}[dim]


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a value between units of one dimension, or across dimensions through hbar = c = 1."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ConstantsError("value must be a finite number")
    table = _units()
    for unit in (from_unit, to_unit):
        if unit not in table:
            raise ConstantsError(f"unknown unit {unit!r}; known: {sorted(table)}")
    (da, pa, fa), (db, pb, fb) = table[from_unit], table[to_unit]
    with localcontext() as ctx:
        ctx.prec = 50
        if da == db:
            return float(_D(value) * fa / fb)
        if pa != pb:
            raise ConstantsError(f"{from_unit} ({da}) and {to_unit} ({db}) differ in dimension even with hbar = c = 1")
        return float(_D(value) * fa * _to_natural(da) / (fb * _to_natural(db)))


# ---------------------------------------------------------------- constants

def constant_names() -> list[str]:
    return sorted(_load("codata")["constants"])


def constant(name: str, unit: str | None = None) -> Quantity:
    """A CODATA 2022 constant by key (constant_names()), optionally converted to another unit."""
    data = _load("codata")
    rec = data["constants"].get(name)
    if rec is None:
        raise ConstantsError(f"unknown constant {name!r}; known: {constant_names()}")
    value, unc, rec_unit = rec["value"], rec["uncertainty"], rec["unit"]
    if unit and unit != rec_unit:
        unc = 0.0 if rec["exact"] else convert(unc, rec_unit, unit)
        value = convert(value, rec_unit, unit)
        rec_unit = unit
    return Quantity(name, value, unc, rec_unit, f"{rec['codata_name']} ({data['source']})", data["edition"], rec["exact"])


def _derived(name: str, value: Decimal, unit: str, how: str) -> Quantity:
    data = _load("codata")
    return Quantity(name, float(value), 0.0, unit, f"derived from the exact h, c and e ({how}); {data['source']}",
                    data["edition"], True)


def hbar(unit: str = "eV s") -> Quantity:
    """Reduced Planck constant h / 2 pi (exact in the 2019 SI). unit: 'J s', 'eV s', 'MeV s' or 'GeV s'."""
    scale = {"eV s": Decimal(1), "MeV s": Decimal("1e-6"), "GeV s": Decimal("1e-9")}
    if unit != "J s" and unit not in scale:
        raise ConstantsError(f"hbar unit must be one of {sorted(scale) + ['J s']}")
    with localcontext() as ctx:
        ctx.prec = 50
        h = _exact("planck_constant") / (2 * PI)
        value = h if unit == "J s" else h / _exact("elementary_charge") * scale[unit]
    return _derived("hbar", value, unit, "hbar = h / 2 pi")


def hbar_c(unit: str = "MeV fm") -> Quantity:
    """hbar c (exact). unit: 'MeV fm', 'GeV fm', 'eV m' or 'GeV m'."""
    scale = {"MeV fm": Decimal("1e9"), "GeV fm": Decimal("1e6"), "eV m": Decimal(1), "GeV m": Decimal("1e-9")}
    if unit not in scale:
        raise ConstantsError(f"hbar c unit must be one of {sorted(scale)}")
    with localcontext() as ctx:
        ctx.prec = 50
        value = _exact("planck_constant") / (2 * PI) * _exact("speed_of_light") / _exact("elementary_charge") * scale[unit]
    return _derived("hbar_c", value, unit, "hbar c = h c / (2 pi e) in eV m")


def hbar_c_squared(unit: str = "GeV^2 mb") -> Quantity:
    """(hbar c)^2 (exact), the conversion from GeV^-2 to a cross section. unit: 'GeV^2 mb' or 'GeV^2 fm^2'."""
    scale = {"GeV^2 mb": Decimal(10), "GeV^2 fm^2": Decimal(1)}  # 1 fm^2 = 10 mb
    if unit not in scale:
        raise ConstantsError(f"(hbar c)^2 unit must be one of {sorted(scale)}")
    with localcontext() as ctx:
        ctx.prec = 50
        hc = _exact("planck_constant") / (2 * PI) * _exact("speed_of_light") / _exact("elementary_charge") * Decimal("1e6")
        value = hc * hc * scale[unit]
    return _derived("hbar_c_squared", value, unit, "(hbar c)^2")


# ---------------------------------------------------------------- particles

def particle_names() -> list[str]:
    return sorted(_load("pdg")["particles"])


def particle_record(name: str) -> dict:
    rec = _load("pdg")["particles"].get(name)
    if rec is None:
        raise ConstantsError(f"unknown particle {name!r} in the bundled PDG 2026 subset; known: {particle_names()}")
    return json.loads(json.dumps(rec))


def has_particle_property(name: str, prop: str) -> bool:
    return prop in particle_record(name)


def particle(name: str, prop: str = "mass", unit: str | None = None) -> Quantity:
    """A PDG 2026 summary value: prop 'mass', 'width' or 'lifetime'; masses and widths are energies (c = 1)."""
    if prop not in ("mass", "width", "lifetime"):
        raise ConstantsError("prop must be mass, width or lifetime")
    rec = particle_record(name)
    if prop not in rec:
        raise ConstantsError(f"{name} has no bundled {prop} (PDG gives a limit or no entry)")
    q, data = rec[prop], _load("pdg")
    value, unc, up, dn, src_unit = q["value"], q.get("uncertainty"), q.get("uncertainty_plus"), q.get("uncertainty_minus"), q["unit"]
    if unit and unit != src_unit:
        conv = lambda x: None if x is None else convert(x, src_unit, unit)  # noqa: E731
        value, unc, up, dn, src_unit = conv(value), conv(unc), conv(up), conv(dn), unit
    source = f"PDG {q['pdg_identifier']} ({q['pdg_value_text']} {q['unit']}); {data['source']}"
    return Quantity(f"{name} {prop}", value, unc, src_unit, source, data["edition"], False, up, dn)


# ---------------------------------------------------------------- nuclides

_NUCLIDE = re.compile(r"^(\d+)([A-Z][a-z]?)$|^([A-Z][a-z]?)-?(\d+)$")


def _key(name) -> tuple[int, int]:
    if isinstance(name, tuple) and len(name) == 2:
        return int(name[0]), int(name[1])
    if name == "n":
        return (0, 1)
    m = _NUCLIDE.match(str(name))
    if not m or (m.group(2) or m.group(3)) not in ELEMENTS:
        raise ConstantsError(f"nuclide {name!r} must look like '4He', 'He-4' or (Z, A)")
    a = int(m.group(1) or m.group(4))
    return ELEMENTS.index(m.group(2) or m.group(3)), a


def _name(z: int, a: int) -> str:
    return "n" if (z, a) == (0, 1) else f"{a}{ELEMENTS[z]}"


@cache
def _nuclides() -> dict[tuple[int, int], dict]:
    return {(r["Z"], r["A"]): r for r in _load("nuclides")["nuclides"].values()}


def nuclide_names() -> list[str]:
    return [_name(*k) for k in sorted(_nuclides(), key=lambda k: (k[1], k[0]))]


def nuclide(name, table: dict | None = None) -> dict:
    """The AME2020/NUBASE2020 record of a nuclide (bundled subset, or a user table from load_ame)."""
    key = _key(name)
    rec = (table or {}).get(key) or _nuclides().get(key)
    if rec is None:
        raise ConstantsError(f"nuclide {_name(*key)} is not in the bundled subset; supply the full AME2020 table "
                             "(core.constants.load_ame)")
    return json.loads(json.dumps(rec))


def atomic_mass(name, table: dict | None = None) -> Quantity:
    rec, data = nuclide(name, table), _load("nuclides")
    return Quantity(f"{_name(rec['Z'], rec['A'])} atomic mass", rec["atomic_mass_u"], rec["atomic_mass_uncertainty_u"],
                    "u", data["source"], data["edition"], rec["A"] == 12 and rec["Z"] == 6,
                    note="estimated (from systematics)" if rec.get("estimated") else None)


def nuclear_mass_gev(z: int, a: int, table: dict | None = None) -> float:
    """Bare-nucleus mass: atomic mass x m_u c^2 - Z m_e c^2 (CODATA 2022), electron binding energy neglected."""
    u_gev = constant("atomic_mass_constant_energy", unit="GeV").value
    e_gev = constant("electron_mass_energy", unit="GeV").value
    return nuclide((z, a), table)["atomic_mass_u"] * u_gev - z * e_gev


def half_life(name, table: dict | None = None) -> Quantity | None:
    """NUBASE2020 ground-state half-life in NUBASE's unit; None for a stable nuclide."""
    rec, data = nuclide(name, table), _load("nuclides")
    hl = rec.get("half_life")
    if not hl:
        raise ConstantsError(f"no half-life for {_name(rec['Z'], rec['A'])} in the table")
    if hl.get("stable"):
        return None
    return Quantity(f"{_name(rec['Z'], rec['A'])} half-life", hl["value"], hl.get("uncertainty"), hl["unit"],
                    data["source"], data["edition"], note="estimated (from systematics)" if hl.get("estimated") else None)


_TIME_S = {"ys": "1e-24", "zs": "1e-21", "as": "1e-18", "fs": "1e-15", "ps": "1e-12", "ns": "1e-9", "us": "1e-6",
           "ms": "1e-3", "s": "1", "m": "60", "h": "3600", "d": "86400"}
_YEAR_S = Decimal("365.2422") * 86400
_TIME_S.update({p + "y": str(Decimal(f) * _YEAR_S) for p, f in
                (("", "1"), ("k", "1e3"), ("M", "1e6"), ("G", "1e9"), ("T", "1e12"), ("P", "1e15"), ("E", "1e18"),
                 ("Z", "1e21"), ("Y", "1e24"))})


def half_life_seconds(name, table: dict | None = None) -> dict:
    """{'value': seconds, 'uncertainty', 'note'}; year units use the NUBASE2020 year (YEAR_NOTE)."""
    q = half_life(name, table)
    if q is None:
        return {"value": None, "uncertainty": None, "note": "stable"}
    if q.unit not in _TIME_S:
        return {"value": None, "uncertainty": None, "note": f"unknown NUBASE unit {q.unit!r}", "nubase": q.to_dict()}
    f = Decimal(_TIME_S[q.unit])
    unc = None if q.uncertainty is None else float(_D(q.uncertainty) * f)
    return {"value": float(_D(q.value) * f), "uncertainty": unc, "note": YEAR_NOTE if q.unit.endswith("y") else None}


_DECAYS = {"alpha": (-2, -4), "beta-": (1, 0), "beta+": (-1, 0), "ec": (-1, 0)}


def qvalue(parent, mode: str, table: dict | None = None) -> dict:
    """Ground-state to ground-state decay energy from AME2020 mass excesses (keV): alpha, beta-, beta+ (minus
    2 m_e c^2) or ec. A nuclide missing from the table gives value None and lists it under 'missing'."""
    if mode not in _DECAYS:
        raise ConstantsError(f"mode must be one of {sorted(_DECAYS)}")
    z, a = _key(parent)
    dz, da = _DECAYS[mode]
    names = [_name(z, a), _name(z + dz, a + da)] + (["4He"] if mode == "alpha" else [])
    out = {"parent": names[0], "mode": mode, "daughter": names[1], "label": LABEL,
           "edition": _load("nuclides")["edition"], "source": _load("nuclides")["source"],
           "note": "ground state to ground state; uncertainty adds the mass-excess uncertainties in quadrature (correlations ignored)"}
    recs, missing = [], []
    for n in names:
        try:
            recs.append(nuclide(n, table))
        except ConstantsError:
            missing.append(n)
    if missing:
        return {**out, "value_keV": None, "uncertainty_keV": None, "missing": missing}
    q = recs[0]["mass_excess_keV"] - sum(r["mass_excess_keV"] for r in recs[1:])
    if mode == "beta+":
        q -= 2 * constant("electron_mass_energy", unit="keV").value
    unc = math.sqrt(sum(r["mass_excess_uncertainty_keV"] ** 2 for r in recs))
    return {**out, "value_keV": q, "uncertainty_keV": unc}


# ---------------------------------------------------------------- user-supplied full tables

def load_ame(path) -> dict[tuple[int, int], dict]:
    """Read a full AME2020 mass.mas20 file (fixed width, as published by the AMDC) into {(Z, A): record}."""
    out: dict[tuple[int, int], dict] = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if len(line) < 120:
            continue
        try:
            z, a = int(line[9:14]), int(line[14:19])
            whole, micro, dmicro = line[106:109].strip(), line[110:123].strip(), line[123:135].strip()
            mexc, dmexc = line[28:42].strip(), line[42:54].strip()
            est = "#" in mexc + micro
            rec = {"element": line[20:23].strip(), "Z": z, "A": a,
                   "mass_excess_keV": float(mexc.replace("#", ".")), "mass_excess_uncertainty_keV": float(dmexc.replace("#", ".")),
                   "atomic_mass_u": float(Decimal(whole) + Decimal(micro.replace("#", ".")) * Decimal("1e-6")),
                   "atomic_mass_uncertainty_u": float(Decimal(dmicro.replace("#", ".")) * Decimal("1e-6")), "estimated": est}
        except (ValueError, ArithmeticError):
            continue
        out[(z, a)] = rec
    if not out:
        raise ConstantsError(f"{path}: no AME2020 mass rows found (expected the fixed-width mass.mas20 format)")
    return out


def load_nubase(path) -> dict[tuple[int, int], dict]:
    """Read a full NUBASE2020 nubase_4.mas20 file into {(Z, A): {'half_life': ...}} (ground states only)."""
    out: dict[tuple[int, int], dict] = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("#") or len(line) < 88:
            continue
        try:
            a, z, iso = int(line[0:3]), int(line[4:7]), line[7]
        except ValueError:
            continue
        if iso != "0":
            continue
        t, unit, dt = line[69:78].strip(), line[78:80].strip(), line[81:88].strip()
        if t == "stbl":
            out[(z, a)] = {"half_life": {"stable": True}}
        elif t and t != "p-unst":
            try:
                value = float(t.replace("#", "").lstrip("<>~"))
            except ValueError:
                continue
            unc = float(dt.replace("#", "")) if re.fullmatch(r"[0-9.#]+", dt) else None
            out[(z, a)] = {"half_life": {"value": value, "unit": unit, "uncertainty": unc, "uncertainty_text": dt or None,
                                         "estimated": "#" in t}}
    if not out:
        raise ConstantsError(f"{path}: no NUBASE2020 rows found (expected the fixed-width nubase_4.mas20 format)")
    return out
