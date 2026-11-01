"""Runner profiles of the detector-simulation shared layer: declared guarantee levels and policy settings (G0).

A module of detsim.py (TASK.md 6.1-6.2 under docs/dev/detector-simulation/; decision D-W1-3 of PROGRESS.md). A
profile is part of every plan's hash scope (TASK.md 9.2 item 5): its id, level, the declared level of each guarantee
(hard, soft or unsupported) and the policy settings build_spec may read. Declared levels are claimed only as far as
they were measured on the profile's own platform: macos-g0 was measured on macOS 27.2 arm64 / APFS (V-04); linux-g0
declares every guarantee unsupported until it is measured on a Linux host (H0 #7). Reports cite these fields, never
summary words such as "isolated".

host_profile_id() names the profile of the running platform (sys.platform darwin -> macos-g0, linux -> linux-g0); on
native Windows or another platform it raises core.hostcaps.UnsupportedPlatform, whose report() is the
missing-dependency answer (exit 3). shortfalls(required, profile) lists every required guarantee the profile does not
meet (TASK.md 10.2 step 4: refuse, never downgrade).
"""
from __future__ import annotations

import sys

if __spec__ is None:  # run as a file (tests/skills/test_cli_robustness.py): a module of detsim.py, not a command
    if sys.argv[1:] in ([], ["--help"], ["-h"]):
        print((__doc__ or "detsim module").splitlines()[0] + "\nA module of detsim.py, not a command: "
              "python3 detsim.py --help")
        sys.exit(0)
    print('{"status": "rejected", "error_code": "usage", "message": "a module of detsim.py, not a command"}')
    sys.exit(2)

import copy  # noqa: E402

from core import hostcaps  # noqa: E402

LEVELS = ("unsupported", "soft", "hard")  # in increasing order
GUARANTEES = (
    "backend_dies_with_controller",  # the backend terminates when its controller dies (PR_SET_PDEATHSIG on Linux)
    "commit_noreplace",              # the commit never replaces an existing target (renameat2 / renamex_np)
    "durable_commit",                # files and folders reach stable storage before the commit counts
    "local_fs_check",                # artifacts lie on an allowlisted local file system (statfs)
    "inputs_unmodified",             # input hashes equal before and after the run
    "timeout_kill",                  # the timeout terminates the backend's own process group
    "output_size_abort",             # output beyond the budget aborts the run
    "descendants_killed",            # every descendant, also setsid-detached ones, is terminated
    "no_network",                    # the backend cannot open outbound connections
)
POLICY = {
    "input_copy_threshold_bytes": 268435456,  # inputs up to 256 MiB are copied into the attempt (TASK.md 10.2 step 9)
    "rendered_file_max_bytes": 1048576,       # a rendered file above 1 MiB is an input, not a rendered file (8.2)
}
PROFILES = {
    "macos-g0": {
        "id": "macos-g0", "level": "G0", "policy": POLICY,
        "guarantees": {
            "backend_dies_with_controller": "soft", "commit_noreplace": "hard", "durable_commit": "soft",
            "local_fs_check": "hard", "inputs_unmodified": "hard", "timeout_kill": "hard",
            "output_size_abort": "soft", "descendants_killed": "soft", "no_network": "unsupported",
        },
    },
    "linux-g0": {
        "id": "linux-g0", "level": "G0", "policy": POLICY,
        "guarantees": {name: "unsupported" for name in GUARANTEES},  # not measured on a Linux host yet
    },
}
PLATFORM_PROFILES = {"darwin": "macos-g0", "linux": "linux-g0"}


def profile(profile_id: str) -> dict:
    """A copy of the named profile; KeyError for an unknown id."""
    return copy.deepcopy(PROFILES[profile_id])


def host_profile_id() -> str:
    """The profile of this platform; UnsupportedPlatform (missing-dependency) on a platform without one."""
    if hostcaps.on_windows() or not hostcaps.process_groups():
        raise hostcaps.UnsupportedPlatform(["process_groups"])
    for prefix, profile_id in PLATFORM_PROFILES.items():
        if sys.platform.startswith(prefix):
            return profile_id
    raise hostcaps.UnsupportedPlatform([f"runner-profile ({sys.platform})"])


def shortfalls(required: dict, declared: dict) -> list[dict]:
    """Each required guarantee the profile declares below the required level (unknown names count as unsupported)."""
    out = []
    for name, level in sorted(required.items()):
        have = declared["guarantees"].get(name, "unsupported")
        if LEVELS.index(have) < LEVELS.index(level):
            out.append({"guarantee": name, "required": level, "declared": have, "profile": declared["id"]})
    return out
