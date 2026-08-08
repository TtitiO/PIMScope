"""Deprecated compatibility imports for the old PIMScope config path.

Use :mod:`ramulator.pimscope.config` for new code.  This module remains for
one migration release so existing researcher scripts do not break silently.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts.lib.config is deprecated; use ramulator.pimscope.config",
    DeprecationWarning,
    stacklevel=2,
)

from ramulator.pimscope.config import (  # noqa: E402,F401
    DEFAULT_HARDWARE,
    DEFAULT_WORKLOAD,
    MANIFEST_SCHEMA_VERSION,
    ResolvedExperiment,
    apply_overrides,
    load_experiment_manifest,
    load_raw_manifest,
    resolve_experiment_manifest,
)

__all__ = [
    "DEFAULT_HARDWARE",
    "DEFAULT_WORKLOAD",
    "MANIFEST_SCHEMA_VERSION",
    "ResolvedExperiment",
    "apply_overrides",
    "load_experiment_manifest",
    "load_raw_manifest",
    "resolve_experiment_manifest",
]
