# Distributed Training Reference

Prefer `DistributedDataParallel` (DDP) over `DataParallel`. For the usual HEP case, a
tagger, regressor or generative model of up to some hundred million parameters on 1 to
8 GPUs of one node, DDP is the answer: every GPU holds the whole model and optimizer,
and only gradients are exchanged. Reach for sharding (FSDP2, below) only when the
memory equation in [parallelism-strategy.md](parallelism-strategy.md) shows that model
states do not fit; activation-bound runs need recomputation or smaller micro-batches
instead. Starting point: `<plugin root>/skills/physics-ml/assets/ddp_train_skeleton.py`.

## Launch

```bash
torchrun --nproc_per_node=4 train_ddp.py
```

On a single machine, add `--standalone --local-addr=127.0.0.1`. The default rendezvous advertises the host name, and
if that does not resolve (common on laptops and home networks) the processes wait forever with
"network addresses of (<host>, <port>) cannot be retrieved".

## Essentials

Read `LOCAL_RANK`, `RANK`, `WORLD_SIZE` from the environment; `torch.cuda.set_device(local_rank)`; initialize the
process group; wrap the model in `DistributedDataParallel`; shard the training split with a `DistributedSampler` (the
grouped split comes first: [ml-analysis.md](ml-analysis.md), "Splits and leakage") and call `set_epoch(epoch)`; save
checkpoints on rank 0 behind a `dist.barrier()` ([checkpointing.md](checkpointing.md)); destroy the process group at
the end. GPU visibility and `NCCL_DEBUG`: [deep-learning-guide.md](deep-learning-guide.md).

## Metric aggregation

Use `dist.all_reduce` to aggregate sums and counts across processes. For weighted
physics metrics, all-reduce the weighted sums (sum of weights passing, sum of weights,
sum of squared weights), not per-rank efficiencies or AUCs; a ROC curve or AUC needs the
scores gathered (`dist.all_gather_object` or `all_gather` of padded tensors) before it is
computed. `DistributedSampler` pads the last batch by repeating events unless
`drop_last=True`, so evaluation on a sharded test set double-counts a few events: use an
unpadded sampler for evaluation, or evaluate on rank 0 only.

## Sharding: FSDP2, DTensor and distributed checkpoints

When model states do not fit one GPU, use FSDP2 (`torch.distributed.fsdp.fully_shard`),
the current API. The older `FullyShardedDataParallel` wrapper class (FSDP1, with
`ShardingStrategy.FULL_SHARD`, `SHARD_GRAD_OP`, `HYBRID_SHARD`) still works in existing
code; new code uses `fully_shard`.

- `fully_shard(module, mesh=mesh)` is applied bottom-up: to each block (transformer
  layer, message-passing layer), then to the root model. Each sharded parameter becomes
  a `DTensor`, a tensor that knows its device mesh and placement (`Shard(0)` or
  `Replicate()`).
- The FSDP1 strategies map onto `fully_shard` arguments: full sharding is the default
  (`reshard_after_forward` left unset or `True`); `reshard_after_forward=False` keeps parameters gathered
  between forward and backward (the `SHARD_GRAD_OP`, ZeRO-2-like trade); a 2-D mesh
  (`init_device_mesh("cuda", (n_nodes, gpus_per_node))`) shards inside a node and
  replicates across nodes (`HYBRID_SHARD`).
- Mixed precision is set with `mp_policy=MixedPrecisionPolicy(param_dtype=torch.bfloat16,
  reduce_dtype=torch.float32)` passed to `fully_shard` ([mixed-precision.md](mixed-precision.md)).
- **Checkpoints use distributed checkpoint (DCP):** every rank writes its own shards and
  the files reload on a different number of GPUs.

  ```python
  import torch.distributed.checkpoint as dcp
  from torch.distributed.checkpoint.state_dict import get_state_dict, set_state_dict

  model_sd, optim_sd = get_state_dict(model, optimizer)
  dcp.save({"model": model_sd, "optim": optim_sd}, checkpoint_id=ckpt_dir)

  model_sd, optim_sd = get_state_dict(model, optimizer)          # templates to load into
  state = {"model": model_sd, "optim": optim_sd}
  dcp.load(state, checkpoint_id=ckpt_dir)
  set_state_dict(model, optimizer, model_state_dict=state["model"], optim_state_dict=state["optim"])
  ```

  Save the RNG states, scheduler, step and data-order state alongside (rank 0, or per
  rank where they differ), as in [checkpointing.md](checkpointing.md).

Verified with torch 2.14.1 (CPU, gloo, world size 1), 2026-10-13: `fully_shard` on a
small MLP with an explicit CPU mesh (`init_device_mesh("cpu", (1,))`), one AdamW step,
then the DCP save and load above. On a Mac the mesh must be given explicitly, because
the default device detection picks MPS and fails. Multi-GPU NCCL behaviour was not
exercised here; `tests/skills/physics_ml/test_gpu_real.py` covers DDP on a GPU host.
