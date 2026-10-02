# Efficient Fine-Tuning Reference (PEFT, Quantization)

For full fine-tuning, head replacement, and freezing/unfreezing strategy, see
[transfer-learning.md](transfer-learning.md) first. This file covers
techniques for fine-tuning large models under tighter compute/memory budgets.

## When to reach for parameter-efficient fine-tuning (PEFT)

Prefer PEFT (LoRA and similar) over full fine-tuning when: the base model is large
relative to available GPU memory, you need to keep several task-specific variants
of one base model cheaply (LoRA adapters are small - often tens of MB, vs. gigabytes
for a full copy), or the fine-tuning dataset is small enough that full fine-tuning
risks catastrophic forgetting of the base model's general capability. Prefer full
fine-tuning when compute/memory allow it and the task is far from the base model's
pretraining distribution - PEFT methods constrain the update to a low-rank or
sparse subspace, which is sometimes not expressive enough for a large distribution
shift.

## LoRA (Low-Rank Adaptation)

Freeze the original weight matrix `W`; learn a low-rank update
`W + (alpha / r) * B @ A` where `A` is `[r, in_features]`, `B` is `[out_features, r]`,
and `r << min(in_features, out_features)`. Only `A` and `B` are trained.

```python
class LoRALinear(nn.Module):
    """Wraps a frozen nn.Linear with a trainable low-rank update."""

    def __init__(self, base: nn.Linear, rank: int = 8, alpha: float = 16.0):
        super().__init__()
        self.base = base
        for p in self.base.parameters():
            p.requires_grad_(False)
        self.lora_a = nn.Parameter(torch.randn(rank, base.in_features) * 0.01)
        self.lora_b = nn.Parameter(torch.zeros(base.out_features, rank))
        self.scale = alpha / rank

    def forward(self, x):
        base_out = self.base(x)
        lora_out = (x @ self.lora_a.T) @ self.lora_b.T
        return base_out + self.scale * lora_out
```

- Initialize `lora_b` to zeros (as above) so the adapted model is numerically
  identical to the base model at step 0 - training then only ever moves away from
  the original behavior, never starts from a randomly perturbed one.
- Typical ranks are small (4-64); higher rank approaches full fine-tuning's
  expressiveness and cost. Start low and increase only if validation quality
  plateaus below what full fine-tuning achieves on a held-out comparison.
- Apply to the attention projection layers first (query/value projections are the
  most common target; some setups also adapt the output and/or feed-forward
  layers) rather than every linear layer in the model - adapting everything
  usually isn't necessary and increases trainable parameters and memory for the
  optimizer state.
- After training, `B @ A` can be merged into `W` for a zero-overhead inference
  path (`W_merged = W + scale * B @ A`), or kept separate to swap adapters at
  inference time without reloading the base model.
- Only `A`/`B` (and any other explicitly unfrozen parameters) need gradients and
  optimizer state - confirm with
  `sum(p.numel() for p in model.parameters() if p.requires_grad)` before a long
  training run; a much larger number than expected usually means a freeze call
  was skipped or ordered after wrapping.

## Quantization

Reduces the numeric precision of weights (and sometimes activations) to save
memory and, on supported hardware, increase throughput.

- **Dynamic quantization** (`torch.quantization.quantize_dynamic`): weights are
  quantized ahead of time, activations are quantized on the fly at inference. Easiest
  to apply, CPU-inference-oriented, no calibration data needed. Best for linear/LSTM-
  heavy models.
- **Static (post-training) quantization**: both weights and activations are
  quantized, using a calibration pass over representative data to determine
  activation ranges. More setup, generally better throughput than dynamic
  quantization, but accuracy depends on how representative the calibration data is.
- **Quantization-aware training (QAT)**: simulates quantization effects
  (fake-quantize) during training/fine-tuning so the model adapts to the precision
  loss. Highest accuracy at a given bit-width, at the cost of a training pass
  rather than a post-hoc conversion.
- **Fine-tuning a quantized (or partially quantized) large model** (e.g. loading
  base weights in 8-bit or 4-bit precision and training LoRA adapters in full/half
  precision on top) combines both techniques above and is the standard way to
  fine-tune large models on limited GPU memory - the frozen base dominates memory
  and is quantized, while the small trainable adapters stay full-precision for
  stable optimization.
- Quantization is a precision/throughput trade against accuracy: always compare
  quantized-model quality against the unquantized baseline on the same held-out
  set before adopting it, not just inference speed.

## Gradient checkpointing alongside PEFT

Combine PEFT with activation (gradient) checkpointing - see
[custom-autograd-and-hooks.md](custom-autograd-and-hooks.md) - when even
a PEFT-sized set of trainable parameters doesn't fit the activation memory budget
for the sequence lengths/batch sizes you need; the two techniques address different
memory costs (parameter/optimizer-state memory vs. activation memory) and are
commonly used together.

## Freezing checklist specific to PEFT

- Confirm frozen parameters actually have `requires_grad=False` *before*
  constructing the optimizer - an optimizer built over `model.parameters()` before
  freezing will still track (and waste memory/compute on) frozen parameters' state
  unless you explicitly filter with
  `filter(lambda p: p.requires_grad, model.parameters())`.
- Put the model in the right mode per component if `dropout`/`BatchNorm` exist in
  the frozen base - see the `BatchNorm` guidance in
  [transfer-learning.md](transfer-learning.md); it applies identically
  here.
- Save only the trainable adapter state for lightweight checkpoints
  (`{k: v for k, v in model.state_dict().items() if "lora_" in k}`), and document
  which base-model checkpoint/version an adapter was trained against - an adapter
  is meaningless without its matching frozen base.
