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

CUDA AMP often improves throughput and memory use. Use `GradScaler` for training
and keep reductions or numerically sensitive operations in full precision when
needed.

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
traces, and be less helpful with dynamic shapes or heavy Python-side data work.
