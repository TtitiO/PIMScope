# PIMScope configuration manifests

PIMScope exposes a validated researcher-facing experiment manifest through the
public `ramulator.pimscope` simulator API. The parent command is a thin adapter
over that API. JSON and YAML files use the same schema; JSON is used for the
checked-in example so it works without a YAML parser during source inspection.

## Quick start

From the parent repository, use the compatibility command:

```bash
.venv/bin/pimscope validate configs/example_custom.json
.venv/bin/pimscope run configs/example_custom.json
```

The maintained Ramulator fork owns the same implementation and installs a
standalone command for users of that repository alone:

```bash
.venv/bin/ramulator-pimscope validate configs/example_custom.json
.venv/bin/ramulator-pimscope run configs/example_custom.json
```

The example is intentionally small (`OPT-125M`, decode, `past_len: 32`) so it
is suitable as a first custom experiment. A second example,
`configs/example_custom_model.json`, demonstrates a user-supplied dense model
without modifying the model registry. The output is a structured JSON result
containing the resolved manifest, simulator organization/timings, concrete
opcode counts, replay status, cycles, and commit provenance. Validate a saved
result with `.venv/bin/pimscope validate-result results/custom/result.json`.

Override values for sweeps without editing the file:

```bash
.venv/bin/pimscope run configs/example_custom.json \
  --set hardware.pim.pim_banks_per_block=1 \
  --set workload.past_len=64 \
  --output results/custom/k1.json
```

Values are parsed as JSON when possible, so use `true`, `false`, numbers, and
quoted JSON strings as appropriate. `validate` applies the same overrides and
prints the canonical resolved manifest plus its SHA-256 fingerprint.

## Manifest shape

```json
{
  "schema_version": 1,
  "experiment": "my-study",
  "hardware": {
    "dram_class": "LPDDR5PIM",
    "org_preset": "LPDDR5_8Gb_x16",
    "timing_preset": "LPDDR5_6400",
    "org_overrides": {},
    "timing_overrides": {},
    "pim": {
      "pim_datatype": "int8",
      "pim_banks_per_block": 2,
      "pim_mac_execution_model": "shared_block_serial"
    },
    "controller": {
      "scheduler": "FRFCFS",
      "refresh_manager": "NoRefresh",
      "row_policy": "Open",
      "addr_mapper": "PassThroughAddrMapper"
    },
    "memory_system": {
      "clock_ratio": 1,
      "channel_mapper": "CacheLineInterleave"
    },
    "topology": {
      "controllers": 1,
      "channels": 1
    },
    "frontend_clock_ratio": 4
  },
  "workload": {
    "model": "opt-125m",
    "datatype": "int8",
    "phase": "decode",
    "past_len": 32,
    "prompt_len": 12,
    "schedule_policy": "serialized",
    "weight_residency": "resident",
    "mac_mode": "per_kind",
    "seed": 12345,
    "max_inflight_requests": 16,
    "interleave_depth": 4
  },
  "output": {"path": "results/custom/result.json"}
}
```

## Accepted values and current scope

- `dram_class`: currently `LPDDR5PIM` only.
- Organization/timing names are resolved by the checked-out Ramulator fork;
  invalid names fail during backend validation. Supported host-byte mapping
  derives all hierarchy bounds from the resolved organization and rejects
  one-past-capacity and invalid repeated ranges.
- PIM datatypes: `int8`, `fp16`, `int16`, and `bf16`. The workload lowering
  currently advertises `int8`, `fp16`, and `bf16`; the manifest requires the
  workload and hardware datatypes to agree.
- Execution models: `shared_block_serial` (validated) and
  `subbank_overlap_experimental` (explicitly experimental).
- Scheduler: `FRFCFS` or `FRFCFSRowHit`.
- Refresh: `NoRefresh`, `AllBank`, or `PerBank`.
- Row policy: `Open` or `ClosedCAP`.
- Address mapper: `PassThroughAddrMapper`, `ChRaBaRoCo`, `RoBaRaCoCh`,
  `MOP4CLXOR`, or `RITAddrMapper`.
- Channel mapper: `CacheLineInterleave` or `PassThroughChannelMapper`.
- Lowering modes: `per_kind`, `per_bank`, or `all_bank`.
- `seed`: a non-negative integer recorded in result provenance. The current
  structured workload generators are deterministic; the seed is reserved for
  randomized frontends and future randomized lowering policies.
- Weight residency: `resident` or synthetic `full_preload`. Generated host
  traffic uses the explicit `bounded_surrogate_v1` placement policy: historical
  surrogate address tokens are deterministically placed within the resolved
  device capacity before canonical byte-address mapping. `full_preload` remains
  a paper-style diagnostic, not checkpoint placement or a capacity claim.
- Phases: `decode` and `prefill`; Mixtral currently supports decode only.
- Built-in models use the registry in the Ramulator workload-surrogate module.
  A custom dense model can instead be an object with `name`, `num_layers`,
  `hidden_size`, `num_heads`, `head_dim`, and `ffn_hidden_size`, plus optional
  `num_kv_heads`, `ffn_variant`, `activation`, and citation fields. See
  [`example_custom_model.json`](example_custom_model.json).

The schema intentionally rejects unknown fields. This prevents a typo such as
`pim_bank_per_block` from silently changing the experiment. Hardware topology and
PIM resources are validated both by the manifest layer and by
`LPDDR5PIM.resolve()` before large trace generation begins.

The manifest records the supported topology explicitly with
`hardware.topology.controllers` and `hardware.topology.channels`; both must be
`1` in the current public runner. Unsupported multi-controller or multi-channel
values fail during manifest validation, before backend construction or trace
generation, rather than being silently pinned to channel/rank zero. The initial
CLI instantiates one controller/channel, matching the validated paper topology.
Semantic PIM bank sequences are retargeted to the selected organization's
resolved bank-unit count. The concrete host-byte mapper is now
mixed-radix and derived from the resolved hierarchy, including physical and
address-level sizes, transaction bytes, and capacity. Selecting a mapper
component does not imply validated multi-channel support; multi-controller and
channel-mapper semantics remain tracked separately. Literal user/trace byte
addresses fail closed when they exceed capacity; generated workload-surrogate
traffic uses `bounded_surrogate_v1` and records that policy explicitly.

## Interpretation boundary

A custom result is a command-level LPDDR5-PIM simulation of a structured
workload surrogate. It is not a framework/runtime trace, numerical execution,
checkpoint placement, silicon calibration, or a claim that every abstract PIM
opcode is a public JEDEC command. Results record the exact resolved manifest so
researchers can reproduce and compare sweeps.

The schema is versioned. Future incompatible changes must increment
`schema_version` and provide a migration or a clear release note. Concrete
opcode JSONL traces use the backend schema
`lpddr5-pim-opcode-v0.2`; validate one against a manifest-derived layout with:

```bash
.venv/bin/pimscope validate-trace path/to/trace.jsonl \\
  --config configs/example_custom.json
```

Legacy MPU configuration/result names are accepted only through a one-release
compatibility layer, normalized to shared-block names, and accompanied by
`DeprecationWarning`; conflicting old and new fields fail closed.
