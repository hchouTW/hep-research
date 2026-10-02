#!/usr/bin/env python3
"""Minimal DistributedDataParallel training skeleton.

Replace `build_dataset`, `build_model`, and `run_train_step` with project code.
Launch with:
    torchrun --nproc_per_node=4 ddp_train_skeleton.py
Uses NCCL on CUDA; without CUDA it falls back to CPU with the gloo backend (smoke tests only).
"""

from __future__ import annotations

import os

import torch
import torch.distributed as dist
from torch import nn
from torch.nn.parallel import DistributedDataParallel
from torch.utils.data import DataLoader, DistributedSampler, TensorDataset


def setup_distributed():
    local_rank = int(os.environ["LOCAL_RANK"])
    rank = int(os.environ["RANK"])
    world_size = int(os.environ["WORLD_SIZE"])
    if torch.cuda.is_available():
        torch.cuda.set_device(local_rank)
        dist.init_process_group(backend="nccl")
    else:  # CPU smoke-test path: gloo backend, no device_ids
        dist.init_process_group(backend="gloo")
    return local_rank, rank, world_size


def build_dataset():
    x = torch.randn(4096, 32)
    y = torch.randint(0, 4, (4096,))
    return TensorDataset(x, y)


def build_model():
    return nn.Sequential(nn.Linear(32, 128), nn.ReLU(), nn.Linear(128, 4))


def reduce_average(value: torch.Tensor, world_size: int) -> torch.Tensor:
    dist.all_reduce(value, op=dist.ReduceOp.SUM)
    return value / world_size


def main() -> None:
    local_rank, rank, world_size = setup_distributed()
    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda", local_rank) if use_cuda else torch.device("cpu")

    dataset = build_dataset()
    sampler = DistributedSampler(dataset, shuffle=True)
    loader = DataLoader(dataset, batch_size=64, sampler=sampler, num_workers=2, pin_memory=use_cuda)

    model = build_model().to(device)
    model = DistributedDataParallel(model, device_ids=[local_rank] if use_cuda else None)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

    for epoch in range(5):
        sampler.set_epoch(epoch)
        model.train()
        total_loss = torch.tensor(0.0, device=device)
        total_examples = torch.tensor(0.0, device=device)

        for inputs, targets in loader:
            inputs = inputs.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            logits = model(inputs)
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()

            batch_size = inputs.size(0)
            total_loss += loss.detach() * batch_size
            total_examples += batch_size

        avg_loss = reduce_average(total_loss, world_size) / reduce_average(total_examples, world_size).clamp_min(1)
        if rank == 0:
            print(f"epoch={epoch + 1} loss={avg_loss.item():.4f}")

    if rank == 0:
        torch.save(model.module.state_dict(), "ddp_model.pt")
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
