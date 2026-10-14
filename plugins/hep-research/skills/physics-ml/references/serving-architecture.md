# Serving Architecture Reference

> Generic ML engineering. Deployment inside experiment software and triggers is in [ml-analysis.md](ml-analysis.md),
> "Deployment in experiment software and triggers"; this file is for a model run as a service (a GPU inference server
> called by many reconstruction or analysis jobs). Export mechanics: [export-and-deployment.md](export-and-deployment.md).
> Sizing: `<plugin root>/skills/physics-ml/scripts/serving_capacity.py`.

- **State the budget first:** a latency percentile (p99; a hard bound in a trigger path), peak throughput from all
  clients at once, and a cost ceiling. Larger batches raise throughput and latency; quantization lowers both and
  risks quality.
- **Latency has parts:** queueing + batching wait + compute + network + pre/post-processing. Measure them separately;
  building particle tensors from the event data model is often comparable to model compute for small models.
- **Batching:** dynamic batching collects requests up to a size or a timeout, and the timeout is latency chosen from
  the budget. Bucket variable-multiplicity events by size or use dynamic axes. Above about 80% utilization queueing
  delay grows sharply: provision headroom.
- **Making the model cheaper** (right-sizing, int8/fp8 quantization, distillation, compilation): every
  accuracy-affecting change needs scores compared on the same events, at the working point and in the regions the
  analysis uses.
- **Hardware:** small-batch inference is usually memory-bandwidth-bound; CPU inference is viable for the small
  taggers run in reconstruction. Plan for peak load, failover headroom and warmup time.

Deliverables: the budget; latency decomposed; batching strategy and timeout; scores compared on identical events after
any optimization; replica count with headroom and measured warmup.
