"""Dataset acquisition, construction, validation, and leakage-safe splitting."""

from provtrust.datasets.split import SplitAssignment, assign_grouped_splits
from provtrust.datasets.synthetic_builder import FactorialDesign, SyntheticSeed, build_factorial
from provtrust.datasets.validate import DatasetAudit, validate_trials

__all__ = [
    "DatasetAudit",
    "FactorialDesign",
    "SplitAssignment",
    "SyntheticSeed",
    "assign_grouped_splits",
    "build_factorial",
    "validate_trials",
]
