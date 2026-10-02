# PyTorch Debugging Reference

## Device mismatch

Typical error:

```text
Expected all tensors to be on the same device
```

Fix by moving model and batch tensors to the same device.

```python
model = model.to(device)
inputs = inputs.to(device)
targets = targets.to(device)
```

## Shape mismatch

Add assertions:

```python
assert logits.ndim == 2, logits.shape
assert targets.ndim == 1, targets.shape
assert logits.size(0) == targets.size(0)
```

## Wrong dtype for classification

`CrossEntropyLoss` expects class indices as `torch.long`.

```python
targets = targets.long()
```

`BCEWithLogitsLoss` expects float targets.

```python
targets = targets.float()
```

## Softmax or sigmoid in the wrong place

Do not apply softmax before `CrossEntropyLoss`.

Do not apply sigmoid before `BCEWithLogitsLoss`.

Apply activation only for metrics or inference probabilities.

## NaNs

Check:

```python
assert torch.isfinite(inputs).all()
assert torch.isfinite(outputs).all()
assert torch.isfinite(loss).all()
```

Use anomaly detection only for debugging:

```python
with torch.autograd.set_detect_anomaly(True):
    loss.backward()
```
