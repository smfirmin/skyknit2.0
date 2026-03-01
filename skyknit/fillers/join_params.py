"""
Join parameter reader for the Stitch Fillers layer.

read_join_parameters extracts the parameters owned by a specific join type
and returns them as a plain dict.  The returned dict is a copy — mutating it
never affects the original Join object.

Join-owned parameters by type (from join_types.yaml):
  CAST_ON_JOIN  — cast_on_count, cast_on_method
  PICKUP        — pickup_ratio, pickup_direction
  SEAM          — seam_method
  CONTINUATION  — (none)
  HELD_STITCH   — (none)
"""

from __future__ import annotations

from typing import Any

from skyknit.topology.types import Join, JoinType


def read_join_parameters(join: Join, edge_ref: str) -> dict[str, Any]:
    """
    Return a copy of the parameters relevant to *edge_ref*'s side of *join*.

    For the current join types all owned parameters apply to the join as a
    whole, not to one specific side, so the full parameters dict is returned
    regardless of which edge_ref is passed.  Future join types with
    asymmetric parameters can override this by key.

    Parameters
    ----------
    join:
        The Join whose parameters are being read.
    edge_ref:
        The "component.edge" reference for the calling component's edge.
        Included for forward compatibility with asymmetric join types.

    Returns
    -------
    A plain (mutable) dict copy of the relevant parameters.  Empty dict for
    join types that own no parameters (CONTINUATION, HELD_STITCH).
    """
    match join.join_type:
        case JoinType.CAST_ON_JOIN:
            return _extract(join, ("cast_on_count", "cast_on_method"))
        case JoinType.PICKUP:
            return _extract(join, ("pickup_ratio", "pickup_direction"))
        case JoinType.SEAM:
            return _extract(join, ("seam_method",))
        case JoinType.CONTINUATION | JoinType.HELD_STITCH:
            return {}

    return {}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _extract(join: Join, keys: tuple[str, ...]) -> dict[str, Any]:
    """Return a plain dict with only the given keys, skipping absent ones."""
    return {k: join.parameters[k] for k in keys if k in join.parameters}
