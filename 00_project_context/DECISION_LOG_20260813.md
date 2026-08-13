# Project Decision Log — 2026-08-13

## RRUFF-301 rerun priority

The reason rerunning RRUFF-301 is **not important** is **not** that the project is temporarily not pursuing publication.

After discussion with the advisor, the working judgment is that, in the context of materials-science research and materials-journal evaluation, formal evidence-governance machinery such as file hashes, execution-provenance chains, pre-execution authorization records, and similarly strict reproducibility bookkeeping is not a central scientific contribution or a core evidentiary requirement. These should be retained as **internal engineering hygiene**, but they should not be treated as a research contribution or as a scientific shortcoming that must be repaired by rerunning the experiment.

The project should instead prioritize whether:

1. the scientific conclusion itself is valid;
2. the experimental design is sensible and interpretable;
3. the observed effect is stable rather than a fragile one-off result;
4. the overall scientific story is coherent and complete.

Under that priority system, the existing RRUFF-301 result is already useful because it provides a stable real-domain few-shot signal across K=1/2/5 and across matched comparisons. Repeating the same experiment merely to upgrade hashes, execution lineage, or formal provenance would have low scientific value and should not be treated as a project priority.

A new real-domain experiment should only be run if it answers a genuinely new scientific question, tests robustness in a materially different setting, or otherwise strengthens the scientific conclusion itself—not merely to repair formal provenance bookkeeping.
