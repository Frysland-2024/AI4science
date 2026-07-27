# Gate 3 ML4pXRDs source-to-port map

**Status:** implementation record for the preregistered Foundation Gate 3  
**Operational model:** ML4pXRDs ResNet-18 with GroupNorm  
**Port:** `src/xrd_robustness/models/ml4pxrd_resnet1d.py`

## Audited source

The implementation was read directly from the uploaded archive `ML4pXRDs-master.zip`.

| Artifact | SHA-256 |
|---|---|
| `ML4pXRDs-master.zip` | `530115878e64a08afa9f4ada31dcad611f4ba8d218e6d15968bdd1297bebbc9e` |
| `training/utils/resnet_keras_1D.py` | `60ea9cbf2e1d268ec48a20482ee3b6b7e5455d9c59839c2ec25c5c49a775759c` |
| `training/models.py` | `8c1949cec99851750d5bdfa4b23d1c739691e5d050cea1f044ee26c4008b1a99` |
| `training/train_classifier.py` | `57c87c54f77f8d4d017295ef6ade8ed73ec09697d6217f6c318d276d4bea367e` |

The source architecture is taken from `ResNet`, `ResidualBlock`, `RESNET_SPECS`, and `build_model_resnet_i`. The first Gate-3 run does **not** copy the source training-data generator, square-root preprocessing, Adam optimizer, or long learning-rate schedule because the registered comparison changes the backbone only.

## Exact architecture mapping

| Source decision | ML4pXRDs source | PyTorch port |
|---|---|---|
| Input layout | Keras `[batch, length, 1]` | Accepts `[batch, length]` or `[batch, 1, length]` |
| Stem | Conv1D 64, kernel 7, stride 2, `same`, no bias | `_SamePadConv1d(1, 64, 7, 2, bias=False)` |
| Stem norm | TensorFlow Addons GroupNormalization, default 32 groups, epsilon 0.001 | `nn.GroupNorm(32, 64, eps=1e-3)` |
| Stem activation | ReLU | ReLU |
| Stem pool | MaxPool1D kernel 3, stride 2, `same` | `_SamePadMaxPool1d(3, 2)` |
| ResNet-18 stages | `(64,2), (128,2), (256,2), (512,2)` | Same four stage specifications |
| Basic-block kernel | `3**2 = 9` because `square_kernel_size_and_stride=True` | Kernel 9 in both block convolutions |
| Stage downsampling | First stage stride 1; later stages `2**2 = 4` | First stage stride 1; stages 2–4 stride 4 |
| Projection shortcut | Conv1D kernel 1, stage stride, no bias, then GroupNorm | Same |
| Block order | Conv–GN–ReLU–Conv–GN–add–ReLU | Same post-activation order |
| Padding | Keras `same`, output length `ceil(L/stride)` | Explicit asymmetric TensorFlow-compatible padding |
| Final map | Last stage tensor | Same |
| Head flatten | `Flatten()` | `torch.flatten(features, 1)` |
| Additional dense | `Dense(256)` | `nn.Linear(flattened, 256)` |
| Dense activation | None in source | None |
| Classifier | `Dense(number_of_output_labels)` | `nn.Linear(256, 7)` |
| Conv initialization | Keras `VarianceScaling` default: fan-in truncated normal | Corrected truncated-normal fan-in initialization |
| Dense initialization | Keras Dense default Glorot uniform | Xavier uniform |
| Output API | Keras logits | Project-compatible dict with logits, pooled embedding, feature tokens, and no prior tokens |

For the current input length 3501, the source stride policy gives the sequence:

`3501 -> 1751 -> 876 -> 876 -> 219 -> 55 -> 14`

The final feature tensor is therefore `512 x 14`, followed by the linear 256-unit layer and seven-class output.

## Deliberate non-architectural differences

1. Framework changes from TensorFlow/Keras to PyTorch.
2. Input is channel-first internally.
3. The model returns the project `BackboneOutput` mapping so the existing audited trainer, evaluation panels, checkpoint code, and early stopping can be reused.
4. Gate 3 keeps the PAMPT experiment's AdamW optimizer, learning rate, weight decay, input normalization, data split, exposure budget, and evaluation contract.
5. The source square-root preprocessing, Adam optimizer, source learning-rate schedule, source class sampling, and longer training are excluded from the backbone-only Gate. They remain optional one-factor follow-ups after Gate 3 is interpreted.

## Safety and interpretation

The full run is blocked unless `gate3_resnet_sanity.py` verifies:

- deterministic initialization;
- finite forward, loss, and gradients on a real rendered Train batch;
- effective batch size 16 fits memory;
- at least 95% accuracy on a frozen 32-structure Train-only level0 subset.

Failure of the tiny-set gate is an implementation or optimization failure. It cannot be interpreted as evidence about the scientific task.
