# Export and Deployment Reference

Covers taking a trained model out of the training script and into a form that another
process, language runtime or device can run. For inference-only weight loading and the
checkpoint format, see [checkpointing.md](checkpointing.md). For `torch.compile` during
training and eager inference, see [performance-memory.md](performance-memory.md). For
deployment inside experiment software and hardware triggers (score agreement between
environments, FPGA latency budgets, trigger systematics) see
[ml-analysis.md](ml-analysis.md), "Deployment in experiment software and triggers"; this
file covers the PyTorch side of the export.

## Before exporting anything

Call `model.eval()` (and freeze parameters): otherwise Dropout and BatchNorm export in training behaviour and the
artifact differs from the validated model.

## Which format

| Target | Export path |
|---|---|
| C++ framework with ONNX Runtime (CMSSW, Athena and other experiment frameworks), Python services | ONNX via `torch.onnx.export(..., dynamo=True)` |
| ROOT-based C++ code without an ML runtime | ONNX, then TMVA SOFIE (generates C++ inference code from the ONNX graph) |
| FPGA trigger | hls4ml (from ONNX or a supported model description); see [ml-analysis.md](ml-analysis.md) |
| PyTorch-native C++ or Python deployment, ahead-of-time compiled | `torch.export` + AOTInductor (`.pt2` package) |
| Same Python process, faster inference | `torch.compile` (not a portable artifact) |

Operator coverage differs between ONNX Runtime, SOFIE and hls4ml: a graph network with
scatter operations or a custom attention may export to ONNX and still fail in SOFIE or
hls4ml. Check the target's supported-operator list before choosing the architecture,
not after training it.

**TorchScript is deprecated.** With torch 2.14.1, `torch.jit.script` and
`torch.jit.trace` emit a `FutureWarning` pointing to `torch.compile` or `torch.export`
(checked 2026-10-13). Do not start new work on it; keep `torch.jit.load` only to read
existing `.pt` TorchScript artifacts, and re-export them through `torch.export` when the
deployment is next touched. The legacy ONNX path (`dynamo=False`, with `dynamic_axes`)
is TorchScript-based too.

## Variable particle multiplicity: declare the dynamic axes

Taggers on particle sets, hits or tracks see a different number of entries per event.
An export that fixes the example input's shape fails, or silently pads or truncates, on
other events. Declare the batch and the particle axis dynamic with `torch.export.Dim`.
Sizes 0 and 1 are specialized, so give the particle axis `min=2` and pad events with
fewer entries. A data-dependent Python `if` on tensor values does not export; rewrite it
with `torch.where` or `torch.cond`, or move it out of the model.

## ONNX export (dynamo exporter)

Verified with torch 2.14.1, onnx 1.23.2, onnxscript 0.7.2 and onnxruntime 1.31.0 (CPU),
2026-10-13, for a masked Deep Sets tagger: exported at batch 8 and 30 particles, the
ONNX Runtime output at batch 3 and 57 particles matched PyTorch within `rtol=1e-4`.

```python
import numpy as np
import onnxruntime as ort
import torch

model.eval()
x = torch.randn(8, 30, 4)            # [batch, n_particles, features], example only
mask = torch.ones(8, 30)             # [batch, n_particles], 1 for real particles

batch = torch.export.Dim("batch", min=1)
n_part = torch.export.Dim("n_particles", min=2, max=512)
onnx_program = torch.onnx.export(
    model, (x, mask), dynamo=True,
    dynamic_shapes={"x": {0: batch, 1: n_part}, "mask": {0: batch, 1: n_part}},
    input_names=["x", "mask"], output_names=["logits"],
)
onnx_program.save("tagger.onnx")

session = ort.InferenceSession("tagger.onnx", providers=["CPUExecutionProvider"])
x2, mask2 = torch.randn(3, 57, 4), torch.ones(3, 57)    # a different batch and multiplicity
(onnx_out,) = session.run(None, {"x": x2.numpy(), "mask": mask2.numpy()})
with torch.inference_mode():
    np.testing.assert_allclose(onnx_out, model(x2, mask2).numpy(), rtol=1e-4, atol=1e-5)
```

- `dynamo=True` (the default in torch 2.14.1) needs `onnx` and `onnxscript`; the `dynamic_shapes` keys are the
  argument names of `forward`. A message that a named axis "will not be used, since it shares the same shape
  constraints with another axis" is harmless.
- Pick and record the opset the deployment runtime supports (the experiment's ONNX Runtime, SOFIE or hls4ml): a newer
  opset fails at load time in the experiment software, not at export.
- Validate against PyTorch on held-out events with realistic multiplicities (smallest and largest), not only on the
  export example: shape or operator-version problems can give silently wrong output.

## `torch.export` and AOTInductor

`torch.export.export` captures the whole graph ahead of time (no Python fallback) with
the same `dynamic_shapes`; `torch.export.save` writes a `.pt2` file that reloads
without the model class. AOTInductor compiles it into a package with native code for a
given device that can be loaded from Python or C++ without the Python model code.
Verified with torch 2.14.1 (CPU), 2026-10-13, with the tagger above; AOTInductor on CPU
needs a working C++ compiler on the build host.

```python
ep = torch.export.export(model, (x, mask), dynamic_shapes={"x": {0: batch, 1: n_part},
                                                          "mask": {0: batch, 1: n_part}})
torch.export.save(ep, "tagger_ep.pt2")
reloaded = torch.export.load("tagger_ep.pt2").module()

package = torch._inductor.aoti_compile_and_package(ep, package_path="tagger_aoti.pt2")
compiled = torch._inductor.aoti_load_package(package)
with torch.inference_mode():
    torch.testing.assert_close(compiled(x2, mask2), model(x2, mask2))
```

An AOTInductor package is compiled for one device type and is tied to the torch version
that built it: rebuild it with the deployment environment's torch, and keep ONNX for
targets that do not ship PyTorch.

## `torch.compile` and quantization

`torch.compile` (`mode="reduce-overhead"` for small latency-bound batches, `"max-autotune"` for long jobs; warm up
with representative shapes) compiles in-process and is not a portable artifact. For a fixed target, static
post-training quantization usually gives the best throughput/accuracy trade; FPGA triggers use per-layer fixed point
from quantization-aware training (QKeras, Brevitas) before hls4ml: the bit widths are part of the model, and the
quantized scores are what must be validated ([efficient-finetuning.md](efficient-finetuning.md)).

## Deployment checklist

- `model.eval()` and `torch.inference_mode()` (not just `no_grad()` - see
  [training-loop.md](training-loop.md)) around every inference call.
- Pin the exact PyTorch, ONNX opset and ONNX Runtime (or SOFIE, hls4ml) versions used
  for export alongside the exported artifact - a version mismatch between export and
  deployment environments is a common source of subtle numerical drift or outright load
  failures. Record this the same way as [reproducibility.md](reproducibility.md)'s
  experiment records.
- Compare scores event by event between the training environment and the deployed
  model on the same events, and re-run the comparison when either environment changes;
  a migration of events across the working point is a systematic
  ([ml-analysis.md](ml-analysis.md)).
- Preprocessing (standardization constants, log transforms, feature order, padding
  value) is part of the model: export it with the graph or version it with the
  artifact, and check it in the comparison above.
- Decide and document the behavior for inputs outside the training domain or malformed
  inputs (wrong multiplicity, out-of-range values) - an exported graph often produces a
  plausible-looking wrong answer rather than an error, and shape asserts in the Python
  model do not survive export.
