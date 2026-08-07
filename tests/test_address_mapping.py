import json
from pathlib import Path

import pytest

from scripts.lib.addressing import (
    addr_vec_from_byte_address,
    extract_dram_layout,
    validate_addr_vec,
)
from scripts.cli import _validate_backend
from scripts.lib.backend_replay import create_dram, hardware_config_from_manifest
from scripts.lib.config import resolve_experiment_manifest


def _layout(preset: str = "LPDDR5_8Gb_x16", **org_overrides):
    dram = create_dram(
        {
            "org_preset": preset,
            "timing_preset": "LPDDR5_6400",
            "dram_kwargs": org_overrides,
            "frontend_clock_ratio": 4,
        }
    )
    return extract_dram_layout(dram)


def _map(address: int, layout: dict) -> list[int]:
    return addr_vec_from_byte_address(
        address,
        level_names=layout["level_names"],
        level_sizes=layout["level_sizes"],
        internal_prefetch_size=layout["internal_prefetch_size"],
        tx_bytes=layout["tx_bytes"],
    )


@pytest.mark.parametrize(
    ("preset", "rows", "capacity"),
    [
        ("LPDDR5_8Gb_x16", 32768, 1 << 30),
        ("LPDDR5_16Gb_x16", 65536, 1 << 31),
    ],
)
def test_layout_is_derived_from_resolved_organization(preset, rows, capacity):
    layout = _layout(preset)
    assert layout["level_names"] == [
        "Channel", "Rank", "BankGroup", "Bank", "Row", "Column"
    ]
    assert layout["level_sizes"] == [1, 1, 4, 4, rows, 1024]
    assert layout["internal_prefetch_size"] == 16
    assert layout["tx_bytes"] == 32
    assert layout["capacity_bytes"] == capacity


def test_byte_address_boundaries_and_transaction_alignment():
    layout = _layout()
    assert _map(0, layout) == [0, 0, 0, 0, 0, 0]
    assert _map(layout["tx_bytes"] - 1, layout) == [0, 0, 0, 0, 0, 0]
    assert _map(layout["tx_bytes"], layout) == [0, 0, 0, 0, 0, 1]
    assert _map(layout["capacity_bytes"] - 1, layout) == [
        0, 0, 3, 3, layout["num_rows"] - 1, 63
    ]
    with pytest.raises(ValueError, match="exceeds configured addressable capacity"):
        _map(layout["capacity_bytes"], layout)


def test_rank_override_participates_in_mixed_radix_mapping():
    layout = _layout(rank=2)
    assert layout["level_sizes"][layout["rank_pos"]] == 2
    assert layout["capacity_bytes"] == 2 << 30
    bytes_per_rank = layout["capacity_bytes"] // 2
    mapped = _map(bytes_per_rank, layout)
    assert mapped[layout["rank_pos"]] == 1
    assert mapped[layout["row_pos"]] == 0
    assert mapped[layout["col_pos"]] == 0


def test_coordinate_validation_reports_level_name_and_range():
    layout = _layout()
    invalid = [0] * layout["addr_vec_size"]
    invalid[layout["row_pos"]] = layout["num_rows"]
    with pytest.raises(ValueError, match=r"Row.*must be in \[0, 32768\)"):
        validate_addr_vec(
            invalid,
            level_names=layout["level_names"],
            level_sizes=layout["level_sizes"],
        )


def test_python_mapper_matches_explicit_mixed_radix_reference():
    layout = _layout()
    transactions = layout["capacity_bytes"] // layout["tx_bytes"]
    samples = [
        0,
        1,
        layout["tx_bytes"] - 1,
        layout["tx_bytes"],
        layout["tx_bytes"] * 63,
        layout["tx_bytes"] * 64,
        layout["capacity_bytes"] // 2,
        layout["capacity_bytes"] - 1,
    ]
    radices = layout["address_level_sizes"]
    for address in samples:
        transaction = address // layout["tx_bytes"]
        assert 0 <= transaction < transactions
        expected = [0] * len(radices)
        for index in range(len(radices) - 1, -1, -1):
            expected[index] = transaction % radices[index]
            transaction //= radices[index]
        assert transaction == 0
        assert _map(address, layout) == expected


def test_concrete_python_validation_uses_the_same_resolved_layout():
    from ramulator.workload_surrogate.lpddr5_pim_concrete_trace import validate_record

    layout = _layout("LPDDR5_16Gb_x16")
    last = layout["capacity_bytes"] - layout["tx_bytes"]
    record = {
        "opcode": "READ",
        "repeat": 1,
        "addr_byte": last,
        "addr_vec": _map(last, layout),
    }
    validate_record(record, address_layout=layout)
    record["addr_vec"][layout["row_pos"]] = layout["num_rows"]
    with pytest.raises(ValueError, match=r"Row.*must be in"):
        validate_record(record, address_layout=layout)


def test_repeated_host_range_crossing_capacity_is_rejected():
    from ramulator.workload_surrogate.lpddr5_pim_concrete_trace import validate_record

    layout = _layout()
    start = layout["capacity_bytes"] - layout["tx_bytes"]
    with pytest.raises(ValueError, match="exceeds configured addressable capacity"):
        validate_record(
            {
                "opcode": "READ",
                "repeat": 2,
                "addr_byte": start,
                "addr_byte_stride": layout["tx_bytes"],
                "addr_vec": _map(start, layout),
            },
            address_layout=layout,
        )


def test_every_flat_bank_maps_once_for_one_and_two_ranks():
    from ramulator.workload_surrogate.generate_lpddr5_pim_concrete import (
        _decompose_flat_bank,
    )

    for layout in (_layout(), _layout(rank=2)):
        seen = set()
        for flat_bank in range(layout["total_bank_units"]):
            addr_vec = [0] * layout["addr_vec_size"]
            _decompose_flat_bank(
                flat_bank,
                addr_vec,
                bank_positions=layout["bank_positions"],
                bank_counts=layout["bank_counts"],
                controller_order=False,
            )
            coordinate = tuple(addr_vec[index] for index in layout["bank_positions"])
            assert coordinate not in seen
            seen.add(coordinate)
        assert len(seen) == layout["total_bank_units"]


def test_validate_backend_reports_resolved_address_layout():
    raw = json.loads(
        (Path(__file__).parents[1] / "configs" / "example_custom.json").read_text(
            encoding="utf-8"
        )
    )
    backend = _validate_backend(resolve_experiment_manifest(raw))
    assert backend["address_layout"]["level_names"][-2:] == ["Row", "Column"]
    assert backend["address_layout"]["address_level_sizes"][-1] == 64
    assert backend["address_layout"]["tx_bytes"] == 32
    assert backend["address_layout"]["capacity_bytes"] == 1 << 30


def test_interleaving_level_override_cannot_bypass_resolved_hierarchy():
    from ramulator.workload_surrogate.lpddr5_pim_concrete_trace import validate_record

    layout = _layout()
    with pytest.raises(ValueError, match="resolved Row/Column"):
        validate_record(
            {
                "opcode": "PIM_MAC",
                "repeat": 1,
                "addr_vec": [0] * layout["addr_vec_size"],
                "bank_sequence": [0, 1],
                "dependency_count": 1,
                "row_count": 1,
                "row_level": layout["col_pos"],
                "col_level": layout["row_pos"],
            },
            address_layout=layout,
        )


def test_interleaving_bank_count_mismatch_is_rejected():
    from ramulator.workload_surrogate.lpddr5_pim_concrete_trace import validate_record

    layout = _layout()
    with pytest.raises(ValueError, match=r"bank_counts\[1\].*configured level Bank size 4"):
        validate_record(
            {
                "opcode": "PIM_MAC",
                "repeat": 1,
                "addr_vec": [0] * layout["addr_vec_size"],
                "bank_sequence": [0, 1],
                "bank_positions": layout["bank_positions"],
                "bank_counts": [1, 99, 4],
                "dependency_count": 1,
                "row_count": 1,
                "row_level": layout["row_pos"],
                "col_level": layout["col_pos"],
            },
            address_layout=layout,
        )


def test_manifest_16gb_run_records_resolved_address_layout():
    raw = json.loads(
        (Path(__file__).parents[1] / "configs" / "example_custom_model.json").read_text(
            encoding="utf-8"
        )
    )
    raw["hardware"]["org_preset"] = "LPDDR5_16Gb_x16"
    resolved = resolve_experiment_manifest(raw)
    backend = hardware_config_from_manifest(resolved)
    layout = extract_dram_layout(create_dram(backend))
    assert layout["num_rows"] == 65536
    assert layout["capacity_bytes"] == 1 << 31
