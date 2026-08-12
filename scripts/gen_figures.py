#!/usr/bin/env python3
"""Reproduce the LPDDR-PIM paper artifacts that appear in main.tex.

Two targets, matching the two artifacts in the paper:

    cross-model   Fig. cross_model_cycles     (15 decode + 14 prefill configs,
                  cold-start vs steady-state).  Data: decode_prefill_cycles_parts/
    pim-sharing   Table tab:pim-sharing        (per-bank b=1 vs shared b=2).
                  Data: pim_sharing_parts/

Usage:
    python scripts/gen_figures.py --collect cross-model --workers 64
    python scripts/gen_figures.py --render cross-model
    python scripts/gen_figures.py --all --workers 64
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import NotRequired, TypedDict

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RAMULATOR2_DIR = PROJECT_ROOT / "ramulator2"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(RAMULATOR2_DIR / "python"))
sys.path.insert(0, str(RAMULATOR2_DIR))

from ramulator.pimscope import validate_aggregate  # noqa: E402

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results"
DECODE_JSON = "decode_cycles.json"
PREFILL_JSON = "prefill_cycles.json"
PIM_SHARING_JSON = "pim_sharing_comparison.json"
CROSS_MODEL_PARTS_DIRNAME = "decode_prefill_cycles_parts"
PIM_SHARING_PARTS_DIRNAME = "pim_sharing_parts"

MODES = ("steady_state", "cold_start")

CACHE_SCHEMA_VERSION = 1
ESTIMATED_WORKER_MEMORY_BYTES = 1 << 30


class ReplayResult(TypedDict, total=False):
    """Replay fields consumed while assembling stable artifact schemas."""

    replay_ok: bool
    cycles: int
    runtime_ns: float
    pim_mac_issued: int
    pim_bcast_issued: int
    opcode_counts: dict[str, int]
    pim_shared_block_stalls: int


class ReplayTask(TypedDict):
    """Serializable description of one isolated simulator replay."""

    model_key: str
    phase: str
    materialize_weights: bool
    part_path: str
    pim_cfg_override: dict
    max_inflight_requests: int
    mac_mode: str
    past_len: NotRequired[int]
    prompt_len: NotRequired[int]
    mode: NotRequired[str]
    pim_label: NotRequired[str]


def _make_replay_task(
    *,
    model_key: str,
    phase: str,
    part_path: Path,
    pim_cfg_override: dict,
    materialize_weights: bool,
    **dimensions: int | str,
) -> ReplayTask:
    return ReplayTask(
        model_key=model_key,
        phase=phase,
        materialize_weights=materialize_weights,
        part_path=str(part_path),
        pim_cfg_override=pim_cfg_override,
        max_inflight_requests=16,
        mac_mode="per_kind",
        **dimensions,
    )


def _git_revision(repo: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


@lru_cache(maxsize=None)
def _source_fingerprint(repo: Path) -> str:
    try:
        diff = subprocess.check_output(
            ["git", "-C", str(repo), "diff", "--binary", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        diff = b""
    payload = _git_revision(repo).encode() + b"\0" + diff
    return hashlib.sha256(payload).hexdigest()


def _installed_versions() -> dict[str, str]:
    versions = {}
    for package in ("pimscope", "ramulator", "numpy", "matplotlib", "PyYAML"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def _source_timestamp() -> tuple[str, str]:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    source = "SOURCE_DATE_EPOCH"
    if epoch is None:
        source = "pimscope_commit"
        try:
            epoch = subprocess.check_output(
                ["git", "-C", str(PROJECT_ROOT), "show", "-s", "--format=%ct", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            epoch = "0"
            source = "unix_epoch_fallback"
    try:
        timestamp = datetime.fromtimestamp(int(epoch), UTC).isoformat()
    except (ValueError, OverflowError) as exc:
        raise ValueError("SOURCE_DATE_EPOCH must be an integer Unix timestamp") from exc
    return timestamp, source


def _provenance(**extra) -> dict:
    generated_at, timestamp_source = _source_timestamp()
    return {
        "generated_at": generated_at,
        "timestamp_source": timestamp_source,
        "generator": "scripts/gen_figures.py",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "python_packages": _installed_versions(),
        "pimscope_commit": _git_revision(PROJECT_ROOT),
        "ramulator2_commit": _git_revision(RAMULATOR2_DIR),
        "pimscope_source_fingerprint": _source_fingerprint(PROJECT_ROOT),
        "ramulator2_source_fingerprint": _source_fingerprint(RAMULATOR2_DIR),
        **extra,
    }


def _cache_fingerprint(task: dict) -> str:
    cache_task = {k: v for k, v in task.items() if k != "part_path"}
    payload = {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "task": cache_task,
        "pimscope_source_fingerprint": _source_fingerprint(PROJECT_ROOT),
        "ramulator2_source_fingerprint": _source_fingerprint(RAMULATOR2_DIR),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _part_cache_matches(path: Path, task: dict) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return data.get("_cache", {}).get("fingerprint") == _cache_fingerprint(task)


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _write_aggregate_json(path: Path, payload: dict, *, kind: str) -> None:
    validate_aggregate(payload, kind=kind)
    _write_json(path, payload)


def _write_part(result: ReplayResult, task: ReplayTask) -> None:
    payload = dict(result)
    payload["_cache"] = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "fingerprint": _cache_fingerprint(task),
    }
    _write_json(Path(task["part_path"]), payload)


# ── cross-model — decode + prefill cycles (cold-start vs steady-state) ──

CROSS_MODEL_DECODE_MODELS = (
    "llama2-7b",
    "llama2-13b",
    "llama2-70b",
    "opt-125m",
    "opt-350m",
    "opt-1.3b",
    "qwen25-7b",
    "qwen25-14b",
    "qwen25-32b",
    "qwen25-72b",
    "gemma-2b",
    "gemma-7b",
    "gemma2-9b",
    "gemma2-27b",
    "mixtral-8x7b",
)
CROSS_MODEL_PREFILL_MODELS = (
    "llama2-7b",
    "llama2-13b",
    "llama2-70b",
    "opt-125m",
    "opt-350m",
    "opt-1.3b",
    "qwen25-7b",
    "qwen25-14b",
    "qwen25-32b",
    "qwen25-72b",
    "gemma-2b",
    "gemma-7b",
    "gemma2-9b",
    "gemma2-27b",
)
CROSS_MODEL_PREFILL_PROMPT_LEN = 12
DECODE_PAST_LEN = 1024


def _cross_model_part_path(output_dir: Path, model: str, phase: str, mode: str) -> Path:
    safe = model.replace("-", "_").replace(".", "_")
    return output_dir / CROSS_MODEL_PARTS_DIRNAME / f"{safe}__{phase}__{mode}.json"


def _replay_task(task: ReplayTask) -> ReplayResult:
    from ramulator.pimscope import generate_and_replay

    result = generate_and_replay(
        task["phase"],
        task["model_key"],
        past_len=task.get("past_len", 1024),
        prompt_len=task.get("prompt_len", 12),
        materialize_weights=task["materialize_weights"],
        pim_cfg_override=task["pim_cfg_override"],
        max_inflight_requests=task["max_inflight_requests"],
        mac_mode=task["mac_mode"],
    )
    _write_part(result, task)
    return result


def collect_cross_model(output_dir: Path, *, force: bool = False, workers: int = 1) -> None:
    from ramulator.pimscope import pim_cfg_shared

    decode_path = output_dir / DECODE_JSON
    prefill_path = output_dir / PREFILL_JSON
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / CROSS_MODEL_PARTS_DIRNAME).mkdir(parents=True, exist_ok=True)

    pim_cfg = pim_cfg_shared()
    tasks: list[dict] = []
    for model in CROSS_MODEL_DECODE_MODELS:
        for mode in MODES:
            part = _cross_model_part_path(output_dir, model, "decode", mode)
            task = _make_replay_task(
                model_key=model,
                phase="decode",
                mode=mode,
                past_len=DECODE_PAST_LEN,
                materialize_weights=mode == "cold_start",
                part_path=part,
                pim_cfg_override=pim_cfg,
            )
            if force or not _part_cache_matches(part, task):
                tasks.append(task)
    for model in CROSS_MODEL_PREFILL_MODELS:
        for mode in MODES:
            part = _cross_model_part_path(output_dir, model, "prefill", mode)
            task = _make_replay_task(
                model_key=model,
                phase="prefill",
                mode=mode,
                prompt_len=CROSS_MODEL_PREFILL_PROMPT_LEN,
                materialize_weights=mode == "cold_start",
                part_path=part,
                pim_cfg_override=pim_cfg,
            )
            if force or not _part_cache_matches(part, task):
                tasks.append(task)

    total = len(tasks)
    expected = (len(CROSS_MODEL_DECODE_MODELS) + len(CROSS_MODEL_PREFILL_MODELS)) * 2
    if expected - total > 0:
        print(
            f"[cross-model] {expected - total} parts already cached in "
            f"{output_dir / CROSS_MODEL_PARTS_DIRNAME}; {total} remaining",
            flush=True,
        )
    if total > 0:
        print(
            f"[cross-model] collecting {total} simulation points with {workers} workers; "
            f"data -> {decode_path}, {prefill_path}",
            flush=True,
        )
        _run_tasks(
            tasks,
            workers,
            _replay_task,
            lambda t: f"{t['model_key']} {t['phase']} {t['mode']} -> {t['part_path']}",
            "cross-model",
        )

    _assemble_cross_model(output_dir, decode_path, prefill_path)


def _available_memory_bytes() -> int | None:
    """Return available host memory on Linux, or ``None`` when unavailable."""
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _effective_workers(requested: int, task_count: int) -> int:
    if requested <= 0:
        raise ValueError("workers must be positive")
    if task_count <= 0:
        return 0
    return min(requested, task_count)


def _warn_worker_memory(workers: int, available_bytes: int | None = None) -> None:
    if workers <= 1:
        return
    available = _available_memory_bytes() if available_bytes is None else available_bytes
    estimated = workers * ESTIMATED_WORKER_MEMORY_BYTES
    if available is not None and estimated > available:
        estimated_gib = estimated / (1 << 30)
        available_gib = available / (1 << 30)
        print(
            f"warning: {workers} workers may require about {estimated_gib:.0f} GiB; "
            f"only {available_gib:.1f} GiB is available. Choose a smaller --workers value.",
            file=sys.stderr,
            flush=True,
        )


def _run_tasks(tasks: list[dict], workers: int, fn, label, tag: str) -> None:
    failures: list[str] = []
    effective_workers = _effective_workers(workers, len(tasks))
    if effective_workers != workers:
        print(
            f"[{tag}] using {effective_workers} workers for {len(tasks)} pending tasks "
            f"(requested {workers})",
            flush=True,
        )
    _warn_worker_memory(effective_workers)
    if effective_workers <= 1:
        for idx, task in enumerate(tasks, 1):
            try:
                fn(task)
                print(f"[{tag}] {idx}/{len(tasks)}: {label(task)}", flush=True)
            except Exception as exc:
                detail = "".join(traceback.format_exception(exc)).rstrip()
                message = f"[{tag}] FAILED {idx}/{len(tasks)}: {label(task)}\n{detail}"
                failures.append(message)
                print(message, flush=True)
    else:
        with ProcessPoolExecutor(max_workers=effective_workers) as pool:
            future_map = {pool.submit(fn, t): t for t in tasks}
            for idx, future in enumerate(as_completed(future_map), 1):
                task = future_map[future]
                try:
                    future.result()
                    print(f"[{tag}] {idx}/{len(tasks)}: {label(task)}", flush=True)
                except Exception as exc:
                    detail = "".join(traceback.format_exception(exc)).rstrip()
                    message = f"[{tag}] FAILED {idx}/{len(tasks)}: {label(task)}\n{detail}"
                    failures.append(message)
                    print(message, flush=True)
    if failures:
        raise RuntimeError(
            f"{tag}: {len(failures)} task(s) failed; refusing to assemble partial artifacts\n"
            + "\n".join(failures)
        )


def _repository_relative(path: Path) -> str:
    candidate = path if path.is_absolute() else PROJECT_ROOT / path
    return candidate.resolve().relative_to(PROJECT_ROOT).as_posix()


def _load_required_part(path: Path, *, description: str) -> dict:
    if not path.exists():
        raise RuntimeError(f"missing required {description}: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("replay_ok"):
        raise RuntimeError(f"{description} did not pass backend replay: {path}")
    return data


def _assemble_cross_model(output_dir: Path, decode_path: Path, prefill_path: Path) -> None:
    from ramulator.pimscope import infer_model_family
    from ramulator.workload_surrogate.generate_full_transformer import get_model_spec

    decode_rows: list[dict] = []
    for model in CROSS_MODEL_DECODE_MODELS:
        spec = get_model_spec(model) if model != "mixtral-8x7b" else None
        for mode in MODES:
            part = _cross_model_part_path(output_dir, model, "decode", mode)
            data = _load_required_part(part, description="decode part")
            model_name = spec.name if spec else "Mixtral-8x7B"
            decode_rows.append(
                {
                    "model_name": model_name,
                    "model_family": infer_model_family(model_name),
                    "mode": mode,
                    "cycles": int(data["cycles"]),
                    "runtime_ns": float(data["runtime_ns"]),
                    "runtime_s": float(data["runtime_ns"]) / 1e9,
                    "pim_mac_issued": int(data["pim_mac_issued"]),
                    "hidden_size": int(spec.hidden_size) if spec else 4096,
                    "ffn_hidden_size": int(spec.ffn_hidden_size) if spec else 14336,
                    "num_layers": int(spec.num_layers) if spec else 32,
                    "replay_status": "PASS" if data.get("replay_ok") else "FAIL",
                    "data_source": "backend_replay",
                    "dimension_scope": (
                        "model_architecture_parameters_with_structured_surrogate_trace"
                    ),
                    "source_cache": _repository_relative(part),
                }
            )
    expected_decode_rows = len(CROSS_MODEL_DECODE_MODELS) * len(MODES)
    if len(decode_rows) != expected_decode_rows:
        raise RuntimeError(
            f"decode assembly produced {len(decode_rows)} rows, expected {expected_decode_rows}"
        )
    _write_aggregate_json(
        decode_path,
        {
            "schema_version": 1,
            "schema_name": "pimscope-decode-aggregate-v1",
            "figure_id": "fig18_cross_model_decode_cycles",
            "description": "Cross-model dense decode backend replay cycles",
            "phase": "decode",
            "metric_units": {"cycles": "cycles", "runtime_ns": "ns"},
            "provenance": _provenance(),
            "rows": decode_rows,
        },
        kind="decode_cycles",
    )
    print(f"wrote {decode_path} ({len(decode_rows)} rows)")
    _assemble_cross_model_prefill(output_dir, prefill_path)


def _assemble_cross_model_prefill(output_dir: Path, prefill_path: Path) -> None:
    from ramulator.pimscope import infer_model_family, prefill_formula
    from ramulator.workload_surrogate.generate_full_transformer import get_model_spec

    P = CROSS_MODEL_PREFILL_PROMPT_LEN
    prefill_rows: list[dict] = []
    for model in CROSS_MODEL_PREFILL_MODELS:
        formula = prefill_formula(model, prompt_len=P)
        spec = get_model_spec(model)
        for mode in MODES:
            part = _cross_model_part_path(output_dir, model, "prefill", mode)
            data = _load_required_part(part, description="prefill part")
            prefill_rows.append(
                {
                    "model_name": spec.name,
                    "model_family": infer_model_family(spec.name),
                    "model_key": model,
                    "mode": mode,
                    "cycles": int(data["cycles"]),
                    "runtime_ns": float(data["runtime_ns"]),
                    "runtime_s": float(data["runtime_ns"]) / 1e9,
                    "pim_mac_issued": int(data["pim_mac_issued"]),
                    "pim_bcast_issued": int(data.get("pim_bcast_issued", 0)),
                    "prompt_len": P,
                    "replay_layers": int(spec.num_layers),
                    "replay_status": "PASS" if data.get("replay_ok") else "FAIL",
                    "data_source": "backend_replay",
                    "dimension_scope": (
                        "model_architecture_parameters_with_structured_surrogate_trace"
                    ),
                    **{
                        k: formula[k]
                        for k in (
                            "hidden_size",
                            "ffn_hidden_size",
                            "ffn_variant",
                            "activation",
                            "num_heads",
                            "num_kv_heads",
                            "head_dim",
                            "datatype",
                            "citation",
                            "seq_len",
                            "prefill_causal_pairs",
                            "valid_attention_pairs_per_layer",
                            "attention_issued_work_elements_per_layer",
                            "score_tile_tokens",
                            "context_tile_tokens",
                            "pim_mac_lanes",
                            "primitive_ops_per_mac",
                            "per_layer_pim_mac_buckets",
                            "kv_residency_policy",
                            "model_total_layers",
                        )
                    },
                    "phase": "prefill",
                    "materialize_weights": mode == "cold_start",
                    "trace_name": f"{model}_prefill_P{P}_{mode}",
                    "command_counts": data.get("opcode_counts", {}),
                    "pim_mac_density": 0.0,
                }
            )
    expected_prefill_rows = len(CROSS_MODEL_PREFILL_MODELS) * len(MODES)
    if len(prefill_rows) != expected_prefill_rows:
        raise RuntimeError(
            f"prefill assembly produced {len(prefill_rows)} rows, expected {expected_prefill_rows}"
        )
    _write_aggregate_json(
        prefill_path,
        {
            "schema_version": 1,
            "schema_name": "pimscope-prefill-aggregate-v1",
            "figure_id": "fig22_cross_model_prefill_cycles",
            "description": "Cross-model dense prefill backend replay cycles",
            "phase": "prefill",
            "metric_units": {"cycles": "cycles", "runtime_ns": "ns"},
            "provenance": _provenance(prompt_len=P),
            "rows": prefill_rows,
            "caveats": ["Simulator-diagnostic cycles, not silicon-calibrated"],
        },
        kind="prefill_cycles",
    )
    print(f"wrote {prefill_path} ({len(prefill_rows)} rows)")


def _cold_start_overhead(rows: list[dict]) -> dict[str, float]:
    by_key = {(row["model_name"], row["mode"]): row for row in rows}
    overhead = {}
    for model_name in sorted({row["model_name"] for row in rows}):
        steady = float(by_key[(model_name, "steady_state")]["cycles"])
        cold = float(by_key[(model_name, "cold_start")]["cycles"])
        if steady <= 0:
            raise ValueError(f"steady-state cycles must be positive for {model_name}")
        overhead[model_name] = (cold - steady) / steady * 100.0
    return overhead


def verify_cold_start_claims(output_dir: Path) -> dict[str, dict[str, float]]:
    decode = validate_aggregate(
        json.loads((output_dir / DECODE_JSON).read_text("utf-8")), kind="decode_cycles"
    )["rows"]
    prefill = validate_aggregate(
        json.loads((output_dir / PREFILL_JSON).read_text("utf-8")),
        kind="prefill_cycles",
    )["rows"]
    summary = {}
    for phase, rows in (("decode", decode), ("prefill", prefill)):
        overhead = _cold_start_overhead(rows)
        summary[phase] = {
            "min_percent": min(overhead.values()),
            "max_percent": max(overhead.values()),
        }
    return summary


# ── pim-sharing — per-bank (b=1) vs two-bank shared (b=2) decode table ──

PIM_SHARING_WORKLOADS = tuple(
    {"model_key": m, "phase": "decode", "past_len": 1024}
    for m in (
        "llama2-7b",
        "llama2-13b",
        "llama2-70b",
        "opt-125m",
        "opt-350m",
        "opt-1.3b",
        "qwen25-7b",
        "qwen25-14b",
        "qwen25-32b",
        "qwen25-72b",
        "gemma-2b",
        "gemma-7b",
        "gemma2-9b",
        "gemma2-27b",
        "mixtral-8x7b",
    )
)

PIM_CONFIGS = {
    "k1": {"pim_banks_per_block": 1, "pim_mac_execution_model": "shared_block_serial"},
    "k2": {"pim_banks_per_block": 2, "pim_mac_execution_model": "shared_block_serial"},
}


def _pim_sharing_part_path(output_dir: Path, model: str, label: str) -> Path:
    safe = model.replace("-", "_").replace(".", "_")
    return output_dir / PIM_SHARING_PARTS_DIRNAME / f"{safe}__{label}.json"


def collect_pim_sharing(output_dir: Path, *, force: bool = False, workers: int = 1) -> None:
    path = output_dir / PIM_SHARING_JSON
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / PIM_SHARING_PARTS_DIRNAME).mkdir(parents=True, exist_ok=True)

    tasks: list[dict] = []
    for wl in PIM_SHARING_WORKLOADS:
        for label, cfg in PIM_CONFIGS.items():
            part = _pim_sharing_part_path(output_dir, wl["model_key"], label)
            task = _make_replay_task(
                model_key=wl["model_key"],
                phase=wl["phase"],
                past_len=wl["past_len"],
                materialize_weights=False,
                pim_cfg_override=cfg,
                part_path=part,
                pim_label=label,
            )
            if force or not _part_cache_matches(part, task):
                tasks.append(task)

    total = len(tasks)
    expected = len(PIM_SHARING_WORKLOADS) * len(PIM_CONFIGS)
    if expected - total > 0:
        print(
            f"[pim-sharing] {expected - total} parts already cached in "
            f"{output_dir / PIM_SHARING_PARTS_DIRNAME}; {total} remaining",
            flush=True,
        )
    if total > 0:
        print(
            f"[pim-sharing] collecting {total} simulation points with {workers} workers; "
            f"data -> {path}",
            flush=True,
        )
        _run_tasks(
            tasks,
            workers,
            _replay_task,
            lambda t: f"{t['model_key']} {t['pim_label']} -> {t['part_path']}",
            "pim-sharing",
        )

    _assemble_pim_sharing(output_dir, path)


def _assemble_pim_sharing(output_dir: Path, path: Path) -> None:
    from ramulator.pimscope import infer_model_family
    from ramulator.workload_surrogate.generate_full_transformer import get_model_spec

    rows: list[dict] = []
    for wl in PIM_SHARING_WORKLOADS:
        model_key = wl["model_key"]
        try:
            spec = get_model_spec(model_key)
        except (KeyError, ValueError):
            spec = None
        if spec is not None:
            model_name, hidden_size, num_layers = (
                spec.name,
                int(spec.hidden_size),
                int(spec.num_layers),
            )
        elif model_key == "mixtral-8x7b":
            model_name, hidden_size, num_layers = "Mixtral-8x7B", 4096, 32
        else:
            model_name, hidden_size, num_layers = model_key, 0, 0

        k1_part = _pim_sharing_part_path(output_dir, model_key, "k1")
        k2_part = _pim_sharing_part_path(output_dir, model_key, "k2")
        k1 = _load_required_part(k1_part, description="pim-sharing k1 part")
        k2 = _load_required_part(k2_part, description="pim-sharing k2 part")

        cycles_k1, cycles_k2 = int(k1["cycles"]), int(k2["cycles"])
        slowdown = (cycles_k2 / cycles_k1) if cycles_k1 > 0 else 0.0
        shared_block_stalls_k2 = int(k2.get("pim_shared_block_stalls", 0) or 0)
        stall_pct = (shared_block_stalls_k2 / cycles_k2 * 100.0) if cycles_k2 > 0 else 0.0
        label = f"{model_name} {wl['phase']}"
        if wl["phase"] == "decode" and wl.get("past_len"):
            label += f" (past={wl['past_len']})"

        rows.append(
            {
                "workload": label,
                "model_key": model_key,
                "model_family": infer_model_family(model_name),
                "phase": wl["phase"],
                "hidden_size": hidden_size,
                "num_layers": num_layers,
                "cycles_k1": cycles_k1,
                "cycles_k2": cycles_k2,
                "runtime_ns_k1": float(k1["runtime_ns"]),
                "runtime_ns_k2": float(k2["runtime_ns"]),
                "slowdown": round(slowdown, 4),
                "pim_simultaneous_active_banks_peak_k1": int(
                    k1.get("pim_simultaneous_active_banks_peak", 0) or 0
                ),
                "pim_simultaneous_active_banks_peak_k2": int(
                    k2.get("pim_simultaneous_active_banks_peak", 0) or 0
                ),
                "pim_ab_completion_latency_cycles_k1": int(
                    k1.get("pim_ab_completion_latency_cycles", 0) or 0
                ),
                "pim_ab_completion_latency_cycles_k2": int(
                    k2.get("pim_ab_completion_latency_cycles", 0) or 0
                ),
                "pim_shared_block_stalls_k2": shared_block_stalls_k2,
                "pim_dependency_stalls_k2": int(k2.get("pim_dependency_stalls", 0) or 0),
                "pim_capacity_stalls_k2": int(k2.get("pim_capacity_stalls", 0) or 0),
                "num_bank_timing_blocked_k2": int(k2.get("num_bank_timing_blocked_cycles", 0) or 0),
                "shared_block_stall_pct": round(stall_pct, 2),
                "pim_banks_per_block_k1": int(k1.get("pim_banks_per_block", 1) or 1),
                "pim_banks_per_block_k2": int(k2.get("pim_banks_per_block", 2) or 2),
                "replay_ok_k1": bool(k1.get("replay_ok")),
                "replay_ok_k2": bool(k2.get("replay_ok")),
            }
        )

    expected_rows = len(PIM_SHARING_WORKLOADS)
    if len(rows) != expected_rows:
        raise RuntimeError(
            f"pim-sharing assembly produced {len(rows)} rows, expected {expected_rows}"
        )
    _write_aggregate_json(
        path,
        {
            "schema_version": 1,
            "schema_name": "pimscope-sharing-aggregate-v1",
            "description": (
                "Transformer-trace PIM comparison: CD-PIM dedicated per-bank (k=1) "
                "vs shared PIM block across 2 banks (k=2)"
            ),
            "provenance": _provenance(),
            "rows": rows,
        },
        kind="pim_sharing_comparison",
    )
    print(f"wrote {path} ({len(rows)} rows)")


def _render_cross_model(output_dir: Path) -> None:
    from scripts.lib.artifact_plotting import render_cross_model

    render_cross_model(output_dir)


COLLECTORS = {"cross-model": collect_cross_model, "pim-sharing": collect_pim_sharing}
RENDERERS = {"cross-model": _render_cross_model}
TARGETS = ("cross-model", "pim-sharing", "all")


def _expand_target(target: str | None) -> list[str]:
    if target in (None, "all"):
        return ["cross-model", "pim-sharing"]
    if target not in COLLECTORS:
        raise ValueError(f"unknown target: {target}")
    return [target]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce the LPDDR-PIM paper figure (cross-model) and table (pim-sharing)"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--collect", nargs="?", const="all", choices=TARGETS)
    group.add_argument("--render", nargs="?", const="all", choices=TARGETS)
    group.add_argument("--all", nargs="?", const="all", choices=TARGETS)
    group.add_argument("--verify-claims", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--workers",
        type=int,
        default=64,
        help="parallel worker processes (default: 64; use 1 for debugging)",
    )
    args = parser.parse_args()
    if args.workers <= 0:
        parser.error("--workers must be positive")

    os.makedirs(args.output_dir, exist_ok=True)

    if args.verify_claims:
        print(json.dumps(verify_cold_start_claims(args.output_dir), indent=2, sort_keys=True))
        return 0
    if args.collect is not None:
        for target in _expand_target(args.collect):
            COLLECTORS[target](args.output_dir, force=args.force, workers=args.workers)
        return 0
    if args.render is not None:
        for target in _expand_target(args.render):
            if target in RENDERERS:
                RENDERERS[target](args.output_dir)
        return 0

    for target in _expand_target(args.all):
        COLLECTORS[target](args.output_dir, force=args.force, workers=args.workers)
    for target in _expand_target(args.all):
        if target in RENDERERS:
            RENDERERS[target](args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
