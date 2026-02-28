"""
Algebraic Checker — public API.

The entry point for consumers is ``check_all``, which takes a ShapeManifest,
a dict of ComponentIRs, and a dict of ConstraintObjects and returns a
``CheckerResult`` containing all validation errors found.

Exposed names
-------------
check_all       -- run the full checker pipeline
CheckerResult   -- top-level result (passed: bool, errors: tuple[CheckerError, ...])
CheckerError    -- a single validation failure (component, op index, message, type)
"""

from checker.checker import CheckerResult, check_all
from checker.simulate import CheckerError

__all__ = ["check_all", "CheckerResult", "CheckerError"]
