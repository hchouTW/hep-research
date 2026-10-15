# Transformer Architecture Reference

> Generic ML engineering; not physics-specific. For physics tasks start at
> [ml-analysis.md](ml-analysis.md). Transformers on particle sets (no positional encoding,
> padding masks, pairwise features) are in
> [particle-and-jet-architectures.md](particle-and-jet-architectures.md); this file covers
> the generic building blocks.

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
contribute. A row that is masked everywhere (an empty event or a padded query) gives
`softmax` of all `-inf`, which is NaN; guard it (`assets/hep_losses.py` has a NaN-safe
masked softmax) or make sure every event keeps at least one real entry.

## Multi-head attention

Split `embed_dim` into `num_heads x head_dim`, project q, k, v once (`nn.Linear(embed_dim, 3 * embed_dim)`), reshape to
`[batch, heads, seq, head_dim]`, attend, merge back and project out. Once a hand-written version is checked, use
`torch.nn.functional.scaled_dot_product_attention` (fused, memory-efficient kernels) or
`torch.nn.TransformerEncoderLayer`; keep a manual version only to modify the attention itself (pairwise interaction
features as attention biases, custom masks, sparse attention). The template is `assets/transformer_classifier.py`.

## Positional information

Attention has no inherent order. For sets of particles, hits or tracks that is what you
want: add no positional encoding, and the model stays permutation invariant (see
[particle-and-jet-architectures.md](particle-and-jet-architectures.md)). For genuinely
ordered inputs (time series, waveforms, sequences of detector layers), add position
information:

- **Sinusoidal (fixed, no parameters)**: good default for from-scratch models; adds
  cleanly to the token embedding.
- **Learned absolute embeddings**: an `nn.Embedding(max_len, embed_dim)` indexed by
  position; simplest, but does not extrapolate past `max_len`.
- **Rotary (RoPE)**: rotates query/key pairs by a position-dependent angle instead of
  adding to the embedding; extrapolates better than learned embeddings. Do not
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

## Encoder block

A pre-norm residual block, `x + dropout(attn(norm1(x)))` then `x + dropout(ff(norm2(x)))` with a GELU feed-forward,
trains far more stably than post-norm beyond a few layers.

## Encoder-only, decoder-only, encoder-decoder

Encoder-only (bidirectional, no causal mask) for classification and embeddings: pool with a learned class token or a
mean over non-pad positions, never including pads. Decoder-only (causal) for autoregressive generation, for example of
ordered or tokenized jet constituents: teacher-forced training ([sequence-models.md](sequence-models.md)), sequential
inference with a KV cache. Encoder-decoder adds cross-attention from the decoder to the encoder output.

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

The cache costs, per token and per layer, `2 (K and V) x n_kv_heads x head_dim x
bytes_per_element` (with grouped-query attention `n_kv_heads` is smaller than the
number of query heads); multiply by layers, sequence length and batch for the total.

## Common failure modes

Loss stuck at chance: a mask inverted or missing, or all inputs padded. Fine on short inputs, wrong on long ones:
positions that do not extrapolate, or high-multiplicity events rare in training. NaN for some events: a fully masked
row in the softmax. Uniform attention: a missing `1/sqrt(head_dim)` scale or an all-zero mask. NaN with more layers:
post-norm without warmup ([debugging-pytorch.md](debugging-pytorch.md)).
