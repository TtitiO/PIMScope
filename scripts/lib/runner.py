"""Deprecated compatibility imports for the old direct runner path.

Use the documented simulator components or :mod:`ramulator.pimscope` for new
code.  This module remains only for one migration release.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts.lib.runner is deprecated; use ramulator.pimscope or Ramulator components",
    DeprecationWarning,
    stacklevel=2,
)

from ramulator.pimscope.runner import *  # noqa: F401,F403,E402
from ramulator.pimscope.runner import _extract_dram_layout  # noqa: E402,F401
