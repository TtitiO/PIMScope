"""PIMScope accessors for Ramulator's canonical address-layout mapper.

The implementation lives in the maintained Ramulator submodule so native and
Python frontends consume one source of truth. This module keeps the parent
project's import surface stable.
"""

from ramulator.dram.addressing import (  # noqa: F401
    addr_vec_from_byte_address,
    concrete_address_layout,
    extract_dram_layout,
    validate_addr_vec,
)

__all__ = [
    "addr_vec_from_byte_address",
    "concrete_address_layout",
    "extract_dram_layout",
    "validate_addr_vec",
]
