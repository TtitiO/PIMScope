import warnings

import pytest
from ramulator.pimscope.compat import (
    canonicalize_legacy_pim_config,
    canonicalize_legacy_result,
)
from ramulator.pimscope.config import resolve_experiment_manifest


def test_legacy_manifest_names_are_normalized_with_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        normalized = canonicalize_legacy_pim_config(
            {
                "pim_banks_per_mpu": 2,
                "pim_mac_execution_model": "shared_mpu_serial",
            }
        )
    assert normalized == {
        "pim_banks_per_block": 2,
        "pim_mac_execution_model": "shared_block_serial",
    }
    assert len(caught) == 2


def test_legacy_and_canonical_config_conflicts_fail_closed():
    with pytest.raises(ValueError, match="conflicts"):
        canonicalize_legacy_pim_config(
            {"pim_banks_per_mpu": 1, "pim_banks_per_block": 2}
        )


def test_legacy_result_fields_are_normalized_recursively():
    normalized = canonicalize_legacy_result(
        {
            "simulation": {
                "pim_mpu_group_stalls": 7,
                "pim_banks_per_mpu": 2,
                "nested": {"effective_mpu_groups": 8},
            }
        }
    )
    assert normalized == {
        "simulation": {
            "pim_shared_block_stalls": 7,
            "pim_banks_per_block": 2,
            "nested": {"effective_shared_blocks": 8},
        }
    }


def test_legacy_and_canonical_result_conflicts_fail_closed():
    with pytest.raises(ValueError, match="conflicts"):
        canonicalize_legacy_result(
            {"pim_mpu_group_stalls": 1, "pim_shared_block_stalls": 2}
        )


def test_manifest_legacy_fields_are_accepted_only_as_compatibility_aliases():
    raw = {
        "hardware": {
            "pim": {
                "pim_banks_per_mpu": 1,
                "pim_mac_execution_model": "shared_mpu_serial",
            }
        },
        "workload": {"datatype": "int8"},
    }
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        resolved = resolve_experiment_manifest(raw)
    assert resolved.manifest["hardware"]["pim"]["pim_banks_per_block"] == 1
    assert resolved.manifest["hardware"]["pim"]["pim_mac_execution_model"] == "shared_block_serial"
    assert len(caught) == 2
