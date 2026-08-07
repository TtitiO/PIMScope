"""Researcher-facing PIMScope command-line interface."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.lib.config import (
    apply_overrides,
    load_raw_manifest,
    resolve_experiment_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAMULATOR2_DIR = PROJECT_ROOT / "ramulator2"


def _git_revision(repo: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _dump_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _load_resolved(path: Path, overrides: list[str]):
    raw = apply_overrides(load_raw_manifest(path), overrides)
    return resolve_experiment_manifest(raw, source=str(path.resolve()))


def _validate_backend(resolved) -> dict[str, Any]:
    from scripts.lib.backend_replay import create_dram, hardware_config_from_manifest

    cfg = hardware_config_from_manifest(resolved)
    dram = create_dram(cfg)
    org, timing = dram.resolve()
    return {
        "organization": org,
        "timing": timing,
        "dram_config": dram.to_config(),
    }


def _cmd_validate(args: argparse.Namespace) -> int:
    resolved = _load_resolved(args.config, args.set)
    payload: dict[str, Any] = {
        "valid": True,
        "manifest_fingerprint": resolved.fingerprint,
        "resolved_manifest": resolved.manifest,
    }
    if not args.no_backend:
        payload["resolved_backend"] = _validate_backend(resolved)
    print(_dump_json(payload), end="")
    return 0


def _custom_model_spec(model: dict[str, Any], datatype: str):
    from ramulator.workload_surrogate.generate_full_transformer import ModelSpec

    return ModelSpec(
        name=model["name"],
        num_layers=model["num_layers"],
        hidden_size=model["hidden_size"],
        num_heads=model["num_heads"],
        num_kv_heads=model.get("num_kv_heads"),
        head_dim=model["head_dim"],
        ffn_hidden_size=model["ffn_hidden_size"],
        datatype=datatype,
        citation=model.get("citation"),
        paper_anchor=model.get("paper_anchor"),
        ffn_variant=model.get("ffn_variant", "swiglu_3proj"),
        activation=model.get("activation", "silu"),
    )


def _generate_semantic(workload: dict[str, Any]) -> tuple[list[dict], str]:
    from ramulator.workload_surrogate.generate_full_transformer import (
        generate_dense_decoder_records_for_model,
        generate_dense_decoder_records_from_spec,
        generate_dense_prefill_records_for_model,
        generate_dense_prefill_records_from_spec,
        generate_mixtral_8x7b_decoder_records,
        get_mixtral_8x7b_moe_decoder_manifests,
    )

    phase = workload["phase"]
    model = workload["model"]
    schedule = workload["schedule_policy"]
    if model == "mixtral-8x7b":
        attention, moe = get_mixtral_8x7b_moe_decoder_manifests(
            past_len=workload["past_len"], schedule_policy=schedule
        )
        return (
            generate_mixtral_8x7b_decoder_records(
                attention_manifest=attention, moe_manifest=moe
            ),
            model,
        )
    if isinstance(model, dict):
        spec = _custom_model_spec(model, workload["datatype"])
        if phase == "decode":
            records = generate_dense_decoder_records_from_spec(
                spec, past_len=workload["past_len"], schedule_policy=schedule
            )
        else:
            records = generate_dense_prefill_records_from_spec(
                spec, prompt_len=workload["prompt_len"], schedule_policy=schedule
            )
        return records, model["name"]
    if phase == "decode":
        records = generate_dense_decoder_records_for_model(
            model, past_len=workload["past_len"], schedule_policy=schedule
        )
    else:
        records = generate_dense_prefill_records_for_model(
            model, prompt_len=workload["prompt_len"], schedule_policy=schedule
        )
    return records, model


def run_experiment(resolved) -> dict[str, Any]:
    from ramulator.workload_surrogate.generate_lpddr5_pim_concrete import (
        lower_semantic_records_to_concrete,
    )

    from scripts.lib.backend_replay import (
        count_concrete_opcodes,
        create_dram,
        hardware_config_from_manifest,
        replay_concrete_trace,
    )
    from scripts.lib.runner import _extract_dram_layout

    manifest = resolved.manifest
    workload = manifest["workload"]
    backend_cfg = hardware_config_from_manifest(resolved)
    dram = create_dram(backend_cfg)
    # Resolve before generating a large trace so invalid organization/timing/PIM
    # combinations fail early with the simulator's field-specific error.
    organization, timing = dram.resolve()
    semantic, model_name = _generate_semantic(workload)

    interleave_banks = workload["max_inflight_requests"] > 1
    lower_kwargs: dict[str, Any] = {
        "materialize_weights": workload["weight_residency"] == "full_preload",
        "interleave_banks": interleave_banks,
        "mac_mode": workload["mac_mode"],
    }
    if interleave_banks:
        layout = _extract_dram_layout(dram)
        lower_kwargs.update({
            "addr_vec_size": layout["addr_vec_size"],
            "bank_positions": layout["bank_positions"],
            "bank_counts": layout["bank_counts"],
            "row_level": layout["row_pos"],
            "col_level": layout["col_pos"],
            "interleave_depth": workload["interleave_depth"],
        })
    concrete = lower_semantic_records_to_concrete(semantic, **lower_kwargs)

    effective_inflight = workload["max_inflight_requests"]
    if interleave_banks and workload["mac_mode"] in {"per_kind", "per_bank"}:
        max_span = max(
            (len(record["bank_sequence"]) for record in semantic if record.get("bank_sequence")),
            default=1,
        )
        effective_inflight = max(
            effective_inflight, max_span * workload["interleave_depth"]
        )
    elif workload["mac_mode"] == "all_bank":
        effective_inflight = 1

    replay = replay_concrete_trace(
        concrete,
        max_inflight_requests=effective_inflight,
        backend_cfg=backend_cfg,
    )
    return {
        "schema_version": 1,
        "experiment": manifest["experiment"],
        "status": "PASS" if replay["replay_ok"] else "FAIL",
        "manifest_fingerprint": resolved.fingerprint,
        "resolved_manifest": manifest,
        "resolved_hardware": {
            "organization": organization,
            "timing": timing,
            "effective_max_inflight_requests": effective_inflight,
        },
        "workload_summary": {
            "model": model_name,
            "phase": workload["phase"],
            "semantic_records": len(semantic),
            "concrete_records": len(concrete),
            "concrete_opcode_counts": count_concrete_opcodes(concrete),
            "surrogate_scope": {
                "architecture_dimensions": "published_or_user_supplied",
                "runtime_trace": False,
                "numerical_execution": False,
                "silicon_calibration": False,
            },
        },
        "simulation": replay,
        "provenance": {
            "generated_at": datetime.now(UTC).isoformat(),
            "pimscope_commit": _git_revision(PROJECT_ROOT),
            "ramulator2_commit": _git_revision(RAMULATOR2_DIR),
            "config_source": resolved.source,
        },
    }


def _cmd_run(args: argparse.Namespace) -> int:
    resolved = _load_resolved(args.config, args.set)
    result = run_experiment(resolved)
    output = Path(args.output or resolved.manifest["output"]["path"])
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_dump_json(result), encoding="utf-8")
    print(f"result: {output}")
    print(f"status: {result['status']}")
    print(f"cycles: {result['simulation']['cycles']}")
    print(f"manifest fingerprint: {resolved.fingerprint}")
    return 0 if result["status"] == "PASS" else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pimscope",
        description="Validate and run configurable LPDDR5-PIM workload-surrogate experiments",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate", help="validate a JSON/YAML manifest and print the resolved configuration"
    )
    validate.add_argument("config", type=Path)
    validate.add_argument(
        "--set", action="append", default=[], metavar="PATH=VALUE",
        help="override a manifest field; VALUE accepts JSON syntax",
    )
    validate.add_argument(
        "--no-backend", action="store_true",
        help="perform schema validation without importing the compiled Ramulator backend",
    )
    validate.set_defaults(func=_cmd_validate)

    run = subparsers.add_parser(
        "run", help="generate, lower, and replay one validated workload experiment"
    )
    run.add_argument("config", type=Path)
    run.add_argument("--output", type=Path, help="override output.path")
    run.add_argument(
        "--set", action="append", default=[], metavar="PATH=VALUE",
        help="override a manifest field; VALUE accepts JSON syntax",
    )
    run.set_defaults(func=_cmd_run)
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"pimscope: error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
