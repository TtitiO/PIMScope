# Code quality and release audit

Last reviewed: 2026-08-12

This document records issues found by reviewing the parent artifact package,
the researcher-facing `ramulator.pimscope` package, tests, documentation, and
`results/oracle`. It distinguishes completed safeguards from open work. A
release must not describe an open item as validated.

## Release status

**Release candidate validated.** Configuration, isolated parallel artifact
collection, validation, a small public CLI, an ABI-matched native simulator,
exact oracle cycle reproduction, and the published Ramulator fork are in place.

## Verification performed

- All 60 PIMScope-maintained tests pass, including native-backed CLI coverage.
- `.venv` is CPython 3.11 and loads the matching
  `_ramulator.cpython-311-x86_64-linux-gnu.so` extension.
- A clean GCC 13/CMake 4.4 build found Python 3.11 `Development.Module` and
  completed both runtime and optional test bindings. Artifact collection lazily
  imports plotting, so a fresh native replay loads without `LD_PRELOAD` despite
  the host Anaconda C++ runtime.
- The shell's vendor CMake 3.3.2 remains unsuitable; documented commands select
  the venv CMake explicitly, and `pimscope doctor` rejects the stale PATH tool.
- The 88-part reproduction in `results/reproduction` validates under the current
  schemas and matches the legacy oracle. A fresh post-change OPT-125M sample of
  decode/prefill steady/cold and PIM-sharing k1/k2 also passed replay and matched
  all six oracle cycle values exactly.

Re-run the commands in [Release gate](#release-gate) after a clean build.

## Issue register

| ID | Priority | Status | Area | Issue and required action |
|---|---|---|---|---|
| CQ-001 | P0 | Fixed | Oracle | The separate 88-part `results/reproduction` output validates with current schemas and matches all 73 aggregate identities and exact cycle fields against the immutable oracle. After the latest changes, six fresh representative OPT-125M replays—decode/prefill steady and cold plus PIM-sharing k1/k2—each passed and matched oracle cycles exactly. No oracle file, public command, or simulator API was changed for these private checks. |
| CQ-002 | P0 | Fixed | Build | An ABI-matched GCC 13/CPython 3.11 clean build completed after selecting the venv CMake 4.4 explicitly; CMake found Python `Development.Module`, the CPython 3.11 extension loads, and doctor passes in the documented environment. Doctor still rejects the vendor CMake 3.3.2 selected by the unmodified shell PATH, preventing accidental use. |
| CQ-003 | P0 | Fixed | Regression | All 60 PIMScope-maintained parent tests pass with the ABI-matched GCC 13/CPython 3.11 build, and all 88 paper parts reproduce oracle cycles exactly. Upstream Ramulator tests are maintained and gated separately in the fork; PIMScope maintenance does not modify or indiscriminately include that suite. |
| CQ-004 | P1 | Fixed | Parallelism | Artifact collection defaults to 64 `ProcessPoolExecutor` workers. Tasks write unique part files, use atomic replacement, and aggregate only after all tasks pass. Tests now exercise both failure-closed sequential handling and real isolated process execution with two workers. |
| CQ-005 | P1 | Fixed | Resource use | The paper tool retains the requested default of 64 workers, caps the pool to pending task count, reports requested versus effective concurrency, and warns when a conservative 1 GiB-per-worker estimate exceeds Linux `MemAvailable`. Explicit requests are never silently reduced for memory; users select a smaller `--workers` value. |
| CQ-006 | P1 | Fixed | Configuration | Researchers can compose an explicit reusable hardware section with an explicit workload section containing model dimensions and trace-generation controls. The prior tag-only model/phase file set was removed. Inline manifests and dotted `--set` overrides remain supported; unknown built-in models fail during validation. The one-controller/channel scope fails closed. |
| CQ-007 | P1 | Fixed | Architecture | Fixed paper plotting and style live in the private `scripts.lib.artifact_plotting` module and consume only validated aggregates. The artifact driver owns the cohesive reproduction pipeline—fixed task matrices, collection, cache/provenance, validated assembly, and claim checks—while simulator behavior remains in `ramulator.pimscope`. This keeps paper-specific policy outside simulator core without fragmenting the small driver into pass-through modules. |
| CQ-008 | P1 | Fixed | Complexity | Core orchestration now delegates preflight limits, materialization policy, concurrency, provenance, frontend count normalization, expected replay counts, and replay-integrity decisions to cohesive tested helpers. Manifest and result validators retain sequential schema checks because splitting them further would obscure field-path error ordering rather than remove a distinct responsibility. Public APIs remain unchanged. |
| CQ-009 | P1 | Fixed | Duplication | Cross-model decode/prefill and PIM-sharing use shared typed replay task/result records, one task factory, one replay worker, shared cache checks, and atomic validated writers. Paper-specific row builders intentionally remain distinct because their stable JSON schemas represent different artifacts rather than duplicated behavior. |
| CQ-010 | P1 | Fixed | Naming | New private modules and helpers use concise verb-object names (`apply_style`, `render_cross_model`, `_replay_task`, `_check_preflight`, and `_replay_integrity`). Existing public `generate_and_replay`, manifest fields, and result fields remain stable; renaming them would require deprecation churn without resolving a defect. |
| CQ-011 | P1 | Fixed | Submodule hygiene | The validated Ramulator changes were committed as `8f24828`, reviewed through fork PR #1, and merged to public `TtitiO/ramulator2:main` as `3a371e8`. The parent gitlink pins that public merge commit and `.gitmodules` uses a public HTTPS URL. Clean-clone verification remains a publication check rather than an unresolved code issue. |
| CQ-012 | P2 | Fixed | Comments/semantics | Essential interpretation boundaries are centralized in documentation and structured result metadata. Long free-form capability and power notes were removed; executable control flow retains only short rationale where behavior is otherwise non-obvious. |
| CQ-013 | P2 | Fixed | Metadata | Capability and power metadata now expose stable fields for support status, paper backend, timing vocabulary, calibration, PIM energy method, and validated scope, plus one `metadata_documentation` link. Long free-form `notes` were removed and regression tests lock the machine-readable contract. |
| CQ-014 | P2 | Fixed | Packaging | The parent distribution declares an exact `ramulator==2.1.0` dependency contract and its only command, `pimscope`, resolves directly to `ramulator.pimscope.cli:main`. The duplicate CLI and installed artifact command are removed; the fixed paper tool remains a repository script outside simulator core. |
| CQ-015 | P2 | Fixed | Supported scope | LPDDR6-PIM remains explicitly `experimental`, reports `paper_artifact_backend: false` and `paper_artifact_backend_name: LPDDR5PIM`, and documents its single-subchannel and non-device-calibrated power boundaries. Public tutorial/config docs support LPDDR5-PIM and paper matrices remain pinned to it; LPDDR6-PIM tests remain development coverage rather than release claims. |

## Completed quality safeguards

The current refactor already provides useful release foundations:

- versioned manifest, result, trace, and aggregate validation;
- unknown-field and unsupported-topology rejection;
- a single `pimscope` implementation at `ramulator.pimscope.cli:main`;
- bounded trace expansion and optional process timeout;
- deterministic source/configuration cache fingerprints;
- repository-relative paths in newly generated aggregate output;
- atomic, isolated part-file writes;
- failure-closed parallel collection (no partial aggregate publication);
- explicit seed and provenance recording;
- independent result and trace validation commands.

These safeguards should be retained while simplifying implementation.

## Refactoring order

1. **Restore correctness:** clean ABI-matched build, run all tests, regenerate
   and validate oracle outputs.
2. **Lock behavior:** add worker-isolation, cache invalidation, CLI, and schema
   tests; privately compare reproduced cycle values with the legacy oracle.
3. **Separate responsibilities:** split artifact execution, aggregation, and
   plotting; split backend replay, validation, and reporting.
4. **Remove duplication:** use typed task descriptions and shared validated
   writers.
5. **Improve names:** rename private functions in small reviewed changes.
   Preserve public commands, manifest keys, result keys, and compatibility.
6. **Reduce prose in code:** keep only rationale that cannot be expressed by
   types, validation, tests, or linked documentation.

Large naming-only rewrites should not precede numerical regression coverage;
they create review noise and can invalidate reproducibility without improving
research use.

## Oracle contract

`results/oracle` is immutable old-tag numerical evidence, not a current-schema
fixture or cache. Its metadata, provenance, path fields, and schema tags are not
part of comparison. A reproduction must:

1. use the recorded parent commit, Ramulator commit, paper matrix, and compatible
   toolchain;
2. write to a new directory, never directly over `results/oracle`;
3. validate every newly generated part and aggregate with current schemas;
4. require every new replay status to pass;
5. privately compare identical row identities and exact integer `cycles`,
   `cycles_k1`, and `cycles_k2` values with the legacy oracle;
6. keep that comparison out of public commands and simulator APIs;
7. render figures from newly generated aggregates;
8. document and review any intentional cycle change instead of rewriting the
   oracle merely to pass.

This preserves the latency-cycle reference while allowing old tags and metadata
to remain historical.

## Release gate

From a fresh recursive clone and a clean environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip setuptools wheel
.venv/bin/python -m pip install -r ramulator2/requirements-dev.txt
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install --no-build-isolation -e ramulator2
CMAKE="$PWD/.venv/bin/cmake"
"$CMAKE" -S ramulator2 -B ramulator2/build \
  -DPython_EXECUTABLE="$PWD/.venv/bin/python" \
  -DCMAKE_BUILD_TYPE=Release
"$CMAKE" --build ramulator2/build -j"$(nproc)"
.venv/bin/python -m ruff check scripts tests
.venv/bin/python -m pytest -q tests
.venv/bin/python scripts/gen_figures.py --all --workers 64 \
  --output-dir results/reproduction
```

Then privately compare the new latency cycles with the legacy oracle. Upstream
Ramulator's own suite is maintained and gated separately in the fork; do not
modify or indiscriminately include it in the PIMScope package gate. Release only
when all P0 issues are closed and no P1 correctness issue remains.
