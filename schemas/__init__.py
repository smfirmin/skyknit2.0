"""
Schemas package: data contracts for all module boundaries.

Exports all public types from proportion, constraint, manifest, and ir
sub-modules. Downstream packages import from `schemas` directly.
"""

from .constraint import ConstraintObject, StitchMotif, YarnSpec
from .ir import ComponentIR, Operation, OpType
from .manifest import ComponentSpec, Handedness, ShapeManifest, ShapeType
from .proportion import PrecisionPreference, ProportionSpec

__all__ = [
    # proportion
    "PrecisionPreference",
    "ProportionSpec",
    # constraint
    "StitchMotif",
    "YarnSpec",
    "ConstraintObject",
    # manifest
    "ShapeType",
    "Handedness",
    "ComponentSpec",
    "ShapeManifest",
    # ir
    "OpType",
    "Operation",
    "ComponentIR",
]
