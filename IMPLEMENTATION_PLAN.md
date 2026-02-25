# Skyknit 2.0 — Incremental Implementation Plan

## Context

Skyknit 2.0 is an AI-powered knitting pattern generator for top-down sweaters. The architecture (`ARCHITECTURE.md`) defines a 12-step build order separating geometry, fabric, and construction concerns. Step 1 (lookup tables + topology registry) is complete. This plan breaks steps 2–12 into the smallest possible self-contained increments, each following TDD (red→green→refactor) and leaving CI green.

**What exists today:**

- `topology/` package: types, enums, registry, 6 YAML lookup tables, 60+ tests
- CI pipeline: ruff lint, mypy strict, pytest
- Python 3.14, uv, `pyproject.toml`

---

## Package Structure

Each architectural module becomes its own top-level Python package for maximum separation of concerns:

```
skyknit2.0/
├── topology/        # (exists) Lookup tables and registry
├── utilities/       # Shared utilities (unit conversion, repeats, tolerance, shaping)
├── schemas/         # Data contracts (IR operations, shape manifest, constraint object)
├── checker/         # Algebraic Checker (simulation VM)
├── validator/       # Geometric Validator (Phase 1 and Phase 3)
├── fillers/         # Stitch Fillers (per-component LLM + deterministic tools)
├── planner/         # Planner (LLM + deterministic tools)
├── fabric/          # Fabric Module (LLM + deterministic tools)
├── orchestrator/    # Orchestrator (DAG execution, retry routing)
├── design/          # Design Module (LLM — proportion spec generation)
├── writer/          # Writer (LLM — IR to pattern prose)
```

---

## Phase 2 — Shared Utilities

### Step 2.1: Create `utilities/` package scaffold + Gauge dataclass

**Files:**

- `utilities/__init__.py`
- `utilities/types.py` — `Gauge` frozen dataclass (`stitches_per_inch: float`, `rows_per_inch: float`)
- `utilities/tests/__init__.py`
- `utilities/tests/test_types.py`

**Update:** `pyproject.toml` — add `"utilities/tests"` to `testpaths`, add `"utilities"` to `known-first-party`

**Tests:**

- Gauge construction with valid values
- Gauge is frozen (immutable)
- Gauge rejects zero/negative values (via `__post_init__` validation)

**Acceptance:** `uv run pytest`, `uv run mypy utilities/`, `uv run ruff check .` all pass.

---

### Step 2.2: Unit conversion functions

**Files:**

- `utilities/conversion.py`

**Functions:**

- `inches_to_mm(inches: float) → float`
- `mm_to_inches(mm: float) → float`
- `physical_to_stitch_count(dimension_mm: float, gauge: Gauge) → float` — raw (non-integer) stitch count
- `physical_to_row_count(dimension_mm: float, gauge: Gauge) → float`
- `stitch_count_to_physical(count: float, gauge: Gauge) → float` — mm
- `row_count_to_physical(count: float, gauge: Gauge) → float` — mm

**File:** `utilities/tests/test_conversion.py`

**Tests:**

- Round-trip: `stitch_count_to_physical(physical_to_stitch_count(x, g), g) ≈ x`
- Round-trip: `row_count_to_physical(physical_to_row_count(x, g), g) ≈ x`
- Known values: 5 sts/inch gauge, 25.4mm (1 inch) → 5.0 stitches
- `inches_to_mm` / `mm_to_inches` round-trip
- Edge cases: zero dimension returns zero

**Acceptance:** All tests pass, mypy clean, ruff clean.

---

### Step 2.3: Tolerance calculator

**Files:**

- `utilities/tolerance.py`

**Types:**

- `PrecisionLevel` enum: `HIGH = 0.75`, `MEDIUM = 1.0`, `LOW = 1.5`

**Functions:**

- `gauge_base_mm(gauge: Gauge) → float` — one stitch-width in mm (`25.4 / gauge.stitches_per_inch`)
- `calculate_tolerance_mm(gauge: Gauge, ease_multiplier: float, precision: PrecisionLevel) → float` — `gauge_base × ease_multiplier × precision.value`

**File:** `utilities/tests/test_tolerance.py`

**Tests:**

- Known calculation: 5 sts/inch, ease 1.0, medium precision → `25.4/5 × 1.0 × 1.0 = 5.08mm`
- High precision produces smaller tolerance than low
- Ease multiplier scales linearly
- Validates `ease_multiplier` in range `[0.75, 2.0]`
- Validates `gauge_base_mm` for typical gauges

**Acceptance:** All tests pass, CI green.

---

### Step 2.4: Pattern repeat arithmetic — valid count enumeration

**Files:**

- `utilities/repeats.py`

**Functions:**

- `find_valid_counts(raw_target: float, tolerance_stitches: float, stitch_repeat: int, hard_constraints: list[int] | None = None) → list[int]`
  - Finds all integer stitch counts within `[raw_target - tolerance, raw_target + tolerance]` that are divisible by `stitch_repeat` and satisfy all hard constraints (each hard constraint is a divisor the count must also be divisible by)
  - Returns sorted list

**File:** `utilities/tests/test_repeats.py`

**Tests:**

- Simple case: target 100, tolerance 3, repeat 4 → `[100]` (100 is divisible by 4)
- Multiple valid counts in range
- No valid counts returns empty list
- Hard constraint filtering (e.g., must also be divisible by 6)
- Repeat of 1 means any integer is valid
- Tolerance of 0 means only exact target (if integer and valid)

**Acceptance:** All tests pass, CI green.

---

### Step 2.5: Pattern repeat arithmetic — stitch count selection

**Functions** (add to `utilities/repeats.py`):

- `select_stitch_count(raw_target: float, tolerance_stitches: float, stitch_repeat: int, hard_constraints: list[int] | None = None) → int | None`
  - Calls `find_valid_counts`, then selects closest to `raw_target`; prefers larger on tie
  - Returns `None` if no valid counts found (triggers escalation)

**Tests** (add to `utilities/tests/test_repeats.py`):

- Selects closest valid count to target
- Tie-breaking: prefers larger
- Returns `None` when no valid counts exist
- With `tolerance=0` and exact match
- Integration: physical dimension → stitch count via conversion + selection

**Acceptance:** All tests pass, CI green.

---

### Step 2.6: Full stitch count selection pipeline

**Functions** (add to `utilities/repeats.py`):

- `select_stitch_count_from_physical(dimension_mm: float, gauge: Gauge, tolerance_mm: float, stitch_repeat: int, hard_constraints: list[int] | None = None) → int | None`
  - Converts physical to raw stitch count, converts `tolerance_mm` to `tolerance_stitches`, delegates to `select_stitch_count`
  - This is the end-to-end function used by Stitch Fillers and Algebraic Checker

**Tests:**

- End-to-end: 254mm (10 inches) at 5sts/inch → raw 50, with repeat 4 and tolerance 5.08mm → selects valid count
- Confirms same utility used by both modules (import path test)

**Acceptance:** All tests pass, CI green.

---

### Step 2.7: Shaping rate calculator

**Files:**

- `utilities/shaping.py`

**Types:**

- `ShapingInterval` frozen dataclass: `action: str` (increase/decrease), `every_n_rows: int`, `times: int`, `stitches_per_action: int`

**Functions:**

- `calculate_shaping_intervals(stitch_delta: int, section_depth_rows: int, stitches_per_action: int = 2) → list[ShapingInterval]`
  - Given the total stitch change needed and the number of rows available, distributes shaping evenly
  - Positive delta = increases, negative = decreases
  - Returns list of `ShapingInterval`s

**File:** `utilities/tests/test_shaping.py`

**Tests:**

- Simple even distribution: delta -20, depth 40 rows, 2 sts/action → decrease every 4 rows, 10 times
- Uneven distribution produces two intervals (more frequent + less frequent)
- Zero delta → empty list
- Delta requires more rows than available → error or single-row intervals
- Positive delta (increases) labeled correctly

**Acceptance:** All tests pass, CI green.

---

### Step 2.8: Utilities public API and exports

**Update:** `utilities/__init__.py` — export all public types and functions

**Tests** (add to `utilities/tests/test_types.py` or new `test_init.py`):

- All public names importable from `utilities`
- Verify `__all__` is complete

**Acceptance:** All tests pass, CI green.

---

## Phase 3 — Schema Definitions

### Step 3.1: Create `schemas/` package + PrecisionPreference

**Files:**

- `schemas/__init__.py`
- `schemas/proportion.py` — `PrecisionPreference` enum (`HIGH`, `MEDIUM`, `LOW`), `ProportionSpec` frozen dataclass (ratios dict, precision preference)
- `schemas/tests/__init__.py`
- `schemas/tests/test_proportion.py`

**Update:** `pyproject.toml` — add `"schemas/tests"` to `testpaths`, `"schemas"` to `known-first-party`

**Tests:**

- `ProportionSpec` is frozen
- `ProportionSpec` contains dimensionless ratios (no units)
- `PrecisionPreference` maps to utility `PrecisionLevel` values

**Acceptance:** CI green.

---

### Step 3.2: Constraint Object schema

**Files:**

- `schemas/constraint.py`

**Types:**

- `StitchMotif` frozen dataclass: `name: str`, `stitch_repeat: int`, `row_repeat: int`
- `YarnSpec` frozen dataclass: `weight: str`, `fiber: str`, `needle_size_mm: float`
- `ConstraintObject` frozen dataclass: `gauge: Gauge` (from utilities), `stitch_motif: StitchMotif`, `hard_constraints: tuple[int, ...]`, `yarn_spec: YarnSpec`, `physical_tolerance_mm: float`

**File:** `schemas/tests/test_constraint.py`

**Tests:**

- `ConstraintObject` is frozen
- All fields accessible
- Reuses `Gauge` from `utilities` (not a duplicate type)

**Acceptance:** CI green.

---

### Step 3.3: Component shape types and edge schema

**Files:**

- `schemas/manifest.py`

**Types:**

- `ShapeType` enum: `CYLINDER`, `TRAPEZOID`, `RECTANGLE` (extensible for v1 sweater shapes)
- `Handedness` enum: `LEFT`, `RIGHT`, `NONE`
- `ComponentSpec` frozen dataclass: `name: str`, `shape_type: ShapeType`, `dimensions: dict[str, float]` (physical mm), `edges: tuple[Edge, ...]` (reuses `topology.Edge`), `handedness: Handedness`, `instantiation_count: int`
- `ShapeManifest` frozen dataclass: `components: tuple[ComponentSpec, ...]`, `joins: tuple[Join, ...]` (reuses `topology.Join`)

**File:** `schemas/tests/test_manifest.py`

**Tests:**

- `ShapeManifest` is frozen
- Components reference edges by name
- Joins reference edges by `"component.edge"` string format
- Edge types come from `topology.EdgeType` enum
- Join types come from `topology.JoinType` enum

**Acceptance:** CI green.

---

### Step 3.4: IR Operation types

**Files:**

- `schemas/ir.py`

**Types:**

- `OpType` enum: `CAST_ON`, `INCREASE_SECTION`, `WORK_EVEN`, `DECREASE_SECTION`, `SEPARATE`, `TAPER`, `BIND_OFF`, `HOLD`, `PICKUP_STITCHES`
- `Operation` frozen dataclass: `op_type: OpType`, `parameters: dict[str, Any]`, `row_count: int | None`, `stitch_count_after: int | None`, `notes: str`
- `ComponentIR` frozen dataclass: `component_name: str`, `handedness: Handedness`, `operations: tuple[Operation, ...]`, `starting_stitch_count: int`, `ending_stitch_count: int`

**File:** `schemas/tests/test_ir.py`

**Tests:**

- `ComponentIR` is frozen
- Operations are parameterized (not flattened row-by-row)
- Can construct a minimal IR for a plain stockinette rectangle (`CAST_ON → WORK_EVEN → BIND_OFF`)
- Handedness annotation present

**Acceptance:** CI green.

---

### Step 3.5: Schemas public API and exports

**Update:** `schemas/__init__.py` — export all public types

**Tests:**

- All schema types importable from `schemas`
- Verify `__all__`

**Acceptance:** CI green.

---

## Phase 4 — Algebraic Checker

### Step 4.1: Create `checker/` package + VM state model

**Files:**

- `checker/__init__.py`
- `checker/vm_state.py` — `VMState` dataclass: `live_stitch_count: int`, `held_stitches: dict[str, int]`, `row_counter: int`, `current_needle: str`
- `checker/tests/__init__.py`
- `checker/tests/test_vm_state.py`

**Update:** `pyproject.toml` — add `"checker/tests"` to `testpaths`, `"checker"` to `known-first-party`

**Tests:**

- `VMState` initial values
- Stitch count cannot go negative
- Held stitches tracked by label

**Acceptance:** CI green.

---

### Step 4.2: Single-operation execution

**Files:**

- `checker/operations.py`

**Functions:**

- `execute_op(state: VMState, op: Operation) → VMState`
  - `CAST_ON`: sets `live_stitch_count`
  - `WORK_EVEN`: advances `row_counter` by `op.row_count`, stitch count unchanged
  - `INCREASE_SECTION`: applies stitch delta over rows
  - `DECREASE_SECTION`: applies stitch delta over rows
  - `BIND_OFF`: sets `live_stitch_count` to 0
  - `HOLD`: moves stitches from live to held
  - `SEPARATE`: splits live stitches into groups
  - `PICKUP_STITCHES`: adds stitches from held/edge

**File:** `checker/tests/test_operations.py`

**Tests** (one per operation type):

- `CAST_ON`: 0 → N stitches
- `WORK_EVEN`: stitch count unchanged, rows advance
- `INCREASE_SECTION`: stitch count increases correctly
- `DECREASE_SECTION`: stitch count decreases correctly
- `BIND_OFF`: stitch count → 0
- `HOLD`: live decreases, held increases
- Invalid operation (negative stitches) → error

**Acceptance:** CI green.

---

### Step 4.3: Intra-component simulation

**Files:**

- `checker/simulate.py`

**Functions:**

- `simulate_component(ir: ComponentIR) → SimulationResult`
  - Executes all operations in sequence
  - Validates: `starting_stitch_count` matches first op, `ending_stitch_count` matches final state
  - Returns `SimulationResult`: `passed: bool`, `final_state: VMState`, `errors: list[CheckerError]`

**Types:**

- `CheckerError` frozen dataclass: `component_name: str`, `operation_index: int`, `message: str`, `error_type: str` (`filler_origin` / `geometric_origin`)
- `SimulationResult` frozen dataclass

**File:** `checker/tests/test_simulate.py`

**Tests:**

- Valid simple component (`CAST_ON → WORK_EVEN → BIND_OFF`) passes
- Stitch count mismatch at end → error
- Invalid operation sequence (`BIND_OFF` before `CAST_ON`) → error
- Declared `starting_stitch_count` doesn't match `CAST_ON` → error

**Acceptance:** CI green.

---

### Step 4.4: Edge stitch count extraction

**Functions** (add to `checker/simulate.py`):

- `extract_edge_counts(ir: ComponentIR, component_spec: ComponentSpec) → dict[str, int]`
  - Maps each named edge to its stitch count at that point in the IR execution
  - E.g., the top edge's count is the `starting_stitch_count`, the bottom edge's count is the `ending_stitch_count`

**Tests:**

- Correct stitch counts extracted for a component with top and bottom edges
- Intermediate edges (e.g., underarm separation) captured

**Acceptance:** CI green.

---

### Step 4.5: Inter-component join validation

**Files:**

- `checker/joins.py`

**Functions:**

- `validate_join(join: Join, edge_counts: dict[str, int], tolerance_mm: float, gauge: Gauge) → CheckerError | None`
  - Uses topology registry `get_arithmetic()` to determine join behavior
  - `ONE_TO_ONE`: both edges must have equal stitch counts (within tolerance)
  - `ADDITIVE`: `edge_b` count = `edge_a` count + `cast_on_count` parameter
  - `RATIO`: `edge_b` count = `edge_a` count × `pickup_ratio`
  - `STRUCTURAL`: both edges consumed (count agreement within tolerance)

- `validate_all_joins(joins, all_edge_counts, tolerances, gauges) → list[CheckerError]`

**File:** `checker/tests/test_joins.py`

**Tests** (one per `ArithmeticImplication`):

- `ONE_TO_ONE`: matching counts → pass
- `ONE_TO_ONE`: mismatched counts → error
- `ONE_TO_ONE`: within tolerance → pass
- `ADDITIVE`: correct `cast_on_count` → pass
- `ADDITIVE`: wrong count → error
- `RATIO`: correct ratio → pass
- `STRUCTURAL`: both edges present → pass

**Depends on:** topology registry for arithmetic implications lookup.

**Acceptance:** CI green.

---

### Step 4.6: Algebraic Checker full pipeline

**Files:**

- `checker/checker.py`

**Functions:**

- `check_all(manifest: ShapeManifest, irs: dict[str, ComponentIR], constraints: dict[str, ConstraintObject]) → CheckerResult`
  - Runs intra-component simulation for each IR
  - Extracts edge counts
  - Runs inter-component join validation
  - Classifies errors as filler-origin or geometric-origin

**Types:**

- `CheckerResult` frozen dataclass: `passed: bool`, `errors: list[CheckerError]`

**File:** `checker/tests/test_checker.py`

**Tests:**

- Fully valid simple manifest → passes
- One component with bad stitch count → filler-origin error
- Join mismatch → error with correct classification
- Integration: uses shared utilities for unit conversion (verifies identical implementation)

**Acceptance:** CI green.

---

### Step 4.7: Checker public API and exports

**Update:** `checker/__init__.py` — export `check_all`, `CheckerResult`, `CheckerError`

**Acceptance:** CI green.

---

## Phase 5 — Geometric Validator Phase 1

### Step 5.1: Create `validator/` package + edge-join compatibility check

**Files:**

- `validator/__init__.py`
- `validator/compatibility.py`
- `validator/tests/__init__.py`
- `validator/tests/test_compatibility.py`

**Update:** `pyproject.toml` — add `"validator/tests"` to `testpaths`, `"validator"` to `known-first-party`

**Functions:**

- `validate_edge_join_compatibility(manifest: ShapeManifest) → list[ValidationError]`
  - For each Join in the manifest, looks up the `(edge_type_a, edge_type_b, join_type)` triple in the topology registry compatibility table
  - `VALID` → ok
  - `INVALID` → error
  - `CONDITIONAL` → looks up `condition_fn` name (actual condition evaluation deferred)

**Types:**

- `ValidationError` frozen dataclass: `join_id: str`, `message: str`, `severity: str`

**Tests:**

- Valid manifest passes
- Invalid edge-join combination → error
- `CONDITIONAL` combination noted
- Terminal edge (`OPEN`) with join → error

**Acceptance:** CI green.

---

### Step 5.2: Spatial coherence validation

**Files:**

- `validator/spatial.py`

**Functions:**

- `validate_spatial_coherence(manifest: ShapeManifest) → list[ValidationError]`
  - Checks that joined edges have compatible physical dimensions
  - E.g., two edges in a `CONTINUATION` join should have the same circumference
  - Validates that all edge `join_ref`s point to existing Join objects and vice versa

**File:** `validator/tests/test_spatial.py`

**Tests:**

- Matching dimensions → pass
- Mismatched dimensions → error
- Dangling `join_ref` → error
- Join referencing non-existent edge → error

**Acceptance:** CI green.

---

### Step 5.3: Geometric Validator Phase 1 pipeline

**Files:**

- `validator/phase1.py`

**Functions:**

- `validate_phase1(manifest: ShapeManifest) → ValidationResult`
  - Runs compatibility check + spatial coherence
  - Returns aggregate result

**Types:**

- `ValidationResult` frozen dataclass: `passed: bool`, `errors: list[ValidationError]`

**File:** `validator/tests/test_phase1.py`

**Tests:**

- Valid manifest → passes
- Combined compatibility + spatial errors reported
- Errors route to Planner (error metadata)

**Acceptance:** CI green.

---

## Phase 6 — Stitch Fillers (Deterministic Tools Layer)

### Step 6.1: Create `fillers/` package + stitch count resolver

**Files:**

- `fillers/__init__.py`
- `fillers/resolver.py`
- `fillers/tests/__init__.py`
- `fillers/tests/test_resolver.py`

**Update:** `pyproject.toml` — add `"fillers/tests"` to `testpaths`, `"fillers"` to `known-first-party`

**Functions:**

- `resolve_stitch_counts(component_spec: ComponentSpec, constraint: ConstraintObject) → dict[str, int]`
  - For each edge, converts physical dimension → stitch count using shared utilities
  - Respects tolerance, repeat, hard constraints
  - Returns `edge_name → stitch_count` mapping

**Tests:**

- Simple rectangle component → correct stitch counts for top and bottom edges
- Repeat constraint forces rounding to valid count
- Tolerance band respected
- Returns `None` for edges that can't be resolved (escalation needed)

**Acceptance:** CI green.

---

### Step 6.2: Join parameter reader

**Files:**

- `fillers/join_params.py`

**Functions:**

- `read_join_parameters(join: Join, edge_name: str) → dict[str, Any]`
  - Reads join-owned parameters as read-only
  - Returns parameters relevant to this edge's side of the join
  - E.g., for `CAST_ON_JOIN`: returns `cast_on_count`; for `PICKUP`: returns `pickup_ratio` and `pickup_direction`

**File:** `fillers/tests/test_join_params.py`

**Tests:**

- `CAST_ON_JOIN` returns `cast_on_count`
- `PICKUP` returns `pickup_ratio` and `pickup_direction`
- `CONTINUATION` returns empty dict (no owned parameters)
- Parameters are read-only (mutation doesn't affect original Join)

**Acceptance:** CI green.

---

### Step 6.3: IR builder — basic operations

**Files:**

- `fillers/ir_builder.py`

**Functions:**

- `build_component_ir(component_spec: ComponentSpec, stitch_counts: dict[str, int], constraint: ConstraintObject, joins: list[Join], handedness: Handedness) → ComponentIR`
  - Deterministic tool that builds IR from resolved stitch counts
  - For v1: handles basic shapes (`CAST_ON → shaping → WORK_EVEN → BIND_OFF`)
  - Uses shaping rate calculator from `utilities`

**File:** `fillers/tests/test_ir_builder.py`

**Tests:**

- Plain rectangle: `CAST_ON → WORK_EVEN → BIND_OFF`
- Tapered component: `CAST_ON → DECREASE_SECTION → BIND_OFF`
- Stitch counts in IR match resolved counts
- Handedness annotation propagated

**Acceptance:** CI green.

---

### Step 6.4: Symmetric component mirroring

**Functions** (add to `fillers/ir_builder.py`):

- `mirror_component_ir(ir: ComponentIR) → ComponentIR`
  - Creates mirrored variant: swaps `LEFT↔RIGHT` handedness
  - Reverses directional shaping (`SSK↔K2tog` noted in parameters)

**Tests:**

- `LEFT → RIGHT` handedness swap
- Shaping direction parameters mirrored
- Stitch counts identical

**Acceptance:** CI green.

---

### Step 6.5: Stitch Filler LLM integration interface

**Files:**

- `fillers/filler.py`

**Types:**

- `FillerInput` frozen dataclass: `component_spec`, `constraint`, `joins`, `handedness`
- `FillerOutput` frozen dataclass: `ir: ComponentIR`, `resolved_counts: dict[str, int]`
- `StitchFiller` protocol/ABC with `fill(input: FillerInput) → FillerOutput`

**Implementation:**

- `DeterministicFiller` — uses only deterministic tools (for testing)
- Interface for future `LLMFiller` (LLM + deterministic tools)

**File:** `fillers/tests/test_filler.py`

**Tests:**

- `DeterministicFiller` produces valid IR for simple shapes
- IR passes algebraic checker (integration test)
- Symmetric components produce mirrored pair

**Acceptance:** CI green.

---

## Phase 7 — Planner (Deterministic Tools Layer)

### Step 7.1: Create `planner/` package + component list builder

**Files:**

- `planner/__init__.py`
- `planner/components.py`
- `planner/tests/__init__.py`
- `planner/tests/test_components.py`

**Update:** `pyproject.toml` — add `"planner/tests"` to `testpaths`, `"planner"` to `known-first-party`

**Functions:**

- `build_component_list(proportion_spec: ProportionSpec, measurements: dict[str, float]) → list[str]`
  - For v1 top-down sweater: returns the canonical component list

> **Note:** This plan is incomplete — phases 7 (remaining steps), 8, 9, 10, 11, and 12 will be added in a future update covering Planner (continued), Fabric Module, Orchestrator, Geometric Validator Phase 3, Design Module, and Writer.
