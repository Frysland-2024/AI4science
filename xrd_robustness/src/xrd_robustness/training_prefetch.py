"""Deterministic multiprocessing prefetch for online PXRD training views.

This restores the dynamic-view acceleration path that was used before the
public training surface was slimmed down.  The design keeps the scientific
stream unchanged: parameter rows are sampled in the training process, workers
only render those rows (with deterministic quality-gate retry when required),
and results are reassembled in the original batch order.
"""

from __future__ import annotations

import atexit
from dataclasses import dataclass
import hashlib
import multiprocessing as mp
import os
from pathlib import Path
import queue
import traceback
from typing import Any, Mapping, Sequence

import numpy as np

from .online_views import OnlineViewFactory
from .peak_cache import load_peak_table
from .perturbation_strategy import IndependentDynamicStrategy
from .physics import PhysicsParameterSampler, PhysicsParameters
from .view_manifest import ViewManifestRow, build_parameter_row


QUALITY_GATE_RETRY_ALGORITHM = "semantic-view-id-stride-v1"
QUALITY_GATE_MAX_ATTEMPTS = 32
QUALITY_GATE_RETRY_VIEW_STRIDE = 2

PREFETCH_SHARDING_ALGORITHM = "sha256-material-id-mod-v1"
PREFETCH_RESULT_ORDER = "absolute-step-then-batch-offset"
PREFETCH_WORKER_PEAK_CACHE = "lazy-static-shard"
PREFETCH_GENERATION = "bounded-online-per-consumed-batch-v1"
PREFETCH_WORKER_THREAD_POLICY = "fixed-native-thread-env-v1"
PREFETCH_NATIVE_THREAD_ENV_VARS = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
)


@dataclass(frozen=True)
class RenderedDynamicBatch:
    """One rendered two-view batch in the exact submitted parent order."""

    batch_key: int
    material_ids: tuple[str, ...]
    first: np.ndarray
    second: np.ndarray
    accepted_rows: tuple[ViewManifestRow, ...]
    parameters_first: tuple[PhysicsParameters, ...]
    parameters_second: tuple[PhysicsParameters, ...]
    quality_checked_count: int
    quality_rejected_count: int


def deterministic_worker_shard(material_id: str, worker_count: int) -> int:
    """Assign one parent to a stable worker independent of Python hash randomization."""

    if worker_count <= 0:
        raise ValueError("worker_count must be positive")
    digest = hashlib.sha256(str(material_id).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False) % int(worker_count)


def _paired_manifest_ids(
    rows: Sequence[ViewManifestRow],
    material_ids: Sequence[str],
) -> None:
    if len(rows) != 2 * len(material_ids):
        raise ValueError("paired rows must contain exactly two rows per material")
    for offset, material_id in enumerate(material_ids):
        first, second = rows[2 * offset : 2 * offset + 2]
        if (
            first.material_id != str(material_id)
            or second.material_id != str(material_id)
            or first.view_id != 1
            or second.view_id != 2
        ):
            raise ValueError("parameter rows do not match the submitted batch order")


def render_accepted_training_row(
    peak_table: Any,
    initial_row: ViewManifestRow,
    *,
    factory: OnlineViewFactory,
    sampler: PhysicsParameterSampler,
    profile: str,
) -> tuple[Any, ViewManifestRow]:
    """Replay one row, retrying rejected training views deterministically."""

    last_error: ValueError | None = None
    for attempt in range(QUALITY_GATE_MAX_ATTEMPTS):
        candidate = initial_row
        if attempt:
            candidate = build_parameter_row(
                initial_row.material_id,
                sampler,
                profile=profile,
                epoch=initial_row.epoch,
                global_step=initial_row.global_step,
                split=initial_row.split,
                view_id=initial_row.view_id,
                sampling_view_id=(
                    initial_row.view_id + attempt * QUALITY_GATE_RETRY_VIEW_STRIDE
                ),
            )
        try:
            return factory.make_view_from_manifest(peak_table, candidate), candidate
        except ValueError as error:
            if not str(error).startswith("quality gate rejected training view "):
                raise
            last_error = error
    raise ValueError(
        "quality gate exhausted deterministic resampling after "
        f"{QUALITY_GATE_MAX_ATTEMPTS} attempts for "
        f"{initial_row.material_id}/{initial_row.epoch}/"
        f"{initial_row.global_step}/{initial_row.view_id}: {last_error}"
    )


def _render_items(
    items: Sequence[tuple[int, str, ViewManifestRow, ViewManifestRow]],
    *,
    peak_loader: Any,
    factory: OnlineViewFactory,
    sampler: PhysicsParameterSampler,
    profile: str,
) -> tuple[list[tuple[Any, ...]], int, int]:
    checked_before = factory.quality_gate_checked_count
    rejected_before = factory.quality_gate_rejected_count
    rendered: list[tuple[Any, ...]] = []
    for offset, material_id, first_row, second_row in items:
        peak_table = peak_loader(material_id)
        first_view, accepted_first = render_accepted_training_row(
            peak_table,
            first_row,
            factory=factory,
            sampler=sampler,
            profile=profile,
        )
        second_view, accepted_second = render_accepted_training_row(
            peak_table,
            second_row,
            factory=factory,
            sampler=sampler,
            profile=profile,
        )
        rendered.append(
            (
                int(offset),
                str(material_id),
                first_view.xrd,
                second_view.xrd,
                accepted_first,
                accepted_second,
                first_view.parameters,
                second_view.parameters,
            )
        )
    return (
        rendered,
        factory.quality_gate_checked_count - checked_before,
        factory.quality_gate_rejected_count - rejected_before,
    )


def _assemble_batch(
    batch_key: int,
    material_ids: Sequence[str],
    shard_results: Sequence[tuple[Sequence[tuple[Any, ...]], int, int]],
) -> RenderedDynamicBatch:
    ordered_ids = tuple(str(value) for value in material_ids)
    by_offset: dict[int, tuple[Any, ...]] = {}
    checked = 0
    rejected = 0
    for items, shard_checked, shard_rejected in shard_results:
        checked += int(shard_checked)
        rejected += int(shard_rejected)
        for item in items:
            offset = int(item[0])
            if offset in by_offset:
                raise RuntimeError(
                    f"duplicate prefetch result offset {offset} for batch {batch_key}"
                )
            by_offset[offset] = tuple(item)
    expected_offsets = set(range(len(ordered_ids)))
    if set(by_offset) != expected_offsets:
        missing = sorted(expected_offsets.difference(by_offset))
        extra = sorted(set(by_offset).difference(expected_offsets))
        raise RuntimeError(
            f"incomplete prefetch result for batch {batch_key}: "
            f"missing={missing}, extra={extra}"
        )
    ordered = [by_offset[offset] for offset in range(len(ordered_ids))]
    observed_ids = tuple(str(item[1]) for item in ordered)
    if observed_ids != ordered_ids:
        raise RuntimeError(
            f"prefetch material order mismatch for batch {batch_key}: "
            f"expected={ordered_ids}, observed={observed_ids}"
        )
    accepted_rows = tuple(
        row for item in ordered for row in (item[4], item[5])
    )
    _paired_manifest_ids(accepted_rows, ordered_ids)
    return RenderedDynamicBatch(
        batch_key=int(batch_key),
        material_ids=ordered_ids,
        first=np.stack([item[2] for item in ordered]),
        second=np.stack([item[3] for item in ordered]),
        accepted_rows=accepted_rows,
        parameters_first=tuple(item[6] for item in ordered),
        parameters_second=tuple(item[7] for item in ordered),
        quality_checked_count=checked,
        quality_rejected_count=rejected,
    )


def _worker_main(
    worker_id: int,
    worker_count: int,
    input_queue: Any,
    output_queue: Any,
    *,
    data_root: str,
    peak_cache_name: str,
    sampler_config: Mapping[str, Any],
    quality_gate: bool,
    quality_gate_config: Mapping[str, Any],
    simulation_config_hash: str,
    profile: str,
    worker_native_threads: int,
) -> None:
    expected_threads = str(int(worker_native_threads))
    mismatched_thread_limits = {
        name: os.environ.get(name)
        for name in PREFETCH_NATIVE_THREAD_ENV_VARS
        if os.environ.get(name) != expected_threads
    }
    if mismatched_thread_limits:
        raise RuntimeError(
            "prefetch worker native-thread limits were not inherited: "
            f"{mismatched_thread_limits}"
        )

    sampler = PhysicsParameterSampler.from_mapping(sampler_config)
    strategy = IndependentDynamicStrategy(sampler, config_hash=simulation_config_hash)
    factory = OnlineViewFactory(
        sampler,
        quality_gate=quality_gate,
        quality_gate_config=quality_gate_config,
        strategy=strategy,
    )
    peak_root = Path(data_root) / "mp_processed" / peak_cache_name
    peak_cache: dict[str, Any] = {}

    def peak_loader(material_id: str) -> Any:
        if deterministic_worker_shard(material_id, worker_count) != worker_id:
            raise RuntimeError(
                f"material {material_id} was routed to worker {worker_id} outside its shard"
            )
        if material_id not in peak_cache:
            peak_cache[material_id] = load_peak_table(
                peak_root / f"{material_id}.npz"
            )
        return peak_cache[material_id]

    while True:
        task = input_queue.get()
        if task is None:
            return
        batch_key, items = task
        try:
            rendered, checked, rejected = _render_items(
                items,
                peak_loader=peak_loader,
                factory=factory,
                sampler=sampler,
                profile=profile,
            )
            output_queue.put(
                (batch_key, worker_id, True, (rendered, checked, rejected))
            )
        except BaseException:
            output_queue.put(
                (batch_key, worker_id, False, traceback.format_exc())
            )


class DynamicBatchPrefetcher:
    """Persistent deterministic process workers for bounded online rendering."""

    def __init__(
        self,
        *,
        worker_count: int,
        worker_native_threads: int,
        prefetch_batches: int,
        start_method: str,
        data_root: str | Path,
        peak_cache_name: str,
        sampler_config: Mapping[str, Any],
        quality_gate: bool,
        quality_gate_config: Mapping[str, Any],
        simulation_config_hash: str,
        profile: str,
    ) -> None:
        if worker_count <= 0:
            raise ValueError("worker_count must be positive")
        if worker_native_threads <= 0:
            raise ValueError("worker_native_threads must be positive")
        if prefetch_batches <= 0:
            raise ValueError("prefetch_batches must be positive")
        if start_method != "spawn":
            raise ValueError("deterministic prefetch requires spawn")

        self.worker_count = int(worker_count)
        self.worker_native_threads = int(worker_native_threads)
        self.prefetch_batches = int(prefetch_batches)
        self.quality_gate_checked_count = 0
        self.quality_gate_rejected_count = 0
        self._closed = False
        self._submitted: dict[int, tuple[str, ...]] = {}
        self._received: dict[int, dict[int, tuple[Any, ...]]] = {}

        context = mp.get_context(start_method)
        self._output_queue = context.Queue()
        self._input_queues = [
            context.Queue(maxsize=prefetch_batches)
            for _ in range(worker_count)
        ]
        worker_kwargs = {
            "data_root": str(Path(data_root).resolve()),
            "peak_cache_name": str(peak_cache_name),
            "sampler_config": dict(sampler_config),
            "quality_gate": bool(quality_gate),
            "quality_gate_config": dict(quality_gate_config),
            "simulation_config_hash": str(simulation_config_hash),
            "profile": str(profile),
            "worker_native_threads": self.worker_native_threads,
        }
        self._processes = []
        previous_thread_limits = {
            name: os.environ.get(name) for name in PREFETCH_NATIVE_THREAD_ENV_VARS
        }
        try:
            for name in PREFETCH_NATIVE_THREAD_ENV_VARS:
                os.environ[name] = str(self.worker_native_threads)
            for worker_id, input_queue in enumerate(self._input_queues):
                process = context.Process(
                    target=_worker_main,
                    args=(
                        worker_id,
                        worker_count,
                        input_queue,
                        self._output_queue,
                    ),
                    kwargs=worker_kwargs,
                    name=f"xrd-dynamic-prefetch-{worker_id}",
                )
                process.start()
                self._processes.append(process)
        finally:
            for name, previous in previous_thread_limits.items():
                if previous is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = previous
        atexit.register(self.close)

    @property
    def in_flight_batches(self) -> int:
        return len(self._submitted)

    def submit(
        self,
        batch_key: int,
        material_ids: Sequence[str],
        rows: Sequence[ViewManifestRow],
    ) -> None:
        if self._closed:
            raise RuntimeError("cannot submit to a closed prefetcher")
        key = int(batch_key)
        if key in self._submitted or key in self._received:
            raise ValueError(f"duplicate prefetch batch key: {key}")
        if self.in_flight_batches >= self.prefetch_batches:
            raise RuntimeError(
                f"prefetch window exceeded: {self.in_flight_batches} >= "
                f"{self.prefetch_batches}"
            )
        ordered_ids = tuple(str(value) for value in material_ids)
        _paired_manifest_ids(rows, ordered_ids)
        shards: list[
            list[tuple[int, str, ViewManifestRow, ViewManifestRow]]
        ] = [[] for _ in range(self.worker_count)]
        for offset, material_id in enumerate(ordered_ids):
            worker_id = deterministic_worker_shard(
                material_id, self.worker_count
            )
            shards[worker_id].append(
                (
                    offset,
                    material_id,
                    rows[2 * offset],
                    rows[2 * offset + 1],
                )
            )
        self._submitted[key] = ordered_ids
        for worker_id, items in enumerate(shards):
            self._input_queues[worker_id].put((key, items))

    def _raise_if_worker_died(self) -> None:
        dead = [
            f"{process.name}(exitcode={process.exitcode})"
            for process in self._processes
            if not process.is_alive()
        ]
        if dead:
            raise RuntimeError(
                f"dynamic prefetch worker exited unexpectedly: {', '.join(dead)}"
            )

    def get(self, batch_key: int) -> RenderedDynamicBatch:
        key = int(batch_key)
        if key not in self._submitted:
            raise KeyError(f"prefetch batch was not submitted: {key}")
        while len(self._received.get(key, {})) < self.worker_count:
            try:
                received_key, worker_id, succeeded, payload = (
                    self._output_queue.get(timeout=1.0)
                )
            except queue.Empty:
                self._raise_if_worker_died()
                continue
            received_key = int(received_key)
            worker_id = int(worker_id)
            bucket = self._received.setdefault(received_key, {})
            if worker_id in bucket:
                raise RuntimeError(
                    f"duplicate result from worker {worker_id} for batch "
                    f"{received_key}"
                )
            if not succeeded:
                raise RuntimeError(
                    f"dynamic prefetch worker {worker_id} failed for batch "
                    f"{received_key}:\n{payload}"
                )
            bucket[worker_id] = payload

        ordered_ids = self._submitted.pop(key)
        completed = self._received.pop(key)
        result = _assemble_batch(
            key,
            ordered_ids,
            [completed[worker_id] for worker_id in range(self.worker_count)],
        )
        self.quality_gate_checked_count += result.quality_checked_count
        self.quality_gate_rejected_count += result.quality_rejected_count
        return result

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for input_queue, process in zip(
            self._input_queues, self._processes, strict=True
        ):
            if process.is_alive():
                try:
                    input_queue.put_nowait(None)
                except queue.Full:
                    pass
        for process in self._processes:
            process.join(timeout=5.0)
        for process in self._processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5.0)
        for item in (*self._input_queues, self._output_queue):
            try:
                item.close()
            except (AttributeError, OSError, ValueError):
                pass
