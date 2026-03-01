"""Tests for the shaping rate calculator."""

import pytest

from skyknit.utilities.shaping import ShapingAction, ShapingInterval, calculate_shaping_intervals


class TestShapingAction:
    def test_values(self):
        assert ShapingAction.INCREASE.value == "increase"
        assert ShapingAction.DECREASE.value == "decrease"

    def test_is_str(self):
        """ShapingAction inherits from str for serialization compatibility."""
        assert isinstance(ShapingAction.INCREASE, str)
        assert isinstance(ShapingAction.DECREASE, str)


class TestShapingInterval:
    def test_is_frozen(self):
        si = ShapingInterval(
            action=ShapingAction.DECREASE, every_n_rows=4, times=10, stitches_per_action=2
        )
        with pytest.raises(AttributeError):
            si.times = 5  # type: ignore[misc]

    def test_fields(self):
        si = ShapingInterval(
            action=ShapingAction.INCREASE, every_n_rows=3, times=5, stitches_per_action=2
        )
        assert si.action == ShapingAction.INCREASE
        assert si.every_n_rows == 3
        assert si.times == 5
        assert si.stitches_per_action == 2


class TestCalculateShapingIntervals:
    def test_zero_delta_returns_empty(self):
        assert calculate_shaping_intervals(0, 40) == []

    def test_even_decrease(self):
        """Delta -20, depth 40, 2 sts/action → 10 actions every 4 rows."""
        result = calculate_shaping_intervals(-20, 40)
        assert len(result) == 1
        assert result[0] == ShapingInterval(
            ShapingAction.DECREASE, every_n_rows=4, times=10, stitches_per_action=2
        )

    def test_even_increase(self):
        """Delta +20, depth 40, 2 sts/action → 10 actions every 4 rows."""
        result = calculate_shaping_intervals(20, 40)
        assert len(result) == 1
        assert result[0].action == ShapingAction.INCREASE
        assert result[0].every_n_rows == 4
        assert result[0].times == 10

    def test_uneven_produces_two_intervals(self):
        """Delta -20, depth 43 → 10 actions in 43 rows. 43/10 = 4 rem 3.
        7 actions every 4 rows + 3 actions every 5 rows."""
        result = calculate_shaping_intervals(-20, 43)
        assert len(result) == 2
        assert result[0] == ShapingInterval(
            ShapingAction.DECREASE, every_n_rows=4, times=7, stitches_per_action=2
        )
        assert result[1] == ShapingInterval(
            ShapingAction.DECREASE, every_n_rows=5, times=3, stitches_per_action=2
        )

    def test_uneven_invariant_total_delta(self):
        """Sum of stitches_per_action * times across intervals == abs(stitch_delta)."""
        result = calculate_shaping_intervals(-20, 43)
        total_stitches = sum(i.stitches_per_action * i.times for i in result)
        assert total_stitches == 20

    def test_uneven_invariant_total_rows(self):
        """Sum of every_n_rows * times across intervals == section_depth_rows."""
        result = calculate_shaping_intervals(-20, 43)
        total_rows = sum(i.every_n_rows * i.times for i in result)
        assert total_rows == 43

    def test_even_invariant_total_delta(self):
        result = calculate_shaping_intervals(-20, 40)
        total_stitches = sum(i.stitches_per_action * i.times for i in result)
        assert total_stitches == 20

    def test_even_invariant_total_rows(self):
        result = calculate_shaping_intervals(-20, 40)
        total_rows = sum(i.every_n_rows * i.times for i in result)
        assert total_rows == 40

    def test_single_action(self):
        """Delta -2, depth 10 → 1 action every 10 rows."""
        result = calculate_shaping_intervals(-2, 10)
        assert len(result) == 1
        assert result[0].every_n_rows == 10
        assert result[0].times == 1

    def test_every_row_shaping(self):
        """Delta -20, depth 10 → 10 actions every 1 row."""
        result = calculate_shaping_intervals(-20, 10)
        assert len(result) == 1
        assert result[0].every_n_rows == 1
        assert result[0].times == 10

    def test_custom_stitches_per_action(self):
        """Delta -30, depth 30, 3 sts/action → 10 actions every 3 rows."""
        result = calculate_shaping_intervals(-30, 30, stitches_per_action=3)
        assert len(result) == 1
        assert result[0].stitches_per_action == 3
        assert result[0].times == 10

    def test_positive_delta_labels_increase(self):
        result = calculate_shaping_intervals(10, 20)
        for interval in result:
            assert interval.action is ShapingAction.INCREASE

    def test_negative_delta_labels_decrease(self):
        result = calculate_shaping_intervals(-10, 20)
        for interval in result:
            assert interval.action is ShapingAction.DECREASE

    def test_rejects_zero_section_depth(self):
        with pytest.raises(ValueError, match="section_depth_rows must be >= 1"):
            calculate_shaping_intervals(-20, 0)

    def test_rejects_negative_section_depth(self):
        with pytest.raises(ValueError, match="section_depth_rows must be >= 1"):
            calculate_shaping_intervals(-20, -5)

    def test_rejects_zero_stitches_per_action(self):
        with pytest.raises(ValueError, match="stitches_per_action must be >= 1"):
            calculate_shaping_intervals(-20, 40, stitches_per_action=0)

    def test_rejects_not_enough_rows(self):
        """More actions needed than rows available."""
        with pytest.raises(ValueError, match="Not enough rows"):
            calculate_shaping_intervals(-20, 5)  # 10 actions in 5 rows

    def test_rejects_non_divisible_delta(self):
        """Delta not divisible by stitches_per_action."""
        with pytest.raises(ValueError, match="must be divisible by"):
            calculate_shaping_intervals(-7, 40, stitches_per_action=2)

    def test_rejects_delta_smaller_than_stitches_per_action(self):
        """Delta of 1 with stitches_per_action=2 fails divisibility."""
        with pytest.raises(ValueError, match="must be divisible by"):
            calculate_shaping_intervals(-1, 10, stitches_per_action=2)

    def test_stitches_per_action_equals_delta(self):
        """Delta equals stitches_per_action → single action."""
        result = calculate_shaping_intervals(-4, 10, stitches_per_action=4)
        assert len(result) == 1
        assert result[0].times == 1
        assert result[0].every_n_rows == 10
        assert result[0].stitches_per_action == 4

    @pytest.mark.parametrize(
        "delta, depth",
        [
            (-20, 40),
            (-20, 43),
            (-30, 45),
            (16, 32),
            (10, 17),
            (-6, 21),
        ],
    )
    def test_invariants_parametrized(self, delta, depth):
        """Verify row and stitch invariants hold for various inputs."""
        result = calculate_shaping_intervals(delta, depth)
        total_stitches = sum(i.stitches_per_action * i.times for i in result)
        total_rows = sum(i.every_n_rows * i.times for i in result)
        assert total_stitches == abs(delta)
        assert total_rows == depth
