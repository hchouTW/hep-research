"""adapters/calo-cluster, D2 stage 4 of T08: the sheet's scenarios A15, A32 and A38 (plan section 13), on hand-made events only.
No fixture event and no Monte Carlo: every grid is a closed-form shower image written here, so the expectation of each test is
fixed before the recipe runs. Nothing here judges quality: whether a variant is worse is K09's question at Freeze B.

What each scenario means for this development binding on t08-grid/1 (docs/dev/detector-reconstruction/t08-scenarios.md):
- A15 (a faster but worse variant is rejected under fixed gates or listed as its own working point): a cheaper configuration
  (fewer sharing iterations, a larger cell threshold) is a whole configuration file with its own identity, recorded in every
  product it makes; the consumers that hold t08-grid/1's references (the readings, the CAI checks) refuse its products, so a
  product of one working point never passes as the other's.
- A32 (cuts, cleaning, model or multiplicity changed: downstream responses are not reused unchecked): a changed threshold
  changes the product's configuration identity, and a consumer holding a response or reference made with another configuration
  refuses the product; the frozen selection applied to the changed product finds the difference.
- A38 (trigger, ROI or quality selection: shape, counts/exposure, hit and unhit, efficiency consistent; an unselected model or a
  repeated correction cannot pass): the product's kept cells are exactly section 7.1's selection of its input under the
  configuration it names (the components are formed here from the input, so a seedless component under a seeded label, two
  labels on one component or one label over two are caught); every input event is in the product, selected or not, and kept plus
  unclustered plus dead cells account for the grid (counts, hit and unhit); exposure is open (t08-grid/1 has no live time
  or trigger, so no test here can show it); every event keeps its event sum and objects, so a shape is formed over one selection (no response histogram is
  built in T08); the reference clusterer's constants are the configuration's, the readings score only products of that
  configuration, and a correction applied to values it was not made for (an already-calibrated readout, a gain applied twice) is
  refused.

Run from the plugin root: python -m unittest tests.adapters.test_calo_scenarios -v
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib
import io
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "calo-cluster" / "assets"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ASSETS / "fixture_tools"))
sys.path.insert(0, str(ASSETS))

from calo_recipe import cell_input, configuration, gain_payload, product  # noqa: E402
import t08_cai  # noqa: E402
import t08_fixture_files  # noqa: E402
import t08_readings  # noqa: E402

N = 40
W = 1.0
T_C, T_S = 0.6, 10.0                   # t04-values-v4.md section 4.2, written here from the text
FROZEN_FILE = ASSETS / "t08-grid-1.configuration.json"
REF = {"iso": 2.907, "dead": 2.855, "sat": 3.485, "edge": {0.5: 1.5, 1.0: 1.6, 1.5: 1.7, 2.0: 1.9},
       "far": {(e, d): 2.0 for e in (1000.0, 4000.0) for d in (3.0, 8.0)}, "near": {(e, d): 3.5 for e in (1000.0, 4000.0) for d in (1.5, 3.0)}}
LONE = [(2000.0, 12.3, 20.1)]
PAIR = [(2000.0, 18.4, 20.2), (1500.0, 21.9, 20.6)]      # one component, two kept peaks: sharing applies


def scenarios():
    """The stage 4 tool, imported when a test needs it, so each test fails on its own before the tool exists."""
    return importlib.import_module("t08_scenarios")


def phi_cdf(u):
    return 0.5 * (1.0 + math.erf(u / math.sqrt(2.0)))


def g_axis(i, c):
    return phi_cdf((i + 1 - c) / W) - phi_cdf((i - c) / W)


def image(showers):
    return numpy.array([[sum(e * g_axis(ix, x) * g_axis(iy, y) for e, x, y in showers) for iy in range(N)] for ix in range(N)])


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def variant_bytes(**changes) -> bytes:
    """A whole configuration file: t08-grid/1's with the named constants changed and its source saying so."""
    doc = json.loads(FROZEN_FILE.read_text(encoding="utf-8"))
    doc.update(changes)
    doc["source"] = "hand-made variant for the stage 4 scenario tests: " + ", ".join(f"{k} {v}" for k, v in sorted(changes.items()))
    return (json.dumps(doc, indent=1) + "\n").encode("utf-8")


def stage1_payloads(raw_unit="adc", gain_unit=None, operation="multiply"):
    ped = cell_input.payload_bytes("pedestal", "subtract", 0.0, N * N, raw_unit, "nominal", "hand-made test constant")
    gain = cell_input.payload_bytes("gain", operation, 1.0, N * N, gain_unit or f"MeV/{raw_unit}", "nominal", "hand-made test constant",
                                    derived_against=[sha(ped)])
    return ped, gain


class HandMadeGenerator:
    """A stand-in with the frozen generator's interface, written here: closed-form images, no random draw. Not t08-grid/1."""
    N_CELLS, GENERATOR, CLIP_MEV = N, "hand-made", 400.0

    def __init__(self, showers_per_event, separation=None, dead=None):
        self.showers_per_event, self.separation, self.dead = showers_per_event, separation, dead or {}

    @staticmethod
    def cell_profile(x, y):
        return numpy.array([[g_axis(ix, x) * g_axis(iy, y) for iy in range(N)] for ix in range(N)])

    def event(self, fixture, block, stratum, index):
        showers = self.showers_per_event[index]
        deposit = numpy.stack([e * self.cell_profile(x, y) for e, x, y in showers])
        value = deposit.sum(axis=0)
        live = numpy.ones((N, N), bool)
        for cell in self.dead.get(index, ()):
            live[cell] = False
            value[cell] = numpy.nan
        n = len(showers)
        return {"data": {"raw": value, "pedestal": 0.0, "gain": 1.0, "live": live, "saturated": numpy.zeros((N, N), bool)},
                "truth": {"energy_mev": showers[0][0], "energy_bin": 2, "separation": self.separation or ("iso" if n == 1 else "far"),
                          "showers": numpy.array([[x, y] for _, x, y in showers]), "d": None if n == 1 else math.dist(showers[0][1:], showers[1][1:]),
                          "azimuth": None if n == 1 else 0.0, "t": None, "f_dead": None, "deposit": deposit}}


class Workspace:
    """Files of one hand-made stratum (harness files, as the job writes them) and the recipe's CLI on them."""

    def __init__(self, folder: Path, showers, stem="s", **kw):
        self.folder, self.stem = folder, stem
        self.files = t08_fixture_files.stratum_files(HandMadeGenerator(showers, **kw), "main", 1, 6, len(showers), folder, stem)
        self.cells, self.pedestal, self.gain = (Path(self.files[k]["path"]) for k in ("cells", "pedestal", "gain"))

    def config(self, name: str, content: bytes) -> Path:
        path = self.folder / f"{name}.configuration.json"
        path.write_bytes(content)
        return path

    def reconstruct(self, name: str, configuration_file=None, gain=None, cells=None, pedestal=None):
        out = self.folder / f"{name}.product.jsonl"
        args = [sys.executable, "-I", "-B", str(ASSETS / "calo_cluster.py"), "reconstruct", "--cells", str(cells or self.cells),
                "--pedestal-payload", str(pedestal or self.pedestal), "--gain-payload", str(gain or self.gain), "--product", str(out),
                "--product-id", name]
        if configuration_file is not None:
            args += ["--configuration", str(configuration_file)]
        p = subprocess.run(args, capture_output=True, text=True, timeout=120)
        return p, out

    def truth(self):
        return t08_fixture_files.read_truth(self.files["truth"]["path"])


def run_main(main, argv):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(io.StringIO()):
        code = main(argv)
    return code, stream.getvalue()


# --- A15: a cheaper variant is its own working point, never silently substituted ---------------------------------------------

class A15WorkingPoints(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.ws = Workspace(Path(self.folder.name), [LONE, PAIR], separation="iso")

    def test_no_flag_changes_a_constant_a_variant_is_a_whole_configuration_file(self):
        import calo_cluster
        flags = {a.option_strings[0] for a in calo_cluster.parser()._subparsers._group_actions[0].choices["reconstruct"]._actions
                 if a.option_strings and a.option_strings[0] != "-h"}
        self.assertEqual(flags, {"--cells", "--pedestal-payload", "--gain-payload", "--product", "--product-id", "--configuration"})

    def test_each_product_names_the_configuration_file_it_was_made_with(self):
        cheap = variant_bytes(sharing_iterations=10)
        p, frozen = self.ws.reconstruct("frozen")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        p, variant = self.ws.reconstruct("cheap", self.ws.config("cheap", cheap))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        hf, hv = product.read_product(frozen).header, product.read_product(variant).header
        self.assertEqual(hf["configuration"]["sha256"], sha(FROZEN_FILE.read_bytes()))
        self.assertEqual(hv["configuration"]["sha256"], sha(cheap))
        self.assertNotEqual(hf["configuration"]["sha256"], hv["configuration"]["sha256"])
        # the recipe name stays reco.calo.cell-cluster/1 for both: the working point is the configuration's identity (a reading)
        self.assertEqual(hf["recipe"], hv["recipe"])
        # the two-peak event differs (fractions after 10, not 30, iterations): the variant is another product, not a relabelling
        ef, ev = (Path(x).read_text().splitlines()[2] for x in (frozen, variant))
        self.assertNotEqual(ef, ev)

    def test_the_readings_score_only_the_frozen_working_point(self):
        header, truth = self.ws.truth()
        _, frozen = self.ws.reconstruct("frozen")
        lines, defects = t08_readings.readings(product.read_product(frozen), header, truth, REF, "frozen")
        self.assertEqual(defects, 0)
        for name, content in (("cheap", variant_bytes(sharing_iterations=10)), ("coarse", variant_bytes(cell_threshold_mev=1.2))):
            with self.subTest(variant=name):
                p, path = self.ws.reconstruct(name, self.ws.config(name, content))
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                with self.assertRaisesRegex(t08_readings.ReadingError, "configuration"):
                    t08_readings.readings(product.read_product(path), header, truth, REF, name)

    def test_the_cai_checks_refuse_a_product_of_another_working_point(self):
        files = t08_cai.write_payloads(self.ws.cells, self.ws.pedestal, self.ws.gain, self.ws.folder, "cai")["files"]
        nominal, derived = files["nominal-multiply"]["path"], files["derived-multiply"]["path"]
        _, variant = self.ws.reconstruct("cheap", self.ws.config("cheap", variant_bytes(sharing_iterations=10)), gain=nominal)
        code, out = run_main(t08_cai.main, ["fixed-membership", "--product", str(variant), "--old-gain", nominal, "--new-gain", derived,
                                            "--out", str(self.ws.folder / "cai1.jsonl"), "--label", "a15", "--min-asserted", "0"])
        self.assertEqual(code, 2, out)
        self.assertIn("configuration", out)
        self.assertFalse((self.ws.folder / "cai1.jsonl").exists())


# --- A32: a changed cut changes the identity, and a consumer holding another configuration's response refuses --------------

class A32ConfigurationChange(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.ws = Workspace(Path(self.folder.name), [LONE, PAIR], separation="iso")

    def test_the_frozen_selection_finds_a_changed_threshold_in_the_product(self):
        sc = scenarios()
        frozen_cfg = configuration.load()
        readout = cell_input.read_file(self.ws.cells, cell_input.read_cells, "cells")
        ped = cell_input.read_file(self.ws.pedestal, cell_input.read_payload, "p")
        gain = cell_input.read_file(self.ws.gain, gain_payload.read_gain, "g")
        for name, change in (("higher", 1.2), ("lower", 0.3)):
            with self.subTest(threshold=name):
                content = variant_bytes(cell_threshold_mev=change)
                _, path = self.ws.reconstruct(name, self.ws.config(name, content))
                read = product.read_product(path)
                own = configuration.from_bytes(content)
                found_frozen = 0
                for i, doc in enumerate(read.events):
                    energy = sc.cell_energies(readout.raw[i], readout.live[i], ped.values, gain.values, gain.operation)
                    found_frozen += bool(sc.selection_defects(doc, readout.raw[i], readout.live[i], energy, frozen_cfg))
                    self.assertEqual(sc.selection_defects(doc, readout.raw[i], readout.live[i], energy, own), [])
                self.assertEqual(found_frozen, 2)        # both events: each image has cells between 0.3 and 1.2 MeV at a kept edge

    def test_a_consumer_holding_another_configuration_refuses(self):
        sc = scenarios()
        content = variant_bytes(cell_threshold_mev=1.2)
        _, path = self.ws.reconstruct("coarse", self.ws.config("coarse", content))
        code, out = run_main(sc.main, ["accounting", "--cells", str(self.ws.cells), "--pedestal-payload", str(self.ws.pedestal),
                                       "--gain-payload", str(self.ws.gain), "--product", str(path), "--label", "a32"])
        self.assertEqual(code, 2, out)
        self.assertIn("configuration", out)
        code, out = run_main(sc.main, ["accounting", "--cells", str(self.ws.cells), "--pedestal-payload", str(self.ws.pedestal),
                                       "--gain-payload", str(self.ws.gain), "--product", str(path), "--label", "a32",
                                       "--configuration", str(self.ws.folder / "coarse.configuration.json")])
        self.assertEqual(code, 0, out)

    def test_cai_t08_2_refuses_two_products_of_different_configurations(self):
        files = t08_cai.write_payloads(self.ws.cells, self.ws.pedestal, self.ws.gain, self.ws.folder, "cai")["files"]
        nominal, derived = files["nominal-multiply"]["path"], files["derived-multiply"]["path"]
        _, a = self.ws.reconstruct("nominal", gain=nominal)
        _, b = self.ws.reconstruct("changed", self.ws.config("coarse", variant_bytes(cell_threshold_mev=1.2)), gain=derived)
        code, out = run_main(t08_cai.main, ["rereco", "--nominal", str(a), "--changed", str(b), "--old-gain", nominal, "--new-gain", derived,
                                            "--out", str(self.ws.folder / "cai2.jsonl"), "--label", "a32"])
        self.assertEqual(code, 2, out)
        self.assertIn("configuration", out)

    def test_cai_t08_2_refuses_two_products_of_one_other_configuration(self):
        """Review F4: both products made with the same variant configuration, checked under the default one."""
        files = t08_cai.write_payloads(self.ws.cells, self.ws.pedestal, self.ws.gain, self.ws.folder, "cai")["files"]
        nominal, derived = files["nominal-multiply"]["path"], files["derived-multiply"]["path"]
        cheap = self.ws.config("cheap", variant_bytes(sharing_iterations=10))
        _, a = self.ws.reconstruct("nominal-cheap", cheap, gain=nominal)
        _, b = self.ws.reconstruct("changed-cheap", cheap, gain=derived)
        code, out = run_main(t08_cai.main, ["rereco", "--nominal", str(a), "--changed", str(b), "--old-gain", nominal, "--new-gain", derived,
                                            "--out", str(self.ws.folder / "cai2-cheap.jsonl"), "--label", "a32"])
        self.assertEqual(code, 2, out)
        self.assertIn("not the configuration given here", out)
        self.assertFalse((self.ws.folder / "cai2-cheap.jsonl").exists())

    def test_cai_thresholds_come_from_the_products_own_configuration(self):
        files = t08_cai.write_payloads(self.ws.cells, self.ws.pedestal, self.ws.gain, self.ws.folder, "cai")["files"]
        nominal, derived = files["nominal-multiply"]["path"], files["derived-multiply"]["path"]
        _, frozen = self.ws.reconstruct("frozen", gain=nominal)
        other = self.ws.config("coarse", variant_bytes(cell_threshold_mev=1.2))
        code, out = run_main(t08_cai.main, ["fixed-membership", "--product", str(frozen), "--old-gain", nominal, "--new-gain", derived,
                                            "--out", str(self.ws.folder / "cai1.jsonl"), "--label", "a32", "--min-asserted", "0",
                                            "--configuration", str(other)])
        self.assertEqual(code, 2, out)
        self.assertIn("configuration", out)
        code, out = run_main(t08_cai.main, ["fixed-membership", "--product", str(frozen), "--old-gain", nominal, "--new-gain", derived,
                                            "--out", str(self.ws.folder / "cai1-own.jsonl"), "--label", "a32", "--min-asserted", "0"])
        self.assertEqual(code, 0, out)

    def test_multiplicity_and_model_changes_are_refused_in_a_t08_grid_configuration(self):
        for name, content in (("peaks kept 3", variant_bytes(peaks_kept=3)), ("no response model", variant_bytes(cell_quantum_mev=None))):
            with self.subTest(change=name):
                with self.assertRaises(configuration.ConfigurationError):
                    configuration.from_bytes(content)


# --- A38: the same selection everywhere, hit and unhit counted, no repeated correction --------------------------------------

class A38Selection(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        # lone shower; pair; lone shower with a dead cell at its centre; a faint shower whose component has no seed (unclustered)
        self.events = [LONE, PAIR, [(2000.0, 25.5, 14.5)], [(30.0, 8.5, 30.5), (2000.0, 25.3, 14.2)]]
        self.ws = Workspace(Path(self.folder.name), self.events, dead={2: [(25, 14)]})
        self.readout = cell_input.read_file(self.ws.cells, cell_input.read_cells, "cells")
        self.ped = cell_input.read_file(self.ws.pedestal, cell_input.read_payload, "p")
        self.gain = cell_input.read_file(self.ws.gain, gain_payload.read_gain, "g")
        p, self.path = self.ws.reconstruct("honest")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.read = product.read_product(self.path)
        self.cfg = configuration.load()

    def energy(self, i, raw=None):
        sc = scenarios()
        return sc.cell_energies(self.readout.raw[i] if raw is None else raw, self.readout.live[i], self.ped.values, self.gain.values,
                                self.gain.operation)

    def test_honest_events_have_exactly_the_section_7_1_selection(self):
        sc = scenarios()
        for i, doc in enumerate(self.read.events):
            with self.subTest(event=i):
                self.assertEqual(sc.selection_defects(doc, self.readout.raw[i], self.readout.live[i], self.energy(i), self.cfg), [])
        # the faint shower's cells above T_c stay unclustered and are counted there
        faint = self.read.events[3]
        self.assertGreater(faint["unclustered_cells"], 0)
        self.assertGreater(faint["unclustered_sum"], 20.0)
        self.assertEqual(self.read.events[2]["dead_channels"], [25 * N + 14])

    def test_each_selection_defect_is_named(self):
        sc = scenarios()
        doc, raw = self.read.events[0], self.readout.raw[0].copy()
        kept = {row[0] for row in doc["cells"]}
        far_cell = next(c for c in range(N * N) if c not in kept and abs(c // N - 12) > 6)
        edge_cell = next(c for c in range(N * N) if c not in kept and any((c // N + dx) * N + (c % N + dy) in kept
                                                                          for dx in (-1, 0, 1) for dy in (-1, 0, 1)))
        low_kept = min(doc["cells"], key=lambda row: row[5])[0]
        cases = {"left unclustered": (far_cell, T_S + 1.0), "adjacent": (edge_cell, T_C + 0.1)}
        for name, (cell, value) in cases.items():
            with self.subTest(defect=name):
                planted = raw.copy()
                planted.flat[cell] = value
                found = sc.selection_defects(doc, planted, self.readout.live[0], self.energy(0, planted), self.cfg)
                self.assertTrue(any(name in d for d in found), found)
        planted = raw.copy()
        planted.flat[low_kept] = T_C / 2
        found = sc.selection_defects(doc, planted, self.readout.live[0], self.energy(0, planted), self.cfg)
        self.assertTrue(any("raw value" in d for d in found), found)
        lowered = json.loads(json.dumps(doc))
        lowered["unclustered_sum"] += 1.0
        found = sc.selection_defects(lowered, raw, self.readout.live[0], self.energy(0), self.cfg)
        self.assertTrue(any("unclustered" in d for d in found), found)
        unseeded = configuration.from_bytes(variant_bytes(seed_threshold_mev=1e6))
        found = sc.selection_defects(doc, raw, self.readout.live[0], self.energy(0), unseeded)
        self.assertTrue(any("no cell at or above T_s" in d for d in found), found)

    # --- fix round 1 (review F1): each rule of section 7.1's selection, from the input -------------------------------------

    def planted(self, i, edit):
        doc = json.loads(json.dumps(self.read.events[i]))
        edit(doc)
        doc["cells"].sort(key=lambda row: row[0])
        return scenarios().selection_defects(doc, self.readout.raw[i], self.readout.live[i], self.energy(i), self.cfg)

    def test_a_seedless_component_under_a_seeded_label_is_caught(self):
        """The reviewer's probe P1: the faint shower's cells at or above T_c (their component has no seed) put into the kept cells
        under the seeded component 0's label, with their count and energy moved from unclustered to clustered."""
        energy = self.energy(3)
        kept = {row[0] for row in self.read.events[3]["cells"]}
        faint = [c for c in range(N * N) if c not in kept and energy.flat[c] >= T_C and c // N < 15]
        self.assertGreater(len(faint), 5)

        def merge(doc):
            moved = sum(float(energy.flat[c]) for c in faint)
            for c in faint:
                doc["cells"].append([c, float(self.readout.raw[3].flat[c]), 0.0, float(self.readout.raw[3].flat[c]), 1.0, float(energy.flat[c]), 0, 0])
            doc["unclustered_cells"] -= len(faint)
            doc["unclustered_sum"] -= moved
            doc["clustered_sum"] += moved
        found = self.planted(3, merge)
        self.assertTrue(any("no cell at or above T_s" in d and "kept" in d for d in found), found)

    def test_two_labels_of_one_component_are_caught(self):
        def split(doc):
            rows = doc["cells"]
            for row in rows[: len(rows) // 2]:
                row[7] = 7
        found = self.planted(0, split)
        self.assertTrue(any("not one" in d for d in found), found)

    def test_two_components_under_one_label_are_caught(self):
        sc = scenarios()
        ws = Workspace(Path(self.folder.name), [[(2000.0, 10.3, 10.2), (2000.0, 28.4, 29.1)]], stem="two")
        _, path = ws.reconstruct("two")
        doc = product.read_product(path).events[0]
        readout = cell_input.read_file(ws.cells, cell_input.read_cells, "cells")
        energy = sc.cell_energies(readout.raw[0], readout.live[0], self.ped.values, self.gain.values, self.gain.operation)
        self.assertEqual(len({row[7] for row in doc["cells"]}), 2)
        self.assertEqual(sc.selection_defects(doc, readout.raw[0], readout.live[0], energy, self.cfg), [])
        for row in doc["cells"]:
            row[7] = 0
        found = sc.selection_defects(doc, readout.raw[0], readout.live[0], energy, self.cfg)
        self.assertTrue(any("not one" in d for d in found), found)

    def test_dead_channels_other_than_the_readouts_are_caught(self):
        found = self.planted(2, lambda doc: doc.update(dead_channels=[]))
        self.assertTrue(any("dead channels" in d for d in found), found)
        found = self.planted(0, lambda doc: doc.update(dead_channels=[5]))
        self.assertTrue(any("dead channels" in d for d in found), found)

    def test_counts_every_input_event_is_in_the_product_selected_or_not(self):
        """A38 counts: an event with no kept component (a single seedless shower) is still an event of the product, with no object
        and all its live cells unclustered; a product short of an event is refused."""
        folder = Path(self.folder.name)
        ws = Workspace(folder, [LONE, [(30.0, 8.5, 30.5)], LONE], stem="counts")
        _, path = ws.reconstruct("counts")
        read = product.read_product(path)
        self.assertEqual(len(read.events), 3)
        empty = read.events[1]
        self.assertEqual((empty["objects"], empty["cells"], empty["unclustered_cells"]), ([], [], N * N))
        lines = path.read_text().splitlines()
        with self.assertRaises(product.ProductError):
            product.read_text("\n".join(lines[:2] + lines[3:]) + "\n")

    def test_the_reader_refuses_cells_that_do_not_account_for_the_grid(self):
        lines = self.path.read_text().splitlines()
        doc = json.loads(lines[1])
        doc["unclustered_cells"] += 1
        lines[1] = product.dumps(doc)
        with self.assertRaisesRegex(product.ProductError, "account for"):
            product.read_text("\n".join(lines) + "\n")

    def test_the_accounting_tool_on_honest_files_and_on_other_cells(self):
        sc = scenarios()
        base = ["accounting", "--pedestal-payload", str(self.ws.pedestal), "--gain-payload", str(self.ws.gain), "--product", str(self.path)]
        code, out = run_main(sc.main, base + ["--cells", str(self.ws.cells), "--label", "honest"])
        self.assertEqual(code, 0, out)
        self.assertIn("GATE honest selection-and-accounting PASS: 0 of 4 events", out)
        other = Workspace(Path(self.folder.name), [LONE], stem="other")
        code, out = run_main(sc.main, base + ["--cells", str(other.cells), "--label", "other"])
        self.assertEqual(code, 2, out)
        self.assertIn("REFUSED", out)

    def test_the_reference_clusterer_constants_are_the_configurations(self):
        sc = scenarios()
        text = "W, SN, Q, TC, TS = 1.0, 0.2, 0.2, 0.6, 10.0\nHALF = 16\nITERS = 30\n"
        self.assertEqual(sc.reference_selection_defects(text, self.cfg), [])
        for changed, line in (("TS", "W, SN, Q, TC, TS = 1.0, 0.2, 0.2, 0.6, 12.0\nITERS = 30\n"),
                              ("TC", "W, SN, Q, TC, TS = 1.0, 0.2, 0.2, 0.7, 10.0\nITERS = 30\n"),
                              ("ITERS", "W, SN, Q, TC, TS = 1.0, 0.2, 0.2, 0.6, 10.0\nITERS = 20\n"),
                              ("missing", "ITERS = 30\n")):
            with self.subTest(changed=changed):
                self.assertNotEqual(sc.reference_selection_defects(line, self.cfg), [])
        script = Path(self.folder.name) / "calc-t08-reference.py"
        script.write_text(text)
        code, out = run_main(sc.main, ["reference-selection", "--script", str(script)])
        self.assertEqual(code, 2, out)           # not the frozen script's SHA-256: refused, never compared
        self.assertEqual(len(sc.REFERENCE_SCRIPT_SHA256), 64)

    def test_the_readings_hold_the_frozen_configurations_identity_and_constants(self):
        self.assertEqual(t08_readings.REFERENCE_CONFIGURATION_SHA256, sha(FROZEN_FILE.read_bytes()))
        self.assertEqual((t08_readings.Q_MEV, t08_readings.SIGMA_N_MEV), (self.cfg.quantum, self.cfg.noise_sigma))

    def test_a_correction_is_never_applied_to_values_it_was_not_made_for(self):
        raw = numpy.array([image(LONE)])
        live, sat = numpy.ones(raw.shape, bool), numpy.zeros(raw.shape, bool)
        folder = Path(self.folder.name)
        cases = {"calibrated readout, ADC payloads": ("MeV", stage1_payloads("adc")),
                 "ADC readout, a gain for calibrated values": ("adc", stage1_payloads("adc", gain_unit="MeV/MeV")),
                 "dividing gain in a multiplying unit": ("adc", stage1_payloads("adc", gain_unit="MeV/adc", operation="divide")),
                 # fix round 1: the gain is right for the readout (MeV/MeV), only the pedestal is not, so only the pedestal rule refuses
                 "calibrated readout, an ADC pedestal": ("MeV", (stage1_payloads("adc")[0],
                                                                  cell_input.payload_bytes("gain", "multiply", 1.0, N * N, "MeV/MeV", "nominal",
                                                                                           "hand-made test constant",
                                                                                           derived_against=[sha(stage1_payloads("adc")[0])])))}
        for name, (raw_unit, (ped, gain)) in cases.items():
            with self.subTest(case=name):
                stem = name.replace(",", "").replace(" ", "-")
                (folder / f"{stem}.cells").write_bytes(cell_input.cells_bytes(raw, live, sat, raw_unit=raw_unit))
                (folder / f"{stem}.p.json").write_bytes(ped)
                (folder / f"{stem}.g.json").write_bytes(gain)
                p, out = self.ws.reconstruct(stem, cells=folder / f"{stem}.cells", pedestal=folder / f"{stem}.p.json", gain=folder / f"{stem}.g.json")
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertIn("unit", json.loads(p.stdout)["reason"])
                self.assertFalse(out.exists())
        for name, raw_unit in (("adc", "adc"), ("identity readout", "MeV")):
            with self.subTest(consistent=name):
                stem = "ok-" + raw_unit
                ped, gain = stage1_payloads(raw_unit)
                (folder / f"{stem}.cells").write_bytes(cell_input.cells_bytes(raw, live, sat, raw_unit=raw_unit))
                (folder / f"{stem}.p.json").write_bytes(ped)
                (folder / f"{stem}.g.json").write_bytes(gain)
                p, _ = self.ws.reconstruct(stem, cells=folder / f"{stem}.cells", pedestal=folder / f"{stem}.p.json", gain=folder / f"{stem}.g.json")
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_a_gain_is_never_applied_twice_through_the_cai_checks(self):
        files = t08_cai.write_payloads(self.ws.cells, self.ws.pedestal, self.ws.gain, self.ws.folder, "cai")["files"]
        nominal, derived = files["nominal-multiply"]["path"], files["derived-multiply"]["path"]
        _, with_derived = self.ws.reconstruct("with-derived", gain=derived)
        # the product already carries the derived gain: re-evaluating it from nominal to derived would apply the change twice
        code, out = run_main(t08_cai.main, ["fixed-membership", "--product", str(with_derived), "--old-gain", nominal, "--new-gain", derived,
                                            "--out", str(self.ws.folder / "twice.jsonl"), "--label", "a38", "--min-asserted", "0"])
        self.assertEqual(code, 2, out)
        self.assertIn("did not consume", out)
        self.assertFalse((self.ws.folder / "twice.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
