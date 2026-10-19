"""Skill-local workflow helpers of hep-writing (plan T5-T9): audits of communication records, claim and reporting
checks, revision impact, terminology. They import contracts/ and core/ and are imported only by this skill's scripts;
nothing in contracts/ or core/ imports them (core admission rule: one consumer is not two). The shared report shape is
contracts/audit_report.py (also used by hep-literature); the literature import is hep-literature's literature_lib.
"""
