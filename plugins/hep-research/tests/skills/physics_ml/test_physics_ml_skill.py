"""Behavioral tests for the deep-learning diagnostic scripts.

Run from the plugin root with python3 -m unittest discover -s tests -t . -v.
Standard library only. These tests do not require PyTorch to be installed: the
diagnostic scripts (other than check_pytorch_env.py) are expected to degrade
gracefully - `--help` always works, and any real invocation without PyTorch exits
cleanly with a one-line message instead of a raw traceback. When PyTorch *is*
installed, the graceful-degradation checks are skipped rather than actually
exercising GPU/CPU training code.
"""
from __future__ import annotations

import importlib
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "skills" / "physics-ml"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    import torch as _torch_probe  # noqa: F401

    TORCH_AVAILABLE = True
except ModuleNotFoundError:
    TORCH_AVAILABLE = False

# (module name, extra CLI args needed to get past argparse before the torch check)
GUARDED_SCRIPTS = [
    ("benchmark_model", []),
    ("check_dataset_contract", []),
    ("find_nan_batches", []),
    ("inspect_checkpoint", ["nonexistent-checkpoint.pt"]),
    ("profile_dataloader", []),
]


class HelpAlwaysWorksTests(unittest.TestCase):
    """--help must succeed whether or not PyTorch is installed."""

    def test_help_exits_zero_and_shows_usage(self):
        for name, _ in GUARDED_SCRIPTS:
            with self.subTest(script=name):
                result = subprocess.run(
                    [sys.executable, str(SCRIPTS / f"{name}.py"), "--help"],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0)
                self.assertIn("usage:", result.stdout)


class HelpWithoutTorchTests(unittest.TestCase):
    def test_check_pytorch_env_help_exits_zero(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "check_pytorch_env.py"), "--help"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("usage:", result.stdout)
        self.assertNotIn("Could not import torch", result.stdout)

    def test_inspect_checkpoint_documents_unsafe_opt_in(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "inspect_checkpoint.py"), "--help"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--unsafe-full-unpickle", result.stdout)
        self.assertIn("trust", result.stdout)


class _UnpickleProbe:
    """Pickles to a call of print(); a full unpickle executes it, weights_only=True refuses it."""

    def __reduce__(self):
        return (print, ("UNPICKLE-EXECUTED",))


@unittest.skipUnless(TORCH_AVAILABLE, "PyTorch not installed")
class InspectCheckpointWeightsOnlyTests(unittest.TestCase):
    def test_weights_only_by_default_and_explicit_opt_in(self):
        import tempfile

        import torch

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ckpt.pt"
            torch.save({"w": torch.zeros(2), "probe": _UnpickleProbe()}, path)
            cmd = [sys.executable, str(SCRIPTS / "inspect_checkpoint.py"), str(path)]
            safe = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(safe.returncode, 0)
            self.assertNotIn("UNPICKLE-EXECUTED", safe.stdout)
            self.assertIn("--unsafe-full-unpickle", safe.stderr)
            self.assertNotIn("Traceback", safe.stderr)
            unsafe = subprocess.run(cmd + ["--unsafe-full-unpickle"], capture_output=True, text=True)
            self.assertEqual(unsafe.returncode, 0, unsafe.stderr)
            self.assertIn("UNPICKLE-EXECUTED", unsafe.stdout)
            plain = Path(tmp) / "plain.pt"
            torch.save({"w": torch.zeros(2)}, plain)
            ok = subprocess.run([sys.executable, str(SCRIPTS / "inspect_checkpoint.py"), str(plain)],
                                capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn("Tensor shape=(2,)", ok.stdout)


class ImportGuardStateTests(unittest.TestCase):
    """The guarded `import torch` sets consistent module-level state either way."""

    def test_torch_name_reflects_availability(self):
        for name, _ in GUARDED_SCRIPTS:
            with self.subTest(script=name):
                module = importlib.import_module(name)
                if TORCH_AVAILABLE:
                    self.assertIsNotNone(module.torch)
                    self.assertIsNone(module._TORCH_IMPORT_ERROR)
                else:
                    self.assertIsNone(module.torch)
                    self.assertIsInstance(module._TORCH_IMPORT_ERROR, ModuleNotFoundError)


@unittest.skipIf(TORCH_AVAILABLE, "only meaningful when PyTorch is not installed")
class CleanDegradationWithoutTorchTests(unittest.TestCase):
    """Without PyTorch, a real (non---help) invocation must fail cleanly, not crash."""

    def test_exits_with_clear_message_not_traceback(self):
        for name, extra_args in GUARDED_SCRIPTS:
            with self.subTest(script=name):
                result = subprocess.run(
                    [sys.executable, str(SCRIPTS / f"{name}.py"), *extra_args],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn("PyTorch is required", result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_check_pytorch_env_reports_missing_torch_cleanly(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_pytorch_env.py")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERROR: Could not import torch", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()


from check_split_integrity import (check, find_duplicates, find_group_leakage,
                                   find_overlaps, find_temporal_violations)
from compare_model_runs import (bootstrap_interval, compare, minimum_detectable_effect,
                                summarize_arm)
from estimate_compute_budget import budget, mfu_from_throughput, training_flops
from serving_capacity import (P99_CONSTANT, batching_wait_ms, plan, replica_capacity_qps,
                              replicas_for, sojourn_p99_ms)
from estimate_training_memory import (BYTES_PER_GB, activation_bytes_per_layer, advise,
                                      estimate, state_bytes_per_param,
                                      transformer_parameters)


class TransformerParameterCountTests(unittest.TestCase):
    """The 4h^2 + 2*r*h^2 per-layer count, checked against arithmetic and a real model."""

    def test_matches_closed_form(self):
        # 32 layers, hidden 4096, ffn ratio 4 -> 12 h^2 per layer, plus vocab embedding.
        expected = 32 * 12 * 4096 ** 2 + 32000 * 4096
        self.assertEqual(transformer_parameters(32, 4096, 32000, 4.0), expected)

    def test_scales_quadratically_with_hidden(self):
        small = transformer_parameters(8, 512, 0, 4.0)
        large = transformer_parameters(8, 1024, 0, 4.0)
        self.assertEqual(large, 4 * small)

    def test_scales_linearly_with_layers(self):
        self.assertEqual(transformer_parameters(16, 512, 0, 4.0),
                         2 * transformer_parameters(8, 512, 0, 4.0))

    def test_ffn_ratio_changes_only_the_mlp_half(self):
        # Attention is 4h^2; MLP is 2*r*h^2. Going r=4 -> r=8 adds 8h^2 per layer.
        base = transformer_parameters(4, 256, 0, 4.0)
        wider = transformer_parameters(4, 256, 0, 8.0)
        self.assertEqual(wider - base, 4 * 8 * 256 ** 2)

    def test_rejects_invalid_geometry(self):
        for bad in (lambda: transformer_parameters(0, 256),
                    lambda: transformer_parameters(4, 0),
                    lambda: transformer_parameters(4, 256, -1),
                    lambda: transformer_parameters(4, 256, 0, 0.0)):
            with self.assertRaises(ValueError):
                bad()


class StateBytesTests(unittest.TestCase):
    """The bytes-per-parameter table, including the claim mixed precision does not halve."""

    def test_fp32_adam_is_sixteen_bytes(self):
        self.assertEqual(sum(state_bytes_per_param("fp32", "adam")), 16)

    def test_mixed_adam_is_also_sixteen_bytes(self):
        # The point of the table in parallelism-strategy.md: fp32 master weights and
        # moments mean mixed precision saves nothing on model states.
        self.assertEqual(sum(state_bytes_per_param("mixed", "adam")), 16)

    def test_mixed_halves_only_params_and_grads(self):
        fp32_p, fp32_g, _ = state_bytes_per_param("fp32", "adam")
        mixed_p, mixed_g, _ = state_bytes_per_param("mixed", "adam")
        self.assertEqual((mixed_p, mixed_g), (fp32_p // 2, fp32_g // 2))

    def test_eight_bit_adam_saves_six_bytes(self):
        self.assertEqual(sum(state_bytes_per_param("mixed", "adam8bit")), 10)

    def test_sgd_without_momentum_has_no_optimizer_state(self):
        self.assertEqual(state_bytes_per_param("fp32", "sgd")[2], 0)

    def test_unknown_combination_raises(self):
        with self.assertRaises(ValueError):
            state_bytes_per_param("fp8", "adam")


class ActivationMemoryTests(unittest.TestCase):
    """Korthikanti et al. activation formulas and their parallelism reductions."""

    GEOMETRY = dict(seq_len=4096, micro_batch=1, hidden=4096, heads=32)

    def test_no_recompute_matches_closed_form(self):
        s, b, h, a = 4096, 1, 4096, 32
        expected = s * b * h * (34.0 + 5.0 * a * s / h)
        self.assertAlmostEqual(activation_bytes_per_layer(**self.GEOMETRY), expected, places=3)

    def test_selective_recompute_drops_the_attention_term(self):
        s, b, h = 4096, 1, 4096
        self.assertAlmostEqual(
            activation_bytes_per_layer(**self.GEOMETRY, recompute="selective"),
            s * b * h * 34.0, places=3)

    def test_full_recompute_keeps_only_the_block_input(self):
        s, b, h = 4096, 1, 4096
        self.assertAlmostEqual(
            activation_bytes_per_layer(**self.GEOMETRY, recompute="full"),
            2.0 * s * b * h, places=3)

    def test_recompute_modes_are_strictly_ordered(self):
        none = activation_bytes_per_layer(**self.GEOMETRY)
        selective = activation_bytes_per_layer(**self.GEOMETRY, recompute="selective")
        full = activation_bytes_per_layer(**self.GEOMETRY, recompute="full")
        self.assertGreater(none, selective)
        self.assertGreater(selective, full)

    def test_activations_scale_linearly_with_micro_batch(self):
        one = activation_bytes_per_layer(seq_len=1024, micro_batch=1, hidden=1024, heads=8)
        four = activation_bytes_per_layer(seq_len=1024, micro_batch=4, hidden=1024, heads=8)
        self.assertAlmostEqual(four / one, 4.0, places=9)

    def test_activations_grow_superlinearly_with_sequence_length(self):
        # The 5as/h term is quadratic in s, so doubling s more than doubles memory.
        short = activation_bytes_per_layer(seq_len=1024, micro_batch=1, hidden=1024, heads=8)
        long = activation_bytes_per_layer(seq_len=2048, micro_batch=1, hidden=1024, heads=8)
        self.assertGreater(long / short, 2.0)

    def test_sequence_parallel_shards_everything_by_tensor_degree(self):
        plain = activation_bytes_per_layer(**self.GEOMETRY)
        sharded = activation_bytes_per_layer(**self.GEOMETRY, tensor_parallel=4,
                                             sequence_parallel=True)
        self.assertAlmostEqual(plain / sharded, 4.0, places=9)

    def test_tensor_parallel_alone_leaves_an_unsharded_remainder(self):
        # Without sequence parallelism the 10-unit term stays replicated, so the
        # reduction is strictly less than the tensor-parallel degree.
        plain = activation_bytes_per_layer(**self.GEOMETRY)
        sharded = activation_bytes_per_layer(**self.GEOMETRY, tensor_parallel=4)
        self.assertLess(plain / sharded, 4.0)
        self.assertGreater(plain / sharded, 1.0)

    def test_rejects_invalid_geometry(self):
        for bad in (lambda: activation_bytes_per_layer(seq_len=0, micro_batch=1,
                                                       hidden=64, heads=8),
                    lambda: activation_bytes_per_layer(seq_len=8, micro_batch=1,
                                                       hidden=65, heads=8),
                    lambda: activation_bytes_per_layer(seq_len=8, micro_batch=1,
                                                       hidden=64, heads=8,
                                                       recompute="magic")):
            with self.assertRaises(ValueError):
                bad()


class MemoryEstimateTests(unittest.TestCase):
    """Sharding arithmetic, the fit decision, and the advice logic."""

    BASE = dict(params=7e9, gpus=8, gpu_memory_gb=80.0,
                precision="mixed", optimizer="adam")

    def test_model_states_match_bytes_per_param(self):
        result = estimate(**self.BASE)
        states = sum(v for k, v in result["per_gpu_bytes"].items() if k != "activations")
        self.assertAlmostEqual(states, 7e9 * 16, places=0)

    def test_zero_stage_one_shards_only_optimizer(self):
        plain = estimate(**self.BASE)
        zero1 = estimate(**self.BASE, zero_stage=1)
        self.assertAlmostEqual(zero1["per_gpu_bytes"]["optimizer"],
                               plain["per_gpu_bytes"]["optimizer"] / 8, places=0)
        self.assertAlmostEqual(zero1["per_gpu_bytes"]["gradients"],
                               plain["per_gpu_bytes"]["gradients"], places=0)
        self.assertAlmostEqual(zero1["per_gpu_bytes"]["parameters"],
                               plain["per_gpu_bytes"]["parameters"], places=0)

    def test_zero_stage_two_also_shards_gradients(self):
        plain = estimate(**self.BASE)
        zero2 = estimate(**self.BASE, zero_stage=2)
        self.assertAlmostEqual(zero2["per_gpu_bytes"]["gradients"],
                               plain["per_gpu_bytes"]["gradients"] / 8, places=0)
        self.assertAlmostEqual(zero2["per_gpu_bytes"]["parameters"],
                               plain["per_gpu_bytes"]["parameters"], places=0)

    def test_zero_stage_three_shards_all_three(self):
        plain = estimate(**self.BASE)
        zero3 = estimate(**self.BASE, zero_stage=3)
        for term in ("parameters", "gradients", "optimizer"):
            self.assertAlmostEqual(zero3["per_gpu_bytes"][term],
                                   plain["per_gpu_bytes"][term] / 8, places=0)

    def test_tensor_parallel_shards_weights_independently_of_zero(self):
        plain = estimate(**self.BASE)
        tp2 = estimate(**{**self.BASE, "gpus": 8}, tensor_parallel=2)
        self.assertAlmostEqual(tp2["per_gpu_bytes"]["parameters"],
                               plain["per_gpu_bytes"]["parameters"] / 2, places=0)
        self.assertEqual(tp2["data_parallel"], 4)

    def test_factorization_must_divide_world_size(self):
        with self.assertRaises(ValueError):
            estimate(**self.BASE, tensor_parallel=3)

    def test_data_parallel_is_the_quotient(self):
        result = estimate(**{**self.BASE, "gpus": 64}, tensor_parallel=4,
                          pipeline_parallel=2)
        self.assertEqual(result["data_parallel"], 8)

    def test_binding_term_and_fit_are_consistent(self):
        result = estimate(**self.BASE, zero_stage=3)
        self.assertTrue(result["fits"])
        self.assertEqual(result["binding_term"],
                         max(result["per_gpu_bytes"], key=result["per_gpu_bytes"].get))
        self.assertAlmostEqual(
            result["headroom_gb"], result["capacity_gb"] - result["total_gb"], places=6)

    def test_activations_are_omitted_without_geometry(self):
        result = estimate(**self.BASE)
        self.assertEqual(result["per_gpu_bytes"]["activations"], 0.0)
        self.assertIn("not estimated", result["activation_note"])

    def test_pipeline_holds_multiple_microbatches_in_flight(self):
        common = dict(params=7e9, gpus=8, gpu_memory_gb=80.0, layers=32, hidden=4096,
                      heads=32, seq_len=1024, micro_batch=1, recompute="selective")
        single = estimate(**common)
        piped = estimate(**common, pipeline_parallel=4, microbatches=16)
        # 1/4 the layers per stage, but up to 4 microbatches in flight: a wash.
        self.assertAlmostEqual(piped["per_gpu_bytes"]["activations"],
                               single["per_gpu_bytes"]["activations"], places=0)

    def test_advice_suggests_ddp_only_when_unsharded_would_fit(self):
        small = estimate(params=1e8, gpus=8, gpu_memory_gb=80.0, zero_stage=3)
        unsharded_small = estimate(params=1e8, gpus=8, gpu_memory_gb=80.0, zero_stage=0)
        tips = " ".join(advise(small, sum(unsharded_small["per_gpu_bytes"].values())))
        self.assertIn("plain DDP", tips)

        big = estimate(params=7e9, gpus=8, gpu_memory_gb=80.0, zero_stage=3)
        unsharded_big = estimate(params=7e9, gpus=8, gpu_memory_gb=80.0, zero_stage=0)
        tips = " ".join(advise(big, sum(unsharded_big["per_gpu_bytes"].values())))
        self.assertNotIn("plain DDP", tips)
        self.assertIn("would not fit", tips)

    def test_advice_names_the_binding_term_when_it_does_not_fit(self):
        activation_bound = estimate(params=7e9, gpus=8, gpu_memory_gb=80.0, zero_stage=3,
                                    layers=32, hidden=4096, heads=32, seq_len=8192,
                                    micro_batch=4)
        tips = " ".join(advise(activation_bound))
        self.assertIn("Activations dominate", tips)
        self.assertIn("will not help", tips)

    def test_rejects_invalid_configuration(self):
        for bad in (lambda: estimate(**{**self.BASE, "gpus": 0}),
                    lambda: estimate(**{**self.BASE, "params": 0}),
                    lambda: estimate(**{**self.BASE, "gpu_memory_gb": 0}),
                    lambda: estimate(**self.BASE, zero_stage=4)):
            with self.assertRaises(ValueError):
                bad()


class MemoryEstimateCliTests(unittest.TestCase):
    """The CLI runs without PyTorch and fails cleanly on bad input."""

    SCRIPT = str(ROOT / "scripts/estimate_training_memory.py")

    def test_runs_on_shipped_plan(self):
        result = subprocess.run(
            [sys.executable, self.SCRIPT, str(ROOT / "assets/scaling-plan.example.json"),
             "--json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertAlmostEqual(payload["parameters_total"],
                               transformer_parameters(32, 4096, 32000, 4.0), places=0)
        self.assertIn("advice", payload)

    def test_text_report_names_the_binding_term(self):
        result = subprocess.run(
            [sys.executable, self.SCRIPT, "--params", "7e9", "--gpus", "8"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Binding term:", result.stdout)

    def test_flags_override_the_plan_file(self):
        result = subprocess.run(
            [sys.executable, self.SCRIPT, str(ROOT / "assets/scaling-plan.example.json"),
             "--zero-stage", "3", "--json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["zero_stage"], 3)

    def test_bad_factorization_exits_cleanly(self):
        result = subprocess.run(
            [sys.executable, self.SCRIPT, "--params", "7e9", "--gpus", "8",
             "--tensor-parallel", "3"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("world size", result.stderr)

    def test_missing_size_information_exits_cleanly(self):
        result = subprocess.run([sys.executable, self.SCRIPT, "--gpus", "8"],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)


@unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is required to measure real allocations")
class MemoryEstimateAgainstTorchTests(unittest.TestCase):
    """Cross-check the byte model against what PyTorch actually allocates.

    Unlike the analytic tests above, this builds a real transformer, takes a real
    optimizer step, and sums the actual tensor bytes - so a wrong bytes-per-parameter
    entry or a wrong parameter-count formula fails here rather than agreeing with
    itself.
    """

    LAYERS, HIDDEN, HEADS, FFN_RATIO, VOCAB = 4, 256, 8, 4.0, 1000

    def _build(self):
        import torch
        import torch.nn as nn

        hidden, heads, ratio = self.HIDDEN, self.HEADS, self.FFN_RATIO

        class Block(nn.Module):
            def __init__(self):
                super().__init__()
                self.qkv = nn.Linear(hidden, 3 * hidden, bias=False)
                self.proj = nn.Linear(hidden, hidden, bias=False)
                self.fc1 = nn.Linear(hidden, int(ratio * hidden), bias=False)
                self.fc2 = nn.Linear(int(ratio * hidden), hidden, bias=False)

            def forward(self, x):
                query, key, value = self.qkv(x).chunk(3, -1)
                heads_view = [t.view(t.size(0), t.size(1), heads, hidden // heads)
                              .transpose(1, 2) for t in (query, key, value)]
                attended = torch.nn.functional.scaled_dot_product_attention(*heads_view)
                x = x + self.proj(attended.transpose(1, 2).reshape(x.shape))
                return x + self.fc2(torch.nn.functional.gelu(self.fc1(x)))

        class Model(nn.Module):
            def __init__(self, layers, vocab):
                super().__init__()
                self.emb = nn.Embedding(vocab, hidden)
                self.blocks = nn.ModuleList(Block() for _ in range(layers))

            def forward(self, idx):
                x = self.emb(idx)
                for block in self.blocks:
                    x = block(x)
                return x

        return Model(self.LAYERS, self.VOCAB)

    def test_parameter_count_matches_a_real_model_exactly(self):
        model = self._build()
        actual = sum(p.numel() for p in model.parameters())
        predicted = transformer_parameters(self.LAYERS, self.HIDDEN, self.VOCAB,
                                           self.FFN_RATIO)
        self.assertEqual(predicted, actual)

    def test_measured_bytes_per_parameter_match_the_table(self):
        import torch

        torch.manual_seed(0)
        model = self._build()
        optimizer = torch.optim.Adam(model.parameters())
        model(torch.randint(0, self.VOCAB, (2, 16))).sum().backward()
        optimizer.step()

        count = sum(p.numel() for p in model.parameters())
        param_bytes = sum(p.numel() * p.element_size() for p in model.parameters())
        grad_bytes = sum(p.grad.numel() * p.grad.element_size()
                         for p in model.parameters() if p.grad is not None)
        optim_bytes = sum(t.numel() * t.element_size()
                          for state in optimizer.state.values()
                          for t in state.values()
                          if torch.is_tensor(t) and t.dim() > 0)

        predicted_p, predicted_g, predicted_o = state_bytes_per_param("fp32", "adam")
        self.assertAlmostEqual(param_bytes / count, predicted_p, places=6)
        self.assertAlmostEqual(grad_bytes / count, predicted_g, places=6)
        self.assertAlmostEqual(optim_bytes / count, predicted_o, places=6)

    def test_estimated_model_state_bytes_match_measurement(self):
        import torch

        torch.manual_seed(0)
        model = self._build()
        optimizer = torch.optim.Adam(model.parameters())
        model(torch.randint(0, self.VOCAB, (2, 16))).sum().backward()
        optimizer.step()

        measured = (sum(p.numel() * p.element_size() for p in model.parameters())
                    + sum(p.grad.numel() * p.grad.element_size()
                          for p in model.parameters() if p.grad is not None)
                    + sum(t.numel() * t.element_size()
                          for state in optimizer.state.values()
                          for t in state.values()
                          if torch.is_tensor(t) and t.dim() > 0))

        result = estimate(params=sum(p.numel() for p in model.parameters()), gpus=1,
                          gpu_memory_gb=80.0, precision="fp32", optimizer="adam")
        predicted = sum(v for k, v in result["per_gpu_bytes"].items()
                        if k != "activations")
        self.assertEqual(round(predicted), measured)


class ComputeBudgetTests(unittest.TestCase):
    """The 6ND rule, the attention term, MFU inversion, and the sizing regime."""

    def test_six_n_d_matches_closed_form(self):
        self.assertAlmostEqual(training_flops(175e9, 300e9)["total_flops"],
                               6.0 * 175e9 * 300e9, places=0)

    def test_matches_the_published_gpt3_scale_figure(self):
        # GPT-3 scale (175B params, 300B tokens) is widely quoted at ~3.14e23 FLOPs.
        total = training_flops(175e9, 300e9)["total_flops"]
        self.assertAlmostEqual(total / 3.14e23, 1.0, delta=0.01)

    def test_attention_term_matches_closed_form(self):
        result = training_flops(7e9, 1e12, layers=32, seq_len=4096, hidden=4096)
        self.assertAlmostEqual(result["attention_flops"],
                               12.0 * 32 * 4096 * 4096 * 1e12, places=0)
        self.assertAlmostEqual(result["total_flops"],
                               result["dense_flops"] + result["attention_flops"], places=0)

    def test_attention_term_is_negligible_at_short_sequence(self):
        short = training_flops(7e9, 1e12, layers=32, seq_len=128, hidden=4096)
        self.assertLess(short["attention_fraction"], 0.05)

    def test_attention_term_grows_with_sequence_length(self):
        short = training_flops(7e9, 1e12, layers=32, seq_len=1024, hidden=4096)
        long = training_flops(7e9, 1e12, layers=32, seq_len=8192, hidden=4096)
        self.assertGreater(long["attention_fraction"], short["attention_fraction"])

    def test_flops_scale_linearly_in_both_factors(self):
        base = training_flops(1e9, 1e11)["total_flops"]
        self.assertAlmostEqual(training_flops(2e9, 1e11)["total_flops"], 2 * base, places=0)
        self.assertAlmostEqual(training_flops(1e9, 2e11)["total_flops"], 2 * base, places=0)

    def test_mfu_inverts_the_throughput_calculation(self):
        # Feed back exactly the throughput implied by a known MFU and recover it.
        params, gpus, peak = 7e9, 8.0, 1e15
        target_mfu = 0.42
        per_token = 6.0 * params
        tokens_per_second = target_mfu * peak * gpus / per_token
        got = mfu_from_throughput(tokens_per_second, params, gpus, peak)
        self.assertAlmostEqual(got["mfu"], target_mfu, places=12)

    def test_measured_throughput_overrides_assumed_mfu(self):
        result = budget(params=7e9, tokens=1e12, gpus=8, peak_tflops=1000.0,
                        mfu=0.9, tokens_per_second=1e5)
        self.assertEqual(result["mfu_source"], "measured from throughput")
        self.assertNotAlmostEqual(result["mfu"], 0.9, places=3)

    def test_wall_clock_and_gpu_hours_are_consistent(self):
        result = budget(params=7e9, tokens=1e12, gpus=64, peak_tflops=989.0, mfu=0.4)
        self.assertAlmostEqual(result["gpu_hours"], result["hours"] * 64, places=6)
        self.assertAlmostEqual(result["seconds"],
                               result["total_flops"] / result["effective_flops"], places=3)

    def test_halving_mfu_doubles_the_time(self):
        fast = budget(params=7e9, tokens=1e12, gpus=8, peak_tflops=989.0, mfu=0.4)
        slow = budget(params=7e9, tokens=1e12, gpus=8, peak_tflops=989.0, mfu=0.2)
        self.assertAlmostEqual(slow["hours"] / fast["hours"], 2.0, places=9)

    def test_cost_follows_gpu_hours(self):
        result = budget(params=1e9, tokens=2e10, gpus=8, peak_tflops=989.0, mfu=0.4,
                        cost_per_gpu_hour=2.5)
        self.assertAlmostEqual(result["cost"], result["gpu_hours"] * 2.5, places=6)

    def test_sizing_regimes(self):
        # GPT-3's 1.7 tokens/param is the canonical undertrained case.
        self.assertIn("undertrained",
                      budget(params=175e9, tokens=300e9, gpus=8, peak_tflops=989.0)["regime"])
        self.assertIn("near compute-optimal",
                      budget(params=1e9, tokens=20e9, gpus=8, peak_tflops=989.0)["regime"])
        self.assertIn("overtrained",
                      budget(params=1e9, tokens=1e12, gpus=8, peak_tflops=989.0)["regime"])

    def test_compute_optimal_tokens_is_twenty_per_parameter(self):
        result = budget(params=7e9, tokens=1e12, gpus=8, peak_tflops=989.0)
        self.assertAlmostEqual(result["compute_optimal_tokens"], 7e9 * 20, places=0)

    def test_rejects_invalid_input(self):
        for bad in (lambda: training_flops(0, 1e9),
                    lambda: training_flops(1e9, -1),
                    lambda: budget(params=1e9, tokens=1e9, gpus=8, peak_tflops=1, mfu=0),
                    lambda: budget(params=1e9, tokens=1e9, gpus=8, peak_tflops=1, mfu=1.5)):
            with self.assertRaises(ValueError):
                bad()

    def test_cli_runs_and_reports_sizing(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/estimate_compute_budget.py"),
             "--params", "175e9", "--tokens", "300e9", "--gpus", "1024"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("undertrained", result.stdout)

    def test_cli_rejects_bad_mfu_cleanly(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/estimate_compute_budget.py"),
             "--params", "1e9", "--tokens", "1e9", "--mfu", "2.0"],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)


class CompareModelRunsTests(unittest.TestCase):
    """Bootstrap intervals against an analytic reference, and the noise-floor logic."""

    def test_summarize_arm_matches_statistics_module(self):
        import statistics
        scores = [0.81, 0.82, 0.80, 0.83]
        summary = summarize_arm(scores)
        self.assertEqual(summary["n"], 4)
        self.assertAlmostEqual(summary["mean"], statistics.fmean(scores), places=12)
        self.assertAlmostEqual(summary["stdev"], statistics.stdev(scores), places=12)
        self.assertAlmostEqual(summary["spread"], 0.03, places=12)

    def test_bootstrap_interval_brackets_the_mean(self):
        import statistics
        samples = [0.1, 0.12, 0.09, 0.11, 0.13, 0.08, 0.10, 0.12]
        low, high = bootstrap_interval(samples, 0.95, 5000, seed=1)
        self.assertLess(low, statistics.fmean(samples))
        self.assertGreater(high, statistics.fmean(samples))

    def test_bootstrap_interval_approximates_the_analytic_interval(self):
        # For a well-behaved sample the percentile bootstrap should land close to
        # mean +/- 1.96 * stderr. This is the independent check on the resampler.
        import statistics
        samples = [1.0, 1.2, 0.9, 1.1, 1.3, 0.8, 1.05, 1.15, 0.95, 1.25,
                   1.02, 1.18, 0.92, 1.08, 1.22, 0.98, 1.12, 1.28, 0.88, 1.16]
        mean = statistics.fmean(samples)
        stderr = statistics.stdev(samples) / math.sqrt(len(samples))
        low, high = bootstrap_interval(samples, 0.95, 20000, seed=3)
        self.assertAlmostEqual(low, mean - 1.96 * stderr, delta=0.3 * stderr)
        self.assertAlmostEqual(high, mean + 1.96 * stderr, delta=0.3 * stderr)

    def test_bootstrap_is_reproducible(self):
        samples = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(bootstrap_interval(samples, seed=7, resamples=2000),
                         bootstrap_interval(samples, seed=7, resamples=2000))

    def test_bootstrap_varies_with_seed_on_a_continuous_sample(self):
        # A tiny integer sample has a coarse enough bootstrap distribution that two
        # seeds can land on identical percentile endpoints, so use a varied sample.
        samples = [0.13, 1.07, 2.91, 0.44, 3.62, 1.88, 2.05, 0.77, 3.19, 1.41,
                   2.66, 0.92, 3.88, 1.55, 2.33]
        self.assertNotEqual(bootstrap_interval(samples, seed=7, resamples=2000),
                            bootstrap_interval(samples, seed=8, resamples=2000))

    def test_wider_level_gives_wider_interval(self):
        samples = [1.0, 1.5, 0.5, 1.2, 0.8, 1.1, 0.9, 1.3]
        narrow = bootstrap_interval(samples, 0.80, 20000, seed=2)
        wide = bootstrap_interval(samples, 0.99, 20000, seed=2)
        self.assertLessEqual(wide[0], narrow[0])
        self.assertGreaterEqual(wide[1], narrow[1])

    def test_minimum_detectable_effect_matches_closed_form(self):
        self.assertAlmostEqual(minimum_detectable_effect(0.01, 50),
                               2.80 * 0.01 / math.sqrt(50), places=12)

    def test_mde_uses_t_factor_for_few_seeds(self):
        # Exact noncentral-t value (scipy.stats.nct) is 3.76 at n=5, not the normal 2.80.
        self.assertAlmostEqual(minimum_detectable_effect(0.01, 5),
                               3.76 * 0.01 / math.sqrt(5), places=12)

    def test_mde_shrinks_as_sqrt_of_n(self):
        self.assertAlmostEqual(minimum_detectable_effect(0.01, 50)
                               / minimum_detectable_effect(0.01, 200), 2.0, places=9)

    def test_identical_arms_are_not_significant(self):
        scores = [0.80, 0.81, 0.79, 0.82, 0.80]
        result = compare(scores, list(scores), resamples=4000, seed=0)
        self.assertAlmostEqual(result["mean_difference"], 0.0, places=12)
        self.assertFalse(result["interval_excludes_zero"])
        self.assertIn("Not supported", " ".join(__import__("compare_model_runs").verdict(result)))

    def test_consistent_paired_improvement_is_significant(self):
        baseline = [0.80, 0.81, 0.79, 0.82, 0.80, 0.78]
        variant = [b + 0.02 for b in baseline]
        result = compare(baseline, variant, resamples=4000, seed=0)
        self.assertAlmostEqual(result["mean_difference"], 0.02, places=12)
        self.assertTrue(result["interval_excludes_zero"])

    def test_pairing_can_beat_the_raw_spread(self):
        # The shipped asset is the instructive case: the paired difference is real
        # even though it is smaller than each arm's own seed spread.
        payload = json.loads((ROOT / "assets/eval-runs.example.json").read_text())
        result = compare(payload["baseline"], payload["variant"], resamples=8000, seed=0)
        self.assertTrue(result["paired"])
        self.assertTrue(result["interval_excludes_zero"])
        self.assertFalse(result["exceeds_noise_floor"])

    def test_lower_is_better_flips_the_sign(self):
        baseline, variant = [1.0, 1.1, 0.9], [0.8, 0.9, 0.7]
        higher = compare(baseline, variant, resamples=2000, seed=0)
        lower = compare(baseline, variant, resamples=2000, seed=0, lower_is_better=True)
        self.assertLess(higher["mean_difference"], 0)
        self.assertGreater(lower["mean_difference"], 0)

    def test_unequal_lengths_fall_back_to_unpaired(self):
        result = compare([0.8, 0.81, 0.79], [0.82, 0.83], resamples=4000, seed=0)
        self.assertFalse(result["paired"])
        self.assertIn("unpaired", " ".join(__import__("compare_model_runs").verdict(result)))

    def test_best_of_n_is_flagged_when_it_overstates(self):
        baseline = [0.80, 0.80, 0.80, 0.80]
        variant = [0.80, 0.80, 0.80, 0.90]  # one lucky seed
        result = compare(baseline, variant, resamples=4000, seed=0)
        self.assertGreater(abs(result["best_of_n_difference"]),
                           abs(result["mean_difference"]))
        self.assertIn("best-of-N",
                      " ".join(__import__("compare_model_runs").verdict(result)))

    def test_rejects_invalid_input(self):
        for bad in (lambda: compare([0.8], [0.9]),
                    lambda: compare([0.8, "x"], [0.9, 0.9]),
                    lambda: compare([0.8, 0.9], [0.9, 0.9], level=1.5),
                    lambda: compare([0.8, float("nan")], [0.9, 0.9])):
            with self.assertRaises(ValueError):
                bad()

    def test_cli_runs_on_shipped_asset(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/compare_model_runs.py"),
             str(ROOT / "assets/eval-runs.example.json"), "--json"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["paired"])


class ServingCapacityTests(unittest.TestCase):
    """Queueing arithmetic and the utilization behavior the reference describes."""

    def test_replica_capacity_matches_closed_form(self):
        self.assertAlmostEqual(replica_capacity_qps(16, 40.0), 16 / 0.040, places=9)

    def test_replicas_respect_the_utilization_ceiling(self):
        capacity = replica_capacity_qps(16, 40.0)  # 400 QPS
        self.assertEqual(replicas_for(500, capacity, 0.8), 2)
        self.assertEqual(replicas_for(320, capacity, 0.8), 1)
        self.assertEqual(replicas_for(321, capacity, 0.8), 2)

    def test_replicas_increase_monotonically_with_load(self):
        capacity = replica_capacity_qps(8, 20.0)
        counts = [replicas_for(qps, capacity, 0.8) for qps in (100, 500, 1000, 5000)]
        self.assertEqual(counts, sorted(counts))

    def test_utilization_never_exceeds_the_ceiling(self):
        for qps in (10, 250, 500, 1500, 9000):
            result = plan(qps, 16, 40.0, 1000.0, max_utilization=0.8)
            self.assertLessEqual(result["utilization"], 0.8 + 1e-12)

    def test_sojourn_p99_matches_closed_form(self):
        self.assertAlmostEqual(sojourn_p99_ms(2.5, 0.625),
                               math.log(100.0) * 2.5 / (1 - 0.625), places=12)
        self.assertAlmostEqual(P99_CONSTANT, math.log(100.0), places=15)

    def test_latency_tail_diverges_as_utilization_approaches_one(self):
        # The core claim of the reference: provisioning near 100% is a tail disaster.
        moderate = sojourn_p99_ms(2.5, 0.5)
        high = sojourn_p99_ms(2.5, 0.95)
        self.assertAlmostEqual(high / moderate, (1 - 0.5) / (1 - 0.95), places=9)
        self.assertGreater(high, 9 * moderate)
        with self.assertRaises(ValueError):
            sojourn_p99_ms(2.5, 1.0)

    def test_batching_wait_is_capped_by_the_timeout(self):
        # Sparse traffic: filling 16 at 250 QPS takes 64 ms, so the 10 ms timeout binds.
        self.assertAlmostEqual(batching_wait_ms(250.0, 16, 10.0), 10.0, places=12)
        # Dense traffic: fill time 1.6 ms, half of it is 0.8 ms, below the timeout.
        self.assertAlmostEqual(batching_wait_ms(10000.0, 16, 10.0), 0.8, places=12)

    def test_p99_is_the_sum_of_its_parts(self):
        result = plan(500, 16, 40.0, 250.0, overhead_ms=15.0)
        self.assertAlmostEqual(
            result["estimated_p99_ms"],
            result["batching_wait_ms"] + result["queue_and_service_p99_ms"]
            + result["overhead_ms"], places=9)

    def test_budget_verdict_matches_the_estimate(self):
        generous = plan(500, 16, 40.0, 250.0)
        tight = plan(500, 16, 40.0, 5.0)
        self.assertTrue(generous["meets_budget"])
        self.assertFalse(tight["meets_budget"])

    def test_advice_names_overhead_when_it_dominates(self):
        result = plan(500, 16, 40.0, 20.0, overhead_ms=500.0)
        tips = " ".join(__import__("serving_capacity").advise(result))
        self.assertIn("Fixed overhead dominates", tips)
        self.assertIn("will not help", tips)

    def test_batch_fill_depends_on_the_timeout_not_on_total_load(self):
        # Replicas scale with load to hold utilization, so per-replica arrival rate is
        # roughly pinned - raising total QPS does not make batches fill.
        sparse = plan(500, 16, 40.0, 250.0, batch_timeout_ms=10.0)
        heavy = plan(20000, 16, 40.0, 250.0, batch_timeout_ms=10.0)
        self.assertFalse(sparse["batches_fill_before_timeout"])
        self.assertFalse(heavy["batches_fill_before_timeout"])
        # Utilization is capped at 0.8, so per-replica arrivals never exceed
        # 0.8 * capacity and the fill time has an exact lower bound - regardless of
        # total load. Replica counts are integers, so lightly-loaded services sit
        # further below the ceiling and fill even more slowly.
        floor_ms = 16 / (replica_capacity_qps(16, 40.0) * 0.8) * 1000.0
        self.assertAlmostEqual(floor_ms, 50.0, places=9)
        for result in (sparse, heavy):
            self.assertGreaterEqual(result["batch_fill_time_ms"], floor_ms - 1e-9)
            self.assertLess(result["batch_fill_time_ms"], 2 * floor_ms)
        # Raising the timeout past the fill time is what makes them fill.
        generous = plan(500, 16, 40.0, 250.0, batch_timeout_ms=100.0)
        self.assertTrue(generous["batches_fill_before_timeout"])

    def test_batch_fill_time_matches_closed_form(self):
        result = plan(500, 16, 40.0, 250.0)
        self.assertAlmostEqual(result["batch_fill_time_ms"],
                               16 / result["per_replica_qps"] * 1000.0, places=9)

    def test_cost_scales_with_replicas(self):
        result = plan(500, 16, 40.0, 250.0, cost_per_replica_hour=3.2)
        self.assertAlmostEqual(result["cost_per_hour"], result["replicas"] * 3.2, places=9)

    def test_rejects_invalid_input(self):
        for bad in (lambda: replica_capacity_qps(0, 40.0),
                    lambda: replicas_for(100, 400, 1.0),
                    lambda: replicas_for(100, 400, 0.0),
                    lambda: plan(500, 16, 40.0, 0.0)):
            with self.assertRaises(ValueError):
                bad()

    def test_cli_runs(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/serving_capacity.py"),
             "--qps", "500", "--batch-size", "16", "--batch-latency-ms", "40",
             "--latency-budget-ms", "250"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Estimated p99 latency", result.stdout)


class SplitIntegrityTests(unittest.TestCase):
    """Set logic with exactly known answers on constructed inputs."""

    def test_finds_duplicates_within_a_split(self):
        self.assertEqual(find_duplicates(["a", "b", "a", "c", "b"]), ["a", "b"])
        self.assertEqual(find_duplicates(["a", "b", "c"]), [])

    def test_finds_pairwise_overlaps(self):
        splits = {"train": ["a", "b", "c"], "val": ["c", "d"], "test": ["e", "a"]}
        overlaps = find_overlaps(splits)
        self.assertEqual(overlaps["train|val"], ["c"])
        self.assertEqual(overlaps["test|train"], ["a"])
        self.assertNotIn("test|val", overlaps)

    def test_clean_splits_have_no_overlap(self):
        self.assertEqual(find_overlaps({"train": ["a", "b"], "test": ["c"]}), {})

    def test_group_leakage_is_found_when_ids_do_not_overlap(self):
        # The point of the check: distinct IDs, same underlying entity.
        splits = {"train": ["r1", "r2"], "test": ["r3"]}
        groups = {"r1": "p1", "r2": "p2", "r3": "p1"}
        self.assertEqual(find_group_leakage(splits, groups), {"p1": ["test", "train"]})

    def test_no_group_leakage_when_groups_are_disjoint(self):
        splits = {"train": ["r1", "r2"], "test": ["r3"]}
        groups = {"r1": "p1", "r2": "p1", "r3": "p2"}
        self.assertEqual(find_group_leakage(splits, groups), {})

    def test_group_check_is_skipped_without_a_mapping(self):
        self.assertEqual(find_group_leakage({"train": ["a"], "test": ["b"]}, {}), {})

    def test_temporal_violation_detected(self):
        splits = {"train": ["a", "b"], "test": ["c"]}
        timestamps = {"a": 1, "b": 10, "c": 5}
        violations = find_temporal_violations(splits, timestamps, ["train", "test"])
        self.assertIn("train|test", violations)
        self.assertEqual(violations["train|test"]["overlapping_ids"], ["b"])

    def test_no_temporal_violation_when_ordered(self):
        splits = {"train": ["a", "b"], "test": ["c"]}
        timestamps = {"a": 1, "b": 2, "c": 5}
        self.assertEqual(find_temporal_violations(splits, timestamps, ["train", "test"]), {})

    def test_shipped_asset_fails_on_group_and_temporal_checks(self):
        payload = json.loads((ROOT / "assets/dataset-splits.example.json").read_text())
        report = check(payload)
        self.assertFalse(report["passed"])
        self.assertIn("p2", report["group_leakage"])
        self.assertTrue(report["temporal_violations"])
        # But it has no plain ID overlap - the leak is invisible to a naive check.
        self.assertEqual(report["overlaps_between_splits"], {})
        self.assertEqual(report["duplicates_within_split"], {})

    def test_clean_manifest_passes(self):
        report = check({"train": ["a", "b"], "val": ["c"], "test": ["d"],
                        "groups": {"a": "g1", "b": "g1", "c": "g2", "d": "g3"},
                        "timestamps": {"a": 1, "b": 2, "c": 3, "d": 4},
                        "temporal_order": ["train", "val", "test"]})
        self.assertTrue(report["passed"])
        self.assertTrue(report["groups_checked"])
        self.assertTrue(report["timestamps_checked"])

    def test_reserved_keys_are_not_treated_as_splits(self):
        report = check({"train": ["a"], "test": ["b"], "groups": {}, "_comment": "x"})
        self.assertEqual(set(report["splits"]), {"train", "test"})

    def test_requires_at_least_two_splits(self):
        with self.assertRaises(ValueError):
            check({"train": ["a", "b"]})

    def test_cli_exits_nonzero_on_a_failing_manifest(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_split_integrity.py"),
             str(ROOT / "assets/dataset-splits.example.json")],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAILED", result.stdout)
        self.assertIn("group leakage", result.stdout)

    def test_cli_reports_bad_input_cleanly(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_split_integrity.py"),
             "does-not-exist.json"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)


class SplitGroupingCompletenessAuditT06(unittest.TestCase):
    """Audit T06: a split passes only when every sample's grouping (and, for a chronological split, timestamp)
    metadata was there to check; missing metadata and leakage are different outcomes."""

    def test_no_groups_is_incomplete_not_passed(self):
        rep = check({"train": ["a"], "test": ["b"]})
        self.assertEqual(rep["status"], "incomplete")
        self.assertFalse(rep["passed"])
        self.assertFalse(rep["groups_checked"])
        self.assertEqual(rep["group_coverage"]["missing_ids"], ["a", "b"])

    def test_partial_groups_not_checked_and_listed(self):
        rep = check({"train": ["a"], "test": ["b"], "groups": {"a": "run1"}})
        self.assertEqual(rep["status"], "incomplete")
        self.assertFalse(rep["passed"])
        self.assertFalse(rep["groups_checked"])
        self.assertEqual(rep["group_coverage"], {"covered": 1, "total": 2, "fraction": 0.5, "missing_ids": ["b"]})

    def test_strict_mode_fails_on_missing_metadata(self):
        rep = check({"train": ["a"], "test": ["b"], "groups": {"a": "run1"}}, strict=True)
        self.assertEqual((rep["status"], rep["failure_kind"]), ("failed", ["missing-metadata"]))

    def test_complete_leak_free_split_passes(self):
        rep = check({"train": ["a", "b"], "test": ["c"], "groups": {"a": "g1", "b": "g1", "c": "g2"}}, strict=True)
        self.assertEqual((rep["status"], rep["passed"], rep["groups_checked"]), ("passed", True, True))

    def test_leakage_and_missing_metadata_are_distinct(self):
        leak = check({"train": ["a"], "test": ["b"], "groups": {"a": "g1", "b": "g1"}})
        self.assertEqual((leak["status"], leak["failure_kind"]), ("failed", ["leakage"]))
        both = check({"train": ["a", "x"], "test": ["b"], "groups": {"a": "g1", "b": "g1"}})
        self.assertEqual(both["status"], "failed")
        self.assertEqual(both["failure_kind"], ["leakage", "missing-metadata"])

    def test_timestamp_coverage_reported(self):
        rep = check({"train": ["a", "b"], "test": ["c"], "groups": {"a": "g1", "b": "g2", "c": "g3"},
                     "timestamps": {"a": 1, "c": 5}, "temporal_order": ["train", "test"]})
        self.assertEqual(rep["status"], "incomplete")
        self.assertFalse(rep["timestamps_checked"])
        self.assertEqual(rep["timestamp_coverage"]["missing_ids"], ["b"])

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "s.json"
            f.write_text(json.dumps({"train": ["a"], "test": ["b"]}))
            run = lambda *a: subprocess.run([sys.executable, str(ROOT / "scripts/check_split_integrity.py"), *a, str(f)],
                                            capture_output=True, text=True)
            self.assertEqual(run().returncode, 3)
            self.assertIn("INCOMPLETE", run().stdout)
            self.assertEqual(run("--strict").returncode, 1)


@unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is required to build datasets")
class DataScriptExitCodeTests(unittest.TestCase):
    """find_nan_batches and check_dataset_contract must signal problems by exit status."""

    def _run_main(self, module_name, dataset, argv):
        import contextlib
        import io
        from unittest import mock

        module = importlib.import_module(module_name)
        out = io.StringIO()
        with mock.patch.object(module, "create_dataset", lambda: dataset), \
                mock.patch.object(sys, "argv", [module_name, *argv]), \
                contextlib.redirect_stdout(out):
            try:
                module.main()
            except SystemExit as exc:
                return exc.code, out.getvalue()
        return None, out.getvalue()

    def test_find_nan_batches_exits_nonzero_on_nan(self):
        from torch.utils.data import TensorDataset

        x = _torch_probe.randn(16, 4)
        x[3, 1] = float("nan")
        code, out = self._run_main(
            "find_nan_batches", TensorDataset(x), ["--batch-size", "8"])
        self.assertIsInstance(code, str)
        self.assertIn("non-finite", out)

    def test_find_nan_batches_exits_zero_when_clean(self):
        from torch.utils.data import TensorDataset

        code, out = self._run_main(
            "find_nan_batches", TensorDataset(_torch_probe.randn(16, 4)), ["--batch-size", "8"])
        self.assertIsNone(code)
        self.assertIn("No non-finite", out)

    def test_contract_ragged_samples_exit_with_message_not_traceback(self):
        from torch.utils.data import Dataset

        class Ragged(Dataset):
            def __len__(self):
                return 4

            def __getitem__(self, idx):
                return _torch_probe.zeros(idx + 1)

        code, _ = self._run_main("check_dataset_contract", Ragged(), ["--batch-size", "4"])
        self.assertIsInstance(code, str)
        self.assertIn("Could not collate", code)

    def test_contract_clean_dataset_exits_zero(self):
        from torch.utils.data import TensorDataset

        code, out = self._run_main(
            "check_dataset_contract", TensorDataset(_torch_probe.randn(8, 3)), ["--batch-size", "4"])
        self.assertIsNone(code)
        self.assertIn("batch", out)
