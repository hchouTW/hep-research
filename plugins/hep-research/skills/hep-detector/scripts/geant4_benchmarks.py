#!/usr/bin/env python3
"""Independent-reference benchmarks for Geant4 layered-slab runs (stopping power, range, thin-layer MPV and width,
multiple scattering, shower shape, published data).

Purpose: compare quantities from layered_sim CSV outputs (adapters/geant4) with references whose inputs do NOT come
from Geant4: density, Z/A, mean excitation energy and the Sternheimer density-effect parameters are read from the
study spec (which cites PDG or NIST for them), physical constants from core/constants (CODATA 2022, PDG 2026). The
Geant4 material dump is never read: an error in the spec must not enter the reference and cancel out. This script
does not import the adapter and does not need Geant4. See <plugin root>/skills/hep-detector/references/
geant4-study-protocol.md.

Grades (the validation classes of the contracts table, contracts.validate.GEANT4_BENCHMARKS): `reference` benchmarks
use an independent source that states its accuracy, on an isolated target; `setup-matched` benchmarks compare with a
published measurement of the same configuration (target hash equal to the measured one, isolated); these two are the
only validation evidence; `sanity` benchmarks are plausibility checks; `interface` hands a comparison to hep-statistics.
  stopping-power    (reference) mean energy loss of transmitted primaries (E_in - E_exit), as linear dE/dx, against
                    the Bethe mean rate (PDG RPP 2024 eq. 34.5, valid 0.1 <~ beta gamma <~ 1000 to a few percent)
                    at the mean energy in the slab; non-transmitted primaries and primaries that ended in a process
                    other than Transportation are excluded and counted. Deposit is not energy loss.
  range             (reference) mean projected stopping depth of primaries in a thick block against a user-supplied
                    PSTAR/ASTAR projected range (dataset-record, interpolated in log-log); primaries that ended in a
                    hadronic process are excluded and counted (PSTAR excludes nuclear interactions).
  thin-layer-mpv    (reference) most probable energy loss of the primary against the PDG Landau-Vavilov value
                    Delta_p = xi [ln(2 m c^2 b^2 g^2 / I) + ln(xi / I) + j - b^2 - delta(bg)], j = 0.200, xi =
                    (K/2)(Z/A) z^2 (rho x / b^2) (RPP 2024 eq. 34.12); applicable only for kappa = xi / W_max < 0.05.
                    MPV estimator (A1.7): in each block's histogram (the summary observable's bins), the vertex of
                    the three-point parabola through the fullest bin and its neighbours; the MPV is the mean of the K
                    block modes with its batch-means SE; more than K/4 fallback blocks, or a mean of block modes more
                    than tol/5 + 2 SE from the merged histogram's mode, is not applicable (incomplete).
  thin-layer-width  (sanity) FWHM of the deposit distribution against 4 xi (thin-layer widths are wider: RPP 2024).
  multiple-scattering (sanity) core width of the projected exit angle (both projections, RMS of the central 98 %
                    divided by the Gaussian truncation factor 0.8673) against Highland from multiple_scattering.py,
                    run as a subprocess (RPP 2024 gives no numerical accuracy for it).
  em-shower-shape   (sanity) depth of the longitudinal maximum from per-copy deposits against t_max = ln(E/E_c) + C_j
                    (config keys layer_x0 and critical_energy_MeV); not applicable when the stack does not contain t_max.
  shower-containment (sanity) rear leakage fraction of an e+-/gamma shower against the PDG gamma-function profile
                    (RPP 2024 Eqs. 34.34-34.36, b = 0.5 by default; config keys depth_x0, critical_energy_MeV, b):
                    the profile is a fit to EGS4 showers (1-100 GeV), so this is never validation; a reference for
                    leakage needs published data (published-data).
  longitudinal-profile (setup-matched) shower maximum t_max = (alpha - 1) / beta of the per-layer mean deposits of a
                    sampling calorimeter, from the fit dQ/dt = Q_E beta (beta t)^(alpha-1) e^(-beta t) / Gamma(alpha)
                    + Q0 (weighted least squares, layers and their depths t from the config key layers), against the
                    same fit to published test-beam data (config key published: alpha and beta with their uncertainties
                    and source); the reference accuracy is the published t_max uncertainty (alpha and beta propagated
                    without their correlation, conservative) plus a stated systematic_relative for known differences
                    between the planar model and the measurement; the fit is made per block and t_max is the batch
                    mean of the block fits.
  published-data    (interface) the Geant4 mean of a named column and a published value, handed to hep-statistics.
Detector benchmarks (CV-B2, element_sim and simreco runs) and their config keys, paths relative to the config file
(worked configs: examples/design-minimal-spectrometer/live.py):
  field-propagation        element_spec, crossings (simroot dump CSV of a charged-geantino run), optional
                           reference_spec, tolerance_um (0.5), tolerance_ps (1.0)
  material-definition      element_spec, geometry (evaluate_design.py geometry), realization (profile), run_record
                           (a geantino run; its effective-config tree gives Geant4's densities), csv and column_map
                           (that run's events and column map), tolerance_relative (0.01)
  reco-closure             reco_record (simreco, every tail source off), summary, pull_observable,
                           residual_observable, rigidity_GV, particle
  multiple-scattering-reference  element_spec (an isolated slab plus a thin downstream measuring plane, vacuum, no
                           field), crossings (simroot dump), measuring_plane (element name), material,
                           thickness_mm, particle, momentum_MeV, blocks (16), tolerance {reference_accuracy,
                           k_sigma, reference_source, validity}, run_record, slab (the slab's logical volume),
                           negative_controls [{crossings, run_record, injected, injected_relative}]:
                           injected_relative must equal the areal-density change Geant4 realized (each run's
                           effective config, to 1e-6; a NIST material resolves to Geant4's own density, so derive
                           the control from it), else the control is not counted; control_rule (shift-window/1
                           default, declared-size/1 for new studies: see Control rules)
  field-propagation-muon, tof-beta  summary, observable, tolerance_absolute
  tof-layer-consistency    summary, observable, tolerance_absolute, sigma_t_ps, width_tolerance_relative (0.1)
  sampling-fraction        summary, active_observable, passive_observable, reference_value, reference_source,
                           window_relative (0.10)
  regression-comparison    summary_a, summary_b, observable, tolerance, tolerance_mode, m, version_a, version_b
Data (contracts CV-A1): stopping-power, range, thin-layer-mpv, thin-layer-width and longitudinal-profile read a run
summary (simulation-summary/1, adapters/geant4/assets/summary_from_csv.py) and estimate their statistic by batch
means over its K blocks (core/simulation/estimates.py; SE on K - 1 degrees of freedom); the summary observable must
have the selection the benchmark's definition requires (transmitted: primary.fate == 1 and primary.end_process ==
Transportation; range: stopped with no hadronic end process). The other sanity and interface benchmarks read the
per-event CSV. Columns (A2.6, D9): the code names semantic columns only (primary.energy_loss, energy_deposit.<slab>,
...) and resolves them through the run's column map (simulation-columns/1, config key column_map, written by
layered_sim from adapter 0.2.0) or, for runs before 0.2.0, through assets/geant4-columns-legacy.json. Verdict: |G4 - ref| / ref <= tolerance, tolerance = reference accuracy + k x SE, plus a stated binning
term for the MPV. Negative controls (A1.10, core/stats/decisions.py): every reference or setup-matched benchmark reruns
on its controls (Geant4 runs with an error of known size injected on the Geant4 side, the reference unchanged); a
control is judged on the observable: shift = (control - nominal) / reference with the SE of both runs, caught when the
control's verdict is fail; detection limit DL = tolerance + |relative difference| + t_0.977(nu) SE_shift (Welch nu);
a control is at the claimed limit when caught and |shift| <= 1.1 DL. Controls in both directions validate the claim;
one direction narrows it to that sign (scope.detection_limit_sign). Gross controls (msc off) do not count.

Input: a benchmark config JSON (schema geant4-benchmarks/1; paths relative to the config file):
  {"schema", "study_spec", "benchmarks": [{"benchmark", "summary" and "observable" (summary-based benchmarks) or
   "csv", "run_record", "slab", "material", "particle", "energy_MeV", "thickness_mm", "tolerance":
   {"reference_accuracy_relative", "k_sigma"}, "binning": {"bin_width_MeV"}, "negative_controls": [{"summary" or
   "csv", "run_record", "injected", "injected_relative"}] (or one "negative_control"), "reference_table" (range),
   "column"/"published" (published-data; column a semantic name or a CSV column), "column_map" (the run's
   column_map.json; also per negative control), "layers" [{"t", "observable"}] (longitudinal-profile), "published"
   {"alpha", "beta", "source"}, "systematic_relative" (longitudinal-profile), "target_slabs" (the slabs of the target,
   absorbers included; default the measured slab; required for longitudinal-profile), "measured_configuration"
   {"target_geometry_sha256", "hash_scheme"} (setup-matched: the configuration the measurement was made on)}]}
Configuration (contracts CV-A1): each result carries configuration (isolated or embedded), target_geometry_sha256,
hash_scheme, target_slabs and configuration_basis, derived from the run record its setting names, never from user
input: tree-v1 from the effective config's geometry for records from geant4 adapter 0.2.0 (a probe that recorded
nothing is a configuration_gap), spec-v1 from spec/1 for earlier records (contracts.validate.geant4_configuration); a reference or setup-matched benchmark is validation
evidence only on an isolated target (vacuum world, every placement in the target) with a run record, and a
setup-matched one only when its target hash equals the measured configuration's (otherwise configuration_gap).
Detector-level benchmarks (contracts CV-B2, Geant4 program B2.7; element_sim and simreco outputs, each result with the
declared-scope keys it covers): field-propagation (verification: charged geantinos of an element_sim run, from the
crossings simroot dumped, against the analytic helix of core/simulation/helix.py; key field_configuration_sha256),
material-definition (verification: independent material densities against Geant4's resolved ones and a geantino
x/X0 scan against the candidate's declared layer_x_over_x0; keys geometry_sha256, realization_sha256), reco-closure
(verification: simreco on charged geantinos at high rigidity, tail sources off: pull width 1 +- 3 sigma_MC, no bias;
key reco_spec_sha256, the reco spec without tail sources, replicas and outputs), tof-beta and tof-layer-consistency
(verification, bookkeeping), field-propagation-muon and sampling-fraction (sanity), multiple-scattering-reference
(reference: the central-98 % core width of the projected exit angle after an isolated slab, measured at the entry of
a downstream plane, against Lynch and Dahl's F = 98 % formula with the declared published accuracy, negative controls
on the slab's density or thickness; scope particle, material, thickness_x0, rigidity_GV), ms-tail-reference
(reference, D0-b: not applicable until a published tail reference is configured) and regression-comparison
(regression: core.stats.decisions.change between two versions; never affects the label). scope-keys prints the keys
a study declares (field configuration, reco spec, geometry and realization-profile hashes).
Control rules (per benchmark, control_rule): shift-window/1 (default) counts a caught control whose |shift| <= 1.1 DL;
declared-size/1 (multiple-scattering-reference, stopping-power, thin-layer-mpv; for new studies) fixes each
control's size before the runs: its expected shift follows from injected_relative through the benchmark's own
reference (Lynch and Dahl's theta0; Bethe at the shifted mid-slab energy; Landau-Vavilov Delta_p), the injection
checked in the control's run record, the control counts when caught and the
expected shift is at most 1.5 x the planned detection limit (from the nominal run alone), and the benchmark claims the
largest detection limit a caught control demonstrated, max(DL, |shift|). plan-controls prints the planned limit and
the +- injections for an expected shift of 1.25 x it (both factors provisional).
Usage: geant4_benchmarks.py run --config CONFIG.json [--out OUT.json] [--status LABEL]
       geant4_benchmarks.py plan-controls --config CONFIG.json [--benchmark NAME] [--index N]
       geant4_benchmarks.py scope-keys [--element-spec SPEC] [--reco-spec RECO] [--geometry G] [--realization P]
       geant4_benchmarks.py reference --study-spec SPEC.json --material NAME --particle P --energy-mev E [--thickness-mm T]
Output JSON: status, status_label, inputs, defaults_used, benchmarks [{benchmark, grade, reference {source, version,
validity}, scope {particle, energy_MeV, material, thickness_mm, observable}, statistic, geant4, reference_value,
relative_difference, relative_se, tolerance {total, parts}, detection_limit_relative, verdict, negative_control
{status, controls [{shift, se_of_shift, sign, detection_limit_relative, at_claimed_detection_limit, ...}],
detection_limit_sign},
configuration, target_geometry_sha256, hash_scheme, target_slabs, configuration_basis, configuration_gap,
validation_evidence}], gaps.
Exit codes: 0 every benchmark ran and no reference benchmark failed; 1 a reference benchmark failed or its negative
control was not caught; 2 bad input; 3 incomplete (a benchmark not applicable or missing data). Standard library only.
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
import gzip
import hashlib
import json
import math
import re
import statistics
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
from contracts.schema import validate as schema_validate  # noqa: E402
from contracts.validate import geant4_configuration  # noqa: E402  (CV-A1, A2.6: one configuration derivation)
from core.simulation import estimates as E, summary as S  # noqa: E402
from core.stats.batch_means import batch_mean  # noqa: E402
from core.stats.decisions import change, detection_limit, difference, equivalence, welch_dof  # noqa: E402
from core.simulation import helix as H  # noqa: E402  (B1.7's analytic-helix oracle, the field benchmark's reference)
from core import constants as K  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

STATUSES = ("failed", "unvalidated", "preliminary", "synthetic", "asimov", "observed", "user-supplied",
            "validated-in-scope", "projection", "outside-validated-range")
MS_SCRIPT = Path(__file__).resolve().parent / "multiple_scattering.py"
ME = K.constant("electron_mass_energy", unit="MeV").value  # CODATA 2022
R_E_CM = K.constant("classical_electron_radius", unit="m").value * 100
N_A = K.constant("avogadro_constant").value
K_BETHE = 4 * math.pi * N_A * R_E_CM ** 2 * ME  # MeV mol^-1 cm^2 (PDG Table 34.1: 0.307075)
J_LANDAU = 0.200  # PDG RPP 2024 eq. 34.12
PATH_LENGTH = "primary_path_length"  # element_sim's semantic name (column map) of the per-element primary path
TRUNC_98 = 0.8673  # RMS of a unit Gaussian truncated to its central 98 %
GRADES = {"stopping-power": "reference", "range": "reference", "thin-layer-mpv": "reference",
          "thin-layer-width": "sanity", "multiple-scattering": "sanity", "em-shower-shape": "sanity",
          "shower-containment": "sanity", "longitudinal-profile": "setup-matched",
          "published-data": "interface",
          # CV-B2 (Geant4 program B2.7): element_sim and simreco benchmarks
          "field-propagation": "verification", "field-propagation-muon": "sanity", "material-definition": "verification",
          "reco-closure": "verification", "tof-beta": "verification", "tof-layer-consistency": "verification",
          "sampling-fraction": "sanity", "multiple-scattering-reference": "reference", "ms-tail-reference": "reference",
          "regression-comparison": "regression"}
DETECTOR_BENCHMARKS = ("field-propagation", "field-propagation-muon", "material-definition", "reco-closure", "tof-beta",
                       "tof-layer-consistency", "sampling-fraction", "multiple-scattering-reference",
                       "ms-tail-reference", "regression-comparison")
UPGRADING = ("reference", "setup-matched")  # the classes that are validation evidence (contracts table)
RPP = "PDG RPP 2024, Passage of particles through matter (pdg.lbl.gov/2024/reviews/rpp2024-rev-passage-particles-matter.pdf)"
HADRONIC_END = ("Inelastic", "hadElastic", "nCapture", "CoulombScat")


class BenchmarkError(ValueError):
    """Input the script refuses (exit 2)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def particle_props(name: str) -> tuple[float, int]:
    """(mass in MeV, charge number) for a Geant4 particle name, from core/constants."""
    table = {"e-": ("electron_mass_energy", -1), "e+": ("electron_mass_energy", 1), "mu-": ("muon_mass_energy", -1),
             "mu+": ("muon_mass_energy", 1), "proton": ("proton_mass_energy", 1), "alpha": ("alpha_particle_mass_energy", 2),
             "deuteron": ("deuteron_mass_energy", 1)}
    if name in table:
        key, z = table[name]
        return K.constant(key, unit="MeV").value, z
    if name in ("pi+", "pi-"):
        return K.particle("pi+", "mass", unit="MeV").value, 1 if name == "pi+" else -1
    raise BenchmarkError(f"no mass for particle {name!r} (known: {sorted(table) + ['pi+', 'pi-']})")


def check_inputs(energy_mev, thickness_mm=None) -> None:
    """Refuse a kinetic energy or thickness outside what the references can be evaluated for."""
    if not isinstance(energy_mev, (int, float)) or not math.isfinite(energy_mev) or not 0 < energy_mev <= 1e9:
        raise BenchmarkError("energy_MeV must be a finite kinetic energy in (0, 1e9] MeV")
    if thickness_mm is not None and (not isinstance(thickness_mm, (int, float)) or not math.isfinite(thickness_mm)
                                     or not 0 < thickness_mm <= 1e4):
        raise BenchmarkError("thickness_mm must be in (0, 1e4] mm")


def kinematics(ekin: float, mass: float) -> tuple[float, float, float]:
    gamma = 1 + ekin / mass
    beta2 = 1 - 1 / gamma ** 2
    return gamma, beta2, math.sqrt(beta2) * gamma


def w_max(ekin: float, mass: float) -> float:
    gamma, beta2, bg = kinematics(ekin, mass)
    return 2 * ME * bg ** 2 / (1 + 2 * gamma * ME / mass + (ME / mass) ** 2)


def density_effect(bg: float, st: dict) -> float:
    """Sternheimer delta(beta gamma) (PDG RPP 2024 eq. 34.7) with parameters a, k, x0, x1, Cbar, delta0."""
    x = math.log10(bg)
    if x >= st["x1"]:
        return 2 * math.log(10) * x - st["Cbar"]
    if x >= st["x0"]:
        return 2 * math.log(10) * x - st["Cbar"] + st["a"] * (st["x1"] - x) ** st["k"]
    return st["delta0"] * 10 ** (2 * (x - st["x0"]))


def bethe(ekin: float, mass: float, z: int, mat: dict) -> float:
    """Mean dE/dx in MeV cm^2/g (PDG RPP 2024 eq. 34.5); I and Z/A and Sternheimer from the study spec."""
    gamma, beta2, bg = kinematics(ekin, mass)
    i_mev = mat["mean_excitation_eV"] * 1e-6
    arg = 2 * ME * bg ** 2 * w_max(ekin, mass) / i_mev ** 2
    return K_BETHE * z ** 2 * mat["z_over_a"] / beta2 * (0.5 * math.log(arg) - beta2
                                                         - density_effect(bg, mat["sternheimer"]) / 2)


def landau_mpv(ekin: float, mass: float, z: int, mat: dict, thickness_mm: float) -> dict:
    gamma, beta2, bg = kinematics(ekin, mass)
    x = mat["density_g_cm3"] * thickness_mm / 10  # g/cm^2
    xi = K_BETHE / 2 * mat["z_over_a"] * z ** 2 * x / beta2
    i_mev = mat["mean_excitation_eV"] * 1e-6
    delta = density_effect(bg, mat["sternheimer"])
    dp = xi * (math.log(2 * ME * bg ** 2 / i_mev) + math.log(xi / i_mev) + J_LANDAU - beta2 - delta)
    return {"delta_p_MeV": dp, "xi_MeV": xi, "kappa": xi / w_max(ekin, mass), "delta": delta, "beta_gamma": bg}


def read_csv(path: Path) -> list[dict]:
    """Rows of a layered_sim CSV (or a gzip-compressed copy, .csv.gz), numbers as floats."""
    raw = gzip.decompress(path.read_bytes()).decode() if path.suffix == ".gz" else path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    if not lines or lines[0] != "# SIMULATION":
        raise BenchmarkError(f"{path.name}: not a layered_sim CSV (first line must be '# SIMULATION')")
    cols = lines[1].split(",")
    rows = []
    for ln in lines[2:]:
        if ln:
            vals = ln.split(",")
            rows.append({c: (float(v) if _is_num(v) else v) for c, v in zip(cols, vals)})
    if not rows:
        raise BenchmarkError(f"{path.name}: no events")
    return rows


def _is_num(v: str) -> bool:
    try:
        float(v)
        return True
    except ValueError:
        return False


LEGACY_COLUMNS = Path(__file__).resolve().parents[1] / "assets" / "geant4-columns-legacy.json"


class Columns:
    """Semantic column names of a run's per-event data (simulation-columns/1, A2.6): from the run's column map, or for
    runs before geant4 adapter 0.2.0 from the legacy layered_sim map; patterns <slab> and <i> stand for a slab name and
    a copy number. The benchmarks name semantic columns only."""

    def __init__(self, path: Path | None = None):
        src = path or LEGACY_COLUMNS
        doc = json.loads(src.read_text(encoding="utf-8"))
        if doc.get("column_map_version") != "simulation-columns/1" or not isinstance(doc.get("columns"), list):
            raise BenchmarkError(f"{src.name}: not a simulation-columns/1 column map")
        self.source = "legacy layered_sim map" if path is None else src.name
        self.exact: dict[str, str] = {}
        patterns = []
        for c in doc["columns"]:
            if c.get("file") != "csv":
                continue
            if "<" in c["column"]:
                pieces = re.split(r"(<slab>|<i>)", c["column"])
                rx = "".join({"<slab>": r"(?P<slab>[A-Za-z0-9_]+)", "<i>": r"(?P<i>[0-9]+)"}.get(x, re.escape(x))
                             for x in pieces)
                patterns.append((len("".join(x for x in pieces if x not in ("<slab>", "<i>"))), re.compile(f"^{rx}$"),
                                 c["semantic"]))
            else:
                self.exact[c["column"]] = c["semantic"]
        self.patterns = [(rx, sem) for _, rx, sem in sorted(patterns, key=lambda t: -t[0])]

    def semantic(self, column: str) -> str:
        if column in self.exact:
            return self.exact[column]
        for rx, sem in self.patterns:
            m = rx.match(column)
            if m:
                return sem.replace("<slab>", m.groupdict().get("slab") or "").replace("<i>", m.groupdict().get("i") or "")
        return column

    def rows(self, rows: list[dict]) -> list[dict]:
        names = {c: self.semantic(c) for c in rows[0]}
        return [{names[c]: v for c, v in r.items()} for r in rows]

    def selection(self, sel: list) -> list:
        return [{**c, "column": self.semantic(c["column"])} for c in sel or []]


def transmitted(rows: list[dict]) -> tuple[list[dict], dict]:
    kept = [r for r in rows if r.get("primary.fate") == 1 and r.get("primary.end_process") == "Transportation"]
    hadronic = sum(1 for r in rows if any(h in str(r.get("primary.end_process")) for h in HADRONIC_END))
    return kept, {"events": len(rows), "used": len(kept), "excluded": len(rows) - len(kept),
                  "excluded_fraction": (len(rows) - len(kept)) / len(rows), "ended_in_hadronic_process": hadronic}


FULL_INPUTS = ("density_g_cm3", "z_over_a", "mean_excitation_eV", "sternheimer", "reference_source")


def material(study: dict, name: str, need: tuple = FULL_INPUTS) -> dict:
    """The study spec's reference inputs for a material; only the keys a benchmark uses are required."""
    for m in study.get("materials", []):
        if m.get("name") == name:
            if m.get("reference_origin") == "geant4-material-dump":
                raise BenchmarkError(f"study spec material {name}: reference inputs from the Geant4 material dump are "
                                     "refused (an error in the spec would cancel)")
            for k in need:
                if k not in m:
                    raise BenchmarkError(f"study spec material {name}: {k} is required for this benchmark's "
                                         "reference inputs")
            if "sternheimer" in need:
                for k in ("a", "k", "x0", "x1", "Cbar", "delta0"):
                    if k not in m["sternheimer"]:
                        raise BenchmarkError(f"study spec material {name}: sternheimer.{k} is required")
            return m
    raise BenchmarkError(f"material {name} not in the study spec (reference inputs come from the spec, never the dump)")


def _tol(b: dict, se_rel: float, extra: float = 0.0) -> tuple[float, dict, float]:
    t = b.get("tolerance", {})
    acc = t.get("reference_accuracy_relative")
    k = t.get("k_sigma", 3.0)
    if not isinstance(acc, (int, float)) or acc < 0:
        raise BenchmarkError(f"{b['benchmark']}: tolerance.reference_accuracy_relative is required")
    total = acc + k * se_rel + extra
    return total, {"reference_accuracy": acc, "mc_statistics": k * se_rel, "k_sigma": k, "binning": extra}, \
        total + 2 * se_rel


TRANSMITTED = [{"column": "primary.fate", "op": "==", "value": 1},
               {"column": "primary.end_process", "op": "==", "value": "Transportation"}]
STOPPED = [{"column": "primary.fate", "op": "==", "value": 0}] + [
    {"column": "primary.end_process", "op": "!contains", "value": h} for h in HADRONIC_END]
SUMMARY_BENCHMARKS = ("stopping-power", "range", "thin-layer-mpv", "thin-layer-width", "longitudinal-profile")


class Summary:
    """The run summary (simulation-summary/1) behind a summary-based benchmark: validated, its observables estimated
    by core.simulation.estimates; each benchmark names the observables it needs and their required selection."""

    def __init__(self, path: Path, columns: Columns | None = None):
        self.path = path
        self.columns = columns or Columns()
        self.doc = json.loads(path.read_text(encoding="utf-8"))
        rep = schema_validate(self.doc, "simulation_summary.json")
        if self.doc.get("summary_version") != "simulation-summary/1" or not rep.ok:
            raise BenchmarkError(f"{path.name}: not a valid simulation-summary/1 "
                                 + "; ".join(f.message for f in rep.errors)[:200])

    def obs(self, name: str, column: str, selection: list, what: str) -> dict:
        try:
            o = S.observable(self.doc, name)
        except S.SummaryError as exc:
            raise BenchmarkError(f"{self.path.name}: {exc}") from exc
        got_col, got_sel = self.columns.semantic(o["source_column"]), self.columns.selection(o["selection"])
        if got_col != column or got_sel != selection:
            raise BenchmarkError(f"{self.path.name}: observable {name} must be {what} (column {column}, selection "
                                 f"{selection}), not column {got_col} with selection {got_sel} ({self.columns.source})")
        return o

    def estimate(self, o: dict, estimator: str, tol=None) -> dict:
        r = E.estimate(self.doc, {**o, "estimator": estimator}, tol)
        if r.get("status") != "ok":
            raise BenchmarkError(f"{self.path.name}: {o['name']} estimate incomplete ({r.get('reason')})")
        return r

    def selection(self, o: dict) -> dict:
        events = sum(b["events"] for b in o["blocks"])
        used = sum(b["n"] for b in o["blocks"])
        return {"events": events, "used": used, "excluded": events - used,
                "excluded_fraction": (events - used) / events if events else None, "blocks": len(o["blocks"])}


def bench_stopping_power(b: dict, summ: Summary, study: dict) -> dict:
    mat = material(study, b["material"])
    mass, z = particle_props(b["particle"])
    o = summ.obs(b["observable"], "primary.energy_loss", TRANSMITTED, "the energy loss of transmitted primaries")
    e = summ.estimate(o, "mean")
    t_cm = b["thickness_mm"] / 10
    mean_loss = e["value"]
    g4 = mean_loss / t_cm
    e_mid = b["energy_MeV"] - mean_loss / 2
    ref = bethe(e_mid, mass, z, mat) * mat["density_g_cm3"]
    ref_in = bethe(b["energy_MeV"], mass, z, mat) * mat["density_g_cm3"]
    _, _, bg = kinematics(b["energy_MeV"], mass)
    applicable = 0.1 <= bg <= 1000
    rel = (g4 - ref) / ref
    se_rel = e["se"] / mean_loss
    tol, parts, _ = _tol(b, se_rel)
    return {"statistic": "mean energy loss of transmitted primaries / thickness (MeV/cm); deposit is not energy loss",
            "geant4": g4, "geant4_se": e["se"] / t_cm, "geant4_dof": e["dof"], "reference_value": ref,
            "relative_difference": rel, "relative_se": se_rel, "tolerance": {"total": tol, "parts": parts},
            "verdict": ("pass" if abs(rel) <= tol else "fail") if applicable else "not-applicable",
            "selection": summ.selection(o), "beta_gamma": bg, "estimator": e["method"],
            "thin_slab_approximation": {"bethe_at_entry": ref_in, "bethe_at_mean_energy": ref,
                                        "relative_change": (ref - ref_in) / ref_in},
            "reference": {"source": f"Bethe mean rate, {RPP}, eq. 34.5, with I, Z/A, density and Sternheimer "
                                    f"parameters from the study spec ({mat['reference_source']})",
                          "version": "RPP 2024", "validity": "0.1 <~ beta gamma <~ 1000, accuracy a few percent"}}


def bench_range(b: dict, summ: Summary, study: dict, cfg_dir: Path) -> dict:
    table = json.loads((cfg_dir / b["reference_table"]).read_text(encoding="utf-8"))
    pts = sorted((float(p["energy_MeV"]), float(p["projected_range_g_cm2"])) for p in table["extension"]["points"]) \
        if "extension" in table else sorted((float(p["energy_MeV"]), float(p["projected_range_g_cm2"]))
                                            for p in table["points"])
    e = b["energy_MeV"]
    if not pts[0][0] <= e <= pts[-1][0]:
        raise BenchmarkError("range: the energy is outside the reference table")
    for (e0, r0), (e1, r1) in zip(pts, pts[1:]):
        if e0 <= e <= e1:
            ref = math.exp(math.log(r0) + (math.log(r1) - math.log(r0)) * (math.log(e) - math.log(e0))
                           / (math.log(e1) - math.log(e0)))
            break
    mat = material(study, b["material"], ("density_g_cm3", "reference_source"))
    o = summ.obs(b["observable"], "primary.end_position.x", STOPPED,
                 "the end position of primaries that stopped without a hadronic process")
    est = summ.estimate(o, "mean")
    x0 = b.get("entry_x_mm", 0.0)
    scale = mat["density_g_cm3"] / 10
    g4, se = (est["value"] - x0) * scale, est["se"] * scale
    rel = (g4 - ref) / ref
    tol, parts, _ = _tol(b, se / g4)
    return {"statistic": "mean projected stopping depth (g/cm^2) of primaries that stopped without a hadronic process",
            "geant4": g4, "geant4_se": se, "geant4_dof": est["dof"], "reference_value": ref,
            "relative_difference": rel, "relative_se": se / ref, "tolerance": {"total": tol, "parts": parts},
            "verdict": "pass" if abs(rel) <= tol else "fail", "selection": summ.selection(o),
            "estimator": est["method"],
            "reference": {"source": table.get("source", b["reference_table"]), "version": table.get("version"),
                          "validity": "projected range without nuclear interactions (PSTAR/ASTAR)"}}


def bench_mpv(b: dict, summ: Summary, study: dict) -> dict:
    mat = material(study, b["material"])
    mass, z = particle_props(b["particle"])
    lv = landau_mpv(b["energy_MeV"], mass, z, mat, b["thickness_mm"])
    width = b.get("binning", {}).get("bin_width_MeV")
    if not isinstance(width, (int, float)) or width <= 0:
        raise BenchmarkError("thin-layer-mpv: binning.bin_width_MeV is required")
    o = summ.obs(b["observable"], "primary.energy_loss", TRANSMITTED, "the energy loss of transmitted primaries")
    if abs(o["bins"]["width"] - width) > 1e-12 * width:
        raise BenchmarkError(f"thin-layer-mpv: the summary bins {o['bins']['width']} MeV, the config declares {width}")
    base = {"reference": {"source": f"most probable energy loss Delta_p, {RPP}, eq. 34.12 (j = 0.200), delta(beta "
                                    f"gamma) from Sternheimer parameters in the study spec ({mat['reference_source']})",
                          "version": "RPP 2024",
                          "validity": "kappa = xi / W_max < 0.05; RPP gives no numerical thickness range or accuracy: "
                                      "the thickness of validity and the accuracy are declared in the study spec"},
            "landau": lv, "selection": summ.selection(o),
            "estimator": f"mean of the three-point parabola modes of the K block histograms (bin width {width} MeV, "
                         "bins from the observable declaration), batch-means SE"}
    if lv["kappa"] >= 0.05:
        return {**base, "verdict": "not-applicable", "statistic": "most probable energy loss",
                "reason": f"kappa = {lv['kappa']:.4g} >= 0.05: not the Landau-Vavilov regime"}
    ref = lv["delta_p_MeV"]
    acc = (b.get("tolerance") or {}).get("reference_accuracy_relative")
    est = E.estimate(summ.doc, {**o, "estimator": "mode"}, acc)
    if est.get("status") != "ok":
        return {**base, "verdict": "not-applicable", "statistic": "most probable energy loss",
                "reason": f"MPV estimate incomplete ({est.get('reason')}; A1.7)", "mpv_estimate": est}
    g4, se = est["value"], est["se"]
    rel = (g4 - ref) / ref
    binning = width / math.sqrt(12) / ref
    tol, parts, _ = _tol(b, se / ref, binning)
    return {**base, "statistic": "most probable energy loss of transmitted primaries (MeV)", "geant4": g4,
            "geant4_se": se, "geant4_dof": est["dof"], "reference_value": ref, "relative_difference": rel,
            "relative_se": se / ref, "tolerance": {"total": tol, "parts": parts},
            "verdict": "pass" if abs(rel) <= tol else "fail",
            "mpv_checks": {"fallback_blocks": est["fallback_blocks"], "merged_mode": est.get("merged_mode"),
                           "merged_check": est.get("merged_check")}}


def bench_width(b: dict, summ: Summary, study: dict) -> dict:
    mat = material(study, b["material"])
    mass, z = particle_props(b["particle"])
    lv = landau_mpv(b["energy_MeV"], mass, z, mat, b["thickness_mm"])
    o = summ.obs(b["observable"], f"energy_deposit.{b['slab']}", TRANSMITTED, "the deposit of transmitted primaries")
    hist, w = S.merged_accumulators(o)["hist"], o["bins"]["width"]
    peak = max(hist)
    above = [i for i, c in enumerate(hist) if c >= peak / 2]
    g4 = (above[-1] - above[0] + 1) * w
    ref = 4 * lv["xi_MeV"]
    return {"statistic": "FWHM of the deposit distribution (MeV)", "geant4": g4, "reference_value": ref,
            "relative_difference": (g4 - ref) / ref, "verdict": "plausible" if 0.5 <= g4 / ref <= 3 else "implausible",
            "plausibility_window": "0.5 to 3 x the Landau width (thin layers are wider than 4 xi, RPP 2024)",
            "selection": summ.selection(o), "reference": {"source": f"Landau FWHM 4 xi, {RPP}", "version": "RPP 2024",
                                                          "validity": "sanity only"}}


def bench_ms(b: dict, rows: list[dict], study: dict, cfg_dir: Path) -> dict:
    kept, sel = transmitted(rows)
    angles = []
    for r in kept:
        angles += [math.atan2(r["primary.exit_direction.y"], r["primary.exit_direction.x"]),
                   math.atan2(r["primary.exit_direction.z"], r["primary.exit_direction.x"])]
    angles.sort()
    cut = int(0.01 * len(angles))
    core = angles[cut:len(angles) - cut] if cut else angles
    g4 = math.sqrt(statistics.fmean(a * a for a in core)) / TRUNC_98
    stack = b.get("highland_stack")
    if not stack:
        raise BenchmarkError("multiple-scattering: highland_stack (a multiple_scattering.py input) is required")
    p = subprocess.run([sys.executable, "-B", str(MS_SCRIPT), str(cfg_dir / stack)], capture_output=True, text=True,
                       timeout=600)
    try:
        ms = json.loads(p.stdout)
    except ValueError as exc:
        raise BenchmarkError(f"multiple_scattering.py printed no JSON: {p.stderr[-300:]}") from exc
    ref = ms.get("scattering_angle_rad")  # Highland theta0 of the stack (multiple_scattering.py)
    if not isinstance(ref, (int, float)):
        raise BenchmarkError(f"multiple_scattering.py output has no theta0: {sorted(ms)}")
    return {"statistic": "core width of the projected exit angle (rad)", "geant4": g4, "reference_value": ref,
            "relative_difference": (g4 - ref) / ref, "verdict": "plausible" if abs(g4 / ref - 1) <= 0.2 else
            "implausible", "plausibility_window": "within 20 % of Highland", "selection": sel,
            "reference": {"source": f"Highland (Lynch and Dahl) via multiple_scattering.py; {RPP}, eq. 34.16",
                          "version": "RPP 2024", "validity": "sanity only: RPP 2024 gives no numerical accuracy; "
                                                              "the beta dependence is poor for large Z, small x"}}


def bench_shower(b: dict, rows: list[dict], study: dict) -> dict:
    copy = "energy_deposit.copy"
    cols = sorted((c for c in rows[0] if c.startswith(copy) and c[len(copy):].isdigit()), key=lambda c: int(c[len(copy):]))
    if not cols:
        raise BenchmarkError("em-shower-shape: needs per-copy deposits (output.per_instance)")
    profile = [statistics.fmean(r[c] for r in rows) for c in cols]
    t_layer = b["layer_x0"]
    k = max(range(len(profile)), key=profile.__getitem__)
    g4 = (k + 0.5) * t_layer
    ref = math.log(b["energy_MeV"] / b["critical_energy_MeV"]) + (-0.5 if b["particle"] in ("e-", "e+") else 0.5)
    depth = len(profile) * t_layer
    if ref >= depth:
        return {"statistic": "depth of the longitudinal maximum (X0)", "verdict": "not-applicable",
                "reason": f"the expected shower maximum {ref:.3g} X0 is not contained in the {depth:.3g} X0 stack",
                "reference": {"source": f"t_max = ln(E/E_c) + C_j, {RPP}, eq. 34.36", "version": "RPP 2024",
                              "validity": "never validation"}}
    return {"statistic": "depth of the longitudinal maximum (X0)", "geant4": g4, "reference_value": ref,
            "relative_difference": (g4 - ref) / ref, "verdict": "plausible" if abs(g4 - ref) <= 1.5 else "implausible",
            "plausibility_window": "within 1.5 X0", "reference": {"source": f"t_max = ln(E/E_c) + C_j, {RPP}, eq. 34.36",
                                                                 "version": "RPP 2024", "validity": "never validation"}}


def gamma_p(a: float, x: float) -> float:
    """Regularized lower incomplete gamma function P(a, x): series for x < a + 1, else the continued fraction."""
    if x <= 0:
        return 0.0
    lg = math.lgamma(a)
    if x < a + 1:
        term = total = 1.0 / a
        n = a
        for _ in range(1000):
            n += 1
            term *= x / n
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return total * math.exp(-x + a * math.log(x) - lg)
    tiny = 1e-300
    b_ = x + 1 - a
    c, d = 1 / tiny, 1 / b_
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b_ += 2
        d = an * d + b_
        d = tiny if abs(d) < tiny else d
        c = b_ + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return 1 - math.exp(-x + a * math.log(x) - lg) * h


def bench_containment(b: dict, rows: list[dict]) -> dict:
    """Rear leakage fraction of an EM shower against the PDG gamma-function profile (sanity only)."""
    for k in ("depth_x0", "critical_energy_MeV"):
        if not isinstance(b.get(k), (int, float)) or b[k] <= 0:
            raise BenchmarkError(f"shower-containment: {k} (from the study spec or PDG, never the dump) is required")
    if "leakage.rear" not in rows[0]:
        raise BenchmarkError("shower-containment needs the rear leakage column (layered_sim with leakage by face)")
    ref_block = {"source": f"longitudinal profile dE/dt = E0 b (bt)^(a-1) e^(-bt) / Gamma(a), {RPP}, Eqs. 34.34-34.36 "
                           "(fits to EGS4 showers, carbon to uranium, 1 to 100 GeV)", "version": "RPP 2024",
                 "validity": "sanity only: the profile is itself a fit to simulated showers and RPP states no accuracy; "
                             "b depends on Z and energy (RPP Fig. 34.21), b = 0.5 by default"}
    e = b["energy_MeV"]
    if not 1000.0 <= e <= 100000.0 or b["particle"] not in ("e-", "e+", "gamma"):
        return {"statistic": "rear leakage fraction", "verdict": "not-applicable", "reference": ref_block,
                "reason": "the fitted profile covers e+-, gamma showers from 1 to 100 GeV only"}
    bpar = b.get("b", 0.5)
    tmax = math.log(e / b["critical_energy_MeV"]) + (-0.5 if b["particle"] in ("e-", "e+") else 0.5)
    a = 1 + bpar * tmax
    ref = 1 - gamma_p(a, bpar * b["depth_x0"])
    vals = [r["leakage.rear"] / r["primary.kinetic_energy"] for r in rows]
    g4 = statistics.fmean(vals)
    window = max(0.3 * min(ref, 1 - ref), 0.02)
    return {"statistic": "rear leakage fraction (energy leaving the +x face over the primary kinetic energy)",
            "geant4": g4, "geant4_se": statistics.stdev(vals) / math.sqrt(len(vals)), "reference_value": ref,
            "relative_difference": (g4 - ref) / ref if ref else None, "profile": {"a": a, "b": bpar, "t_max": tmax},
            "verdict": "plausible" if abs(g4 - ref) <= window else "implausible",
            "plausibility_window": f"within {window:.3g} (absolute) of the profile",
            "albedo_fraction": statistics.fmean(r["leakage.front"] / r["primary.kinetic_energy"] for r in rows),
            "reference": ref_block}


def gamma_profile(t: float, alpha: float, beta: float) -> float:
    """beta (beta t)^(alpha-1) e^(-beta t) / Gamma(alpha): the unit-normalized longitudinal profile."""
    return math.exp(math.log(beta) + (alpha - 1) * math.log(beta * t) - beta * t - math.lgamma(alpha))


def _linear_amplitudes(ts, ys, ws, alpha, beta):
    """Weighted least-squares Q_E and Q0 of y = Q_E g(t) + Q0 for fixed alpha, beta; returns (chi2, Q_E, Q0)."""
    g = [gamma_profile(t, alpha, beta) for t in ts]
    s_w, s_g, s_gg = sum(ws), sum(w * x for w, x in zip(ws, g)), sum(w * x * x for w, x in zip(ws, g))
    s_y, s_gy = sum(w * y for w, y in zip(ws, ys)), sum(w * x * y for w, x, y in zip(ws, g, ys))
    det = s_gg * s_w - s_g * s_g
    if det <= 0:
        return math.inf, 0.0, 0.0
    qe, q0 = (s_gy * s_w - s_g * s_y) / det, (s_gg * s_y - s_g * s_gy) / det
    return sum(w * (y - qe * x - q0) ** 2 for w, x, y in zip(ws, g, ys)), qe, q0


def fit_gamma_profile(ts, ys, ses) -> dict:
    """Fit of Q_E Gamma-profile + Q0 to (t, y +- se): Q_E and Q0 linear, (ln alpha, ln beta) by Nelder-Mead."""
    ws = [1 / s ** 2 if s > 0 else 0.0 for s in ses]
    k = max(range(len(ys)), key=ys.__getitem__)
    start = [math.log(1 + 0.5 * ts[k]), math.log(0.5)]

    def f(v):
        return _linear_amplitudes(ts, ys, ws, math.exp(v[0]), math.exp(v[1]))[0]
    simplex = [start, [start[0] + 0.1, start[1]], [start[0], start[1] + 0.1]]
    vals = [f(v) for v in simplex]
    for _ in range(2000):
        order = sorted(range(3), key=vals.__getitem__)
        simplex, vals = [simplex[i] for i in order], [vals[i] for i in order]
        if abs(vals[2] - vals[0]) <= 1e-12 * (abs(vals[0]) + 1e-300) and max(
                abs(simplex[i][j] - simplex[0][j]) for i in (1, 2) for j in (0, 1)) < 1e-10:
            break
        c = [(simplex[0][j] + simplex[1][j]) / 2 for j in (0, 1)]
        r = [c[j] + (c[j] - simplex[2][j]) for j in (0, 1)]
        fr = f(r)
        if fr < vals[0]:
            e = [c[j] + 2 * (c[j] - simplex[2][j]) for j in (0, 1)]
            fe = f(e)
            simplex[2], vals[2] = (e, fe) if fe < fr else (r, fr)
        elif fr < vals[1]:
            simplex[2], vals[2] = r, fr
        else:
            cc = [c[j] + 0.5 * (simplex[2][j] - c[j]) for j in (0, 1)]
            fc = f(cc)
            if fc < vals[2]:
                simplex[2], vals[2] = cc, fc
            else:
                for i in (1, 2):
                    simplex[i] = [simplex[0][j] + 0.5 * (simplex[i][j] - simplex[0][j]) for j in (0, 1)]
                    vals[i] = f(simplex[i])
    best = min(range(3), key=vals.__getitem__)
    alpha, beta = math.exp(simplex[best][0]), math.exp(simplex[best][1])
    chi2, qe, q0 = _linear_amplitudes(ts, ys, ws, alpha, beta)
    return {"alpha": alpha, "beta": beta, "Q_E": qe, "Q0": q0, "t_max": (alpha - 1) / beta, "chi2": chi2,
            "ndf": len(ts) - 4}


def bench_profile(b: dict, summ: Summary) -> dict:
    """t_max of the per-layer mean profile against the same Gamma fit to published test-beam data; the Gamma fit is
    made in every block (layer means of the block, weights from the spread of the block means) and t_max is their
    batch mean (A1.6)."""
    layers = b.get("layers")
    if not isinstance(layers, list) or len(layers) < 5 or not all(
            isinstance(x, dict) and isinstance(x.get("t"), (int, float)) and x.get("observable") for x in layers):
        raise BenchmarkError("longitudinal-profile: layers must list at least five {t, observable} (summary "
                             "observables of the layer deposits)")
    pub = b.get("published") or {}
    try:
        (a_ref, a_se), (b_ref, b_se) = pub["alpha"], pub["beta"]
    except (KeyError, TypeError, ValueError):
        raise BenchmarkError("longitudinal-profile: published needs alpha and beta as [value, uncertainty]") from None
    if not pub.get("source"):
        raise BenchmarkError("longitudinal-profile: published.source (citation and table) is required")
    ts = [x["t"] for x in layers]
    obs = []
    for x in layers:
        try:
            obs.append(S.observable(summ.doc, x["observable"]))
        except S.SummaryError as exc:
            raise BenchmarkError(f"longitudinal-profile: {exc}") from exc
    per_block = [S.block_means(o) for o in obs]  # [layer][block]
    k = len(per_block[0])
    spread = [statistics.stdev(v) if len(v) > 1 else 0.0 for v in per_block]
    tmax = [fit_gamma_profile(ts, [per_block[j][i] for j in range(len(ts))], spread)["t_max"] for i in range(k)]
    est = batch_mean(tmax)
    merged = fit_gamma_profile(ts, [statistics.fmean(v) for v in per_block], [s / math.sqrt(k) for s in spread])
    ref = (a_ref - 1) / b_ref
    ref_se = math.hypot(a_se / b_ref, (a_ref - 1) * b_se / b_ref ** 2)
    syst = b.get("systematic_relative", 0.0)
    if not isinstance(syst, (int, float)) or syst < 0:
        raise BenchmarkError("longitudinal-profile: systematic_relative must be a nonnegative number")
    b = {**b, "tolerance": {**b.get("tolerance", {}), "reference_accuracy_relative": ref_se / ref + syst}}
    rel = (est["value"] - ref) / ref
    tol, parts, _ = _tol(b, est["se"] / est["value"])
    parts["published_uncertainty"], parts["systematic"] = ref_se / ref, syst
    return {"statistic": "shower maximum t_max = (alpha - 1) / beta of the Gamma fit to the per-layer mean deposits "
                         "(layer units)",
            "geant4": est["value"], "geant4_se": est["se"], "geant4_dof": est["dof"], "reference_value": ref,
            "reference_se": ref_se, "relative_difference": rel, "relative_se": est["se"] / ref,
            "tolerance": {"total": tol, "parts": parts}, "verdict": "pass" if abs(rel) <= tol else "fail",
            "fit": {kk: merged[kk] for kk in ("alpha", "beta", "Q_E", "Q0", "chi2", "ndf")},
            "estimator": "batch mean of the per-block Gamma-fit t_max",
            "published_fit": {"alpha": [a_ref, a_se], "beta": [b_ref, b_se]}, "layers_fitted": ts,
            "events": sum(bb["events"] for bb in obs[0]["blocks"]),
            "reference": {"source": pub["source"], "version": pub.get("version"),
                          "validity": "the measured configuration only (stack, energy, particle, readout window); "
                                      + (pub.get("validity") or "")}}


def bench_published(b: dict, rows: list[dict], columns: Columns | None = None) -> dict:
    col = (columns or Columns()).semantic(b.get("column") or "")
    if not col or col not in rows[0]:
        raise BenchmarkError("published-data: 'column' must name a column of the run (semantic or CSV name)")
    vals = [r[col] for r in rows]
    return {"statistic": f"mean of {col}", "geant4": statistics.fmean(vals),
            "geant4_se": statistics.stdev(vals) / math.sqrt(len(vals)), "published": b.get("published"),
            "verdict": "handoff", "handoff": {"to_skill": "hep-statistics",
                                              "reason": "compatibility with a published measurement is a statistical "
                                                        "question; this benchmark gives no verdict"},
            "reference": {"source": "published measurement (dataset-record)", "version": None, "validity": "interface"}}


def geant4_installation(rec: dict) -> dict | None:
    """What a run record states about the Geant4 installation it ran with (adapters/geant4 0.6.0 writes
    extension.simulation.geant4.origin): `built-from-source` (geant4_build.py build: tag, commit, MD5-checked datasets)
    or `registered` (geant4_build.py register: an existing installation; no source commit, build options or dataset
    MD5s, the datasets content-hashed only), the latter reported as weaker provenance. None for a record without an
    origin (written before 0.6.0, always by a source build), so older outputs are unchanged. Reported, never a gap: the
    benchmarks and their references decide validity, not how Geant4 was installed."""
    g = ((rec.get("extension") or {}).get("simulation") or {}).get("geant4") or {}
    if not g.get("origin"):
        return None
    out = {"origin": g["origin"], "version": g.get("installation_version") or g.get("version"),
           "commit": g.get("commit")}
    if g["origin"] == "registered":
        out["provenance"] = ("weaker: a registered installation (source commit, build options and dataset MD5s "
                             "unknown; datasets content-hashed only)")
    return out


def configuration(b: dict, cfg_dir: Path) -> dict:
    """CV-A1 (A1.3): configuration, target hash (hash_scheme spec-v1) and its basis, derived from the spec/1 of the
    run record the setting names (run_record), never from user input. The target is target_slabs (absorbers
    included), by default the measured slab; longitudinal-profile must list its whole sampling stack."""
    rr = b.get("run_record")
    if not rr:
        return {"configuration": None, "configuration_gap": "no run_record: the configuration cannot be derived"}
    path = cfg_dir / rr
    raw = path.read_bytes()
    rec = json.loads(raw.decode("utf-8"))
    targets = b.get("target_slabs") or ([b["slab"]] if b.get("slab") and b["benchmark"] != "longitudinal-profile"
                                        else None)
    if not targets:
        raise BenchmarkError(f"{b['benchmark']}: target_slabs (the slabs of the target, absorbers included) is required")
    sim = (rec.get("extension") or {}).get("simulation") or {}
    ec = sim.get("effective_config")
    if isinstance(ec, dict) and not ec.get("recorded"):
        return {"configuration": None, "configuration_gap": "the run's probe recorded no effective config (recorded: "
                                                            "false): this run cannot upgrade (A2.4)"}
    try:  # A2.6: records from adapter 0.2.0 use tree-v1 (the effective config), A1 records spec-v1
        conf = geant4_configuration(sim, targets, "tree-v1" if isinstance(ec, dict) else "spec-v1")
    except ValueError as exc:
        raise BenchmarkError(f"{b['benchmark']}: {exc}") from exc
    out = {**conf, "configuration_basis": {"run_record": rr, "artifact_id": rec.get("artifact_id"),
                                           "sha256": hashlib.sha256(raw).hexdigest()}}
    inst = geant4_installation(rec)
    if inst:  # adapter 0.6.0 records: how Geant4 was installed (a registered installation is weaker provenance)
        out["configuration_basis"]["geant4_installation"] = inst
    if "measured_configuration" in b:
        out["measured_configuration"] = b["measured_configuration"]
    return out


# --- CV-B2 detector benchmarks (Geant4 program B2.7) --------------------------------------------------------------

def _canonical_sha(doc) -> str:
    return hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def field_configuration_sha256(spec: dict) -> str:
    """B2.8 condition 2's key: the field regions of an element_sim spec (each region's box and B) and the accuracy
    parameters, canonical JSON (sorted keys, no whitespace)."""
    els = {e["name"]: e for e in spec.get("elements", [])}
    f = spec.get("field") or {}
    regions = sorted(([[float(els[r["element"]]["centre_mm"][i]) for i in range(3)],
                       [float(els[r["element"]]["half_mm"][i]) for i in range(3)],
                       [float(x) for x in r["b_tesla"]]] for r in f.get("regions", [])), key=json.dumps)
    acc = {k: f[k] for k in sorted(f) if k != "regions"}
    return _canonical_sha({"regions": regions, "accuracy": acc})


def reco_spec_sha256(reco: dict) -> str:
    """B2.8 condition 3's key: the reco spec without its tail sources, replicas, outputs and note (the reconstruction
    itself), so the closure with tail sources off and the study with them on share it."""
    return _canonical_sha({k: v for k, v in reco.items() if k not in ("tail_sources", "replicas", "output", "note")})


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_dump(path: Path) -> list[dict]:
    """Rows of a simroot dump CSV (numbers as floats, strings kept)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    cols = lines[0].split(",")
    out = []
    for ln in lines[1:]:
        if ln:
            out.append({c: (float(v) if _is_num(v) else v) for c, v in zip(cols, ln.split(","))})
    return out


def _summary_obs(cfg_dir: Path, path: str, name: str) -> tuple[dict, dict]:
    doc = json.loads((cfg_dir / path).read_text(encoding="utf-8"))
    rep = schema_validate(doc, "simulation_summary.json")
    if not rep.ok:
        raise BenchmarkError(f"{path}: not a valid simulation-summary/1")
    try:
        return doc, S.observable(doc, name)
    except S.SummaryError as exc:
        raise BenchmarkError(f"{path}: {exc}") from exc


def _mean_sd(o: dict) -> tuple[float, float, int]:
    n = sum(b["n"] for b in o["blocks"])
    if n < 2:
        raise BenchmarkError(f"observable {o['name']}: fewer than two entries")
    s = math.fsum(b["sum"] for b in o["blocks"])
    ss = math.fsum(b["sumsq"] for b in o["blocks"])
    mean = s / n
    return mean, math.sqrt(max(ss / n - mean * mean, 0.0) * n / (n - 1)), n


def _equiv(diff: float, se: float, dof: float, tol: float) -> str:
    return {"pass": "pass", "fail": "fail", "unresolved": "unresolved"}[equivalence(diff, se, dof, tol)["verdict"]]


def bench_field_propagation(b: dict, cfg_dir: Path) -> dict:
    """field-propagation (verification): charged geantinos of an element_sim run against the analytic helix
    (core/simulation/helix.py, the oracle of B1.7) from the run's crossings (simroot dump); scope the field
    configuration hash of the reference field (default the run's own)."""
    spec = json.loads((cfg_dir / b["element_spec"]).read_text(encoding="utf-8"))
    ref = json.loads((cfg_dir / b["reference_spec"]).read_text(encoding="utf-8")) if b.get("reference_spec") else spec
    tol_um, tol_ps = float(b.get("tolerance_um", 0.5)), float(b.get("tolerance_ps", 1.0))
    try:
        res = H.compare_crossings(spec, read_dump(cfg_dir / b["crossings"]), ref, tol_um, tol_ps)
    except ValueError as exc:
        raise BenchmarkError(f"field-propagation: {exc}") from exc
    return {"statistic": "largest in-plane distance from the analytic helix (um) and TOF time difference (ps)",
            "geant4": res["max_in_plane_um"], "reference_value": 0.0, "max_dt_ps": res["max_dt_ps"],
            "compared": res["compared"], "verdict": "pass" if not res["problems"] else "fail",
            "problems": res["problems"][:20], "tolerance": {"in_plane_um": tol_um, "time_ps": tol_ps},
            "scope": {"field_configuration_sha256": field_configuration_sha256(ref)},
            "reference": {"source": "analytic helix of a charged particle in uniform fields (core/simulation/helix.py)",
                          "version": "exact", "validity": "deterministic: charged geantinos have no interactions"}}


def bench_material_definition(b: dict, study: dict, cfg_dir: Path) -> dict:
    """material-definition (verification, B2.8 condition 1): every material of the realized geometry has a study-spec
    entry of independent origin whose density equals Geant4's resolved density (relative 1e-3, the effective
    config's tree), and a geantino scan reproduces the candidate's declared layer_x_over_x0 (and passive_x_over_x0)
    within the declared relative tolerance, with the independent radiation length; scope the geometry and
    realization-profile hashes."""
    spec = json.loads((cfg_dir / b["element_spec"]).read_text(encoding="utf-8"))
    geo = json.loads((cfg_dir / b["geometry"]).read_text(encoding="utf-8"))
    rec = json.loads((cfg_dir / b["run_record"]).read_text(encoding="utf-8"))
    tree = ((((rec.get("extension") or {}).get("simulation") or {}).get("effective_config") or {}).get("geometry")
            or {}).get("tree") or {}
    resolved = {m["name"]: float.fromhex(m["density_g_cm3"]) for m in tree.get("materials", [])}
    if not resolved:
        raise BenchmarkError("material-definition: the run record has no effective-config geometry tree")
    tol = float(b.get("tolerance_relative", 0.01))
    problems, rows = [], []
    used = {spec["world"]["material"]} | {e["material"] for e in spec["elements"]}
    for name in sorted(used):
        if name in resolved and resolved[name] < 1e-20:  # vacuum (G4_Galactic): no material to define
            continue
        m = next((x for x in study.get("materials", []) if x.get("name") == name), None)
        if m is None or m.get("reference_origin") != "independent":
            problems.append(f"{name}: no study-spec material of independent origin (reference_origin independent)")
            continue
        if name not in resolved:
            problems.append(f"{name}: not among the materials Geant4 resolved (effective-config tree)")
        elif abs(resolved[name] / m["density_g_cm3"] - 1) > 1e-3:
            problems.append(f"{name}: Geant4 density {resolved[name]:.6g} g/cm3 differs from the independent "
                            f"{m['density_g_cm3']} g/cm3")
    if not b.get("column_map"):
        raise BenchmarkError("material-definition: column_map (the geantino run's column map) is required")
    rows_csv = _columns(b, cfg_dir).rows(read_csv(cfg_dir / b["csv"]))
    planes = [e for e in spec["elements"] if e["role"] == "tracker-plane"]
    declared = (geo.get("fields") or {}).get("layer_x_over_x0")
    if declared is None:
        raise BenchmarkError("material-definition: the geometry file has no layer_x_over_x0")
    decl = declared if isinstance(declared, list) else [declared] * len(planes)
    if len(decl) != len(planes):
        raise BenchmarkError(f"material-definition: {len(decl)} declared layer_x_over_x0 values for {len(planes)} "
                             "tracker planes")
    passive_decl = float((geo.get("fields") or {}).get("passive_x_over_x0") or 0.0)
    prof = json.loads((cfg_dir / b["realization"]).read_text(encoding="utf-8"))
    pname = ((prof.get("templates") or {}).get("passive") or {}).get("element")  # the element passive_x_over_x0 makes
    passive = [e for e in spec["elements"] if e["name"] == pname]
    if passive_decl > 0 or passive:  # B2.8 condition 1 also covers the passive material
        m_x0 = {x["name"]: x.get("radiation_length_mm") for x in study.get("materials", [])}
        got = 0.0
        for e in passive:
            x0 = m_x0.get(e["material"])
            if not isinstance(x0, (int, float)):
                problems.append(f"{e['material']}: no independent radiation_length_mm (passive element {e['name']})")
                continue
            got += statistics.fmean(r[f"{PATH_LENGTH}.{e['name']}"] for r in rows_csv) / x0
        rel = got / passive_decl - 1 if passive_decl > 0 else (math.inf if got > 0 else 0.0)
        rows.append({"element": "passive", "geantino_x_over_x0": got, "declared": passive_decl, "relative": rel})
        if abs(rel) > tol:
            problems.append(f"passive material: geantino x/X0 {got:.6g} against the declared passive_x_over_x0 "
                            f"{passive_decl}")
    for e, want in zip(planes, decl):
        m = next((x for x in study.get("materials", []) if x.get("name") == e["material"]), {})
        x0 = m.get("radiation_length_mm")
        if not isinstance(x0, (int, float)):
            problems.append(f"{e['material']}: no independent radiation_length_mm")
            continue
        path = statistics.fmean(r[f"{PATH_LENGTH}.{e['name']}"] for r in rows_csv)
        got = path / x0
        rows.append({"element": e["name"], "geantino_x_over_x0": got, "declared": want, "relative": got / want - 1})
        if abs(got / want - 1) > tol:
            problems.append(f"{e['name']}: geantino x/X0 {got:.6g} differs from the declared {want} by more than {tol}")
    return {"statistic": "geantino x/X0 per tracker plane against the candidate; densities against independent sources",
            "rows": rows, "verdict": "pass" if not problems else "fail", "problems": problems,
            "tolerance": {"relative": tol, "density_relative": 1e-3},
            "scope": {"geometry_sha256": file_sha256(cfg_dir / b["geometry"]),
                      "realization_sha256": file_sha256(cfg_dir / b["realization"])},
            "reference": {"source": "the study spec's independent material sources and the candidate's declared x/X0",
                          "version": "as declared", "validity": "verification of the realized geometry"}}


def bench_reco_closure(b: dict, cfg_dir: Path) -> dict:
    """reco-closure (verification, B2.8 condition 3): simreco on charged geantinos (no multiple scattering, no energy
    loss) at high rigidity with every tail source off: the pull width within 1 +- 3 sigma_MC (sigma_MC = 1/sqrt(2n))
    and the mean of the relative inverse-rigidity residual within 3 SE of zero; scope the reco-spec hash (tail sources,
    replicas and outputs excluded)."""
    rec = json.loads((cfg_dir / b["reco_record"]).read_text(encoding="utf-8"))
    rx = (rec.get("extension") or {}).get("reconstruction") or {}
    if rx.get("tail_sources_simulated"):
        raise BenchmarkError("reco-closure: the reconstruction must have every tail source off")
    _, pull = _summary_obs(cfg_dir, b["summary"], b["pull_observable"])
    _, res = _summary_obs(cfg_dir, b["summary"], b["residual_observable"])
    pm, psd, n = _mean_sd(pull)
    rm, rsd, nr = _mean_sd(res)
    smc = 1 / math.sqrt(2 * n)
    problems = []
    if abs(psd - 1) > 3 * smc:
        problems.append(f"pull width {psd:.4f} outside 1 +- 3 x {smc:.4f}")
    if abs(rm) > 3 * rsd / math.sqrt(nr):
        problems.append(f"mean relative residual {rm:.3g} beyond 3 SE ({rsd / math.sqrt(nr):.3g})")
    return {"statistic": "pull width and bias of the signed inverse rigidity", "geant4": psd, "reference_value": 1.0,
            "pull_mean": pm, "pull_width": psd, "pull_width_mc_sigma": smc, "residual_mean": rm, "entries": n,
            "verdict": "pass" if not problems else "fail", "problems": problems,
            "scope": {"reco_spec_sha256": reco_spec_sha256(rx.get("reco_spec") or {}),
                      "rigidity_GV": b.get("rigidity_GV"), "particle": b.get("particle")},
            "reference": {"source": "the truth of the simulated charged geantinos", "version": "exact",
                          "validity": "closure of the fit; no physics"}}


def _summary_equivalence(b: dict, cfg_dir: Path, what: str, target: float) -> dict:
    _, o = _summary_obs(cfg_dir, b["summary"], b["observable"])
    mean, sd, n = _mean_sd(o)
    se = sd / math.sqrt(n)
    tol = float(b["tolerance_absolute"])
    verdict = _equiv(mean - target, se, n - 1, tol)
    return {"statistic": what, "geant4": mean, "reference_value": target, "se": se, "sd": sd, "entries": n,
            "tolerance": {"absolute": tol}, "verdict": verdict}


def bench_field_propagation_muon(b: dict, cfg_dir: Path) -> dict:
    """field-propagation-muon (sanity): the mean of (1/R_reco - 1/R_true) R_true of simreco on muons against 0,
    decided by equivalence within the declared absolute tolerance."""
    r = _summary_equivalence(b, cfg_dir, "mean relative inverse-rigidity residual of muons", 0.0)
    r["reference"] = {"source": "plane-averaged true 1/R (B2.1)", "version": "-", "validity": "sanity"}
    return r


def bench_tof_beta(b: dict, cfg_dir: Path) -> dict:
    """tof-beta (verification, bookkeeping): the mean of beta_reco / beta_true - 1 against 0 (equivalence)."""
    r = _summary_equivalence(b, cfg_dir, "mean relative beta residual", 0.0)
    r["reference"] = {"source": "kinematics along the true trajectory", "version": "-",
                      "validity": "bookkeeping verification (no physics control on the Geant4 side)"}
    return r


def bench_tof_layer_consistency(b: dict, cfg_dir: Path) -> dict:
    """tof-layer-consistency (verification, bookkeeping): a station's two-layer time-difference residual has mean 0 and
    width sqrt(2) sigma_t (both within the declared tolerances)."""
    r = _summary_equivalence(b, cfg_dir, "two-layer time-difference residual (ps)", 0.0)
    want = math.sqrt(2) * float(b["sigma_t_ps"])
    rel = r["sd"] / want - 1
    r["width"] = {"geant4": r["sd"], "expected": want, "relative": rel,
                  "tolerance_relative": float(b.get("width_tolerance_relative", 0.1))}
    if abs(rel) > r["width"]["tolerance_relative"]:
        r["verdict"] = "fail"
    r["reference"] = {"source": "inter-layer path / (beta c), widths sqrt(2) sigma_t", "version": "-",
                      "validity": "bookkeeping verification"}
    return r


def bench_sampling_fraction(b: dict, cfg_dir: Path) -> dict:
    """sampling-fraction (sanity): sum of active deposits over active plus passive, against a declared plausible value
    (with its source) within the declared window (default 10 %)."""
    doc = json.loads((cfg_dir / b["summary"]).read_text(encoding="utf-8"))
    a = S.observable(doc, b["active_observable"])
    p = S.observable(doc, b["passive_observable"])
    sa, sp = math.fsum(x["sum"] for x in a["blocks"]), math.fsum(x["sum"] for x in p["blocks"])
    blocks = [x["sum"] / (x["sum"] + y["sum"]) for x, y in zip(a["blocks"], p["blocks"]) if x["sum"] + y["sum"] > 0]
    bm = batch_mean(blocks)
    ref = float(b["reference_value"])
    window = float(b.get("window_relative", 0.10))
    value = sa / (sa + sp)
    return {"statistic": "sampling fraction sum(active) / sum(active + passive)", "geant4": value, "se": bm["se"],
            "reference_value": ref, "relative_difference": value / ref - 1,
            "verdict": "plausible" if abs(value / ref - 1) <= window else "implausible",
            "plausibility_window": f"within {window:.0%} of the reference",
            "reference": {"source": b.get("reference_source", "declared"), "version": "-", "validity": "sanity"}}


def lynch_dahl_theta0(z_target: float, a_target: float, x_g_cm2: float, p_mev: float, beta: float, charge: int = 1,
                      fraction: float = 0.98) -> float:
    """theta0 (rad) of the Gaussian fitted to the central fraction F of the Moliere distribution (Lynch and Dahl
    1991): chi_c^2 = 0.157 Z(Z+1) X/A z^2/(p beta)^2, chi_a^2 = 2.007e-5 Z^(2/3) [1 + 3.34 (Z z alpha/beta)^2]/p^2
    (p in MeV/c, X in g/cm2), Omega = chi_c^2 / (1.167 chi_a^2), v = Omega / (2 (1 - F)),
    theta0^2 = chi_c^2 / (1 + F^2) [(1 + v)/v ln(1 + v) - 1]."""
    alpha = K.constant("fine_structure_constant").value
    chic2 = 0.157 * z_target * (z_target + 1) * x_g_cm2 / a_target * charge ** 2 / (p_mev * beta) ** 2
    chia2 = 2.007e-5 * z_target ** (2 / 3) * (1 + 3.34 * (z_target * charge * alpha / beta) ** 2) / p_mev ** 2
    omega = chic2 / (1.167 * chia2)
    v = 0.5 * omega / (1 - fraction)
    return math.sqrt(chic2 / (1 + fraction ** 2) * ((1 + v) / v * math.log(1 + v) - 1))


def _exit_angles(rows: list[dict], plane_id: int) -> dict[int, list[float]]:
    """Per event, the two projected angles of the primary at its entry into the downstream measuring plane (the
    direction after the slab: vacuum and no field in between)."""
    out = {}
    for r in rows:
        if int(r["track_id"]) == 1 and int(r["plane_id"]) == plane_id:
            out[int(r["event_id"])] = [math.atan2(r["dy"], r["dx"]), math.atan2(r["dz"], r["dx"])]
    return out


def _core98(angles: list[float], fraction: float = 0.98) -> float:
    """Lynch and Dahl's core width: the sigma of a zero-mean Gaussian fitted (maximum likelihood, truncated normal) to
    the angles inside the symmetric window |x| <= c that holds the central fraction F. Not RMS / 0.8673: that assumes
    the inner 98 % is itself Gaussian, and the single-scattering tail inside the window widens it by about 10 %."""
    mags = sorted(abs(x) for x in angles)
    c = mags[min(len(mags) - 1, int(fraction * len(mags)))]
    inside = [x * x for x in angles if abs(x) <= c]
    m2 = statistics.fmean(inside)
    nd = statistics.NormalDist()

    def trunc_var(s: float) -> float:  # variance of N(0, s^2) truncated to [-c, c]; increasing in s
        z = c / s
        return s * s * (1 - 2 * z * nd.pdf(z) / (2 * nd.cdf(z) - 1))

    if not 0 < m2 < c * c / 3:  # a truncated normal's variance stays below the uniform's c^2 / 3
        raise BenchmarkError("multiple-scattering-reference: the angles inside the central window are not "
                             "Gaussian-like (flat or empty): no core width")
    lo, hi = math.sqrt(m2), math.sqrt(m2)
    while trunc_var(hi) < m2:
        hi *= 2
    for _ in range(100):  # bisection: the ML equation is trunc_var(s) = mean of x^2 inside the window
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if trunc_var(mid) < m2 else (lo, mid)
    return 0.5 * (lo + hi)


def bench_ms_reference(b: dict, study: dict, cfg_dir: Path, crossings: str | None = None) -> dict:
    """multiple-scattering-reference (reference, B2.8 condition 4): the core width of the projected exit angle after an
    isolated slab (Gaussian maximum-likelihood fit to the central 98 %, Lynch and Dahl's definition; both projections),
    per block of events and as batch means, against Lynch and Dahl's F = 98 % formula with the slab material's
    independent Z, A and density from the study spec; tolerance = the formula's published accuracy (declared with its
    source) + k SE; scope particle, material, thickness in X0, rigidity."""
    spec = json.loads((cfg_dir / b["element_spec"]).read_text(encoding="utf-8"))
    index = {e["name"]: i for i, e in enumerate(spec["elements"])}
    rows = read_dump(cfg_dir / (crossings or b["crossings"]))
    ang = _exit_angles(rows, index[b["measuring_plane"]])
    if len(ang) < 100:
        raise BenchmarkError("multiple-scattering-reference: fewer than 100 primaries reached the measuring plane")
    k_blocks = int(b.get("blocks", 16))
    evs = sorted(ang)
    per = max(1, len(evs) // k_blocks)
    widths = [_core98([x for e in evs[i * per:(i + 1) * per] for x in ang[e]]) for i in range(k_blocks)]
    bm = batch_mean(widths)
    m = material(study, b["material"], ("z", "a_g_mole", "density_g_cm3", "radiation_length_mm", "reference_source"))
    mass, z = particle_props(b["particle"])
    p = float(b["momentum_MeV"])
    beta = p / math.hypot(p, mass)
    x = float(b["thickness_mm"]) / 10 * m["density_g_cm3"]
    ref = lynch_dahl_theta0(m["z"], m["a_g_mole"], x, p, beta, abs(z))
    rel = bm["value"] / ref - 1
    tol, parts, _ = _tol(b, bm["se"] / ref)
    return {"statistic": "core width of the projected exit angle (rad), central 98 %", "geant4": bm["value"],
            "geant4_dof": bm["dof"], "relative_se": bm["se"] / ref, "reference_value": ref, "relative_difference": rel,
            "tolerance": {"total": tol, "parts": parts}, "verdict": "pass" if abs(rel) <= tol else "fail",
            "selection": {"events": len(ang), "blocks": k_blocks},
            "scope": {"particle": [b["particle"]], "material": [b["material"]],
                      "thickness_x0": float(b["thickness_mm"]) / m["radiation_length_mm"],
                      "rigidity_GV": p / 1000 / abs(z)},
            "reference": {"source": "Lynch and Dahl, Nucl. Instrum. Meth. B 58 (1991) 6, F = 98 % Gaussian fit to "
                                    "Moliere; accuracy " + str(b["tolerance"].get("reference_source", "declared")),
                          "version": "1991", "validity": b["tolerance"].get("validity", "as declared")}}


def bench_ms_tail_reference(b: dict, cfg_dir: Path) -> dict:
    """ms-tail-reference (reference, D0-b): the fraction of projected exit angles beyond about 3 theta0 against
    published data; refused until a published reference (with source) is configured: charge-confusion studies are
    not upgraded without it."""
    if not isinstance(b.get("published"), dict):
        return {"statistic": "fraction of projected angles beyond 3 theta0", "verdict": "not-applicable",
                "reason": "no published tail reference configured (D0-b): charge confusion cannot qualify",
                "reference": {"source": "none", "version": "-", "validity": "-"}}
    raise BenchmarkError("ms-tail-reference: a published tail reference is not implemented in this version")


def bench_regression(b: dict, cfg_dir: Path) -> dict:
    """regression-comparison (regression, B2.7): one scalar observable of two versions (two independent logical runs,
    point ids the version labels) decided by core.stats.decisions.change; it never affects the label."""
    doc_a, oa = _summary_obs(cfg_dir, b["summary_a"], b["observable"])
    doc_b, ob = _summary_obs(cfg_dir, b["summary_b"], b["observable"])
    ea, eb = E.estimate(doc_a, oa), E.estimate(doc_b, ob)
    mode = b.get("tolerance_mode", "relative")
    diff, se = difference(ea["value"], ea["se"], eb["value"], eb["se"], mode)
    dof = welch_dof(ea["se"], ea["dof"], eb["se"], eb["dof"])
    d = change(diff, se, dof, float(b["tolerance"]), int(b.get("m", 1)))
    return {"statistic": f"{b['observable']} between {b.get('version_a', 'a')} and {b.get('version_b', 'b')}",
            "geant4": ea["value"], "reference_value": eb["value"], "difference": diff, "se_of_difference": se,
            "dof": dof, "tolerance": {"value": float(b["tolerance"]), "mode": mode}, "verdict": d["verdict"],
            "decision": d, "reference": {"source": "the other version's run", "version": str(b.get("version_b")),
                                         "validity": "regression only; never validation"}}


def evaluate_detector(b: dict, study: dict, cfg_dir: Path) -> dict:
    name = b["benchmark"]
    if name == "field-propagation":
        return bench_field_propagation(b, cfg_dir)
    if name == "material-definition":
        return bench_material_definition(b, study, cfg_dir)
    if name == "reco-closure":
        return bench_reco_closure(b, cfg_dir)
    if name == "field-propagation-muon":
        return bench_field_propagation_muon(b, cfg_dir)
    if name == "tof-beta":
        return bench_tof_beta(b, cfg_dir)
    if name == "tof-layer-consistency":
        return bench_tof_layer_consistency(b, cfg_dir)
    if name == "sampling-fraction":
        return bench_sampling_fraction(b, cfg_dir)
    if name == "multiple-scattering-reference":
        return bench_ms_reference(b, study, cfg_dir)
    if name == "ms-tail-reference":
        return bench_ms_tail_reference(b, cfg_dir)
    return bench_regression(b, cfg_dir)


def _areal_density_change(b: dict, nc: dict, cfg_dir: Path) -> float | None:
    """The relative change of the slab's areal density (density x thickness, from each run's effective-config tree)
    between a negative control's run record and the nominal's: a control is counted only when its run carries the
    stated injection (slab density or thickness x (1 + delta)); None when either run record or tree is missing."""
    def areal(rr):
        try:
            rec = json.loads((cfg_dir / rr).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
        tree = ((((rec.get("extension") or {}).get("simulation") or {}).get("effective_config") or {}).get(
            "geometry") or {}).get("tree") or {}
        dens = {m["name"]: float.fromhex(m["density_g_cm3"]) for m in tree.get("materials", [])}
        slab = next((lv for lv in tree.get("logical_volumes", []) if lv.get("name") == b.get("slab", "Slab")), None)
        if slab is None or slab.get("material") not in dens:
            return None
        return dens[slab["material"]] * 2 * float.fromhex(slab["solid"]["parameters"]["half_x_mm"])
    a, c = areal(b.get("run_record")), areal(nc.get("run_record"))
    return None if a in (None, 0.0) or c is None else c / a - 1


CONTROL_RULES = ("shift-window/1", "declared-size/1")
# the benchmarks whose response to an areal-density injection is modelled (expected_shift)
DECLARED_BENCHMARKS = ("multiple-scattering-reference", "stopping-power", "thin-layer-mpv")
# declared-size/1 (maintainer decision 2026-10-25, provisional values): plan-controls sizes each control for an expected
# shift of DECLARED_TARGET_FACTOR x the planned detection limit; a control counts only when its expected shift is at
# most DECLARED_CEILING_FACTOR x that limit (and it is caught).
DECLARED_TARGET_FACTOR, DECLARED_CEILING_FACTOR = 1.25, 1.5


def control_rule(b: dict) -> str:
    """The benchmark's control rule: shift-window/1 (default: caught and |shift| <= 1.1 DL after the runs) or
    declared-size/1 (DECLARED_BENCHMARKS: the size fixed by the injection before the runs)."""
    rule = b.get("control_rule", "shift-window/1")
    if rule not in CONTROL_RULES:
        raise BenchmarkError(f"{b.get('benchmark')}: control_rule {rule!r} is not one of {list(CONTROL_RULES)}")
    if rule == "declared-size/1" and b.get("benchmark") not in DECLARED_BENCHMARKS:
        raise BenchmarkError(f"{b.get('benchmark')}: control_rule declared-size/1 is implemented for "
                             f"{', '.join(DECLARED_BENCHMARKS)} (the benchmarks whose response to an areal-density "
                             "injection is modelled)")
    return rule


def planned_detection_limit(res: dict) -> float:
    """The detection limit planned from the nominal run alone: DL = tol + |rel| + t_0.977 sqrt(2) se, nu = 2 dof (a
    control with the nominal's SE), known before any control runs."""
    if not res.get("relative_se") or not res.get("geant4_dof"):
        raise BenchmarkError(f"{res.get('benchmark', 'benchmark')}: the nominal needs a batch-means SE and dof")
    return detection_limit(res["tolerance"]["total"], res["relative_difference"], math.sqrt(2) * res["relative_se"],
                           2 * res["geant4_dof"])["value"]


def ms_expected_shift(b: dict, study: dict, injected_relative: float) -> float:
    """The relative change of Lynch and Dahl's theta0 when the slab's areal density changes by injected_relative (a
    density or thickness control): the control's expected shift of the observable, from the injection alone."""
    m = material(study, b["material"], ("z", "a_g_mole", "density_g_cm3", "radiation_length_mm", "reference_source"))
    mass, z = particle_props(b["particle"])
    p = float(b["momentum_MeV"])
    beta = p / math.hypot(p, mass)
    x = float(b["thickness_mm"]) / 10 * m["density_g_cm3"]
    if not -1.0 < float(injected_relative):
        raise BenchmarkError("injected_relative must be above -1")
    return (lynch_dahl_theta0(m["z"], m["a_g_mole"], x * (1 + float(injected_relative)), p, beta, abs(z))
            / lynch_dahl_theta0(m["z"], m["a_g_mole"], x, p, beta, abs(z)) - 1)


def slab_expected_shift(b: dict, study: dict, injected_relative: float) -> float:
    """The expected shift of a slab benchmark's observable when the slab's areal density changes by injected_relative
    on the Geant4 side (the reference keeping the spec): stopping-power, mean loss / spec thickness = (1 + d) x Bethe
    at the shifted mid-slab energy over Bethe at the nominal one; thin-layer-mpv, Delta_p of the scaled areal density
    over the nominal (xi ~ x, plus its log term). The density effect stays at the spec density's Sternheimer
    parameters (a second-order change for thin slabs)."""
    d = float(injected_relative)
    if not -1.0 < d:
        raise BenchmarkError("injected_relative must be above -1")
    mat = material(study, b["material"])
    mass, z = particle_props(b["particle"])
    e, t = float(b["energy_MeV"]), float(b["thickness_mm"])
    if b["benchmark"] == "stopping-power":
        loss = bethe(e, mass, z, mat) * mat["density_g_cm3"] * t / 10
        return (1 + d) * bethe(e - (1 + d) * loss / 2, mass, z, mat) / bethe(e - loss / 2, mass, z, mat) - 1
    if b["benchmark"] == "thin-layer-mpv":
        return landau_mpv(e, mass, z, mat, t * (1 + d))["delta_p_MeV"] / landau_mpv(e, mass, z, mat, t)["delta_p_MeV"] - 1
    raise BenchmarkError(f"{b['benchmark']}: no modelled response to an areal-density injection")


def expected_shift(b: dict, study: dict, injected_relative: float) -> float:
    """declared-size/1: a control's expected shift of the observable from its areal-density injection alone."""
    if b.get("benchmark") == "multiple-scattering-reference":
        return ms_expected_shift(b, study, injected_relative)
    return slab_expected_shift(b, study, injected_relative)


def declared_size(ctl: list[dict], planned_dl: float) -> dict:
    """declared-size/1: each control (with expected_shift_relative from its injection) is sized when |expected| <=
    DECLARED_CEILING_FACTOR x planned_dl, at the claimed limit when caught and sized; a caught control demonstrates a
    detection limit max(DL, |shift|), and the benchmark claims the largest demonstrated one (never less than a control
    showed). Annotates ctl in place and returns the negative_control fields the rule sets."""
    for c in ctl:
        exp = c.get("expected_shift_relative")
        c["sized"] = exp is not None and abs(exp) <= DECLARED_CEILING_FACTOR * planned_dl
        caught = c["status"] == "caught"
        c["at_claimed_detection_limit"] = bool(caught and c["sized"])
        c["demonstrated_detection_limit_relative"] = (max(c["detection_limit_relative"], abs(c["shift"]))
                                                      if caught else None)
    shown = [c["demonstrated_detection_limit_relative"] for c in ctl if c["demonstrated_detection_limit_relative"]]
    return {"control_rule": "declared-size/1", "planned_detection_limit_relative": planned_dl,
            "target_factor": DECLARED_TARGET_FACTOR, "ceiling_factor": DECLARED_CEILING_FACTOR,
            "detection_limit_relative": max(shown) if shown else max(c["detection_limit_relative"] for c in ctl)}


def run_detector_benchmark(b: dict, study: dict, cfg_dir: Path) -> dict:
    """A CV-B2 benchmark: its result, with the scope keys it covers; a reference (multiple-scattering-reference) also
    reruns on its negative controls (slab density or thickness x (1 +- delta) on the Geant4 side, the reference
    unchanged): caught when the control's verdict is fail, detection limit as for the slab benchmarks (A1.10); with
    control_rule declared-size/1 each control's expected shift comes from its injection (ms_expected_shift) and the
    rule of declared_size decides."""
    name, grade = b["benchmark"], GRADES[b["benchmark"]]
    rule = control_rule(b)
    res = evaluate_detector(b, study, cfg_dir)
    out = {"benchmark": name, "grade": grade, **res}
    out.setdefault("scope", {})
    if name == "multiple-scattering-reference" and res["verdict"] in ("pass", "fail"):
        entries = b.get("negative_controls") or []
        ctl, dls = [], []
        for nc in entries:
            nres = bench_ms_reference({**b, "thickness_mm": b["thickness_mm"]}, study, cfg_dir, nc["crossings"])
            injected = _areal_density_change(b, nc, cfg_dir)
            caught = nres["verdict"] == "fail" and injected is not None and isinstance(nc.get("injected_relative"), (
                int, float)) and abs(injected - nc["injected_relative"]) <= 1e-6 * max(1.0, abs(injected))
            shift = (nres["geant4"] - res["geant4"]) / res["reference_value"]
            se_shift = math.hypot(res["relative_se"], nres["relative_se"])
            dl = detection_limit(res["tolerance"]["total"], res["relative_difference"], se_shift,
                                 welch_dof(res["relative_se"], res["geant4_dof"], nres["relative_se"],
                                           nres["geant4_dof"]))["value"]
            dls.append(dl)
            ctl.append({"status": "caught" if caught else "not-caught", "injected": nc.get("injected"),
                        "injection_in_run": injected,
                        "injected_relative": nc.get("injected_relative"), "shift": shift, "se_of_shift": se_shift,
                        "sign": "+" if shift > 0 else "-", "detection_limit_relative": dl,
                        "at_claimed_detection_limit": bool(caught and abs(shift) <= 1.1 * dl),
                        "crossings": nc["crossings"], "run_record": nc.get("run_record")})
            if rule == "declared-size/1":
                ctl[-1]["expected_shift_relative"] = (expected_shift(b, study, nc["injected_relative"])
                                                      if isinstance(nc.get("injected_relative"), (int, float))
                                                      else None)
        signs = {c["sign"] for c in ctl if c["status"] == "caught"}
        out["negative_control"] = ({"status": "missing"} if not ctl else {
            "status": "caught" if all(c["status"] == "caught" for c in ctl) else "not-caught", "controls": ctl,
            "at_claimed_detection_limit": all(c["at_claimed_detection_limit"] for c in ctl),
            "detection_limit_relative": max(dls),
            "detection_limit_sign": "+-" if signs == {"+", "-"} else "".join(sorted(signs)) or None})
        if ctl and rule == "declared-size/1":
            nc_out = out["negative_control"]
            nc_out.update(declared_size(ctl, planned_detection_limit(res)))
            nc_out["at_claimed_detection_limit"] = all(c["at_claimed_detection_limit"] for c in ctl)
        conf = configuration(b, cfg_dir)
        out.update({k: v for k, v in conf.items() if k != "configuration_gap"})
        out["configuration_gap"] = conf.get("configuration_gap") or (
            None if conf.get("configuration") == "isolated" else "the slab is not isolated (vacuum world, no field, "
                                                                   "every placement in the target)")
        out["validation_evidence"] = (res["verdict"] == "pass" and out["negative_control"].get("status") == "caught"
                                      and not out["configuration_gap"])
    else:
        out["validation_evidence"] = False
    return out


def evaluate(b: dict, src, study: dict, cfg_dir: Path) -> dict:
    name = b["benchmark"]
    if name == "stopping-power":
        return bench_stopping_power(b, src, study)
    if name == "range":
        return bench_range(b, src, study, cfg_dir)
    if name == "thin-layer-mpv":
        return bench_mpv(b, src, study)
    if name == "thin-layer-width":
        return bench_width(b, src, study)
    if name == "multiple-scattering":
        return bench_ms(b, src, study, cfg_dir)
    if name == "em-shower-shape":
        return bench_shower(b, src, study)
    if name == "shower-containment":
        return bench_containment(b, src)
    if name == "longitudinal-profile":
        return bench_profile(b, src)
    return bench_published(b, src, _columns(b, cfg_dir))


def _columns(e: dict, cfg_dir) -> Columns:
    """The column map of a benchmark entry (its column_map, config-relative) or the legacy layered_sim map."""
    return Columns(Path(cfg_dir) / e["column_map"]) if e.get("column_map") and cfg_dir is not None else Columns()


def source(b: dict, cfg_dir: Path, entry: dict | None = None):
    """The data a benchmark reads: the run summary for the summary-based benchmarks, else the per-event CSV with its
    columns renamed to their semantic names (A2.6)."""
    e = entry or b
    cols = _columns(e if e.get("column_map") else b, cfg_dir)
    if b["benchmark"] in SUMMARY_BENCHMARKS:
        if not e.get("summary"):
            raise BenchmarkError(f"{b['benchmark']}: 'summary' (a simulation-summary/1 of the run) is required")
        return Summary(cfg_dir / e["summary"], cols)
    return cols.rows(read_csv(cfg_dir / e["csv"]))


def controls(b: dict, res: dict, study: dict, cfg_dir: Path) -> dict:
    """D3 (A1.10): each negative control is judged on the observable: shift = (control - nominal)/reference, its SE
    combined from the two runs, caught when the control's benchmark verdict is fail; at the claimed detection limit
    DL = tol + |rel| + t_0.977(nu) se_shift when caught and |shift| <= 1.1 DL. Both directions validate the claim;
    one direction narrows it to that sign (detection_limit_sign)."""
    entries = b.get("negative_controls") or ([b["negative_control"]] if b.get("negative_control") else [])
    rule = control_rule(b)
    se_n, dof_n = res.get("relative_se"), res.get("geant4_dof")
    tol, rel = res["tolerance"]["total"], res["relative_difference"]
    out, dls = [], []
    for nc in entries:
        nres = evaluate(b, source(b, cfg_dir, nc), study, cfg_dir)
        caught = nres["verdict"] == "fail"
        shift = (nres["geant4"] - res["geant4"]) / res["reference_value"] if nres.get("geant4") is not None else None
        se_c, dof_c = nres.get("relative_se"), nres.get("geant4_dof")
        if None in (se_n, se_c, dof_n, dof_c):
            raise BenchmarkError(f"{b['benchmark']}: the control and the nominal need batch-means SEs")
        se_shift = math.hypot(se_n, se_c)
        dl = detection_limit(tol, rel, se_shift, welch_dof(se_n, dof_n, se_c, dof_c))["value"]
        dls.append(dl)
        out.append({"status": "caught" if caught else "not-caught", "injected": nc.get("injected"),
                    "injected_relative": nc.get("injected_relative"), "shift": shift, "se_of_shift": se_shift,
                    "sign": "+" if shift and shift > 0 else "-", "detection_limit_relative": dl,
                    "at_claimed_detection_limit": bool(caught and shift is not None and abs(shift) <= 1.1 * dl),
                    "relative_difference": nres.get("relative_difference"), "verdict_on_control": nres["verdict"],
                    "summary": nc.get("summary"), "csv": nc.get("csv"), "run_record": nc.get("run_record")})
        if rule == "declared-size/1":  # the injection must be in the control's run (effective config), as for the MS
            injected = _areal_density_change(b, nc, cfg_dir)
            ok = injected is not None and isinstance(nc.get("injected_relative"), (int, float)) and \
                abs(injected - nc["injected_relative"]) <= 1e-6 * max(1.0, abs(injected))
            out[-1].update(injection_in_run=injected,
                           expected_shift_relative=expected_shift(b, study, nc["injected_relative"]) if ok else None)
    if not out:
        planned = detection_limit(tol, rel, math.sqrt(2) * se_n, 2 * dof_n)["value"] if se_n and dof_n else None
        return {"status": "missing", "planned_detection_limit_relative": planned,
                "planned_basis": "a control with the nominal's SE (se_shift = sqrt(2) se, nu = 2 (K - 1))"}
    signs = {c["sign"] for c in out if c["status"] == "caught"}
    doc = {"status": "caught" if all(c["status"] == "caught" for c in out) else "not-caught", "controls": out,
           "at_claimed_detection_limit": all(c["at_claimed_detection_limit"] for c in out),
           "detection_limit_relative": max(dls), "detection_limit_sign": "+-" if signs == {"+", "-"} else
           "".join(sorted(signs)) or None}
    if rule == "declared-size/1":
        doc.update(declared_size(out, planned_detection_limit(res)))
        doc["at_claimed_detection_limit"] = all(c["at_claimed_detection_limit"] for c in out)
    return doc


def run_benchmark(b: dict, study: dict, cfg_dir: Path) -> dict:
    name = b.get("benchmark")
    if name not in GRADES:
        raise BenchmarkError(f"unknown benchmark {name!r} (known: {sorted(GRADES)})")
    control_rule(b)
    if name in DETECTOR_BENCHMARKS:
        return run_detector_benchmark(b, study, cfg_dir)
    data = ("summary", "observable") if name in SUMMARY_BENCHMARKS and name != "longitudinal-profile" else \
        (("summary",) if name == "longitudinal-profile" else ("csv",))
    for k in data + ("particle", "energy_MeV") + (("material", "slab", "thickness_mm") if name in (
            "stopping-power", "thin-layer-mpv", "thin-layer-width", "range") else ()):
        if k not in b:
            raise BenchmarkError(f"{name}: '{k}' is required")
    check_inputs(b["energy_MeV"], b.get("thickness_mm"))
    res = evaluate(b, source(b, cfg_dir), study, cfg_dir)
    grade = GRADES[name]
    out = {"benchmark": name, "grade": grade, **res,
           "scope": {"particle": b["particle"], "energy_MeV": b["energy_MeV"], "material": b.get("material"),
                     "thickness_mm": b.get("thickness_mm"), "observable": res.get("statistic")},
           "inputs": {"summary": b.get("summary"), "observable": b.get("observable"), "csv": b.get("csv"),
                      "run_record": b.get("run_record")}}
    conf = configuration(b, cfg_dir)
    out.update({k: v for k, v in conf.items() if k != "configuration_gap"})
    if grade in UPGRADING and res["verdict"] in ("pass", "fail"):
        nc = controls(b, res, study, cfg_dir)
        out["negative_control"] = nc
        out["detection_limit_relative"] = nc.get("detection_limit_relative", nc.get("planned_detection_limit_relative"))
        out["scope"]["detection_limit_relative"] = out["detection_limit_relative"]
        if nc.get("detection_limit_sign"):
            out["scope"]["detection_limit_sign"] = nc["detection_limit_sign"]
        if conf.get("target_geometry_sha256") and name == "longitudinal-profile":
            out["scope"].update(target_geometry_sha256=conf["target_geometry_sha256"], hash_scheme=conf["hash_scheme"])
    nc_ok = out.get("negative_control", {}).get("status") == "caught"
    m = conf.get("measured_configuration") or {}
    matched = grade != "setup-matched" or (m.get("target_geometry_sha256") == conf.get("target_geometry_sha256")
                                           and m.get("hash_scheme") == conf.get("hash_scheme"))
    if grade in UPGRADING:
        out["configuration_gap"] = (conf.get("configuration_gap") or
                                    (None if conf["configuration"] == "isolated" else
                                     f"the target {conf['target_slabs']} is embedded (world {conf['world_material']}, "
                                     "other placements or a field): only an isolated target validates") or
                                    (None if matched else "setup-matched: the target hash differs from the measured "
                                                          "configuration (measured_configuration)"))
    out["validation_evidence"] = (grade in UPGRADING and res["verdict"] == "pass" and nc_ok
                                  and not out.get("configuration_gap"))
    return out


def cmd_run(args) -> tuple[str, dict]:
    cfg_path = Path(args.config)
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "geant4-benchmarks/1":
        raise BenchmarkError("config schema must be geant4-benchmarks/1")
    cfg_dir = cfg_path.resolve().parent
    study = json.loads((cfg_dir / cfg["study_spec"]).read_text(encoding="utf-8"))
    results, gaps = [], []
    for b in cfg.get("benchmarks", []):
        r = run_benchmark(b, study, cfg_dir)
        results.append(r)
        nc = r.get("negative_control", {})
        if r["grade"] in UPGRADING:
            if r["verdict"] == "not-applicable":
                gaps.append(f"{r['benchmark']}: not applicable ({r.get('reason', 'outside validity')})")
            elif nc.get("status") == "missing":
                gaps.append(f"{r['benchmark']}: no negative control, so not validation evidence")
            elif nc.get("status") == "not-caught":
                gaps.append(f"{r['benchmark']}: negative control ({nc.get('injected')}) not caught: no discriminating "
                            "power at the claimed detection limit")
            elif r.get("configuration_gap"):
                gaps.append(f"{r['benchmark']}: {r['configuration_gap']}")
            elif not nc.get("at_claimed_detection_limit") and nc.get("control_rule") == "declared-size/1":
                big = ", ".join("undeclared" if c.get("expected_shift_relative") is None
                                else f"{c['expected_shift_relative']:+.4g}"
                                for c in nc.get("controls", []) if not c.get("sized"))
                gaps.append(f"{r['benchmark']}: a negative control's declared size (expected shift {big}) exceeds "
                            f"{DECLARED_CEILING_FACTOR} x the planned detection limit "
                            f"{nc['planned_detection_limit_relative']:.4g} (declared-size/1)")
            elif not nc.get("at_claimed_detection_limit"):
                gaps.append(f"{r['benchmark']}: a negative control's shift of the observable is not at the claimed "
                            f"detection limit {r.get('detection_limit_relative', nc.get('detection_limit_relative')):.4g} (|shift| <= 1.1 DL)")
            elif nc.get("detection_limit_sign") in ("+", "-"):
                gaps.append(f"{r['benchmark']}: negative controls in one direction only: the detection limit is "
                            f"claimed for sign {nc['detection_limit_sign']} only")
        elif r["verdict"] in ("implausible", "not-applicable"):
            gaps.append(f"{r['benchmark']} ({r['grade']}): {r['verdict']}" + (f" ({r['reason']})" if r.get("reason")
                                                                             else ""))
    if not results:
        raise BenchmarkError("the config lists no benchmarks")
    if not any(r["grade"] in UPGRADING for r in results):
        gaps.append("no reference or setup-matched benchmark in the config: nothing here is validation evidence")
    ref = [r for r in results if r["grade"] in UPGRADING]
    failed = [r["benchmark"] for r in ref if r["verdict"] == "fail" or r.get("negative_control", {}).get("status")
              == "not-caught"]
    status = "failed" if failed else ("incomplete" if any(r["verdict"] == "not-applicable" for r in ref) else "ok")
    doc = {"benchmarks": results, "gaps": gaps, "failed": failed,
           "constants": {"K_MeV_mol_cm2": K_BETHE, "m_e_MeV": ME, "source": "core/constants (CODATA 2022)"},
           "note": "reference inputs come from the study spec; the Geant4 material dump is never read"}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps({"status": status, "status_label": args.status, **doc}, indent=1,
                                             sort_keys=True) + "\n", encoding="utf-8")
    return status, doc


def plan_injection(b: dict, study: dict, target: float) -> float:
    """The areal-density change whose expected shift (expected_shift) is target, by bisection (monotonic)."""
    lo, hi = (0.0, 4.0) if target > 0 else (-0.95, 0.0)
    f = lambda d: expected_shift(b, study, d) - target  # noqa: E731
    if f(lo) * f(hi) > 0:
        raise BenchmarkError(f"no areal-density change in [{lo}, {hi}] gives an expected shift of {target:.4g}")
    for _ in range(200):
        mid = (lo + hi) / 2
        if (f(lo) < 0) == (f(mid) < 0):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def cmd_plan_controls(args) -> tuple[str, dict]:
    """declared-size/1: from the nominal run of a config's benchmark (--benchmark, one of DECLARED_BENCHMARKS; before
    any control runs), the planned detection limit and the +- areal-density changes whose expected shift is
    DECLARED_TARGET_FACTOR x that limit, to write into negative_controls (injected_relative) with control_rule
    declared-size/1 before the control runs are made."""
    cfg_path = Path(args.config)
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg_dir = cfg_path.resolve().parent
    study = json.loads((cfg_dir / cfg["study_spec"]).read_text(encoding="utf-8"))
    if args.benchmark not in DECLARED_BENCHMARKS:
        raise BenchmarkError(f"--benchmark {args.benchmark}: declared-size/1 covers {', '.join(DECLARED_BENCHMARKS)}")
    refs = [b for b in cfg.get("benchmarks", []) if b.get("benchmark") == args.benchmark]
    if not refs or not 0 <= args.index < len(refs):
        raise BenchmarkError(f"the config has {len(refs)} {args.benchmark} benchmark(s); --index {args.index} names "
                             "none")
    b = refs[args.index]
    res = bench_ms_reference(b, study, cfg_dir) if args.benchmark == "multiple-scattering-reference" else \
        evaluate(b, source(b, cfg_dir), study, cfg_dir)
    dlp = planned_detection_limit(res)
    target = DECLARED_TARGET_FACTOR * dlp
    plans = []
    for sign in (+1, -1):
        d = plan_injection(b, study, sign * target)
        plans.append({"sign": "+" if sign > 0 else "-", "injected_relative": round(d, 6),
                      "expected_shift_relative": expected_shift(b, study, round(d, 6))})
    return "ok", {"benchmark": args.benchmark, "nominal": {
        "relative_difference": res["relative_difference"], "relative_se": res["relative_se"],
        "tolerance": res["tolerance"]["total"], "verdict": res["verdict"]},
        "control_rule": "declared-size/1", "planned_detection_limit_relative": dlp,
        "target_factor": DECLARED_TARGET_FACTOR, "ceiling_factor": DECLARED_CEILING_FACTOR, "controls": plans,
        "note": "write control_rule declared-size/1 and these injected_relative values into the benchmark config before "
                "the control runs; each control run must realize its injected_relative (areal density, to 1e-6, from "
                "Geant4's own density); the control then counts when caught (its expected shift is within the ceiling "
                "by construction), and the benchmark claims the detection limit a caught control demonstrated"}


def cmd_reference(args) -> tuple[str, dict]:
    study = json.loads(Path(args.study_spec).read_text(encoding="utf-8"))
    mat = material(study, args.material)
    mass, z = particle_props(args.particle)
    check_inputs(args.energy_mev, args.thickness_mm)
    out = {"bethe_MeV_cm2_g": bethe(args.energy_mev, mass, z, mat), "w_max_MeV": w_max(args.energy_mev, mass),
           "beta_gamma": kinematics(args.energy_mev, mass)[2],
           "density_effect": density_effect(kinematics(args.energy_mev, mass)[2], mat["sternheimer"])}
    if args.thickness_mm:
        out["landau"] = landau_mpv(args.energy_mev, mass, z, mat, args.thickness_mm)
    return "ok", out


def cmd_scope_keys(args) -> tuple[str, dict]:
    """The declared-scope keys of a detector-level study (CV-B2, B2.8): what its validation_plan.scope names so that
    each qualification condition is matched by its own key."""
    out = {}
    if args.element_spec:
        out["field_configuration_sha256"] = field_configuration_sha256(
            json.loads(Path(args.element_spec).read_text(encoding="utf-8")))
    if args.reco_spec:
        out["reco_spec_sha256"] = reco_spec_sha256(json.loads(Path(args.reco_spec).read_text(encoding="utf-8")))
    if args.geometry:
        out["geometry_sha256"] = file_sha256(Path(args.geometry))
    if args.realization:
        out["realization_sha256"] = file_sha256(Path(args.realization))
    if not out:
        raise BenchmarkError("scope-keys needs at least one of --element-spec, --reco-spec, --geometry, --realization")
    return "ok", {"scope_keys": out}


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run", help="run the benchmarks of a config")
    p.add_argument("--config", required=True)
    p.add_argument("--out")
    p = sub.add_parser("reference", help="print the reference values for one material, particle and energy")
    p.add_argument("--study-spec", required=True)
    p.add_argument("--material", required=True)
    p.add_argument("--particle", required=True)
    p.add_argument("--energy-mev", type=float, required=True)
    p.add_argument("--thickness-mm", type=float)
    p = sub.add_parser("plan-controls", help="declared-size/1: size the reference's negative controls from the "
                                             "nominal run's planned detection limit, before the control runs")
    p.add_argument("--config", required=True)
    p.add_argument("--benchmark", default="multiple-scattering-reference", choices=DECLARED_BENCHMARKS)
    p.add_argument("--index", type=int, default=0, help="which benchmark of that name in the config (0)")
    p = sub.add_parser("scope-keys", help="the declared-scope keys of a detector-level study (CV-B2)")
    for name in ("--element-spec", "--reco-spec", "--geometry", "--realization"):
        p.add_argument(name)
    for sp in sub.choices.values():
        add_status_argument(sp)
    args = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    try:
        status, doc = {"run": cmd_run, "reference": cmd_reference, "scope-keys": cmd_scope_keys,
                       "plan-controls": cmd_plan_controls}[args.command](args)
    except (BenchmarkError, OSError, KeyError, ValueError, TypeError, ArithmeticError) as exc:
        status, doc = "rejected", {"error": f"{type(exc).__name__}: {exc}" if isinstance(exc, KeyError) else str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs,
                      "defaults_used": ["status"] if "--status" not in (argv or sys.argv[1:]) else [], **doc},
                     indent=1, default=str))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
