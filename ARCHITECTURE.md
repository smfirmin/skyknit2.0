d# AI Knitting Pattern Generator — Architecture Overview

## Purpose
This document provides a high-level architecture reference for implementation. It describes the system's modules, data contracts, lookup tables, and build order. Scope is limited to top-down sweater construction for v1.

---

## Core Philosophy
- **Geometry, fabric, and construction are strictly separated.** No module crosses these boundaries.
- **LLMs handle judgment; deterministic code handles correctness.** The boundary is explicit and enforced.
- **All construction domain knowledge lives in lookup tables** — versioned data files that ship with the system. Modules read from them; nothing writes to them at runtime.
- **Joins are first-class objects**, not properties of components. Every join is edge-to-edge: exactly two typed edges, one from each adjacent component.
- **Tolerance is expressed in physical units (mm)**, derived from gauge, ease, and precision preference.

---

## Pipeline

```
Phase 1 — Geometry
  Design Module → Planner → Shape Manifest (typed edges) + Join Objects

Phase 2 — Fabric (concurrent with Phase 1 after component list is emitted)
  Fabric Module → Constraint Objects (one per component)

Phase 3 — Construction & Validation
  Parallel Stitch Fillers → Algebraic Checker → Geometric Validator → Writer
```

An **Orchestrator** manages the dependency graph, triggers modules when their inputs are ready, and routes failures back to the appropriate upstream module.

---

## Modules

### Design Module
- **Type:** LLM
- **In:** User intent, style preferences, target ease
- **Out:** Proportion spec (dimensionless ratios, no measurements or stitch counts), precision preference (high / medium / low)

### Planner
- **Type:** LLM + deterministic tools
- **In:** Proportion spec, user body measurements
- **Out (stage 1):** Component list — emitted first to unblock Fabric Module
- **Out (stage 2):** Shape manifest — geometric shapes with typed edges and populated Join objects
- Reads: Edge Type Registry, Join Type Registry, Compatibility Table, Defaults Table
- Works entirely in physical units (mm / inches). No stitch awareness.

### Fabric Module
- **Type:** LLM + deterministic tools
- **In:** Component list, user yarn/gauge information, precision preference
- **Out:** One Constraint Object per component
- Runs concurrently with Planner stage 2 once component list is available
- Produces physical tolerance value per component using the Tolerance Calculator utility

### Stitch Fillers (parallel, one per component)
- **Type:** LLM + deterministic tools
- **In:** Shape spec with typed edges and Join objects, Constraint Object, handedness annotation
- **Out:** Component IR (typed operation sequence)
- Integration point — the only module that reasons about both geometry and fabric simultaneously
- Reads Join objects as read-only; treats join-owned parameters as given
- Converts physical dimensions to stitch counts using shared Unit Conversion utility
- Selects nearest valid stitch count within physical tolerance band
- Symmetric components (sleeves) instantiated as left/right variants with mirrored shaping and handedness annotations
- Has full discretion over construction strategy within constraints

### Algebraic Checker
- **Type:** Deterministic
- **In:** All component IR, shape manifest, Join objects, Constraint Objects
- **Out:** Pass, or failure with specific component and error type
- Operates as a virtual machine: simulates IR execution, tracks live stitch count, held stitches, needle state
- Reads: Arithmetic Implications Table for boundary transition behaviour
- Validates intra-component: stitch count progression, pattern repeat divisibility, correct arrival at each edge within tolerance
- Validates inter-component: stitch counts delivered to each join agree within tolerance; join-owned parameters correctly accounted for by both adjacent fillers
- Flags failures as filler-origin or geometric-origin to route correctly

### Geometric Validator
- **Type:** Deterministic
- Runs twice:
  - **Phase 1** (after Planner): validates edge-join spatial coherence from shape manifest alone; produces 3D mesh preview
  - **Phase 3** (after Algebraic Checker passes): final assembly check catching geometry errors that only emerge from stitch count resolution
- Reads: Compatibility Table during Phase 1
- Failures route to Planner to revise shape manifest

### Orchestrator
- **Type:** Deterministic
- Manages the pipeline DAG: tracks which module outputs are available, triggers downstream modules when dependencies are satisfied
- Handles retry routing: algebraic failures → relevant Stitch Filler; geometric failures → Planner; tolerance escalation → defined escalation sequence
- Named component; retry logic lives here, not scattered across modules

### Writer
- **Type:** LLM
- **In:** Assembled validated IR with join context and handedness annotations
- **Out:** Natural language pattern text
- Reads: Writer Dispatch Table for join rendering behaviour (inline, instruction block, or header note)
- Uses controlled stitch vocabulary consistent across all component outputs
- Handedness annotations drive mirrored language for symmetric component instances (SSK vs K2tog, left vs right pickup)
- Swappable variants: beginner-verbose, standard prose, chart notation

---

## Edge and Join Model

### Edges
Each component shape has a named set of typed edges — physical boundaries of the 3D primitive. An edge has a type, physical description (circumference, angle, orientation), and a join slot (empty for terminal edges like cuffs/hems, or populated with a Join object reference).

**Initial edge types:**
- `CAST_ON` — starting edge where stitches are created
- `LIVE_STITCH` — stitches on needle, to be transferred or held
- `BOUND_OFF` — finished edge, no live stitches
- `PICKUP` — selvedge or row-end edge for stitch pickup
- `OPEN` — terminal edge, no join (cuff, hem, neckline)

### Joins
A Join object connects exactly two edges (one from each component). Contains: edge references (ordered — directionality matters for table lookup), join type, join-owned parameters, directionality (symmetric / directional), and physical boundary dimensions.

**Initial join types:**
- `CONTINUATION` — working yarn continues seamlessly; requires LIVE_STITCH on both sides
- `HELD_STITCH` — live stitches placed on hold, returned to later
- `CAST_ON_JOIN` — new stitches cast on at boundary; owns cast-on count
- `PICKUP` — stitches picked up from finished edge; owns pickup ratio
- `SEAM` — two bound-off edges joined post-construction; symmetric

**Top-down sweater underarm example (4 pairwise joins):**
```
YOKE.left_underarm (LIVE_STITCH)  ↔  SLEEVE_LEFT.cap (LIVE_STITCH)   → HELD_STITCH
YOKE.right_underarm (LIVE_STITCH) ↔  SLEEVE_RIGHT.cap (LIVE_STITCH)  → HELD_STITCH
YOKE.body (LIVE_STITCH)           ↔  BODY.top (CAST_ON)              → CAST_ON_JOIN (owns underarm cast-on count)
YOKE.collar (LIVE_STITCH)         ↔  COLLAR.bottom (CAST_ON)         → CONTINUATION
BODY.bottom (OPEN)                                                    → terminal
```

---

## Lookup Tables
Versioned structured data files (JSON or YAML) shipped with the system. Loaded at startup, read at runtime, never written to. Cross-referencing validation runs at startup to catch missing or inconsistent entries.

| Table | Key | Purpose |
|---|---|---|
| Edge Type Registry | edge_type | Master list of edge types with direction and phase constraints |
| Join Type Registry | join_type | Master list of join types with ownership and symmetry metadata |
| Compatibility Table | (edge_type_A, edge_type_B, join_type) | VALID / INVALID / CONDITIONAL per combination. Key is ordered. |
| Defaults Table | (edge_type_A, edge_type_B, join_type) | Default values for join-owned parameters |
| Arithmetic Implications Table | join_type | How join affects stitch count: ADDITIVE / ONE_TO_ONE / RATIO / STRUCTURAL |
| Writer Dispatch Table | join_type | Writer template key, rendering mode, directionality note |

**Compatibility Table entries:**
- `VALID` — unconditionally valid
- `INVALID` — never valid
- `CONDITIONAL` — valid when a named constraint function (in code) returns true; function name stored in table entry

---

## Data Contracts

### Proportion Spec
Dimensionless ratios from Design Module. No measurements, no stitch counts. Includes precision preference.

### Shape Manifest
From Planner. Component list (stage 1) then full manifest (stage 2): shape type and variant, physical dimensions, named typed edges with join slot references, instantiation count for symmetric components, handedness annotation, and all Join objects.

### Constraint Object (one per component)
From Fabric Module:
- `gauge`: stitches/inch, rows/inch
- `stitch_motif`: name, stitch repeat, row repeat
- `hard_constraints`: e.g. stitch count must be multiple of N
- `yarn_spec`: weight, fibre, needle size
- `physical_tolerance_mm`: derived from gauge base × ease multiplier × precision multiplier

### Component IR
From Stitch Fillers. Typed operation sequence. Parameterized (repeat intervals, not flattened). Handedness annotated. Construction-agnostic operations marked portable.

**Example operations:** `CAST_ON`, `INCREASE_SECTION`, `WORK_EVEN`, `SEPARATE`, `TAPER`, `BIND_OFF`

---

## Tolerance Mechanism

```
physical_tolerance_mm = gauge_base × ease_multiplier × precision_multiplier
```

- **gauge_base**: one stitch-width at component gauge (e.g. 5 sts/inch → ~5mm)
- **ease_multiplier**: 0.75× (negative ease) → 2.0× (high positive ease)
- **precision_multiplier**: high=0.75×, medium=1.0×, low=1.5×

**Stitch count selection process:**
1. Convert physical dimension to raw count at gauge
2. Find all counts satisfying pattern repeat and hard constraints
3. Filter to counts within tolerance band
4. Select closest to raw target; prefer larger on tie
5. If none found: escalate

**Escalation sequence:**
1. Widen by one step (+1 stitch-width); proceed with tolerance advisory if resolved
2. Check if failure is geometric in origin; if so route to Planner
3. Surface human-readable message in user terms (measurements, motif names — never stitch arithmetic)

---

## Shared Utilities
Implemented once, used by both Stitch Fillers and Algebraic Checker. Both must use identical implementations.

- **Unit Conversion**: physical dimensions ↔ stitch/row counts at gauge
- **Pattern Repeat Arithmetic**: divisibility checks, nearest valid count within tolerance
- **Tolerance Calculator**: derives physical_tolerance_mm from gauge + ease + precision preference
- **Shaping Rate Calculator**: given stitch delta and section depth, produces valid decrease/increase intervals

---

## Validation Sequence

```
1.  Planner emits component list                          → unblocks Fabric Module
2.  Planner completes shape manifest + Join objects
3.  Geometric Validator Phase 1 (compatibility + spatial)
4.  Fabric Module completes constraint objects             (concurrent with 2–3)
5.  Stitch Fillers run in parallel
6.  Algebraic Checker — intra-component validation
7.  Algebraic Checker — inter-component join validation
8.  Geometric Validator Phase 3 — final assembly check
9.  Writer renders pattern
```

---

## Failure Routing

| Failure type | Routes to |
|---|---|
| Algebraic — filler origin | Relevant Stitch Filler |
| Algebraic — geometric origin | Planner |
| Geometric (Phase 1 or 3) | Planner |
| Tolerance escalation step 1 | Continue with advisory |
| Tolerance escalation step 2 | Planner |
| Tolerance escalation step 3 | User-facing message |

---

## Build Order

1. **Lookup tables** — seeded for top-down sweater construction; startup cross-referencing validation
2. **Shared utilities** — unit conversion, repeat arithmetic, tolerance calculator, shaping rate calculator
3. **Schema definitions** — IR operation types, shape manifest + edge/join schema, constraint object schema
4. **Algebraic Checker** — simulation VM; validate against hand-authored IR corpus from existing published patterns
5. **Geometric Validator Phase 1** — edge-join compatibility and spatial validation, 3D mesh preview
6. **Stitch Fillers** — per-component; iterate against Algebraic Checker
7. **Planner** — shape manifests with typed edges and Join objects
8. **Fabric Module** — constraint objects with tolerance values
9. **Orchestrator** — DAG execution and retry routing
10. **Design Module** — proportion spec generation; full pipeline end-to-end test
11. **Writer** — IR to pattern prose; human knitter evaluation
12. **Geometric Validator Phase 2** — stitch-level mesh and interactive visualization

---

## Key Constraints and Invariants
- The Planner has no stitch awareness. It works in physical units only.
- The Fabric Module has no geometry awareness. It works from component types only.
- Stitch Fillers treat Join object parameters as read-only. They account for join-owned stitches but do not generate them.
- Stitch Fillers and the Algebraic Checker must use identical shared utility implementations for unit conversion and repeat arithmetic.
- The Compatibility Table key is ordered: (edge_type_A, edge_type_B) reflects join directionality and is not a commutative pair.
- Lookup tables are never written to at runtime.
- All tolerance values are in physical units (mm). Stitch count tolerances are always derived, never set directly.
- Failure messages surfaced to users must be expressed in user terms (measurements, motif names, garment size). Never expose internal stitch arithmetic in user-facing output.
