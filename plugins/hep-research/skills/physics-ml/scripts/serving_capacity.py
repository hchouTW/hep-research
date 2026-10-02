#!/usr/bin/env python3
"""Size an inference service: replicas, utilization, and p99 latency against a budget.

Purpose: capacity planning that accounts for queueing. Sizing a service from average
throughput alone produces a p99 far worse than the arithmetic suggests, because waiting
time grows without bound as utilization approaches 1 - the reason services are
provisioned with headroom rather than to their nominal capacity.

What it does: converts a batch compute time and batch size into a per-replica request
rate, computes the replicas needed to serve a target QPS below a utilization ceiling,
and estimates p99 latency as batching wait plus an M/M/1 sojourn-time tail. Reports
whether the latency budget is met and what it costs.

Usage notes / assumptions: standard library only; PyTorch is not required. This is a
design-level queueing estimate, not a load test: it assumes Poisson arrivals and
exponential service, which overstates the tail for very regular workloads and
understates it for bursty ones. Service time is the batch compute time amortized over
the batch, so it assumes batches actually fill; below the fill rate the batching
timeout dominates instead, which the output reports separately.
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/scripts/serving_capacity.py --qps 500 --batch-size 16 --batch-latency-ms 40 --latency-budget-ms 250
"""

import argparse
import math
import sys

# -ln(0.01): the p99 point of an exponential sojourn-time distribution.
P99_CONSTANT = math.log(100.0)


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and greater than zero")
    return float(value)


def replica_capacity_qps(batch_size, batch_latency_ms):
    """Requests per second one replica can sustain with full batches."""
    batch_size = _positive(batch_size, "batch_size")
    batch_latency_ms = _positive(batch_latency_ms, "batch_latency_ms")
    return batch_size / (batch_latency_ms / 1000.0)


def replicas_for(qps, capacity_qps, max_utilization=0.8):
    """Smallest replica count keeping utilization at or below the ceiling."""
    qps = _positive(qps, "qps")
    capacity_qps = _positive(capacity_qps, "capacity_qps")
    if not 0.0 < max_utilization < 1.0:
        raise ValueError("max_utilization must be strictly between zero and one")
    return max(1, math.ceil(qps / (capacity_qps * max_utilization)))


def batching_wait_ms(per_replica_qps, batch_size, batch_timeout_ms):
    """Mean time a request waits for its batch to fill, capped by the timeout."""
    per_replica_qps = _positive(per_replica_qps, "per_replica_qps")
    fill_time_ms = (batch_size / per_replica_qps) * 1000.0
    # A request arriving uniformly during the fill window waits half of it on average.
    return min(fill_time_ms / 2.0, batch_timeout_ms)


def sojourn_p99_ms(service_time_ms, utilization):
    """M/M/1 p99 sojourn time: exponential with rate mu*(1-rho)."""
    service_time_ms = _positive(service_time_ms, "service_time_ms")
    if not 0.0 <= utilization < 1.0:
        raise ValueError("utilization must be in [0, 1) - at or above 1 the queue diverges")
    return P99_CONSTANT * service_time_ms / (1.0 - utilization)


def plan(qps, batch_size, batch_latency_ms, latency_budget_ms,
         batch_timeout_ms=10.0, max_utilization=0.8, cost_per_replica_hour=0.0,
         overhead_ms=0.0):
    """Full capacity plan for one service configuration."""
    latency_budget_ms = _positive(latency_budget_ms, "latency_budget_ms")
    capacity = replica_capacity_qps(batch_size, batch_latency_ms)
    replicas = replicas_for(qps, capacity, max_utilization)
    per_replica_qps = qps / replicas
    utilization = per_replica_qps / capacity
    service_time_ms = batch_latency_ms / batch_size

    wait_ms = batching_wait_ms(per_replica_qps, batch_size, batch_timeout_ms)
    batches_fill = (batch_size / per_replica_qps) * 1000.0 <= batch_timeout_ms
    queue_ms = sojourn_p99_ms(service_time_ms, utilization)
    p99 = wait_ms + queue_ms + overhead_ms

    return {
        "qps": float(qps),
        "batch_size": float(batch_size),
        "batch_latency_ms": float(batch_latency_ms),
        "replica_capacity_qps": capacity,
        "replicas": replicas,
        "per_replica_qps": per_replica_qps,
        "utilization": utilization,
        "max_utilization": max_utilization,
        "service_time_ms": service_time_ms,
        "batching_wait_ms": wait_ms,
        "batch_fill_time_ms": (batch_size / per_replica_qps) * 1000.0,
        "batches_fill_before_timeout": batches_fill,
        "queue_and_service_p99_ms": queue_ms,
        "overhead_ms": float(overhead_ms),
        "estimated_p99_ms": p99,
        "latency_budget_ms": latency_budget_ms,
        "meets_budget": p99 <= latency_budget_ms,
        "cost_per_hour": replicas * cost_per_replica_hour,
    }


def advise(result):
    tips = []
    if result["meets_budget"]:
        tips.append(f"Meets the budget: p99 ~{result['estimated_p99_ms']:.0f} ms vs "
                    f"{result['latency_budget_ms']:.0f} ms.")
    else:
        tips.append(f"Misses the budget: p99 ~{result['estimated_p99_ms']:.0f} ms vs "
                    f"{result['latency_budget_ms']:.0f} ms.")
        parts = {"batching wait": result["batching_wait_ms"],
                 "queue + service": result["queue_and_service_p99_ms"],
                 "fixed overhead": result["overhead_ms"]}
        dominant = max(parts, key=parts.get)
        if dominant == "batching wait":
            tips.append("Batching wait dominates. Lower the batch timeout or the batch "
                        "size; both trade throughput for latency.")
        elif dominant == "queue + service":
            tips.append("Queueing and service dominate. Add replicas to lower "
                        "utilization, or make the model itself faster - at high "
                        "utilization a small capacity increase buys a large tail "
                        "improvement.")
        else:
            tips.append("Fixed overhead dominates - this is pre/post-processing or "
                        "network, not the model. Optimizing the model will not help.")
    if not result["batches_fill_before_timeout"]:
        tips.append("Traffic is too sparse to fill batches before the timeout; the "
                    "configured batch size is not being reached.")
    if result["utilization"] > 0.85:
        tips.append(f"Utilization is {result['utilization'] * 100:.0f}% - queueing delay "
                    "grows sharply above roughly 80%. Provision more headroom.")
    return tips


def _format(result, tips):
    lines = [
        f"Target load:       {result['qps']:.0f} QPS",
        f"Replica capacity:  {result['replica_capacity_qps']:.1f} QPS "
        f"(batch {result['batch_size']:.0f} in {result['batch_latency_ms']:.0f} ms)",
        f"Replicas:          {result['replicas']}  "
        f"({result['per_replica_qps']:.1f} QPS each, "
        f"{result['utilization'] * 100:.0f}% utilized)",
        "",
        "Estimated p99 latency:",
        f"  batching wait    {result['batching_wait_ms']:8.1f} ms",
        f"  queue + service  {result['queue_and_service_p99_ms']:8.1f} ms",
        f"  overhead         {result['overhead_ms']:8.1f} ms",
        f"  TOTAL            {result['estimated_p99_ms']:8.1f} ms  "
        f"(budget {result['latency_budget_ms']:.0f} ms)",
        "",
    ]
    if result["cost_per_hour"]:
        lines.append(f"Cost:              {result['cost_per_hour']:,.2f} per hour")
        lines.append("")
    return "\n".join(lines + tips)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--qps", type=float, required=True, help="peak requests/second")
    parser.add_argument("--batch-size", type=float, required=True, dest="batch_size")
    parser.add_argument("--batch-latency-ms", type=float, required=True,
                        dest="batch_latency_ms", help="compute time for a full batch")
    parser.add_argument("--latency-budget-ms", type=float, required=True,
                        dest="latency_budget_ms", help="p99 target")
    parser.add_argument("--batch-timeout-ms", type=float, default=10.0,
                        dest="batch_timeout_ms")
    parser.add_argument("--max-utilization", type=float, default=0.8,
                        dest="max_utilization")
    parser.add_argument("--overhead-ms", type=float, default=0.0, dest="overhead_ms",
                        help="fixed pre/post-processing and network time")
    parser.add_argument("--cost-per-replica-hour", type=float, default=0.0,
                        dest="cost_per_replica_hour")
    args = parser.parse_args()

    try:
        result = plan(args.qps, args.batch_size, args.batch_latency_ms,
                      args.latency_budget_ms, args.batch_timeout_ms,
                      args.max_utilization, args.cost_per_replica_hour,
                      args.overhead_ms)
        tips = advise(result)
    except ValueError as exc:
        sys.exit(f"error: {exc}")
    print(_format(result, tips))


if __name__ == "__main__":
    main()
