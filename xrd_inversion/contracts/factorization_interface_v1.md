# Factorization interface v1

**Status:** frozen after the successful Stage-1 tiny-overfit Gate recorded in
the current run provenance. A later semantic change requires a new interface
version, new dataset manifest, and regenerated dependent artefacts.

## 1. Scope and canonical orders

This contract covers only the Train-only, known-phase, single-phase,
conventional-tetragonal factorization Pilot. Validation, Test, real spectra,
refinement, forward reconstruction loss, and independent-renderer outcomes are
outside this interface.

The renderer vector and model heads are:

```text
q       = [q_u, q_v, q_delta, q_w]       shape (..., 4)
theta_s = [q_u, q_v]                     shape (..., 2)
theta_m = [q_delta, q_w]                 shape (..., 2)
```

`theta_s` and `theta_m` are exact q slices. Interface v1 applies no hidden
second standardization. Canonical NumPy q, labels, decoded parameters, metrics,
and handoff predictions are `float64`; finite values are mandatory. Training
features, Torch parameters, and model outputs are `float32`, then explicitly
cast to `float64` before canonical metrics or handoff serialization.

Physical order and units are fixed as:

```text
[a_angstrom, c_angstrom, delta_2theta_deg, fwhm_deg]
```

## 2. q encode/decode

For a parent reference cell `(a0,c0)`, all lattice lengths are numerical values
in angstrom:

```text
u0    = (2 ln(a0) + ln(c0)) / 3
v0    = ln(c0 / a0)
u_abs = (2 ln(a)  + ln(c))  / 3
v_abs = ln(c / a)

q_u     = (u_abs - u0) / du_half_range
q_v     = (v_abs - v0) / dv_half_range
q_delta = delta_2theta_deg / delta_half_range_deg

log_center     = (ln(fwhm_min_deg) + ln(fwhm_max_deg)) / 2
log_half_range = (ln(fwhm_max_deg) - ln(fwhm_min_deg)) / 2
q_w            = (ln(fwhm_deg) - log_center) / log_half_range
```

Inverse decode is:

```text
u_abs = u0 + q_u * du_half_range
v_abs = v0 + q_v * dv_half_range
a     = exp(u_abs - v_abs / 3)
c     = exp(u_abs + 2 v_abs / 3)
delta_2theta_deg = q_delta * delta_half_range_deg
fwhm_deg         = exp(log_center + q_w * log_half_range)
```

The implementation API in `xrd_inversion.parameterization` is:

```python
encode_q(physical, *, reference_a_angstrom, reference_c_angstrom,
         parameter_config) -> float64[..., 4]
decode_q(q, *, reference_a_angstrom, reference_c_angstrom,
         parameter_config) -> float64[..., 4]
split_q(q) -> (theta_s, theta_m)
compose_q(theta_s, theta_m) -> q
resolve_reference_q(parameter_config, factorial_config=None) -> float64[4]
```

All functions preserve leading dimensions, reject wrong final dimensions and
non-finite values, and use exact matching leading shapes for `compose_q`.
Encoding/decoding is performed per parent because `(a0,c0)` is parent-specific.

## 3. Parent reference profile

`x_ref` must use the config value `factorial.reference_q`, cross-checked against
`parameterization.nominal_q`; the two must match exactly in v1. The currently
frozen value is:

```text
q_ref = [0.0, 0.0, 0.0, -1.0]
```

Thus `x_ref` uses the parent lattice, zero 2-theta shift, and the minimum frozen
FWHM of `0.08 deg`. It is deliberately **not** `[0,0,0,0]`; `q_w=0` would use
the geometric-centre FWHM `sqrt(0.08*0.20)` and would silently change the
reference-conditioned task.

The reference profile is rendered once per parent with the same axis and
`gpu_forward_compatibility_false` view as observations.

## 4. Profile input contract

Let the max-normalized renderer profile be `p` and define:

```text
T(p) = log1p(100 p) / log(101)
```

For each spectrum:

```text
obs  = T(p_obs)
ref  = T(p_ref)
diff = obs - ref
input = stack([obs, ref, diff], channel axis)
```

Do not compute `T(p_obs-p_ref)`. Shapes and dtypes are:

```text
single spectrum: [3, L]       float32
factorial block: [2, 2, 3, L]       float32
training batch:  [B, 2, 2, 3, L]    float32
flattened compatible view: [B, 4, 3, L] float32
```

Before the explicit `float64 -> float32` cast, rendered/transformed arrays must
be checked for shape and finite values. `L` is the frozen grid length and must
be identical for observation and reference.

## 5. Factorial axes and corner order

The immutable flattened corner order is:

```text
[x11, x12, x21, x22]
```

The first index is structure state and the second is measurement state:

```text
x11 -> [structure=0, measurement=0]
x12 -> [structure=0, measurement=1]
x21 -> [structure=1, measurement=0]
x22 -> [structure=1, measurement=1]
```

For a flattened prediction `[B,4,2]`, C-order reshape produces
`[B,2,2,2]`, indexed as `[batch, structure, measurement, parameter]`.
Equivalently, flattened corner index is `2*structure + measurement`. No code
may swap these axes or use lexical/dictionary iteration to infer corner order.

## 6. Handoff artefacts

Every artefact records the interface version, config SHA-256, dataset-manifest
SHA-256, parameter/corner orders, profile transform, reference q, source hashes,
and Train-only boundary.

- `factorization_pilot_manifest.json`: selected parent IDs and fingerprints;
  parent `(a0,c0)`; block/state IDs and train-internal role; all q states;
  corner order; grid; renderer view; reference q; deterministic seeds.
- `factorial_eval_manifest.json`: the four held-out intervention blocks per
  Train parent. This is Train-parent internal sanity evaluation, not Validation
  or Test evidence.
- `checkpoint.pt`: model kind, seed, fixed final step, model/optimizer state,
  interface/config/manifest hashes, and exact output order. Checkpoints are not
  selected using the internal evaluation blocks.
- `prediction_dump.npz`: canonical `pred_s` and `pred_m` with shape
  `[N,2,2,2]`; `true_s` and `true_m` state tables with shape `[N,2,2]`;
  `parent_id`, `block_id`, corner order, reference q, and hashes. Predictions
  are detached and serialized as finite `float64` after the fixed reshape in
  Section 5.

## 7. Stage-1 freeze Gate

Before Stage-1 tiny-overfit PASS, only implementation defects may be repaired;
parameter order, q equations, reference q, profile channels, corner order, and
artefact schemas may not be tuned against outcomes. PASS requires the
pre-registered tiny parameter-MSE, paired-invariance-MSE, and loss-reduction
thresholds in the frozen config. At PASS, record the config, source, interface,
and tiny-manifest hashes and mark interface v1 frozen. Any subsequent semantic
change starts v2 and invalidates dependent v1 datasets/checkpoints.
