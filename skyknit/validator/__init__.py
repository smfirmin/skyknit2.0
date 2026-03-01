"""
Geometric Validator — public API (Phase 1).

Exposed names
-------------
validate_phase1    -- run both Phase 1 checks (compatibility + spatial)
ValidationResult   -- aggregate result (passed: bool, errors: tuple[ValidationError, ...])
ValidationError    -- a single validation failure or warning (join_id, message, severity)
"""

from skyknit.validator.compatibility import ValidationError
from skyknit.validator.phase1 import ValidationResult, validate_phase1

__all__ = ["validate_phase1", "ValidationResult", "ValidationError"]
