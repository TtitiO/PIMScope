"""Deprecated compatibility imports for the old parent address API.

Use :mod:`ramulator.dram.addressing` for new simulator code.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts.lib.addressing is deprecated; use ramulator.dram.addressing",
    DeprecationWarning,
    stacklevel=2,
)

from ramulator.dram.addressing import (  # noqa: E402,F401
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
