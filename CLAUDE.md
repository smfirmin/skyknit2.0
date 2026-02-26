# CLAUDE.md

## Project Overview

Skyknit 2.0 is an AI-powered knitting pattern generator for top-down sweater construction. It combines formal topology, computational knitting research, and LLM judgment to produce correct patterns from user intent, body measurements, and yarn specifications.

**Language:** Python 3.14+ | **Build tool:** uv | **Package:** setuptools

## Commands

```bash
# Setup
uv sync --extra dev

# Tests
uv run pytest                          # run all tests
uv run pytest -v                       # verbose
uv run pytest topology/tests/ -v       # specific directory

# Lint & format
uv run ruff check .                    # lint
uv run ruff check --fix .              # lint with auto-fix
uv run ruff format .                   # format
uv run ruff format --check .           # format check only

# Type checking
uv run mypy topology/                  # strict mode
```

## CI

GitHub Actions runs three parallel jobs on every push and PR to main: **lint** (`ruff check` + `ruff format --check`), **typecheck** (`mypy topology/`), and **test** (`pytest -v`). All three must pass before merging.

## Dependencies

- Only runtime dependency: PyYAML
- `uv.lock` is committed for reproducible builds — re-run `uv sync` after pulling
- Add runtime deps: `uv add <pkg>` | Add dev deps: `uv add --dev <pkg>`

## Architecture

- **topology/** — Core package: edge/join type registry backed by YAML lookup tables
  - `types.py` — Enums (`EdgeType`, `JoinType`, `CompatibilityResult`, etc.) and frozen dataclasses
  - `registry.py` — `TopologyRegistry` singleton: loads, validates, and queries lookup tables
  - `data/*.yaml` — 6 versioned lookup tables (edge types, join types, compatibility, defaults, arithmetic, writer dispatch)
  - `tests/` — Pytest suite (80+ assertions)

See `ARCHITECTURE.md` for full system design and module build order.

## Code Conventions

- **Strict mypy** — All functions require type annotations (tests exempted from `disallow_untyped_defs`)
- **Frozen dataclasses** for all data structures; `MappingProxyType` for public dicts
- **NamedTuple for composite keys** (e.g., `CompatibilityKey`) to prevent silent key transposition
- **Enums for all domain vocabulary** — never raw strings
- **Fail-fast validation** — cross-reference checks at import time, not lazy
- **Ruff** — line length 100, target py314, rules: E, W, F, I (E501 ignored)
- PascalCase classes, UPPER_CASE enums, snake_case methods, `_prefix` for private
- Docstrings on public classes/methods; inline comments only for non-obvious logic

## Test Conventions

- Module-scoped `registry` fixture — registry loads once per test module for efficiency
- Parametrized tests for edge/join compatibility combinations
- `tmp_path` fixture for testing corrupted or missing YAML (isolated data directories)
- Mutation-proof assertions: verify returned dicts are copies, not mutable views
- Negative tests for known-invalid combinations and missing keys

## Adding New Data

1. Define or extend enum in `topology/types.py`
2. Add entries to the relevant YAML files in `topology/data/`
3. Import the module — cross-reference validation runs at startup and will raise if any enum value is missing from required tables
4. CONDITIONAL compatibility entries must include a `condition_fn` field
5. YAML files carry a `version` field — bump when changing table schema

## Design Invariants

- Geometry, fabric, and construction are strictly separated
- LLM judgment vs. deterministic code boundary is explicit; domain knowledge lives in YAML lookup tables
- Joins are first-class objects connecting typed edges, not properties of components
- Lookup tables are loaded once at startup and are immutable at runtime
- Physical tolerance is always in mm, never stitch counts
