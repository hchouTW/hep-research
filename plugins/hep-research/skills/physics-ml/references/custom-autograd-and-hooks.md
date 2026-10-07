# Custom Autograd, Hooks, and Activation Checkpointing Reference

## Custom `autograd.Function`

Use when you need a forward/backward pair that isn't expressible by composing
existing differentiable ops - a non-differentiable operation you want a
straight-through gradient for, a numerically stabilized backward that differs from
naive differentiation, or an operation with no PyTorch primitive at all.

```python
class ClampWithStraightThroughGrad(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, low, high):
        ctx.save_for_backward(x)
        ctx.low, ctx.high = low, high
        return x.clamp(low, high)

    @staticmethod
    def backward(ctx, grad_output):
        (x,) = ctx.saved_tensors
        # Straight-through: pass the gradient through unchanged inside the clamp
        # range, block it outside - this is a deliberate approximation, not the
        # "true" gradient of clamp (which is 0 outside the range everywhere).
        mask = (x >= ctx.low) & (x <= ctx.high)
        return grad_output * mask, None, None
```

- `forward`/`backward` are `@staticmethod`; `ctx` carries state between them -
  `ctx.save_for_backward(*tensors)` for tensors (participates correctly in
  memory/version tracking), plain attributes (`ctx.low = low`) for non-tensor
  config.
- `backward` must return one gradient per **input** to `forward` (`x`, `low`,
  `high` above), using `None` for inputs that don't require a gradient (here, the
  two scalar bounds).
- Call it via the `.apply` classmethod, not by instantiating: `ClampWithStraightThroughGrad.apply(x, 0.0, 1.0)`.
- Verify a hand-written backward with `torch.autograd.gradcheck` on
  double-precision (`dtype=torch.float64`) small inputs before trusting it in a
  real model - a wrong analytic gradient often still trains "something" while
  quietly producing a worse or wrong result.

## Hooks for inspection and debugging

Hooks let you observe or modify tensors/gradients without changing the model's
forward code - useful for one-off debugging or lightweight instrumentation, not as
a substitute for correct module design.

```python
activations = {}

def make_forward_hook(name):
    def hook(module, inputs, output):
        activations[name] = output.detach()
    return hook

handle = model.encoder.layer[0].register_forward_hook(make_forward_hook("layer0"))
# ... run a forward pass; activations["layer0"] is now populated ...
handle.remove()  # always remove when done, or it leaks for the model's lifetime
```

- **`register_forward_hook(module, input, output)`**: inspect/replace a layer's
  output. Return a new tensor from the hook to replace the output; return `None`
  to leave it unchanged.
- **`register_forward_pre_hook(module, input)`**: inspect/modify a layer's input
  before `forward` runs.
- **`register_full_backward_hook(module, grad_input, grad_output)`**: inspect
  gradients flowing through a module - the most direct way to find *where* in a
  deep network a NaN or vanishing/exploding gradient first appears, by hooking
  several layers and comparing `grad_output` magnitudes.
- **`tensor.register_hook(fn)`**: inspect/modify the gradient of a specific
  intermediate tensor (one not necessarily tied to a module boundary).
- Always keep the handle returned by `register_*` and call `.remove()` once done;
  an un-removed hook on a long-lived model silently keeps consuming memory
  (accumulating entries in a dict like `activations` above) and can distort timing
  measurements in performance profiling.
- Prefer hooks for *diagnosis*. Once you know what's wrong, fix it by changing the
  model/training code rather than leaving permanent hooks in the training path -
  hooks add overhead and are easy to forget about.

## Activation (gradient) checkpointing

Trades compute for activation memory: instead of keeping every layer's activations
in memory for the backward pass, checkpointed segments discard their activations
after the forward pass and **recompute** them during backward.

```python
from torch.utils.checkpoint import checkpoint

class CheckpointedBlock(nn.Module):
    def __init__(self, block: nn.Module):
        super().__init__()
        self.block = block

    def forward(self, x):
        # use_reentrant=False is the modern, recommended mode - see note below
        return checkpoint(self.block, x, use_reentrant=False)
```

- Use on the memory-heaviest segments first (typically transformer blocks or large
  conv stages) rather than the whole model - checkpointing the entire model gives
  the most memory savings but the most recompute overhead; profile to find the
  actual bottleneck (see
  [performance-memory.md](performance-memory.md)) rather than
  checkpointing everything by default.
- Expect roughly 20-30% slower training per step in exchange for a large reduction
  in peak activation memory - this is the standard way to fit a larger batch size
  or longer sequence length than would otherwise fit, not a free win.
- `use_reentrant=False` avoids several sharp edges of the older reentrant
  implementation (silent incorrect gradients with certain RNG/dropout usage inside
  the checkpointed segment, inability to checkpoint a function with no
  `requires_grad` inputs). Prefer it unless a specific compatibility constraint
  forces the old behavior.
- A checkpointed segment must be **deterministic** given the same inputs (recompute
  during backward must match the forward exactly) - if it contains dropout or other
  randomness, PyTorch handles RNG state save/restore automatically for
  `torch.utils.checkpoint`, but a custom source of randomness (e.g. calling into a
  non-PyTorch RNG) will silently break this and produce incorrect gradients.
- Combine with mixed precision and PEFT (see
  [efficient-finetuning.md](efficient-finetuning.md)) when a single
  technique isn't enough to fit the target batch size/sequence length.

## Debugging with `gradcheck` and anomaly detection

- `torch.autograd.gradcheck(fn, inputs)` numerically verifies a custom
  `autograd.Function`'s backward against finite differences - run once when
  writing it, not on every training run (it's slow and needs double precision).
- `torch.autograd.set_detect_anomaly(True)` (debugging only, slow) surfaces the
  forward operation that produced a NaN/Inf during backward, rather than only
  reporting where the NaN was noticed - see the NaN checklist in
  [debugging-pytorch.md](debugging-pytorch.md) for the broader
  workflow this fits into.
