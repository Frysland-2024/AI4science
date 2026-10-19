# Experiment 2: DONUT-PXRD

**Status:** COMPLETE

## `experiment_2_shift`

| Metric | Mean over seeds | Seed SD |
|---|---:|---:|
| du_abs_error | 0.27100814 | 0.26302949 |
| dv_abs_error | 0.52567496 | 0.3779537 |
| q_mae | 0.39834155 | 0.29771186 |
| a_abs_error_angstrom | 0.0078296616 | 0.0063834465 |
| c_abs_error_angstrom | 0.024408823 | 0.019754323 |
| zero_shift_abs_error_deg | 0.051103783 | 0.010381525 |
| fwhm_abs_error_deg | 1.7881393e-09 | 0 |
| background_abs_error | 0 | 0 |
| physics_profile_rmse | 0.087719594 | 0.045896878 |
| encoder_p50_seconds | 0.0029249667 | 0.00030820418 |
| encoder_p95_seconds | 0.0047627183 | 3.0040068e-05 |

Prediction failure fraction: `0`; `n=231` sample-seed rows.

## Audits

```json
{
  "local_identifiability": {
    "parameters": [
      "du",
      "dv",
      "zero_shift_normalized"
    ],
    "local_jacobian_shape": [
      3501,
      3
    ],
    "column_norms": [
      56.34957087629248,
      19.192097269950676,
      5.609592858846094
    ],
    "column_cosine_matrix": [
      [
        1.0000000000000007,
        0.0978191489534224,
        -0.9248749591762458
      ],
      [
        0.0978191489534224,
        1.0,
        -0.09881163168033848
      ],
      [
        -0.9248749591762458,
        -0.09881163168033848,
        1.0000000000000009
      ]
    ],
    "du_shift_abs_cosine": 0.9248749591762458,
    "dv_shift_abs_cosine": 0.09881163168033848,
    "singular_values": [
      56.62342856417116,
      19.088102496135985,
      2.123663894968019
    ],
    "rank_rtol_1e-6": 3,
    "condition_number": 26.663083879864082
  },
  "signed_du_shift_error_pearson": 0.3196086060817594,
  "signed_dv_shift_error_pearson": 0.10963189682362504,
  "fixed_vs_free_lbfgsb": {
    "fixed_zero_shift": {
      "n": 77,
      "q_mae": 0.13032440551445587,
      "zero_shift_mae_deg": 0.029815580692508194,
      "profile_rmse": 0.036673817386181494,
      "success_rate": 0.987012987012987,
      "p50_seconds": 0.2584830999840051,
      "p95_seconds": 0.8017702199984342
    },
    "free_zero_shift": {
      "n": 77,
      "q_mae": 0.10243498665772394,
      "zero_shift_mae_deg": 0.012609309560858286,
      "profile_rmse": 0.01954195570069946,
      "success_rate": 1.0,
      "p50_seconds": 0.2922410999890417,
      "p95_seconds": 0.675981379998848
    }
  }
}
```
