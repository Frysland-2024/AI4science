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


## 2026-10-23 direction reconciliation

- Reorganized the root README around the sole active seven-crystal-system classification task, its completed evidence, exactly three evaluation axes, and the future scale-up sequence.
- Updated the supervisor guide, current state, research decision, and agent rules so quantitative inversion proposals are historical and inactive.
- Preserved completed figures and scientific evidence. The prior slide 13 and presentation PDF/PowerPoint are retained byte-for-byte under paths that identify them as historical; use the README and dated scale-up plan for current work.
- No model, frozen configuration, experiment data, scientific result, or simulator code was changed. No training or data acquisition was started.
- Validation: all modified Markdown links and embedded image targets were checked against the tracked repository tree. Binary presentation pages and image contents were not visually inspected in this update; original bytes were preserved. The checkout was not available in the current execution environment, so local pytest and git diff --check could not be run here. The main-branch XRD workflow is a CPU test job triggered by README changes; it does not run GPU training.
