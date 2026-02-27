# Skyknit 2.0 — Vision

## The Problem

Garment manufacturing is structurally wasteful. The waste is not primarily behavioral — it is an artifact of how production is organized:

- **Patterns are sized to discrete buckets** that fit almost no one precisely. Designers grade patterns from a sample size to 8–12 fixed sizes, accepting fit error as inevitable. Knitters and manufacturers then produce garments that are returned, discarded, or never worn.
- **Production is forecast-driven.** Factories produce based on predicted demand by size. The prediction is almost always wrong in some direction. Unsold inventory is the industry's largest waste category.
- **Pattern engineering expertise is scarce and centralized.** Writing a well-constructed, mathematically correct knitting pattern is a specialized skill. It is expensive, not easily scaled, and inaccessible to small regional producers who have equipment but lack technical capacity.
- **Machine knitting is underutilized at small scale.** Semi-industrial and domestic knitting machines capable of high-quality production exist widely. The bottleneck is not hardware — it is pattern software. Existing machine knitting CAD tools are proprietary, expensive, machine-specific, and require significant training.

The result is a manufacturing system where production is distant, fit is approximate, waste is large, and small local producers cannot compete.

---

## The Vision

Skyknit 2.0 aims to be the software infrastructure layer that makes **localized, made-to-measure, on-demand knitwear manufacturing** economically viable.

The core proposition: if an AI agent can take body measurements, yarn specifications, and a design intent as inputs and produce a mathematically correct, construction-validated knitting pattern as output — for both hand knitting and machine knitting — then:

- Any producer with appropriate equipment can manufacture a garment to exact measurements
- Pattern engineering expertise is no longer a bottleneck
- Production can be triggered by a confirmed order, not a demand forecast
- Small regional producers become competitive with centralized factories

This is not incremental improvement to existing pattern generation tools. It is a different model of how garments are designed, specified, and made.

---

## Three Core Capabilities

### 1. Made-to-Measure Pattern Generation

The pipeline takes body measurements directly and generates patterns scaled to those exact measurements, rather than to a named size. This changes the economics of fit:

| Current model | Made-to-measure model |
|---|---|
| 8–12 fixed sizes per design | Continuous measurement space |
| Producer guesses size distribution | Each garment is ordered before production |
| Returns and unsold inventory are expected | No inventory risk; no fit-based returns |
| Pattern grading is manual, error-prone | Stitch math is computed, not approximated |

The `utilities` package — `conversion.py`, `repeats.py`, `tolerance.py`, `shaping.py` — is built precisely for this. Physical measurements become stitch counts through a validated pipeline that respects motif divisibility, tolerance bands, and shaping constraints. The pipeline runs identically for any measurement input; a "size ramp" is just running it N times.

### 2. Pattern Validation

The topology layer enables structural validation of knitting patterns: given any pattern (hand-authored, LLM-generated, or machine-generated), does it describe a structurally sound garment?

Validation catches:
- Incompatible edge-join pairs (e.g., picking up from a live-stitch edge without an intermediate bind-off)
- Stitch count arithmetic that does not balance across sections
- Missing joins (an underarm cast-on that is never rejoined)
- Construction ordering that is physically impossible

This is useful in two directions. Forward: validate generated patterns before they reach a knitter or machine. Backward: validate existing published patterns, which frequently contain construction errors that knitters discover mid-project. A structured input form — components, joins, stitch counts per section — is a practical near-term entry point before full pattern parsing is feasible.

### 3. Machine Knitting Output

Hand-knit pattern prose and machine control instructions share the same underlying topology. The `ComponentIR` operation sequence (`CAST_ON`, `INCREASE_SECTION`, `WORK_EVEN`, `DECREASE_SECTION`, `BIND_OFF`) is fabric-mode agnostic. Only the Writer layer differs.

Adding machine knitting output means:
- A `FabricMode` enum (`HAND` / `MACHINE`) threaded through the pipeline as a dispatch key
- Machine-specific template keys in `writer_dispatch.yaml`, keyed by `(join_type, fabric_mode)`
- Machine-specific join types and operations added to the YAML tables (`TRANSFER`, `CARRIAGE_PASS`)
- Output formats targeting specific machine families (Brother/Silver Reed DAK format as the most accessible starting point; Stoll and Shima Seiki as longer-term targets)

The topology, stitch count arithmetic, shaping mathematics, and validation are identical for both modes. The investment in the deterministic core is not duplicated.

---

## How the Current Architecture Enables This

The architecture was designed with this vision in mind, even when the initial scope is hand-knit sweater patterns.

**Strict separation of geometry, fabric, and construction** means each layer can be extended independently. Adding machine knitting does not require touching the Planner or Fabric Module — only the Writer and the YAML dispatch tables.

**Domain knowledge in versioned YAML tables** means extending the system for new construction methods, garment types, or fabric modes is additive. New edge types, join types, and compatibility entries are added to the tables; startup cross-reference validation enforces completeness automatically. No code change is required for data changes.

**Physical units throughout** means the stitch math is derived, not hardcoded. The same geometric description of a garment — expressed in millimeters — produces different stitch counts for different gauges, different machines, and different yarn weights. Made-to-measure is the natural output of a system that never stores a stitch count as a design parameter.

**The LLM/deterministic boundary is explicit.** LLM judgment handles what cannot be formalized: design intent, proportion aesthetics, construction strategy selection. Deterministic code handles what must be correct: stitch arithmetic, compatibility checking, tolerance calculation, shaping rates. This boundary makes the system auditable and correctable in ways that purely LLM-driven approaches are not.

---

## The Machine Knitting Extension

The differences between hand and machine knitting are largely in the Writer layer and the YarnSpec schema. The topology is largely shared.

| Layer | Hand knitting | Machine knitting |
|---|---|---|
| Edge types | `CAST_ON`, `LIVE_STITCH`, `BOUND_OFF`, `SELVEDGE`, `OPEN` | Same; add `TRANSFER_BED` |
| Join types | `CONTINUATION`, `HELD_STITCH`, `CAST_ON_JOIN`, `PICKUP`, `SEAM` | Same; add `TRANSFER`, `LATCH_TOOL` |
| Compatibility table | Unchanged | Add machine-specific entries |
| IR operations | `CAST_ON`, `WORK_EVEN`, `INCREASE_SECTION`, etc. | Same; add `CARRIAGE_PASS`, `NEEDLE_OUT` |
| Stitch arithmetic | `utilities` package | Identical — same package |
| YarnSpec | `needle_size_mm` | Replace with `tension_dial`, `machine_gauge` |
| Writer output | Natural language prose | Machine control file (DAK, SDS-ONE, etc.) |
| StitchMotif | Stitch repeats, row repeats | Same; extend vocabulary with tuck, slip, transfer |

The `FabricMode` enum propagates from the top of the pipeline — set at intake alongside yarn and measurement information — and is carried through `ConstraintObject` and `ComponentIR` to the Writer. No module below the Writer branches on it except to pass it forward.

---

## The Localization Opportunity

The supply chain compression this enables is most significant for small regional producers.

A small studio with a semi-industrial knitting machine, access to locally-sourced yarn, and a phone-based measurement capture tool can, with this system:

1. Accept a custom order with body measurements and design preferences
2. Generate a validated machine-specific pattern automatically
3. Produce a single garment on demand, without inventory

The infrastructure that currently makes this impossible — pattern engineering expertise, grading software, machine programming skill — is replaced by the agent. The remaining inputs (equipment, fiber, operator skill) are already present in many regional production contexts.

This mirrors the economics of other digital fabrication tools. CNC routers and laser cutters did not require regional woodworkers to become CAD engineers; accessible software did. The parallel for knitwear is not yet built.

**Regional fiber economies** are a secondary beneficiary. Locally-sourced wool, alpaca, and plant fibers have supply chains that exist but lack downstream demand because the manufacturing infrastructure to use them at small scale is weak. A system that can take a locally-produced yarn's gauge characteristics and generate a correct machine-ready pattern removes one of the barriers to that downstream demand.

---

## Roadmap

The build order in `IMPLEMENTATION_PLAN.md` delivers the hand-knit pipeline first. Each phase below builds on that foundation.

### Phase A — Hand-knit pipeline (current scope)
Complete the 12-step build order: Planner, Fabric Module, Stitch Fillers, Algebraic Checker, Geometric Validator, Orchestrator, Design Module, Writer. Validates the full pipeline end-to-end for top-down hand-knit sweaters.

### Phase B — Made-to-measure as default
Replace the size ramp with direct measurement input as the primary interface. Size ramp becomes a derived feature (run pipeline N times). Validate fit accuracy against real garments.

### Phase C — Pattern validation tool
Build structured input interface for existing patterns (components, joins, stitch counts). Run topology compatibility and algebraic checker against hand-authored patterns. Useful as standalone tool independently of generation.

### Phase D — FabricMode and machine knitting output
Add `FabricMode` enum. Extend YAML tables with machine-specific entries. Build Writer variant targeting Brother/Silver Reed DAK format. Validate against physical machine output.

### Phase E — Yarn database and regional sourcing
Replace generic `YarnSpec` with a structured yarn catalog. Include regional suppliers, fiber types, and measured gauge characteristics. Enable the pipeline to work backward from available yarn to pattern parameters.

### Phase F — Industrial machine formats
Extend Writer to target Stoll and Shima Seiki formats. These require deeper engagement with proprietary specifications but unlock professional-grade production.

### Phase G — Body measurement capture
Integrate phone-based photogrammetry or structured measurement guides for consumer-facing measurement capture. Closes the loop from order to production without manual measurement entry.

---

## Design Invariants That Support the Vision

These invariants from the current architecture are load-bearing for the larger vision and must be preserved as the system grows:

- **Physical units throughout.** Stitch counts are always derived from measurements at gauge. No stitch count is ever stored as a design parameter. This is what makes made-to-measure correct by construction.
- **The LLM/deterministic boundary is explicit and enforced.** Correctness properties (stitch arithmetic, compatibility, tolerance) live in deterministic code. Judgment properties (proportion, style, construction strategy) live in LLM modules. The boundary is not blurred as new capabilities are added.
- **Lookup tables are the extension point.** New construction methods, garment types, fabric modes, and join types are added to YAML tables, not to application code. This keeps the system auditable and the domain knowledge portable.
- **Failure messages are expressed in user terms.** Stitch arithmetic failures surface as measurement and motif language, never as internal counts. This applies equally to knitters and to machine operators reading error output.
- **The Algebraic Checker and Stitch Fillers use identical utility implementations.** Any future machine knitting utilities must follow the same constraint: one implementation, used by both the generator and the validator.
