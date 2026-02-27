"""
Algebraic Checker: simulation VM for verifying knitting pattern correctness.

The checker validates ComponentIR sequences by simulating stitch count evolution
through each operation, then verifies inter-component join constraints. Errors
are classified as filler-origin (bad stitch counts) or geometric-origin (bad
join topology) to route corrections to the right upstream module.
"""

from .checker import CheckerResult, check_all
from .joins import validate_all_joins, validate_join
from .operations import OperationError, execute_op
from .simulate import CheckerError, SimulationResult, extract_edge_counts, simulate_component
from .vm_state import VMState

__all__ = [
    # Full pipeline
    "check_all",
    "CheckerResult",
    # Simulation
    "simulate_component",
    "SimulationResult",
    "CheckerError",
    "extract_edge_counts",
    # Operations
    "execute_op",
    "OperationError",
    # Joins
    "validate_join",
    "validate_all_joins",
    # VM state
    "VMState",
]
