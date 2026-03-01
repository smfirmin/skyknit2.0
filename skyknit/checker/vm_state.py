"""
VM state for the Algebraic Checker simulation.

VMState is a mutable cursor that tracks the live needle state as operations
are executed sequentially. It is intentionally mutable — the checker is a
simulation loop, not a pure-functional transformer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VMState:
    """
    Active state of the knitting simulation at any point during IR execution.

    Attributes:
        live_stitch_count: Number of stitches currently on the active needle.
        held_stitches: Stitches moved off the needle, keyed by label
            (e.g. "underarm_left"). The label matches the edge name for the
            corresponding held-stitch edge in ComponentSpec.
        row_counter: Total rows worked so far in this component.
        current_needle: Identifier for the active needle (default "main").
    """

    live_stitch_count: int = 0
    held_stitches: dict[str, int] = field(default_factory=dict)
    row_counter: int = 0
    current_needle: str = "main"

    def __post_init__(self) -> None:
        if self.live_stitch_count < 0:
            raise ValueError(f"live_stitch_count must be >= 0, got {self.live_stitch_count}")
