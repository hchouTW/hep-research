"""B07: batch campaign configuration: site facts from the user, named refusals, placeholders only in the example."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "batch-schedulers"
sys.path.insert(0, str(ADAPTER))
import batch_config as bc  # noqa: E402

SLURM = {"backend": "slurm", "campaign_dir": "camp", "resources": {"cpus": 1, "memory_mb": 1000, "time_limit": "00:10:00"},
         "slurm": {"partition": "synthetic-partition"}}
CONDOR = {"backend": "htcondor", "campaign_dir": "camp", "resources": {"cpus": 1, "memory_mb": 1000},
          "htcondor": {"universe": "vanilla", "file_transfer": "shared-filesystem"}}


def codes(cfg, **kw):
    return sorted((e["code"], e["key"]) for e in bc.validate(cfg, **kw))


def without(cfg, *path):
    c = copy.deepcopy(cfg)
    d = c
    for k in path[:-1]:
        d = d[k]
    del d[path[-1]]
    return c


class ConfigTests(unittest.TestCase):
    def test_minimal_configs_pass(self):
        self.assertEqual(codes(SLURM), [])
        self.assertEqual(codes(CONDOR), [])

    def test_each_missing_required_key_is_named(self):
        cases = [(SLURM, ("backend",)), (SLURM, ("campaign_dir",)), (SLURM, ("resources",)), (SLURM, ("slurm",)),
                 (SLURM, ("slurm", "partition")), (SLURM, ("resources", "time_limit")),
                 (CONDOR, ("htcondor",)), (CONDOR, ("htcondor", "universe")), (CONDOR, ("htcondor", "file_transfer"))]
        for cfg, path in cases:
            with self.subTest(missing=".".join(path)):
                got = codes(without(cfg, *path))
                self.assertTrue(any(c == "config.missing_key" and k.endswith(path[-1]) for c, k in got), got)

    def test_container_universe_needs_an_image(self):
        c = copy.deepcopy(CONDOR)
        c["htcondor"]["universe"] = "container"
        self.assertIn(("config.missing_key", "htcondor.container_image"), codes(c))

    def test_unknown_keys_are_rejected(self):
        for path, key in ((("",), "partitoin"), (("resources",), "mem"), (("slurm",), "requeue")):
            c = copy.deepcopy(SLURM)
            (c if path == ("",) else c[path[0]])[key] = "x"
            with self.subTest(key=key):
                self.assertTrue(any(code == "config.unknown_key" and k.endswith(key) for code, k in codes(c)))
        c = copy.deepcopy(SLURM)
        c["htcondor"] = {}
        self.assertIn(("config.unknown_key", "htcondor"), codes(c))

    def test_zero_or_negative_resources_are_refused(self):
        for k, v in (("cpus", 0), ("memory_mb", -1), ("disk_mb", 0), ("gpus", -1), ("cpus", 1.5), ("cpus", True)):
            c = copy.deepcopy(SLURM)
            c["resources"][k] = v
            with self.subTest(key=k, value=v):
                self.assertIn(("config.bad_value", f"resources.{k}"), codes(c))
        c = copy.deepcopy(SLURM)
        c["resources"]["time_limit"] = "10 minutes"
        self.assertIn(("config.bad_value", "resources.time_limit"), codes(c))
        c = copy.deepcopy(SLURM)
        c["monitor"] = {"poll_interval_s": 5, "max_polls": 3}
        self.assertIn(("config.bad_value", "monitor.poll_interval_s"), codes(c))

    def test_example_validates_only_as_an_example(self):
        ex = json.loads((ADAPTER / "assets" / "batch-config.example.json").read_text())
        self.assertEqual(codes(ex, example=True), [])
        got = codes(ex)
        self.assertTrue(got and all(c == "config.placeholder" for c, _ in got), got)


if __name__ == "__main__":
    unittest.main()
