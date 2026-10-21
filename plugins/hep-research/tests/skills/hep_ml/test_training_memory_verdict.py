"""estimate_training_memory.py states its verdict (T33) and the activation inputs it assumed (T34).

T33: the estimate is a verdict. The hep-computing script contract (skills/hep-computing/SKILL.md) gives a negative
verdict exit 1 and asks for a JSON "status": a configuration that does not fit exits 1 with status failed, one that fits
exits 0 with status ok. Checked over a stated finite grid (every precision/optimizer pair the tool offers, ZeRO stages
0-3, 1 or 8 GPUs, 1e8, 7e9 and 7e10 parameters: 216 configurations), and at two anchors computed here in closed form:
mixed-precision Adam holds 2 + 2 + 12 = 16 bytes per parameter (fp16 weights and gradients, fp32 master weights and two
fp32 moments), so 7e10 parameters on one 80 GB GPU need 1043 GiB (does not fit) and 1e8 need 1.49 GiB (fits).
T34: the report and the JSON give the micro-batch size and sequence length the activation estimate used."""
import itertools
import json
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-ml" / "scripts" / "estimate_training_memory.py"
PAIRS = [("fp32", "sgd"), ("fp32", "sgd-momentum"), ("fp32", "adam"), ("mixed", "sgd"), ("mixed", "sgd-momentum"),
         ("mixed", "adam"), ("mixed", "adam8bit"), ("bf16", "adam"), ("bf16", "sgd-momentum")]
CONTRACT = {True: (0, "ok"), False: (1, "failed")}  # fits -> (exit code, status)


def run(*args):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                          timeout=600)


class TrainingMemoryVerdict(unittest.TestCase):
    def test_closed_form_anchors(self):
        gib = 1024 ** 3
        for params, fits in ((7e10, False), (1e8, True)):
            with self.subTest(params=params):
                self.assertEqual(params * 16 / gib <= 80, fits)  # the anchor's expected verdict, computed here
                p = run("--params", params, "--gpus", 1, "--gpu-memory-gb", 80, "--json")
                doc = json.loads(p.stdout)
                self.assertAlmostEqual(doc["total_gb"], params * 16 / gib, delta=1e-9 * params)
                self.assertIs(doc["fits"], fits)
                self.assertEqual((p.returncode, doc["status"]), CONTRACT[fits])

    def test_exit_code_and_status_follow_the_verdict_over_the_grid(self):
        grid = list(itertools.product(PAIRS, (0, 1, 2, 3), (1, 8), (1e8, 7e9, 7e10)))
        self.assertEqual(len(grid), 216)

        def one(cfg):
            (prec, opt), zero, gpus, params = cfg
            p = run("--params", params, "--gpus", gpus, "--zero-stage", zero, "--precision", prec, "--optimizer", opt,
                    "--json")
            doc = json.loads(p.stdout)
            return cfg, doc["fits"], p.returncode, doc.get("status")

        with ThreadPoolExecutor(8) as ex:
            rows = list(ex.map(one, grid))
        wrong = [(cfg, fits, code, status) for cfg, fits, code, status in rows if (code, status) != CONTRACT[fits]]
        self.assertEqual(wrong, [])
        self.assertTrue({fits for _, fits, _, _ in rows} == {True, False}, "the grid must hold both verdicts")

    def test_the_text_report_fails_with_exit_1(self):
        p = run("--params", 7e10, "--gpus", 1)
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertIn("Does not fit", p.stdout)

    def test_report_and_json_state_micro_batch_and_sequence_length(self):
        geometry = ["--layers", 80, "--hidden", 8192, "--heads", 64, "--seq-len", 4096, "--micro-batch", 4,
                    "--params", 7e10, "--gpus", 1]
        doc = json.loads(run(*geometry, "--json").stdout)
        self.assertEqual((doc["micro_batch"], doc["seq_len"]), (4, 4096))
        self.assertIn("micro-batch 4, sequence length 4096", run(*geometry).stdout)
        doc = json.loads(run("--params", 1e8, "--gpus", 1, "--json").stdout)
        self.assertEqual((doc["micro_batch"], doc["seq_len"]), (1, None))


if __name__ == "__main__":
    unittest.main()
