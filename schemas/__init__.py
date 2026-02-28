"""
Schema definitions for Skyknit 2.0 data contracts.

Provides the shared data structures (IR operations, shape manifest, constraint
object, proportion spec) that flow between architectural modules.
"""

from .constraint import ConstraintObject, StitchMotif, YarnSpec
from .garment import (
    ComponentBlueprint,
    DimensionRule,
    EdgeSpec,
    GarmentSpec,
    JoinSpec,
)
from .ir import (
    ComponentIR,
    Operation,
    OpType,
    make_bind_off,
    make_cast_on,
    make_work_even,
)
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
    "make_cast_on",
    "make_work_even",
    "make_bind_off",
    # garment
    "EdgeSpec",
    "DimensionRule",
    "ComponentBlueprint",
    "JoinSpec",
    "GarmentSpec",
]
