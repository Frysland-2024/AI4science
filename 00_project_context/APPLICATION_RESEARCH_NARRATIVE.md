# Application Research Narrative

**Updated:** 2026-08-23

**Claim boundary:** the completed work is robust seven-class PXRD
classification. The simulated Validation/Test evidence is frozen; RRUFF-301 is
retrospective validation because its historical execution provenance is
incomplete.

## Research story

I began with a practical materials-ML problem: classifiers trained on simulated
powder X-ray diffraction patterns can be brittle when peak position, width,
preferred orientation, background, or noise changes. The project gradually
became a more general machine-learning question: can information retained by a
scientific simulator provide supervision beyond ordinary class labels?

The first phase taught me to separate foundation failures from method failures.
A peak-aware Transformer-style backbone did not learn the base task reliably,
whereas a matched ResNet-18-GN did. I also explored residual decorrelation and
measurement-supervised residual objectives. Those mechanisms did not establish
the preregistered stable signal, so I closed the branches instead of repeatedly
tuning them. These negative results narrowed the project to one testable idea.

For a parent structure `s`, the simulator generates views `x = g(s, m)` under
different measurement conditions `m`. Two views from the same parent share more
than a crystal-system label: they are measurements of the same latent physical
object. I used this parent provenance as measurement-equivalence supervision by
adding Jensen-Shannon prediction consistency to a matched Dynamic ERM design.
The comparison held the parent structures, perturbation distribution, backbone,
optimization and two-view data exposure fixed.

Across five matched training-seed pairs, JS consistency improved Validation
mean single-factor OOD Macro-F1 by `+0.046569`; all five paired effects were
positive. The already selected checkpoints then produced a `+0.054600` mean
paired improvement on the locked simulated Test, again with five of five effects
positive. The evidence supports an aggregate robustness claim, not universal
improvement for every class or condition.

Stored RRUFF-301 artifacts provide useful external-domain retrospective
validation. At K=1/2/5 shots per class, the recorded JS-minus-ERM Macro-F1
deltas are `+0.0433`, `+0.0460`, and `+0.0545`, with 68 of 75 paired comparisons
positive. The artifacts pass their declared integrity checks, but the historical
runner, support IDs, execution authorization and complete runtime binding are
unavailable. I therefore describe this result as retrospective rather than
prospective or confirmatory.

The project changed how I evaluate research progress. A useful result is not
merely a favorable score; it is a scoped claim whose data split, access boundary,
negative results, corrections and provenance can survive review. It also shifted
my interests from applying standard models to materials data toward robust and
data-efficient learning for scientific measurements.

## Application version (about 150 words)

My research began with a practical PXRD problem: classifiers trained on
simulated diffraction patterns can fail when experimental peak shifts,
broadening, texture, background and noise alter the measurement distribution.
Early failures helped me distinguish foundation problems from method problems:
a peak-aware backbone was a learnability bottleneck, while a residual mechanism
did not satisfy its registered stability gate. These negative results led to a
simpler question. An online simulator knows that two perturbed spectra come from
the same parent crystal, so can that provenance become supervision? I compared
matched Dynamic ERM and Jensen-Shannon consistency training under identical data
exposure. Across five paired seeds, consistency improved simulated OOD
robustness, and the locked simulated Test preserved the direction. Stored
RRUFF-301 artifacts also show more label-efficient few-shot adaptation, although
incomplete historical provenance limits this to retrospective validation. The
project taught me to convert physical data-generation relationships into
auditable ML hypotheses and to close attractive branches when evidence does not
support them.

## Interview version

I started by making simulated XRD classifiers robust to measurement shifts. The
key insight was that a simulator provides relationships, not only more samples:
it knows which spectra are different measurements of the same parent crystal. I
turned that provenance into a consistency objective and compared it fairly with
matched dynamic ERM. Five-seed Validation and a locked simulated Test both
showed aggregate robustness gains. RRUFF artifacts suggest better few-shot
transfer, but I explicitly limit that result to retrospective evidence because
the historical execution chain is incomplete.

## Safe claim language

Use:

- “I reframed simulator provenance as measurement-equivalence supervision.”
- “I used paired, access-controlled simulation experiments and reported failed
  branches as part of the research record.”
- “The locked simulated Test supports an aggregate robustness improvement.”
- “RRUFF-301 provides retrospective external-domain validation.”

Avoid:

- “I invented consistency regularization.”
- “I solved PXRD simulation-to-experiment transfer.”
- “The split is formula- or family-disjoint.”
- “RRUFF-301 is prospective confirmatory evidence.”
- “The method improves every crystal system or measurement condition.”
