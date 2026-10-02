# Tensor Shape Reference

## Common conventions

- Images: `[batch_size, channels, height, width]`
- Video: `[batch_size, channels, frames, height, width]` or project-specific
  `[batch_size, frames, channels, height, width]`
- Token ids: `[batch_size, sequence_length]`
- Token embeddings: `[batch_size, sequence_length, embedding_dim]`
- RNN input with `batch_first=True`: `[batch_size, sequence_length, input_dim]`
- Classification logits: `[batch_size, num_classes]`
- Binary logits: `[batch_size]` or `[batch_size, 1]`
- Multilabel logits: `[batch_size, num_labels]`
- Dense segmentation logits: `[batch_size, num_classes, height, width]`

## Shape assertions

Use assertions near boundaries where incorrect shapes become expensive to debug.

```python
assert images.ndim == 4, f"Expected [B, C, H, W], got {tuple(images.shape)}"
assert logits.size(0) == targets.size(0)
```

For segmentation with `CrossEntropyLoss`:

```python
assert logits.ndim == 4                  # [B, C, H, W]
assert targets.shape == logits.shape[0:1] + logits.shape[2:4]  # [B, H, W]
assert targets.dtype == torch.long
```

## Reshaping guidance

- Prefer `torch.flatten(x, start_dim=1)` for flattening all non-batch dims.
- Use `reshape` when contiguity is uncertain; use `view` only when the tensor is
  known to be contiguous.
- Use `permute` for axis reordering, then call `.contiguous()` only if required
  by a later operation.
- Avoid hard-coded batch sizes in `reshape` or `view`; use `x.size(0)`.

## Loss shape contracts

`CrossEntropyLoss`:

- Logits: `[batch_size, num_classes]` or `[batch_size, num_classes, ...]`
- Targets: `[batch_size]` or `[batch_size, ...]`
- Target dtype: `torch.long`

`BCEWithLogitsLoss`:

- Logits and targets have the same shape.
- Target dtype is floating point.

Regression losses:

- Prediction and target shapes should match, except for deliberate broadcasting.
