# Sequence Model Reference (RNN/LSTM/GRU)

> Generic ML engineering. Physics uses: digitized waveforms and pulse shapes, time series of detector or accelerator
> conditions, sequences of hits along a track. Unordered particle sets are not fed to an RNN in an arbitrary order: use
> a set or graph model ([particle-and-jet-architectures.md](particle-and-jet-architectures.md)). Attention models:
> [transformer-architectures.md](transformer-architectures.md).

- **Cell:** LSTM is the safe default; GRU (one state, fewer parameters) often matches it with less compute; a plain
  `nn.RNN` is unreliable beyond short sequences. RNNs remain reasonable for small data, strict latency or memory, and
  streaming inputs.
- **Shapes:** `nn.LSTM`/`nn.GRU` default to `[seq, batch, features]`; use `batch_first=True`. Hidden states are
  `[num_layers * num_directions, batch, hidden_dim]` regardless. Bidirectional doubles the output features and cannot
  be used in a causal decoder.
- **Variable lengths:** pack before the RNN and unpack after
  (`pack_padded_sequence(x, lengths.cpu(), batch_first=True, enforce_sorted=False)`, `pad_packed_sequence`); padding
  alone keeps updating the state on pads. With packed input `h_n` is the correct final state per sequence; use it for
  a classification head instead of indexing `output`.
- **Heads:** classification from `h_n` (both directions concatenated) or a mean over real positions; tagging applies
  a head per position; seq2seq encodes, then decodes autoregressively.
- **Masked loss:** compute per-position losses with `reduction="none"`, multiply by the real-position mask (times the
  event weight when weighted) and divide by the mask sum. An unmasked pad loss still trains, slower and worse.
- **Teacher forcing** trains on the true previous element; at inference the model feeds its own predictions (exposure
  bias): validate with the real generation procedure; scheduled sampling mitigates.
- **Clip gradients** after `backward()` (`clip_grad_norm_`, max norm about 1); if loss still explodes, suspect the
  learning rate, an unmasked pad loss or a missing gradient reset ([debugging-pytorch.md](debugging-pytorch.md)).
