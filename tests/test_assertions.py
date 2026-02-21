import unittest

from tinytest import (
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


def failure_message(func, *args, **kwargs) -> str:
    """Call an assertion that should fail and return its message."""
    try:
        func(*args, **kwargs)
    except AssertionError as exc:
        return str(exc)
    raise AssertionError(f"{func.__name__} did not fail")


class AssertEqualTests(unittest.TestCase):
    def test_passes_for_equal_values(self) -> None:
        assert_equal(1 + 1, 2)
        assert_equal([1, 2], [1, 2])
        assert_equal({"a": 1}, {"a": 1})

    def test_message_shows_both_values(self) -> None:
        message = failure_message(assert_equal, 3, 4)
        self.assertEqual(message, "3 != 4")

    def test_custom_message_is_prefixed(self) -> None:
        message = failure_message(assert_equal, 3, 4, msg="sum")
        self.assertTrue(message.startswith("sum: 3 != 4"))

    def test_single_line_string_diff_marks_changes(self) -> None:
        message = failure_message(assert_equal, "hello world", "hello word")
        self.assertIn("- hello word", message)
        self.assertIn("+ hello world", message)
        self.assertIn("?", message)

    def test_multi_line_string_uses_unified_diff(self) -> None:
        message = failure_message(assert_equal, "a\nb\nc", "a\nx\nc")
        self.assertIn("--- expected", message)
        self.assertIn("+++ actual", message)
        self.assertIn("-x", message)
        self.assertIn("+b", message)

    def test_list_diff_shows_changed_item(self) -> None:
        message = failure_message(assert_equal, [1, 2, 3], [1, 5, 3])
        self.assertIn("-    5,", message)
        self.assertIn("+    2,", message)

    def test_dict_diff_shows_changed_key(self) -> None:
        message = failure_message(assert_equal, {"a": 1, "b": 2}, {"a": 1, "b": 3})
        self.assertIn("-    'b': 3,", message)
        self.assertIn("+    'b': 2,", message)

    def test_no_diff_for_different_types(self) -> None:
        message = failure_message(assert_equal, [1], (1,))
        self.assertNotIn("---", message)

    def test_long_values_are_shortened(self) -> None:
        message = failure_message(assert_equal, "x" * 500, "y")
        first_line = message.splitlines()[0]
        self.assertLess(len(first_line), 200)
        self.assertIn("...", first_line)


class OtherAssertionTests(unittest.TestCase):
    def test_not_equal(self) -> None:
        assert_not_equal(1, 2)
        self.assertEqual(failure_message(assert_not_equal, 1, 1), "1 == 1")

    def test_true_and_false(self) -> None:
        assert_true([0])
        assert_false([])
        self.assertEqual(failure_message(assert_true, 0), "0 is not true")
        self.assertEqual(failure_message(assert_false, "x"), "'x' is not false")

    def test_identity_and_none(self) -> None:
        marker = object()
        assert_is(marker, marker)
        assert_is_none(None)
        assert_is_not_none(0)
        self.assertIn("is not None", failure_message(assert_is_none, 5))
        self.assertIn("unexpected None", failure_message(assert_is_not_none, None))
        self.assertIn("is not", failure_message(assert_is, [], []))

    def test_membership(self) -> None:
        assert_in("a", "abc")
        assert_not_in(4, [1, 2, 3])
        self.assertEqual(
            failure_message(assert_in, 4, [1, 2, 3]), "4 not found in [1, 2, 3]"
        )
        self.assertIn("unexpectedly found", failure_message(assert_not_in, 1, [1]))

    def test_almost_equal(self) -> None:
        assert_almost_equal(0.1 + 0.2, 0.3)
        assert_almost_equal(1.0, 1.05, abs_tol=0.1)
        self.assertIn("is not close to", failure_message(assert_almost_equal, 1.0, 1.1))

    def test_fail(self) -> None:
        self.assertEqual(failure_message(fail, "nope"), "nope")


class AssertRaisesTests(unittest.TestCase):
    def test_catches_expected_exception(self) -> None:
        with assert_raises(ValueError) as info:
            int("not a number")
        self.assertIsInstance(info.value, ValueError)

    def test_catches_subclass(self) -> None:
        with assert_raises(LookupError):
            {}["missing"]

    def test_fails_when_nothing_raised(self) -> None:
        with self.assertRaisesRegex(AssertionError, "ValueError was not raised"):
            with assert_raises(ValueError):
                pass

    def test_other_exceptions_pass_through(self) -> None:
        with self.assertRaises(KeyError):
            with assert_raises(ValueError):
                raise KeyError("x")

    def test_match_checks_message(self) -> None:
        with assert_raises(ValueError, match=r"bad \d+"):
            raise ValueError("bad 42")
        with self.assertRaisesRegex(AssertionError, "does not match"):
            with assert_raises(ValueError, match="good"):
                raise ValueError("bad")

    def test_value_before_catch_is_an_error(self) -> None:
        with self.assertRaises(RuntimeError):
            with assert_raises(ValueError) as info:
                _ = info.value


if __name__ == "__main__":
    unittest.main()
