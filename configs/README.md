# PIMScope configuration files

This directory is reserved for versioned, validated hardware and workload
manifests used by the public CLI.

The current paper artifact path still defines its model list and LPDDR5-PIM
settings in Python (`scripts/gen_figures.py` and
`scripts/lib/backend_replay.py`). That is sufficient to reproduce the released
paper artifacts, but it is not yet the intended long-term interface for
architecture researchers.

The next public configuration interface should support:

- LPDDR5 organization and timing presets;
- channel and rank topology;
- scheduler, row policy, refresh policy, and address mapping;
- PIM datatype, SIMD width, bank slots, and banks per shared MPU;
- command issue and request completion timing;
- model architecture, decode context, prefill prompt, and weight-residency
  policy;
- custom workload manifests without editing simulator source code.

Until that schema lands, use the Python APIs documented in `README.md` and
`ramulator2/README.md`. Do not treat an unvalidated ad-hoc YAML file as a
supported configuration format.
