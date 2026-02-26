"""Tests for pattern repeat arithmetic."""

import pytest

from utilities.repeats import find_valid_counts


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
