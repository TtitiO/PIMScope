# PIMScope: Command-Level LPDDR-PIM Simulation for Transformer Inference

PIMScope is an open-source LPDDR5-PIM extension built on
[Ramulator 2.1](https://github.com/CMU-SAFARI/ramulator2). It adds explicit
single-bank and rank-scoped PIM commands, shared-MPU resource modeling,
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

Create one project-root virtual environment for the simulator and artifact
scripts:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip setuptools wheel
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install -r ramulator2/requirements-dev.txt
.venv/bin/python -m pip install --no-build-isolation -e ramulator2
```

Build the public runtime backend. The test-only native harness is disabled by
default and is not required by examples or artifact reproduction. If
the virtual environment does not provide a CMake wrapper, use the verified
system `cmake` command:

```bash
cmake -S ramulator2 -B ramulator2/build \
  -DPython_EXECUTABLE="$PWD/.venv/bin/python" \
  -DCMAKE_BUILD_TYPE=Release
cmake --build ramulator2/build -j"$(nproc)"
```

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

After the runtime build succeeds, follow [`scripts/README.md`](scripts/README.md).
The short form is:

```bash
.venv/bin/pimscope-artifacts --all --workers 8
```

The direct form remains supported:

```bash
.venv/bin/python scripts/gen_figures.py --all --workers 8
```

Generated data and figures are written under `results/`, which is intentionally
ignored as local/generated state. Artifact JSON uses repository-relative cache
paths rather than machine-specific absolute paths. Collection fails rather than
assembling a partial artifact if a worker fails, a required part is missing, or
a backend replay does not pass.

## Docker

The maintained container configuration is inside the simulator submodule. Run
Compose from that directory so its relative build context is correct:

```bash
cd ramulator2
docker compose up -d --build --wait
docker compose exec ramulator2 bash
```

## Configure workloads and LPDDR5-PIM

The simulator and workload generator are currently configurable through Python.
For LPDDR5-PIM hardware parameters, construct
`ramulator.dram.LPDDR5PIM(...)`; for supported transformer architecture
parameters, use the generators under
`ramulator.workload_surrogate.generate_full_transformer`. The exact resource
and timing parameters are documented in the Ramulator fork guide.

The paper reproduction command intentionally uses the fixed, versioned paper
configuration. A validated YAML/JSON manifest and higher-level CLI for custom
hardware and workloads are the next release milestone; the planned schema is
outlined in [`configs/README.md`](configs/README.md). Until that interface is
implemented, custom studies should use the typed Python component API rather
than editing generated C++ files.

## Modeling scope

PIMScope's extra opcodes are explicit simulator abstractions, not claims that
each name is a literal public JEDEC command. In particular:

- command launch interval and request completion latency are separate;
- per-bank completion includes pipeline, movement, and writeback residency;
- `shared_mpu_serial` serializes banks that share an MPU;
- `PIM_MAC_AB` is rank-scoped and completes according to the shared-MPU model;
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
