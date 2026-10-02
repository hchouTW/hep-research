# Mixed Precision Reference

Use AMP on CUDA for speed and lower memory use.

```python
scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))

with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
    outputs = model(inputs)
    loss = criterion(outputs, targets)

scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()
```

With gradient clipping:

```python
scaler.scale(loss).backward()
scaler.unscale_(optimizer)
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm)
scaler.step(optimizer)
scaler.update()
```

Do not use CUDA AMP assumptions on CPU-only or MPS-only machines.
