# PIMScope open-source readiness issues

**Status:** active release checklist. Findings are retained here as issues are
closed or discovered; generated results and local caches are not release files.

**Latest implementation:** parent `af0d6da` contains the thin simulator
adapter, schema validation, terminology migration, seed provenance, doctor
checks, topology guards, and the explicit LPDDR6-PIM adaptation plan; the
maintained Ramulator submodule is pinned at `cdc513e`. Generic LPDDR6
construction was smoke-verified without enabling LPDDR6-PIM semantics. The recent terminology audit was backed up at
`/home/tinglin/wksp/PIMScope-backups/mpu-terminology-audit-20260808T112830Z`.
The earlier configuration-interface backup remains at
`/home/tinglin/wksp/PIMScope-backups/config-interface-before-20260807T022039Z`.

**Progress snapshot (2026-08-09):** this checklist contains 53 issue entries;
8 P0, 30 P1, and 15 P2. P1-27 records the newly requested LPDDR6-PIM
adaptability work; generic LPDDR6 construction is verified, and LPDDR6-PIM
remains explicitly experimental. Eight P0/release-hygiene closure clusters are recorded
under `Closed items`; seven P1 entries are explicitly closed or bounded in
their headings (`P1-6`, `P1-7`, `P1-9`, `P1-10`, `P1-20`, `P1-22a`, and
`P1-26`). P1-22b has an implemented, tested migration but is not counted as
closed until publication and compatibility review. The maintained fork now includes shared Python/native LPDDR6PIM trace fixtures
covering positive replay, host-address mapping, all-bank sequencing,
schema/backend mismatches, malformed headers, unsupported opcodes, and address
bounds. The native concrete frontend lifecycle was corrected so records are
initialized and replayed once rather than twice. Focused parent tests pass 22
tests; the focused Ramulator/PIM and trace conformance suites pass 76 tests. The
latest topology/doctor revision adds early unsupported-topology rejection,
package/native-component diagnostics, and manifest-backed address-layout checks.
P2 work has not yet been treated as release-complete.

**Audit date:** 2026-08-06; implementation updates 2026-08-07–2026-08-08; seed-control and LPDDR6-planning updates 2026-08-08

**Repository inspected:** root `master` at `af0d6da` with the `ramulator2`
submodule at `cdc513e`.

**Paper inspected:** `paper/PIMScope_camera_ready.pdf` (8 pages).

**Scope:** identify the issues that should be resolved before a public release that is expected to be cloneable, buildable, reproducible, legally distributable, and usable by people changing the DRAM hardware model or workload. This document deliberately includes confirmed blockers, reproducibility risks, modeling limitations, and product/documentation work. It is not a statement that every modeling limitation is a software bug.

---

## Executive release assessment

The repository is **not yet ready for a final community release**, although
clean-clone/build/reproduction and the first researcher configuration interface
are now implemented. The most immediate remaining concerns are:

1. Reusable simulator configuration/replay functionality is split across the parent `scripts/` package instead of living behind a clear Ramulator/PIMScope simulator API.
2. Public terminology is now canonicalized to shared-block names in the
working tree; legacy MPU spellings remain only in the documented one-release
compatibility layer and negative migration tests. Publication and final
compatibility review remain tracked as P1-22b.
3. Multi-controller/channel mapping remains unvalidated; the public manifest now records topology and rejects unsupported non-single-controller/channel values before backend construction.
4. Aggregate/trace/result schemas now have initial shared machine-readable
validation; broader row-level schemas and migration fixtures remain open.
5. The camera-ready PDF and generated artifact claims need a mechanical release gate, including resolution of the cold-start wording discrepancy.
6. The complete clean-clone CI workflow has been added and locally parses; it still needs to pass on GitHub before it can be treated as a release gate.
7. The new custom runner needs broader multi-rank/channel, datatype, refresh, and negative trace coverage before those combinations are advertised as validated.
8. LPDDR6-PIM remains experimental and is not a paper-reproduction backend.
The underlying fork has an explicit LPDDR6PIM DRAM/controller/frontend path,
backend-specific trace schema, and separate power boundary. Independent source
model validation, broader hierarchy coverage, and final release gating remain
open.

Recommended release gate: do not announce the repository as “easy to use” until all **P0** items are closed and the core **P1** items have either been implemented or explicitly scoped in the public documentation.

---

## Audit evidence and commands

The following checks were run during the audit:

- `git pull --ff-only`: the root repository was already up to date.
- Root status initially contained untracked `.venv/`, `ramulator2_ext.egg-info/`, and `results/`.
- `ramulator2` is a detached submodule at `968a267`; `origin/v2.1` currently points at `bb7cb92`.
- `compileall` succeeded for the Python sources.
- The first normal CMake build using `/usr/bin/cmake` (3.16.3) failed during configuration because `tests/cpp/test_harness.cpp` does not exist.
- The default `cmake` on this machine resolves to an unrelated Xilinx CMake 3.3.2, below the documented/project minimum of 3.14; the setup instructions do not protect users from this PATH problem.
- A Python import works only because the local environment contains editable-install path hooks and/or the working tree is on the import path; the root package itself does not provide a normal `ramulator2_ext` importable module.
- The generated `results/decode_cycles.json` includes source cache paths such as `/home/tinglin/wksp/PIMScope/results/...`.
- PDF text extraction from the paper contains many `[?]` and `??` placeholders.

The CMake failure is a release blocker independent of the local machine’s CMake PATH. The CMake 3.3.2 issue is an additional environment/documentation failure observed on this workstation.

---

# P0 — must fix before public release

## Closed items

The following earlier blockers are now addressed in the current public commits:

- **Anonymous recursive clone:** `.gitmodules` uses HTTPS and pins the parent
  gitlink to a public fork commit; a fresh public recursive clone was verified.
- **Default CMake build:** the optional `_ramulator_test` binding is off by
  default and no longer breaks runtime builds.
- **Optional test harness:** `RAMULATOR_TEST_BINDINGS=ON` builds the native
  harness; the project-owned suites pass in the validated host environment.
- **Docker path:** the submodule contains the referenced `.devcontainer` files,
  and the parent README now tells users to run Compose from `ramulator2/`.
- **Root packaging and CLI:** the parent provides the `pimscope-artifacts`
  entry point and packages `scripts` as a Python package.
- **Initial researcher configuration interface:** `pimscope validate` and
  `pimscope run` accept strict version-1 JSON/YAML manifests, print/record a
  canonical resolved configuration and fingerprint, support dotted-path
  `--set` overrides, and run built-in or custom dense workloads without source
  edits. `configs/example_custom.json` and `configs/example_custom_model.json`
  both pass end-to-end replay. Focused sweeps also passed for NoRefresh,
  AllBank, PerBank, FRFCFSRowHit, ClosedCAP, both channel mappers, all exposed
  address mappers (including nested RIT), both LPDDR5 organization presets,
  and int8/fp16/bf16 configurations. The custom runner retargets semantic bank
  sequences to the resolved bank-unit count rather than retaining the paper's
  fixed 16-bank sequence.
- **CI and release hygiene:** a clean-clone workflow, root license/NOTICE, and
  generated-state `.gitignore` entries are now present.
- **Absolute artifact paths:** aggregate output uses repository-relative cache
  paths and records parent/submodule commit provenance.
- **Paper-result regeneration:** after deleting the local `results/` directory,
  all 58 cross-model parts, 30 PIM-sharing parts, 30 decode rows, 28 prefill
  rows, the sharing table, and the figure were regenerated. All replay checks
  passed, and normalized numerical results matched the pre-regeneration backup.
- **Fail-closed collection:** worker failures, missing parts, failed replay
  status, and incomplete aggregate row counts now stop artifact generation.
- **Cache integrity:** part reuse now validates a fingerprint over task
  configuration and parent/Ramulator source state; legacy/stale parts regenerate.

These closures do not remove the historical audit evidence below; they record
the current status and acceptance evidence.

## P0-1. Make the submodule cloneable by anonymous HTTPS users

**Evidence:** `.gitmodules` sets:

```ini
url = git@github.com:TtitiO/ramulator2.git
branch = v2.1
```

The public root remote is HTTPS, but the nested dependency requires SSH authentication and a configured GitHub key. This breaks the common fresh-clone flow:

```bash
git clone https://github.com/TtitiO/PIMScope.git
git submodule update --init --recursive
```

**Why it matters:** a public open-source project must not require contributors to have write access or SSH credentials merely to download a dependency. It also breaks many hosted CI runners.

**Required resolution:** use a public HTTPS submodule URL, or vendor the extension in a properly attributed tree, or publish a release archive that includes a source snapshot. Pin an immutable commit rather than relying on a moving branch. Test both a fresh clone without GitHub credentials and a CI checkout.

**Also document:** whether the fork is intended to be a maintained fork, whether upstream Ramulator changes are synchronized, and how security/bug fixes are incorporated.

---

## P0-2. Fix the default CMake build after the release removed tests

**Evidence:** `ramulator2/CMakeLists.txt:120` unconditionally declares:

```cmake
nanobind_add_module(_ramulator_test tests/cpp/test_harness.cpp)
```

The checked-out release submodule contains no `tests/` directory and no `tests/cpp/test_harness.cpp`. The submodule history includes commit `7172856` (“tests: remove tests, prepare for code release”), but the CMake target remained.

Observed failure:

```text
Cannot find source file: tests/cpp/test_harness.cpp
No SOURCES given to target: _ramulator_test
```

**Required resolution:** either restore the tests and test harness, or guard the target behind an option and default it off when the source is absent, for example:

```cmake
option(RAMULATOR_BUILD_TEST_BINDING "Build the C++ test binding" OFF)
if(RAMULATOR_BUILD_TEST_BINDING AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests/cpp/test_harness.cpp")
  ...
endif()
```

Do not silently remove validation; restore a maintained test suite as a separate release task.

**Acceptance test:** a clean checkout with no ignored build directory must configure and build with the documented command.

---

## P0-3. Repair or remove the documented Docker path

**Evidence:** root `README.md` instructs users to run `docker compose ...`, but the only compose file is `ramulator2/docker-compose.yml`, which references:

- `.devcontainer/Dockerfile`
- `.devcontainer/post-create.sh`

Neither file is present in the checked-out `ramulator2` submodule. The compose context is also the submodule directory, not the project root, so the root README command does not select this compose file automatically.

**Required resolution:** choose one supported container flow and make it executable:

- add and track a complete root-level `Dockerfile`/`compose.yaml`, or
- restore the referenced `.devcontainer` files and document `docker compose -f ramulator2/docker-compose.yml ...`, or
- remove the Docker instructions until they work.

Pin the base image/toolchain and include a smoke test in the container build.

---

## P0-4. Provide one supported installation/build path for the complete project

The current process crosses three package/build systems and requires manual path management:

1. install the root package with `pip install -e .`;
2. enter `ramulator2`;
3. run CMake with a specially selected Python executable;
4. install the nested Ramulator package separately;
5. add `ramulator2/python:ramulator2` to `PYTHONPATH` for the scripts.

The root `pyproject.toml` declares only `matplotlib` and `numpy`, while the nested `ramulator2/pyproject.toml` declares the separate package `ramulator==2.0.0`. The root package does not define a CLI, package the `scripts` as an installable module, or declare the nested package as a dependency. Its `main.py` only prints `Hello from ramulator2-ext!`.

**Required resolution:** define a supported project layout and make it work from a fresh checkout. Options include:

- a root launcher that builds/imports the nested backend and exposes `pimscope` commands;
- a workspace/monorepo package configuration with a documented editable install for both packages;
- a release script/Make target that validates paths and performs all setup;
- or a standalone artifact package with a clearly versioned backend wheel.

The normal user should not need to understand `PYTHONPATH`, CMake cache variables, nested editable installs, or generated bindings just to run a first example.

---

## P0-5. Restore automated validation and add CI

The release submodule has no tracked `tests/` directory, despite its README describing smoke, latency-throughput, device-timing, and controller-scheduling suites. The root project also has no CI workflow and no root tests.

**Required resolution:** restore or replace tests covering at least:

- clean build and Python import;
- LPDDR5-PIM smoke simulation;
- command legality and timing prerequisites for `SB`, `HAB`, `HAB_PIM`, `PIM_BCAST`, `PIM_MAC`, and `PIM_MAC_AB`;
- shared-MPU serialization and `pim_banks_per_mpu` behavior;
- per-bank and all-bank trace sequence validation;
- trace address decomposition for every supported organization;
- datatype/resource parameter validation;
- semantic-to-concrete lowering counts and dependency preservation;
- a small reproducibility experiment.

Add CI for at least Linux + the documented Python/CMake/compiler range. CI must initialize the submodule and run from a clean checkout, not from the developer’s existing build directory.

---

## P0-6. Make the public technical reference release-quality

The camera-ready PDF in `paper/PIMScope_camera_ready.pdf` contains unresolved citation placeholders (`[?]`, `??`) and visible errors such as “comparsion”, “Conext”, “Curan”, and malformed/broken references/URLs. It also includes future-looking dates and references that should be checked before publication.

**Required resolution:** regenerate and replace the PDF after:

- resolving every citation and cross-reference;
- fixing text, figure labels, spelling, and URLs;
- checking the claims against the released code and result files;
- adding a machine-readable citation record (for example `CITATION.cff` or BibTeX);
- stating the exact root commit and submodule commit used for the artifacts.

If the PDF is only a draft, label it as such and do not call it camera-ready.

---

## P0-7. Establish a complete license and third-party attribution policy

The root project has no root `LICENSE`, `NOTICE`, `CITATION.cff`, `CONTRIBUTING.md`, or `CODE_OF_CONDUCT.md`. The only directly visible license is `ramulator2/LICENSE`, which covers Ramulator but does not clearly state the license for the PIMScope scripts, model metadata, paper, or generated artifacts. The nested source also contains fetched/untracked `ext/` dependencies whose licensing is not represented at the root release boundary.

**Required resolution:** obtain a rights/attribution review and add:

- a root license for PIMScope-owned code;
- a `NOTICE` listing Ramulator, yaml-cpp, fmt, nanobind, and any other distributed code;
- a clear policy for the paper and generated results;
- citations for model architecture specifications and external energy/timing sources;
- a `CITATION.cff`/BibTeX entry;
- contributor and conduct documents appropriate for a community project.

Do not assume that the submodule’s MIT license automatically licenses the root project or third-party data/model descriptions.

---

## P0-8. Remove machine-specific generated state from the public release

The root working tree currently contains untracked `.venv/`, `ramulator2_ext.egg-info/`, and `results/`. Root `.gitignore` ignores only `__pycache__/`; it does not ignore virtual environments, build outputs, CMake state, egg metadata, `.ruff_cache`, or generated results. The audit itself caused and then removed root `CMakeCache.txt`/`CMakeFiles/`; a normal user can easily recreate this noise.

The generated result JSON present in the working tree also stores absolute local paths in `source_cache`; these files are currently untracked in this checkout, so the release policy for them is unclear.

**Required resolution:**

- update the root `.gitignore` for `.venv/`, `build/`, CMake state, `*.egg-info/`, caches, and generated result/figure directories as appropriate;
- decide deliberately which small reference results should be tracked and which should be generated;
- store relative paths or omit local paths from JSON;
- ensure no binary build products, local virtual environments, Python bytecode, or machine metadata are part of a release commit;
- add a clean-tree release check.

---

# P1 — high-priority usability, correctness, and reproducibility issues

## P1-1. Pin and verify all build dependencies

The top-level CMake uses `FetchContent` to fetch yaml-cpp, fmt, and nanobind from GitHub. The nested source contains ignored dependency directories, and the build behavior depends on whether those directories have already been populated. `FETCHCONTENT_UPDATES_DISCONNECTED` is enabled, which can make an existing stale dependency silently persist.

**Required resolution:** pin immutable commits or verified release archives, record checksums where practical, document offline/air-gapped behavior, and test both:

- an empty `ext/`/build directory;
- a pre-populated but stale dependency directory.

Clarify whether dependencies are distributed, fetched, or expected from the system.

---

## P1-2. Make toolchain detection explicit and fail with actionable messages

The project requires CMake >= 3.14 and C++20, while the documented setup does not install/verify a CMake version. On this machine, `cmake` resolves to Xilinx CMake 3.3.2 and fails before configuration. `/usr/bin/cmake` is 3.16.3 and proceeds far enough to reveal the missing test harness. The nested `ramulator2/build.sh` is also out of sync with the root instructions: it assumes a virtual environment at `ramulator2/.venv`, invokes `uv`, and uses the ambient `python`, whereas the root flow uses `../.venv/bin/python` and `pip`.

**Required resolution:** add a preflight command/script that reports and validates:

- CMake version;
- C++ compiler and C++20 support;
- Python version and development headers;
- `pip`/build backend;
- available RAM/disk for large traces;
- Git/submodule accessibility.

The error should say how to select a supported CMake rather than just emitting the raw CMake error.

---

## P1-3. Make Python dependencies reproducible

The root package declares open-ended `matplotlib>=3.7` and `numpy>=1.24` dependencies but has no root lock file or tested upper bounds. The nested package requires `pyyaml`, and the nested `uv.lock` is not used by the root installation flow. A fresh user can therefore receive a materially different Python stack from the one used to generate the paper artifacts.

**Required resolution:** choose and document one dependency strategy: a maintained lock file with a supported update process, or a tested version matrix with compatible ranges. Include `pyyaml` and the compiled-backend installation in the supported environment. Record resolved Python package versions in artifact provenance.

---

## P1-4. Synchronize project/version metadata

The root project calls itself an extension to “Ramulator 2.0”, the vendored README describes Ramulator 2.1, `ramulator2/pyproject.toml` reports version `2.0.0`, and the root package reports `0.1.0`. The root description says “Ramulator 2.0” while the code/build uses the 2.1 branch and custom fork.

**Required resolution:** define the supported compatibility/version matrix, for example:

- PIMScope release version;
- Ramulator base/fork version;
- exact submodule commit;
- Python and C++ ABI compatibility.

Use the same names and versions in package metadata, README, paper, generated artifacts, and `--version` output.

---

## P1-5. Replace implicit `PYTHONPATH` requirements with a supported import mechanism

The root scripts manually insert paths for `ramulator2/python` and `ramulator2`, while `scripts/README.md` asks users to export `PYTHONPATH`. This is fragile in subprocesses, IDEs, notebooks, installed environments, and user scripts. It also makes it easy to import a different globally installed `ramulator` package.

**Required resolution:** use a single documented import/install mechanism. If path insertion remains necessary during development, assert the imported module’s file and backend commit at startup and provide a `pimscope doctor` command.

---

## P1-6. Make experiment collection fail closed — closed

`_run_tasks()` in `scripts/gen_figures.py` catches worker exceptions, prints `FAILED`, and continues. Assembly then writes JSON from whatever parts happen to exist and returns success. A failed or partial experiment can therefore look like a valid result set.

**Required resolution:** collect failures, return nonzero, and refuse assembly unless all expected parts are present and valid. Add checks for:

- expected row count;
- unique `(model, phase, mode, hardware config)` keys;
- `replay_status == PASS`;
- issued/completed request counts;
- schema/version compatibility;
- matching configuration fingerprints.

Add an explicit `--allow-partial` mode only if partial results are useful.

---

## P1-7. Make cache invalidation configuration-aware — closed for paper parts

The collection code reuses a part file based only on its filename. It does not hash or compare the generator version, backend commit, DRAM organization, timing preset, PIM parameters, model spec, prompt/past length, interleave settings, worker/runtime settings, or code version. Changing hardware or workload settings can silently reuse stale results.

**Required resolution:** store a canonical configuration and code fingerprint in every part and include it in the cache key. On reuse, validate the fingerprint. Add `--no-cache`/`--force` semantics with clear output and make the default output reproducible in a fresh directory.

---

## P1-8. Remove absolute paths and nondeterministic dates from result provenance

`source_cache` is written as `str(part)` and can become an absolute machine-specific path. The aggregate files use `date.today()`, so identical simulations produce different content on different days. There is no recorded root commit, submodule commit, compiler, Python version, CMake version, or full simulation configuration.

**Required resolution:** use repository-relative paths, an explicit run timestamp separate from a deterministic artifact hash, and a provenance block containing:

- root/submodule commit IDs;
- generator/backend version;
- complete hardware configuration;
- workload/model configuration;
- random seed(s);
- toolchain/runtime versions;
- command line.

---

## P1-9. Expose hardware configuration as a validated schema — initial public interface closed

The replay path hardcodes a single backend configuration in `scripts/lib/backend_replay.py`:

- `LPDDR5PIM`;
- `LPDDR5_8Gb_x16`;
- `LPDDR5_6400`;
- one rank/channel arrangement;
- `NoRefresh`;
- `FRFCFS`;
- `Open` row policy;
- `CacheLineInterleave`;
- `frontend_clock_ratio = 4`;
- `max_inflight_requests = 1` in the low-level replay default.

`runner.py` has a separate hardcoded configuration with `PassThroughAddrMapper`, `PassThroughChannelMapper`, and other defaults. The two paths are not one coherent configuration system.

**Required resolution:** define a versioned YAML/JSON/TOML hardware schema with typed validation and a CLI override mechanism. Include DRAM class, organization/timing preset or explicit timing values, channel/rank counts, address mapper, channel mapper, scheduler, refresh policy, row policy, controller, PIM resource parameters, and frontend clock ratios. Print the resolved config with every run.

**Implemented:** schema version 1 is provided by `scripts/lib/config.py`, with
JSON/YAML loading, strict unknown-field rejection, dotted-path errors, canonical
resolved manifests, SHA-256 fingerprints, and repeated `--set path=value`
overrides. `pimscope validate` resolves both the public schema and the native
LPDDR5PIM organization/timing configuration; `pimscope run` records the full
resolved manifest in each result. The first release intentionally supports one
controller/channel instance and rejects unsupported DRAM classes; arbitrary
multi-channel topology remains tracked by P1-23 rather than being implied.
The maintained fork also exposes generic LPDDR6, but that standard is not an
LPDDR6-PIM backend; adaptability is tracked separately by P1-27.

---

## P1-10. Remove hardcoded LPDDR5 address assumptions from concrete traces — closed for the supported topology

Both Python and C++ concrete trace code special-case `addr_vec_size == 6` and assume `[Channel, Rank, BankGroup, Bank, Row, Column]` with fixed bases/ranges:

- column modulo 1024;
- row modulo 32768;
- bank modulo 4;
- bank group modulo 4.

This does not adapt when users change organization presets, bank counts, row counts, column counts, ranks, channels, or hierarchy level order. The generic fallback uses base 4096 digits, which is also not a device-derived mapping.

**Required resolution:** obtain level sizes and the configured address mapper from the actual DRAM specification/configuration. Define one canonical byte-address-to-`addr_vec` mapping and test it against every supported organization, rank count, and channel count. Reject configurations where the trace mapping cannot represent the requested address range.

**Implemented for the supported topology:** `scripts/lib/addressing.py` and the
maintained Ramulator fork now share one organization-derived mixed-radix
contract containing hierarchy names/sizes, internal prefetch, transaction
bytes, and addressable capacity. Python lowering/validation and the C++ concrete
frontend use the resolved contract; the hardcoded `1024/32768/4/4` and generic
base-4096 mappings were removed from native replay. Host addresses are checked
at the first and final repeated address, and all concrete `addr_vec`
coordinates, interleaving bank ranges, row ranges, and column ranges fail closed
with hierarchy-level diagnostics.

Validated coverage includes `LPDDR5_8Gb_x16`, `LPDDR5_16Gb_x16`, transaction
boundaries, one-past-capacity rejection, repeated-address overflow/range checks,
and a two-rank organization override within one controller. Resolved CLI output
now records the address-layout mapping version, physical and address-level
sizes, prefetch, transaction bytes, and capacity. The tiny custom experiment remains numerically
unchanged at 5,981 cycles on both supported presets.

This closes the fixed-organization mapping defect for the current
one-controller/channel public runner. P1-23 remains open for multiple
controllers/channels and arbitrary channel-mapper semantics, and synthetic
`full_preload` uses the explicit `bounded_surrogate_v1` placement policy and
remains a diagnostic placement policy rather than a checkpoint layout model.

---

## P1-11. Make flat-bank decomposition and shared-block grouping hierarchy-aware

The canonical layout helper now separates controller hierarchy order from the
synthetic frontend's intentional interleave order, and the concrete host mapping
uses hierarchy order directly. Remaining shared-block grouping semantics still
need to be defined across multiple controllers/channels and non-LPDDR5
hierarchies.

The controller currently also groups the entire controller’s flat bank array, while the semantic concept is “banks per rank”; this needs explicit validation for multiple ranks/channels.

**Required resolution:** centralize hierarchy introspection and flat-bank mapping in one library/API. Define whether a shared PIM-block group is scoped per rank, per channel, per pseudo-channel, or globally. Test mappings with hand-authored expected address vectors and verify that every flat bank maps exactly once. Coordinate the public rename with P1-22b; legacy `*_mpu_*` names must not remain the canonical API.

---

## P1-12. Validate all user-provided hardware values, not only some PIM resource values

`LPDDR5PIM` validates several datatype/resource values, but important fields are weakly validated or are only checked later in C++:

- `pim_enabled` and `pim_mode` are stored but do not visibly gate command availability in the Python DRAM definition;
- `pim_blocks_per_bank` is accepted and then silently normalized to at least one in C++;
- `pim_banks_per_mpu` is not validated against the actual organization until controller initialization;
- datatype names not found in metadata fall back to INT8 metadata unless datatype behavior is enabled;
- `pim_ops_per_mac`/`pim_ops_per_block_issue` are floats even though their meaning may be integral;
- no explicit relationship checks ensure SIMD width is divisible by datatype width or that lanes match the supplied width;
- no clear validation exists for all timing override combinations.

**Required resolution:** fail at config construction with field-specific errors. Make unknown datatype names errors by default. Define explicit override precedence and consistency rules, and serialize a resolved hardware/resource block into stats and output files.

---

## P1-13. Define and enforce the meaning of datatype behavior

The code supports metadata for `int8`, `fp16`, `int16`, and `bf16`, but only `int8` and `fp16` are in `PIM_DATATYPE_RESOURCES`. `pim_datatype_behavior_enabled` controls whether some timing/movement/slot fields are used, while the generator’s `_lanes()` and request-count logic have their own datatype assumptions.

This makes selecting `bf16` or `int16` ambiguous: it may be accepted, use fallback timing, use metadata energy, and generate workload counts under a different rule.

**Required resolution:** define a single datatype/resource registry shared by device model, workload generator, lowering, energy model, and result schema. Document whether datatype changes represent real supported hardware or only a what-if sweep. Add end-to-end tests for each advertised datatype.

---

## P1-14. Clarify timing semantics and validate the two-level PIM timing model

The Python DRAM model adds `nPIM_MAC_LAT` and `nPIM_MAC_II`, but the controller separately schedules launches and completion residency. The issue interval is not obviously applied uniformly to all execution models, and all-bank latency is calculated as `completion_latency * pim_banks_per_mpu`. The paper itself calls several values literature-anchored abstractions rather than silicon ground truth.

**Required resolution:** publish a formal timing contract with diagrams and equations for:

- command issue eligibility;
- row activation prerequisites;
- issue interval;
- per-bank occupancy;
- shared-PIM-block occupancy;
- all-bank operation latency;
- completion/callback time;
- host/PIM interaction;
- refresh interaction.

Add device/controller tests that independently sweep issue interval, pipeline latency, movement latency, writeback, slot cost, bank sharing, and block count. Report which parameters affect command issue versus request completion.

---

## P1-14a. Reconcile the published cold-start-overhead wording with generated data

A clean regeneration at parent `124fee8` and Ramulator `015ae2b` exactly
reproduced the prior cached cycles and Fig. 4 bars, but the cycle ratios do not
support the paper text's stated "18–38% in decode versus 2–3% in prefill" when
overhead is defined as `(cold - steady) / steady`. The regenerated ranges are:

- decode: 67.1% to 299.2% additional cycles over steady state;
- prefill: 19.0% to 27.0% additional cycles over steady state.

The paper figure itself displays the same regenerated steady/cold cycle values,
so this is a paper interpretation/wording inconsistency rather than a
regeneration failure. Before release, either correct the paper wording and
related abstract/conclusion claims, or document and reproduce the exact
alternative denominator/metric that yields 18–38% and 2–3%. Add a machine
check that derives every stated range directly from aggregate JSON.

---

## P1-15. Decide whether refresh should be modeled in the paper path

The figure replay hardcodes `NoRefresh()`. The paper’s experimental table describes LPDDR5 timing and compares cycles, but the production replay does not exercise refresh behavior. `runner.py` also defaults to `NoRefresh`.

**Required resolution:** either make refresh a configurable experiment parameter and include it in results, or prominently state that all artifact numbers are no-refresh diagnostic numbers. Add a comparison with `AllBank`/`PerBank` refresh if the backend claims general LPDDR5-PIM evaluation.

---

## P1-16. Make command accounting complete and self-consistent

The root runner’s command accounting and trace/controller statistics must stay
consistent. A clean regeneration exposed one concrete schema issue: aggregate
prefill output reported `pim_bcast_issued: 0` even though concrete command
counts contained `PIM_BCAST`. The artifact helper now derives this field from
the validated concrete opcode count, but a regression test is still required.

**Required resolution:** derive command counts from one authoritative issued-command stream, include all standard and PIM commands, and distinguish:

- trace records;
- expanded frontend requests;
- issued DRAM commands;
- completed requests;
- controller synthetic completion events.

Add invariants that these numbers reconcile where they should and explicitly document where one semantic request expands into multiple commands.

---

## P1-17. Fix observability output lifetime and make it configurable

`runner.run_single()` creates a `TemporaryDirectory` inside the simulation and stores command trace paths in the returned stats. Those files are deleted before the function returns, so `evidence.modelled.command_traces[].path` points to nonexistent files. The same function accepts `observability_dir` but does not make the output persistent unless the caller inspects files during the context.

**Required resolution:** add explicit observability modes:

- disabled;
- persistent output directory;
- temporary output with no paths returned;
- bounded in-memory preview.

Return paths only for files that remain available, and include a manifest of plugin outputs.

---

## P1-18. Validate trace files before native replay, including all address bounds

The Python validator checks nonnegative vector entries and some interleaving metadata but does not validate every `addr_vec` coordinate against the selected device organization. The C++ reader similarly checks size/nonnegative values but not per-level upper bounds before native indexing. This can turn a customized trace/hardware combination into an assertion/crash or invalid simulation rather than a useful validation error.

**Required resolution:** validate every level against resolved organization sizes before enqueueing a request. Validate bank positions/counts, row/column levels, rank/channel coordinates, repeated address ranges, and interleave bank IDs. Add negative and out-of-range tests.

---

## P1-19. Add backpressure, inflight, and termination validation

`LPDDR5PIMConcreteTrace` accepts `max_inflight_requests` but does not explicitly reject nonpositive values in the shown initialization checks. It also treats only bank-rotating `PIM_MAC` records as parallelizable and serializes other record classes. This is a policy choice that must be visible to users; otherwise `max_inflight_requests` appears to mean global concurrency when it does not.

Large model traces are protected by configurable record/expanded-record ceilings, but the root replay module globally sets `RAMULATOR_MAX_EXPANDED_RECORDS` to one trillion, far above the library default, with no memory/time budget guidance.

**Required resolution:** validate all limits, document which records can overlap, expose the effective concurrency in stats, provide resource estimates before execution, and add timeout/cancellation handling for enormous traces.

---

## P1-20. Make workload configuration data-driven and user-extensible — dense model interface closed

The model registry and experiment lists are embedded in `generate_full_transformer.py` and `gen_figures.py`. Users cannot add a model by supplying a manifest file; they must edit a 4,000+ line Python module and a separate experiment script. The accepted model key aliases are inconsistent with the lists used by the artifact script.

The generator currently supports a bounded set of dense decoder models and Mixtral decode, with prefill explicitly excluding Mixtral. The paper itself lists future work including mixed-phase traces and additional model families.

**Required resolution:** define a documented model manifest schema containing dimensions, attention type, KV heads, FFN variant, activation, datatype/quantization, layer count, sequence lengths, routing policy, citations, and claim boundaries. Add `--model-config path`/`--workload-config path`, schema validation, and a minimal custom-model example. Keep built-in models as data files rather than code constants.

**Implemented for dense models:** `workload.model` accepts either a built-in
registry key or a validated custom dense-model object with layer count, hidden
and FFN dimensions, query/KV heads, head dimension, FFN variant, activation,
datatype, and citation metadata. Decode/prefill length, schedule, synthetic
weight residency, lowering mode, interleave depth, and inflight count are
manifest fields. The checked-in `configs/example_custom.json` and
`pimscope validate/run` commands provide a no-source-edit quick start. Moving
all built-in registry data out of the Ramulator Python module, and a general
custom MoE/routing schema, remain future extensions rather than blockers for
the supported dense interface.

---

## P1-21. Separate real model dimensions from synthetic workload assumptions

The aggregate output labels rows with `dimension_scope: "real"`, but the generator is explicitly a structured workload surrogate and the paper states it is not a full software/runtime replay. Some model dimensions are manually encoded, and the workload only models memory-side command streams. The result schema should not allow “real” to be read as “real runtime trace” or “silicon-faithful.”

**Required resolution:** use precise fields such as:

- `architecture_dimensions: published`;
- `weights: synthetic/not materialized`;
- `runtime_trace: no`;
- `numerical_execution: no`;
- `host_operator_model: partial`;
- `silicon_calibration: no`.

Make these boundaries appear in CLI output, JSON, README, and figures.

---

## P1-22. Make cold-start/materialization semantics explicit and consistent

The `materialize_weights` flag emits synthetic host writes for weight residency,
and the address range is generated from a formula rather than a real layout or
model checkpoint. The concrete lowering now makes the placement policy
explicit: literal host streams use strict physical byte addresses, while the
public generated surrogate path uses deterministic `bounded_surrogate_v1`
placement within the resolved capacity. This prevents native out-of-range
addresses without presenting the result as checkpoint placement. The prefill
and decode paths still use different residency assumptions, and complete
policy/provenance coverage remains tracked here.

**Required resolution:** document cold-start as a synthetic traffic policy. Give users selectable policies such as resident, full preload, partial preload, streamed layers, or custom address map. Record the policy and generated byte volume in every result. Add tests that verify exact writes and that steady-state truly omits them.

---

## P1-22a. Move reusable simulator APIs out of the parent `scripts/` package

**Status:** closed. Implemented and published in Ramulator commit `7aa94e3`
and parent commit `28cf105`; parent clean-clone CI run `31240290858` completed
successfully in 2m48s. The simulator fork now owns `ramulator.pimscope` for
manifest validation,
component construction, replay, experiment execution, and a standalone
`ramulator-pimscope` command. The parent `pimscope` entry point is a thin
compatibility adapter, `scripts/gen_figures.py` imports the simulator API, and
legacy `scripts.lib.*` modules are warning compatibility shims. Parent script
implementation has fallen from approximately 2,000 lines to about 150 lines of
CLI/shim code plus the paper-only artifact generator. Standalone fork tests and
an example manifest/script are included.

Acceptance evidence includes 25 parent tests, 290 project-owned Ramulator tests,
standalone and parent CLI replay at 5,981 cycles, a local recursive clean-clone
package/API check, 88 regenerated paper simulation parts with identical rows,
and the unchanged figure SHA-256
`5e02da61018683b255eb025afa5666a215cda699f9de8bfeca5021c4bd4b5eef`.
Historical evidence and the acceptance criteria remain below. The only planned
follow-up is retiring the one-release compatibility shims after downstream
users have migrated; simulator/API ownership itself is no longer a release
blocker.

The parent previously contained approximately 2,000 lines under `scripts/`.
Only `scripts/gen_figures.py` was clearly paper-artifact orchestration. Reusable
simulator and researcher-facing functionality was also implemented there:

- `scripts/lib/config.py` — manifest schema, defaults, validation, and
  fingerprinting;
- `scripts/lib/backend_replay.py` — DRAM/controller/memory-system factories,
  trace replay, result extraction, and transformer experiment execution;
- `scripts/lib/runner.py` — simulator frontend construction and observability;
- `scripts/cli.py` — model construction, semantic generation, lowering, replay,
  and result assembly;
- `scripts/lib/addressing.py` — a parent compatibility import for a simulator
  API that already lives in Ramulator.

This makes the public architecture look like a collection of paper scripts
rather than a simulator with a stable API. It also duplicates responsibility:
Ramulator owns the DRAM model, frontend, lowering, and workload surrogate, while
the parent script package owns the factory that makes those pieces usable. A
community user cannot tell which layer is the supported simulator interface or
where a new hardware/controller/workload feature belongs.

**Required resolution:** define a strict ownership boundary and migrate in
stages:

1. Keep only paper experiment matrices, aggregate assembly, plotting, and
   release verification in the parent artifact layer.
2. Move generic layout/config factories, component construction, concrete
   replay, result extraction, and experiment execution into a documented
   `ramulator.pimscope` (or equivalently named) package in the maintained
   Ramulator fork.
3. Decide whether the versioned experiment-manifest schema belongs in that
   simulator package or in a small first-class `pimscope` package, but do not
   leave it under a directory named `scripts`.
4. Reduce the parent CLI to a thin installed entry point that loads a manifest,
   calls the simulator API, and writes a result. Avoid private imports such as
   `_extract_dram_layout`, `_make_mem`, and `_make_addr_mapper` across repository
   boundaries.
5. Give public APIs non-underscored names, typed return objects, focused unit
   tests in their owning repository, and migration shims for one release.
6. Document the extension path: DRAM/device behavior, frontends, replay, and
   workload lowering belong in Ramulator; paper-specific workload lists,
   figures, and claim checks belong in PIMScope.

**Acceptance criteria:** ordinary simulation/customization works by importing a
documented simulator package or invoking its CLI without importing
`scripts.lib.*`; `scripts/` contains only thin artifact/release entry points;
clean-clone CI tests the new public API directly; and no simulator feature must
be added in two repositories merely to become usable.

This migration should precede broad community API stabilization, but it must
preserve the validated address-mapping and paper-result baseline. Do not combine
it with the terminology/schema rename in one unreviewable change.

---

## P1-22b. Replace obsolete “MPU” terminology with paper-aligned shared-block terminology

The current paper no longer uses “MPU” as the name of the modeled LPDDR-PIM
resource. It describes a dedicated compute unit/PIM block per bank for `b=1`
and one PIM block shared across a two-bank group for `b=2`, with “shared-block
serialization” as the relevant contention mechanism. The PDF’s remaining
“MPU” occurrences refer to the separate prior work **MPU-Sim**, not PIMScope’s
resource name.

The released code and documentation nevertheless expose “MPU” throughout the
public interface. The initial audit on parent `28cf105`/Ramulator `7aa94e3` found 11 exact
public-document/configuration/script matches outside this issue document and 17
implementation/test matches in the fork. Those public and implementation
surfaces have now been canonicalized in the working tree to shared-block names:
configuration fields, execution-model values, statistics, workload metadata,
frontend validation, controller identifiers/comments, tests, and documentation.
A final mechanical audit now permits only the deliberate negative-config test
that proves the legacy `pim_banks_per_mpu` spelling is rejected. The renamed
fork builds successfully; its PIM configuration suite passes 10 tests and its
controller-scheduling suite passes 32 tests, while the parent configuration and
artifact tests pass 10 tests. A public CLI validation and short replay smoke
also pass. A one-release compatibility layer is now implemented in
`ramulator.pimscope.compat`: legacy config/result names normalize to canonical
shared-block names, emit deprecation warnings, and fail closed on conflicts.
The migration is still uncommitted/unpublished and needs release-schema and
backward-compatibility review before this issue can be closed.

The affected names include:

- `pim_banks_per_mpu`;
- `shared_mpu_serial`;
- `pim_mpu_group_stalls` and `num_mpu_group_busy_blocked_cycles`;
- `pim_mpu_group_count` and `effective_mpu_groups`;
- `mpu_grouping_policy` trace metadata;
- README/configuration wording such as “shared-MPU.”

This terminology mismatch is confusing for readers moving between the paper,
configuration files, JSON results, and simulator statistics. It also makes an
internal implementation label look like an architectural claim that the paper
does not make.

**Required resolution:** define one paper-aligned canonical vocabulary, likely
“PIM block,” “shared block,” “banks per PIM block,” and “shared-block
serialization.” Rename public manifest fields, execution-model values, result
fields, trace metadata, statistics, tests, and documentation consistently.
Provide a time-bounded compatibility/migration layer for old config and result
names, with deprecation warnings and a schema-version decision rather than a
silent breaking rename. Preserve **MPU-Sim** unchanged when referring to the
cited simulator. Mechanically verify that public user-facing text uses “MPU”
only for MPU-Sim or explicitly documented legacy aliases.

This terminology migration should be coordinated with P1-11’s grouping/address
work so the renamed shared-block scope is defined precisely per rank/channel,
and with P1-25 so old/new result fields cannot be mixed silently. The underlying
shared-resource simulation semantics are already tested; the remaining defect is
release integration and compatibility policy, not the paper's cycle data.

---

## P1-23. Handle multiple channels/ranks and channel mapping as first-class features

The paper setup is one channel/rank, and the public runner still builds one
controller/channel. The hierarchy-aware host mapper now derives rank and all
other address-level bounds from the resolved one-controller organization, but
it does not by itself implement system-level channel placement or traffic
across multiple controllers. `generate_and_replay()` uses one controller and
`CacheLineInterleave`, while the user request explicitly asks for broader
hardware customization.

**Required resolution:** expose channel/rank counts and mapping policies in the hardware schema. Generate addresses that exercise all configured channels/ranks, define PIM block scope across those domains, and test single- and multi-channel configurations. If multi-channel is out of scope, reject non-single-channel configurations early instead of silently pinning traffic to channel/rank zero.

**Current release decision:** the initial public manifest records
`hardware.topology.controllers` and `hardware.topology.channels`, but only
accepts `1` for each. Unsupported values fail before backend construction or
trace generation instead of being silently pinned to channel/rank zero.
Multi-channel studies remain unadvertised; multi-rank organization overrides
within one controller remain separately validated, while system-level topology,
mapping, and PIM grouping remain open until tested end-to-end.

---

## P1-24. Add explicit seed/configuration controls

The public manifest now accepts `workload.seed`, validates it as a non-negative
integer, and records it in both result provenance and workload summary. The
legacy host smoke runner also accepts an explicit seed and records it in
observability evidence. The current concrete semantic generators are
structurally deterministic; aggregate rows remain assembled in declared
workload order even when workers complete out of order.

**Remaining resolution:** propagate a seed to every randomized frontend/API,
record all ordering/concurrency controls, and add deterministic replay fixtures.
This issue remains open until those broader controls are covered.

---

## P1-25. Make output schemas versioned and validated

`prefill_cycles.json` and `pim_sharing_comparison.json` have `schema_version: 1`, but `decode_cycles.json` does not. There is no shared schema module, JSON Schema, or validator for aggregate rows. Fields are added ad hoc and can be absent or inconsistent (`pim_bcast_issued`, model keys, provenance, caveats, source paths).

**Required resolution:** define versioned schemas for manifests, semantic traces, concrete traces, simulation results, and aggregate artifacts. Validate both before writing and when rendering. Add migration/version compatibility rules.

**Progress:** the simulator fork now provides `ramulator.pimscope.schema` with
versioned result validation (`pimscope-result-v1`) and standalone concrete JSONL
trace validation for `lpddr5-pim-opcode-v0.2`. The public CLI exposes
`validate-result`, `validate-aggregate`, and `validate-trace`; result generation
includes a schema name, terminology compatibility is normalized before
validation, and aggregate writers/renderers validate the three paper aggregate
schemas. This issue remains open for broader row-level schema coverage and
migration fixtures.

---

## P1-26. Make the public scripts discoverable and callable without source-layout knowledge — core CLI closed

The documented commands invoke `scripts/gen_figures.py` directly and rely on `scripts/lib` being inserted into `sys.path`. There is no `__init__.py` in `scripts/lib`, no installed console script, no `--help` example for custom hardware/workloads, and no quick smoke command that produces a small result in seconds.

**Required resolution:** package the tooling or provide a root CLI (`pimscope reproduce`, `pimscope simulate`, `pimscope trace`, `pimscope validate`, `pimscope doctor`). Add a tiny example trace and a fast end-to-end tutorial before the full paper reproduction.

**Implemented:** the root package now installs `pimscope validate`,
`pimscope run`, and `pimscope doctor` alongside `pimscope-artifacts`. The
checked-in OPT-125M decode manifest is a short end-to-end custom experiment,
and CLI overrides support hardware/workload sweeps without source-layout
knowledge. `doctor --config <manifest>` checks the imported package, native
extension, LPDDR5-PIM component, and resolved address layout. The standalone
trace validator remains available as `validate-trace`.

---

## P1-27. Make the PIMScope backend adaptable to LPDDR6 without reusing LPDDR5 semantics

The maintained Ramulator fork already contains a generic `LPDDR6` DRAM
standard, including LPDDR6-specific organization and timing presets. PIMScope
now also has an explicitly named experimental `LPDDR6PIM` path rather than
silently substituting generic LPDDR6 behind the LPDDR5-PIM controller. The
paper path remains LPDDR5-PIM-specific.

LPDDR6 changes important contracts that cannot safely be handled by merely
allowing `hardware.dram_class: LPDDR6` or substituting an LPDDR6 DRAM object
behind the LPDDR5-PIM controller. The existing LPDDR6 model has a different
command/request vocabulary (`CAS`, `RD_S`/`RD_L`, and corresponding writes),
different command-cycle and burst-length rules, a 12-DQ organization with
LPDDR6 transaction/sub-channel considerations, different timing parameters and
refresh derivations, and potentially different power-accounting inputs. PIM
operations, shared-block scope, all-bank behavior, and completion semantics
must be defined for that standard rather than inherited accidentally from
LPDDR5.

**Required resolution:** introduce an explicit standard/backend capability
layer. Choose and document whether this is a reusable standard-independent PIM
controller/frontend with per-standard command adapters, or an explicitly named
`LPDDR6PIM` DRAM/controller/frontend implementation. In either design:

- require `LPDDR6PIM` explicitly for LPDDR6 PIM experiments; generic `LPDDR6`
  is not accepted as a PIM backend and the implementation must never silently
  fall back to LPDDR5 command IDs or timing fields;
- expose standard, PIM backend variant, organization, timing, transaction-size,
  and sub-channel assumptions in the manifest and result provenance;
- define LPDDR6 PIM command/request mappings, launch versus completion timing,
  shared-block grouping, all-bank serialization, refresh interaction, datatype
  resources, and power/energy units independently where LPDDR5 semantics do not
  apply;
- make hierarchy/address mapping derive from the resolved LPDDR6 organization,
  including rank, bank-group, bank, row, column, channel, and any sub-channel
  interpretation; validate capacity and transaction boundaries;
- use a distinct trace schema version for LPDDR6-specific opcodes, or prove a
  common schema contract with cross-standard conformance tests; do not reuse
  `lpddr5-pim-opcode-v0.2` for incompatible command semantics;
- add native and Python tests for LPDDR6 construction, presets, host read/write
  traffic, concrete trace validation, PIM issue/completion, shared-block
  serialization, refresh, energy accounting, invalid command/address bounds,
  and one- versus two-rank configurations within the supported topology;
- keep paper artifact reproduction explicitly pinned to LPDDR5-PIM until an
  independently validated LPDDR6 artifact configuration exists.

**Progress:** `LPDDR6PIM` now exists as an explicit experimental backend. The
maintained fork has a generated LPDDR6PIM DRAM specification, a shared LPDDR
PIM controller implementation registered under `LPDDR6PIM`, an LPDDR6-aware
CAS/short-long access timing path, an `LPDDR6PIMConcreteTrace` registration,
and a distinct `lpddr6-pim-opcode-v0.1` header. A small custom LPDDR6PIM
manifest replays successfully with hierarchy-derived 2 GiB capacity and
records `dram_class` in result/layout provenance.

**Additional progress:** native LPDDR6PIM conformance now covers LPDDR6
CAS/`RD_S`/`WR_S` vocabulary, PIM issue and delayed completion, shared-block
serialization, all-bank sequencing, datatype resources, rank-scoped refresh,
and rejection of LPDDR5 command names. The AllBank refresh manager now maps
`LPDDR6PIM` explicitly to Rank scope. These tests require and pass the optional
native `_ramulator_test` binding built with Clang 14.

**Trace-conformance progress:** Python and native C++ now consume shared
LPDDR6PIM fixtures. The fixtures cover the explicit header/backend/schema
contract, PIM_MAC replay, host byte-address decomposition, HAB → PIM_BCAST →
HAB_PIM → PIM_MAC_AB sequencing, malformed headers, LPDDR5 schema/opcode
rejection, and out-of-range address rejection. This also exposed and fixed a
native frontend initialization bug that duplicated every loaded record and
request during replay.

**Additional power-boundary progress:** LPDDR6PIM results now contain a
validated `power_accounting` block. It explicitly reports that standard
LPDDR6 background/command energy is unavailable, identifies PIM event
coefficients as metadata-only inputs, uses pJ units, and leaves total standard
and PIM-event energy null rather than emitting a misleading zero. Result-schema
validation fails if LPDDR6PIM claims standard power availability.

**Paper-energy correction:** LPDDR5PIM now defaults to the paper's two-layer
`E = E_LPDDR + E_PIM` contract using the preserved `PAPER_LPDDR5_POWER` IDD
profile and reports the two terms plus their sum. The event coefficients now
match camera-ready Table III exactly: 0.35 pJ/MAC for INT8, 0.69 pJ/MAC for
FP16, 2.68 pJ per 256-bit cell-to-PIM transfer, 3.17 pJ per 256-bit VRF access,
and 0.40 pJ per 32-bit SRF access. This fixes the prior erroneous 686.08 pJ
movement default, which had incorrectly interpreted 2.68 pJ as a per-bit value.
Native/public assertions cover the coefficients and the energy-sum invariant.

**Remaining resolution:** validate the standard-specific PIM command/resource
contract against an LPDDR6-PIM source model, implement and test LPDDR6 PIM-event
accumulation if PIM-only totals are to be reported, expand fixtures across rank and sub-channel combinations, and complete
independent hierarchy/topology validation. Keep LPDDR6PIM experimental and
exclude it from paper artifacts until the remaining P1-27 gates pass.

---

# P2 — important quality and maintenance work

## P2-1. Add formatting, linting, and static checks to the root project

The nested project has Ruff configuration, but the root has no lint configuration or CI invocation. The current scripts use broad dictionaries and dynamic imports, making type and schema errors easy to miss.

**Resolution:** add root Ruff/format configuration, optional mypy/pyright, pre-commit hooks, and CI checks. Keep generated/vendor code excluded deliberately rather than accidentally.

## P2-2. Reduce duplication between `runner.py`, `backend_replay.py`, and native configuration

There are multiple copies of hardware defaults, request ID discovery, layout extraction, controller creation, and timing assumptions. This guarantees drift when a new hardware option is added.

**Resolution:** create one reusable configuration/backend factory and make all entry points use it.

## P2-3. Replace magic constants with named, resolved hardware values

Examples include `DENSE_PIM_BANK_SEQUENCE = list(range(16))`, fixed `stream_cols=8`, fixed row/column bases, observed-bank count `kObservedPimBanks = 4`, and fixed frontend ceilings. These may be valid for the paper’s one device but are dangerous defaults for community customization.

**Resolution:** derive values from the resolved organization or require them in the config, validate them, and mark any diagnostic truncation explicitly.

## P2-4. Fix the limited per-bank observability counters

The controller records per-bank launch/peak statistics only for `kObservedPimBanks = 4`, even though the default device has 16 bank units. This can mislead users into believing the per-bank statistics cover the whole device.

**Resolution:** dynamically size counters or expose a documented sampling/aggregation mode.

## P2-5. Clarify and test the experimental execution model

`subbank_overlap_experimental` is accepted by the configuration, but the public paper/reproduction path uses `shared_mpu_serial`, and the controller behavior/validation boundary is not clearly documented. Users need to know which model is validated and which is experimental.

**Resolution:** label experimental modes in stats/results, add dedicated tests, and document expected invariants.

## P2-6. Reconcile direct-command replay with request-level replay

Mode commands are sent as direct `Request::Cmd`, while PIM operations use supported request IDs. This is an internal implementation detail that affects scheduling, callbacks, counts, and validation. The public trace schema should state whether an opcode is a DRAM command, a synthetic request, or a semantic operation.

**Resolution:** expose a clear opcode/request/command mapping table and test callback/retirement semantics for every opcode.

## P2-7. Make trace parsing streaming and resource-bounded

Python helper functions often materialize complete semantic/concrete record lists and then write another full JSONL copy. This is workable for the paper’s compact records but can become a major memory cost for custom workloads.

**Resolution:** support streaming validation/lowering/replay, report record and expanded-request estimates first, and document disk/time/memory requirements.

## P2-8. Add trace format documentation and standalone validators

The concrete format is implemented in Python and C++ with duplicated validation. A user needs a schema, examples for every opcode sequence, address mapping rules, repeat semantics, and a command such as `pimscope validate-trace` that does not require compiling/running a simulation.

**Resolution:** publish JSON Schema or equivalent, canonical examples, and cross-language conformance tests.

## P2-9. Improve errors and logging

Errors from multiprocessing are printed without traceback/context, and native errors can be difficult to associate with the semantic record because only compact provenance is retained. Logs do not consistently print the resolved hardware/workload configuration.

**Resolution:** use structured logging, include model/phase/part/record IDs, preserve worker tracebacks, and add verbosity controls.

## P2-10. Add performance safeguards and progress reporting

The paper includes traces with billions of PIM operations. Full collection can take substantial time and disk space, but there is no estimated runtime, per-task timeout, progress rate, checkpoint manifest, or resume integrity check.

**Resolution:** estimate expanded requests and output size before running, support bounded workers, timeouts, resumable jobs, and a summary report.

## P2-11. Make plots robust to incomplete/invalid rows

The renderer silently substitutes zero for missing rows and uses log scale. A missing result therefore becomes a zero-height bar rather than a hard error, and the plot can still be saved.

**Resolution:** validate completeness before rendering and fail with a list of missing/invalid rows. If partial plots are desired, mark missing points explicitly rather than substituting zero.

## P2-12. Add compatibility tests for Python 3.11 and 3.12

The root `.python-version` says 3.11, while the active environment is Python 3.12 and the README says Python 3.11 or newer. The package/build path should explicitly support and test the versions claimed.

**Resolution:** define the supported matrix, test both versions in CI, and ensure the generated nanobind extension and package metadata use the same interpreter.

## P2-13. Remove or repurpose the placeholder `main.py`

The root entry point does not run PIMScope, reproduce artifacts, or validate setup. It creates a misleading impression that the package has an application entry point.

**Resolution:** replace it with a useful CLI or remove it and document the real entry point.

## P2-14. Add contribution and issue-reporting templates

A community release needs a bug-report template that asks for OS, compiler, CMake, Python, root/submodule commits, hardware config, workload manifest, trace schema, command line, and logs. Add feature/design documentation for new hardware and workload plugins.

## P2-15. Add release artifacts and a clean-checkout smoke test

Publish a tagged release with a tested source archive/container and a short smoke result. Verify that the release can be cloned/downloaded by a user with no local caches and that no ignored build products are required.

---

# Modeling/documentation limitations that must be explicit, not hidden

These are not necessarily blockers if the project clearly states them, but they affect how community users can interpret results:

1. **The workload is a structured surrogate, not application/runtime replay.** The paper states that host-side softmax, nonlinearities, MoE top-k/dispatch/combine, and other operations are outside the backend model.
2. **PIM_BCAST is explicitly a bounded abstraction.** The code’s provenance says it is not a silicon-faithful source/timing model. This caveat must appear in user-facing output, not only in internal trace provenance.
3. **No absolute silicon timing/energy accuracy is established.** Literature-derived coefficients require calibration and sensitivity analysis.
4. **The default artifact path uses `NoRefresh()`.** Results should not be presented as complete LPDDR5 system behavior without saying so.
5. **The model set and phase coverage are incomplete.** Mixtral prefill is excluded, mixed prefill/decode and serving behavior are not modeled, and batch size is effectively one in the semantic generator.
6. **Physical placement/data movement is synthetic.** Weight materialization and address ranges are generated formulas, not checkpoint-derived placement maps.
7. **The default hardware is one narrow organization.** The supported one-controller mapping now derives bounds from the selected LPDDR5 organization, but claims about multi-controller/channel or arbitrary hierarchy customization remain outside the validated scope.
8. **LPDDR6 is a separate adaptation target.** Generic LPDDR6 DRAM timing support in Ramulator is not equivalent to LPDDR6-PIM support; PIM commands, controller scheduling, trace opcodes, sub-channel/transaction mapping, refresh, and energy semantics require an explicit backend and independent validation.
9. **Energy attribution needs a units/coverage review.** The code combines inherited JEDEC power terms with incremental PIM event terms and literature coefficients; each term should document units, scope, overlap avoidance, and whether it is per command, per MAC, per lane, or per 256-bit transfer.
9. **The paper’s “exact command matching” validation is a useful floor but not sufficient.** Tests must also establish timing legality, resource serialization, address mapping, request completion, and energy-counter invariants.

---

# Suggested implementation order

1. **Release hygiene:** fix `.gitmodules`, root license/NOTICE/citation files, `.gitignore`, version metadata, paper placeholders, and README contradictions.
2. **Build gate:** fix the missing test target, provide one clean build path, repair Docker or remove it, and verify a fresh HTTPS clone.
3. **Validation gate:** restore/add tests and CI for build, smoke, trace validation, PIM timing, shared-block serialization, and address mapping.
4. **Configuration gate:** introduce one validated hardware/workload schema and eliminate duplicated hardcoded defaults.
5. **Reproducibility gate:** add configuration fingerprints, relative paths, deterministic assembly, strict failure handling, and schema validation.
6. **Customization gate:** support user-provided model manifests, dynamic device hierarchy/address mapping, multiple ranks/channels or explicit rejection, and datatype/resource validation.
7. **Usability gate:** add a CLI, doctor command, small tutorial, trace validator, examples, progress/resume support, and contribution guidance.
8. **Modeling gate:** document/validate refresh, energy, timing, data movement, and surrogate claim boundaries with sensitivity experiments.

---

# Definition of done for an open-source release

A release should not be announced until all of the following can be demonstrated from a clean machine/container:

- `git clone` plus `git submodule update --init --recursive` succeeds without SSH credentials;
- the documented build succeeds with no pre-existing build directory;
- `import ramulator` and the public PIMScope CLI resolve to the intended checked-out backend;
- a small LPDDR5-PIM example completes and produces validated stats;
- if LPDDR6-PIM is advertised, a small LPDDR6 standard smoke and an explicit
  LPDDR6-PIM trace/backend replay complete with standard-specific validated
  provenance; otherwise documentation and validation reject LPDDR6-PIM clearly;
- a custom hardware config and a custom model/workload manifest complete without editing library source;
- invalid organization, timing, datatype, address, and trace settings fail with actionable errors;
- the test suite passes in CI on every supported Python/compiler combination;
- paper artifact collection fails on missing/failed parts and records complete provenance;
- repeated runs with the same config produce the same numerical artifacts and stable normalized JSON;
- results do not contain local absolute paths or untracked build products;
- the release includes license, third-party notices, citations, contribution guidance, and accurate scope/limitations.

---

## Current working-tree/commit note

The tracked parent baseline is `8ddf83d` with Ramulator submodule `015ae2b`.
The hierarchy-aware address-mapping revision is currently an uncommitted
parent/submodule change, backed up at
`/home/tinglin/wksp/PIMScope-backups/address-mapping-revision-20260807T082536Z`.
`AGENTS.md` and this issue document remain intentionally untracked. Generated
`results/`, local environments, and build outputs were not committed or
deleted.
