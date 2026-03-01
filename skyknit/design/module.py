"""
Design Module — translates high-level design intent into a ProportionSpec.

DeterministicDesignModule returns hardcoded ease ratios per EaseLevel.  This
is the deterministic stub; an LLM-backed variant will replace or extend it.

The ease ratio keys (body_ease, sleeve_ease, wrist_ease) match the convention
used throughout the pipeline and end-to-end test fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from skyknit.schemas.proportion import PrecisionPreference, ProportionSpec

# Ease ratio tables keyed by EaseLevel.  All values are pure multipliers
# applied against the corresponding body measurement.
_EASE_RATIOS: dict[str, dict[str, float]] = {
    "fitted": {
        "body_ease": 1.00,
        "sleeve_ease": 1.05,
        "wrist_ease": 1.00,
    },
    "standard": {
        "body_ease": 1.08,
        "sleeve_ease": 1.10,
        "wrist_ease": 1.05,
    },
    "relaxed": {
        "body_ease": 1.15,
        "sleeve_ease": 1.20,
        "wrist_ease": 1.10,
    },
}


class EaseLevel(str, Enum):
    """
    Broad ease category for a garment.

    FITTED   — close to body (minimal ease)
    STANDARD — conventional ease for a comfortable fit
    RELAXED  — generous ease for an oversized look
    """

    FITTED = "fitted"
    STANDARD = "standard"
    RELAXED = "relaxed"


@dataclass(frozen=True)
class DesignInput:
    """Input to the Design Module."""

    garment_type: str
    ease_level: EaseLevel = EaseLevel.STANDARD
    precision: PrecisionPreference = PrecisionPreference.MEDIUM


@dataclass(frozen=True)
class DesignOutput:
    """Output of the Design Module — a ProportionSpec ready for the Planner."""

    proportion_spec: ProportionSpec


@runtime_checkable
class DesignModule(Protocol):
    """Protocol for Design Module implementations."""

    def design(self, design_input: DesignInput) -> DesignOutput: ...


class DeterministicDesignModule:
    """
    Deterministic Design Module.

    Returns hardcoded ease ratios for each EaseLevel.  The garment_type field
    is accepted but unused in v1 — all garment types share the same ease
    vocabulary.  An LLM variant will consult garment_type for proportion
    decisions beyond ease.
    """

    def design(self, di: DesignInput) -> DesignOutput:
        """
        Convert a DesignInput into a DesignOutput.

        Parameters
        ----------
        di:
            Design intent: garment type, ease level, and precision preference.

        Returns
        -------
        DesignOutput
            A ProportionSpec with ease ratios for the requested ease level and
            the requested precision preference.
        """
        ratios = _EASE_RATIOS[di.ease_level.value]
        proportion_spec = ProportionSpec(
            ratios=MappingProxyType(ratios),
            precision=di.precision,
        )
        return DesignOutput(proportion_spec=proportion_spec)
