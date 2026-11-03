"""Deterministic, bounded V11 CPU rendering prefetch shared by training and validation.

Reuses the repository's SHA256 worker sharding, fixed native-thread policy,
parent-first Dynamic JS sampling, PeakTable cache, and the exact V11 factory.
Workers never touch CUDA; the main process owns all RNG sampling and GPU work.
"""
from __future__ import annotations

from collections import OrderedDict
import atexit
import multiprocessing as mp
import os
from pathlib import Path
import queue
import traceback
from typing import Any, Sequence


def _worker(
    worker_id: int,
    in_queue: Any,
    out_queue: Any,
    simulation_config: dict[str, Any],
    run_seed: int,
    max_cached_peaks: int,
) -> None:
    # The parent sets OMP/MKL/BLAS env limits BEFORE spawn. Imports follow.
    import numpy as np
    from xrd_robustness.physics import PhysicsParameterSampler
    from xrd_robustness.training.runner import build_online_view_factory
    from xrd_robustness.peak_cache import load_peak_table

    config = {**simulation_config, "run_seed": int(run_seed)}
    sampler = PhysicsParameterSampler.from_mapping(config)
    factory, version, _ = build_online_view_factory(sampler, config)
    if version != "v11_tch_pseudo_voigt":
        raise ValueError("V11 prefetch worker requires V11 renderer")
    cache: OrderedDict[str, Any] = OrderedDict()

    def load(material_id: str, file_path: str) -> Any:
        cached = cache.get(material_id)
        if cached is not None:
            cache.move_to_end(material_id)
            return cached
        value = load_peak_table(Path(file_path))
        cache[material_id] = value
        if len(cache) > max_cached_peaks:
            cache.popitem(last=False)
        return value

    while True:
        task = in_queue.get()
        if task is None:
            return
        batch_key, items = task
        try:
            results = []
            for offset, material_id, peak_path, label, split, epoch, step, profile in items:
                pair = factory.make_pair_from_peaks(
                    load(material_id, peak_path), material_id=material_id,
                    split=split, epoch=epoch, global_step=step, profile=profile,
                )
                first = np.asarray(pair.first.xrd, dtype=np.float32)
                second = np.asarray(pair.second.xrd, dtype=np.float32)
                if first.shape != (3501,) or second.shape != (3501,):
                    raise ValueError(f"Invalid V11 output length: {material_id}")
                if not np.isfinite(first).all() or not np.isfinite(second).all():
                    raise ValueError(f"Nonfinite V11 output: {material_id}")
                results.append((offset, material_id, label, first, second))
            out_queue.put((batch_key, worker_id, True, results))
        except BaseException:
            out_queue.put((batch_key, worker_id, False, traceback.format_exc()))


class V11PairPrefetchPool:
    """Persistent spawn workers; bounded in-flight batches, deterministic order.

    submit/get are explicit so the caller can overlap rendering of upcoming
    training batches with GPU forward/backprop. All parameters are sampled by
    the original V11 factory from (run_seed,parent,epoch,step,view_id), not by
    worker completion order.
    """

    def __init__(
        self, simulation_config: dict[str, Any], *, run_seed: int,
        workers: int = 4, prefetch_batches: int = 3,
        native_threads: int = 1, max_cached_peaks: int = 512,
    ) -> None:
        if min(workers, prefetch_batches, native_threads, max_cached_peaks) < 1:
            raise ValueError("All V11 prefetch resource parameters must be positive")
        if simulation_config.get("simulator_version") != "v11_tch_pseudo_voigt":
            raise ValueError("V11 prefetch received an incompatible simulator config")
        self.workers = workers
        self.prefetch_batches = prefetch_batches
        self.pending: dict[int, tuple[str, ...]] = {}
        self.received: dict[int, dict[int, Any]] = {}
        self.closed = False
        ctx = mp.get_context("spawn")
        self.output = ctx.Queue()
        self.inputs = [ctx.Queue(maxsize=prefetch_batches) for _ in range(workers)]
        from xrd_robustness.training_prefetch import PREFETCH_NATIVE_THREAD_ENV_VARS
        previous = {name: os.environ.get(name) for name in PREFETCH_NATIVE_THREAD_ENV_VARS}
        self.processes = []
        try:
            for name in previous:
                os.environ[name] = str(native_threads)
            for index in range(workers):
                proc = ctx.Process(
                    target=_worker, args=(
                        index, self.inputs[index], self.output, dict(simulation_config),
                        int(run_seed), int(max_cached_peaks),
                    ), name=f"v11-pair-worker-{index}",
                )
                proc.start()
                self.processes.append(proc)
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
        atexit.register(self.close)

    def submit(
        self, key: int, records: Sequence[Any], *,
        epoch: int, global_step: int, profile: str,
    ) -> None:
        from xrd_robustness.training_prefetch import deterministic_worker_shard
        if self.closed:
            raise RuntimeError("Prefetch pool already closed")
        if key in self.pending or key in self.received:
            raise ValueError(f"Duplicate prefetch key: {key}")
        if len(self.pending) >= self.prefetch_batches:
            raise RuntimeError("Bounded prefetch window exceeded")
        if not records:
            raise ValueError("Cannot render an empty V11 batch")
        material_ids = tuple(rec.material_id for rec in records)
        if len(set(material_ids)) != len(material_ids):
            raise ValueError("Repeated parent in single V11 batch")
        shards: list[list[Any]] = [[] for _ in range(self.workers)]
        for offset, rec in enumerate(records):
            worker = deterministic_worker_shard(rec.material_id, self.workers)
            shards[worker].append((
                offset, rec.material_id, str(rec.peak_table_path), int(rec.label),
                str(rec.split), int(epoch), int(global_step), str(profile),
            ))
        self.pending[int(key)] = material_ids
        for index in range(self.workers):
            self.inputs[index].put((int(key), shards[index]))

    def get(self, key: int) -> tuple[Any, Any, Any]:
        import numpy as np
        if key not in self.pending:
            raise KeyError(f"Missing prefetch key: {key}")
        while len(self.received.get(key, {})) < self.workers:
            try:
                batch_key, worker_id, ok, value = self.output.get(timeout=1.0)
            except queue.Empty:
                dead = [f"{p.name}:{p.exitcode}" for p in self.processes
                        if not p.is_alive()]
                if dead:
                    raise RuntimeError(f"V11 worker died: {dead}")
                continue
            slot = self.received.setdefault(int(batch_key), {})
            if worker_id in slot:
                raise RuntimeError(f"Duplicate worker reply for {batch_key}/{worker_id}")
            if not ok:
                raise RuntimeError(f"V11 worker {worker_id} failed:\n{value}")
            slot[worker_id] = value
        ids = self.pending.pop(key)
        shards = self.received.pop(key)
        ordered: dict[int, Any] = {}
        for result in shards.values():
            for item in result:
                if item[0] in ordered:
                    raise RuntimeError("Duplicate prefetch batch offset")
                ordered[item[0]] = item
        if set(ordered) != set(range(len(ids))):
            raise RuntimeError("Missing or extra V11 prefetch results")
        values = [ordered[i] for i in range(len(ids))]
        if tuple(v[1] for v in values) != ids:
            raise RuntimeError("V11 prefetch changed parent order")
        return (
            np.stack([v[3] for v in values]),
            np.stack([v[4] for v in values]),
            np.asarray([v[2] for v in values], dtype=np.int64),
        )

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        for input_queue, proc in zip(self.inputs, self.processes):
            if proc.is_alive():
                try:
                    input_queue.put_nowait(None)
                except queue.Full:
                    pass
        for proc in self.processes:
            proc.join(timeout=3.0)
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=3.0)
        for q in [*self.inputs, self.output]:
            try:
                q.close()
            except (ValueError, OSError):
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

def iter_prefetched_batches(
    pool: V11PairPrefetchPool, records: Sequence[Any], *,
    profile: str, epoch: int = 0, global_step: int = 0, batch_size: int = 64,
):
    """CPU render upcoming batches while the consumer writes/scorers use prior ones."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    next_submit = 0
    for start in range(0, len(records), batch_size):
        while (next_submit < len(records)
               and len(pool.pending) < pool.prefetch_batches):
            rows = records[next_submit:next_submit + batch_size]
            pool.submit(next_submit, rows, epoch=epoch,
                        global_step=global_step, profile=profile)
            next_submit += batch_size
        yield start, pool.get(start)

def enqueue_train_lookahead(
    pool: V11PairPrefetchPool, rng: Any, records: Sequence[Any], *,
    batch_size: int, start_step: int, next_submit: int,
    max_steps: int, committed_states: dict[int, Any],
) -> int:
    """Only the main process samples parents; save RNG state per submitted step.

    The trainer checkpoints committed_states[completed_step], NOT the advanced
    look-ahead RNG. After a restart, replaying from that state yields precisely
    the same parents/physics realizations as an uninterrupted run.
    """
    import copy

    if batch_size <= 0 or not records:
        raise ValueError("Invalid train batch sampling parameters")
    if not (0 <= start_step <= next_submit <= max_steps):
        raise ValueError("Out-of-order training prefetch step")
    while next_submit < max_steps and len(pool.pending) < pool.prefetch_batches:
        selected = rng.choice(len(records), size=batch_size, replace=False)
        batch = [records[int(index)] for index in selected]
        pool.submit(
            next_submit, batch,
            epoch=next_submit * batch_size // len(records),
            global_step=next_submit, profile="train",
        )
        committed_states[next_submit] = copy.deepcopy(rng.bit_generator.state)
        next_submit += 1
    return next_submit
