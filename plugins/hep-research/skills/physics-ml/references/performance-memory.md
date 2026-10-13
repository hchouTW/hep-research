# Performance and Memory Reference

## First checks

- Confirm the model and tensors are on the intended device.
- Measure data-loading throughput separately from model throughput.
- Profile after a warmup period; first batches often include setup overhead.
- Use realistic batch sizes, transforms, and sequence lengths.

## Data loading

If the GPU is underutilized:

- Increase `num_workers` until throughput stops improving.
- Use `pin_memory=True` when training on CUDA.
- Keep expensive CPU transforms outside the hot path when possible.
- Avoid returning Python objects that require heavy collation.
- Use `persistent_workers=True` only when `num_workers > 0`.

## Training loop

Good defaults:

```python
optimizer.zero_grad(set_to_none=True)
```

Avoid synchronizing CUDA every step:

```python
# Expensive if done every iteration only for logging.
loss_value = loss.item()
```

Avoid retaining graphs:

```python
losses.append(loss.item())        # good
outputs_cpu.append(outputs.cpu()) # only after detach/inference when needed
```

## Mixed precision

AMP often improves throughput and activation memory on GPUs with native bf16 or fp16
units. Recipes (bf16 without `GradScaler`, fp16 with it), the fp16 overflow of raw inputs
in MeV, keV or ADC counts, and what stays in fp32 are in
[mixed-precision.md](mixed-precision.md).

## Memory pressure

Common fixes:

- Reduce batch size.
- Use gradient accumulation.
- Use CUDA AMP.
- Use activation checkpointing for very deep models.
- Freeze unused backbone layers during transfer learning.
- Avoid saving full validation outputs unless needed.
- Delete large temporary tensors and call `torch.cuda.empty_cache()` only between
  phases, not every step.

## `torch.compile`

Use `torch.compile` only after the eager model is correct.

```python
if use_compile and hasattr(torch, "compile"):
    model = torch.compile(model)
```

It can improve steady-state throughput but may slow startup, complicate stack
traces, and be less helpful with heavy Python-side data work.

### Variable particle multiplicity: the common recompilation trap

Events have different numbers of particles, hits, tracks or constituents. Padding each
batch to its own maximum gives a new shape almost every batch; `torch.compile`
specializes on the first shape, recompiles on the next ones, and after the recompile
limit (`torch._dynamo.config.recompile_limit`, 8 by default) falls back to eager with
a single warning that is easy to miss. The run gets slower, not faster. Either:

- mark the particle axis dynamic, so one graph serves every multiplicity:

  ```python
  model = torch.compile(model, dynamic=True)        # or leave dynamic=None and mark the axis:
  torch._dynamo.mark_dynamic(x, 1)                   # x: [batch, n_particles, features]
  torch._dynamo.mark_dynamic(mask, 1)                # mask: [batch, n_particles]
  ```

- or pad to a few fixed sizes (bucket events by multiplicity, for example 32, 64,
  128, 256), which keeps static shapes and lets the compiler specialize per bucket.

Check with `TORCH_LOGS=recompiles python train.py`: a recompile reported on every new
size means the axis is not dynamic. Sizes 0 and 1 are specialized even on a dynamic
axis, so pad events with fewer than two particles. Verified with torch 2.14.1 (CPU),
2026-10-13, for a masked Deep Sets tagger across multiplicities 17, 41 and 90.
