"""skills/hep-computing/scripts/extract_names.py, semantic naming P3/P5 surfaces: N3 objects inside ROOT files, N4
branches and defined columns (uproot; skipped without it, spec §12), N6 batch and workflow names, and the hand-off of
a datacard's derived shape names to the N3 inventory."""
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

from tests.skills.naming_extractor_helpers import ProjectCase, load

try:
    import numpy as np
    import uproot
except ImportError:  # the N3/N4 reading tests skip without a ROOT reader (spec §12)
    uproot = None


def write_root(path, names, tree=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    edges = np.array([0.0, 1.0, 2.0])
    with uproot.recreate(path) as f:
        for n in names:
            f[n] = (np.array([1.0, 2.0]), edges)
        if tree:
            f["Events"] = {b: np.array([1.0, 2.0]) for b in tree}


@unittest.skipIf(uproot is None, "needs uproot")
class RootSurfaceTests(ProjectCase):
    SKILL = "hep-computing"

    def test_n3_objects_and_shape_histograms(self):
        write_root(self.root / "cards/shapes.root", ["ttbar", "ttbar_jesUp", "dir/qcd"])
        self.write("cards/a.txt", "shapes * * shapes.root $PROCESS $PROCESS_$SYSTEMATIC\nttbar_jesUp is a variation\n")
        code, inv = self.extract("N3")
        self.assertEqual(code, 0)
        self.assertEqual(self.entity(inv, "ttbar_jesUp")["entity_kind"], "shape_histogram")
        self.assertEqual(self.entity(inv, "ttbar")["entity_kind"], "object")
        self.assertEqual(self.entity(inv, "qcd")["scope"]["container"], "dir")
        self.assertEqual(self.entity(inv, "ttbar_jesUp")["references"], [{"from": "cards/a.txt:2", "kind": "mentions"}])
        self.assertIn("N10:**", inv["entities"][0]["search_coverage"])

    def test_n3_without_a_reader_is_unsupported(self):
        write_root(self.root / "shapes.root", ["h"])
        with mock.patch.object(self.mod, "root_reader", return_value=None):
            code, inv = self.extract("N3")
        self.assertEqual((code, inv["inputs_scanned"], len(inv["skipped_inputs"])), (3, 0, 1))

    def test_n4_branches_defines_and_external(self):
        write_root(self.root / "ntuples/official.root", [], tree=["muPt", "mu_eta"])
        self.write("ana.py", 'df = df.Define("mu_pt_corr", "muPt * 1.01").Alias("mu_pt", "muPt")\n')
        _, inv = self.extract("N4", "--external", "ntuples")
        self.assertEqual(self.entity(inv, "muPt")["source"], "external")
        self.assertEqual(set(self.names(inv)), {"muPt", "mu_eta", "mu_pt_corr", "mu_pt"})

    def test_missing_variation_found_through_the_datacard(self):
        write_root(self.root / "cards/shapes.root", ["ttbar", "ttbar_jesUp", "data_obs"])
        self.write("cards/a.txt", "imax 1\njmax 0\nkmax *\nshapes * * shapes.root $PROCESS $PROCESS_$SYSTEMATIC\n"
                                  "bin a\nobservation -1\nbin a\nprocess ttbar\nprocess 0\nrate -1\njes shape 1\n")
        self.extract("N3")
        stats = load("hep-statistics")
        with redirect_stdout(io.StringIO()):
            stats.main(["--surface", "N10", "--out", str(self.root / "naming/N10.json"), "--root", str(self.root)])
        from contracts import naming_check
        with redirect_stdout(io.StringIO()) as buf:
            code = naming_check.main(["check", "--inventory", str(self.root / "naming/N3.json"),
                                      "--inventory", str(self.root / "naming/N10.json"), "--all"])
        rep = json.loads(buf.getvalue())
        missing = {(f["rule_id"], f["current"]) for f in rep["findings"] if f["state"] == "violated"}
        self.assertIn(("naming.n10.shape-pairing", "jes"), missing)
        self.assertIn(("naming.n3.shape-pairing", "ttbar_jesUp"), missing)
        self.assertEqual(code, 1)


class N6Tests(ProjectCase):
    SKILL = "hep-computing"

    def test_jobs_logs_and_chunks(self):
        self.write("Snakefile", 'rule skim_2018:\n    log: "logs/skim.log"\n    shell: "x"\n')
        self.write("submit.sbatch", "#!/bin/bash\n#SBATCH --job-name=fit_asimov\n#SBATCH --output=logs/%A_%a.out\n")
        self.write("job.sub", "batch_name = skim_dimuon\nlog = logs/$(Cluster).log\n")
        self.write("wf.json", {"workflow": "ana", "steps": [{"id": "histogram", "needs": [], "argv": []}]})
        _, inv = self.extract("N6")
        self.assertEqual(set(self.names(inv, "job")), {"skim_2018", "fit_asimov", "skim_dimuon", "histogram"})
        self.assertEqual(set(self.names(inv, "log_pattern")), {"logs/skim.log", "logs/%A_%a.out", "logs/$(Cluster).log"})


if __name__ == "__main__":
    unittest.main()
