# core/blinding

Advisory blinding tools (masks, sealing, output scans) and the input-blinding transforms a data custodian runs to
prepare a release. Run by an agent on synthetic data they are exercises; with real data, preparation, sealing and
scanning are custodian services (protected-data-architecture.md §6.2, §8). Nothing here is enforcement.

| File | What |
|---|---|
| `blinding.py` | `mask_binned`, `mask_ratio`, `seal`, `scan_text`, `scan_file`, `scan_paths`, `check_figure`, `agent_view` |
| `transforms.py` | One transform per mode (task P4.1): released data, sealed values, protected and retained lists; keys are inputs, never outputs |
| `residual.py` | `residual_checks`: what a prepared release can still give away, as codes (task P4.3) |

## Modes and what they do not protect

Each mode conceals only what its `protected` list says. A release is acceptable only after the residual checks and a
composition review: the agent can run any code on what it receives (rule 6).

- `binned-mask`: hides the blinded bins and their errors. Does not protect: sums over unblinded bins and the sideband
  total (public by definition); a smooth sideband extrapolation that is itself the protected quantity; another
  release of the same source with another region (the difference is revealed).
- `event-removal`: removes the events in the blinded region, drops the fields named in `drop_fields`, sorts the rest.
  Does not protect: totals of the source shown elsewhere (cutflows, metadata, figures, caches: subtraction gives the
  removed count); identifiers kept elsewhere (index gaps); another release with another region.
- `common-offset` (continuous quantities only; counts are refused): hides the absolute location, keeps differences.
  Does not protect: physical boundaries and reference points (non-negative quantities, resonance or calibration peaks,
  kinematic endpoints); integer inputs (one shared fractional part reveals the offset's); uncertainties computed
  before the offset (withheld by the transform); a second release with another offset.
- `common-scale`: hides the normalization, keeps ratios and shape. Does not protect: scaled counts (integer
  quantization, variance/mean); per-event weights (refused); unscaled companions (predictions, simulation, control
  regions) in the same release; unit-area shapes, which carry no normalization in the first place.

Holdout splits are not a plugin mode (DP-3): custody of a holdout is a deployment matter.
