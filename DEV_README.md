# Skyknit 2.0 — Developer Guide

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — fast Python package and project manager

Install uv if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Setup

Clone the repo and create the virtual environment in one step:

```bash
git clone <repo-url>
cd skyknit2.0
uv sync --extra dev
```

`uv sync` reads `pyproject.toml`, creates a `.venv` in the project root, and installs all runtime and dev dependencies. The `.python-version` file pins the interpreter to Python 3.11.

To activate the venv in your shell (optional — `uv run` handles this automatically):

```bash
source .venv/bin/activate
```

---

## Running Tests

```bash
uv run pytest
```

Run with verbose output:

```bash
uv run pytest -v
```

Run a specific test file:

```bash
uv run pytest topology/tests/test_registry.py -v
```

Tests live in `topology/tests/` and use [pytest](https://docs.pytest.org/).

---

## Linting and Formatting

This project uses [ruff](https://docs.astral.sh/ruff/) for both linting and formatting.

**Check for lint errors:**

```bash
uv run ruff check .
```

**Auto-fix lint errors:**

```bash
uv run ruff check --fix .
```

**Check formatting:**

```bash
uv run ruff format --check .
```

**Apply formatting:**

```bash
uv run ruff format .
```

Ruff is configured in `pyproject.toml` under `[tool.ruff]`. The active rule sets are:

| Code | Ruleset |
|------|---------|
| `E`, `W` | pycodestyle |
| `F` | Pyflakes |
| `I` | isort (import ordering) |

---

## Project Structure

```
skyknit2.0/
├── .github/
│   └── workflows/
│       └── ci.yml          # CI/CD pipeline (lint + test)
├── topology/               # Main package
│   ├── __init__.py
│   ├── types.py            # Enums and dataclass definitions
│   ├── registry.py         # Singleton topology registry
│   ├── data/               # Versioned YAML lookup tables
│   │   ├── edge_types.yaml
│   │   ├── join_types.yaml
│   │   ├── compatibility.yaml
│   │   ├── arithmetic_implications.yaml
│   │   ├── defaults.yaml
│   │   └── writer_dispatch.yaml
│   └── tests/
│       └── test_registry.py
├── .python-version         # Pins Python 3.11 for uv
├── pyproject.toml          # Project metadata, deps, tool config
├── ARCHITECTURE.md         # System design reference
├── CITATIONS.md            # Academic references
└── README.md               # Project overview
```

---

## CI/CD Pipeline

The GitHub Actions workflow at `.github/workflows/ci.yml` runs on every push and on pull requests targeting `main`/`master`.

It runs two parallel jobs:

| Job | Steps |
|-----|-------|
| **lint** | `ruff check .` + `ruff format --check .` |
| **test** | `pytest -v` |

Both jobs use `astral-sh/setup-uv` to install uv, then `uv sync --extra dev` to install all dependencies before running.

---

## Adding Dependencies

**Runtime dependency:**

```bash
uv add <package>
```

**Dev-only dependency:**

```bash
uv add --optional dev <package>
```

Both commands update `pyproject.toml` and regenerate `uv.lock` automatically.

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed description of the system design, data model, and build pipeline.

The core idea: all domain knowledge (edge types, join types, compatibility rules) lives in versioned YAML lookup tables under `topology/data/`. The `TopologyRegistry` loads these at import time, validates cross-references, and exposes an immutable query API. LLM-generated judgment feeds into this deterministic core.
