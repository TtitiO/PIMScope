import json
from pathlib import Path

from scripts.cli import _retarget_semantic_banks, run_experiment
from scripts.lib.config import resolve_experiment_manifest


def test_semantic_bank_sequences_follow_resolved_hardware():
    records = [
        {"bank_sequence": [0, 1, 2, 3], "mapping_policy": {"bank_sequence_policy": "manifest_order"}},
        {"kind": "Barrier"},
    ]
    _retarget_semantic_banks(records, 8)
    assert records[0]["bank_sequence"] == list(range(8))
    assert records[0]["mapping_policy"]["bank_sequence_policy"] == "resolved_hardware_round_robin"


def test_tiny_custom_model_replays_with_resolved_manifest():
    raw = json.loads(
        (Path(__file__).parents[1] / "configs" / "example_custom_model.json").read_text(
            encoding="utf-8"
        )
    )
    resolved = resolve_experiment_manifest(raw, source="test-custom-model")
    result = run_experiment(resolved)
    assert result["status"] == "PASS"
    assert result["simulation"]["replay_ok"]
    assert result["simulation"]["pim_mac_issued"] > 0
    assert result["manifest_fingerprint"] == resolved.fingerprint
    assert result["resolved_manifest"]["workload"]["model"]["name"] == "TinyResearchModel"
