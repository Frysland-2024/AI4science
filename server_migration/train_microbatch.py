"""One optimizer step for V11 paired views with optional memory-saving microbatches.

The scientific effective batch consists of B independent parents (2B spectra).
Microbatching changes only forward/backward memory; the CE and JS terms are
weighted by parents per microbatch so the total gradient estimates the same
per-parent mean objective as full-batch training. Clip/step happen ONCE.
"""
from __future__ import annotations

def paired_optimizer_step(
    model, optimizer, first, second, labels, *,
    lambda_js: float, microbatch_size: int,
    loss_fn, torch, F, amp: bool,
):
    n = int(labels.shape[0])
    if n < 1 or microbatch_size < 1:
        raise ValueError("Microbatch must be positive; parent batch cannot be empty")
    microbatch_size=min(microbatch_size,n)
    if int(first.shape[0]) != n or int(second.shape[0]) != n:
        raise ValueError("Paired view batch dimension mismatch")
    optimizer.zero_grad(set_to_none=True)
    totals = [0.0, 0.0, 0.0]
    for start in range(0, n, microbatch_size):
        stop = min(start + microbatch_size, n)
        weight = (stop - start) / n
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=amp):
            a = model(first[start:stop])["logits"]
            b = model(second[start:stop])["logits"]
            loss, ce, js = loss_fn(a, b, labels[start:stop], lambda_js, torch, F)
        if not bool(torch.isfinite(loss).item()):
            raise RuntimeError(f"Nonfinite paired objective in microbatch {start}:{stop}")
        (loss * weight).backward()
        for idx, value in enumerate((loss, ce, js)):
            totals[idx] += float(value.detach().cpu()) * weight
    grad_norm = torch.nn.utils.clip_grad_norm_(
        model.parameters(), max_norm=10.0, error_if_nonfinite=True
    )
    optimizer.step()
    return (*totals, float(grad_norm.detach().cpu()))
