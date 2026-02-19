"""Markers for skipping tests and marking expected failures."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar, overload

__all__ = ["SkipTest", "XFail", "skip", "skip_if", "skip_test", "xfail"]

F = TypeVar("F", bound=Callable[..., Any])

SKIP_ATTR = "__tinytest_skip__"
XFAIL_ATTR = "__tinytest_xfail__"


class SkipTest(Exception):
    """Raised inside a test to skip it at runtime."""


@dataclass(frozen=True)
class XFail:
    """Details of an expected failure marker."""

    reason: str = ""
    raises: type[BaseException] | None = None


@overload
def skip(reason: F) -> F: ...


@overload
def skip(reason: str = "") -> Callable[[F], F]: ...


def skip(reason: str | F = "") -> F | Callable[[F], F]:
    """Always skip the test. Works as @skip or @skip("reason")."""
    if callable(reason):
        setattr(reason, SKIP_ATTR, "")
        return reason

    def decorator(func: F) -> F:
        setattr(func, SKIP_ATTR, reason)
        return func

    return decorator


def skip_if(condition: bool, reason: str = "") -> Callable[[F], F]:
    """Skip the test when condition is true."""

    def decorator(func: F) -> F:
        if condition:
            setattr(func, SKIP_ATTR, reason)
        return func

    return decorator


def xfail(
    reason: str = "", raises: type[BaseException] | None = None
) -> Callable[[F], F]:
    """Mark a test that is expected to fail.

    If `raises` is given, only that exception type counts as the
    expected failure. A test marked with xfail that passes is reported
    as XPASS and counts as a failure.
    """

    def decorator(func: F) -> F:
        setattr(func, XFAIL_ATTR, XFail(reason, raises))
        return func

    return decorator


def skip_test(reason: str = "") -> None:
    """Skip the current test from inside its body."""
    raise SkipTest(reason)
