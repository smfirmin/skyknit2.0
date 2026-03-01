"""
Garment factory registry.

A simple mapping from garment_type string to a callable that returns a GarmentSpec.
User-facing metadata (descriptions, skill levels, embeddings for RAG) lives outside
this codebase and references garment types by key.

Usage
-----
Factories self-register at import time by calling ``register()``.  Import the
``planner.garments`` package to ensure all built-in factories are registered::

    import planner.garments
    from skyknit.planner.garments.registry import get, list_types

    spec = get("top-down-drop-shoulder-pullover")
"""

from __future__ import annotations

from collections.abc import Callable

from skyknit.schemas.garment import GarmentSpec

_REGISTRY: dict[str, Callable[[], GarmentSpec]] = {}


def register(garment_type: str, factory: Callable[[], GarmentSpec]) -> None:
    """Register *factory* under *garment_type*.

    Calling ``factory()`` must return a :class:`~schemas.garment.GarmentSpec`
    whose ``garment_type`` attribute equals the registered key.
    """
    _REGISTRY[garment_type] = factory


def get(garment_type: str) -> GarmentSpec:
    """Return a fresh :class:`~schemas.garment.GarmentSpec` for *garment_type*.

    A new instance is produced on every call — the registry does not cache results.

    Raises
    ------
    KeyError
        If *garment_type* has not been registered.
    """
    if garment_type not in _REGISTRY:
        raise KeyError(f"Unknown garment type: {garment_type!r}")
    return _REGISTRY[garment_type]()


def list_types() -> list[str]:
    """Return a sorted list of all registered garment type keys."""
    return sorted(_REGISTRY.keys())
