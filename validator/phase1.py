"""
Geometric Validator Phase 1 pipeline.

validate_phase1 runs both Phase 1 checks in sequence:
  1. Edge-join compatibility (topology registry lookup)
  2. Spatial coherence (referential integrity)

All errors from both passes are collected and returned in a ValidationResult.
"""

from __future__ import annotations

from dataclasses import dataclass

from schemas.manifest import ShapeManifest
from validator.compatibility import ValidationError, validate_edge_join_compatibility
from validator.spatial import validate_spatial_coherence


@dataclass(frozen=True)
class ValidationResult:
    """Aggregate outcome of the Phase 1 Geometric Validator."""

    passed: bool
    errors: tuple[ValidationError, ...]


def validate_phase1(manifest: ShapeManifest) -> ValidationResult:
    """
    Run all Phase 1 geometric validation checks over *manifest*.

    Collects errors from both the compatibility check and the spatial
    coherence check before returning, so callers see all problems at once.

    Returns ``ValidationResult(passed=True, errors=())`` when the manifest
    is fully valid.
    """
    errors: list[ValidationError] = []
    errors.extend(validate_edge_join_compatibility(manifest))
    errors.extend(validate_spatial_coherence(manifest))

    # Warnings do not cause a failure — only "error" severity does
    failed = any(e.severity == "error" for e in errors)

    return ValidationResult(
        passed=not failed,
        errors=tuple(errors),
    )
