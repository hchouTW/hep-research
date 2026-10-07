#!/usr/bin/env python3
"""Estimate training FLOPs, GPU-hours, wall-clock, cost, and MFU for a training run.

Purpose: size a run before launching it. A job that turns out to need three months of
cluster time is a planning failure visible from a one-line calculation, and a run whose
MFU is 15% is wasting most of the hardware it is paying for.

What it does: computes training FLOPs as 6*N*D plus the attention term 12*L*s*h*D,
converts that to GPU-hours and wall-clock at a given peak throughput and MFU, and
reports cost. Given a measured tokens/second instead, it solves for the achieved MFU.
Also reports the tokens-per-parameter ratio against the Chinchilla-style compute-optimal
value of about 20.

Usage notes / assumptions: standard library only; PyTorch is not required. The 6*N*D
rule counts one forward (2*N) and one backward (4*N) matmul FLOP per parameter per
token and excludes embeddings-only lookups, normalization, and activation functions -
it is accurate to a few percent for transformer training and is the basis of published
compute figures. The attention term matters when sequence length is comparable to
hidden size. Peak FLOPS must be quoted for the dtype actually used.
Run: python3 <plugin root>/skills/physics-ml/scripts/estimate_compute_budget.py --params 175e9 --tokens 300e9 --gpus 1024
"""

import argparse
import sys

SECONDS_PER_HOUR = 3600.0
SECONDS_PER_DAY = 86400.0
CHINCHILLA_TOKENS_PER_PARAM = 20.0


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if value != value or value in (float("inf"), float("-inf")) or value <= 0:
        raise ValueError(f"{name} must be finite and greater than zero")
    return float(value)


def training_flops(params, tokens, layers=None, seq_len=None, hidden=None):
    """C = 6*N*D + 12*L*s*h*D.

    The second term is the attention score and value matmuls, which are not
    parameterized and so are missing from the 6*N*D rule. It is negligible when
    s << h and significant when s is comparable to or larger than h.
    """
    params = _positive(params, "params")
    tokens = _positive(tokens, "tokens")
    dense = 6.0 * params * tokens
    attention = 0.0
    if None not in (layers, seq_len, hidden):
        layers = _positive(layers, "layers")
        seq_len = _positive(seq_len, "seq_len")
        hidden = _positive(hidden, "hidden")
        attention = 12.0 * layers * seq_len * hidden * tokens
    return {
        "dense_flops": dense,
        "attention_flops": attention,
        "total_flops": dense + attention,
        "attention_fraction": attention / (dense + attention) if dense + attention else 0.0,
    }


def mfu_from_throughput(tokens_per_second, params, gpus, peak_flops_per_gpu,
                        layers=None, seq_len=None, hidden=None):
    """Achieved model FLOPs utilization from a measured token throughput."""
    tokens_per_second = _positive(tokens_per_second, "tokens_per_second")
    gpus = _positive(gpus, "gpus")
    peak_flops_per_gpu = _positive(peak_flops_per_gpu, "peak_flops_per_gpu")
    per_token = training_flops(params, 1.0, layers, seq_len, hidden)["total_flops"]
    achieved = per_token * tokens_per_second
    return {
        "flops_per_token": per_token,
        "achieved_flops": achieved,
        "aggregate_peak_flops": peak_flops_per_gpu * gpus,
        "mfu": achieved / (peak_flops_per_gpu * gpus),
    }


def budget(params, tokens, gpus, peak_tflops, mfu=0.4, cost_per_gpu_hour=0.0,
           layers=None, seq_len=None, hidden=None, tokens_per_second=None):
    """Full budget for a run, either at an assumed MFU or at a measured throughput."""
    gpus = _positive(gpus, "gpus")
    peak_tflops = _positive(peak_tflops, "peak_tflops")
    peak_flops = peak_tflops * 1e12
    flops = training_flops(params, tokens, layers, seq_len, hidden)

    measured = None
    if tokens_per_second is not None:
        measured = mfu_from_throughput(tokens_per_second, params, gpus, peak_flops,
                                       layers, seq_len, hidden)
        mfu = measured["mfu"]
    if not 0.0 < mfu <= 1.0:
        raise ValueError("mfu must be in the interval (0, 1]")

    effective = peak_flops * gpus * mfu
    seconds = flops["total_flops"] / effective
    gpu_hours = seconds * gpus / SECONDS_PER_HOUR
    ratio = tokens / params

    if ratio < CHINCHILLA_TOKENS_PER_PARAM / 2:
        regime = ("undertrained for this size - a smaller model trained longer would "
                  "reach the same loss for less compute")
    elif ratio > CHINCHILLA_TOKENS_PER_PARAM * 2:
        regime = ("overtrained relative to compute-optimal - often deliberate, since "
                  "inference cost scales with parameters and not with tokens")
    else:
        regime = "near compute-optimal"

    return {
        **flops,
        "params": float(params),
        "tokens": float(tokens),
        "gpus": int(gpus),
        "peak_tflops_per_gpu": peak_tflops,
        "mfu": mfu,
        "mfu_source": "measured from throughput" if measured else "assumed",
        "measured": measured,
        "effective_flops": effective,
        "seconds": seconds,
        "hours": seconds / SECONDS_PER_HOUR,
        "days": seconds / SECONDS_PER_DAY,
        "gpu_hours": gpu_hours,
        "cost": gpu_hours * cost_per_gpu_hour,
        "tokens_per_param": ratio,
        "compute_optimal_tokens": params * CHINCHILLA_TOKENS_PER_PARAM,
        "regime": regime,
    }


def mfu_verdict(mfu):
    if mfu < 0.2:
        return ("Below 20%: most of the hardware is idle. Check the input pipeline, "
                "communication overlap, and whether recomputation is excessive.")
    if mfu < 0.3:
        return "Low but not pathological; there is usually room in the input pipeline."
    if mfu <= 0.6:
        return "Typical for a well-tuned large training run."
    return "Unusually high - verify the throughput measurement before relying on it."


def _format(result):
    lines = [
        f"Parameters:        {result['params']:.4g}",
        f"Tokens:            {result['tokens']:.4g}  "
        f"({result['tokens_per_param']:.1f} per parameter)",
        f"Compute:           {result['total_flops']:.4g} FLOPs",
    ]
    if result["attention_flops"]:
        lines.append(f"  of which attention: {result['attention_fraction'] * 100:.1f}%")
    lines += [
        "",
        f"Hardware:          {result['gpus']} GPU(s) at "
        f"{result['peak_tflops_per_gpu']:g} TFLOP/s peak",
        f"MFU:               {result['mfu'] * 100:.1f}%  ({result['mfu_source']})",
        f"Effective:         {result['effective_flops']:.4g} FLOP/s aggregate",
        "",
        f"Wall clock:        {result['hours']:.1f} h  ({result['days']:.2f} days)",
        f"GPU-hours:         {result['gpu_hours']:,.0f}",
    ]
    if result["cost"]:
        lines.append(f"Cost:              {result['cost']:,.0f}")
    lines += [
        "",
        f"Sizing:            {result['regime']}",
        f"                   compute-optimal would be about "
        f"{result['compute_optimal_tokens']:.4g} tokens",
        f"MFU:               {mfu_verdict(result['mfu'])}",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--params", type=float, required=True, help="parameter count")
    parser.add_argument("--tokens", type=float, required=True, help="training tokens")
    parser.add_argument("--gpus", type=int, default=8)
    parser.add_argument("--peak-tflops", type=float, default=989.0, dest="peak_tflops",
                        help="per-GPU peak TFLOP/s for the dtype in use (default 989)")
    parser.add_argument("--mfu", type=float, default=0.4, help="assumed MFU (default 0.4)")
    parser.add_argument("--tokens-per-second", type=float, dest="tokens_per_second",
                        help="measured throughput; overrides --mfu by solving for it")
    parser.add_argument("--cost-per-gpu-hour", type=float, default=0.0,
                        dest="cost_per_gpu_hour")
    parser.add_argument("--layers", type=int, help="for the attention FLOPs term")
    parser.add_argument("--seq-len", type=int, dest="seq_len")
    parser.add_argument("--hidden", type=int)
    args = parser.parse_args()

    try:
        result = budget(
            params=args.params, tokens=args.tokens, gpus=args.gpus,
            peak_tflops=args.peak_tflops, mfu=args.mfu,
            cost_per_gpu_hour=args.cost_per_gpu_hour, layers=args.layers,
            seq_len=args.seq_len, hidden=args.hidden,
            tokens_per_second=args.tokens_per_second)
    except ValueError as exc:
        sys.exit(f"error: {exc}")
    print(_format(result))


if __name__ == "__main__":
    main()
