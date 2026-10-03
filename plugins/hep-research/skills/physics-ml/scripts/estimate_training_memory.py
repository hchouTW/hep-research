#!/usr/bin/env python3
"""Estimate per-GPU training memory and identify which term is binding.

Purpose: decide a parallelism strategy from numbers rather than by trial and error.
Sharding weights does not help a run that is activation-bound, and mixed precision does
not halve training memory - both mistakes are cheap to avoid with an estimate.

What it does: computes the four per-GPU memory terms (parameters, gradients, optimizer
states, activations) for a transformer-shaped model under a given precision, optimizer,
recomputation mode, and TP x PP x DP factorization with an optional ZeRO/FSDP stage.
Reports the total, the headroom against a GPU's capacity, which term dominates, and
what to change. Parameter count is derived from the model geometry or supplied directly.

Usage notes / assumptions: standard library only; PyTorch is not required. Activation
formulas follow Korthikanti et al. (arXiv:2205.05198) and assume 2-byte activations and
a standard pre-norm transformer block; they are estimates, not allocator accounting, and
exclude fragmentation, communication buffers, and the CUDA context (add roughly 1-2 GB).
Pipeline activation memory is the 1F1B worst case, held by the first stage.
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/scripts/estimate_training_memory.py ${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/assets/scaling-plan.example.json
     python3 ${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/scripts/estimate_training_memory.py --params 7e9 --gpus 8 --zero-stage 3
"""

import argparse
import json
import sys

BYTES_PER_GB = 1024 ** 3

# (parameter bytes, gradient bytes, optimizer bytes) per parameter.
# "mixed" keeps fp32 master weights, which is why it does not halve training memory.
STATE_BYTES = {
    ("fp32", "sgd"): (4, 4, 0),
    ("fp32", "sgd-momentum"): (4, 4, 4),
    ("fp32", "adam"): (4, 4, 8),
    ("mixed", "sgd"): (2, 2, 4),
    ("mixed", "sgd-momentum"): (2, 2, 8),
    ("mixed", "adam"): (2, 2, 12),
    ("mixed", "adam8bit"): (2, 2, 6),
    ("bf16", "adam"): (2, 2, 8),
    ("bf16", "sgd-momentum"): (2, 2, 4),
}

RECOMPUTE_MODES = ("none", "selective", "full")
ACTIVATION_BYTES = 2


def state_bytes_per_param(precision, optimizer):
    key = (precision, optimizer)
    if key not in STATE_BYTES:
        raise ValueError(
            f"unsupported precision/optimizer combination {precision!r}/{optimizer!r}; "
            f"available: {sorted('/'.join(k) for k in STATE_BYTES)}"
        )
    return STATE_BYTES[key]


def transformer_parameters(layers, hidden, vocab_size=0, ffn_ratio=4.0):
    """Parameter count for a standard transformer.

    Per layer: 4h^2 for attention projections plus 2*r*h^2 for the MLP.
    Plus a vocab_size x hidden embedding. Norm and bias terms are O(h) and ignored.
    """
    for value, name in ((layers, "layers"), (hidden, "hidden")):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if ffn_ratio <= 0:
        raise ValueError("ffn_ratio must be greater than zero")
    if vocab_size < 0:
        raise ValueError("vocab_size must be nonnegative")
    per_layer = 4 * hidden * hidden + 2 * ffn_ratio * hidden * hidden
    return int(layers * per_layer + vocab_size * hidden)


def activation_bytes_per_layer(seq_len, micro_batch, hidden, heads,
                               tensor_parallel=1, sequence_parallel=False,
                               recompute="none"):
    """Activation bytes for one transformer layer (Korthikanti et al., arXiv:2205.05198).

    none      : s*b*h*(34 + 5*a*s/h)          (tensor parallel: 10 + 24/t + 5as/(ht))
    selective : s*b*h*34                       (attention softmax/dropout recomputed)
    full      : 2*s*b*h                        (only the block input is stored)
    Sequence parallelism divides the otherwise-unsharded 10 and 24 terms by t as well.
    """
    if recompute not in RECOMPUTE_MODES:
        raise ValueError(f"recompute must be one of {RECOMPUTE_MODES}")
    for value, name in ((seq_len, "seq_len"), (micro_batch, "micro_batch"),
                        (hidden, "hidden"), (heads, "heads"),
                        (tensor_parallel, "tensor_parallel")):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if hidden % heads != 0:
        raise ValueError("hidden must be divisible by heads")

    base = seq_len * micro_batch * hidden
    attention_term = 5.0 * heads * seq_len / hidden

    if recompute == "full":
        # Only the block input is retained, and sequence parallelism shards it.
        return base * ACTIVATION_BYTES / (tensor_parallel if sequence_parallel else 1)

    if sequence_parallel:
        sharded = 34.0 + (0.0 if recompute == "selective" else attention_term)
        return base * sharded / tensor_parallel

    unsharded = 10.0 + 24.0 / tensor_parallel
    if recompute == "selective":
        return base * unsharded if tensor_parallel > 1 else base * 34.0
    if tensor_parallel > 1:
        return base * (unsharded + attention_term / tensor_parallel)
    return base * (34.0 + attention_term)


def estimate(params, gpus, gpu_memory_gb, precision="mixed", optimizer="adam",
             zero_stage=0, tensor_parallel=1, pipeline_parallel=1,
             sequence_parallel=False, recompute="none",
             layers=None, hidden=None, heads=None, seq_len=None, micro_batch=1,
             microbatches=None):
    """Per-GPU memory breakdown for one training configuration."""
    if not isinstance(gpus, int) or isinstance(gpus, bool) or gpus <= 0:
        raise ValueError("gpus must be a positive integer")
    if zero_stage not in (0, 1, 2, 3):
        raise ValueError("zero_stage must be 0, 1, 2 or 3")
    if params <= 0:
        raise ValueError("params must be greater than zero")
    if gpu_memory_gb <= 0:
        raise ValueError("gpu_memory_gb must be greater than zero")

    model_parallel = tensor_parallel * pipeline_parallel
    if gpus % model_parallel != 0:
        raise ValueError(
            f"tensor_parallel x pipeline_parallel = {model_parallel} does not divide "
            f"gpus = {gpus}; TP x PP x DP must equal world size")
    data_parallel = gpus // model_parallel

    param_b, grad_b, optim_b = state_bytes_per_param(precision, optimizer)
    # TP and PP shard the weights themselves; ZeRO shards across the data-parallel group.
    param_shard = model_parallel * (data_parallel if zero_stage >= 3 else 1)
    grad_shard = model_parallel * (data_parallel if zero_stage >= 2 else 1)
    optim_shard = model_parallel * (data_parallel if zero_stage >= 1 else 1)

    parameter_bytes = params * param_b / param_shard
    gradient_bytes = params * grad_b / grad_shard
    optimizer_bytes = params * optim_b / optim_shard

    activation_total = 0.0
    activation_note = "not estimated (model geometry not supplied)"
    if None not in (layers, hidden, heads, seq_len):
        per_layer = activation_bytes_per_layer(
            seq_len, micro_batch, hidden, heads, tensor_parallel,
            sequence_parallel, recompute)
        layers_per_stage = layers / pipeline_parallel
        # 1F1B keeps up to `pipeline_parallel` microbatches in flight on stage 0.
        in_flight = 1
        if pipeline_parallel > 1:
            in_flight = min(pipeline_parallel, microbatches or pipeline_parallel)
        activation_total = per_layer * layers_per_stage * in_flight
        activation_note = (f"{recompute} recomputation, {layers_per_stage:g} layers/stage, "
                           f"{in_flight} microbatch(es) in flight")

    terms = {
        "parameters": parameter_bytes,
        "gradients": gradient_bytes,
        "optimizer": optimizer_bytes,
        "activations": activation_total,
    }
    total = sum(terms.values())
    capacity = gpu_memory_gb * BYTES_PER_GB

    return {
        "parameters_total": params,
        "gpus": gpus,
        "tensor_parallel": tensor_parallel,
        "pipeline_parallel": pipeline_parallel,
        "data_parallel": data_parallel,
        "zero_stage": zero_stage,
        "precision": precision,
        "optimizer": optimizer,
        "bytes_per_param": {"parameters": param_b, "gradients": grad_b,
                            "optimizer": optim_b, "total": param_b + grad_b + optim_b},
        "per_gpu_bytes": terms,
        "per_gpu_gb": {name: value / BYTES_PER_GB for name, value in terms.items()},
        "total_gb": total / BYTES_PER_GB,
        "capacity_gb": gpu_memory_gb,
        "headroom_gb": (capacity - total) / BYTES_PER_GB,
        "utilization": total / capacity,
        "fits": total <= capacity,
        "binding_term": max(terms, key=terms.get),
        "activation_note": activation_note,
    }


def advise(result, unsharded_total_bytes=None):
    """Short, ordered suggestions keyed to the binding term.

    `unsharded_total_bytes` is the same configuration at ZeRO stage 0; it is what makes
    a "you could use a lower stage" suggestion safe to give, since suggesting DDP for a
    run whose unsharded states do not fit would be actively wrong.
    """
    binding = result["binding_term"]
    tips = []
    if result["fits"]:
        tips.append("Fits as configured.")
        if result["zero_stage"] > 0 and result["data_parallel"] > 1:
            capacity = result["capacity_gb"] * BYTES_PER_GB
            if unsharded_total_bytes is not None and unsharded_total_bytes <= capacity:
                tips.append("This configuration also fits without ZeRO sharding - plain "
                            "DDP would cut communication at no memory cost.")
            elif result["utilization"] < 0.5:
                tips.append("Under half of memory is used, but a lower ZeRO stage would "
                            "not fit; the headroom is available for a larger microbatch "
                            "or longer sequence instead.")
        return tips

    tips.append(f"Does not fit: {result['total_gb']:.1f} GB needed vs "
                f"{result['capacity_gb']:.1f} GB available.")
    if binding == "activations":
        tips.append("Activations dominate. Sharding weights will not help. Try selective "
                    "recomputation, a smaller microbatch with more gradient accumulation, "
                    "or sequence parallelism.")
    elif binding == "optimizer":
        tips.append("Optimizer states dominate. ZeRO-1 shards them across the "
                    "data-parallel group at little communication cost.")
    elif binding == "gradients":
        tips.append("Gradients dominate. ZeRO-2 shards them as well as optimizer states.")
    else:
        tips.append("Parameters dominate. ZeRO-3/FSDP shards them; use tensor "
                    "parallelism inside a node if a single layer is the problem.")
    return tips


def _format(result, advice):
    lines = [
        f"Parameters:        {result['parameters_total']:.4g}",
        f"World size:        {result['gpus']}  "
        f"(TP {result['tensor_parallel']} x PP {result['pipeline_parallel']} "
        f"x DP {result['data_parallel']})",
        f"Precision/optim:   {result['precision']} + {result['optimizer']}  "
        f"({result['bytes_per_param']['total']} bytes/param before sharding)",
        f"ZeRO stage:        {result['zero_stage']}",
        "",
        "Per-GPU memory:",
    ]
    for name, value in result["per_gpu_gb"].items():
        share = value / result["total_gb"] * 100 if result["total_gb"] else 0.0
        lines.append(f"  {name:<13} {value:8.2f} GB  ({share:4.1f}%)")
    lines += [
        f"  {'TOTAL':<13} {result['total_gb']:8.2f} GB  "
        f"({result['utilization'] * 100:.1f}% of {result['capacity_gb']:g} GB)",
        "",
        f"Activations:       {result['activation_note']}",
        f"Binding term:      {result['binding_term']}",
        "",
    ]
    lines += advice
    return "\n".join(lines)


def load_plan(path):
    with open(path, encoding="utf-8") as handle:
        plan = json.load(handle)
    if not isinstance(plan, dict):
        raise ValueError("plan file must contain a JSON object")
    return plan


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", nargs="?", help="JSON plan file; flags override its keys")
    parser.add_argument("--params", type=float, help="parameter count (e.g. 7e9)")
    parser.add_argument("--layers", type=int)
    parser.add_argument("--hidden", type=int)
    parser.add_argument("--heads", type=int)
    parser.add_argument("--vocab-size", type=int, default=0, dest="vocab_size")
    parser.add_argument("--ffn-ratio", type=float, default=4.0, dest="ffn_ratio")
    parser.add_argument("--seq-len", type=int, dest="seq_len")
    parser.add_argument("--micro-batch", type=int, default=1, dest="micro_batch")
    parser.add_argument("--microbatches", type=int)
    parser.add_argument("--gpus", type=int, default=8)
    parser.add_argument("--gpu-memory-gb", type=float, default=80.0, dest="gpu_memory_gb")
    parser.add_argument("--precision", default="mixed", choices=sorted({k[0] for k in STATE_BYTES}))
    parser.add_argument("--optimizer", default="adam", choices=sorted({k[1] for k in STATE_BYTES}))
    parser.add_argument("--zero-stage", type=int, default=0, dest="zero_stage")
    parser.add_argument("--tensor-parallel", type=int, default=1, dest="tensor_parallel")
    parser.add_argument("--pipeline-parallel", type=int, default=1, dest="pipeline_parallel")
    parser.add_argument("--sequence-parallel", action="store_true", dest="sequence_parallel")
    parser.add_argument("--recompute", default="none", choices=RECOMPUTE_MODES)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a report")
    args = parser.parse_args()

    settings = {}
    try:
        if args.plan:
            settings.update(load_plan(args.plan))
        for name in ("params", "layers", "hidden", "heads", "seq_len", "micro_batch",
                     "microbatches", "gpus", "gpu_memory_gb", "precision", "optimizer",
                     "zero_stage", "tensor_parallel", "pipeline_parallel",
                     "sequence_parallel", "recompute", "vocab_size", "ffn_ratio"):
            value = getattr(args, name)
            if value != parser.get_default(name) and value is not None:
                settings[name] = value
            settings.setdefault(name, value)

        if not settings.get("params"):
            if not (settings.get("layers") and settings.get("hidden")):
                raise ValueError("supply --params, or --layers and --hidden to derive it")
            settings["params"] = transformer_parameters(
                settings["layers"], settings["hidden"],
                settings.get("vocab_size") or 0, settings.get("ffn_ratio") or 4.0)

        common = dict(
            params=float(settings["params"]), gpus=settings["gpus"],
            gpu_memory_gb=settings["gpu_memory_gb"], precision=settings["precision"],
            optimizer=settings["optimizer"], zero_stage=settings["zero_stage"],
            tensor_parallel=settings["tensor_parallel"],
            pipeline_parallel=settings["pipeline_parallel"],
            sequence_parallel=bool(settings["sequence_parallel"]),
            recompute=settings["recompute"], layers=settings.get("layers"),
            hidden=settings.get("hidden"), heads=settings.get("heads"),
            seq_len=settings.get("seq_len"), micro_batch=settings.get("micro_batch") or 1,
            microbatches=settings.get("microbatches"))
        result = estimate(**common)
        unsharded = estimate(**{**common, "zero_stage": 0})
        advice = advise(result, sum(unsharded["per_gpu_bytes"].values()))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        sys.exit(f"error: {exc}")

    if args.json:
        print(json.dumps({**result, "advice": advice}, indent=2))
    else:
        print(_format(result, advice))


if __name__ == "__main__":
    main()
