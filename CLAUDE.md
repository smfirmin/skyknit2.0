# CLAUDE.md

## Project Overview

Skyknit 2.0 is an AI-powered knitting pattern generator for top-down sweater construction. It combines formal topology, computational knitting research, and LLM judgment to produce correct patterns from user intent, body measurements, and yarn specifications.

**Language:** Python 3.14+ | **Build tool:** uv | **Package:** setuptools

## Commands

```bash
# Setup
uv sync --extra dev

# Tests
python3.14 -m pytest                          # run all tests (709 tests across 13 packages)
python3.14 -m pytest -v                       # verbose
python3.14 -m pytest tests/topology/ -v       # topology package only
python3.14 -m pytest tests/utilities/ -v      # utilities package only
python3.14 -m pytest tests/schemas/ -v        # schemas package only
python3.14 -m pytest tests/checker/ -v        # checker package only
python3.14 -m pytest tests/validator/ -v      # validator package only
python3.14 -m pytest tests/fillers/ -v        # fillers package only
python3.14 -m pytest tests/planner/ -v        # planner package only
python3.14 -m pytest tests/fabric/ -v         # fabric module only
python3.14 -m pytest tests/orchestrator/ -v   # orchestrator only
python3.14 -m pytest tests/writer/ -v         # template writer only
python3.14 -m pytest tests/design/ -v         # design module only
python3.14 -m pytest tests/api/ -v            # public API only
python3.14 -m pytest tests/test_end_to_end.py -v  # end-to-end integration tests only

# Lint & format
uv run ruff check .                    # lint
uv run ruff check --fix .              # lint with auto-fix
uv run ruff format .                   # format
uv run ruff format --check .           # format check only

# Type checking
uv run mypy skyknit/topology/          # strict mode (CI target)
uv run mypy skyknit/utilities/ skyknit/schemas/  # also type-annotated
```

## CI

GitHub Actions runs three parallel jobs on every push and PR to main: **lint** (`ruff check` + `ruff format --check`), **typecheck** (`mypy skyknit/topology/`), and **test** (`pytest -v`). All three must pass before merging.

## Dependencies

- Only runtime dependency: PyYAML
- `uv.lock` is committed for reproducible builds — re-run `uv sync` after pulling
- Add runtime deps: `uv add <pkg>` | Add dev deps: `uv add --dev <pkg>`

## Architecture

Thirteen packages live under `skyknit/`; all tests live under `tests/`:

- **skyknit/topology/** — Core package: edge/join type registry backed by YAML lookup tables
  - `types.py` — Enums (`EdgeType`, `JoinType`, `CompatibilityResult`, `ArithmeticImplication`, `RenderingMode`) and frozen dataclasses (`EdgeTypeEntry`, `JoinTypeEntry`, `CompatibilityEntry`, `ArithmeticEntry`, `WriterDispatchEntry`); also runtime objects `Edge` and `Join`
  - `registry.py` — `TopologyRegistry` singleton: loads, validates, and queries all 6 lookup tables; `get_registry()` returns the module-level singleton
  - `data/*.yaml` — 6 versioned lookup tables: `edge_types`, `join_types`, `compatibility`, `defaults`, `arithmetic_implications`, `writer_dispatch`
  - `tests/topology/` — 104 tests across `test_registry.py` (62) and `test_types.py` (42)

- **skyknit/utilities/** — Deterministic computation shared by Stitch Fillers and Algebraic Checker
  - `types.py` — `Gauge` frozen dataclass (stitches_per_inch, rows_per_inch) with fail-fast validation
  - `conversion.py` — Pure functions: `inches_to_mm`, `mm_to_inches`, `physical_to_stitch_count`, `physical_to_row_count`, `stitch_count_to_physical`, `row_count_to_physical`, `physical_to_section_rows`
  - `tolerance.py` — `PrecisionLevel` enum (HIGH=0.75, MEDIUM=1.0, LOW=1.5), `gauge_base_mm`, `calculate_tolerance_mm`
  - `repeats.py` — `find_valid_counts`, `select_stitch_count`, `select_stitch_count_from_physical` — the canonical stitch count selection pipeline
  - `shaping.py` — `ShapingAction` enum, `ShapingInterval` dataclass, `calculate_shaping_intervals`
  - `tests/utilities/` — 119 tests across 6 test files

- **skyknit/schemas/** — Data contract definitions for inter-module communication
  - `proportion.py` — `PrecisionPreference` enum, `ProportionSpec` (dimensionless ratios from Design Module)
  - `manifest.py` — `ShapeType` enum, `Handedness` enum, `ComponentSpec`, `ShapeManifest`
  - `constraint.py` — `StitchMotif`, `YarnSpec`, `ConstraintObject` (one per component from Fabric Module)
  - `ir.py` — `OpType` enum, `Operation`, `ComponentIR`; factory helpers `make_cast_on`, `make_work_even`, `make_bind_off`
  - `tests/schemas/` — 54 tests across 5 test files

- **skyknit/checker/** — Algebraic Checker: validates ComponentIR against stitch arithmetic constraints
  - `vm_state.py` — `VMState` mutable dataclass (intentional exception to frozen convention; simulation cursor)
  - `operations.py` — `execute_op`: match/case dispatch over `OpType`; mutates `VMState`
  - `simulate.py` — `CheckerError`, `SimulationResult`, `simulate_component`, `extract_edge_counts`
  - `joins.py` — `validate_join`, `validate_all_joins`: ArithmeticImplication dispatch + gauge-based mm tolerance
  - `checker.py` — `CheckerResult`, `check_all`: end-to-end check over all components and joins
  - `tests/checker/` — tests across 5 test files

- **skyknit/validator/** — Phase 1 Geometric Validator: structural validation of ShapeManifest
  - `compatibility.py` — `ValidationError`, `validate_edge_join_compatibility`: topology registry lookup
  - `spatial.py` — `validate_spatial_coherence`: dangling refs, bad edge refs, self-joins
  - `phase1.py` — `ValidationResult`, `validate_phase1`: pipeline combining both checks; warnings-only → passed
  - `tests/validator/` — tests across 3 test files

- **skyknit/fillers/** — Stitch Fillers: resolve physical dimensions to stitch counts and build ComponentIR
  - `resolver.py` — `resolve_stitch_counts`: maps edge position + ShapeType to dimension key
  - `join_params.py` — `read_join_parameters`: extracts JoinType-specific parameters as mutable copy
  - `ir_builder.py` — `build_component_ir`, `mirror_component_ir`: IR construction + LEFT↔RIGHT mirroring
  - `filler.py` — `FillerInput`, `FillerOutput`, `StitchFiller` protocol, `DeterministicFiller`
  - `tests/fillers/` — tests across 4 test files

- **skyknit/planner/** — Planner: converts GarmentSpec + ProportionSpec + measurements → ShapeManifest
  - `dimensions.py` — `compute_dimensions`: applies `DimensionRule` objects to measurements + ratios
  - `component_specs.py` — `build_component_spec`: assembles `ComponentSpec` from a `ComponentBlueprint`
  - `joins.py` — `build_join`, `build_all_joins`: constructs `Join` objects from `JoinSpec` + topology defaults
  - `manifest_builder.py` — `build_shape_manifest`: full pipeline (validate → dims → specs → joins → manifest)
  - `planner.py` — `PlannerInput`, `PlannerOutput`, `Planner` protocol, `DeterministicPlanner`
  - `garments/registry.py` — `register`, `get`, `list_types`: simple `dict[str, Callable[[], GarmentSpec]]` registry
  - `garments/v1_yoke_pullover.py` — `make_v1_yoke_pullover()`: canonical v1 GarmentSpec factory (self-registers)
  - `garments/drop_shoulder_pullover.py` — `make_drop_shoulder_pullover()`: drop-shoulder GarmentSpec (self-registers)
  - `ordering.py` — `derive_component_order()`: topological sort of components from join dependency graph
  - `tests/planner/` + `tests/planner/garments/` — 99 tests across 8 test files

- **skyknit/fabric/** — Fabric Module: gauge/motif/yarn → ConstraintObject per component
  - `module.py` — `FabricInput`, `FabricOutput`, `FabricModule` protocol, `DeterministicFabricModule`
  - `tests/fabric/` — 11 tests

- **skyknit/orchestrator/** — Pipeline Orchestrator: wires all stages end-to-end
  - `pipeline.py` — `OrchestratorInput`, `OrchestratorOutput`, `PipelineError`, `DeterministicOrchestrator`
  - Pipeline: Planner → derive_component_order → validate_phase1 → FabricModule → DeterministicFiller → check_all (with single retry for filler-origin errors)
  - `tests/orchestrator/` — 13 tests

- **skyknit/writer/** — Template Writer: ComponentIR → human-readable pattern prose
  - `templates.py` — `render_op`, `render_join_instruction`: prose templates keyed by OpType and template_key
  - `writer.py` — `WriterInput`, `WriterOutput`, `PatternWriter` protocol, `TemplateWriter`
  - Uses `writer_dispatch.yaml` (RenderingMode: INLINE/INSTRUCTION/HEADER_NOTE) and Handedness for left/right language
  - `tests/writer/` — 23 tests

- **skyknit/design/** — Design Module: translates ease preferences into ProportionSpec
  - `module.py` — `EaseLevel` enum (FITTED/STANDARD/RELAXED), `DesignInput`, `DesignOutput`, `DesignModule` protocol, `DeterministicDesignModule`
  - `tests/design/` — 12 tests

- **skyknit/api/** — Public made-to-measure API
  - `generate.py` — `generate_pattern()`: single entry point from measurements + yarn → pattern prose
  - `tests/api/` — 6 tests

- **tests/** (root) — All tests consolidated here (subdirs mirror skyknit/ structure)
  - `tests/test_end_to_end.py` — Full pipeline smoke tests for both garment types (5 tests)
  - `tests/{pkg}/` — Per-package test subdirectories (e.g., `tests/topology/`, `tests/checker/`)

See `ARCHITECTURE.md` for full system design, pipeline, and module build order.

## Code Conventions

- **Strict mypy** — All functions require type annotations (tests exempted from `disallow_untyped_defs`)
- **Frozen dataclasses** for all data structures; `MappingProxyType` for public dicts
- **NamedTuple for composite keys** (e.g., `CompatibilityKey`) to prevent silent key transposition
- **Enums for all domain vocabulary** — never raw strings; enums inherit from `str` for YAML round-tripping
- **Fail-fast validation** — cross-reference checks at import time, not lazy; `__post_init__` guards on dataclasses
- **Ruff** — line length 100, target py314, rules: E, W, F, I (E501 ignored)
- PascalCase classes, UPPER_CASE enums, snake_case methods, `_prefix` for private
- Docstrings on public classes/methods; inline comments only for non-obvious logic
- `from __future__ import annotations` in all modules for forward references

## Test Conventions

- Module-scoped `registry` fixture — registry loads once per test module for efficiency
- Parametrized tests for edge/join compatibility combinations
- `tmp_path` fixture for testing corrupted or missing YAML (isolated data directories)
- Mutation-proof assertions: verify returned dicts are copies, not mutable views
- Negative tests for known-invalid combinations and missing keys
- Factory helpers (`make_cast_on`, `make_work_even`, `make_bind_off`) used in IR tests

## Package Dependency Graph

All imports use the `skyknit.` prefix (e.g., `from skyknit.topology.types import EdgeType`).

```
skyknit.schemas      ──depends on──▶  skyknit.topology, skyknit.utilities
skyknit.utilities    ──no upstream deps──▶  (pure computation)
skyknit.topology     ──no upstream deps──▶  (pure domain, depends only on PyYAML)
skyknit.checker      ──depends on──▶  skyknit.schemas, skyknit.utilities, skyknit.topology
skyknit.validator    ──depends on──▶  skyknit.schemas, skyknit.topology
skyknit.fillers      ──depends on──▶  skyknit.schemas, skyknit.utilities, skyknit.topology, skyknit.checker
skyknit.planner      ──depends on──▶  skyknit.schemas, skyknit.topology, skyknit.validator, skyknit.fillers
skyknit.fabric       ──depends on──▶  skyknit.schemas, skyknit.utilities
skyknit.orchestrator ──depends on──▶  skyknit.schemas, skyknit.planner, skyknit.fabric, skyknit.fillers, skyknit.checker, skyknit.validator
skyknit.writer       ──depends on──▶  skyknit.schemas, skyknit.topology
skyknit.design       ──depends on──▶  skyknit.schemas
skyknit.api          ──depends on──▶  skyknit.design, skyknit.fabric, skyknit.orchestrator, skyknit.planner, skyknit.writer
```

## Adding New Data (Topology Tables)

1. Define or extend enum in `topology/types.py`
2. Add entries to the relevant YAML files in `topology/data/`
3. Import the module — cross-reference validation runs at startup and will raise if any enum value is missing from required tables
4. CONDITIONAL compatibility entries must include a `condition_fn` field (name of a callable in `geometry_validator.conditions`)
5. YAML files carry a `version` field — bump when changing table schema
6. Every `JoinType` must have exactly one entry in both `arithmetic_implications.yaml` and `writer_dispatch.yaml`

## Edge Types (current)

| Edge Type    | has_live_stitches | is_terminal | phase_constraint |
|--------------|-------------------|-------------|------------------|
| `CAST_ON`    | false             | false       | start            |
| `LIVE_STITCH`| true              | false       | any              |
| `BOUND_OFF`  | false             | false       | end              |
| `SELVEDGE`   | false             | false       | any              |
| `OPEN`       | false             | true        | end              |

## Join Types (current)

| Join Type      | symmetric | directional | owns_parameters                      |
|----------------|-----------|-------------|--------------------------------------|
| `CONTINUATION` | false     | true        | (none)                               |
| `HELD_STITCH`  | false     | true        | (none)                               |
| `CAST_ON_JOIN` | false     | true        | cast_on_count, cast_on_method        |
| `PICKUP`       | false     | true        | pickup_ratio, pickup_direction       |
| `SEAM`         | true      | false       | seam_method                          |

## Design Invariants

- Geometry, fabric, and construction are strictly separated
- LLM judgment vs. deterministic code boundary is explicit; domain knowledge lives in YAML lookup tables
- Joins are first-class objects connecting typed edges, not properties of components
- Lookup tables are loaded once at startup and are immutable at runtime
- Physical tolerance is always in mm, never stitch counts
- The `CompatibilityKey` triple is ordered and non-commutative: `edge_type_a` is upstream/source
- Stitch Fillers and the Algebraic Checker must use identical `utilities` implementations
- User-facing failure messages are expressed in measurement/motif terms, never stitch arithmetic
