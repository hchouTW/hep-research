# Mixed Precision Reference

The one place in this skill for automatic mixed precision (AMP).

## Choose the dtype

| | bf16 | fp16 |
|---|---|---|
| Exponent range | same as fp32 (max about 3.4e38) | max 65504, smallest normal about 6.1e-5 |
| Significand | 8 bits with the implicit bit (8 log10 2, about 2.4 decimal digits) | 11 bits (about 3.3 decimal digits) |
| `GradScaler` | not needed | required (gradients underflow without loss scaling) |
| Hardware | native on compute capability 8.0 and newer (A100, H100, L40), and on recent CPUs | every CUDA GPU |

Prefer bf16 where the hardware supports it natively. `torch.cuda.is_bf16_supported()` also returns True when
bf16 is only emulated (V100, compute capability 7.0), so check the capability before choosing bf16 for speed.
Mixed precision is not always faster: for very small models (many HEP taggers) the casts dominate. Measure with
`<plugin root>/skills/physics-ml/scripts/benchmark_model.py --amp` before turning it on for speed.

## Inputs in physical units overflow fp16

Raw detector and physics quantities often exceed the fp16 range: energies in MeV or keV, ADC counts, momenta in
MeV, timestamps, run numbers used as features. An energy of 200 GeV written in MeV is 2e5 and becomes `inf` in
fp16, and the first linear layer under autocast then produces NaN. Before autocast:

- standardize each feature with training-set statistics, or log-transform heavy-tailed positive quantities
  (`torch.log1p`); do this in fp32 in the data pipeline, not inside the autocast region;
- keep losses, reductions over many events (sums, means, histograms, weighted metrics), softmax normalizers and
  decorrelation penalties (DisCo, distance correlation) in fp32: cast logits with `.float()` before the loss;
- keep event weights in fp32; large or tiny generator weights lose precision in 16 bits.

## bf16 recipe (no GradScaler)

Verified with torch 2.14.1 (CPU), 2026-10-13; on CUDA the same code runs with `device.type == "cuda"`.

```python
for inputs, targets in loader:            # inputs already standardized or log1p-transformed in fp32
    optimizer.zero_grad(set_to_none=True)
    with torch.autocast(device_type=device.type, dtype=torch.bfloat16):
        logits = model(inputs).squeeze(-1)
    loss = criterion(logits.float(), targets)   # loss and reductions in fp32
    loss.backward()
    optimizer.step()
```

## fp16 recipe (with GradScaler)

Verified with torch 2.14.1 (CPU), 2026-10-13.

```python
scaler = torch.amp.GradScaler(device.type)
for inputs, targets in loader:
    optimizer.zero_grad(set_to_none=True)
    with torch.autocast(device_type=device.type, dtype=torch.float16):
        logits = model(inputs).squeeze(-1)
    loss = criterion(logits.float(), targets)
    scaler.scale(loss).backward()
    scaler.unscale_(optimizer)               # before clipping, so the norm is in true units
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm)
    scaler.step(optimizer)                   # skips the step when gradients are inf/NaN
    scaler.update()
```

- Save `scaler.state_dict()` in the checkpoint ([checkpointing.md](checkpointing.md)); a resumed run without it
  restarts the loss scale at 65536 and skips steps until it settles.
- A scale that keeps falling, or many skipped steps, means overflow in the forward pass: look for unscaled inputs
  (above) before blaming the optimizer.
- Do not wrap `backward()` or `optimizer.step()` in autocast.

Memory: mixed precision does not halve training memory ([parallelism-strategy.md](parallelism-strategy.md)).

## Checks before trusting a mixed-precision result

- Compare the validation metric and the score distribution with an fp32 run on the same seed; a shift larger than
  the seed-to-seed spread is a precision problem, not noise.
- For a model deployed in fp32 (or in another precision on a trigger), compare scores event by event across the
  precisions, as [ml-analysis.md](ml-analysis.md) asks for deployment environments.
