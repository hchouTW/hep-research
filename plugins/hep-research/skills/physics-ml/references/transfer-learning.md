# Transfer Learning Reference

## When to use

Use transfer learning when data is limited, training from scratch is too slow, or
the model domain is close to an available pretrained backbone.

## Replace a classifier head

For a torchvision-style model:

```python
model = torchvision.models.resnet18(weights="DEFAULT")
in_features = model.fc.in_features
model.fc = torch.nn.Linear(in_features, num_classes)
```

For binary classification, set one output and use `BCEWithLogitsLoss`, or set two
outputs and use `CrossEntropyLoss`. Keep the target format aligned with that
choice.

## Freezing and unfreezing

Freeze the backbone first when data is small:

```python
for param in model.parameters():
    param.requires_grad = False

for param in model.fc.parameters():
    param.requires_grad = True
```

Then fine-tune more layers with a lower learning rate after the new head is
stable.

## Optimizer parameter groups

Use different learning rates for pretrained and newly initialized layers.

```python
optimizer = torch.optim.AdamW(
    [
        {"params": backbone.parameters(), "lr": 1e-5},
        {"params": head.parameters(), "lr": 1e-3},
    ],
    weight_decay=1e-4,
)
```

## Normalization

Match the pretrained model's expected preprocessing. For ImageNet-pretrained
vision models, use ImageNet mean and standard deviation unless project-specific
validation shows another choice is better.

## BatchNorm

Small datasets and small batches can make BatchNorm statistics unstable. Consider
keeping the backbone in eval mode while training the head, or fine-tune with a
small learning rate and monitor validation behavior.
