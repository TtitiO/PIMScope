import json
from pathlib import Path

import pytest

from scripts.gen_figures import _load_required_part, _part_cache_matches, _run_tasks, _write_part
from scripts.lib.backend_replay import count_concrete_opcodes


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
        "pim_cfg_override": {"pim_banks_per_mpu": 2},
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
