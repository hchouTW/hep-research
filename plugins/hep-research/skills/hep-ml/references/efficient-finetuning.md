# Efficient Fine-Tuning Reference (PEFT, Quantization)

> Generic ML engineering. The physics use is adapting a pretrained model (a jet or particle foundation model) to a
> new task or detector with few labelled events; validate the adapted model exactly as one trained from scratch
> (grouped splits, simulation-to-data checks). Full fine-tuning and freezing: [transfer-learning.md](transfer-learning.md).
> Template: `assets/lora_finetune.py`.

## LoRA

Prefer parameter-efficient fine-tuning when the base model is large for the GPU, several task variants of one base are
needed, or the labelled sample is small enough to risk forgetting; prefer full fine-tuning when it fits and the task is
far from pre-training (a low-rank update may not be expressive enough). LoRA freezes `W` and learns
`W + (alpha / r) B A` with `A: [r, in]`, `B: [out, r]`, `r << min(in, out)`:

- initialize `B` to zeros, so the adapted model equals the base at step 0;
- start with a small rank (4-64) on the attention projections, and raise it only if validation plateaus below full
  fine-tuning;
- merge `B A` into `W` for inference, or keep adapters separate to swap them;
- check the trainable parameter count before a long run, build the optimizer over
  `filter(lambda p: p.requires_grad, model.parameters())` after freezing, keep frozen BatchNorm in eval mode
  ([transfer-learning.md](transfer-learning.md)), and save adapters with the identity of their base checkpoint.

Activation checkpointing ([custom-autograd-and-hooks.md](custom-autograd-and-hooks.md)) addresses activation memory and
combines with LoRA, which addresses parameter and optimizer memory.

## Quantization

- **Dynamic** (weights ahead of time, activations on the fly; CPU, no calibration data). With torch 2.14.1 (CPU,
  checked 2026-10-13) `torch.ao.quantization` runs but emits a `DeprecationWarning` pointing to `torchao`, and Apple
  silicon needs `torch.backends.quantized.engine = "qnnpack"`; for new work use `torchao` or the deployment toolchain
  (ONNX Runtime, hls4ml).
- **Static post-training** (activation ranges from a calibration pass; accuracy depends on how representative it is)
  and **quantization-aware training** (fake-quantize during training; best accuracy per bit-width).
- A quantized base under LoRA matters only for models too large for the GPU; most physics models are far below that.
- Always compare quantized against unquantized quality on the same held-out events, not only speed.
