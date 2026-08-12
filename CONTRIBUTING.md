# Contributing to PIMScope

Thank you for contributing. Changes must preserve the validated LPDDR5-PIM
paper baseline unless they fix a documented model defect.

## Development setup

Follow the clean installation instructions in [README.md](README.md), including
the recursive submodule checkout. Before submitting a change, run:

```bash
python -m ruff format --check scripts tests
python -m ruff check scripts tests
python -m pytest -q tests
```

Changes in `ramulator2/` must also run the relevant project-owned tests from
that directory. Native timing/controller changes should include native test
binding coverage.

## Change boundaries

- DRAM behavior, controllers, trace replay, workload lowering, and reusable
  simulation APIs belong in `ramulator2/`.
- Paper experiment matrices, aggregate assembly, figures, and claim checks
  belong in this repository.
- New public configuration fields require validation, resolved-result
  provenance, documentation, and negative tests.
- Do not silently change trace schemas or reinterpret existing result fields.
- Do not commit virtual environments, build products, caches, or generated
  `results/` artifacts.

## Bug reports

Include:

- operating system, Python, compiler, and CMake versions;
- root and `ramulator2` commit IDs;
- the command and manifest used;
- trace schema and backend name;
- complete error output and `pimscope doctor --config <manifest>` output;
- whether the issue reproduces in a clean checkout.

Do not attach proprietary model checkpoints or confidential traces. Reduce
large traces to the smallest reproducer when possible.

## Pull requests

Explain the behavior being changed, add focused tests, and report test commands.
For changes that can affect simulation, compare decode, prefill, sharing, and
figure outputs against a preserved baseline. Every numerical difference must be
explained.
