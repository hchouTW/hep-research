"""Geant4 program A2.1: the Geant4-free g4sim headers (adapters/geant4/assets/g4sim/SimHash.hh, SimSummary.hh)
against their Python references, through the self-test driver g4sim/selftest.cc (built here with the system C++
compiler; skipped without one, so this is the optional ctest of A2.8).

- H (SimHash.hh) equals core/simulation/seeds.py on fixed and random vectors.
- PyFloatHex equals Python's float.hex() on special values, subnormals and random bit patterns.
- SplitMix64 equals an independent Python implementation bit for bit; Box-Muller agrees to a relative 1e-12.
- SimSummary.hh equals core/simulation/summary.py on random rows with numeric and string selections: integers
  identical, floating point within a relative 1e-12; three accumulators merged equal one."""
import json
import math
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
from core.simulation import seeds, summary as S  # noqa: E402

G4SIM = PLUGIN / "adapters" / "geant4" / "assets" / "g4sim"
CXX = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")


@unittest.skipUnless(CXX, "no C++ compiler: the g4sim self-test is optional")
class G4simSelfTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = Path(cls.tmp.name) / "g4sim_selftest"
        p = subprocess.run([CXX, "-std=c++17", "-O2", "-ffp-contract=off", "-I", str(G4SIM), str(G4SIM / "selftest.cc"),
                            "-o", str(cls.exe)], capture_output=True, text=True, timeout=600)
        if p.returncode:
            raise AssertionError(p.stderr[-2000:])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def ask(self, request: dict) -> dict:
        path = Path(self.tmp.name) / "request.json"
        path.write_text(json.dumps(request))
        p = subprocess.run([str(self.exe), str(path)], capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

    def test_seed_hash_equals_core_simulation_seeds(self):
        rng = random.Random(1)
        vectors = [["j14-mpv", "nominal", "cut-0.01"], [123456, 0, 0], [123456, 0, 1], [1, 23], [12, 3], ["x"]]
        for _ in range(200):
            vectors.append([rng.choice([rng.randrange(0, 2 ** 31), f"p{rng.randrange(1000)}"])
                            for _ in range(rng.randrange(1, 5))])
        got = self.ask({"seed_hash": vectors})["seed_hash"]
        self.assertEqual(got, [seeds.H(*v) for v in vectors])

    def test_float_hex_equals_python(self):
        rng = random.Random(2)
        values = [0.0, -0.0, 1.0, -1.0, 0.1, 1e-300, 5e-324, -5e-324, 2.2250738585072009e-308, 1.7976931348623157e308,
                  math.inf, -math.inf, math.nan, 3.0, 0.3, 2.5e-9]
        patterns = [struct.unpack("<Q", struct.pack("<d", v))[0] for v in values]
        patterns += [rng.getrandbits(64) for _ in range(300)]
        got = self.ask({"float_hex": [f"{p:016x}" for p in patterns]})["float_hex"]
        for p, h in zip(patterns, got):
            x = struct.unpack("<d", struct.pack("<Q", p))[0]
            want = "nan" if math.isnan(x) else ("inf" if x == math.inf else "-inf" if x == -math.inf else x.hex())
            self.assertEqual(h, want, f"{p:016x}")

    def test_splitmix64_and_box_muller(self):
        def splitmix(seed, n):
            m, out = (1 << 64) - 1, []
            for _ in range(n):
                seed = (seed + 0x9E3779B97F4A7C15) & m
                z = seed
                z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & m
                z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & m
                out.append(z ^ (z >> 31))
            return out
        got = self.ask({"splitmix": {"seed": "1234567", "n": 50}, "box_muller": {"seed": "42", "n": 40}})
        self.assertEqual([int(x) for x in got["splitmix"]], splitmix(1234567, 50))
        u = [(z >> 11) * (1.0 / 9007199254740992.0) for z in splitmix(42, 40)]
        want = []
        for i in range(0, 40, 2):
            r = math.sqrt(-2.0 * math.log(1.0 - u[i]))
            t = 2.0 * math.pi * u[i + 1]
            want += [r * math.cos(t), r * math.sin(t)]
        for a, b in zip(got["box_muller"], want):
            self.assertAlmostEqual(a, b, delta=1e-12 * max(1.0, abs(b)))

    def test_summary_equals_core_simulation_summary(self):
        rng = random.Random(3)
        obs = [{"name": "dep", "source_column": "x", "bins": {"lo": 0.0, "hi": 1.0, "width": 0.05}, "thresholds": [0.5]},
               {"name": "trans", "source_column": "x", "bins": {"lo": 0.0, "hi": 1.0, "width": 0.1},
                "selection": [{"column": "fate", "op": "==", "value": 1},
                              {"column": "proc", "op": "==", "value": "Transportation"}]},
               {"name": "nohad", "source_column": "x", "bins": {"lo": -0.5, "hi": 1.5, "width": 0.25},
                "selection": [{"column": "proc", "op": "!contains", "value": "Inelastic"},
                              {"column": "x", "op": ">=", "value": 0.1}]}]
        rows = [{"event": 100 + i, "x": rng.uniform(-0.3, 1.3), "fate": rng.choice([0, 1, -1]),
                 "proc": rng.choice(["Transportation", "protonInelastic", "eIoni"])} for i in range(1700)]
        want = S.build(rows, obs, 100, 16, 100)
        for split in (1, 3):
            got = self.ask({"summary": {"observables": obs, "block_size": 100, "blocks": 16, "first_event": 100,
                                        "rows": rows, "split": split}})["summary"]
            with self.subTest(split=split):
                self.assertEqual(got["run"]["events_in_blocks"], want["run"]["events_in_blocks"])
                self.assertEqual(got["run"]["events_ignored"], want["run"]["events_ignored"])
                for og, ow in zip(got["observables"], want["observables"]):
                    for bg, bw in zip(og["blocks"], ow["blocks"]):
                        for k in ("block", "events", "n", "hist", "underflow", "overflow", "count_if", "min", "max"):
                            self.assertEqual(bg[k], bw[k], (og["name"], k))
                        for k in ("sum", "sumsq"):
                            self.assertAlmostEqual(bg[k], bw[k], delta=1e-12 * max(1.0, abs(bw[k])))
                from contracts.schema import validate
                self.assertTrue(validate(got, "simulation_summary.json").ok)

    def test_values_equal_core_simulation_summary(self):
        """C2.1: per-block values in event order (also when the work was split across accumulators), values_omitted
        above values_max, and the merge rule concat."""
        rng = random.Random(9)
        obs = [{"name": "v", "source_column": "x", "bins": {"lo": -1.0, "hi": 1.0, "width": 0.5}, "values": True,
                "selection": [{"column": "fate", "op": "==", "value": 1}]},
               {"name": "big", "source_column": "x", "bins": {"lo": -1.0, "hi": 1.0, "width": 0.5}, "values": True,
                "values_max": 5},
               {"name": "plain", "source_column": "x", "bins": {"lo": -1.0, "hi": 1.0, "width": 0.5}}]
        rows = [{"event": i, "x": rng.uniform(-1.2, 1.2), "fate": rng.choice([0, 1])} for i in range(160)]
        want = S.build(rows, obs, 10, 16, 0)
        for split in (1, 4):
            got = self.ask({"summary": {"observables": obs, "block_size": 10, "blocks": 16, "first_event": 0,
                                        "rows": rows, "split": split}})["summary"]
            with self.subTest(split=split):
                self.assertEqual(got["merge"], want["merge"])
                for og, ow in zip(got["observables"], want["observables"]):
                    self.assertEqual({k: og.get(k) for k in ("values_max", "values_omitted", "quantile_method")},
                                     {k: ow.get(k) for k in ("values_max", "values_omitted", "quantile_method")},
                                     og["name"])
                    self.assertEqual([b.get("values") for b in og["blocks"]], [b.get("values") for b in ow["blocks"]],
                                     og["name"])
                from contracts.schema import validate
                self.assertTrue(validate(got, "simulation_summary.json").ok)


    def test_strings_decode_like_python_json(self):
        """MiniJson decodes \\u escapes (any code point, surrogate pairs) to the same UTF-8 bytes as Python's json
        (an independent implementation); a JSON path written by json.dumps for a folder named with a space and
        Chinese characters reaches the C++ programs intact."""
        rng = random.Random(3)
        strings = ["", "plain", "a b", "hep 測試 paths/tmp", "café", "\u00e9\u0301", "€", "\U0001f600 emoji", "\x7f\x00ok",
                   "quote \" backslash \\ slash / tab \t nl \n", "\uffff", "\U0010ffff", "\ud7ff\ue000"]
        for _ in range(300):
            cps = [rng.choice([rng.randrange(0x20, 0x80), rng.randrange(0x80, 0x800), rng.randrange(0x800, 0xd800),
                               rng.randrange(0xe000, 0x10000), rng.randrange(0x10000, 0x110000)])
                   for _ in range(rng.randrange(1, 12))]
            strings.append("".join(map(chr, cps)))
        for ensure_ascii in (True, False):
            with self.subTest(ensure_ascii=ensure_ascii):
                path = Path(self.tmp.name) / "strings.json"
                path.write_text(json.dumps({"utf8_hex": strings}, ensure_ascii=ensure_ascii), encoding="utf-8")
                p = subprocess.run([str(self.exe), str(path)], capture_output=True, text=True, timeout=120)
                self.assertEqual(p.returncode, 0, p.stderr)
                got = json.loads(p.stdout)["utf8_hex"]
                self.assertEqual(got, [s.encode("utf-8").hex() for s in strings])

    def test_malformed_unicode_escapes_are_refused(self):
        """Negative control: a lone or reversed surrogate, or a \\u escape without four hex digits, is a JsonError, never
        decoded into bytes that are not UTF-8."""
        for bad in ("\\ud800", "\\udc00", "\\ud800x", "\\ud800\\u0041", "\\udc00\\ud800", "\\u12", "\\u12g4", "\\u+123"):
            with self.subTest(escape=bad):
                path = Path(self.tmp.name) / "bad.json"
                path.write_text('{"utf8_hex": ["' + bad + '"]}', encoding="utf-8")
                p = subprocess.run([str(self.exe), str(path)], capture_output=True, text=True, timeout=120)
                self.assertNotEqual(p.returncode, 0, p.stdout)
                self.assertIn("escape", p.stderr)


if __name__ == "__main__":
    unittest.main()
