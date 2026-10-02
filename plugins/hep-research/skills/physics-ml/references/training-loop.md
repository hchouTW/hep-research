# PyTorch Training Loop Reference

## Required phases

A robust training script usually has:

1. Configuration parsing
2. Seeding
3. Device selection
4. Dataset and DataLoader creation
5. Model creation
6. Loss, optimizer, scheduler creation
7. Optional checkpoint resume
8. Epoch loop
9. Training loop
10. Validation loop
11. Checkpoint saving
12. Final test or inference

## Training step

```python
model.train()
optimizer.zero_grad(set_to_none=True)
outputs = model(inputs)
loss = criterion(outputs, targets)
loss.backward()
optimizer.step()
```

## Evaluation step

```python
model.eval()
with torch.inference_mode():
    outputs = model(inputs)
```

## Loss averaging

Average by number of examples, not number of batches, unless all batches are guaranteed to have the same size.

```python
total_loss += loss.item() * batch_size
total_examples += batch_size
avg_loss = total_loss / max(total_examples, 1)
```

## Common scheduler conventions

- `StepLR`, `CosineAnnealingLR`: usually step once per epoch.
- `OneCycleLR`: usually step once per optimizer step.
- `ReduceLROnPlateau`: step after validation using validation metric.
