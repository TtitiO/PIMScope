# PIMScope configuration manifests

PIMScope exposes a validated researcher-facing experiment manifest. JSON and
YAML files use the same schema; JSON is used for the checked-in example so it
works without a YAML parser during source inspection.

## Quick start

```bash
.venv/bin/pimscope validate configs/example_custom.json
.venv/bin/pimscope run configs/example_custom.json
```

The example is intentionally small (`OPT-125M`, decode, `past_len: 32`) so it
is suitable as a first custom experiment. A second example,
`configs/example_custom_model.json`, demonstrates a user-supplied dense model
without modifying the model registry. The output is a structured JSON result
containing the resolved manifest, simulator organization/timings, concrete
opcode counts, replay status, cycles, and commit provenance.

Override values for sweeps without editing the file:

```bash
.venv/bin/pimscope run configs/example_custom.json \
  --set hardware.pim.pim_banks_per_mpu=1 \
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
      "pim_banks_per_mpu": 2,
      "pim_mac_execution_model": "shared_mpu_serial"
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
    "max_inflight_requests": 16,
    "interleave_depth": 4
  },
  "output": {"path": "results/custom/result.json"}
}
```

## Accepted values and current scope

- `dram_class`: currently `LPDDR5PIM` only.
- Organization/timing names are resolved by the checked-out Ramulator fork;
  invalid names fail during backend validation.
- PIM datatypes: `int8`, `fp16`, `int16`, and `bf16`. The workload lowering
  currently advertises `int8`, `fp16`, and `bf16`; the manifest requires the
  workload and hardware datatypes to agree.
- Execution models: `shared_mpu_serial` (validated) and
  `subbank_overlap_experimental` (explicitly experimental).
- Scheduler: `FRFCFS` or `FRFCFSRowHit`.
- Refresh: `NoRefresh`, `AllBank`, or `PerBank`.
- Row policy: `Open` or `ClosedCAP`.
- Address mapper: `PassThroughAddrMapper`, `ChRaBaRoCo`, `RoBaRaCoCh`,
  `MOP4CLXOR`, or `RITAddrMapper`.
- Channel mapper: `CacheLineInterleave` or `PassThroughChannelMapper`.
- Lowering modes: `per_kind`, `per_bank`, or `all_bank`.
- Weight residency: `resident` or synthetic `full_preload`. `full_preload` is
  retained for paper-style diagnostics, but its addresses are synthetic and it
  is not yet a checkpoint placement or arbitrary-capacity mapping model.
- Phases: `decode` and `prefill`; Mixtral currently supports decode only.
- Built-in models use the registry in the Ramulator workload-surrogate module.
  A custom dense model can instead be an object with `name`, `num_layers`,
  `hidden_size`, `num_heads`, `head_dim`, and `ffn_hidden_size`, plus optional
  `num_kv_heads`, `ffn_variant`, `activation`, and citation fields. See
  [`example_custom_model.json`](example_custom_model.json).

The schema intentionally rejects unknown fields. This prevents a typo such as
`pim_bank_per_mpu` from silently changing the experiment. Hardware topology and
PIM resources are validated both by the manifest layer and by
`LPDDR5PIM.resolve()` before large trace generation begins.

The initial CLI instantiates one controller/channel, matching the validated
paper topology. Semantic PIM bank sequences are retargeted to the selected
organization's resolved bank-unit count. Selecting a mapper component does not
yet imply validated multi-channel/rank support. The legacy host-byte
decomposition also remains LPDDR5-organization-specific, so arbitrary
organization/topology address mapping is still tracked as an open release
issue rather than silently claimed.

## Interpretation boundary

A custom result is a command-level LPDDR5-PIM simulation of a structured
workload surrogate. It is not a framework/runtime trace, numerical execution,
checkpoint placement, silicon calibration, or a claim that every abstract PIM
opcode is a public JEDEC command. Results record the exact resolved manifest so
researchers can reproduce and compare sweeps.

The schema is versioned. Future incompatible changes must increment
`schema_version` and provide a migration or a clear release note.
