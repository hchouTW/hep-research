#!/usr/bin/env python3
"""Transfer-learning template for image classification with torchvision.

Expected dataset layout:
    data_dir/
      train/class_a/*.jpg
      train/class_b/*.jpg
      val/class_a/*.jpg
      val/class_b/*.jpg
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms


def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def build_model(num_classes: int, freeze_backbone: bool) -> nn.Module:
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    if freeze_backbone:
        for param in model.parameters():
            param.requires_grad = False
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


def make_loaders(data_dir: Path, batch_size: int, num_workers: int):
    weights = models.ResNet18_Weights.DEFAULT
    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]
    train_transform = transforms.Compose(
        [
            transforms.RandomResizedCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ]
    )
    val_transform = weights.transforms()

    train_ds = datasets.ImageFolder(data_dir / "train", transform=train_transform)
    val_ds = datasets.ImageFolder(data_dir / "val", transform=val_transform)
    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
        persistent_workers=num_workers > 0,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
        persistent_workers=num_workers > 0,
    )
    return train_loader, val_loader, train_ds.classes


def run_epoch(model, loader, criterion, device, optimizer=None):
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    total_correct = 0
    total_examples = 0

    context = torch.enable_grad() if training else torch.inference_mode()
    with context:
        for images, targets in loader:
            images = images.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            if training:
                optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, targets)
            if training:
                loss.backward()
                optimizer.step()

            batch_size = images.size(0)
            total_loss += loss.item() * batch_size
            total_correct += (logits.argmax(dim=1) == targets).sum().item()
            total_examples += batch_size

    return {
        "loss": total_loss / max(total_examples, 1),
        "accuracy": total_correct / max(total_examples, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--freeze-backbone", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("transfer_best.pt"))
    args = parser.parse_args()

    device = get_device()
    train_loader, val_loader, classes = make_loaders(args.data_dir, args.batch_size, args.num_workers)
    model = build_model(len(classes), args.freeze_backbone).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.lr)

    best_acc = -1.0
    for epoch in range(args.epochs):
        train_metrics = run_epoch(model, train_loader, criterion, device, optimizer)
        val_metrics = run_epoch(model, val_loader, criterion, device)
        print(
            f"epoch={epoch + 1:03d} "
            f"train_loss={train_metrics['loss']:.4f} train_acc={train_metrics['accuracy']:.4f} "
            f"val_loss={val_metrics['loss']:.4f} val_acc={val_metrics['accuracy']:.4f}"
        )
        if val_metrics["accuracy"] > best_acc:
            best_acc = val_metrics["accuracy"]
            torch.save({"classes": classes, "model_state_dict": model.state_dict()}, args.output)


if __name__ == "__main__":
    main()
