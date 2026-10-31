"""Support package of the control-layer helper (scripts/control_layer.py; reconstruction v12 stage C1).

derivation.py is the in-memory fact log and derivation (Control §1-§6 of the v12.2 spec copy, kept structurally
close to its reference model); task_record.py is the persistent append-only task record and its JSON codec;
completion.py builds the status and completion report. The control rules did not pass the S0 spec review (obligation
N1); see the module docstrings and references/research-workflow-control.md."""
