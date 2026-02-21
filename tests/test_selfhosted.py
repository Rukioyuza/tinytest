"""Tests written in tinytest style, run by tinytest itself.

Run with: python -m tinytest tests
(The unittest files in this folder have no module level test_ functions,
so tinytest skips over them.)
"""

import tinytest
from tinytest import assert_equal, assert_in, assert_raises, assert_true

events: list[str] = []


def setup_function() -> None:
    events.append("setup")


def teardown_function() -> None:
    events.append("teardown")


def test_setup_ran_before_this_test() -> None:
    assert_equal(events[-1], "setup")


def test_equal_failure_has_diff() -> None:
    with assert_raises(AssertionError) as info:
        assert_equal(["a", "b"], ["a", "c"])
    message = str(info.value)
    assert_in("--- expected", message)
    assert_in("+    'b',", message)


def test_raises_match() -> None:
    with assert_raises(ZeroDivisionError, match="division"):
        1 / 0


def test_plain_assert_works_too() -> None:
    assert sum([1, 2, 3]) == 6


@tinytest.skip("shows up as skipped in the summary")
def test_marked_skip() -> None:
    tinytest.fail("skipped tests never run")


@tinytest.xfail("float maths is not exact", raises=AssertionError)
def test_marked_xfail() -> None:
    assert 0.1 + 0.2 == 0.3


def test_teardown_ran_after_previous_tests() -> None:
    assert_true(events.count("teardown") >= 4)
