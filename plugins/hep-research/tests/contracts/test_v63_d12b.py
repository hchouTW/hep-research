"""v6.3 D12b (V30): custody inventory of the profiles a project sees, companion transition stage 1 (C15). Missing
custody metadata is reported as unverified and never read as public; a profile supplied at run time (a companion's
--local folder) is known-controlled with metadata missing, kept apart from a project's own local profile of unknown
custody; existing refusals are unchanged. Profiles are synthetic stand-ins written to temporary folders (no
companion content is read)."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
from make_registry_fixtures import profile, write_profile  # noqa: E402

INCOMPATIBLE = ROOT / "contracts" / "fixtures" / "registry" / "incompatible_version" / "profiles" / "experiments" / "a"
PUBLIC = "experiment:synthetic-collider"


def setup(root: Path, bad_companion: bool = False) -> tuple[Path, Path]:
    """A project binding a public plugin profile and two local ones; a run-time folder standing in for a companion."""
    write_profile(root / "local", "own", profile("experiment:fixture-own", "experiment", "fxown"))
    write_profile(root / "local", "mirror", profile("experiment:fixture-mirror", "experiment", "fxmirror",
                                                     scope="a local copy of public material (synthetic)"))
    companion = root / "companion" / "profile"
    if bad_companion:
        shutil.copytree(INCOMPATIBLE, companion)
    else:
        write_profile(root / "companion", "profile", profile("experiment:fixture-ctl", "experiment", "fxctl"))
    pid = json.loads((companion / "profile.json").read_text())["id"]
    cfg = {"schema_version": "1.0.0", "plugin_version": ">=0.11,<1.0",
           "experiments": [{"profile": PUBLIC, "version": "1.0.0"},
                           {"profile": "experiment:fixture-own", "version": "1.0.0"},
                           {"profile": "experiment:fixture-mirror", "version": "1.0.0"},
                           {"profile": pid, "version": "1.0.0"}],
           "local_profile_paths": ["local/own", "local/mirror"]}
    (root / "hep-research.project.json").write_text(json.dumps(cfg), encoding="utf-8")
    return root, companion


class CustodyInventory(unittest.TestCase):
    def test_v30_stage1_statuses(self):
        from contracts.custody import inventory
        with tempfile.TemporaryDirectory() as td:
            proj, companion = setup(Path(td))
            inv = inventory(proj, [companion])
        rows = {r["profile"]: r for r in inv["profiles"]}
        self.assertEqual(inv["stage"], 1)
        self.assertEqual((rows[PUBLIC]["origin"], rows[PUBLIC]["custody"]), ("plugin", "public"))
        self.assertEqual((rows["experiment:fixture-own"]["origin"], rows["experiment:fixture-own"]["custody"],
                          rows["experiment:fixture-own"]["state"]), ("project-local", "unknown", "unverified"))
        # public material in a local profile without metadata is still unknown, never public
        self.assertEqual(rows["experiment:fixture-mirror"]["custody"], "unknown")
        ctl = rows["experiment:fixture-ctl"]
        self.assertEqual((ctl["origin"], ctl["custody"], ctl["state"], ctl["reason"]),
                         ("run-time-local", "controlled-metadata-missing", "unverified", "custody.metadata_missing"))
        self.assertNotIn("public", {r["custody"] for r in inv["profiles"] if r["origin"] != "plugin"})

    def test_v30_refusals_unchanged(self):
        from contracts.custody import inventory
        from contracts.project import load_project
        with tempfile.TemporaryDirectory() as td:
            proj, companion = setup(Path(td), bad_companion=True)
            before = load_project(proj, extra_local=[companion])
            inv = inventory(proj, [companion])
            after = load_project(proj, extra_local=[companion])
        pid = "experiment:fixture-exp-a"
        self.assertIn(pid, before.rejected)
        self.assertEqual(before.rejected, after.rejected)
        self.assertEqual([p["id"] for p in before.profiles], [p["id"] for p in after.profiles])
        row = next(r for r in inv["profiles"] if r["profile"] == pid)
        self.assertEqual((row["custody"], row["rejected"]), ("controlled-metadata-missing", before.rejected[pid]))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as td:
            proj, companion = setup(Path(td))
            p = subprocess.run([sys.executable, str(ROOT / "contracts" / "custody.py"), str(proj), "--local", str(companion)],
                               capture_output=True, text=True, timeout=300)
            bad = subprocess.run([sys.executable, str(ROOT / "contracts" / "custody.py"), str(Path(td) / "missing")],
                                 capture_output=True, text=True, timeout=300)
        out = json.loads(p.stdout)
        self.assertEqual((p.returncode, out["status"], out["stage"]), (0, "report", 1))
        self.assertEqual((bad.returncode, json.loads(bad.stdout)["status"]), (2, "usage"))


if __name__ == "__main__":
    unittest.main()
