"""Tests for planner.garments.registry — garment factory registry."""

from __future__ import annotations

import pytest

import skyknit.planner.garments  # noqa: F401 — triggers registration of built-in factories
from skyknit.planner.garments.registry import get, list_types, register
from skyknit.schemas.garment import GarmentSpec


class TestListTypes:
    def test_includes_yoke_pullover(self):
        assert "top-down-yoke-pullover" in list_types()

    def test_includes_drop_shoulder(self):
        assert "top-down-drop-shoulder-pullover" in list_types()

    def test_returns_sorted(self):
        types = list_types()
        assert types == sorted(types)


class TestGet:
    def test_returns_garment_spec(self):
        spec = get("top-down-drop-shoulder-pullover")
        assert isinstance(spec, GarmentSpec)

    def test_garment_type_matches_key(self):
        for key in list_types():
            spec = get(key)
            assert spec.garment_type == key

    def test_returns_fresh_instance_each_call(self):
        a = get("top-down-drop-shoulder-pullover")
        b = get("top-down-drop-shoulder-pullover")
        # Frozen dataclasses with equal values compare equal; verify they are
        # independent instances produced by the factory (not a cached object).
        assert a == b  # values equal
        assert a is not b  # distinct objects

    def test_unknown_type_raises_key_error(self):
        with pytest.raises(KeyError, match="nonexistent-type"):
            get("nonexistent-type")


class TestRegister:
    def test_register_custom_factory(self):
        from skyknit.planner.garments.v1_yoke_pullover import make_v1_yoke_pullover

        register("test-custom-type", make_v1_yoke_pullover)
        assert "test-custom-type" in list_types()
        spec = get("test-custom-type")
        assert isinstance(spec, GarmentSpec)
