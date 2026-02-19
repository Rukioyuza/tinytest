"""tinytest: a small zero-dependency testing library."""

from .assertions import (
    assert_almost_equal,
    assert_equal,
    assert_false,
    assert_in,
    assert_is,
    assert_is_none,
    assert_is_not_none,
    assert_not_equal,
    assert_not_in,
    assert_raises,
    assert_true,
    fail,
)
from .markers import SkipTest, skip, skip_if, skip_test, xfail
from .runner import Outcome, Runner, RunSummary, TestResult, run

__all__ = [
    "Outcome",
    "RunSummary",
    "Runner",
    "SkipTest",
    "TestResult",
    "assert_almost_equal",
    "assert_equal",
    "assert_false",
    "assert_in",
    "assert_is",
    "assert_is_none",
    "assert_is_not_none",
    "assert_not_equal",
    "assert_not_in",
    "assert_raises",
    "assert_true",
    "fail",
    "run",
    "skip",
    "skip_if",
    "skip_test",
    "xfail",
]

__version__ = "0.1.0"
