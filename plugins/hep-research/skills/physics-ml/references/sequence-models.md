# Sequence Model Reference (RNN/LSTM/GRU)

For attention-based sequence models see
[transformer-architectures.md](transformer-architectures.md). This file
covers recurrent architectures, which remain a reasonable default for small
datasets, strict latency/memory budgets, or strictly online/streaming inputs where
a fixed-size recurrent state is a better fit than a growing attention context.

## Choosing a cell

- **LSTM**: two states (hidden, cell), gating tends to handle longer dependencies
  than a plain RNN and is a safe default.
- **GRU**: one state, fewer parameters, often matches LSTM quality with less
  compute - a reasonable first try when compute/memory is tight.
- **Plain `nn.RNN`**: rarely the right choice outside teaching; vanishing gradients
  make it unreliable beyond short sequences.

## Shapes

`nn.LSTM`/`nn.GRU` default to `[seq, batch, features]`; pass `batch_first=True` to
use `[batch, seq, features]` and match the rest of this skill's conventions. Hidden
state shape is `[num_layers * num_directions, batch, hidden_dim]` regardless of
`batch_first`.

```python
lstm = nn.LSTM(input_size=32, hidden_size=128, num_layers=2, batch_first=True, bidirectional=False)
output, (h_n, c_n) = lstm(x)  # output: [batch, seq, hidden_dim]
```

## Packing variable-length sequences

Padding alone wastes compute on pad positions and lets the recurrent state keep
updating on padding, corrupting the final hidden state. Pack before feeding the
RNN, unpack after:

```python
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence

# lengths: [batch], true (unpadded) length of each sequence, sorted or not
# enforce_sorted=False lets you skip sorting the batch yourself
packed = pack_padded_sequence(x, lengths.cpu(), batch_first=True, enforce_sorted=False)
packed_out, (h_n, c_n) = lstm(packed)
output, out_lengths = pad_packed_sequence(packed_out, batch_first=True)
```

`h_n`/`c_n` from a packed input are already the correct final states per sequence
(not corrupted by padding) - use them directly for a sequence-classification head
rather than manually indexing `output` at each sequence's last real position, which
is easy to get off-by-one wrong.

## Sequence classification vs. sequence-to-sequence

- **Classification** (one label per sequence): use the final hidden state `h_n`
  (last layer, both directions if bidirectional, concatenated) as the pooled
  representation into a linear head. Mean-pooling `output` over the true (unpadded)
  positions is a reasonable alternative and sometimes outperforms last-hidden-state
  pooling.
- **Tagging** (one label per timestep): apply a linear head to every position of
  `output`; mask the loss at pad positions (see below).
- **Seq2seq** (encoder-decoder, different output length): encode the source with
  one RNN, feed its final hidden state as the decoder RNN's initial state, and
  decode autoregressively with teacher forcing during training (below).

## Teacher forcing and exposure bias

During training, feed the *ground-truth* previous token as the decoder's next
input rather than its own (possibly wrong) prediction - this parallelizes training
and avoids compounding early mistakes. At inference the model must feed back its
own predictions, which it never saw during training; this train/inference mismatch
is **exposure bias** and is a common reason generation quality looks worse than
training loss would suggest. Mitigations, roughly in order of effort: don't over-
train past the point validation quality plateaus (exposure bias worsens with
overfitting), scheduled sampling (mix in the model's own predictions with
increasing probability during training), or evaluate with the actual decoding
procedure (beam search / sampling) during validation rather than trusting
teacher-forced validation loss alone.

## Masking the loss at padded positions

For per-timestep losses (tagging, seq2seq), padded target positions must not
contribute to the loss or its averaging:

```python
loss_per_token = criterion(logits.reshape(-1, num_classes), targets.reshape(-1))  # reduction="none"
mask = (targets != pad_index).reshape(-1).float()
loss = (loss_per_token * mask).sum() / mask.sum().clamp(min=1)
```

Forgetting this mask is one of the most common silent bugs in sequence-to-sequence
code: training still "works" (loss goes down) but converges slower and the model
wastes capacity learning to predict the pad token correctly.

## Bidirectional and stacked layers

`bidirectional=True` doubles the output feature dimension (concatenates forward and
backward hidden states) - update any downstream `nn.Linear` input size accordingly.
Bidirectional RNNs cannot be used for causal/autoregressive decoding (the backward
pass looks at future tokens); use them only for encoders or classification, not
inside a decoder.

## Gradient clipping

Recurrent nets are more prone to exploding gradients than feed-forward/attention
nets because of repeated multiplication through time steps. Clip after
`backward()`, before `optimizer.step()`:

```python
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
```

If loss still explodes with clipping in place, suspect the learning rate, an
unmasked padded loss contribution, or a missing gradient-zeroing call before
`backward()` - see the debugging checklist in
[debugging-pytorch.md](debugging-pytorch.md).
