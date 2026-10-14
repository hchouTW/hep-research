# Custom Autograd, Hooks, and Activation Checkpointing Reference

## Custom `autograd.Function`

For a forward/backward pair not expressible with differentiable ops: a straight-through gradient through a
non-differentiable step, a numerically stabilized backward, an operation with no PyTorch primitive.

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
        mask = (x >= ctx.low) & (x <= ctx.high)  # a deliberate approximation, not the true gradient
        return grad_output * mask, None, None    # one gradient per forward input, None for non-tensors
```

Call it as `ClampWithStraightThroughGrad.apply(x, 0.0, 1.0)`; tensors go through `ctx.save_for_backward`, other state
on `ctx`. Check a hand-written backward once with `torch.autograd.gradcheck` on small float64 inputs: a wrong gradient
often still trains, worse.

## Hooks for diagnosis

`register_forward_hook(module, input, output)` reads or replaces a layer's output; `register_forward_pre_hook` its
input; `register_full_backward_hook(module, grad_input, grad_output)` the gradients through it, the direct way to find
where a NaN or a vanishing or exploding gradient first appears; `tensor.register_hook` the gradient of one
intermediate tensor. Keep the returned handle and call `.remove()`: a forgotten hook keeps memory (for example a dict
of stored activations) and distorts timings. Use hooks to diagnose, then fix the model code.

## Activation checkpointing

`torch.utils.checkpoint.checkpoint(block, x, use_reentrant=False)` drops a segment's activations after forward and
recomputes them in backward: about 20-30% slower steps for much lower peak activation memory. Checkpoint the heaviest
segments first (transformer blocks, large convolution stages) after profiling
([performance-memory.md](performance-memory.md)). `use_reentrant=False` avoids the old mode's silent wrong gradients
with dropout and its failure on segments without `requires_grad` inputs. A recomputed segment must be deterministic:
PyTorch restores its own RNG state, but a non-PyTorch random source breaks the gradients silently. Combine with mixed
precision and LoRA ([efficient-finetuning.md](efficient-finetuning.md)) when one technique is not enough.
`torch.autograd.set_detect_anomaly(True)` (slow, debugging only) names the forward operation that produced a NaN
([debugging-pytorch.md](debugging-pytorch.md)).
