#!/usr/bin/env python3
"""Transfer-learning template for image classification with torchvision.

Expected dataset layout:
    data_dir/
      train/class_a/*.jpg
      train/class_b/*.jpg
      val/class_a/*.jpg
      val/class_b/*.jpg

With --freeze-backbone only the new head trains, and the backbone's BatchNorm layers stay in eval mode during
training, so their running statistics stay the pretrained ones (model.train() would otherwise update them).
--help works without PyTorch; exit code 3 when PyTorch or torchvision is missing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transfer learning: fine-tune a pretrained ResNet-18 on an "
                                     "ImageFolder tree (data_dir/train/<class>/, data_dir/val/<class>/).")
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--freeze-backbone", action="store_true",
                        help="train only the new head; frozen BatchNorm layers stay in eval mode")
    parser.add_argument("--output", type=Path, default=Path("transfer_best.pt"))
    return parser


if __name__ == "__main__":
    build_parser().parse_args()  # --help works without PyTorch

try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader
    from torchvision import datasets, models, transforms
except ModuleNotFoundError as _exc:
    if __name__ != "__main__":
        raise
    print(f"vision_transfer.py: {_exc.name or 'torch'} not available ({_exc})", file=sys.stderr)
    sys.exit(3)


def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def build_model(num_classes: int, freeze_backbone: bool) -> nn.Module:
    # downloads pretrained weights from download.pytorch.org on first use (cached afterwards): run where that network
    # access is allowed, or pre-provision the cache outside the agent session
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


def set_train_mode(model: nn.Module, training: bool) -> None:
    """model.train(training), but BatchNorm layers whose parameters are all frozen stay in eval mode.

    In train mode BatchNorm normalizes with batch statistics and updates its running mean/variance even when its
    affine parameters do not train; for a frozen pretrained backbone that silently changes the backbone.
    """
    model.train(training)
    if not training:
        return
    for module in model.modules():
        if isinstance(module, nn.modules.batchnorm._BatchNorm):
            params = list(module.parameters())
            if params and not any(p.requires_grad for p in params):
                module.eval()


def run_epoch(model, loader, criterion, device, optimizer=None):
    training = optimizer is not None
    set_train_mode(model, training)
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
    args = build_parser().parse_args()

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
