#!/usr/bin/env python3
"""Generic inference template for PyTorch classifiers."""

from __future__ import annotations

import argparse

import torch

from models import MLPClassifier


def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint")
    parser.add_argument("--input-dim", type=int, required=True)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--num-classes", type=int, required=True)
    parser.add_argument("--unsafe-full-unpickle", action="store_true",
                        help="load with weights_only=False (full pickle, can run arbitrary code); only for files you trust")
    args = parser.parse_args()

    device = get_device()
    model = MLPClassifier(args.input_dim, args.hidden_dim, args.num_classes).to(device)

    # weights_only=True loads tensors and plain containers only; a full unpickle can run arbitrary code.
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=not args.unsafe_full_unpickle)
    state_dict = ckpt.get("model_state_dict", ckpt)
    model.load_state_dict(state_dict)
    model.eval()

    # Replace this dummy input with real preprocessing.
    x = torch.randn(1, args.input_dim, device=device)

    with torch.inference_mode():
        logits = model(x)
        probs = torch.softmax(logits, dim=1)
        pred = probs.argmax(dim=1)

    print("prediction:", pred.item())
    print("probabilities:", probs.squeeze(0).detach().cpu().tolist())


if __name__ == "__main__":
    main()
