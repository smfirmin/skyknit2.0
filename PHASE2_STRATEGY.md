# Phase 2 Implementation Strategy — Shared Utilities

## Overview

Phase 2 builds the deterministic utility layer that all downstream modules depend on.
It produces a self-contained `utilities/` package with zero LLM involvement: pure
functions and frozen dataclasses that convert between physical and stitch-count
domains, calculate tolerance, select valid stitch counts, and distribute shaping
evenly.

**Critical design constraint:** Stitch Fillers (Phase 6) and the Algebraic Checker
(Phase 4) must call *identical* implementations. Phase 2 is where that shared code
lives. Getting these functions wrong — or making them subtly inconsistent — would
cause silent divergence that surfaces only at integration time.

---

## What Phase 2 Delivers

| Module | Purpose | Consumed by |
|--------|---------|-------------|
| `utilities/types.py` | `Gauge` frozen dataclass | Every downstream module |
| `utilities/conversion.py` | inches <-> mm, physical <-> stitch/row counts | Fillers, Checker, Fabric Module |
| `utilities/tolerance.py` | `PrecisionLevel` enum, tolerance calculator | Fabric Module, Checker |
| `utilities/repeats.py` | Pattern repeat validation + stitch count selection | Fillers, Checker |
| `utilities/shaping.py` | `ShapingInterval` dataclass, shaping rate calculator | Fillers, Checker |
| `utilities/__init__.py` | Public API with `__all__` | All consumers |

---

## Implementation Order and Rationale

The plan specifies 8 sub-steps (2.1–2.8). The dependency graph is:

```
2.1 Gauge dataclass
 |
 +-- 2.2 Unit conversion (needs Gauge)
 |    |
 |    +-- 2.6 Full pipeline (needs conversion + selection)
 |
 +-- 2.3 Tolerance calculator (needs Gauge)
 |
 +-- 2.4 Valid count enumeration (pure arithmetic, no Gauge needed)
 |    |
 |    +-- 2.5 Stitch count selection (needs 2.4)
 |         |
 |         +-- 2.6 Full pipeline (needs 2.2 + 2.5)
 |
 +-- 2.7 Shaping rate calculator (independent of repeats/tolerance)
 |
 +-- 2.8 Public API exports (after all modules exist)
```

**Proposed execution order:** 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6 → 2.7 → 2.8

This matches the plan's order exactly, which is already topologically sorted. Each
step leaves CI green before the next begins.

Steps 2.3, 2.4, and 2.7 are technically independent of each other (only needing 2.1),
but sequential execution keeps the commit history clean and reviewable.

---

## Design Decisions

### 1. Mirror Phase 1 patterns exactly

Phase 1 established clear conventions. Phase 2 must follow them:

- **Frozen dataclasses** for `Gauge` and `ShapingInterval` — consistent with
  `EdgeTypeEntry`, `JoinTypeEntry`, etc.
- **`__post_init__` validation** with `ValueError` for invalid inputs (zero/negative
  gauge, out-of-range ease multiplier) — fail fast, not lazy.
- **Enums for domain vocabulary** — `PrecisionLevel` as a `float`-valued enum, not
  raw floats passed around.
- **Pure functions** — no side effects, no state. Every function in `conversion.py`,
  `tolerance.py`, `repeats.py`, `shaping.py` is a pure mapping from inputs to outputs.
- **No MappingProxyType needed** here since we return primitives (`float`, `int`,
  `list[int]`, `list[ShapingInterval]`), not dicts that could be mutated.

### 2. Tolerance is always physical (mm)

The architecture mandates: *"Tolerance is expressed in physical units (mm), derived
from gauge, ease, and precision preference."* The `tolerance.py` module computes mm.
The `repeats.py` module's `select_stitch_count_from_physical` converts the mm
tolerance to a stitch tolerance internally — callers never handle stitch tolerances
directly.

### 3. Conversion constant: 25.4 mm/inch

A single constant `MM_PER_INCH = 25.4` defined once in `conversion.py` and used
everywhere. No magic numbers scattered across modules.

### 4. `find_valid_counts` returns a sorted list; `select_stitch_count` picks from it

This two-level API matters because the Algebraic Checker needs the *set of valid
counts* (to verify the Filler picked one), while the Stitch Filler just needs the
*selected count*. Splitting the logic allows both uses without duplication.

### 5. Shaping intervals handle the "uneven distribution" case

Real knitting patterns often can't distribute shaping perfectly evenly.
`calculate_shaping_intervals` must return *two* intervals when the division is
uneven (e.g., "decrease every 4th row 7 times, then every 3rd row 3 times"). This
is a common knitting pattern convention and gets it right from the start rather than
assuming even division.

### 6. Return `None` for unresolvable stitch counts, not exceptions

When `select_stitch_count` finds no valid count in the tolerance band, it returns
`None`. The caller (Filler or Orchestrator) decides whether to escalate. Phase 2
does *not* implement escalation logic — that lives in the Orchestrator (Phase 9).

---

## Testing Strategy

### Pattern: mirror Phase 1 test conventions

- **Module-scoped fixtures** where applicable (no registry to share here, but
  `Gauge` instances used across tests should be fixtures).
- **Parametrized tests** for the combinatorial cases (multiple gauges, repeat
  values, constraint combinations).
- **`tmp_path` not needed** — no file I/O in utilities.
- **Mutation-proof assertions** — verify returned lists are independent copies.
- **Round-trip property tests** for conversion functions: `stitch→physical→stitch ≈ original`.

### Test cases per step

**2.1 — Gauge dataclass:**
- Construction with valid values
- Frozen (immutable) — assignment raises `FrozenInstanceError`
- Zero `stitches_per_inch` raises `ValueError`
- Negative `rows_per_inch` raises `ValueError`
- Equality and hashing work (frozen dataclass gives this for free)

**2.2 — Unit conversion:**
- `inches_to_mm(1.0) == 25.4`
- `mm_to_inches(25.4) == 1.0`
- Round-trip: `mm_to_inches(inches_to_mm(x)) ≈ x` for several values
- `physical_to_stitch_count(25.4, Gauge(5, 5)) == 5.0`
- `physical_to_row_count(25.4, Gauge(5, 5)) == 5.0`
- Round-trip: `stitch_count_to_physical(physical_to_stitch_count(d, g), g) ≈ d`
- Zero dimension → zero count
- Large values don't overflow or lose precision

**2.3 — Tolerance calculator:**
- Known value: 5 sts/inch, ease=1.0, MEDIUM → `25.4/5 * 1.0 * 1.0 = 5.08 mm`
- HIGH precision < MEDIUM < LOW for same gauge/ease
- Ease multiplier scales linearly
- Rejects ease_multiplier outside `[0.75, 2.0]`
- `gauge_base_mm` matches `25.4 / stitches_per_inch`

**2.4 — Valid count enumeration:**
- Target 100, tolerance 3, repeat 4 → `[100]`
- Target 100, tolerance 5, repeat 4 → `[96, 100, 104]`
- No valid counts → empty list
- Hard constraint: must also divide by 6
- Repeat of 1 → every integer in range
- Tolerance of 0 → only exact match (if valid)
- Result is always sorted ascending

**2.5 — Stitch count selection:**
- Selects closest to target
- Tie-breaking: prefers larger (rounds up — typical knitting convention)
- Returns `None` when no valid counts
- With tolerance=0 and exact match
- Delegates correctly to `find_valid_counts`

**2.6 — Full pipeline:**
- End-to-end: 254mm (10") at 5 sts/inch, repeat 4, tolerance 5.08mm → valid count
- Confirms conversion + selection compose correctly
- Import path test: verify Fillers and Checker can import the same function

**2.7 — Shaping rate calculator:**
- Even: delta -20, depth 40, 2 sts/action → decrease every 4 rows, 10 times
- Uneven: produces two `ShapingInterval` objects
- Zero delta → empty list
- Positive delta → "increase" action
- Negative delta → "decrease" action
- More shaping than rows allow → single-row intervals or error

**2.8 — Public API:**
- Every public name importable from `utilities`
- `__all__` is complete and matches actual exports

---

## Risks and Mitigations

### 1. Floating-point precision in conversions

**Risk:** Round-trip `physical → stitch → physical` accumulates error. Downstream
modules may compare counts expecting exactness.

**Mitigation:** All intermediate stitch counts are `float` until the final selection
step, which produces `int`. Tests use `pytest.approx()` for floating-point
comparisons. Document that raw counts are non-integer and only the final selected
count is integer.

### 2. Edge case in repeat arithmetic with tolerance = 0

**Risk:** When tolerance is exactly 0 and the raw target is not an integer, there
are zero valid counts (since `find_valid_counts` only returns integers).

**Mitigation:** Explicitly test this case. The function correctly returns an empty
list, and `select_stitch_count` returns `None`, triggering escalation upstream.

### 3. Uneven shaping distribution correctness

**Risk:** The two-interval approach for uneven shaping (e.g., "every 4th row 7
times, then every 3rd row 3 times") must sum exactly to the total delta and total
depth. Off-by-one errors here produce garments that are the wrong size.

**Mitigation:** Add an invariant assertion in every shaping test:
`sum(interval.every_n_rows * interval.times for i in intervals) == section_depth_rows`
and `sum(interval.stitches_per_action * interval.times for i in intervals) == abs(stitch_delta)`.
This is a hard correctness constraint.

### 4. `pyproject.toml` configuration drift

**Risk:** Forgetting to add `utilities/tests` to `testpaths` or `utilities` to
`known-first-party` means tests don't run or imports get flagged by ruff.

**Mitigation:** Step 2.1 updates `pyproject.toml` *first*, before writing any code.
Step 2.8 includes an import-path test that would catch configuration issues.

### 5. mypy strict mode on a new package

**Risk:** Utilities package needs its own `[[tool.mypy.overrides]]` for tests
(matching the topology pattern of exempting tests from `disallow_untyped_defs`).

**Mitigation:** Add the mypy override in step 2.1 alongside the pytest/ruff config.

---

## Configuration Changes (Step 2.1)

The following `pyproject.toml` changes are required at the start:

```toml
# pytest
testpaths = ["topology/tests", "utilities/tests"]

# ruff isort
known-first-party = ["topology", "utilities"]

# mypy — new override for utilities tests
[[tool.mypy.overrides]]
module = "utilities.tests.*"
disallow_untyped_defs = false
```

---

## File Layout After Phase 2

```
utilities/
  __init__.py          # Public API, __all__
  types.py             # Gauge frozen dataclass
  conversion.py        # inches<->mm, physical<->stitch/row
  tolerance.py         # PrecisionLevel enum, calculate_tolerance_mm
  repeats.py           # find_valid_counts, select_stitch_count, select_stitch_count_from_physical
  shaping.py           # ShapingInterval dataclass, calculate_shaping_intervals
  tests/
    __init__.py
    test_types.py      # Gauge tests
    test_conversion.py # Unit conversion tests
    test_tolerance.py  # Tolerance calculator tests
    test_repeats.py    # Pattern repeat + selection tests
    test_shaping.py    # Shaping rate calculator tests
    test_init.py       # Public API / __all__ completeness tests
```

---

## Commit Strategy

One commit per step (2.1 through 2.8), each leaving CI green:

1. `Add utilities package scaffold with Gauge dataclass`
2. `Add unit conversion functions (inches/mm, physical/stitch)`
3. `Add tolerance calculator with PrecisionLevel enum`
4. `Add pattern repeat valid count enumeration`
5. `Add stitch count selection with tie-breaking`
6. `Add full physical-to-stitch-count pipeline`
7. `Add shaping rate calculator with ShapingInterval`
8. `Add utilities public API exports and completeness tests`

---

## Downstream Impact

Phase 2 unblocks:

- **Phase 3 (Schemas):** `ConstraintObject` references `Gauge` from `utilities.types`
- **Phase 4 (Algebraic Checker):** Uses `conversion`, `repeats` for join validation
- **Phase 6 (Stitch Fillers):** Uses all utilities — conversion, tolerance, repeats, shaping
- **Phase 8 (Fabric Module):** Uses `tolerance.calculate_tolerance_mm` to produce
  `physical_tolerance_mm` in constraint objects

No downstream module can begin meaningful implementation without Phase 2's types and
functions. This makes Phase 2 the critical path for the entire project.
