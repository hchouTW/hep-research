"""adapters/calo-cluster, D2 stage 2 of T08: the gain payload interface and the calibration-interface checks CAI-T08-1 and
CAI-T08-2 of plan R37, on hand-made events only. No fixture event and no Monte Carlo: every grid is a closed-form shower image
written here, so each expectation is fixed in the test before the recipe runs.

CAI-T08-1 (R37): with fixed cluster membership and only the gain payload changed, the cluster energy changes exactly by
sum_c f_c E_c,old (c'/c - 1) when the gain multiplies (E = c ADC) and sum_c f_c E_c,old (g/g' - 1) when it divides
(E = ADC / g), f_c the sharing fraction held fixed. The numbers below are computed here from the image and the gain ratios,
not by the recipe's modules. CAI-T08-2: with full re-reconstruction the changes and the number of membership changes are
recorded, without a numeric assertion; the tests here check only the bookkeeping (matching, counting), never a value.

Run from the plugin root: python -m unittest tests.adapters.test_calo_cai -v
"""
from __future__ import annotations

import copy
import hashlib
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

from calo_recipe import cell_chain, cell_input, clustering, configuration, gain_payload, product, recalibration  # noqa: E402
import t08_cai  # noqa: E402

N = 40
T_C, T_S, W = 0.6, 10.0, 1.0           # t04-values-v4.md section 4.2, written here from the text
FACTOR = 1.25                          # the changed gain of this stage: c' = 1.25 c (multiply), g' = 1.25 g (divide)
TOLERANCE = 1e-12                      # CAI-T08-1's numerical tolerance, relative to max(sum f |E_old|, sum f |E_new|, 1 MeV)
CFG = configuration.load()
CHANNEL_MAP_TEXT = "calo-channel-map/1\nnx 40\nny 40\nchannel = ix * ny + iy, ix in [0, nx), iy in [0, ny)\n"


# --- closed-form images, written here --------------------------------------------------------------------------------------

def phi_cdf(u):
    return 0.5 * (1.0 + math.erf(u / math.sqrt(2.0)))


def g_axis(i, c):
    return phi_cdf((i + 1 - c) / W) - phi_cdf((i - c) / W)


def image(showers, n=N):
    return numpy.array([[sum(e * g_axis(ix, x) * g_axis(iy, y) for e, x, y in showers) for iy in range(n)] for ix in range(n)])


def flat(ix, iy):
    return ix * N + iy


LONE = (2000.0, 27.6, 11.4)                              # one-peak object, core cell (27, 11)
PAIR = [(2000.0, 18.4, 20.2), (1500.0, 21.9, 20.6)]      # one component with two peaks (d about 3.5)


def pedestal_bytes(pedestal=0.0):
    return cell_input.payload_bytes("pedestal", "subtract", pedestal, N * N, "adc", "nominal", "hand-made test constant")


def nominal_gain_bytes(operation, value=1.0, ped=None, nx=N, ny=N):
    ped = pedestal_bytes() if ped is None else ped
    return gain_payload.payload_bytes(operation, value, nx, ny, "nominal", "hand-made test constant",
                                      derived_against=[hashlib.sha256(ped).hexdigest()])


def make_product(grid_events, ped_b, gain_b, product_id="hand-made"):
    """A product text, written through the recipe's own chain, clustering and writer."""
    raw = numpy.array(grid_events, dtype=float)
    cells = cell_input.read_cells(cell_input.cells_bytes(raw, numpy.ones(raw.shape, bool), numpy.zeros(raw.shape, bool)))
    ped, gain = cell_input.read_payload(ped_b), gain_payload.read_gain(gain_b)
    header = product.header_document(product_id, N, N, cells.sha256, cells.events, CFG.sha256, cell_chain.chain_record(ped, gain))
    stream = io.StringIO()
    writer = product.Writer(stream, header)
    for i in range(cells.events):
        chain = cell_chain.apply(cells.raw[i], cells.live[i], cells.saturated[i], ped, gain)
        writer.event(product.event_document(i, chain, clustering.cluster_event(chain.energy, chain.live, chain.saturated, CFG), N))
    writer.finish()
    return stream.getvalue()


# --- the gain payload ------------------------------------------------------------------------------------------------------

class ChannelMap(unittest.TestCase):
    def test_identity_is_the_grid_and_its_rule(self):
        self.assertEqual(gain_payload.channel_map_identity(N, N), hashlib.sha256(CHANNEL_MAP_TEXT.encode()).hexdigest())
        self.assertNotEqual(gain_payload.channel_map_identity(20, 80), gain_payload.channel_map_identity(N, N))
        self.assertNotEqual(gain_payload.channel_map_identity(N, 41), gain_payload.channel_map_identity(N, N))


class GainPayloadFormat(unittest.TestCase):
    def test_round_trip_both_roles(self):
        gains = [1.0 + 0.001 * c for c in range(N * N)]
        for operation, unit in (("multiply", "MeV/adc"), ("divide", "adc/MeV")):
            with self.subTest(role=operation):
                content = nominal_gain_bytes(operation, gains)
                doc = json.loads(content)
                self.assertEqual(doc["format"], "calo-gain-payload/1")
                self.assertEqual(doc["unit"], unit)
                self.assertEqual(doc["gains"][:2], [[0, 1.0], [1, 1.001]])
                read = gain_payload.read(content)
                self.assertEqual(read.identity, hashlib.sha256(content).hexdigest())
                self.assertEqual((read.step, read.operation, read.format), ("gain", operation, "calo-gain-payload/1"))
                self.assertEqual(read.channel_map, gain_payload.channel_map_identity(N, N))
                self.assertIsNone(read.derived_from)
                self.assertEqual(read.changed_channels, ())
                self.assertTrue(numpy.array_equal(read.values, numpy.array(gains)))

    def test_the_stage_1_format_is_still_read_as_before(self):
        ped = pedestal_bytes()
        old = cell_input.payload_bytes("gain", "multiply", 1.0, N * N, "MeV/adc", "nominal", "hand-made test constant",
                                       derived_against=[hashlib.sha256(ped).hexdigest()])
        read = gain_payload.read_gain(old)
        self.assertEqual((read.format, read.channel_map, read.derived_from), ("calo-calibration-payload/1", None, None))
        self.assertEqual(read.identity, cell_input.read_payload(old).identity)
        with self.assertRaisesRegex(cell_input.InputError, "not a gain payload"):
            gain_payload.read_gain(ped)

    def test_refusals(self):
        good = json.loads(nominal_gain_bytes("multiply"))

        def forged(**changes):
            doc = copy.deepcopy(good)
            for key, value in changes.items():
                if value is KeyError:
                    del doc[key]
                else:
                    doc[key] = value
            return json.dumps(doc).encode()

        gains_with = lambda edit: [list(p) for p in edit([list(p) for p in good["gains"]])]  # noqa: E731
        cases = {
            "not JSON": (b"{", "not a JSON"),
            "extra key": (forged(energy_scale=1.01), "keys"),
            "missing key": (forged(derived_from=KeyError), "keys"),
            "another format": (forged(format="calo-gain-payload/0"), "format"),
            "another step": (forged(step="pedestal"), "step"),
            "operation add": (forged(operation="add"), "multiply or divide"),
            "unit not its role's": (forged(unit="adc/MeV"), "unit"),
            "gain zero": (forged(gains=gains_with(lambda g: g[:5] + [[5, 0.0]] + g[6:])), "positive"),
            "gain negative": (forged(gains=gains_with(lambda g: g[:5] + [[5, -1.0]] + g[6:])), "positive"),
            "gain a string": (forged(gains=gains_with(lambda g: g[:5] + [[5, "1.0"]] + g[6:])), "finite"),
            "channel a bool": (forged(gains=gains_with(lambda g: [[False, 1.0]] + g[1:])), "channel"),
            "unknown channel": (forged(gains=gains_with(lambda g: g[:-1] + [[N * N, 1.0]])), "unknown channel"),
            "negative channel": (forged(gains=gains_with(lambda g: [[-1, 1.0]] + g[1:])), "unknown channel"),
            "channel twice": (forged(gains=gains_with(lambda g: g[:6] + [[5, 1.0]] + g[7:])), "ascending"),
            "missing channel": (forged(gains=gains_with(lambda g: g[:-1])), "every channel"),
            "channel map not an identity": (forged(channel_map="abc"), "channel_map"),
            "channel map of another grid": (forged(channel_map=gain_payload.channel_map_identity(20, 80)), "does not match"),
            "grid not counts": (forged(grid={"nx": 40, "ny": 0}), "grid"),
            "derived against not identities": (forged(derived_against=["x"]), "derived_against"),
            "round negative": (forged(round=-1), "round"),
            "origin other": (forged(origin="guessed"), "origin"),
            "nominal but derived": (forged(derived_from={"payload_id": "a" * 64, "changed_channels": [5]},
                                           producer={"kind": "derived", "source": "x"}), "nominal"),
            "derived without its source": (forged(origin="measured", producer={"kind": "derived", "source": "x"}), "derived_from"),
            "source without producer derived": (forged(origin="measured", derived_from={"payload_id": "a" * 64, "changed_channels": [5]}),
                                                "derived"),
            "derived from an unknown channel": (forged(origin="measured", producer={"kind": "derived", "source": "x"},
                                                       derived_from={"payload_id": "a" * 64, "changed_channels": [N * N]}), "unknown channel"),
            "derived from not an identity": (forged(origin="measured", producer={"kind": "derived", "source": "x"},
                                                    derived_from={"payload_id": "abc", "changed_channels": [5]}), "derived_from"),
            "operation a list (F3)": (forged(operation=["multiply"]), "multiply or divide"),
            "producer kind a list (F3)": (forged(producer={"kind": ["external"], "source": "s"}), "producer"),
            "a key twice (N2)": (nominal_gain_bytes("multiply").replace(b'"format": "calo-gain-payload/1",',
                                                                      b'"format": "calo-gain-payload/1",\n "format": "calo-gain-payload/1",', 1),
                                 "twice"),
        }
        for name, (content, reason) in cases.items():
            with self.subTest(defect=name), self.assertRaisesRegex(cell_input.InputError, reason):
                gain_payload.read(content)

    def test_another_channel_map_is_refused_where_it_is_applied(self):
        """A payload for a 20 x 80 grid has 1,600 channels too: well formed, but another channel map, refused against 40 x 40."""
        other = gain_payload.read(nominal_gain_bytes("multiply", nx=20, ny=80))
        with self.assertRaisesRegex(cell_input.InputError, "another channel map"):
            gain_payload.check_channel_map(other, N, N, "gain payload")
        gain_payload.check_channel_map(gain_payload.read(nominal_gain_bytes("multiply")), N, N, "gain payload")

    def test_the_chain_refuses_another_channel_map(self):
        ped_b = pedestal_bytes()
        other = gain_payload.read(nominal_gain_bytes("multiply", nx=20, ny=80, ped=ped_b))
        with self.assertRaisesRegex(cell_input.InputError, "another channel map"):
            cell_chain.apply(numpy.ones((N, N)), numpy.ones((N, N), bool), numpy.zeros((N, N), bool), cell_input.read_payload(ped_b), other)


class DerivedPayload(unittest.TestCase):
    """R32 as T07's alignment payloads: a derived payload has its own identity and records the payload it came from."""

    def test_one_channel_and_a_subset(self):
        parent_b = nominal_gain_bytes("divide")
        parent = gain_payload.read(parent_b)
        for changes in ({flat(20, 20): 1.25}, {flat(3, 3): 1.25, flat(11, 3): 0.5, flat(35, 35): 2.0}):
            with self.subTest(changed=sorted(changes)):
                child_b = gain_payload.derive(parent_b, changes, "hand-made change")
                child = gain_payload.read(child_b)
                self.assertNotEqual(child.identity, parent.identity)
                self.assertEqual(child.identity, hashlib.sha256(child_b).hexdigest())
                self.assertEqual(child.derived_from, parent.identity)
                self.assertEqual(child.changed_channels, tuple(sorted(changes)))
                self.assertEqual((child.origin, child.document["producer"]["kind"]), ("measured", "derived"))
                self.assertEqual((child.operation, child.channel_map, child.derived_against),
                                 (parent.operation, parent.channel_map, parent.derived_against))
                expected = parent.values.copy()
                for channel, value in changes.items():
                    expected[channel] = value
                self.assertTrue(numpy.array_equal(child.values, expected))
                gain_payload.check_derived(child, parent)

    def test_derive_refusals(self):
        parent_b = nominal_gain_bytes("multiply")
        for name, changes, reason in (("nothing changed", {}, "no channel"), ("unknown channel", {N * N: 1.25}, "unknown channel"),
                                      ("non-positive gain", {5: 0.0}, "positive"), ("same value", {5: 1.0}, "not a change")):
            with self.subTest(defect=name), self.assertRaisesRegex(cell_input.InputError, reason):
                gain_payload.derive(parent_b, changes, "hand-made change")

    def test_check_derived_refusals(self):
        parent_b = nominal_gain_bytes("multiply")
        parent = gain_payload.read(parent_b)
        child_b = gain_payload.derive(parent_b, {5: 1.25, 9: 1.5}, "hand-made change")
        other_parent = gain_payload.read(nominal_gain_bytes("multiply", 1.0, ped=pedestal_bytes(1.0)))
        with self.assertRaisesRegex(cell_input.InputError, "not derived from"):
            gain_payload.check_derived(gain_payload.read(child_b), other_parent)
        doc = json.loads(child_b)
        doc["derived_from"]["changed_channels"] = [5]                      # 9 changed but not listed
        with self.assertRaisesRegex(cell_input.InputError, "changed channels"):
            gain_payload.check_derived(gain_payload.read(json.dumps(doc).encode()), parent)
        doc = json.loads(child_b)
        doc["derived_from"]["changed_channels"] = [5, 9, 12]               # 12 listed but not changed
        with self.assertRaisesRegex(cell_input.InputError, "changed channels"):
            gain_payload.check_derived(gain_payload.read(json.dumps(doc).encode()), parent)
        doc = json.loads(child_b)
        doc["operation"], doc["unit"] = "divide", "adc/MeV"
        with self.assertRaisesRegex(cell_input.InputError, "role"):
            gain_payload.check_derived(gain_payload.read(json.dumps(doc).encode()), parent)
        with self.assertRaisesRegex(cell_input.InputError, "not derived from"):
            gain_payload.check_derived(parent, parent)


# --- records: the chain, the product, no overwrite -------------------------------------------------------------------------

class ProductsRecordTheGainPayload(unittest.TestCase):
    def test_chain_record_names_identity_map_and_source(self):
        ped_b = pedestal_bytes()
        ped = cell_input.read_payload(ped_b)
        nominal_b = nominal_gain_bytes("divide", ped=ped_b)
        derived_b = gain_payload.derive(nominal_b, {7: 1.25}, "hand-made change")
        for content, source in ((nominal_b, None), (derived_b, gain_payload.read(nominal_b).identity)):
            gain = gain_payload.read(content)
            step = cell_chain.chain_record(ped, gain)[1]
            self.assertEqual((step["payload_id"], step["format"], step["channel_map"], step["derived_from"], step["operation"]),
                             (gain.identity, "calo-gain-payload/1", gain_payload.channel_map_identity(N, N), source, "divide"))

    def test_the_stage_1_chain_record_is_unchanged(self):
        """Job 7552825's products must come out byte for byte: a calo-calibration-payload/1 gain adds no key."""
        ped_b = pedestal_bytes()
        old = cell_input.payload_bytes("gain", "multiply", 1.0, N * N, "MeV/adc", "nominal", "hand-made test constant",
                                       derived_against=[hashlib.sha256(ped_b).hexdigest()])
        step = cell_chain.chain_record(cell_input.read_payload(ped_b), gain_payload.read_gain(old))[1]
        self.assertEqual(set(step), {"order", "step", "operation", "role", "payload_id", "origin", "round", "derived_against"})
        text = make_product([image([LONE])], ped_b, old)
        self.assertEqual(json.loads(text.split("\n")[0])["format"], "calo-cluster-product/1")
        self.assertEqual(json.loads(text.split("\n")[-2]), {"end": "calo-cluster-product/1", "events": 1})

    def test_same_gains_in_the_new_format_give_the_same_event_lines(self):
        ped_b = pedestal_bytes()
        old = cell_input.payload_bytes("gain", "multiply", 1.0, N * N, "MeV/adc", "nominal", "hand-made test constant",
                                       derived_against=[hashlib.sha256(ped_b).hexdigest()])
        grids = [image([LONE] + PAIR), image([(800.0, 12.2, 30.7)])]
        reference = make_product(grids, ped_b, old).split("\n")
        self.assertEqual(json.loads(reference[-2])["end"], "calo-cluster-product/1")
        for operation in ("multiply", "divide"):
            with self.subTest(role=operation):
                text = make_product(grids, ped_b, nominal_gain_bytes(operation, ped=ped_b))
                lines = text.split("\n")
                self.assertEqual(lines[1:-2], reference[1:-2])            # event lines only: the end line names the format
                self.assertEqual(json.loads(lines[0])["format"], "calo-cluster-product/2")
                self.assertEqual(json.loads(lines[-2]), {"end": "calo-cluster-product/2", "events": len(grids)})
                read = product.read_text(text)
                self.assertEqual(product.product_text(read), text)

    def test_product_reader_checks_the_new_gain_step(self):
        ped_b = pedestal_bytes()
        text = make_product([image([LONE])], ped_b, nominal_gain_bytes("multiply", ped=ped_b))
        lines = text.split("\n")
        header = json.loads(lines[0])

        def with_step(**changes):
            h = copy.deepcopy(header)
            h["chain"][1].update(changes)
            return "\n".join([product.dumps(h)] + lines[1:])

        product.read_text(text)
        for name, bad in (("channel map not an identity", with_step(channel_map="abc")),
                          ("channel map of another grid", with_step(channel_map=gain_payload.channel_map_identity(20, 80))),
                          ("another payload format", with_step(format="calo-gain-payload/0")),
                          ("source not an identity", with_step(derived_from="abc")),
                          ("unknown key", with_step(scale=1.0))):
            with self.subTest(defect=name), self.assertRaises(product.ProductError):
                product.read_text(bad)
        # /1 never carries the gain payload's keys, /2 always carries all three, and the end line names the header's format
        as_v1 = copy.deepcopy(header)
        as_v1["format"] = "calo-cluster-product/1"
        v1_end = product.dumps({"end": "calo-cluster-product/1", "events": 1})
        missing = copy.deepcopy(header)
        del missing["chain"][1]["derived_from"]
        for name, bad in (("/1 with the gain payload keys", "\n".join([product.dumps(as_v1)] + lines[1:-2] + [v1_end, ""])),
                          ("/2 missing derived_from", "\n".join([product.dumps(missing)] + lines[1:])),
                          ("/2 with a /1 end line", "\n".join([lines[0]] + lines[1:-2] + [v1_end, ""]))):
            with self.subTest(defect=name), self.assertRaises(product.ProductError):
                product.read_text(bad)
        old = cell_input.payload_bytes("gain", "multiply", 1.0, N * N, "MeV/adc", "nominal", "hand-made test constant",
                                       derived_against=[hashlib.sha256(ped_b).hexdigest()])
        v1 = make_product([image([LONE])], ped_b, old).split("\n")
        h = json.loads(v1[0])
        h["format"] = "calo-cluster-product/2"
        with self.subTest(defect="/2 without the gain payload keys"), self.assertRaises(product.ProductError):
            product.read_text("\n".join([product.dumps(h)] + v1[1:-2] + [product.dumps({"end": "calo-cluster-product/2", "events": 1}), ""]))


def run_cli(*args):
    return subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "calo_cluster.py"), *args], capture_output=True, text=True, timeout=120)


def run_cai(*args):
    return subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "fixture_tools" / "t08_cai.py"), *args], capture_output=True,
                          text=True, timeout=300)


class ProductsAreNeverOverwritten(unittest.TestCase):
    def test_reconstruct_refuses_an_existing_product(self):
        raw = numpy.array([image([LONE])])
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "c.cells").write_bytes(cell_input.cells_bytes(raw, numpy.ones(raw.shape, bool), numpy.zeros(raw.shape, bool)))
            ped_b = pedestal_bytes()
            nominal_b = nominal_gain_bytes("multiply", ped=ped_b)
            (folder / "p.json").write_bytes(ped_b)
            (folder / "g.json").write_bytes(nominal_b)
            (folder / "g2.json").write_bytes(gain_payload.derive(nominal_b, {flat(27, 11): 1.25}, "hand-made change"))
            (folder / "other-map.json").write_bytes(nominal_gain_bytes("multiply", nx=20, ny=80, ped=ped_b))
            args = ["reconstruct", "--cells", str(folder / "c.cells"), "--pedestal-payload", str(folder / "p.json"),
                    "--gain-payload", str(folder / "g.json"), "--product", str(folder / "out.jsonl"), "--product-id", "hand-made"]
            p = run_cli(*args)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            before = (folder / "out.jsonl").read_bytes()
            for gain in ("g2.json", "g.json"):
                with self.subTest(second_payload=gain):
                    again = list(args)
                    again[again.index("--gain-payload") + 1] = str(folder / gain)
                    p = run_cli(*again)
                    self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                    self.assertIn("never overwritten", json.loads(p.stdout)["reason"])
                    self.assertEqual((folder / "out.jsonl").read_bytes(), before)
            bad = list(args)
            bad[bad.index("--gain-payload") + 1] = str(folder / "other-map.json")
            bad[bad.index("--product") + 1] = str(folder / "other.jsonl")
            p = run_cli(*bad)
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertIn("another channel map", json.loads(p.stdout)["reason"])
            self.assertFalse((folder / "other.jsonl").exists())


# --- CAI-T08-1: fixed membership ---------------------------------------------------------------------------------------------

class FixedMembership(unittest.TestCase):
    """The plan's formula, exactly, for both roles: one-peak objects and two-peak objects with fractions held fixed."""

    def setUp(self):
        self.grid = image([LONE] + PAIR)
        self.ped_b = pedestal_bytes()

    def setup_role(self, operation, changed):
        nominal_b = nominal_gain_bytes(operation, ped=self.ped_b)
        derived_b = gain_payload.derive(nominal_b, {c: FACTOR for c in changed}, "hand-made change")
        read = product.read_text(make_product([self.grid], self.ped_b, nominal_b))
        return read, gain_payload.read(nominal_b), gain_payload.read(derived_b)

    def lone_cells(self, read):
        """The lone shower's object, its core (peak) channel and one member with T_c <= e < 2 T_c, picked from the image."""
        event = read.events[0]
        lone = next(o for o in event["objects"] if o["kind"] == "one-peak")
        energy = {row[0]: row[5] for row in event["cells"]}
        periphery = next(c for c, _ in lone["members"] if T_C <= energy[c] < 2 * T_C)
        return lone, lone["peak_channel"], periphery, energy

    def test_one_peak_change_is_the_formula_for_both_roles(self):
        for operation, ratio_minus_one in (("multiply", FACTOR / 1.0 - 1.0), ("divide", 1.0 / FACTOR - 1.0)):
            with self.subTest(role=operation):
                probe, _, _ = self.setup_role(operation, [flat(0, 0)])
                lone, core, periphery, energy = self.lone_cells(probe)
                self.assertEqual(core, flat(27, 11))
                read, old_gain, new_gain = self.setup_role(operation, [core, periphery])
                changes = recalibration.fixed_membership(read.events[0], read.header, old_gain, new_gain)
                k = next(i for i, o in enumerate(read.events[0]["objects"]) if o["kind"] == "one-peak")
                change = changes[k]
                expected = (energy[core] + energy[periphery]) * ratio_minus_one        # f = 1 in a one-peak object
                scale = max(lone["energy"], 1.0)
                self.assertLessEqual(abs(change.change - expected), TOLERANCE * scale)
                self.assertLessEqual(abs(change.formula - expected), TOLERANCE * scale)
                self.assertEqual(change.changed_members, 2)
                self.assertGreater(abs(change.change), 10.0)                       # a real change, about 0.25 or 0.2 of 290 MeV

    def test_two_peak_change_is_the_formula_with_fractions_held_fixed(self):
        for operation, ratio_minus_one in (("multiply", FACTOR - 1.0), ("divide", 1.0 / FACTOR - 1.0)):
            with self.subTest(role=operation):
                read, old_gain, new_gain = self.setup_role(operation, [flat(19, 19), flat(19, 20), flat(21, 20)])
                event = read.events[0]
                energy = {row[0]: row[5] for row in event["cells"]}
                changes = recalibration.fixed_membership(event, read.header, old_gain, new_gain)
                two = [k for k, o in enumerate(event["objects"]) if o["kind"] == "two-peak"]
                self.assertEqual(len(two), 2)
                for k in two:
                    members = dict(event["objects"][k]["members"])
                    expected = math.fsum(members[c] * energy[c] * ratio_minus_one for c in (flat(19, 19), flat(19, 20), flat(21, 20)))
                    self.assertLessEqual(abs(changes[k].change - expected), TOLERANCE * max(event["objects"][k]["energy"], 1.0))
                    self.assertEqual(changes[k].changed_members, 3)

    def test_an_object_with_no_changed_member_does_not_move(self):
        read, old_gain, new_gain = self.setup_role("multiply", [flat(19, 19)])
        changes = recalibration.fixed_membership(read.events[0], read.header, old_gain, new_gain)
        k = next(i for i, o in enumerate(read.events[0]["objects"]) if o["kind"] == "one-peak")
        self.assertEqual(changes[k].changed_members, 0)
        self.assertEqual(changes[k].formula, 0.0)
        self.assertLessEqual(abs(changes[k].change), TOLERANCE * read.events[0]["objects"][k]["energy"])

    def test_one_peak_fixed_membership_is_the_recipes_own_path(self):
        """Core cell only, gain up: no cell crosses T_c, so a full re-clustering keeps the membership and gives the same change."""
        read, old_gain, new_gain = self.setup_role("multiply", [flat(27, 11)])
        k = next(i for i, o in enumerate(read.events[0]["objects"]) if o["kind"] == "one-peak")
        change = recalibration.fixed_membership(read.events[0], read.header, old_gain, new_gain)[k]
        grid = self.grid.copy()
        grid[27, 11] *= FACTOR
        again = clustering.cluster_event(grid, numpy.ones((N, N), bool), numpy.zeros((N, N), bool), CFG)
        lone = next(o for o in again.objects if o.kind == "one-peak")
        self.assertEqual([c for c, _ in lone.members], [c for c, _ in read.events[0]["objects"][k]["members"]])
        self.assertLessEqual(abs((lone.energy - read.events[0]["objects"][k]["energy"]) - change.change), TOLERANCE * lone.energy)

    def test_the_assessment_passes_on_an_honest_event(self):
        for operation in ("multiply", "divide"):
            with self.subTest(role=operation):
                read, old_gain, new_gain = self.setup_role(operation, [flat(27, 11), flat(19, 19), flat(21, 20)])
                outcome = t08_cai.assess(read, old_gain, new_gain, CFG, "hand-made", min_asserted=1)
                self.assertTrue(outcome.passed, "\n".join(outcome.lines))
                self.assertIn("CAI-T08-1 hand-made RESULT PASS", outcome.lines)
                self.assertEqual(outcome.asserted, 3)

    def test_non_unit_per_channel_gains_both_roles(self):
        """F1: c_ch = 0.8 + 0.0005 ch (or g_ch), a pedestal of 2 ADC, derived x 1.25: the formula's ratio uses the old gain."""
        ped_b = pedestal_bytes(2.0)
        raw = self.grid + 2.0
        gains = [0.8 + 0.0005 * c for c in range(N * N)]
        changed = [flat(27, 11), flat(19, 19), flat(19, 20), flat(21, 20)]
        for operation, ratio_minus_one in (("multiply", 0.25), ("divide", 1.0 / 1.25 - 1.0)):
            with self.subTest(role=operation):
                nominal_b = nominal_gain_bytes(operation, gains, ped=ped_b)
                derived_b = gain_payload.derive(nominal_b, {c: gains[c] * FACTOR for c in changed}, "hand-made change")
                old_gain, new_gain = gain_payload.read(nominal_b), gain_payload.read(derived_b)
                read = product.read_text(make_product([raw], ped_b, nominal_b))
                event = read.events[0]
                rows = {row[0]: row for row in event["cells"]}
                self.assertNotEqual(rows[flat(27, 11)][3], rows[flat(27, 11)][5])     # after the pedestal differs from E
                changes = recalibration.fixed_membership(event, read.header, old_gain, new_gain)
                kinds = set()
                for k, cluster in enumerate(event["objects"]):
                    members = dict(cluster["members"])
                    e_new = {c: (rows[c][3] * gains[c] * FACTOR if operation == "multiply" else rows[c][3] / (gains[c] * FACTOR))
                             if c in changed else rows[c][5] for c in members}
                    expected = math.fsum(members[c] * rows[c][5] * ratio_minus_one for c in members if c in changed)
                    direct = math.fsum(members[c] * e_new[c] for c in members) - cluster["energy"]
                    scale = max(cluster["energy"], 1.0)
                    self.assertLessEqual(abs(changes[k].formula - expected), TOLERANCE * scale)
                    self.assertLessEqual(abs(changes[k].change - direct), TOLERANCE * scale)
                    self.assertLessEqual(abs(changes[k].change - expected), TOLERANCE * scale)
                    self.assertGreater(abs(expected), 1.0)
                    kinds.add(cluster["kind"])
                self.assertEqual(kinds, {"one-peak", "two-peak"})
                outcome = t08_cai.assess(read, old_gain, new_gain, CFG, "hand-made", min_asserted=3)
                self.assertTrue(outcome.passed, "\n".join(outcome.lines))
                self.assertFalse(t08_cai.assess(read, old_gain, new_gain, CFG, "hand-made", min_asserted=3, plant=True).passed)

    def test_reshare_skips_are_counted(self):
        """N4: two-peak components the re-sharing could not redo are counted beside the re-shared line."""
        read, old_gain, new_gain = self.setup_role("multiply", [flat(19, 19)])
        outcome = t08_cai.assess(read, old_gain, new_gain, CFG, "hand-made", min_asserted=1)
        line = next(l for l in outcome.lines if "two-peak re-shared" in l)
        self.assertIn("components skipped 0", line)

    def test_too_few_asserted_objects_fail(self):
        """The run must assert at least --min-asserted objects with a changed member (100 in the job): fewer is no check."""
        read, old_gain, new_gain = self.setup_role("multiply", [flat(27, 11), flat(19, 19), flat(21, 20)])
        self.assertTrue(t08_cai.assess(read, old_gain, new_gain, CFG, "hand-made", min_asserted=3).passed)
        outcome = t08_cai.assess(read, old_gain, new_gain, CFG, "hand-made", min_asserted=4)
        self.assertFalse(outcome.passed)
        self.assertIn("CAI-T08-1 hand-made RESULT FAIL", outcome.lines)

    def test_a_planted_change_in_a_fraction_fails_the_exact_assertion(self):
        for operation in ("multiply", "divide"):
            for where in ("changed member", "unchanged member"):
                with self.subTest(role=operation, planted=where):
                    read, old_gain, new_gain = self.setup_role(operation, [flat(19, 19), flat(21, 20)])
                    event = read.events[0]
                    k = next(i for i, o in enumerate(event["objects"]) if o["kind"] == "two-peak")
                    members = event["objects"][k]["members"]
                    i = next(j for j, (c, _) in enumerate(members) if (c in (flat(19, 19), flat(21, 20))) == (where == "changed member"))
                    members[i][1] += 1e-6
                    outcome = t08_cai.assess(read, old_gain, new_gain, CFG, "hand-made", min_asserted=1)
                    self.assertFalse(outcome.passed)
                    self.assertIn("CAI-T08-1 hand-made RESULT FAIL", outcome.lines)
                    read, old_gain, new_gain = self.setup_role(operation, [flat(19, 19), flat(21, 20)])
                    self.assertTrue(t08_cai.assess(read, old_gain, new_gain, CFG, "hand-made", min_asserted=1, plant=False).passed)
                    self.assertFalse(t08_cai.assess(read, old_gain, new_gain, CFG, "hand-made", min_asserted=1, plant=True).passed)

    def test_reshared_two_peak_change_is_recorded_not_the_formula(self):
        """The recipe's own two-peak path re-derives the fractions from the new e_c (R37: recorded without an exact assertion)."""
        read, old_gain, new_gain = self.setup_role("multiply", [flat(19, 19), flat(19, 20)])
        event = read.events[0]
        fixed = recalibration.fixed_membership(event, read.header, old_gain, new_gain)
        reshared = recalibration.reshare(event, read.header, old_gain, new_gain, CFG)
        two = [k for k, o in enumerate(event["objects"]) if o["kind"] == "two-peak"]
        self.assertEqual(sorted(reshared), two)
        grid = self.grid.copy()
        grid[19, 19] *= FACTOR
        grid[19, 20] *= FACTOR
        again = clustering.cluster_event(grid, numpy.ones((N, N), bool), numpy.zeros((N, N), bool), CFG)
        again_two = [o for o in again.objects if o.kind == "two-peak"]
        for k, o in zip(two, again_two):
            self.assertLessEqual(abs(reshared[k] - o.energy), 1e-9 * o.energy)        # same cells, same peaks: the recipe's path
            self.assertGreater(abs((reshared[k] - event["objects"][k]["energy"]) - fixed[k].formula), 1e-9 * o.energy)

    def test_well_above_threshold_rule(self):
        """Fixed before the run: a changed member is well above threshold when min(E_old, E_new) >= 2 T_c."""
        self.assertTrue(t08_cai.well_above(1.2, CFG))
        self.assertFalse(t08_cai.well_above(1.19, CFG))
        self.assertTrue(t08_cai.well_above(None, CFG))              # no changed member
        read, old_gain, new_gain = self.setup_role("divide", [flat(27, 11)])
        _, core, periphery, energy = self.lone_cells(read)
        read, old_gain, new_gain = self.setup_role("divide", [core, periphery])
        k = next(i for i, o in enumerate(read.events[0]["objects"]) if o["kind"] == "one-peak")
        change = recalibration.fixed_membership(read.events[0], read.header, old_gain, new_gain)[k]
        self.assertEqual(change.lowest_changed, energy[periphery] / FACTOR)
        outcome = t08_cai.assess(read, old_gain, new_gain, CFG, "hand-made", min_asserted=0)
        self.assertEqual(outcome.recorded, 1)            # the lone object: its periphery falls below 2 T_c
        self.assertTrue(outcome.passed)

    def test_no_nonlinear_cell_step_after_the_gain(self):
        """The chain ends with the gain; a clipped cell (the readout clips before the gain) follows the formula too."""
        self.assertEqual(cell_chain.CHAIN_ORDER[-1], "gain")
        nominal_b = nominal_gain_bytes("multiply", ped=self.ped_b)
        derived_b = gain_payload.derive(nominal_b, {flat(27, 11): FACTOR}, "hand-made change")
        raw = numpy.array([numpy.minimum(self.grid, 200.0)])
        sat = numpy.array([self.grid > 200.0])
        cells = cell_input.read_cells(cell_input.cells_bytes(raw, numpy.ones(raw.shape, bool), sat))
        ped, gain = cell_input.read_payload(self.ped_b), gain_payload.read(nominal_b)
        header = product.header_document("clipped", N, N, cells.sha256, 1, CFG.sha256, cell_chain.chain_record(ped, gain))
        chain = cell_chain.apply(cells.raw[0], cells.live[0], cells.saturated[0], ped, gain)
        event = json.loads(product.dumps(product.event_document(0, chain, clustering.cluster_event(chain.energy, chain.live, chain.saturated, CFG), N)))
        k = next(i for i, o in enumerate(event["objects"]) if flat(27, 11) in dict(o["members"]))   # a plateau of clipped cells
        self.assertEqual(event["objects"][k]["kind"], "one-peak")
        self.assertEqual(event["cells"][[row[0] for row in event["cells"]].index(flat(27, 11))][5], 200.0)
        self.assertTrue(event["objects"][k]["saturated"])
        change = recalibration.fixed_membership(event, header, gain, gain_payload.read(derived_b))[k]
        self.assertLessEqual(abs(change.change - 200.0 * (FACTOR - 1.0)), TOLERANCE * event["objects"][k]["energy"])

    def test_refuses_payloads_the_product_did_not_consume(self):
        read, old_gain, new_gain = self.setup_role("multiply", [flat(27, 11)])
        other_ped = pedestal_bytes(1.0)
        cases = {
            "another old payload": (gain_payload.read(nominal_gain_bytes("multiply", 1.0 + 1e-9)), new_gain, "did not consume"),
            "a role change": (old_gain, gain_payload.read(gain_payload.derive(nominal_gain_bytes("divide", ped=self.ped_b), {5: 2.0}, "x")),
                              "role"),
            "another pedestal": (old_gain, gain_payload.read(gain_payload.derive(nominal_gain_bytes("multiply", ped=other_ped), {5: 2.0}, "x")),
                                 "pedestal"),
            "another channel map": (old_gain, gain_payload.read(gain_payload.derive(nominal_gain_bytes("multiply", nx=20, ny=80, ped=self.ped_b),
                                                                               {5: 2.0}, "x")), "channel map"),
        }
        for name, (case_old, case_new, reason) in cases.items():
            with self.subTest(refused=name), self.assertRaisesRegex(cell_input.InputError, reason):
                recalibration.fixed_membership(read.events[0], read.header, case_old, case_new)
        event = copy.deepcopy(read.events[0])
        event["cells"][0][4] = 2.0           # a cell row whose gain is not the old payload's
        with self.assertRaisesRegex(cell_input.InputError, "not the gain payload"):
            recalibration.fixed_membership(event, read.header, old_gain, new_gain)


# --- CAI-T08-2: full re-reconstruction, bookkeeping only ----------------------------------------------------------------------

class ReReconstruction(unittest.TestCase):
    def make_object(self, peak, members, energy=100.0):
        return {"peak_channel": peak, "members": [[c, f] for c, f in members], "energy": energy}

    def test_counterparts_and_membership_changes(self):
        nominal = {"objects": [self.make_object(10, [(9, 1.0), (10, 1.0), (11, 1.0)]), self.make_object(50, [(49, 0.5), (50, 0.6)]),
                               self.make_object(90, [(90, 1.0)])]}
        changed = {"objects": [self.make_object(10, [(10, 1.0), (11, 1.0), (12, 1.0), (13, 1.0)]), self.make_object(51, [(49, 0.5), (50, 0.4), (51, 1.0)]),
                               self.make_object(200, [(200, 1.0)])]}
        matches = t08_cai.match_objects(nominal, changed)
        self.assertEqual(matches, [(0, 0, "peak"), (1, 1, "overlap"), (2, None, "none")])
        self.assertEqual(t08_cai.appeared(matches, changed), [2])
        self.assertEqual(t08_cai.membership_changes(nominal["objects"][0]["members"], changed["objects"][0]["members"]), 3)
        self.assertEqual(t08_cai.membership_changes(nominal["objects"][1]["members"], changed["objects"][1]["members"]), 1)

    def test_gap_of_unchanged_one_peak_objects_is_its_own_reading(self):
        """F2: under re-reconstruction a one-peak object whose membership is unchanged follows the formula to rounding; the
        reading is printed by kind, relative to the scale, and is not an assertion (R37)."""
        ped_b = pedestal_bytes()
        nominal_b = nominal_gain_bytes("multiply", ped=ped_b)
        derived_b = gain_payload.derive(nominal_b, {flat(27, 11): FACTOR}, "hand-made change")
        grids = [image([LONE] + PAIR)]
        nominal = product.read_text(make_product(grids, ped_b, nominal_b))
        changed = product.read_text(make_product(grids, ped_b, derived_b))
        lines, _ = t08_cai.rereco(nominal, changed, gain_payload.read(nominal_b), gain_payload.read(derived_b), CFG, "hand-made")
        line = next(l for l in lines if "change minus the fixed-membership formula" in l)
        self.assertRegex(line, r"one-peak, membership unchanged n 1 largest [0-9.e+-]+ of the scale")
        value = float(line.split("one-peak, membership unchanged n 1 largest ")[1].split(" ")[0])
        self.assertLessEqual(value, TOLERANCE)
        self.assertIn("two-peak, membership unchanged n 2", line)
        old = cell_input.payload_bytes("gain", "multiply", 1.0, N * N, "MeV/adc", "nominal", "hand-made test constant",
                                       derived_against=[hashlib.sha256(ped_b).hexdigest()])
        stage1 = product.read_text(make_product(grids, ped_b, old))
        with self.assertRaisesRegex(t08_cai.Refused, "formats"):
            t08_cai.rereco(nominal, stage1, gain_payload.read(nominal_b), gain_payload.read(derived_b), CFG, "hand-made")

    def test_changed_channels_are_the_fixed_lattice(self):
        channels = t08_cai.changed_channels(N, N)
        self.assertEqual(len(channels), 25)
        self.assertEqual(channels[:3], [flat(3, 3), flat(3, 11), flat(3, 19)])
        self.assertTrue(all((c // N) % 8 == 3 and (c % N) % 8 == 3 for c in channels))


# --- the CAI tool, end to end on hand-made events ----------------------------------------------------------------------------

class CaiToolEndToEnd(unittest.TestCase):
    """The job's path: harness-written payloads, reconstruct under the nominal and the derived payload, CAI-T08-1 and -2."""

    def test_both_roles(self):
        grids = [image([(2000.0, 19.4, 19.6)]), image([(2000.0, 10.6, 26.8), (1500.0, 13.9, 27.3)]), image([(900.0, 27.5, 11.5)])]
        raw = numpy.array(grids)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            cells = folder / "s.cells"
            cells.write_bytes(cell_input.cells_bytes(raw, numpy.ones(raw.shape, bool), numpy.zeros(raw.shape, bool)))
            (folder / "s.pedestal.json").write_bytes(pedestal_bytes())
            p = run_cai("payloads", "--cells", str(cells), "--pedestal-payload", str(folder / "s.pedestal.json"), "--out-dir", str(folder),
                        "--stem", "s")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            written = json.loads(p.stdout)["files"]
            self.assertEqual(set(written), {"nominal-multiply", "nominal-divide", "derived-multiply", "derived-divide", "other-map",
                                            "unknown-channel"})
            for operation in ("multiply", "divide"):
                with self.subTest(role=operation):
                    products = {}
                    for kind in ("nominal", "derived"):
                        out = folder / f"{kind}-{operation}.jsonl"
                        p = run_cli("reconstruct", "--cells", str(cells), "--pedestal-payload", str(folder / "s.pedestal.json"),
                                    "--gain-payload", written[f"{kind}-{operation}"]["path"], "--product", str(out), "--product-id", out.stem)
                        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                        products[kind] = out
                    record = folder / f"cai1-{operation}.jsonl"
                    p = run_cai("fixed-membership", "--product", str(products["nominal"]), "--old-gain", written[f"nominal-{operation}"]["path"],
                                "--new-gain", written[f"derived-{operation}"]["path"], "--out", str(record), "--label", operation,
                                "--min-asserted", "1")
                    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                    self.assertIn(f"CAI-T08-1 {operation} RESULT PASS", p.stdout)
                    header = json.loads(record.read_text().split("\n")[0])
                    self.assertEqual((header["old_gain"]["payload_id"], header["new_gain"]["payload_id"]),
                                     (written[f"nominal-{operation}"]["sha256"], written[f"derived-{operation}"]["sha256"]))
                    self.assertEqual(header["product"]["format"], "calo-cluster-product/2")
                    p = run_cai("fixed-membership", "--product", str(products["nominal"]), "--old-gain", written[f"nominal-{operation}"]["path"],
                                "--new-gain", written[f"derived-{operation}"]["path"], "--out", str(folder / f"plant-{operation}.jsonl"),
                                "--label", operation, "--min-asserted", "1", "--plant-fraction-defect")
                    self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
                    self.assertIn(f"CAI-T08-1 {operation} RESULT FAIL", p.stdout)
                    p = run_cai("fixed-membership", "--product", str(products["nominal"]), "--old-gain", written[f"nominal-{operation}"]["path"],
                                "--new-gain", written[f"derived-{operation}"]["path"], "--out", str(record), "--label", operation)
                    self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                    self.assertIn("never overwritten", p.stdout)
                    p = run_cai("rereco", "--nominal", str(products["nominal"]), "--changed", str(products["derived"]),
                                "--old-gain", written[f"nominal-{operation}"]["path"], "--new-gain", written[f"derived-{operation}"]["path"],
                                "--out", str(folder / f"cai2-{operation}.jsonl"), "--label", operation)
                    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                    self.assertIn(f"CAI-T08-2 {operation} membership changes per object", p.stdout)
                    header2 = json.loads((folder / f"cai2-{operation}.jsonl").read_text().split("\n")[0])
                    self.assertEqual((header2["nominal"]["format"], header2["changed"]["format"]),
                                     ("calo-cluster-product/2", "calo-cluster-product/2"))
                    p = run_cai("rereco", "--nominal", str(products["derived"]), "--changed", str(products["nominal"]),
                                "--old-gain", written[f"nominal-{operation}"]["path"], "--new-gain", written[f"derived-{operation}"]["path"],
                                "--out", str(folder / f"swapped-{operation}.jsonl"), "--label", operation)
                    self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            p = run_cai("rereco", "--nominal", str(folder / "nominal-multiply.jsonl"), "--changed", str(folder / "nominal-multiply.jsonl"),
                        "--old-gain", written["nominal-multiply"]["path"], "--new-gain", written["derived-multiply"]["path"],
                        "--out", str(folder / "same.jsonl"), "--label", "same")
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)           # the changed product did not consume the new payload
            before = Path(written["derived-divide"]["path"]).read_bytes()
            p = run_cai("payloads", "--cells", str(cells), "--pedestal-payload", str(folder / "s.pedestal.json"), "--out-dir", str(folder),
                        "--stem", "s")
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertIn("never overwritten", p.stdout)
            self.assertEqual(Path(written["derived-divide"]["path"]).read_bytes(), before)
            existing = folder / "existing.jsonl"
            existing.write_bytes(b"x\n")
            with self.assertRaisesRegex(t08_cai.Refused, "never overwritten"):
                t08_cai.write_new(existing, b"y\n")
            self.assertEqual(existing.read_bytes(), b"x\n")
            with self.assertRaisesRegex(cell_input.InputError, "unknown channel"):
                gain_payload.read(Path(written["unknown-channel"]["path"]).read_bytes())
            gain_payload.read(Path(written["other-map"]["path"]).read_bytes())


if __name__ == "__main__":
    unittest.main()
