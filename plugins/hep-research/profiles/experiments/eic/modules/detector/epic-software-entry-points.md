# ePIC software and data-format entry points

> Scope: ePIC experiment software, public pages only; no release pinned, nothing executed.
> Method owner: [hep-computing](../../../../../skills/hep-computing/SKILL.md) for environments, builds, I/O, batch execution and reproducibility; this module names ePIC's public entry points only.

- Public development happens in the eic GitHub organization; the detector geometry is the epic repository (DD4hep), reconstruction is EICrecon, the data model is EDM4eic on top of EDM4hep, and eic-shell is the container environment (C08).
- The collaboration's CHEP 2023 proceedings describe the stack as combining ACTS, DD4hep, JANA2 and PODIO; that is Tier 3 context read at abstract level, and the repository pointers rest on C08 (C09).
- No release, tag, container version or schema version is recorded: a project that uses this software records the exact eic-shell image, EICrecon version and epic geometry tag in its `computational-run` artifact and in `hep-research.project.json`, never in this profile (C08).

Capability: `software-execution` is `unavailable` in `profile.json`. Nothing here installs or runs any of these tools, and no claim about their behavior is made.
