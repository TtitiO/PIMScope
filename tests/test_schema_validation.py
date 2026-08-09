from pathlib import Path

import pytest
from ramulator.pimscope import (
    load_raw_manifest,
    resolve_experiment_manifest,
    validate_result,
)
from ramulator.pimscope.schema import validate_aggregate

EXAMPLE = Path(__file__).parents[1] / "configs" / "example_custom.json"


def test_result_schema_accepts_a_short_real_run():
    raw = load_raw_manifest(EXAMPLE)
    raw["workload"]["past_len"] = 1
    raw["workload"]["max_inflight_requests"] = 1
    resolved = resolve_experiment_manifest(raw, source=str(EXAMPLE))
    from ramulator.pimscope.experiment import run_experiment

    result = run_experiment(resolved)
    assert validate_result(result)["status"] == "PASS"
    assert result["schema_name"] == "pimscope-result-v1"


def test_aggregate_schema_validates_name_phase_and_rows():
    payload = {
        "schema_version": 1,
        "schema_name": "pimscope-decode-aggregate-v1",
        "phase": "decode",
        "rows": [{"cycles": 1, "runtime_ns": 2.0, "replay_status": "PASS"}],
    }
    assert validate_aggregate(payload, kind="decode_cycles")["rows"]

    with pytest.raises(ValueError, match="schema_name"):
        validate_aggregate({**payload, "schema_name": "wrong"}, kind="decode_cycles")
    with pytest.raises(ValueError, match="phase"):
        validate_aggregate({**payload, "phase": "prefill"}, kind="decode_cycles")
    with pytest.raises(ValueError, match="non-negative"):
        validate_aggregate(
            {**payload, "rows": [{"cycles": -1}]}, kind="decode_cycles"
        )


def test_lpddr6_result_records_backend_and_trace_schema():
    raw = load_raw_manifest(EXAMPLE)
    raw["hardware"]["dram_class"] = "LPDDR6PIM"
    raw["hardware"]["org_preset"] = "LPDDR6_16Gb_x12"
    raw["hardware"]["timing_preset"] = "LPDDR6_10667_BL24"
    raw["workload"]["past_len"] = 1
    raw["workload"]["max_inflight_requests"] = 1
    resolved = resolve_experiment_manifest(raw, source="lpddr6-schema-test")
    from ramulator.pimscope.experiment import run_experiment

    result = run_experiment(resolved)
    assert validate_result(result)["status"] == "PASS"
    assert result["simulation"]["dram_class"] == "LPDDR6PIM"
    assert result["simulation"]["trace_schema"] == "lpddr6-pim-opcode-v0.1"
    assert result["resolved_hardware"]["address_layout"]["subchannel_model"] == {
        "status": "single_subchannel_only",
        "modeled_subchannels_per_channel": 1,
        "refresh_density_reference_subchannels": 2,
        "independent_subchannel_scheduling": False,
    }
    energy = result["simulation"]["power_accounting"]
    assert energy["status"] == "pim_event_coefficients_only"
    assert energy["standard_background_command_energy_available"] is False
    assert energy["total_energy_pJ"] is None


def test_result_schema_rejects_unsupported_lpddr6_subchannel_claim():
    raw = load_raw_manifest(EXAMPLE)
    raw["hardware"]["dram_class"] = "LPDDR6PIM"
    raw["hardware"]["org_preset"] = "LPDDR6_16Gb_x12"
    raw["hardware"]["timing_preset"] = "LPDDR6_10667_BL24"
    raw["workload"]["past_len"] = 1
    raw["workload"]["max_inflight_requests"] = 1
    resolved = resolve_experiment_manifest(raw, source="schema-subchannel-test")
    from ramulator.pimscope.experiment import run_experiment

    result = run_experiment(resolved)
    result["resolved_hardware"]["address_layout"]["subchannel_model"][
        "independent_subchannel_scheduling"
    ] = True
    with pytest.raises(ValueError, match="unsupported LPDDR6 sub-channel interpretation"):
        validate_result(result)


def test_result_schema_rejects_lpddr6_standard_power_claim():
    raw = load_raw_manifest(EXAMPLE)
    raw["hardware"]["dram_class"] = "LPDDR6PIM"
    raw["hardware"]["org_preset"] = "LPDDR6_16Gb_x12"
    raw["hardware"]["timing_preset"] = "LPDDR6_10667_BL24"
    raw["workload"]["past_len"] = 1
    raw["workload"]["max_inflight_requests"] = 1
    resolved = resolve_experiment_manifest(raw, source="schema-power-test")
    from ramulator.pimscope.experiment import run_experiment

    result = run_experiment(resolved)
    result["simulation"]["power_accounting"][
        "standard_background_command_energy_available"
    ] = True
    with pytest.raises(ValueError, match="standard background/command energy"):
        validate_result(result)


def test_result_schema_rejects_backend_trace_schema_mismatch():
    raw = load_raw_manifest(EXAMPLE)
    raw["workload"]["past_len"] = 1
    raw["workload"]["max_inflight_requests"] = 1
    resolved = resolve_experiment_manifest(raw, source="schema-mismatch-test")
    from ramulator.pimscope.experiment import run_experiment

    result = run_experiment(resolved)
    result["simulation"]["trace_schema"] = "lpddr6-pim-opcode-v0.1"
    with pytest.raises(ValueError, match="trace_schema"):
        validate_result(result)


def test_result_schema_rejects_fingerprint_mismatch():
    with pytest.raises(ValueError, match="fingerprint"):
        validate_result(
            {
                "schema_version": 1,
                "experiment": "x",
                "status": "FAIL",
                "manifest_fingerprint": "0" * 64,
                "resolved_manifest": {},
                "resolved_hardware": {},
                "workload_summary": {},
                "simulation": {"replay_ok": False, "cycles": 0},
                "provenance": {},
            }
        )
