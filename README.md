<h1 align="left">tinytest</h1>

<p align="left">
  <img src="https://img.shields.io/badge/Python-181717?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Dependencies-None-181717?style=for-the-badge" />
  <img src="https://img.shields.io/badge/License-MIT-181717?style=for-the-badge" />
</p>

A small testing library with no dependencies. Write plain `test_*` functions, run them with `python -m tinytest`, and get a readable diff when something does not match.

---

### About

tinytest started as a class project to see how much of a test runner fits in a few hundred lines of standard library Python.

- **Discovery.** Finds `test_*.py` files under a folder and runs every module level `test_*` function in source order.
- **Assertions.** `assert_equal` prints a diff for unequal strings, lists, tuples and dicts. Plain `assert` works too.
- **Fixtures.** Module level `setup_module`, `teardown_module`, `setup_function` and `teardown_function` hooks.
- **Markers.** `@skip`, `@skip_if` and `@xfail`, plus `skip_test()` to skip from inside a test.
- **CLI.** A summary line at the end and a non-zero exit code when anything fails, so it works in CI.

---

### Install

```sh
git clone https://github.com/Rukioyuza/tinytest
cd tinytest
pip install .
```

Requires Python 3.10 or newer.

---

### Usage

```python
# tests/test_maths.py
import tinytest
from tinytest import assert_equal, assert_raises

numbers = []


def setup_function():
    numbers.clear()
    numbers.extend([3, 1, 2])


def test_sorted():
    assert_equal(sorted(numbers), [1, 2, 3])


def test_bad_index():
    with assert_raises(IndexError):
        numbers[10]


def test_divide_message():
    with assert_raises(ZeroDivisionError, match="division by zero") as info:
        1 / 0
    assert isinstance(info.value, ZeroDivisionError)


@tinytest.skip("waiting on the new parser")
def test_parser():
    ...


@tinytest.xfail("floats are not exact")
def test_floats():
    assert 0.1 + 0.2 == 0.3
```

```sh
python -m tinytest tests
```

```
...sx

3 passed, 1 skipped, 1 xfailed in 0.01s
```

When `assert_equal` fails you get both values and a diff:

```
AssertionError: {'name': 'ada', 'age': 36} != {'name': 'ada', 'age': 37}
--- expected
+++ actual
@@ -1,4 +1,4 @@
 {
-    'age': 37,
+    'age': 36,
     'name': 'ada',
 }
```

---

### Command line

```sh
python -m tinytest [paths ...] [-v] [-k KEYWORD] [-x]
```

| Option | Default | Purpose |
| --- | --- | --- |
| `paths` | `.` | Files or folders to search for tests |
| `-v`, `--verbose` | off | Print one line per test instead of dots |
| `-k KEYWORD` | none | Only run tests whose name contains `KEYWORD` |
| `-x`, `--exitfirst` | off | Stop after the first failure or error |

| Exit code | Meaning |
| --- | --- |
| `0` | Every test passed, was skipped or was an expected failure |
| `1` | At least one test failed, errored or unexpectedly passed |
| `2` | A path given on the command line does not exist |

---

### API

| Name | Purpose |
| --- | --- |
| `assert_equal(actual, expected, msg=None)` | Equality check with a diff for strings, lists, tuples and dicts |
| `assert_not_equal(actual, unexpected)` | Inequality check |
| `assert_true(value)` / `assert_false(value)` | Truthiness checks |
| `assert_is(a, b)` / `assert_is_none(v)` / `assert_is_not_none(v)` | Identity checks |
| `assert_in(member, container)` / `assert_not_in(...)` | Membership checks |
| `assert_almost_equal(a, b, rel_tol, abs_tol)` | Float comparison using `math.isclose` |
| `assert_raises(exc_type, match=None)` | Context manager, the caught exception is on `.value` |
| `fail(msg)` | Fail the current test |
| `@skip(reason)` / `@skip_if(cond, reason)` | Skip a test |
| `@xfail(reason, raises=None)` | Expect a test to fail. If it passes it is reported as `XPASSED` and counts as a failure |
| `skip_test(reason)` | Skip from inside a running test |
| `run(paths)` | Run tests from Python and get a `RunSummary` back |

| Hook | When it runs |
| --- | --- |
| `setup_module()` | Once before the first test in the file |
| `teardown_module()` | Once after the last test in the file |
| `setup_function()` | Before every test in the file |
| `teardown_function()` | After every test in the file, even if the test failed |

---

### Running the tests

```sh
pip install -e .
python -m unittest discover -s tests
python -m tinytest tests
```

The unittest suite checks the runner from the outside, and `tests/test_selfhosted.py` is run by tinytest itself.

---

### License

MIT
