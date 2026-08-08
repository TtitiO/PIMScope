import json
from pathlib import Path

import pytest
from ramulator.pimscope import (
    apply_overrides,
    create_dram,
    create_memory_system,
    hardware_config_from_manifest,
    resolve_experiment_manifest,
)

EXAMPLE = Path(__file__).parents[1] / "configs" / "example_custom.json"


def _example_manifest():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_example_manifest_resolves_with_stable_fingerprint():
    first = resolve_experiment_manifest(_example_manifest(), source="example")
    second = resolve_experiment_manifest(_example_manifest(), source="other-path")
    assert first.fingerprint == second.fingerprint
    assert first.manifest["workload"]["model"] == "opt-125m"
    assert first.manifest["hardware"]["pim"]["pim_banks_per_block"] == 2


def test_unknown_and_invalid_fields_fail_with_dotted_path():
    raw = _example_manifest()
    raw["hardware"]["pim"]["pim_bank_per_block"] = 2
    with pytest.raises(ValueError, match=r"hardware\.pim: unknown field.*pim_bank_per_block"):
        resolve_experiment_manifest(raw)

    raw = _example_manifest()
    raw["workload"]["max_inflight_requests"] = 0
    with pytest.raises(ValueError, match=r"workload\.max_inflight_requests"):
        resolve_experiment_manifest(raw)


def test_workload_and_hardware_datatypes_must_match():
    raw = _example_manifest()
    raw["workload"]["datatype"] = "fp16"
    with pytest.raises(ValueError, match=r"workload\.datatype.*must equal"):
        resolve_experiment_manifest(raw)


def test_custom_dense_model_is_validated():
    raw = _example_manifest()
    raw["workload"]["model"] = {
        "name": "TinyResearchModel",
        "num_layers": 2,
        "hidden_size": 64,
        "num_heads": 4,
        "num_kv_heads": 2,
        "head_dim": 16,
        "ffn_hidden_size": 128,
        "ffn_variant": "swiglu_3proj",
        "activation": "silu",
        "citation": "local manifest example",
    }
    resolved = resolve_experiment_manifest(raw)
    assert resolved.manifest["workload"]["model"]["num_layers"] == 2

    raw["workload"]["model"]["num_kv_heads"] = 3
    with pytest.raises(ValueError, match=r"workload\.model\.num_kv_heads"):
        resolve_experiment_manifest(raw)


def test_backend_factory_supports_nested_rit_mapper():
    raw = _example_manifest()
    raw["hardware"]["controller"]["addr_mapper"] = "RITAddrMapper"
    resolved = resolve_experiment_manifest(raw)
    backend = hardware_config_from_manifest(resolved)
    memory = create_memory_system(create_dram(backend), backend)
    config = memory.to_config()
    mapper = config["controllers"][0]["addr_mapper"]
    assert mapper["impl"] == "RITAddrMapper"
    assert mapper["addr_mapper"]["impl"] == "PassThroughAddrMapper"


def test_cli_style_override_changes_resolved_hardware():
    raw = apply_overrides(
        _example_manifest(),
        ["hardware.pim.pim_banks_per_block=1", "workload.past_len=64"],
    )
    resolved = resolve_experiment_manifest(raw)
    backend = hardware_config_from_manifest(resolved)
    assert backend["dram_kwargs"]["pim_banks_per_block"] == 1
    assert resolved.manifest["workload"]["past_len"] == 64
