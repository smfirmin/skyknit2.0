"""
Custom exceptions for the knitting pattern generation system.

This module defines domain-specific exceptions that provide clear error messages
and enable proper error handling throughout the agent workflow.
"""

from typing import Any, Dict, List, Optional


class KnittingPatternError(Exception):
    """Base exception for all knitting pattern generation errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class ValidationError(KnittingPatternError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        expected: Optional[str] = None,
    ):
        super().__init__(message)
        self.field = field
        self.value = value
        self.expected = expected


class AgentProcessingError(KnittingPatternError):
    """Raised when an agent fails to process its input."""

    def __init__(
        self, message: str, agent_type: str, stage: Optional[str] = None, **kwargs
    ):
        super().__init__(message, kwargs)
        self.agent_type = agent_type
        self.stage = stage


class RequirementsParsingError(AgentProcessingError):
    """Raised when requirements cannot be parsed from user input."""

    def __init__(self, message: str, user_request: Optional[str] = None):
        super().__init__(message, "requirements")
        self.user_request = user_request


class FabricSpecificationError(AgentProcessingError):
    """Raised when fabric specifications cannot be determined."""

    def __init__(self, message: str, yarn_weight: Optional[str] = None):
        super().__init__(message, "fabric")
        self.yarn_weight = yarn_weight


class ConstructionPlanningError(AgentProcessingError):
    """Raised when construction planning fails."""

    def __init__(self, message: str, construction_type: Optional[str] = None):
        super().__init__(message, "construction")
        self.construction_type = construction_type


class StitchCalculationError(AgentProcessingError):
    """Raised when stitch calculations fail or produce invalid results."""

    def __init__(
        self,
        message: str,
        calculation_type: Optional[str] = None,
        dimensions: Optional[Dict[str, float]] = None,
    ):
        super().__init__(message, "stitch")
        self.calculation_type = calculation_type
        self.dimensions = dimensions


class PatternValidationError(AgentProcessingError):
    """Raised when pattern validation fails."""

    def __init__(
        self,
        message: str,
        validation_type: Optional[str] = None,
        errors: Optional[List[str]] = None,
    ):
        super().__init__(message, "validation")
        self.validation_type = validation_type
        self.errors = errors or []


class OutputGenerationError(AgentProcessingError):
    """Raised when output generation fails."""

    def __init__(self, message: str, output_format: Optional[str] = None):
        super().__init__(message, "output")
        self.output_format = output_format


class WorkflowOrchestrationError(KnittingPatternError):
    """Raised when workflow orchestration fails."""

    def __init__(
        self,
        message: str,
        failed_stage: Optional[str] = None,
        agent_type: Optional[str] = None,
    ):
        super().__init__(message)
        self.failed_stage = failed_stage
        self.agent_type = agent_type


class DimensionError(KnittingPatternError):
    """Raised when dimensions are invalid or impossible to achieve."""

    def __init__(
        self,
        message: str,
        target_dimensions: Optional[Dict[str, float]] = None,
        actual_dimensions: Optional[Dict[str, float]] = None,
    ):
        super().__init__(message)
        self.target_dimensions = target_dimensions
        self.actual_dimensions = actual_dimensions


class GaugeError(KnittingPatternError):
    """Raised when gauge calculations are invalid."""

    def __init__(
        self,
        message: str,
        gauge: Optional[Dict[str, float]] = None,
        yarn_weight: Optional[str] = None,
    ):
        super().__init__(message)
        self.gauge = gauge
        self.yarn_weight = yarn_weight


class UnsupportedFeatureError(KnittingPatternError):
    """Raised when a requested feature is not yet supported."""

    def __init__(self, message: str, feature: Optional[str] = None):
        super().__init__(message)
        self.feature = feature


class ConfigurationError(KnittingPatternError):
    """Raised when system configuration is invalid."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(message)
        self.config_key = config_key
