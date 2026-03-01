"""Tests for checker.vm_state — VMState dataclass."""

import pytest

from skyknit.checker.vm_state import VMState


class TestVMStateDefaults:
    def test_default_values(self):
        state = VMState()
        assert state.live_stitch_count == 0
        assert state.held_stitches == {}
        assert state.row_counter == 0
        assert state.current_needle == "main"

    def test_explicit_construction(self):
        state = VMState(live_stitch_count=80, row_counter=10, current_needle="spare")
        assert state.live_stitch_count == 80
        assert state.row_counter == 10
        assert state.current_needle == "spare"


class TestVMStateValidation:
    def test_rejects_negative_live_stitch_count(self):
        with pytest.raises(ValueError, match="live_stitch_count must be >= 0"):
            VMState(live_stitch_count=-1)

    def test_zero_live_stitch_count_is_valid(self):
        state = VMState(live_stitch_count=0)
        assert state.live_stitch_count == 0


class TestVMStateHeldStitches:
    def test_held_stitches_tracked_by_label(self):
        state = VMState()
        state.held_stitches["underarm_left"] = 12
        state.held_stitches["underarm_right"] = 12
        assert state.held_stitches["underarm_left"] == 12
        assert state.held_stitches["underarm_right"] == 12

    def test_held_stitches_independent_between_instances(self):
        a = VMState()
        b = VMState()
        a.held_stitches["key"] = 5
        assert "key" not in b.held_stitches

    def test_held_stitches_can_be_provided(self):
        state = VMState(held_stitches={"sleeve": 40})
        assert state.held_stitches["sleeve"] == 40
