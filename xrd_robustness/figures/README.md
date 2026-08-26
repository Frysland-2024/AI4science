# Manuscript figure drafts

These are generated working figures for the frozen V9 simulated-results
manuscript. Do not edit the SVG or PNG files by hand.

From `xrd_robustness`, regenerate every figure with:

```bash
python scripts/generate_paper_figures.py
```

The script reads experiment values only from:

- `reports/validation_results.json`
- `reports/simulated_test_results.json`

Both result files contain an additive `paired_runs` block so Figures 2 and 3
can draw the five real seed pairs rather than reconstructing or inventing
points from aggregate statistics. Before writing any output, the script checks
those rows against every published mean, sample standard deviation, mean paired
delta and available positive-pair count.

Figure 1 is explicitly marked as a method schematic. Its two deterministic
spectrum sketches illustrate paired measurement variation; they are not
presented as experimental traces. Figures 2 and 3 omit the long seed IDs from
the canvas for readability, while retaining the exact `paired_runs` values and
stored order behind all plotted points.

The visual system follows the lab-meeting reference: 16:9 white canvases,
dark-navy section headers, one dominant chart, direct blue/orange comparison,
and a single bottom-line takeaway. Figure 1 borrows the pale module-box and
stage-separation vocabulary of the cited KBS method diagram while deliberately
reducing its density for presentation use.

## Figure map

1. `figure_1_method_overview`: online paired PXRD views and the matched
   Dynamic ERM / Dynamic JS objectives.
2. `figure_2_validation_paired_ood`: five paired Validation single-factor OOD
   Macro-F1 results.
3. `figure_3_simulated_test_paired_ood`: five paired frozen simulated Test
   single-factor OOD Macro-F1 results and its bootstrap interval.
4. `figure_4_metric_overview`: the four frozen simulated Test metrics. This
   panel intentionally does not place the Validation and Test worst-class
   fields side by side because their historical aggregation definitions differ.

The default outputs are editable SVG files plus PNG previews. PDF output is
available with `--formats pdf`.
