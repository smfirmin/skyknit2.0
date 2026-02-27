"""Tests for schemas public API — all public names importable from schemas."""

import schemas


class TestPublicAPI:
    def test_all_defined(self):
        assert hasattr(schemas, "__all__")

    def test_all_names_importable(self):
        """Every name in __all__ is actually importable from the package."""
        for name in schemas.__all__:
            assert hasattr(schemas, name), f"{name!r} in __all__ but not importable"

    def test_proportion_types_importable(self):
        from types import MappingProxyType

        from schemas import PrecisionPreference, ProportionSpec

        spec = ProportionSpec(
            ratios=MappingProxyType({"body_length": 0.6}),
            precision=PrecisionPreference.MEDIUM,
        )
        assert spec.precision == PrecisionPreference.MEDIUM

    def test_constraint_types_importable(self):
        from schemas import ConstraintObject, StitchMotif, YarnSpec
        from utilities import Gauge

        motif = StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1)
        assert motif.stitch_repeat == 1
        yarn = YarnSpec(weight="DK", fiber="wool", needle_size_mm=3.75)
        assert yarn.weight == "DK"
        obj = ConstraintObject(
            gauge=Gauge(stitches_per_inch=5.0, rows_per_inch=7.0),
            stitch_motif=motif,
            hard_constraints=(),
            yarn_spec=yarn,
            physical_tolerance_mm=5.08,
        )
        assert obj.physical_tolerance_mm == 5.08

    def test_manifest_types_importable(self):
        from schemas import ComponentSpec, Handedness, ShapeManifest, ShapeType
        from topology.types import Edge, EdgeType

        spec = ComponentSpec(
            name="body",
            shape_type=ShapeType.CYLINDER,
            dimensions={"circumference_mm": 914.4},
            edges=(Edge(name="top", edge_type=EdgeType.LIVE_STITCH),),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        manifest = ShapeManifest(components=(spec,), joins=())
        assert len(manifest.components) == 1

    def test_ir_types_importable(self):
        from schemas import ComponentIR, Handedness, Operation, OpType

        op = Operation(
            op_type=OpType.CAST_ON,
            parameters={"count": 80},
            row_count=None,
            stitch_count_after=80,
        )
        ir = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(op,),
            starting_stitch_count=80,
            ending_stitch_count=80,
        )
        assert ir.starting_stitch_count == 80

    def test_ir_factories_importable(self):
        from schemas import make_bind_off, make_cast_on, make_work_even

        cast = make_cast_on(80)
        even = make_work_even(row_count=10, stitch_count=80)
        bind = make_bind_off(80)
        assert cast.op_type.value == "CAST_ON"
        assert even.row_count == 10
        assert bind.stitch_count_after == 0

    def test_all_names_in_all(self):
        expected = {
            "PrecisionPreference",
            "ProportionSpec",
            "StitchMotif",
            "YarnSpec",
            "ConstraintObject",
            "ShapeType",
            "Handedness",
            "ComponentSpec",
            "ShapeManifest",
            "OpType",
            "Operation",
            "ComponentIR",
            "make_cast_on",
            "make_work_even",
            "make_bind_off",
        }
        assert expected.issubset(set(schemas.__all__))
