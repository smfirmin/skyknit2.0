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

## Design Invariants

- Geometry, fabric, and construction are strictly separated
- LLM judgment vs. deterministic code boundary is explicit; domain knowledge lives in YAML lookup tables
- Joins are first-class objects connecting typed edges, not properties of components
- Lookup tables are loaded once at startup and are immutable at runtime
- Physical tolerance is always in mm, never stitch counts
