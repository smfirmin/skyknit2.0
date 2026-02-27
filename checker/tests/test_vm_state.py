"""Tests for checker.vm_state — VMState dataclass."""

import pytest

from checker.vm_state import VMState


class TestVMStateConstruction:
    def test_default_values(self):
        state = VMState()
        assert state.live_stitch_count == 0
        assert state.held_stitches == {}
        assert state.row_counter == 0
        assert state.current_needle == "main"

    def test_custom_values(self):
        state = VMState(
            live_stitch_count=80,
            held_stitches={"sleeve": 40},
            row_counter=10,
            current_needle="circular",
        )
        assert state.live_stitch_count == 80
        assert state.held_stitches["sleeve"] == 40
        assert state.row_counter == 10
        assert state.current_needle == "circular"


class TestVMStateValidation:
    def test_rejects_negative_live_stitch_count(self):
        with pytest.raises(ValueError, match="live_stitch_count cannot be negative"):
            VMState(live_stitch_count=-1)

    def test_rejects_negative_held_stitch_count(self):
        with pytest.raises(ValueError, match="held stitch count.*cannot be negative"):
            VMState(held_stitches={"arm": -5})

    def test_zero_live_stitches_allowed(self):
        state = VMState(live_stitch_count=0)
        assert state.live_stitch_count == 0


class TestVMStateHeldStitches:
    def test_multiple_held_groups(self):
        state = VMState(held_stitches={"left_sleeve": 30, "right_sleeve": 30})
        assert len(state.held_stitches) == 2
        assert state.held_stitches["left_sleeve"] == 30
        assert state.held_stitches["right_sleeve"] == 30

    def test_held_stitches_tracked_by_label(self):
        state = VMState()
        state.held_stitches["front"] = 40
        assert "front" in state.held_stitches
        assert state.held_stitches["front"] == 40
