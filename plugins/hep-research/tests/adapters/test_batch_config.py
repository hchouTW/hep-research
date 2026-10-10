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

    def test_example_fills_in_to_a_valid_config_for_either_backend(self):
        """Keep the chosen backend's section, delete the other one (and time_limit for HTCondor), replace each
        placeholder: the result validates. FULLTEST-E3 L08 found no htcondor section in the example."""
        ex = json.loads((ADAPTER / "assets" / "batch-config.example.json").read_text())
        site = {"backend": None, "campaign_dir": "camp", "cpus": 1, "memory_mb": 1000, "time_limit": "00:10:00", "gpus": 0,
                "partition": "synthetic-partition", "account": "synthetic-account", "qos": "synthetic-qos",
                "universe": "vanilla", "file_transfer": "transfer", "requirements": '(OpSysAndVer == "SyntheticOS")',
                "schedd": "schedd.example", "site_attributes": {"JobFlavour": "espresso", "MaxRuntime": 600},
                "throttle": 2, "max_attempts": 2, "poll_interval_s": 60, "max_polls": 10,
                "max_total_jobs": 100, "max_core_hours": 50, "max_resets_per_chunk": 1}

        def fill(obj):
            return {k: fill(v) if isinstance(v, dict) else site[k] for k, v in obj.items()}

        for backend, other in (("slurm", "htcondor"), ("htcondor", "slurm")):
            with self.subTest(backend=backend):
                self.assertIn(backend, ex, f"the example has no {backend} section")
                cfg = copy.deepcopy(ex)
                del cfg[other]
                if backend == "htcondor":
                    del cfg["resources"]["time_limit"]
                    cfg["htcondor"].pop("container_image", None)  # vanilla universe
                site["backend"] = backend
                self.assertEqual(codes(fill(cfg)), [])

    def test_htcondor_accepts_a_time_limit_for_core_hour_accounting(self):
        """T03 H3: a walltime is a site fact the user gives; with it, limits.max_core_hours works for HTCondor too."""
        c = copy.deepcopy(CONDOR)
        c["resources"]["time_limit"] = "00:20:00"
        c["limits"] = {"max_core_hours": 2}
        self.assertEqual(codes(c), [])

    def test_htcondor_site_attributes_are_a_closed_vocabulary_of_classad_values(self):
        """T03 H3: +Name = value lines (CERN: JobFlavour, MaxRuntime, WantOS) come only from the configuration."""
        c = copy.deepcopy(CONDOR)
        c["htcondor"]["site_attributes"] = {"JobFlavour": "espresso", "MaxRuntime": 1200, "WantOS": "el9", "Flag": True}
        self.assertEqual(codes(c), [])
        for name, value in (("Job Flavour", "x"), ("1st", "x"), ("JobFlavour", {"nested": 1}), ("JobFlavour", 1.5),
                            ("JobFlavour", ""), ("JobFlavour", "two\nlines"), ("JobFlavour", 'say "hi"')):
            c = copy.deepcopy(CONDOR)
            c["htcondor"]["site_attributes"] = {name: value}
            with self.subTest(name=name, value=value):
                self.assertIn(("config.bad_value", f"htcondor.site_attributes.{name}"), codes(c))
        c = copy.deepcopy(CONDOR)
        c["htcondor"]["site_attributes"] = ["JobFlavour"]
        self.assertIn(("config.bad_value", "htcondor.site_attributes"), codes(c))

    def test_htcondor_maxruntime_attribute_must_agree_with_the_time_limit(self):
        c = copy.deepcopy(CONDOR)
        c["resources"]["time_limit"] = "00:20:00"
        c["htcondor"]["site_attributes"] = {"MaxRuntime": 1200}
        self.assertEqual(codes(c), [])
        c["htcondor"]["site_attributes"] = {"MaxRuntime": 600}
        self.assertIn(("config.bad_value", "htcondor.site_attributes.MaxRuntime"), codes(c))
        c["htcondor"]["site_attributes"] = {"MaxRuntime": "1200"}
        self.assertIn(("config.bad_value", "htcondor.site_attributes.MaxRuntime"), codes(c))

    def test_htcondor_schedd_is_a_host_name_or_caller(self):
        """T03 H3: a campaign binds to one schedd; the name comes from the user or from the caller's environment."""
        for good in ("bigbird13.cern.ch", "caller"):
            c = copy.deepcopy(CONDOR)
            c["htcondor"]["schedd"] = good
            with self.subTest(schedd=good):
                self.assertEqual(codes(c), [])
        for bad in ("", "two hosts", "host;rm", 13, "a{{b}}"):
            c = copy.deepcopy(CONDOR)
            c["htcondor"]["schedd"] = bad
            with self.subTest(schedd=bad):
                self.assertIn(("config.bad_value", "htcondor.schedd"), codes(c))

    def test_cli_refuses_with_exit_2_and_names_the_keys(self):
        p = subprocess.run([sys.executable, str(ADAPTER / "batch_campaign.py"), "check-config", "--config", "/dev/stdin"],
                           input=json.dumps(without(SLURM, "slurm", "partition")), capture_output=True, text=True, timeout=600)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("slurm.partition", p.stdout)
        ex = ADAPTER / "assets" / "batch-config.example.json"
        run = lambda *a: subprocess.run([sys.executable, str(ADAPTER / "batch_campaign.py"), "check-config", "--config", str(ex), *a], capture_output=True, text=True, timeout=600)
        self.assertEqual(run("--example").returncode, 0)
        self.assertEqual(run().returncode, 2)


if __name__ == "__main__":
    unittest.main()
