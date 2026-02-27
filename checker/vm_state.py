"""
Virtual machine state for the Algebraic Checker.

VMState tracks the live stitch count, held stitches, and row counter as the
checker simulates a ComponentIR sequence. VMState is frozen — operation handlers
return new instances rather than mutating state in place.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VMState:
    """
    Simulation state for a single component's operation sequence.

    Attributes:
        live_stitch_count: Number of stitches currently on the needles.
        held_stitches: Stitches placed on hold, keyed by label.
        row_counter: Total rows worked so far.
        current_needle: Active needle identifier (for future multi-needle support).
    """

    live_stitch_count: int = 0
    held_stitches: dict[str, int] = field(default_factory=dict)
    row_counter: int = 0
    current_needle: str = "main"

    def __post_init__(self) -> None:
        if self.live_stitch_count < 0:
            raise ValueError(f"live_stitch_count cannot be negative, got {self.live_stitch_count}")
        if self.row_counter < 0:
            raise ValueError(f"row_counter cannot be negative, got {self.row_counter}")
        for label, count in self.held_stitches.items():
            if count < 0:
                raise ValueError(f"held stitch count for '{label}' cannot be negative, got {count}")
