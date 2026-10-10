# Storage note: CERN EOS for analysis users

## When to read this file

Read it before code, a batch job or an instruction reads or writes CERN EOS: copying data in or out, choosing between
the mounted file system and `root://`, opening files remotely from ROOT or uproot, recovering an overwritten or
deleted file, or reading a quota message. Batch-specific EOS rules (paths a submit file may not use, the xrootd
transfer plugin) are in [batch-site-cern-htcondor.md](batch-site-cern-htcondor.md).

Everything here is either a statement of the EOS project sources (cited by key, all read on 2026-10-10) or an
observation on 2026-10-10 from an lxplus node (AlmaLinux 9) with `eos` client and `eosxd` 5.4.9, xrootd client
5.9.7, ROOT 6.40.04, uproot 5.7.7 with fsspec-xrootd 0.5.5, against a personal home directory reached through
`root://eosuser.cern.ch` (redirector 5.3.26, home instance 5.4.11), with synthetic files only. Nothing is from
memory; an observation holds for those versions and that day, and a directory's policy is whatever its attributes
say today. Status: **documented, observed on client 5.4.9**. Source keys: W1 = the EOS project site
`https://eos-web.web.cern.ch/eos-web/` (its content catalogue); D1 to D5 = the EOS 5 ("Diopside") documentation
under `https://eos-docs.web.cern.ch/diopside/` ("last updated Oct 08, 2026"): D1 = `introduction/index.html`,
D2 = `architecture/index.html`, D3 = `manual/using.html`, D4 = `manual/interfaces.html`, D5 = `manual/protocols.html`.
The D pages are written mostly for operators; only the user-facing parts are used here.

Paths are written as placeholders: `<EOS home>` for the absolute path of your home directory on EOS (the path you
see on the mount), `root://<instance>/<EOS path>` for an XRootD URL. Find yours with `pwd` inside the mount, or ask
the user; never guess another user's path.

## What EOS is

| Topic | Fact | Source | Observed 2026-10-10 |
|---|---|---|---|
| Purpose | disk storage for physics data and user files, focused on interactive and batch analysis; started at CERN in 2010; the basis of CERNBox (sync and share, at least 1 TB of personal space) and the disk front of the CERN Tape Archive | W1, D1 | — |
| Scale at CERN | site: 1.1 EB, 8,000 M files, 100 k disks, 30 k clients, 1–2 TB/s; documentation: more than 7 billion files, 780 PB, over 60 k drives "as of June 2022" | W1, D1 | the two sources differ because they are dated differently; quote one with its date |
| Version | production line "Diopside" = EOS 5; latest stable 5.5.1 (26 Aug 2026) | W1, D1 | client 5.4.9, redirector 5.3.26, home instance 5.4.11: servers and clients differ in version, so check `eos version` before relying on a feature |
| Services | MGM (namespace and metadata, one active node with standbys, not sharded), MQ (MGM–FST messaging), FST (file data on disk), QuarkDB (Raft key-value store persisting the namespace) | D2, W1 | — |
| Protocols | XRootD is native (strong authentication, redirection that separates metadata from data, vector reads for WAN latency, third-party copy with checksums at both ends); HTTP(S) through XrdHttp; S3, CIFS, SFTP through gateways; the FUSE client `eosxd` mounts EOS with the same authentication | D2, W1 | — |
| Clients | the `eos` shell; `xrdcp` (copy), `xrdfs` (file system operations), the XrdCl C++ library; `eosxd` for the mount | D2 | — |
| Identity | every client is mapped by its authentication method to a virtual identity (uid/gid plus roles); methods include Kerberos 5, X.509, OIDC, shared secret, JWT and EOS tokens | D2, W1 | from lxplus the Kerberos ticket maps you (`eos whoami` shows `authz:krb5`) |
| Layouts | files are stored as replicas or erasure-coded (RAIN: raid5, raiddp, raid6, archive, qrain; at least 6 stripes); a directory policy (`sys.forced.layout`, `sys.forced.nstripes`) decides | D2, D3 | a personal home: 2 replicas, adler32 checksum, atomic uploads, 50 GB maximum file size (from `eos attr ls`) |
| Help | operational questions about the CERN service: the EOS support address on the project site (W1, "Support"); software issues: the EOS JIRA tracker; incidents and interventions: the CERN IT service status board | W1 | — |

## Instances and how to address them

| Topic | Fact | Source | Observed 2026-10-10 |
|---|---|---|---|
| Personal space | — | not stated in W1 or D1–D5 | `root://eosuser.cern.ch` is a redirector (`EOS_INSTANCE=eoshome-redirector`) that forwards path operations to the instance holding the home directory (here `eoshome-i02`, also reachable as the alias the mount reports, `eoshome-<letter>.cern.ch`) |
| Commands without a path | — | not stated | `eos root://eosuser.cern.ch whoami` and `version` are answered by the redirector itself and show uid 65534 (nobody, `authz:unix`) although path operations through it are authenticated; for your identity and server version ask the home instance |
| Default instance | — | not stated in D2–D5 | without a URL argument the `eos` shell went to the instance in `EOS_MGM_URL`; a login shell may export an experiment instance there, and a bare `eos` command then acts on that instance, not on your home |
| Which instance a mounted path belongs to | virtual attributes on the mount: `eos.name`, `eos.mgmurl`, `eos.quota`, `eos.url.xroot` (read with `getfattr -n <key> <path>` or `eosxd get <key> <path>`) | D3 | `getfattr --only-values -n eos.mgmurl <EOS home>/<dir>` printed the home instance URL |

**Rule:** name the instance in every command that writes or deletes (`eos root://<instance> ...`,
`xrdcp ... root://<instance>/<EOS path>`); do not rely on `EOS_MGM_URL` from the environment.

## Copying, checksums and atomic uploads

| Topic | Fact | Source | Observed 2026-10-10 |
|---|---|---|---|
| Checksums | the checksum type is a directory policy (`sys.forced.checksum`); since 5.4.0 additional checksums (MD5, SHA-256) can be configured per directory | D2, D3 | adler32 on a home directory; `xrdadler32 <local file>`, `eos fileinfo <path> -m` (`xs=`) and `xrdfs root://<instance> query checksum <path>` gave the same value for 1 MB and 100 MB files, also from a second node; downloads were byte-identical |
| Atomic upload | — | not described in D2–D5 | with `sys.forced.atomic=1`, during an upload only a hidden `.sys.a#.<name>.<uuid>` entry exists; an `xrdcp` killed mid-transfer left nothing under the target name, and the hidden entry disappeared: a reader never sees a half-written file under the final name |
| Recursive download | — | — | `xrdcp -r root://.../<dir>/ <local dir>/` fails ("no such file or directory processing") unless the local target directory exists |
| Many small files | quota counts files (inodes) as a hard limit | D4 | 200 files of 10 kB took 5–8 s to upload either by `xrdcp` (one call, many sources) or by `cp` onto the mount (about 25–40 ms per file), while one 100 MB file took 0.3–0.5 s: per-file cost dominates; single runs, indicative only |

**Rules:** copy bulk data with `xrdcp` and compare the adler32 of source and destination (`xrdadler32` against
`xrdfs ... query checksum`) before deleting the source; pack many small outputs into one file (a ROOT file, a tar
archive) instead of writing thousands of tiny files.

## The mounted file system (FUSE) versus root://

| Topic | Fact | Source | Observed 2026-10-10 |
|---|---|---|---|
| Mount | `eosxd` mounts EOS as a file system with the same authentication | D2, D3 | on lxplus the mount was already present and showed the personal home |
| Overwriting through the mount | — | not stated | **overwriting an existing file through the mount (`cp` onto it) created no version**: two overwrites by `cp` left the version list unchanged and the replaced contents were lost; the same overwrite by `xrdcp -f` kept the old content as a version |
| Deleting through the mount | — | not stated | deleting a file and recreating it through the mount (`cp --remove-destination`) removed its version history from the directory (it goes to the recycle bin with the file) |
| Stuck mount | eosxd can crash or hang; processes then sit in state `D` and `df` blocks; the documented recovery kills the `eosxd` processes and aborts the connection through the FUSE control file system | D3 | — (inferred: on a shared node these steps are the administrators'; use `root://` or another node and report it) |
| Batch jobs | inside HTCondor jobs use `xrdcp root://...` or `eos`, not the mount | [batch site note](batch-site-cern-htcondor.md) | — |

**Rule:** for data you may need to recover, write and overwrite with `xrdcp -f` (or the `eos` shell), not with
`cp` onto the mount; use the mount for browsing, small edits and reading.

## Versions, recycle bin and quota

| Topic | Fact | Source | Observed 2026-10-10 |
|---|---|---|---|
| Versioning | `sys.versioning=<n>` keeps up to n versions (FIFO) in a hidden `.sys.v#.<name>` folder, plus extra versions in 11 time bins up to one month; `eos file versions <path>` lists them, `eos file versions <path> <id>` grabs one back, `eos file version <path>` forces one, `eos file purge <path> <n>` trims | D3 | a home directory had `sys.versioning=10` and new subdirectories inherited it; grabbing a version made it current and kept the replaced content as a new version |
| Recycle bin | deletions go to a recycle bin with a lifetime and a size limit; `eos recycle ls` lists your entries with a restore key, `eos recycle restore <key>` restores (`-f` renames an object now occupying the path); if the bin is full, deletions fail; deleted files leave your quota at once and count against the recycle bin's quota | D4 | lifetime 3,628,800 s (42 days), keep ratio 0.30 (`eos recycle`); a deleted 100 MB file was restored with the same checksum; after deleting the test tree the user's quota returned to its earlier value |
| Purging the recycle bin | "purging only removes files of the current uid/gid role" | D4 | **a normal user may not purge**: `recycle purge -k <key>` answered "you cannot purge your recycle bin without being a sudo or having an admin role"; deleted data stays restorable (and present) until the lifetime ends |
| Deleting a tree with versions | — | — | `eos rm -r` of a test tree created one recycle entry per version folder (205 of 207 entries) |
| Quota | inode (file count) quota is hard, volume quota is soft; logical bytes are what you stored, raw bytes include replicas (2 replicas: raw = 2 × logical); status `warning` below 5 % left, `exceeded` at 0; with an exceeded inode quota, smaller files do not help, fewer files do | D4 | a home directory is a project quota node: 1 TB logical / 2 TB raw, 5 M files; `eos quota <EOS home>/` (the 5.4.9 client help: without the trailing slash the path is taken as a file and does not match the quota node) |
| ACLs | files take their permissions from the parent directory and only the direct parent is checked; `sys.acl` / `user.acl` (the latter only with `sys.eval.useracl`) hold rules `u:`, `g:`, `egroup:`, `k:`, `z:`; ACLs are copied to a directory when it is created, later changes do not reach existing subdirectories; a valid token replaces the ACLs for that request | D4 | a new subdirectory had the home's ACL |

**Rules:** versions and the recycle bin are a time-limited safety net, not a backup; you cannot empty the recycle bin
yourself, so do not plan on deleting to make room for something that must stay private. Before writing many files,
read the directory's policy: `eos root://<instance> attr ls <dir>`, `eos root://<instance> quota <dir>/`,
`eos root://<instance> recycle`.

## Tokens and sharing

| Topic | Fact | Source | Observed 2026-10-10 |
|---|---|---|---|
| EOS tokens | signed tokens delegate rights on a file or a tree for a limited time: `eos token --path <path> --expires <unix time> [--permission rx] [--tree]` (a directory path ends with `/`); use as `root://<instance>/<EOS path>?authz=<token>` (the only form for tree tokens); `eos token --token <token>` shows the contents | D3 | on the home instance a token for a single file was refused ("no permission!") but a tree token for an owned directory was issued; without Kerberos a read was refused without the token and allowed with it; a write with a read-only token was refused |
| Sharing links | `eos file share <path>` prints ROOT or HTTP URLs | D5 | — |
| HTTP | XrdHttp (MGM port 8443, FST 8444); a client without authorization or token is mapped to nobody | D5 | — |

**Rule:** a token is a credential: never write one into a log, a report or a committed file; give the shortest
lifetime and the narrowest path and permission that work.

## Remote reading from analysis code

| Topic | Fact | Source | Observed 2026-10-10 |
|---|---|---|---|
| ROOT | — | — | `TFile::Open("root://<instance>/<EOS path>")` read a synthetic NanoAOD-like file (ROOT 6.40.04) |
| uproot | — | — | `uproot.open("root://<instance>/<EOS path>")` read the same file through `fsspec-xrootd` (needs the `fsspec-xrootd` package and the XRootD Python bindings, `pip install fsspec-xrootd xrootd`; the system Python on the node had neither) |

See [python-hep-coding-patterns.md](python-hep-coding-patterns.md) for the uproot reading patterns themselves.
