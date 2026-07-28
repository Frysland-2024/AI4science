# Archived PAMPT V9 method-parameter gates (2026-07)

This directory preserves the PAMPT-B3 learned-state, loss/gradient-scale, and candidate-grid gate implementation and evidence.

- Archive date: 2026-07-28
- Status: historical, non-executable
- Reason: JS/Residual feature and gradient scales are backbone-dependent. The PAMPT qualification of JS `[0.3, 3, 30]` and Residual `[0.2, 2, 20]` is not evidence for ResNet-18-GN.

The backbone-independent loss semantics audit remains active. A new ResNet Train-only learned-state and scale gate is required before Validation tuning.
