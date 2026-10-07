# Transformer Architecture Reference

## Core building block: scaled dot-product attention

```python
import math
import torch
from torch import nn


def scaled_dot_product_attention(q, k, v, mask=None):
    # q,k,v: [batch, heads, seq, head_dim]
    scale = 1.0 / math.sqrt(q.size(-1))
    scores = (q @ k.transpose(-2, -1)) * scale  # [batch, heads, seq_q, seq_k]
    if mask is not None:
        scores = scores.masked_fill(mask == 0, float("-inf"))
    weights = torch.softmax(scores, dim=-1)
    return weights @ v, weights
```

`mask` is boolean or 0/1 with `True`/`1` meaning "attend". Fill with `-inf` before
softmax, never after - softmax of an already-zeroed score still lets that position
contribute.

## Multi-head attention

Split `embedding_dim` into `num_heads * head_dim`, project once, reshape, attend,
then merge back:

```python
class MultiHeadAttention(nn.Module):
    def __init__(self, embed_dim: int, num_heads: int):
        super().__init__()
        assert embed_dim % num_heads == 0
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.qkv = nn.Linear(embed_dim, 3 * embed_dim)
        self.out = nn.Linear(embed_dim, embed_dim)

    def forward(self, x, mask=None):
        b, seq, dim = x.shape
        qkv = self.qkv(x).reshape(b, seq, 3, self.num_heads, self.head_dim)
        q, k, v = qkv.permute(2, 0, 3, 1, 4)  # each [b, heads, seq, head_dim]
        attended, _ = scaled_dot_product_attention(q, k, v, mask)
        attended = attended.transpose(1, 2).reshape(b, seq, dim)
        return self.out(attended)
```

Prefer `torch.nn.functional.scaled_dot_product_attention` (fused, memory-efficient
kernels on CUDA) over the hand-written version above once correctness is confirmed;
keep the manual version only for teaching or when you need a non-standard mask/score
modification it doesn't support.

## Positional information

Attention has no inherent order, so add position information:

- **Sinusoidal (fixed, no parameters)**: good default for from-scratch models; adds
  cleanly to the token embedding.
- **Learned absolute embeddings**: an `nn.Embedding(max_len, embed_dim)` indexed by
  position; simplest, but does not extrapolate past `max_len`.
- **Rotary (RoPE)**: rotates query/key pairs by a position-dependent angle instead of
  adding to the embedding; extrapolates better and is standard in modern LLMs. Do not
  hand-roll RoPE without a reference implementation to compare against - a sign or
  interleaving error is easy to introduce and silently degrades quality rather than
  crashing.

## Masking conventions

- **Padding mask**: `True`/`1` for real tokens, `False`/`0` for pad; shape
  `[batch, 1, 1, seq_k]` so it broadcasts over heads and query positions.
- **Causal mask**: lower-triangular, so position `i` cannot attend to `j > i`.
  ```python
  causal = torch.tril(torch.ones(seq, seq, dtype=torch.bool))
  ```
- Combine with `padding_mask & causal_mask` for autoregressive decoding on padded
  batches. A model that trains well without a mask but degrades in production
  usually has a mask shape/broadcast bug, not a modeling problem - check it before
  tuning hyperparameters.

## Encoder block and stacking

```python
class TransformerBlock(nn.Module):
    def __init__(self, embed_dim, num_heads, ff_dim, dropout=0.1):
        super().__init__()
        self.attn = MultiHeadAttention(embed_dim, num_heads)
        self.norm1 = nn.LayerNorm(embed_dim)
        self.ff = nn.Sequential(
            nn.Linear(embed_dim, ff_dim), nn.GELU(), nn.Linear(ff_dim, embed_dim)
        )
        self.norm2 = nn.LayerNorm(embed_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, mask=None):
        x = x + self.dropout(self.attn(self.norm1(x), mask))  # pre-norm residual
        x = x + self.dropout(self.ff(self.norm2(x)))
        return x
```

Prefer **pre-norm** (`LayerNorm` before the sublayer, as above) over post-norm for
anything beyond a handful of layers - it trains far more stably without a learning-
rate warmup, whereas post-norm often diverges early in deep stacks without one.

## Encoder-only vs. decoder-only vs. encoder-decoder

- **Encoder-only** (BERT-style): bidirectional attention, no causal mask; used for
  classification/embedding tasks. Pool with the first token's representation (a
  learned `[CLS]`-style token) or mean-pool over non-pad positions - never mean-pool
  including pad positions.
- **Decoder-only** (GPT-style): causal mask, autoregressive next-token objective;
  used for generation. Training computes all positions' loss in parallel via
  teacher forcing (see [sequence-models.md](sequence-models.md)); inference
  is sequential and needs a KV cache (below) to be tractable.
- **Encoder-decoder** (T5/original Transformer-style): encoder attends bidirectionally
  over the source; decoder self-attends causally over the target and cross-attends
  (queries from the decoder, keys/values from the encoder output) to the source.

## KV caching for autoregressive generation

Recomputing attention over the whole prefix at every generated token is quadratic
and wasteful. Cache each layer's key/value projections for prior positions and only
compute the new token's query against `cache ++ new_kv`:

```python
# Conceptually, per layer: keep k_cache, v_cache of shape [batch, heads, seen, head_dim]
k_cache = torch.cat([k_cache, k_new], dim=2)
v_cache = torch.cat([v_cache, v_new], dim=2)
out, _ = scaled_dot_product_attention(q_new, k_cache, v_cache, mask=None)
```

Without a cache, naive generation re-runs the full forward pass per token: correct
but O(n^2) in sequence length instead of O(n).

## Common failure modes

| Symptom | Likely cause |
|---|---|
| Loss plateaus immediately near `-log(1/vocab_size)` | Learning rate too high/low for warmup schedule, or causal mask is inverted/missing |
| Works on short sequences, garbage on long ones | Positional encoding doesn't extrapolate past training `max_len` |
| Attention weights uniform everywhere | Missing scale factor (`1/sqrt(head_dim)`), or all-zero mask |
| Great train loss, poor generation | Exposure bias from teacher forcing - see sequence-models.md; consider scheduled sampling or just more data/regularization first |
| NaNs after adding more layers | Missing pre-norm, or residual scale growing with depth - check `debugging-pytorch.md` for the NaN checklist |

## When not to build from scratch

For anything beyond a learning exercise or a highly custom architecture, prefer an
existing, tested implementation (e.g. `torch.nn.TransformerEncoderLayer`, or a
well-maintained model library) over hand-rolling attention - the failure modes above
are easy to introduce and hard to notice until training quality quietly suffers.
Building from scratch is still the right call when the point is to modify the
attention mechanism itself (custom masking, sparse attention, a novel positional
scheme) or when a course/interview context asks for it explicitly.
