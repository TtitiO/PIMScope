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
