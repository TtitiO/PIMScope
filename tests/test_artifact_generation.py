import json
from pathlib import Path

import pytest
from ramulator.pimscope import count_concrete_opcodes

from scripts.gen_figures import (
    _load_required_part,
    _part_cache_matches,
    _run_tasks,
    _write_aggregate_json,
    _write_part,
)


def test_run_tasks_fails_closed_when_a_worker_fails():
    tasks = [{"id": "ok"}, {"id": "broken"}]

    def run(task):
        if task["id"] == "broken":
            raise ValueError("intentional failure")

    with pytest.raises(RuntimeError, match=r"1 task\(s\) failed.*refusing to assemble"):
        _run_tasks(tasks, workers=1, fn=run, label=lambda task: task["id"], tag="unit")


def test_required_part_must_exist_and_pass(tmp_path: Path):
    path = tmp_path / "part.json"
    with pytest.raises(RuntimeError, match="missing required"):
        _load_required_part(path, description="test part")

    path.write_text(json.dumps({"replay_ok": False}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="did not pass backend replay"):
        _load_required_part(path, description="test part")

    payload = {"replay_ok": True, "cycles": 42}
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert _load_required_part(path, description="test part") == payload


def test_part_cache_is_configuration_aware(tmp_path: Path):
    task = {
        "model_key": "example",
        "phase": "decode",
        "mode": "steady_state",
        "materialize_weights": False,
        "part_path": str(tmp_path / "part.json"),
        "pim_cfg_override": {"pim_banks_per_block": 2},
        "max_inflight_requests": 16,
        "mac_mode": "per_kind",
    }
    _write_part({"replay_ok": True, "cycles": 42}, task)
    assert _part_cache_matches(Path(task["part_path"]), task)
    assert not _part_cache_matches(
        Path(task["part_path"]), {**task, "max_inflight_requests": 8}
    )


def test_pim_broadcast_count_comes_from_concrete_opcodes():
    records = [
        {"opcode": "PIM_BCAST", "repeat": 3},
        {"opcode": "PIM_MAC", "repeat": 5},
    ]
    assert count_concrete_opcodes(records)["PIM_BCAST"] == 3


def test_aggregate_writer_rejects_invalid_rows(tmp_path: Path):
    path = tmp_path / "decode_cycles.json"
    valid = {
        "schema_version": 1,
        "schema_name": "pimscope-decode-aggregate-v1",
        "phase": "decode",
        "rows": [{"cycles": 1, "runtime_ns": 2.0, "replay_status": "PASS"}],
    }
    _write_aggregate_json(path, valid, kind="decode_cycles")
    assert json.loads(path.read_text(encoding="utf-8"))["schema_name"] == (
        "pimscope-decode-aggregate-v1"
    )

    invalid = {**valid, "rows": [{"cycles": -1}]}
    with pytest.raises(ValueError, match="non-negative"):
        _write_aggregate_json(path, invalid, kind="decode_cycles")
