# Export and Deployment Reference

Covers taking a trained model out of the training script and into a servable form.
For inference-only weight loading and checkpoint format, see
[checkpointing.md](checkpointing.md). For `torch.compile`'s use *during*
training/eager inference, see the brief note in
[performance-memory.md](performance-memory.md) - this file goes deeper
on compile modes and covers the export formats it doesn't.

## Before exporting anything

```python
model.eval()
for p in model.parameters():
    p.requires_grad_(False)
```

Forgetting `model.eval()` before export/tracing is one of the most common export
bugs - `Dropout`/`BatchNorm` stay in training-mode behavior, so the exported
artifact gives different (and nondeterministic, for dropout) outputs than the model
you validated.

## TorchScript: trace vs. script

TorchScript is deprecated: on torch 2.11 `torch.jit.script`, `torch.jit.trace` and
`torch.jit.script_method` emit a warning pointing to `torch.compile` or `torch.export`.
It still works (verified), so keep it for existing artifacts, but prefer
`torch.export.export(model, (example_input,))` for new work (verified on torch 2.11 for a
small MLP: `ep.module()(x)` matches the eager output).

- **`torch.jit.trace(model, example_input)`** runs the model once with example
  input and records the operations executed. Fast and usually just works, but
  **silently bakes in whatever control-flow branch the example input took** - a
  data-dependent `if` or a variable-length loop will not generalize to inputs that
  would take a different branch. Only safe for models with no data-dependent
  control flow.
- **`torch.jit.script(model)`** parses the actual Python source (a restricted
  subset) and preserves control flow, at the cost of needing code that's
  script-compatible (type annotations matter more, some Python constructs aren't
  supported). Prefer `script` whenever the model has real branching (e.g.
  variable-length sequence handling, an `if` on a tensor value); use `trace` for
  simple feed-forward architectures where it just works.
- Always validate the exported module against the original on the same held-out
  batch before trusting it:
  ```python
  scripted = torch.jit.script(model)
  with torch.no_grad():
      original_out = model(example_input)
      scripted_out = scripted(example_input)
  assert torch.allclose(original_out, scripted_out, atol=1e-5)
  ```
- Save/load with `torch.jit.save(scripted, "model.pt")` /
  `torch.jit.load("model.pt")` - this is a self-contained artifact that doesn't
  need the original Python model class to load, unlike a plain `state_dict`.

## ONNX export

Interchange format for serving outside a PyTorch runtime (ONNX Runtime, mobile
runtimes, some hardware-vendor toolchains):

```python
torch.onnx.export(
    model, example_input, "model.onnx",
    input_names=["input"], output_names=["output"],
    dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},  # variable batch size
    opset_version=17,
)
```

- On torch 2.11 `torch.onnx.export` uses the dynamo exporter by default and needs the
  `onnx` and `onnxscript` packages; without them it raises `ModuleNotFoundError`
  (`onnxscript`). `dynamo=False` selects the legacy TorchScript-based path, which needs
  `onnx` and is the path `dynamic_axes` was written for. The snippet below was not
  run end to end (neither package is installed in the test environment).
- `dynamic_axes` marks which dimensions are not fixed at export time (batch size is
  the near-universal case; sequence length if the model genuinely supports variable
  length). Omitting it bakes the example input's shape in as a hard requirement.
- Like `trace`, ONNX export traces the graph - the same data-dependent-control-flow
  caveat applies, and models with such control flow need extra care (e.g.
  `torch.onnx.export` with `torch.jit.script`-first, where supported) or a
  restructuring to remove the data-dependent branching.
- Validate numerically against the PyTorch model with `onnxruntime`, the same way
  as the TorchScript check above, before trusting the export - shape mismatches or
  operator version issues sometimes only surface as silently wrong (not erroring)
  output.

## `torch.compile` deployment modes

Beyond the basic `torch.compile(model)` shown in
[performance-memory.md](performance-memory.md):

- `mode="reduce-overhead"` targets small-batch, latency-sensitive inference (uses
  CUDA graphs where possible) - most relevant to serving, as opposed to
  `mode="max-autotune"` which spends more compile time searching for the fastest
  kernels and suits long-running training jobs better.
- Expect a slow **first call per distinct input shape** (compilation/graph capture)
  - for serving, warm up with representative shapes before accepting real traffic,
  and prefer padding to a small set of fixed shapes (bucket similar-length inputs
  together) over truly dynamic shapes, which can trigger recompilation per shape
  and defeat the purpose.
- `torch.compile`'s output is not a portable artifact the way TorchScript/ONNX are
  - it compiles the same Python model in-process. Use it for same-process serving
  performance; use TorchScript/ONNX when the deployment target is a different
  process, language runtime, or device than the training environment.

## Quantization for deployment

See [efficient-finetuning.md](efficient-finetuning.md) for
quantization's use during fine-tuning; for pure inference deployment, the same
dynamic/static/QAT choices apply, with static (calibrated) quantization typically
the best throughput/accuracy trade-off for a fixed, known deployment target, and
dynamic quantization the fastest to try first.

## Inference-serving checklist

- `model.eval()` and `torch.inference_mode()` (not just `no_grad()` - see
  [training-loop.md](training-loop.md)) around every inference call.
- Batch requests where latency budget allows; single-example inference wastes
  hardware parallelism.
- Pin the exact PyTorch/CUDA/cuDNN/ONNX-Runtime versions used for export alongside
  the exported artifact - a version mismatch between export and serving
  environments is a common source of subtle numerical drift or outright load
  failures. Record this the same way as
  [reproducibility.md](reproducibility.md)'s experiment records.
- Re-run the numerical-equivalence check (above) as part of CI/release, not only
  once at export time - a dependency bump in the serving environment can silently
  change results.
- Decide and document the fallback behavior for out-of-distribution or malformed
  inputs (e.g. wrong shape, out-of-range values) - an exported graph will often
  produce a *plausible-looking* wrong answer rather than a clear error for such
  inputs, unlike the Python model, which may have had explicit shape asserts that
  did not survive export.
