"""A small from-scratch Transformer encoder for sequence classification.

Purpose: starting point for text/sequence classification with a Transformer
encoder built from primitives (multi-head attention, sinusoidal positional
encoding, pre-norm residual blocks) rather than a pretrained library model - useful
when you need a small, fully-owned model (limited compute, no internet access to
pull pretrained weights, or a teaching/debugging context). See
${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/references/transformer-architectures.md for the design rationale behind each piece.

What the code does: embeds a batch of token-id sequences, adds sinusoidal
positional encoding, runs them through a stack of pre-norm Transformer encoder
blocks with a padding mask, mean-pools over non-pad positions, and classifies with
a linear head. Input: token ids `[batch, seq_len]` (long) and a boolean padding
mask `[batch, seq_len]` (True = real token). Output: `[batch, num_classes]` logits.

Usage notes: requires PyTorch. Replace `vocab_size`/`num_classes` and the
`create_dummy_batch` function for a real dataset and tokenizer; this file has no
CLI and is meant to be imported/adapted, not run standalone.
"""
from __future__ import annotations

import math

import torch
from torch import nn


class SinusoidalPositionalEncoding(nn.Module):
    def __init__(self, embed_dim: int, max_len: int = 4096):
        super().__init__()
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, embed_dim, 2) * (-math.log(10000.0) / embed_dim))
        pe = torch.zeros(max_len, embed_dim)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe, persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [batch, seq, embed_dim]
        return x + self.pe[: x.size(1)].unsqueeze(0)


class MultiHeadAttention(nn.Module):
    def __init__(self, embed_dim: int, num_heads: int):
        super().__init__()
        if embed_dim % num_heads != 0:
            raise ValueError("embed_dim must be divisible by num_heads")
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.qkv = nn.Linear(embed_dim, 3 * embed_dim)
        self.out = nn.Linear(embed_dim, embed_dim)

    def forward(self, x: torch.Tensor, padding_mask: torch.Tensor | None) -> torch.Tensor:
        batch, seq, embed_dim = x.shape
        qkv = self.qkv(x).reshape(batch, seq, 3, self.num_heads, self.head_dim)
        q, k, v = qkv.permute(2, 0, 3, 1, 4)  # each: [batch, heads, seq, head_dim]

        scale = 1.0 / math.sqrt(self.head_dim)
        scores = (q @ k.transpose(-2, -1)) * scale  # [batch, heads, seq, seq]
        if padding_mask is not None:
            # padding_mask: [batch, seq] True=real token -> broadcast over heads/query dim
            key_mask = padding_mask[:, None, None, :]
            scores = scores.masked_fill(~key_mask, float("-inf"))
        weights = torch.softmax(scores, dim=-1)
        attended = weights @ v  # [batch, heads, seq, head_dim]
        attended = attended.transpose(1, 2).reshape(batch, seq, embed_dim)
        return self.out(attended)


class TransformerBlock(nn.Module):
    def __init__(self, embed_dim: int, num_heads: int, ff_dim: int, dropout: float = 0.1):
        super().__init__()
        self.attn = MultiHeadAttention(embed_dim, num_heads)
        self.norm1 = nn.LayerNorm(embed_dim)
        self.ff = nn.Sequential(
            nn.Linear(embed_dim, ff_dim), nn.GELU(), nn.Linear(ff_dim, embed_dim)
        )
        self.norm2 = nn.LayerNorm(embed_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, padding_mask: torch.Tensor | None) -> torch.Tensor:
        x = x + self.dropout(self.attn(self.norm1(x), padding_mask))
        x = x + self.dropout(self.ff(self.norm2(x)))
        return x


class TransformerClassifier(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        num_classes: int,
        embed_dim: int = 128,
        num_heads: int = 4,
        ff_dim: int = 512,
        num_layers: int = 4,
        max_len: int = 512,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.positional = SinusoidalPositionalEncoding(embed_dim, max_len=max_len)
        self.blocks = nn.ModuleList(
            [TransformerBlock(embed_dim, num_heads, ff_dim, dropout) for _ in range(num_layers)]
        )
        self.final_norm = nn.LayerNorm(embed_dim)
        self.classifier = nn.Linear(embed_dim, num_classes)

    def forward(self, token_ids: torch.Tensor, padding_mask: torch.Tensor) -> torch.Tensor:
        # token_ids: [batch, seq] long; padding_mask: [batch, seq] bool, True=real token
        x = self.positional(self.embedding(token_ids))
        for block in self.blocks:
            x = block(x, padding_mask)
        x = self.final_norm(x)

        # Mean-pool over real (non-pad) positions only.
        mask = padding_mask.unsqueeze(-1).to(x.dtype)  # [batch, seq, 1]
        summed = (x * mask).sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1.0)
        pooled = summed / counts
        return self.classifier(pooled)


def create_dummy_batch(batch_size: int = 8, seq_len: int = 32, vocab_size: int = 1000):
    """Synthetic batch with random padding, for a quick forward/backward smoke test."""
    lengths = torch.randint(low=seq_len // 2, high=seq_len + 1, size=(batch_size,))
    token_ids = torch.randint(1, vocab_size, (batch_size, seq_len))
    padding_mask = torch.arange(seq_len).unsqueeze(0) < lengths.unsqueeze(1)
    token_ids = token_ids * padding_mask  # zero out (padding_idx=0) the padded tail
    return token_ids, padding_mask


if __name__ == "__main__":
    model = TransformerClassifier(vocab_size=1000, num_classes=5)
    token_ids, padding_mask = create_dummy_batch()
    logits = model(token_ids, padding_mask)
    loss = logits.sum()
    loss.backward()
    print("logits shape:", tuple(logits.shape))
    print("forward/backward smoke test: OK")
