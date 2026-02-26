"""Tests for schemas public API and exports."""

import types as builtin_types

import schemas


class TestPublicAPI:
    def test_all_names_importable(self):
        """Every name in __all__ is actually importable from schemas."""
        for name in schemas.__all__:
            assert hasattr(schemas, name), f"{name!r} in __all__ but not importable"

    def test_all_is_complete(self):
        """__all__ must contain every public non-submodule name."""
        submodules = {
            name
            for name in dir(schemas)
            if isinstance(getattr(schemas, name), builtin_types.ModuleType)
        }
        public_names = {
            name for name in dir(schemas) if not name.startswith("_") and name not in submodules
        }
        all_set = set(schemas.__all__)
        missing = public_names - all_set
        assert not missing, f"Public names missing from schemas.__all__: {missing}"

    def test_proportion_types_importable(self):
        from schemas import PrecisionPreference, ProportionSpec

        spec = ProportionSpec(ratios={"a": 0.5}, precision=PrecisionPreference.MEDIUM)
        assert spec.precision is PrecisionPreference.MEDIUM

    def test_constraint_types_importable(self):
        from schemas import ConstraintObject, StitchMotif, YarnSpec
        from utilities.types import Gauge

        g = Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)
        m = StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1)
        y = YarnSpec(weight="worsted", fiber="wool", needle_size_mm=5.0)
        co = ConstraintObject(
            gauge=g,
            stitch_motif=m,
            hard_constraints=(),
            yarn_spec=y,
            physical_tolerance_mm=5.08,
        )
        assert co.gauge is g

    def test_manifest_types_importable(self):
        from schemas import ComponentSpec, Handedness, ShapeManifest, ShapeType
        from topology.types import Edge, EdgeType

        e = Edge(name="top", edge_type=EdgeType.LIVE_STITCH)
        comp = ComponentSpec(
            name="body",
            shape_type=ShapeType.CYLINDER,
            dimensions={"circumference_mm": 1000.0},
            edges=(e,),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        manifest = ShapeManifest(components=(comp,), joins=())
        assert len(manifest.components) == 1

    def test_ir_types_importable(self):
        from schemas import ComponentIR, Handedness, Operation, OpType

        op = Operation(
            op_type=OpType.CAST_ON,
            parameters={"cast_on_count": 100},
            stitch_count_after=100,
        )
        ir = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(op,),
            starting_stitch_count=100,
            ending_stitch_count=100,
        )
        assert ir.starting_stitch_count == 100

    def test_handedness_importable_from_schemas(self):
        """Handedness is defined in manifest.py but re-exported from schemas root."""
        from schemas import Handedness

        assert Handedness.LEFT.value == "LEFT"
        assert Handedness.RIGHT.value == "RIGHT"
        assert Handedness.NONE.value == "NONE"
