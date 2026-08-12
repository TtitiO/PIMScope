# PIMScope: Command-Level LPDDR-PIM Simulation for Transformer Inference

PIMScope is an open-source LPDDR5-PIM extension built on
[Ramulator 2.1](https://github.com/CMU-SAFARI/ramulator2). It adds explicit
single-bank and rank-scoped PIM commands, shared-block resource modeling,
command/completion timing separation, PIM-aware trace frontends, workload
lowering, and structural power-accounting hooks.

The LPDDR5-PIM energy output preserves the paper's two-layer contract,
`E_total = E_LPDDR + E_PIM`. `E_LPDDR` uses the embedded camera-ready
LPDDR5-6400 IDD analysis profile and legacy conversion; result provenance
records currents in mA, voltages in V, time in ns, output in pJ, and the
retained `1e-3` scale. The PDF cites the DRAMPower IDD method but does not
publish a device part number or machine-readable source profile, so these
values are reproducibility inputs—not calibrated absolute device-energy data.
`E_PIM` remains the separately reported incremental PIM event term.

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
The final arXiv and IEEE paper citations will be provided in this README.

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

Use `pimscope run` for normal experiments. `scripts/gen_figures.py` is a
separate paper-reproduction tool, not a simulator plugin or public simulation
API.

Create one project-root virtual environment for the simulator and artifact
scripts:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip setuptools wheel
.venv/bin/python -m pip install -r ramulator2/requirements-dev.txt
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install --no-build-isolation -e ramulator2
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

Run the two smoke examples:

```bash
(
  cd ramulator2
  ../.venv/bin/python examples/example_config.py
  ../.venv/bin/python examples/lpddr5_pim_example_config.py
)
```

## Validation

The upstream Ramulator test infrastructure is preserved. Tests that use the
native controller/device harness require an opt-in build:

```bash
cmake -S ramulator2 -B ramulator2/build-tests \
  -DPython_EXECUTABLE="$PWD/.venv/bin/python" \
  -DRAMULATOR_TEST_BINDINGS=ON \
  -DCMAKE_BUILD_TYPE=Release
cmake --build ramulator2/build-tests -j"$(nproc)"
(
  cd ramulator2
  ../.venv/bin/python -m pytest -q \
    tests/controller_scheduling \
    tests/device_timings \
    tests/smoke \
    tests/unit_tests \
    tests/test_LPDDR5_params.py \
    tests/test_lpddr5_pim_config.py \
    tests/test_REFpb.py
)
```

See [`ramulator2/README.md`](ramulator2/README.md) for the complete simulator
guide and test suite.

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

The release supports LPDDR5-PIM. LPDDR6-PIM is retained in the maintained
fork as an experimental development path and is not part of the supported
one-workload tutorial or paper reproduction. Generic LPDDR6 is not
interchangeable with LPDDR6PIM. Its remaining adaptation and validation work is
tracked in the supported-scope section of [`CODE_QUALITY.md`](CODE_QUALITY.md).

## Run one workload

Custom studies use a versioned, validated JSON/YAML manifest and the installed
`pimscope` CLI. The example composes an explicit reusable hardware file with an
explicit workload file containing model dimensions and trace-generation
parameters. Start with [`configs/example.json`](configs/example.json):

```bash
.venv/bin/pimscope doctor --config configs/example.json
.venv/bin/pimscope validate configs/example.json
.venv/bin/pimscope run configs/example.json \
  --output results/tutorial/one-workload.json
.venv/bin/pimscope validate-result results/tutorial/one-workload.json
```

Small parameter sweeps can use command-line overrides without editing source:

```bash
.venv/bin/pimscope run configs/example.json \
  --set hardware.pim.pim_banks_per_block=1 \
  --set workload.past_len=64 \
  --output results/custom/per-bank.json
```

The interface exposes organization/timing presets and overrides, PIM datatype
and resources, shared-block grouping, timing and energy terms, scheduler,
refresh, row policy, address/channel mappers, decode/prefill lengths, materialization,
concurrency, an explicit recorded seed, lowering mode, built-in model keys, and
custom dense model dimensions, external workload types, and an optional
process-isolated simulation timeout. Unknown or inconsistent fields fail with a dotted-path error. The
first interface records and validates an explicit topology, but is deliberately
bounded to the validated one-controller/channel PIM topology. Values
other than `hardware.topology.controllers=1` and
`hardware.topology.channels=1` fail before backend construction; they are not
silently mapped to channel/rank zero. Within the supported scope, host-byte
mapping is derived from the resolved hierarchy and capacity;
multi-controller/channel simulation remains an explicit open issue. See
[`configs/README.md`](configs/README.md) for the complete schema and current
scope.

The paper reproduction command intentionally remains fixed to the versioned
paper configuration. The reusable researcher-facing simulator API is
`ramulator.pimscope`. Both installed command names resolve directly to
`ramulator.pimscope.cli:main`; there is no parent CLI implementation. Saved results and concrete traces can be
validated independently with `pimscope validate-result` and
`pimscope validate-trace`. Run `pimscope doctor` to verify the imported
Ramulator package, native extension, selected PIM component, and optionally a
manifest/backend before starting a larger experiment. The lower-level typed Python component API remains
available for simulator developers, but architecture researchers should not
need to edit generated C++ or the artifact scripts for ordinary sweeps.

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
