# Distributed Training Reference

Prefer `DistributedDataParallel` over `DataParallel`.

## Launch

```bash
torchrun --nproc_per_node=4 train_ddp.py
```

On a single machine, add `--standalone --local-addr=127.0.0.1`. The default rendezvous advertises the host name, and
if that does not resolve (common on laptops and home networks) the processes wait forever with
"network addresses of (<host>, <port>) cannot be retrieved".

## Essentials

- Read `LOCAL_RANK`, `RANK`, and `WORLD_SIZE` from environment variables.
- Use `torch.cuda.set_device(local_rank)`.
- Initialize process group.
- Wrap model in `DistributedDataParallel`.
- Use `DistributedSampler`.
- Call `train_sampler.set_epoch(epoch)` every epoch.
- Save checkpoints only on rank 0.
- Destroy process group at the end.

## Metric aggregation

Use `dist.all_reduce` to aggregate sums and counts across processes.
