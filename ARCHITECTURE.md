d# AI Knitting Pattern Generator — Architecture Overview

## Purpose

This document is the architecture reference for Skyknit 2.0. It describes the system's
modules, data contracts, lookup tables, build order, and active development direction.
Scope is top-down sweater construction for hand knitting (v1); machine knitting is Phase D.

---

## Implementation Status

| Module | Type | Status |
|---|---|---|
| Topology (lookup tables + registry) | Deterministic | ✅ Complete |
| Utilities (conversion, repeats, tolerance, shaping) | Deterministic | ✅ Complete |
| Schemas (IR, manifest, constraint, proportion) | Data contracts | ✅ Complete |
| Algebraic Checker | Deterministic | ✅ Complete |
| Geometric Validator Phase 1 | Deterministic | ✅ Complete |
| Stitch Fillers | Deterministic | ✅ Complete |
| Planner | Deterministic | ✅ Complete |
| Fabric Module | Deterministic | ✅ Complete |
| Orchestrator | Deterministic | ✅ Complete |
| Writer (`TemplateWriter`) | Deterministic stub | ✅ Complete (LLM variant: future) |
| Design Module (`DeterministicDesignModule`) | Deterministic stub | ✅ Complete (LLM variant: future) |
| **Parser** (`LLMPatternParser`) | **LLM** | 🔄 **Phase 10 — active** |
| Geometric Validator Phase 2 (mesh/viz) | Deterministic | ⏳ Deferred |

---

## Core Philosophy

- **Geometry, fabric, and construction are strictly separated.** No module crosses these boundaries.
- **LLMs handle judgment; deterministic code handles correctness.** The boundary is explicit
  and enforced. LLM output feeds into deterministic validation; it cannot bypass it.
- **All construction domain knowledge lives in lookup tables** — versioned YAML files shipped
  with the system. Modules read from them; nothing writes to them at runtime.
- **Joins are first-class objects**, not properties of components. Every join is edge-to-edge.
- **Tolerance is expressed in physical units (mm)**, derived from gauge, ease, and precision
  preference.
- **The IR is the lingua franca.** Parser (text → IR) and Writer (IR → text) are symmetric.
  The same IR that the pipeline generates can be parsed back from any conforming pattern text.

---

## Pipeline

### Generation (forward direction)

```
Design Module ──▶ Planner ──▶ Stitch Fillers ──▶ Algebraic Checker ──▶ Writer
  proportion      manifest        ComponentIR       validation           prose text
  spec            + joins
```

### Validation (reverse direction — Phase 10)

```
Pattern Text ──[LLM Parser]──▶ ShapeManifest + ComponentIR dict ──[Algebraic Checker]──▶ ValidationReport
```

### Bidirectional loop

```
generate_pattern() ──▶ pattern prose ──[LLM Parser]──▶ IR + Manifest ──[check_all()]──▶ pass
```

This round-trip loop is the key integration test for Phase 10: a generated pattern,
re-parsed and re-validated, must pass the Algebraic Checker.

### Orchestration

An **Orchestrator** manages the generation DAG, triggers modules when inputs are ready,
and routes algebraic failures back to the relevant Stitch Filler for a single retry with
widened tolerance.

---

## Modules

### Design Module
- **Type:** LLM (v1: deterministic stub `DeterministicDesignModule`)
- **In:** User intent, style preferences, ease level
- **Out:** Proportion spec (dimensionless ratios), precision preference
- **v1 status:** `EaseLevel` enum (FITTED/STANDARD/RELAXED) → hardcoded ease ratios

### Planner
- **Type:** Deterministic
- **In:** Proportion spec, user body measurements (mm), GarmentSpec
- **Out:** ShapeManifest (component list + typed edges + Join objects)
- Reads: Edge Type Registry, Join Type Registry, Compatibility Table, Defaults Table
- Works entirely in physical units (mm). No stitch awareness.

### Fabric Module
- **Type:** Deterministic
- **In:** Component list, gauge, stitch motif, yarn spec, precision preference
- **Out:** One ConstraintObject per component (gauge + tolerance + motif + yarn)
- Applies uniform gauge across all components in v1

### Stitch Fillers
- **Type:** Deterministic
- **In:** ComponentSpec (with typed edges + joins), ConstraintObject, handedness
- **Out:** ComponentIR (typed operation sequence)
- Converts physical dimensions → stitch counts using shared utilities
- Selects nearest valid stitch count within physical tolerance band
- Mirrors shaping operations for LEFT/RIGHT handedness

### Algebraic Checker
- **Type:** Deterministic
- **In:** All ComponentIRs + ShapeManifest + ConstraintObjects
- **Out:** CheckerResult (passed bool + tuple of CheckerError)
- Simulates IR execution as a virtual machine; tracks live stitch count
- Validates intra-component stitch count progression
- Validates inter-component join arithmetic (stitch counts match across joins)
- Flags failures as `filler_origin` (bad arithmetic) or `geometric_origin` (measurement mismatch)

### Geometric Validator Phase 1
- **Type:** Deterministic
- **In:** ShapeManifest
- **Out:** ValidationResult (warnings/errors on structural problems)
- Checks edge-join compatibility (Compatibility Table)
- Checks spatial coherence (dangling refs, self-joins, bad edge refs)

### Orchestrator
- **Type:** Deterministic
- Manages the generation DAG: Planner → validate_phase1 → FabricModule → Fillers → check_all
- Single retry for filler-origin checker failures (widens tolerance × 1.5)
- Raises `PipelineError(stage, detail)` on unrecoverable failure

### Writer
- **Type:** LLM (v1: deterministic `TemplateWriter`)
- **In:** WriterInput (ShapeManifest + IRs + component order)
- **Out:** WriterOutput (per-component sections + full_pattern string)
- **v1 status:** Template-based prose from `writer/templates.py`; uses writer_dispatch.yaml
  for join rendering mode (INLINE / INSTRUCTION / HEADER_NOTE)
- Handedness drives left/right language in join instructions
- Suppresses redundant CAST_ON when a PICKUP join instruction already emitted

### Parser *(Phase 10 — active)*
- **Type:** LLM (`LLMPatternParser`)
- **In:** ParserInput (pattern text + gauge + motif + yarn + precision)
- **Out:** ParserOutput (ParsedPattern + ShapeManifest + IRs + ConstraintObjects)
- Uses Claude tool-use API with `extract_knitting_pattern` tool (structured output)
- Deterministic assembler converts JSON → schema types; no free-text parsing
- Feeds directly into `check_all()` for validation
- `PatternParser` Protocol allows deterministic test injection (no real API calls in CI)

---

## Public API

```python
# Generation
from skyknit.api.generate import generate_pattern

pattern_text = generate_pattern(
    garment_type="top-down-drop-shoulder-pullover",
    measurements={...},   # all in mm
    gauge=Gauge(20.0, 28.0),
    stitch_motif=StitchMotif("stockinette", 1, 1),
    yarn_spec=YarnSpec("DK", "wool", 4.0),
)

# Validation (Phase 10)
from skyknit.api.validate import validate_pattern

report = validate_pattern(pattern_text, gauge, stitch_motif, yarn_spec)
# report.passed: bool
# report.checker_result: CheckerResult | None
# report.parse_error: str | None
```

---

## Edge and Join Model

### Edges

Each component has a named set of typed edges — physical boundaries of the 3D primitive.

| Edge Type | has_live_stitches | is_terminal | phase_constraint |
|---|---|---|---|
| `CAST_ON` | false | false | start |
| `LIVE_STITCH` | true | false | any |
| `BOUND_OFF` | false | false | end |
| `SELVEDGE` | false | false | any |
| `OPEN` | false | true | end |

### Joins

A Join object connects exactly two edges (one from each component). Key is ordered
(edge_a upstream, edge_b downstream) and non-commutative.

| Join Type | Arithmetic | Symmetric | Rendering |
|---|---|---|---|
| `CONTINUATION` | ONE_TO_ONE | false | inline |
| `HELD_STITCH` | ONE_TO_ONE | false | instruction block |
| `CAST_ON_JOIN` | ADDITIVE | false | instruction block |
| `PICKUP` | RATIO | false | instruction block |
| `SEAM` | ONE_TO_ONE | true | header note |

**Known v1 limitation:** PICKUP joins from SELVEDGE edges (drop-shoulder armholes) are
skipped in the Algebraic Checker. Pipeline derives sleeve stitch count from
`upper_arm_circumference × ease` (measurement-driven), but RATIO validation expects
`body_rows × pickup_ratio` (topology-driven). These values are not generally equal.

---

## Lookup Tables

Versioned YAML files under `skyknit/topology/data/`. Loaded once at startup, read at
runtime, never written to. Cross-reference validation runs at import time.

| Table | Key | Purpose |
|---|---|---|
| `edge_types.yaml` | edge_type | Master list of edge types |
| `join_types.yaml` | join_type | Master list of join types |
| `compatibility.yaml` | (edge_type_a, edge_type_b, join_type) | VALID / INVALID / CONDITIONAL |
| `defaults.yaml` | (edge_type_a, edge_type_b, join_type) | Default join-owned parameters |
| `arithmetic_implications.yaml` | join_type | ADDITIVE / ONE_TO_ONE / RATIO / STRUCTURAL |
| `writer_dispatch.yaml` | join_type | template_key, rendering_mode, directionality |

---

## Data Contracts

### Proportion Spec
Dimensionless ease ratios from Design Module. No measurements, no stitch counts.
Keys: `body_ease`, `sleeve_ease`, `wrist_ease`. Includes `PrecisionPreference`.

### Shape Manifest
From Planner: component list with shape types, physical dimensions (mm), named typed edges,
Join objects, handedness, and instantiation counts.

### Constraint Object (one per component)
From Fabric Module: `gauge` (stitches/inch, rows/inch), `stitch_motif`, `hard_constraints`,
`yarn_spec`, `physical_tolerance_mm`.

### Component IR
From Stitch Fillers: typed operation sequence (`CAST_ON`, `WORK_EVEN`, `INCREASE_SECTION`,
`DECREASE_SECTION`, `TAPER`, `BIND_OFF`, `HOLD`, `SEPARATE`, `PICKUP_STITCHES`).
Parameterized (not flattened row-by-row). Handedness-annotated.

### ParsedPattern *(Phase 10)*
Intermediate type from LLM Parser before type conversion. All Python primitives (str, int,
float, dict). Boundary object between the LLM and the deterministic assembler.

### ValidationReport *(Phase 10)*
From `validate_pattern()`: `passed` bool, `checker_result` (CheckerResult or None),
`parsed_pattern` (ParsedPattern or None), `parse_error` (str or None).

---

## Tolerance Mechanism

```
physical_tolerance_mm = gauge_base × ease_multiplier × precision_multiplier
```

- `gauge_base`: one stitch-width at component gauge
- `ease_multiplier`: v1 uses neutral 1.0 (ease applied in Planner dimensions)
- `precision_multiplier`: HIGH=0.75, MEDIUM=1.0, LOW=1.5

**Stitch count selection:**
1. Convert physical dimension to raw count at gauge
2. Find all counts satisfying pattern repeat and hard constraints within tolerance band
3. Select closest to raw target; prefer larger on tie
4. If none: widen tolerance by one step (Orchestrator retry)

---

## Package Dependency Graph

All imports use the `skyknit.` prefix.

```
skyknit.topology     ──no upstream deps──▶  (pure domain, depends only on PyYAML)
skyknit.utilities    ──no upstream deps──▶  (pure computation)
skyknit.schemas      ──depends on──▶  skyknit.topology, skyknit.utilities
skyknit.checker      ──depends on──▶  skyknit.schemas, skyknit.utilities, skyknit.topology
skyknit.validator    ──depends on──▶  skyknit.schemas, skyknit.topology
skyknit.fillers      ──depends on──▶  skyknit.schemas, skyknit.utilities, skyknit.topology, skyknit.checker
skyknit.planner      ──depends on──▶  skyknit.schemas, skyknit.topology, skyknit.validator, skyknit.fillers
skyknit.fabric       ──depends on──▶  skyknit.schemas, skyknit.utilities
skyknit.orchestrator ──depends on──▶  skyknit.schemas, skyknit.planner, skyknit.fabric, skyknit.fillers, skyknit.checker, skyknit.validator
skyknit.writer       ──depends on──▶  skyknit.schemas, skyknit.topology
skyknit.design       ──depends on──▶  skyknit.schemas
skyknit.parser       ──depends on──▶  skyknit.schemas, skyknit.topology, skyknit.utilities, skyknit.checker, skyknit.fabric
                     ──optional──▶    anthropic (LLMPatternParser only; deferred import)
skyknit.api          ──depends on──▶  skyknit.design, skyknit.fabric, skyknit.orchestrator,
                                      skyknit.planner, skyknit.writer, skyknit.parser
```

---

## Build Order

| Phase | Module | Status |
|---|---|---|
| 1 | Lookup tables (topology YAML + registry) | ✅ |
| 2 | Shared utilities | ✅ |
| 3 | Schema definitions | ✅ |
| 4 | Algebraic Checker | ✅ |
| 5 | Geometric Validator Phase 1 | ✅ |
| 6 | Stitch Fillers | ✅ |
| 7 | Planner | ✅ |
| 8 | Fabric Module + Orchestrator | ✅ |
| 9 | Writer (template) + Design Module (stub) + API | ✅ |
| **10** | **Parser (LLM) + Validator API** | 🔄 **active** |
| 11 | Writer (LLM variant — richer prose) | ⏳ next |
| 12 | Design Module (LLM variant — natural language intent) | ⏳ planned |
| 13 | Geometric Validator Phase 2 (mesh + visualization) | ⏳ deferred |

---

## Vision Roadmap

| Phase | Description | Status |
|---|---|---|
| A | Hand-knit pipeline (build order 1–9) | ✅ Complete |
| B | Made-to-measure as default interface | ✅ Substantially complete (`generate_pattern()`) |
| C | Pattern validation tool (LLM Parser) | 🔄 Phase 10 |
| D | FabricMode + machine knitting output (DAK format) | ⏳ Planned |
| E | Yarn database + regional sourcing | ⏳ Planned |
| F | Industrial machine formats (Stoll, Shima Seiki) | ⏳ Future |
| G | Body measurement capture (photogrammetry) | ⏳ Future |

---

## Garment Registry

Two garment types registered at startup (self-registering factory pattern):

| Garment type key | Factory | Components |
|---|---|---|
| `top-down-drop-shoulder-pullover` | `make_drop_shoulder_pullover()` | body (CYLINDER) + left/right sleeve (TRAPEZOID) |
| `top-down-yoke-pullover` | `make_v1_yoke_pullover()` | yoke (CYLINDER) + body (CYLINDER) + left/right sleeve (standalone) |

New garments: add a factory function in `skyknit/planner/garments/`, call `register()`,
import it in `skyknit/planner/garments/__init__.py`.

---

## Key Design Invariants

- **The Planner has no stitch awareness.** It works in physical units only.
- **The Fabric Module has no geometry awareness.** It works from component types only.
- **Stitch Fillers treat Join parameters as read-only.** They account for join-owned stitches
  but do not generate them.
- **The Algebraic Checker and Stitch Fillers must use identical `utilities` implementations.**
- **The `CompatibilityKey` triple is ordered.** `(edge_type_a, edge_type_b, join_type)` is
  non-commutative; edge_type_a is the upstream/source.
- **Lookup tables are never written to at runtime.**
- **Tolerance values are always in mm.** Stitch count tolerances are always derived, never set.
- **Failure messages are in user terms.** Measurements and motif names, never stitch arithmetic.
- **LLM output feeds deterministic validation; it cannot bypass it.** The Parser produces IR;
  the Checker validates it. The LLM cannot produce a passing pattern without correct arithmetic.
- **The IR is the lingua franca.** Any module that produces IR and any module that consumes IR
  are interchangeable at the Protocol boundary.
