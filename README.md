# PIMScope: Command-Level LPDDR-PIM Simulation for Transformer Inference

PIMScope is an open-source LPDDR5-PIM extension built on
[Ramulator 2.1](https://github.com/CMU-SAFARI/ramulator2). It adds explicit
single-bank and rank-scoped PIM commands, shared-block resource modeling,
command/completion timing separation, PIM-aware trace frontends, workload
lowering, and structural power-accounting hooks.

`ramulator2/` is a Git submodule pinned to a validated commit of the maintained
[`TtitiO/ramulator2`](https://github.com/TtitiO/ramulator2) fork. The fork's
`main` branch is based on current CMU-SAFARI `main`; PIMScope changes are kept
in explicit commits on top of that upstream history rather than replacing
upstream infrastructure or tests.

## Clone

Use a recursive clone so the simulator fork is checked out at the exact commit
validated by this repository:

```bash
git clone --recurse-submodules https://github.com/TtitiO/PIMScope.git
cd PIMScope
```

For an existing clone:

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

The submodule URL is public HTTPS; read-only users and CI do not need GitHub SSH
credentials.

## Community, licensing, and citation

See [CONTRIBUTING.md](CONTRIBUTING.md) for development checks, change ownership,
and reproducibility requirements. Community participation follows
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). PIMScope software is released under
[LICENSE](LICENSE), with upstream and third-party attribution in [NOTICE](NOTICE).
The final paper citations will be provided in this README.

## Supported environment

The documented reference environment is Ubuntu 24.04 with Python 3.11 or newer,
CMake 3.14 or newer, and a C++20 compiler. Verify the tools before building:

```bash
python3 --version
cmake --version                 # must be >= 3.14
c++ --version                   # must support C++20
git submodule status
```

On Ubuntu, install the basic host tools with:

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake python3 python3-dev python3-venv python3-pip
```

## Build and install

Create one project-root virtual environment. Install the checked-out Ramulator
fork before the parent package: the parent declares `ramulator==2.1.0`, and its
implementation comes from the pinned submodule rather than an unrelated package
from an index.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip setuptools wheel
.venv/bin/python -m pip install -r ramulator2/requirements-dev.txt
.venv/bin/python -m pip install --no-build-isolation -e ramulator2
.venv/bin/python -m pip install --no-build-isolation -e .
```

Build the public runtime backend. The test-only native harness is disabled by
default. Use the same Python for installation, CMake configuration, and
execution. Check `command -v cmake` and `cmake --version`; vendor SDKs can put
an outdated CMake first in `PATH`.

```bash
CMAKE=$(command -v cmake)  # must report version 3.14 or newer
"$CMAKE" -S ramulator2 -B ramulator2/build \
  -DPython_EXECUTABLE="$PWD/.venv/bin/python" \
  -DCMAKE_BUILD_TYPE=Release
"$CMAKE" --build ramulator2/build -j"$(nproc)"
```

The selected Python needs development headers (`Development.Module`). If
`pimscope doctor` reports an ABI mismatch, remove the stale build directory and
rebuild; a CPython 3.12 extension cannot be loaded by CPython 3.11.

If your default compiler produces binaries requiring a newer GLIBC than the
target machine, select an older supported compiler explicitly, for example with
`-DCMAKE_CXX_COMPILER=/path/to/clang++`.

Check the installed package, native ABI, toolchain, and tutorial backend:

```bash
.venv/bin/pimscope doctor --config configs/example.json
```

A successful report ends with `"valid": true`. If doctor reports a stale ABI,
remove the build directory and rebuild with the same Python used to create the
virtual environment.

For lower-level Ramulator component examples and its separately maintained test
suite, see [`ramulator2/README.md`](ramulator2/README.md). They are not required
to follow the PIMScope workload tutorial below.

## Reproduce the paper artifacts

Paper reproduction is intentionally separate from the researcher-facing
simulator API. Run the fixed camera-ready experiment matrix directly:

```bash
.venv/bin/python scripts/gen_figures.py --all --workers 64
```

Collect individual targets with `--collect cross-model` or `--collect
pim-sharing`; render the cross-model figure with `--render cross-model`. Use
`--force` to regenerate valid caches and `--workers 1` for debugging. Each
independent simulation runs in an isolated process and writes a distinct part
file; aggregation fails closed if a worker, part, or replay fails. The process
pool is capped to pending tasks and warns if a conservative 1 GiB-per-worker
estimate exceeds available memory; choose a smaller `--workers` value when
warned. Generated results are local state under `results/` and are ignored by
Git. See
[`CODE_QUALITY.md`](CODE_QUALITY.md) for the release gate and the maintainer
procedure for checking latency cycles against the old-tag oracle.

## Docker

The maintained container configuration is inside the simulator submodule. Run
Compose from that directory so its relative build context is correct:

```bash
cd ramulator2
docker compose up -d --build --wait
docker compose exec ramulator2 bash
```

## Configure workloads and LPDDR5-PIM

The release and paper artifacts support LPDDR5-PIM. The maintained fork also
contains an explicitly experimental `LPDDR6PIM` backend for development and
conformance testing; it is not used by this tutorial or the paper matrix.
Generic `LPDDR6` is not interchangeable with `LPDDR6PIM`. The experimental
backend's single-subchannel and non-device-calibrated power boundaries are
machine-readable and documented in
[`ramulator2/docs/PIMScope-metadata.md`](ramulator2/docs/PIMScope-metadata.md).

## Tutorial: run one workload

The checked-in tutorial is a small two-layer `TinyTransformer` decode, so it
exercises the complete generate → lower → native replay → validate path without
running the full paper matrix. It composes:

- [`configs/hardware/lpddr5-pim.json`](configs/hardware/lpddr5-pim.json), the
  reusable supported hardware section; and
- [`configs/workloads/tiny-transformer-decode.json`](configs/workloads/tiny-transformer-decode.json),
  explicit model dimensions and trace-generation controls.

First resolve and validate the manifest. `--no-backend` is useful before a
native build; omit it to validate the resolved DRAM backend too.

```bash
.venv/bin/pimscope validate configs/example.json --no-backend
.venv/bin/pimscope validate configs/example.json
```

Then run and independently validate the saved result:

```bash
.venv/bin/pimscope run configs/example.json \
  --output results/tutorial/tiny-transformer-decode.json
.venv/bin/pimscope validate-result \
  results/tutorial/tiny-transformer-decode.json
```

The result records the resolved manifest and fingerprint, hardware organization
and timing, workload summary, concrete opcode counts, cycles, replay-integrity
checks, power-accounting boundary, seed, and source provenance. A successful run
has top-level `"status": "PASS"`.

### Override parameters for a small sweep

Use dotted `--set` overrides without editing source:

```bash
.venv/bin/pimscope run configs/example.json \
  --set hardware.pim.pim_banks_per_block=1 \
  --set workload.past_len=64 \
  --output results/custom/per-bank.json
```

The interface exposes organization/timing presets and overrides, PIM datatype
and resources, shared-block grouping, timing and energy terms, scheduler,
refresh, row policy, address/channel mappers, decode/prefill lengths,
materialization, concurrency, an explicit recorded seed, lowering mode,
built-in model keys, custom dense model dimensions, and an optional
process-isolated simulation timeout. The current public workload type is
`structured_transformer_surrogate`. Unknown or inconsistent fields fail with a
dotted-path error. The
first interface records and validates an explicit topology, but is deliberately
bounded to the validated one-controller/channel PIM topology. Values
other than `hardware.topology.controllers=1` and
`hardware.topology.channels=1` fail before backend construction; they are not
silently mapped to channel/rank zero. Within the supported scope, host-byte
mapping is derived from the resolved hierarchy and capacity;
multi-controller/channel simulation remains an explicit open issue. See
[`configs/README.md`](configs/README.md) for the complete schema and current
scope.

The reusable researcher-facing Python API is `ramulator.pimscope`. The parent
installs `pimscope`; installing the submodule alone provides
`ramulator-pimscope`. Both resolve to the same simulator-owned CLI, and there is
no duplicate parent implementation. Saved results, aggregates, and concrete
traces can be validated independently with `validate-result`,
`validate-aggregate`, and `validate-trace`. The lower-level typed component API
remains available for simulator developers, but ordinary sweeps require only a
manifest and the CLI.

## Modeling scope

PIMScope's extra opcodes are explicit simulator abstractions, not claims that
each name is a literal public JEDEC command. In particular:

- command launch interval and request completion latency are separate;
- per-bank completion includes pipeline, movement, and writeback residency;
- `shared_block_serial` serializes banks that share a PIM block;
- `PIM_MAC_AB` is rank-scoped and completes according to the shared-block model;
- all-bank mode transitions and refresh interactions are modeled explicitly;
- datatype-driven timing behavior is opt-in and validated.

The exact execution contract and statistics are documented in the
[LPDDR5-PIM section of the Ramulator fork guide](ramulator2/README.md#lpddr5-pim-execution-semantics).

## Technical reference

The current paper is available at [`paper/PIMScope_camera_ready.pdf`](paper/PIMScope_camera_ready.pdf).
The released PDF has resolved citations and cross-references and embedded fonts.

## Updating Ramulator

To synchronize future CMU-SAFARI changes safely:

1. preserve a Git bundle and archives of the current PIMScope implementation;
2. fetch `https://github.com/CMU-SAFARI/ramulator2` as `upstream`;
3. integrate upstream on an isolated worktree/branch;
4. keep upstream infrastructure/tests and port only PIMScope-owned behavior;
5. build, run focused and broad tests, run examples, and validate a fresh
   recursive clone;
6. push the validated fork commit, then advance this repository's immutable
   submodule gitlink.

Do not update the parent gitlink to an unpushed or unvalidated fork commit.
