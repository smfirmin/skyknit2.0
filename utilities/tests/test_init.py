"""Tests for utilities public API and exports."""

import utilities


class TestPublicAPI:
    def test_all_names_importable(self):
        """Every name in __all__ is actually importable from the package."""
        for name in utilities.__all__:
            assert hasattr(utilities, name), f"{name!r} in __all__ but not importable"

    def test_all_is_complete(self):
        """__all__ contains every public name defined in the package __init__.

        Submodule names (exposed by dir() when submodules are imported) are
        excluded — only callable/type exports belong in __all__.
        """
        import types as builtin_types

        submodules = {
            name
            for name in dir(utilities)
            if isinstance(getattr(utilities, name), builtin_types.ModuleType)
        }
        public_names = {
            name for name in dir(utilities) if not name.startswith("_") and name not in submodules
        }
        all_set = set(utilities.__all__)
        missing = public_names - all_set
        assert not missing, f"Public names missing from __all__: {missing}"

    def test_gauge_importable(self):
        from utilities import Gauge

        g = Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)
        assert g.stitches_per_inch == 5.0

    def test_precision_level_importable(self):
        from utilities import PrecisionLevel

        assert PrecisionLevel.MEDIUM == 1.0

    def test_shaping_action_importable(self):
        from utilities import ShapingAction

        assert ShapingAction.INCREASE.value == "increase"
        assert ShapingAction.DECREASE.value == "decrease"

    def test_shaping_interval_importable(self):
        from utilities import ShapingAction, ShapingInterval

        si = ShapingInterval(
            ShapingAction.DECREASE, every_n_rows=4, times=10, stitches_per_action=2
        )
        assert si.action is ShapingAction.DECREASE

    def test_conversion_functions_importable(self):
        from utilities import inches_to_mm, mm_to_inches

        assert inches_to_mm(1.0) == 25.4
        assert mm_to_inches(25.4) == 1.0

    def test_tolerance_functions_importable(self):
        from utilities import Gauge, PrecisionLevel, calculate_tolerance_mm

        g = Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)
        t = calculate_tolerance_mm(g, 1.0, PrecisionLevel.MEDIUM)
        assert t > 0

    def test_repeat_functions_importable(self):
        from utilities import find_valid_counts, select_stitch_count

        counts = find_valid_counts(100.0, 5.0, 4)
        assert len(counts) > 0
        selected = select_stitch_count(100.0, 5.0, 4)
        assert selected is not None

    def test_pipeline_function_importable(self):
        from utilities import Gauge, select_stitch_count_from_physical

        g = Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)
        result = select_stitch_count_from_physical(203.2, g, 15.24, 4)
        assert result is not None

    def test_shaping_function_importable(self):
        from utilities import calculate_shaping_intervals

        result = calculate_shaping_intervals(-20, 40)
        assert len(result) == 1
