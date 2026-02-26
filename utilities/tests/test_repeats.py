"""Tests for pattern repeat arithmetic."""

import pytest

from utilities.repeats import find_valid_counts, select_stitch_count


class TestFindValidCounts:
    def test_simple_exact_match(self):
        """Target 100, tolerance 3, repeat 4 → 100 is divisible by 4."""
        result = find_valid_counts(100.0, 3.0, 4)
        assert 100 in result

    def test_multiple_valid_counts(self):
        """Target 100, tolerance 5, repeat 4 → [96, 100, 104]."""
        result = find_valid_counts(100.0, 5.0, 4)
        assert result == [96, 100, 104]

    def test_no_valid_counts(self):
        """Target 101, tolerance 0.5, repeat 4 → no multiples of 4 in [100.5, 101.5]."""
        result = find_valid_counts(101.0, 0.5, 4)
        assert result == []

    def test_hard_constraint_filtering(self):
        """Must also be divisible by 6. LCM(4, 6) = 12."""
        result = find_valid_counts(100.0, 10.0, 4, hard_constraints=[6])
        # Range [90, 110], multiples of 12: 96, 108
        assert result == [96, 108]

    def test_repeat_of_one(self):
        """Repeat 1 means any integer is valid."""
        result = find_valid_counts(50.0, 2.0, 1)
        assert result == [48, 49, 50, 51, 52]

    def test_tolerance_zero_exact_integer_match(self):
        """Tolerance 0 with integer target that satisfies repeat."""
        result = find_valid_counts(100.0, 0.0, 4)
        assert result == [100]

    def test_tolerance_zero_non_integer_target(self):
        """Tolerance 0 with non-integer target → empty (no integer in [50.5, 50.5])."""
        result = find_valid_counts(50.5, 0.0, 1)
        assert result == []

    def test_tolerance_zero_not_divisible(self):
        """Tolerance 0, target is integer but not divisible by repeat."""
        result = find_valid_counts(101.0, 0.0, 4)
        assert result == []

    def test_result_is_sorted(self):
        result = find_valid_counts(100.0, 20.0, 8)
        assert result == sorted(result)

    def test_single_valid_count(self):
        """Narrow band with exactly one valid count."""
        result = find_valid_counts(100.0, 1.0, 4)
        assert result == [100]

    def test_multiple_hard_constraints(self):
        """Multiple hard constraints: must be divisible by 4, 6, and 5. LCM = 60."""
        result = find_valid_counts(100.0, 25.0, 4, hard_constraints=[6, 5])
        # Range [75, 125], multiples of 60: 60, 120
        assert result == [120]

    def test_rejects_zero_stitch_repeat(self):
        with pytest.raises(ValueError, match="stitch_repeat must be >= 1"):
            find_valid_counts(100.0, 5.0, 0)

    def test_rejects_negative_tolerance(self):
        with pytest.raises(ValueError, match="tolerance_stitches must be >= 0"):
            find_valid_counts(100.0, -1.0, 4)

    def test_rejects_invalid_hard_constraint(self):
        with pytest.raises(ValueError, match="hard_constraints values must be >= 1"):
            find_valid_counts(100.0, 5.0, 4, hard_constraints=[0])

    def test_returned_list_is_independent_copy(self):
        """Mutating returned list does not affect subsequent calls."""
        r1 = find_valid_counts(100.0, 5.0, 4)
        r1.clear()
        r2 = find_valid_counts(100.0, 5.0, 4)
        assert len(r2) > 0

    def test_low_target_near_zero(self):
        """Counts must be positive even if tolerance band extends below zero."""
        result = find_valid_counts(2.0, 5.0, 3)
        # Range [-3, 7], multiples of 3 > 0: 3, 6
        assert result == [3, 6]


class TestSelectStitchCount:
    def test_selects_closest_to_target(self):
        """Target 101, tolerance 5, repeat 4 → valid [100, 104], closest is 100."""
        result = select_stitch_count(101.0, 5.0, 4)
        assert result == 100

    def test_selects_exact_match(self):
        """Target 100, tolerance 5, repeat 4 → valid [96, 100, 104], exact match 100."""
        result = select_stitch_count(100.0, 5.0, 4)
        assert result == 100

    def test_tie_breaking_prefers_larger(self):
        """Target 98, tolerance 5, repeat 4 → valid [96, 100], equidistant → picks 100."""
        result = select_stitch_count(98.0, 5.0, 4)
        assert result == 100

    def test_returns_none_when_no_valid_counts(self):
        """No valid counts → None (escalation signal)."""
        result = select_stitch_count(101.0, 0.5, 4)
        assert result is None

    def test_tolerance_zero_exact_match(self):
        result = select_stitch_count(100.0, 0.0, 4)
        assert result == 100

    def test_tolerance_zero_no_match(self):
        result = select_stitch_count(101.0, 0.0, 4)
        assert result is None

    def test_with_hard_constraints(self):
        """Target 100, tolerance 10, repeat 4, must be div by 6. LCM=12. Valid: [96, 108]."""
        result = select_stitch_count(100.0, 10.0, 4, hard_constraints=[6])
        assert result == 96  # 96 is closer to 100 than 108

    def test_selects_closer_above_target(self):
        """Target 99, tolerance 5, repeat 4 → valid [96, 100, 104], 100 is closest."""
        result = select_stitch_count(99.0, 5.0, 4)
        assert result == 100

    def test_single_valid_count(self):
        result = select_stitch_count(100.0, 1.0, 4)
        assert result == 100
