"""Assertion helpers with readable failure messages."""

from __future__ import annotations

import difflib
import math
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Generic, TypeVar

__all__ = [
    "RaisesInfo",
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
]

E = TypeVar("E", bound=BaseException)

_MAX_REPR = 80


def _short_repr(value: Any) -> str:
    """Return repr(value), cut down to a readable length."""
    text = repr(value)
    if len(text) > _MAX_REPR:
        text = text[: _MAX_REPR - 3] + "..."
    return text


def _lines_for_diff(value: Any) -> list[str]:
    """Format a value as a list of lines so two values can be diffed."""
    if isinstance(value, str):
        return value.splitlines() or [""]
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda item: repr(item[0]))
        return ["{"] + [f"    {k!r}: {v!r}," for k, v in items] + ["}"]
    if isinstance(value, (list, tuple)):
        open_, close = ("[", "]") if isinstance(value, list) else ("(", ")")
        return [open_] + [f"    {item!r}," for item in value] + [close]
    return [repr(value)]


def _diff(expected: Any, actual: Any) -> str:
    """Build a diff between expected and actual, or "" if not useful."""
    diffable = (str, list, tuple, dict)
    if not (isinstance(expected, diffable) and isinstance(actual, diffable)):
        return ""
    if type(expected) is not type(actual):
        return ""
    old = _lines_for_diff(expected)
    new = _lines_for_diff(actual)
    if isinstance(expected, str) and len(old) == 1 and len(new) == 1:
        # Single line strings: ndiff marks the changed characters with ^.
        return "\n".join(difflib.ndiff(old, new)).rstrip()
    diff = difflib.unified_diff(
        old, new, fromfile="expected", tofile="actual", lineterm=""
    )
    return "\n".join(diff)


def _with_msg(text: str, msg: str | None) -> str:
    return f"{msg}: {text}" if msg else text


def fail(msg: str = "test failed") -> None:
    """Fail the current test straight away."""
    raise AssertionError(msg)


def assert_equal(actual: Any, expected: Any, msg: str | None = None) -> None:
    """Check that actual == expected, showing a diff when they differ."""
    if actual == expected:
        return
    text = f"{_short_repr(actual)} != {_short_repr(expected)}"
    diff = _diff(expected, actual)
    if diff:
        text += "\n" + diff
    raise AssertionError(_with_msg(text, msg))


def assert_not_equal(actual: Any, unexpected: Any, msg: str | None = None) -> None:
    """Check that actual != unexpected."""
    if actual != unexpected:
        return
    text = f"{_short_repr(actual)} == {_short_repr(unexpected)}"
    raise AssertionError(_with_msg(text, msg))


def assert_true(value: Any, msg: str | None = None) -> None:
    """Check that value is truthy."""
    if not value:
        raise AssertionError(_with_msg(f"{_short_repr(value)} is not true", msg))


def assert_false(value: Any, msg: str | None = None) -> None:
    """Check that value is falsy."""
    if value:
        raise AssertionError(_with_msg(f"{_short_repr(value)} is not false", msg))


def assert_is(actual: Any, expected: Any, msg: str | None = None) -> None:
    """Check that actual is the same object as expected."""
    if actual is not expected:
        text = f"{_short_repr(actual)} is not {_short_repr(expected)}"
        raise AssertionError(_with_msg(text, msg))


def assert_is_none(value: Any, msg: str | None = None) -> None:
    """Check that value is None."""
    if value is not None:
        raise AssertionError(_with_msg(f"{_short_repr(value)} is not None", msg))


def assert_is_not_none(value: Any, msg: str | None = None) -> None:
    """Check that value is not None."""
    if value is None:
        raise AssertionError(_with_msg("unexpected None", msg))


def assert_in(member: Any, container: Any, msg: str | None = None) -> None:
    """Check that member is in container."""
    if member not in container:
        text = f"{_short_repr(member)} not found in {_short_repr(container)}"
        raise AssertionError(_with_msg(text, msg))


def assert_not_in(member: Any, container: Any, msg: str | None = None) -> None:
    """Check that member is not in container."""
    if member in container:
        text = f"{_short_repr(member)} unexpectedly found in {_short_repr(container)}"
        raise AssertionError(_with_msg(text, msg))


def assert_almost_equal(
    actual: float,
    expected: float,
    rel_tol: float = 1e-9,
    abs_tol: float = 1e-12,
    msg: str | None = None,
) -> None:
    """Check that two numbers are close, using math.isclose."""
    if math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=abs_tol):
        return
    text = (
        f"{actual!r} is not close to {expected!r} "
        f"(difference {abs(actual - expected)!r})"
    )
    raise AssertionError(_with_msg(text, msg))


class RaisesInfo(Generic[E]):
    """Holds the exception caught by assert_raises."""

    def __init__(self) -> None:
        self._value: E | None = None

    @property
    def value(self) -> E:
        """The caught exception (only valid after the with block)."""
        if self._value is None:
            raise RuntimeError("no exception has been caught yet")
        return self._value


@contextmanager
def assert_raises(
    expected: type[E], match: str | None = None
) -> Iterator[RaisesInfo[E]]:
    """Check that the with block raises `expected`.

    If `match` is given it is searched for in str(exception) as a regex.
    """
    info: RaisesInfo[E] = RaisesInfo()
    try:
        yield info
    except expected as exc:
        if match is not None and not re.search(match, str(exc)):
            raise AssertionError(
                f"{type(exc).__name__}({str(exc)!r}) does not match {match!r}"
            ) from exc
        info._value = exc
    else:
        raise AssertionError(f"{expected.__name__} was not raised")
