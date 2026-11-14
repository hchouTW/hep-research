"""adapters/calo-cluster, D2 stage 3 of T08 (t07-t09-task-sheets.md, T08, "Input, second"): cell deposits from the user-supplied
zdcsim program, labelled simulated-unvalidated. Hand-made inputs only: no ROOT file is read here (the uproot reader has its own
module, tests/adapters/test_calo_zdcsim_root.py), no Geant4 or Monte Carlo runs, and zdcsim.cc is never read: its hash check is
driven with a stand-in file whose hash is passed in.

Covered: the converter's sums and refusals on stand-in deposits; the channel map between zdcsim's cell = iy * n + ix and the
recipe's channel = ix * ny + iy; zdcsim's configuration rules; the labelled readout calo-cells/2 and the labelled product
calo-cluster-product/3 with their round trip and refusals; the configuration calo-cluster-configuration/2 (no shower profile, no
response model: the rule that replaces them); the readings, which print bookkeeping only; and that the stage 1 and 2 paths on
t08-grid/1 keep their formats and fields. Expectations are written in the test before the code runs.

Run from the plugin root: python -m unittest tests.adapters.test_calo_zdcsim -v
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "calo-cluster"
ASSETS = ADAPTER / "assets"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ASSETS / "fixture_tools"))
sys.path.insert(0, str(ASSETS))

from calo_recipe import cell_input, configuration, gain_payload, product  # noqa: E402
import t08_zdcsim_cells as zc  # noqa: E402

LABEL = "simulated-unvalidated"
N = 6                     # prototype v2: n_crystals 6 (config/geometry/prototype_v2.yaml of the study)
Z_BINS = 53                   # crystal_z_mm 53 in 1 mm bins: ceil(53 / 1)
PROTOTYPE_CONFIG = ASSETS / "zdcsim-prototype-v2.configuration.json"
F32 = lambda v: float(numpy.float32(v))  # noqa: E731  zdcsim writes edep as float


def ev(*entries):
    """One stand-in event: entries (cell, zbin, edep) -> the three column arrays, as the ROOT reader returns them."""
    cell = numpy.array([e[0] for e in entries], dtype=numpy.int32)
    zbin = numpy.array([e[1] for e in entries], dtype=numpy.int32)
    edep = numpy.array([e[2] for e in entries], dtype=numpy.float32)
    return cell, zbin, edep


def provenance(entries=3, seed=930001):
    """A provenance block of the shape the converter writes (hashes are stand-ins: 64 hex digits)."""
    return {"producer": {"name": "zdcsim", "source_sha256": "a" * 64, "label": "user-supplied", "build": {"executable_sha256": None}},
            "configuration": [{"role": "geometry", "name": "g.yaml", "sha256": "b" * 64},
                              {"role": "sample", "name": "s.yaml", "sha256": "c" * 64}],
            "run": {"seed": seed, "events": entries, "physics": "FTFP_BERT_EMZ", "threads": 1},
            "input": {"format": zc.INPUT_FORMAT, "tree": "events", "sha256": "d" * 64, "entries": entries},
            "conversion": {"tool_sha256": "e" * 64, "rule": zc.CONVERSION_RULE, "readout": zc.READOUT_RULE,
                           "geometry": {"n_crystals": N, "z_bins": Z_BINS}}}


def labelled_cells(raw, prov=None):
    raw = numpy.asarray(raw, dtype=float)
    live = numpy.ones(raw.shape, bool)
    return cell_input.cells_bytes(raw, live, numpy.zeros(raw.shape, bool), raw_unit=zc.RAW_UNIT, label=LABEL,
                                  provenance=prov if prov is not None else provenance(raw.shape[0]))


def identity_payloads(channels=N * N):
    ped = cell_input.payload_bytes("pedestal", "subtract", 0.0, channels, zc.RAW_UNIT, "nominal", zc.PEDESTAL_SOURCE)
    gain = cell_input.payload_bytes("gain", "multiply", 1.0, channels, "MeV/MeV", "nominal", zc.GAIN_SOURCE,
                                    derived_against=[hashlib.sha256(ped).hexdigest()])
    return ped, gain


def run_cli(*args):
    return subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "calo_cluster.py"), *args], capture_output=True, text=True,
                          cwd=str(ROOT), timeout=300)


def run_tool(*args):
    return subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "fixture_tools" / "t08_zdcsim_cells.py"), *args],
                          capture_output=True, text=True, cwd=str(ROOT), timeout=300)


# --- the converter --------------------------------------------------------------------------------------------------------

class ChannelMap(unittest.TestCase):
    def test_zdcsim_cell_to_recipe_cell_for_every_crystal(self):
        # zdcsim: id = iy * n + ix (the placement loop); recipe: array axis 0 is ix, channel = ix * ny + iy (section 7.1).
        seen = set()
        for iy in range(N):
            for ix in range(N):
                self.assertEqual(zc.recipe_cell(iy * N + ix, N), (ix, iy))
                seen.add(ix * N + iy)
        self.assertEqual(seen, set(range(N * N)))

    def test_the_two_orders_differ_off_the_diagonal(self):
        self.assertEqual(zc.recipe_cell(13, N), (1, 2))      # zdcsim 13 = iy 2, ix 1 -> recipe channel 1 * 6 + 2 = 8
        self.assertEqual(zc.recipe_cell(8, N), (2, 1))       # zdcsim 8 = iy 1, ix 2 -> recipe channel 13


class Sums(unittest.TestCase):
    EVENTS = [ev((13, 0, 1.5), (13, 1, 2.25), (13, 52, 0.25), (8, 3, 0.125), (0, 0, 4.0)),
              ev(),
              ev((35, 10, 0.1), (35, 11, 0.2), (35, 12, 0.3))]

    def setUp(self):
        self.raw, self.record = zc.deposits_to_cells(self.EVENTS, N, Z_BINS)

    def test_shape_and_untouched_cells(self):
        self.assertEqual(self.raw.shape, (3, N, N))
        self.assertEqual(self.raw.dtype, numpy.float64)
        touched = {(0, 1, 2), (0, 2, 1), (0, 0, 0), (2, 5, 5)}
        for idx in numpy.ndindex(self.raw.shape):
            if idx not in touched:
                self.assertEqual(self.raw[idx], 0.0, idx)

    def test_exact_sums_over_zbin(self):
        self.assertEqual(self.raw[0, 1, 2], 4.0)              # 1.5 + 2.25 + 0.25, each exact in float
        self.assertEqual(self.raw[0, 2, 1], 0.125)
        self.assertEqual(self.raw[0, 0, 0], 4.0)
        self.assertEqual(self.raw[2, 5, 5], math.fsum([F32(0.1), F32(0.2), F32(0.3)]))
        self.assertEqual(self.raw[2, 5, 5], 0.6000000163912773)

    def test_event_record(self):
        self.assertEqual([r["entries"] for r in self.record], [5, 0, 3])
        self.assertEqual([r["cells_hit"] for r in self.record], [3, 0, 1])
        self.assertEqual([r["deposit_sum_mev"] for r in self.record], [8.125, 0.0, math.fsum([F32(0.1), F32(0.2), F32(0.3)])])
        self.assertEqual([r["event"] for r in self.record], [0, 1, 2])

    def test_sum_does_not_depend_on_entry_order(self):
        shuffled = [ev((35, 12, 0.3), (35, 10, 0.1), (35, 11, 0.2))]
        raw, _ = zc.deposits_to_cells(shuffled, N, Z_BINS)
        self.assertEqual(raw[0, 5, 5], self.raw[2, 5, 5])

    def test_a_zero_deposit_is_kept(self):
        raw, record = zc.deposits_to_cells([ev((4, 0, 0.0))], N, Z_BINS)
        self.assertEqual(raw[0, 4, 0], 0.0)
        self.assertEqual(record[0]["entries"], 1)


class Refusals(unittest.TestCase):
    def refused(self, events, text):
        with self.assertRaises(zc.ConversionError) as cm:
            zc.deposits_to_cells(events, N, Z_BINS)
        self.assertIn(text, str(cm.exception))

    def test_unknown_cell(self):
        for cell in (36, -1, 1000, 2000, 5000, 10000):   # beyond the grid, and zdcsim's HCAL ranges
            self.refused([ev((cell, 0, 1.0))], "unknown cell")

    def test_zbin_outside_the_crystal(self):
        self.refused([ev((3, 53, 1.0))], "z bin")
        self.refused([ev((3, -1, 1.0))], "z bin")

    def test_negative_or_non_finite_deposit(self):
        self.refused([ev((3, 0, -0.5))], "negative or non-finite")
        self.refused([ev((3, 0, float("nan")))], "negative or non-finite")
        self.refused([ev((3, 0, float("inf")))], "negative or non-finite")

    def test_columns_of_unequal_length(self):
        cell, zbin, edep = ev((3, 0, 1.0), (4, 0, 1.0))
        self.refused([(cell, zbin[:1], edep)], "lengths")

    def test_a_cell_and_bin_given_twice(self):
        self.refused([ev((3, 7, 1.0), (3, 7, 2.0))], "twice")

    def test_refusal_names_the_event(self):
        self.refused([ev((3, 0, 1.0)), ev((99, 0, 1.0))], "event 1")


class ZdcsimConfiguration(unittest.TestCase):
    """zdcsim's rules (Cfg::load): 'key: value' lines, '#' starts a comment, quotes and blanks trimmed, later files override
    earlier ones; n_crystals defaults to 8, crystal_z_mm to 53, type to prototype; integers are lround of the number."""

    def parse(self, *texts):
        with tempfile.TemporaryDirectory() as work:
            paths = []
            for k, text in enumerate(texts):
                p = Path(work) / f"{k}.yaml"
                p.write_text(text)
                paths.append(p)
            return zc.zdcsim_geometry(paths)

    def test_prototype_v2_values(self):
        g = self.parse("# 2nd prototype\ntype: prototype\nn_crystals: 6\ncrystal_x_mm: 20\ncrystal_y_mm: 20\ncrystal_z_mm: 53\n"
                       "wrap_um: 65          # (assumption)\ngap_mm: 0.2\n", "particle: e+\nenergy_mev: 500\n")
        self.assertEqual((g["n_crystals"], g["z_bins"]), (6, 53))
        self.assertAlmostEqual(g["pitch_x_mm"], 20.33, places=12)
        self.assertAlmostEqual(g["pitch_y_mm"], 20.33, places=12)

    def test_defaults_quotes_and_override(self):
        g = self.parse("crystal_z_mm: '53.5'\n", "n_crystals: \"4\"\n")
        self.assertEqual((g["n_crystals"], g["z_bins"]), (4, 54))
        self.assertEqual(self.parse("gap_mm: 0.2\n")["n_crystals"], 8)
        self.assertEqual(self.parse("n_crystals: 6\n", "n_crystals: 5\n")["n_crystals"], 5)

    def test_only_the_prototype_is_read(self):
        with self.assertRaises(zc.ConversionError) as cm:
            self.parse("type: zdc\nn_crystals: 6\n")
        self.assertIn("prototype", str(cm.exception))


class SourceHash(unittest.TestCase):
    def test_the_supplied_files_hash_is_fixed(self):
        self.assertEqual(zc.ZDCSIM_SOURCE_SHA256, "28018224c1419a87e0da7f6b24b3557d93b878269f32f8d5aaedecf0d51ec203")

    def test_another_source_is_refused(self):
        with tempfile.TemporaryDirectory() as work:
            p = Path(work) / "zdcsim.cc"
            p.write_text("// not the supplied file\n")
            with self.assertRaises(zc.ConversionError) as cm:
                zc.check_source(p)
            self.assertIn("not the supplied", str(cm.exception))
            self.assertEqual(zc.check_source(p, expected=hashlib.sha256(p.read_bytes()).hexdigest()),
                             hashlib.sha256(p.read_bytes()).hexdigest())


class Files(unittest.TestCase):
    """write_files: the labelled readout, the identity payloads and the conversion record, with the provenance on each."""

    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        raw, record = zc.deposits_to_cells(Sums.EVENTS, N, Z_BINS)
        self.files = zc.write_files(raw, record, provenance(3), self.work.name, "s")
        self.dir = Path(self.work.name)

    def tearDown(self):
        self.work.cleanup()

    def test_readout_is_labelled_and_round_trips(self):
        read = cell_input.read_file(self.dir / "s.cells", cell_input.read_cells, "cells")
        self.assertEqual(read.header["format"], "calo-cells/2")
        self.assertEqual(read.header["label"], LABEL)
        self.assertEqual(read.header["provenance"], provenance(3))
        self.assertEqual(read.header["raw_unit"], zc.RAW_UNIT)
        self.assertTrue(read.live.all())
        self.assertFalse(read.saturated.any())
        self.assertEqual(read.raw[0, 1, 2], 4.0)
        self.assertEqual(self.files["cells"]["sha256"], hashlib.sha256((self.dir / "s.cells").read_bytes()).hexdigest())

    def test_identity_payloads_in_chain_order(self):
        from calo_recipe import cell_chain
        ped = cell_input.read_file(self.dir / "s.pedestal.json", cell_input.read_payload, "pedestal")
        gain = cell_input.read_file(self.dir / "s.gain.json", cell_input.read_payload, "gain")
        self.assertEqual((ped.step, ped.operation, ped.origin), ("pedestal", "subtract", "nominal"))
        self.assertTrue(numpy.all(ped.values == 0.0))
        self.assertEqual((gain.step, gain.operation, gain.origin), ("gain", "multiply", "nominal"))
        self.assertTrue(numpy.all(gain.values == 1.0))
        chain = cell_chain.chain_record(ped, gain)
        self.assertEqual([s["step"] for s in chain], ["pedestal", "gain"])
        self.assertIn("identity readout", ped.document["producer"]["source"])
        self.assertIn("identity readout", gain.document["producer"]["source"])

    def test_conversion_record(self):
        doc = json.loads((self.dir / "s.conversion.json").read_text())
        self.assertEqual(doc["format"], zc.CONVERSION_FORMAT)
        self.assertEqual(doc["label"], LABEL)
        self.assertEqual(doc["provenance"], provenance(3))
        self.assertEqual(doc["cells_sha256"], self.files["cells"]["sha256"])
        self.assertEqual([e["deposit_sum_mev"] for e in doc["events"]][:2], [8.125, 0.0])
        self.assertEqual(zc.read_conversion(self.dir / "s.conversion.json")["label"], LABEL)

    def test_conversion_record_without_label_or_provenance_is_refused(self):
        doc = json.loads((self.dir / "s.conversion.json").read_text())
        for key in ("label", "provenance"):
            bad = {k: v for k, v in doc.items() if k != key}
            p = self.dir / f"no-{key}.json"
            p.write_text(json.dumps(bad))
            with self.assertRaises(zc.ConversionError):
                zc.read_conversion(p)

    def test_entries_must_match_the_events(self):
        raw, record = zc.deposits_to_cells(Sums.EVENTS, N, Z_BINS)
        with self.assertRaises(zc.ConversionError) as cm:
            zc.write_files(raw, record, provenance(4), self.work.name, "t")
        self.assertIn("entries", str(cm.exception))
        self.assertFalse((self.dir / "t.cells").exists())


# --- the labelled readout, calo-cells/2 -----------------------------------------------------------------------------------

class LabelledReadout(unittest.TestCase):
    def raw(self):
        return numpy.zeros((2, N, N))

    def test_round_trip(self):
        read = cell_input.read_cells(labelled_cells(self.raw()))
        self.assertEqual((read.header["label"], read.header["provenance"]), (LABEL, provenance(2)))
        self.assertEqual(read.label, LABEL)

    def test_unlabelled_readout_is_unchanged(self):
        content = cell_input.cells_bytes(self.raw(), numpy.ones((2, N, N), bool), numpy.zeros((2, N, N), bool))
        read = cell_input.read_cells(content)
        self.assertEqual(set(read.header), cell_input.HEADER_KEYS)
        self.assertEqual(read.header["format"], "calo-cells/1")
        self.assertIsNone(read.label)

    def header_variant(self, edit):
        content = labelled_cells(self.raw())
        (length,) = __import__("struct").unpack("<I", content[8:12])
        header = json.loads(content[12:12 + length])
        edit(header)
        text = json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
        return content[:8] + __import__("struct").pack("<I", len(text)) + text + content[12 + length:]

    def refused(self, edit, text):
        with self.assertRaises(cell_input.InputError) as cm:
            cell_input.read_cells(self.header_variant(edit))
        self.assertIn(text, str(cm.exception))

    def test_refusals(self):
        self.refused(lambda h: h.update(label="validated"), "label")
        self.refused(lambda h: h.pop("label"), "keys")
        self.refused(lambda h: h.pop("provenance"), "keys")
        self.refused(lambda h: h["provenance"].pop("run"), "provenance")
        self.refused(lambda h: h["provenance"]["producer"].update(source_sha256="xyz"), "provenance")
        self.refused(lambda h: h["provenance"]["input"].update(entries=3), "entries")
        self.refused(lambda h: h["provenance"].update(configuration=[]), "provenance")
        self.refused(lambda h: h["provenance"]["run"].update(seed=-1), "seed")
        self.refused(lambda h: h.update(format="calo-cells/1"), "keys")      # a /1 header never carries a label

    def test_cells_bytes_needs_both_or_neither(self):
        raw = self.raw()
        with self.assertRaises(cell_input.InputError):
            cell_input.cells_bytes(raw, numpy.ones(raw.shape, bool), numpy.zeros(raw.shape, bool), label=LABEL)
        with self.assertRaises(cell_input.InputError):
            cell_input.cells_bytes(raw, numpy.ones(raw.shape, bool), numpy.zeros(raw.shape, bool), provenance=provenance(2))


# --- the configuration for the zdcsim prototype grid ----------------------------------------------------------------------

class ZdcsimRecipeConfiguration(unittest.TestCase):
    def test_the_proposed_file(self):
        cfg = configuration.load(PROTOTYPE_CONFIG)
        self.assertEqual(cfg.format, "calo-cluster-configuration/2")
        self.assertEqual(cfg.label, LABEL)
        self.assertEqual((cfg.cells_x, cfg.cells_y, cfg.cell_width), (N, N, 1.0))
        self.assertIsNone(cfg.shower_width)            # no profile: the rule that replaces it, no split
        self.assertIsNone(cfg.quantum)                 # no response model for deposits
        self.assertIsNone(cfg.noise_sigma)
        self.assertFalse(cfg.splits)
        self.assertFalse(cfg.response_model)
        doc = json.loads(PROTOTYPE_CONFIG.read_text())
        self.assertEqual(set(doc["sources"]), configuration.CONSTANT_KEYS)
        for key in ("cell_threshold_mev", "seed_threshold_mev"):      # no source for this geometry: said so in the file
            self.assertIsNone(doc["sources"][key], key)

    def test_t08_grid_configuration_is_unchanged(self):
        content = configuration.DEFAULT_FILE.read_bytes()
        self.assertEqual(hashlib.sha256(content).hexdigest(), "5fbbea3b4ca81d962c5ca70fa024ddc82dd6e1d2f06e39b354fda56d26483723")
        cfg = configuration.load()
        self.assertEqual((cfg.format, cfg.label, cfg.splits, cfg.response_model), ("calo-cluster-configuration/1", None, True, True))

    def variant(self, edit):
        doc = json.loads(PROTOTYPE_CONFIG.read_text())
        edit(doc)
        return json.dumps(doc).encode()

    def refused(self, edit, text):
        with self.assertRaises(configuration.ConfigurationError) as cm:
            configuration.from_bytes(self.variant(edit))
        self.assertIn(text, str(cm.exception))

    def test_refusals(self):
        self.refused(lambda d: d.update(shower_width_cells=1.0), "together")       # profile without response model
        self.refused(lambda d: d.update(noise_sigma_mev=0.2), "together")
        self.refused(lambda d: d.update(label="synthetic"), "label")
        self.refused(lambda d: d["sources"].pop("grid"), "sources")
        self.refused(lambda d: d["sources"].update(extra="x"), "sources")
        self.refused(lambda d: d["sources"].update(grid=3), "sources")
        self.refused(lambda d: d.pop("sources"), "keys")
        self.refused(lambda d: d.update(cell_threshold_mev=None), "cell_threshold_mev")

    def test_a_version_1_configuration_takes_no_null_and_no_label(self):
        doc = json.loads(configuration.DEFAULT_FILE.read_text())
        doc["shower_width_cells"] = None
        with self.assertRaises(configuration.ConfigurationError):
            configuration.from_bytes(json.dumps(doc).encode())
        doc = json.loads(configuration.DEFAULT_FILE.read_text())
        doc["label"] = LABEL
        with self.assertRaises(configuration.ConfigurationError):
            configuration.from_bytes(json.dumps(doc).encode())

    def test_section_7_1_in_full_with_stated_constants(self):
        def full(d):
            d.update(shower_width_cells=1.0, cell_quantum_mev=0.2, noise_sigma_mev=0.2)
        cfg = configuration.from_bytes(self.variant(full))
        self.assertTrue(cfg.splits and cfg.response_model)


# --- the recipe on a labelled readout -------------------------------------------------------------------------------------

def prototype_events():
    """Four hand-made 6 x 6 events (array axis 0 is ix), deposits in MeV, T_c 0.6 and T_s 10 as the proposed file.
    0: a diagonal chain (1,1)=50, (2,2)=5, (3,3)=5, (4,4)=30: one component, two kept peaks, left unsplit.
    1: one cell (0,5)=20: one component, one peak.
    2: nothing.
    3: one cell (2,3)=5, below T_s: unclustered."""
    raw = numpy.zeros((4, N, N))
    raw[0, 1, 1], raw[0, 2, 2], raw[0, 3, 3], raw[0, 4, 4] = 50.0, 5.0, 5.0, 30.0
    raw[1, 0, 5] = 20.0
    raw[3, 2, 3] = 5.0
    return raw


class LabelledRecipe(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        d = Path(self.work.name)
        self.cells = d / "z.cells"
        self.cells.write_bytes(labelled_cells(prototype_events(), provenance(4)))
        ped, gain = identity_payloads()
        (d / "ped.json").write_bytes(ped)
        (d / "gain.json").write_bytes(gain)
        self.d = d

    def tearDown(self):
        self.work.cleanup()

    def reconstruct(self, out="p.jsonl", cells=None, config=PROTOTYPE_CONFIG, gain=None):
        return run_cli("reconstruct", "--cells", str(cells or self.cells), "--pedestal-payload", str(self.d / "ped.json"),
                       "--gain-payload", str(gain or self.d / "gain.json"), "--product", str(self.d / out), "--product-id", "zdc-test",
                       "--configuration", str(config))

    def test_product_is_labelled_with_the_inputs_provenance(self):
        p = self.reconstruct()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual(out["label"], LABEL)
        read = product.read_product(self.d / "p.jsonl")
        h = read.header
        self.assertEqual(h["format"], "calo-cluster-product/3")
        self.assertEqual(h["label"], LABEL)
        self.assertEqual(h["provenance"], provenance(4))
        self.assertEqual(h["input"]["format"], "calo-cells/2")
        self.assertEqual(h["configuration"], {"format": "calo-cluster-configuration/2",
                                              "sha256": hashlib.sha256(PROTOTYPE_CONFIG.read_bytes()).hexdigest(),
                                              "unresolved": json.loads(PROTOTYPE_CONFIG.read_text())["unresolved"]})
        self.assertEqual(h["energy_kind"], "clustered-deposited-energy")
        c = run_cli("check-product", "--product", str(self.d / "p.jsonl"))
        self.assertEqual(c.returncode, 0, c.stdout)
        self.assertEqual(json.loads(c.stdout)["double_count_defects"], 0)

    def test_unsplit_and_one_peak_objects_without_a_response_model(self):
        self.assertEqual(self.reconstruct().returncode, 0)
        events = product.read_product(self.d / "p.jsonl").events
        e0 = events[0]
        self.assertEqual(len(e0["components"]), 1)
        self.assertEqual(e0["components"][0]["peaks"], [1 * N + 1, 4 * N + 4])
        self.assertEqual(len(e0["objects"]), 1)
        o = e0["objects"][0]
        self.assertEqual(o["kind"], "unsplit")
        self.assertEqual(o["peak_channel"], 1 * N + 1)
        self.assertEqual(o["energy"], 90.0)
        self.assertAlmostEqual(o["x"], 240.0 / 90.0, places=14)
        self.assertAlmostEqual(o["y"], 240.0 / 90.0, places=14)
        self.assertEqual(o["members"], [[1 * N + 1, 1.0], [2 * N + 2, 1.0], [3 * N + 3, 1.0], [4 * N + 4, 1.0]])
        self.assertEqual(o["uncertainty_status"], "no-response-model")
        self.assertEqual((o["sigma_energy"], o["sigma_x"], o["sigma_y"]), (None, None, None))
        self.assertIsNone(e0["event_sum"]["sigma"])
        self.assertEqual((e0["clustered_sum"], e0["unclustered_sum"], e0["input_sum"]), (90.0, 0.0, 90.0))
        o1 = events[1]["objects"][0]
        self.assertEqual((o1["kind"], o1["energy"], o1["x"], o1["y"]), ("one-peak", 20.0, 0.5, 5.5))
        self.assertEqual(o1["uncertainty_status"], "no-response-model")
        self.assertEqual((events[2]["objects"], events[2]["input_sum"]), ([], 0.0))
        self.assertEqual((events[3]["objects"], events[3]["unclustered_sum"], events[3]["unclustered_cells"]), ([], 5.0, N * N))

    def test_raw_kept_beside_calibrated_through_the_identity_chain(self):
        self.assertEqual(self.reconstruct().returncode, 0)
        rows = product.read_product(self.d / "p.jsonl").events[1]["cells"]
        self.assertEqual(rows, [[0 * N + 5, 20.0, 0.0, 20.0, 1.0, 20.0, 0, 0]])

    def test_labelled_input_with_the_t08_grid_configuration_is_refused(self):
        big = self.d / "big.cells"
        big.write_bytes(labelled_cells(numpy.zeros((1, 40, 40)), provenance(1)))
        ped, gain = identity_payloads(1600)
        (self.d / "ped.json").write_bytes(ped)
        (self.d / "gain.json").write_bytes(gain)
        p = self.reconstruct(cells=big, config=configuration.DEFAULT_FILE)
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertIn("written for its label", json.loads(p.stdout)["reason"])
        self.assertFalse((self.d / "p.jsonl").exists())

    def test_unlabelled_input_with_the_labelled_configuration_is_refused(self):
        plain = self.d / "plain.cells"
        raw = prototype_events()
        plain.write_bytes(cell_input.cells_bytes(raw, numpy.ones(raw.shape, bool), numpy.zeros(raw.shape, bool)))
        p = self.reconstruct(cells=plain)
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertIn("labelled input", json.loads(p.stdout)["reason"])

    def test_labelled_input_with_a_gain_payload_of_format_1_is_refused(self):
        ped = cell_input.read_payload((self.d / "ped.json").read_bytes())
        gp = gain_payload.payload_bytes("multiply", 1.0, N, N, "nominal", "test", derived_against=[ped.identity])
        (self.d / "gp.json").write_bytes(gp)
        p = self.reconstruct(gain=self.d / "gp.json")
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertIn("calo-gain-payload/1", json.loads(p.stdout)["reason"])


class LabelledProductReader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        t = LabelledRecipe("test_product_is_labelled_with_the_inputs_provenance")
        t.setUp()
        assert t.reconstruct().returncode == 0
        cls.text = (t.d / "p.jsonl").read_text()
        t.tearDown()

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def lines(self):
        return [json.loads(line) for line in self.text.splitlines()]

    def rewrite(self, docs):
        return "\n".join(product.dumps(d) for d in docs) + "\n"

    def refused(self, edit, text):
        docs = self.lines()
        edit(docs)
        with self.assertRaises(product.ProductError) as cm:
            product.read_text(self.rewrite(docs))
        self.assertIn(text, str(cm.exception))

    def test_reads(self):
        self.assertEqual(product.read_text(self.text).header["label"], LABEL)

    def test_without_label_or_provenance(self):
        self.refused(lambda d: d[0].pop("label"), "keys")
        self.refused(lambda d: d[0].pop("provenance"), "keys")
        self.refused(lambda d: d[0].update(label="synthetic"), "label")
        self.refused(lambda d: d[0]["provenance"].pop("input"), "provenance")

    def test_format_and_input_must_agree(self):
        def as_v1(d):
            d[0]["format"] = "calo-cluster-product/1"
            d[-1]["end"] = "calo-cluster-product/1"
        self.refused(as_v1, "keys")                                               # /1 carries no label
        self.refused(lambda d: d[0]["input"].update(format="calo-cells/1"), "calo-cells/2")
        self.refused(lambda d: d[0]["configuration"].update(format="calo-cluster-configuration/1"), "configuration")
        self.refused(lambda d: d[0]["provenance"]["input"].update(entries=5), "entries")

    def test_uncertainty_and_model_must_agree(self):
        self.refused(lambda d: d[1]["event_sum"].update(sigma=1.0), "response model")
        def one_ok(d):
            d[2]["objects"][0].update(uncertainty_status="ok", sigma_energy=1.0, sigma_x=0.1, sigma_y=0.1)
        self.refused(one_ok, "response model")

    def test_unsplit_needs_two_peaks_and_fractions_one(self):
        self.refused(lambda d: d[2]["objects"][0].update(kind="unsplit"), "two kept peaks")
        self.refused(lambda d: d[1]["objects"][0]["members"][0].__setitem__(1, 0.5), "fraction")

    def test_versions_1_and_2_refuse_the_new_kind_and_status(self):
        # A t08-grid/1 shaped product (/1) with an unsplit object or a no-response-model status is refused as before.
        self.assertNotIn("unsplit", product.KINDS)
        self.assertNotIn("no-response-model", product.STATUSES)


class Readings(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.d = Path(self.work.name)
        raw, record = zc.deposits_to_cells(
            [ev((1 * N + 1, 0, 30.0), (1 * N + 1, 5, 20.0), (2 * N + 2, 1, 5.0), (3 * N + 3, 2, 5.0), (4 * N + 4, 3, 30.0)),
             ev((5 * N + 0, 4, 20.0)), ev(), ev((3 * N + 2, 0, 5.0))], N, Z_BINS)
        self.files = zc.write_files(raw, record, provenance(4), self.d, "z")
        p = run_cli("reconstruct", "--cells", str(self.d / "z.cells"), "--pedestal-payload", str(self.d / "z.pedestal.json"),
                    "--gain-payload", str(self.d / "z.gain.json"), "--product", str(self.d / "z.product.jsonl"), "--product-id", "r",
                    "--configuration", str(PROTOTYPE_CONFIG))
        assert p.returncode == 0, p.stdout + p.stderr

    def tearDown(self):
        self.work.cleanup()

    def readings(self, conversion=None, prod=None):
        return run_tool("readings", "--product", str(prod or self.d / "z.product.jsonl"),
                        "--conversion", str(conversion or self.d / "z.conversion.json"), "--label", "unit")

    def test_gates_pass_and_only_bookkeeping_is_printed(self):
        p = self.readings()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        lines = p.stdout.splitlines()
        gates = [line for line in lines if line.startswith("GATE ")]
        self.assertEqual(len(gates), 4, p.stdout)
        self.assertTrue(all(line.endswith(" PASS") for line in gates), p.stdout)
        readings = [line for line in lines if line.startswith("READING ")]
        names = {line.split()[2] for line in readings}
        self.assertEqual(names, zc.READING_NAMES)
        for word in ("pull", "resolution", "efficiency", "linearity", "incident"):
            self.assertNotIn(word, p.stdout.lower())
        self.assertIn("READING unit events 4", p.stdout)
        self.assertIn("READING unit objects_per_event {0: 2, 1: 2}", p.stdout)
        self.assertIn("READING unit object_kinds {'one-peak': 1, 'unsplit': 1}", p.stdout)
        self.assertIn(f"READING unit label {LABEL}", p.stdout)

    def test_a_conversion_of_another_readout_is_refused(self):
        doc = json.loads((self.d / "z.conversion.json").read_text())
        doc["cells_sha256"] = "f" * 64
        (self.d / "other.json").write_text(json.dumps(doc))
        p = self.readings(conversion=self.d / "other.json")
        self.assertEqual(p.returncode, 2, p.stdout)

    def test_a_product_without_label_is_refused(self):
        docs = [json.loads(line) for line in (self.d / "z.product.jsonl").read_text().splitlines()]
        docs[0].pop("label")
        (self.d / "bad.jsonl").write_text("\n".join(json.dumps(d) for d in docs) + "\n")
        p = self.readings(prod=self.d / "bad.jsonl")
        self.assertEqual(p.returncode, 2, p.stdout)

    def test_conservation_gate_fails_when_the_input_sum_moves(self):
        doc = json.loads((self.d / "z.conversion.json").read_text())
        doc["events"][1]["deposit_sum_mev"] += 1e-6
        (self.d / "moved.json").write_text(json.dumps(doc))
        p = self.readings(conversion=self.d / "moved.json")
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("GATE unit conservation FAIL", p.stdout)


class T08GridPathsUnchanged(unittest.TestCase):
    """Stage 1 and 2 on t08-grid/1: the formats, keys and reported fields stay as they were (byte equality with job 7554028 is
    the job's step)."""

    def test_header_document_without_label(self):
        h = product.header_document("x", 40, 40, "a" * 64, 1, "b" * 64,
                                    [{"order": 1, "step": "pedestal", "operation": "subtract", "payload_id": "c" * 64, "origin": "nominal",
                                      "round": None, "derived_against": []},
                                     {"order": 2, "step": "gain", "operation": "multiply", "role": "r", "payload_id": "d" * 64,
                                      "origin": "nominal", "round": None, "derived_against": ["c" * 64]}])
        self.assertEqual(set(h), product.HEADER_KEYS)
        self.assertEqual(h["format"], "calo-cluster-product/1")
        self.assertEqual(h["input"]["format"], "calo-cells/1")
        self.assertEqual(h["configuration"]["format"], "calo-cluster-configuration/1")

    def test_reconstruct_reports_the_same_fields(self):
        with tempfile.TemporaryDirectory() as work:
            d = Path(work)
            raw = numpy.zeros((1, 40, 40))
            raw[0, 20, 20] = 50.0
            # raw unit MeV, the identity payloads' unit: D2 stage 4 refuses an ADC readout with MeV payloads (A38)
            (d / "c.cells").write_bytes(cell_input.cells_bytes(raw, numpy.ones(raw.shape, bool), numpy.zeros(raw.shape, bool),
                                                               raw_unit=zc.RAW_UNIT))
            ped, gain = identity_payloads(1600)
            (d / "p.json").write_bytes(ped)
            (d / "g.json").write_bytes(gain)
            p = run_cli("reconstruct", "--cells", str(d / "c.cells"), "--pedestal-payload", str(d / "p.json"), "--gain-payload",
                        str(d / "g.json"), "--product", str(d / "x.jsonl"), "--product-id", "x")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(set(json.loads(p.stdout)), {"operation", "status", "reason", "exit_code", "events", "objects",
                                                         "sharing_failures", "uncertainty_failures", "energy_kind", "product",
                                                         "input_sha256", "configuration_sha256", "chain", "seconds"})
            h = product.read_product(d / "x.jsonl").header
            self.assertEqual(h["format"], "calo-cluster-product/1")
            o = product.read_product(d / "x.jsonl").events[0]["objects"][0]
            self.assertEqual((o["kind"], o["uncertainty_status"]), ("one-peak", "ok"))


class NoTruthRead(unittest.TestCase):
    def test_the_converter_names_no_truth_column(self):
        text = (ASSETS / "fixture_tools" / "t08_zdcsim_cells.py").read_text()
        self.assertEqual(zc.COLUMNS, ("cell", "zbin", "edep"))
        for column in ("E0", "x0", "y0", "xin", "yin", "eother", "nopt_gen", "nopt_det"):
            self.assertNotIn(f'"{column}"', text)
            self.assertNotIn(f"'{column}'", text)


# --- D2 stage 3 fix round 1 -----------------------------------------------------------------------------------------------

UNRESOLVED = {"status": "Unresolved (plan 1.1)",
              "decision": "user 2026-11-10: \"Carry over, Unresolved\"",
              "scope": "carried over from t08-grid/1's written constants for the zdcsim format exercise only",
              "owner": "the user",
              "exit": "a sourced ZDC prototype threshold before any physics use"}


class FixRound1Configuration(unittest.TestCase):
    """F1, F6: the user's decision on T_c and T_s, and the coordinator's no-profile rule, written where the configuration is."""

    def doc(self):
        return json.loads(PROTOTYPE_CONFIG.read_text())

    def test_thresholds_are_unresolved_with_owner_and_exit(self):
        doc = self.doc()
        self.assertEqual(doc["unresolved"], {"cell_threshold_mev": UNRESOLVED, "seed_threshold_mev": UNRESOLVED})
        self.assertIsNone(doc["sources"]["cell_threshold_mev"])
        self.assertIsNone(doc["sources"]["seed_threshold_mev"])
        self.assertEqual(configuration.load(PROTOTYPE_CONFIG).unresolved, doc["unresolved"])

    def test_source_text_states_the_decision_and_the_rule(self):
        text = self.doc()["source"]
        self.assertNotIn("for the coordinator's ruling", text)
        for phrase in ("\"Carry over, Unresolved\"", "2026-11-10", "T_c 0.6 MeV and T_s 10 MeV: Unresolved (plan 1.1)",
                       "for the zdcsim format exercise only", "owner: the user",
                       "exit: a sourced ZDC prototype threshold before any physics use",
                       "one unsplit object per component and no uncertainty", "coordinator's ruling",
                       "departure from section 7.1"):
            self.assertIn(phrase, text, phrase)

    def variant(self, edit):
        doc = self.doc()
        edit(doc)
        return json.dumps(doc).encode()

    def test_unresolved_refusals(self):
        def sourced(d):
            d["sources"]["cell_threshold_mev"] = "a source"
        for edit, text in ((sourced, "unresolved"),
                           (lambda d: d["unresolved"].update(grid=UNRESOLVED), "unresolved"),
                           (lambda d: d["unresolved"]["seed_threshold_mev"].pop("owner"), "unresolved"),
                           (lambda d: d.pop("unresolved"), "keys")):
            with self.assertRaises(configuration.ConfigurationError) as cm:
                configuration.from_bytes(self.variant(edit))
            self.assertIn(text, str(cm.exception))

    def test_version_1_has_no_unresolved_key(self):
        cfg = configuration.load()
        self.assertEqual(cfg.unresolved, {})
        self.assertNotIn("unresolved", json.loads(configuration.DEFAULT_FILE.read_text()))


class FixRound1Product(unittest.TestCase):
    def setUp(self):
        self.t = LabelledRecipe("test_product_is_labelled_with_the_inputs_provenance")
        self.t.setUp()
        assert self.t.reconstruct().returncode == 0

    def tearDown(self):
        self.t.tearDown()

    def test_product_configuration_record_carries_the_unresolved_thresholds(self):
        h = product.read_product(self.t.d / "p.jsonl").header
        self.assertEqual(h["configuration"]["unresolved"], {"cell_threshold_mev": UNRESOLVED, "seed_threshold_mev": UNRESOLVED})
        self.assertEqual(set(h["configuration"]), {"format", "sha256", "unresolved"})

    def test_product_without_the_record_is_refused(self):
        docs = [json.loads(line) for line in (self.t.d / "p.jsonl").read_text().splitlines()]
        docs[0]["configuration"].pop("unresolved")
        with self.assertRaises(product.ProductError) as cm:
            product.read_text("\n".join(product.dumps(d) for d in docs) + "\n")
        self.assertIn("configuration", str(cm.exception))


class FixRound1OldReaders(unittest.TestCase):
    def test_a_version_1_product_with_a_null_event_sum_sigma_is_refused(self):     # F3
        with tempfile.TemporaryDirectory() as work:
            d = Path(work)
            raw = numpy.zeros((1, 40, 40))
            raw[0, 20, 20] = 50.0
            # raw unit MeV, the identity payloads' unit: D2 stage 4 refuses an ADC readout with MeV payloads (A38)
            (d / "c.cells").write_bytes(cell_input.cells_bytes(raw, numpy.ones(raw.shape, bool), numpy.zeros(raw.shape, bool),
                                                               raw_unit=zc.RAW_UNIT))
            ped, gain = identity_payloads(1600)
            (d / "p.json").write_bytes(ped)
            (d / "g.json").write_bytes(gain)
            p = run_cli("reconstruct", "--cells", str(d / "c.cells"), "--pedestal-payload", str(d / "p.json"), "--gain-payload",
                        str(d / "g.json"), "--product", str(d / "x.jsonl"), "--product-id", "x")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            docs = [json.loads(line) for line in (d / "x.jsonl").read_text().splitlines()]
            self.assertEqual(docs[0]["format"], "calo-cluster-product/1")
            docs[1]["event_sum"]["sigma"] = None
            with self.assertRaises(product.ProductError) as cm:
                product.read_text("\n".join(product.dumps(x) for x in docs) + "\n")
            self.assertIn("sigma", str(cm.exception))


class FixRound1Converter(unittest.TestCase):
    def test_a_float_cell_column_is_refused(self):                                   # F4 R1
        cell, zbin, edep = ev((3, 0, 1.0))
        with self.assertRaises(zc.ConversionError) as cm:
            zc.deposits_to_cells([(cell.astype(numpy.float64), zbin, edep)], N, Z_BINS)
        self.assertIn("integers", str(cm.exception))

    def test_run_events_must_equal_the_events(self):                                   # F4 R2
        prov = provenance(2)
        prov["run"]["events"] = 3
        with self.assertRaises(cell_input.InputError) as cm:
            cell_input.check_provenance(prov, 2, "readout")
        self.assertIn("run events", str(cm.exception))

    def test_big_endian_columns_as_root_vectors_give_the_same_sums(self):              # F9: uproot reads STL vectors big-endian
        cell, zbin, edep = ev((13, 0, 1.5), (13, 1, 2.25), (8, 3, 0.125))
        raw, record = zc.deposits_to_cells([(cell.astype(">i4"), zbin.astype(">i4"), edep.astype(">f4"))], N, Z_BINS)
        self.assertEqual((raw[0, 1, 2], raw[0, 2, 1], record[0]["deposit_sum_mev"]), (3.75, 0.125, 3.875))

    def test_event_index_is_the_row_index(self):                                      # N7
        self.assertIn("event index = row index", zc.CONVERSION_RULE)

    def test_the_label_states_the_sheets_reason(self):                                # N6
        self.assertIn("that study's model passed 1 of 5 measurable gates", cell_input.LABELS[LABEL])
        self.assertIn("t07-t09-task-sheets.md", cell_input.LABELS[LABEL])

    def test_build_record_is_checked(self):                                            # F7
        with tempfile.TemporaryDirectory() as work:
            p = Path(work) / "b.json"
            good = {"format": zc.BUILD_RECORD_FORMAT, "compiler": "g++ 11.5.0", "geant4_version": "11.4.3",
                    "route": "geant4-config, reconstructed from S3's binary; the supplied CMakeLists.txt not used",
                    "command": "g++ ..."}
            p.write_text(json.dumps(good))
            rec = zc.read_build_record(p)
            self.assertEqual(rec["sha256"], hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertEqual({k: rec[k] for k in good if k != "format"}, {k: good[k] for k in good if k != "format"})
            p.write_text(json.dumps({k: v for k, v in good.items() if k != "route"}))
            with self.assertRaises(zc.ConversionError):
                zc.read_build_record(p)


class FixRound1Readings(unittest.TestCase):
    """F4 R4, R6, R7 and F1's reading line."""

    def setUp(self):
        self.r = Readings("test_gates_pass_and_only_bookkeeping_is_printed")
        self.r.setUp()

    def tearDown(self):
        self.r.tearDown()

    def test_configuration_line_names_the_unresolved_thresholds(self):
        p = self.r.readings()
        self.assertEqual(p.returncode, 0, p.stdout)
        sha = hashlib.sha256(PROTOTYPE_CONFIG.read_bytes()).hexdigest()
        self.assertIn(f"READING unit configuration sha256 {sha}; T_c, T_s Unresolved (plan 1.1), owner the user, "
                      "exit: a sourced ZDC prototype threshold before any physics use", p.stdout)

    def test_a_conversion_with_another_provenance_is_refused(self):
        doc = json.loads((self.r.d / "z.conversion.json").read_text())
        doc["provenance"]["run"]["seed"] += 1
        (self.r.d / "other-prov.json").write_text(json.dumps(doc))
        p = self.r.readings(conversion=self.r.d / "other-prov.json")
        self.assertEqual(p.returncode, 2, p.stdout)

    def evaluated(self, edit_header=None, edit_conv=None, drop_event=False):
        read = product.read_product(self.r.d / "z.product.jsonl")
        conv = zc.read_conversion(self.r.d / "z.conversion.json")
        header, events = copy.deepcopy(read.header), copy.deepcopy(read.events)
        if edit_header:
            edit_header(header)
        if edit_conv:
            edit_conv(conv)
        if drop_event:
            events = events[:-1]
        gates, _ = zc.evaluate(header, events, conv)
        return gates

    def test_gates_pass_on_the_honest_product(self):
        self.assertTrue(all(self.evaluated().values()))

    def test_label_gate(self):
        self.assertFalse(self.evaluated(edit_conv=lambda c: c.update(label="synthetic"))["label"])
        self.assertFalse(self.evaluated(edit_header=lambda h: h.update(label="synthetic"))["label"])

    def test_events_gate(self):
        self.assertFalse(self.evaluated(drop_event=True)["events"])


if __name__ == "__main__":
    unittest.main()
