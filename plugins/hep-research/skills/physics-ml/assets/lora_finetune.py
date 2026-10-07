"""Parameter-efficient fine-tuning of a frozen base model with LoRA adapters.

Purpose: starting point for fine-tuning a base model under a limited compute/memory
budget by training small low-rank adapters instead of the full weight matrices. See
<plugin root>/skills/physics-ml/references/efficient-finetuning.md for the technique and its trade-offs.

What the code does: defines `LoRALinear`, a drop-in wrapper around a frozen
`nn.Linear` that adds a trainable low-rank update, `apply_lora` to swap it in for
named linear layers of an existing model, and a training-loop skeleton that builds
an optimizer over only the adapter parameters. Input/output shapes follow whatever
base model is wrapped - this file does not define a base model itself.

Usage notes: requires PyTorch. Replace `build_base_model` with the real base model
and `create_dataset` with the real fine-tuning data; this file has no CLI and is
meant to be imported/adapted, not run standalone.
"""
from __future__ import annotations

import torch
from torch import nn


class LoRALinear(nn.Module):
    """Wraps a frozen nn.Linear with a trainable low-rank update: W + scale * B @ A."""

    def __init__(self, base: nn.Linear, rank: int = 8, alpha: float = 16.0):
        super().__init__()
        self.base = base
        for param in self.base.parameters():
            param.requires_grad_(False)
        self.lora_a = nn.Parameter(torch.randn(rank, base.in_features) * 0.01)
        self.lora_b = nn.Parameter(torch.zeros(base.out_features, rank))
        self.scale = alpha / rank

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        base_out = self.base(x)
        lora_out = (x @ self.lora_a.T) @ self.lora_b.T
        return base_out + self.scale * lora_out

    def merged_weight(self) -> torch.Tensor:
        """Weight matrix with the LoRA update folded in, for zero-overhead inference."""
        return self.base.weight + self.scale * (self.lora_b @ self.lora_a)


def apply_lora(model: nn.Module, target_names: tuple[str, ...], rank: int = 8, alpha: float = 16.0) -> nn.Module:
    """Replace named nn.Linear submodules (e.g. ("query", "value")) with LoRALinear.

    Collects every (parent_module, child_name, child) match in a first pass, then
    applies all replacements in a second pass - mutating a module's children while
    ``model.modules()``/``named_children()`` are still iterating over it is unsafe
    and can silently skip entries.
    """
    replacements = []
    for module in model.modules():
        for child_name, child in module.named_children():
            if child_name in target_names and isinstance(child, nn.Linear):
                replacements.append((module, child_name, child))
    for module, child_name, child in replacements:
        setattr(module, child_name, LoRALinear(child, rank=rank, alpha=alpha))
    return model


def trainable_parameters(model: nn.Module) -> list[nn.Parameter]:
    params = [p for p in model.parameters() if p.requires_grad]
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in params)
    print(f"trainable params: {trainable:,} / {total:,} ({100 * trainable / total:.2f}%)")
    return params


def build_base_model() -> nn.Module:
    """Placeholder base model; replace with the real pretrained model to fine-tune."""
    return nn.Sequential(
        nn.Linear(256, 256),
        nn.ReLU(),
        nn.Linear(256, 10),
    )


def create_dataset(num_examples: int = 256):
    x = torch.randn(num_examples, 256)
    y = torch.randint(0, 10, (num_examples,))
    return torch.utils.data.TensorDataset(x, y)


def train_one_epoch(model: nn.Module, loader, optimizer, device: torch.device) -> float:
    model.train()
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    for inputs, targets in loader:
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad(set_to_none=True)
        loss = criterion(model(inputs), targets)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * inputs.size(0)
    return total_loss / len(loader.dataset)


if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = build_base_model()
    # Placeholder target names - a real base model's attention projections are
    # typically named things like "query"/"value" or "q_proj"/"v_proj"; adjust to
    # match the actual model being wrapped. Here we adapt every nn.Linear child
    # named "0" or "2" (the two Linear layers in the placeholder Sequential above)
    # purely so this file runs end to end as a smoke test.
    apply_lora(model, target_names=("0", "2"), rank=4, alpha=8.0)
    model = model.to(device)

    trainable = trainable_parameters(model)
    optimizer = torch.optim.AdamW(trainable, lr=1e-3)

    dataset = create_dataset()
    loader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)

    epoch_loss = train_one_epoch(model, loader, optimizer, device)
    print(f"epoch loss: {epoch_loss:.4f}")
