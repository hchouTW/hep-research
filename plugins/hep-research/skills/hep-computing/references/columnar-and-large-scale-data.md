# Columnar and large-scale data

How to read and reduce data that do not fit in memory, or that sit in many files, without changing the result.
Library names and options below are the common ones; check them against the installed version before relying on a
flag. The pipeline-level material (records, mergeable reductions, time slices) is in
[analysis data pipelines](analysis-data-pipelines.md); ROOT object use is in [ROOT usage](root-usage-patterns.md).

## Formats

| Format | Good for | Read with | Watch out for |
|---|---|---|---|
| ROOT TTree / RNTuple | event data from experiment software | uproot (`uproot.iterate`, `arrays`), PyROOT, RDataFrame | jagged branches; split vs unsplit objects; read only the branches you need |
| Parquet (Apache Arrow) | flat or nested columns for Python analysis, interchange | pyarrow (`ParquetFile.iter_batches`), awkward (`ak.from_parquet`), pandas | row-group size sets the smallest unit you can read; keep a schema version |
| Arrow IPC / Feather | fast local caches between steps | pyarrow | not an archival format; record the producing code version |
| HDF5 | dense arrays, detector images, ML inputs | h5py, PyTables | chunk shape and compression decide read speed; datasets are not self-describing without attributes |
| CSV / JSON Lines | small tables, configuration, exchange with people | standard library | text round-trips of floats need repr precision; no types |

Converting ROOT to Parquet: `<plugin root>/adapters/root-uproot/assets/root_to_parquet.py` (uproot and pyarrow,
optional). Convert once, record the converter version and the input checksums, and keep the ROOT file as the source.

## Chunked and out-of-core processing

- Process a bounded number of rows at a time: `uproot.iterate(files, expressions, step_size=...)` for ROOT,
  `ParquetFile.iter_batches(batch_size=...)` for Parquet, `h5py` slicing for HDF5, a row loop for CSV.
- Reduce each chunk to mergeable quantities (sums, sums of squares, counts, histograms with fixed edges, sorted
  unique keys), never to a mean or a median that cannot be combined. The merge rules are those of `core/partition`
  (sum, min, max, first, concat; a non-additive name is refused unless declared).
- Floating-point sums depend on their order. Either accumulate exactly (the template below keeps Shewchuk partials
  per bin and rounds once, so chunked and one-pass results are identical) or declare a tolerance and test it.
- Template: `<plugin root>/skills/hep-computing/assets/chunked_histogram.py` fills a weighted histogram from CSV,
  ROOT (uproot.iterate) or Parquet (pyarrow) chunk by chunk; `--chunk-size 0` is the one-pass reference.
- Dask (`dask.array`, `dask.dataframe`, `dask-awkward` with coffea) builds a task graph over chunks and runs it on a
  local or distributed scheduler. It is worth it when one machine's cores or memory are the limit; for a single
  pass over files on one machine, a plain chunk loop is simpler to debug and to reproduce.

## Partitioned datasets

- Split by a stable key (run, period, file) so that a partition can be recomputed alone and merged without
  duplicates; record the partition manifest (`<plugin root>/skills/hep-computing/scripts/local_partition.py`).
- Hive-style directories (`period=12/part-0.parquet`) let readers prune partitions by key; the key values must not
  be re-derived from file names in a second place.
- Keep one file per partition at a size the storage handles well (tens to hundreds of MB is common); millions of tiny
  files slow every listing.

## Memory budget

- Estimate the memory budget before running: rows per chunk times bytes per row of the columns read (jagged branches: the mean
  multiplicity times the element size), times the copies the code makes (often two or three).
- Set the chunk size from that budget, not from the file size, and leave room for the reduction's own arrays.
- Watch peak memory once on a representative file (`/usr/bin/time -v` on Linux, `resource.getrusage` in Python) and
  write the budget into the run's computational-run record.
- A process that is killed for memory is a failed run, not a partial result: no output from it is merged.

## Checks

- Chunked result equals the one-pass result (exactly, or within the declared tolerance) on a test file.
- Row counts per partition sum to the total; no partition is read twice (the partition manifest says so).
- The output records the reader, its version, the chunk size and the input checksums.
