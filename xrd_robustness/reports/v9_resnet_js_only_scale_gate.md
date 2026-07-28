# V9 ResNet JS-only scale Gate

Status: `pass`.

| JS lambda | Measurement basis | Median auxiliary/classification gradient ratio | Band | Maximum combined/classification ratio | Median combined direction cosine |
|---:|---|---:|---|---:|---:|
| 3 | direct Train-only autograd trace | 0.087859 | weak | 1.095721 | 0.996205 |
| 30 | direct Train-only autograd trace | 0.877058 | material non-dominant | 2.688685 | 0.773968 |
| 60 | exact scalar rescaling of the lambda-30 trace | 1.754115 | dominant | 4.810521 | 0.550031 |

All finite-value, nonzero-gradient, combined-direction, and maximum single-batch
runaway guards passed. The JS candidate range is frozen as `[3,30,60]`.

This was a Train-only scale audit. It did not train candidates, load a
checkpoint, access Validation/Test/real XRD, or start the proposed four-run
tuning stage. Four-run execution remains disabled pending separate explicit
authorization. Residual-v1 remains archived.
