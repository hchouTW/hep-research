# Evaluation and Metrics Reference

## Metric aggregation

Aggregate metrics by example count, not by batch count, unless every batch has the
same size.

```python
total_loss += loss.item() * batch_size
total_examples += batch_size
avg_loss = total_loss / max(total_examples, 1)
```

For distributed training, aggregate numerator and denominator across ranks before
dividing.

## Classification

Single-label multiclass classification:

```python
preds = logits.argmax(dim=1)
correct = (preds == targets).sum().item()
accuracy = correct / max(num_examples, 1)
```

Binary classification with logits:

```python
probs = torch.sigmoid(logits)
preds = probs >= threshold
```

Multilabel classification:

```python
probs = torch.sigmoid(logits)
preds = probs >= threshold
per_label_accuracy = (preds == targets.bool()).float().mean(dim=0)
```

Do not apply softmax or sigmoid before `CrossEntropyLoss` or
`BCEWithLogitsLoss`; use activations only for metrics and inference.

## Regression

Common metrics:

```python
mae = (preds - targets).abs().mean()
rmse = torch.sqrt(torch.mean((preds - targets) ** 2))
```

Report target units and any normalization. If targets were standardized, convert
predictions and targets back to original units before reporting user-facing
metrics.

## Validation protocol

- Keep validation and test transforms deterministic.
- Use `shuffle=False` for validation and test loaders.
- Avoid fitting scalers, tokenizers, vocabularies, or normalization statistics on
  validation or test data.
- Track the checkpoint selection metric separately from the final test metric.
- For imbalanced classes, report class counts and prefer balanced metrics such as
  macro F1, per-class recall, ROC AUC, or PR AUC when appropriate.
