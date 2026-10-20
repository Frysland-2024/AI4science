# Supervisor showcase changelog — 2026-10-20

## Changes

- Rewrote the root README as an English-first 2–4 minute project overview. It retains the method and simulated-OOD figures and adds the absolute parent-budget learning curve and a compact four-result summary.
- Added a reproducible plotting script that reads the archived parent-budget JSON; the plotted points are absolute OOD Macro-F1, with sample-SD error bars.
- Added a supervisor reading path and separated research-role details into a linked document. The full parent-budget protocol and negative savings assessment remain in the existing report.
- No frozen protocol, raw result, test data, model, or scientific metric was changed.

## Validation

- Figure regeneration: <code>python xrd_robustness/scripts/generate_showcase_parent_budget_figure.py</code>.
- Local Markdown targets and fragments: 75 checked across five Markdown files, all resolved. Method/result figures, workflow badge target, and manuscript target exist in the checkout.
- Figure regeneration produced a 2,240 x 1,360 PNG. The relevant pytest figure-contract check could not run because the configured Python 3.11 environment has no pytest module. `git diff --check` passed.

## Caveats

- The parent-budget supplement is post-main, uses the previously evaluated simulated Test, and supports same-budget Macro-F1 improvement only; it does not demonstrate structure-count savings.
- Live PR metadata could not be queried during this update because the saved <code>gh</code> token was invalid and unauthenticated requests were unavailable. Per the task brief, the partial inversion benchmark in PR #46 is unmerged and is not represented as main-branch evidence.
