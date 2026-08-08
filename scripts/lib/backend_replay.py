"""Deprecated compatibility imports for the old replay path.

Use :mod:`ramulator.pimscope.backend` for new code.  The implementation now
lives in the maintained Ramulator fork so researchers can use it without the
parent paper repository.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts.lib.backend_replay is deprecated; use ramulator.pimscope.backend",
    DeprecationWarning,
    stacklevel=2,
)

from ramulator.pimscope.backend import *  # noqa: F401,F403,E402
from ramulator.pimscope.backend import (  # noqa: E402,F401
    _component,
    create_address_mapper,
    create_concrete_frontend,
    create_memory_system,
    infer_model_family,
)

# One-release compatibility for private names used by existing local scripts.
_make_addr_mapper = create_address_mapper
_make_frontend = create_concrete_frontend
_make_mem = create_memory_system
_infer_model_family = infer_model_family
